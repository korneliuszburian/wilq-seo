# System Overview

WILQ Marketing Operating System connects one canonical API to a dashboard, Codex runtime, connector registry, expert rules, workflows, knowledge cards, opportunities, and action objects.

```txt
Dashboard + Codex skills + hooks
  -> WILQ API
  -> connector registry, expert rules, opportunity engine, actions, audit
  -> Google Ads, GSC, GA4, Merchant Center, Sheets, Ahrefs, Localo, WordPress, LinkedIn, Facebook
```

Rules:

- WILQ API is canonical.
- MCP servers are adapters.
- Skills are operator workflows created after the API endpoints they call exist.
- Seed data is allowed only when labeled as non-real.
- No evidence ID means no recommendation.

