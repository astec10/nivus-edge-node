---
name: nivus-home-automation
description: "Plan or implement Nivus integrations for Home Assistant, Zigbee, sensors, energy meters, cameras, and safety-bounded actuators."
---

# Nivus Home Automation

Use for home-device integrations and physical automations. Treat these as planned capabilities unless code and project status confirm the specific integration.

## Start read-only
Read docs/VISION.md, docs/PROJECT_ROADMAP.md Phase 3, docs/MODULE_MAP.md, and the device/vendor documentation for the exact model. Begin with status and measurement ingestion. Normalize units, timestamps, source, quality, and stale/missing states.

Keep adapters replaceable and use the narrowest Home Assistant or device permission. Avoid coupling vendor-specific APIs to core rules. Minimize camera, face, plate, and audio data; set access and retention before collecting it.

## Physical safety
- Never let an AI prediction, face match, plate read, or remote command alone open a gate, disable an alarm, control a battery/inverter, or switch a critical circuit.
- Require deterministic local interlocks, explicit allowlists, acknowledgement, timeouts, safe failure state, and a manual override.
- A loss of Internet or an unavailable Nivus coordinator must not defeat the device's local safety behavior.
- Keep electrical installation and protection within qualified professional/vendor requirements.

Document the sensor schema, failure behavior, privacy effects, and rollback. Test with simulated readings first, then a noncritical read-only integration; do not issue real actuator commands without explicit authorization for that operation.
