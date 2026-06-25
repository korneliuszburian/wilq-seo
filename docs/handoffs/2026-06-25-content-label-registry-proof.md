# Content Label Registry Proof - 2026-06-25

## Scope

This was a structural cleanup after the owner rejected UI-side string
replacement and route-local copy hardcoding.

Changed:

- moved pure Content Planner domain labels and metric formatting from
  `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx` to
  `apps/dashboard/src/lib/contentLabels.ts`;
- updated focused tests to import the shared label registry;
- updated route tests for the new central labels.

Not changed:

- no `replaceAll` translator;
- no route-local jargon cleanup function;
- no new product semantics invented in React;
- no claim that Content Planner UX is now fully clean.

## Verification

Commands:

```bash
rtk pnpm --dir apps/dashboard typecheck
rtk pnpm --filter @wilq/dashboard test -- ContentDiagnosticSurface --testTimeout=15000
```

Result:

- dashboard typecheck passed;
- focused dashboard tests passed: 6 files, 36 tests.

Browser proof:

- `.local-lab/proof/content-label-registry-20260625/content-planner.after-restart.text.txt`

## Browser Finding

The shared label registry is active for selected labels, for example:

- `GOOGLE SEARCH CONSOLE / ODŚWIEŻENIE`;
- `SPRAWDZENIE LUK AHREFS`;
- `wersja robocza istniejącej treści`.

However, Content Planner still exposes marketer-facing jargon from backend/API
summaries and composed payload detail rows, including:

- `inventory`;
- `target_site_*`;
- `draft/staging`;
- `review`;
- raw blocker keys like `human_confirm_before_wordpress_write`;
- lower-section action/debug language.

## Next Correct Slice

Do not patch these leaks with UI-side replacement.

Add a typed Content condensation view-model/API contract that returns
marketer-ready fields:

- `decision`;
- `why_it_matters`;
- `safe_next_action`;
- `missing_inputs`;
- `blocked_claims`;
- `evidence_summary`;
- `measurement_plan`.

React should render that contract and keep raw traceability in technical
details only.
