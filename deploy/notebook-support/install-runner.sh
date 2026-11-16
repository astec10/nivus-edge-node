#!/usr/bin/env bash
set -Eeuo pipefail
readonly REPOSITORY_URL="https://github.com/astec10/nivus-edge-node"
readonly RUNNER_VERSION="2.338.2"
readonly RUNNER_SHA256="baebf204307bac6193480852732f0aba2ae97b6c5597c244f4d5558390147c40"
readonly RUNNER_NAME="nivus-notebook-support"
readonly RUNNER_LABEL="nivus-support"
readonly RUNNER_USER="nivus-support"
readonly RUNNER_HOME="/var/lib/nivus-support"
readonly RUNNER_DIR="/opt/nivus-notebook-support"
fail() {
  printf 'Erro: %s\n' "$*" >&2
  exit 1
}
[[ "$EUID" -eq 0 ]] || fail "execute com sudo: sudo bash deploy/notebook-support/install-runner.sh"
[[ -r /etc/os-release ]] || fail "sistema operacional não identificado"
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || fail "o runner auxiliar exige Ubuntu"
[[ "$(uname -m)" == "x86_64" ]] || fail "esta instalação foi preparada para x86_64"
[[ -d /run/systemd/system ]] || fail "systemd não está ativo"
for command in curl tar sha256sum useradd runuser find sort comm systemctl; do
  command -v "$command" >/dev/null 2>&1 || fail "comando necessário ausente: $command"
done
if id "$RUNNER_USER" >/dev/null 2>&1 || [[ -e "$RUNNER_DIR" || -e "$RUNNER_HOME" ]]; then
  fail "há restos ou uma instalação existente; confira o README antes de remover qualquer coisa"
fi
tmp_dir="$(mktemp -d /tmp/nivus-runner-install.XXXXXX)"
trap 'rm -rf -- "$tmp_dir"; unset RUNNER_REGISTRATION_TOKEN || true' EXIT
archive="$tmp_dir/actions-runner.tar.gz"
download_url="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
printf '[1/6] Baixando o runner oficial v%s...\n' "$RUNNER_VERSION"
curl --fail --silent --show-error --location --retry 3 "$download_url" --output "$archive"
printf '%s  %s\n' "$RUNNER_SHA256" "$archive" | sha256sum --check --status \
  || fail "o SHA-256 do pacote do runner não corresponde ao release oficial"
printf '[2/6] Criando conta de serviço sem login e diretórios isolados...\n'
useradd --system --create-home --home-dir "$RUNNER_HOME" --shell /usr/sbin/nologin "$RUNNER_USER"
install -d -o "$RUNNER_USER" -g "$RUNNER_USER" -m 0750 "$RUNNER_DIR"
printf '[3/6] Instalando dependências documentadas pelo runner...\n'
tar -xzf "$archive" -C "$RUNNER_DIR"
"$RUNNER_DIR/bin/installdependencies.sh"
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR" "$RUNNER_HOME"
chmod 0700 "$RUNNER_HOME"
printf 'No GitHub, abra Settings > Actions > Runners > New self-hosted runner e selecione Linux x64.\n'
printf 'Quando a página mostrar os comandos, copie o token de registro, que expira em uma hora.\n'
read -r -s -p "Token temporário de registro: " RUNNER_REGISTRATION_TOKEN
printf '\n'
[[ -n "$RUNNER_REGISTRATION_TOKEN" ]] || fail "token vazio"
printf '[4/6] Registrando somente o runner auxiliar deste repositório...\n'
runuser -u "$RUNNER_USER" -- env NIVUS_RUNNER_TOKEN="$RUNNER_REGISTRATION_TOKEN" \
  bash -c 'cd /opt/nivus-notebook-support && ./config.sh --url https://github.com/astec10/nivus-edge-node --token "$NIVUS_RUNNER_TOKEN" --name nivus-notebook-support --labels nivus-support --work _work --unattended'
unset RUNNER_REGISTRATION_TOKEN
printf '[5/6] Instalando o serviço e restringindo o sistema de arquivos...\n'
find /etc/systemd/system -maxdepth 1 -type f -name 'actions.runner.*.service' -printf '%f\n' | sort > "$tmp_dir/units-before"
(
  cd "$RUNNER_DIR"
  ./svc.sh install "$RUNNER_USER"
)
find /etc/systemd/system -maxdepth 1 -type f -name 'actions.runner.*.service' -printf '%f\n' | sort > "$tmp_dir/units-after"
mapfile -t new_units < <(comm -13 "$tmp_dir/units-before" "$tmp_dir/units-after")
[[ "${#new_units[@]}" -eq 1 ]] || fail "não consegui identificar unicamente o serviço recém-instalado"
unit_name="${new_units[0]}"
[[ "$unit_name" =~ ^actions\.runner\.[A-Za-z0-9._-]+\.service$ ]] || fail "nome de serviço inesperado"
install -d -m 0755 "/etc/systemd/system/${unit_name}.d"
cat > "/etc/systemd/system/${unit_name}.d/override.conf" <<'EOF'
[Service]
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
NoNewPrivileges=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
ProtectProc=invisible
LockPersonality=true
RestrictSUIDSGID=true
MemoryMax=2G
ReadWritePaths=/opt/nivus-notebook-support /var/lib/nivus-support
InaccessiblePaths=/var/lib/nivus-compose /etc/nivus-compose /opt/nivus-compose /var/www /home/nivus
EOF
chmod 0644 "/etc/systemd/system/${unit_name}.d/override.conf"
systemctl daemon-reload
printf '[6/6] Iniciando e verificando o serviço...\n'
(
  cd "$RUNNER_DIR"
  ./svc.sh start
)
systemctl is-active --quiet "$unit_name" || fail "runner instalado, mas serviço não está ativo; consulte systemctl status $unit_name"
printf 'Runner auxiliar instalado: %s (label %s).\n' "$RUNNER_NAME" "$RUNNER_LABEL"
printf 'Ele não recebe código de PR; use Actions > Notebook support > Run workflow na branch padrão.\n'
printf 'Sem acesso ao Docker, segredos do projeto, dados Compose ou diretórios pessoais.\n'
