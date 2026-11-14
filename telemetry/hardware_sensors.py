"""Read host thermal sensors exposed by psutil/Linux hwmon."""

import math

import psutil


CPU_SOURCES = {"coretemp", "k10temp", "zenpower", "cpu_thermal", "soc_thermal", "x86_pkg_temp"}
GPU_SOURCES = {"amdgpu", "nouveau", "nvidia", "i915", "xe"}
BOARD_SOURCES = {"nct6775", "nct6798", "nct6683", "it87", "w83627ehf"}


def _valid_temperature(value):
    return (
        isinstance(value, (int, float))
        and math.isfinite(value)
        and -40 <= value <= 150
    )


def _classify(source, label):
    source = source.lower()
    label = label.lower()

    if source in GPU_SOURCES or any(token in label for token in ("gpu", "vram", "graphics")):
        return "gpu"
    # Super-I/O chips often label a socket-area probe as CPU; keep those
    # board-controller readings out of the CPU-package metric.
    if source in BOARD_SOURCES:
        return "motherboard"
    if source in CPU_SOURCES or any(
        token in label for token in ("cpu", "package", "physical id", "tdie", "tctl", "core")
    ):
        return "cpu"
    if any(
        token in label for token in ("motherboard", "mainboard", "board", "systin", "ambient")
    ):
        return "motherboard"
    return "other"


def _cpu_priority(source, label):
    source = source.lower()
    label = label.lower()

    if source == "coretemp" and ("package" in label or "physical id" in label):
        return 0
    if "tdie" in label:
        return 1
    if source == "x86_pkg_temp" or "package" in label or "physical id" in label:
        return 2
    if source in {"cpu_thermal", "soc_thermal"}:
        return 3
    if "tctl" in label:
        return 4
    if "core" in label:
        return 5
    return 6


def get_thermal_metrics():
    """Return identified CPU/APU, motherboard, and GPU temperatures.

    Generic ACPI zones such as ``acpitz`` are kept out of the CPU reading
    unless their label identifies the CPU. Missing sensors remain ``None``.
    """
    readings = []
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
    except (AttributeError, OSError, NotImplementedError):
        sensors = {}

    for source, entries in sensors.items():
        for index, entry in enumerate(entries):
            value = getattr(entry, "current", None)
            if not _valid_temperature(value):
                continue
            label = (getattr(entry, "label", "") or "").strip()
            readings.append(
                {
                    "source": str(source)[:48],
                    "label": label[:64] or f"sensor {index + 1}",
                    "value": float(value),
                    "kind": _classify(str(source), label),
                }
            )

    cpu_readings = [reading for reading in readings if reading["kind"] == "cpu"]
    cpu_readings.sort(key=lambda reading: _cpu_priority(reading["source"], reading["label"]))
    board_readings = [reading for reading in readings if reading["kind"] == "motherboard"]
    gpu_readings = [reading for reading in readings if reading["kind"] == "gpu"]

    cpu = cpu_readings[0] if cpu_readings else None
    board = board_readings[0] if board_readings else None
    gpu = gpu_readings[0] if gpu_readings else None
    return {
        "temperature": cpu["value"] if cpu else None,
        "temperature_source": f"{cpu['source']}: {cpu['label']}" if cpu else None,
        "motherboard_temperature": board["value"] if board else None,
        "gpu_temperature": gpu["value"] if gpu else None,
    }

