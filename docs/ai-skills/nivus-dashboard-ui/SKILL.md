---
name: nivus-dashboard-ui
description: "Modify or review Nivus React/Vite interfaces, dashboard components, accessibility, authentication flows, and the development progress page."
---

# Nivus Dashboard UI

Use for React/Vite frontend components, login and dashboard interactions, accessibility, and PROGRESS.html.

## Check scope first
Read AGENTS.md, docs/MODULE_MAP.md, docs/PROJECT_STATUS.md, and the relevant frontend or progress-page files. The product dashboard and the development milestone page are separate interfaces: PROGRESS.html is static project status and is not live node telemetry.

## UI rules
- Preserve the existing API contracts and same-origin authentication flow; inspect the implementation before changing token handling.
- Keep UI code in frontend/src and reuse the existing component boundaries. Do not make browser components connect directly to SQLite or MQTT.
- Keep all filters, buttons, tabs, and refresh controls functional by keyboard and pointer. Maintain accessible names, focus states, and pressed/selected state.
- For filtering, ensure the hidden state is not overridden by layout CSS; include a visible empty state when no records match.
- Preserve the AGPL notice and source/license links in interactive interfaces.
- Avoid new dependencies unless their benefit and bundle cost are justified for the low-resource target.

## Verify
For behavior changes, exercise the real interaction or a focused DOM test, then run the available frontend checks/build if appropriate. Do not say a staging UI was published to the notebook unless the host checks confirm it. Report browser/live-host verification separately from local staging validation.
