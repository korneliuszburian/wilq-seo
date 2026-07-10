# Dashboard Information Architecture

The dashboard is a dynamic React/TypeScript operator cockpit, not a static report.

Routes:

- `/command-center`
- `/workflows`
- `/workflows/:id`
- `/opportunities`
- `/opportunities/:id`
- `/actions`
- `/actions/:id`
- `/ads-doctor`
- `/ads-doctor/search-terms`
- `/ads-doctor/custom-segments`
- `/ads-doctor/demand-gen`
- `/ads-doctor/scaling`
- `/ads-doctor/seasonality`
- `/ads-doctor/recommendations`
- `/ga4`
- `/ahrefs`
- `/localo`
- `/merchant`
- `/content-workflow`
- `/content-inventory` (hidden technical inventory input; not a primary marketer route)
- `/social-publisher` (hidden review-only experiment)
- `/google-sheets` (hidden technical export placeholder)
- `/knowledge`
- `/codex-runs`
- `/security`
- `/settings`

Command Center prioritizes money leaks, scaling candidates, migration readiness, traffic wins, content gaps, feed issues, local visibility drops, social opportunities, tracking gaps, connector failures, and Codex workflow failures.

Usefulness gate:

- Current Goal 001 dashboard routes are foundation surfaces, not the final marketer dashboard.
- A route is useful only when it shows real API-backed metrics, evidence IDs, source connectors, freshness, diagnostic interpretation and action candidates.
- Empty route shells, generic cards, readiness-only connector state, or static labels must not be described as marketer-ready.
- If metrics are unavailable, the route must expose the exact blocker: missing credential names, OAuth/API status, connector disabled state, missing vendor-read adapter, stale refresh or unsupported write action.
- Polish marketer-facing copy must use Polish labels once a route graduates from foundation shell to daily-use surface.

Implementation:

- `apps/dashboard/src/routes/App.tsx`
- TanStack Query fetches WILQ API state.
- Route surfaces share opportunities, actions, connector status, and workflow state.
