---
id: ai-gateway-security-boundaries
title: Keep AI gateway traffic inside explicit security boundaries
topic: ai-gateway-security
tags: ai-gateway, external-provider, api-key, privacy, loopback, authentication, tls, rate-limit, prompt-logging, data-egress
source: https://github.com/shihabshahrier/freelm; https://github.com/djeannie29/cafe_dados_e_gatos/blob/main/ferramentas-ia/tv-box-gateway-ia/pt-br/README.md; docs/VIDEO_RESEARCH_INDEX.md
verified_on: 2026-11-24
confidence: upstream-project-docs-and-source-review
---

## Atomic summary

An AI gateway is a network boundary: it may forward prompts and tool context from Nivus to third-party providers. Treat every external route as data egress and make the destination, authentication, provider policy and failure behavior explicit.

## Bind and authenticate

- Keep the endpoint on loopback by default. The FreeLM upstream documents `127.0.0.1:4000/v1` as its local default.
- If another container needs access, use a private service network and do not publish the gateway port to the LAN unless required.
- Before exposing an endpoint to a LAN, VPN or remote client, require authentication, restrict source networks, add rate and request-size limits, and use TLS or a trusted private tunnel.
- Keep provider credentials outside source control and UI logs. Store them in the designated secret store, reveal them only at entry, and never include them in prompts, responses or diagnostic output.

## Protect prompt data

- Public or free endpoints can have different retention, logging and training policies. The FreeLM README specifically warns that keyless public routes may log prompts; terms and quotas can change.
- Send only public or synthetic data during evaluation. Require explicit operator policy before routing household telemetry, camera descriptions, credentials, personal data or actuator state to any external provider.
- A fallback or parallel fan-out may send the same prompt to multiple providers. Show the selected destinations and require an explicit allowlist; do not silently retry to an unapproved service.
- Default logs should record provider, model, result status, duration and request ID without storing prompt/response bodies or credentials.

## Fail safely

If the approved provider is unavailable, stop or use a separately approved local model. Do not silently change provider, disable authentication, expose a port, or claim offline operation when the model request depends on the Internet.

## Evidence and limits

This note is design guidance, not a claim that every control is already implemented in Nivus. FreeLM documents a loopback local endpoint, an authentication option when it is exposed, and possible prompt logging on no-key public routes. Provider-specific retention and security terms must be checked before each integration.

## References

- [FreeLM upstream README](https://github.com/shihabshahrier/freelm)
- [Creator's TV Box gateway guide](https://github.com/djeannie29/cafe_dados_e_gatos/blob/main/ferramentas-ia/tv-box-gateway-ia/pt-br/README.md)
- [Video research index](../../docs/VIDEO_RESEARCH_INDEX.md)
