---
name: nivus-backend-api
description: "Implement or review Nivus FastAPI routes, authorization, SQLite persistence, and MQTT boundaries. Use for backend changes; use the operations skill for host-level deployment."
---

# Nivus Backend API

Use for work in the FastAPI backend, data layer, authentication, and MQTT service boundary.

## Orient to the actual tree
Read `AGENTS.md`, `docs/AI_CONTEXT.md`, and the relevant router/schema/service/database files. Read `docs/PROJECT_STATUS.md` for status-sensitive work and architecture/decisions only when changing shared contracts. The repository state is authoritative over old conversation snippets.

## Preserve boundaries
- Keep route handlers focused on HTTP validation and response mapping. Use schemas for request validation, dependencies for identity and role checks, services for business behavior, and database.py for SQLite access.
- Preserve existing routes and payloads unless the task explicitly includes a compatible migration.
- Make SQLite schema changes additive. Back up and validate before any data migration; use a disposable database for development.
- Keep authentication separate from network location. Do not trust a LAN address, hostname, telemetry label, or client-supplied node identifier as identity.
- The node registry now provides authenticated pairing and heartbeat. Treat `telemetry.node` as an untrusted display/data label until telemetry ingestion is explicitly scoped to authenticated node identity and a versioned envelope.
- Publish MQTT commands only through the existing service boundary. Preserve ACL, topic allowlists, acknowledgement, timeout, and least privilege. MQTT currently stays private to Compose; require authenticated TLS before any broker traffic crosses node boundaries.
- Never hard-code JWT secrets, passwords, MQTT credentials, or deployment-specific addresses.

## Validate proportionally
Use a temporary SQLite database and isolated MQTT when validating backend behavior. Check protected routes with and without credentials, role enforcement, and schema compatibility. Do not print credentials or personal telemetry. Update `docs/PROJECT_STATUS.md` only when evidence changes. Do not deploy to a live notebook from this skill; use the operations workflow and its isolation requirements.

