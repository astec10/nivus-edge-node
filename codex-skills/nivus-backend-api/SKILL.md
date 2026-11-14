---
name: nivus-backend-api
description: "Implement or review Nivus FastAPI routes, authorization, SQLite persistence, and MQTT boundaries. Use for backend changes; use the operations skill for host-level deployment."
---

# Nivus Backend API

Use for work in the FastAPI backend, data layer, authentication, and MQTT service boundary.

## Orient to the actual tree
Read AGENTS.md, docs/MODULE_MAP.md, docs/PROJECT_STATUS.md, docs/ARCHITECTURE.md, and docs/DECISIONS.md. Inspect the route, schema, dependency, service, and database code involved before editing. The repository state is authoritative over old conversation snippets.

## Preserve boundaries
- Keep route handlers focused on HTTP validation and response mapping. Use schemas for request validation, dependencies for identity and role checks, services for business behavior, and database.py for SQLite access.
- Preserve existing routes and payloads during modularization unless the task explicitly includes a compatible migration.
- Make SQLite schema changes additive. Back up and validate before any data migration; use a disposable database for development.
- Keep authentication separate from network location. Do not trust a LAN address, hostname, telemetry label, or client-supplied node identifier as machine identity.
- Treat telemetry.node as a display/data label until an authenticated node registry is implemented.
- Publish MQTT commands only through the existing service boundary. Preserve ACL, topic allowlists, acknowledgement, timeout, and least privilege.
- Never hard-code JWT secrets, passwords, MQTT credentials, or deployment-specific addresses.

## Validate proportionally
Use a temporary SQLite database and isolated MQTT when validating backend behavior. Check protected routes with and without credentials, role enforcement, and schema compatibility. Do not print credentials or personal telemetry. Update docs/PROJECT_STATUS.md when evidence changes. Do not deploy to a live notebook from this skill; use the operations workflow and its isolation requirements.
