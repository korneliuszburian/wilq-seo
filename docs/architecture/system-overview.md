# System Overview

WILQ Marketing Operating System connects one canonical API to a dashboard, Codex runtime, connector registry, expert rules, workflows, knowledge cards, opportunities, and action objects.

Product inspiration: WILQ should feel like an AI operating system for Ads/SEO/local/content work, with BDOS.ai as a strong Google Ads operating-system reference point. The implementation rule is stricter than a chat-first ads assistant: WILQ decisions must come from WILQ API evidence, typed action contracts, validation and audit, not from model memory or tool prose.

```txt
Dashboard + future Codex skills + hooks
  -> WILQ API
  -> connector registry, evidence registry, metric store, expert rules, opportunity engine, actions, audit, local state
  -> Google Ads, GSC, GA4, Merchant Center, Ahrefs, Localo, WordPress, LinkedIn, Facebook
```

Rules:

- WILQ API is canonical.
- MCP servers are adapters.
- Skills are operator workflows created after the API endpoints they call exist.
- Expert rules live as structured YAML but are consumed through typed WILQ API endpoints, not by prompt-only logic.
- Codex runs, workflow runs, connector refresh runs, and audit events persist to local SQLite state with redaction.
- Redacted connector refresh metric summaries also persist to a local DuckDB metric store for analytical reads.
- Repo-local `.env` is the primary private credential source; the Ekologus access pack is import/fallback material.
- Google Sheets is optional and disabled for the current Ekologus operator scope; it is not a required evidence source.
- Knowledge playbooks compile into source-lineage cards before reaching Codex context packs.
- Evidence registry records expose readiness/source/refresh state without secret values.
- Readiness opportunities may derive from connector-status evidence, connector refresh-run evidence, playbook IDs, and expert-rule IDs. They must not claim vendor performance metrics until vendor refreshes exist.
- Seed data is allowed only when labeled as non-real.
- No evidence ID means no recommendation.

Expert-rule API surface:

- `/api/expert/rules`: full structured rules with evidence requirements and output contracts.
- `/api/expert/rule-summaries`: compact rule contracts for context packs and operator workflows.
- `/api/expert/capabilities`: capability IDs mapped to required evidence, action contracts and source rules.

Local-state API surface:

- `/api/codex/runs`: persisted Codex run records.
- `/api/workflow-runs`: persisted workflow run records.
- `/api/connectors/refresh-runs`: persisted connector refresh run records.
- `/api/audit/events`: persisted audit events, optionally filtered by action ID.

Metric API surface:

- `/api/metrics/status`: local DuckDB metric store status, row counts and backend metadata.
- `/api/metrics`: redacted connector metric facts with optional connector filtering.

Knowledge API surface:

- `/api/knowledge/playbooks`: machine-readable playbook contracts.
- `/api/knowledge/cards`: compact compiled cards with lineage.
- `/api/knowledge/condense`: deterministic playbook-to-card compilation.

Evidence API surface:

- `/api/evidence`: connector-status and connector-refresh evidence records, with freshness and redacted summaries.
- `/api/evidence/{evidence_id}`: one evidence record by ID.
