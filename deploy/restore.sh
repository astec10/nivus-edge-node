#!/usr/bin/env bash
set -Eeuo pipefail

APP=/opt/nivus-compose/current
DATA_DIR=/var/lib/nivus-compose/data
DB="$DATA_DIR/nivus.db"
BACKUP_ROOT=/var/backups/nivus-compose
TELEMETRY_UNIT=nivus-compose-telemetry.service
CHECK_ONLY=0

usage() {
  cat <<'EOF'
Uso:
  sudo bash deploy/restore.sh --check /var/backups/nivus-compose/<data-hora>
  sudo bash deploy/restore.sh /var/backups/nivus-compose/<data-hora>

--check valida o SQLite e os pré-requisitos sem parar serviços nem alterar dados.
Uma restauração exige digitar RESTORE no terminal e cria um backup prévio.
Somente a base SQLite é restaurada; .env e segredos atuais são preservados.
O procedimento só aceita backups locais sob /var/backups/nivus-compose.
EOF
}

fail() { printf 'Erro: %s\n' "$*" >&2; exit 2; }

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0" >&2
  exit 1
fi
if [[ "${1:-}" == "--check" ]]; then CHECK_ONLY=1; shift; fi
[[ $# -eq 1 ]] || { usage >&2; exit 2; }

[[ -d "$APP" && -r "$APP/docker-compose.yml" && -r "$APP/.env" ]] || fail "instalação Compose não encontrada em $APP"
[[ -s "$DB" ]] || fail "base atual não encontrada em $DB"

BACKUP_DIR=$(realpath -e -- "$1") || fail "pasta do backup não encontrada"
case "$BACKUP_DIR" in
  "$BACKUP_ROOT"/*) ;;
  *) fail "o backup precisa estar dentro de $BACKUP_ROOT" ;;
esac
[[ -d "$BACKUP_DIR" && ! -L "$1" ]] || fail "pasta de backup inválida"
[[ $(stat -c '%u' "$BACKUP_DIR") == 0 ]] || fail "a pasta do backup precisa pertencer a root"
BACKUP_DIR_MODE=$(stat -c '%a' "$BACKUP_DIR")
[[ "$BACKUP_DIR_MODE" =~ ^[0-7]{3,4}$ ]] || fail "permissões da pasta do backup inválidas"
(( (8#$BACKUP_DIR_MODE & 0022) == 0 )) || fail "a pasta do backup não pode ser gravável por grupo/outros"
BACKUP_DB="$BACKUP_DIR/nivus.sqlite3"
[[ -f "$BACKUP_DB" && ! -L "$BACKUP_DB" && -s "$BACKUP_DB" ]] || fail "nivus.sqlite3 ausente ou inválido no backup"
[[ $(stat -c '%u' "$BACKUP_DB") == 0 ]] || fail "o banco de backup precisa pertencer a root"
BACKUP_DB_MODE=$(stat -c '%a' "$BACKUP_DB")
[[ "$BACKUP_DB_MODE" =~ ^[0-7]{3,4}$ ]] || fail "permissões do banco de backup inválidas"
(( (8#$BACKUP_DB_MODE & 0077) == 0 )) || fail "o banco de backup não pode ser legível por grupo/outros"
[[ "$BACKUP_DB" != "$(realpath -e -- "$DB")" ]] || fail "a origem não pode ser a base ativa"

check_sqlite() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sqlite3, sys
uri = Path(sys.argv[1]).resolve().as_uri() + "?mode=ro"
connection = sqlite3.connect(uri, uri=True, timeout=10)
try:
    results = connection.execute("PRAGMA quick_check").fetchall()
    if not results or any(row[0] != "ok" for row in results):
        print("SQLite quick_check falhou: " + "; ".join(str(row[0]) for row in results), file=sys.stderr)
        raise SystemExit(1)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {"users", "telemetry"} - tables
    if missing:
        print("Tabelas Nivus ausentes: " + ", ".join(sorted(missing)), file=sys.stderr)
        raise SystemExit(1)
finally:
    connection.close()
PY
}

check_sqlite "$BACKUP_DB" || fail "o banco do backup não passou PRAGMA quick_check"

env_value() {
  awk -F= -v key="$1" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$APP/.env"
}

CONFIG_DATA_DIR=$(env_value NIVUS_DATA_DIR)
RUNTIME_UID=$(env_value NIVUS_RUNTIME_UID)
RUNTIME_GID=$(env_value NIVUS_RUNTIME_GID)
HTTPS_PORT=$(env_value NIVUS_HTTPS_PORT)
[[ "$CONFIG_DATA_DIR" == "$DATA_DIR" ]] || fail "NIVUS_DATA_DIR não corresponde à base administrada por este script"
[[ "$RUNTIME_UID" =~ ^[0-9]+$ && "$RUNTIME_GID" =~ ^[0-9]+$ ]] || fail "UID/GID de runtime ausente ou inválido no .env"
[[ "$HTTPS_PORT" =~ ^[0-9]+$ ]] && ((HTTPS_PORT > 0 && HTTPS_PORT < 65536)) || fail "NIVUS_HTTPS_PORT ausente ou inválida no .env"

if (( CHECK_ONLY )); then
  check_sqlite "$DB" || fail "a base ativa não passou PRAGMA quick_check"
  printf 'Backup válido: %s\n' "$BACKUP_DIR"
  echo "SQLite quick_check: ok. Nenhum serviço ou dado foi alterado."
  exit 0
fi

systemctl is-active --quiet "$TELEMETRY_UNIT" || fail "$TELEMETRY_UNIT precisa estar ativo antes da restauração"
for service in api worker mqtt web; do
  container_id=$(cd "$APP" && docker compose ps -q "$service")
  [[ -n "$container_id" ]] || fail "container Compose '$service' não está em execução"
  [[ $(docker inspect -f '{{.State.Running}}' "$container_id") == true ]] || fail "container Compose '$service' não está em execução"
done

echo "A restauração substituirá somente $DB pelo banco em:"
printf '  %s\n' "$BACKUP_DIR"
echo "O .env, as chaves JWT/MQTT e os certificados atuais serão preservados."
read -r -p "Digite RESTORE para continuar: " confirmation </dev/tty
[[ "$confirmation" == RESTORE ]] || { echo "Cancelado; nenhuma alteração feita."; exit 0; }

PRE_RESTORE_DIR=
SERVICES_STOPPED=0
DB_REPLACED=0
RESTORE_COMPLETE=0
TEMP_DB=

start_writers() {
  (cd "$APP" && docker compose start api worker)
  systemctl start "$TELEMETRY_UNIT"
}

quarantine_sidecars() {
  local destination="$1"
  install -d -m 700 "$destination"
  for sidecar in "$DB-wal" "$DB-shm"; do
    if [[ -e "$sidecar" ]]; then
      mv -- "$sidecar" "$destination/$(basename "$sidecar")"
    fi
  done
}

rollback_on_exit() {
  local original_status=$?
  trap - EXIT
  if (( ! SERVICES_STOPPED || RESTORE_COMPLETE )); then exit "$original_status"; fi
  set +e
  local rollback_status=0
  local stop_status=0
  systemctl stop "$TELEMETRY_UNIT" >/dev/null 2>&1 || stop_status=$?
  (cd "$APP" && docker compose stop api worker) >/dev/null 2>&1 || stop_status=$?
  if (( DB_REPLACED )); then
    if (( stop_status != 0 )); then
      rollback_status=1
    elif [[ -n "$PRE_RESTORE_DIR" && -s "$PRE_RESTORE_DIR/nivus.sqlite3" ]]; then
      quarantine_sidecars "$PRE_RESTORE_DIR/sidecars-failed-restore" || rollback_status=$?
      if (( rollback_status == 0 )); then
        TEMP_DB=$(mktemp "$DATA_DIR/.nivus-rollback.XXXXXX") || rollback_status=$?
        if (( rollback_status == 0 )); then
          install -o "$RUNTIME_UID" -g "$RUNTIME_GID" -m 640 "$PRE_RESTORE_DIR/nivus.sqlite3" "$TEMP_DB" || rollback_status=$?
          if (( rollback_status == 0 )); then mv -f -- "$TEMP_DB" "$DB" || rollback_status=$?; fi
          if (( rollback_status == 0 )); then check_sqlite "$DB" || rollback_status=$?; fi
        fi
      fi
    else
      rollback_status=1
    fi
  fi
  if (( rollback_status == 0 )); then start_writers || rollback_status=$?; fi
  if [[ -n "$TEMP_DB" && -e "$TEMP_DB" ]]; then rm -f -- "$TEMP_DB"; fi
  if (( rollback_status != 0 )); then
    echo "ERRO: o rollback automático não conseguiu restaurar todos os serviços." >&2
    [[ -n "$PRE_RESTORE_DIR" ]] && printf 'Backup anterior preservado em: %s\n' "$PRE_RESTORE_DIR" >&2
  else
    echo "Restauração falhou; base anterior e serviços foram recuperados." >&2
    [[ -n "$PRE_RESTORE_DIR" ]] && printf 'Backup anterior: %s\n' "$PRE_RESTORE_DIR" >&2
  fi
  exit "$original_status"
}
trap rollback_on_exit EXIT

SERVICES_STOPPED=1
systemctl stop "$TELEMETRY_UNIT"
(cd "$APP" && docker compose stop api worker)

BACKUP_OUTPUT=$(bash "$APP/deploy/backup.sh")
printf '%s\n' "$BACKUP_OUTPUT"
PRE_RESTORE_DIR=$(sed -n 's/^Backup SQLite consistente e configuração salvos em //p' <<<"$BACKUP_OUTPUT")
[[ -d "$PRE_RESTORE_DIR" && -s "$PRE_RESTORE_DIR/nivus.sqlite3" ]] || fail "backup prévio não foi criado corretamente"

python3 - "$DB" <<'PY'
import sqlite3, sys
connection = sqlite3.connect(sys.argv[1], timeout=30)
try:
    result = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if result and result[0] != 0:
        raise SystemExit(f"Checkpoint SQLite ocupado: {result}")
finally:
    connection.close()
PY
quarantine_sidecars "$PRE_RESTORE_DIR/sidecars-before-restore"

TEMP_DB=$(mktemp "$DATA_DIR/.nivus-restore.XXXXXX")
install -o "$RUNTIME_UID" -g "$RUNTIME_GID" -m 640 "$BACKUP_DB" "$TEMP_DB"
check_sqlite "$TEMP_DB" || fail "cópia temporária do backup falhou na validação"
DB_REPLACED=1
mv -f -- "$TEMP_DB" "$DB"
TEMP_DB=

(cd "$APP" && docker compose start api worker)
systemctl start "$TELEMETRY_UNIT"

health_ok=0
for attempt in {1..45}; do
  if curl -kfsS --connect-timeout 2 --max-time 4 "https://127.0.0.1:$HTTPS_PORT/health" >/dev/null; then
    health_ok=1
    break
  fi
  sleep 1
done
(( health_ok == 1 )) || fail "health HTTPS não respondeu depois da restauração"
AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 4 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$HTTPS_PORT/api/telemetry")
[[ "$AUTH_STATUS" == 401 ]] || fail "API não preservou a resposta 401 sem token"
(cd "$APP" && docker compose exec -T api python -c 'import sqlite3; c=sqlite3.connect("file:/data/nivus.db?mode=ro", uri=True); r=c.execute("PRAGMA quick_check").fetchall(); assert r and all(x[0] == "ok" for x in r); c.close()')
systemctl is-active --quiet "$TELEMETRY_UNIT"

RESTORE_COMPLETE=1
trap - ERR INT TERM
echo "Restauração concluída; health HTTPS, 401, SQLite e coletor foram verificados."
printf 'Banco restaurado de: %s\n' "$BACKUP_DIR"
printf 'Backup automático pré-restauração: %s\n' "$PRE_RESTORE_DIR"
