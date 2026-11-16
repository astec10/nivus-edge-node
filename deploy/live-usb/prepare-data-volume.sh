#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0 /dev/particao" >&2
  exit 1
fi
DEVICE_INPUT="${1:-}"
[[ -n "$DEVICE_INPUT" && -b "$DEVICE_INPUT" ]] || { echo "Informe uma partição de bloco existente." >&2; exit 2; }
DEVICE=$(readlink -f -- "$DEVICE_INPUT")
[[ "$(lsblk -dnro TYPE -- "$DEVICE")" == "part" ]] || { echo "O alvo precisa ser uma partição, não um disco inteiro ou arquivo." >&2; exit 2; }
FSTYPE=$(blkid -s TYPE -o value "$DEVICE" 2>/dev/null || true)
LABEL=$(blkid -s LABEL -o value "$DEVICE" 2>/dev/null || true)
[[ "$FSTYPE" == "ext4" ]] || { echo "A partição precisa já estar formatada como ext4; nenhuma formatação foi feita." >&2; exit 2; }
[[ "$LABEL" == "NIVUS_DATA" ]] || { echo "O rótulo ext4 precisa ser NIVUS_DATA; nenhum rótulo foi alterado." >&2; exit 2; }
[[ -z "$(lsblk -dnro MOUNTPOINT -- "$DEVICE")" ]] || { echo "A partição já está montada; desmonte-a antes de preparar." >&2; exit 2; }

MOUNT_DIR=$(mktemp -d)
MOUNTED=0
cleanup() {
  rc=$?
  trap - EXIT
  if [[ $MOUNTED -eq 1 ]]; then umount -- "$MOUNT_DIR" || rc=1; fi
  rmdir -- "$MOUNT_DIR" 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT
mount -t ext4 -o rw,noatime -- "$DEVICE" "$MOUNT_DIR"
MOUNTED=1
MARKER="$MOUNT_DIR/.nivus-data-volume"
if [[ -e "$MARKER" || -L "$MARKER" ]]; then
  [[ -f "$MARKER" && ! -L "$MARKER" && "$(cat -- "$MARKER")" == "nivus-data-volume-v1" ]] || {
    echo "Marcador existente não reconhecido; volume preservado sem alterações." >&2; exit 2;
  }
else
  CONTENT=$(find "$MOUNT_DIR" -mindepth 1 -maxdepth 1 ! -name lost+found -print -quit)
  [[ -z "$CONTENT" ]] || { echo "Partição não vazia e sem marcador Nivus; recusando adoção de dados existentes." >&2; exit 2; }
  printf '%s\n' 'nivus-data-volume-v1' > "$MARKER.tmp"
  chmod 644 "$MARKER.tmp"
  mv -- "$MARKER.tmp" "$MARKER"
fi

install -d -m 755 "$MOUNT_DIR/compose" "$MOUNT_DIR/config" "$MOUNT_DIR/releases" "$MOUNT_DIR/docker"
sync
echo "Volume NIVUS_DATA preparado em ext4. Nenhum dado foi apagado e nenhuma formatação foi feita."
