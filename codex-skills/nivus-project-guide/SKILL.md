---
name: nivus-project-guide
description: "Orient work in the Nivus Edge Node repository using its current status, dependency map, roadmap, and contribution boundaries. Use at task start or when coordinating changes across modules."
---

# Nivus Project Guide

Use this skill for project-level planning, status questions, architecture reviews, and work that crosses module boundaries.

## Start with current evidence
- Locate the actual Nivus checkout or staging tree; do not assume a path from another session.
- Read AGENTS.md, docs/AI_CONTEXT.md, docs/PROJECT_STATUS.md, docs/MODULE_MAP.md, docs/PROJECT_ROADMAP.md, docs/ARCHITECTURE.md, and docs/DECISIONS.md.
- Inspect the current code and GitHub branch before describing a change as present, published, installed, or tested.
- Keep four states distinct: implemented in the tree, observed on the CCE U25, staged for review, and planned.

## Keep work modular
- Assign a change to one functional owner from docs/MODULE_MAP.md.
- Identify inputs, outputs, dependencies, persistence, permissions, and failure behavior before integrating.
- For CPU/APU, motherboard, or GPU sensor work, use `nivus-hardware-telemetry` to identify the driver/source and avoid treating a generic ACPI zone as a CPU sensor.
- Avoid simultaneous edits to shared contracts such as backend/main.py, backend/api/schemas.py, backend/database.py, Compose, and MQTT ACLs.
- Integrate small changes through reviewable commits and update status/roadmap documents when facts change.

## Preserve project decisions
- Target Ubuntu Server minimal x86_64, but do not claim universal hardware support without the recorded compatibility evidence.
- Current product is single-node; authenticated node identity, home automation, local AI, task federation, and commercial connectors are future roadmap capabilities unless the inspected code proves otherwise.
- Current user authentication is password/JWT. USB and biometrics are not implemented.
- Preserve AGPL-3.0-only and third-party notices. Do not publish local temp knowledge, credentials, real databases, or private household data.
- Never claim a deploy or test passed without observable output. Do not treat a skill or roadmap entry as proof of implementation.

Use the operations skill for host installation/recovery, and use the relevant domain skill only for the module in scope.
