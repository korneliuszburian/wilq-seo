# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. To ma być krótki recovery ledger, nie pełny changelog.

Pełne archiwa:

- `docs/progress/archive/2026-06-19-progress-ledger.md`
- `docs/progress/archive/2026-06-23-progress-ledger.md`

## Maintenance Rule

- Trzymaj tutaj aktualny stan, ostatnie 3-5 slice'ów, aktywne luki i następny
  krok.
- Nie dopisuj setek linii historii. Starsze wpisy przenoś do
  `docs/progress/archive/`.
- Git, goal i dedykowane ledgery są źródłem długiej historii. Ten plik ma
  pomagać po utracie contextu.

## Current Readout

Data: 2026-06-23

Stan produktu:

- Goal 001 nadal aktywny: `docs/goals/001-goal.md`.
- WILQ API jest system brain. Dashboard i Codex skills mają korzystać z tych
  samych kontraktów API, evidence IDs, ActionObject IDs i source connectors.
- Lokalny stack prowadź przez `scripts/local_stack.sh start|stop|restart|status|logs`.
  Kanoniczne URL-e: API `http://127.0.0.1:8000`, dashboard
  `http://127.0.0.1:5173/command-center`.
- Operator-facing output ma być po polsku z polskimi znakami.
- Nie wolno naprawiać błędów reasoning przez dopisywanie edge-case'ów do skill
  references. Naprawa ma iść przez typed API state, knowledge cards, expert
  rules, context-packi, evale i dashboard.
- Ekologus jest depth-first reference client. Docelowy kierunek produktu to
  agency/multi-client, ale multi-client abstraction dopiero po tym, jak Ekologus
  działa głęboko na realnych danych i ActionObjectach.

## Last Done

0. Command Center refresh-run bundle cleanup, 2026-06-23.
   `/api/dashboard/command-center` now fetches connector refresh runs once in
   the daily path and passes that bundle into `build_command_center_response`.
   Command Center brief builders use preloaded refresh runs for Ads, Merchant,
   Ahrefs and Localo instead of calling `local_state_store().list_connector_refresh_runs`
   separately per connector. Focused proof: API tests for preloaded refresh-run
   reuse and Command Center no-Marketing-Brief path, Python ruff and mypy.
   Live HTTP after stack restart: cold Command Center around `1.19s`, warm
   requests around `0.01s`, 4 daily decisions, 2 blockers and 37,734 bytes.
   Do not overclaim this as the final cold-path fix; the remaining bottleneck
   is deeper in cold Command Center internals and metric/view-model assembly.

0. Dashboard ActionObject review preview cards, 2026-06-23.
   `/actions/act_review_merchant_feed_issues` now renders a compact
   review-only `payload_preview` summary above the raw JSON payload. Preview
   cards prioritize items with `sample_product_ids`, show concrete Merchant
   sample product IDs/titles when available, and keep the safety state explicit:
   `Apply zablokowany`, `mutacja API: zablokowana`. Browser proof:
   `.local-lab/proof/dashboard/action-merchant-preview-samples-full.txt`
   shows product samples for `n:unit_pricing_measure` and `n:availability`.
   Focused proof: dashboard Action detail route tests and dashboard typecheck.
   The user's live Merchant skill feedback stays as an API/contract rule:
   final queues should be `decision_queue`-first, `issue_clusters` are
   drilldown, freshness and unknowns must be explicit, and validation state
   from context-pack must be distinguished from current endpoint validation.

0. Merchant ActionObject sample preview, 2026-06-23.
   `act_review_merchant_feed_issues` now carries Merchant sample product IDs
   and titles into its review-only `payload_preview` and dry-run
   `/api/actions/{id}/preview` response when those samples exist in metric
   facts. This keeps `/merchant`, `/api/merchant/diagnostics`,
   `/api/actions` and Codex context-pack aligned. Live proof after stack
   restart: preview items for `n:unit_pricing_measure` and `n:availability`
   include concrete sample product IDs/titles while `mutation_allowed=false`,
   `apply_allowed=false` and `api_mutation_ready=false`. Focused proof:
   Merchant API/action contract subset, merchant context-pack subset, Python
   ruff and mypy.

0. Merchant decision sample products, 2026-06-23.
   `/api/merchant/diagnostics` now carries `sample_product_ids` and
   `sample_titles` on each `decision_queue` item when Merchant evidence has
   product examples. `/merchant` renders those samples directly on decision
   cards as review hints, while still saying they are not a full SKU list or a
   ready feed mutation. Live proof after `scripts/local_stack.sh restart`:
   Merchant freshness is `fresh`, `product_sample_readiness.sample_products_available=true`,
   and decision cards include concrete product IDs/titles for
   `n:unit_pricing_measure` and `n:availability`. Focused proof: Merchant API
   contract tests, Merchant route test, shared schema typecheck, dashboard
   typecheck, Python ruff and mypy.

0. GA4 diagnostics freshness contract, 2026-06-23.
   `/api/ga4/diagnostics` now exposes a typed `freshness_assessment` with
   `fresh/stale/missing/blocked`, `age_hours`, `stale_after_hours=48` and
   `requires_refresh`. GA4 route shows that freshness state at the top and in
   the operator safety panel, so stale GA4 facts are not mistaken for a current
   campaign verdict. Live proof after `scripts/local_stack.sh restart`: GA4 is
   currently `stale`, `requires_refresh=true`, latest refresh
   `refresh_google_analytics_4_681b6bcefc85`, age about `139h`, while
   `act_review_ga4_tracking_quality` remains the only review ActionObject and
   conversion/ROAS/revenue claims stay blocked. Focused proof: GA4 API contract
   tests, stale-refresh test, GA4 route test, shared schema typecheck, dashboard
   typecheck, Python ruff and mypy.

0. Command Center Ads KPI review tiles, 2026-06-23.
   Command Center Ads daily decision now surfaces review-only campaign KPI
   availability from the same Google Ads metric facts already loaded for the
   first screen: `KPI do review`, `wiersze CPA` and `wiersze ROAS`. This gives
   the marketer a clearer reason to open `/ads-doctor` without pretending that
   CPA/ROAS, profitability or wasted-budget verdicts are unlocked. Live proof
   after `scripts/local_stack.sh restart`: `decision_review_ads_campaign_metrics`
   shows `KPI do review=18`, `wiersze CPA=1`, `wiersze ROAS=2` and still blocks
   `CPA`, `ROAS`, `profitability` and `wasted budget`. Focused proof:
   `tests/test_api_contracts.py -k 'command_center_ads_plan_uses_live_review_queues
   or command_center_ads_totals_use_latest_refresh_summary'`, ruff and mypy for
   `wilq/briefing/command_center.py`.

0. Command Center shared metric read performance slice, 2026-06-23.
   Cold `/api/dashboard/command-center` no longer performs separate DuckDB
   metric reads for tactical queue and Command Center brief. Daily runtime now
   builds one command-center metric bundle and passes it through
   `build_tactical_queue(...facts_by_connector=...)` and
   `build_command_center_response(...facts_by_connector=...)`. Response schema
   did not change. Live proof after `scripts/local_stack.sh restart`:
   `/api/dashboard/command-center` returned 4 decisions and 36,919 bytes with
   timings `0.667s`, then warm `0.007s`, `0.006s`, `0.007s`, `0.006s`.
   Focused proof: `tests/test_api_contracts.py -k 'daily_command_center or
   command_center_exposes_polish_operator_brief'`, ruff and mypy for
   `daily_runtime.py`, `command_center.py` and `tactical_queue.py`.

0. Command Center content labels and Merchant skill guardrails, 2026-06-23.
   Command Center content decision metric labels are now Polish at the API
   contract level: `zapytania/URL`, `dopasowania WordPress`, `ocena Ahrefs`,
   `luki Ahrefs` and `luki linków`. Live proof after
   `scripts/local_stack.sh restart`: `/api/dashboard/command-center`
   `decision_prepare_content_refresh_queue.metric_tiles` has no old
   `query/page`, `WP match`, `Ahrefs review` or `link gaps` keys, and
   `co_widzimy` says the decision is based on `zapytania/URL`. Merchant skill
   follow-up from the live user run is captured in the skill contract and smoke:
   use `freshness_assessment`, group final work by `decision_queue`, treat
   `issue_clusters` as drilldown, report `unknowns`, and preserve
   `count_semantics=reported_issue_occurrences` so issue counts are not called
   unique products/SKU. Focused proof: Command Center API contract test,
   Command Center route test, `wilq-merchant-feed-operator` smoke,
   `tests/test_codex_skill_eval_cases.py`, ruff and dashboard typecheck.

0. Daily Ads action focus cleanup, 2026-06-23.
   Command Center Ads daily card no longer carries deep Ads actions such as
   Demand Gen readiness, search-term n-grams or target/strategy review. The
   daily Ads card now exposes only the four first-flow review actions:
   campaign review, recommendation review, custom segments and negative keyword
   review. Because `/api/marketing/brief` now filters safe actions through
   daily decisions, live `safe_next_actions` dropped from 13 to 7. Live proof
   after `scripts/local_stack.sh restart`: Ads daily decision action IDs are
   `act_prepare_ads_campaign_review_queue`,
   `act_prepare_google_ads_recommendation_review_queue`,
   `act_prepare_custom_segments_from_search_terms`,
   `act_prepare_negative_keyword_review_queue`.

0. Marketing brief dedupe and Localo copy cleanup, 2026-06-23.
   `/api/marketing/brief` no longer duplicates the GA4 blocker when the same
   blocked daily decision is present both in daily decisions and operator brief.
   Localo metric facts now render as a Polish review headline
   `Localo: widoczność lokalna i opinie do review` with tracked keywords,
   visibility and review counts, instead of a raw technical metric name such as
   `localo_total_keyword_volume = 69420`. Live proof after
   `scripts/local_stack.sh restart`: `what_blocks_us` has one GA4 blocker and
   the Localo item shows `23 monitorowanych fraz`, `53.1739` average visibility
   and `798 opinii`.

0. Ads diagnostics ActionObject consistency, 2026-06-23.
   `/api/ads/diagnostics?view=summary` no longer emits
   `act_configure_ads_business_context` after the business context is already
   configured, because `/api/actions/{id}` correctly hides that ActionObject in
   that state. Added a focused contract test requiring every Ads summary
   `action_id` from operator summary, optimizer readiness and decision queue to
   exist and validate through `/api/actions/{id}/validate`. Live proof after
   `scripts/local_stack.sh restart`: all Ads summary action IDs returned
   `200 valid`; no `act_configure_ads_business_context` remained in the summary
   action set.

1. Compact all-skill coverage audit, 2026-06-23.
   Added `docs/evals/skill-coverage-audit.md` as the short map of current
   WILQ skill readiness. It lists 12/12 WILQ skills, latest eval artifact,
   usefulness score, state and remaining blocker. Current readout: all 12
   skills have current non-interactive eval artifacts, Polish output, WILQ API
   usage and zero safety findings. The strongest demo path is
   `wilq-daily-command` -> `/merchant` -> `/content-planner` -> `/ads-doctor`
   -> optional `/ga4`. Next product slice should move from skill proof to
   dashboard/API value, with Ads business-context guardrails and apply-preview
   safety as the best candidate.

2. `wilq-daily-command` cross-surface eval, 2026-06-23.
   Daily Command now has a stricter cross-surface eval proving that Codex uses
   `/api/dashboard/command-center`, `/api/marketing/brief` and the daily
   context-pack as one product surface. Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T161009Z/wilq-daily-command/result.json`.
   Result: `blocked=false`, `pl-PL`, `api_used=true`,
   `operator_usefulness_score=5`, no safety findings. The response uses
   `daily_decisions`, `primary_next_step`, `/merchant`, `/content-planner`,
   `/ga4` and `/ads-doctor`; it gives Merchant, Content, GA4 and Ads decisions
   with real metric tiles. It validates
   `act_review_merchant_feed_issues`, `act_prepare_content_refresh_queue` and
   `act_review_ga4_tracking_quality`; Ads is review-only through
   `act_prepare_ads_campaign_review_queue`. Social draft ActionObjects and
   `act_review_localo_visibility_facts` are explicitly forbidden as daily
   action candidates.

3. `wilq-custom-segments` review-only decision eval, 2026-06-23.
   Custom Segments now has current proof that Codex can use
   `ads_diagnostics.custom_segments_read_contract` as a review queue without
   inventing audience terms. Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T160335Z/wilq-custom-segments/result.json`.
   Result: `blocked=false`, `pl-PL`, `api_used=true`,
   `operator_usefulness_score=4`, no safety findings, source connectors
   `google_ads` and `google_search_console`. The response recommends only one
   review candidate, `Search terms: Kompendium PPWR`, with real `source_terms`,
   `review_priority=pilne`, `review_score=75` and `validation_status=pending_validation`.
   It explicitly keeps `audience_forecast_read_contract.status=blocked` and
   blocks audience size, ROAS, targeting-applied and campaign-performance
   claims until forecast/audience-size and apply-safety contracts exist.

4. `wilq-content-strategist` freshness-aware eval, 2026-06-23.
   Content Strategist now has a stricter eval that requires freshness/stale
   handling, not only valid evidence IDs. Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T155420Z/wilq-content-strategist/result.json`.
   Result: `blocked=false`, `pl-PL`, `api_used=true`,
   `operator_usefulness_score=4`, no safety findings, all expected content
   source connectors, and validated `act_prepare_content_refresh_queue`.
   The response uses `content_diagnostics.decision_queue`, explicitly says
   GSC/Ahrefs freshness is `stale`, prioritizes Zielony Ład as
   `merge_create_after_inventory_check`, keeps `bdo co to` as
   `inventory_check_before_create`, and treats Ahrefs gaps as a separate
   discovery backlog. The eval case now requires `freshness` and `stale`.

5. `wilq-localo-operator` partial-evidence eval, 2026-06-23.
   Localo skill now has current proof that Localo is not a simple access
   blocker anymore. Live smoke completed a read-only Localo refresh and showed
   `access_ready`, `mcp_initialize_status=200`, `localo_read_contract_count=3`,
   `localo_active_place_count=4`, `localo_tracked_keyword_count=23`,
   `localo_avg_visibility_current=53.1739`, `localo_reviews_count=798` and
   `local_visibility_review_preview_v1`. Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T154853Z/wilq-localo-operator/result.json`.
   Result: `blocked=true`, `pl-PL`, `api_used=true`,
   `operator_usefulness_score=5`, no safety findings, source connector
   `localo`, validated `act_review_localo_visibility_facts`, and a blocked
   apply/publication candidate. The block now means: aggregate Localo facts are
   reviewable, but GBP performance, competitor visibility, local tasks, write
   paths and local visibility uplift remain blocked until WILQ exposes those
   contracts.

6. `wilq-campaign-builder` landing-context eval, 2026-06-23.
   Campaign Builder context-pack now fills `content_landing_context` from
   `/api/content/diagnostics.decision_queue` before falling back to raw metric
   facts. Live proof after stack restart: `live_data_available=true`,
   `query_page_candidate_count=4`, `source=content_decision_queue`, with GSC
   candidates such as BDO, Zielony Ład, Remediacja and homepage query/page
   rows. The smoke script now exposes compact `content_landing_context`, and
   the eval case requires `content_landing_context`, `query_page_candidates`,
   review-only payload language and blocked campaign-performance claims.
   Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T154147Z/wilq-campaign-builder/result.json`.
   Result: `blocked=false`, `pl-PL`, `api_used=true`,
   `operator_usefulness_score=4`, no safety findings, validated
   `act_prepare_ads_campaign_review_queue` and
   `act_prepare_google_ads_recommendation_review_queue`. The response now
   explicitly tells Codex to use landing candidates before building
   `campaign_candidates`.

7. `wilq-demand-gen-operator` blocked readiness eval, 2026-06-23.
   Demand Gen eval is now explicit that the current correct state is a
   blocker/review-only workflow, not a launch or migration recommendation.
   The eval case requires `expected_blocked=true` and keeps blocked claims
   such as `Demand Gen launch recommendation`, `Demand Gen migration ready`,
   `creative quality verdict`, `asset performance verdict`, `campaign apply`
   and `performance uplift` out of recommendations. Non-interactive eval
   passed at
   `.local-lab/evals/codex-skill/20260623T153134Z/wilq-demand-gen-operator/result.json`.
   Result: `blocked=true`, `pl-PL`, `api_used=true`,
   `operator_usefulness_score=4`, no safety findings, zero recommendations,
   and one validated review-only `act_review_demand_gen_readiness` candidate.
   Live context: WILQ sees 18 Ads campaign rows across `PERFORMANCE_MAX` and
   `SEARCH`, but zero Demand Gen campaign/ad/creative/landing/migration rows,
   so launch/migration/creative quality claims stay blocked.

6. `wilq-social-publisher` review-only draft context/eval, 2026-06-23.
   Social Publisher now receives a typed `social_draft_context` in its
   skill-scoped context-pack. It exposes `mode=review_only`,
   `publish_allowed=false`, missing LinkedIn/Facebook permissions,
   `candidate_inputs` from WILQ evidence, draft constraints and blocked claims.
   This lets Codex prepare evidence-backed LinkedIn/Facebook draft directions
   while keeping publication blocked. Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T152228Z/wilq-social-publisher/result.json`.
   Result: `blocked=false`, `pl-PL`, `api_used=true`,
   `operator_usefulness_score=4`, no safety findings, validated
   `act_prepare_linkedin_social_drafts` and
   `act_prepare_facebook_social_drafts`, plus an explicit blocked publish
   action candidate because `publish_allowed=false`.

7. `wilq-ahrefs-gap-finder` review-only gap eval, 2026-06-23.
   Ahrefs eval now treats ready gap records as a review workflow, not a global
   blocker. Smoke exposes compact `gap_read_contract` fields:
   `status=ready`, `gap_record_count=8`, `missing_read_contracts=[]`,
   `freshness_states=["stale"]`, freshness labels about `60-62h`, and
   `review_mode=review-only`. The eval case expects `blocked=false` while
   still blocking unsupported `traffic uplift` and `authority improvement`
   claims outside recommendations. Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T151121Z/wilq-ahrefs-gap-finder/result.json`.
   Result: `pl-PL`, `api_used=true`, `operator_usefulness_score=4`, no safety
   findings, no ActionObject IDs, and review-only recommendations for
   `ahrefs_review_authority_context` plus `ahrefs_review_gap_records`.

8. `wilq-gsc-content-doctor` scoped context-pack/eval, 2026-06-23.
   GSC Content Doctor no longer receives/promotes Ahrefs decisions in its
   skill-scoped `POST /api/codex/context-pack`. Full
   `/api/content/diagnostics` can still include Ahrefs for Content Planner and
   `wilq-content-strategist`, but `wilq-gsc-content-doctor` gets only the
   GSC/WordPress decision subset. New guardrails:
   `context_pack_compaction.purpose=gsc_content_doctor_context`,
   `ahrefs_decisions_removed=true`, smoke asserts no Ahrefs decisions/evidence,
   and the eval harness supports `forbidden_connectors=["ahrefs"]`.
   Non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260623T150248Z/wilq-gsc-content-doctor/result.json`.
   Result: `pl-PL`, `api_used=true`, source connectors
   `google_search_console`, `wordpress_ekologus`, `wordpress_sklep`,
   `operator_usefulness_score=5`, no safety findings, validated
   `act_prepare_content_refresh_queue`.

9. `wilq-merchant-feed-operator` product-sample eval, 2026-06-23.
   Non-interactive Codex eval passed against the new Merchant product-sample
   contract:
   `.local-lab/evals/codex-skill/20260623T144931Z/wilq-merchant-feed-operator/result.json`.
   Result: `pl-PL`, `api_used=true`, evidence count `3`,
   `operator_usefulness_score=5`, no safety findings, source connector
   `google_merchant_center`, and validated
   `act_review_merchant_feed_issues`. The eval result explicitly mentions
   `/merchant`, `merchant_diagnostics`, `freshness_assessment=fresh`,
   `decision_queue`, `unknowns`, `product_sample_readiness ready`,
   `sample_product_ids` and review-only handling. The smoke script now also
   exposes context-pack ActionObject state (`needs_validation/not_validated`)
   alongside current endpoint validation (`valid=true/status=valid`).

9. Merchant product-sample readiness contract, 2026-06-23.
   `/api/merchant/diagnostics` exposes `product_sample_readiness`, so WILQ no
   longer implies that aggregate Merchant issue clusters contain concrete
   product IDs, SKU or titles unless the read contract actually supplies them.
   The initial state of this contract was blocked; it is now superseded by the
   product-sample enrichment below. Current live state:
   `sample_products_available=true`, `sample_count=12`, with sample IDs/titles
   usable only as review examples. `/merchant` shows `Gotowość próbek produktów`
   and the Merchant skill smoke asserts the same field.

10. `wilq-ga4-analyst` decision-sample eval, 2026-06-23.
   GA4 smoke now exposes compact `decision_samples` with `active_users`,
   `sessions`, `engagement_rate` and landing/source/campaign dimensions, so
   non-interactive Codex can cite real GA4 decision metrics instead of only
   decision IDs. Eval passed at
   `.local-lab/evals/codex-skill/20260623T141114Z/wilq-ga4-analyst/result.json`.
   Result: `pl-PL`, `api_used=true`, evidence count `12`,
   `operator_usefulness_score=4`, no safety findings, validated
   `act_review_ga4_tracking_quality`. The live queue has
   `fix_measurement` and `review_traffic_quality`; `review_landing_mapping`
   remains absent, so Codex must not infer landing quality from GA4 rows alone.

11. `wilq-ads-doctor` current API proof, 2026-06-23.
   Non-interactive Codex eval passed against the current WILQ API:
   `.local-lab/evals/codex-skill/20260623T130149Z/wilq-ads-doctor/result.json`.
   Result: `pl-PL`, `api_used=true`, evidence count `3`,
   `operator_usefulness_score=5`, no safety findings, and validated
   `act_prepare_ads_campaign_review_queue`,
   `act_prepare_google_ads_recommendation_review_queue`,
   `act_prepare_custom_segments_from_search_terms` and
   `act_prepare_negative_keyword_review_queue`. A first run failed on a scoped
   context-pack byte-budget reading (`210127` bytes); direct remeasure was about
   `188143` bytes and rerun passed. If it repeats, fix API context-pack
   compaction/budget stability, not skill references.

12. Merchant product sample enrichment, 2026-06-23.
   Merchant read-only `vendor_read` enriches aggregate issue clusters with
   product samples. It parses `sampleProducts` from `aggregateProductStatuses`
   when present and falls back to `products.list` / product status issue rows
   when aggregate samples are absent. Live proof:
   `refresh_google_merchant_center_a471db43f332`,
   `ev_refresh_refresh_google_merchant_center_a471db43f332`,
   `product_sample_count=20`, `product_sample_read_status=completed`.
   `/api/merchant/diagnostics.product_sample_readiness` is now `ready` on the
   live stack and exposes 12 matched sample product IDs plus titles for
   `unit_pricing_measure` and `availability` clusters. The diagnostics layer
   normalizes Merchant attribute names such as `n:unit_pricing_measure` and
   `unit pricing measure` only for matching; raw evidence dimensions remain
   unchanged.

13. Merchant diagnostics decision contract, 2026-06-23.
   `/api/merchant/diagnostics` ma typed pola eliminujące błąd interpretacji z
   live-run `wilq-merchant-feed-operator`: `freshness_assessment`,
   `unknowns`, `operator_summary.decision_source=decision_queue`,
   `drilldown_source=issue_clusters`, `count_semantics=reported_issue_occurrences`
   oraz `issue_cluster_ids` na decyzjach. Historical proof before the latest
   product-sample refresh correctly labeled a stale Merchant read at about
   `133.3h`; current live proof is fresh through
   `refresh_google_merchant_center_a471db43f332`.
   Proof: Merchant API contract tests, Merchant dashboard route test, Python
   ruff/mypy, dashboard lint/typecheck, shared-schemas typecheck, browser proof
   `.local-lab/proof/dashboard/merchant-freshness-unknowns.txt`.

14. Ads Doctor drilldown/API copy cleanup, 2026-06-23.
   Commit `92febad fix(dashboard): polish ads doctor drilldowns` oczyścił dolne
   sekcje Ads Doctor i Custom Segments z najbardziej mylącego mieszanego copy.
   Keep enum names, endpoint names, field IDs, blocked-claim keys and Google API
   resource names unchanged; marketer-facing summaries/titles/next steps should
   stay Polish.

15. Command Center and Ads first-flow copy cleanup, 2026-06-23.
   Command Center first-screen daily decision cards compose concise Polish
   marketer copy from typed API fields and metric tiles. Ads Doctor first flow
   shows review-only Ads decisions instead of raw API slang and hides raw
   `ev_*`/`act_*` from the first decision path.

## Active Gaps

- Full BDOS-class Ads optimizer is not done. Current Ads has campaign/search
  term/recommendation/budget/impression-share/change-history/business-context
  review contracts, but still blocks unsupported claims such as wasted budget,
  profitability, budget scaling, recommendation apply, CPA/ROAS verdicts and
  incrementality without stronger business/target/human confirmation contracts.
- Merchant item-by-item work is partially unblocked. WILQ now has read-only
  product samples and titles for some issue clusters, but still blocks product
  fixes, feed writes, approval restoration, unique-product counts and full
  SKU-level workflows until payload preview, ActionObject validation and audit
  contracts exist for the exact product rows.
- Localo is partially useful, not fully solved. WILQ has MCP access and
  aggregate Localo facts for active places, tracked keywords, visibility,
  grid position and reviews. It still blocks GBP performance, competitor
  visibility, local tasks, write/apply and local visibility uplift until those
  exact read/write contracts exist.
- Skill evals prove API usage, Polish and evidence shape for all 12 WILQ
  skills. `docs/evals/skill-coverage-audit.md` is the compact coverage table.
  The
  newest Daily Command eval proves the cross-surface operating loop from
  `command-center`, `marketing_brief` and context-pack; Custom Segments eval
  proves review-only segment candidates from real
  Ads `source_terms` while blocking audience size and performance claims;
  Content Strategist eval proves freshness-aware content decisions from
  `content_diagnostics.decision_queue`; Localo eval proves partial Localo facts
  are reviewable while unsupported local claims stay blocked; Campaign Builder eval proves Ads
  review actions can be paired with
  GSC landing candidates instead of generic campaign prose; Demand Gen eval
  proves a useful blocker/review-only state instead of fake launch/migration
  readiness; Social eval distinguishes review-only draft preparation from
  blocked publishing; Ahrefs eval distinguishes ready review workflows from
  blocked uplift claims; GSC eval prevents Ahrefs scope leakage; Merchant eval
  proves product-sample/freshness/decision-queue usefulness. Remaining skills
  still need the same stricter “quality of decision” assertions.
- `docs/goals/001-goal.md` is still too long. Keep it canonical for now, but
  future cleanup should preserve active requirements and archive old history.

## Next Best Queue

1. Move from skill proof back into product value: choose the next API/dashboard
   slice that makes the demo stronger. Ads business-context ActionObject
   consistency is now repaired; next candidates are GA4 tracking-quality detail,
   Merchant product-row payload preview, Localo typed local tasks, or deeper Ads
   apply/impact contracts.
2. If a future eval exposes reasoning gaps, fix typed API/dashboard contracts
   first, not skill references.
3. Keep focused verification. Use full `scripts/verify.sh` only for final
   handoff or broad cross-surface changes.
