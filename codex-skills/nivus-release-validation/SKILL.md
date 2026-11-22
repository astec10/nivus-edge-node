---
name: nivus-release-validation
description: "Plan and review Nivus release readiness across hosted CI, isolated install/restore flows, and physical hardware validation."
---

# Nivus Release Validation

Use before describing a Nivus release, installer, recovery procedure, or hardware capability as validated.

## Read the applicable evidence
- Start with `docs/AI_CONTEXT.md`, `docs/PROJECT_STATUS.md`, `docs/TEST_STRATEGY.md`, and `docs/VM_VALIDATION.md`.
- Read `deploy/README.md` and the touched operational scripts for installation, update, backup or restore work.
- Inspect the exact commit, workflow runs, artifacts and test output. A green CI job is evidence for its stated runner only.

## Keep gates separate
1. Hosted CI validates reproducible software flows, syntax, unit checks, Compose smoke and isolated restore/rollback.
2. Physical qualification validates boot, reboot, sensor exposure, network devices, sustained load, thermals and resource use on identified hardware.
3. Notebook deployment records the installed release and observable health/rollback evidence; it does not imply universal compatibility.

## Release checks
- Confirm backup, upgrade, rollback, configuration/secrets preservation, health, authentication and service recovery.
- Record hardware model, CPU, RAM, storage, firmware, OS, driver and measurement source without publishing serials or private host details.
- Mark missing physical checks as pending; do not replace them with VM results or a roadmap checkbox.
- Keep production merge/deploy under human approval. Stop release claims when a required gate lacks evidence.

