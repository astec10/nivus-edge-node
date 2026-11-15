---
id: ai-development-persistent-worker
title: Persistent AI development worker with review gates
topic: ai-development-orchestration
tags: hermes, omniroute, discord, jira, github, queue, worker, pull-request, ci, human-review
source: docs/AI_DEVELOPMENT_ORCHESTRATION.md; https://hermes-agent.nousresearch.com/docs/user-guide/docker
verified_on: 2026-11-15
confidence: secondary-source
---

## Atomic summary

A persistent development executor can accept tasks through an authorized chat/webhook, reserve work from a durable queue, execute in an isolated workspace, open a pull request and wait for CI and human review. A small always-on notebook may dispatch work while an ephemeral hosted runner handles code execution; the durable queue remains in GitHub. Supervision/restart, bounded retry, idempotency and persisted task state make it resilient to interruptions. This is a workflow pattern, not a guaranteed uninterrupted service.

## When it applies

Use it for asynchronous repository work when the operator may be offline. Keep it separate from the Nivus edge runtime and its telemetry. A notebook controller is optional; cross-node telemetry becomes useful when the Nivus Master is operational. Do not let the agent merge or deploy production changes.

## Evidence and limits

The Hermes Docker documentation describes a persistent messaging gateway; Hermes, OmniRoute, Jira, Discord and GitHub capabilities are documented separately. The exact integration reported in the video comment has not been confirmed from a video transcript or a reproducible deployment.

## References

- [Nivus component analysis](../../docs/AI_DEVELOPMENT_ORCHESTRATION.md)
- [Module work packages and integration plan](../../docs/AI_MODULE_WORKPLAN.md)
- [Hermes persistent gateway documentation](https://hermes-agent.nousresearch.com/docs/user-guide/docker)
- [GitHub deployment reviews](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
