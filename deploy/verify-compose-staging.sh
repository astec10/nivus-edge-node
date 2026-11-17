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

for command in docker openssl curl ss python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "Comando ausente: $command" >&2; exit 2; }
done
bash -n deploy/promote-dashboard-443.sh
if ss -H -ltn 'sport = :28444' | grep -q .; then
  echo "Porta de proxy de staging 28444 ocupada." >&2
  exit 2
fi
if ss -H -ltn 'sport = :28443' | grep -q .; then
  echo "Porta de staging ocupada." >&2
  exit 2
fi

PROJECT="nivus-smoke-$(date -u +%Y%m%d-%H%M%S)-$$"
PORTLESS_PROXY="${PROJECT}-portless-proxy"
PORTLESS_CONFIG="/tmp/${PROJECT}-portless-nginx.conf"
DATA_DIR="/tmp/$PROJECT-data"
MOSQ_DATA_DIR="$APP_DIR/mosquitto"
SECRETS_DIR="$APP_DIR/secrets"
MAINTENANCE_DIR="/tmp/$PROJECT-maintenance"
TIME_SYNC_DIR="/tmp/$PROJECT-time-sync"
NIVUS_HELP_BIN="$APP_DIR/runtime-bin/$PROJECT"
export NIVUS_MAINTENANCE_STATE_DIR="$MAINTENANCE_DIR"
export NIVUS_TIME_SYNC_DIR="$TIME_SYNC_DIR"
export NIVUS_DATA_DIR="$DATA_DIR"
export NIVUS_MAINTENANCE_STATE_PATH="$MAINTENANCE_DIR/state.json"
RUNTIME_UID=$(sed -n 's/^NIVUS_RUNTIME_UID=//p' .env)
RUNTIME_GID=$(sed -n 's/^NIVUS_RUNTIME_GID=//p' .env)
HOST_UID=$(id -u)
HOST_GID=$(id -g)
[[ ! -e "$DATA_DIR" && ! -L "$DATA_DIR" && ! -e "$MAINTENANCE_DIR" && ! -L "$MAINTENANCE_DIR" && ! -e "$TIME_SYNC_DIR" && ! -L "$TIME_SYNC_DIR" ]] || { echo "Smoke temp path already exists; refusing to reuse it." >&2; exit 2; }

MOSQUITTO_IMAGE=$(awk '$1 == "image:" && $2 ~ /^eclipse-mosquitto:/ {print $2; exit}' docker-compose.yml)
[[ "$MOSQUITTO_IMAGE" =~ ^eclipse-mosquitto:2@sha256:[a-f0-9]{64}$ ]] || { echo "Imagem Mosquitto fixada por digest não encontrada no Compose." >&2; exit 2; }
docker image inspect nivus-edge-api:local nivus-edge-web:local >/dev/null
if ! docker image inspect "$MOSQUITTO_IMAGE" >/dev/null 2>&1; then docker pull "$MOSQUITTO_IMAGE"; fi
install -d -m 700 "$SECRETS_DIR"
install -d -m 750 "$DATA_DIR" "$MOSQ_DATA_DIR"
install -d -m 755 "$APP_DIR/runtime-state"
install -d -m 755 "$MAINTENANCE_DIR" "$TIME_SYNC_DIR"
rm -f -- "$SECRETS_DIR/jwt_secret" "$SECRETS_DIR"/mqtt_*_password \
  "$SECRETS_DIR/mosquitto_passwords" "$SECRETS_DIR/mosquitto_acl" \
  "$SECRETS_DIR/tls.key" "$SECRETS_DIR/tls.crt" "$SECRETS_DIR/provider_encryption_key"
cp -- deploy/mosquitto.acl "$SECRETS_DIR/mosquitto_acl"
openssl rand -hex 48 > "$SECRETS_DIR/jwt_secret"
for role in api worker agent health; do openssl rand -hex 32 > "$SECRETS_DIR/mqtt_${role}_password"; done
(umask 077; openssl rand -out "$SECRETS_DIR/provider_encryption_key" 32)
chmod 444 "$SECRETS_DIR/jwt_secret" "$SECRETS_DIR"/mqtt_*_password "$SECRETS_DIR/provider_encryption_key"
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
  --mount "type=bind,source=$MAINTENANCE_DIR,target=/maintenance" \
  --env "RUNTIME_UID=$RUNTIME_UID" --env "RUNTIME_GID=$RUNTIME_GID" \
  --entrypoint /bin/sh nivus-edge-api:local -ec \
  'chown -R "$RUNTIME_UID:$RUNTIME_GID" /data /maintenance; chmod 700 /data; chmod 2750 /maintenance; chown -R 1883:1883 /mosq; chmod 750 /mosq'
[[ $(stat -c "%a" "$MAINTENANCE_DIR") == 2750 ]]
[[ $(stat -c "%u:%g" "$MAINTENANCE_DIR") == "$RUNTIME_UID:$RUNTIME_GID" ]]

cleanup() {
  local rc=$?
  trap - EXIT
  docker rm -f "$PORTLESS_PROXY" >/dev/null 2>&1 || true
  rm -f -- "$PORTLESS_CONFIG"
  if (( rc != 0 )); then docker compose -p "$PROJECT" logs --no-color --tail=30 api worker mqtt web 2>&1 || true; fi
  docker compose -p "$PROJECT" down --remove-orphans >/dev/null 2>&1 || true
  docker run --rm --user 0 --network none \
    --mount "type=bind,source=$DATA_DIR,target=/data" \
    --mount "type=bind,source=$MOSQ_DATA_DIR,target=/mosq" \
    --mount "type=bind,source=$MAINTENANCE_DIR,target=/maintenance" \
    --env "HOST_UID=$HOST_UID" --env "HOST_GID=$HOST_GID" \
    --entrypoint /bin/sh nivus-edge-api:local -ec \
    'chown -R "$HOST_UID:$HOST_GID" /data /mosq /maintenance; chmod 750 /data /mosq; chmod 755 /maintenance' >/dev/null 2>&1 || true
  if (( rc == 0 )); then
    if [[ "$MAINTENANCE_DIR" == "/tmp/$PROJECT-maintenance" ]]; then
      rm -rf -- "$MAINTENANCE_DIR" 2>/dev/null || true
    else
      echo "Refusing to remove unexpected maintenance staging path: $MAINTENANCE_DIR" >&2
      rc=1
    fi
    if [[ "$TIME_SYNC_DIR" == "/tmp/$PROJECT-time-sync" ]]; then
      rm -rf -- "$TIME_SYNC_DIR" 2>/dev/null || true
    else
      echo "Refusing to remove unexpected time-sync staging path: $TIME_SYNC_DIR" >&2
      rc=1
    fi
    if [[ "$DATA_DIR" == "/tmp/$PROJECT-data" ]]; then
      rm -rf -- "$DATA_DIR" 2>/dev/null || true
    else
      echo "Refusing to remove unexpected data staging path: $DATA_DIR" >&2
      rc=1
    fi
  else
    echo "Keeping isolated smoke data for diagnosis: $DATA_DIR and $MAINTENANCE_DIR" >&2
  fi
  rm -f -- "$NIVUS_HELP_BIN/nivus"
  rmdir -- "$NIVUS_HELP_BIN" 2>/dev/null || true
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
PROGRESS_HTML=$(curl -kfsS --connect-timeout 2 --max-time 5 https://127.0.0.1:28443/PROGRESS.html)
grep -q 'id="milestones"' <<< "$PROGRESS_HTML"
curl -kfsS --connect-timeout 2 --max-time 5 https://127.0.0.1:28443/progress.js | grep -q 'filterStatus'
echo "frontend_index_asset_and_progress=ok ($JS_ASSET)"
AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' https://127.0.0.1:28443/api/telemetry)
[[ "$AUTH_STATUS" == 401 ]]
echo "unauthenticated_telemetry_http=$AUTH_STATUS"
echo '===PORTLESS_NGINX_PROXY==='
INGRESS_NETWORK=$(docker network ls \
  --filter "label=com.docker.compose.project=$PROJECT" \
  --filter 'label=com.docker.compose.network=edge_ingress' -q)
[[ -n "$INGRESS_NETWORK" ]]
bash deploy/promote-dashboard-443.sh --render 8443 28443 127.0.0.1 /run/secrets/tls.crt /run/secrets/tls.key > "$PORTLESS_CONFIG"
docker run -d --name "$PORTLESS_PROXY" --network "$INGRESS_NETWORK" \
  -p 127.0.0.1:28444:8443 \
  --mount "type=bind,source=$PORTLESS_CONFIG,target=/tmp/nivus-portless.conf,readonly" \
  --mount "type=bind,source=$SECRETS_DIR/tls.crt,target=/run/secrets/tls.crt,readonly" \
  --mount "type=bind,source=$SECRETS_DIR/tls.key,target=/run/secrets/tls.key,readonly" \
  --entrypoint nginx nivus-edge-web:local -c /tmp/nivus-portless.conf -g 'daemon off;'
for attempt in $(seq 1 15); do
  if curl -kfsS --connect-timeout 2 --max-time 4 https://127.0.0.1:28444/health >/dev/null; then break; fi
  sleep 1
done
curl -kfsS --connect-timeout 2 --max-time 5 https://127.0.0.1:28444/health | grep -q '"status":"ok"'
PROXY_AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' \
  https://127.0.0.1:28444/api/telemetry)
[[ "$PROXY_AUTH_STATUS" == 401 ]]
echo "portless_proxy_health=200; unauthenticated_telemetry_http=$PROXY_AUTH_STATUS"
docker rm -f "$PORTLESS_PROXY" >/dev/null
rm -f -- "$PORTLESS_CONFIG"
python3 deploy/nivusctl help | grep -q 'sudo nivus maintenance disable'
MAINT_UNAUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' https://127.0.0.1:28443/api/maintenance)
[[ "$MAINT_UNAUTH_STATUS" == 401 ]]
echo "unauthenticated_maintenance_http=$MAINT_UNAUTH_STATUS"
install -d -m 755 "$NIVUS_HELP_BIN"
ln -s "$APP_DIR/deploy/nivusctl" "$NIVUS_HELP_BIN/nivus"
"$NIVUS_HELP_BIN/nivus" help | grep -q 'usage: nivus '

echo '===MQTT_TO_SQLITE==='
ADMIN_TOKEN=$(docker compose -p "$PROJECT" exec -T api python -c \
  'from database import get_db_connection; from security import create_access_token,hash_password; c=get_db_connection(); c.execute("INSERT OR REPLACE INTO users (username,password,role,must_change_password) VALUES (?,?,?,0)", ("smoke-maint-admin",hash_password("SmokeOnly-Password-1"),"admin")); c.commit(); c.close(); print(create_access_token("smoke-maint-admin","admin"))')
[[ -n "$ADMIN_TOKEN" ]]
VIEWER_TOKEN=$(docker compose -p "$PROJECT" exec -T api python -c \
  'from database import get_db_connection; from security import create_access_token,hash_password; c=get_db_connection(); c.execute("INSERT OR REPLACE INTO users (username,password,role,must_change_password) VALUES (?,?,?,0)", ("smoke-maint-viewer",hash_password("SmokeOnly-Password-2"),"viewer")); c.commit(); c.close(); print(create_access_token("smoke-maint-viewer","viewer"))')
[[ -n "$VIEWER_TOKEN" ]]
NTP_STATUS=$(curl -kfsS --connect-timeout 2 --max-time 5 \
  -H "Authorization: Bearer $ADMIN_TOKEN" https://127.0.0.1:28443/api/settings/time-sync)
python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["state"]=="unavailable" and not d["can_configure"], d' <<< "$NTP_STATUS"
NTP_INVALID_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"servers":["a.ntp.br","a.ntp.br","c.ntp.br"]}' https://127.0.0.1:28443/api/settings/time-sync)
[[ "$NTP_INVALID_STATUS" == 422 ]]
NTP_VIEWER_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Content-Type: application/json' \
  -d '{"servers":["a.ntp.br","b.ntp.br","c.ntp.br"]}' https://127.0.0.1:28443/api/settings/time-sync)
[[ "$NTP_VIEWER_STATUS" == 403 ]]
NTP_ADMIN_UNAVAILABLE=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"servers":["a.ntp.br","b.ntp.br","c.ntp.br"]}' https://127.0.0.1:28443/api/settings/time-sync)
[[ "$NTP_ADMIN_UNAVAILABLE" == 503 ]]
echo "host_ntp_status=unavailable; duplicate_validation=$NTP_INVALID_STATUS; viewer_write=$NTP_VIEWER_STATUS; missing_controller=$NTP_ADMIN_UNAVAILABLE"
VIEWER_MAINT_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled":true}' https://127.0.0.1:28443/api/maintenance)
[[ "$VIEWER_MAINT_STATUS" == 403 ]]
echo "viewer_maintenance_write_http=$VIEWER_MAINT_STATUS"

get_telemetry_count() {
  docker compose -p "$PROJECT" exec -T api python -c \
    'import sqlite3,sys; c=sqlite3.connect("/data/nivus.db"); print(c.execute("SELECT COUNT(*) FROM telemetry WHERE node=?", (sys.argv[1],)).fetchone()[0]); c.close()' \
    "$PROJECT"
}

publish_smoke_sample() {
  local timestamp payload password
  timestamp=$(date +%s)
  password=$(cat "$SECRETS_DIR/mqtt_agent_password")
  payload=$(printf '{"node":"%s","timestamp":%s,"cpu_percent":5.2,"memory_percent":42.0,"disk_percent":20.0,"temperature":57.0,"temperature_source":"coretemp: Package id 0","motherboard_temperature":null,"gpu_temperature":47.0,"gpu_temperature_source":"amdgpu: edge","gpu_hotspot_temperature":68.0,"gpu_hotspot_source":"amdgpu: junction","power_consumption":17.6}' "$PROJECT" "$timestamp")
  docker compose -p "$PROJECT" exec -T mqtt mosquitto_pub \
    -h 127.0.0.1 -p 1883 -u nivus-agent -P "$password" \
    -t nivus/edge/telemetry -q 1 -m "$payload"
}

wait_for_telemetry_count() {
  local expected="$1" actual=0
  for attempt in $(seq 1 15); do
    actual=$(get_telemetry_count)
    if [[ "$actual" == "$expected" ]]; then return 0; fi
    sleep 1
  done
  echo "Esperava $expected amostras MQTT; encontrei $actual." >&2
  return 1
}

assert_telemetry_count_unchanged() {
  local expected="$1" actual
  sleep 3
  actual=$(get_telemetry_count)
  [[ "$actual" == "$expected" ]] || {
    echo "A manutenção deveria manter $expected amostras; encontrei $actual." >&2
    return 1
  }
}

publish_smoke_sample
wait_for_telemetry_count 1
DB_RESULT=$(docker compose -p "$PROJECT" exec -T api python -c \
  'import sqlite3,sys; c=sqlite3.connect("/data/nivus.db"); check=c.execute("PRAGMA quick_check").fetchone()[0]; row=c.execute("SELECT COUNT(*),temperature_source,temperature,gpu_temperature,gpu_hotspot_temperature FROM telemetry WHERE node=?", (sys.argv[1],)).fetchone(); assert row == (1,"coretemp: Package id 0",57.0,47.0,68.0), row; print(check, row[0]); c.close()' \
  "$PROJECT")
[[ "$DB_RESULT" == 'ok 1' ]]
echo "sqlite_check_and_sample=$DB_RESULT"

echo '===MAINTENANCE_MODE==='
API_STATE=$(curl -kfsS --connect-timeout 2 --max-time 5 \
  -H "Authorization: Bearer $ADMIN_TOKEN" https://127.0.0.1:28443/api/maintenance)
grep -q '"enabled":false' <<< "$API_STATE"
curl -kfsS --connect-timeout 2 --max-time 5 -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled":true}' https://127.0.0.1:28443/api/maintenance | grep -q '"enabled":true'
STATE_METADATA=$(docker compose -p "$PROJECT" exec -T api python -c \
  'import os,stat,sys; st=os.stat(sys.argv[1]); print(f"{stat.S_IMODE(st.st_mode):o}:{st.st_uid}:{st.st_gid}")' \
  /run/nivus-maintenance/state.json)
[[ "$STATE_METADATA" == "640:$RUNTIME_UID:$RUNTIME_GID" ]]
docker run --rm --user "$HOST_UID:$RUNTIME_GID" --network none \
  --mount "type=bind,source=$MAINTENANCE_DIR,target=/maintenance,readonly" \
  --entrypoint /bin/sh nivus-edge-api:local -ec 'test -r /maintenance/state.json'
run_nivusctl() {
  local -a privilege=()
  if [[ $EUID -ne 0 ]]; then privilege=(sudo); fi
  "${privilege[@]}" env \
    NIVUS_DB_PATH="$DATA_DIR/nivus.db" \
    NIVUS_MAINTENANCE_STATE_PATH="$MAINTENANCE_DIR/state.json" \
    python3 deploy/nivusctl "$@"
}
run_nivusctl maintenance status | grep -q 'ATIVO'
publish_smoke_sample
assert_telemetry_count_unchanged 1
curl -kfsS --connect-timeout 2 --max-time 5 https://127.0.0.1:28443/health | grep -q '"status":"ok"'
run_nivusctl maintenance disable | grep -q 'inativo'
publish_smoke_sample
wait_for_telemetry_count 2
run_nivusctl maintenance enable | grep -q 'ATIVO'
curl -kfsS --connect-timeout 2 --max-time 5 -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled":false}' https://127.0.0.1:28443/api/maintenance | grep -q '"enabled":false'
publish_smoke_sample
wait_for_telemetry_count 3
[[ $(get_telemetry_count) == 3 ]]
echo 'maintenance_api_cli_toggle=passed'
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
