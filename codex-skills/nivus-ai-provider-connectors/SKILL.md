---
name: nivus-ai-provider-connectors
description: "Review Nivus AI provider profiles and optional inference connectors with data controls, secret handling, quotas, costs, and local fallback."
---

# Nivus AI Provider Connectors

The administrative provider catalog and encrypted profile management were implemented by PR #72; the bounded inference runtime was connected by PR #82. The latest recorded read-only check reports notebook release `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3`, and the operator reported seeing the provider tab. This is historical evidence, not a current host check, and it does not confirm saved credentials or a real inference. Verify current status and code before changing these claims.

## Privacy and credentials
- Read `docs/AI_CONTEXT.md`, `docs/AI_PROVIDER_CONNECTORS.md`, the relevant provider adapter, and current official provider documentation.
- Treat profile CRUD, endpoint validation, connectivity test and actual prompt execution as separate capabilities.
- Classify data that may leave the house. Require explicit operator policy before sending user documents, camera content, telemetry or personal data to a provider.
- Keep keys in the configured secret mechanism; never print, log, return or commit them. Runtime provider keys use authenticated encryption at rest with a separate master key; a one-way hash cannot replace a credential the runtime must use. Preserve key recovery and rotation boundaries.

## Quotas and reliability
- Enforce request/cost budgets before network calls; distinguish a configured local estimate from metered or provider-enforced spend.
- Use the current runtime's explicit provider selection, timeout, cancellation and idempotency key. It does not retry or fall back automatically; do not add retries without defining duplicate-billing behavior.
- Redact provider logs and retain only audit metadata needed for support.
- Keep cloud connectors optional and isolated from core local monitoring. A local fallback must be explicit and must not be described as equivalent.

