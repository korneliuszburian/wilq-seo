# Dashboard Audit Active Slice

Last updated: 2026-06-18.

This file preserves the active dashboard audit while Goal 001 is open. Keep it
updated when new route evidence is collected or a problem is fixed.

## Runtime Proof Method

Agent-browser requires a short runtime directory on this WSL host:

```bash
mkdir -p /tmp/ab-krn
XDG_RUNTIME_DIR=/tmp/ab-krn TMPDIR=/tmp/ab-krn agent-browser open http://127.0.0.1:5173/command-center
```

The default `XDG_RUNTIME_DIR=/run/user/1000/` is not usable here, and a
repo-local runtime dir creates a Chromium socket path that is too long.

Partial text proof exists under:

```txt
.local-lab/proof/dashboard-audit/text/
```

Routes collected before the interrupted scrape:

- `/command-center`
- `/opportunities`
- `/actions`
- `/workflows`
- `/ads-doctor`
- `/ads-doctor/search-terms`
- `/ads-doctor/custom-segments`
- `/ads-doctor/demand-gen`
- `/ads-doctor/scaling`
- `/ads-doctor/seasonality`
- `/ads-doctor/recommendations`
- `/ga4`
- `/seo-gsc`

The scrape was intentionally stopped before every route completed. Resume from
`/ahrefs`, `/localo`, `/merchant`, `/content-planner`, `/content-inventory`,
`/social-publisher`, `/google-sheets`, `/knowledge`, `/codex-runs`,
`/security`, and `/settings`.

## Confirmed Problems

### 1. Generic Opportunities Surface Is Outdated

Evidence:

- `.local-lab/proof/dashboard-audit/text/opportunities.txt`
- `.local-lab/proof/dashboard-audit/text/actions.txt`
- many generated Ads subroutes such as
  `.local-lab/proof/dashboard-audit/text/ads-doctor__search-terms.txt`

Observed copy:

- `Google Ads connector ready for first search-term refresh`
- `GSC connector ready for query/page opportunity refresh`
- `GA4 connector ready for behavior diagnostics refresh`
- `No performance metrics have been collected in this response.`
- `Connector ... has credential names available`
- stale `oauth_error=invalid_grant` / OAuth repair content appears in generic
  actions/opportunities even though live Google Ads campaign facts exist.

Decision:

- `/opportunities` and generic generated routes must stop showing
  readiness-only connector opportunities as marketing insight.
- Either replace them with API-backed tactical/diagnostic view models or label
  them as lower-level diagnostic inventory outside marketer first-flow.

### 2. Command Center Still Shows Internal Ranking Labels

Evidence:

- `.local-lab/proof/dashboard-audit/text/command-center.txt`

Observed copy:

- `PRIORITY 10`, `PRIORITY 12`, `PRIORITY 14`, etc.
- `SEO / GSC / ODŚWIEŻENIE TREŚCI / PRIORITY 17`
- `GA4 / JAKOŚĆ LANDING PAGE / PRIORITY 25`

Decision:

- Replace visible `priority N` with marketer wording such as:
  - `Najpierw`
  - `Wysoki priorytet`
  - `Do sprawdzenia`
  - `Niżej w kolejce`
- Keep numeric priority internal only.

### 3. GA4 `(not set)` Is A Tracking Gap, Not A Marketing Tactic

Evidence:

- `.local-lab/proof/dashboard-audit/text/command-center.txt`
- `.local-lab/proof/dashboard-audit/text/ga4.txt`

Observed copy:

- `GA4: (not set) / (not set)`
- `Landing (not set) z (not set) i kampanii (not set)`
- `GA4: (not set) / google / organic`

Interpretation:

- `(not set)` in GA4 means the dimension is missing/unassigned in the report
  context. It can indicate tracking, attribution, landing-page or campaign
  tagging gaps.
- It must not be presented as a normal landing-page optimization tactic.

Decision:

- Move `(not set)` items into a tracking-quality blocker/diagnostic group.
- Display them as `Problem pomiaru GA4: landing/source/campaign = (not set)`.
- Do not include `(not set)` rows in top "konkretne taktyki" unless the card is
  explicitly a measurement repair task.

### 4. Demo Script Is Not A Marketer First-Screen Section

Evidence:

- `.local-lab/proof/dashboard-audit/text/command-center.txt`

Observed copy:

- `Demo dla marketera`
- `Krok 1`, `Krok 2`, etc.
- long evidence lists under every demo step.

Decision:

- Remove or collapse `Demo dla marketera` from the main Command Center flow.
- Keep demo proof as dev/test route or handoff artifact, not daily marketer UI.

### 5. Metric Inventory Shows Probe/Debug Facts

Evidence:

- `.local-lab/proof/dashboard-audit/text/command-center.txt`

Observed copy:

- `localo_mcp_oauth_probe`
- `access_token_present`
- `authorization_code_supported`
- `mcp_initialize_status`
- raw repeated `content_object_count` facts.

Decision:

- First-screen metric inventory should hide probe/debug facts by default.
- Localo OAuth probe details belong in `/localo` or `/settings`.
- Repeated metric facts should be grouped/deduped by connector/name/dimensions.

### 6. Connector Freshness Surface Contradicts Live Evidence

Evidence:

- `.local-lab/proof/dashboard-audit/text/command-center.txt`

Observed copy:

- `Freshness: unknown - Credential presence only; no external API call was made`
  for connectors that also have fresh/live refresh evidence elsewhere.

Decision:

- Connector freshness must derive from latest refresh/evidence where available,
  not only from static credential status.
- If a connector has live metric facts, do not show credential-only freshness on
  the same first-screen route.

### 7. Workflows Route Is Mostly Registry Placeholder

Evidence:

- `.local-lab/proof/dashboard-audit/text/workflows.txt`

Observed copy:

- repeated `Workflow definition runs against WILQ API and records evidence/action IDs`
- one queued local smoke run with `Evidence: 0`, `Actions: 0`, `Errors: 0`

Decision:

- `/workflows` must show runnable/useful workflow status or be demoted as
  internal registry.
- The marketer should not see 15 generic workflow definitions as product value.

### 8. Ads Doctor Main Route Is Better But Still Verbose

Evidence:

- `.local-lab/proof/dashboard-audit/text/ads-doctor.txt`

Good:

- Shows live Google Ads metrics and explicitly blocks search-term waste, CPA,
  ROAS and apply paths.

Problems:

- Repeats many `clicks=3` and long evidence lists.
- Still says `Po naprawie OAuth` in one search-term next step even though OAuth
  is already repaired.
- `Bezpieczne akcje Ads` mentions repair action wording even though active
  repair is filtered out in live state.

Decision:

- Dedupe repeated metric facts.
- Remove stale OAuth repair phrasing from live Ads sections.
- Keep search-terms/recommendations as explicit missing read contracts.

## Completed In This Slice

- `Command Center` no longer renders the old `Kandydaci działań API` panel.
- `Command Center` no longer fetches `/api/marketing/brief` on first screen.
- `Dzisiejszy panel operatora` is now a compact status/header only. The
  duplicated detailed decision cards were removed; detailed next moves live in
  one place: `Plan działań marketera`.
- `Command Center` API now returns an empty `demo_script`; the old
  `Demo dla marketera` proof sequence must stay out of the first-screen daily
  marketer flow.
- GA4 `(not set)` rows are classified as `tracking_gap` tactical items and are
  hidden from the top Command Center tactics list. They belong in GA4
  measurement diagnostics, not normal landing-page tactics.
- Visible numeric priority labels are replaced with marketer wording:
  `najpierw`, `wysoki priorytet`, `do sprawdzenia`, `niżej w kolejce`.
- `/api/opportunities` no longer exposes `connector_configured` metric names or
  English `Run a read-only...` copy. It is still a lower-level technical
  inventory and needs a broader replacement in the marketer flow.
- First-screen metric inventory hides Localo OAuth/probe/debug facts such as
  `localo_mcp_oauth_probe`, `access_token_present`, and
  `mcp_initialize_status`.
- First-screen connector blocker copy no longer renders credential-only
  freshness text such as `Freshness: unknown - Credential presence only`.
- Command Center composes Ads, Merchant, Content and GA4 diagnostics in parallel
  and reuses one tactical queue build for count + action plan.
- `Command Center` API response now sends empty `sections` and empty
  `active_actions`; `/api/opportunities` and `/api/actions` remain available.
- Dashboard tests now assert that `Priorytety dnia`, `Budżet i ryzyko wydatków`,
  `Dzisiejszy brief WILQ`, `Kandydaci działań API`, `connector_configured`,
  `No performance metrics have been collected`, `Run a read-only`,
  `Demo dla marketera`, `priority N` and `GA4: (not set)` are absent from
  Command Center.

## Latest Focused Verification

Passed:

```bash
uv run ruff check wilq/briefing/command_center.py apps/api/wilq_api/main.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py apps/api/wilq_api/main.py
uv run pytest tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief tests/test_api_contracts.py::test_opportunities_are_derived_from_evidence_and_rule_mappings -q
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
```

Important caveat:

- Do not run `ruff` on TS/TSX files. Use `pnpm --filter @wilq/dashboard lint`
  for dashboard TypeScript.

## Performance Measurements

Latest live-server measurement after parallel Command Center composition:

```txt
/api/dashboard/command-center run=1 code=200 time=2.025s size=22604
/api/dashboard/command-center run=2 code=200 time=2.317s size=22604
/api/dashboard/command-center run=3 code=200 time=1.951s size=22604
```

Latest browser proof:

```txt
.local-lab/proof/dashboard-audit/text/command-center-final-slice.txt
```

Confirmed absent in that proof:

- duplicated operator-brief cards such as `Merchant: feed/product issues do przeglądu`,
- `Demo dla marketera`,
- visible `PRIORITY N`,
- `GA4: (not set)` and `Problem pomiaru GA4: (not set)`,
- `localo_mcp_oauth_probe`, `access_token_present`, `mcp_initialize_status`,
- `Freshness: unknown`, `Credential presence only`,
- `connector_configured`, `Run a read-only`.

Measured with current Python/FastAPI code through `TestClient`:

```txt
/api/dashboard/command-center status=200 time=6.310s size=28453
/api/marketing/tactical-queue status=200 time=0.754s size=81947
/api/metrics?limit=80 status=200 time=0.083s size=30264
```

Earlier live-server measurement before endpoint trimming:

```txt
/api/dashboard/command-center status=200 time=5.576s size=66251
/api/marketing/tactical-queue status=200 time=0.678s size=81947
/api/metrics?limit=80 status=200 time=0.079s size=30264
```

Interpretation:

- Payload size improved by removing unused `sections`, `active_actions`, demo
  script and duplicated first-screen cards.
- Latency improved materially after parallel diagnostic composition, but
  Command Center still depends on expensive diagnostic builders. Next
  architecture step should be a dedicated lightweight daily-decision endpoint
  or cache/materialized view, not more frontend `useMemo` patches.

## Frontend Architecture Research Notes

Sources checked on 2026-06-18:

- TanStack Query official docs: parallel queries should run at the same time to
  maximize fetching concurrency.
- TanStack Query dependent queries docs: dependent query waterfalls hurt
  performance; restructure backend/API to avoid serial client waterfalls when
  feasible.
- TanStack Router official data-loading docs: route-level async dependencies
  should be fetched and fulfilled as early as possible, in parallel; router is
  the right coordination layer when it knows the destination route.
- React official `useMemo` docs: memoize expensive calculations between renders,
  but do not use memoization as a substitute for a simpler data model.

Command Center decision:

- Do not solve this by sprinkling `useMemo` everywhere.
- Keep one canonical API-backed view model for first-screen decisions.
- Defer lower-priority diagnostics below the fold and out of the critical route
  path.
- Remove duplicated cards before optimizing render performance.
- Prefer backend/view-model consolidation over more parallel client queries when
  the UI needs one coherent daily decision object.

## Next Implementation Queue

0. Preserve the 2026-06-18 direction: WILQ is not a connector dashboard. The
   current slice is dashboard-to-Codex usefulness: real marketer prompt ->
   correct WILQ skill -> WILQ API context-pack -> Polish evidence-backed
   diagnosis/action preview.
1. Keep WILQ skill trigger descriptions marketer-intent based. Required prompt
   patterns include:
   - `pokaż przestrzeń do polepszenia adsów w Ekologus`,
   - `znajdź ostatnie kampanie i ich efekty`,
   - `które treści odświeżyć`,
   - `czy feed produktowy jest OK`,
   - `sprawdź jakość ruchu z GA4`,
   - `jak poprawić lokalną widoczność`.
2. Command Center action-plan cards must carry `skill_id`, `codex_prompt`,
   `codex_context_endpoint`, `expected_codex_output`, evidence IDs, action IDs
   and blocked claims. This is the explicit bridge from dashboard to Codex.
3. Reframe Command Center as a decision cockpit:
   `co widzę`, `co to znaczy`, `co zrobić teraz`, `czego nie wolno twierdzić`,
   `jak Codex może pomóc`.
4. Remove raw tactical queue and raw metric inventory from first-screen Command
   Center. Keep those in dedicated diagnostic routes unless condensed into a
   decision card.
5. Finish route scrape for remaining dashboard routes and append findings here.
6. Replace generic `/opportunities` and generic generated route surfaces with
   marketer-useful API view models or demote them to diagnostics.
7. Replace generic `/opportunities` with marketer-useful workflow queue or
   demote it fully to settings/diagnostics.
8. Continue reducing Command Center latency by introducing a dedicated
   lightweight daily-decision view model or short-lived materialized cache.
