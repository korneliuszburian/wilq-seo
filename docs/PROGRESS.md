# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. To ma być krótki recovery ledger, nie pełny changelog.

Pełne archiwa:

- `docs/progress/archive/2026-06-19-progress-ledger.md`
- `docs/progress/archive/2026-06-23-progress-ledger.md`

## Maintenance Rule

- Trzymaj tutaj aktualny stan, ostatnie 3-5 ważnych faktów, aktywne luki i
  następny krok.
- Nie dopisuj setek linii historii. Starsze wpisy przenoś do
  `docs/progress/archive/`.
- Git, goal i dedykowane ledgery są źródłem długiej historii. Ten plik ma
  pomagać po utracie contextu.

## Current Readout

Data: 2026-06-23

Stan produktu:

- Active goal: `docs/goals/001-goal.md`.
- WILQ API is the system brain. Dashboard and Codex skills must use the same
  typed WILQ API contracts, evidence IDs, ActionObject IDs and source
  connectors.
- Local stack: `scripts/local_stack.sh start|stop|restart|status|logs`.
  Canonical URLs: API `http://127.0.0.1:8000`, dashboard
  `http://127.0.0.1:5173/command-center`.
- Operator-facing output must be Polish with Polish diacritics.
- Do not fix reasoning/product behavior by adding edge-case workaround prose to
  skill references. Fix typed API/schema/view-model/eval contracts first.
- Ekologus is the depth-first reference client. Multi-client/agency scale comes
  after Ekologus works deeply.

## Latest Important Facts

- Goal and progress were compacted on 2026-06-23 to remove ready/done task
  noise from active recovery docs. Historical proof remains in git history and
  `docs/progress/archive/`.
- Skill eval schema/harness now requires `decision_quality`: actionable
  decision, safe next step, blocked-claims handling, workflow-specific
  interpretation and evidence-backed reasoning. Live proof:
  `.local-lab/evals/codex-skill/20260623T191904Z/wilq-daily-command/result.json`.
- Content/GSC inventory matching no longer marks current Ekologus URLs as
  missing when wide WordPress inventory pushes public sitemap URLs past the old
  slice boundary. Live HTTP proof after stack restart:
  `/api/content/diagnostics` returned `query_page_count=10` and
  `matched_inventory_count=10`.
- GA4 landing inventory matching preserves dimensioned landing facts even when
  aggregate GA4 facts are noisy. Live HTTP proof after stack restart:
  `/api/ga4/diagnostics` returned `landing_group_count=10`,
  `wordpress_match_count=6`; `(not set)` rows remain measurement blockers.
- Merchant decision queue now carries review-only `payload_preview` on concrete
  feed issue decisions, including sample product IDs/titles when available and
  blocked apply/API mutation state. Focused API contract tests pass for issue
  queue and grouped reporting contexts. Live HTTP proof after stack restart:
  `/api/merchant/diagnostics` decision queue entries expose
  `merchant_feed_issue_review_preview_v1`; apply/API mutation/destructive flags
  stay false.
- Localo diagnostics now expose live aggregate facts and typed
  `read_contract_statuses`. Live HTTP proof after managed stack restart:
  `refresh_localo_a1b33cd17835` returned `live_data_available=true`,
  `visibility_fact_count=23`, `act_review_localo_visibility_facts` ready,
  `place_inventory`, `local_rankings`, `gbp_visibility`,
  `competitor_visibility` and `reviews` ready; `local_tasks` remains missing
  with explicit blocked claims. If Localo appears empty while metric store has
  facts, restart the managed stack before changing product logic.
- Skill hygiene now has a deterministic gate: `scripts/skill_hygiene_check.py`
  runs from `scripts/quality.sh`, blocks `Goal 001`/workaround/bugfix/outdated
  prose, English safety headings, English `with mode=vendor_read` endpoint notes
  English imperative workflow steps in WILQ skill docs and mixed-language
  `API identifiers` wording. WILQ `SKILL.md` and
  `references/output-contract.md` files now use Polish operator prose while
  preserving API IDs, endpoint paths and enum values.
- Live Ads blocker distinction: current `change_history_read_contract` is
  blocked because Google Ads returned zero change_event rows in the current
  window; current `keyword_planner_read_contract` is blocked by
  `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`, not by missing OAuth.
- GA4 freshness was refreshed on 2026-06-23:
  `refresh_google_analytics_4_89801bbfd735` completed, `/api/ga4/diagnostics`
  reports latest GA4 vendor_read within the 48h freshness window. GA4 still
  blocks conversion/revenue/ROAS claims until conversion/key-event/ecommerce
  contracts exist.
- Goal 001 now has a thematic stack assessment: acquisition/source proof,
  decision contracts, action safety, Codex skills, dashboard/UI and
  testing/release. Current source triage: Merchant product sample readiness and
  Localo GBP/competitor/reviews/rankings are ready for review-only decisions;
  the nearest source gaps are now Ads optimizer context, Merchant deepening,
  Ahrefs granular gaps and cross-source decision joins.
- GA4 conversion/ecommerce read contract is now live. The GA4 Data API request
  stores `key_events`, `ecommerce_purchases`, `purchase_revenue`,
  `total_revenue` and `transactions` with landing/source/campaign dimensions.
  Live proof `refresh_google_analytics_4_6acb3a6c9be8` completed; diagnostics
  and `wilq-ga4-analyst` context-pack show
  `conversion_readiness_contract.status=ready`, no missing read contracts, and
  blocked ROAS/profitability/conversion-drop claims until cost/history/
  attribution context exists.
- Latest pushed slice: `41735b4 fix(dashboard): surface ads business guardrails`.
  `/actions/act_confirm_ads_target_guardrails` and
  `/actions/act_record_ads_strategy_review` render Ads business context,
  missing target ROAS/CPA, target env options, strategy gates, validations,
  blocked claims and blocked apply/API mutation state as Polish review cards.
- Skill coverage table: `docs/evals/skill-coverage-audit.md`. Current state:
  12/12 skills have non-interactive eval artifacts; base API/evidence/Polish
  output/safety checks are covered.
- Strong demo path today:
  `/command-center` -> `/merchant` -> `/content-planner` -> `/ads-doctor` ->
  optional `/ga4` and `/localo`.

## Active Gaps

1. **Source contracts and data acquisition**
   - Current Localo supports live place inventory, local rankings and reviews as
     typed aggregate read contracts, and now also GBP visibility and competitor
     visibility aggregate read contracts.
   - Missing: Localo tasks, write/apply contracts and uplift claims. Keep
     Localo tasks blocked unless a side-effect-free read exists.
   - Source-contract queue: Ads pacing/recommendations/impression-share/change
     history context, Merchant product-performance/supplemental-feed/
     price-impact deepening and Ahrefs granular gap enrichment.
   - Ads remaining gaps are not OAuth: Keyword Planner is blocked by developer
     token approval, change history has no rows in the current window, and
     deeper optimizer value still needs pacing, recommendations safety, forecast
     and apply/audit contracts.
   - Merchant and GA4 need deeper product/conversion/commerce contracts before
     revenue, approval, ROAS or product-fix claims.

2. **Decision API and shared view-models**
   - Dashboard and skills must consume the same API contracts:
     command-center, marketing brief, tactical queue, diagnostics and actions.
   - Do not push decisions into prompt/reference prose; implement typed
     API/schema/view-model first.
   - Next decision/API work should add a shared daily decision view-model,
     stable domain queues and explicit ready/stale/blocked semantics. Avoid
     showing connector readiness as a marketing decision.

3. **Action safety and apply path**
   - Current demo is mostly prepare/review-only.
   - Future writes need dry_run, preview, confirm, audit, SafetyLimits and
     partial-failure handling before apply claims.
   - Near-term actions stay review-only: Ads negative keywords/custom
     segments/strategy, Merchant feed review, content refresh/merge/create,
     Localo/GBP and social drafts. Apply remains blocked until the matching
     preview, validation, confirmation and audit contracts exist.

4. **Skill/reference hygiene and eval quality**
   - Obvious hygiene failures are now guarded by `scripts/skill_hygiene_check.py`.
   - Repeated output-contract language wording has been normalized across WILQ
     skills.
   - Remaining: deeper semantic review of references for product logic hidden in prose.
   - References should describe contracts and output shape only; product logic,
     workaround rules and bug fixes belong in API/schema/eval.
   - Evals now cover basic API/evidence/Polish/safety, but still need stronger
     decision-quality assertions per skill.
   - Skill queue: manual + non-interactive eval per skill after its domain API
     contract is strong; upgrade evals to require concrete decisions, not only
     JSON shape; normalize dashboard prompts to Polish operator commands with
     evidence IDs, action IDs and blocked claims.

5. **Dashboard usefulness, performance and code quality**
   - Avoid broad aesthetic refactors.
   - Extract large route modules only when they block product work, reviewability
     or focused verification.
   - Focus performance work on shared daily view-model/cache and duplicated
     aggregation, not visual churn.
   - Dashboard queue: route-by-route marketer audit, Command Center as decision
     cockpit only, drilldowns for raw evidence/registries, shared route data
     boundaries and targeted extraction of large modules only when it speeds
     real slices.

6. **Release/live-test strategy**
   - Release gates should assert contracts, safety, evidence, Polish output and
     secret redaction.
   - Exact changing metric values belong in fixture tests only. Live smokes
     should assert freshness, nonempty expected facts and correct
     ready/missing/blocked status.
   - Release queue: separate fixture tests from live smokes, define a smaller
     pre-demo gate, keep full `scripts/verify.sh` for broad/final gates and add
     operational alerts for stale contracts, missing facts, unsafe apply and
     secret leakage.

## Next Best Queue

1. Work by theme: source contracts -> decision API/view-model -> ActionObject
   safety -> Codex skill/eval quality -> dashboard usefulness/performance ->
   release/live-test hardening.
2. Next concrete slice should come from live proof: Localo missing read
   `local_tasks` if a read-only contract exists, Ads optimizer blockers,
   semantic skill-reference audit or shared daily view-model/cache.
3. Do not re-add ready/done surfaces as active tasks. If a completed area looks
   wrong, reopen it only with fresh API/browser proof and a focused failing
   check.
