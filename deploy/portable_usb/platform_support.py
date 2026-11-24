#!/usr/bin/env python3
"""Supported Linux distributions for the portable Nivus installer."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class SupportedPlatform:
    distro_id: str
    version_id: str
    display_name: str


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        try:
            parts = shlex.split(raw_value, comments=False, posix=True)
        except ValueError:
            continue
        if parts:
            values[key] = parts[0]
    return values


def _version_parts(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except (TypeError, ValueError):
        return ()


def identify_supported_platform(release: Mapping[str, str]) -> SupportedPlatform | None:
    distro_id = release.get("ID", "").lower()
    version_id = release.get("VERSION_ID", "")
    version = _version_parts(version_id)
    codename = release.get("VERSION_CODENAME", "").lower()

    if distro_id == "ubuntu" and version >= (24, 4):
        return SupportedPlatform(distro_id, version_id, f"Ubuntu Server {version_id}+")
    if distro_id == "debian" and version == (13,) and codename in ("", "trixie"):
        return SupportedPlatform(distro_id, version_id, "Debian 13 Trixie")
    return None


def describe_supported_platforms() -> str:
    return "Ubuntu Server 24.04 ou mais recente, ou Debian 13 Trixie"
