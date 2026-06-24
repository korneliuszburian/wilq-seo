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
- Przed dopisaniem nowych zadań usuń albo zastąp rzeczy outdated/done, jeżeli
  nie zmieniają następnej decyzji operatora. Ten plik ma zostać najmniejszym
  użytecznym recovery ledgerem.
- Git, goal i dedykowane ledgery są źródłem długiej historii. Ten plik ma
  pomagać po utracie contextu.

## Current Readout

Data: 2026-06-24

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
  `matched_inventory_count=10`. Content diagnostics now also returns a typed
  `block_until_vendor_read` decision when no GSC/WordPress/Ahrefs-backed
  content decisions exist, so skills/dashboard show a blocker instead of an
  empty queue.
- GA4 landing inventory matching preserves dimensioned landing facts even when
  aggregate GA4 facts are noisy. Live HTTP proof after stack restart:
  `/api/ga4/diagnostics` returned `landing_group_count=10`,
  `wordpress_match_count=6`; `(not set)` rows remain measurement blockers.
- Merchant decision queue now carries review-only `payload_preview` on concrete
  feed issue decisions, including sample product IDs/titles when available and
  blocked apply/API mutation state. Focused API contract tests pass for issue
  queue and grouped reporting contexts. Live HTTP proof after stack restart:
  `/api/merchant/diagnostics` decision queue entries expose
  `merchant_feed_issue_review_preview_v1` with consistent grouped
  `reported_issue_occurrences`; apply/API mutation/destructive flags stay
  false. Product samples are ready; GA4 exposes item-level product facts and
  Ads now has live `shopping_performance_view` and `shopping_product` state
  read contracts. Merchant now promotes state-only Ads joins into a review-safe
  `review_product_state_mapping` decision with
  `merchant_product_state_review_preview_v1`. Live HTTP proof after stack
  restart: `/api/merchant/diagnostics` shows 3 joined products, all
  `NOT_ELIGIBLE`, with Ads title, availability, price and Merchant issue
  context; product ROAS/revenue/fix impact and feed write remain blocked because
  no Ads/GA4 performance metrics match those products. The same decision now
  includes review-only `merchant_supplemental_feed_review_preview_v1`
  candidates with product ID, title, Merchant issue context, Ads state,
  required validation and blocked apply/API mutation. This is not a feed write
  or approval/revenue claim. Merchant diagnostics now also expose the
  `price_impact_readiness` response key with contract id
  `merchant_price_impact_readiness` and preview contract
  `merchant_price_impact_readiness_preview_v1`: live API sees 3 current Ads
  prices, 0 previous price snapshots and 0 matching product performance
  windows, so price-impact stays blocked with missing read contracts instead of
  pretending to measure price impact. `wilq-merchant-feed-operator` now consumes
  that typed contract: its deterministic smoke verifies endpoint/context-pack
  consistency for `price_impact_readiness`, required missing read contracts,
  review-only preview flags and blocked product ROAS/profitability/price-impact
  claims. Metric facts now also expose `previous_evidence_id` and
  `previous_collected_at`, and Merchant price preview rows expose current and
  previous price snapshot timestamps. Live proof still shows 3 current Ads
  prices, 0 previous price snapshots and 0 performance windows, so impact claims
  remain blocked. Merchant `product_performance_readiness` now also exposes
  `missing_read_contracts`, so dashboard and skills can distinguish state-only
  Ads joins from missing Ads/GA4 product performance contracts without deriving
  that in prompt prose.
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
  preserving API IDs, endpoint paths and enum values. Semantic audit also
  removed hardcoded Daily Command domain ranking and GA4 prompt-side item
  classification; both now consume WILQ API decision order/types, and the
  hygiene gate blocks those exact regressions.
- Ads Doctor semantic cleanup removed a long prompt-pack style evidence
  paragraph from `wilq-ads-doctor/SKILL.md`; the skill now points to typed
  `/api/ads/diagnostics` contracts such as `allowed_metrics`,
  `missing_read_contracts`, `blocked_claims`, `action_ids` and
  `payload_preview`. `scripts/skill_hygiene_check.py` now also blocks
  `Inspiracja produktowa` reference prose and body lines over 900 characters,
  so skill references cannot silently become bugfix/product-logic dumps. The
  Ads Doctor context-pack uses Ads summary diagnostics before context
  compaction; live smoke proof:
  `.local-lab/proof/skills/ads-doctor-contract-slim-smoke.json` with
  `context_pack_bytes=178744`.
- Live Ads optimizer review is ready but review-only. `/api/ads/diagnostics`
  exposes ready campaign triage, budget pacing, recommendation review,
  impression-share context, search terms, search-term safety, custom-segment
  review and negative-keyword review. Apply/API mutation remains blocked.
  Current `keyword_planner_read_contract` is blocked by
  `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`, not by missing OAuth.
  Empty `change_history_read_contract` means "ready, no changes in the selected
  window"; `change_impact_readiness_contract` remains blocked until WILQ has
  change rows plus before/after performance windows.
- Ads Shopping/PMax product performance read contract is now live. The Google
  Ads adapter queries `shopping_performance_view` by `segments.product_item_id`
  and stores `shopping_product_*` facts when rows exist. Live proof
  `refresh_google_ads_3a629caccfa3` completed with
  `shopping_product_performance_query=shopping_performance_view_last_90_days`,
  `shopping_product_performance_zero_row_lookbacks=30,90` and 0 product rows.
- Ads `shopping_product` current-state read contract is now live. Live proof
  `refresh_google_ads_72dc2a727c45` returned 500 state rows, 500 products,
  `shopping_product_state_status=ready`, `shopping_product_state_not_eligible_count=500`
  and availability values `IN_STOCK,OUT_OF_STOCK`. Merchant diagnostics now
  show state-only product joins as `blocked`, not performance-ready, and expose
  a separate state review decision for marketer triage.
- Goal 001 now has a thematic stack assessment: acquisition/source proof,
  decision contracts, action safety, Codex skills, knowledge/compiler,
  dashboard/UI and testing/release. Current source triage: Ads optimizer review,
  Merchant product sample readiness and Localo GBP/competitor/reviews/rankings
  are ready for review-only decisions; Merchant product-performance join is
  blocked by state-only/zero performance product rows, not by missing GA4/Ads
  read contracts. The nearest source gaps are Merchant before-after price
  history/performance windows, Ahrefs granular gaps, Keyword Planner approval/
  forecast and cross-source decision joins.
- GA4 conversion/ecommerce read contract is now live. The GA4 Data API request
  stores `key_events`, `ecommerce_purchases`, `purchase_revenue`,
  `total_revenue` and `transactions` with landing/source/campaign dimensions.
  Live proof `refresh_google_analytics_4_6acb3a6c9be8` completed; diagnostics
  and `wilq-ga4-analyst` context-pack show
  `conversion_readiness_contract.status=ready`, no missing read contracts, and
  blocked ROAS/profitability/conversion-drop claims until cost/history/
  attribution context exists.
- GA4 item/product read contract is now live. The GA4 adapter requests
  `itemId`, `itemName`, `itemsViewed`, `itemsAddedToCart`, `itemsCheckedOut`,
  `itemsPurchased` and `itemRevenue`; live proof
  `refresh_google_analytics_4_33a4b3fda0db` completed with 50 item rows and
  250 item-scoped metric facts. Merchant sees `ga4_item_metric_facts`, but the
  current Merchant sample IDs do not join to those GA4 item IDs.
- Goal 001 now tracks knowledge/compiler work as a separate theme: source
  ingestion, lineage, confidence/freshness, rule/card promotion and evals that
  prove external marketing standards improve WILQ decisions without turning
  skills into long prompt dumps.
- Lightweight live contract smoke now exists at `scripts/live_contract_smoke.py`.
  It checks API health, command center, marketing brief and Ads/Merchant/
  Content/GA4/Localo diagnostics for shape, evidence IDs, Polish language and
  ready/blocked state without asserting exact changing metric values. Live
  proof on 2026-06-23 returned `status=completed`, `errors=[]`.
- Command Center now uses shared `daily_decisions` as the first-screen
  decision view-model. Live `/api/dashboard/command-center` returns Merchant,
  Content, GA4 and Ads daily decisions with Polish Codex prompts, evidence IDs,
  ActionObject IDs and blocked claims; raw sections are empty on the first
  screen. Daily decisions now also carry stable `domain` identifiers:
  `merchant`, `content`, `ga4` and `google_ads`; `scripts/live_contract_smoke.py`
  asserts the field exists without checking changing live metric values.
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
   - Source-contract queue: Merchant before-after price history/performance
     windows, Ahrefs granular gap enrichment, Keyword Planner approval/forecast
     and cross-source decision joins.
   - Ads remaining gaps are not OAuth: optimizer review is ready/read-only,
     Keyword Planner is blocked by developer token approval, change history
     currently has no rows in the selected window, and apply/audit contracts
     are still required before budget, recommendation, custom-segment or
     negative-keyword mutations.
   - Merchant now has partial Ads product-state joins for Merchant samples,
     a state-only review decision, review-only supplemental-feed candidates and
     a blocked price-impact readiness contract. It still needs historical price
     snapshots and before/after performance windows before product-performance
     decisions can become useful. GA4 item facts, state-only Ads rows or zero-row
     Ads performance reads alone do not justify revenue, approval, ROAS, price
     impact or product-fix claims.

2. **Decision API and shared view-models**
   - Dashboard and skills must consume the same API contracts:
     command-center, marketing brief, tactical queue, diagnostics and actions.
   - Do not push decisions into prompt/reference prose; implement typed
     API/schema/view-model first.
   - Shared `daily_decisions` are now the canonical first-screen view-model.
     They expose stable `domain` identifiers for Merchant, Content, GA4 and Ads.
     Next decision/API work should harden stable domain queues and explicit
     ready/stale/blocked semantics. Avoid showing connector readiness as a
     marketing decision.

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
   - Ads Doctor now consumes typed Ads diagnostics contracts instead of carrying
     long prompt-pack logic in `SKILL.md`; its context-pack stays under the
     deterministic smoke budget by using summary diagnostics before compaction.
   - Remaining: deeper semantic review of references for product logic hidden in prose.
   - References should describe contracts and output shape only; product logic,
     workaround rules and bug fixes belong in API/schema/eval.
   - Evals now cover basic API/evidence/Polish/safety, but still need stronger
     decision-quality assertions per skill.
   - Skill queue: manual + non-interactive eval per skill after its domain API
     contract is strong; upgrade evals to require concrete decisions, not only
     JSON shape; normalize dashboard prompts to Polish operator commands with
     evidence IDs, action IDs and blocked claims.

5. **Knowledge compiler and source condensation**
   - Goal: convert official docs, reputable PPC/SEO/analytics sources, papers
     and expert playbooks into versioned rules/cards with source lineage,
     confidence, freshness and blocked-claim boundaries.
   - Do not put raw research into dashboard cards or skill prompts.
   - Knowledge queue: define source-ingestion contract, promote high-confidence
     claims into `wilq/expert/**` or `wilq/knowledge/**`, then add eval checks
     proving the rules improve decisions without unsupported overclaims.

6. **Dashboard usefulness, performance and code quality**
   - Avoid broad aesthetic refactors.
   - Extract large route modules only when they block product work, reviewability
     or focused verification.
   - Focus performance work on shared daily view-model/cache and duplicated
     aggregation, not visual churn.
   - Dashboard queue: route-by-route marketer audit, Command Center as decision
     cockpit only, drilldowns for raw evidence/registries, shared route data
     boundaries and targeted extraction of large modules only when it speeds
     real slices.

7. **Release/live-test strategy**
   - Release gates should assert contracts, safety, evidence, Polish output and
     secret redaction.
   - Exact changing metric values belong in fixture tests only. Live smokes
     should assert freshness, nonempty expected facts and correct
     ready/missing/blocked status.
   - Release queue: separate fixture tests from live smokes, define a smaller
     pre-demo gate, keep full `scripts/verify.sh` for broad/final gates and add
     operational alerts for stale contracts, missing facts, unsafe apply and
     secret leakage.
   - Do not block production on exact live metric values. Exact clicks, costs,
     reviews, rankings and issue counts belong in fixtures/proof notes; live
     gates assert contract shape, freshness, nonempty expected facts and honest
     ready/missing/blocked state.

## Next Best Queue

1. Work by theme: source contracts -> decision API/view-model -> ActionObject
   safety -> Codex skill/eval quality -> knowledge compiler -> dashboard
   usefulness/performance -> release/live-test hardening.
2. Next concrete slice should come from live proof: Localo missing read
   `local_tasks` only if a read-only contract exists, Merchant before/after
   price-performance windows, Ahrefs granular gaps, semantic skill-reference
   audit or route-level dashboard usefulness/performance.
3. Do not re-add ready/done surfaces as active tasks. If a completed area looks
   wrong, reopen it only with fresh API/browser proof and a focused failing
   check.
