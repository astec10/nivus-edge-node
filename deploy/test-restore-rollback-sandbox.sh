#!/usr/bin/env bash
set -Eeuo pipefail

APP=/opt/nivus-compose/current
DATA_DIR=/var/lib/nivus-compose/data
DB="$DATA_DIR/nivus.db"
BACKUP_DIR=/var/backups/nivus-compose/older
HTTPS_PORT=28443
SERVER_PID=

fail() { printf 'Erro: %s\n' "$*" >&2; exit 1; }

cleanup() {
  local rc=$?
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  exit "$rc"
}
trap cleanup EXIT

[[ $EUID -eq 0 ]] || fail 'o sandbox precisa rodar como root dentro do container descartável.'

install -d -o root -g root -m 755 "$DATA_DIR" "$BACKUP_DIR" /var/backups/nivus-compose /etc/nivus-compose/secrets
chmod 700 "$BACKUP_DIR"
ln -sfn "$DATA_DIR" /data

cat > "$APP/.env" <<EOF_ENV
NIVUS_DATA_DIR=$DATA_DIR
NIVUS_RUNTIME_UID=1000
NIVUS_RUNTIME_GID=1000
NIVUS_HTTPS_PORT=$HTTPS_PORT
EOF_ENV
chmod 600 "$APP/.env"
cat > "$APP/docker-compose.yml" <<'EOF_COMPOSE'
services:
  api: {}
  worker: {}
  mqtt: {}
  web: {}
EOF_COMPOSE
chmod 644 "$APP/docker-compose.yml"

python3 - "$DB" "$BACKUP_DIR/nivus.sqlite3" <<'PY'
import os
import sqlite3
import sys

def create_database(path, telemetry_rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE
            );
            CREATE TABLE telemetry (
                id INTEGER PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                cpu_percent REAL NOT NULL
            );
            CREATE TABLE system_settings (
                id INTEGER PRIMARY KEY,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL
            );
            INSERT INTO users (id, username) VALUES (1, 'sandbox-admin');
            INSERT INTO system_settings (id, setting_key, setting_value)
                VALUES (1, 'temperature_limit', '75');
        """)
        for index in range(telemetry_rows):
            connection.execute(
                "INSERT INTO telemetry (recorded_at, cpu_percent) VALUES (?, ?)",
                (f"2026-11-17T00:00:{index:02d}Z", float(index + 10)),
            )
        connection.commit()
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    finally:
        connection.close()

create_database(sys.argv[1], 2)
create_database(sys.argv[2], 1)
PY
chown root:root "$BACKUP_DIR/nivus.sqlite3"
chmod 600 "$BACKUP_DIR/nivus.sqlite3"

cat > /usr/local/sbin/systemctl <<'EOF_SYSTEMCTL'
#!/usr/bin/env bash
case "${1:-}" in
  is-active|start|stop|restart|enable|disable|daemon-reload|cat) exit 0 ;;
  *) exit 0 ;;
esac
EOF_SYSTEMCTL
cat > /usr/local/sbin/systemd-detect-virt <<'EOF_VIRT'
#!/usr/bin/env bash
printf 'kvm\n'
EOF_VIRT
cat > /usr/local/sbin/docker <<'EOF_DOCKER'
#!/usr/bin/env bash
if [[ "${1:-}" == inspect ]]; then
  printf 'true\n'
  exit 0
fi
if [[ "${1:-}" == compose ]]; then
  shift
  case "${1:-}" in
    ps)
      shift
      [[ "${1:-}" != -q ]] || shift
      printf 'sandbox-%s\n' "${1:-service}"
      exit 0
      ;;
    exec)
      python3 - <<'PY'
import sqlite3
connection = sqlite3.connect("file:/data/nivus.db?mode=ro", uri=True)
try:
    result = connection.execute("PRAGMA quick_check").fetchall()
    assert result and all(row[0] == "ok" for row in result)
finally:
    connection.close()
PY
      exit $?
      ;;
    stop|start)
      exit 0
      ;;
  esac
fi
printf 'mock docker recebeu chamada inesperada: %s\n' "$*" >&2
exit 2
EOF_DOCKER
chmod 755 /usr/local/sbin/systemctl /usr/local/sbin/systemd-detect-virt /usr/local/sbin/docker

openssl req -x509 -newkey rsa:2048 -nodes -keyout /run/nivus-test.key \
  -out /run/nivus-test.crt -subj '/CN=localhost' -days 1 >/dev/null 2>&1
cat > /run/nivus-test-https.py <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith("/health"):
            self.send_response(200)
            body = b'{"status":"ok"}'
        elif self.path.endswith("/api/telemetry"):
            self.send_response(401)
            body = b'{"detail":"Not authenticated"}'
        else:
            self.send_response(404)
            body = b'not found'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass

server = HTTPServer(("127.0.0.1", 28443), Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain("/run/nivus-test.crt", "/run/nivus-test.key")
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
PY
python3 /run/nivus-test-https.py &
SERVER_PID=$!

ready=0
for _ in $(seq 1 30); do
  if /usr/bin/curl -kfsS --connect-timeout 1 --max-time 2 "https://127.0.0.1:$HTTPS_PORT/health" >/dev/null; then
    ready=1
    break
  fi
  sleep 0.2
done
[[ "$ready" == 1 ]] || fail 'servidor HTTPS simulado não iniciou.'

printf 'VM-ROLLBACK-TEST\nRESTORE\n' | script -qefc \
  "bash '$APP/deploy/test-restore-rollback.sh' --i-understand-this-is-a-disposable-vm '$BACKUP_DIR'" \
  /dev/null

echo 'Sandbox de rollback aprovado: restore falhou de forma induzida, banco anterior foi recuperado e health/401 passaram.'
