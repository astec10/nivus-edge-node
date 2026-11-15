---
name: nivus-hardware-telemetry
description: "Identify, collect, and display Nivus host hardware sensors for CPU/APU, motherboard, GPU, and thermals across Ubuntu x86_64 systems."
---

# Nivus Hardware Telemetry

Use this skill when adding or reviewing host CPU, APU, motherboard, GPU, fan, or thermal readings. This is hardware telemetry for the Nivus host; Home Assistant device sensors belong to `nivus-home-automation`.

## Establish what the machine exposes
- Read `docs/MODULE_MAP.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`, `telemetry/agent.py`, and the current sensor provider before editing.
- Identify the host with read-only sources such as `lscpu`, `lspci`, `/sys/class/hwmon`, `/sys/class/thermal`, and `psutil.sensors_temperatures()`.
- The Linux kernel [`hwmon` interface](https://docs.kernel.org/hwmon/sysfs-interface.html) and [`lm-sensors`](https://github.com/lm-sensors/lm-sensors) are the Ubuntu baseline; `psutil` is the existing lightweight Python interface. Use the `sensors` command as an optional diagnostic, remembering that many laptops expose only ACPI/BIOS sensors and not a full motherboard sensor chip.
- [`LibreHardwareMonitor`](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) is the preferred Windows open-source comparison. The original [`Open Hardware Monitor`](https://github.com/openhardwaremonitor/openhardwaremonitor) is legacy; its official Releases page listed no packaged releases when checked on 2026-11-14. [`HardwareMonitor/OpenHardwareMonitor`](https://github.com/HardwareMonitor/OpenHardwareMonitor) is a separate fork based on the original and publishes its own releases. Neither Windows project proves Linux sensor availability. HWiNFO, CPU-Z, and GPU-Z are comparison references; none is a runtime dependency for Ubuntu Server.
- Prefer Linux kernel drivers and `/sys/class/hwmon` for collection. Do not install a Windows monitor or a .NET runtime in the Ubuntu edge stack solely to read temperatures.
- A VM can hide or synthesize sensors. Record hardware, kernel, driver, and whether the observation came from bare metal or a VM.

## Classify readings by evidence
- Prefer a source driver plus its label. For Intel CPUs, prioritize `coretemp` package readings; for AMD, prefer `Tdie` when available, then a documented package/control reading. Use generic `x86_pkg_temp`, `cpu_thermal`, or `soc_thermal` only when the source identifies that component.
- Recognize GPU readings only when an installed driver/tool exposes them, such as Linux `amdgpu`/`nouveau`/`i915` hwmon entries or an optional vendor adapter. Do not infer GPU temperature from utilization or model name.
- Map a motherboard reading only from an explicit board/system sensor label or a known board-monitoring driver. Do not label a bare `acpitz` value or `thermal_zone0` as CPU or motherboard by position.
- Keep source and label with each scalar reading. Normalize temperature to Celsius; validate finite values and reject implausible ranges.
- Missing, unsupported, or permission-denied sensors are `null`/N/A. Never substitute zero, a different component's value, or an old reading without its timestamp/source.

## Keep collection safe and small
- Prefer kernel/sysfs and `psutil` reads over shelling out on every sample. Optional tools such as `nvidia-smi` must be detected, invoked without a shell, time-limited, and treated as absent when unavailable.
- Keep collection optional so a missing GPU, fan, or motherboard sensor cannot stop CPU, memory, disk, MQTT, or API collection.
- Set the sampling cadence and retention intentionally. Do not append an unlimited high-frequency row for every raw sensor to the SQLite database.
- Never run invasive SMBus probing or load an unverified kernel module during normal installation. Use read-only discovery first and document any privileged diagnostic separately.

## Verify and document
- On each test machine, record the sensor source/label and compare it with the vendor or board diagnostic when available. Compare like-for-like sensors, such as package with package, not package with ACPI zone.
- Exercise a brief bounded CPU workload when the operator authorizes it; check that the chosen CPU reading follows the load and that N/A remains N/A for absent components.
- Validate at least Intel and AMD hosts and integrated/discrete GPU cases before claiming broad sensor coverage. Do not infer physical sensor support from a CI VM.
- Preserve the telemetry API compatibility field or write an additive schema migration. Update dashboard labels so component, unit, source, and missing-data state are clear.
- Record hardware, environment, commands, observations, and limits in `docs/PROJECT_STATUS.md`; do not include serial numbers, private host identifiers, or household telemetry.
