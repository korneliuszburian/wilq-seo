# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-23 05:17 CEST.

This is the only active goal file. Keep it short and current. Do not append a
chronological work log here. When a task is done, move it to the short completed
foundation list or remove it from the active queue. Git history is the detailed
archive.

Progress hygiene rule: `docs/PROGRESS.md` is a compact recovery ledger, not a
full chronological dump. Keep current state, last 3-5 slices, active gaps and
next best actions there. Older detail belongs in `docs/progress/archive/`; the
first full archive is `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Recovery Contract

Every Codex session working on WILQ must read these files first:

1. `AGENTS.md` - operating rules, secrets policy, local paths and gotchas.
2. `docs/goals/001-goal.md` - current active goal and queue.
3. `docs/architecture/bdos-class-wilq-operating-system.md` - product bar.
4. `docs/infra/001.md` - original product scope.
5. `docs/architecture/codex-runtime.md` - skills, hooks, MCP and Codex evals.
6. `docs/audits/001-output.md` - fresh 2026-06-18 audit and next-slice critique.

Keep this file updated when connector readiness, live data status, blockers,
verification state or next tasks change.

Development speed rule: WILQ must move faster. Do not run broad test suites
after every tiny edit. Use a verification budget:

- During implementation, inspect diffs and run only the cheapest check that
  proves the local boundary you touched, or skip tests until a meaningful
  boundary is reached.
- Run a focused test only when a change crosses an API/schema/route/action
  boundary or when the risk is concrete.
- Run `scripts/verify.sh` only before a push/main handoff, after a genuinely
  large cross-surface change, or when a failure pattern suggests broad
  regression risk.
- Prefer batching several small safe refactors into one verified slice instead
  of paying the full gate after each tiny extraction.
- Slice gate matrix:
  - Dashboard component/route extraction: run the touched route unit file or
    focused `vitest` files plus `tsc --noEmit` when props/types moved. Skip
    Playwright unless routing, loading state or browser-only behavior changed.
  - API contract change: run `uv run pytest tests/test_api_contracts.py -q -k
    '<affected feature>'`; run the whole file only at the final gate.
  - Codex skill change: run `uv run pytest tests/test_codex_skill_eval_cases.py
    -q` plus `scripts/codex_skill_eval.sh --skill <skill>`. Use `--all` only
    if the shared harness/schema changed.
  - Connector/read adapter change: run the connector-specific tests plus the
    relevant API-contract subset. Add browser e2e only if the connector is
    surfaced in the dashboard.
  - Security-sensitive, shared schema, action validation, connector-read,
    cross API/dashboard/skill, or release/handoff work: run full
    `scripts/verify.sh` once at the final gate.

Subagent speed rule: use subagents to accelerate development, not only audits.
Delegate whenever work can run in parallel with disjoint write sets or clear
read-only questions: repo hotspot discovery, implementation slices, focused
test triage, browser QA, code review, performance profiling, docs/research and
handoff prep. Do not delegate overlapping edits into the same files without a
clear owner and integration plan.

Current dashboard monolith/performance slice: `ContentDiagnosticSurface`,
`AhrefsDiagnosticSurface`, `LocaloDiagnosticSurface` and
`DemandGenDiagnosticSurface`, `Ga4DiagnosticSurface` and
`CustomSegmentsDiagnosticSurface` plus `AdsDoctorSurface` have been extracted
from `apps/dashboard/src/routes/App.tsx` into dedicated route modules. Current
line-counts after route-level lazy loading: `App.tsx=276`, `AdsDoctorSurface.tsx=2277`,
`ContentDiagnosticSurface.tsx=802`,
`AhrefsDiagnosticSurface.tsx=348`, `LocaloDiagnosticSurface.tsx=344`,
`DemandGenDiagnosticSurface.tsx=361`, `Ga4DiagnosticSurface.tsx=568`.
`CustomSegmentsDiagnosticSurface.tsx=433`. Focused proof: dashboard lint OK,
dashboard typecheck OK, focused content/GSC/GA4/Ahrefs/Localo/Demand Gen/Custom
Segments/Ads Doctor route tests OK. This resolves the immediate `App.tsx`
monolith concern for the dashboard route shell; remaining large files should be
handled as separate code-quality slices only when they block product velocity or
reviewability. Post-push dashboard route-shell proof:
`pnpm --filter @wilq/dashboard test -- --run App.test.tsx` passed with 17 tests
across 4 route test files. Latest performance proof: `App.tsx` lazy-loads heavy
diagnostic modules for Ads Doctor, Custom Segments, Demand Gen, GA4, Localo,
Ahrefs, Merchant and Content/GSC. `pnpm --filter @wilq/dashboard build`
emits separate diagnostic chunks and passed together with dashboard typecheck,
lint and focused route tests.

Current API performance slice: Command Center first-screen paths must not build
full route diagnostics. `/api/dashboard/command-center` now uses lightweight
daily builders from tactical queue groups plus scoped metric facts for Ads,
Merchant, Content and GA4. Full diagnostics remain on dedicated routes:
`/api/ads/diagnostics`, `/api/merchant/diagnostics`, `/api/content/diagnostics`
and `/api/ga4/diagnostics`. `tactical_queue` uses a static action-ID map for
the tactical connectors instead of full `list_actions()` payload construction.
Latest live proof after stack restart: Command Center cold/warm/warm
`2.1856s/0.0074s/0.0086s`, Marketing Brief after Command Center
`0.4372s/0.0087s/0.0110s`, tactical queue around `0.008s` warm. Focused proof:
Python ruff OK, Python mypy OK, 10 command/tactical API tests OK and 17 dashboard
route tests OK. Remaining performance work should target tactical metric-store
read/model construction or route-specific diagnostics only when a measured
bottleneck justifies it.

2026-06-23 follow-up: Command Center first-screen paths also stopped building
full ActionObject payloads. `build_daily_command_center` now builds only
connectors + tactical queue when no full daily base is provided, and
`build_command_center_response` uses lightweight action stubs for first-screen
ActionObject IDs. Command Center also uses one batched
`list_metric_facts_by_connector` read instead of four separate metric fact
reads. Live proof after stack restart: `/api/dashboard/command-center`
cold/warm/warm/warm/warm `1.483985s/0.009951s/0.012386s/0.008260s/0.008596s`,
down from the previous measured `2.54s` cold hit. Tradeoff: the first
`/api/marketing/brief` after restart now pays the full ActionObject cost
(`1.741512s`), which is acceptable because Marketing Brief needs full payloads.

Latest skill eval proof: `wilq-ga4-analyst` now has the stricter validated
ActionObject eval. The smoke script validates `act_review_ga4_tracking_quality`
through `POST /api/actions/{action_id}/validate` and exposes
`action_validations`; the non-interactive eval case requires
`expected_validated_action_ids=["act_review_ga4_tracking_quality"]`. Passing
artifact:
`.local-lab/evals/codex-skill/20260623T011123Z/wilq-ga4-analyst/result.json`.
The result has `language=pl-PL`, Polish diacritics, `api_used=true`, 12 GA4
evidence IDs, `source_connectors=["google_analytics_4"]`,
`operator_usefulness_score=4`, no safety findings and
`action_candidates[0].validation_state="validated"`. It still correctly keeps
revenue, ROAS, conversion-drop, profitability and tracking-fixed claims blocked
because `conversion_readiness_contract.status=blocked` and
`conversion_like_metric_count=0`.

Merchant now follows the same stricter validated ActionObject pattern. The
`wilq-merchant-feed-operator` smoke validates
`act_review_merchant_feed_issues` through
`POST /api/actions/{action_id}/validate`, the eval case requires
`expected_validated_action_ids=["act_review_merchant_feed_issues"]`, and the
passing artifact is
`.local-lab/evals/codex-skill/20260623T011722Z/wilq-merchant-feed-operator/result.json`.
The result has `operator_usefulness_score=5`,
`action_candidates[0].validation_state="validated"` and still blocks approval,
revenue, feed-write and automatic-fix claims. Use this as the template for
hardening the remaining high-value skills; do not solve this by adding
edge-case prose to skill references.

Content now follows the same validated ActionObject pattern. The
`wilq-content-strategist` smoke validates
`act_prepare_content_refresh_queue`, the eval case requires
`expected_validated_action_ids=["act_prepare_content_refresh_queue"]`, and the
passing artifact is
`.local-lab/evals/codex-skill/20260623T012450Z/wilq-content-strategist/result.json`.
The result has `operator_usefulness_score=4`,
`action_candidates[0].validation_state="validated"` and source connectors
`google_search_console`, `google_analytics_4`, `ahrefs`,
`wordpress_ekologus`, `wordpress_sklep`. This is now the strongest content
proof path: API decision queue plus WordPress inventory boundaries plus a
validated prepare/review ActionObject; it still blocks ranking, lead, revenue,
WordPress write and auto-publish claims.

Ads Doctor now follows the stricter validated ActionObject pattern for its
main review-only paths. The `wilq-ads-doctor` smoke validates
`act_prepare_ads_campaign_review_queue`,
`act_prepare_google_ads_recommendation_review_queue`,
`act_prepare_custom_segments_from_search_terms` and
`act_prepare_negative_keyword_review_queue` through
`POST /api/actions/{action_id}/validate`, and the eval case requires all four
in `expected_validated_action_ids`. Passing artifact:
`.local-lab/evals/codex-skill/20260623T013842Z/wilq-ads-doctor/result.json`.
The result has `operator_usefulness_score=5`,
`source_connectors=["google_ads"]`, four validated Ads action candidates and
no safety findings. It still blocks recommendation apply, negative keyword
apply, budget scaling, targeting/apply, CPA, ROAS and wasted-budget claims
without the missing review/apply/audit contracts.

Custom Segments now exposes the same standardized validation proof. The
`wilq-custom-segments` smoke returns `action_validations` for
`act_prepare_custom_segments_from_search_terms`, the eval case requires that
ActionObject in `expected_validated_action_ids`, and the passing artifact is
`.local-lab/evals/codex-skill/20260623T014325Z/wilq-custom-segments/result.json`.
The result has `operator_usefulness_score=4`, source connectors `google_ads`
and `google_search_console`, one validated action candidate and no safety
findings. Apply remains blocked by `custom_segment_apply_safety_v1` until
forecast/audience size, Keyword Planner enrichment, Google Ads mutation audit
and human confirmation exist.

GSC Content Doctor also follows the validated ActionObject pattern. The
`wilq-gsc-content-doctor` smoke validates `act_prepare_content_refresh_queue`,
the eval case requires it in `expected_validated_action_ids`, and the passing
artifact is
`.local-lab/evals/codex-skill/20260623T014727Z/wilq-gsc-content-doctor/result.json`.
The result has `operator_usefulness_score=4`, source connectors
`google_search_console`, `wordpress_ekologus`, `wordpress_sklep`, one
validated action candidate and no safety findings. It is the route-specific
GSC/query-page proof; broader content planning still belongs to
`wilq-content-strategist`.

Demand Gen now has validated review-only readiness proof. The
`wilq-demand-gen-operator` smoke validates `act_review_demand_gen_readiness`,
the eval case requires it in `expected_validated_action_ids`, and the passing
artifact is
`.local-lab/evals/codex-skill/20260623T015108Z/wilq-demand-gen-operator/result.json`.
The result has `blocked=true`, `operator_usefulness_score=4`, source
connectors `google_ads` and `google_analytics_4`, one validated action
candidate and no safety findings. This is not a Demand Gen launch proof; it is
an honest readiness/review gate while campaign migration, creative quality and
performance claims remain blocked.

Localo now has validated review-only visibility proof. The
`wilq-localo-operator` smoke validates `act_review_localo_visibility_facts`,
the eval case requires it in `expected_validated_action_ids`, and the passing
artifact is
`.local-lab/evals/codex-skill/20260623T015753Z/wilq-localo-operator/result.json`.
The result has `blocked=true`, `operator_usefulness_score=4`,
`source_connectors=["localo"]`, one validated action candidate and no safety
findings. This proves Localo MCP access/review wiring, not detailed ranking,
GBP, competitor visibility or local visibility uplift.

Daily Command now has validated core daily ActionObject proof. The
`wilq-daily-command` smoke validates `act_review_merchant_feed_issues`,
`act_prepare_content_refresh_queue` and `act_review_ga4_tracking_quality`
through `POST /api/actions/{action_id}/validate`, and the eval case requires
those three in `expected_validated_action_ids`. Passing artifact:
`.local-lab/evals/codex-skill/20260623T020946Z/wilq-daily-command/result.json`.
The result has `operator_usefulness_score=5`, source connectors across Ads,
GSC, GA4, Merchant, Ahrefs, Localo and WordPress, 26 evidence IDs, three
validated action candidates and no safety findings. Command Center
`daily_decisions` is intentionally capped to the four core daily decisions:
Merchant, Content, GA4 and Ads. Ads business-context and Localo review items
may remain in operator brief/action plan/route-specific surfaces, but must not
inflate the first-screen daily decision list unless they become the actual top
blocker or a real evidence-backed decision.

Social Publisher now has validated review-only draft ActionObject proof. The
`wilq-social-publisher` smoke validates
`act_prepare_linkedin_social_drafts` and
`act_prepare_facebook_social_drafts`, and the eval case requires both in
`expected_validated_action_ids`. Passing artifact:
`.local-lab/evals/codex-skill/20260623T021758Z/wilq-social-publisher/result.json`.
The result has `blocked=true`, `operator_usefulness_score=5`, two validated
social draft action candidates and no safety findings. This is intentionally a
blocked/review-only proof: LinkedIn/Facebook credentials and social evidence
are missing, so WILQ must not claim publishing ability or recommend actual
social output from nonexistent social data.

Campaign Builder now has validated review-only Ads planning proof. The
`wilq-campaign-builder` smoke validates
`act_prepare_ads_campaign_review_queue` and
`act_prepare_google_ads_recommendation_review_queue`, and the eval case
requires both in `expected_validated_action_ids`. Passing artifact:
`.local-lab/evals/codex-skill/20260623T022153Z/wilq-campaign-builder/result.json`.
The result has `operator_usefulness_score=4`, source connectors
`google_ads`, `google_analytics_4` and `google_search_console`, 15 evidence
IDs, two validated action candidates and no safety findings. This proves a
campaign/recommendation review queue, not campaign creation, mutation apply,
budget scaling or targeting changes.

Full local verification is green after the validated skill-eval series:
`scripts/verify.sh` passed with backend API contracts `156 passed`, dashboard
unit tests `17 passed`, Playwright e2e `14 passed`, skill/API smokes and
dashboard production build. Keep future tests state-aware: live evals may
require validated ActionObjects, but clean-runtime smoke fixtures must not fail
only because scoped context-packs have no live review actions yet.

## Product Bar

WILQ is an API-first marketing operating system for Ekologus, operated by a
Polish marketer through dashboard + Codex Desktop/CLI + WILQ skills. Ekologus
is the depth-first reference client. The long-term product direction is
agency/multi-client operation, but do not add broad multi-client abstractions
until Ekologus works deeply with real evidence, dashboard decisions, Codex
skills and safe ActionObjects.

WILQ is not:

- a connector dashboard,
- a prompt pack,
- a static report generator,
- a list of readiness cards,
- a place for invented marketing metrics.

The expected loop is:

1. Connector reads collect source facts.
2. WILQ normalizes facts into evidence IDs and metric facts.
3. Knowledge cards and expert rules map facts to diagnosis.
4. Opportunities and ActionObjects describe safe next moves.
5. Dashboard and Codex skills show the same evidence/action state.
6. Writes stay `dry_run -> preview -> confirm -> audit`.

Every marketer-facing response must be in Polish with Polish diacritics. Stable
API IDs, connector IDs, evidence IDs, enum values and endpoint paths remain in
their original form.

Skills are thin operator workflows over WILQ API. Do not put product decision
logic, dedupe rules, edge-case fixes or dashboard cleanup logic into skill
references. If a skill needs a smarter decision, implement the typed
API/schema/view-model first and make the skill consume that field.

## Delivery Expectation

Do not claim "better than BDOS" as done until the data/action contracts prove
it. A strong Ekologus demo can be delivered before the full product is complete:
dashboard decisions, WILQ API evidence, Polish Codex skills, ActionObject
safety, eval ledger and visible blocked claims. Ads now has a derived KPI read
contract for CTR/CPC/conversion rate/CPA/ROAS as calculations from campaign
facts, a read-only account currency contract, a read-only budget context
contract for campaign daily budgets versus 7-day cost, a read-only Google Ads
recommendations contract, a read-only Google Ads impression-share contract, a
read-only Google Ads change-history contract plus a review-only
`change_history_impact_review_v1` ActionObject path when change-event rows
exist, a typed Ads business context contract for profit margin, business goal,
budget goal and target ROAS/CPA inputs plus typed
`ads_business_target_interpretation_v1`, a read-only recommendation impact
preview for recommendation types that expose impact metrics, a review-only
recommendation apply payload preview, a read-only 90-day search-term safety
contract and a review-only negative keyword payload preview plus read-only
keyword match context for negative keyword review, a read-only search-term
n-gram contract for grouping repeated query themes plus a review-only
`search_term_ngram_review_v1` ActionObject path, plus a read-only Keyword
Planner enrichment contract for custom segment review. Custom segments now
have a review-only payload preview, a review-only targeting preview from real
search terms, and a typed nested
`ads_custom_segment_audience_forecast_read_contract` that produces
`missing_forecast` rows instead of hiding `forecast_or_audience_size` as only a
string. Custom segment payload previews now also expose typed
`custom_segment_apply_safety_v1` safety reviews: apply remains blocked, audit
is required, and missing requirements include forecast/audience size, Keyword
Planner enrichment, Google Ads mutation audit and human confirmation. Their
review reason preserves missing search-term impressions/cost as `brak danych`
instead of fake zeroes, but no custom segment targeting apply support.
Campaign budgets now have read-only budget pacing, typed
`shared_budget_distribution_rows` for campaigns sharing a Google Ads
`budget_id`, review-only `CampaignBudgetOperation` payload previews from
budget facts and typed `campaign_budget_apply_safety_v1` safety reviews that
keep budget apply blocked until missing requirements are satisfied. There is
still no budget apply support. Missing target ROAS/CPA now has a dedicated review-only
`act_confirm_ads_target_guardrails` ActionObject, and successful confirmations
are persisted as local `AdsTargetGuardrailConfirmation` state. Human Ads
strategy review now also has a typed review-only `act_record_ads_strategy_review`
ActionObject and persisted `AdsStrategyReviewRecord` local state. Target
confirmation alone does not unlock target verdict, apply or profitability
verdicts; target verdict remains preliminary until the latest strategy review is
`approved_for_prepare`.
Ads now also has a typed `campaign_triage_read_contract` that joins campaign
activity, derived KPI, budget pacing, recommendations, impression share and
business-context gaps into one review queue for the marketer. It is explicitly
review-only: it ranks what to inspect first and keeps `wasted budget`,
`profitability`, `budget scaling`, `budget apply`, `recommendation apply` and
`campaign mutation` blocked. The same contract is present in scoped
`wilq-ads-doctor` context-pack and is guarded by the skill smoke.
Full BDOS-class parity still requires optimizer contracts such as
live change-event rows plus pre/post change-impact windows, approved Keyword
Planner access/idea rows in live data, live forecast or audience-size data,
custom segment apply confirmation and mutation audit paths. Localo now has read-only aggregate
review facts for place inventory, local rankings and reviews plus a
`local_visibility_review_preview_v1` ActionObject preview; full Localo parity
still requires GBP visibility, competitor visibility, local task/write
contracts and proof that these facts are fresh enough for recommendations.
Merchant now has a typed review-only
`merchant_feed_issue_review_preview_v1` payload preview for issue clusters, so
the first Command Center decision can move from generic feed review to a
cluster-level review queue with evidence and safety gates.
Demand Gen now has typed empty-read contracts for ad inventory, creative
assets, landing quality by campaign and migration constraints. Current live
Ekologus evidence has no Demand Gen/Discovery campaign rows, so
`/api/demand-gen/diagnostics` correctly stays `status=blocked`, but
`missing_read_contracts=[]` means this is no longer a missing-implementation
blocker; it is an evidence/no-candidate blocker. Demand Gen launch, migration,
creative-quality verdicts, campaign apply and performance uplift claims remain
blocked.
GA4 now has a typed `ga4_conversion_readiness_contract` that keeps behavior
review separate from conversion/profitability claims. Current live Ekologus GA4
evidence has landing/source/campaign behavior rows, but no conversion-like
metrics, so `/api/ga4/diagnostics` correctly reports
`conversion_readiness_contract.status=blocked`,
`missing_read_contracts=[conversion_or_key_event_mapping]` and
`blocker_count=1` while still allowing review-only
`act_review_ga4_tracking_quality`. The dashboard and `wilq-ga4-analyst`
context-pack must show this same blocker instead of implying GA4 is fully ready
for ROAS, revenue, profitability, conversion-drop or attribution verdicts.
Missing contracts must be shown as blockers, not hidden with prompt language.

Ads search-term review now has a typed
`ads_search_term_review_summary_contract` that sits above raw
`search_terms_read_contract` rows. It aggregates search-term row count,
zero-conversion row count, clicks, impressions, cost, conversions, top cost
terms and campaign-level review rows so Ads Doctor can say "review these
queries/campaigns first" without claiming waste, CPA, ROAS or apply-ready
negative keywords. Live proof on 2026-06-22: status `ready`,
`total_search_term_count=50`, `zero_conversion_search_term_count=50`,
`total_cost_micros=45969902`, `campaign_review_rows=1`, blocked claims
`search-term waste`, `negative keyword apply`, `CPA`, `ROAS`; the same contract
is present in the scoped `wilq-ads-doctor` context-pack and dashboard
`/ads-doctor` renders `Kolejność review zapytań`.

Latest Ads campaign triage proof, 2026-06-22 10:22 CEST:
`/api/ads/diagnostics.campaign_triage_read_contract` is `ready` on live
Ekologus evidence with `triage_rows=18`. The top row is `(2026) Ekologus
Ogólna`, `review_priority=pilne`, `review_score=90`, `clicks=93`,
`cost_micros=60694109`, `roas=0`, `spend_to_budget_ratio_7d=0.867059`, and
ActionObject `act_prepare_ads_campaign_review_queue`. Scoped
`POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` includes the same
contract with `campaign_triage_rows_total=18`, compacted rows included for the
skill, and `context_pack_bytes=197058`. RED/GREEN proof:
`test_ads_diagnostics_exposes_live_campaign_metric_facts` and
`test_codex_context_pack_scopes_ads_doctor_payload` failed on missing
`campaign_triage_read_contract`, then passed after the typed schema/API/context
contract. `wilq-ads-doctor` smoke now requires this contract when campaign
rows are ready.

Latest dashboard detail route stability proof, 2026-06-22 11:55 CEST:
dashboard evidence/action detail routes no longer load broad registries when a
single detail object is enough. `/evidence/{evidence_id}` now uses
`GET /api/evidence/{evidence_id}` instead of waiting for the full evidence
registry, and ActionObject detail renders a bounded latest audit history while
preserving payload preview, evidence links, validation, preview, confirmation
and impact-check controls. This keeps the marketer's drilldown path connected
to live WILQ evidence without turning detail routes into registry dumps.
Final proof: `scripts/verify.sh` green, including 153 backend tests, 17
dashboard unit tests, Skill/API smokes, 14 Playwright e2e tests and dashboard
production build.

Latest Ads optimizer/readiness and Command Center cleanup proof, 2026-06-22
16:34 CEST: `/api/ads/diagnostics` exposes a typed
`optimizer_readiness_contract` that separates review-ready campaign/search
term/custom segment work from blocked change impact and apply safety. The
contract is present in shared schemas, `/ads-doctor`, scoped
`wilq-ads-doctor` context-pack and the Ads skill smoke. Ads context-pack now
compacts optimizer readiness and decision queue payloads; ActionObject detail
uses `GET /api/actions/{action_id}` instead of broad `/api/actions`, and
`/content-planner` no longer blocks the whole route on the full actions
registry. Command Center first screen now hides raw `ev_*`, `act_*`, `Skill:
wilq-*` and `Context-pack: /api/codex/context-pack`; it shows Polish status
labels, marketer-readable source names, proof counts and safe-action counts.
Browser proof on `http://127.0.0.1:5173/command-center` shows five decisions,
one blocker and seven sources without first-screen raw trace IDs. Final proof:
`scripts/verify.sh` green, including 153 backend tests, 17 dashboard unit
tests, Skill/API smokes, 14 Playwright e2e tests and dashboard production
build.

Latest Ads change-impact readiness proof, 2026-06-22 16:51 CEST:
`/api/ads/diagnostics` exposes typed
`change_impact_readiness_contract` as the bridge between raw
`change_history_read_contract` and optimizer item
`change_history_impact_review`. It reports whether change-event rows exist,
whether current campaign snapshots can be matched, allowed current/change
metrics, missing pre/post windows, evidence IDs and blocked claims. Ads Doctor
renders this as `Gotowość impact review zmian`, and `wilq-ads-doctor` smoke
requires the same contract in endpoint and scoped context-pack. Current live
Ekologus proof is intentionally blocked: no live change-event rows in the last
14 days, no pre/post windows, no human impact review and no apply preview. Do
not claim change impact, performance uplift, budget scaling, budget apply or
campaign mutation from this state.

Latest Ads strategy review readiness proof, 2026-06-22 17:25 CEST:
`/api/ads/diagnostics.business_context_read_contract` now exposes nested typed
`strategy_review_readiness_contract`. Current live Ekologus state is honest:
profit margin, business goal and budget goal are present, but target ROAS/CPA
and human strategy review are still missing. The nested contract is
`status=blocked`, `latest_review_status=missing`,
`action_ids=[act_record_ads_strategy_review]`, `apply_allowed=false`, and it
blocks profitability verdict, target KPI verdict, budget scaling, budget apply,
recommendation apply and automatic optimization. Ads Doctor renders this as
`Gotowość strategy review Ads`, and the scoped `wilq-ads-doctor` context-pack
includes the same safety gate. Context-pack compaction now also trims generic
ActionObject `review_gate` payloads; live smoke proof reports
`context_pack_bytes=192530`, below the 200 KB skill budget. This is not apply
support and does not make target verdicts safe; it only makes the blocker
typed, visible and testable for dashboard + Codex.

Latest Command Center daily focus and daily context-pack proof, 2026-06-22
17:52 CEST: `/api/dashboard/command-center.daily_decisions` is now capped to
the four core daily decisions: Merchant feed issues, Content SEO queue, GA4
measurement/traffic quality and Ads review queues. Localo can still appear in
`operator_brief`, `action_plan` and source health, but it is no longer promoted
as a primary "what to do now" card while full GBP/competitor/local task parity
is still incomplete. `wilq-daily-command` smoke now fails if non-core Localo
decisions leak into `daily_decisions` or if the live daily context-pack exceeds
180 KB. Live proof after stack restart: daily decisions
`decision_review_merchant_feed_issues`,
`decision_prepare_content_refresh_queue`,
`decision_review_ga4_landing_quality`,
`decision_review_ads_campaign_metrics`; daily context-pack size 174219 bytes
after compacting ActionObject review gates, refresh runs, evidence summaries
and opportunity summaries. `/api/opportunities` is deliberately decoupled from
the focused `daily_decisions`: it is derived from the broader `action_plan`, so
`opp_decision_review_localo_visibility_facts` remains available in the
opportunity registry while Localo stays out of the primary daily cards.

Latest Ads code-quality split proof, 2026-06-22 20:22 CEST:
`build_budget_pacing_read_contract` and its budget/shared-budget/apply-preview
helpers have been extracted from the large
`wilq/briefing/ads_diagnostics.py` into
`wilq/briefing/ads_budget_pacing.py`. This is intentionally a behavior-preserving
maintenance slice: `/api/ads/diagnostics` still exposes the same typed budget
pacing contract and Ads Doctor/Codex surfaces consume the same API state.
`ads_diagnostics.py` keeps section rendering and top-level orchestration while
the new module owns the read-contract row building. Proof:
`ads_diagnostics.py=6590` lines, `ads_budget_pacing.py=400` lines; ruff,
mypy, `tests/test_api_contracts.py` and full `scripts/verify.sh` passed,
including backend API contracts 154/154, dashboard unit tests 17/17,
Playwright 14/14 and dashboard production build. The first full verify attempt
hit a `custom segments` Playwright startup/process-contention failure; focused
rerun on a clean process passed, then full verify passed.

Latest Ads recommendations split proof, 2026-06-22 20:45 CEST:
`build_recommendations_read_contract` and its recommendation row, impact,
apply-preview and review-scoring helpers have been extracted from
`wilq/briefing/ads_diagnostics.py` into
`wilq/briefing/ads_recommendations.py`. This is the second behavior-preserving
Ads diagnostics split after budget pacing. `/api/ads/diagnostics` still exposes
the same typed recommendations read contract; `ads_diagnostics.py` still owns
top-level orchestration and the rendered `Rekomendacje Google Ads do review`
section. Proof so far: `ads_diagnostics.py=6179` lines,
`ads_recommendations.py=506` lines; ruff, mypy and
`tests/test_api_contracts.py` passed. Full `scripts/verify.sh` passed,
including backend API contracts 154/154, dashboard unit tests 17/17,
Playwright 14/14 and dashboard production build.

Latest Ads impression-share split proof, 2026-06-22 21:05 CEST:
`build_impression_share_read_contract` and impression-share row helpers have
been extracted from `wilq/briefing/ads_diagnostics.py` into
`wilq/briefing/ads_impression_share.py`. This is the third behavior-preserving
Ads diagnostics split after budget pacing and recommendations. `/api/ads/diagnostics`
still exposes the same typed impression-share read contract; `ads_diagnostics.py`
still owns top-level orchestration, campaign triage/optimizer composition and
the rendered `Udział w wyświetleniach Google Ads` section. Proof so far:
`ads_diagnostics.py=6029` lines, `ads_impression_share.py=188` lines; ruff,
mypy and `tests/test_api_contracts.py` passed. One full verify attempt hit a
non-reproducing action-detail Playwright route-load failure; the focused rerun
passed, then full `scripts/verify.sh` passed, including backend API contracts
154/154, dashboard unit tests 17/17, Playwright 14/14 and dashboard production
build.

Latest Ads change-history split proof, 2026-06-22 21:24 CEST:
`build_change_history_read_contract` and change-event row helpers have been
extracted from `wilq/briefing/ads_diagnostics.py` into
`wilq/briefing/ads_change_history.py`. This is the fourth behavior-preserving
Ads diagnostics split. `/api/ads/diagnostics` still exposes the same typed
change-history read contract; `ads_diagnostics.py` still owns top-level
orchestration, change-impact readiness composition, ActionObject ID enrichment
and the rendered `Historia zmian Google Ads` section. Proof:
`ads_diagnostics.py=5876` lines, `ads_change_history.py=195` lines; ruff,
mypy and `tests/test_api_contracts.py` passed. The dashboard e2e route helper
now applies the same route-ready timeout to headings after the loading state
disappears; focused action detail/workflows reruns passed, then full
`scripts/verify.sh` passed, including backend API contracts 154/154, dashboard
unit tests 17/17, Playwright 14/14 and dashboard production build.

Latest Custom Segments apply/audit safety proof, 2026-06-22 04:55 CEST:
`/api/ads/diagnostics.custom_segments_read_contract.payload_preview[0]` and
scoped `POST /api/codex/context-pack {"skill":"wilq-custom-segments"}` both
carry `safety_review.safety_contract=custom_segment_apply_safety_v1` with
`status=blocked`, `apply_allowed=false`, `api_mutation_ready=false`,
`audit_required=true` and missing requirements
`forecast_or_audience_size`, `keyword_planner_enrichment`,
`google_ads_mutation_audit`, `human_confirm_before_apply`. RED/GREEN proof:
`test_ads_diagnostics_exposes_live_campaign_metric_facts` failed on missing
`safety_review`; `test_codex_context_pack_scopes_custom_segments_payload`
failed because context-pack compaction dropped it. Both now pass, and
`wilq-custom-segments` smoke requires the safety review. Final proof:
`scripts/verify.sh` green, including 150 backend tests, 17 dashboard unit
tests, Skill API smoke, 14 Playwright e2e tests and dashboard production build.

Latest Ads source-backed knowledge/rule lineage proof, 2026-06-22 06:02 CEST:
`wilq-ads-doctor` now has explicit eval/smoke/API guardrails for the chain
knowledge card / expert rule -> `/api/ads/diagnostics.decision_queue` ->
scoped context-pack -> Polish Codex output. The scoped context-pack contains
`knowledge_card_summaries=7` and `expert_rule_summaries=8`, and the API test
plus skill smoke fail if a decision references a card/rule ID that is missing
from those summaries. Non-interactive eval passed at
`.local-lab/evals/codex-skill/20260622T040032Z/wilq-ads-doctor/result.json`
with `language=pl-PL`, `api_used=true`, source connector `google_ads`,
Google Ads evidence IDs, seven knowledge cards, eight expert rules, four
review ActionObject candidates and `operator_usefulness_score=5`. This proves
source/rule lineage for Ads review; it still does not unlock CPA/ROAS, wasted
budget, budget scaling, recommendation apply, targeting apply or negative
keyword apply.

Latest Content ActionObject preview preservation proof, 2026-06-22 05:54 CEST:
`/api/content/diagnostics` and `act_prepare_content_refresh_queue` now preserve
the same dimensioned GSC/WordPress evidence path. The regression was that newer
aggregate GSC facts could push older `query/page` facts out of the ActionObject
metric read, leaving content decisions without `content_brief_preview`.
`wilq/actions/service.py` now gives content connectors larger ActionObject
metric fact limits, matching the broader diagnostics path. RED/GREEN proof:
`test_content_action_preview_keeps_dimensioned_decisions_after_newer_aggregate_runs`
failed on empty preview, then passed. Live proof after
`scripts/local_stack.sh restart`: `/api/content/diagnostics`
`decision_count=5`, `/api/actions/act_prepare_content_refresh_queue`
`content_preview_count=8`, first preview
`content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca`,
`apply_allowed=false`, `api_mutation_ready=false`; scoped
`POST /api/codex/context-pack {"skill":"wilq-content-strategist"}` returns
`content_preview_count=4` and `content_decisions=5`. Final proof:
`scripts/verify.sh` green, including 151 backend tests, 17 dashboard unit
tests, Skill API smoke, 14 Playwright e2e tests and dashboard production build.

Latest Content brief homepage traceability proof, 2026-06-22 08:41 CEST:
`act_prepare_content_refresh_queue` no longer emits the root-page candidate as
`content_brief_gsc_`. Homepage content brief previews now slug the host when
the normalized URL path is `/`, so the Ekologus homepage candidate becomes
`content_brief_gsc_www_ekologus_pl`. This matters for operator review,
audit-event summaries and later WordPress draft preview lineage. RED/GREEN
proof: `test_content_brief_preview_homepage_candidate_id_is_traceable` failed
on the old empty suffix and now passes. Live proof after
`scripts/local_stack.sh restart`: `/api/actions/act_prepare_content_refresh_queue`
returns `preview_count=8`, homepage preview
`candidate_id=content_brief_gsc_www_ekologus_pl`, topic `ekologus`,
`apply_allowed=false`, `api_mutation_ready=false` and evidence
`ev_refresh_refresh_google_search_console_554550c44ec7`. Narrow checks passed:
ruff, mypy and the content/action API contract subset. Final proof:
`scripts/verify.sh` green, including 152 backend tests, 17 dashboard unit
tests, Skill/API smokes, 14 Playwright e2e tests and dashboard production
build.

Latest Content review-to-Codex draft preview proof, 2026-06-22 09:58 CEST:
when an operator reviews a content brief candidate, scoped
`POST /api/codex/context-pack {"skill":"wilq-content-strategist"}` now exposes
a compacted `wordpress_draft_payload_preview` contract with
`wordpress_draft_payload_preview_total`, `wordpress_draft_payload_preview_included`,
candidate ID, `post_status=draft`, evidence IDs, blocked claims and
`apply_allowed=false` / `api_mutation_ready=false`. This connects dashboard
operator selection to Codex skill context without dumping the full WordPress
payload or implying publication. RED/GREEN proof:
`test_content_strategist_context_pack_preserves_reviewed_draft_preview` failed
on missing `wordpress_draft_payload_preview_total`, then passed after context
compaction. Live proof after `scripts/local_stack.sh restart`: reviewing
`content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca` makes the
`wilq-content-strategist` context-pack return `draft_total=1`,
`draft_included=1`, `post_status=draft`, `apply_allowed=false`,
`api_mutation_ready=false` and evidence
`ev_refresh_refresh_google_search_console_554550c44ec7`. Narrow checks passed:
ruff, mypy and the content/action/context-pack API subset. Verification
follow-up: Playwright route smoke had a loading-state race under heavy
API-backed routes. The e2e route helper now waits for `Ładowanie stanu WILQ API`
to disappear before first route heading assertions, and Playwright is
configured for one worker to match `scripts/verify.sh` and avoid concurrent
demo-proof/API smoke contention. Final proof: `scripts/verify.sh` green,
including 153 backend tests, 17 dashboard unit tests, Skill/API smokes,
14 Playwright e2e tests and dashboard production build.

Latest Ads Doctor ActionObject scope compaction proof, 2026-06-22 01:40 CEST:
`wilq-ads-doctor` now has an explicit ActionObject allowlist. It no longer
pulls every `google_ads` ActionObject into the scoped context-pack, so
`act_review_demand_gen_readiness` stays in `wilq-demand-gen-operator` and is
not duplicated in Ads Doctor. RED/GREEN proof:
`tests/test_api_contracts.py::test_codex_context_pack_scopes_ads_doctor_payload`
failed before the fix because Demand Gen readiness appeared in Ads Doctor
context; after the allowlist, it passed together with
`test_codex_context_pack_scopes_demand_gen_payload`, proving the Demand Gen
skill still receives its own ActionObject. Live smoke after
`scripts/local_stack.sh restart`: `wilq-ads-doctor`
`context_pack_bytes=191793`, down from the previous `198997`, while preserving
campaign review, recommendation review, n-gram review, custom segments,
negative keywords, target guardrails, strategy review and Keyword Planner
access ActionObjects.

Latest Ads n-gram review missing-contract precision, 2026-06-22 03:38 CEST:
search-term n-gram review now uses the n-gram-specific missing read contract
`ngram_to_negative_keyword_payload_preview`, not the generic
`negative_keyword_payload_preview` used by the negative keyword review queue.
This prevents dashboard/Codex confusion where a review-only n-gram decision
looked like the normal negative keyword payload preview was missing. RED/GREEN
proof: `tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts`
failed before the fix on the old generic missing contract, then passed.
Live proof after `scripts/local_stack.sh restart`:
`/api/ads/diagnostics.search_term_ngram_read_contract.missing_read_contracts`
and decision `ads_review_search_term_ngrams.missing_read_contracts` both show
`[human_intent_review, ngram_to_negative_keyword_payload_preview]`, while
`negative_keywords_read_contract.missing_read_contracts=[]`. Dashboard labels
the new blocker in Polish as `podgląd payloadu wykluczeń z n-gramów`; the
`wilq-ads-doctor` smoke script fails if the n-gram contract regresses to the
generic negative keyword payload preview blocker. Final proof:
`scripts/verify.sh` green, including 150 backend tests, 17 dashboard unit
tests, Skill API smoke, 14 Playwright e2e tests and dashboard production build.

Latest Ads shared-budget distribution proof, 2026-06-22 01:25 CEST:
`/api/ads/diagnostics.budget_pacing_read_contract` exposes typed
`shared_budget_distribution_rows`. WILQ now groups campaign budget rows by
Google Ads `budget_id`, computes shared-budget campaign shares and removes
`shared_budget_distribution` from `missing_read_contracts` when all live budget
rows expose `budget_id`. Live proof after `scripts/local_stack.sh restart`:
`budget_rows=18`, `shared_rows=0`, `missing=[]`; decision
`ads_review_budget_context` has `missing_read_contracts=[]` and metric tiles
`budżety=18`, `podgląd budżetu=18`, `koszt 7 dni=154`, without a useless
zero-value shared-budget tile. Dashboard `/ads-doctor` renders
`Podział wspólnych budżetów` with an honest empty-state when no campaigns share
a budget. `wilq-ads-doctor` smoke now fails if the typed field is absent or if
the context-pack omits it. Non-interactive Codex eval passed at
`.local-lab/evals/codex-skill/20260621T232046Z/wilq-ads-doctor/result.json`
with `language=pl-PL`, `api_used=true`, source connector `google_ads` and
Google Ads evidence IDs. Final verification passed: `scripts/verify.sh` green,
including 150 backend tests, 17 dashboard unit tests, API/skill smokes,
14 Playwright e2e tests and dashboard production build. Later follow-up:
ActionObject scope compaction reduced the scoped `wilq-ads-doctor` context-pack
from `198997` to `191793` bytes.

Previous Ads change-history empty-read + context-pack budget proof, 2026-06-22
00:56 CEST: WILQ no longer treats an attempted read-only Google Ads
change-history read with 0 `change_event` rows as a generic missing
`change_history` contract on every Ads decision. Live `/api/ads/diagnostics`
after `scripts/local_stack.sh restart` reports
`change_history_read_contract.status=blocked`, `change_history_rows=[]` and
missing contracts `change_event_rows`, `pre_change_performance_window`,
`post_change_performance_window`, `human_change_impact_review` and
`apply_preview`. Decisions `ads_review_campaign_activity`,
`ads_review_derived_kpis`, `ads_review_recommendations` and
`ads_review_impression_share` no longer list `change_history` as missing;
`ads_review_budget_context` still listed `shared_budget_distribution`; that
specific missing contract is fixed by the later shared-budget distribution
slice. `ads_review_change_history` stays blocked with `zmiany=0`. Scoped
`wilq-ads-doctor` context-pack compaction now keeps common Ads row samples at
3 rows and preserves total/included counts in `context_pack_compaction`; the
full `/api/ads/diagnostics` endpoint is not cut by this limit. Live context
proof: HTTP/JQ size about 188 KB, smoke `context_pack_bytes=198343`, below the
200 KB skill budget. `wilq-ads-doctor` smoke passed. Non-interactive Codex eval
passed at
`.local-lab/evals/codex-skill/20260621T223847Z/wilq-ads-doctor/result.json`
with `language=pl-PL`, `api_used=true`, `operator_usefulness_score=5`, source
connector `google_ads` and Google Ads evidence IDs. Final verification passed:
`scripts/verify.sh` green, including 149 backend tests, 17 dashboard unit
tests, API/skill smokes, 14 Playwright e2e tests and dashboard production
build.

Latest Custom Segments forecast/audience-size proof, 2026-06-22 00:21 CEST:
`/api/ads/diagnostics.custom_segments_read_contract` now exposes nested
`audience_forecast_read_contract`, not only a loose
`forecast_or_audience_size` missing string. Live HTTP proof after
`scripts/local_stack.sh restart`: `custom_segments_read_contract.status=ready`,
`candidates=1`, `payload_preview=1`, missing contracts
`keyword_planner_enrichment` and `forecast_or_audience_size`,
`audience_forecast_read_contract.status=blocked`,
`checked_candidate_count=1`, `forecast_row_count=1`; the first row has
`status=missing_forecast`, `forecast_available=false`,
`audience_size=null`, source terms and Google Ads evidence IDs. Decision
`ads_prepare_custom_segments_from_search_terms` carries
`custom_segment_audience_forecast_rows`, so dashboard, API and
`wilq-custom-segments` see the same blocker. `/custom-segments` and Ads Doctor
render the forecast/audience-size panel. `wilq-custom-segments` smoke passed.
Non-interactive Codex eval passed at
`.local-lab/evals/codex-skill/20260621T221018Z/wilq-custom-segments/result.json`
with `language=pl-PL`, `api_used=true`, `operator_usefulness_score=4`, source
connectors `google_ads` and `google_search_console`, Google Ads evidence IDs,
ActionObject `act_prepare_custom_segments_from_search_terms`, blocked action
candidate for `audience_forecast_read_contract.status=blocked`,
`missing_forecast` and blocked claims `audience size`, `ROAS`,
`targeting applied`, `campaign performance`. Final verification passed:
`scripts/verify.sh` green, including 149 backend tests, 17 dashboard unit
tests, API/skill smokes, 14 Playwright e2e tests and dashboard production
build.

Latest Demand Gen landing/migration empty-read proof, 2026-06-21 23:40 CEST:
`/api/demand-gen/diagnostics` exposes available read contracts
`demand_gen_campaign_rows`, `demand_gen_ad_group_ad_rows`,
`demand_gen_creative_asset_rows`, `demand_gen_landing_quality_by_campaign`,
`demand_gen_migration_constraints` and
`demand_gen_readiness_review_action_object`. Live HTTP proof after
`scripts/local_stack.sh restart`: `status=blocked`, `kampanie Ads=18`,
`kanały=2`, `wiersze DG=0`, `reklamy DG=0`, `assety DG=0`, `landingi DG=0`,
`ograniczenia=0`, `braki=0`, `missing_read_contracts=[]`. Payload preview
keeps `apply_allowed=false`, `api_mutation_ready=false` and
`destructive=false`. Regression test
`tests/test_api_contracts.py::test_demand_gen_diagnostics_uses_empty_read_ad_and_asset_contracts`
now seeds one Demand Gen campaign plus matching GA4 landing facts and requires
1 landing-quality row plus 1 migration-constraint row. `wilq-demand-gen-operator`
smoke passed, non-interactive Codex eval passed at
`.local-lab/evals/codex-skill/20260621T212918Z/wilq-demand-gen-operator/result.json`
with `language=pl-PL`, `api_used=true`, source connectors Google Ads + GA4,
`operator_usefulness_score=4`, `blocked=true` and ActionObject candidate
`act_review_demand_gen_readiness`. Final verification passed:
`scripts/verify.sh` green, including 149 backend tests, 17 dashboard unit
tests, API/skill smokes, 14 Playwright e2e tests and dashboard production
build.

Latest Ads Doctor context-pack consistency proof, 2026-06-21 20:59 CEST:
scoped `wilq-ads-doctor` context-pack now preserves all
`recommendations_read_contract.recommendation_rows` with
`impact_available=true` instead of blindly taking the first three rows. This
fixes the failed non-interactive eval at
`.local-lab/evals/codex-skill/20260621T184838Z/wilq-ads-doctor/result.json`,
where the smoke correctly blocked because Codex would have received only one
of two recommendation impact rows from live Ads evidence. Live proof after
`scripts/local_stack.sh restart`: `/api/ads/diagnostics` has
`recommendation_rows=4`, `impact_rows=2`; scoped
`POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` has compacted
`recommendation_rows=3`, `impact_rows=2`, `payload_preview=4`, and
`context_pack_bytes=198755`. Regression test:
`tests/test_api_contracts.py::test_ads_doctor_context_pack_preserves_recommendation_impact_rows`.
`wilq-ads-doctor` smoke passed, and non-interactive Codex eval passed at
`.local-lab/evals/codex-skill/20260621T185704Z/wilq-ads-doctor/result.json`
with `language=pl-PL`, `api_used=true`, `operator_usefulness_score=5`,
Google Ads evidence IDs, required Ads knowledge cards and expert rules.
Read-only diagnosis is usable again; CPA/ROAS, wasted budget, search-term
waste and every write/apply path remain blocked without human review,
validated ActionObject and audit/apply contracts. Final verification passed on
2026-06-21 21:18 CEST: `scripts/verify.sh` green, including 147 backend tests,
17 dashboard unit tests, API/skill smokes, 14 Playwright e2e tests and dashboard
production build. The first full verify attempt hit a transient Playwright
`ERR_NETWORK_CHANGED` on `/workflows`; the narrow rerun of `/workflows` and
`/knowledge` passed, then the full verify rerun passed.

Latest Ads search-term visibility proof, 2026-06-21 20:30 CEST:
large Google Ads refreshes must not hide search-term evidence from diagnostics,
ActionObjects or Command Center. The root cause was two inconsistent silent
metric-fact caps: Ads diagnostics asked for 2500 facts while DuckDB store and
ActionObject seeding could cap Google Ads to 2000, which let large refreshes
show campaign facts but drop `search_term_*` facts from the active view.
`MAX_METRIC_FACT_READ_LIMIT=5000` is now the shared store cap and Google Ads
ActionObject seeding uses the same cap. Regression fixture covers a refresh with
more than 2000 neutral filler facts before the real search-term facts. Live HTTP
proof after `scripts/local_stack.sh restart`: `/api/ads/diagnostics` shows
`search_terms_read_contract.status=ready` with 50 search-term rows,
`search_term_ngram_read_contract.status=ready` with 30 n-gram rows and
`act_review_ads_search_term_ngrams`, `negative_keywords_read_contract.status=ready`
with 6 candidates, and `custom_segments_read_contract.status=ready` with 1
candidate. `/api/dashboard/command-center` now shows the Ads daily decision as
`ready` with metric tiles `kampanie=18`, `zapytania=50`, `podgląd budżetu=18`,
`rekomendacje=4`, `wykluczenia=6`, `segmenty=1`. Final verification passed on
2026-06-21 20:45 CEST: `scripts/verify.sh` green, including 146 backend tests,
17 dashboard unit tests, API/skill smokes, 14 Playwright e2e tests and
dashboard production build.

Latest Merchant issue review contract proof, 2026-06-21 19:35 CEST:
`act_review_merchant_feed_issues` now exposes
`merchant_feed_issue_review_preview_v1` in `payload.preview_contract` and
`payload.payload_preview`: Merchant issue cluster IDs aligned with
`/api/merchant/diagnostics`, issue type/attribute/country/context/severity,
`metric_snapshot`, sample-unavailable reason, required validation, blocked
claims and hard `apply_allowed=false` / `api_mutation_ready=false` /
`destructive=false`. `POST /api/codex/context-pack
{"skill":"wilq-merchant-feed-operator"}` keeps a compact payload preview for
the Merchant skill. Non-interactive eval passed at
`.local-lab/evals/codex-skill/20260621T173358Z/wilq-merchant-feed-operator/result.json`
with `language=pl-PL`, `api_used=true`, `operator_usefulness_score=5`,
source connector `google_merchant_center`, evidence IDs
`ev_connector_google_merchant_center_status` and
`ev_refresh_refresh_google_merchant_center_a3ef2f66703f`, action candidate
`act_review_merchant_feed_issues`, and recommendations that mention
`merchant_feed_issue_review_preview_v1`. This still does not unlock automatic
feed edits, product mutation, approval restored or revenue recovered claims.
Final verification for this slice passed on 2026-06-21 20:15 CEST:
`scripts/verify.sh` green, including 146 backend tests, 17 dashboard unit tests,
skill structure/API smokes, 14 Playwright e2e tests and dashboard production
build. Test stability fix from this verification: Ads/custom-segments API tests
now seed their own search-term facts instead of relying on private `.local-lab`
state, and dashboard e2e smoke accepts either ready or evidence-backed blocker
state for Ads/Custom Segments/Ahrefs while still rejecting generic registry
junk.

Latest Localo value contract proof, 2026-06-21 18:59 CEST:
`act_review_localo_visibility_facts` now exposes a typed
`local_visibility_review_preview_v1` payload preview with Localo metric
snapshot, allowed contracts (`place_inventory`, `local_rankings`, `reviews`),
missing contracts (`gbp_visibility`, `competitor_visibility`, `local_tasks`),
blocked claims and `apply_allowed=false` / `api_mutation_ready=false`.
`POST /api/codex/context-pack {"skill":"wilq-localo-operator"}` keeps one
compacted preview item, so Codex and dashboard/actions API see the same
ActionObject. `wilq-localo-operator` non-interactive eval passed at
`.local-lab/evals/codex-skill/20260621T165825Z/wilq-localo-operator/result.json`
with `language=pl-PL`, `api_used=true`, `source_connectors=["localo"]`,
evidence IDs including `ev_connector_localo_status` and
`ev_refresh_refresh_localo_9928e881eef7`, action candidate
`act_review_localo_visibility_facts`, and blocked claims for ranking/GBP/
competitor/local visibility uplift beyond current evidence.
Final verification for this slice passed on 2026-06-21 19:21 CEST:
`scripts/verify.sh` green, including 145 backend tests, 17 dashboard unit tests,
skill structure/API smokes, 14 Playwright e2e tests and dashboard production
build. The only verify blocker found during this slice was an outdated Ahrefs
e2e expectation: Ahrefs currently exposes typed `competitor_page` records while
content/backlink gap contracts are intentionally still missing. The test now
checks the current typed gap record contract instead of expecting the old
`Luka treści:` marker.

Latest Ads human strategy review state truth, contract proof
2026-06-21 16:51 CEST: `act_record_ads_strategy_review` records operator review
outcomes through the standard ActionObject review path and persists
`AdsStrategyReviewRecord` in SQLite local state with action ID, outcome,
reviewer, notes, checked items, blockers, audit event ID and evidence IDs.
`/api/ads/diagnostics.business_context_read_contract` now exposes
`strategy_review_status`, `strategy_reviewed_by`, `strategy_reviewed_at` and
`strategy_review_summary`. If no strategy review exists, WILQ shows missing
contract `human_strategy_review`; if review exists but is not
`approved_for_prepare`, WILQ shows `approved_human_strategy_review`. Target
ROAS/CPA can be used only as review context until strategy review is approved;
then `target_interpretation.status=ready` and the active strategy ActionObject is
removed. This still does not unlock profitability verdicts, budget apply,
recommendation apply, automatic scaling or Google Ads mutations. Current live
operator state after `scripts/local_stack.sh restart`: no target and no strategy
review are recorded yet, so Ads diagnostics correctly shows
`missing_read_contracts=["target_roas_or_cpa", "human_strategy_review"]`,
`strategy_review_status=missing`, `target_interpretation.status=preliminary`,
and action IDs `act_confirm_ads_target_guardrails` plus
`act_record_ads_strategy_review`; validating the strategy review ActionObject
returns `valid=true`.

Latest Ads target guardrail confirmation state truth, contract proof
2026-06-21 16:05 CEST: target ROAS/CPA confirmation is now an API/local-state
contract, not only a `.env` instruction. `ActionConfirmRequest` accepts
`target_roas` or `target_cpa_micros`; the `confirm_ads_target_guardrails`
confirm path requires exactly one target, records audit event
`ads_target_guardrail_confirmed`, and persists `AdsTargetGuardrailConfirmation`
in SQLite local state. Ads diagnostics reads `.env` first and then local state,
so a confirmed target removes `target_roas_or_cpa` from
`business_context_read_contract.missing_read_contracts`, removes the target
portion of `target_interpretation.missing_requirements`, and removes
`act_confirm_ads_target_guardrails` from active `action_ids`. After the
2026-06-21 strategy-review slice, `target_interpretation.status=ready` requires
both target confirmation and `approved_for_prepare` strategy review. This still
does not unlock profitability verdicts, budget apply, recommendation apply,
automatic scaling or Google Ads mutations.

Latest Ads search-term n-gram review truth, live proof 2026-06-21 15:38 CEST:
`ads_review_search_term_ngrams` now has a concrete review-only ActionObject,
not only a table of repeated search-term themes. Live `/api/ads/diagnostics`
shows `act_review_ads_search_term_ngrams` in top-level `action_ids`,
`search_term_ngram_read_contract.action_ids`,
`sections[id=ads_search_term_ngrams].action_ids` and
`decision_queue[id=ads_review_search_term_ngrams].action_ids`. The full
ActionObject payload uses `action_type=google_ads_search_term_ngram_review`,
`preview_contract=search_term_ngram_review_v1`, keeps `ngram_preview` rows
with sample search terms and metric snapshots, and stays review-only with
`apply_allowed=false`, `api_mutation_ready=false` and `destructive=false`.
`/api/actions/act_review_ads_search_term_ngrams/validate` returns
`valid=true`. Scoped `wilq-ads-doctor` context-pack remains below the size
limit at about `182599` chars, keeps the action type unredacted and includes
only one compact n-gram preview anchor. This still does not unlock search-term
waste, negative keyword apply, conversion loss, CPA or ROAS claims.

Latest Ads change-history impact truth, live proof 2026-06-21 15:12 CEST:
WILQ now has a typed review-only path for change history impact review, but it
does not appear without real change-event rows. In seeded contract tests,
`change_history_read_contract.action_ids`,
`sections[id=ads_change_history].action_ids`,
`decision_queue[id=ads_review_change_history].action_ids` and
`/api/actions/act_review_ads_change_history_impact/validate` are connected to
`act_review_ads_change_history_impact`. Its payload uses
`action_type=google_ads_change_history_impact_review`,
`preview_contract=change_history_impact_review_v1`,
`operation_type=ChangeHistoryImpactReview`, carries
`change_history_preview`, `missing_read_contracts` for pre/post performance
windows, human review and apply preview, and keeps `apply_allowed=false`,
`api_mutation_ready=false` and `destructive=false`. Live local Ads diagnostics
after stack restart still report `change_history_read_contract.status=blocked`,
`rows=0`, `action_ids=[]`; `/api/actions/act_review_ads_change_history_impact`
returns 404. This is correct: no change-event evidence means no impact claim
and no review ActionObject.

Latest Ads target guardrail confirmation truth, live proof 2026-06-21
14:31 CEST: missing `target_roas_or_cpa` is now an operational ActionObject,
not just prose in the Ads business context. `/api/ads/diagnostics.action_ids`,
`business_context_read_contract.target_interpretation.action_ids`,
`sections[id=ads_business_context].action_ids` and
`decision_queue[id=ads_review_business_context].action_ids` include
`act_confirm_ads_target_guardrails`. `/api/actions/act_confirm_ads_target_guardrails`
returns a review-only payload with `action_type=confirm_ads_target_guardrails`,
current non-secret business context, target env options
`WILQ_ADS_TARGET_ROAS` and `WILQ_ADS_TARGET_CPA_MICROS`,
`missing_read_contracts=[target_roas_or_cpa]`, `apply_allowed=false` and
`destructive=false`. Its validation endpoint returns `valid=true`. This still
does not confirm target KPI, profitability, budget apply or recommendation
apply. Scoped `wilq-ads-doctor` context-pack preserves
`credential_source=repo_env` and `created_by=system_ads_target_confirmation_seed`
without `[REDACTED]` on this ActionObject. Full `scripts/verify.sh` passed for
this slice: backend `144 passed`, dashboard unit `17 passed`, Playwright
`14 passed`, skill smokes and dashboard build.

Latest Ads business target interpretation truth, live proof 2026-06-21
14:11 CEST: `business_context_read_contract.target_interpretation` now carries
`interpretation_contract=ads_business_target_interpretation_v1`. Current
Ekologus state is `status=preliminary`: WILQ can use profit margin, business
goal and human budget goal as campaign/budget review context, but blocks
`target_kpi_verdict`, `profitability_verdict`, `budget_scaling`,
`budget_apply` and `recommendation_apply` until `target_roas_or_cpa` and apply
gates are confirmed. Scoped `wilq-ads-doctor` context-pack preserves this
contract without `[REDACTED]` (`redacted=false`, about `185814` bytes).
Dashboard `/ads-doctor` shows `Interpretacja celu biznesowego Ads`. Full
`scripts/verify.sh` passed for this slice: backend `144 passed`, dashboard
unit `17 passed`, Playwright `14 passed`, skill smokes and dashboard build.

Latest Ads budget apply safety truth, live proof 2026-06-21 13:50 CEST:
`/api/ads/diagnostics.budget_pacing_read_contract.payload_preview[*]` and
`act_prepare_ads_campaign_review_queue.payload.budget_payload_preview[*]`
now include `safety_review.safety_contract=campaign_budget_apply_safety_v1`.
The safety review carries `status=blocked`, `max_allowed_delta_percent=0.3`,
missing requirements such as `change_history`, `human_budget_goal`,
`mutation_audit`, `human_confirm_before_apply`, `recommended_budget_missing`
and `budget_delta_percent`, plus evidence IDs and hard
`apply_allowed=false`, `api_mutation_ready=false`, `destructive=false`.
Scoped `wilq-ads-doctor` context-pack keeps a compacted safety review under
200 KB (`4` budget preview rows, about `184632` bytes). Dashboard `/ads-doctor`
shows the safety contract and first missing requirements in the budget pacing
table. This still does not unlock Google Ads budget mutation: vendor apply,
operator confirmation and mutation audit remain blocked. Full
`scripts/verify.sh` passed for this slice: backend `144 passed`, dashboard
unit `17 passed`, Playwright `14 passed`, skill smokes and dashboard build.

Latest GA4 tracking-quality preview truth, live proof 2026-06-21 13:17 CEST:
`act_review_ga4_tracking_quality` now exposes typed review-only
`ga4_tracking_quality_review_v1` payload preview rows instead of only generic
GA4 metrics. The preview groups landing/source/campaign facts, marks missing
reporting dimensions such as `(not set)`, carries metric snapshots, evidence
IDs, required validation `review_landing_page_dimension`,
`review_source_medium_dimension`, `review_campaign_name_dimension`,
`review_conversion_or_key_event_mapping` and
`human_confirm_before_tracking_change`, and keeps `apply_allowed=false`,
`api_mutation_ready=false` and `destructive=false`. Its validation endpoint
returns `valid=true`. Scoped `wilq-ga4-analyst` context-pack now preserves a
compacted version of the same preview (`4` rows, about `57758` bytes), so Codex
and dashboard use the same ActionObject state. Dashboard `/ga4` renders
`Podgląd review GA4`. This still does not unlock conversion rate, ROAS, revenue,
profitability, funnel diagnosis, attribution verdict, tracking fixed or GA4
write claims.

Latest Ads custom segment targeting preview truth, live proof 2026-06-21
12:46 CEST: custom segments now expose a typed review-only targeting preview,
not just keyword member preview. `/api/ads/diagnostics.custom_segments_read_contract`
and decision `ads_prepare_custom_segments_from_search_terms` include
`payload_preview[0].targeting_preview[0]` with
`target_scope=campaign_context_review`,
`operation_type=custom_segment_targeting_review`, campaign context
`Kompendium PPWR`, required validation `keyword_planner_enrichment`,
`forecast_or_audience_size`, `human_confirm_before_apply` and
`mutation_audit_required`. The same preview is present in
`act_prepare_custom_segments_from_search_terms`, whose validation endpoint
returns `valid=true`. Scoped `wilq-custom-segments` context-pack is about
`50087` bytes and preserves `custom_segment_preview_id` so Codex can trace the
segment preview to targeting preview. This still does not unlock audience size,
forecast, targeting applied, ROAS, campaign performance or vendor mutation.

Latest Localo visibility ActionObject truth, live proof 2026-06-21
12:22 CEST: Localo aggregate evidence is now connected to a review-safe
ActionObject instead of being shown only as readiness text. `/api/localo/diagnostics`
returns `live_data_available=true`,
`action_ids=[act_review_localo_visibility_facts]`, a ready decision
`localo_review_visibility_facts` and a separate blocked decision for claims
without read contracts. `act_review_localo_visibility_facts` is a prepare-only
Localo ActionObject with payload type `local_visibility_task`, evidence
`ev_refresh_refresh_localo_9e9ff67eadad`, `allowed_contracts=[place_inventory,
local_rankings, reviews]`, `missing_read_contracts=[gbp_visibility,
competitor_visibility, local_tasks]`, `apply_allowed=false` and
`destructive=false`. Its validation endpoint returns `valid=true`. Command
Center and scoped `wilq-localo-operator` context-pack expose the same action ID.
Still blocked: GBP performance, competitor visibility, local tasks, GBP writes
and local visibility uplift until typed Localo read/write contracts exist.

Latest Google Ads Keyword Planner approval truth, live proof 2026-06-21
11:40 CEST: Google Ads live reads can work while Keyword Planner enrichment is
blocked by Google Ads API approval state. WILQ now exposes that state as
review-only ActionObject `act_configure_google_ads_keyword_planner_access`
instead of hiding it inside prose or treating it as a missing prompt. The
payload type is `configure_google_ads_keyword_planner_access`; it carries
evidence IDs, `blocked_api=Keyword Planner`, sanitized
`PERMISSION_DENIED: DEVELOPER_TOKEN_NOT_APPROVED`, required validation,
blocked claims, `apply_allowed=false` and `destructive=false`. The action is
available in `/api/actions` and scoped `wilq-ads-doctor` context-pack, but it
is filtered out of the general Command Center Ads daily item so the marketer
does not see access repair as a campaign optimization task. Focused proof:
ruff, mypy and targeted API tests passed; scoped `wilq-ads-doctor`
context-pack is `199512` bytes, under the 200 KB limit. Full
`scripts/verify.sh` passed after this slice: backend `144 passed`, dashboard
unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and dashboard
production build passed.

Latest Ads section ActionObject ownership truth, live proof 2026-06-21
12:05 CEST: `act_configure_google_ads_keyword_planner_access` is no longer
shown as a generic Ads campaign/search-term action. Top-level
`/api/ads/diagnostics.action_ids` still includes it for scoped Ads Doctor and
safety context, but section ownership is explicit:
`ads_live_data_status.action_ids=[]`,
`ads_campaign_overview.action_ids=[act_prepare_ads_campaign_review_queue]`,
`ads_search_terms.action_ids=[act_prepare_custom_segments_from_search_terms,
act_prepare_negative_keyword_review_queue]`, and
`ads_keyword_planner.action_ids=[act_configure_google_ads_keyword_planner_access]`.
Command Center Ads decision continues to show only the four real Ads review
queues, not Keyword Planner access repair. Scoped `wilq-ads-doctor`
context-pack is `190224` bytes after this separation.

Latest Content brief preview/review truth, live proof 2026-06-21 10:16 CEST:
`act_prepare_content_refresh_queue` now exposes review-only
`content_brief_preview_v1` inside the ActionObject payload. The payload turns
GSC/WordPress/Ahrefs evidence into brief candidates with source type, topic,
metric snapshot, required validation, evidence IDs, blocked claims,
`apply_allowed=false`, `api_mutation_ready=false` and `destructive=false`.
Runtime proof after `scripts/local_stack.sh restart`:
`/api/actions/act_prepare_content_refresh_queue` returns `preview_count=4`,
topics `beczka`, `denios`, `denios.pl`, `manutan.pl`, and `contains_cuk=false`;
`/api/actions/act_prepare_content_refresh_queue/preview` returns
`status=blocked`, `preview_contract=content_brief_preview_v1`,
`preview_items_total=4`, plus blockers for prepare-only mode, validation,
human confirmation, impact sanity check and blocked marketing claims. Scoped
`wilq-content-strategist` context-pack includes the compacted same preview, and
dashboard `/content-planner` renders `Podgląd briefów do review`. The
dashboard now lets the operator save `Zapisz review briefu` for a specific
candidate through the existing `/api/actions/{action_id}/review` path. The
saved audit preserves non-secret trace IDs such as
`candidate:content_brief_*`, while token-like values are still redacted. This
is not a publish path, not a final article, and not a
ranking/traffic/lead/revenue promise. Remaining content work: use the
strengthened GSC/WP overlap and review-gated draft preview to improve final
brief selection before any real WordPress write adapter exists. Ads scoped context-pack is still kept below
200 KB after trace redaction (`197559` bytes in focused proof). Full
`scripts/verify.sh` passed after this slice: backend `143 passed`, dashboard
unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and dashboard
production build passed.

Latest review-gated WordPress draft preview truth, live proof 2026-06-21
11:07 CEST: after a human review audit selects a content brief candidate with
`candidate:content_brief_*`, `act_prepare_content_refresh_queue` now enriches
its payload with `wordpress_draft_payload_preview_v1`. The draft preview is
derived from the selected `content_brief_preview_v1` candidate and includes
`post_status=draft`, draft title/excerpt direction, content blocks, evidence
IDs, required validation, blocked claims, `mutation_allowed=false`,
`apply_allowed=false`, `api_mutation_ready=false` and `destructive=false`.
Runtime proof with a temporary state DB: before review,
`wordpress_draft_payload_preview` is absent; after
`human_review_approved_for_prepare`, one draft preview appears and
`POST /api/actions/act_prepare_content_refresh_queue/preview` includes it while
the preview status remains `blocked`. Dashboard `/content-planner` renders
`Payload draftu po review` only when the ActionObject contains this review-gated
payload. This is still not a publish path and not a vendor mutation adapter.
Full `scripts/verify.sh` passed after this slice: backend `143 passed`,
dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and
dashboard production build passed.

Latest Ahrefs overlap evidence truth, live proof 2026-06-21 10:44 CEST:
Ahrefs candidate rows in `/api/content/diagnostics` now expose exact overlap
signals instead of only `present/missing`: `gsc_overlap_terms` and
`wordpress_overlap_urls`. Polish text normalization now preserves Polish
matching semantics such as `zielony ład` -> `zielony lad`, so domain relevance
does not disappear because of `ł`. Context-pack redaction preserves these
public overlap fields while still redacting token-like values. Current live
TestClient proof for `review_ahrefs_gap_records`: tiles
`rekordy Ahrefs=32`, `pasujące=5`, `do review=10`, `off-topic=17`,
`GSC overlap=0`, `WP overlap=6`; candidate `beczka` has `gsc_demand=missing`
and four `wordpress_overlap_urls`, so the marketer can see it as a WP/feed
review signal rather than a GSC-backed content brief. Dashboard
`/content-planner` renders `Overlap GSC` and `Overlap WP` rows under Ahrefs
candidates. Full `scripts/verify.sh` passed after this slice: backend
`143 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
skill/API smokes and dashboard production build passed.

Latest Ahrefs content-gap truth, live proof 2026-06-21 05:05 CEST:
`refresh_ahrefs_cb31460610d3` used real read-only Ahrefs API for authority,
organic competitors, competitor top pages, organic keywords by top-page URL,
sample-backed content gap candidates and refdomains-based backlink gap
candidates against the real marketing target `ekologus.pl`. Current live facts:
DR=40, Ahrefs Rank=1541946, `organic_competitor_rows=10`,
`top_pages_by_competitor_rows=4`, `organic_keywords_by_url_rows=4`,
`content_gap_read_status=completed`, `content_gap_rows=4`,
`content_gap_target_keywords=100`, `backlink_gap_read_status=completed`,
`backlink_gap_rows=9`. `/api/ahrefs/diagnostics` now has
`gap_read_contract.status=ready`, `missing_read_contracts=[]`,
`gap_records=24`, `content_records=4`, `backlink_records=9` and all Ahrefs gap
read contracts available: `ahrefs_competitor_pages`,
`ahrefs_top_pages_by_competitor`, `ahrefs_organic_keywords_by_url`,
`ahrefs_content_gap_records` and `ahrefs_backlink_gap_records`. Scoped
`wilq-ahrefs-gap-finder` context-pack is about `100234` bytes and keeps
`active_action_objects=0`. Latest strict eval:
`.local-lab/evals/codex-skill/20260621T030447Z/wilq-ahrefs-gap-finder/result.json`.
Dashboard `/ahrefs` may show reviewable competitor/top-page/organic-keyword,
content-gap and backlink-gap records, but must still block traffic uplift and
authority improvement claims until impact/change-window contracts exist. Full
`scripts/verify.sh` passed after this slice: backend `139 passed`, dashboard
unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and dashboard
production build passed.

Latest Ahrefs -> Content Planner bridge, live proof 2026-06-21 05:50 CEST:
`/api/content/diagnostics.decision_queue` now includes typed decision
`content_decision_ahrefs_gap_records_review` with title
`Ahrefs: zweryfikuj luki SEO przed briefem contentowym`, priority `18`,
source connector `ahrefs`, evidence count `2` and action
`act_prepare_content_refresh_queue`. Current live tiles are
`rekordy Ahrefs=32`, `content gaps=4`, `organic keywords=4`, `top pages=4`,
`backlink gaps=9`. This connects real Ahrefs gap records to the marketer's
Content Planner without dumping raw technical facts. It is still review-only:
operator must reject broad/off-topic records and cross-check with GSC and
WordPress inventory before choosing `refresh`, `merge`, `create` or `block`.
Next Ahrefs product gap after scoring: turn the surviving relevant/review
records into per-topic candidate rows with explicit GSC demand, WordPress
inventory match and business-relevance reasons before any content brief exists.

Latest Ahrefs relevance scoring truth, live proof 2026-06-21 06:07 CEST:
`content_decision_ahrefs_gap_records_review` now scores Ahrefs gap facts before
showing examples in Content Planner. Current live `/api/content/diagnostics`
tiles: `rekordy Ahrefs=32`, `pasujące=5`, `do review=10`, `off-topic=17`,
`GSC overlap=0`, `WP overlap=6`, `content gaps=4`, `backlink gaps=9`.
Displayed example queries are now `beczka, denios`; off-topic insurance/driving
queries such as `prawo jazdy` and `OC` are counted as rejected/off-topic
instead of being shown as content candidates. This is backend scoring logic, not
a prompt workaround. It still does not produce a content brief, ranking promise,
traffic uplift or authority improvement claim; it only narrows what the marketer
should review before cross-checking GSC and WordPress inventory.

Latest Ahrefs candidate-row truth, live proof 2026-06-21 09:05 CEST:
Content Planner no longer exposes Ahrefs gap review only as aggregate counts.
`content_decision_ahrefs_gap_records_review` now carries typed
`ahrefs_candidate_rows` with `topic`, `gap_type`, `relevance_status`,
`relevance_score`, `business_relevance_reasons`, `gsc_demand`,
`wordpress_inventory_match`, evidence IDs and a safe next step per row. Current
live `/api/content/diagnostics` returns 6 candidate rows; first examples are
`beczka`, `denios`, `denios.pl`. `/content-planner` renders these rows as
`Kandydaci Ahrefs do review`, so Ahrefs becomes a review queue for the marketer,
not a loose metric block. This still does not create content briefs by itself
and still blocks ranking, traffic, authority and lead uplift claims. Focused
proof passed: ruff/mypy on changed backend modules, content diagnostics API
test, dashboard typecheck/lint/unit tests and API-backed Playwright
`dashboard-api.spec.ts` (`13 passed`). Full `scripts/verify.sh` passed after
this slice: backend `141 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, skill/API smokes and dashboard production build passed.

Latest Ads custom segment source-quality truth, live proof 2026-06-21 06:27
CEST: custom segment review now exposes typed `source_quality` instead of only
a raw rejected-term list. Current live `/api/ads/diagnostics` candidate
`ads_custom_segment_23848569273` says `accepted_terms=6`,
`rejected_terms=44`, `total_terms=50`, `missing_metric_terms=6` and
`rejection_reasons={"termin nie ma aktywności w dostępnych metrykach": 44}`.
The decision `ads_prepare_custom_segments_from_search_terms` carries the same
quality object inside `custom_segment_candidates`, so dashboard and Codex
context see the same evidence. Missing search-term impressions/cost are still
rendered as `brak danych`, not fake zeroes. Operator gates remain
`review_source_terms`, `reject_brand_or_low_intent_terms`,
`keyword_planner_enrichment`, `forecast_or_audience_size` and
`human_confirm_before_apply`. This is still prepare/review-only. Do not claim
Keyword Planner enrichment, forecast, audience size, targeting applied, CPA,
ROAS or campaign performance from this contract until the corresponding
read/safety/apply contracts exist and are fresh. Full `scripts/verify.sh`
passed after this slice: backend `140 passed`, dashboard unit `17 passed`,
Playwright e2e `14 passed`, skill/API smokes and dashboard production build
passed.

Latest Ads change-history empty-read truth, live proof 2026-06-21 06:48 CEST:
`/api/ads/diagnostics.change_history_read_contract` no longer exposes a
read-attempted-but-empty change history surface as a ready review task. Current
live API has `status=blocked`, title `Google Ads: brak zmian do review`,
`change_history_rows=[]` and missing contracts `change_event_rows`,
`pre_change_performance_window`, `post_change_performance_window`,
`human_change_impact_review`, `apply_preview`. Decision
`ads_review_change_history` is also `blocked` with metric tiles `zmiany=0`,
`kampanie=0` and title `Historia zmian: brak zdarzeń do impact review`. This is
the intended behavior: WILQ can say the read found no change events, but must
not invent change-impact analysis, performance uplift, budget scaling, budget
apply or campaign mutation claims without concrete change_event rows and
pre/post performance windows. Full `scripts/verify.sh` passed after this
slice: backend `141 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, skill/API smokes and dashboard production build passed.

Latest Ads Doctor strict Codex eval truth, live proof 2026-06-21 07:07 CEST:
`wilq-ads-doctor` passes the stricter non-interactive eval against the current
live Ads Doctor surface. Passing artifact:
`.local-lab/evals/codex-skill/20260621T050542Z/wilq-ads-doctor/result.json`.
The eval result has `language=pl-PL`, `api_used=true`, source `google_ads`,
live Ads evidence IDs, top-level `card_google_ads_budget_review_playbook`,
`ads_scaling_candidates_v1`, `ads_recommendations_v1`,
`ads_principles_v1`, and all four Ads prepare/review ActionObject IDs:
`act_prepare_ads_campaign_review_queue`,
`act_prepare_google_ads_recommendation_review_queue`,
`act_prepare_custom_segments_from_search_terms`,
`act_prepare_negative_keyword_review_queue`. The fix was not a prompt/reference
workaround: the WILQ API already exposed the correct action/lineage state. The
skill smoke was aligned with the current empty-read semantics for change
history, and the eval harness now treats structural blocked state as satisfying
blocked-claim discipline without forcing English UI copy into Polish operator
output. Full `scripts/verify.sh` passed after this fix: backend `141 passed`,
dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and
dashboard production build passed.

Latest Demand Gen ad/creative empty-read truth, live proof 2026-06-21 22:53 CEST:
`/api/demand-gen/diagnostics` and scoped
`POST /api/codex/context-pack {"skill":"wilq-demand-gen-operator"}` now expose
the same marketer-facing title, metric tiles, read contracts and review-only
ActionObject.
Current live title is `Demand Gen: brak kampanii do rekomendacji`; current
tiles are `kampanie Ads=18`, `kanały=2`, `wiersze DG=0`, `reklamy DG=0`,
`assety DG=0`, `braki=2`.
Readiness exposes `action_ids=["act_review_demand_gen_readiness"]`,
`demand_gen_readiness_review_action_object` as available and
`demand_gen_readiness_review_preview_v1` in `payload_preview`. Live read-only
Google Ads refresh `refresh_google_ads_dc9e77806e9c` proves that the Demand Gen
ad-level and creative asset-level queries are valid in the current Ads API:
`demand_gen_ad_group_ad_status=ready`, `demand_gen_ad_group_ad_row_count=0`,
`demand_gen_creative_asset_status=ready`,
`demand_gen_creative_asset_row_count=0`. Therefore
`demand_gen_ad_group_ad_rows` and `demand_gen_creative_asset_rows` are available
empty-read contracts. The obsolete `demand_gen_asset_group_rows` contract must
not come back. Remaining missing contracts are now only
`demand_gen_landing_quality_by_campaign` and
`demand_gen_migration_constraints`. The ActionObject is `prepare_only`,
`apply_allowed=false`, `api_mutation_ready=false` and `destructive=false`;
validation passes. This keeps the route useful as a decision/blocker surface
without pretending there is a Demand Gen launch or migration recommendation.
Strict eval passed:
`.local-lab/evals/codex-skill/20260621T205115Z/wilq-demand-gen-operator/result.json`.
Result: `blocked=true`, `language=pl-PL`, `api_used=true`,
`source_connectors=["google_ads","google_analytics_4"]`,
`action_candidates=[act_review_demand_gen_readiness]` and
`operator_usefulness_score=4`. Adjacent GA4/Ads ActionObject IDs must remain
forbidden as active Demand Gen actions. Redaction false-positive fixed:
lowercase contract IDs in Demand Gen summaries stay visible, while token-like
values remain redacted. Final verification passed on 2026-06-21 23:13 CEST:
`scripts/verify.sh` green, including 149 backend tests, 17 dashboard unit tests,
Skill API smoke, 14 Playwright e2e tests and dashboard production build.

Latest Ads business policy truth, live proof 2026-06-21 01:01 CEST:
`AdsBusinessContextReadContract` now exposes typed `business_policy_ids` and
`operator_review_gates`, so local profit margin/business goal/budget goal become
review policy, not only "configured fields". Current live policy IDs are
`use_margin_as_context_not_profitability_verdict`,
`align_campaign_review_to_business_goal`,
`honor_human_budget_goal_before_budget_changes` and
`block_target_verdict_until_roas_or_cpa_confirmed`. Current gates are
`human_strategy_review`, `review_profit_margin_model`, `review_business_goal`,
`review_human_budget_goal` and `confirm_target_roas_or_cpa`. The
`ads_review_business_context` decision now exposes `review gates=5` and
`polityki=4` in metric tiles. Redaction allowlist preserves
`business_policy_ids`; scoped `wilq-ads-doctor` context-pack after
`scripts/local_stack.sh restart` was `189432` bytes and carried unredacted
policy IDs. Narrow checks passed: ruff/mypy, three API contract tests, shared
schema build, dashboard lint/typecheck and `App.test.tsx`. This still does not
unlock profitability, margin verdict, budget scaling/apply, recommendation
apply or wasted-budget claims.

Latest Ads n-gram decision usefulness truth, live proof 2026-06-21 00:45
CEST: `ads_review_search_term_ngrams` no longer loses its metric tiles during
decision lineage normalization. It is priority `42`, directly after raw
search-term review, and exposes non-additive overlapping n-gram tiles:
`n-gramy`, `pokazane`, `z kliknięciami`, `max query/temat`,
`top kliknięcia` and conditional `top koszt`. Live `/api/ads/diagnostics` after
`scripts/local_stack.sh restart` returned `n-gramy=30`, `pokazane=8`,
`z kliknięciami=8`, `max query/temat=12`, `top kliknięcia=2`; blocked claims
still include `search-term waste`, `negative keyword apply`, CPA, ROAS and
conversion loss. Scoped `wilq-ads-doctor` context-pack remained under 200 KB at
`188899` bytes and carries the same decision tiles without heavy n-gram rows.
Narrow checks passed: ruff/mypy, Ads API contract test, dashboard
lint/typecheck and `App.test.tsx`. This is still search-term review only; it
does not create negative keywords or claim waste.

Latest Ads target-aware campaign review truth, live proof 2026-06-21 00:31
CEST: campaign rows, derived KPI rows, Ads campaign review ActionObject and
scoped `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` now carry
target-aware state: `target_status`, `target_status_label` and ActionObject
`target_context`. Current live truth remains honest: business context is ready,
but no human-confirmed target ROAS/CPA is set, so
`/api/ads/diagnostics.business_context_read_contract.missing_read_contracts`
contains `target_roas_or_cpa`, top campaign `(2026) Ekologus Ogólna` is
`target_status=no_target` / `target_status_label=brak targetu`, and campaign
decision metric tiles do not show a noisy `targety=0`. Campaign decision
`operator_review_gates` now carries the union of row gates instead of an empty
list. Process-env proof with `WILQ_ADS_TARGET_ROAS=5.0` marks the same top
campaign `outside_target` / `ROAS poniżej targetu`, adds
`review_target_context` and `review_target_gap_before_budget_decision`, and
shows `targety=18`. Scoped context-pack proof: `189752` bytes and first Ads
campaign candidate includes `target_context`. Narrow checks passed: ruff/mypy,
two Ads API contract tests, shared schema build, dashboard lint/typecheck and
`App.test.tsx`. This is still review-only: budget apply, campaign pause,
wasted-budget claims, CPA/ROAS verdicts and profitability claims remain
blocked.

Latest Ads campaign review ActionObject/context truth, live proof 2026-06-21
00:13 CEST: `/api/ads/diagnostics`,
`/api/actions/act_prepare_ads_campaign_review_queue` and scoped
`POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` now expose the same
campaign triage vocabulary: typed `review_priority`, `review_score`, Polish
`review_reason` and `human_review_gates`. The scoped context-pack keeps a
compact top 3 of 8 `campaign_candidates` instead of an empty list; full payload
remains in `/api/actions/{id}`. Live proof after `scripts/local_stack.sh
restart`: top candidate `(2026) Ekologus Ogólna` is `pilne/90`,
`clicks=94`, `impressions=2763`, `cost_micros=61051723`, `conversions=0.0`,
`candidate_included=3`, `metrics_total=12`,
`budget_payload_preview_included=0`, `apply_allowed=false`, scoped context-pack
`187638` bytes. Redaction preserves `human_review_gates` such as
`review_search_terms_before_budget_decision`, because those are audit/check
identifiers, not secrets. Action validation returns `valid=true`. This is still
read-only campaign review order: budget apply, campaign pause, wasted-budget
claims, CPA/ROAS verdicts and profitability claims remain blocked. Full
`scripts/verify.sh` passed after this slice: backend `136 passed`, dashboard
unit `17 passed`, Playwright e2e `14 passed`, API/skill smokes and dashboard
production build OK.

Latest Ads n-gram truth, live proof 2026-06-20 23:12 CEST:
`/api/ads/diagnostics.search_term_ngram_read_contract` is now typed backend and
shared Zod state. It builds 1/2/3-gram rows from existing Google Ads
`search_term_rows`, exposes source query count, samples, clicks, impressions,
cost, conversions, evidence IDs and blocked claims, and adds decision
`ads_review_search_term_ngrams` plus dashboard Ads Doctor n-gram table. This is
read-only review, not a negative-keyword recommendation. It must continue to
block `search-term waste`, `negative keyword apply`, CPA, ROAS and conversion
loss until human intent review, 90-day safety and payload preview gates are
satisfied. Live proof after `scripts/local_stack.sh restart`: status `ready`,
`ngram_rows=30`, top n-gram `bdo`, section `ads_search_term_ngrams` linked to
`card_google_ads_search_playbook`,
`card_google_ads_negative_keywords_playbook`, `ads_search_terms_v1` and
`ads_negative_keywords_v1`. Narrow checks passed: ruff/mypy,
`pytest -k ads_diagnostics`, shared-schema build, dashboard lint/typecheck and
`App.test.tsx`. Full `scripts/verify.sh` passed after the final context-pack
compaction: backend `136 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, API/skill smokes and dashboard production build OK. Ads doctor
context-pack remains scoped under the 200 KB test limit with full diagnostics
available from `/api/ads/diagnostics`.

Latest Command Center DailyDecision usefulness truth, live proof 2026-06-20
22:40 CEST: `DailyDecision.co_widzimy` no longer carries technical trace
phrases such as `Źródła=`, `dowody=` or `akcje=`. Those identifiers remain in
typed fields and dashboard trace lines, while the primary decision copy now
describes marketer-facing facts: Merchant issue review, GSC/WordPress content
queue, GA4 measurement blocker, Ads read-only review queues and Localo
aggregate visibility review. Live `/api/dashboard/command-center` after
`scripts/local_stack.sh restart` returned `false` for any `co_widzimy`
containing `Źródła=`, `dowody=` or `akcje=`, and GA4 no longer duplicates the
`Status blocked oznacza...` sentence. Narrow checks passed:
`uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py`,
`uv run mypy wilq/briefing/command_center.py`,
`uv run pytest tests/test_api_contracts.py -q -k 'command_center'`,
`pnpm --filter @wilq/dashboard lint`, `pnpm --filter @wilq/dashboard typecheck`
and `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`. Full
`scripts/verify.sh` passed: backend `136 passed`, dashboard unit `17 passed`,
Playwright e2e `14 passed`, API/skill smokes and dashboard production build
OK.

Latest ActionObject mutation audit visibility truth, runtime proof 2026-06-20
22:24 CEST: `ActionObject.review_gate` now carries the latest mutation audit
summary: `last_mutation_audit_id/status/actor/at/summary`,
`last_mutation_attempted`, `last_mutation_adapter`,
`last_mutation_audit_event_id` and `last_mutation_blockers`. Action detail,
daily context-pack and dashboard render the same typed state. Runtime proof on a
temporary state DB: blocked apply on `act_review_merchant_feed_issues` returned
`mutation_status=blocked`, `mutation_attempted=false`; follow-up
`/api/actions/{action_id}` and `POST /api/codex/context-pack
{"skill":"wilq-daily-command"}` both returned
`review_gate.last_mutation_audit_status=blocked` and
`last_mutation_attempted=false`. `scripts/verify.sh` passed for this visibility
follow-up, including API/skill smokes, Playwright e2e and dashboard production
build.

Latest ActionObject mutation audit truth, runtime proof 2026-06-20 21:58 CEST:
WILQ now has typed `ActionMutationAuditRecord`, SQLite persistence for
`action_mutation_audits`, `GET /api/action-mutation-audits`,
`GET /api/actions/{action_id}/mutation-audits` and `ActionApplyResult` carries
`mutation_audit`. `POST /api/actions/{action_id}/apply` now persists both the
local audit event and mutation audit record before returning/raising. The apply
service requires prior dry-run preview, recorded confirmation, completed impact
sanity check, valid ActionObject, configured connector, non-destructive payload,
non-high/critical risk and a supported vendor mutation adapter. Current Goal
001 truth: no vendor mutation adapter is implemented, so even an otherwise
synthetic apply-ready ActionObject returns `applied=false`, `status=blocked`,
`mutation_attempted=false`, `mutation_adapter=null` and blocker
`Vendor mutation adapter is not implemented for this ActionObject.` Redaction
now preserves `audit_event_id`/`audit_event_ids` as traceability identifiers,
not secrets. Full `scripts/verify.sh` after this slice passed: backend
`136 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
dashboard build OK.

Latest ActionObject impact sanity truth, runtime proof 2026-06-20 21:28 CEST:
WILQ now has `POST /api/actions/{action_id}/impact-check`, typed
`ActionImpactCheckRequest/ActionImpactCheckResult`, local audit events
`action_impact_check_blocked` and `action_impact_check_completed`, dashboard
panel `Impact sanity check` and Codex context-pack propagation through
`ActionObject.review_gate.last_impact_check_status/by/at/summary`. Impact check
before confirmation is blocked with `action_confirmation_required`; impact check
after `preview -> confirm` records `action_impact_check_completed`, removes
only `impact_sanity_check_required` and keeps real apply blockers. Runtime
proof on a temporary state DB: impact-before-confirm ->
`action_impact_check_blocked`, preview -> `action_preview_generated`, confirm
-> `action_apply_confirmed`, impact-after-confirm ->
`action_impact_check_completed`, context-pack latest audit event ->
`action_impact_check_completed`, `last_impact_check_status=checked`,
`apply_allowed=false`. This satisfies the local impact-sanity visibility/audit
step only. It does not execute vendor apply and does not prove real mutation
audit paths. Full `scripts/verify.sh` after this slice passed: backend
`135 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
dashboard build OK.

Latest ActionObject confirmation truth, runtime proof 2026-06-20 21:03 CEST:
WILQ now has a separate `POST /api/actions/{action_id}/confirm`, typed
`ActionConfirmRequest/ActionConfirmResult`, local audit events
`action_confirmation_blocked` and `action_apply_confirmed`, dashboard panel
`Jawne potwierdzenie preview` and Codex context-pack propagation through
`ActionObject.review_gate.last_confirmation_by/at/summary`. Confirmation before
dry-run preview is blocked with `dry_run_preview_required`; confirmation after
preview records `action_apply_confirmed`, removes only the satisfied
human-confirm blocker and keeps real apply blockers such as prepare-only mode or
`payload_apply_allowed_false`. Runtime proof on a temporary state DB:
confirm-before-preview -> `action_confirmation_blocked`, preview ->
`action_preview_generated`, confirm-after-preview -> `action_apply_confirmed`,
context-pack latest audit event -> `action_apply_confirmed`,
`last_confirmation_by=operator_runtime_proof`, `apply_allowed=false`. This
satisfies the local `preview -> confirm` visibility/audit step only. It does
not execute vendor apply, does not satisfy impact-sanity checks and does not
prove real mutation audit paths. Full `scripts/verify.sh` after this slice
passed: backend `133 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, dashboard build OK.

Latest ActionObject dry-run preview truth, runtime proof 2026-06-20 20:44 CEST:
WILQ now has `POST /api/actions/{action_id}/preview`, typed
`ActionPreviewRequest/ActionPreviewResult`, local audit event
`action_preview_generated` and dashboard panel `Dry-run preview`. Preview uses
existing ActionObject payload preview rows and returns `dry_run=true`,
`mutation_allowed=false`, `preview_items_total`, `omitted_items`, blockers and
`review_gate`. Daily context-pack includes the compact `latest_audit_event`
for active actions so Codex can see that preview was generated without loading
full audit history. Runtime proof on a temporary state DB: preview endpoint
returned `200`, ActionObject and `wilq-daily-command` context-pack both carried
`latest_audit_event.event_type=action_preview_generated` and
`apply_allowed=false`. This satisfies the local dry-run/preview visibility step
only. It does not execute vendor apply, does not confirm mutation and does not
satisfy remaining impact-sanity or real mutation-audit requirements. Full
`scripts/verify.sh` after this slice passed: backend `131 passed`, dashboard
unit `17 passed`, Playwright e2e `14 passed`, dashboard build OK.

Latest human review outcome truth, runtime proof 2026-06-20 20:28 CEST:
WILQ now has `POST /api/actions/{action_id}/review`, typed
`ActionReviewRequest/ActionReviewResult`, local audit events
`human_review_<outcome>` and `ActionObject.review_gate` fields
`last_review_outcome`, `last_reviewed_by`, `last_reviewed_at`,
`last_review_summary`. Dashboard cards and action detail show `Wynik review
człowieka`; daily context-pack preserves the same state for Codex skills.
Runtime proof on a temporary state DB: event type `human_review_needs_changes`,
ActionObject and `wilq-daily-command` context-pack both carried
`last_review_outcome=needs_changes`, `apply_allowed=false`, with no
`[REDACTED]`. This is local audit/review state only. It does not execute apply,
does not mutate vendors and does not satisfy remaining apply confirmation,
mutation audit or impact-sanity requirements. Full `scripts/verify.sh` after
this slice passed: backend `129 passed`, dashboard unit `17 passed`,
Playwright e2e `14 passed`, dashboard build OK.

Latest ActionObject review gate truth, live proof 2026-06-20 20:04 CEST:
`ActionObject.review_gate` is now a typed API/shared-schema/dashboard/Codex
context-pack contract. It exposes `required_checks`, `operator_checklist`,
`apply_blockers`, `confirmation_required` and `apply_allowed` for review-only
actions. Current live `/api/actions` and `POST /api/codex/context-pack
{"skill":"wilq-daily-command"}` show Merchant, content and Ads ActionObjects
with `status=pending_validation`, `apply_allowed=false`,
`confirmation_required=true` and explicit apply blockers. Redaction preserves
review-gate IDs; no `[REDACTED]` review checklist values should appear in
context-pack output. Scoped skill context-pack action metrics are compacted to
one exemplar row plus `metrics_total`, because detailed Ads facts live in the
typed diagnostics contracts and `wilq-ads-doctor` must stay under the 200 KB
budget. This is a visibility/safety contract only. It does not permit
write/apply mutations and does not satisfy the remaining apply confirmation or
audit-path requirements. Full `scripts/verify.sh` after this slice passed:
backend `127 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
dashboard build OK.

Latest Ads Keyword Planner truth, live proof 2026-06-20 19:30 CEST:
WILQ now has a conservative read-only Keyword Planner adapter using
Google Ads `generateKeywordIdeas`, typed `keyword_planner_read_contract`,
shared frontend schema, dashboard enrichment for custom segments and an Ads
Doctor smoke/eval guard. Current live `vendor_read`
`refresh_google_ads_0477a745f098` completed and collected normal Ads evidence,
but Keyword Planner returned `403 PERMISSION_DENIED` with
`authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`. Treat this as a Google Ads
developer-token approval/readiness blocker, not as missing `.env`, broken
OAuth or missing MCC/child customer setup. Current
`/api/ads/diagnostics.keyword_planner_read_contract.status=blocked`,
`missing_read_contracts=[keyword_planner_enrichment]`, `idea_rows=[]`; custom
segments remain review-only with
`missing_read_contracts=[keyword_planner_enrichment, forecast_or_audience_size]`.
Do not fabricate Keyword Planner ideas, audience size, forecast, targeting
applied, campaign performance, ROAS or conversion uplift. Latest strict eval:
`.local-lab/evals/codex-skill/20260620T173651Z/wilq-ads-doctor/result.json`.

Latest Ads business context truth, live proof 2026-06-20 17:34 CEST:
repo-local `.env` may contain non-secret Ads context such as profit margin,
Polish business goal and Polish budget goal, but `WILQ_ADS_TARGET_ROAS` and
`WILQ_ADS_TARGET_CPA_MICROS` are intentionally empty until a human confirms the
target. Do not preserve guessed CPA/ROAS targets as product truth. With empty
target values and the core non-secret context present, current
`/api/ads/diagnostics.business_context_read_contract` shows `status=ready`,
`missing_read_contracts=[target_roas_or_cpa]`, `target_roas=null`,
`target_cpa_micros=null` and `allowed_metrics=[profit_margin, business_goal,
human_budget_goal]`. The `ads_review_business_context` decision is also ready
with `braki=1`, `ustawione pola=3` and no
`act_configure_ads_business_context`; Command Center therefore keeps a single
ready Ads review card instead of a false business-context blocker. This still
does not unlock target verdicts, budget apply, recommendation apply,
wasted-budget verdicts, profitability verdicts or scaling recommendations;
those require confirmed targets plus the remaining optimizer contracts, human
review and audit paths.

Latest custom-segments context truth, live proof 2026-06-20 17:34 CEST:
`POST /api/codex/context-pack {"skill":"wilq-custom-segments"}` is now
workflow-specific: about 50 KB, `active_action_objects` and
`ads_diagnostics.action_ids` contain only
`act_prepare_custom_segments_from_search_terms`, `decision_queue` contains only
`ads_prepare_custom_segments_from_search_terms`, and `top_opportunities=[]`.
The dedicated `/ads-doctor/custom-segments` route renders the same review-only
contract, including real source terms, payload preview, missing
`keyword_planner_enrichment` and `forecast_or_audience_size`, and blocked
audience/apply/performance claims. Do not re-expand this skill context with
generic Ads decisions or opportunity cards.
Latest custom-segments triage follow-up, 2026-06-20 18:24 CEST:
`/api/ads/diagnostics.custom_segments_read_contract.candidates` now carries
typed `review_priority`, bounded `review_score`, Polish `review_reason` and
`human_review_gates`. Live proof after `scripts/local_stack.sh restart`: one
candidate, `Search terms: Kompendium PPWR`, with `review_priority=pilne`,
`review_score=75`, 6 source terms and blocked claims for audience size, ROAS,
targeting/apply and campaign performance. Decision
`ads_prepare_custom_segments_from_search_terms.metric_tiles` shows
`segmenty=1`, `pilne=1`, `wysokie=0`, `podgląd akcji=1`,
`źródłowe zapytania=6`. Scoped `wilq-custom-segments` context-pack is about
51 KB and keeps only `act_prepare_custom_segments_from_search_terms`,
`ads_prepare_custom_segments_from_search_terms`, the custom segment candidate
and no top opportunities. Strict eval now requires the review fields:
`.local-lab/evals/codex-skill/20260620T162316Z/wilq-custom-segments/result.json`
has `api_used=true`, `language=pl-PL`,
`act_prepare_custom_segments_from_search_terms` validated,
`operator_usefulness_score=5` and notes that audience size, ROAS, targeting
and campaign performance remain blocked. Full `scripts/verify.sh` passed after
this slice: backend `126 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, dashboard production build OK.

Latest Ads recommendation triage follow-up, 2026-06-20 18:48 CEST:
`/api/ads/diagnostics.recommendations_read_contract.recommendation_rows` now
carries typed `review_priority`, bounded `review_score`, Polish
`review_reason` and `human_review_gates`. Live proof after
`scripts/local_stack.sh restart`: 4 recommendation rows, `missing_read_contracts=[]`,
`act_prepare_google_ads_recommendation_review_queue` present, and decision
`ads_review_recommendations.metric_tiles` shows `rekomendacje=4`, `pilne=0`,
`wysokie=2`, `podgląd wpływu=2`, `podgląd akcji=4`. Row priorities:
`DISPLAY_EXPANSION_OPT_IN=normalne/23`,
`DYNAMIC_IMAGE_EXTENSION_OPT_IN=niski sygnał/10`,
`IMPROVE_PERFORMANCE_MAX_AD_STRENGTH=wysokie/57`,
`SEARCH_PARTNERS_OPT_IN=wysokie/53`. `/ads-doctor` renders the same priority,
score, reason and human review gates. Smoke script and strict Codex eval now
require these fields; latest eval artifact:
`.local-lab/evals/codex-skill/20260620T164726Z/wilq-ads-doctor/result.json`
with `api_used=true`, `language=pl-PL`, `operator_usefulness_score=5`. This is
still review-only; recommendation apply, automatic accepts, budget apply,
campaign mutation and performance uplift remain blocked.

Command Center is being held to the Polish marketer cockpit bar: stable API
fields such as `evidence_ids` remain unchanged, but marketer-facing labels must
say `Dowody`, `Przykładowe dowody`, `podgląd akcji`, `odczyt` and similar
Polish terms instead of raw English implementation wording. GA4 on Command
Center must use the same `Ga4DiagnosticsResponse.decision_queue` semantics as
`/ga4`, showing concrete review counts for `grupy ruchu`, `decyzje`, `pomiar`
and `jakość ruchu` while still blocking ROAS/revenue/conversion/tracking-fixed
claims until explicit contracts exist.

GA4 dedicated route and `wilq-ga4-analyst` context-pack must expose decision
metadata directly, not rely on frontend inference. Current live proof after
`scripts/local_stack.sh restart`: `/api/ga4/diagnostics.decision_queue` has
6 decisions with explicit `status`, `priority` and `metric_tiles`; 2 decisions
are `blocked` measurement issues for `(not set)` rows and 4 are `ready`
traffic-quality reviews. Metric tiles include `aktywni`, `sesje`, `zdarzenia`,
`odsłony` and `engagement`, e.g. `(not set)/(not set)` has `aktywni=179`,
`sesje=179`, `engagement=0%`; scoped `wilq-ga4-analyst` context-pack carries
the same fields with no GA4 redaction paths and no null
`status`/`priority`/`metric_tiles`. Full `scripts/verify.sh` passed after this
slice: backend `117 passed`, dashboard unit `14 passed`, Playwright e2e
`9 passed`, security, skill/API smokes and dashboard production build passed.

Ahrefs dedicated route and `wilq-ahrefs-gap-finder` context-pack must expose
authority evidence separately from true gap evidence. Current live proof after
the 2026-06-21 top-pages slice: `/api/ahrefs/diagnostics` has
`live_data_available=true`, `authority_fact_count=2`, `gap_fact_count=24`,
`blocker_count=1`, authority facts `DR=40`, `Ahrefs Rank=1541946`,
`organic_competitor_rows=10`, and `top_pages_by_competitor_rows=4` from
2 competitors. The target is the real marketing target `ekologus.pl`, not
staging `ekologus.dev.proudsite.pl`; priority is `AHREFS_TARGET`, then
`MIS_PRIMARY_SITE_URL`, then `WORDPRESS_EKOLOGUS_URL`. Ready decision
`ahrefs_review_gap_records` now exposes 14 records: 10 competitor-page records
through `ahrefs_competitor_pages` and 4 competitor top-page records through
`ahrefs_top_pages_by_competitor`. Blocked decision
`ahrefs_block_gap_claims_without_records` still blocks missing read contracts:
`ahrefs_content_gap_records`, `ahrefs_backlink_gap_records`,
`ahrefs_organic_keywords_by_url`. Scoped
`POST /api/codex/context-pack {"skill":"wilq-ahrefs-gap-finder"}` is about
`68651 bytes`, includes `ahrefs_diagnostics`, omits broad unrelated context,
and has `active_action_objects=0`. Diagnostics also ignore orphan/test DuckDB
facts not attached to known refresh-run evidence IDs. Do not claim
content/backlink/ranking/traffic/authority gaps from DR/rank, competitor-page
or top-page records alone. Strict non-interactive eval now enforces this: case
`wilq-ahrefs-gap-finder` targets `/ahrefs`, requires `blocked=true`, no unsafe
action IDs, read-contract gaps and blocked claim terms. Latest eval artifact:
`.local-lab/evals/codex-skill/20260621T020523Z/wilq-ahrefs-gap-finder/result.json`;
result has `api_used=true`, `blocked=true`, Ahrefs evidence IDs and
`operator_usefulness_score=4`. Full `scripts/verify.sh` passed after this
slice: backend `139 passed`, dashboard unit `17 passed`, Playwright e2e
`14 passed`, skill/API smokes and dashboard production build passed.

Ads dedicated route and `wilq-ads-doctor` context-pack must expose decision
metadata directly, not rely on frontend inference. Current live proof after
`scripts/local_stack.sh restart`: `/api/ads/diagnostics.decision_queue` has
11 decisions with explicit `priority` and `metric_tiles`; `null_priority_count`
is `0` and `empty_tiles=[]`. Campaign review shows `kampanie=18`,
`kliknięcia=117`, `wyświetlenia=3075`, `koszt=161`, `konwersje=2`;
recommendations show `rekomendacje=4`, `podgląd wpływu=2`,
`podgląd akcji=4`; search terms show supported evidence-backed tiles
`zapytania=50`, `kliknięcia=7` and `koszt=41.8` when current evidence contains
`cost_micros`. Scoped `wilq-ads-doctor` context-pack carries the same fields
with no Ads redaction paths.

Ads recommendation review must separate missing read contracts from operator
review gates. Current live proof after `scripts/local_stack.sh restart`:
`/api/ads/diagnostics.recommendations_read_contract.missing_read_contracts=[]`
and the same decision in `decision_queue` has `operator_review_gates`:
`human_strategy_review`, `review_recommendation_type`, `review_impact_metrics`,
`review_change_history`, `review_business_goal`, `recommendation_apply_preview`,
`google_ads_rmf_compliance_review`, `human_confirm_before_apply`. Scoped
`wilq-ads-doctor` context-pack preserves these gates without `[REDACTED]`.
This does not unlock apply; it makes the human review gate explicit and
traceable.

Ads search-term and negative keyword review must apply the same rule:
human/operator validation gates are not missing read contracts. Current live
proof after `scripts/local_stack.sh restart` on 2026-06-20 15:52 CEST:
`/api/ads/diagnostics.search_terms_read_contract.missing_read_contracts=[]`
and `operator_review_gates=["negative_keyword_action_validation"]`; decision
`ads_review_search_terms` has the same gate and no missing read contracts.

Ads custom segment review must follow the same separation. Current live proof
after `scripts/local_stack.sh restart` on 2026-06-20 16:15 CEST:
`/api/ads/diagnostics.custom_segments_read_contract.status=ready`,
`missing_read_contracts=["keyword_planner_enrichment",
"forecast_or_audience_size"]` and
`operator_review_gates=["review_source_terms",
"reject_brand_or_low_intent_terms", "human_confirm_before_apply"]`; decision
`ads_prepare_custom_segments_from_search_terms` has the same separation with
`metric_tiles.segmenty=1`, `metric_tiles.źródłowe zapytania=6` and
`action_ids=["act_prepare_custom_segments_from_search_terms"]`. This remains
review-only source-term preparation; it does not unlock audience size,
conversion uplift, ROAS, targeting apply or campaign performance claims.
`search_term_safety_read_contract.missing_read_contracts=[]`,
`keyword_match_context_read_contract.missing_read_contracts=[]`, and the safety
decisions carry `operator_review_gates=["human_intent_review"]`. This still
does not unlock negative keyword apply; it only prevents the dashboard and
skills from mislabeling validation/human review as missing data. Full
`scripts/verify.sh` passed after the earlier safety slice:
backend `119 passed`, dashboard unit `14 passed`, Playwright e2e `11 passed`,
skill/API smokes, security checks and dashboard production build passed.
Latest negative keyword triage follow-up, 2026-06-20 18:03 CEST:
`/api/ads/diagnostics.negative_keywords_read_contract.candidates` now carries
typed `review_priority`, bounded `review_score`, Polish `review_reason` and
`human_review_gates`. Live proof after `scripts/local_stack.sh restart`: 6
candidates, top candidate
`asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a`
has `review_priority=pilne`, `review_score=84`; decision
`ads_review_negative_keyword_safety.metric_tiles` shows `kandydaci=6`,
`pilne=1`, `wysokie=1`, `podgląd akcji=6`, `kontekst słów=12`. The reason text
must keep saying that this is review ordering, not a wasted-budget verdict.
Dashboard `/ads-doctor` renders the same fields. This does not unlock negative
keyword apply, wasted-budget claims, CPA/ROAS verdicts or automatic exclusions.
Full `scripts/verify.sh` passed after this slice: backend `126 passed`,
dashboard unit `17 passed`, Playwright e2e `14 passed`, dashboard production
build OK.

Campaign-builder context-pack must stay workflow-specific. It must not pull
negative keyword or custom-segment ActionObjects unless the selected workflow
explicitly needs them. Current focused proof after the Ads review-gate slice:
`wilq-campaign-builder` context-pack is `191737 bytes` in a fresh API process
and `active_action_objects` contains only `act_prepare_ads_campaign_review_queue`
and `act_prepare_google_ads_recommendation_review_queue`. This keeps the
non-daily skill payload under the 200 KB budget and prevents Codex from mixing
campaign-building with separate negative/custom-segment workflows.

`wilq-ads-doctor` scoped context-pack must stay under the non-daily skill budget
without losing Ads decision state. Current live proof after
`scripts/local_stack.sh restart`: `POST /api/codex/context-pack` for
`wilq-ads-doctor` is `174292 bytes` over the wire, smoke-reported
`context_pack_bytes=183152`, keeps 11 Ads decisions, omits duplicate `sections`
and row payloads inside `decision_queue`, caps budget payload preview rows to 4,
keeps source evidence/action IDs, and preserves the full endpoint pointer:
`/api/ads/diagnostics`.

Demand Gen must stay honest until WILQ has Demand Gen-specific evidence and
ActionObjects. It must not present GA4 tracking review, negative keyword review
or custom segment review as Demand Gen actions. Current live proof after
`scripts/local_stack.sh restart`: dedicated endpoint
`GET /api/demand-gen/diagnostics`, dashboard route `/ads-doctor/demand-gen`
and scoped `wilq-demand-gen-operator` context-pack all expose the same blocked
readiness contract: `active_action_objects=[act_review_demand_gen_readiness]`,
`ads_diagnostics.action_ids=[]`,
`demand_gen_readiness.action_ids=[act_review_demand_gen_readiness]`,
`demand_gen_readiness.status=blocked`, `campaign_rows_evaluated=18`,
`campaign_channel_counts={PERFORMANCE_MAX: 8, SEARCH: 10}`,
`demand_gen_campaign_rows=[]`, `demand_gen_ad_group_ad_rows=[]` and
`demand_gen_creative_asset_rows=[]`. `/ads-doctor/demand-gen` must not fall
back to generic registry sections such as `Evidence Registry` or
`Connector Refresh Runs`.
`demand_gen_campaign_rows` is now an available read contract when campaign
channel facts exist; it must not be listed as missing in that state. The
ad-level and creative asset empty-read contracts are also available after live
Google Ads proof `refresh_google_ads_dc9e77806e9c`: both queries are `ready`
with row count `0`. Remaining missing read contracts are only
`demand_gen_landing_quality_by_campaign` and
`demand_gen_migration_constraints`, while
`demand_gen_readiness_review_action_object` is available. These IDs must not be
redacted; they are product contracts, not secrets. The
`wilq-demand-gen-operator` smoke script must fail if adjacent ActionObjects are
again exposed as active Demand Gen actions, if its review-only payload preview
is missing, if obsolete `demand_gen_asset_group_rows` returns, or if
channel/ad/creative read contracts are neither available nor honestly missing.
Live seeded/API tests and the live smoke prove the available empty-read state;
full verify can run on a temporary DB where these contracts remain honest
missing contracts. Focused route proof passed: API contract tests for Demand
Gen, dashboard unit route test, live skill smoke and non-interactive eval at
`.local-lab/evals/codex-skill/20260621T205115Z/wilq-demand-gen-operator/result.json`.

Content on Command Center must use the same
`ContentDiagnosticsResponse.decision_queue` semantics as `/content-planner` and
`wilq-content-strategist`. Do not rebuild content first-screen copy from raw
tactical items. Current live proof after `scripts/local_stack.sh restart`:
`/api/content/diagnostics.decision_queue` has 4 decisions with
`null_status=[]`, `null_priority=[]`, `empty_tiles=[]`. Top decision:
`SEO: odśwież lub scal "zielony ład co to" (7 zapytań)` with `status=ready`,
`priority=15`, `zapytania=7`, `WP=znaleziono`, `wyświetlenia=2902`,
`kliknięcia=123`, `CTR=4.24%`, `pozycja=1.5`. Scoped
`wilq-content-strategist` context-pack preserves those typed fields. Command
Center `daily_content_queue` consumes the same state and shows `query/page=10`,
`WP match=10`, `decyzje=4`, `wyświetlenia=7852`, `kliknięcia=138`, with no
`[REDACTED]` in content decision prose. Evidence IDs and ActionObject IDs must
stay in structured fields, not inside prose where redaction can mask useful
marketer context.

Merchant on Command Center must use the same
`MerchantDiagnosticsResponse.decision_queue` semantics as `/merchant` and
`wilq-merchant-feed-operator`. Do not rebuild Merchant first-screen copy from
raw metric facts. Current live proof after `scripts/local_stack.sh restart`:
`/api/merchant/diagnostics` shows `product_count=10900`, `issue_count=15`,
`issue_clusters=11`, `decision_count=8`; the top decision is
"Merchant: sprawdź brak potencjalnie wymaganego atrybutu / miara ceny
jednostkowej", `issue_count=892`,
`ev_refresh_refresh_google_merchant_center_a3ef2f66703f` and
`act_review_merchant_feed_issues`. Scoped `wilq-merchant-feed-operator`
context-pack carries the same decision with no redaction under
`merchant_diagnostics.decision_queue`. Command Center shows
`produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`, `decyzje=8`,
`blockery=0` and Polish marketer-facing labels. Latest follow-up: every
Merchant decision now exposes typed `priority` and numeric `metric_tiles`, so
`/merchant`, Command Center and `wilq-merchant-feed-operator` can rank the same
issue-level queue without frontend inference. Live proof after restart:
8 Merchant decisions, `null_priority=[]`, `empty_tiles=[]`, top decision
`priority=21`, `metric_tiles.zgłoszenia=892`.

Marketing Brief and Codex context-packs must use the same daily decision state
as Command Center. Do not rebuild `/api/marketing/brief` from stale raw metric
summaries when `CommandCenterResponse.daily_decisions` already contains typed
Merchant, Content, GA4 and Ads decisions. Current live proof after
`scripts/local_stack.sh restart`: `/api/marketing/brief.what_we_know` shows
`Przejrzyj kolejkę problemów Merchant Center`, `Przejrzyj kolejkę SEO z GSC i
WordPress`, `GA4: pomiar i jakość ruchu do kontroli`,
`Przejrzyj kolejki Ads do oceny bez apply` and `Ahrefs: domain_rating = 90`;
`what_blocks_us` contains the GA4 contract blocker; `recommended_focus` mirrors
ready daily decisions; scoped `wilq-daily-command` context-pack has the same
brief and Command Center decision titles with no `marketing_brief` redaction
paths. Stale strings such as `feed/product issues`, `active_products=12`,
`disapproved_products=3`, `active_users=20`, `sessions=30` and
`feed issue queue` must not return to the daily brief. Full `scripts/verify.sh`
passed after this slice: backend `117 passed`, dashboard unit `14 passed`,
Playwright e2e `9 passed`, security, skill/API smokes and dashboard production
build passed.

Latest daily context-pack follow-up, 2026-06-20 14:30 CEST:
`active_action_objects` in scoped `wilq-daily-command` context now inherit
`decision_id`, `decision_status`, `metric_tiles`, evidence IDs, blocked claims
and safe next step from `CommandCenterResponse.daily_decisions`. Redaction
preserves `decision_id`. Live proof after `scripts/local_stack.sh restart`:
Merchant action points to `decision_review_merchant_feed_issues` with
`produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`; GA4 action points to
`decision_review_ga4_landing_quality` with status `blocked`, `grupy ruchu=10`,
`pomiar=2`, `jakość ruchu=4`. Stale strings
`active_products=12`, `disapproved_products=3`, `active_users=20`,
`sessions=30`, `Connector .* ready`, `No performance metrics` and
`Run a read-only refresh` are absent from the live daily context-pack.

Latest Localo routing follow-up, 2026-06-20 14:30 CEST: Localo with real
aggregate facts is now `daily_localo_visibility_facts` and maps to
`plan_review_localo_visibility_facts`. Readiness/access-only Localo remains
`daily_localo_readiness` and must not be promoted as a ready primary operator
item. Current live Localo tiles: `miejsca=4`, `frazy=23`,
`widoczność=52.8261`, `recenzje=793`. `wilq-daily-command` smoke passed after
this change. Full `scripts/verify.sh` passed after this slice: backend
`124 passed`, dashboard unit `15 passed`, Playwright e2e `12 passed`,
dashboard production build OK.
Localo diagnostics and Command Center must select these facts by evidence ID
from the last successful Localo MCP aggregate read, not by a small newest-facts
limit, because later access probes can otherwise hide `localo_tracked_keyword_count`
and regress `frazy` to `0`. Live proof after `scripts/local_stack.sh restart`
on 2026-06-20 16:35 CEST: `/api/localo/diagnostics` uses
`refresh_localo_9e9ff67eadad`, reports `visibility_fact_count=17`,
`metric_tiles.frazy=23`, and Command Center
`decision_review_localo_visibility_facts.metric_tiles.frazy=23` with
`daily_localo_readiness` absent from the primary brief.

Opportunities must be decision-backed, not connector-registry-backed, when
daily decisions exist. `/api/opportunities`, `/opportunities` and full Codex
context-pack `top_opportunities` must show the same marketer decisions as
Command Center: Merchant feed review, Content refresh queue, GA4
measurement/traffic review and Ads review queue. Current live proof after
`scripts/local_stack.sh restart`: `/api/opportunities` returns 4 IDs:
`opp_decision_review_merchant_feed_issues`,
`opp_decision_prepare_content_refresh_queue`,
`opp_decision_review_ga4_landing_quality` and
`opp_decision_review_ads_campaign_metrics`; each carries `metric_tiles`,
evidence IDs, source connectors, ActionObject IDs and a Polish safe next step.
No `opp_connector_*` cards or `opportunities` redaction paths are present in
the live context-pack proof. Connector registry cards may remain as fallback
only when there are no daily decisions. Full `scripts/verify.sh` passed after
this slice: backend `117 passed`, dashboard unit `14 passed`, Playwright e2e
`9 passed`, security, skill/API smokes and dashboard production build passed.

Workflows must be operator contracts, not placeholder automation names. When
daily decisions exist, `/api/workflows` and `/workflows` must show core
workflow cards with `status`, `route`, `skill_id`, `metric_tiles`, source
connectors, evidence IDs, ActionObject IDs, blocked claims and a safe next
step. Planned workflows must explicitly list missing contracts and must not
imply automation or apply support. Current live proof after
`scripts/local_stack.sh restart`: `/api/workflows` returns 15 workflows:
4 `ready`, 4 `blocked`, 7 `planned`. Core workflows include `daily_command`,
`merchant_feed_review`, `gsc_content_doctor`, `ga4_data_analyst` and
`ads_daily_check`; `daily_command` has `decyzje=4`, `blockery=1`, `źródła=6`,
`akcje=7`; `ads_daily_check` has Ads review tiles and four review-only
ActionObjects. Old placeholder strings `Workflow definition runs against WILQ
API` and `Fetch WILQ API context` are absent. Full `scripts/verify.sh` passed
after this slice: backend `118 passed`, dashboard unit `14 passed`,
Playwright e2e `10 passed`, security, skill/API smokes and dashboard
production build passed.

Knowledge must connect source material to marketer decisions, not only list
cards and YAML playbooks. `/api/knowledge/operating-map` and `/knowledge` must
show how canonical knowledge cards, machine-readable playbooks and expert rules
bind to routes, skills, evidence IDs, ActionObject IDs, blocked claims and
missing contracts. Current live proof after `scripts/local_stack.sh restart`:
`/api/knowledge/operating-map` returns 11 bindings, 15 source cards, 14
playbooks and 31 expert rules. Core bindings include `knowledge_daily_command`,
`knowledge_merchant_feed_review`, `knowledge_gsc_content_doctor`,
`knowledge_ads_daily_check`, `knowledge_ga4_data_analyst` and
`knowledge_localo_visibility_review`; Ads binds
`card_google_ads_search_playbook`, `google_ads_search_playbook`,
`ads_search_terms_v1` and four review-only ActionObjects to `/ads-doctor` and
`wilq-ads-doctor`, while Localo stays blocked on `local_ranking_rows`,
`gbp_performance_rows` and `review_rows`.

## Research And Knowledge Contract

WILQ must be built from a source-backed marketing knowledge loop, not from loose
prompt intuition. The canonical source map is:

```txt
docs/research/wilq-marketing-source-map.md
```

Every serious Ads, SEO, Merchant, GA4, Ahrefs, Localo, WordPress or social
slice must follow this path:

1. Pick sources from the source map or add better current sources first.
2. Condense the source into a knowledge card, expert rule, schema contract or
   skill reference.
3. Bind the rule to required WILQ evidence fields and blocked claims.
4. Expose the result through the WILQ API before dashboard or skill polish.
5. Prove with dashboard/browser checks and `codex exec` that Polish prompts
   produce evidence-backed Polish outputs.

Research methods to preserve:

- ReAct-style loop: reason about the marketer task, call WILQ API/tooling, then
  answer from observed evidence.
- Self-RAG-style critique: retrieve only relevant evidence, check whether it is
  sufficient, then block unsupported recommendations.
- RAGAS/RAG-eval-style gates: context relevance, faithfulness to evidence,
  answer usefulness and no hallucinated metrics.
- Official platform docs first for APIs and constraints; practitioner sources
  only after the official contract is understood.
- BDOS-class product bar: diagnostics, safe actions, dry-run/preview/confirm,
  mutation/audit history, expert knowledge and multi-surface operation.

## Current Runtime Truth

Local dashboard:

```bash
http://127.0.0.1:5173/command-center
```

Local API:

```bash
http://127.0.0.1:8000/api/health
```

Current performance truth:

- `WILQ_DAILY_RUNTIME_CACHE_SECONDS` now defaults to `30`, while tests still
  disable runtime cache and connector refresh/action validation/action apply
  paths clear the cache.
- Dashboard TanStack Query now treats WILQ server state as a short operator
  snapshot: `staleTime=30000` and `refetchOnWindowFocus=false` by default.
- Live proof after local stack restart on 2026-06-20:
  `/api/dashboard/command-center` `27856 bytes`, cold `1.777s`, then `0.007s`,
  `0.009s`, `0.010s`, `0.007s` within the operator cache window. Daily Codex
  context-pack was `126449 bytes`, `0.382s`, then `0.237s`, `0.234s`.

Use `uv run ...` for Python/WILQ commands. Do not use global `python`.

Current connector truth:

- Connector summary live check 2026-06-19 14:53 Europe/Warsaw:
  `total=12`, `configured=9`, `missing_credentials=2`, `disabled=1`.
  The disabled connector is `google_sheets`, intentionally outside current
  Ekologus scope. The missing connectors are `linkedin` and `facebook`;
  they block publishing only, not evidence-backed drafting.
- `google_ads`: credentials are configured and live campaign-level
  `vendor_read` works after the 2026-06-18 OAuth + MCC/child-account fix.
  `596-895-8639 Agencja Proud Media` is the MCC/login customer. `Ekologus NOWY`
  is the child metrics customer. Do not call Ads an OAuth blocker unless a fresh
  read proves that. Google Ads now has live campaign rows, search-term rows,
  account currency evidence, a derived KPI read contract for
  CTR/CPC/conversion rate/CPA/ROAS, a
  read-only budget context contract, a read-only recommendations contract, a
  read-only impression-share contract, a read-only change-history contract, a
  read-only 90-day search-term safety contract, a prepare-only custom segment
  candidate contract with review-only payload preview and a prepare-only
  negative keyword safety review contract with review-only payload preview plus
  read-only keyword match context. Recommendations now also have a review-only
  apply payload preview ActionObject. Campaign budgets now also have
  review-only `CampaignBudgetOperation` payload previews exposed through
  `/api/ads/diagnostics`, `/api/actions/act_prepare_ads_campaign_review_queue`
  and dashboard `/ads-doctor`; every preview keeps `api_mutation_ready=false`,
  `apply_allowed=false` and `destructive=false`.
  Command Center now consumes those Ads diagnostics as a marketer decision,
  not as generic connector readiness. Live `/api/dashboard/command-center`
  proof after local stack restart: `daily_ads_status` title
  `Ads: kolejki budżetu, rekomendacji i zapytań`, status `ready`,
  priority `16`, metric tiles `kampanie=18`, `zapytania=50`,
  `podgląd budżetu=18`, `rekomendacje=4`, `wykluczenia=6`, `segmenty=1`,
  and ActionObjects `act_prepare_ads_campaign_review_queue`,
  `act_prepare_google_ads_recommendation_review_queue`,
  `act_prepare_custom_segments_from_search_terms` and
  `act_prepare_negative_keyword_review_queue`. The `wilq-daily-command`
  scoped context-pack carries the same Ads action-plan prompt.
  Command Center keeps API `blocked_claims` stable, but the dashboard now
  translates marketer-facing blocked claims in general decision/tactical/brief
  cards. Do not regress to visible raw labels such as `approval restored`,
  `lead uplift`, `profitability`, `wasted budget` or `search-term waste` on
  first-screen marketer surfaces.
  Latest live Ads proof: `refresh_google_ads_60956db2c42f` /
  `ev_refresh_refresh_google_ads_60956db2c42f` exposes
  `customer_currency_code=PLN`, 18 campaign rows, 50 30-day search-term rows,
  200 90-day search-term safety rows, 211 keyword match context rows, 4 active
  Google Ads recommendation rows, 2 recommendation rows with impact preview,
  4 recommendation apply payload preview rows, 18 campaign budget apply preview
  rows, 2 impression-share rows and
  `change_event_row_count=0` for the last 14 days.
  `/api/ads/diagnostics` reports
  `account_currency_read_contract.status=ready`,
  `account_currency_read_contract.currency_code=PLN`,
  `impression_share_read_contract.status=ready`,
  `change_history_read_contract.status=ready`,
  `recommendations_read_contract.status=ready`,
  `recommendations_read_contract.action_ids=["act_prepare_google_ads_recommendation_review_queue"]`,
  `recommendations_read_contract.missing_read_contracts=[]`,
  `recommendations_read_contract.operator_review_gates` includes
  `human_strategy_review` and `google_ads_rmf_compliance_review`,
  `search_term_safety_read_contract.status=ready`,
  `keyword_match_context_read_contract.status=ready`, decisions
  `ads_review_impression_share`, `ads_review_change_history` and
  `ads_review_search_term_safety`. CPA/ROAS are allowed only as calculations
  from campaign facts; budget context, recommendations, impression share,
  change history, 90-day search-term safety and keyword match context are
  allowed only as review/audit context. Dashboard `/ads-doctor` may format
  cost, CPC, CPA, budget and search-term costs in PLN, but profitability and
  margin verdicts remain blocked. Current `negative_keywords_read_contract`
  has 7 review-only
  candidates, 7 `negative_keyword_payload_preview` rows, no
  `90_day_safety_check` missing contract and no
  `negative_keyword_payload_preview` missing contract and no
  `keyword match context` missing contract. Negative keyword preview rows are
  exact-match review rows with `api_mutation_ready=false`,
  `apply_allowed=false` and `destructive=false`. Recommendation apply preview
  rows use `operation_type=ApplyRecommendationOperation`, but also keep
  `api_mutation_ready=false`, `apply_allowed=false` and `destructive=false`.
  Budget apply preview rows use `operation_type=CampaignBudgetOperation`, but
  also keep `api_mutation_ready=false`, `apply_allowed=false` and
  `destructive=false`.
  WILQ still blocks `negative keyword apply`, `recommendation apply`,
  `search-term waste`, CPA, ROAS and conversion-loss claims until human review,
  confirmation and future apply/audit contracts exist. Budget preview does not
  mean budget apply: WILQ still blocks budget scaling/apply until
  `human_budget_goal`, apply safety and mutation audit exist. Profitability,
  wasted-budget, audience size, campaign-performance, recommendation apply,
  change impact and performance-uplift claims still need explicit
  read/safety/apply contracts. Individual recommendation rows may still show
  `missing_metrics=["recommendation_impact"]` when Google Ads does not return
  impact metrics for that recommendation type; that is not an OAuth/API blocker.
  Full `scripts/verify.sh` passed for the Command Center Ads review-queues
  slice on 2026-06-20: backend API contracts `117 passed`, dashboard route
  tests `14 passed`, Playwright e2e `9 passed`, API smoke, skill structure
  smoke, skill API smoke, security checks and dashboard production build
  passed.
  Source-backed decision lineage now exists for Ads diagnostics: sections and
  decision queue items expose `knowledge_card_ids` and `expert_rule_ids`.
  Current proof chain for the budget slice is
  `google_ads_budget_review_playbook` ->
  `card_google_ads_budget_review_playbook` ->
  `ads_review_budget_context` with expert rules
  `ads_scaling_candidates_v1`, `ads_recommendations_v1` and
  `ads_principles_v1`. Dashboard `/ads-doctor` renders those trace IDs, and
  `wilq-ads-doctor` scoped context-pack preserves them for Codex. Fresh
  non-interactive `wilq-ads-doctor` eval passed for the newest 90-day safety
  slice:
  `.local-lab/evals/codex-skill/20260619T182309Z/wilq-ads-doctor/result.json`.
  Eval result includes `card_google_ads_budget_review_playbook`,
  `ads_scaling_candidates_v1`, `ads_recommendations_v1`,
  `ads_principles_v1`, `keyword_match_context_read_contract`,
  Google Ads evidence IDs and prepare-only
  `act_prepare_ads_campaign_review_queue` /
  `act_prepare_negative_keyword_review_queue` action candidates.
  Full `scripts/verify.sh` passed for this lineage/eval slice on 2026-06-19:
  backend API contracts `111 passed`, dashboard route tests `13 passed`,
  Playwright e2e `9 passed`, API smoke, skill structure smoke, skill API smoke,
  security checks and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk is `530.51 kB`, above the 500 KB warning threshold.
- `google_merchant_center`: live product/feed facts exist and support a review
  queue. Merchant diagnostics now distinguishes report occurrences from unique
  affected products: `/merchant` labels them as `Zgłoszenia`/`kontekst`, not
  `Affected`, and aggregate `product_count`/`issue_count` may fallback to latest
  refresh summary when issue-level metric facts are the only stored facts.
  Latest Merchant regression fix: live issue clusters can disappear when the
  Merchant metric fact read limit is too low, because newer aggregate facts push
  issue-level rows out of the window. The fix raises that limit and makes the
  Merchant skill smoke fail if live diagnostics has issues but no
  `issue_clusters`.
- `google_search_console`: query/page facts exist and support content decisions.
  Tactical/content reads now preserve complete latest metric groups per
  `(connector, evidence, dimensions)`, so query/page cards do not show false
  `impressions=0` when the same evidence group has real impressions. Latest
  GSC/content regression fix: newer aggregate GSC refresh rows can push older
  but still useful query/page facts outside a generic 300-row read window. The
  tactical/content selectors now preserve a larger GSC window for query/page
  evidence, and `wilq-gsc-content-doctor` smoke fails if query/page metric
  facts exist but `content_diagnostics.decision_queue` is empty. Latest content
  follow-up on 2026-06-20 makes `content_diagnostics.decision_queue` carry
  marketer-facing `summary`, `primary_query`, `total_clicks`,
  `total_impressions`, `aggregate_ctr` and `best_average_position`, sorted by
  real GSC demand instead of URL/id. Latest 2026-06-21 follow-up adds
  review-only `content_brief_preview_v1` to `act_prepare_content_refresh_queue`
  so the same GSC/WordPress/Ahrefs evidence can become a blocked payload preview
  for Codex and `/content-planner`, not only a diagnostic card.
- `google_analytics_4`: landing/source/campaign facts exist and
  `/api/ga4/diagnostics.decision_queue` now feeds both dashboard `/ga4` and
  `wilq-ga4-analyst`. Current live decisions are traffic-quality review; ROAS,
  revenue, conversion-drop, attribution verdict and tracking-fixed claims stay
  blocked unless conversion/cost/read contracts exist. Command Center must keep
  GA4 as `blocked` while those interpretation contracts are missing, even when
  live GA4 behavior facts exist; `ready` would imply a complete marketer
  decision and causes confusion.
- `wordpress_ekologus` and `wordpress_sklep`: inventory context exists and must
  protect against duplicate content.
- `ahrefs`: authority/rank, competitor, content gap and backlink gap facts exist
  as read-only evidence. `/api/content/diagnostics` scores Ahrefs gap records
  into relevant/review/off-topic candidates, and
  `act_prepare_content_refresh_queue` now exposes only review-safe Ahrefs brief
  previews that still require GSC demand, WordPress inventory and duplicate
  checks before any create/refresh decision. No traffic, ranking, authority,
  lead or revenue uplift claim is allowed.
- `localo`: MCP Server URL, OAuth Client ID/Organization ID, OAuth Client
  Secret/Create Token and local OAuth access token are configured. On
  2026-06-18, `refresh_localo_af3a75e8659e` completed a live API-triggered
  Localo MCP initialize with `mcp_initialize_status=200`, checked
  `LOCALO_ACCESS_TOKEN` and redacted the token value. No local ranking/GBP
  claim is allowed yet until WILQ API exposes Localo evidence beyond the
  OAuth/initialize probe.
- `linkedin` and `facebook`: publishing is permission-gated. Drafting can be
  prepare-only and evidence-backed; publishing cannot be claimed.
- `google_sheets`: disabled intentionally and not needed for current scope.

Known important local paths are documented in `AGENTS.md`; do not print secret
values.

## Completed Foundation

Do not rebuild these from scratch:

- Private repo, `.gitignore`, AGENTS rules, architecture docs and quality gates.
- WILQ API spine, typed schemas, connector registry, evidence registry,
  opportunities, expert rules, knowledge compiler and ActionObjects.
- Local `.env` credential runtime and redaction rules.
- SQLite local state, DuckDB metric store, Typer CLI and manual job scheduler.
- 12 repo-local WILQ skills under `.agents/skills`.
- Baseline non-interactive Codex eval harness and deterministic skill smokes.
- API-backed dashboard shell using typed frontend boundaries.
- Command Center, Merchant, Content Planner, GA4, Ads Doctor, Localo and Ahrefs route
  surfaces.
- Google Ads OAuth helper and successful live campaign metric read.
- Real-browser Playwright smoke in `scripts/verify.sh`.
- Merchant route/API clarification for feed problems: issue clusters show report
  occurrences and context, while product-level sample IDs/titles remain blocked
  until the Merchant read contract exposes them.
- Merchant route operator cleanup: `/merchant` now shows the feed review task,
  issue clusters, translated blocked claims, ActionObject validation and
  `Dowody i ograniczenia Merchant` instead of duplicate diagnostic sections or
  English technical copy.
- Content Planner route operator cleanup: `/content-planner` now renders
  typed content decisions from `content_diagnostics.decision_queue`, blocks GA4
  tracking gaps as non-content tasks, groups GSC/WordPress decisions per URL
  and avoids false zero metrics when evidence is missing. Latest proof after
  `scripts/local_stack.sh restart`: top decisions are
  `SEO: odśwież lub scal "bdo co to" (1 zapytanie)` z
  `4429 wyświetleń`, `4 kliknięcia`, CTR `0.09%`, oraz
  `SEO: odśwież lub scal "zielony ład co to" (7 zapytań)` z
  `2902 wyświetlenia`, `123 kliknięcia`, CTR `4.24%`; scoped
  `wilq-content-strategist` context-pack preserves the same decision fields,
  evidence IDs and `act_prepare_content_refresh_queue`.
- Command Center content bridge: `daily_content_queue`,
  `decision_prepare_content_refresh_queue` and scoped `wilq-daily-command`
  context-pack now consume `ContentDiagnosticsResponse.decision_queue` instead
  of raw tactical item summaries. The visible first-screen content decision is
  `Przejrzyj kolejkę SEO z GSC i WordPress`, with GSC aggregate counts and
  Polish no-claim summary. Action/evidence IDs stay available as structured
  fields.
- GA4 route operator cleanup: `/api/ga4/diagnostics` now exposes a typed
  `decision_queue` with `fix_measurement`, `review_landing_mapping` and
  `review_traffic_quality` decisions. Dashboard `/ga4` renders this as the
  primary marketer view, keeps evidence/action IDs, and no longer shows raw
  English diagnostic section titles such as `GA4: landing/source/campaign
  behavior`, `GA4: tracking/conversion readiness` or `Analytics Safety Gate`.
- Ads Doctor route operator cleanup: `/api/ads/diagnostics` now exposes a typed
  `decision_queue` with campaign review, search-term review, custom segment
  candidate review, budget context review and blocked write path decisions.
  Dashboard `/ads-doctor` renders those decisions first, keeps evidence/action
  traceability, translates status/blocked claims to Polish and no longer shows
  raw `Read contract Ads`, `Search terms read-only`,
  `Campaign activity read contract`, `Evidence`, `configured`, `READY`,
  `payload preview` or stale OAuth blocker copy when live Ads data exists.
- Localo route operator cleanup: `/api/localo/diagnostics` now exposes a typed
  access/readiness contract with missing Localo visibility contracts and blocked
  claims. Dashboard `/localo` renders `Status Localo / MCP access`,
  `Co marketer ma wiedzieć o Localo`, `Dowody i ograniczenia Localo` and a
  Localo/GBP safety gate instead of the generic tactical queue, `Metric facts`,
  `24 Taktyki` counters or stale `Dokończ Localo access` copy when MCP
  initialize already works.
- Ahrefs route operator cleanup: `/api/ahrefs/diagnostics` now exposes typed
  authority-context decisions and a blocker for missing competitor/content/
  backlink gap records. Dashboard `/ahrefs` renders `Status Ahrefs / dowody
  SEO`, `Co marketer ma wiedzieć o Ahrefs`, `Dowody i ograniczenia Ahrefs`
  and does not fall back to the generic registry surface.
- Metric store grouped batch reads for tactical/content surfaces: latest
  query/page groups keep clicks, impressions, CTR and position together instead
  of truncating by connector row count.

## Active Product Problems

These are the current reasons Goal 001 is not complete:

1. **Dashboard route audit must stay enforced, not restarted.**
   Command Center, `/actions`, `/opportunities` and `/merchant` have been
   cleaned up for the current stale Ads/Localo/readiness issues and technical
   wording. `/content-planner` has also been cleaned up around its typed
   content decision queue. `/ga4` has been cleaned up around its typed GA4
   decision queue. `/ads-doctor` has been cleaned up around its typed Ads
   decision queue. `/localo` has been cleaned up around
   `/api/localo/diagnostics`. `/ahrefs` has been cleaned up around
   `/api/ahrefs/diagnostics`. Remaining route work is now regression control:
   every touched route must preserve the decision-first hierarchy, Polish
   operator copy, Codex bridge, evidence IDs and blocked claims. Do not
   reintroduce generic registries, readiness-only cards, stale blocker copy or
   raw metric dumps as first-screen marketer insight.

2. **Command Center and supporting registries must stay separated.**
   Evidence IDs and ActionObjects are required, but the marketer needs a clear
   "what to do now and why" hierarchy. Raw connector/status/readiness cards and
   opportunity/action registries must not masquerade as marketing insight.

   Hard block: first-screen Command Center must not render readiness-only cards
   such as `connector_configured=true`, `Connector ... ready for ... refresh`,
   `No performance metrics have been collected`, or `Run a read-only refresh`.
   Those belong in lower diagnostic/settings surfaces unless converted into a
   real decision, blocker or action.

   Fresh audit correction: canonical `DailyDecision` is the primary Command
   Center model. `operator_brief`, `action_plan`, `marketing_brief`,
   diagnostics, `/api/actions` and `/api/opportunities` are supporting
   surfaces, not competing first-screen decision queues.

3. **Ads Doctor is useful for read-only review, but not yet a full optimizer.**
   Campaign-level activity, search-term facts, custom segment candidates and
   the latest negative keyword safety review queue now have explicit
   read/decision contracts. Budget context is also explicit and read-only:
   WILQ can compare campaign daily budget against 7-day cost, but cannot
   recommend scaling, pausing or applying budget changes. The negative keyword
   queue is prepare-only safety review, not a waste verdict or apply path.
   Recommendations, quality scoring, budget optimization decisions, impression
   share, keyword/match context, full 90-day safety history, Keyword Planner enrichment,
   forecast/audience-size contracts and apply previews still need explicit
   read/safety/ActionObject contracts before WILQ can claim BDOS-class Ads
   optimization value.

4. **Codex skill usefulness is not fully proven end-to-end.**
   Skills have contracts and smokes, and `wilq-daily-command` now has a
   strengthened usefulness guardrail plus a fresh non-interactive eval pass.
   `wilq-content-strategist`, `wilq-ads-doctor` and
   `wilq-custom-segments` also have strict usefulness passes after their
   matching API contracts. `wilq-ga4-analyst` has now been repaired against
   `/api/ga4/diagnostics.decision_queue` and passed a fresh strict
   non-interactive eval on 2026-06-19. `wilq-localo-operator` should consume
   `/api/localo/diagnostics` for access/readiness and must continue blocking
   ranking/GBP/competitor claims until actual Localo visibility facts exist.
   Goal 001 still needs the same strict usefulness pass across the remaining
   high-value skills and a clean plug-and-play Codex session proving Polish
   prompts -> WILQ API calls -> same evidence IDs as dashboard -> useful next
   actions.

5. **Knowledge condensation is not fully proven.**
   Playbooks and knowledge cards exist, but we must prove they influence skill
   outputs and content/Ads decisions instead of sitting beside the product.
   Goal 001 must show at least one source-backed chain:
   source -> knowledge card/rule -> API view model -> dashboard card ->
   non-interactive Codex skill output.

   Current progress moves this in the right direction for content and Ads:
   `content_diagnostics.decision_queue` is typed API state, not skill-reference
   logic. Ads diagnostics now has a first source-backed chain for budget
   review: `google_ads_budget_review_playbook` compiles to
   `card_google_ads_budget_review_playbook`, API decisions expose
   `knowledge_card_ids` and `expert_rule_ids`, `/ads-doctor` renders those
   trace IDs and `wilq-ads-doctor` context-pack preserves them. The remaining
   proof is a non-interactive Codex eval that verifies the skill uses that
   lineage in a Polish marketer answer. The follow-up daily context-pack slice
   also moved metric fact reads into batched/read-only API storage paths instead
   of skill-reference patches.

   This is the explicit home for the "best standards / practitioner sources /
   papers / doctoral-quality sources" layer. It is not a vague memory dump.
   The required shape is: source map -> knowledge card or expert rule ->
   typed WILQ evidence requirements -> blocked claims -> API view model ->
   dashboard + Codex skill proof. Do not close this problem by adding long
   prompt text to skills; close it by proving source-backed rules change
   concrete marketer decisions.

6. **Localo and social remain limited-evidence surfaces.**
   Localo access/readiness has a typed API surface in `/api/localo/diagnostics`.
   It proves MCP initialize/access state and names missing contracts, but local
   ranking/GBP/competitor/review insight remains blocked until a concrete Localo
   visibility read contract exists. Latest Localo follow-up: every
   `LocaloDecisionItem` now exposes typed `priority` and `metric_tiles`.
   Live proof after restart: 2 Localo decisions, `null_priority=[]`,
   `empty_tiles=[]`; access-ready decision shows `dostęp MCP=1`,
   `fakty Localo=0`, `braki kontraktu=5`, while the visibility blocker shows
   `blokady claimów=5`. Fresh `wilq-localo-operator` eval passed on
   2026-06-19 and proves the same semantic state: access is ready, local
   visibility insight is blocked. Social publishing remains permission-gated;
   drafting can be prepare-only and evidence-backed.

7. **Full verification after the latest changes passed.**
   `scripts/verify.sh` passed after the 2026-06-21 Ahrefs top-pages slice:
   backend API contracts `139 passed`, dashboard unit tests `17 passed`,
   Playwright e2e `14 passed`, security, skill/API smokes and dashboard
   production build passed. Keep this file current after every future slice.

8. **Ahrefs is source-read-ready for authority, organic competitors, competitor top pages, organic keywords by URL, content-gap candidates and backlink-gap candidates.**
   `/api/ahrefs/diagnostics`, `/ahrefs` and scoped `wilq-ahrefs-gap-finder`
   context-pack now prove DR/rank authority facts, real organic competitor
   records, competitor top-page records, organic keyword records by competitor
   URL, sample-backed content gap records, refdomains-based backlink gap
   records and explicit blocking of unsupported impact claims.
   Current live proof: DR=40, Ahrefs Rank=1541946,
   `organic_competitor_read_status=completed`, `organic_competitor_rows=10`,
   `organic_competitor_mode=subdomains`,
   `top_pages_by_competitor_read_status=completed`,
   `top_pages_by_competitor_rows=4`,
   `organic_keywords_by_url_read_status=completed`,
   `organic_keywords_by_url_rows=4`,
   `content_gap_read_status=completed`, `content_gap_rows=4`,
   `backlink_gap_read_status=completed`, `backlink_gap_rows=9`,
   `gap_read_contract.status=ready`, `missing_read_contracts=[]`,
   `gap_records=24`, `active_action_ids=[]`,
   available read contracts `ahrefs_competitor_pages` and
   `ahrefs_top_pages_by_competitor`, `ahrefs_organic_keywords_by_url` and
   `ahrefs_content_gap_records` and `ahrefs_backlink_gap_records`. Next Ahrefs
   value work is not another fake gap unlock; it is to connect these records
   with GSC/WordPress/action review and keep traffic/authority uplift claims
   blocked until impact/change-window contracts exist.
   Strict eval coverage now exists for this blocker guardrail:
   `.local-lab/evals/codex-skill/20260621T030447Z/wilq-ahrefs-gap-finder/result.json`.

## What WILQ Must Give The Marketer

For every meaningful screen or skill response, WILQ should answer:

- **Co widzę?** Real facts, source connector, freshness and evidence IDs.
- **Co to znaczy?** Diagnosis in Polish, with blocked claims named explicitly.
- **Co zrobić teraz?** One or more safe next actions, preferably ActionObjects.
- **Czego nie wolno twierdzić?** Missing evidence, unsupported metrics, blocked
  writes or permission gaps.
- **Jak sprawdzić?** Link/ID to evidence, action validation or dashboard route.

Examples of real value:

- Merchant: "10900 produktów, 15 typów problemów i 1887 zgłoszeń problemów
  feedu wymagają review; validate `act_review_merchant_feed_issues`; do not
  promise approval recovery."
- Content: "GSC + inventory WordPress suggests refresh/create/block decisions;
  do not promise ranking or lead uplift."
- GA4: "Landing/source/campaign traffic quality looks weak; review tracking and
  message match; do not claim ROAS/revenue."
- Ads: "Campaign and search-term metric facts exist, including conversion
  counts/value; review live activity and prepare safety review candidates, but
  keep profitability, wasted budget, budget scaling, negative keyword apply and
  recommendation/apply claims blocked until currency, margin, pacing,
  match-context, safety and ActionObject apply contracts exist."
- Localo: "MCP access działa (`mcp_initialize_status=200`), ale lokalna
  widoczność nie może być analizowana, dopóki WILQ API nie zbierze konkretnych
  Localo ranking/GBP/competitor facts poza initialize probe."

If a dashboard section only says "connector configured" without converting that
into a decision or blocker, it is not yet useful to the marketer.

## Plug-And-Play Acceptance Gate

Before Goal 001 can be closed, run a clean session that proves WILQ is useful
out of the box:

1. Start WILQ API and dashboard.
2. Open a fresh Codex session with repo skills available.
3. Use Polish marketer prompts:
   - `Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.`
   - `Co w Ads mogę uczciwie powiedzieć na podstawie obecnego evidence?`
   - `Którą treść odświeżyć albo stworzyć i czego nie wolno obiecywać?`
   - `Czy Merchant ma problem z produktami/feedem i jaki ActionObject sprawdzić?`
   - `Czy Localo daje już ranking/GBP insight czy nadal blocker?`
4. For each prompt compare:
   - plain Codex without WILQ skill/API context,
   - Codex using the matching WILQ skill,
   - dashboard/API view for the same evidence.
5. Pass only if the skill response:
   - is in Polish,
   - calls WILQ API or honestly reports a blocker,
   - includes source connectors and evidence IDs,
   - does not invent metrics,
   - gives a next safe action,
   - matches dashboard/API evidence for the same claim.

This gate answers the real question: can Codex + WILQ API + WILQ skills do more
for the marketer than plain Codex/manual panel work?

## MCP Decision

Do not build a WILQ MCP server just because MCP exists.

Current position:

- WILQ REST API is canonical.
- Repo skills call REST/context-pack.
- MCP servers are adapters, not the product brain.
- Localo exposes external MCP/OAuth and remains an adapter source.

A WILQ MCP server is justified only if plug-and-play testing proves that Codex
tool ergonomics or reliability are materially worse through REST/skills than
through a thin MCP surface. If built, it must wrap WILQ API and must not bypass
evidence IDs, ActionObject validation, audit logging or redaction.

## Active Queue

This is the current executable goal. Work through it in order and update this
section whenever a step is completed, blocked or replaced by a better-proven
next step.

### Audit-Derived Goal Stack

Source of truth for this stack:

```txt
docs/audits/001-output.md
```

The audit confirms the architecture direction is right: FastAPI/WILQ API is the
brain, typed schemas and evidence IDs are the product contract, and dashboard
plus Codex skills must consume the same API state. The audit also confirms the
current weakness: WILQ still sometimes presents system readiness as marketer
insight and several skills pass because they block safely, not because they
produce high-value decisions.

Work in this order:

1. **Done: content decision queue and Content Planner route cleanup.**
   `content_diagnostics.decision_queue` must remain typed API state, not skill
   reference logic. It must support `refresh_or_merge`,
   `merge_create_after_inventory_check`, `inventory_check_before_create` and
   `block_as_tracking_not_content`, with evidence IDs, source connectors,
   ActionObject IDs and blocked claims. This was committed as
   `2e0b0dc feat(content): expose content decision queue`.
   Follow-up route cleanup on 2026-06-19 made `/content-planner` render this
   decision queue as the primary marketer view, grouped duplicated GSC queries
   per URL, blocked GA4 tracking gaps as non-content work and removed stale
   labels such as `Query/page`, `WP match`, `exact_url`, `payload preview` and
   false `impressions=0` / `ctr=0` for missing evidence. Follow-up on
   2026-06-20 added human-readable content decision summaries and GSC aggregates
   to the typed API/shared schema/dashboard/context-pack contract. Later the
   same day, Command Center and `wilq-daily-command` were bridged to this
   content diagnostics contract, so the first-screen Content card no longer
   uses the old raw `query/page + WP match` prose as the main insight. Full
   `scripts/verify.sh` passed for this bridge slice on 2026-06-20: backend
   `117 passed`, dashboard unit `14 passed`, Playwright e2e `9 passed`,
   security, skill/API smokes and dashboard production build passed.

2. **Done: Command Center as canonical `DailyDecision`.**
   Introduce one first-screen decision model instead of competing
   `operator_brief`, `action_plan`, `marketing_brief`, diagnostics and action
   fragments. A `DailyDecision` must include:
   `co_widzimy`, `dlaczego_to_ma_znaczenie`, `bezpieczny_next_step`,
   `blocked_claims`, `evidence_ids`, `source_connectors`, `action_ids`,
   `skill_id`, `codex_prompt` and `route`.

   Current local status: `DailyDecision` schema and
   `/api/dashboard/command-center.daily_decisions` are implemented. Dashboard
   Command Center now renders one `Dzisiejsze decyzje marketera` board instead
   of duplicating the same intent as `Dzisiejszy panel operatora` plus
   `Plan działań marketera`. Full connector blocker cards were removed from
   `/command-center`; a compact `Źródła i ograniczenia` footer links to
   `/settings` for diagnostic credential/status details. `wilq-daily-command`
   smoke validates the field and its context-pack trace. Focused API/shared
   schema/dashboard checks and Playwright Command Center/demo proof pass after
   this cleanup. Full `scripts/verify.sh` passed on 2026-06-18 for the current
   checkout: backend API contracts 97 passed, dashboard route tests 12 passed,
   Playwright e2e 8 passed and dashboard production build passed.

   Follow-up completed on 2026-06-19: `/actions` starts from
   `ActionObjecty do przeglądu` and related evidence instead of generic
   registry dumps. `/api/actions` no longer resurrects
   `act_configure_google_ads_env` after a later Ads `status_probe` when a live
   Ads `vendor_read` exists. Browser proof with `agent-browser` found no stale
   Ads OAuth action and no generic registry dump on `/actions`. Focused
   Playwright e2e passed: `9 passed`.

   Follow-up completed on 2026-06-20: `/api/opportunities`, `/opportunities`
   and full Codex context-pack `top_opportunities` now consume daily marketer
   decisions instead of old connector-registry cards. Live proof after
   `scripts/local_stack.sh restart`: 4 decision-backed cards, all with
   `opp_decision_*` IDs, `metric_tiles`, evidence IDs, source connectors,
   ActionObject IDs and Polish next steps. The live proof contains no
   `opp_connector_*` opportunities and no redaction paths under
   `opportunities`. Full `scripts/verify.sh` passed after this slice.

   Follow-up completed on 2026-06-20: `/api/workflows` and `/workflows` now
   expose workflow contracts derived from daily decisions instead of 15 generic
   placeholders. Core workflows carry route, skill, metric tiles, source
   connectors, evidence IDs and ActionObject IDs; planned workflows show
   missing contracts such as `pre_post_change_impact`,
   `creative_asset_readiness`, `local_ranking_rows` and
   `social_publish_permission`. Full `scripts/verify.sh` passed after this
   slice with backend `118 passed`, dashboard unit `14 passed` and Playwright
   e2e `10 passed`.

   Follow-up completed on 2026-06-19: `/ga4` now consumes a typed
   `Ga4DecisionItem` queue from `/api/ga4/diagnostics.decision_queue` and shows
   marketer-facing decisions instead of raw `landing/source/campaign behavior`
   cards.

   Follow-up completed on 2026-06-22: Command Center first screen was cleaned
   again as a marketer view, not a trace registry. It keeps the same
   `DailyDecision` evidence/action state, but hides raw `ev_*`, `act_*`,
   `Skill: wilq-*` and `Context-pack: /api/codex/context-pack` from the first
   screen. It now shows Polish status labels, human source names, proof counts
   and safe-action counts, with raw IDs preserved on supporting detail routes.
   Browser proof and Playwright prove this behavior, and `scripts/verify.sh`
   passed with backend, dashboard, skill smoke, e2e and build gates.

   Earlier GA4 route cleanup also removed stale diagnostic sections. Browser
   proof found no stale phrases:
   `payload preview`, `read-only`, `Evidence`, `READY`, `configured`,
   `WP match`, `WP missing`, `landing/source/campaign`,
   `Analytics Safety Gate`, `Tracking readiness`, `conversion-like`,
   `tracking-gap checklist` or `metric_facts`. Full `scripts/verify.sh` passed
   after this slice with backend API contracts `98 passed`, dashboard route
   tests `13 passed`, Playwright e2e `9 passed` and dashboard production build
   passed.

   Follow-up completed on 2026-06-19: `/localo` now consumes
   `/api/localo/diagnostics` instead of the generic workflow/tactical surface.
   The route shows MCP access/readiness, missing visibility contracts and
   blocked Localo/GBP claims. It does not show `Local Visibility Focus`,
   `Taktyki z WILQ API`, `Metric facts`, `24 Taktyki` or stale
   `Dokończ Localo access` copy when access is already proven. Focused backend
   contract tests and dashboard route tests pass for this slice. Full
   `scripts/verify.sh` passed after this slice with backend API contracts
   `100 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
   and dashboard production build passed.

   Follow-up completed on 2026-06-20: Command Center Ads now consumes the same
   Ads diagnostics as `/ads-doctor` and exposes concrete review queues instead
   of generic `live metric facts` prose. `daily_ads_status` and
   `plan_review_ads_campaign_metrics` show budget, recommendation, search-term,
   negative keyword and custom segment review context with ActionObject IDs,
   blocked claims and a Polish Codex prompt. Live proof after
   `scripts/local_stack.sh restart`: `kampanie=18`, `zapytania=50`,
   `podgląd budżetu=18`, `rekomendacje=4`, `wykluczenia=6`, `segmenty=1`.
   Focused ruff, mypy and command-center API contract tests pass for this
   slice. Full `scripts/verify.sh` passed with backend API contracts
   `117 passed`, dashboard route tests `14 passed`, Playwright e2e `9 passed`,
   API smoke, skill structure smoke, skill API smoke, security checks and
   dashboard production build.

   Follow-up completed on 2026-06-20: Command Center marketer-facing blocked
   claims are now translated at the dashboard boundary. The API still exposes
   stable raw `blocked_claims`, but daily decisions, tactical cards and
   brief/action cards render Polish labels such as `ponowne zatwierdzenie
   produktu`, `wzrost leadów`, `opłacalność` and `zmarnowany budżet`. The Ads
   Codex prompt in `/api/dashboard/command-center` and scoped
   `/api/codex/context-pack` now blocks `opłacalność`, `zmarnowany budżet` and
   `wdrożenie zmian` in Polish instead of visible raw `profitability` /
   `wasted budget`. Focused backend/frontend checks and real-browser Command
   Center smoke passed for this slice.

   Follow-up completed on 2026-06-20: Ads search-term safety, keyword match
   context and negative keyword review now separate data availability from
   human intent review. `human_intent_review` moved out of
   `missing_read_contracts` and into `operator_review_gates` when the 90-day
   safety rows and keyword match context are present. Live proof after
   `scripts/local_stack.sh restart`: search-term safety and keyword context
   both have empty missing read contracts plus
   `operator_review_gates=["human_intent_review"]`; decisions
   `ads_review_search_term_safety` and `ads_review_negative_keyword_safety`
   carry the same gate. Full `scripts/verify.sh` passed with backend
   `119 passed`, dashboard unit `14 passed`, Playwright e2e `11 passed`,
   skill/API smokes, security checks and dashboard production build.

3. **Slice 2: performance budget and scoped runtime.**
   Command Center summary target: under 1s local and about 80-120 KB when
   feasible. Non-daily skill context-pack target: under 2s and under 200 KB.
   Full context-pack is a debug mode, not default runtime. Measure before and
   after; do not hide performance issues with random frontend memoization.

   Current status after the 2026-06-19 non-daily context-pack follow-up:
   all default skill context-packs are now below 200 KB. Full diagnostic detail
   remains in `full_context=true` and dedicated API endpoints. Live proof after
   `scripts/local_stack.sh restart`:
   - `wilq-campaign-builder`: `90711 bytes`, cold `1.867s`, warm `0.158s`,
     sources `google_ads`, `google_analytics_4`, `google_search_console`.
     It now uses `ads_diagnostics` plus lightweight `content_landing_context`
     instead of full `content_diagnostics`, and it no longer pulls Merchant,
     negative keyword or custom-segment ActionObjects by default. Latest fresh
     API-process proof after Ads review-gate scope cleanup: `191737 bytes`,
     active actions only `act_prepare_ads_campaign_review_queue` and
     `act_prepare_google_ads_recommendation_review_queue`.
   - `wilq-demand-gen-operator`: `100349 bytes`, cold `2.574s`, warm `0.156s`,
     sources `google_ads`, `google_analytics_4`; Ads and GA4 diagnostics build
     in parallel and Merchant stays omitted until a concrete Demand Gen/Merchant
     read contract exists. Latest fresh API-process proof after Demand Gen
     campaign-channel follow-up: `active_action_objects=[]`,
     `ads_diagnostics.action_ids=[]`, `demand_gen_readiness.status=blocked`,
     `campaign_rows_evaluated=18`,
     `campaign_channel_counts={PERFORMANCE_MAX: 8, SEARCH: 10}`,
     `demand_gen_campaign_rows=[]`; campaign rows are available, while asset,
     creative, landing-quality, migration and ActionObject contracts remain
     missing.
   - `wilq-content-strategist`: `91731 bytes`, cold `2.044s`, warm `0.166s`.
   - `wilq-ga4-analyst`: `28578 bytes`, cold `1.927s`, warm `0.147s`.
   - `wilq-merchant-feed-operator`: `24007 bytes`, cold `1.819s`, warm
     `0.153s`.
   - `wilq-ads-doctor`: `185126 bytes`, cold `1.392s`, warm `0.156s`.
     Latest live follow-up after Ads context-pack compaction:
     `174292 bytes` over the wire, smoke-reported `context_pack_bytes=183152`,
     duplicate `sections` and decision row payloads omitted, full Ads endpoint
     pointer preserved.
   - `wilq-custom-segments`: `187121 bytes`, cold `1.408s`, warm `0.194s`.
   - `wilq-daily-command`: `120504 bytes`, cold `1.918s`, warm `0.236s`.
   Focused ruff, mypy, context-pack API tests and live smoke scripts for
   `wilq-campaign-builder` and `wilq-demand-gen-operator` passed. Full
   `scripts/verify.sh` also passed after this slice: API smoke, skill smokes,
   dashboard route tests, Playwright e2e `9 passed` and dashboard production
   build. Slice 2 remains open only for deeper cold-path improvement,
   especially Demand Gen cold latency around `2.6s`, and future route-level
   lazy loading if browser proof shows it is still needed.

4. **Slice 3: Merchant issue-level triage.**
   Convert Merchant from `products/issues` summary into issue clusters by
   `issue_type`, `affected_attribute`, `country`, `reporting_context`, impact,
   sample products if available, evidence IDs and
   `act_review_merchant_feed_issues`. This is the strongest current demo win.

   Current status: typed `MerchantIssueCluster` exists in Python and
   shared frontend schemas. `/api/merchant/diagnostics` now returns
   `issue_clusters`, `act_review_merchant_feed_issues` carries the same cluster
   payload, and dashboard `/merchant` renders clusters as the primary review
   queue. Full `scripts/verify.sh` passed for this slice on 2026-06-18. The
   current Merchant API read contract still does not return sample product IDs
   or product titles; the UI must state that limit honestly.

   Latest Merchant follow-up after overnight context handoff: latest live check found a
   regression where `issue_count=15` but `issue_clusters=[]` because
   `MERCHANT_METRIC_FACT_LIMIT=240` was too low for the current DuckDB history.
   The fix raises the limit to `2000` and strengthens
   `wilq-merchant-feed-operator` smoke to fail on live issue data without
   clusters. Proof so far: `/api/merchant/diagnostics` on `:8015` returns
   `issue_cluster_count=11`; the Merchant smoke passes; non-interactive
   `wilq-merchant-feed-operator` eval passed at
   `.local-lab/evals/codex-skill/20260619T073915Z/wilq-merchant-feed-operator/result.json`
   with `operator_usefulness_score=5`, `act_review_merchant_feed_issues` and
   blocked feed/product mutation claims. Focused ruff/mypy/API tests passed.
   Full `scripts/verify.sh` passed after updating the stale Merchant demo e2e
   assertion: backend API contracts `102 passed`, dashboard route tests
   `13 passed`, Playwright e2e `9 passed`, skill API smoke passed and dashboard
   production build passed.

5. **Slice 4: Content/GSC/GA4/WordPress URL normalizer.**
   Normalize host, path, slash, sitemap, post/page type and GA4 landing path to
   full WordPress URL. The goal is reliable `refresh/merge/create/block`
   decisions and no duplicate content suggestions. GA4 `(not set)` remains a
   tracking issue, not a content task.

   Current local status: tactical queue now reads enough WordPress inventory
   rows from DuckDB to avoid false `missing` caused by large sitemap inventories.
   GSC full URLs and GA4 landing paths expose normalized path keys, match
   confidence and matched WordPress URL in typed API fields. Direct checkout
   proof shows BDO, Zielony Ład and remediacja GSC URLs as `found exact_url`,
   and GA4 landing paths as `found path_fallback`. Full `scripts/verify.sh`
   passed for this slice on 2026-06-18.

   Latest follow-up on 2026-06-19: content/tactical GSC selection now preserves
   older dimensioned query/page evidence even when newer aggregate GSC refreshes
   exist. Live proof on `:8016` after the fix:
   `query_page_count=10`, `matched_inventory_count=10`, `decision_count=4`
   with decisions for homepage, BDO, Zielony Ład and remediacja. Regression test
   `test_content_diagnostics_preserves_gsc_query_page_after_newer_aggregate_runs`
   seeds newer aggregate GSC runs and fails if the older query/page group is
   lost again.

6. **Slice 5: Ads Doctor read contracts.**
   Keep Ads as live campaign-level review until WILQ has explicit read
   contracts for search terms, conversions, campaign budget/spend/clicks,
   recommendations, change history, safety checks and blocked-claim matrix. Do
   not call it a money-leak optimizer until those facts exist.

   Current local status: `/api/ads/diagnostics.campaign_read_contract` is typed
   and live. It groups Google Ads metric facts into campaign rows with
   `campaign_id`, `campaign_name`, `clicks`, `impressions`, `cost_micros`,
   `conversions`, `conversion_value`, evidence IDs and blocked claims.

   Current local status: `/api/ads/diagnostics.search_terms_read_contract` is
   now typed too. Google Ads `vendor_read` queries `search_term_view` in read
   mode and stores `search_term_clicks`, `search_term_impressions`,
   `search_term_cost_micros`, `search_term_conversions` and
   `search_term_conversion_value` metric facts with campaign/ad group/search
   term dimensions. Live read `refresh_google_ads_c2f62ee2b43a` completed on
   2026-06-18 with 18 campaign rows, 50 search term rows, campaign
   `conversions=2.0`, campaign `conversion_value=2.0`, search-term
   `search_term_conversions=0.0` and
   `search_term_conversion_value=0.0`. This unlocks honest campaign/search-term
   review with conversion context, not automatic waste or negative keyword
   claims.

   Current local status: `/api/ads/diagnostics.decision_queue` is typed and
   dashboard `/ads-doctor` renders it as the primary marketer view:
   `ads_review_campaign_activity`, `ads_review_search_terms`,
   `ads_prepare_custom_segments_from_search_terms` and
   `ads_block_write_actions_without_actionobject`. Browser proof on 2026-06-19
   found no stale visible `Read contract Ads`, `Search terms read-only`,
   `Campaign activity read contract`, `Search terms read contract`,
   `Google Ads: campaign activity rows`, `Google Ads: search terms read-only rows`,
   `Evidence`, `configured`, `READY`, `payload preview`, `write/apply` or
   `WILQ ma read-only Google Ads evidence`.

   Current local status: `/api/ads/diagnostics.custom_segments_read_contract`
   is typed and ready when Google Ads search-term evidence exists. It exposes
   1 prepare-only candidate for campaign `Kompendium PPWR`, real
   `source_terms`, review-only `custom_segment_payload_preview`, evidence
   `ev_refresh_refresh_google_ads_eb8c239bc32b`, missing contracts
   `keyword_planner_enrichment` and `forecast_or_audience_size`, and
   ActionObject `act_prepare_custom_segments_from_search_terms`. The preview
   uses `member_type=KEYWORD`, `api_mutation_ready=false`,
   `apply_allowed=false` and `destructive=false`. Dashboard `/ads-doctor`
   renders these candidates; the skill `wilq-custom-segments` consumes the
   same contract.

   Fresh correction: Ads diagnostics now selects the latest Google Ads
   `vendor_read` as the evidence-bearing refresh. A later `status_probe` cannot
   downgrade live Ads state into stale OAuth blocker language. While live Ads
   data is available, `/api/marketing/brief`,
   `/api/ads/diagnostics.action_ids` and the scoped `wilq-ads-doctor`
   context-pack no longer promote `act_configure_google_ads_env`.

   Fresh skill proof: `wilq-ads-doctor` passed non-interactive Codex eval at
   `.local-lab/evals/codex-skill/20260618T191243Z/wilq-ads-doctor/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_connector_google_ads_status` and
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`, shows 18 campaign read-only
   rows and 50 search-term rows, and blocks CPA/ROAS profitability verdicts,
   search-term waste, wasted budget and negative keywords until missing
   interpretation/read/safety/ActionObject contracts exist.

   Fresh negative keyword safety proof: `wilq-ads-doctor` passed a new
   non-interactive Codex eval after `negative_keywords_read_contract` and
   `act_prepare_negative_keyword_review_queue` were added:
   `.local-lab/evals/codex-skill/20260619T065511Z/wilq-ads-doctor/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_connector_google_ads_status` and
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`, returns
   `negative_keywords_read_contract.status=ready`, `candidate_count=7`, one
   prepare-only ActionObject and blocked apply/waste/CPA/ROAS claims.

   Fresh manual usefulness proof: a 2026-06-19 `wilq-ads-doctor` run over live
   Ads evidence produced a useful Polish triage: 18 campaigns, 50 search-term
   rows, top campaign/search-term observations, and valid prepare-only
   ActionObjects `act_prepare_negative_keyword_review_queue` plus
   `act_prepare_custom_segments_from_search_terms`. This is recorded in
   `docs/evals/skill-eval-ledger.md`. It still blocks profitability, wasted
   budget, negative keyword apply, budget scaling and recommendation/apply
   claims until match context, full 90-day safety, payload preview, currency or
   margin interpretation, recommendations, change history and
   impression share exist.
   action candidate `act_prepare_negative_keyword_review_queue`, usefulness
   score 5 and no safety findings. It blocks `negative keyword apply`,
   search-term waste, wasted budget, CPA and ROAS without
   `90_day_safety_check`, payload preview and validated ActionObject.

   Fresh skill proof: `wilq-custom-segments` passed non-interactive Codex eval
   at
   `.local-lab/evals/codex-skill/20260619T035937Z/wilq-custom-segments/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`,
   `ev_connector_google_ads_status` and
   `ev_connector_google_search_console_status`, returns 1 recommendation and
   1 action candidate, validates
   `act_prepare_custom_segments_from_search_terms`, and blocks `audience size`,
   `ROAS`, `conversion uplift`, `targeting applied` and
   `campaign performance`.

   Latest follow-up: `/api/ads/diagnostics.negative_keywords_read_contract`,
   `keyword_match_context_read_contract` and
   `act_prepare_negative_keyword_review_queue` are implemented. The contract
   builds review-only candidates from `search_term_*` facts with activity and
   zero conversions/value in current evidence, attaches existing keyword/match
   type context from `ad_group_criterion`, and requires
   `apply_allowed=false`, `destructive=false`, evidence IDs, 90-day safety,
   payload preview and human intent review. It blocks `negative keyword apply`,
   `search-term waste`, `conversion loss`, CPA and ROAS.

   Latest local Ads budget context slice: Google Ads `campaign_budget` fields
   are stored as metric facts, `/api/ads/diagnostics` exposes
   `budget_pacing_read_contract.status=ready`, and `/ads-doctor` renders
   `Koszt 7 dni`, `7-dniowy budżet`, spend ratio and Google recommended-budget
   signal as read-only review context. This does not unlock budget scaling,
   campaign pause, wasted-budget or recommendation/apply claims.
   Full `scripts/verify.sh` passed for this slice on 2026-06-19: backend API
   contracts `108 passed`, dashboard route tests `13 passed`, Playwright e2e
   `9 passed`, API smoke, skill structure smoke, skill API smoke and dashboard
   production build passed. Known non-blocking warning: Vite main JS chunk
   `530.14 kB` exceeds the 500 KB warning threshold.

   Still missing for BDOS-class Ads value: change history,
   keyword/match context, full 90-day safety history, Keyword
   Planner enrichment, forecast/audience-size contract, custom segment payload
   preview, margin/currency interpretation, budget apply confirmation
   and all Ads apply/audit paths. Budget apply safety now exists as
   `campaign_budget_apply_safety_v1`. Full `scripts/verify.sh` passed after the custom
   segments slice on 2026-06-19: backend API contracts `100 passed`, dashboard
   route tests `13 passed`, Playwright e2e `9 passed` and dashboard production
   build passed. For the negative keyword safety slice, focused
   ruff/mypy/backend tests/dashboard tests/shared-schema typecheck passed, and
   full `scripts/verify.sh` passed with backend API contracts `102 passed`,
   dashboard route tests `13 passed`, Playwright e2e `9 passed`, skill API
   smoke passed and dashboard production build passed.

7. **Later P2/P3 data contracts.**
   Localo has access/readiness diagnostics, but still needs rankings, GBP
   visibility, competitors, reviews and local tasks before local SEO claims.
   Ahrefs needs competitor pages/backlink/content-gap records before gap claims.
   Custom Segments have real source terms, a prepare-only ActionObject and a
   review-only payload preview, but still need Keyword Planner enrichment,
   forecast/audience-size and targeting/apply contracts before any apply path.
   Campaign Builder needs campaign
   ActionObjects and payload preview contracts. Demand Gen needs
   creative/asset/landing-quality diagnostics. Social publishing stays explicit
   workflow only.

8. **Skill repair track: thin workflows after API contracts.**
   Skill repair is not done. It is also not the last cosmetic step. It runs
   immediately after the API/view-model contract for a workflow exists. The
   order is:
   - `wilq-daily-command` after canonical `DailyDecision`;
   - `wilq-merchant-feed-operator` after Merchant issue-level triage;
   - `wilq-content-strategist` and `wilq-gsc-content-doctor` after
     `content_diagnostics.decision_queue` and URL normalization. Fresh
     `wilq-gsc-content-doctor` eval passed on 2026-06-19 after the GSC
     query/page preservation fix:
     `.local-lab/evals/codex-skill/20260619T083631Z/wilq-gsc-content-doctor/result.json`;
   - done for `wilq-ga4-analyst` after GA4 decision queue repair; keep rerunning
     when conversion/cost/read contracts, tracking validation or richer
     landing/source/campaign classifiers are added;
   - done for `wilq-ads-doctor` after campaign table,
     search terms/conversions, budget context, recommendations, impression
     share and blocked-claim matrix; keep rerunning when change history, budget
     apply previews or negative keyword apply contracts are added. Fresh eval
     after impression-share context passed on 2026-06-19;
   - `wilq-localo-operator` after `/api/localo/diagnostics` for
     access/readiness and again after real ranking/GBP/competitor/review facts
     exist. Fresh access-ready blocker eval passed on 2026-06-19:
     `.local-lab/evals/codex-skill/20260619T072709Z/wilq-localo-operator/result.json`;
   - done for `wilq-custom-segments` after
     `ads_diagnostics.custom_segments_read_contract`,
     review-only `custom_segment_payload_preview` and
     `act_prepare_custom_segments_from_search_terms`; keep rerunning when
     Keyword Planner enrichment, forecast/audience-size or targeting/apply
     contracts are added;
   - done for `wilq-ahrefs-gap-finder` as an authority plus organic-competitor
     read workflow after `/api/ahrefs/diagnostics` and scoped context-pack were
     added. Fresh strict eval with 10 competitor-page records passed on
     2026-06-21:
     `.local-lab/evals/codex-skill/20260621T013710Z/wilq-ahrefs-gap-finder/result.json`.
     Rerun after typed content/backlink/organic-keyword/top-page gap records
     exist;
   - `wilq-campaign-builder`, `wilq-demand-gen-operator` and
     `wilq-social-publisher` only after their required read contracts or
     ActionObjects exist.

   Repair means:
   - `SKILL.md` has clean trigger intent, allowed endpoints, evidence
     requirements, blocked claims and output contract;
   - references contain durable domain guidance only, not product bug fixes,
     dedupe rules or dashboard cleanup patches;
   - deterministic smoke validates the API contract;
   - `scripts/codex_skill_eval.sh --skill <skill>` proves Polish output,
     WILQ API usage, evidence IDs, source connectors, ActionObject safety and
     a useful marketer decision for that workflow.

Stop doing, per audit:

- Do not treat `configured`, `ready for refresh`, or `connector_configured=true`
  as marketer insight.
- Do not promote LinkedIn/Facebook/social draft actions in daily flow unless
  the operator explicitly asks for social.
- Do not develop skills ahead of read contracts. Better prompts cannot replace
  missing API evidence.
- Do not load the full context-pack as default skill runtime.
- Do not put product decision repairs, dedupe rules or edge-case classifiers in
  skill references. Move them to typed API/schema/view-model contracts first.
- Do not call Ads Doctor a CPA/ROAS/search-term/wasted-budget optimizer until
  those read contracts exist.

Demo acceptance from the audit:

- First screen shows 3-5 marketer decisions, not system status.
- Every decision has evidence IDs, source connectors, blocked claims, route,
  ActionObject where applicable and a Polish Codex prompt for the matching
  skill.
- Dashboard and the matching skill return the same evidence/action IDs for the
  same marketer question.
- Skills are evaluated for usefulness, not only schema pass:
  Daily, Merchant, GA4, Content/GSC and Ads must each prove a concrete,
  evidence-backed Polish operator answer.

### 0. Preflight Truth

Goal: start from current runtime truth, not chat memory.

Tasks:

- Read `AGENTS.md`, this file, `docs/infra/001.md`,
  `docs/architecture/bdos-class-wilq-operating-system.md`,
  `docs/research/wilq-marketing-source-map.md` and
  `docs/goals/002-system-audit-and-usefulness-goal.md`.
- Check `git status --branch --short`.
- Use the canonical local runtime manager, not hand-rolled detached processes:
  - `scripts/local_stack.sh status`
  - `scripts/local_stack.sh start` if either service is not ready
  - `scripts/local_stack.sh restart` only when a managed WILQ process or stale
    port owner needs to be replaced
- Check API and dashboard routes:
  - `http://127.0.0.1:8000/api/health`
  - `http://127.0.0.1:5173/command-center`
- Measure command-center API latency and payload size.

Pass criteria:

- current blockers are written here,
- no old Ads OAuth blocker is treated as current unless fresh API evidence says
  so,
- no credential value or secret path content is printed.

### 1. Command Center Anti-Slop Cleanup

Goal: first-screen Command Center must be useful to a Polish marketer.

Active slice handoff:

```txt
docs/handoffs/dashboard-audit-active-slice.md
docs/handoffs/command-center-second-opinion-brief.md
```

Keep this file updated while auditing dashboard routes. It contains current
agent-browser proof paths, confirmed broken/outdated surfaces and the next
implementation queue. If context is lost, resume from that handoff before
editing more dashboard code.

Current product correction:

- Stop treating Command Center as a place to display every available metric.
- Command Center must become a decision cockpit for the Polish marketer.
- Each top-level item must explain:
  - `co widzę`,
  - `co to znaczy`,
  - `co zrobić teraz`,
  - `czego nie wolno twierdzić`,
  - `jak Codex może pomóc`.
- Raw metric facts, query/page rows, GA4 landing/source rows and Merchant issue
  rows belong in dedicated diagnostic routes unless condensed into one decision.
- Codex skills are the operating layer: from a Command Center decision, the
  marketer should be able to run a matching WILQ skill that calls WILQ API,
  returns Polish evidence-backed output, prepares safe briefs/drafts/action
  previews, and blocks unsupported claims.
- Skill trigger descriptions must be written for real marketer intent, not for
  internal connector names. Example prompts that must route naturally:
  `pokaż przestrzeń do polepszenia adsów w Ekologus`,
  `znajdź ostatnie kampanie i ich efekty`,
  `które treści odświeżyć najpierw`,
  `czy feed produktowy jest OK`,
  `sprawdź jakość ruchu z GA4`,
  `jak poprawić lokalną widoczność`.
- Command Center action cards must expose the Codex bridge explicitly:
  `skill_id`, Polish `codex_prompt`, `codex_context_endpoint`,
  `expected_codex_output`, evidence IDs, ActionObject IDs and blocked claims.
  Without this bridge, the dashboard is only a data UI and Codex is not an
  operating layer.
- Before broad UI changes continue, use the second-opinion brief to validate
  the information architecture and next slices.

Tasks:

- Audit `/command-center` top-to-bottom with browser proof after the page
  settles. Current proof:
  `.local-lab/proof/dashboard-audit/text/command-center-final-slice.txt`.
- Remove, rewrite or demote readiness-only cards:
  - `connector_configured=true`,
  - `Connector ... ready for ... refresh`,
  - `No performance metrics have been collected`,
  - `Run a read-only refresh`,
  - social/local/connector debug cards that do not create a decision.
- Keep evidence IDs, ActionObjects and blockers, but present them as decisions:
  `co widzę`, `co to znaczy`, `co zrobić teraz`, `czego nie wolno twierdzić`,
  `jak Codex może pomóc`.
- Fix duplicate React keys and any UI warnings observed in browser console.
- Keep dashboard labels in Polish with Polish diacritics.
- Preserve the 2026-06-18 cleanup: `Dzisiejszy panel operatora` is only a
  compact status/header; detailed decision cards live only in
  `Plan działań marketera`.
- Preserve the 2026-06-18 cleanup: Command Center must not show
  `Demo dla marketera`, visible `PRIORITY N`, GA4 `(not set)` tactical cards,
  Localo OAuth probe/debug metric facts, `Freshness: unknown - Credential
  presence only`, `connector_configured`, or `Run a read-only`.
- Preserve the 2026-06-18 Localo correction: Command Center and `/localo` must
  say "access działa, brak ranking/GBP facts", not "dokończ access", after a
  completed Localo MCP initialize proof.
- Preserve the 2026-06-18 brief dedupe: `/api/marketing/brief` and generated
  ActionObjects must show the latest metric fact per
  `(source_connector, metric_name, dimensions)` and must not repeat the same
  aggregate metrics from older refresh runs.
- Preserve the 2026-06-18 brief scope cleanup: `/api/marketing/brief` is a
  marketer decision brief, not a connector inventory. Optional social/missing
  credential items such as LinkedIn/Facebook and disabled Sheets must not show
  as global blockers in `what_blocks_us`; social draft ActionObjects may exist
  in `/api/actions`, but they must not be promoted into brief
  `safe_next_actions` until social becomes an active marketer workflow.
- Preserve the 2026-06-18 skill eval ledger: real skill prompt runs and their
  usefulness findings belong in `docs/evals/skill-eval-ledger.md`; latest
  runtime/progress/performance state belongs in `docs/PROGRESS.md`.
- Preserve the 2026-06-18 context-pack performance finding:
  `/api/codex/context-pack` measured about 9.15s and 940 KB for
  `wilq-content-strategist`, mostly because it embeds broad state including
  hundreds of evidence summaries and multiple diagnostics. The next runtime
  optimization should be skill-scoped context packs, not random frontend
  memoization.
- 2026-06-18 follow-up: `wilq-content-strategist` now receives a skill-scoped
  context-pack by default. Local proof after API restart: full pre-scope pack
  about 8.106s / 940864 bytes; scoped content pack about 2.679s / 154334 bytes.
  Smoke still passes with `content_live=True`, `query_page_count=10`,
  action IDs `act_review_ga4_tracking_quality` and
  `act_prepare_content_refresh_queue`.
- 2026-06-18 follow-up: deterministic smoke suite passed for 12/12 WILQ skills
  after scoped context-pack changes. Summary artifact:
  `.local-lab/evals/skill-smoke-summary-20260618T093210Z.jsonl`. This proves
  API contract health, not final `codex exec` usefulness; non-interactive
  Codex evals are still required.
- 2026-06-18 follow-up: first real non-interactive Codex eval passed for
  `wilq-content-strategist`:
  `.local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, evidence IDs,
  source connectors and `act_prepare_content_refresh_queue` as a safe candidate.
  Remaining quality gap: this eval is still too broad and must evolve to assert
  concrete content decisions (`refresh`, `merge/create-after-inventory-check`,
  `block`) rather than only schema-safe recommendations.
- 2026-06-18 follow-up: second real non-interactive Codex eval passed for
  `wilq-merchant-feed-operator`:
  `.local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  `google_merchant_center` evidence IDs, live Merchant facts
  (`product_count=10900`, `issue_count=15`) and
  `act_review_merchant_feed_issues` as the safe pending-validation review path.
  Remaining quality gap: future Merchant evals should assert issue-level
  clustering and explicit ActionObject validation proof.
- 2026-06-18 follow-up: third real non-interactive Codex eval passed for
  `wilq-ga4-analyst`:
  `.local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  `google_analytics_4` evidence IDs and
  `act_review_ga4_tracking_quality` as the safe pending-validation review path.
  It correctly blocks ROAS/revenue/conversion claims without stronger evidence.
  Remaining quality gap: future GA4 evals should assert ranked
  landing/source/campaign diagnostic items and explicit ActionObject validation
  proof.
- 2026-06-19 follow-up: `wilq-ga4-analyst` now consumes
  `/api/ga4/diagnostics.decision_queue` as the primary decision source. Fresh
  runtime proof after API restart showed `live_data_available=true`,
  `landing_group_count=10`, `decision_count=6` and
  `act_review_ga4_tracking_quality`. Fresh non-interactive Codex eval passed:
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, GA4 evidence IDs,
  `review_traffic_quality` decisions, pending validation for
  `act_review_ga4_tracking_quality`, and blocked ROAS/revenue/conversion/
  attribution/tracking-fixed claims. Remaining gap: no current evidence
  exercises `fix_measurement` or `review_landing_mapping`, and ActionObject
  validation is still pending.
- 2026-06-18 follow-up: fourth real non-interactive Codex eval passed for
  `wilq-gsc-content-doctor`:
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  GSC/WordPress evidence IDs, `content_diagnostics.live_data_available=true`,
  `query_page_count=10`, `matched_inventory_count=0` and
  `act_prepare_content_refresh_queue` as the safe pending-validation content
  queue path. Remaining quality gap: future GSC evals should assert concrete
  query/page candidates with `refresh`, `merge`, `create` or `block` decisions.
- 2026-06-18 follow-up: `wilq-daily-command` was hardened after Command Center
  and brief cleanup. Deterministic smoke now fails if daily context loses core
  ActionObjects or reintroduces social draft actions. Fresh non-interactive
  Codex eval passed:
  `.local-lab/evals/codex-skill/20260618T112920Z/wilq-daily-command/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, 14 evidence IDs, core
  ActionObject candidates only, no safety findings and
  `operator_usefulness_score=5`.
- 2026-06-18 active local slice: `content_diagnostics.decision_queue` moved
  content classification into typed WILQ API. Fresh eval passed at
  `.local-lab/evals/codex-skill/20260618T114810Z/wilq-content-strategist/result.json`.
  It uses API decisions `inventory_check_before_create`,
  `merge_create_after_inventory_check` and `block_as_tracking_not_content`.
  The follow-up route cleanup is documented in `docs/PROGRESS.md`; resume route
  audit on `/ga4`, `/ads-doctor` and `/localo`.
- Performance direction: follow TanStack/React guidance by avoiding client
  waterfalls and duplicated data models. Do not patch this with random
  `useMemo`; next performance slice should build a lightweight daily-decision
  view model or short-lived materialized cache for the first screen.

Pass criteria:

- `agent-browser` or Playwright proof shows no readiness slop on the first
  screen,
- marketer sees concrete daily decisions and tactical work, not connector
  inventory,
- dashboard unit/e2e tests assert the slop is absent.
- `/api/dashboard/command-center` remains materially faster than the previous
  6-7s baseline. Latest proof after parallel diagnostics:
  1.95-2.32s live-server response time.
- Latest proof after Localo + brief cleanup:
  - `http://127.0.0.1:8000/api/dashboard/command-center` returns
    `daily_localo_readiness.status=ready`, title
    `Localo: MCP access działa, brak jeszcze ranking/GBP facts`, and
    `plan_localo_access_ready_wait_for_visibility_facts`.
  - `http://127.0.0.1:8000/api/marketing/brief` has
    `duplicates_found=False` for item-local metric facts.
  - Latest live proof for `/api/marketing/brief` after restart:
    `what_we_know=6`, `what_blocks_us=0`, `safe_next_actions=3`,
    `recommended_focus=2`, duplicate item IDs `0`, duplicate metric facts `0`.
    Core brief actions are only:
    `act_review_merchant_feed_issues`,
    `act_review_ga4_tracking_quality`,
    `act_prepare_content_refresh_queue`.

### 2. Source-To-Product Condensation

Goal: prove that research sources shape WILQ behavior, not only docs.

Tasks:

- Done: Google Ads change-history read chain.
  - Product layer added:
    `/api/ads/diagnostics.change_history_read_contract`.
  - Live evidence:
    `refresh_google_ads_e7f371e9efac` /
    `ev_refresh_refresh_google_ads_e7f371e9efac`.
  - Live result: `change_event_row_count=0` for the last 14 days. This proves
    read access and blocker behavior, not change-impact.
  - API view model: `AdsChangeHistoryReadContract`, `AdsChangeHistoryRow` and
    decision `ads_review_change_history`.
  - Dashboard proof: `/ads-doctor` renders change-history read state and, when
    rows exist, sanitized event rows only.
  - Skill proof: `wilq-ads-doctor` smoke, scoped context-pack and
    non-interactive eval expose the same change-history contract.
  - Safety proof: change impact, performance uplift, budget scaling, budget
    apply and campaign mutation remain blocked.
  - Non-interactive Codex proof:
    `.local-lab/evals/codex-skill/20260619T162014Z/wilq-ads-doctor/result.json`
    has `language=pl-PL`, `api_used=true`, Google Ads evidence IDs and no
    safety findings.
  - Full proof: `scripts/verify.sh` passed with backend API contracts
    `111 passed`, dashboard route tests `13 passed`, Playwright e2e
    `9 passed`, API smoke, skill structure smoke, skill API smoke, security
    checks and dashboard production build passed. Non-blocking warning: Vite
    main JS chunk `540.14 kB`.
- Done: Google Ads impression-share read chain.
  - Product layer added:
    `/api/ads/diagnostics.impression_share_read_contract`.
  - Live evidence:
    `refresh_google_ads_baba7f993f1a` /
    `ev_refresh_refresh_google_ads_baba7f993f1a`.
  - API view model: `AdsImpressionShareReadContract`,
    `AdsImpressionShareRow` and decision `ads_review_impression_share`.
  - Dashboard proof: `/ads-doctor` renders campaign impression-share rows as
    read-only review input.
  - Skill proof: `wilq-ads-doctor` smoke, scoped context-pack and
    non-interactive eval expose the same impression-share contract.
  - Safety proof: budget scaling, budget apply, wasted budget, performance
    uplift and campaign mutation remain blocked.
  - Full proof: `scripts/verify.sh` passed with backend API contracts
    `111 passed`, dashboard route tests `13 passed`, Playwright e2e
    `9 passed`, API smoke, skill structure smoke, skill API smoke, security
    checks and dashboard production build passed. Non-blocking warning: Vite
    main JS chunk `536.68 kB`.
- Done: Google Ads recommendations read
  chain.
  - Product layer added:
    `/api/ads/diagnostics.recommendations_read_contract`.
  - Live evidence:
    `refresh_google_ads_138befce0a2c` /
    `ev_refresh_refresh_google_ads_138befce0a2c`.
  - API view model: `AdsRecommendationsReadContract`,
    `AdsRecommendationRow` and decision `ads_review_recommendations`.
  - Dashboard proof: `/ads-doctor` renders active recommendation types as
    read-only review input.
  - Skill proof: `wilq-ads-doctor` smoke and scoped context-pack expose the
    same recommendations contract.
  - Safety proof: apply, automatic accept, budget mutation and performance
    uplift claims remain blocked.
  - Full proof: `scripts/verify.sh` passed with backend API contracts
    `111 passed`, dashboard route tests `13 passed`, Playwright e2e
    `9 passed`, API smoke, skill structure smoke, skill API smoke, security
    checks and dashboard production build passed. Non-blocking warning: Vite
    main JS chunk `533.57 kB`.
  - Non-interactive Codex proof:
    `.local-lab/evals/codex-skill/20260619T153351Z/wilq-ads-doctor/result.json`
    includes `recommendations_read_contract`, `ads_review_recommendations`,
    `recommendation apply`, Google Ads evidence IDs and no safety findings.
- Done: Google Ads budget review chain.
  - Product layer added: `google_ads_budget_review_playbook`.
  - Compiled knowledge card:
    `card_google_ads_budget_review_playbook`.
  - Expert rules bound to API decisions:
    `ads_scaling_candidates_v1`, `ads_recommendations_v1`,
    `ads_principles_v1`.
  - API view model: `AdsDiagnosticSection` and `AdsDecisionItem` expose
    `knowledge_card_ids` and `expert_rule_ids`.
  - Dashboard proof: `/ads-doctor` renders those trace IDs only when present.
  - Skill context proof: `POST /api/codex/context-pack` for
    `wilq-ads-doctor` preserves the same decision lineage.
  - Safety proof: redaction allowlist preserves `knowledge_card_ids` and
    `expert_rule_ids`, while still redacting secret values.
- Done for this chain: non-interactive `wilq-ads-doctor` Codex eval passed at
  `.local-lab/evals/codex-skill/20260619T144600Z/wilq-ads-doctor/result.json`.
  It proves the Polish answer references the budget review knowledge/rule
  lineage, evidence IDs, prepare-only ActionObjects and blocked budget/apply
  claims.
- Next chains after Ads change history:
  - Ads pre/post change-impact window joined to campaign/search-term facts.
  - Ads Keyword Planner enrichment for search terms and custom segments.
  - GSC/content source-to-decision quality.
  - Localo visibility once ranking/GBP evidence exists.
- Use official docs first, then practitioner/academic sources only where they
  add operating value.

Pass criteria:

- one visible dashboard decision can be traced:
  source -> knowledge/rule -> API -> dashboard -> skill/eval,
- no rule exists only as prompt prose,
- blocked claims are explicit.

### 3. API And Skill Integration Proof

Goal: prove Codex + WILQ API + skills are better than plain Codex.

Tasks:

- Run real `codex exec` or Codex CLI/Desktop prompts against the local WILQ API.
- Use Polish prompts:
  - `Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.`
  - `Co w Ads mogę uczciwie powiedzieć na podstawie obecnego evidence?`
  - `Którą treść odświeżyć albo stworzyć i czego nie wolno obiecywać?`
  - `Czy Merchant ma problem z produktami/feedem i jaki ActionObject sprawdzić?`
  - `Czy Localo daje już ranking/GBP insight czy nadal blocker?`
- Compare plain Codex answer vs WILQ-skill/API answer vs dashboard/API state.

Pass criteria:

- WILQ answer is in Polish,
- WILQ answer uses API or reports blocker,
- WILQ answer includes evidence IDs/source connectors,
- WILQ answer avoids invented metrics,
- WILQ answer gives a safe next action,
- WILQ answer matches dashboard/API for the same claim.

Current eval progress:

- `wilq-daily-command`: strengthened and re-evaluated at
  `.local-lab/evals/codex-skill/20260618T112920Z/wilq-daily-command/result.json`.
  Strong daily pass: Merchant, Content and GA4 core action candidates only;
  Localo/social are not promoted without explicit evidence/workflow.
- `wilq-content-strategist`: passed non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json`.
  Safe, API-backed, but future eval must force concrete
  `refresh`/`merge`/`create`/`block` decisions.
- `wilq-merchant-feed-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json`.
  Strong Merchant pass with `product_count=10900`, `issue_count=15` and
  `act_review_merchant_feed_issues`.
- `wilq-ga4-analyst`: strict decision_queue pass at
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
  The skill uses `/api/ga4/diagnostics.decision_queue`, returns
  `review_traffic_quality` decisions with GA4 evidence IDs, carries
  `act_review_ga4_tracking_quality` as pending validation, and blocks
  ROAS/revenue/conversion/attribution/tracking-fixed claims.
- `wilq-gsc-content-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  Safe GSC/content pass; future eval must force concrete query/page decisions.
- `wilq-ads-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T102132Z/wilq-ads-doctor/result.json`.
  Important correction: Ads is currently live campaign review, not OAuth repair.
  The skill may use campaign and search-term evidence from `google_ads`, plus
  read-only derived KPI rows. It must still block profitability, wasted budget,
  negative keyword apply, budget scaling and recommendation/apply claims until
  WILQ exposes stronger interpretation, safety and apply contracts.
  Fresh strict source-backed lineage eval passed at
  `.local-lab/evals/codex-skill/20260619T144600Z/wilq-ads-doctor/result.json`
  and requires `card_google_ads_budget_review_playbook`,
  `ads_scaling_candidates_v1`, `ads_recommendations_v1` and
  `ads_principles_v1`.
- `wilq-localo-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T102743Z/wilq-localo-operator/result.json`.
  Important correction: Localo is currently access-ready, not missing
  `LOCALO_ACCESS_TOKEN`; however, the skill must still block ranking, GBP,
  competitor and local visibility uplift claims until WILQ exposes Localo facts
  beyond MCP initialize/access readiness.
- `wilq-daily-command`: passed at
  `.local-lab/evals/codex-skill/20260618T103758Z/wilq-daily-command/result.json`.
  This proves the top-level Polish daily loop across Command Center,
  MarketingBrief and context-pack: Merchant first, then Content/GA4/Ads/Localo
  with evidence IDs and safe next actions. Cleanup still needed:
  LinkedIn/Facebook draft ActionObjects can leak into daily action candidates
  from the wider `marketing_brief.action_ids`; daily primary actions should stay
  focused on core marketer decisions unless social is explicitly requested.
- `wilq-campaign-builder`: passed at
  `.local-lab/evals/codex-skill/20260618T104154Z/wilq-campaign-builder/result.json`.
  This is a safety/blocker pass, not campaign creation proof. It confirms
  Ads/GA4/GSC evidence access, then blocks campaign candidate and payload
  preview because WILQ lacks a campaign-specific ActionObject, keyword/asset
  evidence, budget facts and validated campaign payload contract.
- `wilq-custom-segments`: passed at
  `.local-lab/evals/codex-skill/20260618T104644Z/wilq-custom-segments/result.json`.
  This is an anti-hallucination pass. It blocks audience/custom segment
  candidates because WILQ currently has aggregate Ads/GSC facts, but not real
  source terms/search terms/query evidence with lineage.
- `wilq-demand-gen-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T105005Z/wilq-demand-gen-operator/result.json`.
  This is a guardrail pass with low usefulness (`operator_usefulness_score=3`).
  It correctly blocks Demand Gen recommendations because WILQ has aggregate
  Ads/GA4/Merchant readiness only, not asset, creative, landing-quality,
  migration diagnostics or a Demand Gen-specific ActionObject.
- `wilq-ahrefs-gap-finder`: passed at
  `.local-lab/evals/codex-skill/20260618T105335Z/wilq-ahrefs-gap-finder/result.json`.
  This is a guardrail pass with low usefulness (`operator_usefulness_score=3`).
  It correctly blocks backlink/competitor/content gap claims because WILQ has
  aggregate Ahrefs authority metrics plus GSC/WordPress context, but no concrete
  Ahrefs gap records.
- `wilq-social-publisher`: passed at
  `.local-lab/evals/codex-skill/20260618T105649Z/wilq-social-publisher/result.json`.
  This is a strong safety pass. It exposes LinkedIn/Facebook draft ActionObjects
  but blocks publishing and draft claims because social credentials and
  ActionObject validation are missing.

Current eval coverage: 12/12 WILQ skills have recorded non-interactive Codex
evals. GA4 has a fresh strict decision_queue rerun, Ads has multiple strengthened
read-contract reruns, and Ahrefs now has a strict eval with 10 real
competitor-page records plus 4 competitor top-page records proving that
authority plus competitor pages still cannot be promoted into unsupported
content/backlink/ranking/traffic claims:
`.local-lab/evals/codex-skill/20260621T020523Z/wilq-ahrefs-gap-finder/result.json`.
This proves API integration and guardrails, not Goal 001 completion. The next
product work must convert eval findings into fixes: Ahrefs content/backlink/
organic-keyword read contracts, source-term/custom-segment evidence, campaign
ActionObjects, Demand Gen diagnostics and the final plug-and-play Codex
acceptance session.

### 4. Performance Slice

Goal: Command Center must feel usable, not wait ~15 seconds for avoidable work.

Tasks:

- Measure:
  - `/api/dashboard/command-center`,
  - `/api/marketing/tactical-queue`,
  - `/api/metrics?limit=80`,
  - dashboard first meaningful render.
- Identify whether bottleneck is backend joins, payload size, duplicate frontend
  fetches, rendering volume or dev-server overhead.
- Prefer small fixes:
  - remove unused first-screen fetches,
  - lazy-load secondary panels,
  - truncate long evidence lists,
  - cache expensive view-model joins,
  - avoid broad refactors until measured.

Pass criteria:

- before/after timing is recorded here,
- first-screen work is reduced or a precise blocker remains,
- no performance fix removes required evidence/action traceability.

Current slice result:

- Implemented scoped default context-pack for
  `POST /api/codex/context-pack {"skill":"wilq-daily-command"}`.
- Default daily context now includes `command_center`, `marketing_brief`, core
  daily ActionObjects, relevant connector status, relevant evidence summaries,
  knowledge cards, expert rules and expert capabilities.
- Default daily context no longer embeds `tactical_queue`, Ads/Merchant/Content
  or GA4 diagnostics. Full context remains available through
  `{"skill":"wilq-daily-command","full_context":true}`.
- Baseline from the old `:8000` runtime before this slice:
  - command-center: `5.937s`, `30521 bytes`;
  - marketing brief: `1.648s`, `46310 bytes`;
  - daily context-pack: `15.030s`, `996121 bytes`;
  - daily full context-pack: `11.734s`, `996121 bytes`.
- Fresh `:8011` runtime proof after this slice:
  - default daily context-pack: `2.888s`, `160053 bytes`;
  - repeated default daily context-pack: `2.985s`, `160053 bytes`;
  - repeated default daily context-pack: `2.959s`, `160053 bytes`;
  - full daily context-pack: `6.465s`, `998704 bytes`;
  - marketing brief: `0.541s`, `46072 bytes`;
  - command-center: `2.424s`, `30521 bytes`;
  - repeated command-center: `2.094s`, `30521 bytes`;
  - repeated command-center: `2.102s`, `30521 bytes`.
- Metric store read paths now use batch DuckDB reads and read-only DuckDB
  connections when the DB file already exists. This removes the conflicting
  lock failure observed when local profiling and the running `:8000` API read
  `.local-lab/state/wilq.duckdb` at the same time.
- Current follow-up adds a shared `DailyRuntime` for daily Codex context:
  `command_center`, `marketing_brief` and core daily ActionObjects are built
  from one connector/action/refresh snapshot and cached for a short TTL.
  `WILQ_DAILY_RUNTIME_CACHE_SECONDS` controls the TTL, default `30`; tests
  disable the cache. The cache is invalidated after connector refresh and
  action validation/apply paths.
- Fresh helper API proof on `:8011` after this follow-up:
  - default daily context: `3.047s` cold, then `0.467s`, `0.544s`, `0.470s`
    warm within TTL;
  - payload size stayed `160478 bytes`;
  - `/api/dashboard/command-center`: `2.034s`, `2.029s`, `2.396s`;
  - `/api/marketing/brief`: `0.618s`, `0.608s`, `0.588s`.
- Focused proof passed:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run pytest tests/test_api_contracts.py -q -k 'daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or command_center_exposes_polish_operator_brief or daily_context_pack_excludes_social_draft_action_objects or codex_context_pack_contains_no_metric_invention_instruction or codex_context_pack_includes_expert_rule_summaries'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8011
  ```
- Full proof passed:
  ```bash
  scripts/verify.sh
  ```

Completed follow-up on 2026-06-19, pushed as
`35d8be3 perf(api): share daily runtime endpoints`:

- Public dashboard endpoints are being moved onto the same `DailyRuntime`
  cache:
  - `GET /api/dashboard/command-center` ->
    `build_daily_runtime().command_center`;
  - `GET /api/marketing/brief` ->
    `build_daily_runtime().marketing_brief`.
- This is the next real bottleneck after scoping daily Codex context-pack:
  Command Center, Marketing Brief and Codex daily context should share one
  daily view-model in the API process instead of rebuilding overlapping daily
  state through separate endpoint paths.
- Changed files were:
  - `apps/api/wilq_api/main.py`,
  - `tests/test_api_contracts.py`,
  - `docs/CONTEXT.md`,
  - `docs/PROGRESS.md`,
  - `docs/goals/001-goal.md`.
- Added/updated tests:
  - `test_command_center_endpoint_uses_daily_runtime_cache`,
  - `test_marketing_brief_endpoint_uses_daily_runtime_cache`.
- Focused checks passed after adding both endpoint regression tests:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py tests/test_api_contracts.py
  uv run pytest tests/test_api_contracts.py -q -k 'command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache or daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or marketing_brief_aggregates_metric_facts_and_blockers'
  ```
- Result: ruff passed, mypy passed, pytest 5 selected tests passed.
- Broader route/API proof also passed:
  ```bash
  uv run pytest tests/test_api_contracts.py -q -k 'command_center or marketing_brief or daily_runtime or context_pack'
  pnpm --filter @wilq/dashboard typecheck
  pnpm --filter @wilq/dashboard test -- --run App.test.tsx
  ```
- Result: backend selected tests 17 passed, dashboard typecheck passed,
  dashboard route tests 13 passed.
- Full proof passed:
  ```bash
  scripts/verify.sh
  ```
- Result: backend API contracts 102 passed, dashboard route tests 13 passed,
  Playwright e2e 9 passed, skill API smoke passed and dashboard production
  build passed.
- Non-blocking warning: Vite reports the main JS chunk is above 500 KB. This is
  now a known future performance issue, not a blocker for this API runtime
  slice.

Completed follow-up on 2026-06-22, pushed as current performance cache slice:

- `/api/marketing/tactical-queue` now has a short TTL cache controlled by
  `WILQ_TACTICAL_QUEUE_CACHE_SECONDS`, default `30s`, disabled under pytest.
  The tactical queue is read-only view-model state over metric facts and
  ActionObjects, so it can share the same short-lived runtime behavior as
  `DailyRuntime` while preserving evidence/action traceability.
- API mutation/readiness paths now call one `clear_api_view_model_caches()`
  helper after connector refresh and ActionObject
  validate/review/preview/confirm/impact/apply operations. This invalidates
  tactical queue, daily runtime and skill context caches together.
- Measured live proof after `scripts/local_stack.sh restart`:
  - before this slice, `/api/marketing/tactical-queue` median was about
    `1.198s`, payload `35262 bytes`;
  - after this slice, `/api/marketing/tactical-queue` median is `0.006s`,
    payload `35262 bytes`;
  - `/api/dashboard/command-center` warm median remains `0.007s`;
  - `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` warm median
    remains `0.152s`;
  - full debug context remains intentionally heavy at about `6.263s` and
    `6.19 MB`, so it must stay debug-only rather than default runtime.
- Browser proof through `agent-browser` opened
  `http://127.0.0.1:5173/command-center` and showed the four current primary
  daily decisions plus `Źródła i ograniczenia`.
- Verification:
  - focused ruff/mypy/backend/dashboard tests passed;
  - `scripts/verify.sh` passed with backend API contracts `154 passed`,
    dashboard unit tests `17 passed`, Skill/API smokes, Playwright e2e
    `14 passed` and dashboard production build.

Remaining blocker:

- Warm daily runtime is now acceptable for the local demo path, but cold runtime
  and debug/full-context payloads are not done. Remaining performance work is
  bundle/code-splitting risk, cold diagnostic construction for non-daily routes,
  and keeping future value contracts from reintroducing broad registry fetches
  into first-screen marketer routes. Do not hide this in skill references.

### 5. Code Quality and Maintainability Slice

Goal: keep WILQ shippable as it grows into a BDOS-class operator system. The
current product works, but several files are too large to remain healthy
long-term. Current known hotspots after the latest dashboard extraction:
`apps/dashboard/src/routes/App.tsx` is still about 7180 lines,
`apps/dashboard/src/routes/App.test.tsx` about 6149 lines,
`wilq/briefing/ads_diagnostics.py` about 5876 lines,
`wilq/actions/service.py` about 2076 lines and
`packages/shared-schemas/src/index.ts` about 1918 lines. These are acceptable
as temporary consolidation during fast product discovery, not as the target
architecture.

This slice must be treated as product-risk reduction, not cosmetic cleanup.
Assume there are more hotspots until a repo-wide hotspot pass proves otherwise.
Use subagents for hotspot mapping, disjoint implementation slices and focused
review/test triage whenever that materially speeds development.

Rules:

- Do not start with a broad rewrite.
- First map real ownership boundaries from the current code:
  - dashboard route shells,
  - route-specific panels,
  - shared cards/chips,
  - API client hooks,
  - Ads diagnostic contracts,
  - ActionObject lifecycle services,
  - shared schema modules.
- Split only along existing API/product boundaries. A component/module split is
  good only if it makes dashboard/API/Codex behavior easier to verify.
- Every extraction must keep public API contracts and rendered marketer behavior
  unchanged unless the active slice explicitly changes product behavior.
- Keep tests close to behavior: move test helpers/fixtures only when they reduce
  duplication or make route-specific expectations clearer.
- Do not hide complexity in generic abstractions. Prefer concrete modules like
  `AdsDoctorRoute`, `CommandCenterDecisionCard`, `MerchantDiagnosticsPanel`,
  `build_ads_business_context_contract` over frameworky indirection.

Initial target slices:

1. Dashboard file map and route extraction:
   - split `App.tsx` into route-level components and shared marketer cards,
   - keep TanStack Router/TanStack Query behavior unchanged,
   - prove with dashboard unit tests and Playwright e2e.
   - 2026-06-22 first safe extraction completed:
     `CommandCenter` moved to `apps/dashboard/src/routes/CommandCenterRoute.tsx`;
     shared `priorityLabel` and blocked-claim labels moved to
     `apps/dashboard/src/routes/marketingLabels.ts`; narrow proof:
     dashboard lint OK, dashboard typecheck OK, `App.test.tsx` 17/17 OK.
     Final proof: `scripts/verify.sh` OK, including backend API contracts
     154/154, dashboard unit tests 17/17, Playwright 14/14 and dashboard
     production build.
   - 2026-06-22 workflow panel extraction completed:
     `WorkflowRunList` and `WorkflowRegistryList` moved to
     `apps/dashboard/src/routes/WorkflowPanels.tsx`; `WorkflowsSurface` keeps
     the same routing/query behavior in `App.tsx`. Final proof:
     `scripts/verify.sh` OK, including backend API contracts 154/154,
     dashboard unit tests 17/17, Playwright 14/14 and dashboard production
     build.
2. Dashboard test split:
   - move route groups out of one huge `App.test.tsx` into route-focused test
     files,
   - keep the same smoke coverage: Command Center, Ads Doctor, Merchant, GA4,
     SEO/GSC, Localo, Ahrefs, Actions, Workflows, Knowledge.
   - 2026-06-22 first safe split completed:
     `CommandCenterRoute.test.tsx` now owns the Command Center first-screen
     assertions for Polish daily decisions, Codex prompt bridge, hidden raw
     `ev_*`/`act_*` IDs and translated blocked claims. `App.test.tsx` now has
     16 tests and the new route test has 1 test, preserving 17 dashboard unit
     tests total. Final proof: `scripts/verify.sh` OK, including backend API
     contracts 154/154, dashboard unit tests 17/17 across 2 files, Playwright
     14/14 and dashboard production build.
3. Ads diagnostics service split:
   - split `ads_diagnostics.py` by read contracts: campaign, derived KPI,
     budget, recommendations, change history, search terms, business context,
     custom segments,
   - keep one public builder response.
4. Action service split:
   - separate registry/listing, review, preview, confirm, impact-check, apply
     and mutation audit helpers.
5. Shared schema packaging:
   - split generated/shared schema exports only if imports stay stable for the
     dashboard and tests.

Pass criteria:

- Before/after file-size and module map are recorded in `docs/PROGRESS.md`.
- No route, endpoint, skill context-pack or ActionObject behavior regresses.
- `scripts/verify.sh` passes after each extraction slice.
- Dashboard screenshots or Playwright checks prove the marketer-visible routes
  still render.
- The slice reduces cognitive load without weakening evidence IDs, ActionObject
  IDs, source connector traceability, blocked claims or Polish operator copy.

Completed 2026-06-19 follow-up, pushed as
`ad17223 perf(api): slim command center runtime`:

- `build_command_center_response()` and `build_command_center_brief()` now
  accept preloaded `tactical_queue` and `actions`, so DailyRuntime can build
  Command Center without refetching action/tactical state.
- Command Center no longer builds full Content Diagnostics, GA4 Diagnostics and
  Merchant Diagnostics just to render first-screen daily cards. Content and GA4
  summaries are derived from the already-built tactical queue; Merchant summary
  reads `google_merchant_center` metric facts directly and keeps full issue
  clustering on `/merchant`.
- Measured before this follow-up from local direct profiling:
  - `build_command_center_response()`: about `4.896s`;
  - `build_daily_runtime()`: about `6.600s`;
  - after removing Content/GA4 duplicate diagnostics:
    `build_command_center_response()` about `2.7-2.8s`;
  - after replacing Merchant Diagnostics in Command Center:
    `build_command_center_response()` about `1.685-2.073s`,
    `build_daily_runtime()` about `2.053-2.104s`.
- HTTP proof on fresh `:8016` after this follow-up:
  - cold `GET /api/dashboard/command-center`: `2.526s`, `26629 bytes`;
  - warm repeated Command Center within TTL: `0.011-0.012s`;
  - `POST /api/codex/context-pack {"skill":"wilq-daily-command"}`:
    `0.882-0.934s` while warm, `3.451s` after TTL expiry, `171000 bytes`.
- Full `scripts/verify.sh` passed after this follow-up:
  - backend API contracts: `103 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill API smoke and dashboard production build passed.
- This is useful progress, not final performance completion. The next
  bottleneck is the daily context-pack after cache expiry and any remaining
  route-level render cost in the dashboard. Keep evidence IDs, ActionObject IDs
  and blocked claims intact when optimizing.

Active 2026-06-19 follow-up:

- Daily Codex context-pack now reuses `DailyRuntime.refresh_runs` instead of
  calling `list_connector_refresh_runs()` again.
- Daily Codex context-pack now uses targeted `list_evidence_by_ids()` instead
  of scanning the full evidence registry. Metric-fact evidence can be fetched
  directly by evidence ID through DuckDB.
- Follow-up 2026-06-19 21:13 Europe/Warsaw reduces the shared daily cold path
  further without changing external API contracts:
  - `build_daily_runtime()` builds independent daily inputs in parallel;
  - Command Center passes preloaded ActionObjects into
    `build_ads_diagnostics(actions=...)` instead of reseeding action state;
  - Marketing Brief reads 200 latest metric groups per connector instead of
    500. Live checks confirmed this still preserves dimensional Merchant issue,
    GA4 landing/source, GSC query/page, WordPress and Ads facts.
- Follow-up 2026-06-19 21:32 Europe/Warsaw reduces default daily
  `wilq-daily-command` context-pack payload:
  - compacted active ActionObjects keep IDs, status, risk, evidence IDs,
    diagnosis/reason and full endpoint template, but drop heavy metrics/payload
    rows from the default packet;
  - embedded Command Center keeps `operator_brief`, `action_plan`,
    `daily_decisions` and primary counts, but omits duplicated
    `connector_health`;
  - embedded Marketing Brief caps item metric facts to 3 compact examples and
    top metric facts to 8 compact examples;
  - full data remains available via `full_context=true`,
    `/api/marketing/brief`, `/api/dashboard/command-center` and
    `/api/actions/{action_id}`;
  - Localo remains available in connector context, but is not required as a
    daily source connector until WILQ has Localo ranking/GBP evidence.
- Follow-up 2026-06-19 21:44 Europe/Warsaw resolves the current Vite main
  chunk warning by splitting dashboard vendor bundles:
  - no `chunkSizeWarningLimit` bypass was added;
  - Rollup manual chunks split React, TanStack, icons, schemas and misc vendor
    code;
  - current build chunks are app `142.44 kB`, `vendor-react` `192.70 kB`,
    `vendor-tanstack` `126.96 kB`, `vendor-schemas` `76.67 kB`,
    `vendor-icons` `7.91 kB`, `vendor-misc` `2.16 kB`.
- Focused proof passed:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/evidence/registry.py wilq/storage/metric_store.py wilq/briefing/daily_runtime.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/evidence/registry.py wilq/storage/metric_store.py wilq/briefing/daily_runtime.py
  uv run pytest tests/test_api_contracts.py -q -k 'codex_context_pack_embeds_marketing_brief_contract or list_evidence_by_ids_returns_metric_fact_evidence_without_full_scan or daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_includes_compiled_knowledge_cards or daily_context_pack_excludes_social_draft_action_objects or command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
  ```
- HTTP proof on local `:8000` after this follow-up:
  - earlier daily context follow-up:
    `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` cold after
    TTL `2.548s`, warm `0.273s` and `0.324s`;
  - after the 21:13 follow-up and `scripts/local_stack.sh restart`:
    `GET /api/dashboard/command-center` after TTL `1.448s`, `1.466s`,
    `1.505s` at `27575 bytes`;
  - `GET /api/marketing/brief` after TTL `1.423s`, `1.503s`, `1.476s` at
    `71215 bytes`;
  - daily `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` after
    TTL `1.671s`, `1.764s`, `1.707s` at `235159 bytes`;
  - after the 21:32 context-pack payload compaction:
    default daily context-pack `120436 bytes`;
  - warm cache hits remain millisecond-level.
- Full `scripts/verify.sh` passed after this follow-up:
  - backend API contracts: `106 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.
- Full `scripts/verify.sh` passed after the 21:13 follow-up:
  - backend API contracts: `112 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.
- Non-interactive `wilq-daily-command` eval passed after the 21:32 payload
  compaction:
  `.local-lab/evals/codex-skill/20260619T193056Z/wilq-daily-command/result.json`.
  Result has `language=pl-PL`, `api_used=true`, 19 evidence IDs and source
  connectors for Merchant, GSC, WordPress, GA4, Ads and Ahrefs.
- Full `scripts/verify.sh` passed after the 21:32 payload compaction:
  - backend API contracts: `112 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.
- Focused dashboard proof passed after the 21:44 bundle split:
  - `pnpm --filter @wilq/dashboard typecheck`;
  - `pnpm --filter @wilq/dashboard test -- --run App.test.tsx` -> `13 passed`;
  - `WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1` -> `8 passed`;
  - `pnpm --filter @wilq/dashboard build` -> no >500 KB chunk warning.
- Full `scripts/verify.sh` passed after the 21:44 bundle split:
  - API smoke passed;
  - skill structure smoke passed;
  - skill API smoke passed;
  - Playwright dashboard suite `9 passed`;
  - production dashboard build passed with no >500 KB chunk warning.
- This improves the known daily context-pack TTL spike and shared daily cold
  path, compacts daily context payload and removes the current dashboard chunk
  warning. Remaining future work: richer value contracts rather than hidden
  frontend-only memoization.
- Active Ads skill performance follow-up:
  - scoped `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` now
    removes nested `*_metric_facts` from the skill packet, strips duplicated
    nested candidate payload previews, trims ActionObject row arrays while
    preserving totals in `context_pack_compaction`, and points to
    `/api/ads/diagnostics` plus `/api/actions/{action_id}` for full detail;
  - the API uses a short 5s skill context cache only as a compute shortcut for
    repeated identical skill calls. It is disabled in pytest and cleared after
    connector refresh, ActionObject validation and apply;
  - local proof on `:8000`: Ads context-pack `198513 bytes`, cold
    `1.281-1.620s`, warm `0.145-0.159s`, `search_term_rows_total=50`,
    `search_term_rows_included=8`,
    `search_term_safety_rows_included=8`,
    `keyword_match_context_rows_included=8`,
    `negative_keyword_candidates_included=4`, no `*_metric_facts` keys in
    scoped Ads diagnostics payload;
  - this satisfies the immediate non-daily Ads context-pack size target, but
    does not complete full performance work. Remaining: Command Center cold
    path, content/GA4 context packs, dashboard JS chunk and richer value
    contracts.
- Active Command Center GA4 correction:
  - live `/api/ga4/diagnostics` had GA4 dimensional facts, but Command Center
    could still show `landing groups=0` because it only counted GA4 tactical
    items;
  - Command Center now uses a lightweight GA4 `MetricFact` fallback for unique
    `landing_page` / `source_medium` / `campaign_name` groups;
  - GA4 remains `blocked`, because WILQ still lacks the interpretation
    contracts for ROAS/revenue/conversion drop/tracking fixed claims;
  - live proof on `:8000`: title
    `GA4: brak pełnego kontraktu interpretacji ruchu`, metric tiles
    `landing groups=10`, `low engagement=0`, `WP match=0`, `blockery=1`,
    evidence `ev_refresh_refresh_google_analytics_4_681b6bcefc85`, action
    `act_review_ga4_tracking_quality`;
  - daily Codex context-pack now returns the same GA4 decision as the
    dashboard.

Current hook-runtime fix:

- The Stop hook must never print plain text on stdout when Codex expects Stop
  hook JSON. The observed failure was:
  `Stop hook (failed): hook returned invalid stop hook JSON output`.
- `.codex/hooks/stop_log.py` now emits valid JSON with `continue=true` when it
  skips run logging because WILQ API is unreachable or because the configured
  API URL is unsupported. This keeps WILQ API unreachable as context, not as a
  hook failure.
- `.codex/hooks.json` must use `uv run python` from repo root, not global
  `python3`.
- Regression proof must cover unreachable local API and parse stdout as JSON.
- Full `scripts/verify.sh` passed after the hook fix:
  - backend API contracts: `105 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill smokes and dashboard production build passed.

### 5. Verification And Commit

Goal: finish with proof, not vibes.

Required focused checks after touched surfaces:

```bash
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run pytest tests/test_api_contracts.py -q
```

Required full gate:

```bash
scripts/verify.sh
```

Commit rules:

- Conventional Commits only.
- Do not commit `.env`, `.local-lab`, traces, screenshots, secrets or protected
  client data.
- Update this goal before commit with:
  - completed step,
  - proof commands,
  - remaining blockers,
  - next step.

## Immediate Next Tasks

1. **Preserve the cleaned marketer routes and move to value contracts.**
   Command Center, `/merchant`, `/content-planner`, `/ga4`, `/ads-doctor`,
   `/localo`, `/actions` and `/opportunities` have current decision-first
   cleanup proof. Do not restart those audits unless browser proof shows a
   regression. Search-term review summary now exists as a typed contract; next
   Ads product work should move beyond review ordering into missing value
   contracts: approved live Keyword Planner access/enrichment, live forecast/
   audience-size data, custom segment apply/audit contracts and remaining
   campaign optimization contracts.
   Demand Gen readiness now has review-only
   `act_review_demand_gen_readiness` plus available empty-read contracts for
   `demand_gen_ad_group_ad_rows`, `demand_gen_creative_asset_rows`,
   `demand_gen_landing_quality_by_campaign` and
   `demand_gen_migration_constraints`; do not count that as launch/migration
   readiness. Custom segments now have typed
   `audience_forecast_read_contract` blocker rows, but no live forecast/
   audience-size data and no apply support. Ads
   target-aware KPI triage is started, but remains review-only. Campaign
   ActionObjects are now partially started via
   `act_prepare_ads_campaign_review_queue`; do not treat that as budget
   optimization or apply support. Ads Doctor now has typed
   `/api/ads/diagnostics.operator_summary` for top decisions, summary copy,
   campaign/search-term counts, allowed metrics, missing read contracts,
   review gates, evidence IDs, ActionObject IDs and blocked claims. Localo,
   Ahrefs, Merchant, GA4 and content
   routes now have typed `/api/localo/diagnostics.operator_summary`,
   `/api/ahrefs/diagnostics.operator_summary`,
   `/api/merchant/diagnostics.operator_summary`,
   `/api/ga4/diagnostics.operator_summary` and
   `/api/content/diagnostics.operator_summary`, so do not move top-decision
   ordering/counts/labels back into React; next Localo/Ahrefs/Merchant/GA4/
   content work should add new API facts or contracts, not UI-side recomputation.
   Tactical queue compact grouping is now also API-owned through
   `/api/marketing/tactical-queue.compact_groups`; do not reintroduce query/page
   or feed issue grouping, summed metrics, compact titles or compact diagnoses
   in React.

2. **Continue the measured Command Center performance work.**
   First backend split is done: `/api/dashboard/command-center` now uses
   `build_daily_command_center()` and does not build the full Marketing Brief on
   that endpoint path; `/api/marketing/brief` uses
   `build_daily_marketing_brief()`, and shared base inputs are cached
   separately. Focused proof includes a test that Command Center does not call
   `build_marketing_brief`. Next performance bottleneck is deeper in cold
   Command Center internals: Ads/content/merchant/GA4 diagnostics and
   metric-store reads. Do not hide this with arbitrary frontend loading copy;
   profile the next cold path and move repeated source reads into typed shared
   read bundles/view-models. After backend cold path improves, consider
   route-level code splitting for dashboard app code.

3. **Keep supporting registries out of first-screen decision flow.**
   `/actions` is now ActionObject review, and `/opportunities` is now a
   supporting registry. Do not reintroduce them as duplicated Command Center
   decision queues unless a typed API model adds a new, useful marketer
   decision.

4. **Improve route usefulness, not just wording.**
   For every route cleanup, prefer typed API/view-model changes over copy-only
   patches. If a card has only connector readiness, convert it into a real
   decision, honest blocker, ActionObject validation path or remove it from the
   marketer route.

5. **Use a verification budget, not test loops.**
   Do not run every check after every small edit. For route/component-only
   slices, use this as a menu, not a mandatory sequence:
   ```bash
   pnpm --filter @wilq/dashboard lint
   pnpm --filter @wilq/dashboard typecheck
   pnpm --filter @wilq/dashboard test -- --run App.test.tsx
   ```
   Pick the cheapest command that proves the changed boundary. Use focused e2e
   only for UI behavior or route-load risk. Use Python ruff/mypy/pytest only
   when Python/API/schema files changed. Do not run full `scripts/verify.sh`
   repeatedly during exploratory implementation.

6. **Run full verification only at real gates.**
   Required before push/main handoff or after a broad cross-surface change:
   ```bash
   scripts/verify.sh
   ```
   If a tiny refactor is still inside an uncommitted batch, keep working and
   pay this cost once for the whole slice.

6. **Use subagents to reduce wall-clock time.**
   For non-trivial work, delegate independent work in parallel:
   - `repo-explorer`/`architect` for hotspot maps and boundaries,
   - `implementation-worker` for disjoint files,
   - `test-runner` or `performance-profiler` for focused failures and slow
     gates,
   - `browser-qa` for route proof,
   - `reviewer` for owner-style review before broad commits.
   Keep ownership explicit and do not let subagents edit overlapping files
   without coordination.

7. **Run stricter Codex/API proof for the next high-value gap.**
   Use `codex exec` or Codex Desktop/CLI against the local WILQ API. Plain
   static prompt evaluation is not enough. The proof must show API use, Polish
   output, evidence IDs, source connectors, blocked claims and safe next actions.
   GA4 now has a strict decision_queue rerun. Continue with Localo after real
   visibility facts, or Ahrefs/custom-segments/campaign-builder after their API
   read/action contracts exist.

7. **Commit semantically and push.**
   Use Conventional Commits only. Do not commit `.env`, `.local-lab`, test
   traces or secrets.

8. **Run plug-and-play Codex acceptance session.**
   Add only the final result and any active blockers back into this file.

## Latest Focused Verification

Passed after the 2026-06-23 tactical queue compact groups API slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k marketing_tactical_queue_uses_dimensioned_metric_facts
uv run ruff check wilq/schemas.py wilq/briefing/tactical_queue.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/tactical_queue.py
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard test -- --run App.test.tsx -t "ga4 and gsc routes render workflow-specific brief focus"
scripts/local_stack.sh restart
uv run python - <<'PY'
import httpx
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60.0) as client:
    data = client.get("/api/marketing/tactical-queue").json()
print({
    "item_count": len(data["items"]),
    "compact_group_count": len(data["compact_groups"]),
    "first_group": data["compact_groups"][0] if data["compact_groups"] else None,
})
PY
```

Live proof:

- raw `item_count=10`;
- API-owned `compact_group_count=4`;
- first compact group is the Zielony Ład cluster:
  `SEO: zweryfikuj treść /europejski-zielony-lad-co-to-takiego/ (7 zapytań)`;
- compact diagnosis sums visible evidence-backed metrics:
  `clicks=123`, `impressions=2902`;
- evidence and ActionObject trace:
  `ev_refresh_refresh_google_search_console_554550c44ec7`,
  `act_prepare_content_refresh_queue`;
- `TacticalQueuePanel` compact mode now renders `compact_groups` instead of
  owning grouping/copy logic in React.

Full `scripts/verify.sh` intentionally not run for this narrow API/dashboard
contract slice; run it at the next broader release gate.

Passed after the 2026-06-23 daily runtime split performance slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k "daily_runtime or daily_command_center or command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache"
uv run ruff check wilq/briefing/daily_runtime.py apps/api/wilq_api/main.py tests/test_api_contracts.py
uv run mypy wilq/briefing/daily_runtime.py apps/api/wilq_api/main.py
scripts/local_stack.sh restart
uv run python - <<'PY'
from time import perf_counter
import httpx
paths = [
    "/api/dashboard/command-center",
    "/api/dashboard/command-center",
    "/api/marketing/brief",
    "/api/marketing/brief",
]
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60.0) as client:
    for path in paths:
        start = perf_counter()
        response = client.get(path)
        elapsed = perf_counter() - start
        print(f"{path} status={response.status_code} seconds={elapsed:.4f}")
PY
```

Proof:

- `build_daily_command_center()` has a focused test proving it does not call
  `build_marketing_brief`;
- `/api/dashboard/command-center` endpoint now calls `build_daily_command_center()`;
- `/api/marketing/brief` endpoint now calls `build_daily_marketing_brief()`;
- compatibility `build_daily_runtime()` still returns both objects for surfaces
  that need both;
- HTTP timing after restart: first process-warm Command Center hit remained
  expensive, warm Command Center hit was about `0.0076s`, first Marketing Brief
  after Command Center was about `0.3518s`, warm Marketing Brief was about
  `0.0086s`;
- next performance work should profile Command Center internals, not re-add
  duplicate brief construction.

Full `scripts/verify.sh` intentionally not run for this narrow performance
contract slice; run it at the next broader release gate.

Passed after the 2026-06-23 Ads operator summary view-model slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k ads_diagnostics_exposes_live_campaign_metric_facts
uv run ruff check wilq/schemas.py wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/ads_diagnostics.py
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx -t "ads doctor route renders live metric-backed diagnostics"
pnpm --filter @wilq/dashboard lint
scripts/local_stack.sh restart
curl -sS http://127.0.0.1:8000/api/ads/diagnostics | jq '{operator_summary, decision_count:(.decision_queue|length), blocker_count, live_data_available}'
```

Live proof:

- `operator_summary.id=ads_operator_summary`;
- `campaign_count=18`;
- `search_term_count=50`;
- `ready_area_count=5`;
- `blocked_area_count=3`;
- `decision_count=14`;
- `blocker_count=2`;
- `live_data_available=true`;
- top Ads decision IDs, allowed metrics, missing read contracts, review gates,
  evidence IDs, ActionObject IDs and blocked claims now come from WILQ API
  summary, not React-side sorting/text ownership.

Full `scripts/verify.sh` intentionally not run for this narrow API/dashboard
contract slice; run it at the next broader release gate.

Passed after the 2026-06-23 Localo operator summary view-model slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k localo_diagnostics_shows_access_ready_without_visibility_claims
uv run ruff check wilq/schemas.py wilq/briefing/localo_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/localo_diagnostics.py
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx -t "localo social and content routes render workflow-specific blockers or focus"
pnpm --filter @wilq/dashboard lint
uv run pytest tests/test_api_contracts.py -q -k localo_diagnostics
scripts/local_stack.sh restart
curl -sS http://127.0.0.1:8000/api/localo/diagnostics | jq '{operator_summary, decision_count:(.decision_queue|length), visibility_fact_count, blocker_count}'
```

Live proof:

- `operator_summary.id=localo_operator_summary`;
- `decision_count=2`;
- `visibility_fact_count=17`;
- `blocker_count=1`;
- `access_status=access_ready`;
- `action_ids=["act_review_localo_visibility_facts"]`;
- blocked GBP/competitor/local-task claims now come from WILQ API summary, not
  React-side sorting/text ownership.

Full `scripts/verify.sh` intentionally not run for this narrow API/dashboard
contract slice; run it at the next broader release gate.

Passed after the 2026-06-23 Ahrefs operator summary view-model slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k ahrefs_diagnostics_exposes_authority_context_and_blocks_gap_claims
uv run ruff check wilq/schemas.py wilq/briefing/ahrefs_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/ahrefs_diagnostics.py
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx -t "ahrefs route renders authority context and typed gap records"
pnpm --filter @wilq/dashboard lint
uv run pytest tests/test_api_contracts.py -q -k ahrefs_diagnostics
scripts/local_stack.sh restart
curl -sS http://127.0.0.1:8000/api/ahrefs/diagnostics | jq '{operator_summary, decision_count:(.decision_queue|length), blocker_count}'
```

Live proof:

- `operator_summary.id=ahrefs_operator_summary`;
- `decision_count=2`;
- `blocker_count=2`;
- `gap_read_status=blocked`;
- missing Ahrefs gap read contracts and blocked gap/traffic/authority claims are
  carried by the WILQ API summary.

Full `scripts/verify.sh` intentionally not run for this narrow API/dashboard
contract slice; run it at the next broader release gate.

Passed after the 2026-06-23 Merchant operator summary view-model slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k merchant_diagnostics_exposes_feed_issue_queue
uv run ruff check wilq/schemas.py wilq/briefing/merchant_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/merchant_diagnostics.py
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx -t "merchant route renders dedicated feed diagnostics"
pnpm --filter @wilq/dashboard lint
uv run pytest tests/test_api_contracts.py -q -k merchant_diagnostics
scripts/local_stack.sh restart
curl -sS http://127.0.0.1:8000/api/merchant/diagnostics | jq '{operator_summary, decision_count:(.decision_queue|length), issue_cluster_count:(.issue_clusters|length), blocker_count}'
```

Live proof:

- `operator_summary.id=merchant_operator_summary`;
- `decision_count=8`;
- `issue_cluster_count=11`;
- `reported_issue_occurrences=1887`;
- `action_ids=["act_review_merchant_feed_issues"]`;
- top Merchant decisions, issue clusters, issue types, reported issue count and
  blocked claims now come from WILQ API, not React-side sorting/counting.

Full `scripts/verify.sh` intentionally not run for this narrow API/dashboard
contract slice; run it at the next broader release gate.

Passed after the 2026-06-22 Content operator summary view-model slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k content_diagnostics_exposes_query_page_inventory_queue
uv run ruff check wilq/schemas.py wilq/briefing/content_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/content_diagnostics.py
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx -t "localo social and content routes render workflow-specific blockers or focus"
pnpm --filter @wilq/dashboard lint
uv run pytest tests/test_api_contracts.py -q -k content_diagnostics
scripts/local_stack.sh restart
curl -sS http://127.0.0.1:8000/api/content/diagnostics | jq '{operator_summary, decision_count:(.decision_queue|length), blocker_count}'
```

Live proof:

- `operator_summary.id=content_operator_summary`;
- `decision_count=5`;
- `blocker_count=0`;
- `action_ids=["act_prepare_content_refresh_queue"]`;
- top content decisions, WordPress counts, decision labels and blocked claims now
  come from WILQ API, not React-side sorting/counting.

Full `scripts/verify.sh` intentionally not run for this narrow API/dashboard
contract slice; run it at the next broader release gate.

Passed after the 2026-06-22 GA4 operator summary view-model slice:

```bash
uv run pytest tests/test_api_contracts.py -q -k ga4_diagnostics_exposes_landing_quality_contract
uv run ruff check wilq/schemas.py wilq/briefing/ga4_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/ga4_diagnostics.py
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx -t "ga4 and gsc routes render workflow-specific brief focus"
pnpm --filter @wilq/dashboard lint
uv run pytest tests/test_api_contracts.py -q -k ga4
scripts/local_stack.sh restart
curl -sS http://127.0.0.1:8000/api/ga4/diagnostics | jq '{operator_summary, decision_count:(.decision_queue|length), blocker_count}'
```

Live proof:

- `operator_summary.id=ga4_operator_summary`;
- `decision_count=6`;
- `blocker_count=1`;
- `conversion_readiness_status=blocked`;
- `action_ids=["act_review_ga4_tracking_quality"]`;
- top GA4 decisions and measurement/WP counts now come from WILQ API, not
  React-side sorting/counting.

Full `scripts/verify.sh` intentionally not run for this narrow API/dashboard
contract slice; run it at the next broader release gate.

Passed after the 2026-06-22 Custom Segments audience forecast readiness slice:

```bash
uv run ruff check wilq/schemas.py wilq/briefing/ads_diagnostics.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/ads_diagnostics.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py -q -k 'custom_segments or codex_context_pack_scopes_custom_segments_payload'
uv run pytest tests/test_api_contracts.py -q -k 'live_campaign_metric_facts or custom_segment_review_reason or custom_segment_source_quality or codex_context_pack_scopes_custom_segments_payload'
uv run pytest tests/test_codex_skill_eval_cases.py -q
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run python .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-custom-segments --api-base http://127.0.0.1:8000
scripts/verify.sh
```

Live `:8000` proof after `scripts/local_stack.sh restart`:

- `/api/ads/diagnostics.custom_segments_read_contract.status=ready`;
- `candidate_count=1`, `payload_preview_count=1`;
- remaining missing contracts:
  `keyword_planner_enrichment`, `forecast_or_audience_size`;
- nested
  `custom_segments_read_contract.audience_forecast_read_contract.status=blocked`;
- `checked_candidate_count=1`, `forecast_row_count=1`;
- forecast row has `status=missing_forecast`,
  `forecast_available=false`, `audience_size=null`, source terms and evidence
  IDs from Google Ads;
- decision `ads_prepare_custom_segments_from_search_terms` carries
  `custom_segment_audience_forecast_rows`;
- `/custom-segments` and Ads Doctor render the forecast/audience-size blocker;
- non-interactive `wilq-custom-segments` eval passed:
  `.local-lab/evals/codex-skill/20260621T221018Z/wilq-custom-segments/result.json`
  with `operator_usefulness_score=4`, `api_used=true`, Polish output,
  `act_prepare_custom_segments_from_search_terms`, and a blocked action
  candidate for `audience_forecast_read_contract.status=blocked`;
- full `scripts/verify.sh` passed:
  - backend API contracts `149 passed`;
  - dashboard route tests `17 passed`;
  - Playwright e2e `14 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.

Still blocked:

- live Keyword Planner approval/enrichment in current Ads data;
- live forecast/audience-size data;
- custom segment apply confirmation and mutation audit;
- audience-size, conversion-uplift, ROAS, targeting-applied and
  campaign-performance claims.

Passed after the 2026-06-19 Custom Segments review-only payload preview slice:

```bash
uv run ruff check wilq/schemas.py wilq/actions/google_ads/custom_segments.py wilq/briefing/ads_diagnostics.py apps/api/wilq_api/main.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/schemas.py wilq/actions/google_ads/custom_segments.py wilq/briefing/ads_diagnostics.py apps/api/wilq_api/main.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ads_diagnostics or custom_segments or route_specific'
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run python .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-custom-segments --api-base http://127.0.0.1:8000
```

Live `:8000` proof after `scripts/local_stack.sh restart`:

- `/api/ads/diagnostics.custom_segments_read_contract.status=ready`;
- `candidate_count=1`, `payload_preview_count=1`;
- remaining missing contracts:
  `keyword_planner_enrichment`, `forecast_or_audience_size`;
- `custom_segment_payload_preview` uses `member_type=KEYWORD`,
  `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false`;
- `/api/actions/act_prepare_custom_segments_from_search_terms` exposes
  `preview_contract=custom_segment_payload_preview_v1` and validates;
- scoped `wilq-custom-segments` context-pack omits `content_diagnostics`, caps
  ActionObject metrics and measures about `186317 bytes`;
- non-interactive `wilq-custom-segments` eval passed:
  `.local-lab/evals/codex-skill/20260619T201200Z/wilq-custom-segments/result.json`
  with `operator_usefulness_score=5` and `safety_findings=[]`.
- full `scripts/verify.sh` passed after this slice:
  - backend API contracts `113 passed`;
  - dashboard route tests `13 passed`;
  - Playwright e2e `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed;
  - production build chunks remain below the 500 KB warning threshold.

Still blocked:

- custom segment targeting/apply;
- audience-size, conversion-uplift, ROAS, targeting-applied and
  campaign-performance claims;
- Keyword Planner enrichment, forecast/audience-size, human confirmation and
  Ads apply/audit contracts.

Passed after the 2026-06-19 Ads negative keyword payload preview slice:

```bash
uv run ruff check wilq/actions/google_ads/negative_keywords.py wilq/briefing/ads_diagnostics.py wilq/schemas.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/actions/google_ads/negative_keywords.py wilq/briefing/ads_diagnostics.py wilq/schemas.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ads_diagnostics_exposes_live_campaign_metric_facts or google_ads_vendor_read_uses_oauth_and_search_stream or route_specific or ads_skill'
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-ads-doctor --api-base http://127.0.0.1:8000
```

Live `:8000` proof after `scripts/local_stack.sh restart` and the 2026-06-19
keyword context slice:

- `/api/ads/diagnostics.keyword_match_context_read_contract.status=ready`
  with 211 context rows and `missing_read_contracts=["human_intent_review"]`.
- `/api/ads/diagnostics.negative_keywords_read_contract.payload_preview` has
  7 review-only preview rows and `missing_read_contracts=[]`.
- `/api/actions/act_prepare_negative_keyword_review_queue` exposes
  `preview_contract=negative_keyword_payload_preview_v1`,
  `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false`.
- `wilq-ads-doctor` smoke passed with `context_row_count=211`,
  `candidate_count=7` and `payload_preview_count=7`.
- Non-interactive `wilq-ads-doctor` eval passed at
  `.local-lab/evals/codex-skill/20260619T182309Z/wilq-ads-doctor/result.json`.
- Full `scripts/verify.sh` passed: backend API contracts `111 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed`, API smoke,
  skill smokes and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk `549.44 kB` exceeds the 500 KB warning threshold.
- Still blocked: negative keyword apply, search-term waste, conversion loss,
  CPA and ROAS until human review, confirmation, apply/audit contracts and
  stronger intent validation exist.

Passed after the 2026-06-19 Ads campaign review ActionObject:

```bash
uv run ruff check wilq/actions/google_ads/campaign_review.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/actions/google_ads/campaign_review.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py -k "ads_diagnostics" tests/test_codex_skill_eval_cases.py::test_route_specific_codex_eval_cases_define_surface_markers -q
uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
pnpm --filter @wilq/dashboard test -- --run
scripts/verify.sh
```

Live `:8000` proof after API restart:

- `/api/ads/diagnostics.action_ids` includes
  `act_prepare_ads_campaign_review_queue`.
- Campaign and derived KPI decisions attach only
  `act_prepare_ads_campaign_review_queue`.
- `/api/actions/act_prepare_ads_campaign_review_queue` exposes 8 live campaign
  candidates with evidence ID `ev_refresh_refresh_google_ads_c2f62ee2b43a`.
- Validation passed:
  `POST /api/actions/act_prepare_ads_campaign_review_queue/validate`
  returned `valid=true`.
- Full `scripts/verify.sh` passed: backend API contracts `108 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed`, API smoke,
  skill structure smoke, skill API smoke and dashboard production build passed.
  Known non-blocking warning: Vite main JS chunk `525.96 kB` exceeds the
  500 KB warning threshold.

Remaining Ads optimizer blockers:

- budget apply preview exists as review-only `CampaignBudgetOperation` with
  typed `campaign_budget_apply_safety_v1`, but target ROAS/CPA confirmation,
  apply confirmation and actual vendor budget-apply adapter are still missing,
- no recommendation apply support or vendor recommendation-apply adapter,
- no target KPI verdict or profitability verdict until target ROAS/CPA and value
  model review are confirmed,
- no campaign pause/budget apply vendor adapter.

Superseded safety note, 2026-06-20 21:58 CEST: local
review/preview/confirm/impact-check and mutation-audit gates now exist. Current
blocker is actual vendor mutation adapter support, not missing local audit
state.

Passed after the 2026-06-19 Command Center GA4 metric-fact fallback:

```bash
uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or command_center_uses_ga4_metric_facts_without_ga4_tactical_items'
uv run pytest tests/test_api_contracts.py -q -k 'command_center'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1
```

Result:

- Command Center no longer shows GA4 `landing groups=0` when dimensional GA4
  metric facts exist.
- Live `/api/dashboard/command-center` and
  `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` expose the
  same GA4 daily decision: `landing groups=10`, `blocked`, evidence
  `ev_refresh_refresh_google_analytics_4_681b6bcefc85`, action
  `act_review_ga4_tracking_quality`.
- Focused checks passed: API selected `2 passed`, Command Center API `6
  passed`, dashboard route tests `13 passed`, Playwright dashboard-api `8
  passed`.
- Full `scripts/verify.sh` passed after this slice:
  - backend API contracts: `108 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed;
  - non-blocking warning: Vite main chunk is `525.96 kB`, above the 500 KB
    warning threshold.

Passed after the 2026-06-19 Ads scoped context-pack compaction:

```bash
uv run ruff check apps/api/wilq_api/main.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py
uv run pytest tests/test_api_contracts.py -q -k 'codex_context_pack_scopes_ads_doctor_payload or codex_context_pack_scopes_content_strategist_payload or codex_context_pack_full_context_keeps_diagnostic_surfaces or list_evidence_by_ids_returns_metric_fact_evidence_without_full_scan'
uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Result:

- Scoped `wilq-ads-doctor` context-pack keeps Ads evidence/action traceability
  but removes nested metric-fact dumps from the Codex runtime packet.
- Runtime measurement on local `:8000` after keyword-context compaction:
  `198513 bytes`, cold `1.281-1.620s`, warm `0.145-0.159s`.
- The full Ads detail endpoint remains `/api/ads/diagnostics`; the cache must
  not be treated as source truth.
- Full `scripts/verify.sh` passed after this slice:
  - backend API contracts: `107 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed;
  - non-blocking warning: Vite main chunk is `525.96 kB`, above the 500 KB
    warning threshold.

Passed after the 2026-06-19 GA4 blocked-copy correction and manual
`wilq-ads-doctor` usefulness proof:

```bash
uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief'
pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-demo-proof.spec.ts --workers=1
scripts/verify.sh
```

Result:

- Live `/api/dashboard/command-center` now exposes
  `decision_review_ga4_landing_quality` as `blocked`, with title
  `GA4: brak danych do oceny ruchu` and copy that frames `/ga4` as a missing
  contract diagnostic, not a ready performance recommendation.
- Manual `wilq-ads-doctor` proof is recorded in
  `docs/evals/skill-eval-ledger.md`: 18 campaigns, 50 search-term rows,
  Google Ads evidence IDs, valid prepare-only ActionObjects and blocked
  waste/profitability/apply claims.
- Focused checks passed: ruff, mypy, selected backend contract test and
  targeted Playwright demo proof.
- Full gate passed: backend API contracts `106 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed`, API smoke, skill structure smoke,
  skill API smoke and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk remains above 500 KB.

Passed after the 2026-06-19 `wilq-ga4-analyst` decision_queue repair:

```bash
uv run ruff check wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py wilq/schemas.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ga4_diagnostics or route_specific'
uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-ga4-analyst --api-base http://127.0.0.1:8000
scripts/verify.sh
```

Result:

- API runtime proof: `live_data_available=true`, `landing_group_count=10`,
  `decision_count=6`.
- Deterministic smoke: passed with `act_review_ga4_tracking_quality`, GA4
  evidence IDs and supported decision types.
- Non-interactive Codex eval: passed at
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
- Narrow backend checks: ruff passed, mypy passed, focused pytest `3 passed`.
- Full gate: backend API contracts `100 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed` and dashboard production build passed.

Passed after the 2026-06-19 Ads derived KPI + conservative GA4 Command Center
status slice:

```bash
uv run ruff check wilq/schemas.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or ads_diagnostics_exposes_live_campaign_metric_facts'
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
scripts/verify.sh
```

Result:

- Command Center GA4 remains `blocked` when live behavior facts exist but
  ROAS/revenue/conversion-drop/tracking-fixed interpretation contracts are
  missing.
- `/api/ads/diagnostics.derived_kpi_read_contract` exposes CTR/CPC/conversion
  rate/CPA/ROAS/value per conversion as calculated read-only KPI rows with
  evidence IDs and blocked profitability/waste/budget/apply claims.
- Live runtime proof on `:8000`: derived KPI status `ready`, `kpi_rows=18`,
  decision `ads_review_derived_kpis`.
- Full gate: backend API contracts `106 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed`, API smoke, skill structure smoke,
  skill API smoke and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk remains above 500 KB.

Passed after the 2026-06-19 `/ads-doctor` decision route cleanup:

```bash
uv run ruff check wilq/briefing/ads_diagnostics.py wilq/schemas.py tests/test_api_contracts.py
uv run mypy wilq/briefing/ads_diagnostics.py wilq/schemas.py
uv run pytest tests/test_api_contracts.py -q -k 'ads_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
scripts/verify.sh
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/ads-doctor` has decisions for campaign review,
  search-term review and blocked write path, with no visible stale
  `Read contract Ads`, `Search terms read-only`, `Campaign activity read contract`,
  `Search terms read contract`, `Google Ads: campaign activity rows`,
  `Google Ads: search terms read-only rows`, `Evidence`, `configured`, `READY`,
  `payload preview`, `write/apply` or stale read-only evidence copy.
- Full `scripts/verify.sh`: passed with backend API contracts `98 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed` and dashboard
  production build passed.

Passed after the 2026-06-19 `/merchant` operator cleanup:

```bash
uv run ruff check wilq/briefing/merchant_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/briefing/merchant_diagnostics.py
uv run pytest tests/test_api_contracts.py -q -k 'merchant_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
scripts/verify.sh
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/merchant` has no visible `payload preview`,
  `review queue`, `read-only`, `feed/product`, `configured`, `Evidence`,
  `Feed Safety Gate`, `ActionObject focus`, duplicate old Merchant diagnostic headings,
  `automatic feed edit`, `approval restored`, `sample product IDs` or `READY`.
- Full `scripts/verify.sh`: passed with backend API contracts `98 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed` and dashboard
  production build passed.

Passed after the 2026-06-19 `/actions` + `/opportunities` cleanup:

```bash
uv run ruff check wilq/opportunities/engine.py wilq/actions/service.py tests/test_api_contracts.py
uv run mypy wilq/opportunities/engine.py wilq/actions/service.py
uv run pytest tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts -q
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/actions` has no generic registry dump or stale Ads
  OAuth repair action; `/opportunities` has no old readiness/English blocker
  phrases.
- Full `scripts/verify.sh`: passed after this slice with backend API contracts
  `98 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
  and dashboard production build passed.

Already passed after the current stale-state cleanup started:

```bash
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run ruff check wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py
uv run mypy wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py
uv run pytest tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts tests/test_api_contracts.py::test_google_ads_oauth_repair_action_is_explicit_and_redacted -q
```

Result:

- Dashboard typecheck: passed.
- Dashboard route tests: 12 passed.
- Backend ruff: passed.
- Backend mypy: passed.
- Focused backend API tests: 3 passed.
- Current-code sanity check: `daily_ads_status` is ready/live, Ads action plan
  is live review, Ads demo step is live campaign metrics, and active Ads repair
  action is filtered out when latest Ads refresh has live data.

Full `scripts/verify.sh` passed after the current cleanup:

```text
backend API contracts: 93 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Latest content decision queue verification:

- Focused ruff, mypy and API contract tests passed for
  `content_diagnostics.decision_queue`, redaction and skill smoke updates.
- Full `scripts/verify.sh` passed after adding clean-runtime core prepare
  ActionObjects and stabilizing `wilq-content-strategist` smoke.
- Clean runtime rule: core daily prepare ActionObjects may exist with connector
  evidence only, but content `decision_queue` must remain empty until real
  GSC/GA4/WordPress metric facts exist. Live runtime still requires concrete
  `inventory_check_before_create`, `merge_create_after_inventory_check` and
  `block_as_tracking_not_content` decisions.

Latest focused backend slice:

- Social draft ActionObjects remain available in `/api/actions` and explicit
  `wilq-social-publisher` context-pack.
- `GET /api/marketing/brief` top-level `action_ids` now contains only core
  daily actions:
  `act_review_merchant_feed_issues`,
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`.
- `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` now exposes
  only those core daily `active_action_objects`.
- Proof:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py
  uv run pytest tests/test_api_contracts.py -q -k 'marketing_brief_exposes_metric_backed_prepare_actions or codex_context_pack_embeds_marketing_brief_contract or daily_context_pack_excludes_social_draft_action_objects or social_context_pack_keeps_explicit_social_draft_action_objects or command_center_exposes_polish_operator_brief'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
  ```

Latest Command Center cleanup:

- Localo is configured and access-ready, not an active OAuth/access blocker.
- Because WILQ still lacks concrete Localo ranking/GBP/competitor facts,
  access-ready Localo is no longer shown as a primary Command Center
  `operator_brief` card or action-plan item.
- Localo still appears as a primary Command Center card only when access is
  genuinely missing, because that is an actionable blocker.
- `/localo` and `wilq-localo-operator` remain the right surfaces for Localo
  access/readiness status until a real Localo visibility read contract exists.

Latest Marketing Brief cleanup:

- `GET /api/marketing/brief` now reads metric facts per connector instead of a
  single global DuckDB limit that was dominated by recent aggregate refreshes.
- Metric cards prefer dimensional business facts before aggregate facts, so the
  brief promotes useful GSC query/page, GA4 landing/source, Merchant issue and
  Ads campaign facts instead of stale-looking aggregates such as
  `active_products=12`, `sessions=30` or `clicks=3`.
- This does not change `/api/actions`; it only improves the evidence selected
  for the daily brief and Codex context.

Latest Command Center Codex bridge cleanup:

- Daily decision cards now visibly expose `Jak Codex może pomóc`, the matching
  `skill_id`, `codex_prompt`, `codex_context_endpoint` and
  `expected_codex_output`.
- The first-screen source footer uses Polish operator wording:
  `Źródła`, `Aktywne`, `Do naprawy`, `Otwórz ustawienia`.
- Focused proof passed:
  ```bash
  pnpm --filter @wilq/dashboard lint
  pnpm --filter @wilq/dashboard typecheck
  pnpm --filter @wilq/dashboard test -- --run App.test.tsx
  WILQ_E2E_API_PORT=<dynamic> WILQ_E2E_DASHBOARD_PORT=<dynamic> CI= pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1
  ```

Latest Command Center metric-decision cleanup:

- `DailyDecision` now exposes `metric_tiles` and Command Center renders them
  directly on the first-screen decision cards.
- Runtime proof after API restart:
  - Merchant decision: `produkty=10900`, `typy problemów=15`,
    `zgłoszenia=1887`, `decyzje=8`, `blockery=0`;
  - Content decision: `query/page=10`, `WP match=10`, `decyzje=4`,
    `wyświetlenia=7852`, `kliknięcia=138`;
  - GA4 decision: `grupy ruchu=10`, `decyzje=6`, `pomiar=2`,
    `jakość ruchu=4`, `braki kontraktu=1`;
  - Ads decision: `kampanie=18`, `search terms=50`, `rekomendacje=4`,
    `podgląd budżetu=18`.
- GA4 no longer claims `0 landing/source groups` when tactical queue already
  has landing/source/campaign groups; diagnostics falls back to tactical group
  count when section metric facts are empty.
- Merchant issue cluster IDs include reporting context and resolution, so issue
  clusters do not collide across `all_contexts`, `FREE_LISTINGS` and
  `SHOPPING_ADS`.
- `agent-browser` proof was run with local runtime dir:
  `XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime`.

Latest Ads/Localo stale-state cleanup:

- Live Ads diagnostics no longer overload `blocked_handoff` for "next step"
  messaging. `blocked_handoff` is now only for real access blockers; live Ads
  keeps write/apply limits in `ads_action_safety`, campaign/search-term read
  contracts and blocked claims.
- `wilq-ads-doctor` smoke now accepts both legal API states: live diagnostics
  with no OAuth handoff, or blocked diagnostics with a blocked handoff and
  ActionObject IDs.
- `/localo` no longer renders generic global tactical queue stats when there
  are no Localo tactical items. It keeps Localo access/readiness and blocks
  ranking/GBP/local-visibility claims until a real Localo read contract exists.
- Focused proof passed:
  - `uv run ruff check wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`
  - `uv run mypy wilq/briefing/ads_diagnostics.py`
  - `uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q`
  - `pnpm --filter @wilq/dashboard lint`
  - `pnpm --filter @wilq/dashboard typecheck`
  - `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
  - `WILQ_E2E_API_PORT=8875 WILQ_E2E_DASHBOARD_PORT=5373 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts` -> `8 passed`
  - `scripts/verify.sh` -> backend API contracts `98 passed`, dashboard route
    tests `12 passed`, Playwright e2e `8 passed`, dashboard production build
    passed.

Important product note:

- The Codex bridge is necessary but not sufficient. It only connects a dashboard
  decision to a WILQ skill. It is not yet the marketer value by itself.
- The next useful slice must audit the primary dashboard routes
  `/ga4`, `/ads-doctor` and `/localo`, then
  replace technical inventory with real metric-backed decisions.
- Every route should preserve evidence/action traceability while making the
  marketer-facing hierarchy obvious: real metric, diagnosis, safe next action,
  blocked claims and matching Codex skill/prompt.

Latest Localo aggregate value facts slice:

- Done: Localo is no longer only an OAuth/MCP access proof. The Localo connector
  now performs read-only MCP GraphQL `query` calls after initialize and stores
  only aggregate facts. It must not store raw Localo place names, addresses,
  keywords, categories or Localo IDs.
- Live proof: `uv run wilq connectors refresh localo --mode vendor_read
  --reason "Goal 001 Localo aggregate value facts proof"` completed as
  `refresh_localo_9e9ff67eadad` with evidence
  `ev_refresh_refresh_localo_9e9ff67eadad`.
- Live aggregate facts: `localo_active_place_count=4`,
  `localo_tracked_keyword_count=23`,
  `localo_avg_visibility_current=52.8261`,
  `localo_avg_latest_grid_position=3.2105`,
  `localo_reviews_count=793`, `localo_review_reply_rate=0.809584`.
- `/api/localo/diagnostics` now reports `live_data_available=true`,
  `visibility_fact_count=17`, `allowed_evidence=[place_inventory,
  local_rankings, reviews]`, and missing contracts
  `[gbp_visibility, competitor_visibility, local_tasks]`.
- Command Center now promotes Localo only when real facts exist or access is
  genuinely blocked. Current live Localo card tiles:
  `miejsca=4`, `frazy=23`, `widoczność=52.8261`, `recenzje=793`.
- `wilq-localo-operator` context-pack receives the same diagnostics. Redaction
  now preserves long metric names such as
  `localo_latest_grid_position_count`; secret-like values remain redacted.
- Still blocked by design: do not claim `GBP performance`,
  `competitor visibility`, `local task completed`, `GBP write` or
  `local visibility uplift` until separate read/action contracts exist.
- Full proof passed: ruff/mypy on changed backend modules, selected
  Localo/redaction API tests, dashboard route unit tests, live Localo
  vendor_read, live context-pack redaction check and `scripts/verify.sh`.
  Final verify result: backend API contracts `122 passed`, dashboard unit tests
  `14 passed`, Playwright e2e `11 passed`, skill/API smokes and production
  build passed.

Latest Localo dashboard snapshot slice:

- `/localo` now shows `Snapshot lokalnej widoczności` before the technical
  Localo proof. This is the marketer-facing summary of Localo facts from
  `/api/localo/diagnostics`; MCP initialize/OAuth/PKCE details stay lower as
  adapter proof, not the main product value.
- The snapshot intentionally consumes existing WILQ API `decision_queue`
  metric tiles instead of hardcoding changing Localo values.
- Focused proof passed:
  - `pnpm --filter @wilq/dashboard test -- --run src/routes/App.test.tsx -t "localo social and content routes render workflow-specific blockers or focus"`
  - `pnpm --filter @wilq/dashboard lint`
  - `pnpm --filter @wilq/dashboard typecheck`

Latest GA4 dashboard measurement slice:

- `/ga4` now names the top status area `Status GA4 / pomiar i jakość ruchu`
  and shows `Problemy pomiaru GA4` before the main operator decision queue.
- `(not set)` and `tracking_gap` rows remain measurement/attribution review
  signals. They must not be displayed as landing-quality wins/losses or
  campaign-performance verdicts.
- Focused proof passed:
  - `pnpm --filter @wilq/dashboard test -- --run src/routes/App.test.tsx -t "ga4 and gsc routes render workflow-specific brief focus"`
  - `pnpm --filter @wilq/dashboard lint`
  - `pnpm --filter @wilq/dashboard typecheck`

Latest Ads Doctor first-screen snapshot slice:

- `/ads-doctor` now shows `Ads snapshot marketera` before detailed operator
  decisions. This is the marketer-facing readout for what WILQ can honestly
  inspect in Ads today.
- The snapshot condenses campaign count, search-term count, recommendations,
  budget rows, ready/blocked areas, missing read contracts and blocked claims
  from `/api/ads/diagnostics`.
- `Operator Ads` top metric grid was reduced to the core review counts; deeper
  read contracts and technical tables remain lower on the route for drilldown.
- Focused proof passed:
  - `pnpm --filter @wilq/dashboard test -- --run src/routes/App.test.tsx -t "ads doctor route renders live metric-backed diagnostics"`
  - `pnpm --filter @wilq/dashboard lint`
  - `pnpm --filter @wilq/dashboard typecheck`
