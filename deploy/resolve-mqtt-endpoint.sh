#!/usr/bin/env bash
set -Eeuo pipefail

CURRENT=/opt/nivus-compose/current
RUNTIME_DIR=/run/nivus-compose
RUNTIME_ENV="$RUNTIME_DIR/telemetry-runtime.env"

install -d -o root -g nivus-telemetry -m 0750 "$RUNTIME_DIR"

for attempt in {1..30}; do
  container_id=$(docker compose \
    --project-directory "$CURRENT" \
    -f "$CURRENT/docker-compose.yml" \
    ps -q mqtt 2>/dev/null || true)

  if [[ -n "$container_id" ]]; then
    container_ip=$(docker inspect \
      --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
      "$container_id" 2>/dev/null || true)

    if [[ "$container_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && \
       python3 -c 'import socket,sys; s=socket.create_connection((sys.argv[1], 1883), timeout=2); s.close()' "$container_ip"; then
      temp_file="$RUNTIME_DIR/.telemetry-runtime.env.$$"
      printf 'NIVUS_MQTT_BROKER=%s\n' "$container_ip" > "$temp_file"
      chown root:nivus-telemetry "$temp_file"
      chmod 0640 "$temp_file"
      mv -f -- "$temp_file" "$RUNTIME_ENV"
      exit 0
    fi
  fi

  sleep 1
done

echo "Não foi possível localizar um broker MQTT saudável na rede privada Docker." >&2
exit 1
