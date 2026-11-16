#!/usr/bin/env bash
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0" >&2
  exit 1
fi
APP=/opt/nivus-compose/current
if [[ ! -d "$APP" ]]; then
  echo "Instalação Nivus Compose não encontrada em $APP" >&2
  exit 2
fi
systemctl disable --now nivus-compose-telemetry.service 2>/dev/null || true
systemctl stop nivus-time-sync.service 2>/dev/null || true
cd "$APP"
docker compose down
cat <<'EOF'
Stack parada. Dados, segredos, certificados e imagens foram preservados.
Para reativar: cd /opt/nivus-compose/current && sudo docker compose up -d
EOF
