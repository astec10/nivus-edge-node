#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash deploy/update.sh" >&2
  exit 1
fi

SOURCE_ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
INSTALL_ROOT=/opt/nivus-compose
RELEASES="$INSTALL_ROOT/releases"
CURRENT="$INSTALL_ROOT/current"
SERVICE=nivus-compose-telemetry.service
UNIT_FILE="/etc/systemd/system/$SERVICE"
BACKUP_ROOT=/var/backups/nivus-compose
SWITCHED=0
READY=0
OVERRIDE_FILE=
NEW_RELEASE=
OLD_RELEASE=
BACKUP_DIR=

compose_release() {
  local release=$1
  shift
  docker compose --project-name nivus-edge --project-directory "$release" \
    --env-file "$release/.env" -f "$release/docker-compose.yml" "$@"
}

new_compose() {
  docker compose --project-name nivus-edge --project-directory "$NEW_RELEASE" \
    --env-file "$NEW_RELEASE/.env" -f "$NEW_RELEASE/docker-compose.yml" \
    -f "$OVERRIDE_FILE" "$@"
}

fail_and_rollback() {
  local rc=$?
  trap - ERR INT TERM
  if [[ $SWITCHED -eq 1 && $READY -eq 0 ]]; then
    set +e
    echo "A atualização falhou após a troca; voltando à release anterior." >&2
    systemctl stop "$SERVICE" >/dev/null 2>&1
    local rollback_link="$INSTALL_ROOT/.current-rollback-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    if ln -s "$OLD_RELEASE" "$rollback_link" && mv -Tf -- "$rollback_link" "$CURRENT"; then
      if [[ -n "$BACKUP_DIR" && -s "$BACKUP_DIR/$SERVICE" ]]; then
        cp -a "$BACKUP_DIR/$SERVICE" "$UNIT_FILE"
        systemctl daemon-reload
      fi
      compose_release "$OLD_RELEASE" up -d --no-build
      systemctl restart "$SERVICE"
      local old_port
      old_port=$(sed -n 's/^NIVUS_HTTPS_PORT=//p' "$OLD_RELEASE/.env" | tr -d '\r' | tail -n1)
      if [[ "$old_port" =~ ^[0-9]+$ ]] &&
         curl -kfsS --connect-timeout 3 --max-time 8 "https://127.0.0.1:$old_port/health" >/dev/null &&
         [[ $(curl -k -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$old_port/api/telemetry") == 401 ]] &&
         systemctl is-active --quiet "$SERVICE"; then
        echo "Rollback do código confirmado; banco, release e backup foram preservados." >&2
      else
        echo "Rollback iniciado, mas as verificações falharam. Preserve $BACKUP_DIR para recuperação." >&2
      fi
    else
      echo "Não foi possível trocar o link current durante o rollback. Preserve $BACKUP_DIR." >&2
    fi
  else
    echo "Falha no preflight/build; release ativa e serviços não foram alterados." >&2
  fi
  [[ -z "$OVERRIDE_FILE" ]] || rm -f -- "$OVERRIDE_FILE"
  exit "$rc"
}
trap fail_and_rollback ERR INT TERM

[[ -d "$SOURCE_ROOT/.git" && -f "$SOURCE_ROOT/docker-compose.yml" ]] || {
  echo "Use um clone Git limpo do repositório astec10/nivus-edge-node." >&2
  exit 2
}
[[ $(git -C "$SOURCE_ROOT" rev-parse --show-toplevel) == "$SOURCE_ROOT" ]] || {
  echo "Raiz Git inesperada." >&2
  exit 2
}
REMOTE=$(git -C "$SOURCE_ROOT" remote get-url origin)
case "$REMOTE" in
  https://github.com/astec10/nivus-edge-node.git|https://github.com/astec10/nivus-edge-node|git@github.com:astec10/nivus-edge-node.git|ssh://git@github.com/astec10/nivus-edge-node.git) ;;
  *) echo "A origem Git não é astec10/nivus-edge-node; nenhuma alteração foi feita." >&2; exit 2 ;;
esac
[[ -z "$(git -C "$SOURCE_ROOT" status --porcelain)" ]] || {
  echo "O clone contém alterações locais; use uma cópia limpa para atualizar." >&2
  exit 2
}
TARGET_SHA=$(git -C "$SOURCE_ROOT" rev-parse HEAD)
[[ "$TARGET_SHA" =~ ^[a-f0-9]{40}$ ]] || { echo "Commit inválido." >&2; exit 2; }

for command in git tar docker systemctl curl python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "Comando necessário ausente: $command" >&2; exit 2; }
done
docker compose version >/dev/null
[[ -L "$CURRENT" && -d "$CURRENT" ]] || { echo "Instalação Compose não encontrada em $CURRENT." >&2; exit 2; }
OLD_RELEASE=$(readlink -f -- "$CURRENT")
case "$OLD_RELEASE" in "$RELEASES"/*) ;; *) echo "Release ativa fora de $RELEASES; atualização recusada." >&2; exit 2 ;; esac
[[ -f "$CURRENT/.env" && -f "$CURRENT/docker-compose.yml" && -f "$CURRENT/deploy/backup.sh" ]] || {
  echo "Arquivos esperados não encontrados na release ativa." >&2
  exit 2
}
[[ -s "$UNIT_FILE" && -d /etc/nivus-compose/secrets ]] || {
  echo "Serviço ou segredos externos não encontrados." >&2
  exit 2
}
systemctl is-active --quiet docker.service
systemctl is-active --quiet "$SERVICE"

HTTPS_PORT=$(sed -n 's/^NIVUS_HTTPS_PORT=//p' "$CURRENT/.env" | tr -d '\r' | tail -n1)
DATA_DIR=$(sed -n 's/^NIVUS_DATA_DIR=//p' "$CURRENT/.env" | tr -d '\r' | tail -n1)
[[ "$HTTPS_PORT" =~ ^[0-9]+$ && "$HTTPS_PORT" -ge 1 && "$HTTPS_PORT" -le 65535 ]] || {
  echo "Porta HTTPS inválida em .env." >&2
  exit 2
}
[[ "$DATA_DIR" == /* && -s "$DATA_DIR/nivus.db" ]] || {
  echo "Banco persistente não encontrado no caminho configurado." >&2
  exit 2
}
curl -kfsS --connect-timeout 3 --max-time 8 "https://127.0.0.1:$HTTPS_PORT/health" >/dev/null
PRE_AUTH=$(curl -k -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$HTTPS_PORT/api/telemetry")
[[ "$PRE_AUTH" == 401 ]] || { echo "Proteção da API não passou no preflight (HTTP $PRE_AUTH)." >&2; exit 2; }

ACTIVE_SHA=
if [[ -s "$CURRENT/.nivus-revision" ]]; then
  ACTIVE_SHA=$(cat "$CURRENT/.nivus-revision")
else
  ACTIVE_NAME=\${OLD_RELEASE##*/}
  ACTIVE_SHA=\${ACTIVE_NAME##*-}
fi
if [[ "$ACTIVE_SHA" == "$TARGET_SHA" ]]; then
  echo "A release $TARGET_SHA já está ativa; nenhuma alteração necessária."
  READY=1
  exit 0
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SHORT_SHA=\${TARGET_SHA:0:12}
NEW_RELEASE="$RELEASES/$STAMP-$TARGET_SHA"
[[ ! -e "$NEW_RELEASE" && ! -L "$NEW_RELEASE" ]] || { echo "Pasta da release já existe." >&2; exit 2; }
install -d -m 755 "$RELEASES" "$NEW_RELEASE"
git -C "$SOURCE_ROOT" archive --format=tar "$TARGET_SHA" | tar -C "$NEW_RELEASE" -xf -
cp -a "$CURRENT/.env" "$NEW_RELEASE/.env"
chmod 600 "$NEW_RELEASE/.env"
printf '%s\n' "$TARGET_SHA" > "$NEW_RELEASE/.nivus-revision"
chmod 644 "$NEW_RELEASE/.nivus-revision"

OVERRIDE_FILE=$(mktemp "/run/nivus-compose-update-$SHORT_SHA-XXXXXX.yml")
chmod 600 "$OVERRIDE_FILE"
cat > "$OVERRIDE_FILE" <<EOF
services:
  api:
    image: nivus-edge-api:update-$SHORT_SHA
  worker:
    image: nivus-edge-api:update-$SHORT_SHA
  web:
    image: nivus-edge-web:update-$SHORT_SHA
EOF
new_compose config --quiet

echo "[1/5] Construindo imagens em sequência; a release ativa continua atendendo."
COMPOSE_PARALLEL_LIMIT=1 new_compose build api
COMPOSE_PARALLEL_LIMIT=1 new_compose build web
docker image inspect "nivus-edge-api:update-$SHORT_SHA" "nivus-edge-web:update-$SHORT_SHA" >/dev/null

echo "[2/5] Criando backup SQLite consistente e preservando o serviço."
BACKUP_OUTPUT=$(bash "$CURRENT/deploy/backup.sh")
printf '%s\n' "$BACKUP_OUTPUT"
BACKUP_DIR=$(printf '%s\n' "$BACKUP_OUTPUT" | sed -n 's/^Backup SQLite consistent and configuration saved in //p' | tail -n1)
[[ "$BACKUP_DIR" == "$BACKUP_ROOT"/* && -d "$BACKUP_DIR" ]] || {
  echo "Não foi possível confirmar o diretório do backup." >&2
  exit 2
}
cp -a "$UNIT_FILE" "$BACKUP_DIR/$SERVICE"
chmod 600 "$BACKUP_DIR/$SERVICE"

TELEMETRY_BEFORE=$(python3 - "$DATA_DIR/nivus.db" <<'PY'
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1], timeout=30)
try:
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise SystemExit("SQLite quick_check falhou antes da atualização")
    print(conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0])
finally:
    conn.close()
PY
)

echo "[3/5] Trocando release e reiniciando os serviços Nivus."
systemctl stop "$SERVICE"
NEW_LINK="$INSTALL_ROOT/.current-update-$STAMP"
ln -s "$NEW_RELEASE" "$NEW_LINK"
mv -Tf -- "$NEW_LINK" "$CURRENT"
SWITCHED=1
install -m 644 "$NEW_RELEASE/deploy/nivus-compose-telemetry.service" "$UNIT_FILE"
systemctl daemon-reload
new_compose up -d --no-build
systemctl restart "$SERVICE"

echo "[4/5] Conferindo saúde HTTPS, autenticação, contêineres, painel de marcos e SQLite."
HEALTH_OK=0
for attempt in $(seq 1 45); do
  if curl -kfsS --connect-timeout 2 --max-time 5 "https://127.0.0.1:$HTTPS_PORT/health" >/dev/null; then HEALTH_OK=1; break; fi
  sleep 2
done
[[ "$HEALTH_OK" == 1 ]]
AUTH_STATUS=$(curl -k -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$HTTPS_PORT/api/telemetry")
[[ "$AUTH_STATUS" == 401 ]]
for service in api worker mqtt web; do
  container_id=$(new_compose ps -q "$service")
  [[ -n "$container_id" ]]
  [[ $(docker inspect -f '{{.State.Status}}' "$container_id") == running ]]
done
[[ $(docker inspect -f '{{.State.Health.Status}}' "$(new_compose ps -q api)") == healthy ]]
[[ $(docker inspect -f '{{.State.Health.Status}}' "$(new_compose ps -q mqtt)") == healthy ]]
PROGRESS_HTML=$(curl -kfsS --connect-timeout 3 --max-time 8 "https://127.0.0.1:$HTTPS_PORT/PROGRESS.html")
grep -q 'id="milestones"' <<< "$PROGRESS_HTML"
curl -kfsS --connect-timeout 3 --max-time 8 "https://127.0.0.1:$HTTPS_PORT/progress.js" | grep -q 'filterStatus'
python3 - "$DATA_DIR/nivus.db" <<'PY'
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1], timeout=30)
try:
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise SystemExit("SQLite quick_check falhou após a atualização")
finally:
    conn.close()
PY
MAINTENANCE_DIR=$(sed -n 's/^NIVUS_MAINTENANCE_STATE_DIR=//p' "$CURRENT/.env" | tr -d '\r' | tail -n1)
if [[ -n "$MAINTENANCE_DIR" && -s "$MAINTENANCE_DIR/state.json" ]] &&
   grep -q '"enabled"[[:space:]]*:[[:space:]]*true' "$MAINTENANCE_DIR/state.json"; then
  echo "Coleta está em manutenção; não é esperado receber novas amostras."
else
  sleep 20
  TELEMETRY_AFTER=$(python3 - "$DATA_DIR/nivus.db" <<'PY'
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1], timeout=30)
try:
    print(conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0])
finally:
    conn.close()
PY
)
  [[ "$TELEMETRY_AFTER" -gt "$TELEMETRY_BEFORE" ]]
fi
systemctl is-active --quiet "$SERVICE"

echo "[5/5] Atualização concluída; release anterior e backup foram mantidos."
printf 'Release ativa: %s\n' "$TARGET_SHA"
printf 'Backup consistente: %s\n' "$BACKUP_DIR"
printf 'Health HTTPS: 200; telemetria sem token: %s\n' "$AUTH_STATUS"
READY=1
trap - ERR INT TERM
rm -f -- "$OVERRIDE_FILE"
