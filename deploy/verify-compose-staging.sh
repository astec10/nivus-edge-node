#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${NIVUS_ALLOW_STAGING_SMOKE:-}" != "1" ]]; then
  echo "Defina NIVUS_ALLOW_STAGING_SMOKE=1 para confirmar execução isolada." >&2
  exit 2
fi
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
APP_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd -P)
cd -- "$APP_DIR"
sed -i 's/\r$//' .env

require_env() {
  grep -Fx "$1=$2" .env >/dev/null || {
    echo "Configuração de staging recusada: $1 não corresponde." >&2
    exit 2
  }
}
require_env NIVUS_BIND_ADDRESS 127.0.0.1
require_env NIVUS_NODE_NAME compose-config-check
require_env NIVUS_HTTPS_PORT 28443
require_env NIVUS_DATA_DIR "$APP_DIR/data"
require_env NIVUS_MOSQUITTO_DATA_DIR "$APP_DIR/mosquitto"
require_env NIVUS_SECRET_DIR "$APP_DIR/secrets"

for command in docker openssl curl ss; do
  command -v "$command" >/dev/null 2>&1 || { echo "Comando ausente: $command" >&2; exit 2; }
done
if ss -H -ltn 'sport = :28443' | grep -q .; then
  echo "Porta de staging ocupada." >&2
  exit 2
fi

PROJECT="nivus-smoke-$(date -u +%Y%m%d-%H%M%S)-$$"
DATA_DIR="$APP_DIR/data"
MOSQ_DATA_DIR="$APP_DIR/mosquitto"
SECRETS_DIR="$APP_DIR/secrets"
RUNTIME_UID=$(sed -n 's/^NIVUS_RUNTIME_UID=//p' .env)
RUNTIME_GID=$(sed -n 's/^NIVUS_RUNTIME_GID=//p' .env)
HOST_UID=$(id -u)
HOST_GID=$(id -g)

MOSQUITTO_IMAGE=$(awk '$1 == "image:" && $2 ~ /^eclipse-mosquitto:/ {print $2; exit}' docker-compose.yml)
[[ "$MOSQUITTO_IMAGE" =~ ^eclipse-mosquitto:2@sha256:[a-f0-9]{64}$ ]] || { echo "Imagem Mosquitto fixada por digest não encontrada no Compose." >&2; exit 2; }
docker image inspect nivus-edge-api:local nivus-edge-web:local >/dev/null
if ! docker image inspect "$MOSQUITTO_IMAGE" >/dev/null 2>&1; then docker pull "$MOSQUITTO_IMAGE"; fi
install -d -m 700 "$SECRETS_DIR"
install -d -m 750 "$DATA_DIR" "$MOSQ_DATA_DIR"
rm -f -- "$SECRETS_DIR/jwt_secret" "$SECRETS_DIR"/mqtt_*_password \
  "$SECRETS_DIR/mosquitto_passwords" "$SECRETS_DIR/mosquitto_acl" \
  "$SECRETS_DIR/tls.key" "$SECRETS_DIR/tls.crt"
cp -- deploy/mosquitto.acl "$SECRETS_DIR/mosquitto_acl"
openssl rand -hex 48 > "$SECRETS_DIR/jwt_secret"
for role in api worker agent health; do openssl rand -hex 32 > "$SECRETS_DIR/mqtt_${role}_password"; done
chmod 444 "$SECRETS_DIR/jwt_secret" "$SECRETS_DIR"/mqtt_*_password
docker run --rm --user 0 --network none \
  --mount "type=bind,source=$SECRETS_DIR,target=/run/secrets" \
  --entrypoint /bin/sh "$MOSQUITTO_IMAGE" -ec \
  'umask 077; mosquitto_passwd -b -c /run/secrets/mosquitto_passwords nivus-api "$(cat /run/secrets/mqtt_api_password)"; mosquitto_passwd -b /run/secrets/mosquitto_passwords nivus-worker "$(cat /run/secrets/mqtt_worker_password)"; mosquitto_passwd -b /run/secrets/mosquitto_passwords nivus-agent "$(cat /run/secrets/mqtt_agent_password)"; mosquitto_passwd -b /run/secrets/mosquitto_passwords nivus-health "$(cat /run/secrets/mqtt_health_password)"; chown 1883:1883 /run/secrets/mosquitto_passwords /run/secrets/mosquitto_acl; chmod 0600 /run/secrets/mosquitto_passwords /run/secrets/mosquitto_acl'
openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 1 \
  -keyout "$SECRETS_DIR/tls.key" -out "$SECRETS_DIR/tls.crt" \
  -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'
chmod 444 "$SECRETS_DIR/tls.key" "$SECRETS_DIR/tls.crt"

docker run --rm --user 0 --network none \
  --mount "type=bind,source=$DATA_DIR,target=/data" \
  --mount "type=bind,source=$MOSQ_DATA_DIR,target=/mosq" \
  --env "RUNTIME_UID=$RUNTIME_UID" --env "RUNTIME_GID=$RUNTIME_GID" \
  --entrypoint /bin/sh nivus-edge-api:local -ec \
  'chown -R "$RUNTIME_UID:$RUNTIME_GID" /data; chmod 750 /data; chown -R 1883:1883 /mosq; chmod 750 /mosq'

cleanup() {
  local rc=$?
  trap - EXIT
  if (( rc != 0 )); then docker compose -p "$PROJECT" logs --no-color --tail=30 api worker mqtt web 2>&1 || true; fi
  docker compose -p "$PROJECT" down --remove-orphans >/dev/null 2>&1 || true
  docker run --rm --user 0 --network none \
    --mount "type=bind,source=$DATA_DIR,target=/data" \
    --mount "type=bind,source=$MOSQ_DATA_DIR,target=/mosq" \
    --env "HOST_UID=$HOST_UID" --env "HOST_GID=$HOST_GID" \
    --entrypoint /bin/sh nivus-edge-api:local -ec \
    'chown -R "$HOST_UID:$HOST_GID" /data /mosq; chmod 750 /data /mosq' >/dev/null 2>&1 || true
  if (( rc == 0 )); then echo "SMOKE_CLEANUP=containers-stopped; staging preserved under $APP_DIR"; else echo "SMOKE_CLEANUP=containers-stopped; staging kept for diagnosis" >&2; fi
  exit "$rc"
}
trap cleanup EXIT

docker compose -p "$PROJECT" config --quiet
docker compose -p "$PROJECT" up -d --no-build --pull missing
API_ID=$(docker compose -p "$PROJECT" ps -q api)
MQTT_ID=$(docker compose -p "$PROJECT" ps -q mqtt)
WORKER_ID=$(docker compose -p "$PROJECT" ps -q worker)
WEB_ID=$(docker compose -p "$PROJECT" ps -q web)
for attempt in $(seq 1 45); do
  API_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "$API_ID" 2>/dev/null || true)
  MQTT_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "$MQTT_ID" 2>/dev/null || true)
  if [[ "$API_HEALTH" == healthy && "$MQTT_HEALTH" == healthy ]]; then break; fi
  sleep 2
done
[[ "$API_HEALTH" == healthy ]]
[[ "$MQTT_HEALTH" == healthy ]]
[[ $(docker inspect -f '{{.State.Status}}' "$WORKER_ID") == running ]]
[[ $(docker inspect -f '{{.State.Status}}' "$WEB_ID") == running ]]

echo '===CANDIDATE_HEALTH==='
docker compose -p "$PROJECT" ps web
docker compose -p "$PROJECT" port web 8443 || true
docker inspect -f 'BINDINGS={{json .HostConfig.PortBindings}} NETWORK={{json .NetworkSettings.Ports}} MODE={{.HostConfig.NetworkMode}}' "$WEB_ID"
ss -ltnp 'sport = :28443' || true
docker compose -p "$PROJECT" exec -T web wget -q --no-check-certificate -O - https://127.0.0.1:8443/health || true
for attempt in $(seq 1 15); do
  if curl -kfsS --connect-timeout 2 --max-time 5 https://127.0.0.1:28443/health; then break; fi
  sleep 1
done
curl -kfsS --connect-timeout 2 --max-time 5 https://127.0.0.1:28443/health
echo
INDEX_HTML=$(curl -kfsS --connect-timeout 2 --max-time 5 https://127.0.0.1:28443/)
grep -qi 'nivus-dashboard' <<< "$INDEX_HTML"
JS_ASSET=$(sed -n 's/.*src="\([^"]*\.js\)".*/\1/p' <<< "$INDEX_HTML" | head -n 1)
[[ -n "$JS_ASSET" ]]
curl -kfsS --connect-timeout 2 --max-time 5 "https://127.0.0.1:28443$JS_ASSET" -o /dev/null
echo "frontend_index_and_asset=ok ($JS_ASSET)"
AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' https://127.0.0.1:28443/api/telemetry)
[[ "$AUTH_STATUS" == 401 ]]
echo "unauthenticated_telemetry_http=$AUTH_STATUS"

echo '===MQTT_TO_SQLITE==='
TIMESTAMP=$(date +%s)
MQTT_PASSWORD=$(cat "$SECRETS_DIR/mqtt_agent_password")
PAYLOAD=$(printf '{"node":"%s","timestamp":%s,"cpu_percent":5.2,"memory_percent":42.0,"disk_percent":20.0,"temperature":57.0,"temperature_source":"coretemp: Package id 0","motherboard_temperature":null,"gpu_temperature":47.0,"gpu_temperature_source":"amdgpu: edge","gpu_hotspot_temperature":68.0,"gpu_hotspot_source":"amdgpu: junction","power_consumption":17.6}' "$PROJECT" "$TIMESTAMP")
docker compose -p "$PROJECT" exec -T mqtt mosquitto_pub \
  -h 127.0.0.1 -p 1883 -u nivus-agent -P "$MQTT_PASSWORD" \
  -t nivus/edge/telemetry -q 1 -m "$PAYLOAD"
for attempt in $(seq 1 15); do
  DB_RESULT=$(docker compose -p "$PROJECT" exec -T api python -c \
    'import sqlite3,sys; c=sqlite3.connect("/data/nivus.db"); check=c.execute("PRAGMA quick_check").fetchone()[0]; row=c.execute("SELECT COUNT(*),temperature_source,temperature,gpu_temperature,gpu_hotspot_temperature FROM telemetry WHERE node=?", (sys.argv[1],)).fetchone(); assert row == (1,"coretemp: Package id 0",57.0,47.0,68.0), row; print(check, row[0]); c.close()' \
    "$PROJECT")
  [[ "$DB_RESULT" == 'ok 1' ]] && break
  sleep 1
done
[[ "$DB_RESULT" == 'ok 1' ]]
echo "sqlite_check_and_sample=$DB_RESULT"
echo '===CANDIDATE_CONTAINER_RESOURCES==='
docker stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}' "$API_ID" "$MQTT_ID" "$WORKER_ID" "$WEB_ID"
if [[ "${NIVUS_STAGING_REQUIRE_LEGACY_HOST:-1}" == "1" ]]; then
  echo '===EXISTING_SERVICES_DURING_SMOKE==='
  systemctl is-active nivus-api nivus-worker nivus-telemetry
  curl -fsS --max-time 3 http://127.0.0.1:8000/health
  echo
  docker ps --filter name=^/nivus-mosquitto$ --format '{{.Names}} {{.Status}}'
else
  echo 'legacy_host_checks=skipped (isolated disposable runner)'
fi
echo 'COMPOSE_SMOKE=passed'
