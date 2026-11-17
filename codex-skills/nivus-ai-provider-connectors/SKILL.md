---
name: nivus-ai-provider-connectors
description: "Review Nivus AI provider profiles and optional inference connectors with data controls, secret handling, quotas, costs, and local fallback."
---

# Nivus AI Provider Connectors

The administrative profile-management surface is implemented in PR #72 and passed hosted CI; it was not yet deployed on the test notebook in the latest recorded status. Saving or testing a profile does not connect the inference task executor. Provider execution, quota enforcement and fallback remain separate work. Verify the current status and code before changing these claims.

## Privacy and credentials
- Read `docs/AI_CONTEXT.md`, `docs/AI_PROVIDER_CONNECTORS.md`, the relevant provider adapter, and current official provider documentation.
- Treat profile CRUD, endpoint validation, connectivity test and actual prompt execution as separate capabilities.
- Classify data that may leave the house. Require explicit operator policy before sending user documents, camera content, telemetry or personal data to a provider.
- Keep keys in the configured secret mechanism; never print, log, return or commit them. Preserve encryption-key recovery and rotation boundaries.

## Quotas and reliability
- Enforce per-period request/cost budgets before network calls; distinguish a configured budget from metered or provider-enforced spend.
- Define timeout, retry/backoff and idempotency behavior; avoid duplicate billable requests after uncertain failures.
- Redact provider logs and retain only audit metadata needed for support.
- Keep cloud connectors optional and isolated from core local monitoring. A local fallback must be explicit and must not be described as equivalent.
