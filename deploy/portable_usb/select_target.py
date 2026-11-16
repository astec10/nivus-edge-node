#!/usr/bin/env python3
"""Inspect and explicitly select a USB disk without changing its contents.

This is a discovery step only. It never partitions, formats, mounts, unmounts,
or writes to the selected block device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class InspectionError(RuntimeError):
    pass


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _mountpoints(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [str(item) for item in values if item not in (None, "")]


def _walk(devices: list[dict[str, Any]]):
    for device in devices:
        yield device
        children = device.get("children")
        if isinstance(children, list):
            yield from _walk(children)


def _has_mounted_child(device: dict[str, Any]) -> bool:
    return any(_mountpoints(item.get("mountpoints")) for item in _walk([device]))


def _is_read_only(device: dict[str, Any]) -> bool:
    value = device.get("ro", 0)
    return str(value).strip().lower() in {"1", "true", "yes"}


def _has_control_chars(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def _canonical_device_path(path: str) -> str:
    return os.path.realpath(path)


def eligible_usb_disks(
    inventory: dict[str, Any], protected_paths: set[str] | None = None
) -> list[dict[str, Any]]:
    """Return USB whole disks with unique serials and no mounted filesystems."""
    devices = inventory.get("blockdevices")
    if not isinstance(devices, list):
        raise InspectionError("a saída do lsblk não contém blockdevices.")

    all_devices = list(_walk(devices))
    serial_counts: dict[str, int] = {}
    for item in all_devices:
        if _text(item.get("type")).lower() == "disk":
            serial = _text(item.get("serial"))
            if serial:
                serial_counts[serial] = serial_counts.get(serial, 0) + 1

    protected = {
        _canonical_device_path(path)
        for path in (protected_paths or set())
        if _text(path)
    }
    candidates: list[dict[str, Any]] = []
    for disk in devices:
        if _text(disk.get("type")).lower() != "disk":
            continue
        path = _text(disk.get("path"))
        serial = _text(disk.get("serial"))
        model = _text(disk.get("model"))
        transport = _text(disk.get("tran")).lower()
        try:
            size_bytes = int(disk.get("size") or 0)
        except (TypeError, ValueError):
            continue

        if not path.startswith("/dev/") or not serial or not model:
            continue
        if _has_control_chars(path) or _has_control_chars(serial) or _has_control_chars(model):
            continue
        if transport != "usb" or size_bytes <= 0 or _is_read_only(disk):
            continue
        if serial_counts.get(serial, 0) != 1:
            continue
        if _canonical_device_path(path) in protected:
            continue
        if _has_mounted_child(disk):
            continue

        candidates.append(
            {
                "path": path,
                "name": _text(disk.get("name")),
                "model": model,
                "serial": serial,
                "size_bytes": size_bytes,
                "transport": transport,
            }
        )

    # Stable display order only; selection is always by the exact serial supplied
    # by the operator. Device size is never used to choose a disk.
    return sorted(candidates, key=lambda item: (item["path"], item["serial"]))


def select_candidate(
    candidates: list[dict[str, Any]], serial: str
) -> dict[str, Any]:
    matches = [item for item in candidates if item["serial"] == serial]
    if len(matches) != 1:
        raise InspectionError(
            "o número de série informado não corresponde a exatamente um USB elegível."
        )
    return matches[0]


def _root_backing_paths() -> set[str]:
    """Resolve the current root filesystem to its block-device dependency chain."""
    try:
        source_result = subprocess.run(
            ["findmnt", "--noheadings", "--raw", "--output", "SOURCE", "--target", "/"],
            check=True,
            capture_output=True,
            text=True,
        )
        source = source_result.stdout.strip().splitlines()[0]
    except (subprocess.CalledProcessError, IndexError, FileNotFoundError) as exc:
        raise InspectionError("não foi possível identificar a origem de /.") from exc

    # Overlay roots used by installer environments have no direct /dev source.
    # Mounted partitions (including installer media mounted at /cdrom) are still
    # excluded below; the selection helper performs no block-device writes.
    if not source.startswith("/dev/"):
        return set()
    source = source.split("[", 1)[0]
    try:
        result = subprocess.run(
            [
                "lsblk",
                "--inverse",
                "--noheadings",
                "--raw",
                "--paths",
                "--output",
                "PATH",
                source,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise InspectionError("não foi possível mapear os dispositivos que contêm /.") from exc
    paths = {line.strip() for line in result.stdout.splitlines() if line.strip().startswith("/dev/")}
    if not paths:
        raise InspectionError("o disco que contém / não pôde ser mapeado.")
    return {_canonical_device_path(path) for path in paths}


def _read_inventory() -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "lsblk",
                "--json",
                "--bytes",
                "--paths",
                "--output",
                "PATH,NAME,TYPE,SIZE,MODEL,SERIAL,TRAN,RO,MOUNTPOINTS",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        inventory = json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as exc:
        raise InspectionError("não foi possível obter inventário válido do lsblk.") from exc
    if not isinstance(inventory, dict):
        raise InspectionError("inventário de discos inválido.")
    return inventory


def _safe_display(value: str) -> str:
    return "".join(char if ord(char) >= 32 and ord(char) != 127 else "?" for char in value)


def _format_size(size_bytes: int) -> str:
    gib = size_bytes / (1024**3)
    return f"{gib:.1f} GiB"


def _identity_digest(device: dict[str, Any]) -> str:
    identity = {
        "model": device["model"],
        "path": device["path"],
        "serial": device["serial"],
        "size_bytes": device["size_bytes"],
        "transport": device["transport"],
    }
    payload = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_selection(output: Path, device: dict[str, Any]) -> None:
    if not output.parent.is_dir():
        raise InspectionError("a pasta de destino do manifesto não existe.")
    record = {
        "schema": "nivus-portable-usb-selection-v1",
        "selected_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "device": device,
        "identity_sha256": _identity_digest(device),
        "note": "Selection only; this file does not authorize partitioning or formatting.",
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(output), flags, 0o600)
    except FileExistsError as exc:
        raise InspectionError("o manifesto já existe; nenhum arquivo foi sobrescrito.") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            output.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _print_candidates(candidates: list[dict[str, Any]]) -> None:
    print("Discos USB elegíveis para seleção (nenhum disco será alterado):")
    if not candidates:
        print("Nenhum disco passou pelos critérios de segurança.")
        return
    for item in candidates:
        print(
            f"- {item['path']} | modelo: {_safe_display(item['model'])} | "
            f"série: {_safe_display(item['serial'])} | "
            f"capacidade: {_format_size(item['size_bytes'])}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lista e seleciona um USB por número de série; não particiona nem formata."
    )
    parser.add_argument(
        "--serial",
        help="número de série exato do USB que você escolheu; sem isso, apenas lista.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="arquivo novo para registrar a seleção; obrigatório junto com --serial.",
    )
    args = parser.parse_args(argv)
    if bool(args.serial) != bool(args.output):
        parser.error("--serial e --output devem ser usados juntos.")

    try:
        inventory = _read_inventory()
        protected_paths = _root_backing_paths()
        candidates = eligible_usb_disks(inventory, protected_paths)
        _print_candidates(candidates)
        if not args.serial:
            return 0

        selected = select_candidate(candidates, args.serial)
        print(
            "\nAlvo escolhido: "
            f"{selected['path']} | {_safe_display(selected['model'])} | "
            f"série {_safe_display(selected['serial'])} | "
            f"{_format_size(selected['size_bytes'])}"
        )
        print("Esta etapa não particiona, formata, monta ou altera o dispositivo.")
        typed_serial = input("Digite o número de série exato para registrar a seleção: ")
        if typed_serial != selected["serial"]:
            raise InspectionError("confirmação diferente; seleção cancelada.")
        _write_selection(args.output, selected)
        print(f"Seleção registrada em {args.output}; o dispositivo não foi alterado.")
        print("O instalador futuro terá de revalidar a identidade antes de qualquer escrita.")
        return 0
    except (InspectionError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
