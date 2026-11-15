---
name: nivus-node-registry
description: "Design or implement the planned Nivus node catalog, per-node identity, enrollment, revocation, heartbeat, and multi-node telemetry."
---

# Nivus Node Registry

Use only when multi-node identity or monitoring is part of the explicit task. This is a future Nivus capability until the code and project status show otherwise.

## Prerequisites and design
Read docs/PROJECT_ROADMAP.md Phase 2, docs/MODULE_MAP.md, backend schemas, auth dependencies, and current telemetry ingestion. Do not begin by trusting telemetry.node or an IP address as identity.

Design stable server and node identifiers, explicit enrollment, one-time pairing, per-node credentials stored as hashes, revocation, and authenticated heartbeat. Derive online/offline from last_seen and a configured timeout. Include agent version and allowlisted capability declarations, with schema versions.

Keep the first increment read-only: list registered nodes, last contact, and telemetry freshness. Do not add remote shell, task execution, MQTT actuator privileges, or arbitrary file transfer as part of node registration.

## Compatibility and failure handling
- Preserve existing telemetry.node and payload compatibility during migration.
- Reject unknown/revoked identities and replayed enrollment credentials.
- Test delayed and duplicate heartbeats, clock skew, network partitions, stale nodes, and credential rotation.
- Scope data and alerts by authenticated node identity before enabling multi-node actions.
- Record the threat model and API contract before changing shared schema/database files.

The skill and roadmap are design guidance, not proof that a node registry exists. Integrate only with an explicit task and update status after implementation and tests.
