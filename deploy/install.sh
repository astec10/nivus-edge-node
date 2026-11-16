#!/usr/bin/env bash
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0" >&2
  exit 1
fi
SOURCE_ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
INSTALL_ROOT=/opt/nivus-compose
RELEASES="$INSTALL_ROOT/releases"
CURRENT="$INSTALL_ROOT/current"
DATA_ROOT=/var/lib/nivus-compose
ETC_ROOT=/etc/nivus-compose
SECRET_DIR="$ETC_ROOT/secrets"
READY=0
STACK_STARTED=0
AGENT_STARTED=0
CURRENT_CREATED=0
TMPFILES_CREATED=0
CTL_LINK_CREATED=0
NIVUS_LINK_CREATED=0
RELEASE_DIR=
rollback_install() {
  rc=$?
  trap - ERR INT TERM
  if [[ $READY -eq 0 ]]; then
    echo "Instalação não concluiu; parando somente a candidata Compose. Dados e segredos são preservados." >&2
    if [[ $AGENT_STARTED -eq 1 ]]; then systemctl disable --now nivus-compose-telemetry.service 2>/dev/null || true; fi
    if [[ $STACK_STARTED -eq 1 && -d "$CURRENT" ]]; then (cd "$CURRENT" && docker compose down) || true; fi
    if [[ $CTL_LINK_CREATED -eq 1 ]]; then rm -f -- /usr/local/bin/nivusctl; fi
    if [[ $NIVUS_LINK_CREATED -eq 1 ]]; then rm -f -- /usr/local/bin/nivus; fi
    if [[ $TMPFILES_CREATED -eq 1 ]]; then
      rm -f -- /etc/tmpfiles.d/nivus-maintenance.conf
      rmdir /run/nivus-maintenance 2>/dev/null || true
    fi
    if [[ $CURRENT_CREATED -eq 1 ]]; then rm -f -- "$CURRENT"; fi
    echo "Seus serviços systemd/Nginx existentes não foram modificados." >&2
  fi
  exit "$rc"
}
trap rollback_install ERR INT TERM
[[ -r /etc/os-release ]] || { echo "Ubuntu não identificado." >&2; exit 2; }
. /etc/os-release
[[ ${ID:-} == ubuntu ]] || { echo "Suporte inicial somente a Ubuntu Server." >&2; exit 2; }
[[ $(uname -m) == x86_64 ]] || { echo "Este pacote inicial foi preparado para x86_64/amd64." >&2; exit 2; }
[[ ! -e /usr/local/bin/nivusctl && ! -L /usr/local/bin/nivusctl ]] || { echo "/usr/local/bin/nivusctl já existe; instalação interrompida sem substituí-lo." >&2; exit 2; }
[[ ! -e /usr/local/bin/nivus && ! -L /usr/local/bin/nivus ]] || { echo "/usr/local/bin/nivus já existe; instalação interrompida sem substituí-lo." >&2; exit 2; }
SYSTEMD_VERSION=$(systemctl --version | awk 'NR==1 {print $2}')
[[ $(printf '%s\n' 247 "$SYSTEMD_VERSION" | sort -V | head -n1) == 247 ]] || { echo "systemd 247 ou superior é necessário para credenciais seguras do serviço de telemetria." >&2; exit 2; }
NEED_APT=0
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then NEED_APT=1; fi
if ! command -v python3 >/dev/null 2>&1 || ! python3 -m venv --help >/dev/null 2>&1; then NEED_APT=1; fi
if ! command -v openssl >/dev/null 2>&1 || ! command -v ss >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then NEED_APT=1; fi
if [[ $NEED_APT -eq 1 ]]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  if ! command -v docker >/dev/null 2>&1; then apt-get install -y docker.io; fi
  if ! docker compose version >/dev/null 2>&1; then apt-get install -y docker-compose-v2; fi
  apt-get install -y python3 python3-venv python3-pip openssl iproute2 curl
fi
command -v docker >/dev/null
docker compose version >/dev/null
systemctl enable --now docker.service
MOSQUITTO_IMAGE=$(awk '$1 == "image:" && $2 ~ /^eclipse-mosquitto:/ {print $2; exit}' "$SOURCE_ROOT/docker-compose.yml")
[[ "$MOSQUITTO_IMAGE" =~ ^eclipse-mosquitto:2@sha256:[a-f0-9]{64}$ ]] || { echo "Imagem Mosquitto fixada por digest não encontrada no Compose." >&2; exit 2; }
if ! docker image inspect "$MOSQUITTO_IMAGE" >/dev/null 2>&1; then docker pull "$MOSQUITTO_IMAGE"; fi
install -d -m 755 "$RELEASES" "$INSTALL_ROOT"
if [[ -e "$CURRENT" ]]; then
  echo "Nivus Compose já existe em $CURRENT. Instalação inicial interrompida sem alterar o stack." >&2
  exit 2
fi
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RELEASE_DIR="$RELEASES/$STAMP"
install -d -m 755 "$RELEASE_DIR"
tar -C "$SOURCE_ROOT" \
  --exclude=.git --exclude=node_modules --exclude=.venv --exclude=venv \
  --exclude=data --exclude=secrets --exclude=certs --exclude=usb-key --exclude=.ssh \
  --exclude=work --exclude=logs --exclude=dist --exclude=build \
  --exclude=__pycache__ --exclude='*.pyc' --exclude='*.pyo' --exclude='*.pyd' \
  --exclude='*.log' --exclude='*.log.*' \
  --exclude='*.db' --exclude='*.db-*' --exclude='*.sqlite' --exclude='*.sqlite-*' --exclude='*.sqlite3' --exclude='*.sqlite3-*' \
  --exclude='*.pem' --exclude='*.key' --exclude='*.p12' --exclude='*.pfx' \
  --exclude='id_rsa*' --exclude='id_ed25519*' --exclude='id_ecdsa*' --exclude='id_dsa*' \
  --exclude=authorized_keys --exclude=known_hosts --exclude=credentials.json --exclude='service-account*.json' \
  --exclude='secrets.*' --exclude='*_secret.*' \
  --exclude='.env*' --exclude='*.env' --exclude='*.env.*' \
  -cf - . | tar -C "$RELEASE_DIR" -xf -
SENSITIVE_FILE=$(find "$RELEASE_DIR" -type f \( \
  -name '.env' -o -name '.env.*' -o -name '*.env' -o -name '*.env.*' \
  -o -name '*.db' -o -name '*.db-*' -o -name '*.sqlite' -o -name '*.sqlite-*' -o -name '*.sqlite3' -o -name '*.sqlite3-*' \
  -o -name '*.pem' -o -name '*.key' -o -name '*.p12' -o -name '*.pfx' \
  -o -name 'id_rsa*' -o -name 'id_ed25519*' -o -name 'id_ecdsa*' -o -name 'id_dsa*' \
  -o -name 'authorized_keys' -o -name 'known_hosts' -o -name 'credentials.json' -o -name 'service-account*.json' \
  -o -name 'secrets.*' -o -name '*_secret.*' \
\) -print -quit)
if [[ -n "$SENSITIVE_FILE" ]]; then
  echo "Arquivo de dados ou credencial inesperado na release; interrompendo sem iniciar serviços." >&2
  exit 2
fi
ln -s "$RELEASE_DIR" "$CURRENT"
CURRENT_CREATED=1
install -d -m 700 "$ETC_ROOT" "$SECRET_DIR"
install -d -m 750 "$DATA_ROOT/data" "$DATA_ROOT/mosquitto"
if ! id -u nivus-telemetry >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/nivus-telemetry --create-home --shell /usr/sbin/nologin nivus-telemetry
fi
chown 1883:1883 "$DATA_ROOT/mosquitto"
chmod 750 "$DATA_ROOT/mosquitto"
RUNTIME_ID=12001
while getent passwd "$RUNTIME_ID" >/dev/null 2>&1 || getent group "$RUNTIME_ID" >/dev/null 2>&1; do RUNTIME_ID=$((RUNTIME_ID + 1)); done
if [[ ! -e "$SECRET_DIR/jwt_secret" ]]; then openssl rand -hex 48 > "$SECRET_DIR/jwt_secret"; fi
for role in api worker agent health; do
  secret="$SECRET_DIR/mqtt_"$role"_password"
  if [[ ! -e "$secret" ]]; then openssl rand -hex 32 > "$secret"; fi
done
chmod 444 "$SECRET_DIR/jwt_secret" "$SECRET_DIR"/mqtt_*_password
if [[ ! -e "$SECRET_DIR/mosquitto_passwords" ]]; then
  docker run --rm --user 0 --network none --mount "type=bind,source=$SECRET_DIR,target=/run/secrets" --entrypoint /bin/sh "$MOSQUITTO_IMAGE" -ec 'umask 077; mosquitto_passwd -b -c /run/secrets/mosquitto_passwords nivus-api "$(cat /run/secrets/mqtt_api_password)"; mosquitto_passwd -b /run/secrets/mosquitto_passwords nivus-worker "$(cat /run/secrets/mqtt_worker_password)"; mosquitto_passwd -b /run/secrets/mosquitto_passwords nivus-agent "$(cat /run/secrets/mqtt_agent_password)"; mosquitto_passwd -b /run/secrets/mosquitto_passwords nivus-health "$(cat /run/secrets/mqtt_health_password)"'
fi
chown 1883:1883 "$SECRET_DIR/mosquitto_passwords"
chmod 600 "$SECRET_DIR/mosquitto_passwords"
install -o 1883 -g 1883 -m 600 "$CURRENT/deploy/mosquitto.acl" "$SECRET_DIR/mosquitto_acl"
if [[ ! -s "$SECRET_DIR/tls.crt" || ! -s "$SECRET_DIR/tls.key" ]]; then
  HOST_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([^ ]*\).*/\1/p' | head -n1 || true)
  SAN=DNS:nivus-edge.local
  if [[ -n "$HOST_IP" ]]; then SAN="DNS:nivus-edge.local,IP:$HOST_IP"; fi
  openssl req -x509 -nodes -newkey rsa:3072 -sha256 -days 825 -keyout "$SECRET_DIR/tls.key" -out "$SECRET_DIR/tls.crt" -subj "/CN=nivus-edge.local" -addext "subjectAltName=$SAN"
  chmod 444 "$SECRET_DIR/tls.crt" "$SECRET_DIR/tls.key"
fi
if [[ ! -e "$CURRENT/.env" ]]; then
  HTTPS_PORT=8443
  while ss -H -ltn "sport = :$HTTPS_PORT" | grep -q .; do HTTPS_PORT=$((HTTPS_PORT + 1)); done
  printf '%s\n' \
    'NIVUS_BIND_ADDRESS=0.0.0.0' \
    "NIVUS_HTTPS_PORT=$HTTPS_PORT" \
    'NIVUS_NODE_NAME=nivus-edge-node' \
    'NIVUS_CORS_ORIGINS=' \
    "NIVUS_DATA_DIR=$DATA_ROOT/data" \
    "NIVUS_MOSQUITTO_DATA_DIR=$DATA_ROOT/mosquitto" \
    "NIVUS_SECRET_DIR=$SECRET_DIR" \
    'NIVUS_MAINTENANCE_STATE_DIR=/run/nivus-maintenance' \
    "NIVUS_RUNTIME_UID=$RUNTIME_ID" \
    "NIVUS_RUNTIME_GID=$RUNTIME_ID" \
    'NIVUS_API_MEMORY_LIMIT=256m' \
    'NIVUS_WORKER_MEMORY_LIMIT=128m' \
    'NIVUS_MQTT_MEMORY_LIMIT=64m' \
    'NIVUS_WEB_MEMORY_LIMIT=64m' \
    'NIVUS_API_CPUS=1.00' \
    'NIVUS_WORKER_CPUS=0.50' \
    'NIVUS_MQTT_CPUS=0.25' \
    'NIVUS_WEB_CPUS=0.25' > "$CURRENT/.env"
  chmod 600 "$CURRENT/.env"
fi
RUNTIME_UID=$(sed -n 's/^NIVUS_RUNTIME_UID=//p' "$CURRENT/.env")
RUNTIME_GID=$(sed -n 's/^NIVUS_RUNTIME_GID=//p' "$CURRENT/.env")
[[ "$RUNTIME_UID" =~ ^[0-9]+$ && "$RUNTIME_GID" =~ ^[0-9]+$ ]] || { echo "IDs de runtime inválidos no .env." >&2; exit 2; }
chown "$RUNTIME_UID:$RUNTIME_GID" "$DATA_ROOT/data"
chmod 750 "$DATA_ROOT/data"
if [[ -e /etc/tmpfiles.d/nivus-maintenance.conf || -e /run/nivus-maintenance ]]; then
  echo "Caminho de estado de manutenção já existe; instalação interrompida sem substituí-lo." >&2
  exit 2
fi
TELEMETRY_GID=$(id -g nivus-telemetry)
printf 'd /run/nivus-maintenance 2750 %s %s - -\n' "$RUNTIME_UID" "$TELEMETRY_GID" > /etc/tmpfiles.d/nivus-maintenance.conf
chmod 644 /etc/tmpfiles.d/nivus-maintenance.conf
TMPFILES_CREATED=1
systemd-tmpfiles --create /etc/tmpfiles.d/nivus-maintenance.conf
python3 -m venv "$INSTALL_ROOT/venv"
"$INSTALL_ROOT/venv/bin/python" -m pip install --no-cache-dir -r "$CURRENT/telemetry/requirements.txt"
install -m 644 "$CURRENT/deploy/nivus-compose-telemetry.service" /etc/systemd/system/nivus-compose-telemetry.service
chmod 0755 "$CURRENT/deploy/resolve-mqtt-endpoint.sh"
cat > "$ETC_ROOT/telemetry.env" <<EOF
NIVUS_MQTT_PORT=1883
NIVUS_MQTT_USERNAME=nivus-agent
NIVUS_TELEMETRY_TOPIC=nivus/edge/telemetry
NIVUS_NODE_NAME=nivus-edge-node
NIVUS_DISK_PATH=/
EOF
chmod 644 "$ETC_ROOT/telemetry.env"
chmod 0755 "$CURRENT/deploy/nivusctl"
(cd "$CURRENT" && docker compose config --quiet)
STACK_STARTED=1
(cd "$CURRENT" && docker compose up -d --build)
HTTPS_PORT=$(sed -n 's/^NIVUS_HTTPS_PORT=//p' "$CURRENT/.env")
for attempt in {1..40}; do
  if curl -kfsS --connect-timeout 2 --max-time 4 "https://127.0.0.1:$HTTPS_PORT/health" >/dev/null; then break; fi
  sleep 2
done
curl -kfsS --connect-timeout 2 --max-time 4 "https://127.0.0.1:$HTTPS_PORT/health"
AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 4 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$HTTPS_PORT/api/telemetry")
[[ "$AUTH_STATUS" == 401 ]]
USER_COUNT=$(cd "$CURRENT" && docker compose exec -T api python -c 'from database import get_db_connection; c=get_db_connection(); print(c.execute("SELECT COUNT(*) FROM users").fetchone()[0]); c.close()')
if [[ "$USER_COUNT" == 0 ]]; then
  echo "Crie a primeira conta administradora. Nome: 1–32 caracteres (letras, números, ponto, hífen ou sublinhado). Senha temporária: 8–256 caracteres, com uma letra e um número; será solicitada duas vezes sem eco e deverá ser trocada no primeiro acesso."
  (cd "$CURRENT" && docker compose run --rm -it api python create_admin.py)
fi
systemctl daemon-reload
AGENT_STARTED=1
ln -s "$CURRENT/deploy/nivusctl" /usr/local/bin/nivus
NIVUS_LINK_CREATED=1
ln -s "$CURRENT/deploy/nivusctl" /usr/local/bin/nivusctl
CTL_LINK_CREATED=1
systemctl enable --now nivus-compose-telemetry.service
READY=1
trap - ERR INT TERM
printf '\nInstalação paralela concluída. O stack systemd/Nginx preexistente não foi alterado.\n'
printf 'Painel HTTPS: https://<IP-do-host>:%s/\n' "$HTTPS_PORT"
printf 'Broker MQTT: rede Docker privada, sem porta publicada no host.\n'
printf 'Dados persistentes: %s\n' "$DATA_ROOT"
printf 'Para parar apenas a candidata: sudo bash %s/deploy/stop-compose.sh\n' "$CURRENT"
