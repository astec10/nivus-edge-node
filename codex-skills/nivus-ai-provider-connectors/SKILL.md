---
name: nivus-ai-provider-connectors
description: "Add optional Nivus connectors to commercial AI providers with explicit data controls, secret handling, quotas, costs, timeouts, and local fallback."
---

# Nivus AI Provider Connectors

Use only for the planned external-provider phase or an explicitly scoped connector. Provider APIs, prices, and quotas change; consult current official provider documentation during implementation.

## Privacy and credential boundary
Read docs/PROJECT_ROADMAP.md Phase 6, docs/VISION.md, docs/DECISIONS.md, and the provider's current official API docs. Make the connector an optional adapter; core local monitoring must keep working if it is disabled or offline.

Classify what data may leave the house. Require an explicit operator policy before transmitting user documents, camera-derived content, telemetry, or credentials. Store keys in the configured secret mechanism and never print them, include them in exceptions, or commit them.

## Quotas and reliability
Track configurable per-day/week/month request and cost budgets. Enforce limits before network calls, define timeout/retry/backoff behavior, and avoid duplicate billable requests after uncertain failures. Redact provider request/response logs and retain only what is needed for auditing.

Expose provider name, model/version, cost estimate, and source provenance to the operator. Provide a local model or queued result as an explicit fallback; do not claim equivalence. Keep the connector behind a stable internal interface and document opt-in, disable, revoke, and data-retention behavior.
