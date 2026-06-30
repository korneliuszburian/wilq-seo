# WILQ Progress Ledger

This file is the short recovery ledger. It is not a changelog and must not
become an append-only transcript.

Current cleanup plan: `PLAN.md`
Active product execution plan: `PLANS.md`
Goal 001 contract: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-30

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured. They are not canonical content targets and must not drive content
  decisions by default.
- WILQ API is the product brain. Dashboard and Codex skills consume typed API
  contracts, source connectors and WILQ-described evidence.
- Beads (`bd`) is the operational task graph for current work. Run `bd prime`
  and `bd ready --json` after recovery. Active Goal 002 epic:
  `wilq-seo-zu4`. Historical Goal 001 cleanup epic: `wilq-seo-6rw`.
- Marketer-facing UI and skill output must use Polish operating language.
- Marketer-facing text must defend itself: every empty, missing or blocked
  state has to say what it means for the next decision, not just that data is
  absent.
- Raw IDs, connector trace, raw payloads and audit details belong only in
  technical detail.
- Dirty copy must be fixed in typed API/schema/view-model/domain source, not
  with React translators, string replacement helpers or stale label maps.
- Do not preserve deprecated active fields, compatibility aliases or stale
  dev-preview/migration semantics when direct migration is feasible.
- Real marketer UAT for Goal 001 is explicitly deferred by the owner in
  `docs/handoffs/2026-06-30-owner-defer-marketer-uat.json`. This does not
  claim that UAT happened. It means the current cockpit may be treated as a
  verified review surface while WILQ moves to Goal 002 content-production work
  before presenting it as a real content workflow to Wilku.

## Live Connector State

Live API check on 2026-06-29:

- WILQ API health: `ok`.
- Google Search Console: configured, fresh, no missing credentials.
- Google Analytics 4: configured, fresh, no missing credentials.
- Google Merchant Center: configured, fresh, no missing credentials.
- Google Ads, Ahrefs, Localo and WordPress are configured.
- LinkedIn and Facebook credentials are missing; social remains later scope.
- Google Sheets is intentionally disabled for the current operator scope.

Do not reopen old WSL credential recovery for GSC, GA4 or Merchant unless live
API status later contradicts this state.

## Current Goal Transition

- Goal 001 cleanup is no longer blocked by missing UAT input because the owner
  explicitly deferred real marketer UAT until WILQ has a stronger content
  production workflow.
- The safe next product goal is Goal 002: Content Production Engine bez slopu.
- Goal 002 must start from anti-slop guardrails and content workflow contracts,
  not from prompt-only drafting or more dashboard labels.
- WILQ may be described as a review cockpit today. It must not be described as
  a complete content production engine until preflight, preserve-first planning,
  sales brief, claim ledger, draft package, human review, WordPress draft
  handoff and measurement window are implemented and verified end-to-end for at
  least one real Ekologus content item.
- Goal 002 Beads epic is `wilq-seo-zu4`.
- Goal 002 anti-slop baseline proof lives in
  `docs/handoffs/2026-06-30-goal-002-anti-slop-baseline.md`.
- `scripts/audit_complexity.py` now reports Python LOC, largest files,
  functions, classes and frozen-file growth risk. Current baseline shows
  147 Python files, 81,481 non-empty Python LOC and no changed frozen growth
  files in this slice.
- Historical quality debt is now explicit: full Ruff reports 68 issues, mypy
  reports 5 existing type errors in `content_refresh.py`/`main.py`, and Fallow
  reports 21.0% TypeScript duplication with 13 functions above threshold.
  These are baseline risks for Goal 002, not permission to add new behavior to
  the known monoliths.
- Goal 002 content domain extraction has started under `wilq-seo-x4u`.
  Canonical/public URL semantics moved from
  `wilq/briefing/content_diagnostics.py` to `wilq/content/canonical/urls.py`.
  This is behavior-preserving extraction: focused canonical tests, two content
  diagnostics contract tests, Ruff, mypy for the new module, import-boundary
  smoke and `git diff --check` passed.
- Goal 002 content preflight verdict helpers moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/preflight/verdicts.py`. This is behavior-preserving extraction:
  focused preflight tests, canonical tests, two content diagnostics contract
  tests, Ruff, mypy for the new module, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 content inventory gate rules moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/inventory/gates.py`. This is behavior-preserving extraction:
  focused inventory gate tests, preflight tests, canonical tests, two content
  diagnostics contract tests, Ruff, mypy for the new module, import-boundary
  smoke, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed. Unused private WordPress inventory detail helpers
  were deleted instead of moved to a new module.
- Goal 002 content planning decision helpers moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/planning/decisions.py`. This is behavior-preserving extraction:
  focused planning tests, inventory gate tests, preflight tests, canonical tests,
  two content diagnostics contract tests, Ruff, mypy for the new module,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Goal 002 GSC content decision construction moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/planning/decisions.py`. This is behavior-preserving extraction:
  focused planning tests now cover `gsc_content_decisions`, preserve-first
  handling and dev-preview URL rejection as canonical; the same content
  diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 GA4 tracking-gap content blocker moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/measurement/decisions.py`. This is behavior-preserving
  extraction: focused measurement tests now cover GA4 tracking gaps as
  measurement blockers, not content rewrite recommendations. The same content
  diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 Ahrefs gap review decision construction moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/planning/ahrefs.py`. This is behavior-preserving extraction:
  focused Ahrefs planning tests now cover relevant/off-topic filtering,
  candidate rows, GSC/WordPress overlap labels and blocked growth claims. The
  same content diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 GSC/WordPress vendor-read blocker moved from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/preflight/vendor_read.py`. This is behavior-preserving
  extraction: focused vendor-read tests now cover blocker reasons, refresh
  evidence fallback and the `block_until_vendor_read` decision. The same content
  diagnostics contract tests, Ruff, mypy, import-boundary smoke,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 marketer-facing content preflight/decision view construction moved
  from `wilq/briefing/content_diagnostics.py` to
  `wilq/content/preflight/marketer_view.py`. This is behavior-preserving
  extraction: focused marketer-view tests now cover preserve-first copy, draft
  blocking with sales brief allowance, concrete gate labels and generic unknown
  claim labels. The same content diagnostics contract tests, Ruff, mypy,
  import-boundary smoke, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.
- Goal 002 API router extraction has started under `wilq-seo-hdl`. Read-only
  connector endpoints moved from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/connectors.py` without changing endpoint paths or
  response shapes. Connector refresh POST remains in `main.py` until cache
  invalidation can be extracted safely. Focused connector API tests, route-shape
  smoke, Ruff, mypy for the new router, `scripts/audit_complexity.py --changed
  --allow-frozen` and `git diff --check` passed.
- Goal 002 jobs router extraction moved `/api/jobs*` and `/api/job-runs*`
  endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/jobs.py` without changing endpoint paths or
  response shapes. Focused scheduler tests, jobs route-shape smoke, Ruff, mypy,
  `scripts/audit_complexity.py --changed --allow-frozen` and `git diff --check`
  passed.
- Goal 002 evidence/metrics router extraction moved `/api/evidence*` and
  `/api/metrics*` read endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/evidence.py` and
  `apps/api/wilq_api/routers/metrics.py` without changing endpoint paths or
  response shapes. Focused evidence/metrics API tests, route-shape smoke, Ruff,
  mypy, `scripts/audit_complexity.py --changed --allow-frozen` and
  `git diff --check` passed.
- Goal 002 knowledge/expert router extraction moved `/api/knowledge*` and
  `/api/expert*` endpoints from `apps/api/wilq_api/main.py` to
  `apps/api/wilq_api/routers/knowledge.py` and
  `apps/api/wilq_api/routers/expert.py` without changing endpoint paths or
  response shapes. Context-pack compaction helpers remain in `main.py` for a
  later scoped extraction. Focused knowledge/expert API tests, route-shape
  smoke, Ruff, mypy, `scripts/audit_complexity.py --changed --allow-frozen`
  and `git diff --check` passed.

## Latest Verified Product State

- Command Center, shared evidence freshness, GA4/Merchant freshness and Ads
  recommendation impact copy no longer turn unknown/missing data into bare
  `brak danych`, `brak odczytu` or a false zero-cost impact. Live
  `/api/dashboard/command-center` scan is clean, and focused API/dashboard
  checks plus marketer/context/operator language guards passed.
- `docs/goals/001-goal.md` has been pruned after closing Beads issue
  `wilq-seo-6rw.4`; raw-label cleanup is no longer listed as an active broad
  task. Future cleanup should start from fresh Fallow/browser/API evidence,
  context-pack guard failures or UAT findings.
- Action preview, Content, GA4 and tactical WordPress labels no longer use bare
  `brak`/`brak danych` fallbacks for missing review, URL, WordPress-match,
  percentage or Ads custom-segment values. They now describe the unconfirmed
  fact at API/schema/domain source, and no React label remapper was added.
  Focused API tests, dashboard route tests, ruff I/F, marketer/context/operator
  language guards, live API proof and `git diff --check` passed.
- `App.tsx` route composition uses a dedicated route renderer map. Focused
  dashboard tests, typecheck, lint, Fallow audit/health, language guards,
  `git diff --check` and browser proof for `/merchant`, `/content-planner` and
  `/settings` passed. Fallow still lists `App.tsx` as a historical hotspot due
  to churn, but there are no current high-confidence refactoring targets.
- `App.test.tsx` mock API routing is split into focused endpoint handlers.
  Fallow no longer reports it as a current high-confidence refactoring target.
- `OperatingRouteSurfaces.tsx` and `GenericSurface.tsx` are split into focused
  sections. `/workflows` renders the main process decision surface before
  secondary process-run history is required.
- Dashboard patch/minor dependencies are current where no framework migration
  was required: `@tanstack/react-query@5.101.2`,
  `@playwright/test@1.61.1`, `postcss@8.5.16` and
  `autoprefixer@10.5.2`.
- `lucide-react` has been upgraded to `1.22.0`. Dashboard typecheck, focused
  route tests, lint, production build, Fallow changed-file audit and browser
  proof for `/command-center` passed after the upgrade.
- `jsdom` has been upgraded to `29.1.1`. Dashboard typecheck, full dashboard
  test suite, lint, production build, Fallow changed-file audit,
  marketer/context-pack language guards and browser proof for `/command-center`
  passed after the upgrade.
- `@types/node` has been upgraded to `26.0.1`. Workspace typecheck, full
  dashboard test suite, lint, production build, Fallow changed-file audit,
  marketer/context-pack language guards and browser proof for `/command-center`
  passed after the upgrade.
- `typescript` has been upgraded to `6.0.3`. Workspace typecheck, full
  dashboard test suite, lint, production build, Fallow changed-file audit,
  marketer/context-pack language guards and browser proof for `/command-center`
  passed after the upgrade.
- `zod` has been upgraded to `4.4.3`. Shared schemas now use explicit
  `z.record(z.string(), valueSchema)` contracts required by Zod 4, the action
  review gate has an explicit default state, and live shared-schema smoke uses
  a realistic timeout for heavier WILQ API endpoints. Workspace typecheck,
  shared-schema tests, live shared-schema smoke, full dashboard tests, lint,
  production build, Fallow changed-file audit, marketer/context-pack language
  guards and browser proof for `/command-center` passed after the upgrade.
- `tailwindcss` has been upgraded to `4.3.1` with `@tailwindcss/postcss`.
  Dashboard CSS now uses the Tailwind v4 import path with the existing config
  explicitly loaded. Dashboard typecheck, full dashboard test suite, lint,
  production build, Fallow changed-file audit, marketer/context-pack language
  guards, browser proof for `/command-center` and generated CSS proof for WILQ
  custom colors passed after the upgrade.
- `vite`, `vitest` and `@vitejs/plugin-react` have been upgraded to current
  major versions (`vite@8.1.0`, `vitest@4.1.9`,
  `@vitejs/plugin-react@6.0.3`). Shared schemas explicitly include Node types
  for the live schema smoke environment. Workspace typecheck, workspace tests,
  live shared-schema smoke, dashboard lint/build, Fallow changed-file audit,
  marketer/context-pack language guards, `pnpm outdated` and browser proof for
  `/command-center` passed after the upgrade.
- JS workspace dependencies are current as of 2026-06-29.
- Fallow is wired through `.fallowrc.json` and root package scripts. Dead-code
  and dependency hygiene are clean; full structural cleanup still has inherited
  dashboard duplication and complexity debt.
- Active dashboard/API/skill cleanup removed the worst slash-combined labels,
  stale dev-preview placement semantics, a hybrid Merchant sample-readiness
  field, misleading review wording, raw route slugs in action reasons and
  technical registry fallback language from primary surfaces.
- `scripts/live_contract_smoke.py` guards live content diagnostics against
  stale dev-preview URL and migration-era semantics.
- `tests/test_operator_endpoint_language_guard.py` now guards the main
  operator endpoints against stale route names, dev-preview/migration
  semantics and action-model jargon in serialized API output.
- Active dev-preview/migration semantics audit is closed in Beads
  (`wilq-seo-6rw.3`). Current active API/dashboard/schema/skill code no longer
  exposes dev preview as a final/canonical content target; remaining matches are
  guard/smoke tests or historical plan text. Focused operator endpoint/content
  URL tests, marketer language guard and live contract smoke passed.
- Merchant diagnostics active API contract now uses `change_preview` instead
  of `payload_preview`; `/api/merchant/diagnostics`, the Merchant context pack
  compaction and the Merchant skill smoke no longer expose `payload` wording.
- Google Ads connector versioning now documents why the REST endpoint stays on
  the major `v24` path while v24.2 capabilities enter WILQ as explicit read or
  review contracts. A focused contract test prevents accidental `v24.2`/`v24_2`
  endpoint churn.
- Codex context-pack compaction no longer builds operator-facing evidence
  summaries, knowledge-card titles or audit summaries from raw connector,
  source, card or event types. Focused API contract coverage guards those
  fallbacks.
- Central operator summary labels now explain decision limits instead of
  returning bare `brak ...` placeholders. Missing sources, evidence, actions,
  knowledge, required evidence, lineage, blocked promises and credential source
  summaries tell the marketer whether the item is safe to treat as a
  recommendation. Focused API/dashboard tests, marketer/context-pack language
  guards, dashboard typecheck/lint and `git diff --check` passed.
- Shared dashboard fallbacks now defend themselves: missing status labels,
  empty trace rows, empty registry lists, action audit history, opportunity
  metrics and knowledge/playbook lists explain what remains unsafe instead of
  serving a bare missing-state label. Focused dashboard tests, dashboard
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Demand Gen metric rows now expose self-defending marketer labels from the
  typed API/schema contract. The dashboard no longer renders generic `brak`
  fallbacks or local Ads cost/GA4 percent formatters for Demand Gen metrics.
  Focused API/dashboard/shared-schema tests, dashboard typecheck/lint,
  marketer language guard and `git diff --check` passed.
- Demand Gen readiness now builds from Ads summary diagnostics instead of the
  full Ads cockpit. Direct/TestClient proof returns in about two seconds. A
  temporary HTTP timeout was traced to orphaned `agent-browser`/headless Chrome
  processes hammering the dashboard after Vite restarted; after closing them
  and restarting the canonical stack, `/api/health` returned in 0.001 s and
  `/api/demand-gen/diagnostics` returned in 1.47 s.
- Marketer-facing empty states now have to defend the decision surface: action
  evidence, action preview blockers, review conditions, workflow outcomes,
  brief workflow evidence, expert rule action mapping and evidence source
  references explain what the missing state means instead of showing bare
  `brak` placeholders. Focused dashboard tests, dashboard typecheck/lint,
  marketer language guard and `git diff --check` passed.
- Action validation, confirmation, effect-check and Tactical Queue empty states
  now explain the decision limit when errors, warnings, sources, evidence or
  actions are missing. These panels no longer use context-free `brak błędów`,
  `brak ostrzeżeń`, `brak dowodów do pokazania` or `brak akcji do sprawdzenia`
  as the operator-facing answer. Focused dashboard tests, dashboard
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Content Planner empty states now explain why missing preflight inputs,
  similar URLs, preview URL, decision modes, evidence, GSC overlap or WordPress
  overlap limit the recommendation. The dashboard explicitly says not to treat
  a dev host as canonical and not to start writing without the content check.
  Focused content dashboard tests passed.
- Merchant empty states now explain the operational limit when scope, actions,
  decision source, data sources, evidence, validation inputs, issue types,
  product context or sample titles are missing. The route no longer uses
  `empty="brak..."` copy and its focused route test guards against regressions.
  Dashboard typecheck/lint, marketer language guard and `git diff --check`
  passed.
- GA4, Brief Workflow, Localo, Ahrefs and Custom Segments empty states now use
  decision-limit language instead of bare `brak...` placeholders. The copy
  clarifies when data is only context, when a recommendation is not justified,
  and when human review is still required. Focused source test, dashboard
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Ads Doctor empty states now explain missing metrics, review, evidence,
  actions, source conditions, allowed uses, blocked uses, policy and human
  review as decision limits. Active dashboard routes/components no longer
  contain `empty="brak..."`, `?? "brak"` or `|| "brak"` fallbacks. Focused Ads
  source test, dashboard typecheck/lint, marketer language guard and
  `git diff --check` passed.
- GA4 action summary, Ads optimizer readiness, negative-keyword safety, workflow
  run history and connector-status fallbacks now explain the operational
  consequence of missing labels or runs. The dashboard says when a panel is not
  a list of actions, when a process is not executed automation, and when source
  status must be refreshed before judging readiness. Focused dashboard tests,
  typecheck/lint, marketer language guard and `git diff --check` passed.
- Content Planner preflight tiles and compact utility-route blockers no longer
  use bare `brak` wording for unavailable states. Missing content preflight now
  says `nie pisz` / `bramka niedostępna`, while utility routes explain what must
  not be done from that view. Focused route tests, dashboard typecheck/lint,
  marketer language guard and `git diff --check` passed.
- Ads field-level fallbacks for missing latest read, campaign channel/status,
  budget proposal, preview, date, campaign, ad group, change ID and campaign
  metrics now say what the operator must not infer or do. The Ads route no
  longer turns these missing fields into context-free missing-state answers in
  the active surface. Focused Ads dashboard tests, typecheck/lint, marketer
  language guard and `git diff --check` passed.
- Marketing brief Ads summaries are now condensed at API source. The brief keeps
  one metric observation, uses short action summaries for Ads actions and keeps
  the profitability/write blocker in the focus item instead of repeating the
  full Ads diagnosis across sections. Focused marketing-brief API tests,
  live `/api/marketing/brief` proof, marketer/context-pack language guards and
  `git diff --check` passed.
- Content metric tiles no longer show a bare missing-state word when a metric
  value is unavailable. They say `metryka niepotwierdzona`, while the Treści
  route continues to explain actual blockers and next safe steps in the page
  flow. Focused content dashboard tests, marketer language guard,
  `git diff --check` and browser proof for `/content-planner` passed.
- Shared metric chips no longer say `zmiana: brak` when a delta exists but the
  trend direction is not confirmed. They explain `zmiana: kierunek
  niepotwierdzony`, with a focused component test and browser proof that Localo
  metric chips still render correctly in the live dashboard.
- Merchant primary-surface fallbacks for report counts, problem resolution and
  product samples no longer use bare `brak` copy. Missing counts and samples now
  state what remains unconfirmed before product-file review. Focused Merchant
  source/render tests, marketer language guard, `git diff --check` and browser
  proof for `/merchant` passed.
- Ads missing status/channel fallbacks now come from API/domain labels instead
  of bare status/channel placeholders. Missing campaign status, channel type and
  keyword status explain that the state is unconfirmed. Focused pytest, App route
  test, ruff import/name checks, marketer language guard and browser proof for
  `/ads-doctor` passed.
- Ads change-history resource, operation and change-source fallbacks now explain
  unconfirmed state from API/domain labels instead of context-free missing
  placeholders. Focused Ads API tests, ruff import/name checks, marketer and
  context-pack language guards, live Ads diagnostics proof and `git diff --check`
  passed.
- Action detail validation no longer uses context-free `brak` answers. The
  validation result now says that WILQ did not report errors or warnings, so the
  positive empty state is tied to an actual check.
- Action detail safety-record fields now use API-owned labels for mutation
  audit status, write attempt, external write path and audit trace. The review
  panel shows concrete states such as `nie próbowano zapisu w systemie
  zewnętrznym`, `brak bezpiecznej ścieżki zapisu` and `ślad bezpieczeństwa
  zapisany` instead of local `brak` fallbacks. Focused action API tests,
  action-panel/detail route tests, shared-schema tests, dashboard
  typecheck/lint, language guards, live blocked-apply API proof and browser
  proof passed.
- GA4 dashboard trace lines no longer use generic `brak` empty states for
  measurement readiness, evidence or sources. Focused GA4 route tests,
  dashboard typecheck/lint, language guards and browser proof passed.
- Merchant dashboard trace lines no longer use generic `brak` empty states for
  decision sources, evidence, actions, source connectors or missing metrics.
  Focused Merchant route tests, dashboard typecheck/lint, language guards and
  browser proof passed.
- Merchant product-performance rows now use API-owned labels for missing
  Ads/GA4 product metrics. Product cards show concrete states such as
  `kliknięcia Ads do potwierdzenia`, `koszt Ads do potwierdzenia`,
  `zakupy GA4 do potwierdzenia` and `przychód GA4 do potwierdzenia` instead
  of context-free `brak`. Focused Merchant API/dashboard/shared-schema tests,
  dashboard typecheck/lint, marketer/context-pack language guards, live API
  proof and browser proof passed.
- Localo and Ahrefs dashboard evidence traces no longer use generic `brak`
  empty states. Focused route tests, dashboard typecheck/lint, language guards
  and browser proofs passed.
- Content diagnostics no longer expose generic Ahrefs/GSC overlap labels such
  as `GSC: brak` or `Overlap GSC`; API labels now distinguish confirmed GSC or
  WordPress matches from missing overlap. Focused API/dashboard tests,
  typecheck/lint, language guards, context-pack guard and browser proof passed.
- Custom Segments and Tactical Queue dashboard traces no longer use generic
  `brak` empty states for evidence, human review, audience forecasts or action
  availability. Focused dashboard tests, typecheck/lint and language guard
  passed.
- Google Ads dashboard traces no longer use generic `brak` empty states for
  evidence, blocked claims, missing data, actions, review gates or source
  conditions. Shared trace rows also no longer default to context-free `brak`.
  Focused Ads route tests, dashboard typecheck/lint, language guard and browser
  proof passed.
- Google Ads target-guardrail action previews no longer show context-free
  `Docelowy zwrot z reklam: brak` or `Docelowy koszt pozyskania celu: brak`.
  The API preview now says that the Ads target is not set and which business
  conclusion WILQ therefore will not make. Focused target-guardrail API tests,
  action-detail route tests, dashboard typecheck/lint, marketer/context-pack
  language guards, live API proof and browser proof passed.
- Google Ads budget preview cards no longer show context-free
  `Propozycja: brak` or `Propozycja do sprawdzenia: brak danych`. The API
  preview now explains that Google Ads did not provide a proposed amount and
  WILQ therefore shows the current budget while blocking budget writes. Focused
  Ads budget API tests, action-detail route test, dashboard typecheck/lint,
  marketer/context-pack language guards, live Ads diagnostics proof and browser
  proof passed.
- Localo marketer-facing summaries now use correct Polish aggregate-count
  wording and all shared metric tiles render decimal values with Polish number
  formatting. Focused API/dashboard tests, language guards and browser proof
  for `/localo` passed.
- Ahrefs gap summaries now use correct Polish count wording and condense
  repeated record-level facts into readable signal counts instead of repeating
  the same gap phrase. Focused Ahrefs/content API tests, dashboard route tests,
  language guards and browser proof for `/ahrefs` passed.
- Ahrefs authority summaries now format large ranking values with Polish
  grouping and keep the competitor-read sentence separated, so the summary is
  readable without dashboard-side cleanup.
- Ahrefs and Localo decision cards now label supporting proof as `Na czym można
  się oprzeć` instead of the contract-like `Dozwolone dowody`; focused
  dashboard tests, typecheck/lint, language guards and browser proof for both
  routes passed.
- Empty missing-data states now say `dane kompletne` instead of awkward
  negative phrasing such as `brak brakujących danych` or `Brakujące dane:
  brak`; focused API/dashboard tests, language guards and Ahrefs browser/API
  proof passed.
- GA4 conversion-readiness now carries an API-owned missing-data summary label,
  so `/ga4` shows `Brakujące dane: dane kompletne` when conversion/key-event
  data is present instead of relying on a route fallback. Focused GA4 API,
  dashboard, shared-schema, language-guard and browser proof passed.
- GA4 action preview blocked-claim labels now use concrete claim names instead
  of repeated fallback text like `wniosek GA4 do sprawdzenia`; focused GA4 API
  tests, language guards and browser proof for
  `/actions/act_review_ga4_tracking_quality` passed.
- `AGENTS.md` now codifies the marketer-content rule: first-screen summaries,
  decision cards and empty states must be understandable without developer
  translation and must state the decision, reason, proof, blocker or next safe
  step directly.
- Action detail now hides legacy English apply/audit summaries from the
  marketer-facing history. The GA4 action detail shows "Zapis zmian
  zablokowany" and a Polish safety summary instead of raw apply-contract text;
  focused API, dashboard, language-guard and browser checks passed.
- Main dashboard status chips no longer expose hidden semicolon separators or
  markdown backticks in marketer-facing text. Content and Merchant browser proof
  passed after the shared chip cleanup.
- Marketing brief, Merchant, GA4 and Ahrefs blocked-read summaries use Polish
  operator status labels instead of raw refresh status enum values.
- Command Center decision freshness notes use Polish source and freshness
  labels instead of raw `connector_id=state` pairs.
- Tactical queue Ahrefs diagnoses use Polish gap/context labels instead of raw
  `gap_type` values, backticks or `key=value` URL context.
- Codex context-pack refresh-run summaries use Polish evidence/access count
  labels instead of numeric fragments like `dowody 2` or `braki dostępu 0`.
- Skill context packs scope active actions per workflow, so the content
  strategist no longer receives unrelated GA4 action payloads.
- Skill context-pack actions expose compacted execution context as
  `action_plan`; the technical `payload` key remains on action detail endpoints
  and is guarded out of `active_action_objects`.
- Skill context-pack `action_plan` no longer exposes technical preview/safety
  field names such as `payload_preview`, `preview_contract`,
  `required_validation`, `apply_allowed`, `api_mutation_ready` or
  `destructive`, and no longer repeats raw action type/connector/mode fields.
  Compact action plans now use preview lists and Polish status labels for
  operator-facing skill context. Raw `source_metric_names` are also removed
  from compact action plans; metric meaning must come through labels/summaries.
  Search-term theme previews use marketer-readable compact keys instead of
  `ngram_preview`, and validation counters use required-check naming. Raw
  blocked-claim and missing-contract lists are removed from compact action
  plans when marketer-readable labels are present.
- Skill context-pack `action_plan` metric snapshots are condensed into
  `metric_tiles` keyed by marketer-readable labels; raw metric field names stay
  out of compact skill action context.
- Google Ads monetary values in raw `*_micros` units are stripped from compact
  skill action plans; full action endpoints keep the technical payload when
  needed for validation/review.
- Skill context-pack `action_plan` now keeps labeled contract/review-gate lists
  only. Raw `allowed_contracts`, `available_read_contracts` and
  `operator_review_gates` are removed from compact skill context when their
  marketer-readable label fields exist.
- Content skill plan items now keep labeled source, publication-readiness,
  blocker and risky-claim fields only. Raw `source_type`,
  `publication_readiness_status`, `publication_blockers` and `forbidden_claims`
  stay out of compact skill context when label fields exist.
- Ads skill campaign plans now use campaign/channel/review-gate labels in
  compact context. Raw `campaign_status`, `advertising_channel_type`,
  `human_review_gates`, `target_status` and safety `missing_requirements` stay
  out of compact skill context when label fields exist, while the budget preview
  keeps its reason and marketer-readable safety checks.
- Compact Ads and custom-segment skill plans no longer expose technical preview
  identifiers or internal safety contract names such as campaign IDs, budget
  IDs, custom-segment preview IDs, `safety_contract`, `target_scope`,
  `member_type` or `audit_required`; full action endpoints retain technical
  payload details for validation/review.
- Content skill plan items now use labeled inventory, canonical, duplicate and
  WordPress inventory gate fields. Raw gate status keys stay out of compact
  skill context, while full action endpoints retain technical payload details
  for validation/review.
- GA4 skill action plans now use labeled required-dimension fields. Raw
  `required_breakdowns` stay out of compact skill context, while full action
  endpoints retain the technical GA4 breakdown contract for validation/review.
- Skill context-pack expert capabilities use `required_inputs` instead of the
  technical `required_mapping` field name.
- Marketer language guard now blocks bare Ads missing status/channel
  placeholders, so future cleanup cannot reintroduce unexplained first-screen
  missing-state copy.
- Workflow cards now explain when a process has no dedicated route instead of
  rendering bare missing-view fallback text.
- Workflow API model now explains complete missing-data state for processes
  instead of returning a bare missing-state fallback in process detail labels.
- Localo and Command Center now explain missing Localo read contracts as
  unconfirmed/unconnected data scopes from API/domain copy instead of bare
  missing-data placeholders.
- Knowledge operating map now explains complete missing-data detail labels as
  a full operator sentence instead of a bare missing-state fallback.
- Ads business-context metric tiles now explain missing margin, business goal,
  budget goal and strategy review states as concrete operator states instead of
  bare missing placeholders.
- Daily, Ads, Ahrefs and Merchant missing-status labels now describe
  unconfirmed data scopes instead of returning bare missing-data copy in active
  briefing contracts.
- Content action labels now describe missing content contracts and unavailable
  GSC metrics as unconfirmed source data instead of bare missing placeholders.
- `docs/goals/001-goal.md` has been condensed back into an active goal
  contract: current state, active findings, execution policy, verification and
  completion definition. Detailed slice history remains in git/proof artifacts,
  not in the active goal.

## Current Blockers And Deferred Work

- Real marketer UAT with Wilku/Ekologus is still not complete. This is the main
  non-technical blocker before claiming the current cockpit is done for humans.
- Major JS dependency migrations are separate product-safe slices, not cleanup
  drive-by changes. JS workspace dependencies are currently up to date; future
  vendor API updates such as Google Ads release changes should land as explicit
  contract slices with focused proof.
- Full Marketing OS layers remain later milestones unless explicitly promoted:
  workspace contracts, full content preflight, sales brief, claim review, human
  review, WordPress draft handoff, measurement loop, broader write/apply
  adapters and multi-client/agency UI.
- Social connectors are missing credentials and remain out of current core
  proof.
- Localo has access proof and guarded read data. Do not claim ranking, GBP,
  write or uplift behavior without explicit WILQ evidence.

## Next Queue

1. Run real marketer UAT or record explicit owner defer.
2. Continue active surface audits from current Fallow hotspots only when they
   affect marketer UX, product semantics or guardrails.
3. Take major dependency migrations one at a time with focused migration notes
   and verification.
4. Keep `PLAN.md`, `PLANS.md`, `docs/goals/001-goal.md`, `docs/CONTEXT.md` and
   this file pruned after every meaningful slice.
5. Before broad completion claims, run focused checks plus `scripts/verify.sh`.

## Recent Verification Commands

- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --filter @wilq/dashboard test -- App.test.tsx --runInBand`
- `rtk pnpm --dir apps/dashboard lint`
- `rtk pnpm --dir apps/dashboard build`
- `rtk pnpm fallow:audit --format compact --no-cache`
- `rtk pnpm fallow health --hotspots --targets --format compact --no-cache`
- `rtk uv run pytest tests/test_operator_endpoint_language_guard.py -q`
- `rtk uv run pytest tests/test_api_contracts.py::test_marketing_tactical_queue_uses_dimensioned_metric_facts -q`
- `rtk uv run pytest tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief -q`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'blocked_refresh_summaries or operator_label_fallbacks'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'operator_label_fallbacks'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'operator_label_fallbacks or refresh_run'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'content_strategist_payload or ga4'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'context_pack_scopes_content_strategist_payload or ga4 or localo or ads_doctor_payload or custom_segments_payload or demand_gen_payload'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'expert_capabilities or expert_rule_summaries'`
- `rtk uv run pytest tests/test_context_pack_language_guard.py -q`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'context_pack_scopes_content_strategist_payload or content'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'ga4 and context_pack'`
- `rtk uv run ruff check wilq/actions/ga4/tracking_quality.py wilq/actions/service.py apps/api/wilq_api/main.py scripts/context_pack_language_guard.py tests/test_context_pack_language_guard.py`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'merchant and (price_impact or groups_reporting_contexts or context_pack)'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'merchant_product_performance_readiness or merchant_diagnostics_promotes_ads_product_state_review_decision'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'target_guardrail'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'action_apply_requires_validation or apply_ready_action_blocks_without_mutation_adapter'`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'context_pack_scopes_content_strategist_payload or ga4 or localo or ads_doctor_payload or custom_segments_payload or demand_gen_payload'`
- `rtk pnpm --filter @wilq/shared-schemas test -- index.test.ts --runInBand`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk uv run pytest tests/test_marketer_language_guard.py -q`
- `rtk uv run pytest tests/content/test_preflight_verdicts.py tests/content/test_canonical_urls.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue tests/test_api_contracts.py::test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists -q`
- `rtk uv run ruff check wilq/content/preflight/verdicts.py wilq/briefing/content_diagnostics.py tests/content/test_preflight_verdicts.py`
- `rtk uv run mypy wilq/content/preflight/verdicts.py`
- `rtk uv run python scripts/audit_complexity.py --changed --allow-frozen --limit 5`
- `rtk uv run pytest tests/content/test_inventory_gates.py tests/content/test_preflight_verdicts.py tests/content/test_canonical_urls.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue tests/test_api_contracts.py::test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists -q`
- `rtk uv run ruff check wilq/content/inventory/gates.py wilq/briefing/content_diagnostics.py tests/content/test_inventory_gates.py`
- `rtk uv run mypy wilq/content/inventory/gates.py`
- `rtk uv run pytest tests/content/test_planning_decisions.py tests/content/test_inventory_gates.py tests/content/test_preflight_verdicts.py tests/content/test_canonical_urls.py tests/test_api_contracts.py::test_content_diagnostics_exposes_query_page_inventory_queue tests/test_api_contracts.py::test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists -q`
- `rtk uv run ruff check wilq/content/planning/decisions.py wilq/briefing/content_diagnostics.py tests/content/test_planning_decisions.py`
- `rtk uv run mypy wilq/content/planning/decisions.py`
- `rtk pnpm --dir apps/dashboard test -- WorkflowPanels.test.tsx --runInBand`
- `rtk uv run pytest tests/test_api_contracts.py -q -k 'workflow_label_fallbacks_do_not_expose_raw_values or workflow_missing_contract_detail_fallback_explains_complete_process or workflows_are_decision_backed_operator_contracts'`
- `rtk uv run python scripts/context_pack_language_guard.py --api-base http://127.0.0.1:8000`
- `rtk pnpm outdated -r`
- browser proof with `agent-browser` for touched routes
- `rtk git diff --check`

## Recovery Rule

Older proof history is intentionally omitted from this recovery ledger. Use git
history and `.local-lab/proof/` when older evidence is needed. When adding new
status, remove or replace outdated lines instead of appending a new history
block.
