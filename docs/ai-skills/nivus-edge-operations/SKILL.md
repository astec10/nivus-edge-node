---
name: nivus-edge-operations
description: "Work on Nivus Ubuntu and Docker Compose installation, resource sizing, backups, restore, rollback, and operational validation."
---

# Nivus Edge Operations

Use for Ubuntu packaging, Docker Compose, service management, resource limits, backup, restore, upgrade, and rollback.

## Read before operating
Read AGENTS.md, docs/MODULE_MAP.md, docs/PROJECT_STATUS.md, deploy/README.md, and docs/VM_VALIDATION.md. Inspect the actual service names, paths, Compose file, environment and backup scripts; never infer them from historical notes.

## Safety and portability
- Use a disposable Ubuntu VM for clean install, reboot, backup/restore, and forced-failure rollback. Do not test destructive restore against the active notebook database.
- For CPU/APU, board, and GPU temperatures, use `nivus-hardware-telemetry`; confirm the source exposed by Linux and label unavailable values as N/A instead of estimating them.
- Preserve existing systemd/Nginx services when installing a parallel candidate. Keep rollback paths and the pre-change SQLite backup.
- Keep secrets outside Git and out of shell output. The operator types administrative credentials directly into the target terminal.
- Keep MQTT private to the Compose network. Publish only the intended HTTPS entry point.
- Record Ubuntu version, architecture, CPU/RAM, disk, Docker/Compose versions, ports and measured resource use. A virtual runner does not prove hardware compatibility.
- Declare cleanup scope before running any command that removes containers, files, volumes, or directories.

## Recovery validation
For backup/restore, validate SQLite integrity, API health and authentication, all expected services, and telemetry resumption. Exercise both successful restore and rollback on a disposable clone. Stop if a prerequisite or rollback check fails; do not keep retrying against an active host.

Report staging, VM, and notebook results separately and update docs/PROJECT_STATUS.md. A skill does not authorize host changes; follow the current user request and required approvals for each external or high-impact operation.
