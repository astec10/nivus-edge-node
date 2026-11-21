"""Fail-closed AC/UPS governor selection for the Nivus host.

The module intentionally changes only CPUFreq scaling_governor attributes.
It never changes frequency/voltage limits, thermal controls, actuators, or
overclock settings.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


POWER_SUPPLY_ROOT = Path("/sys/class/power_supply")
CPUFREQ_ROOT = Path("/sys/devices/system/cpu/cpufreq")
CONFIG_PATH = Path("/etc/nivus-compose/power-policy.json")
GOVERNOR_RE = re.compile(r"[A-Za-z0-9_-]{1,32}\Z")
NUT_TARGET_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,31}@localhost\Z")


class PowerPolicyError(ValueError):
    """A policy is invalid or cannot be applied safely."""


@dataclass(frozen=True)
class PowerSignal:
    state: str
    source: str
    observed_at: float | None
    reason: str


def _unknown(source: str, reason: str, clock: Callable[[], float]) -> PowerSignal:
    return PowerSignal("unknown", source, clock(), reason)


def read_linux_mains(
    power_supply_root: Path = POWER_SUPPLY_ROOT,
    *,
    clock: Callable[[], float] = time.time,
) -> PowerSignal:
    """Read the Linux power_supply Mains/online values, never battery percent."""
    try:
        entries = sorted(power_supply_root.iterdir(), key=lambda entry: entry.name)
    except OSError:
        return _unknown("linux_mains", "source_unavailable", clock)

    values: list[int] = []
    unreadable_mains = False
    for entry in entries:
        try:
            supply_type = (entry / "type").read_text(encoding="ascii").strip().lower()
        except OSError:
            # A missing type is not enough evidence to infer a power source.
            continue
        if supply_type != "mains":
            continue
        try:
            raw_online = (entry / "online").read_text(encoding="ascii").strip()
        except OSError:
            unreadable_mains = True
            continue
        if raw_online not in {"0", "1"}:
            unreadable_mains = True
            continue
        values.append(int(raw_online))

    if unreadable_mains or not values or len(set(values)) != 1:
        return _unknown("linux_mains", "missing_or_ambiguous_signal", clock)
    return PowerSignal("ac" if values[0] else "battery", "linux_mains", clock(), "fresh_sysfs_read")


def read_nut_status(
    target: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    clock: Callable[[], float] = time.time,
) -> PowerSignal:
    """Read a local NUT UPS status through the read-only upsc client.

    upsd rejects stale driver data; a missing client, timeout, stale reply, or
    unrecognized/contradictory flags all produce an unknown signal.
    """
    if not isinstance(target, str) or not NUT_TARGET_RE.fullmatch(target):
        return _unknown("nut", "invalid_target", clock)
    try:
        result = runner(
            ["/usr/bin/upsc", target, "ups.status"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _unknown("nut", "source_unavailable", clock)
    if result.returncode != 0:
        return _unknown("nut", "source_unavailable_or_stale", clock)

    output = (result.stdout or "").strip()
    if not output or "\n" in output or "\r" in output:
        return _unknown("nut", "invalid_status", clock)
    flags = set(output.split())
    if "OL" in flags and "OB" not in flags:
        return PowerSignal("ac", "nut", clock(), "fresh_ups_status")
    if "OB" in flags and "OL" not in flags:
        return PowerSignal("battery", "nut", clock(), "fresh_ups_status")
    return _unknown("nut", "missing_or_ambiguous_signal", clock)


def load_config(path: Path = CONFIG_PATH, *, require_root_owner: bool = True) -> dict:
    """Load a root-managed policy file with a small, explicit schema."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {"schema_version": 1, "enabled": False}
    except OSError as exc:
        raise PowerPolicyError("policy_config_unavailable") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise PowerPolicyError("policy_config_must_be_regular_file")
    if require_root_owner and (
        metadata.st_uid != 0 or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise PowerPolicyError("policy_config_permissions_invalid")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PowerPolicyError("policy_config_invalid") from exc
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise PowerPolicyError("policy_config_schema_invalid")
    if type(config.get("enabled")) is not bool:
        raise PowerPolicyError("policy_enabled_must_be_boolean")
    if not config["enabled"]:
        governors = config.get("governors")
        if governors is None:
            return config
        if not isinstance(governors, dict):
            raise PowerPolicyError("policy_governors_invalid")
        conservative = governors.get("conservative")
        if not isinstance(conservative, str) or not GOVERNOR_RE.fullmatch(conservative):
            raise PowerPolicyError("governor_name_invalid")
        if conservative.lower() in {"performance", "userspace", "balance_performance"}:
            raise PowerPolicyError("conservative_governor_must_not_force_performance")
        return config

    source = config.get("source")
    governors = config.get("governors")
    if not isinstance(source, dict) or not isinstance(governors, dict):
        raise PowerPolicyError("policy_config_incomplete")
    source_type = source.get("type")
    if source_type == "linux_mains":
        if source.get("feed_topology") not in {"direct_ac", "ups_output"}:
            raise PowerPolicyError("linux_mains_feed_topology_required")
    elif source_type == "nut":
        target = source.get("target")
        if not isinstance(target, str) or not NUT_TARGET_RE.fullmatch(target):
            raise PowerPolicyError("nut_target_must_be_local")
    else:
        raise PowerPolicyError("power_source_type_unsupported")

    for name in ("on_ac", "conservative"):
        governor = governors.get(name)
        if not isinstance(governor, str) or not GOVERNOR_RE.fullmatch(governor):
            raise PowerPolicyError("governor_name_invalid")
    if governors["conservative"].lower() in {"performance", "userspace", "balance_performance"}:
        raise PowerPolicyError("conservative_governor_must_not_force_performance")
    return config


def read_configured_signal(
    config: dict,
    *,
    power_supply_root: Path = POWER_SUPPLY_ROOT,
    nut_runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    clock: Callable[[], float] = time.time,
) -> PowerSignal:
    source = config.get("source", {})
    source_type = source.get("type")
    if source_type == "linux_mains":
        # A host powered from a UPS output cannot infer the UPS's upstream AC.
        if source.get("feed_topology") != "direct_ac":
            return _unknown("linux_mains", "ups_input_not_observable_from_output", clock)
        return read_linux_mains(power_supply_root, clock=clock)
    if source_type == "nut":
        return read_nut_status(source.get("target", ""), runner=nut_runner, clock=clock)
    return _unknown("unknown", "source_not_configured", clock)


def apply_governor(
    governor: str,
    *,
    cpufreq_root: Path = CPUFREQ_ROOT,
) -> int:
    """Preflight every CPUFreq policy, apply one governor, and rollback partial writes."""
    if not isinstance(governor, str) or not GOVERNOR_RE.fullmatch(governor):
        raise PowerPolicyError("governor_name_invalid")
    try:
        policy_paths = sorted(
            (
                path
                for path in cpufreq_root.glob("policy*")
                if re.fullmatch(r"policy[0-9]+", path.name)
                and not path.is_symlink()
                and path.is_dir()
            ),
            key=lambda path: path.name,
        )
    except OSError as exc:
        raise PowerPolicyError("cpufreq_unavailable") from exc
    if not policy_paths:
        raise PowerPolicyError("cpufreq_unavailable")

    plan: list[tuple[Path, str]] = []
    for policy in policy_paths:
        try:
            available = (policy / "scaling_available_governors").read_text(encoding="ascii").split()
            current = (policy / "scaling_governor").read_text(encoding="ascii").strip()
        except OSError as exc:
            raise PowerPolicyError("cpufreq_policy_unreadable") from exc
        if governor not in available:
            raise PowerPolicyError("governor_not_supported_by_all_policies")
        plan.append((policy / "scaling_governor", current))

    changed: list[tuple[Path, str]] = []
    try:
        for governor_path, previous in plan:
            if previous == governor:
                continue
            changed.append((governor_path, previous))
            governor_path.write_text(governor + "\n", encoding="ascii")
            if governor_path.read_text(encoding="ascii").strip() != governor:
                raise PowerPolicyError("governor_readback_mismatch")
    except (OSError, PowerPolicyError) as exc:
        for governor_path, previous in reversed(changed):
            try:
                governor_path.write_text(previous + "\n", encoding="ascii")
            except OSError:
                pass
        if isinstance(exc, PowerPolicyError):
            raise
        raise PowerPolicyError("governor_write_failed") from exc
    return len(changed)


def governor_supported(governor: str, *, cpufreq_root: Path = CPUFREQ_ROOT) -> bool:
    """Return whether every online CPUFreq policy lists this governor."""
    if not isinstance(governor, str) or not GOVERNOR_RE.fullmatch(governor):
        raise PowerPolicyError("governor_name_invalid")
    try:
        policies = sorted(
            (
                path
                for path in cpufreq_root.glob("policy*")
                if re.fullmatch(r"policy[0-9]+", path.name)
                and not path.is_symlink()
                and path.is_dir()
            ),
            key=lambda path: path.name,
        )
    except OSError as exc:
        raise PowerPolicyError("cpufreq_unavailable") from exc
    if not policies:
        raise PowerPolicyError("cpufreq_unavailable")
    for policy in policies:
        try:
            available = (policy / "scaling_available_governors").read_text(encoding="ascii").split()
        except OSError as exc:
            raise PowerPolicyError("cpufreq_policy_unreadable") from exc
        if governor not in available:
            return False
    return True


def apply_policy(
    config: dict,
    *,
    power_supply_root: Path = POWER_SUPPLY_ROOT,
    cpufreq_root: Path = CPUFREQ_ROOT,
    nut_runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    clock: Callable[[], float] = time.time,
) -> dict:
    if not config.get("enabled", False):
        governors = config.get("governors", {})
        if not isinstance(governors, dict):
            raise PowerPolicyError("policy_governors_invalid")
        conservative = governors.get("conservative")
        if not isinstance(conservative, str):
            return {"status": "disabled", "signal": "unknown", "governor": None, "changed": 0}
        if not governor_supported(conservative, cpufreq_root=cpufreq_root):
            raise PowerPolicyError("conservative_governor_not_supported_by_all_policies")
        changed = apply_governor(conservative, cpufreq_root=cpufreq_root)
        return {
            "status": "disabled",
            "signal": "unknown",
            "governor": conservative,
            "changed": changed,
            "reason": "policy_disabled_conservative_restored",
        }
    signal = read_configured_signal(
        config,
        power_supply_root=power_supply_root,
        nut_runner=nut_runner,
        clock=clock,
    )
    governors = config["governors"]
    conservative = governors["conservative"]
    if not governor_supported(conservative, cpufreq_root=cpufreq_root):
        raise PowerPolicyError("conservative_governor_not_supported_by_all_policies")
    governor = conservative
    if signal.state == "ac" and governor_supported(governors["on_ac"], cpufreq_root=cpufreq_root):
        governor = governors["on_ac"]
    elif signal.state == "ac":
        signal = PowerSignal("unknown", signal.source, signal.observed_at, "on_ac_governor_unsupported")
    changed = apply_governor(governor, cpufreq_root=cpufreq_root)
    return {
        "status": "applied",
        "signal": signal.state,
        "source": signal.source,
        "governor": governor,
        "changed": changed,
        "reason": signal.reason,
    }
