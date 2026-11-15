#!/usr/bin/env bash
set -Eeuo pipefail

RUNTIME_ENV=/run/nivus-compose/telemetry-runtime.env
if [[ ! -r "$RUNTIME_ENV" ]]; then
  echo "Arquivo de endpoint MQTT temporário não está disponível." >&2
  exit 1
fi

broker=$(sed -n 's/^NIVUS_MQTT_BROKER=//p' "$RUNTIME_ENV")
if [[ ! "$broker" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "Endpoint MQTT temporário inválido." >&2
  exit 1
fi
IFS=. read -r a b c d <<< "$broker"
for octet in "$a" "$b" "$c" "$d"; do
  if (( 10#$octet > 255 )); then
    echo "Endpoint MQTT temporário inválido." >&2
    exit 1
  fi
done

if [[ -z "${CREDENTIALS_DIRECTORY:-}" || ! -r "$CREDENTIALS_DIRECTORY/mqtt_agent_password" ]]; then
  echo "Credencial MQTT do coletor não está disponível pelo systemd." >&2
  exit 1
fi

export NIVUS_MQTT_BROKER="$broker"
export NIVUS_MQTT_PASSWORD_FILE="$CREDENTIALS_DIRECTORY/mqtt_agent_password"
exec /opt/nivus-compose/venv/bin/python /opt/nivus-compose/current/telemetry/agent.py
