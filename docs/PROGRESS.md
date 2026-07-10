# WILQ Progress Ledger

This is the short recovery ledger, not an append-only changelog. Historical
proof is archived in `docs/progress/archive/` and in git history.

## Current readout — 2026-07-10

- WILQ is the marketing operating system; Wilku is the Polish marketer/operator;
  Ekologus is the first workspace.
- The WILQ API is canonical. Dashboard and Codex skills consume typed API
  contracts, connector evidence and freshness; nie wolno im zmyślać metryk.
- `ekologus.pl` and `sklep.ekologus.pl` are public content/evidence sources.
  Dev WordPress is a safe authoring workspace only, never canonical SEO proof.
- Marketer-facing output uses normal Polish and explains the decision, proof,
  blocker and next safe step.
- The primary dashboard route is `/content-workflow`. The legacy content
  planner route and `ContentDiagnosticSurface` are removed from active truth.
- Current WILQ queue state is API-owned: 1 of 2 candidates is actionable and
  the queue is blocked on reaching the minimum actionable candidate count.
  The actionable candidate is the existing public homepage and is supported by
  GSC and WordPress evidence; the Ahrefs gap candidate remains blocked by
  inventory/canonical checks.
- Latest API refresh reports DuckDB metric_fact_count=95532 and
  refresh_run_count=4425; the queue remains 1/2 actionable with the same
  GSC/WordPress homepage candidate and Ahrefs duplicate/canonical blockers.
- Full `scripts/verify.sh` reached the complete pytest stage: 753 passed, 2
  skipped, 7 failures. The Ahrefs wording assertions, WordPress authorization
  expectation and Localo smoke fixture are now aligned and pass focused tests;
  remaining failures are explicit Goal 005 state/eval and endpoint-copy
  follow-up work, so the overall verification gate is not claimed green.
- The previously failing Goal 005, endpoint-language, Localo, WordPress and
  Ahrefs-focused contracts now pass together. Goal 005 truth explicitly shows
  All 13 live skill evals are now fresh and passing. The custom segment case
  correctly requires only `google_ads`, matching the API's evidence-backed
  source contract rather than inventing GSC provenance.
- The full verification run reached 760 backend tests and 136 dashboard tests.
  The only late failure was a stale Goal 005 artifact caused by the final Ads
  output-contract wording edit; refreshing that Ads eval and rerunning the
  focused Goal 005 gate now passes.
- Dashboard copy assertions were aligned with the current Polish marketer
  labels (`twierdzenia`, `Posty społecznościowe`, `Sprawdzenie GSC i WordPress`,
  `Rejestr twierdzeń`); dashboard remains 136/136 green.
- The next bounded action-service seam is also verified: construction of
  `act_prepare_content_refresh_queue` now lives in
  `_content_refresh_queue_action(...)`; focused action/content tests, mypy,
  Ruff and `git diff --check` pass, with the payload and downstream WordPress
  handoff unchanged.
- A second `jnra` seam now owns Google Ads campaign-review ActionObject
  construction in `_campaign_review_action(...)`; metric filtering, evidence,
  payload and prepare-only safety remain unchanged and the focused suite stays
  green.
- A third seam now owns Google Ads recommendation-review ActionObject
  construction in `_recommendation_review_action(...)`; source filtering and
  prepare-only safety are unchanged and the focused Ads/action checks pass.
- A fourth seam now owns Google Ads change-history impact ActionObject
  construction in `_change_history_impact_action(...)`; event/evidence
  filtering and prepare-only behavior remain covered by focused tests.
- A fifth seam now owns search-term n-gram ActionObject construction in
  `_search_term_ngram_action(...)`; source-term/evidence filtering and the
  prepare-only boundary remain unchanged and verified.
- A sixth seam now owns custom-segment ActionObject construction in
  `_custom_segment_action(...)`; Google Ads source filtering and prepare-only
  safety remain unchanged and covered by focused checks.
- A seventh seam now owns negative-keyword ActionObject construction in
  `_negative_keyword_action(...)`; search-term evidence filtering, 90-dniowa
  kontrola and prepare-only behavior remain unchanged and verified.
- An eighth seam now owns Localo visibility-review ActionObject construction in
  `_localo_visibility_review_action(...)`; prioritized metrics, evidence and
  GBP/ranking blockers remain unchanged and covered by focused checks.
- A ninth seam now owns GA4 tracking-quality ActionObject construction in
  `_ga4_tracking_quality_action(...)`; evidence selection, blocked conversion/
  ROAS claims and prepare-only safety remain unchanged and verified.
- A tenth seam now owns Merchant feed-issue ActionObject construction in
  `_merchant_feed_issue_action(...)`; issue clusters, preview contract, blocked
  claims and `apply_allowed=false` remain unchanged and verified.
- The first constructor now lives outside the service monolith: GA4
  tracking-quality ActionObject construction moved to
  `wilq/actions/ga4/tracking_quality.py`; `service.py` delegates with behavior
  and safety unchanged.
- Merchant feed-issue construction now also lives in the domain module
  `wilq/actions/merchant.py`; `service.py` delegates while preserving the
  preview contract, blocked claims and `apply_allowed=false`.
- Localo visibility-review construction now also lives in
  `wilq/actions/localo/visibility.py`; the service delegates while preserving
  prioritized metrics and GBP/ranking blockers.
- Custom-segment construction now also lives in
  `wilq/actions/google_ads/custom_segments.py`; `service.py` delegates while
  preserving source-term filtering, payload and prepare-only safety.
- Negative-keyword construction now also lives in
  `wilq/actions/google_ads/negative_keywords.py`; `service.py` delegates while
  preserving search-term evidence filtering and 90-dniowa safety.
- Campaign-review construction now also lives in
  `wilq/actions/google_ads/campaign_review.py`; `service.py` delegates while
  preserving campaign/evidence filtering, payload and budget safety.
- Recommendation-review construction now also lives in
  `wilq/actions/google_ads/recommendations.py`; `service.py` delegates while
  preserving evidence filtering and review-before-acceptance safety.
- Change-history impact construction now also lives in
  `wilq/actions/google_ads/change_history.py`; `service.py` delegates while
  preserving event/evidence filtering and prepare-only safety.
- Search-term n-gram construction now also lives in
  `wilq/actions/google_ads/search_term_ngrams.py`; `service.py` delegates while
  preserving source-term selection and no-automatic-exclusions safety.
- Content-refresh queue construction now also lives in
  `wilq/actions/content_refresh.py`; `service.py` delegates while preserving
  fallback payload, evidence and WordPress review gates.
- Complexity audit after the domain moves reports `wilq/actions/service.py` at
  6,009 LOC (down from the earlier ~6,682 LOC baseline); the metric seeder has
  no remaining inline `ActionObject` constructors. The next dominant seam is
  `_demand_gen_readiness_review_action`.
- The Demand Gen readiness ActionObject constructor now lives in
  `wilq/actions/google_ads/demand_gen.py`; `service.py` retains evidence and
  contract calculation but delegates the domain construction.
- Post-split complexity audit reports `service.py` at 5,990 LOC. The next
  separate senior-cleanup target is `wilq-seo-kgvy` for
  `wilq/briefing/ads_diagnostics.py` (7,144 non-empty LOC); it remains open and
  must be handled as its own bounded Beads slice.
- Started `wilq-seo-kgvy`: the Ads change-history section builder now lives in
  `wilq/briefing/ads_change_history.py`; the diagnostics view-model and blocked
  claims remain unchanged. Focused Ads contracts, mypy, Ruff and diff check
  pass.
- Second `kgvy` seam: the Ads recommendations section builder now lives in
  `wilq/briefing/ads_recommendations.py`; status, evidence, blocked claims and
  action IDs are unchanged and focused checks pass.
- Third `kgvy` seam: the Ads impression-share section builder now lives in
  `wilq/briefing/ads_impression_share.py`; read-contract, evidence and blocked
  budget/traffic claims remain unchanged.
- Fourth `kgvy` seam: the Ads budget-pacing section builder now lives in
  `wilq/briefing/ads_budget_pacing.py`; pacing evidence and no automatic budget
  scaling/change claims remain unchanged.
- Fifth `kgvy` seam: Ads search-terms and n-gram section builders now live in
  `wilq/briefing/ads_search_terms.py`; action ID filtering, evidence and blocked
  exclusion claims remain unchanged.
- Sixth `kgvy` seam: the Ads 90-day search-term safety section builder now lives
  in `wilq/briefing/ads_search_terms.py`; long-window evidence and no-write
  blockers remain unchanged.
- Seventh `kgvy` seam: the Ads keyword-match context section builder now lives
  in `wilq/briefing/ads_search_terms.py`; source context and no-exclusion blocker
  remain unchanged.
- Eighth `kgvy` seam: the Keyword Planner section builder now lives in
  `wilq/briefing/ads_keyword_planner.py`; access-action filtering and blocked
  forecast/audience claims remain unchanged.
- Ninth `kgvy` seam: the Ads custom-segments section builder now lives in
  `wilq/briefing/ads_custom_segments.py`; source-term-only policy and blocked
  audience-size/effectiveness claims remain unchanged.
- Tenth `kgvy` seam: the Ads negative-keyword safety section builder now lives
  in `wilq/briefing/ads_negative_keywords.py`; 90-day/write blockers and
  evidence remain unchanged.
- Eleventh `kgvy` seam: the Ads campaign-overview section builder now lives in
  `wilq/briefing/ads_campaigns.py`; campaign evidence, action filtering and
  blocked claims remain unchanged.
- Twelfth `kgvy` seam: the Ads derived-KPI section builder now lives in
  `wilq/briefing/ads_campaigns.py`; calculated KPI presentation and blocked
  ROAS/CPA/budget claims remain unchanged.
- Thirteenth `kgvy` seam: the Ads business-context section builder now lives in
  `wilq/briefing/ads_campaigns.py`; operator-contract separation, evidence and
  blocked ROAS/budget claims remain unchanged.
- Fourteenth `kgvy` seam: the first `_ads_decision_queue` campaign-activity
  decision builder now lives in `wilq/briefing/ads_decision_queue.py`; missing
  contracts, action IDs, evidence and lineage behavior remain unchanged.
- Fifteenth `kgvy` seam: the campaign-triage decision builder now lives in
  `wilq/briefing/ads_decision_queue.py`; triage rows, review gates, evidence and
  blocked budget/efficiency claims remain unchanged.
- Sixteenth `kgvy` seam: the derived-KPI decision builder now lives in
  `wilq/briefing/ads_decision_queue.py`; a first-pass metric-field mismatch was
  caught by the focused Ads suite and removed, restoring the original contract.
- Seventeenth `kgvy` seam: the budget-context decision builder now lives in
  `wilq/briefing/ads_decision_queue.py`; budget rows, shared-budget data, action
  IDs and scaling blockers remain unchanged.
- Eighteenth `kgvy` seam: the recommendations decision builder now lives in
  `wilq/briefing/ads_decision_queue.py`; recommendation rows, preview, review
  gates, action IDs and no-write claims remain unchanged.
- Nineteenth `kgvy` seam: the change-history decision builder now lives in
  `wilq/briefing/ads_decision_queue.py`; event rows, evidence, no-impact claims
  and action IDs remain unchanged.
- Twentieth `kgvy` seam: the search-terms decision builder now lives in
  `wilq/briefing/ads_decision_queue.py`; source rows, filtered action IDs,
  evidence and no-automatic-exclusions safety remain unchanged.
- Added `GET /api/content/wordpress/existing-draft-update-readiness` with typed
  `wordpress_existing_draft_update_readiness_v1` output and a deterministic
  blocker. It exposes work-item, evidence and connector lineage while keeping
  update, publish and destructive writes disabled; focused contract test passes.
- Added `act_prepare_wordpress_existing_draft_update` as a separate validated
  prepare-only ActionObject with `wordpress_existing_draft_update_preview_v1`.
  Its preview emits an audit event and remains blocked by prepare-only,
  apply-false, impact-check and blocked-claim gates; no vendor mutation path was added.
- The same action has focused review-to-confirm coverage: human review is
  audited, confirmation records only the prepare preview, and
  `review_gate.apply_allowed` remains false.
- The shared frontend schema and `api.ts` now expose the existing-draft
  readiness contract through a typed `getContentWordPressExistingDraftUpdateReadiness()`
  boundary; the dashboard can consume the blocker without inventing UI state.
- `/content-workflow` now consumes that typed readiness query in the dev column
  and shows the API-owned existing-draft update blocker beside the draft action;
  dashboard typecheck and 136-test suite remain green.
- The readiness response matches the public source path to the dev REST
  inventory, exposing current target post `2` at the dev root when available;
  update remains blocked even when current state is readable.
- Readiness now returns typed `section_diff_preview`: 9 current dev sections,
  3 proposed sections and three API-owned current/proposed status rows. This
  is preview data only; no ACF or post write is attempted.
- The dev workbench renders those diff rows as marketer-readable `Aktualne` →
  `Proponowane` summaries beside the blocker; dashboard remains 136/136 green.
- ContentWorkflowSurface coverage now asserts the blocker and both diff summaries
  on the rendered workbench, not just the API response.
- The existing-draft ActionObject constructor now lives in
  `wilq/actions/wordpress_draft.py`; `service.py` keeps a compatibility wrapper.
  Focused action/content tests, mypy, Ruff and diff checks pass.

## Completed cleanup slices

- `wilq-seo-50wa.9`: extracted focused contract-test support leaves and removed
  dynamic imports of the legacy mega-test.
- Fresh verification confirms the extracted-test bridge remains absent (`rg`
  finds no `importlib`, `globals().update` or `tests.test_api_contracts` under
  `tests/api_contracts`, `tests/actions` and `tests/_contract_support`); the
  combined contract suite passes and the legacy file is now 1846 LOC. The
  `/api/system/status` contract now lives in
  `tests/api_contracts/test_system_status_contracts.py`.
- The command-center evidence-to-source mapping contract now lives in
  `tests/api_contracts/test_command_center_evidence_contracts.py`; the legacy
  file is down to 1818 LOC and the focused test/Ruff checks pass.
- Opportunity source/evidence validation now lives in
  `tests/api_contracts/test_opportunity_contracts.py`; focused pytest/Ruff pass
  and the legacy file is down to 1789 LOC.
- Evidence registry secret-redaction coverage now lives in
  `tests/api_contracts/test_evidence_registry_contracts.py`; its focused test,
  Ruff and diff checks pass and the legacy file is down to 1766 LOC.
- Metric-context dimension-label coverage now lives in
  `tests/api_contracts/test_metric_context_contracts.py`; both focused tests
  pass and the legacy file is down to 1702 LOC.
- Google Ads operator-dimension label coverage now joins that metric-context
  module; its three focused tests pass and the legacy file is down to 1670 LOC.
- Context-pack anti-invention and secret-redaction coverage now lives in
  `tests/api_contracts/test_context_safety_contracts.py`; focused pytest/Ruff
  checks pass and the legacy file is down to 1653 LOC.
- Daily-check traceability validation now lives in
  `tests/api_contracts/test_daily_check_contracts.py`; its focused test and
  Ruff checks pass and the legacy file is down to 1602 LOC.
- Connector evidence operator-language coverage now lives in
  `tests/api_contracts/test_evidence_language_contracts.py`; focused pytest,
  Ruff and diff checks pass and the legacy file is down to 1581 LOC.
- Targeted metric-fact evidence lookup coverage now lives in
  `tests/api_contracts/test_evidence_metric_registry_contracts.py`; focused
  pytest/Ruff checks pass and the legacy file is down to 1534 LOC.
- Action-to-registered-evidence integrity coverage now lives in
  `tests/api_contracts/test_action_evidence_registry_contracts.py`; focused
  pytest/Ruff checks pass and the legacy file is down to 1523 LOC.
- Connector refresh redaction coverage now lives in
  `tests/api_contracts/test_connector_refresh_redaction_contracts.py`; focused
  pytest/Ruff checks pass and the legacy file is down to 1476 LOC.
- Action recommended-reason marketer-language coverage now lives in
  `tests/api_contracts/test_action_operator_language_contracts.py`; focused
  pytest/Ruff checks pass and the legacy file is down to 1444 LOC.
- Localo marketer-language metric headline coverage now lives in
  `tests/api_contracts/test_localo_marketing_language_contracts.py`; focused
  pytest/Ruff checks pass and the legacy file is down to 1367 LOC.
- Localo access-blocker marketer copy coverage now joins that module; both
  Localo language tests pass and the legacy file is down to 1315 LOC.
- Daily context-pack action-summary compaction coverage now joins
  `tests/api_contracts/test_context_safety_contracts.py`; its two focused tests
  pass and the legacy file is down to 1281 LOC.
- Full combined verification for `tests/api_contracts` plus
  `tests/test_api_contracts.py` passes after the extraction batch.
- Campaign-builder context-pack scoping coverage now lives in
  `tests/api_contracts/test_campaign_builder_context_contracts.py`; focused
  pytest/Ruff checks pass and the legacy file is down to 1228 LOC.
- Ads recommendation impact-row preservation now lives in
  `tests/api_contracts/test_ads_recommendation_context_contracts.py`; focused
  pytest/Ruff checks pass and the legacy file is down to 1193 LOC.
- Ads summary-diagnostics selection coverage now joins that module; both Ads
  context tests pass and the legacy file is down to 1160 LOC.
- Full combined contract regression passes again after the Ads context
  extraction batch (`tests/api_contracts` + `tests/test_api_contracts.py`).
- Latest complexity audit remains intentionally failing on the dirty-worktree
  budget: largest remaining files are `wilq/briefing/ads_diagnostics.py`
  (7144 LOC), `wilq/actions/service.py` (6226 LOC),
  `tests/api_contracts/test_ads_contracts.py` (4971 LOC) and
  `tests/actions/test_action_object_contracts.py` (3335 LOC). This is the
  next cleanup map, not a completion claim.
- A clean route-label fallback contract was extracted to
  `tests/actions/test_route_label_contracts.py`; focused pytest/Ruff checks
  pass. The larger ActionObject fallback test remains intentionally open.
- Ads vendor-label fallback coverage now lives in
  `tests/actions/test_ads_operator_label_contracts.py`; focused pytest/Ruff
  checks pass and the ActionObject mega-test is down to 3522 LOC.
- Ads entity display-label/raw-ID protection now joins that module; both Ads
  label tests pass and the ActionObject mega-test is down to 3432 LOC.
- Ads helper-label fallback coverage now also joins that module; three Ads
  label tests pass and the ActionObject mega-test is down to 3400 LOC.
- Missing-domain/content status-label contracts now live in
  `tests/actions/test_domain_status_label_contracts.py`; focused pytest/Ruff
  checks pass and the ActionObject mega-test is down to 3383 LOC.
- Localo missing-status label coverage now joins that module; three focused
  tests pass and the ActionObject mega-test is down to 3373 LOC.
- Full `tests/actions` regression and Ruff pass after the label-contract
  extractions; ActionObject safety behavior remains green.
- Validation-vs-human-review copy coverage now lives in
  `tests/actions/test_action_validation_contracts.py`; focused pytest/Ruff
  checks pass and the ActionObject mega-test is down to 3348 LOC.
- Dry-run preview/audit safety coverage now lives in
  `tests/actions/test_action_preview_contracts.py`; focused pytest/Ruff checks
  pass and the ActionObject mega-test is down to 3310 LOC.
- Full `tests/actions` regression and Ruff pass again after the preview
  extraction; ActionObject safety behavior remains green.
- Content preview-only brief payload coverage now joins
  `tests/actions/test_action_preview_contracts.py`; both preview tests pass and
  the ActionObject mega-test is down to 3270 LOC.
- Human-review audit-without-apply coverage now lives in
  `tests/actions/test_action_review_contracts.py`; focused pytest/Ruff checks
  pass and the ActionObject mega-test is down to 3213 LOC.
- Confirmation-without-preview blocking coverage now lives in
  `tests/actions/test_action_confirmation_contracts.py`; focused pytest/Ruff
  checks pass and the ActionObject mega-test is down to 3177 LOC.
- Preview-confirmation-without-apply coverage now joins that module; both
  confirmation tests pass and the ActionObject mega-test is down to 3124 LOC.
- Impact-check-before-confirmation blocking coverage now joins that module;
  three confirmation/impact tests pass and the ActionObject mega-test is down
  to 3090 LOC.
- Full `tests/actions` regression and Ruff pass after moving review contracts;
  ActionObject safety behavior remains green.
- `wilq-seo-50wa.11`: moved three evidence-required ActionObject safety tests into
  `tests/actions/test_action_evidence_contracts.py`; focused and remaining
  action tests plus Ruff pass, with mutation safety unchanged. A shared
  `action_safety_factory.py` now owns synthetic audit fixtures; the source file
  dropped to 3335 LOC and remains open for larger test bodies.
- `wilq-seo-3bst.21`: closed the marketer-first `/actions/:actionId` slice. The
  action detail hero now leads with decision, reason, write readiness, blockers,
  evidence and safe next-step links; merchant-feed blocked-write coverage keeps
  payload and contract mechanics below the fold.
- `wilq-seo-b4kg.1`–`.4`: converted `wilq.schemas` into explicit domain modules
  behind a 12-line compatibility facade; public imports, OpenAPI, contracts,
  Ruff, mypy and live API checks pass. Parent `wilq-seo-b4kg` is closed.
- The active `/content-workflow` workbench now combines public WordPress
  sections, GSC/Ahrefs/knowledge signals, generic dev ACF readback, editable
  draft sections and draft-only WordPress execution.

## Current product truth and next work

- `/content-workflow` is useful but not finished: the next product slice is an
  explicit public-to-dev target selector, current-versus-proposed dev values,
  and an existing-draft/ACF update path. Do not claim production readiness.
- `wilq-seo-50wa` remains open for the remaining oversized test bodies.
- Other open cleanup work includes `wilq-seo-ho41` (content route split),
  `wilq-seo-pidl` (dashboard test split), `wilq-seo-jnra` (action service),
  `wilq-seo-kgvy` (Ads diagnostics), `wilq-seo-ksiq` (shared TypeScript
  schemas), `wilq-seo-0q74` (skill smoke harness), and `wilq-seo-co30`
  (documentation truth; this slice).
- The senior audit epic `wilq-seo-c9h9` remains open. Do not mark the overall
  goal complete while these product and cleanup requirements remain.

## Verification anchors

- API health: `GET /api/health` returns `status: ok`.
- Metrics status: `GET /api/metrics/status` reports the live DuckDB backend,
  connector and refresh-run counts.
- Content queue: `GET /api/content/work-items/queue` is the source for the
  current content decision and evidence IDs.
- Schema split verification: focused API-contract suite, package compatibility,
  Ruff, mypy, AST definition preservation, live OpenAPI and `git diff --check`.
- Full complexity audits still report unrelated dirty-worktree violations;
  those remain tracked by the open Beads and are not silently waived here.

## Recovery rule

After context loss, read `docs/CONTEXT.md`, `docs/current-cleanup-state.md`,
`docs/dashboard-state.md`, this file, `PLANS.md`, then run `bd ready --json`.
Choose one Beads-backed slice, verify it against the API and relevant tests, and
replace this ledger instead of appending a transcript.
