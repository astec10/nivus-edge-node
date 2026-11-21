"""Bounded standard-library telemetry collection for Linux Nivus nodes."""

from __future__ import annotations

import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

TELEMETRY_SCHEMA_VERSION = 1
TELEMETRY_CAPABILITIES = (
    "telemetry.cpu",
    "telemetry.memory",
    "telemetry.disk",
)


def _unavailable(metric: str, unit: str) -> dict:
    return {"metric": metric, "value": None, "unit": unit, "quality": "unavailable"}


def _measured(metric: str, value: float, unit: str) -> dict:
    return {"metric": metric, "value": round(float(value), 2), "unit": unit, "quality": "measured"}


def _cpu_counters(line: str) -> tuple[int, int] | None:
    fields = line.split()
    if not fields or fields[0] != "cpu" or len(fields) < 5:
        return None
    try:
        counters = [int(item) for item in fields[1:9]]
    except ValueError:
        return None
    if len(counters) < 4 or any(value < 0 for value in counters):
        return None
    total = sum(counters)
    idle = counters[3] + (counters[4] if len(counters) > 4 else 0)
    return (total, idle) if total >= idle else None


class NodeTelemetryCollector:
    """Collect CPU, memory, and root filesystem usage without third-party packages."""

    def __init__(
        self,
        proc_root: Path = Path("/proc"),
        disk_path: str = "/",
        disk_usage: Callable = shutil.disk_usage,
    ):
        self.proc_root = Path(proc_root)
        self.disk_path = disk_path
        self._disk_usage = disk_usage
        self._previous_cpu: tuple[int, int] | None = None

    @property
    def capabilities(self) -> tuple[str, ...]:
        # Do not claim procfs based telemetry on platforms that do not expose it.
        return TELEMETRY_CAPABILITIES if self.proc_root.is_dir() else ()

    def _cpu_utilization(self) -> dict:
        try:
            line = (self.proc_root / "stat").read_text(encoding="ascii").splitlines()[0]
        except (OSError, UnicodeError, IndexError):
            self._previous_cpu = None
            return _unavailable("cpu.utilization", "percent")

        current = _cpu_counters(line)
        previous = self._previous_cpu
        self._previous_cpu = current
        if current is None or previous is None:
            return _unavailable("cpu.utilization", "percent")

        total_delta = current[0] - previous[0]
        idle_delta = current[1] - previous[1]
        if total_delta <= 0 or idle_delta < 0 or idle_delta > total_delta:
            return _unavailable("cpu.utilization", "percent")
        return _measured("cpu.utilization", 100.0 * (total_delta - idle_delta) / total_delta, "percent")

    def _memory_utilization(self) -> dict:
        values: dict[str, tuple[int, str]] = {}
        try:
            lines = (self.proc_root / "meminfo").read_text(encoding="ascii").splitlines()
        except (OSError, UnicodeError):
            return _unavailable("memory.utilization", "percent")

        for line in lines:
            key, separator, raw_value = line.partition(":")
            if not separator or key not in {"MemTotal", "MemAvailable", "MemFree", "Buffers", "Cached"}:
                continue
            parts = raw_value.split()
            if len(parts) != 2 or parts[1] != "kB":
                continue
            try:
                amount = int(parts[0])
            except ValueError:
                continue
            if amount >= 0:
                values[key] = (amount, parts[1])

        total = values.get("MemTotal", (0, ""))[0]
        available = values.get("MemAvailable")
        quality = "measured"
        if available is None:
            # Older Linux kernels may not expose MemAvailable; this is an estimate.
            estimated = sum(values.get(key, (0, ""))[0] for key in ("MemFree", "Buffers", "Cached"))
            if not any(key in values for key in ("MemFree", "Buffers", "Cached")):
                return _unavailable("memory.utilization", "percent")
            available_value = estimated
            quality = "estimated"
        else:
            available_value = available[0]

        if total <= 0 or available_value > total:
            return _unavailable("memory.utilization", "percent")
        result = _measured("memory.utilization", 100.0 * (total - available_value) / total, "percent")
        result["quality"] = quality
        return result

    def _disk_utilization(self) -> dict:
        try:
            usage = self._disk_usage(self.disk_path)
            total = int(usage.total)
            used = int(usage.used)
        except (OSError, ValueError, TypeError, AttributeError, OverflowError):
            return _unavailable("disk.utilization", "percent")
        if total <= 0 or used < 0 or used > total:
            return _unavailable("disk.utilization", "percent")
        return _measured("disk.utilization", 100.0 * used / total, "percent")

    def collect(self) -> dict:
        observed_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        return {
            "schema_version": TELEMETRY_SCHEMA_VERSION,
            "observed_at": observed_at,
            "samples": [
                self._cpu_utilization(),
                self._memory_utilization(),
                self._disk_utilization(),
            ],
        }
