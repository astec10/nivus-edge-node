#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || { echo "Este teste precisa de root num runner descartável." >&2; exit 2; }
for command in losetup sfdisk mkfs.ext4 mount umount lsblk blkid findmnt; do
  command -v "$command" >/dev/null || { echo "Comando necessário ausente: $command" >&2; exit 2; }
done
REPO_ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
TMP=$(mktemp -d)
LOOP=
MOUNTED=0
cleanup() {
  rc=$?
  trap - EXIT
  if [[ $MOUNTED -eq 1 ]]; then umount -- "$TMP/mnt" || rc=1; fi
  if [[ -n "$LOOP" ]]; then losetup -d "$LOOP" || rc=1; fi
  rm -rf -- "$TMP"
  exit "$rc"
}
trap cleanup EXIT

truncate -s 96M "$TMP/live-data.img"
printf 'label: dos\nunit: sectors\n\nstart=2048,size=180000,type=83\n' | sfdisk "$TMP/live-data.img" >/dev/null
LOOP=$(losetup --find --show --partscan "$TMP/live-data.img")
PARTITION="${LOOP}p1"
for attempt in {1..20}; do [[ -b "$PARTITION" ]] && break; sleep 0.1; done
[[ -b "$PARTITION" ]] || { echo "Partição loop não apareceu." >&2; exit 1; }
mkfs.ext4 -F -q -L NIVUS_DATA "$PARTITION"

bash "$REPO_ROOT/deploy/live-usb/prepare-data-volume.sh" "$PARTITION"
mkdir "$TMP/mnt"
mount -t ext4 -o noatime "$PARTITION" "$TMP/mnt"
MOUNTED=1
bash "$REPO_ROOT/deploy/live-usb/nivus-data-volume-guard" "$TMP/mnt"
printf '%s\n' 'marker-inválido' > "$TMP/mnt/.nivus-data-volume"
if bash "$REPO_ROOT/deploy/live-usb/nivus-data-volume-guard" "$TMP/mnt"; then
  echo "O guard aceitou marcador inválido." >&2; exit 1
fi
printf '%s\n' 'nivus-data-volume-v1' > "$TMP/mnt/.nivus-data-volume"
umount "$TMP/mnt"
MOUNTED=0
if bash "$REPO_ROOT/deploy/live-usb/nivus-data-volume-guard" "$TMP/mnt"; then
  echo "O guard aceitou volume desmontado." >&2; exit 1
fi

ROOTFS="$TMP/rootfs"
mkdir -p "$ROOTFS/etc" "$ROOTFS/var/lib/docker"
printf '%s\n' 'ID=ubuntu' > "$ROOTFS/etc/os-release"
touch "$ROOTFS/.nivus-live-image-root"
bash "$REPO_ROOT/deploy/live-usb/install-image-integration.sh" "$ROOTFS"
[[ "$(readlink "$ROOTFS/var/lib/nivus-compose")" == "/var/lib/nivus/compose" ]]
[[ "$(readlink "$ROOTFS/etc/nivus-compose")" == "/var/lib/nivus/config" ]]
[[ "$(readlink "$ROOTFS/opt/nivus-compose")" == "/var/lib/nivus" ]]
[[ "$(readlink "$ROOTFS/var/lib/docker")" == "/var/lib/nivus/docker" ]]
[[ -x "$ROOTFS/usr/local/libexec/nivus-data-volume-guard" ]]
[[ -L "$ROOTFS/etc/systemd/system/local-fs.target.wants/var-lib-nivus.mount" ]]
[[ -L "$ROOTFS/etc/systemd/system/multi-user.target.wants/nivus-data-volume-guard.service" ]]

BAD_ROOTFS="$TMP/unmarked-rootfs"
mkdir -p "$BAD_ROOTFS/etc"
printf '%s\n' 'ID=ubuntu' > "$BAD_ROOTFS/etc/os-release"
if bash "$REPO_ROOT/deploy/live-usb/install-image-integration.sh" "$BAD_ROOTFS"; then
  echo "Integração aceitou uma raiz de imagem sem sentinel." >&2; exit 1
fi

echo "Live USB persistence checks passed."
