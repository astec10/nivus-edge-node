#!/usr/bin/env python3
"""Configure a supported Linux USB root and NIVUS_DATA partition."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from deploy.portable_usb.platform_support import describe_supported_platforms, identify_supported_platform, read_os_release


DATA_MOUNT = "/var/lib/nivus"
DATA_LABEL = "NIVUS_DATA"
MARKER_NAME = ".nivus-data-volume"
MARKER_VALUE = "nivus-data-volume-v1"
PERSISTENT_DIRS = ("compose", "config", "releases", "docker")
LINKS = {
    "/var/lib/nivus-compose": "/var/lib/nivus/compose",
    "/etc/nivus-compose": "/var/lib/nivus/config",
    "/opt/nivus-compose": "/var/lib/nivus",
    "/var/lib/docker": "/var/lib/nivus/docker",
}
UNIT_FILES = (
    ("deploy/live-usb/nivus-data-volume-guard", "/usr/local/libexec/nivus-data-volume-guard", 0o755),
    ("deploy/live-usb/var-lib-nivus.mount", "/etc/systemd/system/var-lib-nivus.mount", 0o644),
    ("deploy/live-usb/nivus-data-volume-guard.service", "/etc/systemd/system/nivus-data-volume-guard.service", 0o644),
    ("deploy/live-usb/docker.service.d/10-nivus-data-volume.conf", "/etc/systemd/system/docker.service.d/10-nivus-data-volume.conf", 0o644),
    ("deploy/live-usb/nivus-compose-telemetry.service.d/10-nivus-data-volume.conf", "/etc/systemd/system/nivus-compose-telemetry.service.d/10-nivus-data-volume.conf", 0o644),
)


class RuntimeSetupError(RuntimeError):
    """An unsafe or incomplete precondition for USB runtime setup."""


@dataclass(frozen=True)
class MountRecord:
    source: str
    fstype: str
    target: str
    options: str = ""


@dataclass(frozen=True)
class BlockRecord:
    kind: str
    parent: str
    transport: str


def validate_storage_layout(
    root_mount: MountRecord,
    data_mount: MountRecord,
    fstab_entries: Sequence[MountRecord],
    root_block: BlockRecord,
    data_block: BlockRecord,
    data_label: str,
    label_sources: Sequence[str],
) -> None:
    """Validate that the system root and NIVUS_DATA are persistent partitions on one USB."""
    if root_mount.target != "/" or data_mount.target != DATA_MOUNT:
        raise RuntimeSetupError("os pontos de montagem ativos não correspondem ao layout USB esperado.")
    if root_mount.fstype != "ext4" or data_mount.fstype != "ext4":
        raise RuntimeSetupError("as partições do sistema e NIVUS_DATA precisam usar ext4.")
    if "rw" not in data_mount.options.split(","):
        raise RuntimeSetupError("NIVUS_DATA está montado somente para leitura.")
    if root_mount.source == data_mount.source:
        raise RuntimeSetupError("a raiz do sistema e NIVUS_DATA precisam ser partições separadas.")
    if root_block.kind != "part" or data_block.kind != "part":
        raise RuntimeSetupError("a raiz e NIVUS_DATA precisam estar em partições de bloco.")
    if not root_block.parent or root_block.parent != data_block.parent:
        raise RuntimeSetupError("a raiz e NIVUS_DATA não estão no mesmo dispositivo USB.")
    if root_block.transport.lower() != "usb" or data_block.transport.lower() != "usb":
        raise RuntimeSetupError("o dispositivo que contém o sistema não foi identificado como USB.")
    if data_label != DATA_LABEL:
        raise RuntimeSetupError(f"rótulo esperado {DATA_LABEL}; encontrado {data_label or 'nenhum'}.")
    if list(label_sources) != [data_mount.source]:
        raise RuntimeSetupError("o rótulo NIVUS_DATA não identifica uma única partição correspondente.")

    entries = [entry for entry in fstab_entries if entry.target == DATA_MOUNT]
    if len(entries) != 1:
        raise RuntimeSetupError("o fstab precisa conter exatamente uma entrada para NIVUS_DATA.")
    entry = entries[0]
    if entry.fstype != "ext4" or entry.source != data_mount.source:
        raise RuntimeSetupError("o fstab não monta a partição NIVUS_DATA ativa em ext4.")


def _run(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(list(args), capture_output=True, text=True, check=False)
    except OSError as exc:
        raise RuntimeSetupError(f"não foi possível executar {args[0]}.") from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeSetupError(f"comando {args[0]} falhou{suffix}")
    return result


def _one_line(args: Sequence[str]) -> str:
    output = _run(args).stdout.strip().splitlines()
    if len(output) != 1:
        raise RuntimeSetupError(f"resultado inesperado ao consultar {args[0]}.")
    return output[0].strip()


def _resolve_device(source: str) -> str:
    try:
        path = Path(source).resolve(strict=True)
        if not stat.S_ISBLK(path.stat().st_mode):
            raise RuntimeSetupError(f"a origem {source} não é dispositivo de bloco.")
    except OSError as exc:
        raise RuntimeSetupError(f"a partição {source} não está disponível.") from exc
    return str(path)


def _mount_record(target: str) -> MountRecord:
    line = _one_line(
        ["findmnt", "--noheadings", "--output", "SOURCE,FSTYPE,OPTIONS", "--mountpoint", target]
    )
    fields = line.split()
    if len(fields) != 3:
        raise RuntimeSetupError(f"findmnt não retornou os dados esperados para {target}.")
    source = _resolve_device(fields[0])
    return MountRecord(source, fields[1], target, fields[2])


def _fstab_records() -> list[MountRecord]:
    result = _run(
        ["findmnt", "--fstab", "--evaluate", "--noheadings", "--output", "SOURCE,FSTYPE,TARGET"]
    )
    entries: list[MountRecord] = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        source, fstype, target = fields
        if target == DATA_MOUNT:
            source = _resolve_device(source)
        entries.append(MountRecord(source, fstype, target))
    return entries


def _block_record(source: str) -> BlockRecord:
    kind = _one_line(["lsblk", "--noheadings", "--raw", "--output", "TYPE", source])
    parent_name = _one_line(["lsblk", "--noheadings", "--raw", "--output", "PKNAME", source])
    if not parent_name:
        return BlockRecord(kind, "", "")
    parent_path = f"/dev/{parent_name}"
    transport = _one_line(
        ["lsblk", "--nodeps", "--noheadings", "--raw", "--output", "TRAN", parent_path]
    )
    return BlockRecord(kind, parent_name, transport)


def inspect_storage() -> tuple[MountRecord, MountRecord]:
    if _run(["mountpoint", "--quiet", "/"]).returncode != 0:
        raise RuntimeSetupError("a raiz do sistema não é um ponto de montagem.")
    if _run(["mountpoint", "--quiet", DATA_MOUNT]).returncode != 0:
        raise RuntimeSetupError(f"{DATA_MOUNT} não é uma montagem ativa.")
    root_mount = _mount_record("/")
    data_mount = _mount_record(DATA_MOUNT)
    root_block = _block_record(root_mount.source)
    data_block = _block_record(data_mount.source)
    label = _run(["blkid", "--match-tag", "LABEL", "--output", "value", data_mount.source]).stdout.strip()
    label_result = _run(["blkid", "--match-token", f"LABEL={DATA_LABEL}", "--output", "device"], check=False)
    label_sources = []
    for value in label_result.stdout.splitlines():
        try:
            label_sources.append(_resolve_device(value.strip()))
        except RuntimeSetupError:
            label_sources.append(value.strip())
    validate_storage_layout(
        root_mount,
        data_mount,
        _fstab_records(),
        root_block,
        data_block,
        label,
        label_sources,
    )
    return root_mount, data_mount


def _rooted(root: Path, absolute_path: str) -> Path:
    if not absolute_path.startswith("/") or ".." in Path(absolute_path).parts:
        raise RuntimeSetupError(f"caminho interno inválido: {absolute_path}.")
    return root / absolute_path.lstrip("/")


def _validate_volume_tree(data_root: Path) -> bool:
    """Check the data volume without changing it; return whether a marker is needed."""
    if data_root.is_symlink() or not data_root.is_dir():
        raise RuntimeSetupError("o ponto NIVUS_DATA precisa ser um diretório real.")
    marker = data_root / MARKER_NAME
    if marker.is_symlink():
        raise RuntimeSetupError("o marcador NIVUS_DATA não pode ser um link.")
    if marker.exists():
        if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != MARKER_VALUE:
            raise RuntimeSetupError("marcador NIVUS_DATA desconhecido; volume preservado.")
        needs_marker = False
    else:
        entries = list(data_root.iterdir())
        for entry in entries:
            if entry.name == "lost+found":
                if entry.is_symlink() or not entry.is_dir():
                    raise RuntimeSetupError("lost+found tem tipo inválido; volume preservado.")
                continue
            raise RuntimeSetupError("volume não vazio e sem marcador Nivus; dados preservados.")
        needs_marker = True

    for name in PERSISTENT_DIRS:
        path = data_root / name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise RuntimeSetupError(f"diretório persistente inválido: {name}.")
    return needs_marker


def _validate_link(root: Path, link_path: str, target: str) -> None:
    link = _rooted(root, link_path)
    if link.is_symlink():
        if os.readlink(link) != target:
            raise RuntimeSetupError(f"o link {link_path} já aponta para outro destino.")
    elif link.exists():
        if not link.is_dir():
            raise RuntimeSetupError(f"o caminho {link_path} existe e não é diretório.")
        try:
            next(link.iterdir())
        except StopIteration:
            return
        raise RuntimeSetupError(f"o diretório {link_path} não está vazio; nenhum dado será movido.")


def _source_unit_files(repository_root: Path) -> list[tuple[Path, str, int]]:
    files: list[tuple[Path, str, int]] = []
    for relative, destination, mode in UNIT_FILES:
        source = repository_root / relative
        if source.is_symlink() or not source.is_file():
            raise RuntimeSetupError(f"arquivo de integração ausente ou inválido: {relative}.")
        files.append((source, destination, mode))
    return files


def _validate_unit_destinations(root: Path, files: Sequence[tuple[Path, str, int]]) -> None:
    for source, destination, _mode in files:
        target = _rooted(root, destination)
        if target.is_symlink():
            raise RuntimeSetupError(f"destino de unidade é um link inesperado: {destination}.")
        if target.exists():
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                raise RuntimeSetupError(f"arquivo conflitante em {destination}; nenhum arquivo foi substituído.")


def _initialize_volume(data_root: Path) -> None:
    marker = data_root / MARKER_NAME
    if not marker.exists():
        with marker.open("x", encoding="utf-8") as stream:
            stream.write(MARKER_VALUE + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        marker.chmod(0o644)
    for name in PERSISTENT_DIRS:
        (data_root / name).mkdir(mode=0o755, exist_ok=True)


def _ensure_link(root: Path, link_path: str, target: str) -> None:
    link = _rooted(root, link_path)
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        if os.readlink(link) != target:
            raise RuntimeSetupError(f"o link {link_path} mudou durante a instalação.")
        return
    if link.exists():
        if not link.is_dir():
            raise RuntimeSetupError(f"o caminho {link_path} mudou durante a instalação.")
        try:
            next(link.iterdir())
        except StopIteration:
            link.rmdir()
        else:
            raise RuntimeSetupError(f"o diretório {link_path} deixou de estar vazio.")
    link.symlink_to(target)


def _install_unit_files(root: Path, files: Sequence[tuple[Path, str, int]]) -> None:
    for source, destination, mode in files:
        target = _rooted(root, destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.is_symlink() or not target.is_file() or target.read_bytes() != source.read_bytes():
                raise RuntimeSetupError(f"arquivo conflitante em {destination}.")
            target.chmod(mode)
            continue
        fd, temporary = tempfile.mkstemp(prefix=".nivus-unit-", dir=target.parent)
        temp_path = Path(temporary)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(source.read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            temp_path.chmod(mode)
            os.replace(temp_path, target)
        finally:
            temp_path.unlink(missing_ok=True)


def configure_persistent_paths(repository_root: Path, root: Path = Path("/")) -> None:
    """Initialize a validated, empty NIVUS_DATA volume and install persistent links/units."""
    repository_root = repository_root.resolve(strict=True)
    root = root.resolve(strict=True)
    data_root = _rooted(root, DATA_MOUNT)
    _validate_volume_tree(data_root)
    files = _source_unit_files(repository_root)
    _validate_unit_destinations(root, files)
    for link_path, target in LINKS.items():
        _validate_link(root, link_path, target)

    _initialize_volume(data_root)
    for link_path, target in LINKS.items():
        _ensure_link(root, link_path, target)
    _install_unit_files(root, files)


def _require_fresh_install() -> None:
    current = Path("/opt/nivus-compose/current")
    if current.exists() or current.is_symlink():
        raise RuntimeSetupError("Nivus já está instalado; use o procedimento de atualização.")


def configure_live_system(repository_root: Path) -> None:
    if os.geteuid() != 0:
        raise RuntimeSetupError("execute com sudo.")
    try:
        release = read_os_release()
    except OSError as exc:
        raise RuntimeSetupError("não foi possível identificar a distribuição Linux.") from exc
    supported = identify_supported_platform(release)
    if supported is None:
        raise RuntimeSetupError(
            f"sistemas aceitos: {describe_supported_platforms()} x86_64/amd64."
        )
    if platform.machine() != "x86_64":
        raise RuntimeSetupError("esta etapa suporta somente x86_64/amd64.")
    if shutil.which("systemctl") is None:
        raise RuntimeSetupError("systemd/systemctl é necessário.")
    _require_fresh_install()

    docker_active = _run(["systemctl", "is-active", "--quiet", "docker.service"], check=False)
    if docker_active.returncode == 0:
        raise RuntimeSetupError("Docker já está ativo; interrompendo antes de alterar seus dados.")
    telemetry_active = _run(
        ["systemctl", "is-active", "--quiet", "nivus-compose-telemetry.service"], check=False
    )
    if telemetry_active.returncode == 0:
        raise RuntimeSetupError("o coletor Nivus já está ativo; interrompendo sem alteração.")

    inspect_storage()
    configure_persistent_paths(repository_root)
    _run(["systemctl", "daemon-reload"])
    _run(["systemctl", "enable", "--now", "var-lib-nivus.mount"])
    _run(["systemctl", "enable", "--now", "nivus-data-volume-guard.service"])
    _run(["/usr/local/libexec/nivus-data-volume-guard"])
    print(f"Persistência NIVUS_DATA validada em {supported.display_name}: sistema e dados estão no mesmo USB.")
    print("Integração persistente instalada. Iniciando o instalador Compose do Nivus.")


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Configura os dados persistentes de uma instalação Linux iniciada pelo USB."
    )
    parser.add_argument("--repository-root", type=Path, default=default_root)
    args = parser.parse_args(argv)
    try:
        configure_live_system(args.repository_root)
        return 0
    except (RuntimeSetupError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        print("Nenhum filesystem foi formatado. Corrija a causa e repita; a etapa é reexecutável.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
