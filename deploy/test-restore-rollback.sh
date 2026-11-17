#!/usr/bin/env bash
set -Eeuo pipefail

APP=/opt/nivus-compose/current
DB=/var/lib/nivus-compose/data/nivus.db
BACKUP_ROOT=/var/backups/nivus-compose
TELEMETRY_UNIT=nivus-compose-telemetry.service
TEST_DIR=
GUARD_DIR=

usage() {
  cat <<'EOF'
Uso:
  sudo bash deploy/test-restore-rollback.sh --i-understand-this-is-a-disposable-vm BACKUP_DIR

Este teste induz falha de health após a troca SQLite e espera o rollback automático.
Use somente numa VM descartável; o processo leva cerca de 45 segundos e exige
digitar VM-ROLLBACK-TEST e depois RESTORE no terminal. Mantém um backup de segurança.
EOF
}

fail() { printf 'Erro: %s\n' "$*" >&2; exit 2; }

cleanup() {
  local rc=$?
  trap - EXIT
  if [[ -n "$TEST_DIR" && "$TEST_DIR" == /run/nivus-restore-rollback.* && -d "$TEST_DIR" && ! -L "$TEST_DIR" ]]; then
    if [[ -n "$GUARD_DIR" && -d "$GUARD_DIR" && -f "$TEST_DIR/restore.log" ]]; then
      install -o root -g root -m 600 "$TEST_DIR/restore.log" "$GUARD_DIR/rollback-test.log" || true
    fi
    rm -rf -- "$TEST_DIR"
  fi
  exit "$rc"
}
trap cleanup EXIT

if [[ $# -eq 1 && ( "$1" == '-h' || "$1" == '--help' ) ]]; then usage; exit 0; fi
if [[ $EUID -ne 0 ]]; then fail 'execute com sudo.'; fi
if [[ $# -ne 2 || "$1" != '--i-understand-this-is-a-disposable-vm' ]]; then
  usage >&2
  exit 2
fi
[[ -d "$APP" && -r "$APP/deploy/restore.sh" && -r "$APP/deploy/backup.sh" ]] || fail "instalação não encontrada em $APP"
[[ -s "$DB" ]] || fail "base ativa não encontrada em $DB"
command -v systemd-detect-virt >/dev/null 2>&1 || fail 'systemd-detect-virt não está disponível.'
VIRT=$(systemd-detect-virt --vm 2>/dev/null || true)
[[ -n "$VIRT" && "$VIRT" != none ]] || fail 'esta rotina só pode rodar dentro de uma máquina virtual.'

BACKUP_DIR=$(realpath -e -- "$2") || fail 'pasta do backup não encontrada.'
case "$BACKUP_DIR" in
  "$BACKUP_ROOT"/*) ;;
  *) fail "o backup precisa estar dentro de $BACKUP_ROOT" ;;
esac
[[ -d "$BACKUP_DIR" && ! -L "$2" ]] || fail 'pasta do backup inválida.'
bash "$APP/deploy/restore.sh" --check "$BACKUP_DIR" >/dev/null || fail 'backup ou pré-requisitos não passaram em --check.'

read -r -p "VM detectada ($VIRT). Este teste restaura um backup mais antigo, força falha de health por ~45s e verifica a recuperação do banco atual. Digite VM-ROLLBACK-TEST: " confirmation </dev/tty
[[ "$confirmation" == VM-ROLLBACK-TEST ]] || { echo 'Cancelado; nada foi alterado.'; exit 0; }

GUARD_OUTPUT=$(bash "$APP/deploy/backup.sh")
printf '%s\n' "$GUARD_OUTPUT"
GUARD_DIR=$(sed -n 's/^Backup SQLite consistente e configuração salvos em //p' <<<"$GUARD_OUTPUT")
[[ -d "$GUARD_DIR" && -s "$GUARD_DIR/nivus.sqlite3" ]] || fail 'backup de segurança pré-teste não foi criado.'

sqlite_telemetry_count() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sqlite3, sys
uri = Path(sys.argv[1]).resolve().as_uri() + "?mode=ro"
connection = sqlite3.connect(uri, uri=True, timeout=10)
try:
    print(connection.execute('SELECT COUNT(*) FROM telemetry').fetchone()[0])
finally:
    connection.close()
PY
}

SOURCE_COUNT=$(sqlite_telemetry_count "$BACKUP_DIR/nivus.sqlite3")
GUARD_COUNT=$(sqlite_telemetry_count "$GUARD_DIR/nivus.sqlite3")
[[ "$SOURCE_COUNT" =~ ^[0-9]+$ && "$GUARD_COUNT" =~ ^[0-9]+$ ]] || fail 'não foi possível contar linhas da telemetria.'
(( GUARD_COUNT > SOURCE_COUNT )) || fail 'selecione um backup mais antigo: a telemetria atual precisa ter mais linhas para confirmar o rollback.'

TEST_DIR=$(mktemp -d /run/nivus-restore-rollback.XXXXXX)
install -d -m 700 "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/curl" <<'EOF_CURL'
#!/usr/bin/env bash
for argument in "$@"; do
  case "$argument" in
    */health)
      if [[ "${NIVUS_RESTORE_PHASE:-restore}" != rollback ]]; then
        echo 'Falha de health simulada apenas para validar o rollback em VM.' >&2
        exit 22
      fi
      ;;
  esac
done
exec /usr/bin/curl "$@"
EOF_CURL
chmod 700 "$TEST_DIR/bin/curl"

echo 'O teste agora vai trocar a base, provocar falha de health e validar o rollback automático.'
echo 'No próximo prompt, digite RESTORE para confirmar esta etapa.'
set +e
PATH="$TEST_DIR/bin:$PATH" bash "$APP/deploy/restore.sh" "$BACKUP_DIR" 2>&1 | tee "$TEST_DIR/restore.log"
RESTORE_STATUS=${PIPESTATUS[0]}
set -e
(( RESTORE_STATUS != 0 )) || fail 'o restore deveria falhar no health simulado, mas terminou com sucesso.'
grep -Fq 'Restauração falhou; base anterior e serviços foram recuperados.' "$TEST_DIR/restore.log" || fail 'a mensagem de rollback automático não foi confirmada.'

systemctl is-active --quiet "$TELEMETRY_UNIT" || fail 'coletor não voltou a ficar ativo.'
for service in api worker mqtt web; do
  container_id=$(cd "$APP" && docker compose ps -q "$service")
  [[ -n "$container_id" ]] || fail "container '$service' não foi encontrado após rollback."
  [[ $(docker inspect -f '{{.State.Running}}' "$container_id") == true ]] || fail "container '$service' não voltou após rollback."
done

HTTPS_PORT=$(awk -F= '$1 == "NIVUS_HTTPS_PORT" {print $2; exit}' "$APP/.env")
[[ "$HTTPS_PORT" =~ ^[0-9]+$ ]] || fail 'NIVUS_HTTPS_PORT inválida.'
HEALTH_CODE=$(/usr/bin/curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$HTTPS_PORT/health")
[[ "$HEALTH_CODE" == 200 ]] || fail "health HTTPS retornou HTTP $HEALTH_CODE após rollback."
AUTH_CODE=$(/usr/bin/curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$HTTPS_PORT/api/telemetry")
[[ "$AUTH_CODE" == 401 ]] || fail "telemetria sem token retornou HTTP $AUTH_CODE após rollback."

python3 - "$GUARD_DIR/nivus.sqlite3" "$DB" <<'PY'
from pathlib import Path
from collections import Counter
import hashlib, json, sqlite3, sys

def snapshot(path):
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        result = connection.execute("PRAGMA quick_check").fetchall()
        if not result or any(row[0] != "ok" for row in result):
            raise SystemExit(f"quick_check falhou em {path}")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"users", "telemetry"}.issubset(tables):
            raise SystemExit(f"tabelas Nivus ausentes em {path}")
        schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'index', 'trigger', 'view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        fingerprints = {}
        for table in tables:
            if table == "sqlite_sequence":
                continue
            escaped = table.replace('"', '""')
            rows = connection.execute(f'SELECT * FROM "{escaped}"').fetchall()
            encoded_rows = []
            for row in rows:
                normalized = [{"blob": value.hex()} if isinstance(value, bytes) else value for value in row]
                encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str).encode()
                encoded_rows.append(hashlib.sha256(encoded).hexdigest())
            fingerprints[table] = Counter(encoded_rows)
        return tables, schema, fingerprints
    finally:
        connection.close()

before_tables, before_schema, before_rows = snapshot(sys.argv[1])
after_tables, after_schema, after_rows = snapshot(sys.argv[2])
if before_tables != after_tables:
    raise SystemExit("rollback alterou a lista de tabelas SQLite")
if before_schema != after_schema:
    raise SystemExit("rollback alterou o esquema SQLite")
for table in before_rows:
    if table == "telemetry":
        if before_rows[table] - after_rows[table]:
            raise SystemExit("rollback perdeu linhas da telemetria anterior ao teste")
    elif before_rows[table] != after_rows[table]:
        raise SystemExit(f"rollback alterou dados da tabela {table}")
print("Rollback de dados confirmado: conteúdo anterior preservado e telemetria nova mantida.")
PY

echo 'Rollback automático validado; serviços, health HTTPS, 401 e SQLite estão íntegros.'
printf 'Backup de segurança: %s\n' "$GUARD_DIR"

