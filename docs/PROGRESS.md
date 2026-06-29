# WILQ Progress Ledger

This file is the short recovery ledger. It is not a changelog and must not
become an append-only transcript.

Full current plan: `PLAN.md`
Long-range product plan: `PLANS.md`
Active goal: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-29

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured. They are not canonical content targets and must not drive content
  decisions by default.
- WILQ API is the product brain. Dashboard and Codex skills consume typed API
  contracts, source connectors and WILQ-described evidence.
- Marketer-facing UI and skill output must use Polish operating language.
- Raw IDs, connector trace, raw payloads and audit details belong only in
  technical detail.
- Dirty copy must be fixed in typed API/schema/view-model/domain source, not
  with React translators, string replacement helpers or stale label maps.
- Do not preserve deprecated active fields, compatibility aliases or stale
  dev-preview/migration semantics when direct migration is feasible.

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

## Latest Verified Product State

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
- `rtk uv run python scripts/context_pack_language_guard.py --api-base http://127.0.0.1:8000`
- `rtk pnpm outdated -r`
- browser proof with `agent-browser` for touched routes
- `rtk git diff --check`

## Recovery Rule

Older proof history is intentionally omitted from this recovery ledger. Use git
history and `.local-lab/proof/` when older evidence is needed. When adding new
status, remove or replace outdated lines instead of appending a new history
block.
