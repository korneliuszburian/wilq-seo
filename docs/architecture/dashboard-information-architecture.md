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
- `/seo-gsc`
- `/ahrefs`
- `/localo`
- `/merchant`
- `/content-planner`
- `/content-inventory`
- `/social-publisher`
- `/google-sheets`
- `/knowledge`
- `/codex-runs`
- `/security`
- `/settings`

Command Center prioritizes money leaks, scaling candidates, migration readiness, traffic wins, content gaps, feed issues, local visibility drops, social opportunities, tracking gaps, connector failures, and Codex workflow failures.

Implementation:

- `apps/dashboard/src/routes/App.tsx`
- TanStack Query fetches WILQ API state.
- Route surfaces share opportunities, actions, connector status, and workflow state.

