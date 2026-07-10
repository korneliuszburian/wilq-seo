# 2026-07-08 Full Repo Senior Code Audit

This audit turns the pasted full-repository review prompt into a concrete
cleanup graph. It is intentionally blunt. The target is not "more tests" or
"more screens"; the target is senior-grade WILQ: API-owned product logic,
React as a typed renderer, small Python domain modules, useful tests, honest
docs and Beads that force the cleanup order.

## FILE_COVERAGE_PROOF

Machine-readable manifest:

- `.local-lab/audits/full-repo-senior-code-audit-20260708/manifest.jsonl`
- `.local-lab/audits/full-repo-senior-code-audit-20260708/summary.json`

Method used:

- `rtk git ls-files -z` for tracked files.
- `rtk git status --short -z` for modified/deleted/untracked worktree files.
- `rtk git ls-files --others --exclude-standard -z` for non-gitignored
  untracked project files.
- A local manifest script read every present file's bytes, recorded size,
  SHA-256 prefix, type, line count for text, audit category and role.
- Binary/assets were represented by metadata. No secret values were printed.

Summary from `summary.json`:

| Metric | Count |
| --- | ---: |
| Total files mapped | 647 |
| Tracked files | 644 |
| Untracked nonignored files | 3 |
| Modified/deleted/status entries | 50 |
| Text files content-read for manifest hash/line-count | 633 |
| Binary/asset files metadata-inspected | 11 |
| Deleted files in working tree | 3 |
| Skipped/unreadable files | 3 |

Skipped files:

| Path | Reason |
| --- | --- |
| `apps/dashboard/e2e/content-planner-layout.spec.ts` | Deleted in working tree; content unavailable from filesystem. |
| `apps/dashboard/src/routes/ContentDiagnosticSurface.test.ts` | Deleted in working tree; content unavailable from filesystem. |
| `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx` | Deleted in working tree; content unavailable from filesystem. |

Manifest category counts:

| Category | Count |
| --- | ---: |
| `python_runtime` | 201 |
| `python_test` | 75 |
| `docs_archive_audit` | 68 |
| `dashboard_runtime` | 60 |
| `skill` | 54 |
| `docs_current` | 46 |
| `api_runtime` | 38 |
| `script` | 33 |
| `dashboard_test` | 30 |
| `config` | 28 |
| `project_other` | 8 |
| `shared_schema_or_package` | 6 |

Coverage caveat: the manifest proves every file was mapped and read/inspected
for file coverage. The findings below are based on targeted human review of
runtime, dashboard, test, schema, skill, docs and script hotspots from that
manifest plus complexity output. The manifest is the complete file table; this
document is the prioritized senior cleanup verdict.

## EXECUTIVE_VERDICT

This repo is not currently senior-grade. It has serious product ambition and a
lot of useful safety machinery, but the implementation has accumulated giant
files, route-level React workbenches, schema monoliths, omnibus API tests,
historical docs drift and placeholder routes. A senior team could extend it,
but only by paying down structure first; otherwise every product improvement
will keep landing in the same frozen files.

The tests are both useful and harmful. They catch real WILQ risks: missing
evidence IDs, unsafe writes, stale connectors, blocked claims and Polish
operator copy. But the biggest test files are now slop engines:
`tests/test_api_contracts.py` is 21,233 lines and
`apps/dashboard/src/routes/App.test.tsx` is 9,205 lines. They preserve huge
fixtures, route strings and implementation wording, making refactors expensive
without proving marketer usefulness proportionally.

Dashboard/API/skills are directionally aligned around WILQ API, but not cleanly
enough. React still assembles too much meaning in route files, skills still
carry heavy smoke harness logic, docs still preserve old route names, and the
API schema layer is too centralized. The architecture is API-first in intent;
the code shape is still "everything knows everything" in several places.

## SCORING

| Area | Score | Reason |
| --- | ---: | --- |
| Repository architecture | 4 | Product boundaries exist, but monolith files and old surfaces dominate change cost. |
| API contracts | 6 | Strong evidence/action contracts, but `wilq/schemas.py` and shared TS schemas are overgrown. |
| Python maintainability | 4 | Runtime works but largest modules are not senior-extensible. |
| Dashboard maintainability | 3 | Route files and tests are too large; placeholder surfaces remain reachable. |
| Dashboard usefulness | 6 | `/content-workflow` is becoming useful, but many surfaces are still report/admin/placeholder views. |
| Test quality | 3 | Good risk coverage buried in test theater and giant fixtures. |
| Skill quality | 6 | Skills enforce evidence and Polish output, but smoke scripts are too complex. |
| Docs truthfulness | 4 | Current docs are improving, but progress/eval ledgers preserve stale `/content-planner` truth. |
| Safety without guard theater | 6 | Write safety is strong; visible safety/copy can still overwhelm marketer decisions. |
| Readiness for senior development speed | 3 | Any serious slice risks touching frozen files and 10k-line tests. |

## OFFICIAL_STANDARD_BASELINE

React baseline used for this audit:

- React's "Keeping Components Pure": route/component render logic must be
  deterministic from props/state, not a place for hidden mutation or business
  side effects. Source: `https://react.dev/learn/keeping-components-pure`.
- React's "You Might Not Need an Effect": derived values should generally be
  calculated during render; effects should not synchronize redundant state.
  Source: `https://react.dev/learn/you-might-not-need-an-effect`.
- React's `useMemo` reference: memoization is not architecture; prefer local
  state, pure rendering and removing unnecessary effects before adding memo.
  Source: `https://react.dev/reference/react/useMemo`.
- React's "Separating Events from Effects": event handlers represent user
  interactions; effects synchronize with external systems. Source:
  `https://react.dev/learn/separating-events-from-effects`.

Python baseline used for this audit:

- Python `dataclasses` docs: use explicit data structures for clear data
  contracts when behavior does not need a heavy object hierarchy. Source:
  `https://docs.python.org/3/library/dataclasses.html`.
- Python `typing` docs: use aliases and explicit types to keep complex nested
  contracts readable instead of repeating unreadable shapes everywhere. Source:
  `https://docs.python.org/3/library/typing.html`.
- Python `unittest` docs and CPython test guidance: tests should be organized
  around named behavior, with setup/teardown only where needed and public API
  boundaries explicit. Source: `https://docs.python.org/3/library/unittest.html`.

Translated into WILQ rules:

- React routes are orchestration shells; domain hooks and components do the
  rest.
- Derived UI rows are render-time values, not synchronized state.
- Backend/API owns marketer decisions, blockers, labels and evidence meaning.
- Python modules own one domain concept; frozen monoliths get compatibility
  exports only.
- Tests prove product behavior and failure modes, not incidental strings.

## TOP_25_FINDINGS

1. **Frozen-growth gate is currently violated.**  
   Evidence: `scripts/audit_complexity.py --summary --limit 18` reports 51
   changed files, 77 changed-code budget violations, and frozen-growth changes
   in `tests/test_api_contracts.py` and `wilq/schemas.py`.
   This is bad because the repo already knows which files must stop growing,
   yet current work grows them anyway. Senior move: enforce the gate before new
   features, split behavior out of frozen files. Action: rewrite/split. Beads:
   `wilq-seo-c2lf`, then `wilq-seo-50wa`, `wilq-seo-b4kg`.

2. **`tests/test_api_contracts.py` is no longer a maintainable test module.**  
   Evidence: 21,233 physical lines; complexity audit reports
   `test_ads_diagnostics_exposes_live_campaign_metric_facts` at line 11111 as
   2,914 lines, `test_google_ads_vendor_read_uses_oauth_and_search_stream` at
   line 9512 as 748 lines and `test_content_diagnostics_exposes_query_page_inventory_queue`
   at line 15818 as 633 lines. Imports at lines 31-148 pull GA4, Localo,
   Ads, Ahrefs, Merchant, content diagnostics and connectors into one file.
   Senior move: split by domain and replace giant fixtures with focused
   behavior factories. Action: split/rewrite. Bead: `wilq-seo-50wa`.

3. **`apps/dashboard/src/routes/App.test.tsx` is a dashboard omnibus.**  
   Evidence: 9,205 lines. It contains long fixture literals around lines
   7366-7560 asserting exact `/content-workflow` copy and another hidden
   competitor fixture around lines 6397-6405/9080.
   This is bad because route tests preserve strings and dead IA, not just
   behavior. Senior move: split by route and test first-screen decisions,
   blockers and technical-details boundaries. Action: split. Bead:
   `wilq-seo-pidl`.

4. **`ContentWorkflowSurface.tsx` is a route god file.**  
   Evidence: 3,543 lines. It declares route state at lines 95-104, layout and
   legacy detail panels at 279-364, editor state at 412-445 and 1524-1570,
   mutation hooks at 1852-1915, action request builders at 1915-2003, and
   safety/copy helpers through 3293-3541.
   This violates React guidance: keep render pure, keep transient state local,
   compute derived values during render/useMemo only when useful, and split
   components/hooks around responsibilities. Senior move: route shell plus
   domain hooks and presentational workbench components. Action: split. Beads:
   `wilq-seo-ho41`, blocked by `wilq-seo-d380` and `wilq-seo-i2qb`.

5. **`wilq/schemas.py` is a cross-domain schema monolith.**  
   Evidence: 5,435 lines. Connector models start around lines 54-281, Action
   models around 545-949, Knowledge models around 968-1366, and Ads/content/
   merchant/domain classes continue thousands of lines later.
   This is bad because every contract change risks import churn and frozen-file
   growth. Senior move: domain schema modules with a compatibility barrel.
   Action: split. Bead: `wilq-seo-b4kg`.

6. **`wilq/actions/service.py` centralizes unrelated action behavior.**  
   Evidence: 6,682 lines. `seed_core_prepare_actions` starts at line 224,
   Service Profile actions start at 592 and 707, `list_actions` at 852,
   Google Ads action construction at 922-1039, and complexity audit flags
   `seed_metric_action_candidates` at line 1106 as 467 lines.
   Senior move: registry/facade plus domain action modules. Keep
   ActionObject safety loop intact. Action: split. Bead: `wilq-seo-jnra`.

7. **`wilq/briefing/ads_diagnostics.py` is a monster diagnostic brain.**  
   Evidence: 7,620 physical lines. It imports dozens of Ads schema classes at
   lines 69-122, stores platform/source maps around lines 252-367, builds the
   whole diagnostics response in `build_ads_diagnostics` from line 376, and
   complexity audit flags `_ads_decision_queue` at line 5315 as 587 lines.
   Senior move: split account, campaign, budget, recommendations, search terms,
   negative keywords, custom segments, change history and labels; connect to
   ExpertRule/platform trap packs. Action: split. Bead: `wilq-seo-kgvy`.

8. **Shared TypeScript schemas are becoming another monolith.**  
   Evidence: `packages/shared-schemas/src/index.ts` is 4,156 lines and
   `packages/shared-schemas/src/contentWorkflow.ts` is 1,838 lines. Dashboard
   API imports dozens of schema and type names from the barrel at
   `apps/dashboard/src/lib/api.ts:2-146`.
   Senior move: domain entrypoints and a deliberate export map. Action: split.
   Bead: `wilq-seo-ksiq`.

9. **`apps/dashboard/src/lib/api.ts` is a typed boundary but too broad.**  
   Evidence: lines 217-566 expose command center, WordPress, actions, Ads,
   Merchant, content workflow, GA4 and action mutation calls in one file.
   The good part is Zod parsing; the bad part is one API module becoming a
   central dependency for every screen. Senior move: keep `apiGet/apiPost`
   shared, split domain clients. Action: split with shared schemas. Bead:
   `wilq-seo-ksiq`.

10. **Legacy `/content-planner` truth is still alive in docs/evals.**  
    Evidence: current `docs/dashboard-state.md:49` says the deleted route must
    not return. But `docs/PROGRESS.md:32` and `:78`, `docs/evals/skill-coverage-audit.md:13`,
    `docs/evals/skill-eval-ledger.md:1590`, `:1602`, `:2309`, `:2326`,
    `:3109`, `:3144`, `:9360` still preserve `/content-planner`.
    Senior move: active docs must use `/content-workflow`; old route references
    belong only to archive. Action: quarantine/delete. Beads:
    `wilq-seo-77b1`, `wilq-seo-co30`, `wilq-seo-i2qb`.

11. **Placeholder routes remain reachable and tested as product surfaces.**  
    Evidence: `surfaceRegistry.ts:195-255` keeps hidden placeholder Ads routes,
    `:283-310` keeps content inventory/google sheets placeholders, and
    `GenericSurface.tsx:1323-1377` renders placeholder explanations.
    This is honest copy, but still product surface sprawl. Senior move: hidden
    technical stubs only when a real API owner exists; otherwise delete until
    workflow exists. Action: quarantine. Bead: `wilq-seo-77b1`.

12. **Route registry is useful but now mixes IA, readiness, placeholder state
    and product truth.**  
    Evidence: `surfaceRegistry.ts:49-344` is the nav/route source of truth,
    with primary/secondary/hidden and status labels. This is better than
    scattering nav, but it can become a product-truth dumping ground.
    Senior move: keep route registry minimal; readiness lives in API/dashboard
    state docs, not static route metadata. Action: keep but prune. Beads:
    `wilq-seo-77b1`, existing `wilq-seo-3bst`.

13. **`GenericSurface.tsx` is too large for a generic fallback.**  
    Evidence: 1,534 lines. It renders multiple admin/technical modes, source
    health, knowledge, placeholder surfaces and route-specific behavior.
    Generic fallback files should be tiny. Senior move: split generic admin
    panels or delete generated placeholders. Action: split/quarantine. Beads:
    `wilq-seo-77b1`, `wilq-seo-d380`.

14. **React route components still carry business copy and safety semantics.**  
    Evidence: `ContentWorkflowSurface.tsx:3293-3417` contains safety text
    functions, including WordPress execution text at 3374-3395 and measurement
    safety at 3417. Some UI labels belong in API-owned view-model fields.
    Senior move: backend provides marketer labels and blocker summaries; React
    renders them. Action: rewrite boundary. Beads: `wilq-seo-d380`,
    `wilq-seo-ho41`.

15. **The content workbench has duplicate section editors.**  
    Evidence: `ContentPageWorkbench` creates editor state at 401-445 and
    `ContentSectionWritingWorkbench` repeats similar logic at 1524-1570.
    This is a React smell: duplicated local state and derived data in one route
    file. Senior move: one `useDraftSectionOverrides` hook and one editor
    component. Action: split. Bead: `wilq-seo-ho41`.

16. **Current worktree deletes old content planner files but does not finish
    the quarantine.**  
    Evidence: git status shows deleted
    `apps/dashboard/e2e/content-planner-layout.spec.ts`,
    `ContentDiagnosticSurface.test.ts` and `ContentDiagnosticSurface.tsx`.
    Remaining active docs/evals still reference the old route.
    Senior move: make this the first cleanup PR. Action: first PR. Bead:
    `wilq-seo-i2qb`.

17. **Skill smoke scripts are their own monoliths.**  
    Evidence: complexity audit reports
    `.agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py:60`
    `main` at 1,002 lines/288 branches, GSC at 491/132, Merchant at 371/118,
    Localo at 302/92 and Custom Segments at 292/72.
    Senior move: shared smoke harness plus declarative per-skill assertions.
    Action: split. Bead: `wilq-seo-0q74`.

18. **Skill eval proof is strong but can overstate usefulness.**  
    Evidence: `docs/evals/skill-eval-ledger.md:13-49` defines hard gates and
    score semantics; lines 657-770 describe score/rubric evolution and strong
    9/10 runs. This is useful, but it is still self/eval proof, not Wilku UAT.
    Senior move: skills summarize API-owned outputs; daily-check evals must
    validate that skills cannot invent product behavior. Action: keep/tighten.
    Existing Beads: `wilq-seo-v9ab.10`, plus `wilq-seo-0q74`.

19. **Docs are still too append-heavy for recovery.**  
    Evidence: `docs/PROGRESS.md` is 4,256 lines and contains many historical
    entries, including stale route names. `docs/CONTEXT.md:65` correctly warns
    not to infer readiness from route/API availability, but the progress file
    still makes recovery noisy.
    Senior move: current truth in short docs; history in archives/git. Action:
    prune/archive. Bead: `wilq-seo-co30`.

20. **Dashboard usefulness scores can hide UI slop.**  
    Evidence: `docs/dashboard-state.md:75` scores `/content-workflow` at 88%
    while admitting lower details are too long and cannot yet update existing
    dev draft/ACF row in place. Older docs also recorded `/content-planner`
    high scores despite later roast findings.
    Senior move: usefulness score must include screenshot and 30-second task
    review, not only API counts. Action: keep/tune. Existing Bead:
    `wilq-seo-3bst`.

21. **Content WordPress/ACF boundary is improving but not finished.**  
    Evidence: `docs/dashboard-state.md:39-49` requires generic ACF parsing and
    warns not to assume `flexible-home`; the route still has ACF preview and
    execution logic in `ContentWorkflowSurface.tsx:1287-1320`,
    `1428-1472`, `1551-1570`, `1776-1789`, `2477-2490`.
    Senior move: API-owned authoring profile and explicit current-vs-proposed
    ACF view-model. Action: split/refine. Bead: `wilq-seo-ho41`.

22. **Dashboard API/view-model overlap still exists.**  
    Evidence: `apps/dashboard/src/lib/api.ts:298-333` exposes content
    diagnostics, preflight, service profile, queue, snapshot and enrichment;
    `/content-workflow` consumes many surfaces. Good product intent, but it
    increases frontend composition pressure.
    Senior move: add a content workbench view-model if the route must assemble
    business meaning from multiple endpoints. Action: rewrite API boundary
    where needed. Bead: `wilq-seo-ho41`.

23. **Action detail is still too technical for marketer mode.**  
    Evidence: existing Bead `wilq-seo-3bst.21` already captures that
    `/actions/:actionId` forces ActionObject conditions, payloads and audit
    mechanics above the decision.
    Senior move: decision-first action detail with technical audit below fold.
    Action: rewrite. Existing Bead: `wilq-seo-3bst.21`.

24. **Python storage classes exceed class budget.**  
    Evidence: complexity audit lists `wilq/storage/local_state.py:38`
    `LocalStateStore` at 502 lines and `wilq/storage/metric_store.py:34`
    `DuckDbMetricStore` at 496 lines. They are not first PR material, but they
    are real infrastructure debt.
    Senior move: split persistence adapters by connector refresh, metric facts,
    action audit and workflow state. Action: later split. Add follow-up after
    schema/action splits if still hot.

25. **The repo has enough safety, but safety copy can become guard theater.**  
    Evidence: safety panels and labels are spread through
    `ContentWorkflowSurface.tsx:2938-3417`, Action models at
    `wilq/schemas.py:545-949`, and action service payload previews in
    `wilq/actions/service.py:224-568`.
    Senior move: keep concrete risk controls (evidence IDs, freshness, no
    writes without ActionObject), remove duplicated mechanism explanations
    from marketer first screens. Action: keep/rewrite. Beads:
    `wilq-seo-d380`, `wilq-seo-3bst.11`, `wilq-seo-3bst.21`.

## TEST_THEATER_AUDIT

Oversized/brittle test files:

| File | Size | Problem | Plan |
| --- | ---: | --- | --- |
| `tests/test_api_contracts.py` | 21,233 lines | Cross-domain mega-test, huge seeders, giant handlers, implementation strings. | Split by domain via `wilq-seo-50wa`. |
| `apps/dashboard/src/routes/App.test.tsx` | 9,205 lines | Dashboard omnibus with route/copy fixtures and hidden placeholders. | Split via `wilq-seo-pidl`. |
| `packages/shared-schemas/src/index.test.ts` | 2,456 lines | Shared schema test mass around one barrel. | Split with `wilq-seo-ksiq`. |
| `apps/dashboard/src/routes/ContentWorkflowSurface.test.tsx` | 2,169 lines | Necessary coverage but tied to one route god file. | Split alongside `wilq-seo-ho41`. |
| `apps/dashboard/src/routes/ActionDetailRoute.test.tsx` | 2,130 lines | Likely preserving current technical action detail shape. | Rework with `wilq-seo-3bst.21`. |
| Skill smoke scripts under `.agents/skills/*/scripts` | Multiple 200-1,000 line `main` functions | Test harness complexity becomes product risk. | Extract shared harness via `wilq-seo-0q74`. |

Tests protecting obsolete UI:

- Deleted in worktree but still part of the coverage story:
  `apps/dashboard/e2e/content-planner-layout.spec.ts`,
  `ContentDiagnosticSurface.test.ts`, `ContentDiagnosticSurface.tsx`.
- Current docs/evals still preserve `/content-planner` assertions or proof:
  `docs/evals/skill-coverage-audit.md:13`,
  `docs/evals/skill-eval-ledger.md:1590`, `:1602`, `:2309`, `:2326`,
  `:3109`, `:3144`, `:9360`.

Delete or replace:

- Delete active `/content-planner` E2E/component tests.
- Replace `App.test.tsx` broad route assertions with route-local behavior
  tests: first-screen decision, blocker, next safe action, technical details
  below fold.
- Replace `tests/test_api_contracts.py` giant fixtures with domain factories
  and contract-specific tests.

Keep:

- Evidence/source connector guards.
- Secret redaction tests.
- ActionObject validate/preview/review/confirm/audit safety tests.
- WordPress draft-only and publish/destructive-write blockers.
- Polish operator output guards, but only if they test user-visible behavior,
  not arbitrary string snapshots.

## DASHBOARD_ARCHITECTURE_AUDIT

Route-by-route:

| Route | Verdict | Cleanup |
| --- | --- | --- |
| `/command-center` | Keep as cockpit; risk is becoming a summary of everything. | Route into one work item; avoid more cards. Existing `wilq-seo-3bst`. |
| `/content-workflow` | Keep as primary content workspace; current route file is too large. | Split with `wilq-seo-ho41`; add explicit dev target and ACF current-vs-proposed. |
| `/content-planner` | Delete/quarantine; old report-like route. | First PR `wilq-seo-i2qb`. |
| `/content-inventory` | Placeholder; concept belongs inside content workbench for now. | Hide/delete until API-owned inventory workbench exists. `wilq-seo-77b1`. |
| `/actions` | Keep queue; make details marketer-first. | Existing `wilq-seo-3bst.21`. |
| `/opportunities` | Overlaps with Command Center/Actions. | Merge into decision/action queue later via `wilq-seo-3bst.5`. |
| `/ads-doctor` | API value exists; screen can overload. | Park until diagnostics queue pattern. Existing `wilq-seo-3bst.7`. |
| Ads hidden drilldowns | Mostly placeholder/experimental. | Keep hidden or delete; no primary nav. `wilq-seo-77b1`. |
| `/merchant`, `/ga4`, `/localo`, `/ahrefs` | Useful drilldowns, not primary operating system. | Convert to prioritized queues only when current content slice is stable. |
| `/knowledge`, `/service-profile` | Admin/review support, not daily writing cockpit. | Feed claims into content workbench, keep owner-review mode. |
| `/workflows`, `/system`, `/security`, `/codex-runs` | Technical/admin. | Keep below marketer mode. |
| `/social-publisher`, `/google-sheets` | Experimental/placeholder. | Keep hidden until contracts are real. |

React standards to enforce:

- Route shell owns routing and query composition only.
- Domain hook owns screen data normalization without inventing business truth.
- Presentational components render typed props.
- Local editor/form state stays local; duplicated editor state is extracted.
- Derived lists are computed during render or `useMemo` only when expensive.
- Effects should synchronize with external systems only, not maintain redundant
  derived state.
- Technical audit details are disclosure components, never the first viewport.
- Prefer explicit components over generic card factories where product meaning
  differs.

Primary content workspace split:

- `ContentWorkflowSurface.tsx` -> route shell.
- `useContentWorkflowData`.
- `useDraftSectionOverrides`.
- `ContentWorkbenchHeader`.
- `SourceStatusStrip`.
- `WorkItemSelector`.
- `PublicPageSectionMap`.
- `DevTargetSelector`.
- `AcfCurrentVsProposedPanel`.
- `DraftSectionEditor`.
- `ProofClaimSummary`.
- `LegacyDetailsDisclosure`.

## API_AND_SCHEMA_AUDIT

Main monoliths:

- `wilq/schemas.py`: split into domain schema modules; keep compatibility
  re-export temporarily.
- `packages/shared-schemas/src/index.ts`: split into domain entrypoints.
- `packages/shared-schemas/src/contentWorkflow.ts`: split WordPress/ACF,
  workflow step, draft package, claim ledger and authoring contracts if it
  keeps growing.
- `apps/dashboard/src/lib/api.ts`: split domain API clients after shared schema
  split.

Overlapping endpoints:

- Content screen composes diagnostics, preflight, service profile, queue,
  snapshot, enrichment, WordPress authoring profile and action state. If the
  route continues to assemble business meaning, introduce a backend content
  workbench view-model.
- Actions/opportunities/command center overlap as task queues. The API should
  define one canonical decision/action queue or make their roles explicit.

Missing/weak contracts:

- Current-vs-proposed ACF values for dev draft updates.
- Explicit public-to-dev target selection.
- Dashboard job state for stale-source refresh beyond first settings slice.
- Daily-check `ExpertRule`/rule IDs for BDOS-class operating knowledge
  already captured by Goal 006 Beads.

## PYTHON_RUNTIME_AUDIT

Connectors:

- Google Ads client is large; keep it after Ads diagnostics split unless it
  blocks work.
- WordPress client/authoring is active product-critical; preserve generic ACF
  parsing and public/dev separation.
- Vendor read adapters should stay read-only and redacted.

Actions:

- ActionObject model is the right safety primitive.
- `wilq/actions/service.py` must stop being the central action warehouse.
- Extract seeders and mutation readiness without weakening validate -> preview
  -> human review -> confirm -> audit.

Content workflow:

- Content workflow API is useful but should not force React to compose business
  meaning from too many endpoints.
- Keep WordPress draft-only, no destructive updates, no publish.

Jobs/storage:

- Storage classes are large but not first PR. Revisit after schema/action
  splits.

Safety boundaries:

- Under-engineered risks are mostly controlled: evidence IDs, source connectors
  and ActionObject blockers exist.
- Over-engineered risk is UI/smoke/test ceremony that makes a marketer decode
  mechanics before a decision.

## SKILLS_AND_EVALS_AUDIT

Skill inventory:

- `wilq-daily-command`: useful operator entry point; should consume future
  DailyCheckResult.
- `wilq-content-operator`: valuable but should not require normal users to
  understand output-contract mechanics.
- `wilq-content-strategist`, `wilq-gsc-content-doctor`, `wilq-ahrefs-gap-finder`:
  useful SEO/content reviewers; must keep GSC/WordPress cross-check API-owned.
- `wilq-ads-doctor`, `wilq-campaign-builder`, `wilq-custom-segments`,
  `wilq-demand-gen-operator`: must not become Ads product brain; rules belong
  in API ExpertRule/platform packs.
- `wilq-ga4-analyst`, `wilq-merchant-feed-operator`, `wilq-localo-operator`:
  useful diagnostic skills, but need reusable smoke harness.
- `wilq-social-publisher`: correctly review-only; duplicate-free and publish
  claims stay blocked.

Eval problem:

- Evals prove format, evidence and blockers. They do not prove real Wilku
  usefulness by themselves.
- Smoke scripts are too complex and duplicate API contract reading.

Cleanup:

- Extract shared smoke harness: API health, context-pack calls, evidence/source
  assertions, ActionObject validation, Polish visible fields.
- Keep skill instructions small: endpoint, evidence requirement, answer shape,
  safety rule.
- Daily-check skills should summarize API-owned DailyCheckResult, not invent
  recommendations.

## DOCS_AND_PRODUCT_TRUTH_AUDIT

Current source of truth map:

- Product/API behavior: WILQ API contracts and typed schemas.
- Dashboard current state: `docs/dashboard-state.md`.
- Active execution plan: `PLANS.md`.
- Recovery index: `docs/CONTEXT.md`.
- Operational task graph: Beads.
- Historical proof: `docs/audits`, `docs/handoffs`, `docs/progress/archive`,
  git history.

Drift:

- `docs/PROGRESS.md` is too long and contains stale `/content-planner`
  references.
- `docs/evals/skill-coverage-audit.md` has stale `/content-planner` next step.
- `docs/evals/skill-eval-ledger.md` is valid history, but it should not be
  treated as current product truth.
- `docs/dashboard-state.md` is the best current map, but readiness scores must
  be treated as smoke signals, not UAT proof.

Archive/delete:

- Do not delete historical audits. Mark active/current docs clearly and prune
  recovery docs.
- Archive route-specific handoffs that preserve `/content-planner` as current
  workflow.

## DELETE_OR_QUARANTINE_LIST

| Priority | File/route | Action | Blast radius |
| --- | --- | --- | --- |
| P0 | `/content-planner` active route concept | Delete/quarantine; `/content-workflow` is primary. | Route registry, docs, E2E, skill eval references. |
| P0 | `apps/dashboard/e2e/content-planner-layout.spec.ts` | Delete; already deleted in worktree. | E2E suite update. |
| P0 | `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx` | Delete; already deleted in worktree. | App route imports, tests, docs. |
| P0 | `apps/dashboard/src/routes/ContentDiagnosticSurface.test.ts` | Delete; already deleted in worktree. | Dashboard tests. |
| P0 | Active `/content-planner` mentions in current docs/evals | Replace or archive. | Recovery/eval docs only. |
| P1 | Hidden Ads placeholder routes | Keep hidden with blocker copy or delete until API workflow exists. | Route registry/generic surface tests. |
| P1 | `GenericSurface` placeholder sections | Split or remove generated placeholders. | Hidden/admin routes. |
| P1 | Stale route assertions in `App.test.tsx` | Delete/replace. | Dashboard test split. |

## SPLIT_REFACTOR_LIST

| File | Split into | Do not abstract |
| --- | --- | --- |
| `ContentWorkflowSurface.tsx` | Route shell, hooks, workbench panels, draft editor, ACF panel, proof/claim summary. | Do not create one generic card factory for all panels. |
| `App.test.tsx` | Shell/nav, command center, content workflow, actions, settings, diagnostics tests. | Do not preserve exact long copy fixtures. |
| `tests/test_api_contracts.py` | Security, actions, Ads, Merchant, GA4, Localo, Ahrefs, command center, content tests. | Do not build one giant shared fixture object. |
| `wilq/schemas.py` | `schemas/connectors.py`, `actions.py`, `ads.py`, `merchant.py`, `ga4.py`, `content.py`, `knowledge.py`, `command_center.py`. | Do not break public imports in one PR. |
| `wilq/actions/service.py` | Registry, seeders, review gates, mutation readiness, domain action modules. | Do not weaken ActionObject safety. |
| `ads_diagnostics.py` | Account, campaigns, budgets, recommendations, search terms, ngrams, negatives, custom segments, change history, labels. | Do not split into tiny files without domain ownership. |
| `packages/shared-schemas/src/index.ts` | Domain entrypoints and barrel exports. | Do not make dashboard import raw backend internals. |
| Skill smoke scripts | Shared smoke harness and declarative per-skill checks. | Do not move product logic into smoke helpers. |
| `docs/PROGRESS.md` | Current short readout plus archive. | Do not copy Beads into markdown TODOs. |

## SENIOR_REBUILD_PLAN

1. **Publish and freeze the audit baseline.**  
   Goal: final audit and issue graph are canonical.  
   Files: this audit, Beads `wilq-seo-c9h9`, manifest artefacts.  
   Proof: `bd show wilq-seo-c9h9`, `bd dep cycles --json`, manifest summary.

2. **First PR: remove legacy content planner surface.**  
   Goal: stop preserving obsolete UI.  
   Files: route registry, App route, deleted content planner E2E/component
   tests, current docs/eval route refs.  
   Keep tests: `/content-workflow` route and Command Center links.  
   Remove tests: old `/content-planner` tests.  
   Proof: `rg content-planner` active refs are archive-only, dashboard
   typecheck/tests pass.

3. **React standards and content workbench split.**  
   Goal: route shell plus typed components/hooks.  
   Files: `ContentWorkflowSurface.tsx`, new content-workflow components/hooks,
   `ContentWorkflowSurface.test.tsx`.  
   Proof: route file under budget, public/dev/ACF draft-only tests pass,
   screenshot shows first-screen decision.

4. **Dashboard test split.**  
   Goal: replace `App.test.tsx` omnibus.  
   Files: route-local dashboard tests and shared test utilities.  
   Proof: no 9k-line dashboard test; focused behavior tests pass.

5. **Python freeze gate and standards.**  
   Goal: no new behavior in frozen monoliths.  
   Files: standards doc/audit appendix, `scripts/audit_complexity.py` if needed.  
   Proof: `rtk uv run python scripts/audit_complexity.py --changed` passes or
   documented extraction slices are active.

6. **Schema split.**  
   Goal: domain contracts with compatibility exports.  
   Files: `wilq/schemas.py`, new schema modules, shared TS schemas.  
   Proof: API contract tests, mypy/ruff, dashboard typecheck.

7. **Action service split.**  
   Goal: ActionObject safety in small domain modules.  
   Files: `wilq/actions/service.py`, action registry/seeders/review/mutation
   modules.  
   Proof: action validate/preview/review/confirm/audit tests pass.

8. **Ads diagnostics split into rule-backed subdomains.**  
   Goal: no single Ads brain file; prepare for ExpertRule use.  
   Files: `wilq/briefing/ads_*`, Ads tests.  
   Proof: Ads diagnostics tests pass; no CPA/ROAS/waste claims without
   contracts.

9. **Skill smoke harness extraction.**  
   Goal: small per-skill scripts, shared assertions.  
   Files: `.agents/skills/*/scripts`, shared helper module.  
   Proof: strict skill eval coverage and touched smoke scripts pass.

10. **Docs truth pruning.**  
    Goal: current docs are short, accurate and route-current.  
    Files: `docs/PROGRESS.md`, `docs/CONTEXT.md`, `docs/dashboard-state.md`,
    eval coverage summary.  
    Proof: no stale active `/content-planner` truth; Beads/docs/API priorities
    agree.

## FIRST_PR_RECOMMENDATION

Smallest PR that removes the most visible slop:

**PR title:** Delete/quarantine legacy content planner surface.

Exact scope:

- Keep deleted:
  - `apps/dashboard/e2e/content-planner-layout.spec.ts`
  - `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx`
  - `apps/dashboard/src/routes/ContentDiagnosticSurface.test.ts`
- Verify/remove active imports/routes for `ContentDiagnosticSurface`.
- Ensure `surfaceRegistry.ts` has `/content-workflow` as primary content route.
- Replace active `/content-planner` references in current docs/eval summaries.
- Leave historical archived audits/handoffs intact but not current truth.

Do not include:

- `ContentWorkflowSurface.tsx` split.
- schema split.
- Ads diagnostics changes.

Verification:

```bash
rtk rg -n "content-planner|ContentDiagnosticSurface" apps/dashboard apps/api wilq tests docs/evals docs/dashboard-state.md docs/PROGRESS.md
rtk pnpm --filter @wilq/dashboard test
rtk pnpm --filter @wilq/dashboard typecheck
rtk git diff --check
```

Expected remaining `rg` hits: archived/handoff/audit references only, plus this
audit and the prompt document.

## BEADS_GRAPH

New audit epic:

- `wilq-seo-c9h9` - Full repo senior audit and anti-slop cleanup plan.

Children:

| Bead | Purpose | Main blockers/dependencies |
| --- | --- | --- |
| `wilq-seo-yrpf` | Publish final audit with file coverage proof. | Parent `wilq-seo-c9h9`. |
| `wilq-seo-c2lf` | Stop growing frozen monolith files. | Blocks on `wilq-seo-yrpf`. |
| `wilq-seo-d380` | Define/enforce React dashboard standards. | Blocks on `wilq-seo-yrpf`. |
| `wilq-seo-y0o5` | Define Python runtime/test standards. | Blocks on `wilq-seo-yrpf`. |
| `wilq-seo-77b1` | Quarantine zombie routes/placeholders. | Blocks on `wilq-seo-yrpf`. |
| `wilq-seo-i2qb` | First PR: delete/quarantine legacy content planner. | Blocks on `wilq-seo-77b1`. |
| `wilq-seo-ho41` | Split `ContentWorkflowSurface.tsx`. | Blocks on `wilq-seo-i2qb`, `wilq-seo-d380`. |
| `wilq-seo-pidl` | Replace `App.test.tsx` monolith. | Blocks on `wilq-seo-77b1`, `wilq-seo-d380`. |
| `wilq-seo-50wa` | Dismantle `tests/test_api_contracts.py`. | Blocks on `wilq-seo-c2lf`, `wilq-seo-y0o5`. |
| `wilq-seo-b4kg` | Split `wilq/schemas.py`. | Blocks on `wilq-seo-c2lf`, `wilq-seo-y0o5`. |
| `wilq-seo-jnra` | Split `wilq/actions/service.py`. | Blocks on `wilq-seo-b4kg`, `wilq-seo-y0o5`. |
| `wilq-seo-kgvy` | Split Ads diagnostics. | Blocks on `wilq-seo-b4kg`, `wilq-seo-y0o5`. |
| `wilq-seo-ksiq` | Split shared TypeScript schemas. | Blocks on `wilq-seo-b4kg`, `wilq-seo-d380`. |
| `wilq-seo-0q74` | Extract skill smoke harness. | Blocks on `wilq-seo-y0o5`. |
| `wilq-seo-co30` | Prune docs truth and archive stale progress. | Blocks on `wilq-seo-yrpf`, `wilq-seo-77b1`. |

Graph verification:

- `rtk bd dep cycles --json` returned `[]`.
