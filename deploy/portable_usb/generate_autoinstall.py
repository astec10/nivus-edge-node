#!/usr/bin/env python3
"""Generate a human-reviewed Subiquity seed for a persistent Nivus USB install.

The generated seed never writes to a block device. Subiquity shows the storage
screen and requires an operator to review and confirm the selected target.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from .select_target import (
        InspectionError,
        _identity_digest,
        _read_inventory,
        _root_backing_paths,
        eligible_usb_disks,
        select_candidate,
    )
except ImportError:  # Direct invocation from deploy/portable_usb.
    from select_target import (  # type: ignore[no-redef]
        InspectionError,
        _identity_digest,
        _read_inventory,
        _root_backing_paths,
        eligible_usb_disks,
        select_candidate,
    )


MINIMUM_DISK_BYTES = 40 * 1024**3
ROOT_PARTITION_SIZE = "24G"
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
HOSTNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class GenerationError(RuntimeError):
    pass


def validate_selection(
    record: Any,
    inventory: dict[str, Any],
    protected_paths: set[str] | None = None,
    minimum_disk_bytes: int = MINIMUM_DISK_BYTES,
) -> dict[str, Any]:
    """Verify an earlier selection against the current live block inventory."""
    if not isinstance(record, dict):
        raise GenerationError("o manifesto de seleção não é um objeto JSON.")
    if record.get("schema") != "nivus-portable-usb-selection-v1":
        raise GenerationError("versão de manifesto não reconhecida.")
    device = record.get("device")
    if not isinstance(device, dict):
        raise GenerationError("o manifesto não contém a identidade do dispositivo.")
    try:
        digest = _identity_digest(device)
    except (KeyError, TypeError, ValueError) as exc:
        raise GenerationError("a identidade do USB está incompleta.") from exc
    if record.get("identity_sha256") != digest:
        raise GenerationError("o manifesto foi alterado ou está corrompido.")

    required = ("path", "model", "serial", "size_bytes", "transport")
    if any(not isinstance(device.get(key), str) or not device[key] for key in required if key != "size_bytes"):
        raise GenerationError("o manifesto não contém todos os campos da identidade USB.")
    try:
        size_bytes = int(device["size_bytes"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GenerationError("capacidade inválida no manifesto.") from exc
    if device.get("transport") != "usb" or not device["path"].startswith("/dev/"):
        raise GenerationError("o manifesto não aponta para um disco USB.")
    if size_bytes < minimum_disk_bytes:
        minimum_gib = minimum_disk_bytes / (1024**3)
        raise GenerationError(
            f"o USB tem menos de {minimum_gib:.0f} GiB; use um disco com capacidade adequada."
        )

    candidates = eligible_usb_disks(inventory, protected_paths)
    try:
        current = select_candidate(candidates, device["serial"])
    except InspectionError as exc:
        raise GenerationError(
            "o serial escolhido não é único e elegível no inventário atual."
        ) from exc
    if current != device:
        raise GenerationError(
            "a identidade do USB mudou desde a seleção; gere novamente o manifesto."
        )
    return current


def load_and_revalidate_selection(path: Path) -> dict[str, Any]:
    """Load a selection manifest and compare it with the live Ubuntu host."""
    if path.is_symlink() or not path.is_file():
        raise GenerationError("o manifesto não existe ou não é um arquivo regular.")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GenerationError("não foi possível ler o manifesto JSON.") from exc
    try:
        inventory = _read_inventory()
        protected = _root_backing_paths()
    except InspectionError as exc:
        raise GenerationError("não foi possível revalidar os discos do computador.") from exc
    return validate_selection(record, inventory, protected)


def validate_account(username: str, hostname: str) -> None:
    if not USERNAME_RE.fullmatch(username):
        raise GenerationError(
            "usuário inválido; use até 32 letras minúsculas, números, '_' ou '-', começando com letra ou '_'."
        )
    if not HOSTNAME_RE.fullmatch(hostname):
        raise GenerationError("hostname inválido; use letras minúsculas, números e hífens.")


def hash_password(password: str) -> str:
    """Hash a password via OpenSSL stdin; never put it in argv or logs."""
    if len(password) < 12:
        raise GenerationError("a senha do Ubuntu precisa ter pelo menos 12 caracteres.")
    if "\x00" in password or "\n" in password or "\r" in password:
        raise GenerationError("a senha contém um caractere não permitido.")
    openssl = shutil.which("openssl")
    if not openssl:
        raise GenerationError("OpenSSL não foi encontrado; instale-o antes de gerar a configuração.")
    try:
        result = subprocess.run(
            [openssl, "passwd", "-6", "-stdin"],
            input=password + "\n",
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GenerationError("não foi possível gerar o hash da senha com OpenSSL.") from exc
    hashed = result.stdout.strip()
    if not hashed.startswith("$6$") or "\n" in hashed or "\r" in hashed:
        raise GenerationError("OpenSSL retornou um hash de senha inesperado.")
    return hashed


def early_validation_code() -> str:
    """Return a self-contained check executed by Subiquity before storage setup."""
    return """import json, subprocess, sys
expected_path, expected_model, expected_serial, expected_size = sys.argv[1:5]
def fail(message):
    print("Nivus USB target check: " + message, file=sys.stderr)
    raise SystemExit(2)
try:
    result = subprocess.run(
        ["lsblk", "--json", "--bytes", "--paths", "--output",
         "PATH,NAME,TYPE,SIZE,MODEL,SERIAL,TRAN,RO,MOUNTPOINTS"],
        check=True, capture_output=True, text=True)
    inventory = json.loads(result.stdout)
except Exception:
    fail("não foi possível ler um inventário válido de discos.")
devices = inventory.get("blockdevices")
if not isinstance(devices, list):
    fail("inventário sem blockdevices.")
disks = [item for item in devices if str(item.get("type", "")).lower() == "disk"]
matches = [item for item in disks if str(item.get("serial") or "").strip() == expected_serial]
if len(matches) != 1:
    fail("o serial esperado não identifica exatamente um disco.")
disk = matches[0]
if str(disk.get("path") or "").strip() != expected_path:
    fail("o caminho do disco mudou desde a seleção.")
if str(disk.get("model") or "").strip() != expected_model:
    fail("o modelo do disco mudou desde a seleção.")
try:
    if int(disk.get("size") or 0) != int(expected_size):
        fail("a capacidade do disco mudou desde a seleção.")
except (TypeError, ValueError):
    fail("a capacidade do disco é inválida.")
if str(disk.get("tran") or "").strip().lower() != "usb":
    fail("o dispositivo esperado não é identificado como USB.")
if str(disk.get("ro", 0)).strip().lower() in {"1", "true", "yes"}:
    fail("o USB está em modo somente leitura.")
def has_mount(node):
    mounts = node.get("mountpoints")
    if mounts is not None:
        values = mounts if isinstance(mounts, list) else [mounts]
        if any(value not in (None, "") for value in values):
            return True
    children = node.get("children")
    return isinstance(children, list) and any(has_mount(child) for child in children)
if has_mount(disk):
    fail("há uma partição deste USB montada; instalação cancelada.")
print("Nivus USB target identity revalidated.")
"""


def build_autoinstall_user_data(
    device: dict[str, Any],
    username: str,
    hostname: str,
    password_hash: str,
) -> str:
    """Build cloud-config user-data as JSON, which is valid YAML 1.2."""
    validate_account(username, hostname)
    if not isinstance(password_hash, str) or not password_hash.startswith("$6$"):
        raise GenerationError("a senha precisa estar armazenada como hash SHA-512-crypt.")
    if any(char in password_hash for char in "\x00\n\r"):
        raise GenerationError("o hash de senha contém caracteres inválidos.")
    if int(device.get("size_bytes") or 0) < MINIMUM_DISK_BYTES:
        raise GenerationError("USB abaixo da capacidade mínima suportada.")

    storage_config = [
        {
            "type": "disk",
            "id": "nivus-usb",
            "serial": device["serial"],
            "model": device["model"],
            "ptable": "gpt",
            "wipe": "superblock",
            "grub_device": True,
        },
        {
            "type": "partition",
            "id": "bios-boot",
            "device": "nivus-usb",
            "size": "1M",
            "flag": "bios_grub",
        },
        {
            "type": "partition",
            "id": "efi-partition",
            "device": "nivus-usb",
            "size": "1G",
            "flag": "boot",
        },
        {
            "type": "format",
            "id": "efi-format",
            "volume": "efi-partition",
            "fstype": "fat32",
            "label": "NIVUS_EFI",
        },
        {
            "type": "mount",
            "id": "efi-mount",
            "device": "efi-format",
            "path": "/boot/efi",
        },
        {
            "type": "partition",
            "id": "root-partition",
            "device": "nivus-usb",
            "size": ROOT_PARTITION_SIZE,
        },
        {
            "type": "format",
            "id": "root-format",
            "volume": "root-partition",
            "fstype": "ext4",
            "label": "NIVUS_ROOT",
        },
        {
            "type": "mount",
            "id": "root-mount",
            "device": "root-format",
            "path": "/",
        },
        {
            "type": "partition",
            "id": "nivus-data-partition",
            "device": "nivus-usb",
            "size": -1,
        },
        {
            "type": "format",
            "id": "nivus-data-format",
            "volume": "nivus-data-partition",
            "fstype": "ext4",
            "label": "NIVUS_DATA",
        },
        {
            "type": "mount",
            "id": "nivus-data-mount",
            "device": "nivus-data-format",
            "path": "/var/lib/nivus",
        },
    ]
    check = [
        "python3",
        "-c",
        early_validation_code(),
        device["path"],
        device["model"],
        device["serial"],
        str(device["size_bytes"]),
    ]
    config = {
        "autoinstall": {
            "version": 1,
            "interactive-sections": ["storage"],
            "early-commands": [check],
            "identity": {
                "hostname": hostname,
                "username": username,
                "password": password_hash,
            },
            "storage": {"config": storage_config},
        }
    }
    schema_doc = "https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html"
    return "#cloud-config\n# Subiquity schema reference: " + schema_doc + "\n" + json.dumps(config, ensure_ascii=False, indent=2) + "\n"


def _write_new_file(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def write_seed(output: Path, user_data: str, device: dict[str, Any]) -> None:
    """Create a private NoCloud seed directory without overwriting any files."""
    output = output.expanduser()
    if output.exists() or output.is_symlink():
        raise GenerationError("a pasta de saída já existe; nenhum arquivo foi sobrescrito.")
    parent = output.parent.resolve()
    if not parent.is_dir():
        raise GenerationError("a pasta pai da saída não existe.")
    created: list[Path] = []
    try:
        output.mkdir(mode=0o700)
        created.append(output)
        instance_id = "nivus-usb-" + hashlib.sha256(device["serial"].encode("utf-8")).hexdigest()[:12]
        meta_data = f"instance-id: {instance_id}\nlocal-hostname: nivus-installer\n"
        identity_text = (
            "Alvo selecionado para instalação Ubuntu + Nivus\n"
            f"Caminho: {device['path']}\n"
            f"Modelo: {device['model']}\n"
            f"Serial: {device['serial']}\n"
            f"Capacidade: {int(device['size_bytes'])} bytes\n"
            "AVISO: a instalação apaga as partições e dados do USB selecionado.\n"
            "A tela de armazenamento do Subiquity deve ser revisada manualmente.\n"
        )
        files = {
            "user-data": user_data,
            "meta-data": meta_data,
            "TARGET-IDENTITY.txt": identity_text,
        }
        for filename, content in files.items():
            target = output / filename
            _write_new_file(target, content)
            created.append(target)
        sums = "".join(
            f"{hashlib.sha256((output / filename).read_bytes()).hexdigest()}  {filename}\n"
            for filename in ("user-data", "meta-data", "TARGET-IDENTITY.txt")
        )
        sums_path = output / "SHA256SUMS"
        _write_new_file(sums_path, sums)
        created.append(sums_path)
    except Exception:
        for path in reversed(created):
            try:
                if path.is_dir() and not path.is_symlink():
                    path.rmdir()
                else:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
        raise



def build_seed_iso(seed_dir: Path) -> Path:
    """Build a private NoCloud ISO; this is config media, not a bootable Ubuntu ISO."""
    seed_dir = seed_dir.expanduser()
    if seed_dir.is_symlink() or not seed_dir.is_dir():
        raise GenerationError("a pasta do seed não existe ou não é um diretório seguro.")
    cloud_localds = shutil.which("cloud-localds")
    if not cloud_localds:
        raise GenerationError(
            "cloud-localds não foi encontrado; instale cloud-image-utils e tente novamente."
        )
    user_data = seed_dir / "user-data"
    meta_data = seed_dir / "meta-data"
    if any(path.is_symlink() or not path.is_file() for path in (user_data, meta_data)):
        raise GenerationError("os arquivos user-data/meta-data do seed não estão disponíveis.")
    output = seed_dir / "nivus-autoinstall-seed.iso"
    checksum = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or output.is_symlink() or checksum.exists() or checksum.is_symlink():
        raise GenerationError("a ISO ou checksum já existe; nenhum arquivo foi sobrescrito.")

    try:
        with tempfile.TemporaryDirectory(prefix=".nivus-seed-iso-", dir=seed_dir) as temp_dir:
            temporary_iso = Path(temp_dir) / output.name
            subprocess.run(
                [
                    cloud_localds,
                    "--filesystem=iso",
                    str(temporary_iso),
                    str(user_data),
                    str(meta_data),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            if not temporary_iso.is_file() or temporary_iso.stat().st_size == 0:
                raise GenerationError("cloud-localds não produziu uma ISO de seed válida.")
            os.chmod(temporary_iso, 0o600)
            os.link(temporary_iso, output)
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            _write_new_file(checksum, f"{digest}  {output.name}\n")
    except FileExistsError as exc:
        raise GenerationError("a ISO ou checksum já existe; nenhum arquivo foi sobrescrito.") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GenerationError("não foi possível criar a ISO NoCloud do seed.") from exc
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera uma configuração revisável do instalador; não grava em discos."
    )
    parser.add_argument("--selection", required=True, type=Path, help="manifesto criado pelo select_target.py")
    parser.add_argument("--output", required=True, type=Path, help="nova pasta para os arquivos NoCloud")
    parser.add_argument("--build-seed-iso", action="store_true", help="cria ISO NoCloud privada; requer cloud-localds")
    args = parser.parse_args(argv)

    try:
        if args.build_seed_iso and not shutil.which("cloud-localds"):
            raise GenerationError("cloud-localds não foi encontrado; instale cloud-image-utils.")
        device = load_and_revalidate_selection(args.selection)
        print(
            f"USB revalidado: {device['path']} | {device['model']} | "
            f"serial {device['serial']} | {int(device['size_bytes']) / (1024**3):.1f} GiB"
        )
        username = input("Usuário inicial do Ubuntu [nivus]: ").strip() or "nivus"
        hostname = input("Hostname [nivus-node]: ").strip() or "nivus-node"
        validate_account(username, hostname)
        password = getpass.getpass("Senha inicial do Ubuntu (mínimo 12 caracteres): ")
        confirmation = getpass.getpass("Confirme a senha: ")
        if password != confirmation:
            raise GenerationError("as senhas não coincidem.")
        password_hash = hash_password(password)
        del password, confirmation
        user_data = build_autoinstall_user_data(device, username, hostname, password_hash)
        del password_hash
        write_seed(args.output, user_data, device)
        print(f"Seed privado criado em {args.output.expanduser()}. Nenhum disco foi alterado.")
        if args.build_seed_iso:
            iso_path = build_seed_iso(args.output.expanduser())
            print(f"ISO de configuração criada: {iso_path}")
            print("A ISO é um seed NoCloud, não uma mídia inicializável do Ubuntu.")
        print("O instalador revalidará o USB e abrirá a tela de armazenamento para confirmação humana.")
        return 0
    except (GenerationError, InspectionError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
