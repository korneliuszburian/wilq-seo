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

1. `wilq-campaign-builder` landing-context eval, 2026-06-23.
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

2. `wilq-demand-gen-operator` blocked readiness eval, 2026-06-23.
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

3. `wilq-social-publisher` review-only draft context/eval, 2026-06-23.
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

4. `wilq-ahrefs-gap-finder` review-only gap eval, 2026-06-23.
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

5. `wilq-gsc-content-doctor` scoped context-pack/eval, 2026-06-23.
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

6. `wilq-merchant-feed-operator` product-sample eval, 2026-06-23.
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

7. Merchant product-sample readiness contract, 2026-06-23.
   `/api/merchant/diagnostics` exposes `product_sample_readiness`, so WILQ no
   longer implies that aggregate Merchant issue clusters contain concrete
   product IDs, SKU or titles unless the read contract actually supplies them.
   The initial state of this contract was blocked; it is now superseded by the
   product-sample enrichment below. Current live state:
   `sample_products_available=true`, `sample_count=12`, with sample IDs/titles
   usable only as review examples. `/merchant` shows `Gotowość próbek produktów`
   and the Merchant skill smoke asserts the same field.

8. `wilq-ga4-analyst` decision-sample eval, 2026-06-23.
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

9. `wilq-ads-doctor` current API proof, 2026-06-23.
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

10. Merchant product sample enrichment, 2026-06-23.
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

11. Merchant diagnostics decision contract, 2026-06-23.
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

12. Ads Doctor drilldown/API copy cleanup, 2026-06-23.
   Commit `92febad fix(dashboard): polish ads doctor drilldowns` oczyścił dolne
   sekcje Ads Doctor i Custom Segments z najbardziej mylącego mieszanego copy.
   Keep enum names, endpoint names, field IDs, blocked-claim keys and Google API
   resource names unchanged; marketer-facing summaries/titles/next steps should
   stay Polish.

13. Command Center and Ads first-flow copy cleanup, 2026-06-23.
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
- Localo access works at OAuth/MCP initialize level, but WILQ still must expose
  real Localo ranking/GBP/competitor evidence before local SEO recommendations.
- Skill evals prove API usage, Polish and evidence shape for many routes. The
  newest Campaign Builder eval proves Ads review actions can be paired with
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

1. Run the next high-value Codex skill eval against current API contracts and
   record whether it produces real decisions, not only schema-valid output.
   Recommended next skill: `wilq-localo-operator` if the next demo needs local
   visibility readiness proof, or revisit `wilq-content-strategist` if the next
   demo focuses on landing/content-to-campaign handoff.
2. If an eval exposes reasoning gaps, fix typed API/dashboard contracts first,
   not skill references.
3. Keep focused verification. Use full `scripts/verify.sh` only for final
   handoff or broad cross-surface changes.
