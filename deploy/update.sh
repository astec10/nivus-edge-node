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
TIME_SYNC_SERVICE=nivus-time-sync.service
TIME_SYNC_UNIT_FILE="/etc/systemd/system/$TIME_SYNC_SERVICE"
TIME_SYNC_ENV=/etc/nivus-compose/time-sync.env
TIME_SYNC_DROPIN_DIR=/etc/systemd/timesyncd.conf.d
TIME_SYNC_BACKUP_DIR=/var/backups/nivus-compose/time-sync
BACKUP_ROOT=/var/backups/nivus-compose
TIME_SYNC_WAS_PRESENT=0
TIME_SYNC_WAS_ACTIVE=0
TIME_SYNC_WAS_ENABLED=0
TIME_SYNC_DROPIN_DIR_CREATED=0
TIME_SYNC_BACKUP_DIR_CREATED=0
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
    echo "A promoção falhou; restaurando a release anterior e seus serviços." >&2
    systemctl stop "$SERVICE" >/dev/null 2>&1
    systemctl stop "$TIME_SYNC_SERVICE" >/dev/null 2>&1 || true
    local rollback_link="$INSTALL_ROOT/.current-rollback-$(date -u +%Y%m%dT%H%M%SZ)-$"
    if ln -s "$OLD_RELEASE" "$rollback_link" && mv -Tf -- "$rollback_link" "$CURRENT"; then
      if [[ -n "$BACKUP_DIR" && -s "$BACKUP_DIR/$SERVICE" ]]; then
        cp -a "$BACKUP_DIR/$SERVICE" "$UNIT_FILE"
      fi
      if [[ -n "$BACKUP_DIR" && -s "$BACKUP_DIR/time-sync-state" ]]; then
        local previous_present previous_active previous_enabled
        read -r previous_present previous_active previous_enabled < "$BACKUP_DIR/time-sync-state"
        if [[ "$previous_present" == 1 && -s "$BACKUP_DIR/$TIME_SYNC_SERVICE" ]]; then
          cp -a "$BACKUP_DIR/$TIME_SYNC_SERVICE" "$TIME_SYNC_UNIT_FILE"
        else
          rm -f -- "$TIME_SYNC_UNIT_FILE"
        fi
        if [[ -s "$BACKUP_DIR/time-sync.env" ]]; then
          cp -a "$BACKUP_DIR/time-sync.env" "$TIME_SYNC_ENV"
        else
          rm -f -- "$TIME_SYNC_ENV"
        fi
        systemctl daemon-reload
        if [[ "$previous_present" == 1 ]]; then
          if [[ "$previous_enabled" == 1 ]]; then systemctl enable "$TIME_SYNC_SERVICE" >/dev/null 2>&1; else systemctl disable "$TIME_SYNC_SERVICE" >/dev/null 2>&1; fi
          if [[ "$previous_active" == 1 ]]; then systemctl start "$TIME_SYNC_SERVICE" >/dev/null 2>&1; else systemctl stop "$TIME_SYNC_SERVICE" >/dev/null 2>&1; fi
        else
          systemctl disable "$TIME_SYNC_SERVICE" >/dev/null 2>&1 || true
        fi
        if [[ "$TIME_SYNC_DROPIN_DIR_CREATED" == 1 ]]; then rmdir "$TIME_SYNC_DROPIN_DIR" 2>/dev/null || true; fi
        if [[ "$TIME_SYNC_BACKUP_DIR_CREATED" == 1 ]]; then rmdir "$TIME_SYNC_BACKUP_DIR" 2>/dev/null || true; fi
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
if systemctl cat "$TIME_SYNC_SERVICE" >/dev/null 2>&1; then
  [[ -s "$TIME_SYNC_UNIT_FILE" ]] || { echo "A unidade NTP existente não pertence ao atualizador Nivus; atualização recusada." >&2; exit 2; }
  grep -q "ExecStart=/usr/bin/python3 /opt/nivus-compose/current/deploy/nivus-timesyncd.py" "$TIME_SYNC_UNIT_FILE" || {
    echo "A unidade NTP existente não corresponde ao controlador Nivus; atualização recusada." >&2
    exit 2
  }
  TIME_SYNC_WAS_PRESENT=1
  systemctl is-active --quiet "$TIME_SYNC_SERVICE" && TIME_SYNC_WAS_ACTIVE=1 || true
  systemctl is-enabled --quiet "$TIME_SYNC_SERVICE" && TIME_SYNC_WAS_ENABLED=1 || true
elif [[ -e "$TIME_SYNC_UNIT_FILE" || -L "$TIME_SYNC_UNIT_FILE" ]]; then
  echo "Há um arquivo de unidade NTP conflitante; atualização recusada." >&2
  exit 2
fi
if [[ -e "$TIME_SYNC_ENV" || -L "$TIME_SYNC_ENV" ]]; then
  [[ -f "$TIME_SYNC_ENV" && ! -L "$TIME_SYNC_ENV" ]] || { echo "Ambiente do controlador NTP inválido; atualização recusada." >&2; exit 2; }
fi
validate_protected_dir() {
  local path=$1 owner mode
  [[ -d "$path" && ! -L "$path" ]] || return 1
  owner=$(stat -c '%u' "$path")
  mode=$(stat -c '%a' "$path")
  [[ "$owner" == 0 && "$mode" =~ ^[0-7]{3,4}$ ]] && (( (8#$mode & 0022) == 0 ))
}
for protected_dir in "$TIME_SYNC_DROPIN_DIR" "$TIME_SYNC_BACKUP_DIR"; do
  if [[ -e "$protected_dir" || -L "$protected_dir" ]]; then
    validate_protected_dir "$protected_dir" || {
      echo "Diretório NTP existente não é seguro; atualização recusada sem alterá-lo." >&2
      exit 2
    }
  fi
done
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
  ACTIVE_NAME=${OLD_RELEASE##*/}
  ACTIVE_SHA=${ACTIVE_NAME##*-}
fi
if [[ "$ACTIVE_SHA" == "$TARGET_SHA" ]]; then
  echo "A release $TARGET_SHA já está ativa; nenhuma alteração necessária."
  READY=1
  exit 0
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SHORT_SHA=${TARGET_SHA:0:12}
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
BACKUP_DIR=$(printf '%s\n' "$BACKUP_OUTPUT" | sed -n 's/^Backup SQLite consistente e configuração salvos em //p' | tail -n1)
[[ "$BACKUP_DIR" == "$BACKUP_ROOT"/* && -d "$BACKUP_DIR" ]] || {
  echo "Não foi possível confirmar o diretório do backup." >&2
  exit 2
}
cp -a "$UNIT_FILE" "$BACKUP_DIR/$SERVICE"
chmod 600 "$BACKUP_DIR/$SERVICE"
printf '%s %s %s\n' "$TIME_SYNC_WAS_PRESENT" "$TIME_SYNC_WAS_ACTIVE" "$TIME_SYNC_WAS_ENABLED" > "$BACKUP_DIR/time-sync-state"
chmod 600 "$BACKUP_DIR/time-sync-state"
if [[ "$TIME_SYNC_WAS_PRESENT" == 1 ]]; then
  cp -a "$TIME_SYNC_UNIT_FILE" "$BACKUP_DIR/$TIME_SYNC_SERVICE"
  chmod 600 "$BACKUP_DIR/$TIME_SYNC_SERVICE"
fi
if [[ -f "$TIME_SYNC_ENV" && ! -L "$TIME_SYNC_ENV" ]]; then
  cp -a "$TIME_SYNC_ENV" "$BACKUP_DIR/time-sync.env"
  chmod 600 "$BACKUP_DIR/time-sync.env"
fi
if ! grep -q '^NIVUS_TIME_SYNC_DIR=' "$NEW_RELEASE/.env"; then
  printf 'NIVUS_TIME_SYNC_DIR=/run/nivus-time-sync\n' >> "$NEW_RELEASE/.env"
fi


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
SWITCHED=1
systemctl stop "$SERVICE"
NEW_LINK="$INSTALL_ROOT/.current-update-$STAMP"
ln -s "$NEW_RELEASE" "$NEW_LINK"
mv -Tf -- "$NEW_LINK" "$CURRENT"
if [[ ! -e "$TIME_SYNC_DROPIN_DIR" && ! -L "$TIME_SYNC_DROPIN_DIR" ]]; then
  install -d -m 755 "$TIME_SYNC_DROPIN_DIR"
  TIME_SYNC_DROPIN_DIR_CREATED=1
elif ! validate_protected_dir "$TIME_SYNC_DROPIN_DIR"; then
  echo "Diretório de configuração timesyncd inválido; abortando." >&2
  exit 2
fi
if [[ ! -e "$TIME_SYNC_BACKUP_DIR" && ! -L "$TIME_SYNC_BACKUP_DIR" ]]; then
  install -d -m 700 "$TIME_SYNC_BACKUP_DIR"
  TIME_SYNC_BACKUP_DIR_CREATED=1
elif ! validate_protected_dir "$TIME_SYNC_BACKUP_DIR"; then
  echo "Diretório de backup NTP inválido; abortando." >&2
  exit 2
fi
RUNTIME_UID=$(sed -n 's/^NIVUS_RUNTIME_UID=//p' "$CURRENT/.env" | tr -d '\r' | tail -n1)
RUNTIME_GID=$(sed -n 's/^NIVUS_RUNTIME_GID=//p' "$CURRENT/.env" | tr -d '\r' | tail -n1)
[[ "$RUNTIME_UID" =~ ^[1-9][0-9]{0,4}$ && "$RUNTIME_GID" =~ ^[1-9][0-9]{0,4}$ ]] || {
  echo "UID/GID de runtime inválidos para o controlador NTP." >&2
  exit 2
}
install -d -m 700 /etc/nivus-compose
printf 'NIVUS_RUNTIME_UID=%s\nNIVUS_RUNTIME_GID=%s\n' "$RUNTIME_UID" "$RUNTIME_GID" > "$TIME_SYNC_ENV"
chmod 600 "$TIME_SYNC_ENV"
install -m 644 "$NEW_RELEASE/deploy/nivus-compose-telemetry.service" "$UNIT_FILE"
install -m 644 "$NEW_RELEASE/deploy/nivus-time-sync.service" "$TIME_SYNC_UNIT_FILE"
systemctl daemon-reload
systemctl enable --now "$TIME_SYNC_SERVICE"
systemctl restart "$TIME_SYNC_SERVICE"
systemctl is-active --quiet "$TIME_SYNC_SERVICE"
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
rm -f -- "$OVERRIDE_FILE"
READY=1
trap - ERR INT TERM
