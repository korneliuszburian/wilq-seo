# WILQ Context Index

Ten plik jest indeksem recovery po utracie kontekstu. Nie zastępuje goalu ani
AGENTS.md; wskazuje, gdzie leży aktualna prawda operacyjna.

## Start Here

1. `AGENTS.md` - stałe reguły pracy, sekrety, lokalne ścieżki i gotchas.
2. `docs/goals/001-goal.md` - jedyny aktywny goal i kolejka następnych zadań.
3. `docs/PROGRESS.md` - krótki aktualny stan slice'ów, testów i decyzji.
4. `docs/evals/skill-eval-ledger.md` - przebiegi ręcznych i non-interactive testów skillów.
5. `docs/research/wilq-marketing-source-map.md` - źródła marketingowe i techniczne.
6. `docs/architecture/bdos-class-wilq-operating-system.md` - poprzeczka produktowa.
7. `docs/architecture/codex-runtime.md` - Codex skills, hooks, evals i runtime.
8. `docs/audits/001-output.md` - świeży audyt 2026-06-18: co zatrzymać, co
   zacząć i pięć następnych slice'ów dla marketera.
9. `docs/progress/archive/2026-06-19-progress-ledger.md` - pełny progress
   ledger sprzed kompaktowania, używany tylko gdy potrzebna jest starsza
   historia.

## Current Critical Direction

Audit `docs/audits/001-output.md` is now folded into
`docs/goals/001-goal.md`. The current order is:

0. Progress ledger maintenance rule, 2026-06-19 22:51 Europe/Warsaw:
   `docs/PROGRESS.md` is now a short recovery ledger, not the full historical
   changelog. Keep current state, last 3-5 slices, active gaps and next best
   actions there. Move older detail to `docs/progress/archive/`; the first full
   archive is `docs/progress/archive/2026-06-19-progress-ledger.md`.

0. Ads n-gram review missing-contract precision, 2026-06-22 03:38 CEST:
   search-term n-gram review uses
   `ngram_to_negative_keyword_payload_preview`, not the generic
   `negative_keyword_payload_preview` used by the normal negative keyword
   review queue. This keeps `/api/ads/diagnostics`, dashboard wording and
   `wilq-ads-doctor` context aligned: n-grams are a review-only theme grouping
   and do not imply negative-keyword payload preview/apply readiness. Live proof
   after `scripts/local_stack.sh restart`: n-gram contract and decision both
   show missing `[human_intent_review, ngram_to_negative_keyword_payload_preview]`,
   while `negative_keywords_read_contract.missing_read_contracts=[]`. Full
   `scripts/verify.sh` passed after this slice: backend `150 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes
   and dashboard production build.

0. Ads Doctor ActionObject scope compaction, 2026-06-22 01:40 CEST:
   `wilq-ads-doctor` has an explicit ActionObject allowlist and no longer
   inherits every `google_ads` action. `act_review_demand_gen_readiness` stays
   in the `wilq-demand-gen-operator` context-pack, not Ads Doctor. RED/GREEN
   proof: `test_codex_context_pack_scopes_ads_doctor_payload` failed before the
   fix, then passed together with
   `test_codex_context_pack_scopes_demand_gen_payload`. Live smoke after
   `scripts/local_stack.sh restart`: `context_pack_bytes=191793`, active Ads
   actions are campaign review, recommendation review, n-gram review, custom
   segments, negative keywords, target guardrails, strategy review and Keyword
   Planner access.

0. Ads shared-budget distribution contract, 2026-06-22 01:25 CEST:
   `/api/ads/diagnostics.budget_pacing_read_contract` now exposes typed
   `shared_budget_distribution_rows`. If all Google Ads budget rows expose
   `budget_id`, WILQ must not keep `shared_budget_distribution` in
   `missing_read_contracts`. Live proof after `scripts/local_stack.sh restart`:
   `budget_rows=18`, `shared_rows=0`, `missing=[]`; decision
   `ads_review_budget_context.missing_read_contracts=[]`. Dashboard
   `/ads-doctor` renders `Podział wspólnych budżetów`; when no campaigns share
   a budget it shows an empty-state instead of a fake zero-value decision.
   `wilq-ads-doctor` smoke verifies the same field in the scoped context-pack.
   Eval artifact:
   `.local-lab/evals/codex-skill/20260621T232046Z/wilq-ads-doctor/result.json`
   with `language=pl-PL`, `api_used=true` and Google Ads evidence IDs. Full
   `scripts/verify.sh` passed after this slice: backend `150 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes
   and dashboard production build. Later follow-up reduced scoped Ads
   context-pack size from `198997` to `191793` bytes by excluding Demand Gen
   ActionObject from Ads Doctor scope.

0. Ads change-history empty-read semantics and Ads Doctor context budget,
   2026-06-22 00:56 CEST: if Google Ads `vendor_read` attempted
   `change_event` and returned 0 rows, WILQ must not show generic
   `change_history` as a missing read contract on campaign, KPI,
   recommendation or impression-share decisions. The correct state is:
   `change_history_read_contract.status=blocked`, missing
   `change_event_rows`, `pre_change_performance_window`,
   `post_change_performance_window`, `human_change_impact_review` and
   `apply_preview`; only `ads_review_change_history` stays blocked with
   `zmiany=0`. At the time this slice ran, `ads_review_budget_context` still
   exposed `shared_budget_distribution` as missing; the later shared-budget
   distribution slice fixes that. Scoped `wilq-ads-doctor` context-pack keeps common Ads samples
   at 3 rows and preserves total/included counts, while the full
   `/api/ads/diagnostics` endpoint remains richer. Eval artifact:
   `.local-lab/evals/codex-skill/20260621T223847Z/wilq-ads-doctor/result.json`
   with `language=pl-PL`, `api_used=true`, `operator_usefulness_score=5`.
   Full `scripts/verify.sh` passed after this slice: backend `149 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes
   and dashboard production build.

0. Custom segments audience forecast readiness contract, 2026-06-22 00:21 CEST:
   `/api/ads/diagnostics.custom_segments_read_contract` exposes nested
   `audience_forecast_read_contract`. Live state after
   `scripts/local_stack.sh restart`: custom segments are `ready` for review
   with 1 candidate and 1 payload preview, but
   `audience_forecast_read_contract.status=blocked`,
   `checked_candidate_count=1`, `forecast_row_count=1`,
   row status `missing_forecast`, `forecast_available=false` and
   `audience_size=null`. Decision
   `ads_prepare_custom_segments_from_search_terms` carries
   `custom_segment_audience_forecast_rows`; `/custom-segments` and Ads Doctor
   render the same blocker. `wilq-custom-segments` eval artifact:
   `.local-lab/evals/codex-skill/20260621T221018Z/wilq-custom-segments/result.json`
   with `language=pl-PL`, `api_used=true`, `operator_usefulness_score=4`,
   `act_prepare_custom_segments_from_search_terms`, and a blocked action
   candidate for `audience_forecast_read_contract.status=blocked`.
   Full `scripts/verify.sh` passed after this slice: backend `149 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes
   and dashboard production build.

0. Demand Gen landing/migration empty-read contracts, 2026-06-21 23:40 CEST:
   `/api/demand-gen/diagnostics` now treats
   `demand_gen_landing_quality_by_campaign` and
   `demand_gen_migration_constraints` as typed available read contracts, not
   missing implementation. Current live state is still `status=blocked` because
   Google Ads evidence has 18 campaigns but 0 Demand Gen/Discovery rows:
   `wiersze DG=0`, `reklamy DG=0`, `assety DG=0`, `landingi DG=0`,
   `ograniczenia=0`, `braki=0`, `missing_read_contracts=[]`. The review-only
   `act_review_demand_gen_readiness` payload keeps `apply_allowed=false`,
   `api_mutation_ready=false`, `destructive=false`. Eval artifact:
   `.local-lab/evals/codex-skill/20260621T212918Z/wilq-demand-gen-operator/result.json`
   with `language=pl-PL`, `api_used=true`, source connectors Google Ads + GA4,
   `operator_usefulness_score=4`, `blocked=true`. Full `scripts/verify.sh`
   passed after this slice: backend `149 passed`, dashboard unit `17 passed`,
   Playwright e2e `14 passed`, skill/API smokes and dashboard production build.

0. Ahrefs content/backlink gap candidates, 2026-06-21 05:05 CEST:
   `refresh_ahrefs_cb31460610d3` performed read-only Ahrefs `organic-keywords`
   for the target sample and `refdomains` for backlink gap candidates. Content
   gap records are sample-backed: a competitor keyword becomes a content gap
   only when it is absent from the target organic-keyword sample. Backlink gap
   records are also sample-backed: a competitor referring domain becomes a gap
   only when it is absent from the target refdomains sample. Live facts:
   DR=40, Ahrefs Rank=1541946, `organic_competitor_rows=10`,
   `top_pages_by_competitor_rows=4`, `organic_keywords_by_url_rows=4`,
   `content_gap_read_status=completed`, `content_gap_rows=4`,
   `content_gap_target_keywords=100`, `backlink_gap_read_status=completed`,
   `backlink_gap_rows=9`. `/api/ahrefs/diagnostics` now has
   `gap_read_contract.status=ready`, `missing_read_contracts=[]`,
   `gap_records=24`, `content_records=4`, `backlink_records=9`, all Ahrefs gap
   read contracts available, context-pack about `100234` bytes and
   `active_action_objects=0`. Latest eval is
   `.local-lab/evals/codex-skill/20260621T030447Z/wilq-ahrefs-gap-finder/result.json`.
   Full `scripts/verify.sh` passed after this slice: backend `139 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and
   dashboard production build passed. This still blocks traffic/authority
   uplift claims; it makes gap candidate review real.

0. Ahrefs competitor page records, 2026-06-21 03:38 CEST:
   `refresh_ahrefs_a106dd4ab417` performed a real read-only Ahrefs API refresh
   against the real marketing target `ekologus.pl`, not
   `ekologus.dev.proudsite.pl`. Target priority is now `AHREFS_TARGET`,
   `MIS_PRIMARY_SITE_URL`, then `WORDPRESS_EKOLOGUS_URL`. Live facts: DR=40,
   Ahrefs Rank=1541946, `organic_competitor_read_status=completed`,
   `organic_competitor_rows=10`, `organic_competitor_country=pl`,
   `organic_competitor_mode=subdomains`. `/api/ahrefs/diagnostics` has
   `gap_fact_count=10`, `gap_records=10`, available contract
   `ahrefs_competitor_pages`, ready decision `ahrefs_review_gap_records`, and
   blocked claim decision for the remaining content/backlink/organic-keyword/
   top-page contracts. Scoped `wilq-ahrefs-gap-finder` context-pack is about
   `53100` bytes, `active_action_objects=0`, and latest eval is
   `.local-lab/evals/codex-skill/20260621T013710Z/wilq-ahrefs-gap-finder/result.json`.
   Full `scripts/verify.sh` passed after this slice: backend `139 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes
   and dashboard production build passed. This is an API/view-model fix, not a
   skill-reference workaround.

0. Ahrefs typed gap read contract, 2026-06-21 01:21 CEST, superseded by the
   03:38 target fix above:
   `/api/ahrefs/diagnostics` includes `gap_read_contract` and must block
   unsupported content/backlink/ranking/traffic/authority claims. The old
   zero-row state from `refresh_ahrefs_21a12047ec6a` is historical only. Current
   proof is `refresh_ahrefs_a106dd4ab417`: DR=40, Ahrefs Rank=1541946,
   `organic_competitor_rows=10`, `gap_records=10`,
   `available_read_contracts` includes `ahrefs_competitor_pages`, and the
   remaining missing contracts are `ahrefs_content_gap_records`,
   `ahrefs_backlink_gap_records`, `ahrefs_organic_keywords_by_url`,
   `ahrefs_top_pages_by_competitor`.

0. Ads custom segment missing-metric truth, 2026-06-21 01:40 CEST:
   Custom segment review must not coerce absent search-term impressions/cost to
   zero. Current live proof after restart: `/api/ads/diagnostics` returns
   `Source terms=6, kliknięcia=7, wyświetlenia=brak danych, koszt=brak danych,
   konwersje=0, odrzucone terminy=44` for the custom segment candidate.
   `operator_review_gates` now includes `keyword_planner_enrichment` and
   `forecast_or_audience_size` in both `custom_segments_read_contract` and
   decision `ads_prepare_custom_segments_from_search_terms`. Dashboard labels
   these gates in Polish. This remains prepare/review-only: Keyword Planner
   live access is still blocked and WILQ must not claim forecast, audience
   size, targeting applied, ROAS, CPA or campaign performance from this
   contract.

0. Ads business policy gates, 2026-06-21 01:01 CEST:
   `AdsBusinessContextReadContract` now exposes typed `business_policy_ids` and
   `operator_review_gates`. Current live policy IDs:
   `use_margin_as_context_not_profitability_verdict`,
   `align_campaign_review_to_business_goal`,
   `honor_human_budget_goal_before_budget_changes`,
   `block_target_verdict_until_roas_or_cpa_confirmed`. Current gates:
   `human_strategy_review`, `review_profit_margin_model`,
   `review_business_goal`, `review_human_budget_goal`,
   `confirm_target_roas_or_cpa`. Business-context decision shows
   `review gates=5` and `polityki=4`. Redaction allowlist preserves
   `business_policy_ids`; scoped `wilq-ads-doctor` context-pack after restart
   was `189432` bytes and carried unredacted policy IDs. This is review policy,
   not profitability, margin verdict, budget scaling/apply, recommendation
   apply or wasted-budget permission.

0. Ads n-gram decision usefulness, 2026-06-21 00:45 CEST:
   `ads_review_search_term_ngrams` now keeps useful decision metric tiles after
   lineage normalization instead of falling back to `{}` and priority `90`.
   It is priority `42` and exposes non-additive overlapping n-gram tiles:
   total n-grams, displayed rows, rows with clicks, max source queries per
   topic and top clicks per topic; cost is shown only when present. Live proof:
   `/api/ads/diagnostics` returned `n-gramy=30`, `pokazane=8`,
   `z kliknięciami=8`, `max query/temat=12`, `top kliknięcia=2`, while still
   blocking `search-term waste`, `negative keyword apply`, CPA, ROAS and
   conversion loss. Scoped `wilq-ads-doctor` context-pack was `188899` bytes
   and carries the same lightweight decision tiles without heavy n-gram rows.

0. Ads target-aware campaign review, 2026-06-21 00:31 CEST:
   Campaign rows, derived KPI rows, Ads campaign review ActionObject and scoped
   `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` now carry
   target-aware state: `target_status`, `target_status_label` and ActionObject
   `target_context`. Current live truth remains honest: business context is
   ready, but there is no human-confirmed target ROAS/CPA, so
   `/api/ads/diagnostics.business_context_read_contract.missing_read_contracts`
   includes `target_roas_or_cpa`; top campaign `(2026) Ekologus Ogólna` is
   `target_status=no_target` / `target_status_label=brak targetu`; campaign
   decision metric tiles do not show noisy `targety=0`. Campaign decision
   `operator_review_gates` now carries the union of row gates instead of an
   empty list. Process-env proof with `WILQ_ADS_TARGET_ROAS=5.0` marks the same
   top campaign `outside_target` / `ROAS poniżej targetu`, adds
   `review_target_context` and `review_target_gap_before_budget_decision`, and
   shows `targety=18`. Scoped context-pack proof: `189752` bytes and first Ads
   campaign candidate includes `target_context`. This is still review-only:
   no budget apply, campaign pause, wasted-budget claim, CPA/ROAS verdict or
   profitability claim.

0. Ads campaign review ActionObject/context alignment, 2026-06-21 00:13 CEST:
   `/api/ads/diagnostics`,
   `/api/actions/act_prepare_ads_campaign_review_queue` and scoped
   `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` now share the
   same campaign triage vocabulary: `review_priority`, `review_score`, Polish
   `review_reason` and `human_review_gates`. The context-pack keeps a compact
   top 3 of 8 campaign candidates instead of an empty list, while full payload
   remains in `/api/actions/{id}`. Live proof after `scripts/local_stack.sh
   restart`: top candidate `(2026) Ekologus Ogólna` is `pilne/90` with
   `clicks=94`, `impressions=2763`, `cost_micros=61051723`,
   `conversions=0.0`; `candidate_included=3`, `metrics_total=12`,
   `budget_payload_preview_included=0`, `apply_allowed=false`; scoped pack is
   `187638` bytes. Redaction preserves `human_review_gates`, including
   `review_search_terms_before_budget_decision`. Validate action returns
   `valid=true`. This is review-only order, not budget apply, campaign pause,
   wasted-budget, CPA/ROAS or profitability verdict. Full `scripts/verify.sh`
   passed after this slice: backend `136 passed`, dashboard unit `17 passed`,
   Playwright e2e `14 passed`, API/skill smokes and dashboard production build
   OK.

0. Ads search-term n-gram read contract, 2026-06-20 23:12 CEST:
   `/api/ads/diagnostics` exposes `search_term_ngram_read_contract` and
   decision `ads_review_search_term_ngrams`. It groups existing Google Ads
   `search_term_rows` into 1/2/3-grams with source search-term count, examples,
   clicks, impressions, cost, conversions, evidence IDs and blocked claims.
   Dashboard Ads Doctor renders a n-gram table. This is read-only review state,
   not a negative-keyword recommendation or apply path. It must keep blocking
   `search-term waste`, `negative keyword apply`, CPA, ROAS and conversion
   loss until human intent review, 90-day safety and payload preview gates are
   satisfied. Live proof after `scripts/local_stack.sh restart`:
   `search_term_ngram_read_contract.status=ready`, `ngram_rows=30`, top n-gram
   `bdo`, section `ads_search_term_ngrams` carries
   `card_google_ads_search_playbook`,
   `card_google_ads_negative_keywords_playbook`,
   `ads_search_terms_v1` and `ads_negative_keywords_v1`. Full
   `scripts/verify.sh` passed after final context-pack compaction: backend
   `136 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
   API/skill smokes and dashboard production build OK. Ads doctor context-pack
   stays under the 200 KB test limit; full rows remain in `/api/ads/diagnostics`.

0. Command Center DailyDecision usefulness, 2026-06-20 22:40 CEST:
   `DailyDecision.co_widzimy` is now marketer-facing copy, not a trace/debug
   sentence. It must not contain `Źródła=`, `dowody=` or `akcje=`; those remain
   in typed fields and trace lines. Live proof after `scripts/local_stack.sh
   restart`: `/api/dashboard/command-center` returned `false` for those
   substrings in all `co_widzimy` values, and GA4 no longer duplicates
   `Status blocked oznacza...`. `scripts/verify.sh` passed for this follow-up:
   backend `136 passed`, dashboard unit `17 passed`, Playwright e2e
   `14 passed`, API/skill smokes and dashboard production build OK.

0. ActionObject mutation audit visibility, 2026-06-20 22:24 CEST:
   `ActionObject.review_gate` now carries the latest mutation audit fields:
   `last_mutation_audit_id/status/actor/at/summary`,
   `last_mutation_attempted`, `last_mutation_adapter`,
   `last_mutation_audit_event_id` and `last_mutation_blockers`. Dashboard action
   detail and daily context-pack render the same typed state. Runtime proof on a
   temp state DB: blocked apply on `act_review_merchant_feed_issues` returned
   `mutation_status=blocked`, `mutation_attempted=false`; follow-up
   `/api/actions/{action_id}` and `POST /api/codex/context-pack
   {"skill":"wilq-daily-command"}` both returned
   `review_gate.last_mutation_audit_status=blocked` and
   `last_mutation_attempted=false`. `scripts/verify.sh` passed for this
   visibility follow-up, including API/skill smokes, Playwright e2e and
   dashboard production build.

0. ActionObject mutation audit boundary, 2026-06-20 21:58 CEST:
   `POST /api/actions/{action_id}/apply` must not report `applied=true`
   without a real vendor mutation adapter and persisted mutation audit. Current
   WILQ state includes typed `ActionMutationAuditRecord`,
   `action_mutation_audits` SQLite persistence, `GET /api/action-mutation-audits`,
   `GET /api/actions/{action_id}/mutation-audits` and
   `ActionApplyResult.mutation_audit`. Apply now requires prior dry-run preview,
   recorded confirmation, completed impact sanity check, valid ActionObject,
   configured connector, non-destructive payload, safe risk and supported vendor
   mutation adapter. No vendor mutation adapter is implemented in Goal 001, so
   all current apply attempts must return `applied=false`, `status=blocked`,
   `mutation_attempted=false`, `mutation_adapter=null`. Redaction preserves
   `audit_event_id`/`audit_event_ids`. Full `scripts/verify.sh` passed after
   this slice: backend `136 passed`, dashboard unit `17 passed`, Playwright e2e
   `14 passed`, dashboard build OK.

0. ActionObject review gate truth, 2026-06-20 20:04 CEST:
   `ActionObject.review_gate` is now typed backend/frontend product state, not
   skill prose. It must preserve `required_checks`, `operator_checklist`,
   `apply_blockers`, `confirmation_required` and `apply_allowed` through
   `/api/actions`, dashboard views and `POST /api/codex/context-pack`. Redaction
   allowlists these review-gate keys so IDs such as
   `google_ads_rmf_compliance_review`, `review_source_terms` and
   `negative_keyword_payload_preview` are not replaced with `[REDACTED]`.
   Current live proof after `scripts/local_stack.sh restart`: Merchant,
   content and Ads review actions all expose `status=pending_validation`,
   `apply_allowed=false`, `confirmation_required=true` and explicit
   `apply_blockers`. Scoped skill context-packs intentionally keep only one
   exemplar `active_action_objects.metrics` row plus `metrics_total`, because
   Ads diagnostics already carries the detailed read contracts and the
   `wilq-ads-doctor` pack must stay below 200 KB. This closes review-gate
   visibility only; it does not enable apply/write mutations.

0. Human review outcome truth, 2026-06-20 20:28 CEST:
   `POST /api/actions/{action_id}/review` records a local audit event
   `human_review_<outcome>` with typed `ActionReviewRequest` and returns
   `ActionReviewResult`. `ActionObject.review_gate` now carries
   `last_review_outcome`, `last_reviewed_by`, `last_reviewed_at` and
   `last_review_summary`; dashboard shows `Wynik review człowieka`; daily
   context-pack preserves the same fields. Runtime proof on a temp state DB:
   review endpoint returned `200`, event type `human_review_needs_changes`,
   ActionObject and `wilq-daily-command` context-pack both carried
   `last_review_outcome=needs_changes`, `apply_allowed=false`, and no
   `[REDACTED]` marker. This is only local review/audit state and must not be
   interpreted as vendor mutation permission.

0. ActionObject impact sanity truth, 2026-06-20 21:28 CEST:
   `POST /api/actions/{action_id}/impact-check` is now the local impact sanity
   step after preview and confirmation. It returns typed
   `ActionImpactCheckResult`, writes `action_impact_check_blocked` or
   `action_impact_check_completed`, and never executes vendor apply. It blocks
   without prior confirmation (`action_confirmation_required`) or without
   metric facts/evidence. After successful check it updates
   `ActionObject.review_gate.last_impact_check_status/by/at/summary` and
   removes only `impact_sanity_check_required`; other apply blockers remain.
   Dashboard shows `Impact sanity check`. Daily context-pack carries
   `latest_audit_event=action_impact_check_completed` and the `last_impact_*`
   review-gate fields. Runtime proof on a temp state DB: impact-before-confirm
   -> blocked, preview -> `action_preview_generated`, confirm ->
   `action_apply_confirmed`, impact-after-confirm ->
   `action_impact_check_completed`, context-pack `apply_allowed=false`. Full
   `scripts/verify.sh` passed after this slice: backend `135 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, dashboard build OK.

0. ActionObject confirmation truth, 2026-06-20 21:03 CEST:
   `POST /api/actions/{action_id}/confirm` is now a separate local confirmation
   step after dry-run preview. It returns typed `ActionConfirmResult` and never
   executes vendor apply. Confirmation before preview is blocked with
   `dry_run_preview_required` and audit event `action_confirmation_blocked`.
   Confirmation after preview writes `action_apply_confirmed`, updates
   `ActionObject.review_gate.last_confirmation_by/at/summary`, removes only the
   satisfied human-confirm blocker and keeps real apply blockers such as
   `action_mode_prepare_only` or `payload_apply_allowed_false`. Dashboard shows
   `Jawne potwierdzenie preview`. Daily context-pack carries both
   `latest_audit_event=action_apply_confirmed` and the `last_confirmation_*`
   review-gate fields. Runtime proof on a temp state DB: confirm-before-preview
   -> blocked, preview -> `action_preview_generated`, confirm-after-preview ->
   `action_apply_confirmed`, context-pack `apply_allowed=false`. Full
   `scripts/verify.sh` passed after this slice: backend `133 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, dashboard build OK.

0. ActionObject dry-run preview truth, 2026-06-20 20:44 CEST:
   `POST /api/actions/{action_id}/preview` is the standard local preview step
   in the Goal 001 `dry_run -> preview -> confirm -> audit` path. It returns
   typed `ActionPreviewResult` with `dry_run=true`, `mutation_allowed=false`,
   preview rows extracted from the existing ActionObject payload,
   `preview_items_total`, `omitted_items`, blockers, `review_gate` and local
   audit event `action_preview_generated`. Dashboard shows `Dry-run preview`
   next to review/validation. Daily context-pack carries the latest audit event
   as `latest_audit_event`, not the full audit history. Runtime proof on a temp
   state DB: preview endpoint returned `200`, ActionObject and
   `wilq-daily-command` context-pack both carried
   `latest_audit_event.event_type=action_preview_generated`,
   `apply_allowed=false`. This does not enable vendor apply. Full
   `scripts/verify.sh` passed after this slice: backend `131 passed`,
   dashboard unit `17 passed`, Playwright e2e `14 passed`, dashboard build OK.

0. Daily context-pack action summary truth, 2026-06-20 14:30 Europe/Warsaw:
   `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` must use
   `CommandCenterResponse.daily_decisions` for active ActionObject summaries.
   Do not rebuild daily action prose from stale raw ActionObject summaries.
   Current live proof after `scripts/local_stack.sh restart`: Merchant action
   carries `decision_id=decision_review_merchant_feed_issues` with tiles
   `produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`; GA4 carries
   `decision_id=decision_review_ga4_landing_quality`, `decision_status=blocked`
   and tiles `grupy ruchu=10`, `pomiar=2`, `jakość ruchu=4`. Stale strings
   `active_products=12`, `disapproved_products=3`, `active_users=20`,
   `sessions=30`, readiness-only connector copy and `Run a read-only refresh`
   must stay absent. Redaction preserves `decision_id`.

0. Localo Command Center routing truth, 2026-06-20 14:30 Europe/Warsaw:
   Localo with real aggregate facts uses `daily_localo_visibility_facts`, not
   readiness-only `daily_localo_readiness`. Current live tiles:
   `miejsca=4`, `frazy=23`, `widoczność=52.8261`, `recenzje=793`.
   `daily_localo_readiness` remains a readiness/access/blocker ID and the
   daily-command smoke must fail if it returns as a ready primary operator
   item. Full `scripts/verify.sh` passed after this slice: backend
   `124 passed`, dashboard unit `15 passed`, Playwright e2e `12 passed`,
   production build OK.

0. Localo metric fact selection truth, live proof 2026-06-20 16:35 CEST:
   Localo diagnostics and Command Center must read aggregate facts by evidence
   ID of the last successful Localo MCP read, not from a small newest-facts
   limit that can be filled by later probe failures. Current live state after
   `scripts/local_stack.sh restart`: `/api/localo/diagnostics` uses
   `refresh_localo_9e9ff67eadad`, has `visibility_fact_count=17`,
   `metric_tiles.frazy=23`, `miejsca=4`, `średnia widoczność=52.8261`,
   `recenzje=793`; Command Center daily decision
   `decision_review_localo_visibility_facts` has `frazy=23`, and
   `daily_localo_readiness` count is `0` while visibility facts exist.

0. Demand Gen dedicated route truth, updated live proof 2026-06-21 22:53 CEST:
   Demand Gen readiness is now a first-class product surface, not a generic
   registry fallback. `GET /api/demand-gen/diagnostics`, `/ads-doctor/demand-gen`
   and the scoped `wilq-demand-gen-operator` context-pack share the same
   blocked readiness contract: Ads campaign channel rows are available
   (`PERFORMANCE_MAX=8`, `SEARCH=10`), there are no Demand Gen/Discovery rows
   in current evidence, and `act_review_demand_gen_readiness` is the only
   scoped Demand Gen ActionObject. Live Google Ads refresh
   `refresh_google_ads_dc9e77806e9c` proves `demand_gen_ad_group_ad_rows` and
   `demand_gen_creative_asset_rows` are available empty-read contracts with
   row count `0`. Remaining missing contracts are only
   `demand_gen_landing_quality_by_campaign` and
   `demand_gen_migration_constraints`. The obsolete
   `demand_gen_asset_group_rows` contract must not return. The route must not
   show `Evidence Registry`, `Connector Refresh Runs` or adjacent Ads
   ActionObjects as Demand Gen actions. The smoke script is state-neutral for
   full verify: with a temporary empty DB, ad/creative contracts may be honest
   missing contracts; with live proof they must be available empty-read
   contracts.

0. Content decision metadata truth, 2026-06-20 14:06 Europe/Warsaw:
   `/api/content/diagnostics.decision_queue` now owns marketer-facing
   `status`, `priority` and `metric_tiles`. Do not recreate these fields in
   dashboard or skills from raw tactical items. Live proof:
   `decision_count=4`, `null_status=[]`, `null_priority=[]`, `empty_tiles=[]`.
   Top decision is `SEO: odśwież lub scal "zielony ład co to" (7 zapytań)`
   with metric tiles `zapytania=7`, `WP=znaleziono`, `wyświetlenia=2902`,
   `kliknięcia=123`, `CTR=4.24%`, `pozycja=1.5`. Scoped
   `wilq-content-strategist` context-pack carries the same fields. Command
   Center `daily_content_queue` bridges the same API state and shows
   `query/page=10`, `WP match=10`, `decyzje=4`, `wyświetlenia=7852`,
   `kliknięcia=138`.

0. Ads business context truth, live proof 2026-06-20 17:34 CEST, after target
   reset:
   `/api/ads/diagnostics` now exposes `business_context_read_contract` and
   decision `ads_review_business_context`. Current local runtime may keep
   preliminary non-secret Ads business values for profit margin, Polish
   business goal and Polish budget goal, but `WILQ_ADS_TARGET_ROAS` and
   `WILQ_ADS_TARGET_CPA_MICROS` are intentionally empty until a human confirms
   them. This is API product state, not skill prompt logic. After
   `scripts/local_stack.sh restart`,
   `/api/ads/diagnostics.business_context_read_contract.status=ready`,
   `missing_read_contracts=[target_roas_or_cpa]`, `target_roas=null`,
   `target_cpa_micros=null` and
   `allowed_metrics=[profit_margin,business_goal,human_budget_goal]`.

0. Ads business context cockpit truth, live proof 2026-06-20 17:34 CEST, after
   target reset:
   with empty target values and core context present, Command Center must not
   expose a false blocked business-context item. It should keep the single ready
   Ads review card and show target emptiness inside Ads Doctor as
   `missing_read_contracts=[target_roas_or_cpa]`.
   `/api/ads/diagnostics.derived_kpi_read_contract.kpi_rows` can still include
   `target_cpa_micros`, `cpa_vs_target_micros`, `target_status`,
   `target_status_label` and `target_review_priority`, but rows without human
   target confirmation now remain `no_target` / `brak targetu` style triage.
   Current Command Center shows read-only Ads review
   `decision_review_ads_campaign_metrics`; it does not show
   `decision_ads_business_context_before_budget_decisions` and does not include
   `act_configure_ads_business_context` in Ads action IDs.
   Daily Codex still must not claim profitability, margin verdict, wasted
   budget or budget scaling without the remaining optimizer contracts.

0. Ads Keyword Planner truth, live proof 2026-06-20 19:30 CEST:
   Keyword Planner is now a typed read-only contract, not prompt text.
   `wilq/connectors/google_ads/client.py` calls Google Ads
   `generateKeywordIdeas`; `/api/ads/diagnostics` exposes
   `keyword_planner_read_contract`; the dashboard and shared schema understand
   Keyword Planner ideas for custom segments. Current live vendor_read
   `refresh_google_ads_0477a745f098` completed normal Ads reads but Keyword
   Planner returned `403 PERMISSION_DENIED` /
   `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`. This is a Google Ads
   developer-token approval/readiness blocker, not missing `.env`, broken
   OAuth, MCC setup or child-customer setup. Current contract state:
   `keyword_planner_read_contract.status=blocked`,
   `missing_read_contracts=[keyword_planner_enrichment]`, no idea rows; custom
   segments keep
   `missing_read_contracts=[keyword_planner_enrichment, forecast_or_audience_size]`.
   Latest `wilq-ads-doctor` eval artifact:
   `.local-lab/evals/codex-skill/20260620T173651Z/wilq-ads-doctor/result.json`.

0. Ads recommendation triage truth, live proof 2026-06-20 18:48 CEST:
   `/api/ads/diagnostics.recommendations_read_contract.recommendation_rows`
   now carries `review_priority`, `review_score`, Polish `review_reason` and
   `human_review_gates`. Live rows after `scripts/local_stack.sh restart`:
   4 recommendations, 0 pilne, 2 wysokie, 4 apply previews, 2 impact previews,
   `missing_read_contracts=[]`, action
   `act_prepare_google_ads_recommendation_review_queue`. This is review triage
   only; recommendation apply, automatic accepts, budget apply, campaign
   mutation and performance uplift remain blocked. Latest eval:
   `.local-lab/evals/codex-skill/20260620T164726Z/wilq-ads-doctor/result.json`.

0. Custom segments scoped context truth, live proof 2026-06-20 17:34 CEST:
   `POST /api/codex/context-pack {"skill":"wilq-custom-segments"}` is scoped to
   the custom-segments workflow only: about 50 KB, `active_action_ids` and
   `ads_action_ids` contain only `act_prepare_custom_segments_from_search_terms`,
   `decision_ids=[ads_prepare_custom_segments_from_search_terms]`,
   `top_opportunity_count=0`, and
   `context_pack_compaction.purpose=custom_segments_context`. The dedicated
   `/ads-doctor/custom-segments` route renders this as a review-only segment
   queue with source terms, missing Keyword Planner/forecast contracts and
   blocked audience/apply/performance claims.

0. Ads custom segment gate truth, live proof 2026-06-20 16:15 CEST:
   custom segments keep true missing read contracts separate from operator
   review gates. `/api/ads/diagnostics.custom_segments_read_contract` is
   `ready` with `missing_read_contracts=["keyword_planner_enrichment",
   "forecast_or_audience_size"]` and
   `operator_review_gates=["review_source_terms",
   "reject_brand_or_low_intent_terms", "human_confirm_before_apply"]`.
   Decision `ads_prepare_custom_segments_from_search_terms` carries the same
   fields plus `metric_tiles.segmenty=1`, `metric_tiles.źródłowe zapytania=6`
   and `action_ids=["act_prepare_custom_segments_from_search_terms"]`.
   Do not claim audience size, conversion uplift, ROAS, targeting applied or
   campaign performance from this contract.

0. Ads business context ActionObject truth, 2026-06-20 11:05 Europe/Warsaw:
   the same blocker is now actionable through review-only
   `act_configure_ads_business_context`. Its payload action is
   `configure_ads_business_context`, `mode=prepare_only`,
   `apply_allowed=false`, `destructive=false`, and it lists only non-secret
   business env names. It belongs in `/api/actions`, `/api/ads/diagnostics`,
   Command Center and marketing brief, but not in `/api/opportunities`;
   opportunities remain marketing moves, not setup repair tasks.

0. Ads recommendation apply-preview truth, 2026-06-20 00:20 Europe/Warsaw:
   Google Ads recommendation review now has a typed review-only apply payload
   preview in `/api/ads/diagnostics`, `/api/actions`,
   dashboard `/ads-doctor` and scoped `wilq-ads-doctor` context-pack. Live
   proof `refresh_google_ads_60956db2c42f` /
   `ev_refresh_refresh_google_ads_60956db2c42f` returned 4 active
   recommendations, 2 impact-preview rows and 4 apply payload preview rows.
   `/api/ads/diagnostics.recommendations_read_contract.status=ready`,
   `missing_read_contracts=["human_strategy_review"]`, and
   `action_ids=["act_prepare_google_ads_recommendation_review_queue"]`.
   The ActionObject payload uses
   `preview_contract="recommendation_apply_preview_v1"` and
   `operation_type=ApplyRecommendationOperation`, but keeps
   `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false`.
   Do not call this apply support; it is a review queue and safety preview.
   Full `scripts/verify.sh` passed after this slice: backend `115 passed`,
   dashboard unit `13 passed`, Playwright e2e `9 passed`, security checks,
   skill/API smokes and dashboard production build passed. The security gate
   also required `uv.lock` update `msgpack 1.2.0 -> 1.2.1`.

0. Ads account-currency truth, 2026-06-19 23:12 Europe/Warsaw:
   Google Ads campaign read now includes `customer.currency_code` and persists
   a read-only `account_currency_code` fact. Live proof
   `refresh_google_ads_26cb4673eee2` /
   `ev_refresh_refresh_google_ads_26cb4673eee2` returned
   `customer_currency_code=PLN`, 18 campaign rows, 50 30-day search-term rows,
   200 90-day safety rows, 211 keyword context rows and 4 active
   recommendations. `/api/ads/diagnostics.account_currency_read_contract` is
   `ready` with `currency_code=PLN`, and derived KPI missing contracts no
   longer include `account_currency`. Dashboard `/ads-doctor` formats Ads costs
   in PLN across campaign, KPI, budget, search-term and negative-keyword review
   surfaces. Full `scripts/verify.sh` passed: backend API contracts
   `115 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
   and dashboard production build passed. This is still not profitability
   proof: profit margin, business goal, recommendation apply support and human
   confirmation remain blocked.

0. Ads recommendation impact truth, 2026-06-19 23:44 Europe/Warsaw:
   Google Ads recommendation read now includes `recommendation.impact` and
   persists read-only `recommendation_impact_{base|potential}_*` metric facts.
   Live proof `refresh_google_ads_978ef3a667f6` /
   `ev_refresh_refresh_google_ads_978ef3a667f6` returned 4 active
   recommendations and `recommendation_impact_row_count=2` with
   `recommendation_impact_metric_count=8`.
   `/api/ads/diagnostics.recommendations_read_contract.status=ready`; missing
   contracts after the newer apply-preview slice are now only
   `human_strategy_review`.
   The scoped `wilq-ads-doctor` context-pack exposes the same impact rows:
   `IMPROVE_PERFORMANCE_MAX_AD_STRENGTH` has `delta_cost_micros=4377640`, and
   `SEARCH_PARTNERS_OPT_IN` has zero click/impression/cost deltas in current
   evidence. Some recommendation types legitimately return no impact metrics;
   treat that as per-row `missing_metrics=["recommendation_impact"]`, not a
   global API blocker. This is still review-only: recommendation apply,
   automatic accept, budget apply, campaign mutation and performance-uplift
   claims remain blocked. Full `scripts/verify.sh` passed after this slice:
   backend API contracts `115 passed`, dashboard route tests `13 passed`,
   Playwright e2e `9 passed`, skill/API smokes and dashboard production build
   passed.

0. Local runtime stability rule, 2026-06-19 15:12 Europe/Warsaw: use
   `scripts/local_stack.sh start|stop|restart|status|logs` for the normal local
   WILQ API/dashboard stack. It owns `.local-lab/runtime/{api,dashboard}.pid`
   and logs, reports unmanaged port owners, and keeps canonical URLs
   `http://127.0.0.1:8000/api/health` and
   `http://127.0.0.1:5173/command-center`. Do not hand-roll `nohup`, `setsid`,
   detached `uvicorn`, detached Vite or ad hoc `kill` loops for these ports.
0. Source-to-product lineage rule, 2026-06-19 16:47 Europe/Warsaw: do not fix
   Ads/marketing reasoning by stuffing more edge cases into skill references.
   Current Ads budget review proof lives in typed product state:
   `google_ads_budget_review_playbook` ->
   `card_google_ads_budget_review_playbook` ->
   `/api/ads/diagnostics.ads_review_budget_context` with
   `knowledge_card_ids` and `expert_rule_ids` ->
   dashboard `/ads-doctor` trace lines ->
   `wilq-ads-doctor` scoped context-pack. Redaction must preserve
   `knowledge_card_ids` and `expert_rule_ids`, just like evidence/action IDs.
   Non-interactive proof passed at
   `.local-lab/evals/codex-skill/20260619T144600Z/wilq-ads-doctor/result.json`.
   The first strengthened eval failed because the smoke output did not expose
   lineage IDs; the fix was to make the deterministic smoke script emit the
   typed API lineage, not to make the skill invent it.
0. Runtime truth gotcha, 2026-06-19 16:47 Europe/Warsaw: if live API output
   contradicts source/tests, restart with `scripts/local_stack.sh restart`
   before debugging product logic. The Ads lineage proof initially looked broken
   because the managed API child was stale; after restart,
   `/api/ads/diagnostics` and the scoped context-pack exposed the expected
   `knowledge_card_ids` and `expert_rule_ids`.
0. DailyRuntime performance truth, 2026-06-19 21:13 Europe/Warsaw: the current
   cold-path fix is shared backend work, not frontend memoization. Profiling
   showed repeated wide DuckDB metric fact materialization and duplicate Ads
   action seeding. `build_daily_runtime()` now parallelizes independent daily
   inputs; Command Center passes preloaded ActionObjects into
   `build_ads_diagnostics(actions=...)`; Marketing Brief reads 200 latest metric
   groups per connector, which preserves live dimensional Merchant, GA4, GSC,
   WordPress and Ads facts. Current proof after restart:
   `/api/dashboard/command-center` after TTL is about `1.45-1.51s`,
   `/api/marketing/brief` after TTL is about `1.42-1.50s`, and daily
   `wilq-daily-command` context-pack after TTL is about `1.67-1.76s`. Remaining
   gaps are dashboard JS chunk size and daily context-pack payload size.
0. Daily context-pack payload truth, 2026-06-19 21:32 Europe/Warsaw: default
   `wilq-daily-command` context-pack is intentionally compact. It keeps
   `operator_brief`, `action_plan`, `daily_decisions`, evidence IDs, source
   connectors and core ActionObject IDs, but compacts Marketing Brief metric
   facts, compacts active ActionObjects and omits Command Center
   `connector_health`; full detail stays in `full_context=true` and the API
   endpoints. Current proof: default daily context-pack is `120436 bytes`
   instead of the previous `235159 bytes`, and non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260619T193056Z/wilq-daily-command/result.json`.
   Localo is not a required daily source connector while WILQ lacks Localo
   ranking/GBP evidence.
0. Dashboard bundle truth, 2026-06-19 21:44 Europe/Warsaw: the main Vite JS
   chunk warning was fixed by Rollup manual chunks, not by raising
   `chunkSizeWarningLimit`. Current production build chunks are below 500 KB:
   app `142.44 kB`, `vendor-react` `192.70 kB`, `vendor-tanstack`
   `126.96 kB`, `vendor-schemas` `76.67 kB`, `vendor-icons` `7.91 kB`,
   `vendor-misc` `2.16 kB`. Preserve this split unless a better measured
   lazy-route split replaces it.
0. Non-daily context-pack scope truth, 2026-06-19 22:45 Europe/Warsaw:
   default skill packs must carry decision context, evidence IDs, ActionObject
   IDs and enough examples for the matching workflow, not whole diagnostic
   registries. Current live proof after restart: `wilq-campaign-builder`
   `90711 bytes` with `ads_diagnostics` plus lightweight
   `content_landing_context`; `wilq-demand-gen-operator` `100349 bytes` with
   Ads + GA4 only; `wilq-content-strategist` `91731 bytes`;
   `wilq-ga4-analyst` `28578 bytes`; `wilq-merchant-feed-operator`
   `24007 bytes`; `wilq-ads-doctor` `185126 bytes`;
   `wilq-custom-segments` `187121 bytes`; `wilq-daily-command`
   `120504 bytes`. Full diagnostics remain available through `full_context=true`
   and dedicated API endpoints. Remaining performance gap: Demand Gen cold
   request is about `2.6s`, while warm cache hits are about `0.15s`. Full
   `scripts/verify.sh` passed after this slice with API smoke, skill smokes,
   dashboard route tests, Playwright e2e `9 passed` and dashboard production
   build.
0. Demand Gen campaign-channel truth, updated 2026-06-21 22:53 Europe/Warsaw:
   `wilq-demand-gen-operator` is still correctly blocked, but campaign rows are
   no longer a missing read contract when Google Ads campaign channel facts are
   present, and Demand Gen ad/creative empty-read contracts are now available.
   Live API proof after restarting the 8000 API process:
   `campaign_rows_evaluated=18`,
   `campaign_channel_counts={PERFORMANCE_MAX: 8, SEARCH: 10}`,
   `demand_gen_campaign_rows=[]`, `demand_gen_ad_group_ad_rows=[]`,
   `demand_gen_creative_asset_rows=[]`,
   `active_action_objects=[act_review_demand_gen_readiness]` and
   `ads_diagnostics.action_ids=[]`. `demand_gen_campaign_rows`,
   `demand_gen_ad_group_ad_rows` and `demand_gen_creative_asset_rows` are now
   available read contracts. Remaining missing contracts are
   `demand_gen_landing_quality_by_campaign` and
   `demand_gen_migration_constraints`. Do not
   unlock launch/migration recommendations from this; it only proves there are
   currently no Demand Gen/Discovery campaign rows in the Ads evidence. Full
   `scripts/verify.sh` passed after this slice: backend `123 passed`,
   dashboard unit `15 passed`, Playwright e2e `12 passed`, dashboard build OK.
0. Custom segments payload-preview truth, 2026-06-19 22:08 Europe/Warsaw:
   custom segments now have a typed review-only payload preview in
   `/api/ads/diagnostics`, `/api/actions/act_prepare_custom_segments_from_search_terms`
   and `/ads-doctor`. This is not apply support. Keep
   `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false` until
   Keyword Planner enrichment, forecast/audience-size, human confirmation and
   Ads apply/audit contracts exist. Default `wilq-custom-segments`
   context-pack is scoped to Ads diagnostics, omits `content_diagnostics` and
   measures about `186317 bytes`. Latest eval artifact:
   `.local-lab/evals/codex-skill/20260619T201200Z/wilq-custom-segments/result.json`.
0. Ads recommendations truth, 2026-06-19 17:22 Europe/Warsaw: Google Ads
   recommendation review is now a typed read-only contract, not a prompt TODO.
   Live proof `refresh_google_ads_138befce0a2c` /
   `ev_refresh_refresh_google_ads_138befce0a2c` returned 4 active
   recommendations: `DISPLAY_EXPANSION_OPT_IN`,
   `DYNAMIC_IMAGE_EXTENSION_OPT_IN`,
   `IMPROVE_PERFORMANCE_MAX_AD_STRENGTH`, `SEARCH_PARTNERS_OPT_IN`.
   `/api/ads/diagnostics.recommendations_read_contract.status=ready`, decision
   queue includes `ads_review_recommendations`, and scoped
   `wilq-ads-doctor` context-pack exposes the same contract. Historical note:
   at this point impact preview was still missing; see the newer 2026-06-19
   23:44 entry above for the current impact-read truth. Do not call
   recommendations apply-ready until human review and recommendation apply
   preview exist.
0. Ads impression-share truth, 2026-06-19 17:55 Europe/Warsaw: Google Ads
   impression share is now a typed read-only contract, not a missing Ads
   optimizer blocker. Live proof `refresh_google_ads_baba7f993f1a` /
   `ev_refresh_refresh_google_ads_baba7f993f1a` returned
   `impression_share_row_count=2`. `/api/ads/diagnostics` exposes
   `impression_share_read_contract.status=ready` and decision
   `ads_review_impression_share`; scoped `wilq-ads-doctor` context-pack exposes
   the same contract. Current live rows: `Kompendium PPWR` has search IS
   `0.2322`, budget-lost IS `0.5924`, rank-lost IS `0.1754`; `(2026) Ekologus
   Ogólna` has search IS `0.1819`, budget-lost IS `0.0075`, rank-lost IS
   `0.8106`. Do not call this budget scaling or wasted-budget proof: change
   history, human budget goal and budget apply preview remain missing.
0. Ads change-history truth, 2026-06-19 18:19 Europe/Warsaw: Google Ads
   change history is now a typed read-only contract. Live proof
   `refresh_google_ads_e7f371e9efac` /
   `ev_refresh_refresh_google_ads_e7f371e9efac` returned
   `change_event_row_count=0`; `/api/ads/diagnostics` exposes
   `change_history_read_contract.status=ready`, decision
   `ads_review_change_history`, and section `ads_change_history`. This means
   WILQ successfully queried `change_event` for the last 14 days and found no
   events. It is not change-impact proof. Keep `change impact`,
   `performance uplift`, `budget scaling`, `budget apply` and
   `campaign mutation` blocked until pre/post performance windows, human review
   and apply preview exist. Non-interactive `wilq-ads-doctor` eval passed at
   `.local-lab/evals/codex-skill/20260619T162014Z/wilq-ads-doctor/result.json`.
0. Ads search-term review gate truth, live proof 2026-06-20 15:52 CEST:
   `negative_keyword_action_validation` is an operator review gate, not a
   missing read contract. `/api/ads/diagnostics.search_terms_read_contract` is
   `ready` with 50 rows, `missing_read_contracts=[]` and
   `operator_review_gates=[negative_keyword_action_validation]`.
   Decision `ads_review_search_terms` shows `zapytania=50`, `kliknięcia=7`,
   `koszt=41.8`, no missing read contracts, and ActionObjects
   `act_prepare_custom_segments_from_search_terms` plus
   `act_prepare_negative_keyword_review_queue`. Dashboard `/ads-doctor` must
   show this as `Wymaga review`, not as `Brakujące kontrakty`.

0. Ads 90-day search-term safety truth, 2026-06-19 18:57 Europe/Warsaw:
   Google Ads negative keyword review now has a typed 90-day safety read.
   Live proof `refresh_google_ads_5a0c672b5000` /
   `ev_refresh_refresh_google_ads_5a0c672b5000` returned 50 30-day
   search-term rows and 200 90-day `search_term_90d_*` rows.
   `/api/ads/diagnostics.search_term_safety_read_contract.status=ready`, the
   decision queue includes `ads_review_search_term_safety`, and
   `negative_keywords_read_contract` has 7 review-only candidates without
   `90_day_safety_check` as a missing contract. Do not call this apply-ready:
   `negative keyword apply`, `search-term waste`, CPA, ROAS and
   conversion-loss claims remain blocked until keyword match context, payload
   preview, ActionObject validation and human review exist. Gotcha: Ads
   diagnostics and action generation must use a large enough Google Ads metric
   fact window, otherwise 200 safety rows can push 30-day search-term facts out
   of view. Non-interactive `wilq-ads-doctor` eval passed at
   `.local-lab/evals/codex-skill/20260619T165729Z/wilq-ads-doctor/result.json`.
0. Ads keyword match context truth, 2026-06-19 20:17 Europe/Warsaw:
   Google Ads negative keyword review now has typed read-only context for
   existing account keywords and match types. Live proof
   `refresh_google_ads_eb8c239bc32b` /
   `ev_refresh_refresh_google_ads_eb8c239bc32b` returned 211
   `keyword_match_context` rows from `ad_group_criterion`. `/api/ads/diagnostics`
   exposes `keyword_match_context_read_contract.status=ready` with
   `operator_review_gates=[human_intent_review]`. `negative_keywords_read_contract` now has 7
   candidates, 7 payload preview rows and `missing_read_contracts=[]`. This is
   still not apply-ready: negative keyword apply, search-term waste,
   conversion loss, CPA and ROAS stay blocked until human review/confirmation
   and future apply/audit contracts exist. Non-interactive
   `wilq-ads-doctor` eval passed at
   `.local-lab/evals/codex-skill/20260619T182309Z/wilq-ads-doctor/result.json`
   after the eval case was tightened to require
   `keyword_match_context_read_contract` and forbid stale `bez match context`
   wording.
0. Recovery truth, 2026-06-19 14:53 Europe/Warsaw: connector summary is
   `total=12`, `configured=9`, `missing_credentials=2`, `disabled=1`.
   `google_sheets` is intentionally disabled for this Ekologus scope.
   `linkedin` and `facebook` are missing credential surfaces; they block
   publishing, not prepare-only evidence-backed drafting. The knowledge layer
   is explicitly in the active goal, but it is not fully proven: future slices
   must connect source-backed marketing standards/papers/practitioner sources
   to knowledge cards or expert rules, then to typed WILQ API view-models,
   dashboard decisions and non-interactive Codex skill outputs.
0. Overnight recovery truth, 2026-06-19 09:37 Europe/Warsaw: after
   `3a7d4ab test(skills): prove localo access-ready blocker`, the next Merchant
   slice fixed issue-cluster preservation. `MERCHANT_METRIC_FACT_LIMIT` was too
   low and live issue-level facts were truncated out of
   `/api/merchant/diagnostics`. Fresh proof on temporary API `:8015` showed
   `issue_cluster_count=11`, and non-interactive eval passed:
   `.local-lab/evals/codex-skill/20260619T073915Z/wilq-merchant-feed-operator/result.json`.
   Final proof for this Merchant fix: `scripts/verify.sh` passed with backend
   API contracts `102 passed`, dashboard route tests `13 passed`, Playwright
   e2e `9 passed`, skill API smoke passed and dashboard build passed.
   Temporary API/e2e ports were cleaned up after verification.
1. Command Center first-screen cleanup is implemented and verified: one
   `Dzisiejsze decyzje marketera` board, no duplicated `Plan działań marketera`
   and no full connector blocker cards on `/command-center`.
2. Ads campaign/search-term/budget/recommendation/impression-share read contracts are
   implemented with conversion counts/value, read-only budget context and
   read-only recommendation/impression-share review. Latest local work adds
   `impression_share_read_contract.status=ready`, 2 impression-share rows from
   `refresh_google_ads_baba7f993f1a`, and decision
   `ads_review_impression_share`. This is still not budget/waste/apply.
   Continue with change history, keyword/match context, full 90-day safety,
   human budget goals, recommendation apply support/audit and
   value/account-currency semantics before any money-leak/CPA/ROAS/budget
   scaling/negative-keyword apply claims. Full `scripts/verify.sh` passed for
   this slice with backend `108 passed`, dashboard unit `13 passed`,
   Playwright e2e `9 passed`, skill smokes and dashboard production build.
3. Repair each skill only after the matching API/read contract exists.

Recently completed and pushed foundations:

- `2e0b0dc feat(content): expose content decision queue`
- `39511ac feat(command-center): add daily decision model`
- `8cfdf83 perf(codex): scope daily command context pack`
- `de09cab perf(api): batch metric fact reads`
- `ad17223 perf(api): slim command center runtime`

Current performance slice truth:

- `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` now defaults
  to `context_scope.mode=daily`.
- Default daily context excludes full tactical queue and diagnostics. Use
  `{"skill":"wilq-daily-command","full_context":true}` for debug/full mode.
- Latest fresh `:8011` proof after the local patch:
  - daily context-pack: about `2.9s`, `160053 bytes`;
  - full daily context-pack: about `6.5s`, `998704 bytes`;
  - marketing brief: about `0.5s`, `46072 bytes`;
  - command-center: about `2.1-2.4s`, `30521 bytes`.
- Current follow-up adds a shared `DailyRuntime` view-model for
  daily Codex context. It builds `command_center`, `marketing_brief` and core
  actions from one connector/action/refresh snapshot and caches that runtime
  for a short operator TTL. The default TTL is now 30 seconds and is still
  invalidated after connector refresh and action validation/apply paths. Fresh
  helper API proof on `:8011`: cold daily context
  `3.047s`, then warm cached daily context `0.467s`, `0.544s`, `0.470s`, same
  payload size `160478 bytes`.
- This is improved from the old full context-pack (`~996 KB`, `~15s`) but not
  done. Batch DuckDB reads and read-only metric-store connections fixed a
  conflicting-lock runtime risk. Remaining cold-run bottleneck: diagnostics
  inside Command Center, especially the tactical/diagnostic joins used before
  Merchant issue-level triage and URL normalization are fully shaped.
- 2026-06-19 follow-up pushed as `ad17223`: Command Center first-screen cards now reuse
  preloaded `tactical_queue`/`actions`; Content/GA4 cards no longer build full
  diagnostics; Merchant card reads `google_merchant_center` metric facts
  directly instead of full Merchant Diagnostics. Direct cold proof improved to
  `build_command_center_response() ~=1.7-2.1s` and
  `build_daily_runtime() ~=2.1s`; HTTP proof on fresh `:8016` showed cold
  Command Center `2.526s` and warm TTL `0.011-0.012s`. Daily context-pack can
  still spike after TTL (`3.451s` observed), so this is not final performance
  completion.
- Active 2026-06-19 follow-up after `ad17223`: daily context-pack now reuses
  `DailyRuntime.refresh_runs` and targeted `list_evidence_by_ids()` instead of
  scanning the full evidence registry. Local `:8000` proof: daily context-pack
  after TTL `2.548s`, warm `0.273-0.324s`, size `171000 bytes`; Command Center
  after TTL `2.009s`, warm `0.008s`, size `26629 bytes`. This improves the
  context-pack TTL spike, but full performance is not done.
- Active 2026-06-19 Ads skill follow-up after keyword context: scoped
  `wilq-ads-doctor` context-pack now removes `*_metric_facts`, keeps full
  detail available at `/api/ads/diagnostics`, limits embedded Ads sample rows
  for skill runtime, strips duplicated nested candidate `payload_preview`,
  trims ActionObject payload row arrays while preserving totals, limits scoped
  connector refresh runs to 3, and uses a short 5s API-side context cache. The
  cache is only a compute shortcut; it is cleared after connector refresh,
  ActionObject validation and apply. Local `:8000` proof: Ads context-pack
  `198513 bytes`, cold `1.281-1.620s`, warm `0.145-0.159s`; full totals remain
  in `context_pack_compaction` with embedded samples
  `search_term_rows_included=8`, `search_term_safety_rows_included=8`,
  `keyword_match_context_rows_included=8` and
  `negative_keyword_candidates_included=4`. Non-interactive
  `wilq-ads-doctor` eval passed at
  `.local-lab/evals/codex-skill/20260619T184940Z/wilq-ads-doctor/result.json`.
  Remaining performance gaps: Command Center cold path is still about `2.2s`,
  daily context-pack is about `237939 bytes`, and dashboard JS chunk is still
  above Vite's 500 KB warning.
- Active 2026-06-19 Command Center GA4 fallback: `/api/ga4/diagnostics`
  had live GA4 dimensional facts (`landing_group_count=10`), but Command
  Center could show `landing groups=0` because it only counted GA4 tactical
  queue items. Command Center now reads a lightweight GA4 metric-fact fallback
  directly and keeps GA4 as `blocked` for missing interpretation contracts.
  Live `:8000` proof after restart: GA4 daily decision title
  `GA4: brak pełnego kontraktu interpretacji ruchu`, metric tiles
  `landing groups=10`, `low engagement=0`, `WP match=0`, `blockery=1`,
  evidence `ev_refresh_refresh_google_analytics_4_681b6bcefc85`, action
  `act_review_ga4_tracking_quality`. Targeted Playwright dashboard-api spec
  passed `8 passed` on `:8000/:5173`.
- Active 2026-06-19 Ads campaign review ActionObject:
  `act_prepare_ads_campaign_review_queue` is implemented with payload type
  `campaign_change_review`. It is generated from live `google_ads` campaign
  metric facts, exposes up to 8 campaign candidates, includes budget context
  when available, and now also has read-only recommendations and
  impression-share contracts. It still requires change history, value/currency
  review, budget/apply preview and human confirmation before any apply path. It
  keeps `apply_allowed=false` plus `destructive=false`. Live `:8000` proof
  after restart: Ads diagnostics includes the new action ID, campaign and
  derived KPI decisions attach only this campaign action, and validation
  returns `valid=true`. This closes the first campaign ActionObject gap, not
  the full Ads optimizer. Full `scripts/verify.sh` passed for this slice with
  backend API contracts `108 passed`, dashboard route tests `13 passed`,
  Playwright e2e `9 passed` and dashboard production build passed.

Current Ads negative-keyword safety truth:

- `negative_keyword_payload_preview` and `keyword_match_context` are now
  implemented as review-only contracts, not apply contracts. Live
  `/api/ads/diagnostics` shows
  `negative_keywords_read_contract.payload_preview` with 7 items and
  `missing_read_contracts=[]`; the keyword context contract is ready with 211
  rows and only `human_intent_review` missing.
- `act_prepare_negative_keyword_review_queue.payload` includes
  `preview_contract=negative_keyword_payload_preview_v1`,
  `api_mutation_ready=false`, `apply_allowed=false`, `destructive=false` and
  exact-match preview rows with evidence IDs.
- Do not describe these rows as ready negative keywords. They are a review
  preview for the marketer. Still blocked: negative keyword apply,
  search-term waste, conversion loss, CPA and ROAS until human review,
  confirmation, apply/audit contracts and stronger intent validation exist.
  Full `scripts/verify.sh` passed after the newest keyword-context slice with
  backend API contracts `111 passed`, dashboard route tests `13 passed`,
  Playwright e2e `9 passed`, API smoke, skill smokes and dashboard production
  build passed. Non-blocking warning: Vite main JS chunk `549.44 kB` exceeds
  the 500 KB warning threshold.

Current hook-runtime truth:

- If WILQ API is unreachable, SessionStart may report that as context. It is
  not a product blocker by itself.
- Stop hook must not print plain text on stdout. `.codex/hooks/stop_log.py`
  emits valid JSON with `continue=true` for unreachable API or unsupported API
  URL skip paths.
- `.codex/hooks.json` must use `uv run python` from repo root for hooks; do not
  reintroduce global `python3`.

Current Merchant slice truth:

- `MerchantIssueCluster` is implemented in Python and shared frontend schemas.
- `/api/merchant/diagnostics` returns `issue_clusters` grouped by issue type,
  affected attribute, country, reporting context, severity and resolution.
- `act_review_merchant_feed_issues` includes issue clusters in its payload.
- Dashboard `/merchant` renders issue clusters as the primary review queue.
- Full `scripts/verify.sh` passed for this slice on 2026-06-18.
- Current Merchant read contract still exposes aggregate issue dimensions and
  counts only; no sample product IDs/titles yet.
- Active WIP on 2026-06-19: if live Merchant diagnostics reports
  `issue_count > 0`, the smoke script must require `issue_clusters`. This guards
  against a regression where DuckDB metric fact row limits hide issue-level
  rows while aggregate Merchant facts remain visible.
- Fresh Merchant skill proof: `wilq-merchant-feed-operator` passed
  non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260619T073915Z/wilq-merchant-feed-operator/result.json`.
  It reports `product_count=10900`, `issue_count=15`,
  `issue_cluster_count=11`, recommends `act_review_merchant_feed_issues`, and
  blocks automatic feed edit/product mutation claims.
- Dashboard demo proof now asserts the Merchant issue-cluster view
  (`Zgłoszenia` plus issue types such as
  `missing_potentially_required_attribute` / `availability_updated`) instead of
  the old stale `Merchant: status produktów PL` copy.

Current content URL normalization truth:

- Tactical queue reads enough WordPress inventory rows from DuckDB to keep large
  sitemap inventories in the WordPress index.
- GSC full URLs and GA4 landing paths are normalized to stable path keys.
- `ContentDecisionItem` now exposes `normalized_page_path`,
  `wordpress_match_confidence` and `wordpress_content_url`.
- Context-pack redaction preserves these public URL/path fields while still
  redacting token-like secret values.
- Direct checkout proof shows BDO, Zielony Ład and remediacja GSC URLs as
  `found exact_url`; GA4 landing paths resolve with `path_fallback`.
- Full `scripts/verify.sh` passed for this slice on 2026-06-18.

Current Command Center cleanup truth:

- `/command-center` renders `daily_decisions` as the single marketer decision
  board.
- The old summary/plan duplication is removed from the first screen.
- Full connector blocker/status cards are no longer rendered on
  `/command-center`; the compact `Źródła i ograniczenia` footer links to
  `/settings`.
- Focused frontend/backend checks and full `scripts/verify.sh` passed on
  2026-06-18 after the cleanup.

Current Ads Doctor contract truth:

- `/api/ads/diagnostics.campaign_read_contract` is typed and rendered on
  `/ads-doctor`.
- It groups live Google Ads metric facts into campaign rows with campaign ID,
  campaign name, clicks, impressions, cost micros, conversions, conversion
  value, evidence IDs and blocked claims.
- It explicitly limits allowed metrics to `clicks`, `impressions`,
  `cost_micros`, `conversions` and `conversion_value`.
- `/api/ads/diagnostics.search_terms_read_contract` is typed and rendered on
  `/ads-doctor`.
- Google Ads `vendor_read` now queries `search_term_view` read-only and stores
  `search_term_clicks`, `search_term_impressions` and
  `search_term_cost_micros`, `search_term_conversions` and
  `search_term_conversion_value` with campaign, ad group, search term and
  status dimensions.
- Search terms rows are for read-only review. Latest work adds
  `/api/ads/diagnostics.negative_keywords_read_contract` and
  `act_prepare_negative_keyword_review_queue` for prepare-only safety review of
  zero-conversion search terms with activity. Do not claim search-term waste,
  CPA, ROAS, conversion loss or negative keyword apply until keyword/match
  context, full 90-day safety, derived KPI semantics and validated preview/apply
  contracts exist.
- Live proof on 2026-06-18:
  `refresh_google_ads_c2f62ee2b43a` completed with 18 campaign rows, 50 search
  term rows, `conversions=2.0`, `conversion_value=2.0`,
  `search_term_conversions=0.0` and
  `search_term_conversion_value=0.0`.
- Still missing read contracts: recommendations, change history, impression
  share, keyword/match context, full 90-day safety history, payload previews for
  apply paths, human budget goals and explicit profitability/account-currency
  interpretation.

Do not repair product logic inside skill references. If a skill needs a better
decision, add the typed WILQ API/schema/view-model field first and make the
skill consume it.

## Current Runtime

- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:5173/command-center`
- API health: `curl -sf http://127.0.0.1:8000/api/health`
- Final gate: `scripts/verify.sh`

## Latest Localo Skill Proof

- `wilq-localo-operator` passed non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260619T072709Z/wilq-localo-operator/result.json`.
- Localo access is ready: `localo_access_status=access_ready`,
  `localo_refresh_status=completed`, `mcp_initialize_status=200`.
- The skill correctly blocks ranking, GBP, competitor and local visibility
  uplift claims because WILQ has no Localo visibility facts beyond MCP/OAuth
  access probe.
- There is no Localo write/apply path yet: `action_ids=[]`.

## Skill Eval Harness

Istniejący harness non-interactive:

```bash
scripts/codex_skill_eval.sh --all --api-base http://127.0.0.1:8000
scripts/codex_skill_eval.sh --skill wilq-content-strategist --api-base http://127.0.0.1:8000
```

Ważne pliki:

- `scripts/codex_skill_eval.sh`
- `docs/evals/cases/wilq-skill-eval-cases.json`
- `docs/evals/schemas/wilq-skill-eval-result.schema.json`
- `.agents/skills/*/scripts/smoke_*`

Harness sprawdza schema, język PL, API usage, evidence/source connectors i
ActionObject safety. Wspiera też case-specific guardrails:
`expected_blocked`, `expected_no_action_ids`, `blocked_claim_terms` i
`forbidden_action_ids`. Używaj ich, gdy skill ma zwrócić blocker zamiast
rekomendacji albo nie może dziedziczyć ActionObjectów z sąsiedniego workflow.
Nie zastępuje ręcznej oceny użyteczności odpowiedzi dla marketera; tę ocenę
zapisujemy w `docs/evals/skill-eval-ledger.md`.

## Skill Eval Pipeline

Cel: udowodnić, że WILQ skill realnie pomaga polskiemu marketerowi, a nie tylko
zwraca poprawny JSON. Każdy skill musi przejść przez ten sam pipeline.

### 1. Preflight

Sprawdź aktualną prawdę runtime:

```bash
curl -sf http://127.0.0.1:8000/api/health
git status --short
```

Nie zaczynaj od pamięci rozmowy. Jeśli API nie działa, najpierw napraw runtime
albo zapisz blocker w `docs/PROGRESS.md`.

### 2. Ręczny prompt marketera

Użyj realistycznego polskiego promptu, takiego jak marketer faktycznie zada:

```text
Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh, merge,
create albo block dla Ekologus na podstawie GSC, WordPress, GA4 i Ahrefs
evidence. Nie obiecuj leadów, revenue ani wzrostów pozycji.
```

Oczekiwany przebieg:

- skill czyta swój `SKILL.md`,
- skill czyta wymagane `references/`,
- skill pobiera WILQ API evidence,
- skill cytuje source connector IDs i evidence IDs,
- skill wskazuje ActionObject IDs, jeśli API je udostępnia,
- skill blokuje unsupported claims,
- odpowiedź jest po polsku z polskimi znakami.

Manualny wynik zapisuj w `docs/evals/skill-eval-ledger.md`, nawet jeśli potem
non-interactive eval przejdzie. Manualny przebieg jest często bogatszy i pokazuje
realną użyteczność dla marketera.

### 3. Deterministic smoke

Uruchom smoke script skilla:

```bash
uv run python .agents/skills/<skill>/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Dla `wilq-daily-command` użyj:

```bash
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
```

Smoke potwierdza kontrakt API/skilla, ale sam nie dowodzi jakości odpowiedzi.

### 4. Non-interactive Codex eval

Uruchom `codex exec` przez harness:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill <skill> --api-base http://127.0.0.1:8000
```

Używaj `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1`, gdy globalna konfiguracja
Codexa/MCP może powodować poboczne błędy transportu. Eval ma mierzyć WILQ
skill/API, nie przypadkowe globalne narzędzia.

Wyniki zapisują się w:

```text
.local-lab/evals/codex-skill/<timestamp>/<skill>/
  prompt.md
  result.json
  trace.jsonl
  stderr.log
```

Nie commituj `.local-lab`.

### 5. Interpretacja pass/fail

`passed` oznacza tylko, że wynik spełnił obecne warunki harnessa:

- `language=pl-PL`,
- polskie znaki,
- `api_used=true`,
- zgodność ze schemą,
- source connectors,
- evidence IDs,
- ActionObject safety,
- brak oczywistych unsafe claims.

To nie zawsze oznacza, że skill dał świetną decyzję marketingową. Po każdym
passie zapisz ocenę jakości:

- Czy odpowiedź jest konkretna, czy ogólna?
- Czy daje kolejkę decyzji, czy tylko opisuje zasady?
- Czy używa tych samych evidence IDs co dashboard/API?
- Czy wskazuje najmniejszy bezpieczny następny krok?
- Czy blokuje metryki, których WILQ nie ma?
- Czy marketer może od razu coś zrobić?

Jeśli pass jest zbyt ogólny, nie traktuj go jako koniec pracy. Dopisz gap do
`docs/evals/skill-eval-ledger.md` i wzmocnij case/harness tak, żeby wymagał
konkretnych decyzji.

### 6. Aktualizacja dokumentów

Po każdym istotnym przebiegu zaktualizuj:

- `docs/evals/skill-eval-ledger.md` - prompt, endpointy, wynik, evidence IDs,
  ActionObject IDs, jakość odpowiedzi i product gaps.
- `docs/PROGRESS.md` - krótki aktualny stan i ścieżka artefaktu.
- `docs/goals/001-goal.md` - tylko jeśli zmienia się aktywny goal, blocker,
  acceptance gate albo następny krok.

### Aktualny znany wynik referencyjny

Pierwszy pełny przebieg:

```text
skill: wilq-content-strategist
manual prompt: completed and useful
non-interactive eval: passed
artifact: .local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json
```

Wynik zawierał:

- `pl-PL`,
- polskie znaki,
- `api_used=true`,
- evidence IDs,
- source connectors,
- `act_prepare_content_refresh_queue`.

Najważniejszy wniosek: obecny harness dobrze łapie kontrakt, API usage i brak
halucynacji, ale za słabo mierzy "czy skill dał świetną kolejkę decyzji".
Manualny przebieg był bogatszy, bo wyciągnął konkretne decyzje: BDO refresh,
Zielony Ład merge/create-after-inventory-check, homepage low-priority refresh i
GA4 `(not set)` jako block. Następny poziom evali musi tego wymagać wprost.

### Następna kolejność skillów

Najpierw testuj skille, które mają realne ActionObjects i największą wartość
dla demo:

1. `wilq-merchant-feed-operator` - `act_review_merchant_feed_issues`.
2. `wilq-ga4-analyst` - `act_review_ga4_tracking_quality`.
3. `wilq-gsc-content-doctor` - `act_prepare_content_refresh_queue`.
4. `wilq-ads-doctor` - live campaign evidence; search terms/CPA/ROAS nadal
   wymagają osobnych read contracts.
5. `wilq-localo-operator` - access działa, ale local ranking/GBP facts są nadal
   blocked.

Po nich wróć do skillów bez aktualnego ActionObject i oceń, czy powinny dostać
nowe API/action contracts, czy pozostać blocker/readiness workflows.

## Current Product Direction

Command Center ma być "co marketer robi dziś", nie connector inventory.
Codex skills mają być operacyjną warstwą nad WILQ API: najpierw API evidence,
potem diagnoza, blokady claimów i bezpieczny następny krok po polsku.

## Current Critical Direction - 2026-06-18 13:55

Najważniejszy świeży audyt:

```txt
docs/audits/001-output.md
```

Wniosek audytu: architektura idzie w dobrym kierunku, ale WILQ jest nadal
`safe operating shell`, nie pełny BDOS-class OS. Największy problem to nie
liczba skillów, tylko brak jednego canonical operator view modelu i brak części
read/action contracts. API ma być mózgiem; skills mają być cienkimi workflow po
API.

Twarda zasada zapisana w `AGENTS.md`: nie wolno łatać logiki produktu,
deduplikacji, klasyfikacji decyzji, rankingów ani edge-case fixes w skill
references. Jeśli skill potrzebuje mądrzejszej decyzji, najpierw implementujemy
typed WILQ API/schema/view-model, a skill tylko konsumuje pole API.

## Recently Completed - Shared Daily Runtime Endpoints

This slice is done and pushed as `35d8be3 perf(api): share daily runtime endpoints`.
Do not resume it as active work unless a new performance regression is found.

What changed:

- `GET /api/dashboard/command-center` returns
  `build_daily_runtime().command_center`.
- `GET /api/marketing/brief` returns
  `build_daily_runtime().marketing_brief`.
- `connector_refresh()` clears `clear_daily_runtime_cache()` after refresh.
- Endpoint regression tests cover both daily-runtime-backed routes.

Full proof before commit:

```bash
scripts/verify.sh
```

Result:

- backend API contracts: `102 passed`;
- dashboard route tests: `13 passed`;
- Playwright e2e: `9 passed`;
- skill API smoke: passed;
- dashboard production build: passed;
- non-blocking warning: Vite main chunk is above 500 KB.

## Latest Slice - Ads Negative Keyword Safety Review

Ads safety slice is implemented and verified locally. Nie zaczynaj od zera i
nie cofaj poprzednich route/performance cleanupów.

Commit: `c68a9fd feat(ads): add negative keyword safety review`.

Cel slice'a:

- Dodać Ads negative keyword safety review jako prepare-only contract.
- Użyć realnych Google Ads search-term metric facts, ale nie claimować waste.
- Wystawić ten sam stan przez API, dashboard, shared schema, ActionObject i
  `wilq-ads-doctor` smoke/eval contract.
- Zablokować `negative keyword apply`, `search-term waste`, CPA, ROAS,
  conversion loss i automatyczne zmiany bez walidacji.

Main files:

- `wilq/actions/google_ads/negative_keywords.py`
- `wilq/actions/payloads.py`
- `wilq/actions/service.py`
- `wilq/briefing/ads_diagnostics.py`
- `wilq/schemas.py`
- `packages/shared-schemas/src/index.ts`
- `apps/dashboard/src/routes/App.tsx`
- `apps/dashboard/src/routes/App.test.tsx`
- `.agents/skills/wilq-ads-doctor/SKILL.md`
- `.agents/skills/wilq-ads-doctor/references/output-contract.md`
- `.agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`
- `tests/test_api_contracts.py`
- `tests/test_codex_skill_eval_cases.py`
- `docs/evals/cases/wilq-skill-eval-cases.json`

Implemented contract:

- New ActionObject ID: `act_prepare_negative_keyword_review_queue`.
- New diagnostics contract:
  `/api/ads/diagnostics.negative_keywords_read_contract`.
- New Ads decision type: `review_negative_keyword_safety`.
- Candidates are built only from grouped `search_term_*` metric facts with
  activity and zero conversions/conversion value in current evidence.
- Candidate payloads require:
  `apply_allowed=false`, `destructive=false`,
  `required_validation=["90_day_safety_check", ...]` and evidence IDs.
- Dashboard `/ads-doctor` shows candidates as review/safety cards, not ready
  exclusions.
- `wilq-ads-doctor` smoke now fails if the negative keyword contract is ready
  without candidates/action ID or blocked without missing contracts.

Focused proof already passed:

```bash
uv run ruff check wilq/actions/google_ads/negative_keywords.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/schemas.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run mypy wilq/actions/google_ads/negative_keywords.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/schemas.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ads_diagnostics or custom_segments or negative_keyword or route_specific'
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
```

Wynik:

- ruff: passed.
- mypy: passed.
- backend selected tests: 4 passed.
- dashboard typecheck: passed.
- shared schema typecheck: passed.
- dashboard route tests: 13 passed.

Full proof before commit:

```bash
scripts/verify.sh
```

Result:

- backend API contracts: `102 passed`;
- dashboard route tests: `13 passed`;
- Playwright e2e: `9 passed`;
- skill API smoke: passed;
- dashboard production build: passed;
- non-blocking warning: Vite main chunk is above 500 KB.

Fresh Codex eval proof:

- Artifact:
  `.local-lab/evals/codex-skill/20260619T065511Z/wilq-ads-doctor/result.json`.
- Result: `pl-PL`, Polish diacritics, `api_used=true`,
  `operator_usefulness_score=5`, no safety findings.
- Evidence IDs:
  `ev_connector_google_ads_status`,
  `ev_refresh_refresh_google_ads_c2f62ee2b43a`.
- Confirms `negative_keywords_read_contract.status=ready`,
  `candidate_count=7` and `act_prepare_negative_keyword_review_queue`.
- Blocks `negative keyword apply`, search-term waste, wasted budget, CPA and
  ROAS without `90_day_safety_check`, payload preview and validated
  ActionObject.
- Smoke script now summarizes `blocked_handoff=null` correctly for live Ads
  diagnostics instead of assuming an OAuth blocker object.

## Latest Localo Aggregate Facts Slice

Status: implemented, full `scripts/verify.sh` passed.

What changed:

- `wilq.connectors.localo.client.refresh_localo_visibility_summary()` now uses
  Localo MCP as a read-only adapter after initialize:
  `notifications/initialized`, then `tools/call` with GraphQL `query`.
- The adapter stores aggregate facts only. It must not store raw Localo place
  names, addresses, keywords, categories or Localo IDs.
- Current live refresh:
  `refresh_localo_9e9ff67eadad`, evidence
  `ev_refresh_refresh_localo_9e9ff67eadad`.
- Current live aggregate facts:
  `localo_active_place_count=4`,
  `localo_tracked_keyword_count=23`,
  `localo_avg_visibility_current=52.8261`,
  `localo_avg_latest_grid_position=3.2105`,
  `localo_reviews_count=793`,
  `localo_review_reply_rate=0.809584`.
- `/api/localo/diagnostics` now reports:
  `live_data_available=true`, `visibility_fact_count=17`,
  `allowed_evidence=[place_inventory, local_rankings, reviews]`,
  `missing_read_contracts=[gbp_visibility, competitor_visibility, local_tasks]`.
- Command Center now promotes Localo only when real Localo facts exist or access
  is genuinely blocked. Current live card tiles:
  `miejsca=4`, `frazy=23`, `widoczność=52.8261`, `recenzje=793`.
- `POST /api/codex/context-pack {"skill":"wilq-localo-operator"}` includes
  the same Localo diagnostics. Redaction was fixed so metric names like
  `localo_latest_grid_position_count` are not replaced with `[REDACTED]`.

Still blocked by design:

- Do not claim `GBP performance`, `competitor visibility`,
  `local task completed`, `GBP write` or `local visibility uplift`.
- Localo facts currently support review of aggregate place inventory,
  local-ranking aggregates and reviews only. They do not prove competitor
  movement, GBP profile performance or improvement after an action.

Final proof:

- `scripts/verify.sh` passed after this slice.
- Backend API contracts: `122 passed`.
- Dashboard route unit tests: `14 passed`.
- Playwright e2e: `11 passed`.
- Skill/API smokes and dashboard production build passed.

## Latest Ahrefs Diagnostics Slice

Status: implemented; full `scripts/verify.sh` passed. Follow-up strict skill
eval also passed.

What changed:

- `/api/ahrefs/diagnostics` now exposes typed Ahrefs decisions instead of
  relying on generic metric cards.
- Dashboard `/ahrefs` renders `Status Ahrefs / dowody SEO`,
  `Co marketer ma wiedzieć o Ahrefs` and `Dowody i ograniczenia Ahrefs`.
- Scoped `POST /api/codex/context-pack {"skill":"wilq-ahrefs-gap-finder"}`
  contains `ahrefs_diagnostics`, omits `marketing_brief` and
  `content_diagnostics`, and has `active_action_ids=[]`.
- Skill smoke now fails if Ahrefs diagnostics has no actions but the context
  pack exposes adjacent ActionObjects.
- Strict non-interactive eval now targets `/ahrefs`, requires
  `ahrefs_diagnostics`, `ahrefs_block_gap_claims_without_records`,
  `blocked=true`, no non-null `action_id`, and forbids adjacent content/Ads/
  Merchant/GA4 ActionObjects.

Historical live proof after the 2026-06-21 Ahrefs target fix, superseded by the
05:05 content/backlink-gap proof near the top of this file:

- `/api/ahrefs/diagnostics.live_data_available=true`.
- `authority_fact_count=2`, `gap_fact_count=10`, `blocker_count=1`.
- Authority facts: `DR=40`, `Ahrefs Rank=1541946`.
- Organic competitor read: `organic_competitor_read_status=completed`,
  `organic_competitor_rows=10`, `organic_competitor_country=pl`,
  `organic_competitor_mode=subdomains`.
- Ready decision `ahrefs_review_gap_records` exposes 10 competitor-page records
  through available contract `ahrefs_competitor_pages`.
- Blocked decision `ahrefs_block_gap_claims_without_records` listed missing
  contracts: `ahrefs_content_gap_records`, `ahrefs_backlink_gap_records`,
  `ahrefs_organic_keywords_by_url`, `ahrefs_top_pages_by_competitor`.
- Context-pack size: about `53100 bytes`; active action IDs: none.
- Eval artifact:
  `.local-lab/evals/codex-skill/20260621T013710Z/wilq-ahrefs-gap-finder/result.json`.
  Result: `api_used=true`, `blocked=true`, Ahrefs evidence IDs present,
  `operator_usefulness_score=4`.

Still blocked by design:

- Current Ahrefs can support review of competitor pages, top pages, organic
  keywords by URL, content gap candidates and backlink gap candidates. Do not
  claim traffic uplift or authority improvement until impact/change-window
  contracts exist.
- Next Ahrefs value work is to connect these records into GSC/WordPress/action
  review, not prompt-language polish or another fake gap unlock.

Final proof:

- `scripts/verify.sh` passed after this slice.
- Backend API contracts: `123 passed`.
- Dashboard route unit tests: `15 passed`.
- Playwright e2e: `12 passed`.
- Skill/API smokes and dashboard production build passed.
