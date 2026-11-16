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


def _is_hotspot_label(label):
    label = label.lower()
    return any(token in label for token in ("hotspot", "junction"))


def _is_gpu_memory(label):
    label = label.lower()
    return any(token in label for token in ("memory", "mem", "vram"))


def _gpu_priority(reading):
    label = reading["label"].lower()
    if _is_hotspot_label(label):
        return 10
    if any(token in label for token in ("edge", "gpu", "core")):
        return 0
    if _is_gpu_memory(label):
        return 20
    return 7


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
    cpu_hotspot_readings = [
        reading for reading in cpu_readings if _is_hotspot_label(reading["label"])
    ]
    cpu_package_readings = [
        reading for reading in cpu_readings if not _is_hotspot_label(reading["label"])
    ]
    board_readings = [reading for reading in readings if reading["kind"] == "motherboard"]
    gpu_readings = [reading for reading in readings if reading["kind"] == "gpu"]
    gpu_readings.sort(key=_gpu_priority)
    gpu_hotspot_readings = [
        reading for reading in gpu_readings if _is_hotspot_label(reading["label"])
    ]
    gpu_core_readings = [
        reading
        for reading in gpu_readings
        if not _is_hotspot_label(reading["label"])
        and not _is_gpu_memory(reading["label"])
    ]

    cpu = cpu_package_readings[0] if cpu_package_readings else None
    cpu_hotspot = cpu_hotspot_readings[0] if cpu_hotspot_readings else None
    board = board_readings[0] if board_readings else None
    gpu = gpu_core_readings[0] if gpu_core_readings else None
    gpu_hotspot = gpu_hotspot_readings[0] if gpu_hotspot_readings else None
    return {
        "temperature": cpu["value"] if cpu else None,
        "temperature_source": f"{cpu['source']}: {cpu['label']}" if cpu else None,
        "cpu_hotspot_temperature": cpu_hotspot["value"] if cpu_hotspot else None,
        "cpu_hotspot_source": (
            f"{cpu_hotspot['source']}: {cpu_hotspot['label']}" if cpu_hotspot else None
        ),
        "motherboard_temperature": board["value"] if board else None,
        "motherboard_temperature_source": (
            f"{board['source']}: {board['label']}" if board else None
        ),
        "gpu_temperature": gpu["value"] if gpu else None,
        "gpu_temperature_source": f"{gpu['source']}: {gpu['label']}" if gpu else None,
        "gpu_hotspot_temperature": gpu_hotspot["value"] if gpu_hotspot else None,
        "gpu_hotspot_source": (
            f"{gpu_hotspot['source']}: {gpu_hotspot['label']}" if gpu_hotspot else None
        ),
    }


def get_host_battery_metrics():
    """Return the host's internal battery state when the OS exposes one."""
    try:
        battery = psutil.sensors_battery()
    except (psutil.Error, AttributeError, NotImplementedError):
        battery = None
    if battery is None:
        return {
            "host_battery_percent": None,
            "host_battery_power_plugged": None,
            "host_battery_source": None,
        }

    percent = getattr(battery, "percent", None)
    if not _valid_battery_percent(percent):
        percent = None
    plugged = getattr(battery, "power_plugged", None)
    if not isinstance(plugged, bool):
        plugged = None
    return {
        "host_battery_percent": float(percent) if percent is not None else None,
        "host_battery_power_plugged": plugged,
        "host_battery_source": "psutil: internal host battery" if percent is not None else None,
    }


def _valid_battery_percent(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 100
