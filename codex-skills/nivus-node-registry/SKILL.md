---
name: nivus-node-registry
description: "Review Nivus node identity, pairing, revocation, heartbeat, validated capability profiles, and registry synchronization."
---

# Nivus Node Registry

The initial authenticated registry is implemented: the Master creates node identities, pairs nodes with one-time codes, rotates session credentials, tracks ordered heartbeats, and supports revocation. The minimal agent pairs and sends heartbeat metadata. Check current code and `docs/PROJECT_STATUS.md`; do not infer that capability discovery, multi-node telemetry, or task scheduling is complete.

## Extend the registry safely
- Read `docs/AI_CONTEXT.md`, `docs/MODULE_MAP.md`, Phase 2 of `docs/PROJECT_ROADMAP.md`, the node router/service/schemas, and the agent files directly involved.
- Never treat hostname, IP, LAN discovery, `telemetry.node`, or agent self-assertion as identity or proof of capability.
- Keep identity, validated capabilities, and dynamic availability separate. Capabilities require recorded evidence and a schema/profile revision.
- Preserve the existing pairing and heartbeat contract. Store credential hashes, reject revoked identities and replayed enrollment credentials, and rotate credentials safely.
- A replicated fleet catalog should be read-only at workers, versioned, fresh and contain no peer credentials. The Master remains authoritative; stale snapshots cannot grant new leases.
- Begin with inventory and profile visibility. Do not add remote shell, arbitrary task execution, MQTT actuator privileges, or arbitrary file transfer to node registration.

## Failure handling and validation
Cover delayed/duplicate heartbeats, clock skew, network partitions, stale profiles, revocation, capability changes and schema compatibility. Validate real devices before claiming support. The scheduler, capability qualification and multi-node telemetry remain future work unless the inspected implementation proves otherwise.

