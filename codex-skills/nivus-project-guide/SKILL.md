---
name: nivus-project-guide
description: "Orient work in the Nivus Edge Node repository using its current status, dependency map, roadmap, and contribution boundaries. Use at task start or when coordinating changes across modules."
---

# Nivus Project Guide

Use for project-level planning, status questions, architecture reviews, and changes that cross module boundaries.

## Start with current evidence
- Locate the actual Nivus checkout or staging tree; do not assume a path from another session.
- Start with `docs/AI_CONTEXT.md` and read the relevant parts of `docs/PROJECT_STATUS.md`.
- Read `docs/MODULE_MAP.md` and `docs/PROJECT_ROADMAP.md` for cross-module or future-phase work. Read `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` before changing shared contracts; do not load every reference document for a contained change.
- Inspect the current code and GitHub branch before describing a change as present, published, installed, or tested.
- Keep four states distinct: implemented in the tree, observed on the CCE U25, staged for review, and planned.

## Keep work modular
- Assign a change to one functional owner from the module map.
- Identify inputs, outputs, dependencies, persistence, permissions, and failure behavior before integrating.
- For CPU/APU, motherboard, or GPU sensor work, use `nivus-hardware-telemetry` to identify the driver/source and avoid treating a generic ACPI zone as a CPU sensor.
- Avoid simultaneous edits to shared contracts such as backend/main.py, backend/api/schemas.py, backend/database.py, Compose, and MQTT ACLs.
- Integrate small changes through reviewable commits and update status/roadmap documents when facts change.

## Preserve project decisions
- Target Ubuntu Server minimal x86_64; do not claim universal hardware support without compatibility evidence.
- The initial authenticated node registry and heartbeat exist. Capability inventory, authenticated multi-node telemetry, task scheduling, home automation, local AI and commercial inference remain future or partially validated work unless inspected code proves otherwise.
- User authentication currently uses password/JWT; USB and biometrics are not implemented.
- Preserve AGPL-3.0-only and third-party notices. Do not publish local temp knowledge, credentials, real databases, or private household data.
- Never claim a deploy or test passed without observable output. A skill or roadmap entry is not proof of implementation.

Use the operations skill for host installation/recovery and the relevant domain skill for the module in scope.
