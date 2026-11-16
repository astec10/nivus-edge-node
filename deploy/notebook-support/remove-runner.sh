#!/usr/bin/env bash
set -Eeuo pipefail
readonly RUNNER_USER="nivus-support"
readonly RUNNER_HOME="/var/lib/nivus-support"
readonly RUNNER_DIR="/opt/nivus-notebook-support"
fail() {
  printf 'Erro: %s\n' "$*" >&2
  exit 1
}
[[ "$EUID" -eq 0 ]] || fail "execute com sudo: sudo bash deploy/notebook-support/remove-runner.sh"
[[ -d "$RUNNER_DIR" && -d "$RUNNER_HOME" ]] || fail "runner não parece instalado neste caminho"
id "$RUNNER_USER" >/dev/null 2>&1 || fail "conta do runner não encontrada"
printf 'Esta operação remove somente o runner e sua área de trabalho em:\n  %s\n  %s\n' "$RUNNER_DIR" "$RUNNER_HOME"
read -r -p "Digite REMOVE NIVUS SUPPORT para confirmar: " confirmation
[[ "$confirmation" == "REMOVE NIVUS SUPPORT" ]] || fail "remoção cancelada"
printf 'Gere um token de remoção em Settings > Actions > Runners > nivus-notebook-support > Remove.\n'
read -r -s -p "Token temporário de remoção: " RUNNER_REMOVE_TOKEN
printf '\n'
[[ -n "$RUNNER_REMOVE_TOKEN" ]] || fail "token vazio"
mapfile -t units < <(grep -lF "$RUNNER_DIR" /etc/systemd/system/actions.runner.*.service 2>/dev/null || true)
[[ "${#units[@]}" -eq 1 ]] || fail "não consegui identificar unicamente o serviço registrado"
unit_path="${units[0]}"
unit_name="$(basename -- "$unit_path")"
[[ "$unit_name" =~ ^actions\.runner\.[A-Za-z0-9._-]+\.service$ ]] || fail "nome de serviço inesperado"
systemctl stop "$unit_name" || true
runuser -u "$RUNNER_USER" -- env NIVUS_RUNNER_TOKEN="$RUNNER_REMOVE_TOKEN" \
  bash -c 'cd /opt/nivus-notebook-support && ./config.sh remove --token "$NIVUS_RUNNER_TOKEN"'
unset RUNNER_REMOVE_TOKEN
(
  cd "$RUNNER_DIR"
  ./svc.sh uninstall
)
systemctl daemon-reload
rm -rf -- "/etc/systemd/system/${unit_name}.d" "$RUNNER_DIR" "$RUNNER_HOME"
userdel "$RUNNER_USER"
printf 'Runner removido e desregistrado. O Nivus e seus dados não foram alterados.\n'
