#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root durante a montagem da imagem Ubuntu." >&2
  exit 1
fi
[[ $# -eq 1 ]] || { echo "Uso: sudo bash $0 /caminho/raizfs-de-imagem" >&2; exit 2; }
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
SOURCE_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
ROOTFS=$(realpath -e -- "$1")
HOST_ROOT=$(realpath -e /)
[[ "$ROOTFS" != "$HOST_ROOT" ]] || { echo "Recusando modificar a raiz do sistema em execução." >&2; exit 2; }
[[ -f "$ROOTFS/.nivus-live-image-root" ]] || {
  echo "Raiz de imagem sem .nivus-live-image-root; nenhuma alteração foi feita." >&2; exit 2;
}
[[ -r "$ROOTFS/etc/os-release" ]] || { echo "A raiz fornecida não parece conter um Ubuntu instalado." >&2; exit 2; }

ensure_mountpoint() {
  local path="$1" full="$ROOTFS$1"
  if [[ -L "$full" || ( -e "$full" && ! -d "$full" ) ]]; then
    echo "Ponto de montagem incompatível: $path" >&2; exit 2
  fi
  install -d -m 755 "$full"
  if find "$full" -mindepth 1 -print -quit | grep -q .; then
    echo "Ponto de montagem não está vazio: $path" >&2; exit 2
  fi
}

link_persistent() {
  local path="$1" target="$2" full="$ROOTFS$1"
  install -d -m 755 "$(dirname -- "$full")"
  if [[ -L "$full" ]]; then
    [[ "$(readlink -- "$full")" == "$target" ]] || { echo "Link existente aponta a outro destino: $path" >&2; exit 2; }
    return
  fi
  if [[ -e "$full" ]]; then
    [[ -d "$full" ]] || { echo "Caminho existente não é diretório: $path" >&2; exit 2; }
    if find "$full" -mindepth 1 -print -quit | grep -q .; then
      echo "Diretório existente não está vazio: $path; imagem preservada sem mover dados." >&2; exit 2
    fi
    rmdir -- "$full"
  fi
  ln -s -- "$target" "$full"
}

enable_unit() {
  local wants="$1" target="$2" full="$ROOTFS/etc/systemd/system/$wants"
  install -d -m 755 "$(dirname -- "$full")"
  if [[ -L "$full" ]]; then
    [[ "$(readlink -- "$full")" == "$target" ]] || { echo "Ativação systemd conflitante: $wants" >&2; exit 2; }
  elif [[ -e "$full" ]]; then
    echo "Ativação systemd já existe: $wants" >&2; exit 2
  else
    ln -s -- "$target" "$full"
  fi
}

ensure_mountpoint /var/lib/nivus
install -d -m 755 "$ROOTFS/usr/local/libexec" "$ROOTFS/etc/systemd/system"
install -m 755 "$SCRIPT_DIR/nivus-data-volume-guard" "$ROOTFS/usr/local/libexec/nivus-data-volume-guard"
install -m 644 "$SCRIPT_DIR/var-lib-nivus.mount" "$ROOTFS/etc/systemd/system/var-lib-nivus.mount"
install -m 644 "$SCRIPT_DIR/nivus-data-volume-guard.service" "$ROOTFS/etc/systemd/system/nivus-data-volume-guard.service"
install -d -m 755 "$ROOTFS/etc/systemd/system/docker.service.d" "$ROOTFS/etc/systemd/system/nivus-compose-telemetry.service.d"
install -m 644 "$SCRIPT_DIR/docker.service.d/10-nivus-data-volume.conf" "$ROOTFS/etc/systemd/system/docker.service.d/10-nivus-data-volume.conf"
install -m 644 "$SCRIPT_DIR/nivus-compose-telemetry.service.d/10-nivus-data-volume.conf" "$ROOTFS/etc/systemd/system/nivus-compose-telemetry.service.d/10-nivus-data-volume.conf"

link_persistent /var/lib/nivus-compose /var/lib/nivus/compose
link_persistent /etc/nivus-compose /var/lib/nivus/config
link_persistent /opt/nivus-compose /var/lib/nivus/releases
link_persistent /var/lib/docker /var/lib/nivus/docker
enable_unit local-fs.target.wants/var-lib-nivus.mount ../var-lib-nivus.mount
enable_unit multi-user.target.wants/nivus-data-volume-guard.service ../nivus-data-volume-guard.service

printf 'Persistência integrada à imagem staged: %s\n' "$ROOTFS"
printf 'Dados, configuração, releases e Docker usarão /var/lib/nivus após o boot.\n'
printf 'O guard bloqueia Docker e telemetria se NIVUS_DATA não estiver íntegro.\n'
