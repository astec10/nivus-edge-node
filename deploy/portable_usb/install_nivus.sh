#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo após iniciar o Ubuntu instalado no USB." >&2
  echo "Uso: sudo bash deploy/portable_usb/install_nivus.sh" >&2
  exit 1
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
REPOSITORY_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)

if [[ -e /opt/nivus-compose/current || -L /opt/nivus-compose/current ]]; then
  echo "Nivus já está instalado neste USB. Use o procedimento de atualização." >&2
  exit 2
fi

python3 "$SCRIPT_DIR/configure_runtime.py" --repository-root "$REPOSITORY_ROOT"
exec bash "$REPOSITORY_ROOT/deploy/install.sh"
