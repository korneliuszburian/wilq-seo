# System Overview

WILQ Marketing Operating System connects one canonical API to a dashboard, Codex runtime, connector registry, expert rules, workflows, knowledge cards, opportunities, and action objects.

```txt
Dashboard + Codex skills + hooks
  -> WILQ API
  -> connector registry, expert rules, opportunity engine, actions, audit, local state
  -> Google Ads, GSC, GA4, Merchant Center, Sheets, Ahrefs, Localo, WordPress, LinkedIn, Facebook
```

Rules:

- WILQ API is canonical.
- MCP servers are adapters.
- Skills are operator workflows created after the API endpoints they call exist.
- Expert rules live as structured YAML but are consumed through typed WILQ API endpoints, not by prompt-only logic.
- Codex runs, workflow runs, and audit events persist to local SQLite state with redaction.
- Seed data is allowed only when labeled as non-real.
- No evidence ID means no recommendation.

Expert-rule API surface:

- `/api/expert/rules`: full structured rules with evidence requirements and output contracts.
- `/api/expert/rule-summaries`: compact rule contracts for context packs and operator workflows.
- `/api/expert/capabilities`: capability IDs mapped to required evidence, action contracts and source rules.

Local-state API surface:

- `/api/codex/runs`: persisted Codex run records.
- `/api/workflow-runs`: persisted workflow run records.
- `/api/audit/events`: persisted audit events, optionally filtered by action ID.
