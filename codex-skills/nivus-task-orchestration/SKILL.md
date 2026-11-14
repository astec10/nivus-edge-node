---
name: nivus-task-orchestration
description: "Design the planned Nivus task queue and worker execution across nodes, with leases, quotas, cancellation, isolation, and verified artifacts."
---

# Nivus Task Orchestration

Use for the future distributed processing phase. This capability depends on authenticated node identity and measured local workloads; do not treat shared files as pooled compute.

## Before implementation
Read docs/PROJECT_ROADMAP.md Phase 5, docs/MODULE_MAP.md, and the node registry design. Start with independent batch work such as OCR, indexing, embeddings, or clip classification. Do not distribute live control loops or safety-critical actuator decisions.

## Scheduling contracts
Define task ID, input/output schemas, accepted capabilities, resource reservation, lease expiry, deadline, retry policy, cancellation, idempotency, and result acceptance before implementing workers. Use bounded CPU/RAM/disk, least privilege, and a sandbox with no general host access. Validate artifact hashes, model/data versions, and provenance.

## Failure behavior
Handle worker loss, coordinator restart, duplicate delivery, stale result, partial file transfer, network partition, and cancellation. A retry must not silently create a second physical side effect. Keep task data and worker permissions scoped to the job.

Prefer HTTPS artifact transfer with checksums. Add P2P only after measurements show that it solves a real bandwidth or latency problem and after its peer-authentication model is reviewed. P2P does not pool VRAM or automatically split one model across machines.
