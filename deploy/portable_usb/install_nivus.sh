#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  sudo bash install_nivus.sh [--profile master|worker] [--mode online|offline] [--check-only]

Master instala a stack Nivus no Linux persistente do USB. São aceitos Ubuntu Server
24.04+ e Debian 13 Trixie, amd64/x86_64. No momento, Master exige
internet para APT, imagens Docker e dependências Python/npm; o modo offline falha
antes de alterar o host e lista os artefatos ainda ausentes.

Worker instala o agente leve. Online, solicita URL/nome e código de pareamento;
offline, deixa o agente instalado, sem parear nem iniciar serviço.
EOF
}

fail() { printf 'Instalação Nivus: %s\n' "$*" >&2; exit 2; }

PROFILE=
MODE=
CHECK_ONLY=0
while (($#)); do
  case "$1" in
    --profile)
      (($# >= 2)) || fail "--profile requer master ou worker."
      PROFILE=$2
      shift 2
      ;;
    --mode)
      (($# >= 2)) || fail "--mode requer online ou offline."
      MODE=$2
      shift 2
      ;;
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) fail "opção desconhecida: $1" ;;
  esac
done

if [[ -z "$PROFILE" ]]; then
  [[ -t 0 ]] || fail "informe --profile master ou --profile worker quando não houver terminal interativo."
  printf 'Perfil de instalação:\n  1) Master — dashboard, API e serviços locais\n  2) Worker — agente leve pareado ao Master\n'
  read -r -p 'Escolha [1/2]: ' choice
  case "$choice" in 1) PROFILE=master ;; 2) PROFILE=worker ;; *) fail "perfil inválido." ;; esac
fi
[[ "$PROFILE" == master || "$PROFILE" == worker ]] || fail "perfil deve ser master ou worker."

if [[ -z "$MODE" ]]; then
  if [[ -t 0 ]]; then
    read -r -p 'Modo [online/offline] (padrão online): ' answer
    MODE=${answer:-online}
  else
    MODE=online
  fi
fi
[[ "$MODE" == online || "$MODE" == offline ]] || fail "modo deve ser online ou offline."

((EUID == 0)) || fail "execute no Linux alvo com sudo: sudo bash install_nivus.sh --profile master|worker."

BUNDLE_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
PAYLOAD_ROOT="$BUNDLE_DIR/payload"
[[ -x "$(command -v python3 || true)" ]] || fail "Python 3 é necessário para validar o manifesto antes de qualquer alteração."
PYTHON_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 - "$PYTHON_VERSION" <<'PY' || fail "Python 3.10 ou superior é necessário."
import sys
major, minor = map(int, sys.argv[1].split("."))
raise SystemExit(0 if (major, minor) >= (3, 10) else 1)
PY

[[ -f "$PAYLOAD_ROOT/deploy/portable_usb/create_bundle.py" ]] || fail "o payload do pacote está incompleto."
python3 "$PAYLOAD_ROOT/deploy/portable_usb/create_bundle.py" verify --bundle "$BUNDLE_DIR"
BUNDLE_VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["bundle_version"])' "$BUNDLE_DIR/bundle_manifest.json")
BUNDLE_COMMIT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["source_commit"])' "$BUNDLE_DIR/bundle_manifest.json")

preflight_worker() {
  PYTHONPATH="$PAYLOAD_ROOT" python3 - "$BUNDLE_VERSION" "$BUNDLE_COMMIT" "$PAYLOAD_ROOT/deploy/nivus-node-agent.service.example" <<'PY'
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from deploy.portable_usb.platform_support import describe_supported_platforms, identify_supported_platform, read_os_release

def stop(message):
    raise SystemExit("Pré-verificação Worker: " + message)

if os.geteuid() != 0:
    stop("execute com sudo.")
try:
    release = read_os_release()
except OSError:
    stop("não foi possível identificar a distribuição Linux.")
supported = identify_supported_platform(release)
if supported is None:
    stop(f"sistemas aceitos: {describe_supported_platforms()} x86_64/amd64.")
if platform.machine() != "x86_64":
    stop("esta versão do pacote aceita somente x86_64/amd64.")
if any(shutil.which(command) is None for command in ("systemctl", "runuser", "useradd", "getent", "install", "cmp", "stat", "od", "tr", "chown", "chmod", "cp", "mv")):
    stop("systemd e runuser são necessários.")
if shutil.which("python3") is None or sys.version_info < (3, 10):
    stop("Python 3.10 ou superior é necessário; nenhum pacote será instalado automaticamente no modo Worker.")
try:
    systemd_version = int(subprocess.run(["systemctl", "--version"], check=True, capture_output=True, text=True).stdout.split()[1])
except (OSError, subprocess.SubprocessError, IndexError, ValueError):
    stop("não foi possível confirmar a versão do systemd.")
if systemd_version < 247:
    stop("systemd 247 ou superior é necessário.")
opt_parent = Path("/opt/nivus")
if opt_parent.is_symlink() or (opt_parent.exists() and not opt_parent.is_dir()):
    stop("/opt/nivus existe como caminho inválido; preservado.")
app_root = opt_parent / "node-agent"
state_root = Path("/var/lib/nivus-node-agent")
unit_path = Path("/etc/systemd/system/nivus-node-agent.service")
account = subprocess.run(["getent", "passwd", "nivus-node-agent"], capture_output=True, text=True).stdout.strip()
state_uid = None
state_gid = None
if account:
    fields = account.split(":")
    if len(fields) < 7 or fields[2] == "0" or fields[5] != str(state_root) or not fields[6].endswith("nologin"):
        stop("a conta nivus-node-agent já existe com propriedades diferentes; preservada.")
    state_uid = int(fields[2])
    group = subprocess.run(["getent", "group", "nivus-node-agent"], capture_output=True, text=True).stdout.strip()
    if not group or len(group.split(":")) < 3:
        stop("o grupo nivus-node-agent está ausente; preservado.")
    state_gid = int(group.split(":")[2])
    if state_root.is_symlink() or not state_root.is_dir():
        stop("o diretório de estado do agente existente é inválido; preservado.")
    state_stat = state_root.stat()
    if state_stat.st_uid != state_uid or state_stat.st_gid != state_gid or (state_stat.st_mode & 0o777) != 0o700:
        stop("proprietário ou permissões do estado existente são inesperados; preservados.")
else:
    if state_root.exists() or state_root.is_symlink():
        stop("/var/lib/nivus-node-agent já existe sem a conta esperada; preservado.")
if app_root.exists() or app_root.is_symlink():
    marker = app_root / ".nivus-installer-bundle"
    if app_root.is_symlink() or not app_root.is_dir() or not marker.is_file() or marker.is_symlink():
        stop("/opt/nivus/node-agent já existe sem o marcador deste pacote; preservado.")
    if marker.read_text(encoding="utf-8").strip() != sys.argv[1] + " " + sys.argv[2]:
        stop("a versão instalada do agente difere do pacote; preservada.")
    app_stat = app_root.stat()
    marker_stat = marker.stat()
    if app_stat.st_uid != 0 or (app_stat.st_mode & 0o022) or marker_stat.st_uid != 0 or (marker_stat.st_mode & 0o022):
        stop("proprietário ou permissões do agente instalado são inesperados; preservados.")
if unit_path.exists() or unit_path.is_symlink():
    if unit_path.is_symlink() or not unit_path.is_file():
        stop("a unidade systemd existente é inválida; preservada.")
    if unit_path.read_bytes() != Path(sys.argv[3]).read_bytes():
        stop("a unidade systemd instalada difere do pacote; preservada.")
    unit_stat = unit_path.stat()
    if unit_stat.st_uid != 0 or (unit_stat.st_mode & 0o022):
        stop("proprietário ou permissões da unidade systemd são inesperados; preservados.")
if state_root.exists() and state_root.is_dir():
    credentials = state_root / "credentials.json"
    if credentials.exists() or credentials.is_symlink():
        if credentials.is_symlink() or not credentials.is_file():
            stop("arquivo de credenciais do nó é inválido; preservado.")
        credentials_stat = credentials.stat()
        if credentials_stat.st_uid != state_uid or credentials_stat.st_gid != state_gid or (credentials_stat.st_mode & 0o777) != 0o600:
            stop("proprietário ou permissões das credenciais do nó são inesperados; preservados.")
    ca_file = state_root / "master-ca.crt"
    if ca_file.exists() or ca_file.is_symlink():
        if ca_file.is_symlink() or not ca_file.is_file():
            stop("certificado CA local inválido; preservado.")
        ca_stat = ca_file.stat()
        if ca_stat.st_uid != state_uid or ca_stat.st_gid != state_gid or (ca_stat.st_mode & 0o777) != 0o644:
            stop("proprietário ou permissões do certificado CA são inesperados; preservados.")
if shutil.disk_usage("/opt").free < 256 * 1024**2:
    stop("menos de 256 MiB livres em /opt; libere espaço antes da instalação.")
if shutil.disk_usage("/var/lib").free < 64 * 1024**2:
    stop("menos de 64 MiB livres em /var/lib; libere espaço antes da instalação.")
print(f"Pré-verificação Worker aprovada: {supported.display_name}, x86_64, systemd e espaço disponíveis.")
print("Nenhuma verificação de pareamento ou execução de tarefas distribuídas foi presumida.")
PY
}

preflight_master() {
  PYTHONPATH="$PAYLOAD_ROOT" python3 - "$PAYLOAD_ROOT" <<'PY'
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from deploy.portable_usb import configure_runtime as runtime
from deploy.portable_usb.platform_support import describe_supported_platforms, identify_supported_platform, read_os_release

def stop(message):
    raise SystemExit("Pré-verificação Master: " + message)

if os.geteuid() != 0:
    stop("execute com sudo.")
try:
    release = read_os_release()
except OSError:
    stop("não foi possível identificar a distribuição Linux.")
supported = identify_supported_platform(release)
if supported is None:
    stop(f"sistemas aceitos: {describe_supported_platforms()} x86_64/amd64.")
if platform.machine() != "x86_64":
    stop("esta versão do pacote aceita somente x86_64/amd64.")
if shutil.which("systemctl") is None or shutil.which("python3") is None:
    stop("systemd e Python 3 são necessários.")
if sys.version_info < (3, 10):
    stop("Python 3.10 ou superior é necessário.")
try:
    systemd_version = int(subprocess.run(["systemctl", "--version"], check=True, capture_output=True, text=True).stdout.split()[1])
except (OSError, subprocess.SubprocessError, IndexError, ValueError):
    stop("não foi possível confirmar a versão do systemd.")
if systemd_version < 247:
    stop("systemd 247 ou superior é necessário.")
if Path("/opt/nivus-compose/current").exists() or Path("/opt/nivus-compose/current").is_symlink():
    stop("Nivus Compose já está instalado; nenhum arquivo foi alterado.")
for conflict in (
    "/etc/systemd/system/nivus-time-sync.service",
    "/etc/nivus-compose/time-sync.env",
    "/usr/local/bin/nivusctl",
    "/usr/local/bin/nivus",
    "/etc/tmpfiles.d/nivus-maintenance.conf",
    "/run/nivus-maintenance",
):
    path = Path(conflict)
    if path.exists() or path.is_symlink():
        stop(f"caminho conflitante {conflict}; nenhum arquivo foi alterado.")
for unit in ("docker.service", "nivus-compose-telemetry.service"):
    active = subprocess.run(["systemctl", "is-active", "--quiet", unit], check=False).returncode == 0
    if active:
        stop(f"{unit} já está ativo; nenhum arquivo foi alterado.")
root_mount, data_mount = runtime.inspect_storage()
data_root = Path("/var/lib/nivus")
runtime._validate_volume_tree(data_root)
unit_files = runtime._source_unit_files(Path(sys.argv[1]))
runtime._validate_unit_destinations(Path("/"), unit_files)
for link_path, target in runtime.LINKS.items():
    runtime._validate_link(Path("/"), link_path, target)
if shutil.disk_usage(data_root).free < 8 * 1024**3:
    stop("NIVUS_DATA tem menos de 8 GiB livres para imagens e builds; libere espaço e tente novamente.")
print(f"Pré-verificação Master aprovada: {supported.display_name}, raiz e dados em USB/ext4; {shutil.disk_usage(data_root).free // 1024**3} GiB livres.")
print("O instalador usará APT, Docker Hub, PyPI e npm; nenhum serviço foi iniciado nesta etapa.")
PY
}

install_worker_app() {
  local app_root=/opt/nivus/node-agent
  local state_root=/var/lib/nivus-node-agent
  local account_info
  if ! getent passwd nivus-node-agent >/dev/null; then
    useradd --system --user-group --home-dir "$state_root" --create-home --shell /usr/sbin/nologin nivus-node-agent
  fi
  account_info=$(getent passwd nivus-node-agent)
  [[ "$(cut -d: -f3 <<<"$account_info")" != 0 ]] || fail "a conta do agente não pode ser root."
  if [[ ! -d "$state_root" ]]; then install -d -o nivus-node-agent -g nivus-node-agent -m 700 "$state_root"; fi
  [[ ! -L "$state_root" ]] || fail "o diretório de estado do agente é um link inesperado."
  chown nivus-node-agent:nivus-node-agent "$state_root"
  chmod 700 "$state_root"

  if [[ -e "$app_root" || -L "$app_root" ]]; then
    [[ -d "$app_root" && ! -L "$app_root" && -f "$app_root/.nivus-installer-bundle" ]] || fail "diretório de agente conflitante; nada foi substituído."
    [[ "$(cat -- "$app_root/.nivus-installer-bundle")" == "$BUNDLE_VERSION $BUNDLE_COMMIT" ]] || fail "a versão instalada do agente difere do pacote; use o atualizador apropriado."
  else
    if [[ ! -d /opt/nivus ]]; then install -d -m 755 /opt/nivus; fi
    local stage
    stage=$(mktemp -d /opt/nivus/.node-agent.XXXXXX)
    cp -a "$PAYLOAD_ROOT/node_agent" "$stage/node_agent"
    printf '%s %s\n' "$BUNDLE_VERSION" "$BUNDLE_COMMIT" > "$stage/.nivus-installer-bundle"
    chown -R root:root "$stage"
    chmod 755 "$stage" "$stage/node_agent"
    mv -- "$stage" "$app_root"
  fi
}

pair_worker() {
  local state_root=/var/lib/nivus-node-agent
  local credentials="$state_root/credentials.json"
  if [[ ! -e "$credentials" ]]; then
    local suffix suggested node_name master_url ca_file ca_destination
    suffix=$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')
    suggested="nivus-worker-$suffix"
    read -r -p 'URL HTTPS do Nó Master: ' master_url
    [[ -n "$master_url" ]] || fail "URL do Master obrigatória; o agente foi instalado sem iniciar serviço."
    read -r -p "Nome inicial único [$suggested]: " node_name
    node_name=${node_name:-$suggested}
    read -r -p 'Caminho do certificado CA público (Enter se já confiável no sistema): ' ca_file
    local -a command=(python3 -m node_agent.agent pair --master-url "$master_url" --name "$node_name" --credentials "$credentials")
    if [[ -n "$ca_file" ]]; then
      [[ -f "$ca_file" && ! -L "$ca_file" ]] || fail "arquivo CA não existe ou não é regular; o agente continua instalado sem serviço."
      python3 - "$ca_file" <<'PY' || fail "o arquivo indicado não é um certificado CA PEM válido."
import ssl
import sys
ssl.create_default_context(cafile=sys.argv[1])
PY
      ca_destination="$state_root/master-ca.crt"
      if [[ -e "$ca_destination" || -L "$ca_destination" ]]; then
        [[ -f "$ca_destination" && ! -L "$ca_destination" ]] || fail "certificado CA anterior inválido; preservado."
        cmp -s -- "$ca_file" "$ca_destination" || fail "já existe outro certificado CA; nenhum arquivo foi substituído."
      else
        install -o nivus-node-agent -g nivus-node-agent -m 644 "$ca_file" "$ca_destination"
      fi
      command+=(--ca-file "$ca_destination")
    fi
    printf '\nO agente pedirá o código de pareamento de uso único em entrada oculta.\n'
    runuser -u nivus-node-agent -- env HOME="$state_root" PYTHONPATH=/opt/nivus/node-agent "${command[@]}"
  else
    [[ -f "$credentials" && ! -L "$credentials" ]] || fail "credencial existente inválida; preservada."
    [[ "$(stat -c '%U:%G:%a' "$credentials")" == "nivus-node-agent:nivus-node-agent:600" ]] || fail "credencial existente não tem proprietário/permissões esperados; preservada."
  fi
}

install_worker_service() {
  local source="$PAYLOAD_ROOT/deploy/nivus-node-agent.service.example"
  local target=/etc/systemd/system/nivus-node-agent.service
  [[ -s /var/lib/nivus-node-agent/credentials.json ]] || fail "o Worker está instalado, mas não pareado; serviço não será iniciado."
  if [[ -e "$target" || -L "$target" ]]; then
    [[ -f "$target" && ! -L "$target" ]] || fail "unidade systemd conflitante; preservada."
    cmp -s -- "$source" "$target" || fail "unidade systemd existente difere do pacote; preservada."
  else
    install -o root -g root -m 644 "$source" "$target"
  fi
  systemctl daemon-reload
  systemctl enable --now nivus-node-agent.service
  if ! systemctl is-active --quiet nivus-node-agent.service; then
    systemctl status --no-pager --full nivus-node-agent.service || true
    fail "o serviço do Worker não ficou ativo. Credencial local preservada para diagnóstico e nova tentativa."
  fi
  printf 'Worker instalado e ativo. Ele envia heartbeat e CPU/memória/disco; execução de tarefas remotas ainda não está implementada.\n'
}

if [[ "$PROFILE" == master ]]; then
  if [[ "$MODE" == offline ]]; then
    cat >&2 <<'EOF'
Modo offline Master não está pronto. O host não foi alterado.
Artefatos que ainda faltam no pacote para instalar sem rede:
  - arquivos .deb versionados para Docker, Compose, Python, OpenSSL e utilitários;
  - imagens Docker pré-construídas e verificadas para API, dashboard e Mosquitto;
  - dependências Python e npm incorporadas ao build (ou imagens completas exportadas);
  - procedimento de carga offline com SHA-256 e validação do conjunto de versões.
Use --mode online quando o Linux tiver acesso a APT, Docker Hub, PyPI e npm.
EOF
    exit 3
  fi
  preflight_master
  if ((CHECK_ONLY)); then
    printf 'Verificação concluída para Master. Nenhuma configuração foi escrita.\n'
    exit 0
  fi
  read -r -p 'Continuar com a instalação Master no Linux persistente deste USB? [s/N] ' confirm
  [[ "$confirm" == s || "$confirm" == S || "$confirm" == sim || "$confirm" == SIM ]] || fail "cancelado sem iniciar a instalação."
  PYTHONPATH="$PAYLOAD_ROOT" python3 "$PAYLOAD_ROOT/deploy/portable_usb/configure_runtime.py" --repository-root "$PAYLOAD_ROOT"
  exec bash "$PAYLOAD_ROOT/deploy/install.sh"
fi

preflight_worker
if ((CHECK_ONLY)); then
  if [[ "$MODE" == offline ]]; then
    printf 'Verificação concluída para Worker offline. Nada foi instalado nem pareado.\n'
  else
    printf 'Verificação concluída para Worker online. O pareamento pedirá URL e código de uso único.\n'
  fi
  exit 0
fi
read -r -p 'Continuar com a instalação do agente Worker neste Linux? [s/N] ' confirm
[[ "$confirm" == s || "$confirm" == S || "$confirm" == sim || "$confirm" == SIM ]] || fail "cancelado sem iniciar a instalação."
install_worker_app
if [[ "$MODE" == offline ]]; then
  printf 'Agente Worker instalado offline, ainda sem pareamento. Nenhum serviço foi iniciado.\n'
  printf 'Quando o Master estiver acessível, rode novamente este pacote com --profile worker --mode online para parear e ativar.\n'
  exit 0
fi
pair_worker
install_worker_service
