---
name: nivus-ai-dev-workflow
description: "Maintain and review the Nivus GitHub Issues and Actions development worker, isolated proposal branches, CI, draft pull requests, and human approval."
---

# Nivus AI Development Workflow

Use for the external development executor, which is separate from the Nivus runtime and from the future task scheduler among Nivus nodes.

## Current repository flow
- The implemented intake validates a public/synthetic Issue contract. `ai:queued` records validated waiting work; an explicit maintainer authorization for one free-tier Gemini call adds `ai:ready` and starts the GitHub-hosted worker.
- The worker uses an isolated hosted runner, a fixed Gemini adapter, bounded exact paths and runtime, creates a proposal branch, runs the reusable Ubuntu CI, and opens a draft PR after checks. Human review is required; the worker cannot merge or deploy.
- Check `docs/AI_EXECUTOR_IMPLEMENTATION.md`, the current workflows and `docs/PROJECT_STATUS.md` before stating that a new end-to-end run succeeded. The last recorded status still awaited a fresh explicitly authorized run after the automatic PR-creation fix.
- Issue text, comments, commit metadata and model output are untrusted input. Preserve validation, duplicate protection, bounded retries, audit history, and least-privilege job permissions.

## Changes and future integrations
- Keep secrets out of prompts, artifacts and logs. Only public/synthetic repository context is allowed in the current free-tier path.
- Do not remove the human authorization step or make model calls on every queued Issue without an explicit policy decision.
- Discord, Jira, Hermes and OmniRoute are optional external components described for comparison; they are not active Nivus integrations. Do not install them on the edge node based on this skill.
- Keep each task scoped to one Issue, acceptance criteria, allowed paths, resource/time limits and a human owner. Use one isolated branch/worktree per task.
- Update `docs/AI_DEVELOPMENT_ORCHESTRATION.md` only when verified integrations or policy decisions change; update status only after observable results.
