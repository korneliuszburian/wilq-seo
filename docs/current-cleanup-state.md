# Current Cleanup State - 2026-07-10

This file is the handoff for the senior cleanup work after the full repo audit.
Read it before continuing cleanup, dashboard refactors or API contract work.

## Current instruction

The user resumed cleanup on 2026-07-10. `wilq-seo-50wa.9` is complete: shared
test support now has focused domain leaves and extracted test modules no longer
import `tests/test_api_contracts.py` dynamically. `wilq-seo-b4kg.1` is also
complete: `wilq.schemas` is now a compatibility package with its shared core
in a lower-level domain module. The next tranche is also complete: action,
knowledge and marketing contracts now live in sibling modules.
Ads and Demand Gen contracts now live in `wilq/schemas/ads.py`.
Merchant, Content, GA4, Localo, Ahrefs and Command Center contracts now live
in their own sibling modules as well.
`wilq-seo-co30` is now complete: the active progress ledger is concise and the
previous append-only ledger is archived under `docs/progress/archive/`.

This file remains the single handoff for the next model/session. Before taking
another cleanup slice, read this file, `docs/dashboard-state.md`, then Beads.
Pick one Beads-backed slice, verify it, and replace the relevant state here
before moving on.

`wilq-seo-50wa` remains open. Do not start unrelated broad splits of
`ContentWorkflowSurface.tsx`, `App.test.tsx`,
`wilq/actions/service.py`, Ads diagnostics, skill smoke scripts or the remaining
large test files without selecting the next Beads-backed slice deliberately.

The current `wilq-seo-jnra` slice extracted construction of
`act_prepare_content_refresh_queue` into a focused helper without changing its
payload or downstream WordPress handoff. Focused action/content tests, mypy,
Ruff and `git diff --check` are green.
The same slice now also extracts Google Ads campaign-review ActionObject
construction into `_campaign_review_action(...)`; its evidence filtering and
prepare-only boundary are covered by the focused suite.
Recommendation-review construction is now similarly isolated in
`_recommendation_review_action(...)`, with Ads/action tests and static checks
remaining green.
Change-history impact construction is now isolated in
`_change_history_impact_action(...)`; its event/evidence filtering remains
prepare-only and verified by the focused Ads suite.
Search-term n-gram construction is now isolated in
`_search_term_ngram_action(...)`, with source-term filtering and prepare-only
safety covered by the focused Ads tests.
Custom-segment construction is now isolated in `_custom_segment_action(...)`,
keeping Google Ads source filtering and the prepare-only boundary intact.
Negative-keyword construction is now isolated in `_negative_keyword_action(...)`,
keeping the search-term evidence gate and 90-day safety review intact.
Localo visibility-review construction is now isolated in
`_localo_visibility_review_action(...)`, keeping prioritized metrics and
GBP/ranking blockers intact.
GA4 tracking-quality construction is now isolated in
`_ga4_tracking_quality_action(...)`, keeping evidence selection and blocked
conversion/ROAS claims intact.
Merchant feed-issue construction is now isolated in
`_merchant_feed_issue_action(...)`, keeping issue clusters, preview contract,
blocked claims and `apply_allowed=false` intact.
The first constructor has now moved out of `service.py`: GA4 tracking-quality
construction lives in `wilq/actions/ga4/tracking_quality.py`, with the service
delegating to the domain module and focused checks green.
Merchant feed-issue construction now lives in `wilq/actions/merchant.py`; the
service delegates and retains the preview contract and write blocker.
Localo visibility-review construction now lives in
`wilq/actions/localo/visibility.py`; the service delegates and retains the
metric prioritization and GBP/ranking blockers.
Custom-segment construction now lives in
`wilq/actions/google_ads/custom_segments.py`; the service delegates and retains
the source-term evidence gate and prepare-only safety.
Negative-keyword construction now lives in
`wilq/actions/google_ads/negative_keywords.py`; the service delegates and
retains the search-term evidence gate and 90-day safety review.
Campaign-review construction now lives in
`wilq/actions/google_ads/campaign_review.py`; the service delegates and retains
campaign/evidence filtering and budget safety.
Recommendation-review construction now lives in
`wilq/actions/google_ads/recommendations.py`; the service delegates and retains
evidence filtering and review-before-acceptance safety.
Change-history impact construction now lives in
`wilq/actions/google_ads/change_history.py`; the service delegates and retains
event/evidence filtering and prepare-only safety.
Search-term n-gram construction now lives in
`wilq/actions/google_ads/search_term_ngrams.py`; the service delegates and
retains source-term selection and no-automatic-exclusions safety.
Content-refresh queue construction now lives in
`wilq/actions/content_refresh.py`; the service delegates and retains fallback
payload, evidence and WordPress review gates.
The current complexity audit puts `service.py` at 6,009 LOC and confirms that
the metric seeder has no inline `ActionObject` constructors left. The next
dominant seam is `_demand_gen_readiness_review_action`.
The final Demand Gen readiness ActionObject constructor now lives in
`wilq/actions/google_ads/demand_gen.py`; the service retains contract/evidence
calculation and delegates the domain construction.
The latest complexity audit reports `service.py` at 5,990 LOC. The next
separate target is Beads `wilq-seo-kgvy` for
`wilq/briefing/ads_diagnostics.py` (7,144 non-empty LOC), which must be treated
as a separate bounded slice.
That slice has started: the Ads change-history section builder now lives in
`wilq/briefing/ads_change_history.py`; focused Ads contracts and static checks
are green with the view-model and blockers unchanged.
The second `kgvy` seam moved the Ads recommendations section builder into
`wilq/briefing/ads_recommendations.py`; evidence, blockers and action IDs remain
unchanged.
The third `kgvy` seam moved the Ads impression-share section builder into
`wilq/briefing/ads_impression_share.py`; read-contract and blocked budget/traffic
claims remain unchanged.
The fourth `kgvy` seam moved the Ads budget-pacing section builder into
`wilq/briefing/ads_budget_pacing.py`; pacing evidence and budget-change blockers
remain unchanged.
The fifth `kgvy` seam moved Ads search-terms and n-gram section builders into
`wilq/briefing/ads_search_terms.py`; action filtering and blocked exclusion
claims remain unchanged.
The sixth `kgvy` seam moved the Ads 90-day search-term safety section builder
into `wilq/briefing/ads_search_terms.py`; long-window evidence and no-write
blockers remain unchanged.
The seventh `kgvy` seam moved the Ads keyword-match context section builder into
`wilq/briefing/ads_search_terms.py`; source context and no-exclusion blocker
remain unchanged.
The eighth `kgvy` seam moved the Keyword Planner section builder into
`wilq/briefing/ads_keyword_planner.py`; access-action filtering and blocked
forecast/audience claims remain unchanged.
The ninth `kgvy` seam moved the Ads custom-segments section builder into
`wilq/briefing/ads_custom_segments.py`; source-term-only policy and blocked
audience-size/effectiveness claims remain unchanged.
The tenth `kgvy` seam moved the Ads negative-keyword safety section builder into
`wilq/briefing/ads_negative_keywords.py`; 90-day/write blockers and evidence
remain unchanged.
The eleventh `kgvy` seam moved the Ads campaign-overview section builder into
`wilq/briefing/ads_campaigns.py`; campaign evidence, action filtering and
blocked claims remain unchanged.
The twelfth `kgvy` seam moved the Ads derived-KPI section builder into
`wilq/briefing/ads_campaigns.py`; calculated KPI presentation and blocked
ROAS/CPA/budget claims remain unchanged.
The thirteenth `kgvy` seam moved the Ads business-context section builder into
`wilq/briefing/ads_campaigns.py`; operator-contract separation and blocked
ROAS/budget claims remain unchanged.
The fourteenth `kgvy` seam extracted the first `_ads_decision_queue`
campaign-activity decision builder into `wilq/briefing/ads_decision_queue.py`;
missing contracts, evidence and lineage remain unchanged.
The fifteenth `kgvy` seam extracted the campaign-triage decision builder into
`wilq/briefing/ads_decision_queue.py`; triage rows, review gates and blocked
budget/efficiency claims remain unchanged.
The sixteenth `kgvy` seam extracted the derived-KPI decision builder into
`wilq/briefing/ads_decision_queue.py`; focused verification caught and removed
an invalid `metric_facts` assumption on `AdsDerivedKpiRow`.
The seventeenth `kgvy` seam extracted the budget-context decision builder into
`wilq/briefing/ads_decision_queue.py`; budget rows, shared-budget data and
scaling blockers remain unchanged.
The eighteenth `kgvy` seam extracted the recommendations decision builder into
`wilq/briefing/ads_decision_queue.py`; recommendation rows, preview, review gates
and no-write claims remain unchanged.
The nineteenth `kgvy` seam extracted the change-history decision builder into
`wilq/briefing/ads_decision_queue.py`; event rows, evidence and no-impact claims
remain unchanged.
The twentieth `kgvy` seam extracted the search-terms decision builder into
`wilq/briefing/ads_decision_queue.py`; source rows, action filtering and
no-automatic-exclusions safety remain unchanged.
The twenty-first `kgvy` seam extracted the search-term n-gram decision builder
into `wilq/briefing/ads_decision_queue.py`; priority, metric tiles, top rows and
blocked exclusion claims remain unchanged.
The twenty-second `kgvy` seam extracted the negative-keyword safety decision
builder into `wilq/briefing/ads_decision_queue.py`; current/safety/context
evidence and no-write blockers remain unchanged.

Current product priority remains the content workspace; cleanup must not take
precedence over a user-directed marketer-facing product slice.

`wilq-seo-ho41` is in progress. The first seam extraction moved dev target
matching and URL normalization to `apps/dashboard/src/routes/contentWorkflowTarget.ts`.
The workbench now has explicit dev target selection and a compact
current-vs-proposed section disclosure, both preview-only. It still needs
existing-draft update semantics and the remaining component boundaries. The
queue, ACF comparison and source-status strip now live in focused React files.
`wilq-seo-50wa.11` is closed: the smallest ActionObject evidence contract test
now lives outside the action mega-file, with the focused and remaining action
tests green.
`wilq-seo-3bst.21` is also closed: `/actions/:actionId` is decision-first in
normal Polish, exposes write blockers and evidence before technical details,
and its merchant-feed blocked-write path is covered by
`ActionDetailRoute.test.tsx`.
The latest live queue check still reports `queue_status=blocked`, with 1 of 2
candidates actionable and evidence from GSC, WordPress and Ahrefs. The
`/content-workflow` focused route/target tests pass (16 tests) and dashboard
TypeScript passes; this confirms the current preview seams without implying
that the missing existing-draft/ACF update contract is implemented.

The broader active objective is not complete. It still includes senior-grade
cleanup of the Beads audit graph and a fully useful `/content-workflow`
workspace. This file does not mark that objective done; it freezes the current
checkpoint so the next model/session can resume deliberately instead of
continuing an uncontrolled split.

Latest live API check: DuckDB is enabled with 95,532 metric facts and 4,425
refresh runs; the content queue remains blocked at 1 of 2 actionable candidates.

Current live check after eval refresh: DuckDB reports 95,622 metric facts and
4,460 refresh runs. All 13 skill evals are fresh/passing and the strict coverage
audit has no gaps or warnings. The full verify run reached 760 backend tests;
dashboard tests are 136/136. A late Goal 005 stale-artifact failure caused by
the final Ads output-contract wording edit was repaired by refreshing the Ads
eval; the targeted Goal 005 gate now passes.

The final dashboard suite is green at 23 files / 136 tests after replacing
stale English and `claimy` assertions with the current Polish operator labels.

The first existing-draft/ACF update seam now exists as an API-owned typed
readiness contract (`GET /api/content/wordpress/existing-draft-update-readiness`)
and focused test. It is intentionally blocked until the reviewed ActionObject
update adapter is implemented; no write capability is claimed.

The readiness seam now has a separate `act_prepare_wordpress_existing_draft_update`
ActionObject. Validation succeeds, preview is dry-run/audit-backed, and the
preview remains blocked with `mutation_allowed=false`; the ActionObject does
not call WordPress.

Review-to-confirm is covered for the prepare-only action: review writes an
audit event, confirmation records the preview acknowledgement, and the review
gate still reports `apply_allowed=false`.

The content workbench now reads this readiness contract and surfaces its blocker
next to the dev draft action, so the missing update capability is visible in the
marketer workflow rather than hidden in technical API details.

The new WordPress update ActionObject seed was also extracted from the core
action registry into a named `_wordpress_existing_draft_update_action()` helper;
its payload and safety behavior are unchanged.

The latest `scripts/verify.sh` run passes Ruff, dashboard lint, marketer
language hygiene and type checking, then reaches the full pytest stage: 753
passed, 2 skipped and 7 failures. The Ahrefs contract's three stale assertions
were aligned with the intentional `GSC i WordPress` wording. Remaining failures
are explicit Goal 005, WordPress write-gate, Localo smoke and endpoint-copy
follow-up work; no green full-verification claim is made until those are fixed
or deliberately isolated.

The targeted regression suite covering Goal 005, endpoint language, Localo,
WordPress authorization and Ahrefs wording is now green. Goal 005 is not
falsely promoted: its report now has all 13 fresh passing evals. The custom
segment eval case was corrected to match the API's actual `google_ads` evidence
source; no unsupported GSC provenance is claimed.

## Why this cleanup exists

The repo audit found real senior-grade problems:

- `tests/test_api_contracts.py` was a 21k-line mega-test mixing unrelated
  domains.
- the `wilq/schemas/` compatibility module, `wilq/actions/service.py`, Ads diagnostics and dashboard
  route files are still oversized.
- Several tests preserve implementation wording and old surface shape instead
  of product behavior.
- Dashboard/product work must stay API-owned and marketer-useful, not become
  more card spam or guard theater.

## Completed in the current cleanup run

Closed Beads:

- `wilq-seo-c2lf` - frozen growth gate policy recorded.
- `wilq-seo-y0o5` - Python runtime/test standards recorded.
- `wilq-seo-50wa.1` - security/redaction/connector tests extracted.
- `wilq-seo-50wa.2` - content workflow and WordPress contract tests extracted.
- `wilq-seo-50wa.3` - ActionObject safety tests extracted.
- `wilq-seo-50wa.4` - Command Center and marketing brief tests extracted.
- `wilq-seo-50wa.5` - GA4, Localo and Ahrefs diagnostics tests extracted.
- `wilq-seo-50wa.6` - Ads diagnostics and Google Ads vendor-read tests extracted.
- `wilq-seo-50wa.7` - Merchant diagnostics and vendor-read tests extracted.
- `wilq-seo-50wa.8` - non-Ads vendor refresh tests extracted.
- `wilq-seo-50wa.9` - focused API-contract support factories extracted and
  dynamic legacy test-module imports removed.
- `wilq-seo-50wa.10` - social, demand-gen, knowledge and workflow tests extracted.
- `wilq-seo-b4kg.1` - schema package conversion and shared schema-core
  extraction behind the compatible `wilq.schemas` import path.
- `wilq-seo-b4kg.2` - ActionObject, knowledge and marketing schema domains
  extracted behind the same compatibility facade.
- `wilq-seo-b4kg.3` - Ads and Demand Gen schema domains extracted behind the
  same compatibility facade.
- `wilq-seo-b4kg.4` - Merchant, Content, GA4, Localo, Ahrefs and Command
  Center/Daily Check schema domains extracted behind the same facade.

Also completed before this handoff:

- Active `/content-planner` / `ContentDiagnosticSurface` runtime cleanup is
  treated as done for current surfaces. `/content-workflow` is the primary
  content route.
- Current docs were updated so active non-archive references to
  `/content-planner`, `ContentDiagnosticSurface` and `/seo-gsc` are either gone
  or explicitly historical/negative.
- `AGENTS.md` recovery index points to this file before `docs/dashboard-state.md`.

Created or updated key files:

- `docs/architecture/python-runtime-and-test-standards.md`
- `tests/api_contracts/test_security_connector_contracts.py`
- `tests/api_contracts/test_redaction_contracts.py`
- `tests/actions/test_action_object_contracts.py`
- `tests/api_contracts/test_command_center_contracts.py`
- `tests/api_contracts/test_source_diagnostics_contracts.py`
- `tests/api_contracts/test_ads_contracts.py`
- `tests/api_contracts/test_merchant_contracts.py`
- `tests/api_contracts/test_vendor_read_contracts.py`
- `tests/api_contracts/test_content_workflow_contracts.py`
- `tests/api_contracts/test_operator_context_and_knowledge_contracts.py`
- `tests/_contract_support/` focused API-client, environment, assertion and
  domain-seed leaves.
- `wilq/schemas/__init__.py` compatibility façade and `wilq/schemas/core.py`
  shared schema foundation.
- `tests/test_schema_package_compatibility.py`

## Current test_api_contracts.py state

Before this run:

- `tests/test_api_contracts.py`: more than 21k physical lines.

After this run:

- `tests/test_api_contracts.py`: 1857 physical lines.

The old file now contains core evidence/opportunity/daily-runtime/context-pack
contract tests. Reusable support moved into small domain leaves rather than a
single fixture module.

## Test-support seam

The transitional dynamic import bridge is removed. Extracted test modules import
their product symbols directly and consume only the needed support leaf:

- `tests/_contract_support/api_client.py`
- `tests/_contract_support/env.py`
- `tests/_contract_support/assertions.py`
- `tests/_contract_support/action_candidate_seed.py`
- `tests/_contract_support/ads_review_seed.py`

There is intentionally no re-export barrel or giant shared fixture object.
`rg` confirms no `importlib`, `globals().update`, or
`tests.test_api_contracts` bridge remains under the extracted contract tests or
their support package.

## Schema package seam

`wilq.schemas` is now a package, so the 90+ runtime consumers keep their
existing `from wilq.schemas import ...` imports. `wilq/schemas/core.py` owns
the acyclic shared enums, connector/evidence refresh contracts, metric facts,
opportunity base model and their label helpers. `actions.py`, `knowledge.py`,
`marketing.py`, `ads.py`, `merchant.py`, `content.py`, `ga4.py`, `localo.py`,
`ahrefs.py` and `command.py` now own their respective contract groups.
`wilq/schemas/__init__.py` is a 12-line compatibility façade.

No schema leaf imports `wilq.schemas`, preventing a re-export cycle. The
existing `/content-workflow` route label remains in `knowledge.py` unchanged.
Content workflow call sites still use the public facade; no product behavior
was migrated as part of the schema split.

## Verification completed

Focused checks passed during the cleanup:

```bash
rtk uv run pytest tests/actions/test_action_object_contracts.py \
  tests/test_api_contracts.py::test_command_center_returns_valid_shape \
  tests/test_api_contracts.py::test_ga4_diagnostics_exposes_landing_quality_contract -q

rtk uv run pytest tests/api_contracts/test_command_center_contracts.py \
  tests/test_api_contracts.py::test_ga4_diagnostics_exposes_landing_quality_contract -q

rtk uv run pytest tests/api_contracts/test_source_diagnostics_contracts.py -q
rtk uv run pytest tests/api_contracts/test_ads_contracts.py -q
rtk uv run pytest tests/api_contracts/test_merchant_contracts.py -q
rtk uv run pytest tests/api_contracts/test_vendor_read_contracts.py -q
rtk uv run pytest tests/api_contracts/test_content_workflow_contracts.py -q
rtk uv run pytest tests/api_contracts/test_operator_context_and_knowledge_contracts.py -q
rtk uv run pytest tests/api_contracts tests/actions/test_action_object_contracts.py tests/test_api_contracts.py -q
rtk git diff --check
```

The last combined pytest command passed. `git diff --check` also passed.

Verification for `wilq-seo-50wa.9` on 2026-07-10:

```bash
rtk uv run ruff format tests/_contract_support
rtk uv run ruff check tests/_contract_support tests/test_api_contracts.py \
  tests/api_contracts/test_ads_contracts.py \
  tests/api_contracts/test_command_center_contracts.py \
  tests/api_contracts/test_content_workflow_contracts.py \
  tests/api_contracts/test_merchant_contracts.py \
  tests/api_contracts/test_operator_context_and_knowledge_contracts.py \
  tests/api_contracts/test_source_diagnostics_contracts.py \
  tests/api_contracts/test_vendor_read_contracts.py \
  tests/actions/test_action_object_contracts.py
rtk uv run pytest tests/api_contracts \
  tests/actions/test_action_object_contracts.py tests/test_api_contracts.py -q
rtk rg -n 'importlib|globals\\(\\)\\.update|tests\\.test_api_contracts' \
  tests/api_contracts tests/actions tests/_contract_support
rtk git diff --check
rtk uv run python scripts/audit_complexity.py --changed --summary --limit 12 \
  --allow-frozen
```

The full pytest invocation passed. The negative `rg` scan returned no matches.
The strict complexity audit still reports global changed-file debt from the
broader dirty worktree, but no support leaf is a budget violation; the old
mega-test fell from 2611 to 1857 physical lines in this slice.

The latest small extraction moved the `/api/system/status` contract into
`tests/api_contracts/test_system_status_contracts.py`; its focused pytest and
Ruff checks pass. The command-center evidence mapping contract now also lives
in `tests/api_contracts/test_command_center_evidence_contracts.py`. Opportunity
source/evidence validation is now also isolated in
`tests/api_contracts/test_opportunity_contracts.py`; the legacy file is 1789
LOC.
Evidence registry secret-redaction coverage is now isolated in
`tests/api_contracts/test_evidence_registry_contracts.py`; the legacy file is
1766 LOC.
Metric-context dimension-label coverage is now isolated in
`tests/api_contracts/test_metric_context_contracts.py`; its focused tests and
Ruff checks pass. Google Ads operator-dimension labels are covered in the same
module; the legacy file is now 1670 LOC.
Context-pack anti-invention and secret-redaction coverage is now isolated in
`tests/api_contracts/test_context_safety_contracts.py`; its focused pytest and
Ruff checks pass, leaving the legacy file at 1653 LOC.
Daily-check traceability validation is now isolated in
`tests/api_contracts/test_daily_check_contracts.py`; its focused pytest and
Ruff checks pass, leaving the legacy file at 1602 LOC.
Connector evidence operator-language coverage is now isolated in
`tests/api_contracts/test_evidence_language_contracts.py`; its focused pytest
and Ruff checks pass, leaving the legacy file at 1581 LOC.
Targeted metric-fact evidence lookup coverage is now isolated in
`tests/api_contracts/test_evidence_metric_registry_contracts.py`; its focused
pytest and Ruff checks pass, leaving the legacy file at 1534 LOC.
Action-to-registered-evidence integrity coverage is now isolated in
`tests/api_contracts/test_action_evidence_registry_contracts.py`; its focused
pytest and Ruff checks pass, leaving the legacy file at 1523 LOC.
Connector refresh redaction coverage is now isolated in
`tests/api_contracts/test_connector_refresh_redaction_contracts.py`; its
focused pytest and Ruff checks pass, leaving the legacy file at 1476 LOC.
Action recommended-reason marketer-language coverage is now isolated in
`tests/api_contracts/test_action_operator_language_contracts.py`; its focused
pytest and Ruff checks pass, leaving the legacy file at 1444 LOC.
Localo marketer-language metric headline coverage is now isolated in
`tests/api_contracts/test_localo_marketing_language_contracts.py`; its focused
pytest and Ruff checks pass, leaving the legacy file at 1367 LOC.
Localo access-blocker marketer copy coverage now joins that module; both tests
pass and the legacy file is 1315 LOC.
Daily context-pack action-summary compaction coverage now joins
`tests/api_contracts/test_context_safety_contracts.py`; both focused tests and
Ruff checks pass, leaving the legacy file at 1281 LOC.
The full combined contract verification (`tests/api_contracts
tests/test_api_contracts.py`) also passes after the current extraction batch.
Campaign-builder context-pack scoping coverage is now isolated in
`tests/api_contracts/test_campaign_builder_context_contracts.py`; its focused
pytest and Ruff checks pass, leaving the legacy file at 1228 LOC.
Ads recommendation impact-row preservation is now isolated in
`tests/api_contracts/test_ads_recommendation_context_contracts.py`; its focused
pytest and Ruff checks pass, leaving the legacy file at 1193 LOC.
Ads summary-diagnostics selection coverage now joins that module; both tests
pass and the legacy file is 1160 LOC.
The full combined contract regression passes again after this Ads extraction
batch.
The current complexity audit still reports 83 changed-code budget violations
across the dirty worktree. The largest remaining hotspots are Ads diagnostics,
the action service, the Ads contract test and the ActionObject contract test;
they remain open Beads work and are not silently waived.
A small route-label fallback contract is now isolated in
`tests/actions/test_route_label_contracts.py`; the larger ActionObject label
fallback test remains open because it spans many domain label dependencies.
Ads vendor-label fallback coverage is now isolated in
`tests/actions/test_ads_operator_label_contracts.py`; its focused pytest and
Ruff checks pass, leaving the ActionObject mega-test at 3522 LOC.
Ads entity display-label/raw-ID protection now joins that module; both tests
pass and the ActionObject mega-test is 3432 LOC.
Ads helper-label fallback coverage now also joins that module; three tests pass
and the ActionObject mega-test is 3400 LOC.
Missing-domain/content status-label contracts are now isolated in
`tests/actions/test_domain_status_label_contracts.py`; focused pytest and Ruff
checks pass, leaving the ActionObject mega-test at 3383 LOC.
Localo missing-status label coverage now joins that module; three tests pass
and the ActionObject mega-test is 3373 LOC.
The full `tests/actions` regression and Ruff checks pass after these
extractions; ActionObject safety behavior remains green.
Validation-vs-human-review copy coverage is now isolated in
`tests/actions/test_action_validation_contracts.py`; its focused pytest and
Ruff checks pass, leaving the ActionObject mega-test at 3348 LOC.
Dry-run preview/audit safety coverage is now isolated in
`tests/actions/test_action_preview_contracts.py`; its focused pytest and Ruff
checks pass, leaving the ActionObject mega-test at 3310 LOC.
The full `tests/actions` regression and Ruff checks pass again after the
preview extraction; ActionObject safety behavior remains green.
Content preview-only brief payload coverage now joins
`tests/actions/test_action_preview_contracts.py`; both tests pass and the
ActionObject mega-test is 3270 LOC.
Human-review audit-without-apply coverage is now isolated in
`tests/actions/test_action_review_contracts.py`; its focused pytest and Ruff
checks pass, leaving the ActionObject mega-test at 3213 LOC.
Confirmation-without-preview blocking coverage is now isolated in
`tests/actions/test_action_confirmation_contracts.py`; its focused pytest and
Ruff checks pass, leaving the ActionObject mega-test at 3177 LOC.
Preview-confirmation-without-apply coverage now joins that module; both tests
pass and the ActionObject mega-test is 3124 LOC.
Impact-check-before-confirmation blocking coverage now joins that module;
three tests pass and the ActionObject mega-test is 3090 LOC.
The full `tests/actions` regression and Ruff checks pass after moving review
contracts; ActionObject safety behavior remains green.

Verification for `wilq-seo-b4kg.1` on 2026-07-10:

```bash
rtk uv run pytest tests/test_connector_status_labels.py \
  tests/test_metric_store_and_cli.py tests/test_jobs_scheduler.py \
  tests/api_contracts/test_vendor_read_contracts.py -q
rtk uv run pytest tests/actions/test_action_object_contracts.py \
  tests/api_contracts/test_command_center_contracts.py \
  tests/api_contracts/test_operator_context_and_knowledge_contracts.py -q
rtk uv run pytest tests/api_contracts \
  tests/actions/test_action_object_contracts.py tests/test_api_contracts.py \
  tests/test_schema_package_compatibility.py -q
rtk uv run ruff check wilq/schemas scripts/audit_complexity.py \
  scripts/marketer_language_guard.py tests/test_audit_complexity.py \
  tests/test_marketer_language_guard.py tests/test_schema_package_compatibility.py
rtk uv run mypy wilq/schemas
rtk uv run python -c 'from apps.api.wilq_api.main import app; assert app.openapi()'
rtk scripts/local_stack.sh restart
rtk curl -sS -m 10 http://127.0.0.1:8000/api/health
rtk curl -sS -m 10 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/openapi.json
rtk git diff --check
```

Those checks passed, including live API health and OpenAPI `200`. The strict
complexity audit remains non-green in the broader dirty worktree. It now also
names the already oversized `scripts/marketer_language_guard.py` because this
slice changed its source root from a file to the schema package; that update is
covered by a focused guard test and must not be mistaken for a clean parent
completion.

Verification for `wilq-seo-b4kg.2` on 2026-07-10:

```bash
rtk uv run pytest tests/api_contracts tests/actions/test_action_object_contracts.py \
  tests/test_api_contracts.py tests/test_schema_package_compatibility.py -q
rtk uv run ruff check wilq/schemas scripts/audit_complexity.py \
  scripts/marketer_language_guard.py tests/test_schema_package_compatibility.py \
  tests/test_audit_complexity.py tests/test_marketer_language_guard.py
rtk uv run mypy wilq/schemas
rtk rg -n 'from wilq\\.schemas import|import wilq\\.schemas' wilq/schemas
rtk scripts/local_stack.sh restart
rtk curl -sS -m 10 http://127.0.0.1:8000/api/health
rtk curl -sS -m 10 -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/openapi.json
rtk git diff --check
```

The full contract suite, package checks, import-cycle scan, live health and
OpenAPI `200` passed. The global complexity audit still reports the known
dirty-worktree violations; this tranche reduces the compatibility facade from
4484 to 3402 non-empty LOC.

Verification for `wilq-seo-b4kg.3` on 2026-07-10:

```bash
rtk uv run pytest tests/api_contracts/test_ads_contracts.py \
  tests/actions/test_action_object_contracts.py -q
rtk uv run pytest tests/api_contracts tests/actions/test_action_object_contracts.py \
  tests/test_api_contracts.py tests/test_schema_package_compatibility.py -q
rtk uv run ruff check wilq/schemas
rtk uv run mypy wilq/schemas
rtk rg -n 'from wilq\\.schemas import|import wilq\\.schemas' wilq/schemas
rtk scripts/local_stack.sh restart
rtk curl -sS -m 10 http://127.0.0.1:8000/api/health
rtk curl -sS -m 10 -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/openapi.json
rtk git diff --check
```

All checks passed. The compatibility facade now measures 1539 non-empty LOC;
`ads.py` owns 1891 non-empty LOC and is a domain-sized seam for later tuning.

Verification for `wilq-seo-b4kg.4` on 2026-07-10:

```bash
rtk uv run pytest tests/api_contracts tests/actions/test_action_object_contracts.py \
  tests/test_api_contracts.py tests/test_schema_package_compatibility.py -q
rtk uv run ruff check wilq/schemas
rtk uv run mypy wilq/schemas
rtk rg -n 'from wilq\\.schemas import|import wilq\\.schemas' wilq/schemas
rtk scripts/local_stack.sh restart
rtk curl -sS -m 10 http://127.0.0.1:8000/api/health
rtk curl -sS -m 10 -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/openapi.json
rtk git diff --check
```

All checks passed. The compatibility facade is now 12 physical lines and all
remaining schema domains are explicit siblings.

Additional verification completed after route-doc cleanup:

```bash
rtk rg -n "content-planner|ContentDiagnosticSurface|content_planner|/seo-gsc" \
  apps tests docs .agents packages wilq AGENTS.md PLANS.md PLAN.md \
  --glob '!docs/audits/**' \
  --glob '!docs/handoffs/**' \
  --glob '!docs/archive/**' \
  --glob '!docs/progress/archive/**' \
  --glob '!docs/goals/archive/**'

rtk pnpm --dir apps/dashboard typecheck
rtk git diff --check
```

Expected remaining active `rg` hits are only negative/historical reminders:

- this file warning not to bring back `/content-planner`;
- historical note in `docs/evals/skill-eval-ledger.md` about old `/seo-gsc`.

## Test updates made during extraction

`tests/api_contracts/test_vendor_read_contracts.py` was updated to match the
current WordPress read-only contract:

- WordPress REST now requests `content`, `acf` and `template` in `_fields`.
- WordPress content/sitemap facts may expose extra dimensions such as ACF field
  count, block names and section headings.
- The test now asserts required dimensions as a subset instead of blocking
  useful extra read-only fields.

This is aligned with the content workspace goal: WILQ needs real WordPress/ACF
structure, not only title/link inventory.

## Still open / do not forget

Main open cleanup task:

- `wilq-seo-50wa` remains open because the legacy test file is still above its
  changed-file budget and several extracted test files retain giant test bodies.

Next best task when cleanup resumes:

- continue the primary product slice `wilq-seo-ho41`: split the content
  workbench into route orchestration, target selection, current-vs-proposed ACF
  values and draft editing boundaries; do not reopen the removed dynamic bridge.
- schema package extraction is complete; do not reopen the compatibility facade
  unless a concrete import or OpenAPI regression appears.

Other major cleanup tasks still open:

- `wilq-seo-jnra` - split `wilq/actions/service.py`.
- `wilq-seo-kgvy` - split Ads diagnostics.
- `wilq-seo-pidl` - split `apps/dashboard/src/routes/App.test.tsx`.
- `wilq-seo-ho41` - split `ContentWorkflowSurface.tsx`.
- `wilq-seo-0q74` - extract shared skill smoke harness.
- `wilq-seo-co30` - prune docs truth and archive stale progress ledgers.

The user has resumed cleanup, but choose the next Beads-backed slice
deliberately; do not let this completion expand into an unrelated broad split.

The goal should not be marked complete until the original objective is proven:
`/content-workflow` is genuinely marketer-first and useful, active legacy
content surfaces are gone, dashboard state/docs/Beads/tests agree, and the
senior cleanup graph has been completed or explicitly reprioritized by the
user.

## Current known risk

The cleanup reduced one mega-test but did not solve the whole repo.

Current complexity snapshot after extraction still reports:

- `wilq/briefing/ads_diagnostics.py`: 7144 LOC.
- `wilq/actions/service.py`: 6226 LOC.
- `tests/api_contracts/test_ads_contracts.py`: 4937 LOC.
- `wilq/schemas/__init__.py`: 12 physical lines (compatibility façade only).
- `wilq/schemas/core.py`: 522 physical lines, under the changed-file budget.
- `wilq/schemas/actions.py`: 436 physical lines.
- `wilq/schemas/knowledge.py`: 444 physical lines.
- `wilq/schemas/marketing.py`: 405 physical lines.
- `wilq/schemas/ads.py`: 1891 non-empty LOC / 2070 physical lines.
- `wilq/schemas/merchant.py`: 305 non-empty LOC / 333 physical lines.
- `wilq/schemas/content.py`: 309 non-empty LOC / 338 physical lines.
- `wilq/schemas/ga4.py`: 178 non-empty LOC / 197 physical lines.
- `wilq/schemas/localo.py`: 148 non-empty LOC / 165 physical lines.
- `wilq/schemas/ahrefs.py`: 213 non-empty LOC / 234 physical lines.
- `wilq/schemas/command.py`: 384 non-empty LOC / 428 physical lines.
- `tests/test_api_contracts.py`: 1705 non-empty LOC / 1857 physical lines.
- `tests/_contract_support/action_candidate_seed.py` and
  `tests/_contract_support/ads_review_seed.py` are focused leaves below the
  function-size budget; the strict audit no longer lists either as a violation.
- `tests/actions/test_action_object_contracts.py`: 3472 LOC.

Large extracted files are acceptable only as a temporary stopgap. They should
be split further only after shared factories exist, otherwise cleanup will
duplicate fixture mess.

## Current worktree risk

The worktree contains many modified files from earlier dashboard/API/content
and cleanup work. Treat them as in-progress project state, not disposable
noise. Do not run destructive git commands. Do not revert unrelated changes.

Important dirty areas currently include:

- dashboard route and test changes;
- content workflow API/schema/workflow changes;
- WordPress authoring/execution changes;
- Beads issue/interactions files;
- docs and audit files;
- extracted test files under `tests/api_contracts/` and `tests/actions/`.

Before any future code work, run:

```bash
rtk git status --short
rtk git diff --stat
```

Then inspect the relevant file diffs before editing.

## Dashboard/content warning

The user's current product priority remains the content workspace/dashboard:

- The target is a clean marketer-facing content workspace based on real public
  page sections, dev WordPress/ACF sections, GSC signals, Ahrefs support and
  a usable editor/preview.
- Do not bring back `/content-planner`.
- Do not add card spam, generic safety paragraphs or technical copy above the
  fold.
- Do not show "WILQ sees candidates" style copy; show real pages, sections,
  signals, editor state and actions.

The desired `/content-workflow` direction is still:

- one marketer-facing workspace for public `ekologus.pl` / `sklep.ekologus.pl`
  evidence and dev `ekologus.dev.proudsite.pl` writing;
- real public page sections and real dev ACF/WordPress sections;
- GSC/Ahrefs/WP signals presented as page/section context, not report prose;
- editor/preview/draft action above technical details;
- technical audit details collapsed below the first working screen.

Target mockup reference:

- `docs/audits/dashboard-visualization/content-workflow-target-mockup.png`

Current implementation is not yet at that visual/product bar. Do not claim that
it is finished.

## Working tree caveat

The worktree is dirty with many unrelated dashboard/API/doc changes that were
already present or came from previous slices. Do not revert them casually.
Future work should inspect current diffs before editing the same files.

## Next session start command set

If the user resumes cleanup or asks for status, start with:

```bash
rtk sed -n '1,320p' docs/current-cleanup-state.md
rtk sed -n '1,220p' docs/dashboard-state.md
rtk git status --short
rtk bd ready --json
```

If the user asks only to continue product/UI work, do not start with broad repo
cleanup. Start from `/content-workflow`, the target mockup and the real
WordPress/GSC/Ahrefs/dev data path.
