# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. Nie rób tu pełnego changeloga; szczegóły ma mieć Git i test
artifacts.

## Current Snapshot

Data: 2026-06-19

- API działa lokalnie: `http://127.0.0.1:8000`.
- Dashboard działa lokalnie: `http://127.0.0.1:5173/command-center`.
- `/api/marketing/brief` został zawężony do marketer decision brief:
  `what_we_know=6`, `what_blocks_us=0`, `safe_next_actions=3`,
  `recommended_focus=2`.
- Brief nie promuje już LinkedIn/Facebook/Sheets jako globalnych blockerów.
- Brief pokazuje tylko core działania:
  `act_review_merchant_feed_issues`,
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`.
- `/api/dashboard/command-center` po restarcie zwraca `sections={}` i action
  plan bez Localo status-only taska:
  `plan_review_merchant_feed_issues`,
  `plan_prepare_content_refresh_queue`,
  `plan_review_ga4_landing_quality`,
  `plan_review_ads_campaign_metrics`.
- Localo access działa na poziomie MCP initialize. `/api/localo/diagnostics`
  ma teraz osobny typed contract dla access/readiness, missing visibility
  contracts i blocked claims. Dashboard `/localo` renderuje własny widok
  `Status Localo / MCP access`, `Co marketer ma wiedzieć o Localo` i
  `Dowody i ograniczenia Localo`, zamiast generycznej kolejki `Taktyki z WILQ
  API`. Ranking/GBP/competitor/review facts nadal są blocked, bo WILQ ma tylko
  access probe, nie lokalną widoczność.
- Merchant issue-level triage jest wdrożony lokalnie w API/schema/action
  payload/dashboard route. `/api/merchant/diagnostics` zwraca
  `issue_clusters` z `issue_type`, `affected_attribute`, `country`,
  `reporting_context`, `severity`, `resolution`, `product_count`, evidence IDs,
  blocked claims i `act_review_merchant_feed_issues`. Dashboard `/merchant`
  pokazuje klastry jako primary review queue, a tactical items tylko jako
  fallback.
- Merchant diagnostics nie miesza już unikalnych produktów z wystąpieniami
  problemu w raportach. Top-level `product_count` i `issue_count` fallbackują do
  latest refresh summary, gdy metric store ma tylko issue-level facts. Dashboard
  `/merchant` używa etykiet `Zgłoszenia`, `kontekst` i `Metryki Merchant`, nie
  angielskiego `Affected`/`Metric facts`. Product-level sample IDs/titles nadal
  są jawnie niedostępne w obecnym read contract.
- Content URL normalization jest wdrożony lokalnie w tactical/content API:
  WordPress inventory jest pobierane pełniej z DuckDB, GSC full URL i GA4
  landing path są normalizowane do jednego path key, a decision queue pokazuje
  `normalized_page_path`, `wordpress_match_confidence` i
  `wordpress_content_url`. Bezpośredni proof z aktualnego checkoutu pokazał
  `found` dla BDO, Zielonego Ładu, remediacji oraz GA4 path fallback. Pełny
  `scripts/verify.sh` przeszedł dla tego slice'a.
- Metric store batch reads zachowują teraz kompletne najnowsze grupy metryk
  `(connector, evidence, dimensions)`, zamiast ucinać pojedyncze wiersze po
  `metric_name`. To naprawia Content Planner: GSC query/page cards nie pokazują
  już fałszywego `impressions=0` przy istniejących `clicks`/`ctr`; live browser
  proof po restarcie API pokazał m.in. `bdo co to` z `impressions=4429`,
  `ekologus` z `impressions=80` i Zielony Ład z realnymi impressions.
- Command Center first screen został odchudzony do jednego boardu
  `Dzisiejsze decyzje marketera`. Stary dubel `Dzisiejszy panel operatora` +
  `Plan działań marketera` został usunięty, a pełne connector blocker cards
  zeszły z `/command-center` do diagnostycznego `/settings`. Na głównym widoku
  zostaje tylko skrót `Źródła i ograniczenia`, bez credential names i bez
  udawania marketing insightu. Pełny `scripts/verify.sh` przeszedł po tej
  zmianie: backend API contracts 97 passed, dashboard route tests 12 passed,
  Playwright e2e 8 passed i dashboard production build passed.
- Ads Doctor ma pierwszy typed read contract:
  `/api/ads/diagnostics.campaign_read_contract`. Kontrakt grupuje live Google
  Ads metric facts do campaign rows z `campaign_id`, `campaign_name`, `clicks`,
  `impressions`, `cost_micros`, `conversions`, `conversion_value`, evidence
  IDs i blocked claims.
- Ads Doctor ma drugi typed read contract:
  `/api/ads/diagnostics.search_terms_read_contract`. Google Ads `vendor_read`
  odpytuje `search_term_view` w trybie odczytu i zapisuje `search_term_clicks`,
  `search_term_impressions`, `search_term_cost_micros`,
  `search_term_conversions`, `search_term_conversion_value` z wymiarami
  `campaign_id`, `campaign_name`, `ad_group_id`, `ad_group_name`,
  `search_term`, `search_term_status`. To odblokowuje uczciwy przegląd zapytań z
  kontekstem konwersji, ale nie odblokowuje waste/negative keyword claims bez
  `keyword match context`, `90_day_safety_check` i walidowanego ActionObject.
- Ads Doctor ma teraz typed decision queue:
  `/api/ads/diagnostics.decision_queue` zwraca
  `ads_review_campaign_activity`, `ads_review_search_terms` i
  `ads_block_write_actions_without_actionobject`. Dashboard `/ads-doctor`
  renderuje te decyzje jako primary marketer view oraz przenosi kampanie i
  zapytania do `Dowody i ograniczenia Ads`. Browser proof po restarcie API nie
  znalazł starych fraz: `Read contract Ads`, `Search terms read-only`,
  `Campaign activity read contract`, `Search terms read contract`,
  `Google Ads: campaign activity rows`, `Google Ads: search terms read-only rows`,
  `Evidence`, `configured`, `READY`, `payload preview`, `write/apply` ani
  `WILQ ma read-only Google Ads evidence`.
- Live Google Ads proof po restarcie API: `uv run wilq connectors refresh
  google_ads --mode vendor_read --reason "Goal 001 Ads conversion read
  contract proof"` zakończył się `completed`,
  `refresh_google_ads_c2f62ee2b43a`, `row_count=18`,
  `search_term_row_count=50`, `conversions=2.0`, `conversion_value=2.0`,
  `search_term_conversions=0.0`,
  `search_term_conversion_value=0.0`. Następnie `/api/ads/diagnostics`
  zwrócił campaign allowed metrics
  `clicks/impressions/cost_micros/conversions/conversion_value`, search-term
  allowed metrics z `conversions/conversion_value`, a missing contracts zostały
  ograniczone do `recommendations`, `change_history`, `budget_pacing`,
  `impression_share`, `keyword match context`, `90_day_safety_check` i
  `negative_keyword_action_validation`.
- Nadal nie wolno claimować CPA, ROAS, wasted budget, negative keyword
  candidates, budget scaling ani conversion drop bez osobnych read contracts.
- Command Center nie renderuje już zdublowanego zestawu kafli
  `Decyzje/Blockery/Źródła`; globalne stats zostają tylko w nagłówku strony.
  Test dashboardu ma regresję `Decyzje` count = 1.
- Ads Doctor i Command Center nie mówią już, że `search terms` są brakującym
  read contractem, gdy live search-term rows istnieją. Runtime blokuje teraz
  precyzyjniej: `search-term waste`, `negative keyword candidates`, CPA/ROAS i
  apply zmian pozostają blocked do czasu safety/ActionObject/derived KPI
  contracts.
- Ads Doctor nie zwraca już `blocked_handoff` przy live Google Ads data.
  `/api/ads/diagnostics` w stanie live ma teraz `blocked_handoff=null`,
  `action_ids=[]`, campaign/search-term read contracts i decyzję
  `ads_block_write_actions_without_actionobject` dla zablokowanego write path.
  OAuth repair handoff jest zarezerwowany wyłącznie dla realnego access
  blockera.
- `/localo` ma własny endpoint `/api/localo/diagnostics` i nie dokleja już
  generycznej globalnej kolejki `Taktyki z WILQ API`. Localo pokazuje
  access/readiness, missing contracts i blocked claims bez fałszywych liczników
  typu `24 Taktyki`, bez angielskiego `Metric facts` i bez komunikatu
  `Dokończ Localo access`, gdy MCP initialize już działa.
- `/ga4` ma teraz typed decision queue w `/api/ga4/diagnostics.decision_queue`
  i renderuje ją jako primary marketer view. Widok pokazuje decyzje
  `fix_measurement`, `review_landing_mapping` i `review_traffic_quality`,
  dowody, ActionObject `act_review_ga4_tracking_quality` i zablokowane claimy.
  Stare surowe sekcje typu `GA4: landing/source/campaign behavior`,
  `GA4: tracking/conversion readiness`, `Analytics Safety Gate`,
  `payload preview`, `read-only`, `configured`, `WP match`, `conversion-like`
  i `tracking-gap checklist` nie pojawiają się w browser proof.
  `agent-browser` proof: `.local-lab/proof/ga4-route-audit/screenshot-1781832367747.png`.
- `wilq-ga4-analyst` został dopięty do typed GA4 decision queue. Smoke skilla
  wymaga teraz `ga4_diagnostics.decision_queue`, evidence IDs,
  `google_analytics_4`, ActionObject `act_review_ga4_tracking_quality` i
  rozróżnienia `fix_measurement`, `review_landing_mapping`,
  `review_traffic_quality`. Fresh runtime proof po restarcie API:
  `/api/ga4/diagnostics` ma `live_data_available=true`,
  `landing_group_count=10`, `decision_count=6`, a smoke skilla widzi
  `decision_count=6`. Non-interactive Codex eval passed:
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
  Pełny `scripts/verify.sh` przeszedł po tym slice: backend API contracts
  `100 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
  i dashboard production build passed.
- Pełny `scripts/verify.sh` przeszedł po Ads search terms i Command Center
  duplicate-stats slice: backend API contracts 97 passed, dashboard route
  tests 12 passed, Playwright e2e 8 passed i dashboard production build passed.
- Pełny `scripts/verify.sh` przeszedł po Ads Doctor decision route cleanup:
  backend API contracts 98 passed, dashboard route tests 13 passed,
  Playwright e2e 9 passed i dashboard production build passed.
- Pełny `scripts/verify.sh` przeszedł po Localo diagnostics route cleanup:
  backend API contracts 100 passed, dashboard route tests 13 passed,
  Playwright e2e 9 passed i dashboard production build passed. Localo e2e
  potwierdza access readiness bez wymyślonych lokalnych metryk.

## Latest Verified Checks

- `uv run ruff check apps/api/wilq_api/main.py wilq/briefing/command_center.py tests/test_api_contracts.py`
- `uv run mypy apps/api/wilq_api/main.py wilq/briefing/command_center.py`
- `uv run pytest tests/test_api_contracts.py::test_command_center_returns_valid_shape tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief tests/test_api_contracts.py::test_command_center_treats_localo_mcp_initialize_as_access_ready -q`
- `uv run ruff check wilq/briefing/marketing_brief.py tests/test_api_contracts.py`
- `uv run mypy wilq/briefing/marketing_brief.py`
- `uv run pytest tests/test_api_contracts.py::test_marketing_brief_aggregates_metric_facts_and_blockers tests/test_api_contracts.py::test_marketing_brief_exposes_metric_backed_prepare_actions -q`
- `uv run ruff check wilq/schemas.py wilq/briefing/merchant_diagnostics.py wilq/actions/service.py tests/test_api_contracts.py`
- `uv run mypy wilq/schemas.py wilq/briefing/merchant_diagnostics.py wilq/actions/service.py tests/test_api_contracts.py`
- `uv run pytest tests/test_api_contracts.py -q -k 'merchant_diagnostics_exposes_feed_issue_queue or merchant_vendor_read_uses_aggregate_product_statuses'`
- `pnpm --filter @wilq/dashboard lint`
- `pnpm --filter @wilq/dashboard typecheck`
- `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
- `uv run ruff check .agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py wilq/briefing/localo_diagnostics.py wilq/schemas.py apps/api/wilq_api/main.py tests/test_api_contracts.py`
- `uv run mypy .agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py wilq/briefing/localo_diagnostics.py wilq/schemas.py apps/api/wilq_api/main.py`
- `uv run pytest tests/test_api_contracts.py -q -k 'localo_diagnostics or localo_access'`
- `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
- `WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts`
- `scripts/verify.sh`
- `pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts`
- `scripts/verify.sh`
- `uv run ruff check wilq/briefing/tactical_queue.py wilq/briefing/content_diagnostics.py wilq/storage/metric_store.py wilq/security/redaction.py wilq/schemas.py tests/test_api_contracts.py`
- `uv run mypy wilq/briefing/tactical_queue.py wilq/briefing/content_diagnostics.py wilq/storage/metric_store.py wilq/security/redaction.py wilq/schemas.py tests/test_api_contracts.py`
- `uv run pytest tests/test_api_contracts.py -q -k 'redaction_preserves_env_names_but_redacts_token_values or content_diagnostics_exposes_query_page_inventory_queue or marketing_tactical_queue_uses_wordpress_host_alias_sitemap_match or marketing_tactical_queue_uses_full_wordpress_inventory_for_url_matching'`
- `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-content-strategist --api-base http://127.0.0.1:8000`
- `uv run ruff check wilq/briefing/command_center.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py`
- `uv run mypy wilq/briefing/command_center.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py`
- `uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or command_center_treats_localo_mcp_initialize_as_access_ready or marketing_brief_exposes_metric_backed_prepare_actions'`
- `pnpm --filter @wilq/dashboard lint`
- `pnpm --filter @wilq/dashboard typecheck`
- `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
- `pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts`
- `uv run ruff check wilq/schemas.py wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py`
- `uv run mypy wilq/schemas.py wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py`
- `uv run ruff check wilq/connectors/google_ads/client.py wilq/schemas.py wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py`
- `uv run mypy wilq/connectors/google_ads/client.py wilq/schemas.py wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py`
- `uv run pytest tests/test_api_contracts.py -q -k 'google_ads_vendor_read_uses_oauth_and_search_stream or ads_diagnostics_exposes_live_campaign_metric_facts or ads_diagnostics_exposes_oauth_blocker_without_fake_metrics'`
- `pnpm --filter @wilq/dashboard lint`
- `pnpm --filter @wilq/dashboard typecheck`
- `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
- `uv run pytest tests/test_api_contracts.py -q -k 'ads_diagnostics_exposes_live_campaign_metric_facts or ads_diagnostics_exposes_oauth_blocker_without_fake_metrics'`
- `pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts`
- `scripts/verify.sh`
- `uv run ruff check wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`
- `uv run mypy wilq/briefing/ads_diagnostics.py`
- `uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q`
- `pnpm --filter @wilq/dashboard lint`
- `pnpm --filter @wilq/dashboard typecheck`
- `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
- `WILQ_E2E_API_PORT=8875 WILQ_E2E_DASHBOARD_PORT=5373 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts`
- `scripts/verify.sh`
- `uv run ruff check wilq/briefing/merchant_diagnostics.py tests/test_api_contracts.py`
- `uv run mypy wilq/briefing/merchant_diagnostics.py`
- `uv run pytest tests/test_api_contracts.py -q -k 'merchant_diagnostics_exposes_feed_issue_queue'`
- `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
- `pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts`
- `scripts/verify.sh`
- `uv run ruff check wilq/storage/metric_store.py tests/test_metric_store_and_cli.py tests/test_api_contracts.py`
- `uv run mypy wilq/storage/metric_store.py wilq/briefing/tactical_queue.py wilq/briefing/content_diagnostics.py`
- `uv run pytest tests/test_metric_store_and_cli.py -q`
- `uv run pytest tests/test_api_contracts.py -q -k 'marketing_tactical_queue_uses_dimensioned_metric_facts or content_diagnostics_exposes_query_page_inventory_queue'`
- `uv run ruff check wilq/briefing/ga4_diagnostics.py wilq/schemas.py tests/test_api_contracts.py`
- `uv run mypy wilq/briefing/ga4_diagnostics.py wilq/schemas.py`
- `uv run pytest tests/test_api_contracts.py -q -k 'ga4_diagnostics'`
- `pnpm --filter @wilq/dashboard lint`
- `pnpm --filter @wilq/dashboard typecheck`
- `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
- `uv run ruff check wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py`
- `uv run mypy wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py wilq/schemas.py`
- `uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ga4_diagnostics or route_specific'`
- `uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
- `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-ga4-analyst --api-base http://127.0.0.1:8000`
- `scripts/verify.sh`

```text
scripts/verify.sh passed
backend API contracts: 97 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Po Command Center cleanup 2026-06-18:

```text
scripts/verify.sh passed
backend API contracts: 97 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Po Ads campaign read contract 2026-06-18:

```text
scripts/verify.sh passed
backend API contracts: 97 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Po Merchant occurrence wording/API fallback 2026-06-18:

```text
scripts/verify.sh passed
backend API contracts: 98 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Po metric grouped reads / Content Planner impressions fix 2026-06-18:

```text
scripts/verify.sh passed
backend API contracts: 98 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Po Ads/Localo stale-state cleanup 2026-06-18:

```text
scripts/verify.sh passed
backend API contracts: 98 passed
dashboard route tests: 13 passed
Playwright e2e: 9 passed
dashboard production build: passed
```

Po GA4 decision queue route cleanup 2026-06-19:

```text
scripts/verify.sh passed
backend API contracts: 98 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Po Localo diagnostics route cleanup 2026-06-19:

```text
scripts/verify.sh passed
backend API contracts: 100 passed
dashboard route tests: 13 passed
Playwright e2e: 9 passed
dashboard production build: passed
```

## Current Gaps

1. Every WILQ skill must be tested against a real Polish marketer prompt and
   logged in `docs/evals/skill-eval-ledger.md`.
2. `scripts/codex_skill_eval.sh` exists, but current cases are still mostly
   smoke/schema oriented. They need richer usefulness scoring per skill.
3. `POST /api/codex/context-pack` is very large and expensive because it embeds
   many broad surfaces at once. This is a likely source of Codex skill latency.
4. `GET /api/dashboard/command-center` still computes several diagnostics and
   tactical queue data live. It is faster than the old baseline but should move
   toward a lightweight decision view model/cache.
5. Content workflow gap is narrower after URL normalization. GSC/GA4/WordPress
   URL matching now handles large WordPress inventories and GA4 landing paths,
   but decisions still need richer scoring for query intent, cannibalization and
   final marketer usefulness.
6. Merchant issue clusters expose aggregate issue dimensions and report
   occurrences, but not sample product IDs/titles. The dashboard states this
   limit explicitly instead of pretending to show product-level fixes.

## Performance Snapshot

Measured locally on 2026-06-18 before skill-scoped context-pack:

```text
/api/dashboard/command-center    3.217814 s    23790 bytes
/api/marketing/brief             0.640781 s    25392 bytes
/api/content/diagnostics         1.062442 s    91342 bytes
/api/marketing/tactical-queue    0.450769 s    82420 bytes
/api/codex/context-pack          9.152960 s    940864 bytes
```

Main causes:

- `context-pack` embeds broad product state for every skill, including 979
  `evidence_summaries`, 10 refresh runs, command center, marketing brief,
  tactical queue and multiple full diagnostic responses.
- `command-center` builds several diagnostic surfaces and tactical queue live.
- Skill runs often fetch both narrow diagnostics and the huge context-pack,
  causing repeated work.

Next performance direction:

- Add skill-scoped context-pack modes that return only the diagnostics,
  evidence IDs, ActionObjects and knowledge cards needed by the selected skill.
- Keep full context-pack for deep debug only.
- Add timing/size assertions for `context-pack` and Command Center after the
  view model is narrowed.

After adding skill-scoped `POST /api/codex/context-pack` for
`wilq-content-strategist`:

```text
full pre-scope context-pack       8.106033 s    940864 bytes
scoped content context-pack       2.679348 s    154334 bytes
```

Scoped content pack now includes:

- `content_diagnostics`,
- 5 relevant connector statuses,
- 80 evidence summaries,
- 2 action objects:
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`,
- 4 content-adjacent opportunities,
- no `command_center`,
- no `ads_diagnostics`,
- no social ActionObjects.

Smoke after the change:

```bash
uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Result: passed with `content_live=True`, `query_page_count=10`.

## Skill Smoke Snapshot

2026-06-18 deterministic smoke after skill-scoped context-pack:

```text
12/12 WILQ skill smoke scripts passed
summary artifact: .local-lab/evals/skill-smoke-summary-20260618T093210Z.jsonl
```

Notable contract corrections:

- `wilq-ads-doctor` smoke now allows live Ads mode without OAuth repair
  ActionObject. If Ads `live_data_available=false`, OAuth blocker ActionObject
  is still required.
- `wilq-daily-command` smoke now treats `demo_script=[]` as valid and checks
  `action_plan` as the marketer workflow source.

Current scoped context behavior:

- Daily command still gets full context because it is the operating brief.
- Other skills get skill-scoped context with narrower connectors, evidence,
  opportunities, actions and diagnostics.
- Several skills correctly return zero ActionObjects because current WILQ API
  has evidence/readiness but no safe prepare action for that workflow yet.

## Next Best Slice

Run skill evals one by one:

1. Manual prompt through Codex Desktop/CLI.
2. Deterministic smoke script.
3. `scripts/codex_skill_eval.sh --skill <skill> --api-base http://127.0.0.1:8000`.
4. Record prompt, endpoints, evidence IDs, useful output, hallucination risks
   and product gaps in `docs/evals/skill-eval-ledger.md`.

First non-interactive Codex eval completed:

```text
skill: wilq-content-strategist
result: passed
artifact: .local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json
```

Interpretation: the current harness proves Polish output, API usage, evidence
IDs, source connectors and safety discipline. It still needs stricter
usefulness assertions that force concrete decision queues like refresh,
merge/create-after-inventory-check and block.

Recovery note: full pipeline instructions now live in `docs/CONTEXT.md` under
`Skill Eval Pipeline`. Do not reconstruct the process from chat history. Next
recommended eval target: `wilq-merchant-feed-operator`, because it has a real
Merchant ActionObject (`act_review_merchant_feed_issues`) and high demo value.

Second non-interactive Codex eval completed:

```text
skill: wilq-merchant-feed-operator
result: passed
artifact: .local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json
```

Interpretation: this is a strong pass. It returned `pl-PL`, evidence IDs,
`google_merchant_center`, live Merchant facts (`product_count=10900`,
`issue_count=15`), and `act_review_merchant_feed_issues` as a safe
pending-validation review ActionObject. Next stricter improvement: force
issue-level clustering and validation-call proof.

Third non-interactive Codex eval completed:

```text
skill: wilq-ga4-analyst
result: passed
artifact: .local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/result.json
```

Interpretation: safe and useful pass. It returned `pl-PL`, GA4 evidence IDs,
`google_analytics_4`, `act_review_ga4_tracking_quality`, and correctly blocked
ROAS/revenue/conversion claims without stronger evidence. Next stricter
improvement: force ranked landing/source/campaign diagnostic items and
validation-call proof.

Fourth non-interactive Codex eval completed:

```text
skill: wilq-gsc-content-doctor
result: passed
artifact: .local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json
```

Interpretation: safe pass. It returned `pl-PL`, GSC/WordPress source
connectors, evidence IDs, `content_diagnostics.live_data_available=true`,
`query_page_count=10`, `matched_inventory_count=0`, and
`act_prepare_content_refresh_queue`. Next stricter improvement: force concrete
query/page candidates with `refresh`, `merge`, `create` or `block` decisions.

Fifth non-interactive Codex eval completed:

```text
skill: wilq-ads-doctor
result: passed
artifact: .local-lab/evals/codex-skill/20260618T102132Z/wilq-ads-doctor/result.json
```

Interpretation: strong guardrail pass. The eval case was corrected away from
the stale OAuth/deleted-client blocker. Current Ads truth is
`ads_diagnostics.live_data_available=true`, source connector `google_ads`,
32 evidence IDs, and no active Ads ActionObject in the main flow. The skill
allows live campaign-level facts, but blocks `search terms`, `CPA`, `ROAS` and
`wasted budget` without stronger evidence/read contracts. Next stricter
improvement: force a ranked campaign table and blocked-claim matrix.

Sixth non-interactive Codex eval completed:

```text
skill: wilq-localo-operator
result: passed
artifact: .local-lab/evals/codex-skill/20260618T102743Z/wilq-localo-operator/result.json
```

Interpretation: strong guardrail pass. The eval case was corrected away from
the stale missing-`LOCALO_ACCESS_TOKEN` blocker. Current Localo truth is access
readiness only: connector `localo` is configured, Localo refresh is completed,
`localo_metric_summary.api=localo_mcp_oauth_probe`, and
`mcp_initialize_status=200`. The skill correctly returns `blocked=true` for
ranking, GBP, competitor and local visibility uplift claims because those facts
do not exist yet in WILQ evidence. Next stricter improvement: add a real Localo
diagnostics/read contract before expecting local SEO recommendations.

Seventh non-interactive Codex eval completed:

```text
skill: wilq-daily-command
result: passed
artifact: .local-lab/evals/codex-skill/20260618T103758Z/wilq-daily-command/result.json
```

Interpretation: strong daily-loop pass. It returned `pl-PL`, all 8 expected
source connectors, daily evidence IDs, primary opportunities, and a concrete
next step: open `/merchant` and validate `act_review_merchant_feed_issues`.
The answer correctly treats Ads as live campaign review, Localo as access-ready
but no ranking/GBP facts, and blocks unsupported claims. Product gap found:
daily action candidates still include LinkedIn/Facebook draft ActionObjects
from wider `marketing_brief.action_ids`, while `CommandCenter.action_plan` is
cleaner and has only Merchant/Content/GA4 core actions.

Eighth non-interactive Codex eval completed:

```text
skill: wilq-campaign-builder
result: passed
artifact: .local-lab/evals/codex-skill/20260618T104154Z/wilq-campaign-builder/result.json
```

Interpretation: safe blocker pass. It returned `pl-PL`, `api_used=true`,
required connectors `google_ads`, `google_analytics_4`,
`google_search_console`, and 3 evidence IDs. It correctly sets `blocked=true`
because WILQ does not expose a campaign-specific ActionObject, payload preview,
keywords, assets, budget or campaign structure. Next product slice for this
skill is not prompt polish; it is an API/action contract for safe campaign
drafts.

Ninth non-interactive Codex eval completed:

```text
skill: wilq-custom-segments
result: passed
artifact: .local-lab/evals/codex-skill/20260618T104644Z/wilq-custom-segments/result.json
```

Interpretation: anti-hallucination pass. It returned `pl-PL`, `api_used=true`,
connectors `google_ads` and `google_search_console`, and `blocked=true`.
Recommendations and action candidates are empty because WILQ currently exposes
aggregate Ads/GSC metrics, not real source terms/search terms/query evidence
for audience candidates. Next product slice: source-term read contract with
evidence lineage.

Tenth non-interactive Codex eval completed:

```text
skill: wilq-demand-gen-operator
result: passed
artifact: .local-lab/evals/codex-skill/20260618T105005Z/wilq-demand-gen-operator/result.json
```

Interpretation: safe but shallow guardrail pass. It returned `pl-PL`,
`api_used=true`, Ads/GA4/Merchant connectors, `blocked=true`, and
`operator_usefulness_score=3`. The skill correctly refuses Demand Gen
recommendations because WILQ has aggregate Ads/GA4/Merchant readiness, but no
asset, creative, landing-quality or migration diagnostics. Next product slice:
Demand Gen diagnostics/read contract plus Demand Gen-specific ActionObject.

Eleventh non-interactive Codex eval completed:

```text
skill: wilq-ahrefs-gap-finder
result: passed
artifact: .local-lab/evals/codex-skill/20260618T105335Z/wilq-ahrefs-gap-finder/result.json
```

Interpretation: safe but shallow guardrail pass. It returned `pl-PL`,
`api_used=true`, connectors `ahrefs`, `google_search_console`,
`wordpress_ekologus`, and `blocked=true` with `operator_usefulness_score=3`.
The skill blocks backlink/competitor/content gap claims because WILQ currently
exposes aggregate Ahrefs authority metrics and adjacent GSC/WordPress facts, not
specific gap records. Next product slice: Ahrefs competitor/backlink/content
gap read contracts with evidence IDs.

Twelfth non-interactive Codex eval completed:

```text
skill: wilq-social-publisher
result: passed
artifact: .local-lab/evals/codex-skill/20260618T105649Z/wilq-social-publisher/result.json
```

Interpretation: strong safety pass. It returned `pl-PL`, `api_used=true`,
connectors `linkedin` and `facebook`, `blocked=true`, and
`operator_usefulness_score=5`. The skill exposes draft ActionObjects
`act_prepare_linkedin_social_drafts` and `act_prepare_facebook_social_drafts`,
but blocks them because social credentials and validation are missing. It does
not publish, does not call write/apply, and does not pretend permissions exist.

## Current Skill Eval Coverage

12/12 WILQ skills now have recorded non-interactive Codex evals.

The eval pass proves guardrails and API integration, not full product
completion. Highest-priority implementation fixes from the eval series:

1. Filter social draft ActionObjects out of daily primary action candidates.
2. Add Ads search-term/spend/conversion read contracts.
3. Add campaign-specific ActionObject + payload preview contracts.
4. Add source-term evidence for custom segments.
5. Add Localo ranking/GBP/competitor facts.
6. Add Ahrefs competitor/backlink/content gap records.
7. Add Demand Gen asset/creative/landing-quality diagnostics.
8. Upgrade evals from schema/safety checks to strict usefulness checks.

## Daily Social Action Filtering

Implemented the first eval-driven cleanup after 12/12 skill eval coverage.

Result:

- `/api/actions` still exposes `act_prepare_linkedin_social_drafts` and
  `act_prepare_facebook_social_drafts` for the explicit `/social-publisher`
  workflow.
- `/api/marketing/brief` no longer includes social draft ActionObjects in
  top-level daily `action_ids`.
- `POST /api/codex/context-pack` for `wilq-daily-command` now exposes only core
  daily `active_action_objects`.
- `POST /api/codex/context-pack` for `wilq-social-publisher` still includes
  the social draft ActionObjects.

Focused proof:

```bash
uv run ruff check apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py
uv run pytest tests/test_api_contracts.py -q -k 'marketing_brief_exposes_metric_backed_prepare_actions or codex_context_pack_embeds_marketing_brief_contract or daily_context_pack_excludes_social_draft_action_objects or social_context_pack_keeps_explicit_social_draft_action_objects or command_center_exposes_polish_operator_brief'
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
```

Live API note: the previously running `uvicorn` process did not use `--reload`,
so the first smoke still showed stale social action IDs. Restarted WILQ API on
`127.0.0.1:8000`; the repeated smoke returned only the three core daily actions.

## Localo Command Center Demotion

Cleaned the next Command Center readiness-only card.

Result:

- Current Localo state is configured/access-ready, not an OAuth/access blocker.
- Access-ready Localo no longer appears in primary `/api/dashboard/command-center`
  `operator_brief`, because WILQ still has no ranking/GBP/competitor facts.
- If Localo credentials are actually missing, Command Center still keeps a
  `daily_localo_readiness` blocker card.
- `/localo` remains the place for Localo readiness/access status until WILQ has
  a concrete local visibility read contract.

Focused proof:

```bash
uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or command_center_demotes_localo_access_ready_without_visibility_facts or command_center_keeps_localo_access_blocker_in_primary_brief'
```

## Marketing Brief Dimensional Facts

Cleaned another stale/sloppy state source.

Problem:

- `/api/marketing/brief` used a single global DuckDB metric limit.
- Recent aggregate refresh facts dominated that window, so the brief promoted
  weak aggregates such as `active_products=12`, `sessions=30`, `clicks=12` or
  `clicks=3` even though richer dimensional evidence existed in the store.

Result:

- Marketing brief now loads facts per connector with a larger connector-local
  limit.
- Metric selection prefers dimensional business facts and higher-value decision
  metrics before aggregate facts.
- Live shape now promotes Merchant issue facts, GSC query/page facts, GA4
  landing/source facts and Ads campaign facts.

Focused proof:

```bash
uv run ruff check wilq/briefing/marketing_brief.py tests/test_api_contracts.py
uv run mypy wilq/briefing/marketing_brief.py
uv run pytest tests/test_api_contracts.py -q -k 'marketing_brief_aggregates_metric_facts_and_blockers or marketing_brief_exposes_metric_backed_prepare_actions or codex_context_pack_embeds_marketing_brief_contract or command_center_exposes_polish_operator_brief'
```

## Daily Command Skill Guardrails

Hardened the first WILQ skill after the Command Center/brief cleanup.

Result:

- `wilq-daily-command` now explicitly treats the daily brief as a core daily
  loop: Merchant, Content/GSC/WordPress, GA4 and Ads.
- Localo readiness is not a primary daily task unless WILQ has a real Localo
  blocker or Localo ranking/GBP evidence.
- Social draft ActionObjects stay out of daily command and belong to
  `wilq-social-publisher`.
- The daily smoke now fails if the context-pack drops core daily actions or
  reintroduces social draft actions.

Focused proof:

```bash
uv run ruff check .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py tests/test_codex_skill_eval_cases.py
uv run mypy .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py
uv run pytest tests/test_codex_skill_eval_cases.py -q
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
scripts/codex_skill_eval.sh --skill wilq-daily-command --api-base http://127.0.0.1:8000
```

Non-interactive Codex eval artifact:

```txt
.local-lab/evals/codex-skill/20260618T112920Z/wilq-daily-command/result.json
```

Eval result: `pl-PL`, Polish diacritics, `api_used=true`, 14 evidence IDs,
core ActionObject candidates only, no safety findings and
`operator_usefulness_score=5`.

## Completed: Content Decision Queue In API

Status: committed and pushed.

Why:

- A 2026-06-18 audit in `docs/audits/001-output.md` confirmed that WILQ must
  move product decisions into typed API/view-model contracts, not skill
  references.
- `wilq-content-strategist` needed stronger usefulness, but the fix belongs in
  `/api/content/diagnostics`, not prompt edge cases.

Current result:

- Added typed `ContentDecisionItem`.
- Added `ContentDiagnosticsResponse.decision_queue`.
- `/api/content/diagnostics` now exposes canonical content decisions:
  `inventory_check_before_create`, `merge_create_after_inventory_check`,
  `refresh_or_merge` when inventory confirms a page, and
  `block_as_tracking_not_content` for GA4 tracking gaps.
- `wilq-content-strategist` now consumes `content_diagnostics.decision_queue`
  instead of recreating classification in skill references.
- Redaction preserves `decision_type` / `decision_types` enum values in
  context-pack while still redacting secrets.

Live smoke after API restart:

```bash
uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Observed decision types:

- `block_as_tracking_not_content`
- `inventory_check_before_create`
- `inventory_check_before_create`
- `merge_create_after_inventory_check`
- `inventory_check_before_create`

Focused proof already passed:

```bash
uv run ruff check wilq/briefing/content_diagnostics.py wilq/security/redaction.py wilq/schemas.py .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/briefing/content_diagnostics.py wilq/security/redaction.py wilq/schemas.py .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py -q -k 'redaction_preserves_env_names_but_redacts_token_values or content_diagnostics_exposes_query_page_inventory_queue or codex_context_pack_embeds_marketing_brief_contract'
uv run pytest tests/test_codex_skill_eval_cases.py -q
```

Non-interactive Codex eval after this change:

```txt
.local-lab/evals/codex-skill/20260618T114810Z/wilq-content-strategist/result.json
```

Eval result: `pl-PL`, `api_used=true`, 11 evidence IDs,
`operator_usefulness_score=4`, and recommendations based on
`content_diagnostics.decision_queue`.

Clean-runtime verify finding:

- `scripts/verify.sh` runs skill API smokes against an empty temporary
  SQLite/DuckDB runtime. Core daily ActionObjects must still exist there as
  review-only prepare actions with connector evidence, but content
  `decision_queue` must stay empty until real GSC/GA4/WordPress facts exist.
- `wilq/actions/service.py` now seeds core prepare ActionObjects and lets
  metric-backed ActionObjects override them when real facts are available.
- `wilq-content-strategist` smoke now distinguishes clean runtime from live
  content facts; it must not require fake decisions in clean runtime.

## Completed: Canonical DailyDecision

Status: committed and pushed as
`39511ac feat(command-center): add daily decision model`.

Why:

- `docs/audits/001-output.md` says Command Center must become one
  operator-first decision model instead of competing `operator_brief`,
  `action_plan`, `marketing_brief`, diagnostics and ActionObject fragments.
- Goal 001 requires canonical `DailyDecision` fields:
  `co_widzimy`, `dlaczego_to_ma_znaczenie`, `bezpieczny_next_step`,
  `blocked_claims`, `evidence_ids`, `source_connectors`, `action_ids`,
  `skill_id`, `codex_prompt` and `route`.

Current result:

- Added typed `DailyDecision`.
- `GET /api/dashboard/command-center` exposes `daily_decisions`.
- `daily_decisions` are built from the current action plan so backcompat
  surfaces remain available while the first screen moves to one canonical
  contract.
- Dashboard Command Center now renders `daily_decisions` as the main marketer
  plan.
- `wilq-daily-command` smoke validates that `daily_decisions` exists and is
  present in the context-pack trace.

Focused proof already passed:

```bash
uv run ruff check apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/schemas.py .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/schemas.py .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py
pnpm --filter @wilq/shared-schemas lint
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or daily_context_pack_excludes_social_draft_action_objects or codex_context_pack_embeds_marketing_brief_contract'
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
```

Live smoke after API restart showed four daily decisions:

- `decision_review_merchant_feed_issues` -> `wilq-merchant-feed-operator`
- `decision_prepare_content_refresh_queue` -> `wilq-content-strategist`
- `decision_review_ga4_landing_quality` -> `wilq-ga4-analyst`
- `decision_review_ads_campaign_metrics` -> `wilq-ads-doctor`

Full proof:

```bash
scripts/verify.sh
```

Result:

- backend API contracts: 93 passed
- dashboard route tests: 12 passed
- Playwright e2e: 8 passed
- dashboard production build: passed

Next after this foundation:

- keep Command Center first-screen work on `daily_decisions`,
- do not re-promote readiness-only cards as marketer insight,
- keep matching Codex prompts on the same evidence/action IDs.

## In Progress: Daily Codex Context-Pack Performance

Why:

- `wilq-daily-command` was still using the full context-pack by default.
- Baseline against the existing `:8000` runtime before this slice:
  - `/api/dashboard/command-center`: `5.937s`, `30521 bytes`;
  - `/api/marketing/brief`: `1.648s`, `46310 bytes`;
  - `POST /api/codex/context-pack {"skill":"wilq-daily-command"}`:
    `15.030s`, `996121 bytes`;
  - `POST /api/codex/context-pack {"skill":"wilq-daily-command","full_context":true}`:
    `11.734s`, `996121 bytes`.

Current local result:

- `wilq-daily-command` now gets a scoped default context-pack:
  - `context_scope.mode=daily`,
  - includes `command_center`, `marketing_brief`, core daily ActionObjects,
    relevant connector status, relevant evidence summaries, knowledge cards,
    expert rules and capabilities,
  - excludes `tactical_queue`, `ads_diagnostics`, `merchant_diagnostics`,
    `content_diagnostics` and `ga4_diagnostics` unless `full_context=true`.
- Evidence summaries are limited to evidence IDs referenced by the daily
  command/brief/actions, not every evidence object from every source connector.
- Fresh `:8011` runtime proof after the patch:
  - default daily context: `2.888s`, `160053 bytes`;
  - default daily context repeated: `2.985s`, `160053 bytes`;
  - default daily context repeated: `2.959s`, `160053 bytes`;
  - full daily context: `6.465s`, `998704 bytes`;
  - `/api/marketing/brief`: `0.541s`, `46072 bytes`;
  - `/api/dashboard/command-center`: `2.424s`, `30521 bytes`;
  - `/api/dashboard/command-center` repeated: `2.094s`, `30521 bytes`;
  - `/api/dashboard/command-center` repeated: `2.102s`, `30521 bytes`.
- The follow-up fix moved `marketing_brief` and evidence registry metric reads
  to batch DuckDB queries and makes read paths use read-only DuckDB
  connections when the DB file already exists. This removed the conflicting
  lock failure observed when the running `:8000` API and local profiling code
  read the same DuckDB file.
- Current local follow-up adds `wilq.briefing.daily_runtime.DailyRuntime`.
  Daily Codex context now builds `command_center`, `marketing_brief` and core
  actions from one connector/action/refresh snapshot instead of calling the
  endpoint builder and brief builder independently.
- `DailyRuntime` has a short API-process TTL cache
  (`WILQ_DAILY_RUNTIME_CACHE_SECONDS`, default `2`, disabled under pytest) and
  is invalidated after connector refresh and action validation/apply paths.
- Fresh helper API proof on `:8011` after this follow-up:
  - default daily context: `3.047s` cold, then `0.467s`, `0.544s`, `0.470s`
    warm within TTL;
  - payload size stayed `160478 bytes`;
  - `/api/dashboard/command-center`: `2.034s`, `2.029s`, `2.396s`;
  - `/api/marketing/brief`: `0.618s`, `0.608s`, `0.588s`.
- Runtime gotcha: direct `uv run python` profiling against the real
  `.local-lab/state/wilq.duckdb` can fail with a DuckDB conflicting lock if a
  long-running API process already has the DB open. For runtime proof, measure
  through HTTP or start a helper API with a copied `WILQ_METRIC_DB`.

Focused proof already passed:

```bash
uv run ruff check apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
uv run pytest tests/test_api_contracts.py -q -k 'daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or command_center_exposes_polish_operator_brief or daily_context_pack_excludes_social_draft_action_objects or codex_context_pack_contains_no_metric_invention_instruction or codex_context_pack_includes_expert_rule_summaries'
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8011
```

Remaining performance gap:

- This is a real improvement in payload size, DuckDB read stability and warm
  daily Codex runtime, but not a full cold-run performance win.
- The shared runtime/cache removes duplicated `command_center` +
  `marketing_brief` assembly for daily Codex context. The remaining cold cost
  is inside Command Center diagnostics and tactical joins; solve that through
  Merchant issue-level triage, URL normalization and a slimmer daily decision
  model, not prompt/reference logic.

## 2026-06-18 - Ads Doctor Status-Probe Regression And Skill Eval

What changed:

- `/api/ads/diagnostics` now selects the latest Google Ads `vendor_read` as
  the evidence-bearing refresh. A later `status_probe` no longer downgrades
  live Ads diagnostics into an OAuth blocker.
- When Ads live data is available, `act_configure_google_ads_env` is filtered
  out of `/api/marketing/brief`, `/api/ads/diagnostics.action_ids` and the
  scoped `wilq-ads-doctor` context-pack.
- DuckDB metric store operations now use a process-wide lock around reads and
  writes. This prevents concurrent FastAPI requests from competing for the
  local DuckDB file during Ads diagnostics/context-pack smoke runs.
- `wilq-ads-doctor` smoke output now exposes campaign/search-term read
  contract summaries, allowed metrics and row counts.

Runtime proof:

- `/api/ads/diagnostics` after restart:
  - `live_data_available=true`;
  - latest refresh `refresh_google_ads_c2f62ee2b43a`, mode `vendor_read`;
  - campaign rows `18`;
  - search-term rows `50`;
  - `blocked_handoff=null`;
  - write/apply constraints stay in `ads_action_safety`, not in an OAuth
    handoff.
- `/api/marketing/brief` no longer returns Google Ads OAuth repair action while
  Ads live data is available.
- `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` returns
  `active_action_objects=[]` and `ads_diagnostics.action_ids=[]` in the live
  Ads state.

Non-interactive skill proof:

```txt
.local-lab/evals/codex-skill/20260618T191243Z/wilq-ads-doctor/result.json
```

Result:

- `language=pl-PL`
- `api_used=true`
- `operator_usefulness_score=5`
- Evidence IDs:
  `ev_connector_google_ads_status`,
  `ev_refresh_refresh_google_ads_c2f62ee2b43a`.
- The output correctly states that Ads Doctor can show 18 campaign read-only
  rows and 50 search-term read-only rows, while blocking CPA, ROAS,
  search-term waste, wasted budget and negative keywords until missing
  read/safety/ActionObject contracts exist.

Focused proof already passed:

```bash
uv run ruff check apps/api/wilq_api/main.py wilq/briefing/ads_diagnostics.py wilq/briefing/marketing_brief.py wilq/storage/metric_store.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py wilq/briefing/ads_diagnostics.py wilq/briefing/marketing_brief.py wilq/storage/metric_store.py
uv run pytest tests/test_metric_store_and_cli.py tests/test_api_contracts.py -k 'metric_store or ads_diagnostics' -q
uv run pytest tests/test_api_contracts.py -k 'ads_diagnostics or context_pack or marketing_brief' -q
uv run pytest tests/test_codex_skill_eval_cases.py -q
uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=360 scripts/codex_skill_eval.sh --skill wilq-ads-doctor --api-base http://127.0.0.1:8000
```

## Audit-Derived Next Stack

Source:

```text
docs/audits/001-output.md
```

Current execution order after the daily context-pack/DuckDB read stability,
shared runtime/cache, Merchant issue-level triage and URL normalization slices:

1. Remove remaining Command Center readiness/developer slop.
2. Add Ads read contracts before search-term, CPA, ROAS or wasted-budget
   claims.

Skill repair is not done. It happens per workflow after the matching API/read
contract exists. Do not repair missing product behavior inside skill
references.

## 2026-06-18 - Command Center Codex Bridge Polish UI

What changed:

- Command Center daily decision cards now expose the full Codex bridge already
  present in the API model:
  - `skill_id`;
  - `codex_prompt`;
  - `codex_context_endpoint`;
  - `expected_codex_output`.
- The card copy now explicitly labels this area as `Jak Codex może pomóc`, so
  the marketer sees how the dashboard decision maps into a WILQ skill workflow.
- Command Center loading/footer copy was tightened in Polish:
  - `Ładowanie stanu WILQ API`;
  - `Otwórz ustawienia`;
  - `Źródła`, `Aktywne`, `Do naprawy` instead of connector/debug wording.

Focused proof:

```bash
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=<dynamic> WILQ_E2E_DASHBOARD_PORT=<dynamic> CI= pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1
```

Result:

- Dashboard lint passed.
- Dashboard typecheck passed.
- Dashboard route tests: `12 passed`.
- Controlled Playwright dashboard API smoke: `7 passed`.

## 2026-06-18 - Command Center Daily Decision Metric Tiles

What changed:

- `DailyDecision` now carries `metric_tiles`, not only status/source/evidence
  prose. Command Center decision cards render the tiles directly.
- The first-screen decisions now show marketer-readable numbers:
  - Merchant: `produkty=10900`, `issues=15`, `blockery=0`;
  - Content: `query/page=10`, `WP match=15`, `blockery=0`;
  - GA4: `landing groups=10`, `low engagement=0`, `WP match=5`;
  - Ads: `kampanie=18`, `search terms=50`, `blockery=1`.
- GA4 diagnostics now falls back to GA4 tactical queue groups when the
  section-level metric facts are empty, so Command Center no longer says
  `0 landing/source groups` while listing landing candidates.
- Merchant issue cluster IDs now include reporting context and resolution, so
  the same issue type in `all_contexts`, `FREE_LISTINGS` and `SHOPPING_ADS`
  no longer produces duplicate React keys or ambiguous cluster IDs.

Runtime proof:

```bash
curl -sS http://127.0.0.1:8000/api/dashboard/command-center | jq '.daily_decisions[] | {id,metric_tiles,co_widzimy}'
XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser open http://127.0.0.1:5173/command-center
XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser wait --text "produkty"
XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser snapshot --compact --depth 10
```

Proof artifact:

```txt
.local-lab/proof/command-center-audit/screenshot-1781814322197.png
```

Focused proof passed:

```bash
uv run ruff check wilq/schemas.py wilq/briefing/command_center.py wilq/briefing/ga4_diagnostics.py wilq/briefing/merchant_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/command_center.py wilq/briefing/ga4_diagnostics.py wilq/briefing/merchant_diagnostics.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or merchant_diagnostics_exposes_feed_issue_queue or ga4_diagnostics_exposes_landing_quality_contract'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
```

Remaining product risk:

- Command Center is better, but the primary route audit is not complete.
  Continue with `/merchant`, `/content-planner`, `/ga4`, `/ads-doctor` and
  `/localo`, checking each route for technical wording, stale readiness cards,
  duplicate intent and missing Codex/action bridge.

## 2026-06-19 - Actions And Opportunities Route Cleanup

What changed:

- `/actions` is no longer a generic registry dump. It starts from
  `ActionObjecty do przeglądu`, shows only ActionObjects plus related evidence,
  and does not prepend `OPPORTUNITIES`, `Evidence Registry` or
  `Connector Refresh Runs`.
- `/api/actions` no longer resurrects `act_configure_google_ads_env` after a
  later Google Ads `status_probe` when a completed Google Ads `vendor_read`
  already exists. The live-data check now selects the latest evidence-bearing
  `vendor_read`, not the latest refresh of any mode.
- `/opportunities` is explicitly a pomocniczy rejestr, not a marketer decision
  queue. The UI now uses Polish labels (`Dowody`, `Źródła`, `Reguły`,
  `Playbooki`) and no longer uses English readiness/inventory wording in the
  visible route copy.
- Backend opportunity titles were normalized from English readiness titles to
  Polish registry/blocker titles such as `Google Ads: rejestr reguł i
  playbooków` and `LinkedIn: brak dostępu do organizacji blokuje publikację`.
- Dashboard ESLint ignores Playwright artifacts (`test-results`,
  `playwright-report`) so lint does not depend on whether e2e artifacts already
  exist locally.

Browser proof:

- `agent-browser` `/opportunities` after a 15s settle:
  - headings start with `Rejestr kart opportunities`;
  - suspect hits are empty for `technical playbook inventory`,
    `Evidence użyte`, `Kolejka decyzji`, `connector ready for`,
    `requires evidence before`, `Run a read-only refresh`,
    `LinkedIn publishing evidence`, `Facebook Page publishing evidence`.
- `agent-browser` `/actions` after a 15s settle:
  - headings start with `ActionObjecty do przeglądu`;
  - suspect hits are empty for `OPPORTUNITIES`, `Connector Refresh Runs`,
    `Evidence Registry`, `Odnow Google Ads OAuth refresh token`,
    `Handoff blockera Ads`, `act_configure_google_ads_env`.

Focused proof passed:

```bash
uv run ruff check wilq/opportunities/engine.py wilq/actions/service.py tests/test_api_contracts.py
uv run mypy wilq/opportunities/engine.py wilq/actions/service.py
uv run pytest tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts -q
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts
```

Full proof passed:

```bash
scripts/verify.sh
```

Full gate result:

- Backend API contracts: `98 passed`.
- Dashboard route tests: `13 passed`.
- Playwright e2e: `9 passed`.
- Dashboard production build: passed.

Result:

- API focused pytest passed.
- Dashboard lint/typecheck passed.
- Dashboard route tests: `13 passed`.
- Playwright e2e: `9 passed`.

Remaining product risk:

- `/actions` is still a technical review surface and shows payload previews by
  design; marketer-first work belongs in Command Center and dedicated routes.
- `/opportunities` is no longer pretending to be the plan of the day, but it
  remains a supporting registry. Do not promote it back into Command Center as
  a decision queue.
- Continue route audit on `/merchant`, `/content-planner`, `/ga4`,
  `/ads-doctor` and `/localo` for stale copy, duplicate intent, missing
  Codex/action bridge and performance cost.

## 2026-06-19 - Merchant Route Operator Cleanup

What changed:

- `/merchant` is no longer a duplicate diagnostic dump of
  `Merchant Center: feed/product health` and
  `Merchant Center: kolejka feed/product issues`.
- The route now starts from a marketer task: `Co marketer ma zrobić teraz z
  feedem`, then shows issue clusters, safe mode, `Dowody i ograniczenia
  Merchant`, ActionObject validation and the feed safety gate.
- Visible Merchant copy no longer shows stale English/technical phrases such as
  `payload preview`, `review queue`, `read-only`, `configured`, `Evidence`,
  `Feed Safety Gate`, `ActionObject focus`, `automatic feed edit`,
  `approval restored` or `sample product IDs`.
- Merchant API copy now uses Polish operator wording for missing sample product
  IDs/titles, review queue and payload preview. Stable IDs/enums remain
  unchanged.
- Blocked Merchant claims are translated in the route UI while preserving the
  original API contract values underneath.
- Shared `ActionObjectFocus` now uses Polish labels:
  `ActionObjecty do walidacji`, `Dowody`, `Podgląd payloadu` and a Polish
  apply-blocker explanation.

Browser proof:

- `agent-browser` `/merchant` after API restart and an 8s settle:
  - headings include `Co marketer ma zrobić teraz z feedem`,
    `DOWODY I OGRANICZENIA MERCHANT`, `ACTIONOBJECTY DO WALIDACJI`,
    `BRAMA BEZPIECZEŃSTWA FEEDU`;
  - suspect hits are empty for `payload preview`, `review queue`,
    `read-only`, `feed/product`, `live product facts`, `raw product dumps`, `issue queue`,
    `configured`, `Evidence`, `Feed Safety Gate`, `ActionObject focus`,
    `Merchant Center: feed/product health`,
    `Merchant Center: kolejka feed/product issues`, `automatic feed edit`,
    `approval restored`, `sample product IDs`, `READY`, `resolution:`.

Focused proof passed:

```bash
uv run ruff check wilq/briefing/merchant_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/briefing/merchant_diagnostics.py
uv run pytest tests/test_api_contracts.py -q -k 'merchant_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
```

Full proof passed:

```bash
scripts/verify.sh
```

Full gate result:

- Backend API contracts: `98 passed`.
- Dashboard route tests: `13 passed`.
- Playwright e2e: `9 passed`.
- Dashboard production build: passed.

Remaining product risk:

- `/merchant` is now a useful route for feed review, but it still cannot show
  product-level sample IDs/titles until the Merchant read contract exposes
  them.
- Continue route audit on `/content-planner`, `/ga4`, `/ads-doctor` and
  `/localo` for stale copy, duplicate intent, missing Codex/action bridge and
  performance cost.

## 2026-06-19 - Content Planner Decision Route Cleanup

What changed:

- `/content-planner` now renders the typed
  `content_diagnostics.decision_queue` as the primary marketer view instead of
  re-rendering raw diagnostic sections and tactical rows.
- The route starts from `Co marketer ma zrobić teraz z treściami`, then shows
  content decisions, safe mode, `Dowody i ograniczenia Content`, ActionObject
  validation and the content safety gate.
- GSC/WordPress decisions are grouped per URL. The Zielony Ład cluster is one
  decision, not several duplicated query cards.
- GA4 `(not set)` tracking gaps are explicitly blocked as content tasks and
  routed to GA4 tracking review instead of pretending to be content
  recommendations.
- Missing GSC metrics are no longer coerced to zero. If a metric is absent from
  evidence, the API says `brak w evidence` instead of rendering false
  `impressions=0` or `ctr=0`.
- Visible Content Planner copy no longer shows stale English/technical labels
  such as `payload preview`, `refresh queue`, `read-only`, `Evidence`,
  `READY`, `configured`, `Query/page`, `WP match`, `WordPress match`,
  `missing`, `found`, `exact_url`, `GSC: query/page matrix`,
  `WordPress: inventory protection`,
  `Content Planner: bezpieczne akcje`, `CONTENT SAFETY GATE`,
  `impressions=0` or `ctr=0`.
- Backend content/GSC copy now uses Polish operator wording:
  `zapytania i URL-e`, `Zapytanie`, `Metryki GSC`,
  `Inventory WordPress`, `dokładny URL`, `zaindeksowany`,
  `brak w evidence`. Stable API field names and enum values remain unchanged.

Browser proof:

- `agent-browser` `/content-planner` after API restart and a 10s settle:
  - headings include `Co marketer ma zrobić teraz z treściami`,
    `Zablokuj GA4 tracking gaps jako zadania contentowe`,
    `Odśwież lub scal: /europejski-zielony-lad-co-to-takiego/`,
    `Bezpieczny tryb treści`, `Dowody i ograniczenia Content`,
    `ActionObjecty do walidacji` and `Brama bezpieczeństwa treści`;
  - suspect hits are empty for `payload preview`, `refresh queue`,
    `read-only`, `Evidence`, `READY`, `configured`, `Query/page`,
    `query/page`, ` query `, `WP match`, `WordPress match`, `missing`,
    `found`, `exact_url`, `GSC: query/page matrix`,
    `WordPress: inventory protection`,
    `Content Planner: bezpieczne akcje`, `CONTENT SAFETY GATE`,
    `impressions=0`, `ctr=0`.

Focused proof passed:

```bash
uv run ruff check wilq/briefing/content_diagnostics.py wilq/briefing/tactical_queue.py
uv run mypy wilq/briefing/content_diagnostics.py wilq/briefing/tactical_queue.py
uv run pytest tests/test_api_contracts.py -q -k 'content_diagnostics or tactical_queue'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
```

Focused Playwright note:

- A direct `pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts`
  attempt was interrupted because Playwright started the API webServer on
  `8875` but did not proceed to the dashboard webServer on `5373` within the
  interactive wait window. No test assertion failed before interruption.
  Browser proof against the live API/dashboard completed instead, and the full
  repo `scripts/verify.sh` later ran the same Playwright suite successfully.

Full proof passed:

```bash
scripts/verify.sh
```

Full gate result:

- Backend API contracts: `98 passed`.
- Dashboard route tests: `13 passed`.
- Playwright e2e: `9 passed`.
- Dashboard production build: passed.

Remaining product risk:

- `/content-planner` is now a usable decision route for content work, but the
  underlying decision model still needs richer ranking/impact logic before it
  can prioritize beyond evidence availability, WordPress match state and risk.
- Continue route audit on `/ga4`, `/ads-doctor` and `/localo` for stale copy,
  duplicate intent, missing Codex/action bridge and performance cost.

## 2026-06-19 - GA4 Decision Route Cleanup

What changed:

- `/api/ga4/diagnostics` now exposes `decision_queue` as typed API state.
- `Ga4DecisionItem` supports `fix_measurement`, `review_landing_mapping` and
  `review_traffic_quality`.
- Dashboard `/ga4` renders `Co marketer ma sprawdzić teraz w jakości ruchu` as
  the primary route surface instead of repeating raw diagnostic sections.
- The route keeps evidence IDs, source connectors, ActionObject
  `act_review_ga4_tracking_quality`, blocked claims and metric facts, but
  translates the proof layer into Polish operator wording.
- Old GA4 slop was removed from the route and proof tests:
  `GA4: landing/source/campaign behavior`,
  `GA4: tracking/conversion readiness`, `Analytics Safety Gate`,
  `payload preview`, `read-only`, `configured`, `WP match`, `WP missing`,
  `conversion-like`, `tracking-gap checklist` and `metric_facts`.
- Playwright Merchant assertions were also hardened to current live data:
  they verify Merchant review metrics, ActionObject and evidence rather than a
  single volatile issue type like `availability_updated`.

Browser proof:

- `agent-browser` `/ga4` after API restart and 10s settle:
  - headings include `GA4`, `Status GA4 / Landing Quality`,
    `Co marketer ma sprawdzić teraz w jakości ruchu`,
    `Napraw problem pomiaru GA4`, `Sprawdź mapowanie landing page: /`,
    `Sprawdź jakość ruchu: /europejski-zielony-lad-co-to-takiego/`,
    `Bezpieczny tryb analityki`, `Dowody i ograniczenia GA4`,
    `ActionObjecty do walidacji` and `Brama bezpieczeństwa GA4`;
  - suspect hits were empty for `payload preview`, `read-only`, `Evidence`,
    `READY`, `configured`, `WP match`, `WP missing`,
    `landing/source/campaign`, `Analytics Safety Gate`,
    `Tracking readiness`, `conversion-like`, `tracking-gap checklist` and
    `metric_facts`.
- Screenshot artifact:
  `.local-lab/proof/ga4-route-audit/screenshot-1781832367747.png`.

Focused proof passed:

```bash
uv run ruff check wilq/briefing/ga4_diagnostics.py wilq/schemas.py tests/test_api_contracts.py
uv run mypy wilq/briefing/ga4_diagnostics.py wilq/schemas.py
uv run pytest tests/test_api_contracts.py -q -k 'ga4_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
```

Full proof passed:

```bash
scripts/verify.sh
```

Full gate result:

- Backend API contracts: `98 passed`.
- Dashboard route tests: `13 passed`.
- Playwright e2e: `9 passed`.
- Dashboard production build: passed.

Remaining product risk:

- `/ga4` is now a usable decision route for traffic-quality review, but still
  does not unlock ROAS, revenue, conversion-drop or campaign-blame claims
  without conversion/cost/read contracts.
- Next route audit: `/ads-doctor`, then `/localo`.
- Next matching skill repair: `wilq-ga4-analyst` should consume the new
  `decision_queue` and pass strict non-interactive usefulness eval.

## 2026-06-19 - Ads Custom Segments Contract And Skill Proof

What changed:

- `/api/ads/diagnostics` now exposes
  `custom_segments_read_contract` and a `prepare_custom_segments` decision.
- Dashboard `/ads-doctor` renders custom segment candidates from real Google
  Ads search terms, with source terms, evidence IDs, blocked claims and
  prepare-only status.
- WILQ seeds `act_prepare_custom_segments_from_search_terms` from Google Ads
  metric facts when enough search-term evidence exists.
- `wilq-custom-segments` now requires `GET /api/ads/diagnostics`,
  `ads_diagnostics.custom_segments_read_contract`, source terms, evidence IDs
  and ActionObject validation.

Focused proof passed:

```bash
uv run ruff check wilq/schemas.py wilq/actions/google_ads/custom_segments.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py apps/api/wilq_api/main.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/schemas.py wilq/actions/google_ads/custom_segments.py wilq/actions/payloads.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py apps/api/wilq_api/main.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ads_diagnostics or custom_segments or route_specific'
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run python .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-custom-segments --api-base http://127.0.0.1:8000
```

Full proof passed:

```bash
scripts/verify.sh
```

Full gate result:

- Backend API contracts: `100 passed`.
- Dashboard route tests: `13 passed`.
- Playwright e2e: `9 passed`.
- Dashboard production build: passed.

Codex eval artifact:

```txt
.local-lab/evals/codex-skill/20260619T035937Z/wilq-custom-segments/result.json
```

Result:

- `pl-PL`, Polish diacritics and `api_used=true`.
- Evidence IDs include `ev_refresh_refresh_google_ads_c2f62ee2b43a`.
- 1 recommendation, 1 action candidate, usefulness score 5.
- ActionObject `act_prepare_custom_segments_from_search_terms` validates.
- Blocked claims remain `audience size`, `ROAS`, `conversion uplift`,
  `targeting applied` and `campaign performance`.

Remaining product risk:

- Custom segment candidates are now useful as prepare-only review, but still
  require Keyword Planner enrichment, forecast/audience-size contract and
  payload preview before any apply path.
- The current source terms are Google Ads evidence, not final audience quality.
  The operator must reject irrelevant or low-intent terms before campaign use.

## 2026-06-19 - Active Handoff: Shared Daily Runtime Endpoints

Current stage:

- WILQ is past the "connector dashboard" stage. The main demo routes now use
  typed decision queues and Polish operator copy for Command Center, Merchant,
  Content Planner, GA4, Ads Doctor and Localo.
- The next bottleneck is product usefulness plus performance: dashboard,
  Marketing Brief and Codex skills must consume the same daily view-model and
  not rebuild the same picture several times.

Current uncommitted slice:

- `apps/api/wilq_api/main.py` now routes:
  - `GET /api/dashboard/command-center` through
    `build_daily_runtime().command_center`;
  - `GET /api/marketing/brief` through
    `build_daily_runtime().marketing_brief`.
- `tests/test_api_contracts.py` has endpoint-level regression tests for both
  routes:
  - `test_command_center_endpoint_uses_daily_runtime_cache`;
  - `test_marketing_brief_endpoint_uses_daily_runtime_cache`.
- This builds on the already verified `DailyRuntime` TTL cache. It is meant to
  reduce duplicated daily view-model work across dashboard endpoints and daily
  Codex context-pack. It is not a claim that cold Command Center is solved.

Focused proof:

```bash
uv run ruff check apps/api/wilq_api/main.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py tests/test_api_contracts.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache or daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or marketing_brief_aggregates_metric_facts_and_blockers'
```

Result:

- ruff passed after removing the stale `build_command_center_response` import.
- mypy passed after using a string monkeypatch target.
- pytest passed: 5 selected tests.

Broader proof:

```bash
uv run pytest tests/test_api_contracts.py -q -k 'command_center or marketing_brief or daily_runtime or context_pack'
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
```

Result:

- backend selected tests: 17 passed.
- dashboard typecheck: passed.
- dashboard route tests: 13 passed.

Full proof:

```bash
scripts/verify.sh
```

Result:

- backend API contracts: 102 passed.
- dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- dashboard production build: passed.
- Skill API smoke passed.
- Non-blocking warning: Vite reports the main JS chunk is above 500 KB.

Next before push:

- commit as `perf(api): share daily runtime endpoints`.

Still open after this slice:

- Cold Command Center still needs a slimmer API decision model and less
  diagnostic/tactical join work.
- Skills still need strict usefulness evals beyond "safe blocking" for the
  remaining high-value operators.
- Dashboard still needs more real value contracts: Localo visibility facts,
  Ahrefs gaps, Keyword Planner enrichment, negative keyword safety and
  campaign ActionObject previews.
