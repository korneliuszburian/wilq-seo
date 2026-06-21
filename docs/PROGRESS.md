# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. To ma być krótki recovery ledger, nie pełny changelog.

Pełne archiwum sprzed kompaktowania:
`docs/progress/archive/2026-06-19-progress-ledger.md`.

## Maintenance Rule

- Trzymaj tutaj aktualny stan, ostatnie 3-5 slice'ów, aktywne luki i następny
  krok.
- Nie dopisuj kolejnych setek linii historii. Starsze wpisy przenoś do
  `docs/progress/archive/`.
- Git i dedykowane ledgery są źródłem długiej historii. Ten plik ma pomagać po
  utracie contextu.

## Current Snapshot

Data: 2026-06-21

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

Aktualny proof produktowy:

- Ads budget apply safety review, 2026-06-21 13:50 CEST.
  Budget preview nie jest już tylko `CampaignBudgetOperation` z tekstową
  blokadą. Każdy Ads budget apply preview ma typed
  `safety_review.safety_contract=campaign_budget_apply_safety_v1`,
  `status=blocked`, `max_allowed_delta_percent=0.3`, missing requirements,
  evidence IDs i twarde `apply_allowed=false`, `api_mutation_ready=false`,
  `destructive=false`. Ten sam safety review jest w
  `/api/ads/diagnostics`, `act_prepare_ads_campaign_review_queue`, scoped
  `wilq-ads-doctor` context-pack i `/ads-doctor`. Context-pack zachowuje
  kompaktowy safety review (`4` budget preview rows, około `184632` bytes) bez
  `[REDACTED]` w missing requirements. Nadal zablokowane: realny vendor budget
  apply, apply confirmation i mutation audit do Google Ads. Full
  `scripts/verify.sh` passed po tym slice: backend `144 passed`, dashboard
  unit `17 passed`, Playwright `14 passed`, skill smokes i dashboard build.
- GA4 tracking-quality payload preview, 2026-06-21 13:17 CEST.
  `act_review_ga4_tracking_quality` ma teraz typed review-only
  `ga4_tracking_quality_review_v1` payload preview. Preview grupuje
  landing/source/campaign facts, pokazuje braki wymiarów takich jak
  `(not set)`, metric snapshot, evidence IDs i required validation:
  `review_landing_page_dimension`, `review_source_medium_dimension`,
  `review_campaign_name_dimension`, `review_conversion_or_key_event_mapping`,
  `human_confirm_before_tracking_change`. Walidacja ActionObject zwraca
  `valid=true`. Scoped `wilq-ga4-analyst` context-pack zachowuje kompaktowy
  preview (`4` rows, około `57758` bytes), a `/ga4` renderuje panel
  `Podgląd review GA4`. Nadal zablokowane: conversion rate, ROAS, revenue,
  profitability, funnel diagnosis, attribution verdict, tracking fixed i GA4
  write.
- Ads custom segment targeting preview, 2026-06-21 12:46 CEST.
  `AdsCustomSegmentPayloadPreview` ma teraz typed `targeting_preview`, który
  wiąże kandydat segmentu z campaign context bez odblokowania mutacji.
  Live `/api/ads/diagnostics.custom_segments_read_contract.payload_preview[0]`
  i decision `ads_prepare_custom_segments_from_search_terms` pokazują
  `target_scope=campaign_context_review`,
  `operation_type=custom_segment_targeting_review`, kampanię
  `Kompendium PPWR`, required validation `keyword_planner_enrichment`,
  `forecast_or_audience_size`, `human_confirm_before_apply`,
  `mutation_audit_required`, oraz `apply_allowed=false`,
  `api_mutation_ready=false`, `destructive=false`. ActionObject
  `act_prepare_custom_segments_from_search_terms` waliduje się z tym samym
  targeting preview. Scoped `wilq-custom-segments` context-pack ma około
  `50087` bytes i zachowuje `custom_segment_preview_id`, więc Codex widzi
  trace preview -> targeting preview bez utraty redakcji sekretów. Nadal
  zablokowane: audience size, conversion uplift, ROAS, targeting applied,
  campaign performance.
- Localo visibility review ActionObject, 2026-06-21 12:22 CEST.
  Localo nie jest już tylko readiness/blocker card, gdy WILQ ma live aggregate
  facts. `/api/localo/diagnostics` pokazuje
  `action_ids=[act_review_localo_visibility_facts]`, decyzję
  `localo_review_visibility_facts` jako `ready` oraz jawny blocked item dla
  claimów bez kontraktów. ActionObject
  `act_review_localo_visibility_facts` ma connector `localo`, mode `prepare`,
  risk `low`, evidence `ev_refresh_refresh_localo_9e9ff67eadad`, payload
  `local_visibility_task`, `allowed_contracts=[place_inventory,
  local_rankings, reviews]`, `missing_read_contracts=[gbp_visibility,
  competitor_visibility, local_tasks]`, `apply_allowed=false` i
  `destructive=false`. Walidacja
  `/api/actions/act_review_localo_visibility_facts/validate` zwraca
  `valid=true`. Command Center decision
  `decision_review_localo_visibility_facts` pokazuje tę akcję, a scoped
  `wilq-localo-operator` context-pack ma
  `localo_diagnostics.action_ids=[act_review_localo_visibility_facts]`.
  Nadal zablokowane: `GBP performance`, `competitor visibility`, `GBP write`,
  `local visibility uplift`.
- Ads section ActionObject ownership, 2026-06-21 12:05 CEST.
  Keyword Planner access blocker nie rozlewa się już w Ads Doctor na ogólne
  sekcje. Live `/api/ads/diagnostics` po restarcie stacka: top-level
  `action_ids` nadal zawiera
  `act_configure_google_ads_keyword_planner_access`, ale
  `ads_live_data_status.action_ids=[]`,
  `ads_campaign_overview.action_ids=[act_prepare_ads_campaign_review_queue]`,
  `ads_search_terms.action_ids=[act_prepare_custom_segments_from_search_terms,
  act_prepare_negative_keyword_review_queue]`, a
  `ads_keyword_planner.action_ids=[act_configure_google_ads_keyword_planner_access]`.
  Command Center Ads decision nadal pokazuje tylko cztery właściwe kolejki Ads,
  bez Keyword Planner access repair. Scoped `wilq-ads-doctor` context-pack ma
  `190224` bytes po tej separacji.
- Google Ads Keyword Planner approval blocker, 2026-06-21 11:40 CEST.
  Keyword Planner 403/`DEVELOPER_TOKEN_NOT_APPROVED` nie jest już ukrytym
  tekstem w Ads diagnostics. WILQ wystawia review-only ActionObject
  `act_configure_google_ads_keyword_planner_access` z payloadem
  `configure_google_ads_keyword_planner_access`, evidence IDs, walidacją,
  `apply_allowed=false` i `destructive=false`. ActionObject jest dostępny w
  `/api/actions` i w `wilq-ads-doctor` context-packu, ale nie rozlewa się do
  ogólnego Command Center jako marketerowa akcja kampanii. To jest zewnętrzny
  access blocker Google Ads API, nie brak promptu ani brak `.env`. Focused
  proof: ruff/mypy/test dla Ads diagnostics, action payloadów, Command Center
  i context-packa passed; `wilq-ads-doctor` context-pack ma `199512` bytes,
  czyli mieści się poniżej limitu 200 KB. Full `scripts/verify.sh` passed:
  backend `144 passed`, dashboard unit `17 passed`, Playwright e2e
  `14 passed`, skill/API smokes and dashboard production build passed.
- Review-gated WordPress draft payload preview, 2026-06-21 11:07 CEST.
  Po zapisanym human review dla `candidate:content_brief_*`,
  `act_prepare_content_refresh_queue` wzbogaca payload o
  `wordpress_draft_payload_preview_v1`. Preview powstaje z wybranego
  `content_brief_preview_v1` i zawiera `post_status=draft`, kierunek tytułu/
  excerptu, bloki treści, evidence IDs, wymagane walidacje, blocked claims,
  `mutation_allowed=false`, `apply_allowed=false`, `api_mutation_ready=false`
  i `destructive=false`. Runtime proof na tymczasowym state DB: przed review
  brak `wordpress_draft_payload_preview`; po `human_review_approved_for_prepare`
  pojawia się 1 draft preview, a `/api/actions/act_prepare_content_refresh_queue/preview`
  zwraca je przy statusie `blocked`. Dashboard `/content-planner` renderuje
  `Payload draftu po review`. To nadal nie jest publikacja ani WordPress write
  adapter. Full `scripts/verify.sh` passed: backend `143 passed`, dashboard
  unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and dashboard
  production build passed.
- Ahrefs overlap evidence in Content Planner, 2026-06-21 10:44 CEST.
  `content_decision_ahrefs_gap_records_review.ahrefs_candidate_rows` ma teraz
  `gsc_overlap_terms` i `wordpress_overlap_urls`, więc marketer i Codex widzą
  dokładnie, które GSC query i które WordPress/sklep URL-e wspierają albo
  blokują kandydata Ahrefs. Naprawiono normalizację polskich znaków w scoringu
  (`zielony ład` trafia w `zielony lad`), a redaction allowlist zachowuje
  publiczne overlap URL-e w context-packu bez odsłaniania sekretów. Live
  TestClient proof: Ahrefs tiles `rekordy Ahrefs=32`, `pasujące=5`,
  `do review=10`, `off-topic=17`, `GSC overlap=0`, `WP overlap=6`; kandydat
  `beczka` ma `gsc_demand=missing` i cztery `wordpress_overlap_urls`, więc jest
  WP/feed review signal, nie GSC-backed content brief. Dashboard
  `/content-planner` renderuje `Overlap GSC` i `Overlap WP`. Full
  `scripts/verify.sh` passed: backend `143 passed`, dashboard unit `17 passed`,
  Playwright e2e `14 passed`, skill/API smokes and dashboard production build
  passed.
- Content brief preview + review persistence, 2026-06-21 10:16 CEST.
  `act_prepare_content_refresh_queue` ma teraz review-only
  `content_brief_preview_v1` w ActionObject payloadzie, a `/content-planner`
  pokazuje panel `Podgląd briefów do review`. Live proof po restarcie stacka:
  `/api/actions/act_prepare_content_refresh_queue` zwraca `preview_count=4`,
  tematy `beczka`, `denios`, `denios.pl`, `manutan.pl`, `contains_cuk=false`.
  `/api/actions/act_prepare_content_refresh_queue/preview` zwraca
  `status=blocked`, `preview_contract=content_brief_preview_v1`,
  `preview_items_total=4`, apply blockers dla prepare-only, walidacji,
  human confirm, impact sanity check i zablokowanych claimów. Preview jest
  ograniczony do review: GSC/WordPress/Ahrefs evidence, wymagane checki,
  blocked claims i brak WordPress publish/apply. Dashboard zapisuje teraz
  wybór konkretnego kandydata przez istniejący
  `/api/actions/{action_id}/review` jako human review audit; `candidate:*`,
  ActionObject ID i evidence IDs pozostają traceable, a token-like values dalej
  są redagowane. Focused proof: Ads scoped context-pack po tej zmianie ma
  `197559` bytes i 2 refresh summaries, więc nadal mieści się w limicie 200 KB.
  Full `scripts/verify.sh` passed after this slice: backend `143 passed`,
  dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and
  dashboard production build passed.
- Ahrefs relevance/off-topic scoring in Content Planner, 2026-06-21 06:07 CEST.
  `content_decision_ahrefs_gap_records_review` nie pokazuje już off-topic
  query jako przykładowych tematów contentowych. Live proof z
  `/api/content/diagnostics`: Ahrefs decision ma `pasujące=5`, `do review=10`,
  `off-topic=17`, `GSC overlap=0`, `WP overlap=6`; przykładowe query to
  `beczka, denios`, a nie `prawo jazdy` / `OC`. Scoring jest typed backend
  logicą opartą o domain terms, competitor domains, GSC/WP token overlap oraz
  broad/off-topic backlink checks. Nadal review-only: wynik nie jest briefem,
  ranking promise ani traffic uplift claimem.
- Ahrefs gap records in Content Planner, 2026-06-21 05:50 CEST.
  `/api/content/diagnostics.decision_queue` łączy teraz realne Ahrefs gap facts
  z kolejką contentową jako typed decision
  `content_decision_ahrefs_gap_records_review`. Live proof po restarcie API:
  `decision_count=5`, Ahrefs decision priority `18`, title
  `Ahrefs: zweryfikuj luki SEO przed briefem contentowym`, tiles:
  `rekordy Ahrefs=32`, `content gaps=4`, `organic keywords=4`,
  `top pages=4`, `backlink gaps=9`, source `ahrefs`, evidence count `2`,
  action `act_prepare_content_refresh_queue`. To jest review-only: WILQ każe
  odrzucić szerokie/off-topic rekordy Ahrefs i połączyć sensowne tematy z
  GSC/WordPress przed `refresh`, `merge`, `create` albo `block`. Narrow proof:
  ruff/mypy for content schemas, `pytest -k content_diagnostics`,
  dashboard unit tests and dashboard production build passed. Next product gap:
  jakościowe filtrowanie Ahrefs off-topic/broad records oraz scoring z GSC,
  WordPress inventory i business relevance.
- Ahrefs content/backlink gap candidates, 2026-06-21 05:05 CEST.
  `refresh_ahrefs_cb31460610d3` wykonał read-only Ahrefs `organic-keywords`
  dla targetu jako próbkę content gap oraz `refdomains` dla backlink gap.
  Rekord content gap powstaje tylko dla konkurencyjnej frazy, której nie ma w
  target organic keyword sample; rekord backlink gap tylko dla referring domain,
  której nie ma w target refdomains sample. Live facts: DR=40, Ahrefs
  Rank=1541946, `organic_competitor_rows=10`,
  `top_pages_by_competitor_rows=4`, `organic_keywords_by_url_rows=4`,
  `content_gap_read_status=completed`, `content_gap_rows=4`,
  `content_gap_target_keywords=100`, `backlink_gap_read_status=completed`,
  `backlink_gap_rows=9`. `/api/ahrefs/diagnostics` ma teraz
  `gap_read_contract.status=ready`, `missing_read_contracts=[]`,
  `gap_records=24`, `content_records=4`, `backlink_records=9` i wszystkie
  Ahrefs gap contracts available. Scoped `wilq-ahrefs-gap-finder` context-pack
  ma około `100234` bytes i `active_action_objects=0`. Non-interactive eval
  przeszedł:
  `.local-lab/evals/codex-skill/20260621T030447Z/wilq-ahrefs-gap-finder/result.json`;
  wynik ma `api_used=true`, `language=pl-PL`, `blocked=true`, brak ActionObject
  IDs i brak safety findings. Full `scripts/verify.sh` passed after this slice:
  backend `139 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
  skill/API smokes and dashboard production build passed.
- Ahrefs competitor page records, 2026-06-21 03:38 CEST.
  `refresh_ahrefs_a106dd4ab417` wykonał realny read-only Ahrefs API dla
  authority i organic competitors na prawdziwym targetcie `ekologus.pl`, nie
  stagingowym `ekologus.dev.proudsite.pl`. Target priority: `AHREFS_TARGET`,
  potem `MIS_PRIMARY_SITE_URL`, potem `WORDPRESS_EKOLOGUS_URL`. Live facts:
  DR=40, Ahrefs Rank=1541946, `organic_competitor_read_status=completed`,
  `organic_competitor_rows=10`, `organic_competitor_country=pl`,
  `organic_competitor_mode=subdomains`. `/api/ahrefs/diagnostics` ma teraz
  `gap_fact_count=10`, `gap_records=10`, available contract
  `ahrefs_competitor_pages`, ready decision `ahrefs_review_gap_records` i
  nadal blocked `ahrefs_block_gap_claims_without_records` dla
  `ahrefs_content_gap_records`, `ahrefs_backlink_gap_records`,
  `ahrefs_organic_keywords_by_url` oraz `ahrefs_top_pages_by_competitor`.
  Scoped `wilq-ahrefs-gap-finder` context-pack ma około `53100` bytes,
  `active_action_objects=0` i przenosi te rekordy do Codex bez write path.
  Non-interactive eval przeszedł:
  `.local-lab/evals/codex-skill/20260621T013710Z/wilq-ahrefs-gap-finder/result.json`.
  Full `scripts/verify.sh` passed after this slice: backend `139 passed`,
  dashboard unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes
  and dashboard production build passed.
- Ads custom segment source-quality truth, 2026-06-21 06:27 CEST.
  Custom segment review now exposes typed `source_quality`, so marketer and
  Codex can see why source terms are only a review queue. Current live proof
  after `scripts/local_stack.sh restart`: `/api/ads/diagnostics`
  `ads_custom_segment_23848569273` has `accepted_terms=6`,
  `rejected_terms=44`, `total_terms=50`, `missing_metric_terms=6` and
  rejection reason count
  `termin nie ma aktywności w dostępnych metrykach=44`. The same object is
  present in decision `ads_prepare_custom_segments_from_search_terms`.
  Missing search-term impressions/cost still render as `brak danych`, not fake
  zeroes. Operator gates remain `keyword_planner_enrichment`,
  `forecast_or_audience_size` and human confirmation, so this is still
  prepare/review-only: no forecast, audience-size, targeting, CPA/ROAS or apply
  claim is allowed. Full `scripts/verify.sh` passed after this slice: backend
  `140 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
  skill/API smokes and dashboard production build passed.
- Ads change-history empty-read truth, 2026-06-21 06:48 CEST.
  Read-attempted-but-empty Google Ads change history no longer becomes a ready
  review task. Current live `/api/ads/diagnostics` has
  `change_history_read_contract.status=blocked`, title
  `Google Ads: brak zmian do review`, `change_history_rows=[]` and missing
  contracts `change_event_rows`, `pre_change_performance_window`,
  `post_change_performance_window`, `human_change_impact_review`,
  `apply_preview`. Decision `ads_review_change_history` is also blocked with
  tiles `zmiany=0`, `kampanie=0`. This keeps WILQ from showing an empty ready
  card or claiming change impact/performance uplift/budget apply without
  concrete change_event rows and pre/post performance windows. Full
  `scripts/verify.sh` passed after this slice: backend `141 passed`, dashboard
  unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and dashboard
  production build passed.
- Ads Doctor strict non-interactive eval, 2026-06-21 07:07 CEST.
  `wilq-ads-doctor` now passes the stricter live Ads eval after the empty
  change-history fix. The first rerun failed because the smoke script still
  expected stale `missing_read_contracts=["change_history"]`; the live API and
  context-pack already exposed the correct state: `status=blocked`,
  `change_history_rows=[]`, missing `change_event_rows` plus pre/post review
  contracts. The smoke script was updated to accept the read-attempted-but-empty
  state, and the eval harness now treats structural blocked state
  (`blocked_reason` or blocked action candidate) as satisfying the `blocked
  claims` marker without forcing English text into Polish operator output.
  Passing artifact:
  `.local-lab/evals/codex-skill/20260621T050542Z/wilq-ads-doctor/result.json`.
  Result summary: `api_used=true`, `language=pl-PL`, source `google_ads`,
  evidence IDs from the live Ads refresh, top-level budget knowledge/rules,
  four Ads ActionObject IDs and `operator_usefulness_score=5`. Full
  `scripts/verify.sh` passed after this fix: backend `141 passed`, dashboard
  unit `17 passed`, Playwright e2e `14 passed`, skill/API smokes and dashboard
  production build passed.
- Demand Gen typed blocker title/tiles, 2026-06-21 08:22 CEST.
  `/api/demand-gen/diagnostics` and the scoped
  `wilq-demand-gen-operator` context-pack now expose a marketer-facing title
  and metric tiles instead of forcing the dashboard to assemble the decision
  locally. Current live title: `Demand Gen: brak kampanii do rekomendacji`.
  Current tiles: `kampanie Ads=18`, `kanały=2`, `wiersze DG=0`, `braki=5`.
  The skill smoke asserts these fields, and the non-interactive eval passed:
  `.local-lab/evals/codex-skill/20260621T062101Z/wilq-demand-gen-operator/result.json`.
  The eval result has `blocked=true`, `api_used=true`, `language=pl-PL`,
  source connectors `google_ads` and `google_analytics_4`, evidence count `14`
  and no non-null Demand Gen ActionObject IDs. The eval case was corrected to
  stop requiring `google_merchant_center` and to forbid adjacent GA4/Ads action
  IDs for this workflow. Full `scripts/verify.sh` passed after this slice:
  backend `141 passed`, dashboard unit `17 passed`, Playwright e2e
  `14 passed`, skill/API smokes and dashboard production build passed.
- Ahrefs candidate rows in Content Planner, 2026-06-21 09:05 CEST.
  `content_decision_ahrefs_gap_records_review` now exposes typed
  `ahrefs_candidate_rows` instead of only aggregate counts and sample queries.
  Candidate rows include `topic`, `gap_type`, `relevance_status`,
  `relevance_score`, `business_relevance_reasons`, `gsc_demand`,
  `wordpress_inventory_match`, source URLs/competitor hints, evidence IDs and a
  safe next step. Live `/api/content/diagnostics` currently returns 6 Ahrefs
  candidates; first examples are `beczka`, `denios`, `denios.pl`. The dashboard
  Content Planner renders the top rows under `Kandydaci Ahrefs do review`,
  making the Ahrefs card a review queue rather than a loose metric block.
  Focused proof passed: ruff/mypy for changed backend, content diagnostics API
  test, dashboard typecheck/lint/unit tests and API-backed Playwright
  `dashboard-api.spec.ts` (`13 passed`). Full `scripts/verify.sh` passed after
  this slice: backend `141 passed`, dashboard unit `17 passed`, Playwright e2e
  `14 passed`, skill/API smokes and dashboard production build passed.
- Ahrefs typed gap read contract, 2026-06-21 01:21 CEST, superseded by the
  03:38 target fix above. The important surviving contract is still valid:
  `/api/ahrefs/diagnostics` exposes `gap_read_contract` as typed API state and
  blocks unsupported content/backlink/ranking/traffic/authority claims. The
  stale zero-row proof from `refresh_ahrefs_21a12047ec6a` is historical only;
  use `refresh_ahrefs_a106dd4ab417` as current proof.
- Ads business policy gates, 2026-06-21 01:01 CEST.
  `AdsBusinessContextReadContract` now exposes typed `business_policy_ids` and
  `operator_review_gates` so profit margin/business goal/budget goal become
  review policy, not just "configured fields". Current live policy IDs:
  `use_margin_as_context_not_profitability_verdict`,
  `align_campaign_review_to_business_goal`,
  `honor_human_budget_goal_before_budget_changes`,
  `block_target_verdict_until_roas_or_cpa_confirmed`. Current review gates:
  `human_strategy_review`, `review_profit_margin_model`,
  `review_business_goal`, `review_human_budget_goal`,
  `confirm_target_roas_or_cpa`. Business-context decision now shows
  `review gates=5` and `polityki=4`. Redaction allowlist preserves
  `business_policy_ids`; scoped `wilq-ads-doctor` context-pack proof after
  restart: `189432` bytes with unredacted policy IDs and review gates. Narrow
  checks passed: ruff/mypy, three API contract tests, shared schema build,
  dashboard lint/typecheck and `App.test.tsx`. Still blocked: profitability,
  margin verdict, budget scaling/apply, recommendation apply and wasted budget.
- Ads n-gram decision usefulness, 2026-06-21 00:45 CEST.
  `ads_review_search_term_ngrams` no longer falls back to empty metric tiles
  and priority `90` after decision lineage normalization. It is now priority
  `42`, directly after raw search-term review, and exposes honest overlapping
  n-gram tiles: total n-grams, displayed rows, rows with clicks,
  max source queries per topic and top clicks per topic; cost is only shown
  when present. Live proof after `scripts/local_stack.sh restart`:
  `/api/ads/diagnostics` returned `metric_tiles={"n-gramy":30,"pokazane":8,
  "z kliknięciami":8,"max query/temat":12,"top kliknięcia":2}` and kept
  blocked claims for `search-term waste`, `negative keyword apply`, CPA, ROAS
  and conversion loss. Scoped `wilq-ads-doctor` context-pack stayed under
  200 KB at `188899` bytes and carries the same decision tiles without heavy
  n-gram rows. Narrow checks passed: ruff/mypy, Ads API contract test,
  dashboard lint/typecheck and `App.test.tsx`.
- Ads target-aware campaign review, 2026-06-21 00:31 CEST.
  Campaign rows, derived KPI rows, Ads campaign review ActionObject and scoped
  `wilq-ads-doctor` context-pack now carry target-aware state:
  `target_status`, `target_status_label` and ActionObject `target_context`.
  Current live truth remains honest: repo-local business context is ready, but
  no human-confirmed target ROAS/CPA is set, so live API returns
  `missing_read_contracts=["target_roas_or_cpa"]`, top campaign
  `(2026) Ekologus Ogólna` has `target_status=no_target` /
  `target_status_label=brak targetu`, and the campaign decision does not show a
  noisy `targety=0` metric tile. Campaign decision `operator_review_gates` now
  carries the union of row gates instead of an empty list. Process-env proof
  with `WILQ_ADS_TARGET_ROAS=5.0` marks the same top campaign
  `outside_target` / `ROAS poniżej targetu`, adds
  `review_target_context` and `review_target_gap_before_budget_decision`, and
  shows `targety=18`. Scoped context-pack proof: `189752` bytes and first Ads
  campaign candidate includes `target_context`. Narrow checks passed:
  ruff/mypy, two Ads API contract tests, shared schema build, dashboard
  lint/typecheck and `App.test.tsx`. This still does not unlock budget apply,
  pause, wasted-budget claims, CPA/ROAS verdicts or profitability claims.
- Ads campaign review ActionObject/context alignment, 2026-06-21 00:13 CEST.
  `/api/ads/diagnostics` i
  `/api/actions/act_prepare_ads_campaign_review_queue` używają teraz tego
  samego campaign triage: `review_priority`, `review_score`, polski
  `review_reason` i `human_review_gates`. Scoped
  `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` nie wycina już
  całego `campaign_candidates`; zachowuje kompaktowe top 3 z 8 kandydatów,
  `metrics_total=12`, `apply_allowed=false` i `budget_payload_preview_included=0`.
  Live proof po `scripts/local_stack.sh restart`: top candidate
  `(2026) Ekologus Ogólna` ma `review_priority=pilne`, `review_score=90`,
  `clicks=94`, `impressions=2763`, `cost_micros=61051723`,
  `conversions=0.0`, gates
  `review_campaign_goal`, `review_conversion_quality`,
  `review_budget_context`, `review_search_terms_before_budget_decision`,
  `human_strategy_review`, `review_conversion_tracking`,
  `review_pmax_asset_feed_context`. Context-pack ma `187638` bytes, czyli
  dalej mieści się pod limitem 200 KB. Redakcja preserve'uje
  `human_review_gates`, bo to identyfikatory kontroli, nie sekrety. Validate
  action zwraca `valid=true`. To nadal jest review-only: bez budget apply,
  pause, `wasted budget`, CPA/ROAS verdict ani profitability claimów. Full
  `scripts/verify.sh` przeszedł: backend `136 passed`, dashboard unit
  `17 passed`, Playwright e2e `14 passed`, API/skill smokes i produkcyjny
  build dashboardu OK.
- Ads search-term n-gram read contract, 2026-06-20 23:12 CEST.
  WILQ ma teraz typed `search_term_ngram_read_contract` w
  `/api/ads/diagnostics`, shared Zod schema, decyzję
  `ads_review_search_term_ngrams` i dashboardową tabelę n-gramów w Ads Doctor.
  Kontrakt grupuje istniejące Google Ads `search_term_rows` w 1/2/3-gramy,
  pokazuje liczbę źródłowych zapytań, przykłady, kliknięcia, koszt,
  konwersje, evidence IDs i blocked claims. To jest read-only review surface:
  blokuje `search-term waste`, `negative keyword apply`, CPA, ROAS i conversion
  loss. Nie tworzy negative keyword apply ani nie odblokowuje automatycznego
  działania. Live proof po `scripts/local_stack.sh restart`:
  `/api/ads/diagnostics.search_term_ngram_read_contract.status=ready`,
  `ngram_rows=30`, top n-gram `bdo` z 12 źródłowych search terms,
  sekcja `ads_search_term_ngrams` ma knowledge cards
  `card_google_ads_search_playbook`, `card_google_ads_negative_keywords_playbook`
  i expert rules `ads_search_terms_v1`, `ads_negative_keywords_v1`. Wąskie
  checks przeszły: ruff/mypy dla Ads diagnostics i schematów,
  `pytest -k ads_diagnostics`, shared schema build, dashboard lint/typecheck i
  `App.test.tsx`. Full `scripts/verify.sh` przeszedł po końcowej kompaktacji
  context-packa: backend `136 passed`, dashboard unit `17 passed`, Playwright
  e2e `14 passed`, API/skill smokes i produkcyjny build dashboardu OK. Ads
  doctor context-pack zostaje pod limitem 200 KB, a pełne dane zostają w
  `/api/ads/diagnostics`.
- Command Center DailyDecision usefulness, 2026-06-20 22:40 CEST.
  `DailyDecision.co_widzimy` nie pokazuje już technicznego debug tekstu
  `Źródła=`, `dowody=` ani `akcje=`. Te identyfikatory zostają w typed fields i
  trace lines, a główne zdanie decyzji mówi po polsku, co marketer realnie ma
  przejrzeć: Merchant issue review, GSC/WordPress content queue, GA4 blocker
  pomiaru, Ads read-only review queues i Localo agregaty. Live proof po
  `scripts/local_stack.sh restart`: `/api/dashboard/command-center` zwrócił
  `false` dla obecności `Źródła=`/`dowody=`/`akcje=` w `co_widzimy`, a GA4 nie
  dubluje już zdania `Status blocked oznacza...`. Wąskie checks przeszły:
  ruff/mypy dla `command_center.py`, `pytest -k command_center`, dashboard
  lint/typecheck i `App.test.tsx`. Full `scripts/verify.sh` przeszedł:
  backend `136 passed`, dashboard unit `17 passed`, Playwright e2e
  `14 passed`, API/skill smokes i produkcyjny build dashboardu OK.
- ActionObject mutation audit visibility, 2026-06-20 22:24 CEST.
  `ActionObject.review_gate` niesie teraz najnowszy mutation audit:
  `last_mutation_audit_id/status/actor/at/summary`,
  `last_mutation_attempted`, `last_mutation_adapter`,
  `last_mutation_audit_event_id` i `last_mutation_blockers`. Ten sam stan
  renderuje dashboard i trafia do daily context-packu. Runtime proof na
  tymczasowej bazie: blocked apply na `act_review_merchant_feed_issues`
  zwrócił `mutation_status=blocked`, `mutation_attempted=false`; follow-up
  `/api/actions/{action_id}` i `POST /api/codex/context-pack
  {"skill":"wilq-daily-command"}` oba miały
  `review_gate.last_mutation_audit_status=blocked` i
  `last_mutation_attempted=false`. `scripts/verify.sh` przeszedł dla tej
  poprawki, w tym API/skill smokes, Playwright e2e i produkcyjny build
  dashboardu.
- ActionObject mutation audit boundary, 2026-06-20 21:58 CEST.
  WILQ ma teraz typed `ActionMutationAuditRecord`, lokalną tabelę
  `action_mutation_audits`, endpointy `GET /api/action-mutation-audits` i
  `GET /api/actions/{action_id}/mutation-audits`, a `ActionApplyResult`
  zawiera `mutation_audit`. `/api/actions/{action_id}/apply` zapisuje mutation
  audit przy każdym wyniku, także 409. `apply_action` wymaga teraz wcześniejszego
  dry-run preview, zapisanego confirmation, completed impact sanity check,
  valid ActionObject, skonfigurowanego connectora, bezpiecznego ryzyka/payloadu
  i realnego vendor mutation adaptera. Ponieważ Goal 001 nie ma jeszcze
  zaimplementowanego adaptera mutującego, nawet syntetyczne apply-ready
  ActionObject kończy jako `applied=false`, `status=blocked`,
  `mutation_attempted=false`, `mutation_adapter=null`, z blockerem
  `Vendor mutation adapter is not implemented for this ActionObject.` Redaction
  preserve'uje `audit_event_id`, żeby nie gubić traceability. Full
  `scripts/verify.sh` po slice przeszedł: backend `136 passed`, dashboard unit
  `17 passed`, Playwright e2e `14 passed`, dashboard build OK.
- ActionObject impact sanity gate, 2026-06-20 21:28 CEST.
  WILQ ma teraz `POST /api/actions/{action_id}/impact-check`, typed
  `ActionImpactCheckRequest/ActionImpactCheckResult`, lokalne audit eventy
  `action_impact_check_blocked` i `action_impact_check_completed` oraz
  dashboardowy panel `Impact sanity check`. Impact check wymaga wcześniejszego
  confirmation, metric facts i evidence IDs. Bez confirmation zwraca blocker
  `action_confirmation_required`; po `preview -> confirm` zapisuje
  `action_impact_check_completed`, propaguje
  `last_impact_check_status/by/at/summary` przez `ActionObject.review_gate` i
  usuwa tylko blocker `impact_sanity_check_required`. Runtime proof na
  tymczasowej bazie: impact-before-confirm -> `action_impact_check_blocked`,
  preview -> `action_preview_generated`, confirm -> `action_apply_confirmed`,
  impact-after-confirm -> `action_impact_check_completed`, context-pack ma
  `latest_audit_event=action_impact_check_completed`,
  `last_impact_check_status=checked`, `apply_allowed=false`. To domyka lokalny
  etap impact sanity bez vendor mutation; nadal nie odblokowuje realnego
  `apply` ani mutation audit. Pełne `scripts/verify.sh` po slice: backend
  `135 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
  dashboard build OK.
- ActionObject confirmation gate, 2026-06-20 21:03 CEST.
  WILQ ma teraz osobny `POST /api/actions/{action_id}/confirm`, typed
  `ActionConfirmRequest/ActionConfirmResult`, lokalne audit eventy
  `action_confirmation_blocked` i `action_apply_confirmed` oraz dashboardowy
  panel `Jawne potwierdzenie preview`. Confirm wymaga wcześniejszego dry-run
  preview i `preview_acknowledged=true`; bez preview zwraca blocker
  `dry_run_preview_required`. Confirm po preview zapisuje potwierdzenie i
  propaguje `last_confirmation_by/at/summary` przez `ActionObject.review_gate`
  oraz Codex context-pack. Runtime proof na tymczasowej bazie:
  confirm-before-preview -> `action_confirmation_blocked`,
  preview -> `action_preview_generated`, confirm-after-preview ->
  `action_apply_confirmed`, context-pack ma
  `latest_audit_event=action_apply_confirmed`,
  `last_confirmation_by=operator_runtime_proof`, `apply_allowed=false`. To
  domyka lokalny etap `preview -> confirm` bez vendor mutation; nadal nie
  odblokowuje realnego `apply`. Pełne `scripts/verify.sh` po slice: backend
  `133 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
  dashboard build OK.
- ActionObject dry-run preview contract, 2026-06-20 20:44 CEST.
  WILQ ma teraz `POST /api/actions/{action_id}/preview`, typed
  `ActionPreviewRequest/ActionPreviewResult`, lokalny audit event
  `action_preview_generated` i dashboardowy panel `Dry-run preview`.
  Preview używa istniejących payload preview rows z ActionObjecta, zwraca
  `dry_run=true`, `mutation_allowed=false`, `preview_items_total`,
  `omitted_items`, `blockers` i `review_gate`. Runtime proof na tymczasowej
  bazie: endpoint zwrócił `200`, `event_type=action_preview_generated`,
  ActionObject i daily context-pack mają `latest_audit_event=action_preview_generated`,
  `apply_allowed=false`. To domyka standardowy etap `dry_run -> preview` bez
  mutacji vendorów; nadal nie odblokowuje `confirm -> apply`. Pełne
  `scripts/verify.sh` po slice: backend `131 passed`, dashboard unit
  `17 passed`, Playwright e2e `14 passed`, dashboard build OK.
- Human review outcome contract, 2026-06-20 20:28 CEST.
  WILQ ma teraz `POST /api/actions/{action_id}/review`, typed
  `ActionReviewRequest/ActionReviewResult`, lokalny audit event
  `human_review_<outcome>` i propagację `last_review_outcome`,
  `last_reviewed_by`, `last_reviewed_at`, `last_review_summary` przez
  `ActionObject.review_gate`. Dashboard pokazuje panel `Wynik review człowieka`
  i zapisuje review bez apply. Runtime proof na tymczasowej bazie:
  `event_type=human_review_needs_changes`, ActionObject i daily context-pack
  mają `last_review_outcome=needs_changes`, `apply_allowed=false`, bez
  `[REDACTED]`. To zamyka widoczny zapis wyniku review; nadal nie odblokowuje
  apply, budżetów, negative keywords ani mutacji vendorów. Pełne
  `scripts/verify.sh` po slice: backend `129 passed`, dashboard unit
  `17 passed`, Playwright e2e `14 passed`, dashboard build OK.
- ActionObject review gate contract, 2026-06-20 20:04 CEST.
  `ActionObject` ma teraz typed `review_gate` z `status`,
  `required_checks`, `operator_checklist`, `apply_blockers`,
  `confirmation_required` i `apply_allowed`. Ten sam stan idzie przez
  `/api/actions`, dashboard i `POST /api/codex/context-pack
  {"skill":"wilq-daily-command"}`. Live proof po
  `scripts/local_stack.sh restart`: aktywne akcje
  `act_review_merchant_feed_issues`, `act_prepare_content_refresh_queue`,
  `act_prepare_ads_campaign_review_queue`,
  `act_prepare_google_ads_recommendation_review_queue`,
  `act_prepare_custom_segments_from_search_terms` i
  `act_prepare_negative_keyword_review_queue` mają
  `review_gate.status=pending_validation`, `apply_allowed=false`,
  `confirmation_required=true` i jawne blokady apply bez `[REDACTED]`.
  Scoped skill context-pack kompaktuje `active_action_objects.metrics` do jednej
  przykładowej metryki z `metrics_total`, żeby utrzymać `wilq-ads-doctor`
  poniżej budżetu 200 KB. To domyka widoczność warunków review, ale nie
  odblokowuje żadnego write/apply. Pełne `scripts/verify.sh` po slice:
  backend `127 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
  dashboard build OK.
- Ads Keyword Planner enrichment contract, 2026-06-20 19:30 CEST.
  WILQ ma read-only adapter dla Google Ads Keyword Planner
  `generateKeywordIdeas`, typed `keyword_planner_read_contract`, shared Zod
  schema, dashboard enrichment dla custom segments i smoke skilla, który
  rozróżnia `ready` od legalnego `blocked`. Live vendor_read
  `refresh_google_ads_0477a745f098` zakończył się `status=completed`; kampanie,
  search terms, 90-day safety, keyword match context, recommendations,
  impression share i change history zostały zebrane, ale Keyword Planner
  zwrócił `403 PERMISSION_DENIED` z
  `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`. To jest zewnętrzny
  readiness blocker developer tokena, nie brak `.env` ani błąd OAuth. Aktualne
  `/api/ads/diagnostics.keyword_planner_read_contract.status=blocked`,
  `missing_read_contracts=[keyword_planner_enrichment]`, a
  `custom_segments_read_contract.missing_read_contracts=[
  keyword_planner_enrichment, forecast_or_audience_size]`. Non-interactive
  `wilq-ads-doctor` eval przeszedł:
  `.local-lab/evals/codex-skill/20260620T173651Z/wilq-ads-doctor/result.json`.
- Ads recommendation review triage, 2026-06-20 18:48 CEST.
  Recommendation rows mają teraz typed `review_priority`, `review_score`,
  polski `review_reason` i `human_review_gates`, tak jak negative keywords i
  custom segments. Live proof po `scripts/local_stack.sh restart`:
  `/api/ads/diagnostics.recommendations_read_contract` ma `status=ready`,
  4 rows, `missing_read_contracts=[]`, action
  `act_prepare_google_ads_recommendation_review_queue`; decyzja
  `ads_review_recommendations.metric_tiles` pokazuje `rekomendacje=4`,
  `pilne=0`, `wysokie=2`, `podgląd wpływu=2`, `podgląd akcji=4`. Rowki:
  `DISPLAY_EXPANSION_OPT_IN=normalne/23`,
  `DYNAMIC_IMAGE_EXTENSION_OPT_IN=niski sygnał/10`,
  `IMPROVE_PERFORMANCE_MAX_AD_STRENGTH=wysokie/57`,
  `SEARCH_PARTNERS_OPT_IN=wysokie/53`. Smoke `wilq-ads-doctor` przeszedł i
  scoped Ads context-pack ma ~198 KB. `codex exec` eval przeszedł:
  `.local-lab/evals/codex-skill/20260620T164726Z/wilq-ads-doctor/result.json`,
  `api_used=true`, `language=pl-PL`, `operator_usefulness_score=5`, marker
  terms obejmują `review_priority`, `review_score`, `review_reason`,
  `kolejność review rekomendacji`.
- Ads preliminary business context + custom-segments scoped context, 2026-06-20
  17:34 CEST. Puste `WILQ_ADS_TARGET_ROAS` i
  `WILQ_ADS_TARGET_CPA_MICROS` nie robią już fałszywego blockera, jeśli core
  nie-sekretny context Ads jest ustawiony. Live
  `/api/ads/diagnostics.business_context_read_contract` ma `status=ready`,
  `missing_read_contracts=["target_roas_or_cpa"]`,
  `allowed_metrics=["profit_margin","business_goal","human_budget_goal"]`,
  `target_roas=null`, `target_cpa_micros=null`; decyzja
  `ads_review_business_context` ma `action_ids=[]`, więc Command Center nie
  pokazuje `daily_ads_business_context`. Jednocześnie
  `wilq-custom-segments` context-pack jest scoped: ~50 KB,
  `active_action_ids=["act_prepare_custom_segments_from_search_terms"]`,
  `decision_ids=["ads_prepare_custom_segments_from_search_terms"]`,
  `top_opportunity_count=0`, `purpose=custom_segments_context`. Dodano
  dedicated route `/ads-doctor/custom-segments` z Playwright smoke.
- Ads custom segment review triage, 2026-06-20 18:24 CEST.
  Custom segment candidates mają teraz typed `review_priority`, `review_score`,
  polski `review_reason` i `human_review_gates`, tak jak negative keyword
  review. Live proof po `scripts/local_stack.sh restart`:
  `/api/ads/diagnostics.custom_segments_read_contract` ma `status=ready`,
  1 kandydata `Search terms: Kompendium PPWR`, `review_priority=pilne`,
  `review_score=75`, 6 source terms, `missing_read_contracts=[
  keyword_planner_enrichment, forecast_or_audience_size]`. Decyzja
  `ads_prepare_custom_segments_from_search_terms.metric_tiles` pokazuje
  `segmenty=1`, `pilne=1`, `wysokie=0`, `podgląd akcji=1`,
  `źródłowe zapytania=6`. Scoped `wilq-custom-segments` context-pack ma
  ~51 KB, tylko `act_prepare_custom_segments_from_search_terms`, te same
  review fields i `top_opportunity_count=0`. `codex exec` eval przeszedł:
  `.local-lab/evals/codex-skill/20260620T162316Z/wilq-custom-segments/result.json`,
  `operator_usefulness_score=5`, `api_used=true`, `language=pl-PL`. Full
  `scripts/verify.sh` passed after this slice: backend `126 passed`,
  dashboard unit `17 passed`, Playwright e2e `14 passed`, dashboard
  production build OK.
- Ads negative keyword review triage, 2026-06-20 18:03 CEST.
  Negative keyword candidates nie są już tylko listą search terms do review.
  `/api/ads/diagnostics.negative_keywords_read_contract.candidates` niesie
  `review_priority`, `review_score`, polski `review_reason` i
  `human_review_gates`. Live proof po `scripts/local_stack.sh restart`:
  6 kandydatów, w tym `pilne=1`, `wysokie=1`; top candidate
  `asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a`
  ma `review_priority=pilne`, `review_score=84`. Decyzja
  `ads_review_negative_keyword_safety.metric_tiles` pokazuje teraz
  `kandydaci=6`, `pilne=1`, `wysokie=1`, `podgląd akcji=6`,
  `kontekst słów=12`. To nadal jest kolejność review, nie werdykt
  zmarnowanego budżetu i nie negative keyword apply. Full `scripts/verify.sh`
  passed after this slice: backend `126 passed`, dashboard unit `17 passed`,
  Playwright e2e `14 passed`, dashboard production build OK.
- Demand Gen diagnostics route, 2026-06-20 16:55 CEST.
  Demand Gen nie wpada już w generyczny registry surface. Dodano
  `GET /api/demand-gen/diagnostics`, a `/ads-doctor/demand-gen` renderuje ten
  sam readiness contract co `wilq-demand-gen-operator` context-pack:
  `status=blocked`, `campaign_rows_evaluated=18`,
  `campaign_channel_counts={PERFORMANCE_MAX: 8, SEARCH: 10}`,
  `demand_gen_campaign_rows=[]`, `action_ids=[]`. `demand_gen_campaign_rows`
  jest available, a brakujące kontrakty to asset groups, creative assets,
  landing quality per campaign, migration constraints i Demand Gen ActionObject.
  Route pokazuje to marketerowi jako blocker kontraktów, nie jako gotową
  rekomendację launch/migration.
- Localo metric fact evidence selection, 2026-06-20 16:35 CEST.
  Naprawiono regresję, w której późniejsze probe'y Localo `401` wypełniały
  limit `list_metric_facts` i Command Center pokazywało `frazy=0` mimo
  udanego aggregate read. `/api/localo/diagnostics` i Command Center czytają
  teraz facts po evidence ID ostatniego udanego Localo MCP read. Live proof po
  `scripts/local_stack.sh restart`: `/api/localo/diagnostics` ma
  `visibility_fact_count=17`, `latest_refresh=refresh_localo_9e9ff67eadad`,
  `metric_tiles.frazy=23`, `miejsca=4`, `średnia widoczność=52.8261`,
  `recenzje=793`; Command Center `decision_review_localo_visibility_facts`
  ma `frazy=23` i `daily_localo_readiness` nie wraca jako ready karta.
- Ads custom segment review gates, 2026-06-20 16:15 CEST.
  Custom segments rozdzielają teraz prawdziwe braki danych od gate'ów
  operatora. Live proof po `scripts/local_stack.sh restart`:
  `/api/ads/diagnostics.custom_segments_read_contract.status=ready`,
  `missing_read_contracts=["keyword_planner_enrichment",
  "forecast_or_audience_size"]` oraz
  `operator_review_gates=["review_source_terms",
  "reject_brand_or_low_intent_terms", "human_confirm_before_apply"]`.
  Decyzja `ads_prepare_custom_segments_from_search_terms` ma te same pola,
  `metric_tiles.segmenty=1`, `metric_tiles.źródłowe zapytania=6` i
  `action_ids=["act_prepare_custom_segments_from_search_terms"]`. To nadal
  nie jest targeting/apply support ani audience-size proof.
- Daily context-pack/action summary cleanup, 2026-06-20 14:30 CEST.
  `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` używa teraz
  `CommandCenterResponse.daily_decisions` jako źródła streszczeń
  `active_action_objects`, zamiast wracać do starych action summaries. Live
  proof po `scripts/local_stack.sh restart`: stale string check zwraca `[]`
  dla `active_products=12`, `disapproved_products=3`, `active_users=20`,
  `sessions=30`, `Connector .* ready`, `No performance metrics` i
  `Run a read-only refresh`. `act_review_merchant_feed_issues` ma
  `decision_id=decision_review_merchant_feed_issues` oraz tiles
  `produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`; GA4 ma
  `decision_id=decision_review_ga4_landing_quality` i status `blocked` z
  tiles `grupy ruchu=10`, `pomiar=2`, `jakość ruchu=4`. Redaction allowlist
  zachowuje `decision_id`.
- Localo Command Center routing, 2026-06-20 14:30 CEST. Realne Localo
  aggregate facts nie używają już readiness-only ID. Command Center pokazuje
  `daily_localo_visibility_facts` z tiles `miejsca=4`, `frazy=23`,
  `widoczność=52.8261`, `recenzje=793`, a `daily_localo_readiness` zostaje
  wyłącznie access/blocker statusem i nie może być główną kartą ready. Smoke
  `wilq-daily-command/scripts/smoke_context_pack.py` przeszedł po tej zmianie.
  Full `scripts/verify.sh` passed after this slice: backend `124 passed`,
  dashboard unit `15 passed`, Playwright e2e `12 passed`, dashboard production
  build OK.
- Content decision queue ma teraz typed metadata zamiast frontendowego
  zgadywania. Live proof po `scripts/local_stack.sh restart`:
  `/api/content/diagnostics.decision_queue` ma 4 decyzje, `null_status=[]`,
  `null_priority=[]`, `empty_tiles=[]`; każda decyzja ma `status`, `priority`
  i `metric_tiles`. Top decyzja to `SEO: odśwież lub scal "zielony ład co to"
  (7 zapytań)` z `wyświetlenia=2902`, `kliknięcia=123`, `CTR=4.24%`,
  `pozycja=1.5`, `WP=znaleziono`. Scoped `wilq-content-strategist`
  context-pack niesie te same pola, a Command Center `daily_content_queue`
  pokazuje `query/page=10`, `WP match=10`, `decyzje=4`,
  `wyświetlenia=7852`, `kliknięcia=138`. Dashboard renderuje API
  `metric_tiles` i `status`, bez duplikowania starych content metric chips.
  Full `scripts/verify.sh` passed after this slice: backend `123 passed`,
  dashboard unit `15 passed`, Playwright e2e `12 passed`, dashboard build OK.
- Ahrefs ma dedicated diagnostics, route i scoped context-pack. Current proof:
  `/api/ahrefs/diagnostics` has `live_data_available=true`, authority facts
  `DR=40`, `Ahrefs Rank=1541946`, `gap_read_contract.status=ready`,
  `missing_read_contracts=[]`, `gap_records=24`, ready decision
  `ahrefs_review_gap_records` with competitor pages, top pages, organic
  keywords by URL, content gap records and backlink gap records. The only
  remaining blocked claims are impact claims: traffic uplift and authority
  improvement. `wilq-ahrefs-gap-finder` context-pack has about `100234 bytes`,
  `active_action_objects=0`, contains `ahrefs_diagnostics` and
  omits broad unrelated context. Strict non-interactive eval passed:
  `.local-lab/evals/codex-skill/20260621T030447Z/wilq-ahrefs-gap-finder/result.json`.
  Result has `blocked=true`, `api_used=true`, `language=pl-PL`, Ahrefs evidence
  IDs and no unsafe action IDs.
- Command Center ma teraz 30-sekundowy operator snapshot cache po stronie WILQ
  API i dashboardu. Live proof po `scripts/local_stack.sh restart`:
  `/api/dashboard/command-center` `27856 bytes`, cold `1.777s`, potem
  `0.007s`, `0.009s`, `0.010s`, `0.007s` w oknie cache; daily Codex
  context-pack `126449 bytes`, `0.382s`, potem `0.237s`, `0.234s`.
- Najnowszy live Ads proof: `refresh_google_ads_60956db2c42f` /
  `ev_refresh_refresh_google_ads_60956db2c42f` odczytał
  `customer_currency_code=PLN`, 18 kampanii, 50 search terms, 200 wierszy
  90-dniowego search-term safety, 211 keyword context rows i 4 aktywne
  rekomendacje Google Ads.
- `/api/ads/diagnostics.account_currency_read_contract.status=ready`,
  `currency_code=PLN`; `account_currency` zniknęło z brakujących kontraktów
  derived KPI. Profitability, margin verdict i budget apply nadal są
  zablokowane.
- `/api/ads/diagnostics.recommendations_read_contract.status=ready`; impact
  preview jest dostępny dla 2 z 4 rekomendacji, a review-only apply payload
  preview dla 4 z 4 rekomendacji. Brakujący kontrakt pozostaje celowo wąski:
  zapisany wynik/akceptacja review strategii przez człowieka. Sam review gate
  jest już typed: `human_strategy_review`, `review_recommendation_type`,
  `review_impact_metrics`, `review_change_history`, `review_business_goal`,
  `recommendation_apply_preview`, `google_ads_rmf_compliance_review`,
  `human_confirm_before_apply`.
- `/api/ads/diagnostics.budget_pacing_read_contract.payload_preview` ma 18
  review-only `CampaignBudgetOperation` preview rows. ActionObject
  `act_prepare_ads_campaign_review_queue` ma 8 budżetowych preview rows,
  `preview_contract=budget_apply_preview_v1`, `apply_allowed=false`,
  `destructive=false` i waliduje się jako `valid=true`. To nadal nie jest
  budget apply support.
- Command Center Ads nie pokazuje już ogólnego statusu connectora jako insightu.
  Live `/api/dashboard/command-center` pokazuje teraz decyzję
  `Ads: kolejki budżetu, rekomendacji i zapytań` z licznikami:
  `kampanie=18`, `zapytania=50`, `podgląd budżetu=18`, `rekomendacje=4`,
  `wykluczenia=6`, `segmenty=1`. Ten sam prompt i ActionObjecty trafiają do
  scoped `/api/codex/context-pack` dla `wilq-daily-command`.
- Ads business context ma teraz wstępne, lokalne i nie-sekretne wartości w
  repo-local `.env` dla marży, celu biznesowego i celu budżetu, ale target
  ROAS/CPA jest celowo pusty do czasu ludzkiego potwierdzenia. Live proof
  2026-06-20 17:34 CEST po `scripts/local_stack.sh restart`:
  `/api/ads/diagnostics.business_context_read_contract.status=ready`,
  `missing=[target_roas_or_cpa]`, `target_roas=null`,
  `target_cpa_micros=null`, `allowed_metrics=[
  profit_margin,business_goal,human_budget_goal]`. Derived KPI rows nadal expose
  `target_cpa_micros`, `cpa_vs_target_micros`, `target_status`,
  `target_status_label` and `target_review_priority`, ale bez targetu pokazują
  `target_status=no_target` / `target_status_label=brak targetu` i pozostają
  triage/read-only, nie werdyktem.
- Ads business context z pustym targetem nie jest już globalnym blockerem.
  Command Center nie pokazuje `daily_ads_business_context` ani
  `decision_ads_business_context_before_budget_decisions`, a
  `/api/actions` nie zwraca `act_configure_ads_business_context`, jeśli core
  context jest ustawiony. Ten ActionObject wraca tylko wtedy, gdy brakuje
  marży, celu biznesowego albo celu budżetu. `/api/opportunities` ma nadal
  pomijać czysty setup blocker, bo opportunities są marketingowymi ruchami, nie
  naprawą konfiguracji.
  Historical proof for the earlier blocker slice:
  Wąski proof: ruff/mypy OK, 3 targeted backend tests OK, dashboard unit
  `14 passed`, Playwright action-detail smoke `1 passed`. Full
  `scripts/verify.sh` passed after this slice: backend `120 passed`,
  dashboard unit `14 passed`, Playwright e2e `11 passed`, dashboard build OK.
- Command Center tłumaczy teraz marketer-facing blocked claims w ogólnych
  kartach decyzyjnych/tactical/brief: API nadal niesie stabilne raw
  `blocked_claims`, ale UI pokazuje np. `ponowne zatwierdzenie produktu`,
  `wzrost leadów`, `opłacalność` i `zmarnowany budżet` zamiast
  `approval restored`, `lead uplift`, `profitability` albo `wasted budget`.
  Prompt Ads w `daily_decisions` i scoped `wilq-daily-command` context-pack
  też używa polskiego brzmienia: `Nie twierdź opłacalności, zmarnowanego
  budżetu ani wdrożenia zmian...`.
- Command Center nie pokazuje już marketerowi angielskich etykiet
  `Evidence` / `Przykładowe evidence` na kartach decyzji, taktyk i briefów.
  Widoczne etykiety to teraz `Dowody`, `Dowody: N ID(s)` i
  `Przykładowe dowody`; API nadal używa stabilnych pól `evidence_ids`.
- Command Center GA4 nie buduje już osobnego ogólnego skrótu z samych metric
  facts. Daily decision i scoped `wilq-daily-command` context-pack używają
  teraz tego samego `Ga4DiagnosticsResponse.decision_queue`, co `/ga4`, więc
  pokazują liczby `grupy ruchu`, `decyzje`, `pomiar`, `jakość ruchu` i
  `braki kontraktu` zamiast angielskich `landing groups` i ogólnego
  "brak pełnego kontraktu" jako głównego przekazu.
- `/api/ga4/diagnostics.decision_queue` ma teraz operator-facing `status`,
  `priority` i `metric_tiles`, a `/ga4` renderuje te kafelki per decyzja.
  Live proof po `scripts/local_stack.sh restart`: 6 decyzji GA4, 2 z
  `status=blocked` dla `(not set)` pomiaru i 4 z `status=ready` dla review
  jakości ruchu; kafelki pokazują `aktywni`, `sesje`, `zdarzenia`, `odsłony`
  i `engagement`, np. `(not set)/(not set)` ma `aktywni=179`, `sesje=179`,
  `engagement=0%`. Scoped `wilq-ga4-analyst` context-pack niesie te same
  pola bez redakcji GA4.
- `/api/ads/diagnostics.decision_queue` ma teraz operator-facing `priority` i
  `metric_tiles`, a `/ads-doctor` renderuje kafelki z typed API zamiast
  frontendowo zgadywać liczby z głębokich tablic. Live proof po
  `scripts/local_stack.sh restart`: 11 decyzji Ads, `null_priority_count=0`,
  `empty_tiles=[]`; top campaign decision pokazuje `kampanie=18`,
  `kliknięcia=117`, `wyświetlenia=3075`, `koszt=161`, `konwersje=2`.
  Search terms pokazują istniejące evidence-backed kafelki `zapytania=50`,
  `kliknięcia=7`, `koszt=41.8`, gdy bieżący search-term evidence ma
  `cost_micros`. Scoped `wilq-ads-doctor` context-pack niesie te same
  `priority` i `metric_tiles` bez redakcji Ads.
- Ads recommendations nie mieszają już human review z brakującymi read
  contracts. Live proof po `scripts/local_stack.sh restart`: rekomendacje i
  decision `ads_review_recommendations` mają `missing_read_contracts=[]` oraz
  `operator_review_gates` z `human_strategy_review`,
  `review_recommendation_type`, `review_impact_metrics`,
  `review_change_history`, `review_business_goal`,
  `recommendation_apply_preview`, `google_ads_rmf_compliance_review` i
  `human_confirm_before_apply`. Scoped `wilq-ads-doctor` context-pack zachowuje
  te gates bez `[REDACTED]`.
- Ads search terms nie mieszają już walidacji ActionObject z brakującym read
  contract. Live proof 2026-06-20 15:52 CEST:
  `/api/ads/diagnostics.search_terms_read_contract.missing_read_contracts=[]`,
  `operator_review_gates=[negative_keyword_action_validation]`; decyzja
  `ads_review_search_terms` pokazuje `metric_tiles={zapytania=50,
  kliknięcia=7, koszt=41.8}`, `missing_read_contracts=[]`,
  `operator_review_gates=[negative_keyword_action_validation]` i ActionObjecty
  `act_prepare_custom_segments_from_search_terms`,
  `act_prepare_negative_keyword_review_queue`.
- `/api/ads/diagnostics.search_term_safety_read_contract` i
  `keyword_match_context_read_contract` nie traktują już
  `human_intent_review` jako brakującego kontraktu danych, kiedy 90-dniowe
  safety rows i keyword match context istnieją. Live proof po
  `scripts/local_stack.sh restart`: oba kontrakty mają
  `missing_read_contracts=[]` oraz
  `operator_review_gates=["human_intent_review"]`; decyzje
  `ads_review_search_term_safety` i `ads_review_negative_keyword_safety`
  niosą tę samą bramkę. To nadal nie odblokowuje negative keyword apply.
- Scoped `wilq-campaign-builder` context-pack ma workflow-specific
  `active_action_objects`: tylko `act_prepare_ads_campaign_review_queue` i
  `act_prepare_google_ads_recommendation_review_queue`. Negative keywords i
  custom segments zostają w swoich skillach, żeby campaign-builder nie mieszał
  intencji i trzymał payload poniżej limitu 200 KB. Fresh API-process proof:
  `191737 bytes`.
- Scoped `wilq-ads-doctor` context-pack wrócił poniżej non-daily skill budget.
  Live proof po `scripts/local_stack.sh restart`: payload over the wire
  `174292 bytes`, smoke-reported `context_pack_bytes=183152`; `sections` i
  zduplikowane row payloads w `decision_queue` są pominięte, budget preview w
  kontrakcie jest ograniczony do 4 rows, a full endpoint pointer zostaje
  `/api/ads/diagnostics`.
- Scoped `wilq-demand-gen-operator` context-pack jest teraz honest-blocked, ale
  nie kłamie już o brakującym campaign-row read contract. Live API proof po
  restarcie portu 8000: `demand_gen_readiness.status=blocked`,
  `campaign_rows_evaluated=18`, `campaign_channel_counts={PERFORMANCE_MAX: 8,
  SEARCH: 10}`, `demand_gen_campaign_rows=[]`, `active_action_objects=[]` i
  `ads_diagnostics.action_ids=[]`. `demand_gen_campaign_rows` jest teraz w
  `available_read_contracts`; missing zostają tylko
  `demand_gen_asset_group_rows`, `demand_gen_creative_asset_rows`,
  `demand_gen_landing_quality_by_campaign`,
  `demand_gen_migration_constraints`, `demand_gen_action_object`. Skill smoke
  failuje, jeśli adjacent ActionObject wróci jako aktywna akcja Demand Gen albo
  jeśli campaign rows z kanałami są ponownie raportowane jako missing. Full
  `scripts/verify.sh` passed after this slice: backend `123 passed`,
  dashboard unit `15 passed`, Playwright e2e `12 passed`, dashboard build OK.
- `/api/opportunities` nie jest już rejestrem connectorów. Live proof po
  `scripts/local_stack.sh restart`: zwraca 4 decision-backed opportunities:
  Merchant feed review, Content refresh queue, GA4 measurement/traffic review
  i Ads review queue. ID zaczynają się od `opp_decision_*`, nie
  `opp_connector_*`; karty mają `metric_tiles`, evidence IDs, source
  connectors, ActionObject IDs i polski safe next step. Full Codex
  context-pack `top_opportunities` niesie ten sam zestaw bez redakcji
  `opportunities`.
- `/api/workflows` nie jest już listą 15 identycznych placeholderów. Live proof
  po `scripts/local_stack.sh restart`: 15 workflowów, w tym 4 `ready`,
  4 `blocked` i 7 `planned`; core workflowy (`daily_command`,
  `merchant_feed_review`, `gsc_content_doctor`, `ga4_data_analyst`,
  `ads_daily_check`) mają route, skill, metric tiles, source connectors,
  evidence IDs i ActionObject IDs. Stare stringi `Workflow definition runs
  against WILQ API` i `Fetch WILQ API context` są nieobecne. Ciepły
  `/api/workflows` zwraca około 23 KB w `0.008-0.012s`.
- `/api/knowledge/operating-map` i `/knowledge` mapują teraz wiedzę źródłową na
  decyzje, workflowy i skille zamiast pokazywać tylko katalog kart/playbooków.
  Live proof po `scripts/local_stack.sh restart`: 11 bindingów, 15 source
  cards, 14 playbooków i 31 expert rules. Core bindingi obejmują
  `knowledge_daily_command`, `knowledge_merchant_feed_review`,
  `knowledge_gsc_content_doctor`, `knowledge_ads_daily_check`,
  `knowledge_ga4_data_analyst` i `knowledge_localo_visibility_review`; Ads
  wiąże `card_google_ads_search_playbook`, `google_ads_search_playbook`,
  `ads_search_terms_v1` i 4 review-only ActionObjecty z `/ads-doctor` oraz
  `wilq-ads-doctor`, a Localo jawnie blokuje `local_ranking_rows`,
  `gbp_performance_rows` i `review_rows`.
- Content diagnostics i scoped `wilq-content-strategist` context-pack pokazują
  teraz typed decyzje z marketer-facing tytułem, summary, `primary_query`,
  `total_clicks`, `total_impressions`, `aggregate_ctr` i
  `best_average_position`. Live proof po `scripts/local_stack.sh restart`:
  top decyzje to `SEO: odśwież lub scal "bdo co to" (1 zapytanie)` z
  `4429 wyświetleń`, `4 kliknięcia`, CTR `0.09%` oraz
  `SEO: odśwież lub scal "zielony ład co to" (7 zapytań)` z
  `2902 wyświetlenia`, `123 kliknięcia`, CTR `4.24%`. Context-pack zachowuje
  evidence IDs i `act_prepare_content_refresh_queue`.
- Command Center first screen i scoped `wilq-daily-command` context-pack używają
  teraz tej samej content decision zamiast starego skrótu
  `Content: GSC query/page + WordPress inventory`. Live proof:
  `daily_decisions` dla `/content-planner` ma title
  `Przejrzyj kolejkę SEO z GSC i WordPress`, liczby `query/page=10`,
  `WP match=10`, `decyzje=4`, `wyświetlenia=7852`, `kliknięcia=138`,
  top reason `bdo co to` i brak `[REDACTED]` w `co_widzimy` /
  `dlaczego_to_ma_znaczenie`.
- Merchant diagnostics, `/merchant`, Command Center i scoped
  `wilq-merchant-feed-operator` context-pack używają teraz wspólnej
  `MerchantDiagnosticsResponse.decision_queue`, a nie osobno składanych raw
  facts. Live proof po `scripts/local_stack.sh restart`:
  `/api/merchant/diagnostics` pokazuje `product_count=10900`,
  `issue_count=15`, `issue_clusters=11`, `decision_count=8`; top decyzja:
  "Merchant: sprawdź brak potencjalnie wymaganego atrybutu / miara ceny
  jednostkowej", `issue_count=892`,
  `ev_refresh_refresh_google_merchant_center_a3ef2f66703f` i
  `act_review_merchant_feed_issues`. Scoped context-pack niesie tę samą
  decyzję bez redakcji w `merchant_diagnostics.decision_queue`, a Command
  Center pokazuje `produkty=10900`, `typy problemów=15`, `zgłoszenia=1887`,
  `decyzje=8`, `blockery=0`. Latest Merchant follow-up:
  `MerchantDecisionItem` ma teraz typed `priority` i numeric `metric_tiles`;
  live proof: 8 decyzji, `null_priority=[]`, `empty_tiles=[]`, top decyzja
  ma `priority=21` i `metric_tiles.zgłoszenia=892`.
- `wilq-ads-doctor` smoke przeszedł na świeżym API i potwierdza ten sam
  recommendations contract w scoped context-packu.
- Pełny `scripts/verify.sh` przeszedł po Ads scoped context-pack compaction
  slice:
  backend API contracts `119 passed`, dashboard route tests `14 passed`,
  Playwright e2e `11 passed`, security, skill/API smokes i dashboard production
  build passed.

Aktualny maintenance:

- `docs/PROGRESS.md` został skompaktowany do recovery ledgeru.
- Pełna historia sprzed kompaktowania leży w
  `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Last Completed Slices

1. ActionObject mutation audit boundary, 2026-06-20 21:58 CEST.
   Apply no longer has a path that can truthfully return `applied=true`
   without persisted mutation audit and a real vendor mutation adapter. Current
   Goal 001 state has no vendor mutation adapters, so all apply attempts remain
   blocked with `mutation_attempted=false`; this is intentional safety, not a
   missing `.env` issue. Full `scripts/verify.sh` passed: backend
   `136 passed`, dashboard unit `17 passed`, Playwright e2e `14 passed`,
   dashboard build OK.

2. Ahrefs strict skill usefulness eval, latest 2026-06-21 03:37 CEST.
   `wilq-ahrefs-gap-finder` eval case now targets `/ahrefs`, requires
   `ahrefs_diagnostics`, `decision_queue`,
   `ahrefs_review_authority_context`,
   `ahrefs_block_gap_claims_without_records`, missing gap read contracts and
   `blocked=true`. The harness now supports `expected_blocked`,
   `expected_no_action_ids`, `blocked_claim_terms` and
   `forbidden_action_ids`, so Ahrefs cannot pass by recommending adjacent
   content/Ads/Merchant/GA4 actions. Latest non-interactive eval passed at
   `.local-lab/evals/codex-skill/20260621T013710Z/wilq-ahrefs-gap-finder/result.json`
   with `api_used=true`, `blocked=true`, evidence from Ahrefs,
   `source_connectors=["ahrefs","google_search_console","wordpress_ekologus"]`
   and `operator_usefulness_score=4`.

3. Ahrefs diagnostics contract, 2026-06-20 12:41 CEST, superseded by the
   2026-06-21 04:05 competitor top-pages proof.
   `/api/ahrefs/diagnostics`, dashboard `/ahrefs`, shared schemas and scoped
   `wilq-ahrefs-gap-finder` context-pack now expose Ahrefs as authority
   context plus explicit competitor-page records. Historical live proof: DR=40,
   Ahrefs Rank=1541946, `gap_fact_count=10`, available contract
   `ahrefs_competitor_pages`, blocker `ahrefs_block_gap_claims_without_records`,
   missing read contracts then included `ahrefs_content_gap_records`,
   `ahrefs_backlink_gap_records`, `ahrefs_organic_keywords_by_url`,
   `ahrefs_top_pages_by_competitor`. Current proof now also has
   `ahrefs_top_pages_by_competitor`. The scoped context-pack has
   `active_action_objects=0`, so the skill no longer inherits content ActionObjects
   when Ahrefs diagnostics has no actions. Focused proof passed:
   ruff/mypy, targeted API contract test, dashboard route unit test, live
   Ahrefs skill smoke and Playwright `/ahrefs` smoke. Full `scripts/verify.sh`
   passed: backend `123 passed`, dashboard unit `15 passed`, Playwright e2e
   `12 passed`, skill/API smokes and dashboard production build passed.

4. Localo aggregate value facts, 2026-06-20 11:42 CEST.
   Localo MCP vendor_read now performs read-only GraphQL `query` calls after
   MCP initialize and stores only aggregate facts, not raw place names,
   addresses, keywords or Localo IDs. Live proof:
   `refresh_localo_9e9ff67eadad` completed with evidence
   `ev_refresh_refresh_localo_9e9ff67eadad`; key facts are
   `localo_active_place_count=4`, `localo_tracked_keyword_count=23`,
   `localo_avg_visibility_current=52.8261`,
   `localo_avg_latest_grid_position=3.2105`,
   `localo_reviews_count=793`, `localo_review_reply_rate=0.809584`.
   `/api/localo/diagnostics` now reports `live_data_available=true`,
   `visibility_fact_count=17`, `allowed_evidence=[place_inventory,
   local_rankings, reviews]`, and still blocks missing contracts
   `gbp_visibility`, `competitor_visibility`, `local_tasks`. Command Center
   now shows a Localo decision card only when real facts exist or access is
   blocked; current live tiles are `miejsca=4`, `frazy=23`,
   `widoczność=52.8261`, `recenzje=793`. Context-pack redaction was fixed so
   long metric names such as `localo_latest_grid_position_count` are preserved,
   while secret-like values remain redacted. Full proof passed:
   ruff/mypy on changed modules, `uv run pytest tests/test_api_contracts.py -q
   -k 'localo or redaction'`, dashboard route unit tests, live Localo
   vendor_read, live context-pack redaction check and `scripts/verify.sh`.
   Final verify result: backend API contracts `122 passed`, dashboard unit
   tests `14 passed`, Playwright e2e `11 passed`, skill/API smokes and
   production build passed.

5. Ads business context contract, 2026-06-20 10:12 CEST.
   `AdsDiagnosticsResponse` exposes typed
   `business_context_read_contract`, shared Zod schema and Ads Doctor UI
   labels. Current local target truth, live proof 2026-06-20 17:34 CEST:
   profit margin, business goal and budget goal can remain as non-secret review
   context, but `WILQ_ADS_TARGET_ROAS` and `WILQ_ADS_TARGET_CPA_MICROS` are
   empty until a human confirms them. With empty targets and core context
   present, the contract is `ready` but keeps
   `missing_read_contracts=[target_roas_or_cpa]`.
   Derived KPI rows still expose target comparison fields
   `target_cpa_micros`, `cpa_vs_target_micros`, `target_status`,
   `target_status_label` and `target_review_priority`; this is review-only
   context and still does not unlock apply, profitability verdicts or
   wasted-budget claims.

6. Ads scoped context-pack compaction, 2026-06-20 09:46 CEST.
   `wilq-ads-doctor` context-pack no longer ships duplicated Ads sections or
   row payloads inside `decision_queue`. Live proof: 174292 bytes over the wire
   and smoke-reported `context_pack_bytes=183152`; `sections_omitted=true`,
   `decision_row_payloads_omitted=true`, budget payload preview included rows
   capped at 4, full endpoint pointer preserved. The smoke script now fails if
   `wilq-ads-doctor` exceeds 200 KB.

## Active Gaps

- Content now has typed Ahrefs candidate rows and review-only
  `content_brief_preview_v1` payload previews in
  `act_prepare_content_refresh_queue`, operator selection/review persistence,
  stronger GSC/WP overlap for Ahrefs candidates and review-gated
  `wordpress_draft_payload_preview_v1`. Remaining work is better final brief
  selection, eventual WordPress write adapter/safety after explicit review and
  richer content impact contracts. Do not claim ranking, traffic, authority,
  lead or revenue uplift.
- Demand Gen is honest-blocked, not useful yet. Campaign channel rows are now
  available from Google Ads evidence, and current live state has no
  Demand Gen/Discovery campaigns. It still needs real Demand Gen read
  contracts for asset groups, creative assets, landing quality by campaign,
  migration constraints and a Demand Gen ActionObject.
- Full BDOS-class Ads optimizer is not done. Remaining areas include setting
  and using business targets (`WILQ_ADS_PROFIT_MARGIN`,
  `WILQ_ADS_BUSINESS_GOAL`, `WILQ_ADS_BUDGET_GOAL`,
  `WILQ_ADS_TARGET_ROAS` or `WILQ_ADS_TARGET_CPA_MICROS`), approved Keyword
  Planner access/idea rows, forecast/audience size, strategy-specific review
  policies beyond the generic human review outcome, budget apply safety and
  actual vendor mutation adapters. Local review/preview/confirm/impact-check
  and mutation-audit gates exist, but no vendor apply path is enabled.
- Command Center/dashboard is moving toward a usable marketer cockpit, but Goal
  001 remains active until the goal file's API/dashboard/skills/evals/safety
  requirements are all verified.
- Knowledge base/source-map work exists, but the long-term knowledge compiler
  and memory layer are not complete. Do not replace that with prompt stuffing.

## Next Best Slice

Continue with Goal 001 in this order unless live state shows a stronger blocker:

1. Improve the next marketer-facing cockpit surface that still repeats or hides
   useful decisions, or persist operator selection/review outcome for content
   brief previews if Content Planner is the active focus.
2. Continue Ads optimizer read contracts toward safe, review-only decisions.
3. Add or strengthen non-interactive skill evals only when they test real
   product usefulness, not just schema compliance.
4. Keep `docs/PROGRESS.md` compact; archive older entries instead of appending
   long history here.

## Recovery Pointers

- Active goal: `docs/goals/001-goal.md`.
- Recovery index: `docs/CONTEXT.md`.
- Skill eval ledger: `docs/evals/skill-eval-ledger.md`.
- Marketing source map: `docs/research/wilq-marketing-source-map.md`.
- BDOS-class architecture target:
  `docs/architecture/bdos-class-wilq-operating-system.md`.
- Full pre-compaction progress archive:
  `docs/progress/archive/2026-06-19-progress-ledger.md`.
