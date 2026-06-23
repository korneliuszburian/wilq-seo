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

Aktualny proof produktowy:

- Command Center metric read performance, 2026-06-23.
  Command Center and tactical queue now use a faster DuckDB read path,
  `list_latest_metric_facts_by_connector`, for marketer first-screen decisions
  that do not need previous-value delta windows. The existing full
  `list_metric_facts_by_connector` remains available for surfaces that need
  deltas/trends. Local profile with copied DuckDB and cache disabled showed the
  latest read path at `0.666s` versus full delta read at `0.976s`; tactical
  queue and Command Center now consume the latest path. Follow-up: Command
  Center now reuses already batched Localo facts before falling back to
  `list_metric_facts_by_evidence_ids`, avoiding another DuckDB read for the
  same Localo run. Local copied-DB profile with cache disabled:
  `1.095s`, `1.028s`, `1.050s` for three Command Center builds with 4 daily
  decisions. Live HTTP after stack restart: `/api/dashboard/command-center`
  returned 4 daily decisions and warm cache responses around `0.010-0.015s`.
  Focused proof: RED/GREEN metric-store latest-read test, RED/GREEN tactical
  queue latest-read test, RED/GREEN Localo batched-fact reuse test, Command
  Center brief test, Command Center API contract test, Python ruff OK and mypy
  OK.
- Demand Gen first-flow cleanup, 2026-06-23.
  `/ads-doctor/demand-gen` no longer prints raw `ev_*` evidence IDs or raw
  `act_review_demand_gen_readiness` inside the marketer-facing first flow.
  Demand Gen campaign, landing-quality, migration-constraint and readiness
  preview cards now show counts such as `Dowody: N ID` and `ActionObjecty: N
  ActionObjecty`; lower `Dowody i ograniczenia Demand Gen` remains the place
  for raw evidence/action traceability. Browser proof with agent-browser on
  `http://127.0.0.1:5173/ads-doctor/demand-gen`: raw trace links appear after
  the lower proof heading. Focused proof: RED/GREEN Demand Gen route test,
  dashboard lint OK and dashboard typecheck OK.
- Command Center operator guidance cleanup, 2026-06-23 13:20 CEST.
  `/api/dashboard/command-center` no longer puts raw ActionObject IDs such as
  `act_review_ga4_tracking_quality`, `act_confirm_ads_target_guardrails` or
  `act_configure_google_ads_env` inside operator-facing `next_step`,
  `operator_action` or `bezpieczny_next_step` text. Those IDs remain in
  structured `action_ids` fields for traceability. Live API proof after stack
  restart: grep over Command Center guidance returned no raw `act_*` matches.
  Focused proof: RED/GREEN Command Center API contract, Python ruff OK and
  mypy OK.
- Ads Doctor cost formatting, 2026-06-23.
  `/api/ads/diagnostics` no longer exposes raw `koszt_micros=...` in
  marketer-facing summaries for campaign activity, search terms, n-grams or
  90-day safety reads. Decision tiles now use account currency labels such as
  `154 PLN`, `46 PLN` and `138 PLN` while technical schema fields like
  `cost_micros` remain available for Google Ads contracts and ActionObject
  payloads. Live API proof after stack restart showed no `koszt_micros=` in
  operator summaries. Focused proof: RED/GREEN Ads diagnostics API contract,
  Python ruff OK and mypy OK.
- Content Planner metric formatting, 2026-06-23.
  `/content-planner` no longer shows raw GSC metric float noise in decision
  metric tiles such as `1.6897081413210446` or `0.0445468509984639`. The route
  now renders marketer-facing values such as `1,69` for position and `4,45%`
  for CTR. The shared `TacticalQueuePanel` compact mode also renders grouped
  decisions without raw `ev_*` or `act_*` IDs. Live browser proof on
  `http://127.0.0.1:5173/content-planner` confirmed the formatted values.
  Focused proof: content formatter test, TacticalQueuePanel compact test,
  dashboard lint OK and dashboard typecheck OK.
- GA4 measurement decision titles, 2026-06-23.
  `/api/ga4/diagnostics` no longer emits repeated generic
  `Napraw problem pomiaru GA4` titles for different `(not set)` report rows.
  Measurement decisions now include the reporting context, for example
  `GA4: napraw pomiar - (not set) / (not set)` and
  `GA4: napraw pomiar - (not set) / google / organic`. Live `/ga4` browser
  proof shows the same distinct titles. Focused proof: RED/GREEN GA4 API title
  test, existing GA4 diagnostics contract test, Python ruff OK and mypy OK.
- Daily Command compact context hardening, 2026-06-23 11:03 CEST.
  `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` now embeds a
  compact Command Center based on `daily_decisions` only; legacy
  `operator_brief`, `action_plan` and `demo_script` are omitted from the packed
  command-center context. Live payload after stack restart:
  `command_center_daily_decisions_only=true`, `daily_decision_count=4`,
  payload size `149671` bytes. Non-interactive result:
  `.local-lab/evals/codex-skill/20260623T090211Z/wilq-daily-command/result.json`.
  Result: `pl-PL`, `api_used=true`, usefulness score 5, 17 evidence IDs,
  validated core actions `act_review_merchant_feed_issues`,
  `act_prepare_content_refresh_queue`, `act_review_ga4_tracking_quality`.
  Focused proof: API context-pack tests, daily smoke script and
  `scripts/codex_skill_eval.sh --skill wilq-daily-command` passed.
- Content strategist Codex eval usefulness hardening, 2026-06-23 10:52 CEST.
  `wilq-content-strategist` eval no longer proves only schema/API usage. The
  eval case now requires concrete `content_diagnostics.decision_queue` markers:
  `review_ahrefs_gap_records`, `inventory_check_before_create`,
  `merge_create_after_inventory_check`, `bdo co to` and `zielony ład`.
  Passing non-interactive result:
  `.local-lab/evals/codex-skill/20260623T085105Z/wilq-content-strategist/result.json`.
  Result: `pl-PL`, `api_used=true`, usefulness score 4, validated
  `act_prepare_content_refresh_queue`, recommendations for Ahrefs gap review,
  BDO inventory check and Zielony Ład merge/create-after-inventory-check.
  Focused proof: RED/GREEN eval-case test, content strategist smoke script and
  `scripts/codex_skill_eval.sh --skill wilq-content-strategist` passed.
- Ahrefs relevance cleanup, 2026-06-23 10:46 CEST.
  `/api/ahrefs/diagnostics` now ranks reviewable Ekologus gap records before
  generic/off-topic Ahrefs records and filters hard noise such as CUK insurance
  content and broad backlink domains. `/ahrefs` shows only top 5 gap records in
  the marketer-facing contract panel, while keeping the full API count and raw
  traceability lower in `Dowody i ograniczenia Ahrefs`. Live proof after stack
  restart: Ahrefs first flow shows Denios/DLA/Manutan-style review records and
  no longer starts with `apple.com`, `google.com`, `prawo jazdy` or CUK noise.
  Focused proof: RED/GREEN Ahrefs relevance API test, existing Ahrefs API tests,
  Ahrefs route test, Python ruff/mypy OK, dashboard lint OK and dashboard
  typecheck OK.
- GA4 first-flow trace cleanup, 2026-06-23 10:31 CEST.
  `/ga4` no longer prints raw `ev_*` evidence IDs or raw
  `act_review_ga4_tracking_quality` in first-flow GA4 measurement/operator
  cards or the `Bezpieczny tryb analityki` panel. Those cards now show
  evidence/action counts and the validation CTA says `Waliduj review GA4`;
  raw trace links remain lower in `Dowody i ograniczenia GA4`, ActionObject
  validation and review preview sections. Browser proof with agent-browser on
  `http://127.0.0.1:5173/ga4`: raw trace links start only under lower proof and
  validation sections. Focused proof: RED/GREEN GA4 route test, dashboard lint
  OK and dashboard typecheck OK.
- Merchant first-flow trace cleanup, 2026-06-23 10:24 CEST.
  `/merchant` no longer prints raw `ev_*` evidence IDs or raw
  `act_review_merchant_feed_issues` in first-flow Merchant decision cards or
  the `Bezpieczny tryb pracy` panel. Those cards now show evidence/action
  counts and marketer copy says `ActionObject review`; raw trace links remain
  lower in `Dowody i ograniczenia Merchant` and ActionObject validation.
  Browser proof with agent-browser on `http://127.0.0.1:5173/merchant`: raw
  trace links start only under the lower proof/validation sections. Focused
  proof: RED/GREEN Merchant API contract test, RED/GREEN Merchant route test,
  Python ruff/mypy OK, dashboard lint OK and dashboard typecheck OK.
- Custom Segments first-flow trace cleanup, 2026-06-23 10:15 CEST.
  `/ads-doctor/custom-segments` no longer prints raw `ev_*` evidence IDs inside
  marketer-facing custom segment candidate or forecast cards. Those cards now
  show evidence counts such as `Dowody: N ID`; raw evidence/action links remain
  available lower in `Dowody i ograniczenia segmentów`. Browser proof with
  agent-browser on `http://127.0.0.1:5173/ads-doctor/custom-segments`: raw
  trace links start only under the lower proof section. Focused proof: RED/GREEN
  custom-segments route test, dashboard lint OK and dashboard typecheck OK.
- Ahrefs first-flow trace cleanup, 2026-06-23 10:07 CEST.
  `/ahrefs` no longer prints raw `ev_*` evidence IDs in the marketer-facing
  first flow: Ahrefs decision cards and the Ahrefs gap contract panel now show
  evidence counts such as `Dowody: N ID`. Raw trace links remain available
  lower in `Dowody i ograniczenia Ahrefs`, where proof/traceability is the
  purpose. Browser proof with agent-browser on `http://127.0.0.1:5173/ahrefs`:
  raw evidence links start only under the lower Ahrefs proof section. Focused
  proof: RED/GREEN Ahrefs route test, dashboard lint OK and dashboard typecheck
  OK.
- Content Planner first-flow trace cleanup, 2026-06-23 09:59 CEST.
  `/content-planner` and `/seo-gsc` no longer print raw `ev_*` evidence IDs or
  raw `act_prepare*` ActionObject IDs in the first content decision flow:
  safe-mode summary, content decision cards, content brief preview cards and
  WordPress draft preview cards now show counts such as `Dowody: N ID` and
  `ActionObject: 1 ActionObject`. Raw trace links remain available lower in
  `Dowody i ograniczenia Content` and ActionObject validation sections. Browser
  proof with agent-browser on `http://127.0.0.1:5173/content-planner`: first
  decisions and preview cards are clean, raw links start only in the lower
  proof/validation sections. Focused proof: RED/GREEN GSC/content route test,
  dashboard lint OK and dashboard typecheck OK.
- Localo first-flow trace cleanup, 2026-06-23 09:53 CEST.
  `/localo` no longer prints raw `ev_*` evidence IDs in the marketer-facing
  first flow: Localo decision cards and the Localo/GBP safety gate now show
  evidence counts such as `Dowody: N ID`. Technical access proof and lower
  diagnostic trace sections remain separate from marketer recommendations.
  Browser proof with agent-browser on `http://127.0.0.1:5173/localo`: the top
  Localo flow shows status, visibility facts, two Localo decisions, the proof
  toggle and the safety gate without raw evidence links. Focused proof:
  RED/GREEN Localo route test, dashboard lint OK and dashboard typecheck OK.
- Ads Doctor first-flow trace cleanup, 2026-06-23 09:48 CEST.
  `/ads-doctor` no longer prints raw `ev_*` evidence IDs or raw
  `act_prepare/review/configure/apply*` ActionObject IDs in the first Ads
  decision flow: optimizer readiness, safe-mode summary, top decision cards and
  nested campaign triage cards now show counts such as `Dowody: N ID` and
  `ActionObjecty: N ActionObjecty`. Raw trace links remain available lower in
  dedicated evidence/action validation sections where traceability is the
  purpose. Browser proof with agent-browser on
  `http://127.0.0.1:5173/ads-doctor`: raw links start only after the lower
  `Dowody i ograniczenia Ads` / validation sections. Focused proof:
  RED/GREEN Ads Doctor route test, dashboard lint OK and dashboard typecheck OK.
- Actions route evidence-registry cleanup, 2026-06-23.
  `/actions` no longer renders the extra `Dowody powiązane z akcjami` evidence
  registry under ActionObject cards. The route still shows evidence counts on
  ActionObjects and the top metric, but it no longer lists raw `ev_*` headings
  on the marketer-facing route. Browser proof with agent-browser on
  `http://127.0.0.1:5173/actions`: the route shows `ActionObjecty do przeglądu`
  and ActionObject payload buttons, with no raw evidence section below.
  Focused proof: RED/GREEN dashboard route test, dashboard lint OK and
  dashboard typecheck OK.
- Ads change-impact wording cleanup, 2026-06-23.
  `/api/ads/diagnostics.change_impact_readiness_contract.next_step` no longer
  uses the marketer-facing phrase `snapshot kampanii`. It now says
  `aktualny odczyt kampanii`, while keeping the same safety gate: change rows,
  current campaign readout and pre/post windows are required before claiming
  change impact. Live proof after stack restart: `contains_snapshot_kampanii=false`
  and `contains_aktualny_odczyt=true`. Focused proof: RED/GREEN
  `test_ads_diagnostics_exposes_live_campaign_metric_facts`, Python ruff OK and
  mypy OK.
- Localo partial-contract blocker copy fix, 2026-06-23.
  `/api/localo/diagnostics` no longer contradicts itself when typed aggregate
  facts exist. With partial Localo evidence, the blocked decision now says it
  blocks missing contracts for GBP, competitor visibility and local tasks; it
  no longer says Localo has no facts. Live proof after stack restart:
  `live_data_available=true`, `visibility_fact_count=17`, `blocker_count=1`,
  blocked title `Blokuj GBP, konkurencję i local tasks bez pełnych kontraktów
  Localo`, missing contracts `[gbp_visibility, competitor_visibility,
  local_tasks]`. Focused proof: RED/GREEN Localo partial-visibility test plus
  access-ready and missing-access Localo diagnostics tests, Python ruff OK and
  mypy OK.
- Localo operator-summary visibility-facts fix, 2026-06-23.
  `/api/localo/diagnostics.operator_summary` now distinguishes ready typed
  Localo aggregate facts from access-only proof. When Localo has visibility
  facts, the summary directs the marketer to review places, tracked phrases,
  average visibility and reviews while keeping GBP, competitor visibility and
  write actions blocked. Live proof after stack restart:
  `live_data_available=true`, `visibility_fact_count=17`, `blocker_count=1`,
  next step starts with `Przejrzyj agregaty Localo`. Focused proof: RED/GREEN
  Localo partial-visibility diagnostics test plus access-ready/missing-access
  Localo tests, Python ruff OK and mypy OK.
- Ahrefs operator-summary copy fix, 2026-06-23.
  `/api/ahrefs/diagnostics.operator_summary.next_step` now reflects the ready
  gap-read state. When `gap_status=ready`, it tells the marketer to combine
  authority context with Ahrefs gap records, `/content-planner` and GSC instead
  of warning as if records were still missing. Live proof after stack restart:
  `gap_status=ready`, `gap_fact_count=100`, `blocker_count=0`, next step starts
  with `Połącz kontekst autorytetu z rekordami luk Ahrefs`. Focused proof:
  RED/GREEN Ahrefs gap-record diagnostics test plus neighboring Ahrefs tests,
  Python ruff OK and mypy OK.
- Ahrefs diagnostics gap-record visibility fix, 2026-06-23.
  `/api/ahrefs/diagnostics` no longer loses typed Ahrefs gap records when many
  newer authority-only reads exist in the metric store. The dedicated Ahrefs
  diagnostics read now covers enough Ahrefs metric facts to keep content/backlink
  gap records visible, so `/ahrefs` no longer contradicts `/content/diagnostics`.
  Live proof after `scripts/local_stack.sh restart`: `live_data_available=true`,
  `gap_fact_count=100`, `gap_status=ready`, `blocker_count=0`,
  `missing_read_contracts=[]`, decision IDs
  `ahrefs_review_authority_context` and `ahrefs_review_gap_records`. Focused
  proof: RED/GREEN Ahrefs buried-gap regression test plus existing Ahrefs
  authority/gap diagnostics tests, Python ruff OK and mypy OK for
  `wilq/briefing/ahrefs_diagnostics.py`.
- Command Center Content + Ahrefs decision alignment, 2026-06-23.
  `daily_content_queue` on `/api/dashboard/command-center` now includes the
  same Ahrefs gap-review source that `/api/content/diagnostics` exposes in its
  top content decisions. Live proof after `scripts/local_stack.sh restart`:
  source connectors include `ahrefs`, `google_search_console`,
  `wordpress_ekologus`, `wordpress_sklep`; metric tiles show `decyzje=5`,
  `rekordy Ahrefs=31`, `luki Ahrefs=4`, `link gaps=9`,
  `wyświetlenia=7852`, `kliknięcia=138`; evidence sample includes
  `ev_refresh_refresh_ahrefs_cb31460610d3` and
  `ev_refresh_refresh_google_search_console_554550c44ec7`. Focused proof:
  RED/GREEN `test_command_center_exposes_polish_operator_brief`, lightweight
  builder test, Python ruff OK and mypy OK for `wilq/briefing/command_center.py`.
- Command Center Ads value tiles, 2026-06-23 08:31 CEST.
  `daily_ads_status.metric_tiles` on `/api/dashboard/command-center` now
  includes live Ads value totals from campaign facts: `kliknięcia`,
  `wyświetlenia`, `koszt`, `konwersje` and `wartość konw.`. Cost and
  conversion value are rendered as account units with the detected currency,
  not as raw micros or unlabelled money-like numbers. This reuses
  the generic Command Center metric tile renderer, so the first screen gets the
  same evidence-backed Ads volume/value context as `/ads-doctor` without React
  owning Ads business logic. The summary copy now says `aktualny odczyt`, not
  snapshot. Focused proof: RED/GREEN
  `uv run pytest tests/test_api_contracts.py -q -k
  command_center_ads_plan_uses_live_review_queues`, plus Python ruff/mypy on
  `wilq/briefing/command_center.py` and `tests/test_api_contracts.py`.
- Command Center Ads plan value-led follow-up, 2026-06-23 08:36 CEST.
  `plan_review_ads_campaign_metrics` now starts from `Przejrzyj aktualny
  odczyt Ads bez apply` and carries the live Ads values in `why_it_matters`
  before review queues. The operator action now points to the value readout on
  `/ads-doctor` first, then budget, recommendation, exclusion and segment
  review. Focused proof: `uv run pytest tests/test_api_contracts.py -q -k
  command_center_ads_plan_uses_live_review_queues`, Python ruff OK and mypy OK
  for `wilq/briefing/command_center.py`.
- Command Center Ads latest-summary fix, 2026-06-23 08:43 CEST.
  `daily_ads_status` now uses the latest Google Ads refresh `metric_summary`
  for top-line campaign totals instead of summing older metric-store facts.
  Live proof after `scripts/local_stack.sh restart`:
  `kampanie=18`, `zapytania=50`, `kliknięcia=117`, `wyświetlenia=2968`,
  `koszt=154.05 PLN`, `konwersje=2`, `wartość konw.=2 PLN`,
  `podgląd budżetu=18`, `rekomendacje=4`, while review candidates still come
  from detailed facts. Focused proof: RED/GREEN
  `uv run pytest tests/test_api_contracts.py -q -k
  'command_center_ads_totals_use_latest_refresh_summary or
  command_center_ads_plan_uses_live_review_queues'`, Python ruff OK and mypy
  OK for `wilq/briefing/command_center.py`.
- Command Center Merchant latest-refresh fix, 2026-06-23 08:48 CEST.
  `daily_merchant_feed` now filters Merchant facts to the latest
  `google_merchant_center` refresh before building first-screen totals. It no
  longer sums older refreshes or carries stale Merchant tactical evidence into
  the Command Center card. Live proof after `scripts/local_stack.sh restart`:
  Command Center shows `produkty=10900`, `typy problemów=4`,
  `zgłoszenia=1887`, `decyzje=8`, matching `/api/merchant/diagnostics`
  `decision_count=8` and `reported_issue_occurrences=1887`. Focused proof:
  RED/GREEN `uv run pytest tests/test_api_contracts.py -q -k
  'command_center_merchant_uses_latest_refresh_issue_facts or
  command_center_ads_totals_use_latest_refresh_summary or
  command_center_ads_plan_uses_live_review_queues or
  command_center_exposes_polish_operator_brief'`, Python ruff OK and mypy OK.
- Command Center GA4 decision-category fix, 2026-06-23 08:54 CEST.
  `daily_ga4_landing_quality` now counts the same visible decision categories
  as `/api/ga4/diagnostics`: missing reporting dimensions are `pomiar`, normal
  landing/source/campaign groups are `jakość ruchu`, and the first-screen
  decision count is capped to the visible GA4 queue. Live proof after
  `scripts/local_stack.sh restart`: Command Center shows `grupy ruchu=10`,
  `decyzje=6`, `pomiar=2`, `jakość ruchu=4`, matching `/api/ga4/diagnostics`
  `decision_count=6`, `blocked=2`, `ready=4`. Focused proof: RED/GREEN
  `uv run pytest tests/test_api_contracts.py -q -k
  'command_center_ga4_uses_visible_decision_cap or
  command_center_uses_ga4_metric_facts_without_ga4_tactical_items or
  command_center_exposes_polish_operator_brief'`, Python ruff OK and mypy OK.
- Ads value readout, 2026-06-23 07:53 CEST.
  `/api/ads/diagnostics.operator_summary` exposes typed top-line campaign
  totals: `total_clicks`, `total_impressions`, `total_cost_micros`,
  `total_conversions` and `total_conversion_value`. `/ads-doctor` renders them
  in the first `Aktualny odczyt Ads` section under `Wartości Ads`,
  before review-count metadata. This gives the marketer immediate live Ads
  volume/value context while still blocking ROAS, CPA, waste and apply claims.
  Focused proof: RED/GREEN API contract test
  `uv run pytest tests/test_api_contracts.py -q -k
  ads_diagnostics_exposes_live_campaign_metric_facts`, focused dashboard route
  test `pnpm --filter @wilq/dashboard exec vitest run src/routes/App.test.tsx
  -t "ads doctor route renders live metric-backed diagnostics"`, Python
  ruff/mypy, dashboard typecheck and dashboard lint passed.
- Connector refresh evidence-summary cleanup, 2026-06-23 07:36 CEST.
  `ConnectorRefreshRunList` shows `Dowody: N ID` instead of inline raw
  evidence IDs in refresh-run cards and renders `metric_summary` as a compact
  `Metryki: key=value` line instead of raw JSON. The registry can still expose
  operational run state, but cards no longer read like raw trace logs. Focused
  proof: `pnpm --filter @wilq/dashboard exec vitest run src/routes/App.test.tsx
  -t "connector refresh run cards summarize evidence"` passed, dashboard
  typecheck OK and dashboard lint OK.
- Actions evidence-summary cleanup, 2026-06-23 07:31 CEST.
  `/actions` ActionObject cards show `Dowody: N ID` instead of raw evidence
  IDs such as `ev_1`. Full evidence trace remains in API/detail surfaces, but
  the marketer-facing card no longer reads like an internal registry dump.
  Focused proof: `pnpm --filter @wilq/dashboard test -- --run
  src/routes/App.test.tsx -t "actions route starts from ActionObjects instead
  of registry dumps"` passed, dashboard lint OK and dashboard typecheck OK.
- Custom Segments dashboard cleanup, 2026-06-23 07:27 CEST.
  `/ads-doctor/custom-segments` nie pokazuje już debugowego
  `/api/codex/context-pack skill=wilq-custom-segments`. Widok pokazuje
  marketer-facing `Tryb Codexa: Custom Segments`, zachowując dowody i
  ActionObjecty jako linkowane trace. Focused proof: `pnpm --filter
  @wilq/dashboard test -- --run src/routes/App.test.tsx -t "custom segments
  route renders dedicated review-only contract"` passed, dashboard lint OK and
  dashboard typecheck OK.
- Settings dashboard cleanup, 2026-06-23 07:22 CEST.
  `/settings` używa polskiego nagłówka `Ustawienia` i pokazuje tylko status
  connectorów/credentiali zamiast doklejać opportunities, evidence registry,
  connector refresh runs, actions i expert rules. Widok pobiera tylko dane
  potrzebne do connector status. Focused proof: `pnpm --filter
  @wilq/dashboard test -- --run src/routes/App.test.tsx -t "connector status
  renders"` passed on rerun after one lazy-load flake in unrelated Ads Doctor
  assertion, dashboard lint OK and dashboard typecheck OK.
- Knowledge dashboard cleanup, 2026-06-23 07:14 CEST.
  `/knowledge` nie drukuje już raw `knowledge_card_ids`, `playbook_ids`,
  `expert_rule_ids`, `missing_contracts` ani source lineage jako list ID na
  kartach mapy wiedzy. Widok pokazuje marketer-facing liczniki: skill
  dostępny/brak, liczba dowodów, ActionObjectów, kart wiedzy, playbooków,
  reguł eksperckich i brakujących kontraktów. `/knowledge` nie dokleja już
  ogólnych registry dumpów (`Evidence Registry`, refresh runs, actions,
  expert rules, connector status) i nie pobiera tych rejestrów w tym widoku.
  Focused proof:
  `pnpm --filter @wilq/dashboard test -- --run src/routes/App.test.tsx -t
  "knowledge route renders compiled cards and playbooks"` passed, dashboard
  lint OK and dashboard typecheck OK.
- Actions/dashboard navigation polish, 2026-06-23 07:10 CEST.
  `/actions` używa nagłówka i kafla `ActionObjecty` zamiast angielskiego
  `Actions/ActionObjects`, a główna nawigacja ma polskie etykiety
  `ActionObjecty`, `Baza wiedzy`, `Ustawienia`. Focused proof:
  `pnpm --filter @wilq/dashboard test
  -- --run src/routes/App.test.tsx -t "actions route starts from ActionObjects
  instead of registry dumps"` passed, dashboard lint OK and dashboard typecheck
  OK.
- Connector settings localization, 2026-06-23 07:03 CEST.
  `ConnectorGrid` używa polskich operator-facing labeli:
  `Brakujące credentiale`, `Skonfigurowany`, `Źródło dostępu`. Focused proof:
  `pnpm --filter @wilq/dashboard test -- --run src/routes/App.test.tsx -t
  "connector status renders"` passed, dashboard lint OK and dashboard
  typecheck OK.
- Workflows dashboard cleanup, 2026-06-23 07:00 CEST.
  `/workflows` nie drukuje już raw `skill_id` ani nazw brakujących kontraktów
  na kartach workflowów. Widok pokazuje, czy skill jest dostępny, oraz licznik
  brakujących kontraktów; raw kontrakty zostają w API/diagnostyce. Focused
  proof: `pnpm --filter @wilq/dashboard test -- --run src/routes/App.test.tsx
  -t "workflow route renders persisted workflow runs"` passed, dashboard lint
  OK and dashboard typecheck OK.
- Opportunities dashboard cleanup, 2026-06-23 06:57 CEST.
  `OpportunityList` nie drukuje już raw evidence IDs, expert rule IDs ani
  playbook IDs na kartach decyzji. Karta pokazuje liczbę dowodów, źródła
  marketerowym labellem, liczbę ActionObjectów i licznik kontraktów wiedzy;
  pełne dowody nadal są w sekcji `Dowody użyte przez karty`. Focused proof:
  `pnpm --filter @wilq/dashboard test -- --run src/routes/OpportunitiesRoute.test.tsx`
  passed, dashboard lint OK and dashboard typecheck OK.
- Localo dashboard cleanup, 2026-06-23 06:53 CEST.
  `/localo` nie pokazuje już MCP/OAuth jako pierwszoplanowej metryki
  marketingowej. Top route pokazuje `Fakty lokalne`, `Braki danych` i
  `Blokady`, a `MCP initialize`, OAuth code, PKCE i token presence są schowane
  pod przyciskiem `Pokaż techniczny proof Localo`. Focused proof:
  `pnpm --filter @wilq/dashboard test -- --run src/routes/App.test.tsx -t
  "localo social and content routes render workflow-specific blockers or focus"`
  passed, dashboard lint OK and dashboard typecheck OK. Product finding:
  Localo pozostaje review/access proof bez ranking/GBP/competitor facts, ale
  dashboard nie myli już marketera technicznym MCP statusem na first screen.
- Full verify stabilization, 2026-06-23 05:17 CEST.
  `scripts/verify.sh` passes after the validated skill-eval series and clean
  runtime fixes. Final proof: backend API contracts `156 passed`, dashboard
  unit tests `17 passed`, Playwright e2e `14 passed`, skill/API smokes passed
  and dashboard production build passed. Two contract clarifications are now
  encoded: opportunities can include evidence-backed blocked plan items even
  when no ActionObject is safe yet, and campaign/social smoke scripts validate
  review ActionObjects when the scoped context-pack exposes them but do not
  fail empty clean-runtime smoke fixtures.
- Campaign Builder eval hardening, 2026-06-23 02:21 CEST.
  `wilq-campaign-builder` smoke validates
  `act_prepare_ads_campaign_review_queue` and
  `act_prepare_google_ads_recommendation_review_queue` through
  `POST /api/actions/{action_id}/validate`, exposes `action_validations`, and
  the eval case requires both review ActionObjects. Passing artifact:
  `.local-lab/evals/codex-skill/20260623T022153Z/wilq-campaign-builder/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_ads","google_analytics_4","google_search_console"]`,
  15 evidence IDs, `operator_usefulness_score=4`, `safety_findings=[]` and
  two validated Ads review action candidates. Product finding: Campaign
  Builder can now prepare campaign/recommendation review queues from WILQ
  evidence, but this is still not a campaign apply/create proof.
- Social Publisher eval hardening, 2026-06-23 02:17 CEST.
  `wilq-social-publisher` smoke validates
  `act_prepare_linkedin_social_drafts` and
  `act_prepare_facebook_social_drafts` through
  `POST /api/actions/{action_id}/validate`, exposes `action_validations`, and
  the eval case requires both social draft ActionObjects. Passing artifact:
  `.local-lab/evals/codex-skill/20260623T021758Z/wilq-social-publisher/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["linkedin","facebook"]`, 2 evidence IDs,
  `blocked=true`, `operator_usefulness_score=5`, `safety_findings=[]` and two
  validated review-only social draft action candidates. Product finding:
  WILQ can prepare the social review path, but it correctly refuses to
  recommend or publish social content while LinkedIn/Facebook credentials and
  social evidence are missing.
- Daily Command eval hardening, 2026-06-23 02:09 CEST.
  `wilq-daily-command` smoke validates the three core daily ActionObjects
  through `POST /api/actions/{action_id}/validate`:
  `act_review_merchant_feed_issues`,
  `act_prepare_content_refresh_queue` and
  `act_review_ga4_tracking_quality`. The eval case requires those
  `expected_validated_action_ids`. Passing artifact:
  `.local-lab/evals/codex-skill/20260623T020946Z/wilq-daily-command/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`, source
  connectors across Ads, GSC, GA4, Merchant, Ahrefs, Localo and WordPress, 26
  evidence IDs, 3 validated ActionObject candidates,
  `operator_usefulness_score=5` and `safety_findings=[]`. Product finding:
  daily-command now proves the shared dashboard/Codex daily loop for Merchant,
  Content and GA4 review actions while keeping social drafts out of the daily
  path and Localo out of primary work unless concrete visibility facts or a
  real blocker exist.
- Localo eval hardening, 2026-06-23 01:57 CEST.
  `wilq-localo-operator` smoke now validates
  `act_review_localo_visibility_facts` through
  `POST /api/actions/{action_id}/validate`, exposes `action_validations`, and
  the eval case requires
  `expected_validated_action_ids=["act_review_localo_visibility_facts"]`.
  Passing artifact:
  `.local-lab/evals/codex-skill/20260623T015753Z/wilq-localo-operator/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["localo"]`, 2 evidence IDs, `blocked=true`,
  `operator_usefulness_score=4`, `safety_findings=[]` and a validated Localo
  review ActionObject. Product finding: Localo MCP access/review proof exists,
  but detailed ranking, GBP performance, competitor visibility and local
  visibility uplift claims remain blocked without additional WILQ facts.
- Demand Gen eval hardening, 2026-06-23 01:51 CEST.
  `wilq-demand-gen-operator` smoke now validates
  `act_review_demand_gen_readiness` through
  `POST /api/actions/{action_id}/validate`, exposes `action_validations`, and
  the eval case requires
  `expected_validated_action_ids=["act_review_demand_gen_readiness"]`. Passing
  artifact:
  `.local-lab/evals/codex-skill/20260623T015108Z/wilq-demand-gen-operator/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_ads","google_analytics_4"]`, 16 evidence IDs,
  `blocked=true`, `operator_usefulness_score=4`, `safety_findings=[]` and a
  validated readiness review ActionObject. Product finding: Demand Gen remains
  honestly blocked for launch/migration/performance claims, but WILQ can now
  prove the review-only readiness ActionObject.
- GSC Content Doctor eval hardening, 2026-06-23 01:47 CEST.
  `wilq-gsc-content-doctor` smoke now validates
  `act_prepare_content_refresh_queue` through
  `POST /api/actions/{action_id}/validate`, exposes `action_validations`, and
  the eval case requires
  `expected_validated_action_ids=["act_prepare_content_refresh_queue"]`.
  Passing artifact:
  `.local-lab/evals/codex-skill/20260623T014727Z/wilq-gsc-content-doctor/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_search_console","wordpress_ekologus","wordpress_sklep"]`,
  4 evidence IDs, `operator_usefulness_score=4`, `safety_findings=[]` and a
  validated content refresh queue candidate. Product finding: the GSC-specific
  skill now proves the same safe content review ActionObject as
  `wilq-content-strategist`, but scoped to `/seo-gsc` and query/page evidence.
- Custom Segments eval hardening, 2026-06-23 01:43 CEST.
  `wilq-custom-segments` already validated
  `act_prepare_custom_segments_from_search_terms`; the smoke output now exposes
  the standard `action_validations` field and the eval case requires
  `expected_validated_action_ids=["act_prepare_custom_segments_from_search_terms"]`.
  Passing artifact:
  `.local-lab/evals/codex-skill/20260623T014325Z/wilq-custom-segments/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_ads","google_search_console"]`, 2 evidence IDs,
  `operator_usefulness_score=4`, `safety_findings=[]` and one validated
  custom-segment action candidate. Product finding: WILQ can prepare
  source-term-backed custom segment candidates for review, but apply remains
  blocked by `custom_segment_apply_safety_v1` until forecast/audience size,
  Keyword Planner enrichment, Google Ads mutation audit and human confirmation
  exist.
- Ads Doctor eval hardening, 2026-06-23 01:38 CEST.
  `wilq-ads-doctor` smoke now validates the four marketer-facing Ads
  review-only ActionObjects through `POST /api/actions/{action_id}/validate`:
  `act_prepare_ads_campaign_review_queue`,
  `act_prepare_google_ads_recommendation_review_queue`,
  `act_prepare_custom_segments_from_search_terms` and
  `act_prepare_negative_keyword_review_queue`. The eval case now requires all
  four in `expected_validated_action_ids`. Passing artifact:
  `.local-lab/evals/codex-skill/20260623T013842Z/wilq-ads-doctor/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_ads"]`, 3 Ads evidence IDs,
  `operator_usefulness_score=5`, `safety_findings=[]` and four validated Ads
  `action_candidates`. Product finding: Ads Doctor can now prove safe
  campaign review, recommendation review, custom-segment review and negative
  keyword safety review paths while still blocking recommendation apply,
  negative keyword apply, budget scaling, targeting/apply, CPA, ROAS and
  wasted-budget claims without the missing review/apply/audit contracts.
- Command Center cold path action split, 2026-06-23 01:31 CEST.
  `/api/dashboard/command-center` no longer builds full ActionObject payloads
  through `list_actions()` on the first-screen path. `build_daily_command_center`
  now builds only connectors + tactical queue when no full daily base is
  provided, and `build_command_center_response` uses lightweight action stubs
  for IDs needed by the first screen. The endpoint also uses one batched
  `list_metric_facts_by_connector` read instead of four separate metric fact
  reads. Live proof after stack restart: Command Center cold/warm/warm/warm/warm
  `1.483985s/0.009951s/0.012386s/0.008260s/0.008596s`, down from the previous
  measured `2.54s` cold hit. Tradeoff: first `/api/marketing/brief` after
  restart now pays the full ActionObject payload cost (`1.741512s`) because it
  genuinely needs the full action model. Focused proof: command-center daily
  runtime/API tests OK, Python ruff OK and Python mypy OK.
- Content strategist eval hardening, 2026-06-23 01:24 CEST.
  `wilq-content-strategist` smoke now validates
  `act_prepare_content_refresh_queue` through
  `POST /api/actions/{action_id}/validate` and exposes
  `action_validations`. The non-interactive eval case now requires
  `expected_validated_action_ids=["act_prepare_content_refresh_queue"]`.
  Passing artifact:
  `.local-lab/evals/codex-skill/20260623T012450Z/wilq-content-strategist/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_search_console","google_analytics_4","ahrefs","wordpress_ekologus","wordpress_sklep"]`,
  6 evidence IDs, `operator_usefulness_score=4`, `safety_findings=[]` and
  `action_candidates[0].validation_state="validated"`. Product finding: the
  skill now proves the content refresh/merge/create/block review queue is a
  validated prepare path while still blocking unsupported ranking, lead,
  revenue, WordPress write and auto-publish claims.
- Merchant skill eval hardening, 2026-06-23 01:17 CEST.
  `wilq-merchant-feed-operator` smoke now validates
  `act_review_merchant_feed_issues` through
  `POST /api/actions/{action_id}/validate` and exposes
  `action_validations`. The non-interactive eval case now requires
  `expected_validated_action_ids=["act_review_merchant_feed_issues"]`.
  Passing artifact:
  `.local-lab/evals/codex-skill/20260623T011722Z/wilq-merchant-feed-operator/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_merchant_center"]`, 14 Merchant evidence IDs,
  `operator_usefulness_score=5`, `safety_findings=[]` and
  `action_candidates[0].validation_state="validated"`. Product finding: the
  skill can now prove the Merchant feed review ActionObject is valid while
  still blocking approval-restored, revenue-recovered, automatic-feed-edit and
  primary-feed-overwrite claims.
- GA4 skill eval hardening, 2026-06-23 01:13 CEST.
  `wilq-ga4-analyst` smoke now validates
  `act_review_ga4_tracking_quality` through
  `POST /api/actions/{action_id}/validate` and exposes
  `action_validations`. The non-interactive Codex eval case now requires
  `expected_validated_action_ids=["act_review_ga4_tracking_quality"]`.
  Passing artifact:
  `.local-lab/evals/codex-skill/20260623T011123Z/wilq-ga4-analyst/result.json`.
  Result has `language=pl-PL`, Polish diacritics, `api_used=true`,
  `source_connectors=["google_analytics_4"]`, 12 GA4 evidence IDs,
  `operator_usefulness_score=4`, `safety_findings=[]` and
  `action_candidates[0].validation_state="validated"`. Product finding: the
  skill can now prove the safe GA4 review ActionObject is valid while still
  blocking revenue, ROAS, conversion-drop, profitability and tracking-fixed
  claims because conversion/key-event mapping remains missing.
- Command Center lightweight daily builders, 2026-06-23 01:05 CEST.
  `/api/dashboard/command-center` no longer builds full Ads/Content/Merchant/GA4
  diagnostics for the first screen. It now builds daily brief items from
  tactical queue groups plus scoped metric facts, while full diagnostics remain
  on their dedicated routes. `tactical_queue` also stopped calling full
  `list_actions()` just to attach action IDs; it now uses a static lightweight
  action-ID map for the three tactical queue connectors. Live proof after stack
  restart: Command Center cold/warm/warm HTTP `2.1856s/0.0074s/0.0086s`;
  Marketing Brief after CC `0.4372s/0.0087s/0.0110s`; tactical queue warm
  around `0.008s`. Focused proof: Python ruff OK, Python mypy OK, 10 API
  command/tactical tests OK and 17 dashboard route tests OK. Remaining cold
  cost is mostly tactical metric-store read/model construction; avoid rebuilding
  full route diagnostics on first-screen paths.
- Dashboard diagnostic route code splitting, 2026-06-23 00:50 CEST.
  `apps/dashboard/src/routes/App.tsx` lazy-loads the heavy diagnostic route
  modules: Ads Doctor, Custom Segments, Demand Gen, GA4, Localo, Ahrefs,
  Merchant and Content/GSC. Detail routes stay statically imported because they
  are smaller and have named exports. Production build now emits separate
  diagnostic chunks, including `AdsDoctorSurface` (~67.7 kB raw), `ContentDiagnosticSurface`
  (~20.9 kB raw), GA4/Merchant/Localo/Ahrefs/Demand Gen/Custom Segments chunks,
  and a separate main `index` chunk. Focused proof: dashboard typecheck OK,
  dashboard lint OK, focused dashboard route test OK, and dashboard build OK.
  Remaining performance work is backend cold-build internals and later
  component-level splitting inside large route modules when it directly improves
  product velocity.
- Tactical queue compact groups, 2026-06-23 00:41 CEST.
  `/api/marketing/tactical-queue` now exposes API-owned `compact_groups` next
  to raw `items`. `TacticalQueuePanel` compact mode now renders these groups
  instead of grouping query/page/landing/feed issue rows, summing metrics and
  generating marketer-facing copy in React. Live proof after stack restart:
  raw `item_count=10`, `compact_group_count=4`, first compact group is the
  Zielony Ład cluster with `7 zapytań`, summed `clicks=123` and
  `impressions=2902`, evidence `ev_refresh_refresh_google_search_console_554550c44ec7`
  and `act_prepare_content_refresh_queue`. Focused proof:
  `uv run pytest tests/test_api_contracts.py -q -k marketing_tactical_queue_uses_dimensioned_metric_facts`,
  Python ruff OK, Python mypy OK, shared schema typecheck OK, dashboard
  typecheck OK, dashboard lint OK and focused dashboard route test OK.
- Daily runtime split, 2026-06-23 00:36 CEST.
  `/api/dashboard/command-center` no longer builds the full Marketing Brief on
  the Command Center endpoint path. `wilq/briefing/daily_runtime.py` now has a
  shared `DailyRuntimeBase` plus separate cached derivations:
  `build_daily_command_center()` and `build_daily_marketing_brief()`. The
  compatibility `build_daily_runtime()` still exists for surfaces that need both
  objects. Focused proof:
  `uv run pytest tests/test_api_contracts.py -q -k "daily_runtime or daily_command_center or command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache"`,
  Python ruff OK and Python mypy OK. Live HTTP after stack restart showed first
  process-warm Command Center hit still expensive, but the next Marketing Brief
  derivation reused the command/base path and returned in about 0.35s, with warm
  hits around 0.01s. Next performance bottleneck is deeper in Command Center
  cold build itself: Ads/content/merchant/GA4 diagnostics and metric-store reads.
- Ads operator summary contract, 2026-06-23 00:28 CEST.
  `/api/ads/diagnostics` exposes typed `operator_summary` for Ads Doctor:
  title/summary/next_step, top decision IDs, campaign/search-term counts,
  optimizer ready/blocked counts, allowed metrics, missing read contracts,
  review gates, evidence IDs, ActionObject IDs and blocked claims.
  `AdsDoctorSurface` now renders the API-owned top Ads decisions and safety
  trace instead of sorting Ads decisions and owning operator summary text in
  React. Live proof after `scripts/local_stack.sh restart`:
  `/api/ads/diagnostics` returns `operator_summary.id=ads_operator_summary`,
  `campaign_count=18`, `search_term_count=50`, `ready_area_count=5`,
  `blocked_area_count=3`, `decision_count=14`, `blocker_count=2` and
  `live_data_available=true`. Focused proof:
  `uv run pytest tests/test_api_contracts.py -q -k ads_diagnostics_exposes_live_campaign_metric_facts`,
  Python ruff OK, Python mypy OK, shared schema typecheck OK, dashboard
  typecheck OK, dashboard lint OK, and focused Ads Doctor route test OK.
  Full `scripts/verify.sh` intentionally not run for this narrow contract slice.
- Performance scout, 2026-06-23 00:27 CEST.
  The next real bottleneck is backend cold-build/duplicate daily view-model
  work, not raw React rendering: `/api/dashboard/command-center` warm hits are
  fast, but cold command-center build was measured around 3.3s, with
  `daily_runtime` and `marketing_brief` recomputing overlapping source state.
  Next performance slice should split daily runtime into shared base inputs plus
  separately cached `command_center` and `marketing_brief` derivations, then
  consider route-level code splitting for dashboard app code.
- Localo operator summary contract, 2026-06-23 00:18 CEST.
  `/api/localo/diagnostics` exposes typed `operator_summary` for the marketer
  route: title/summary/next_step, top decision IDs, access status,
  visibility fact count, missing read contracts, evidence IDs, ActionObject IDs
  and blocked claims. `LocaloDiagnosticSurface` now renders this API view-model
  instead of sorting Localo decisions and owning Localo operator summary text in
  React. Live proof after `scripts/local_stack.sh restart`:
  `/api/localo/diagnostics` returns
  `operator_summary.id=localo_operator_summary`, `decision_count=2`,
  `visibility_fact_count=17`, `blocker_count=1`, access ready,
  `act_review_localo_visibility_facts`, and blocked GBP/competitor/local-task
  claims. Focused proof: RED then GREEN
  `uv run pytest tests/test_api_contracts.py -q -k localo_diagnostics_shows_access_ready_without_visibility_claims`,
  `uv run pytest tests/test_api_contracts.py -q -k localo_diagnostics`, ruff
  OK, mypy OK, shared schema typecheck OK, dashboard typecheck OK, dashboard
  lint OK, and focused dashboard route test OK. Full `scripts/verify.sh`
  intentionally not run for this narrow contract slice.
- Ahrefs operator summary contract, 2026-06-23 00:12 CEST.
  `/api/ahrefs/diagnostics` exposes typed `operator_summary` for the marketer
  route: title/summary/next_step, top decision IDs, gap read status,
  authority/gap fact counts, available/missing read contracts, evidence IDs,
  ActionObject IDs and blocked claims. `AhrefsDiagnosticSurface` now renders
  this API view-model instead of sorting Ahrefs decisions and owning operator
  summary text in React. Live proof after `scripts/local_stack.sh restart`:
  `/api/ahrefs/diagnostics` returns
  `operator_summary.id=ahrefs_operator_summary`, `decision_count=2`,
  `blocker_count=2`, `gap_read_status=blocked`, missing Ahrefs gap read
  contracts and blocked gap/traffic/authority claims. Focused proof: RED then
  GREEN `uv run pytest tests/test_api_contracts.py -q -k ahrefs_diagnostics_exposes_authority_context_and_blocks_gap_claims`,
  `uv run pytest tests/test_api_contracts.py -q -k ahrefs_diagnostics`, ruff
  OK, mypy OK, shared schema typecheck OK, dashboard typecheck OK, dashboard
  lint OK, and focused dashboard route test OK. Full `scripts/verify.sh`
  intentionally not run for this narrow contract slice.
- Merchant operator summary contract, 2026-06-23 00:05 CEST.
  `/api/merchant/diagnostics` exposes typed `operator_summary` for the marketer
  route: title/summary/next_step, top decision IDs, top issue cluster IDs, top
  tactical item IDs, reported issue occurrences, issue types, evidence IDs,
  ActionObject IDs and blocked claims. `MerchantDiagnosticSurface` now renders
  this API view-model instead of recomputing top feed decisions, issue cluster
  counts, issue types and blocked claims in React. Live proof after
  `scripts/local_stack.sh restart`: `/api/merchant/diagnostics` returns
  `operator_summary.id=merchant_operator_summary`, `decision_count=8`,
  `issue_cluster_count=11`, `reported_issue_occurrences=1887`,
  `action_ids=["act_review_merchant_feed_issues"]`, and live Merchant issue
  types. Focused proof: RED then GREEN
  `uv run pytest tests/test_api_contracts.py -q -k merchant_diagnostics_exposes_feed_issue_queue`,
  `uv run pytest tests/test_api_contracts.py -q -k merchant_diagnostics`, ruff
  OK, mypy OK, shared schema typecheck OK, dashboard typecheck OK, dashboard
  lint OK, and focused dashboard route test OK. Full `scripts/verify.sh`
  intentionally not run for this narrow contract slice.
- Content operator summary contract, 2026-06-22 23:55 CEST.
  `/api/content/diagnostics` exposes typed `operator_summary` for the marketer
  route: title/summary/next_step, top decision IDs, confirmed/missing WordPress
  counts, decision type labels, source connectors, evidence IDs, ActionObject
  IDs and blocked claims. `ContentDiagnosticSurface` now renders this API
  view-model instead of recomputing top content decisions, WordPress counts,
  decision labels and blocked claims in React. Live proof after
  `scripts/local_stack.sh restart`: `/api/content/diagnostics` returns
  `operator_summary.id=content_operator_summary`, `decision_count=5`,
  `blocker_count=0`, `action_ids=["act_prepare_content_refresh_queue"]`, and
  real top decision IDs for Ahrefs/GSC content work. Focused proof: RED then
  GREEN `uv run pytest tests/test_api_contracts.py -q -k content_diagnostics_exposes_query_page_inventory_queue`,
  `uv run pytest tests/test_api_contracts.py -q -k content_diagnostics`, ruff
  OK, mypy OK, shared schema typecheck OK, dashboard typecheck OK, dashboard
  lint OK, and focused dashboard route test OK. Full `scripts/verify.sh`
  intentionally not run for this narrow contract slice.
- GA4 operator summary contract, 2026-06-22 23:45 CEST.
  `/api/ga4/diagnostics` exposes typed `operator_summary` for the marketer route:
  title/summary/next_step, top decision IDs, measurement issue count,
  WordPress missing count, conversion readiness status, evidence IDs,
  ActionObject IDs and blocked claims. `Ga4DiagnosticSurface` now renders this
  API view-model instead of recomputing top GA4 decisions and counts in React.
  Live proof after `scripts/local_stack.sh restart`: `/api/ga4/diagnostics`
  returns `operator_summary.id=ga4_operator_summary`, `decision_count=6`,
  `blocker_count=1`, `conversion_readiness_status=blocked`, and
  `act_review_ga4_tracking_quality`. Focused proof: RED then GREEN
  `uv run pytest tests/test_api_contracts.py -q -k ga4_diagnostics_exposes_landing_quality_contract`,
  `uv run pytest tests/test_api_contracts.py -q -k ga4`, ruff OK, mypy OK,
  shared schema typecheck OK, dashboard typecheck OK, dashboard lint OK, and
  focused dashboard route test OK. Full `scripts/verify.sh` intentionally not
  run for this narrow contract slice.
- Dashboard Ads Doctor extraction, 2026-06-22 23:30 CEST.
  Entire Ads Doctor route surface, Ads operator summary, campaign/KPI/budget/
  recommendation/search-term/negative-keyword panels, Ads labels and Ads
  format helpers were extracted from `App.tsx` into `AdsDoctorSurface.tsx`.
  `App.tsx` is now a route-composition file instead of a dashboard monolith.
  Current line-counts: `App.tsx=211`, `AdsDoctorSurface.tsx=2294`.
  Focused proof: dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "ads doctor route"` OK: 1/1 and
  focused
  `vitest run src/routes/App.test.tsx -t "custom segments route renders dedicated review-only contract"`
  OK: 1/1. Post-push dashboard route-shell proof:
  `pnpm --filter @wilq/dashboard test -- --run App.test.tsx` OK: 17 tests in
  4 route test files.
- Dashboard Custom Segments route extraction, 2026-06-22 23:28 CEST.
  `CustomSegmentsDiagnosticSurface`, custom segment candidates panel and
  audience forecast panel were extracted from `App.tsx` into
  `CustomSegmentsDiagnosticSurface.tsx`. `/ads-doctor/custom-segments` still
  reads `/api/ads/diagnostics`, while the main Ads Doctor keeps reusing the
  exported panels for evidence/proof. Current line-counts: `App.tsx=2507`,
  `CustomSegmentsDiagnosticSurface.tsx=433`. Focused proof: dashboard lint OK,
  dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "custom segments route renders dedicated review-only contract"`
  OK: 1/1 and focused
  `vitest run src/routes/App.test.tsx -t "ads doctor route"` OK: 1/1.
- Dashboard GA4 route extraction, 2026-06-22 23:23 CEST.
  `Ga4DiagnosticSurface`, GA4 operator summary, tracking review preview,
  proof panel, WordPress match labels and GA4 label helpers were extracted
  from `App.tsx` into `Ga4DiagnosticSurface.tsx`. `/ga4` still reads
  `/api/ga4/diagnostics` plus `/api/actions`, preserves conversion/key-event
  blockers, and keeps the same review-only ActionObject focus. Current
  line-counts: `App.tsx=2888`, `Ga4DiagnosticSurface.tsx=581`. Focused proof:
  dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "ga4 and gsc routes render workflow-specific brief focus"`
  OK: 1/1.
- Dashboard Demand Gen route extraction, 2026-06-22 23:20 CEST.
  `DemandGenDiagnosticSurface`, readiness contract view, review-only payload
  preview, landing quality/migration rows and Demand Gen label helpers were
  extracted from `App.tsx` into `DemandGenDiagnosticSurface.tsx`.
  `/ads-doctor/demand-gen` still reads `/api/demand-gen/diagnostics` and still
  blocks launch/migration/performance claims without real Demand Gen evidence.
  Current line-counts: `App.tsx=3454`, `DemandGenDiagnosticSurface.tsx=361`.
  Focused proof: dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "demand gen route renders readiness contract instead of generic registry"`
  OK: 1/1.
- Dashboard Localo route extraction, 2026-06-22 23:17 CEST.
  `LocaloDiagnosticSurface`, Localo operator summary, safety gate, proof panel
  and Localo label helpers were extracted from `App.tsx` into
  `LocaloDiagnosticSurface.tsx`. `/localo` still reads
  `/api/localo/diagnostics`, preserves the current rule that MCP access is not
  ranking/GBP evidence, and no longer keeps Localo presentation in the route
  monolith. Current line-counts: `App.tsx=3782`,
  `LocaloDiagnosticSurface.tsx=349`. Focused proof: dashboard lint OK,
  dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "localo social and content routes render workflow-specific blockers or focus"`
  OK: 1/1.
- Dashboard Ahrefs route extraction, 2026-06-22 23:15 CEST.
  `AhrefsDiagnosticSurface`, Ahrefs operator summary, gap contract panel,
  proof panel and Ahrefs label helpers were extracted from `App.tsx` into
  `AhrefsDiagnosticSurface.tsx`. `/ahrefs` still reads
  `/api/ahrefs/diagnostics`, but Ahrefs-specific authority/gap presentation no
  longer lives in the route monolith. Current line-counts: `App.tsx=4120`,
  `AhrefsDiagnosticSurface.tsx=353`. Focused proof: dashboard lint OK,
  dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "ahrefs route renders authority context and typed gap records"`
  OK: 1/1.
- Dashboard content diagnostics extraction, 2026-06-22 23:13 CEST.
  `ContentDiagnosticSurface`, content operator summary, content brief preview,
  WordPress draft payload preview, content decision cards, proof panel and
  content label helpers were extracted from `App.tsx` into
  `ContentDiagnosticSurface.tsx`. `/seo-gsc` and `/content-planner` still use
  the same WILQ API route behavior, but content-specific diagnostics and review
  UI no longer live in the route monolith. Current line-counts:
  `App.tsx=4461`, `ContentDiagnosticSurface.tsx=821`. Focused proof:
  dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "ga4 and gsc routes render workflow-specific brief focus"`
  OK: 1/1 and focused
  `vitest run src/routes/App.test.tsx -t "localo social and content routes render workflow-specific blockers or focus"`
  OK: 1/1.
- Dashboard Merchant route extraction, 2026-06-22 23:05 CEST.
  `MerchantDiagnosticSurface`, operator summary, decision cards, proof panel
  and Merchant label helpers were extracted from `App.tsx` into
  `MerchantDiagnosticSurface.tsx`. The route still reads
  `/api/merchant/diagnostics` and `/api/actions`, but Merchant-specific
  presentation no longer lives in the route monolith. Current line-counts:
  `App.tsx=5247`, `MerchantDiagnosticSurface.tsx=479`. Focused proof:
  dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx -t "merchant route renders dedicated feed diagnostics"`
  OK: 1/1.
- Dashboard brief workflow extraction, 2026-06-22 22:59 CEST.
  `BriefWorkflowSurface`, `MarketingBriefCard`, `briefSurfaceConfigs` and
  brief-surface matching were extracted from `App.tsx` into
  `BriefWorkflowSurface.tsx`. This moves generic fallback workflow views for
  settings/social/SEO/brief routes out of the route monolith while preserving
  the same WILQ API reads and ActionObject focus. Current line-counts:
  `App.tsx=5707`, `BriefWorkflowSurface.tsx=294`. Focused proof: dashboard
  lint OK, dashboard typecheck OK, focused `vitest run src/routes/App.test.tsx`
  OK: 14/14.
- Dashboard tactical queue extraction, 2026-06-22 22:52 CEST.
  `TacticalQueuePanel`, tactical grouping, labels, context chips and shared
  `shortPath` helper were extracted from `App.tsx` into
  `TacticalQueuePanel.tsx`. Merchant and content surfaces now import the same
  helpers instead of keeping tactical presentation logic in the route monolith.
  Current line-counts: `App.tsx=5985`, `TacticalQueuePanel.tsx=350`. Focused
  proof: dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx` OK: 14/14.
- Dashboard operating route surfaces extraction, 2026-06-22 22:45 CEST.
  Top-level `/opportunities`, `/actions` and `/workflows` route surfaces were
  extracted from `App.tsx` into `OperatingRouteSurfaces.tsx`. This keeps route
  registration in `App.tsx` but moves registry-route data loading and
  presentation to a dedicated file. Current line-counts: `App.tsx=6319`,
  `OperatingRouteSurfaces.tsx=218`. Focused proof: dashboard lint OK,
  dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx src/routes/OpportunitiesRoute.test.tsx`
  OK: 15/15.
- Dashboard generic surface extraction, 2026-06-22 22:40 CEST.
  `GenericSurface` and route-expert-domain mapping were extracted from
  `App.tsx` into `GenericSurface.tsx`. This moves broad fallback/knowledge
  registry queries out of the route monolith while preserving route behavior.
  Current line-counts: `App.tsx=6524`, `GenericSurface.tsx=229`. Focused proof:
  dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx` OK: 14/14.
- Dashboard detail panels extraction, 2026-06-22 22:34 CEST.
  `ActionDetailSurface`, `EvidenceDetailSurface`, `OpportunityDetailSurface`
  and their detail renderers were extracted from `App.tsx` into
  `DetailPanels.tsx`. Routing remains in `App.tsx`, so workflow detail fallback
  and route registration are unchanged. The `/opportunities` route test was
  also split out of `App.test.tsx` into `OpportunitiesRoute.test.tsx`. Current
  line-counts: `App.tsx=6723`, `DetailPanels.tsx=177`. Focused proof:
  dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/ActionDetailRoute.test.tsx
  src/routes/OpportunitiesRoute.test.tsx` OK: 2/2.
- Dashboard registry panels extraction, 2026-06-22 22:27 CEST.
  `ConnectorGrid`, `OpportunityList`, `EvidenceList`, `ConnectorRefreshRunList`,
  `ActionList` and `ExpertRuleList` were extracted from `App.tsx` into
  `RegistryPanels.tsx`. Behavior remains the same; this removes generic
  registry presentation from the route monolith. Current line-counts:
  `App.tsx=6867`, `RegistryPanels.tsx=219`. Focused proof: dashboard lint OK,
  dashboard typecheck OK.
- Dashboard hotspot batch, 2026-06-22 22:22 CEST.
  Zasady prędkości zostały dopisane do `docs/goals/001-goal.md`: verification
  budget zamiast test-loopów, full `scripts/verify.sh` tylko na realnych gate'ach
  oraz subagenty do równoległego developmentu, nie tylko audytu. W batchu:
  `ActionObjectPanels.tsx` wyciągnięty z `App.tsx`, `KnowledgePanels.tsx`
  wyciągnięty z `App.tsx`, a test action detail route przeniesiony do
  `ActionDetailRoute.test.tsx` przez subagenta i poprawiony pod aktualny
  `review_gate` schema. Aktualne line-counts: `App.tsx=7073`,
  `App.test.tsx=6140`, `ActionDetailRoute.test.tsx=114`,
  `KnowledgePanels.tsx=116`, `ActionObjectPanels.tsx=604`. Focused proof:
  dashboard lint OK, dashboard typecheck OK, focused
  `vitest run src/routes/App.test.tsx src/routes/ActionDetailRoute.test.tsx`
  OK: 16/16.
- Dashboard ActionObject panel extraction, 2026-06-22 22:13 CEST.
  `ActionObjectFocus`, `ActionObjectIdFocus`, review gate, preview, human
  review, validation, confirmation and impact-check controls were extracted
  from `apps/dashboard/src/routes/App.tsx` into
  `apps/dashboard/src/routes/ActionObjectPanels.tsx`. Shared Ads missing/blocked
  claim labels moved into `marketingLabels.ts`. This is a behavior-preserving
  code-quality slice: `App.tsx=7180` lines,
  `ActionObjectPanels.tsx=604`, `marketingLabels.ts=150`. Focused proof:
  dashboard lint OK, dashboard typecheck OK, dashboard unit tests 17/17 OK.
  Full `scripts/verify.sh` also completed green before this note was written:
  backend 154/154, dashboard unit 17/17, Playwright 14/14 and dashboard
  production build. Process correction from the user is now recorded in
  `docs/goals/001-goal.md`: use a verification budget, batch small safe
  refactors, run full verify only at real gates, and use subagents for parallel
  development, not only audits.
- Ads change history contract extraction, 2026-06-22 21:24 CEST.
  `build_change_history_read_contract` i helpery change-event rows zostały
  przeniesione z `wilq/briefing/ads_diagnostics.py` do
  `wilq/briefing/ads_change_history.py`. Publiczny `/api/ads/diagnostics`
  pozostaje bez zmiany; `ads_diagnostics.py` nadal renderuje sekcję
  `Historia zmian Google Ads`, enrichuje ActionObject IDs i składa
  change-impact readiness. File-size proof: `ads_diagnostics.py=5876` linii,
  `ads_change_history.py=195`. Proof: ruff OK, mypy OK,
  `tests/test_api_contracts.py` OK, focused Playwright reruns dla action detail
  i workflows OK po ujednoliceniu route heading timeout helpera, a pełne
  `scripts/verify.sh` przeszło zielono: backend 154/154, dashboard unit 17/17,
  Playwright 14/14 i dashboard production build.
- Ads impression share contract extraction, 2026-06-22 21:05 CEST.
  `build_impression_share_read_contract` i helpery impression-share rows
  zostały przeniesione z `wilq/briefing/ads_diagnostics.py` do
  `wilq/briefing/ads_impression_share.py`. Publiczny `/api/ads/diagnostics`
  pozostaje bez zmiany; `ads_diagnostics.py` nadal renderuje sekcję
  `Udział w wyświetleniach Google Ads` i składa campaign triage/optimizer.
  File-size proof: `ads_diagnostics.py=6029` linii,
  `ads_impression_share.py=188`. Wąskie proofy: ruff OK, mypy OK,
  `tests/test_api_contracts.py` OK. Finalny proof: focused Playwright action
  detail rerun OK po jednorazowym route-load failure, potem `scripts/verify.sh`
  OK, including backend API contracts 154/154, dashboard unit tests 17/17,
  Playwright 14/14 and dashboard production build.
- Ads recommendations contract extraction, 2026-06-22 20:45 CEST.
  `build_recommendations_read_contract` i helpery recommendation rows,
  impact/apply-preview oraz review scoring zostały przeniesione z
  `wilq/briefing/ads_diagnostics.py` do
  `wilq/briefing/ads_recommendations.py`. Publiczny `/api/ads/diagnostics`
  pozostaje bez zmiany; `ads_diagnostics.py` nadal renderuje sekcję
  `Rekomendacje Google Ads do review` i składa całość odpowiedzi. File-size
  proof: `ads_diagnostics.py=6179` linii, `ads_recommendations.py=506`.
  Wąskie proofy: ruff OK, mypy OK, `tests/test_api_contracts.py` OK.
  Finalny proof: `scripts/verify.sh` OK, including backend API contracts
  154/154, dashboard unit tests 17/17, Playwright 14/14 and dashboard
  production build.
- Ads budget pacing contract extraction, 2026-06-22 20:22 CEST.
  `build_budget_pacing_read_contract` i helpery budget/shared-budget/apply-preview
  zostały przeniesione z dużego `wilq/briefing/ads_diagnostics.py` do
  `wilq/briefing/ads_budget_pacing.py`. Publiczny `/api/ads/diagnostics`
  pozostaje bez zmiany; `ads_diagnostics.py` tylko składa kontrakty i dalej
  renderuje sekcje diagnostyczne. File-size proof: `ads_diagnostics.py=6590`
  linii, `ads_budget_pacing.py=400`. Wąskie proofy: ruff OK, mypy OK,
  `tests/test_api_contracts.py` OK. Finalny proof: `scripts/verify.sh` OK,
  including backend API contracts 154/154, dashboard unit tests 17/17,
  Playwright 14/14 and dashboard production build. Focused Playwright
  `custom segments route exposes review-only segment candidates` został
  powtórzony po sprzątnięciu nakładających się runnerów i przeszedł; wcześniejszy
  failure był startup/process contention, nie regresją route.
- Dashboard workflows panel extraction, 2026-06-22 19:38 CEST.
  Route-specific panele `WorkflowRunList` i `WorkflowRegistryList` zostały
  przeniesione z `apps/dashboard/src/routes/App.tsx` do
  `apps/dashboard/src/routes/WorkflowPanels.tsx`. `WorkflowsSurface` nadal
  zostaje w `App.tsx`, więc routing i pobieranie danych są bez zmian; to mały
  krok utrzymaniowy po granicy "workflow presentation panels". File-size proof:
  `App.tsx=7824` linii, `WorkflowPanels.tsx=92`. Wąskie proofy: dashboard lint
  OK, dashboard typecheck OK, dashboard unit tests 17/17 OK. Finalny proof:
  `scripts/verify.sh` OK, including backend API contracts 154/154, dashboard
  unit tests 17/17, Playwright 14/14 and dashboard production build.
- Dashboard Command Center route test split, 2026-06-22 19:21 CEST.
  Pierwszy route-focused test został wyjęty z monolitycznego
  `apps/dashboard/src/routes/App.test.tsx` do
  `apps/dashboard/src/routes/CommandCenterRoute.test.tsx`. Test sprawdza ten
  sam kontrakt first-screen Command Center: polski cockpit decyzji, prompt do
  Codex, brak raw `ev_*`/`act_*`, tłumaczone blocked claims i link do
  ustawień. File-size proof: `App.test.tsx=6149` linii,
  `CommandCenterRoute.test.tsx=150`; `App.test.tsx` ma teraz 16 testów, nowy
  route test 1, razem dashboard unit coverage nadal 17 testów. Finalny proof:
  `scripts/verify.sh` OK, including backend API contracts 154/154, dashboard
  unit tests 17/17 split across 2 files, Playwright 14/14 and dashboard
  production build.
- Dashboard Command Center route extraction, 2026-06-22 18:56 CEST.
  `CommandCenter` został przeniesiony z dużego
  `apps/dashboard/src/routes/App.tsx` do
  `apps/dashboard/src/routes/CommandCenterRoute.tsx`, a współdzielone etykiety
  priorytetów i blocked claims do
  `apps/dashboard/src/routes/marketingLabels.ts`. Zachowanie renderingu ma
  pozostać bez zmian: to jest pierwszy mały slice redukcji ryzyka kodowego, nie
  nowy UX. File-size proof po ekstrakcji: `App.tsx=7911` linii,
  `CommandCenterRoute.tsx=225`, `marketingLabels.ts=72`. Wąskie proofy:
  dashboard lint OK, dashboard typecheck OK, `App.test.tsx` 17/17 OK. Finalny
  proof: `scripts/verify.sh` OK, including backend API contracts 154/154,
  dashboard unit tests 17/17, Playwright 14/14 and dashboard production build.
- Tactical queue performance cache, 2026-06-22 18:48 CEST.
  `/api/marketing/tactical-queue` był największym mierzalnym nie-debug
  bottleneckiem po odchudzeniu Command Center: przed zmianą median HTTP wynosił
  około `1.198s` przy payloadzie `35262 B`. Dodano krótki TTL cache
  `WILQ_TACTICAL_QUEUE_CACHE_SECONDS` z domyślnym `30s`, wyłączany w pytestach,
  oraz wspólną invalidację `clear_api_view_model_caches()` po connector refresh
  i ActionObject validate/review/preview/confirm/impact/apply paths. Live proof
  po `scripts/local_stack.sh restart`: `/api/marketing/tactical-queue` median
  `0.006s`, payload `35262 B`; Command Center warm median `0.007s`, daily
  context-pack warm median `0.152s`, full debug context nadal ciężki
  `~6.263s` / `~6.19 MB` i pozostaje debug path. Agent-browser proof otworzył
  `http://127.0.0.1:5173/command-center` i zobaczył decyzje Merchant, Content,
  GA4 oraz Ads. Proofy: ruff OK, mypy OK, focused backend tests OK, dashboard
  route tests 17/17 OK, Playwright 14/14 OK, `scripts/verify.sh` OK with
  backend API contracts 154/154.
- Command Center daily focus + daily context-pack budget, 2026-06-22 17:52 CEST.
  `daily_decisions` na `/api/dashboard/command-center` są teraz ograniczone do
  core decyzji dnia: Merchant feed issues, Content SEO queue, GA4
  pomiar/jakość ruchu i Ads review queues. Localo nadal zostaje w
  `operator_brief`, `action_plan` i źródłach, ale nie jest promowane jako
  primary "co zrobić teraz", dopóki nie ma pełniejszego GBP/competitor/local
  task parity. `wilq-daily-command` smoke failuje, jeśli Localo przecieknie do
  `daily_decisions` albo jeśli live daily context-pack przekroczy 180 KB. Live
  proof po `scripts/local_stack.sh restart`: 4 decyzje
  (`decision_review_merchant_feed_issues`,
  `decision_prepare_content_refresh_queue`,
  `decision_review_ga4_landing_quality`,
  `decision_review_ads_campaign_metrics`) i context-pack 174219 B po kompakcji
  ActionObject review gates, refresh runs, evidence summaries i opportunity
  summaries. Regression fix: `/api/opportunities` nie jest już pochodną
  odchudzonego `daily_decisions`, tylko pełniejszego `action_plan`, więc
  registry nadal pokazuje Localo opportunity
  `opp_decision_review_localo_visibility_facts`, mimo że Localo nie jest
  primary daily card. Proofy: ruff OK, mypy OK, API contracts 153/153 OK,
  dashboard route tests 17/17 OK, daily skill smoke OK, Playwright 14/14 OK,
  `scripts/verify.sh` OK.
- Ads strategy review readiness, 2026-06-22 17:25 CEST.
  `/api/ads/diagnostics.business_context_read_contract` ma teraz nested typed
  `strategy_review_readiness_contract`, który pokazuje, czy human Ads strategy
  review jest zatwierdzone do prepare. Live Ekologus state jest celowo
  zablokowany: profit margin, business goal i budget goal są obecne, ale
  `target_roas_or_cpa` i `human_strategy_review` nadal brakują. Kontrakt ma
  `status=blocked`, `latest_review_status=missing`,
  `action_ids=[act_record_ads_strategy_review]`, `apply_allowed=false` i
  blokuje profitability verdict, target KPI verdict, budget scaling, budget
  apply, recommendation apply oraz automatic optimization. Ads Doctor renderuje
  panel `Gotowość strategy review Ads`; scoped `wilq-ads-doctor` context-pack
  zawiera tę samą bramkę. Context-pack kompresuje teraz także generic
  ActionObject `review_gate`; live smoke ma `context_pack_bytes=192530`, poniżej
  limitu 200 KB. Wąskie proofy: ruff OK, mypy OK, API tests 3/3 OK, dashboard
  route tests 17/17 OK, Ads skill smoke OK. Final proof: `scripts/verify.sh`
  green, including 153 backend tests, 17 dashboard unit tests, Skill/API smokes,
  14 Playwright e2e tests and dashboard production build.
- Ads change-impact readiness contract, 2026-06-22 16:51 CEST.
  `/api/ads/diagnostics` ma teraz typed
  `change_impact_readiness_contract`, który siedzi między surowym
  `change_history_read_contract` a optimizer item
  `change_history_impact_review`. Kontrakt pokazuje, czy są change-event rows,
  czy da się dopasować bieżący snapshot kampanii, jakie metryki wolno pokazać
  i czego brakuje do oceny wpływu zmian. Apply, impact, performance uplift,
  budget scaling i campaign mutation pozostają zablokowane. Fixture testowa
  pokrywa ścieżkę z change row + snapshotem kampanii, ale bez pre/post windows;
  live Ekologus proof po `scripts/local_stack.sh restart` pokazuje obecnie
  `status=blocked`, `readiness_rows=0`, `missing_read_contracts` zawiera
  `change_event_rows`, `pre_change_performance_window`,
  `post_change_performance_window`, `human_change_impact_review` i
  `apply_preview`. Ads Doctor renderuje panel `Gotowość impact review zmian`,
  a `wilq-ads-doctor` smoke wymusza obecność kontraktu w endpointzie i scoped
  context-packu. Wąskie proofy: ruff OK, mypy OK, API tests 2/2 OK,
  dashboard route tests 17/17 OK, Ads skill smoke OK.
- Ads optimizer readiness, context-pack/action performance i Command Center
  marketer cleanup, 2026-06-22 16:34 CEST. `/api/ads/diagnostics` ma teraz
  typed `optimizer_readiness_contract`, który rozdziela obszary gotowe do
  review od blokad apply/change impact. Kontrakt jest obecny w shared schema,
  dashboardzie `/ads-doctor`, scoped `wilq-ads-doctor` context-packu i smoke
  skilla; apply pozostaje zablokowany. `POST /api/codex/context-pack` dla Ads
  ma dodatkową kompakcję optimizer readiness i decision queue, a detail route
  ActionObject używa `GET /api/actions/{action_id}` zamiast pobierać całe
  `/api/actions`. `/content-planner` nie blokuje już całej strony na pełnym
  `/api/actions`; pokazuje shell ActionObject IDs i dogrywa detale później.
  Command Center first screen ukrywa surowe `ev_*`, `act_*`, `Skill:
  wilq-*` i `Context-pack: /api/codex/context-pack`; pokazuje polskie statusy,
  ludzkie nazwy źródeł, podsumowanie dowodów i liczbę bezpiecznych akcji do
  walidacji. Browser proof na `http://127.0.0.1:5173/command-center` pokazuje
  5 decyzji, 1 blocker, 7 źródeł, bez raw trace IDs na pierwszym ekranie.
  Final proof: `scripts/verify.sh` green, including 153 backend tests, 17
  dashboard unit tests, Skill/API smokes, 14 Playwright e2e tests and
  dashboard production build.
- Dashboard detail route performance/stability, 2026-06-22 11:55 CEST.
  Root cause dwóch późnych failures w `scripts/verify.sh`: detail route dla
  evidence czekał na pełne `/api/evidence` registry (~1.7 MB, ~17 s), a detail
  ActionObject czekał na niepotrzebne registry i renderował całą narastającą
  historię audytu. Dashboard ma teraz single-item
  `GET /api/evidence/{evidence_id}` client path, osobne detail surfaces dla
  evidence/actions/opportunities i limit najnowszych audit events w detalu
  ActionObject. Targeted Playwright:
  `action detail route shows validation, evidence and payload preview` oraz
  `merchant route renders live Merchant Diagnostics evidence links` passed.
  Final proof: `scripts/verify.sh` green, including 153 backend tests, 17
  dashboard unit tests, Skill/API smokes, 14 Playwright e2e tests and
  dashboard production build.
- Ads campaign triage contract, 2026-06-22 10:22 CEST.
  `/api/ads/diagnostics` ma teraz typed `campaign_triage_read_contract`,
  który łączy campaign activity, derived KPI, budget pacing, recommendations,
  impression share i business-context gaps w jedną kolejkę review kampanii.
  To jest kolejność sprawdzania, nie werdykt waste/profitability/CPA/ROAS ani
  apply. RED/GREEN proof:
  `test_ads_diagnostics_exposes_live_campaign_metric_facts` i
  `test_codex_context_pack_scopes_ads_doctor_payload` najpierw failowały na
  braku `campaign_triage_read_contract`, potem przeszły. Live proof po
  `scripts/local_stack.sh restart`: `triage_status=ready`, `triage_rows=18`,
  top kampania `(2026) Ekologus Ogólna`, `review_priority=pilne`,
  `review_score=90`, `clicks=93`, `cost_micros=60694109`, `roas=0`,
  `spend_to_budget_ratio_7d=0.867059`, ActionObject
  `act_prepare_ads_campaign_review_queue`, blocked claims:
  `wasted budget`, `profitability`, `budget scaling`, `budget apply`,
  `recommendation apply`, `campaign mutation`. Scoped
  `wilq-ads-doctor` context-pack niesie ten sam kontrakt z compaction
  `campaign_triage_rows_total=18`, `campaign_triage_rows_included=2`; smoke
  skilla passed z `context_pack_bytes=197058`.
- Content review -> Codex context-pack draft preview, 2026-06-22 09:58 CEST.
  Po zapisanym review kandydata content briefu scoped
  `POST /api/codex/context-pack {"skill":"wilq-content-strategist"}` ma teraz
  jawny, kompaktowany `wordpress_draft_payload_preview`: licznik
  `wordpress_draft_payload_preview_total`, licznik included i zwięzły draft
  preview z `candidate_id`, `post_status=draft`, evidence IDs, blocked claims
  oraz `apply_allowed=false` / `api_mutation_ready=false`. To spina wybór
  operatora w dashboardzie z tym, co widzi Codex skill, bez pełnego WordPress
  payload dumpu i bez publikacji. RED/GREEN proof:
  `test_content_strategist_context_pack_preserves_reviewed_draft_preview`
  failował na braku `wordpress_draft_payload_preview_total`, a po kompakcji
  przechodzi. Live proof po `scripts/local_stack.sh restart`: po review
  `content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca`, context-pack zwraca
  `draft_total=1`, `draft_included=1`, `post_status=draft`,
  `apply_allowed=false`, `api_mutation_ready=false` i evidence
  `ev_refresh_refresh_google_search_console_554550c44ec7`. Wąskie checks:
  ruff OK, mypy OK, content/action/context-pack API tests 6/6 OK. Verification
  follow-up: Playwright route smoke had a loading-state race under heavy
  API-backed routes. E2E now waits for `Ładowanie stanu WILQ API` to disappear
  before first route heading assertions and Playwright is configured for one
  worker, matching `scripts/verify.sh`. Final proof: `scripts/verify.sh` green,
  including 153 backend tests, 17 dashboard unit tests, Skill/API smokes,
  14 Playwright e2e tests and dashboard production build.
- Content brief homepage candidate ID traceability, 2026-06-22 08:41 CEST.
  Live ActionObject preview miał regresję jakościową:
  `target_url=https://www.ekologus.pl/` dostawał `candidate_id=content_brief_gsc_`,
  bo generator slugował root path `/` zamiast hosta. To psuło późniejsze
  review/audit i mogło powodować nieczytelne albo kolidujące wybory operatora.
  RED/GREEN proof:
  `test_content_brief_preview_homepage_candidate_id_is_traceable` najpierw
  failował na `content_brief_gsc_`, a po poprawce generatora przechodzi z
  `content_brief_gsc_www_ekologus_pl`. Live proof po
  `scripts/local_stack.sh restart`: `/api/actions/act_prepare_content_refresh_queue`
  zwraca `preview_count=8`, homepage preview z
  `candidate_id=content_brief_gsc_www_ekologus_pl`, topic `ekologus`,
  `apply_allowed=false`, `api_mutation_ready=false` i evidence
  `ev_refresh_refresh_google_search_console_554550c44ec7`. Wąskie checks:
  ruff OK, mypy OK, content/action API tests 4/4 OK. Final proof:
  `scripts/verify.sh` green, including 152 backend tests, 17 dashboard unit
  tests, Skill/API smokes, 14 Playwright e2e tests and dashboard production
  build.
- Ads knowledge/rule lineage eval, 2026-06-22 06:02 CEST. Goal 001 requires a
  source-backed chain, not a prompt-only skill. Scoped
  `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}` now has an
  explicit guard in API tests and in
  `.agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`: every
  decision-level `knowledge_card_ids` and `expert_rule_ids` referenced by
  `ads_diagnostics.decision_queue` must be present in
  `knowledge_card_summaries` and `expert_rule_summaries`. Live context proof:
  `knowledge_card_summaries=7`, `expert_rule_summaries=8`. Non-interactive
  eval passed:
  `.local-lab/evals/codex-skill/20260622T040032Z/wilq-ads-doctor/result.json`
  with `language=pl-PL`, `api_used=true`, source `google_ads`, Google Ads
  evidence IDs, seven knowledge cards, eight expert rules, four review
  ActionObject candidates and `operator_usefulness_score=5`. Apply/waste/CPA/
  ROAS/budget scaling claims remain blocked.
- Content ActionObject preview preserves decision evidence, 2026-06-22
  05:54 CEST. Root cause: `/api/content/diagnostics` could still build
  GSC/WordPress decisions, but `act_prepare_content_refresh_queue` used a
  lower per-connector metric fact limit, so newer aggregate/noisy GSC facts
  could push older dimensioned `query/page` and WordPress inventory facts out
  of the ActionObject preview. RED/GREEN proof:
  `test_content_action_preview_keeps_dimensioned_decisions_after_newer_aggregate_runs`
  first failed with empty `content_brief_preview`, then passed after raising
  content ActionObject limits for `google_search_console`,
  `wordpress_ekologus` and `ahrefs`. Live proof after
  `scripts/local_stack.sh restart`: `/api/content/diagnostics` returns
  `decision_count=5`, first decision
  `SEO: odśwież lub scal "zielony ład co to" (7 zapytań)`;
  `/api/actions/act_prepare_content_refresh_queue` returns
  `content_preview_count=8`, first preview
  `content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca`,
  `mode=refresh`, `topic=bdo co to`, `apply_allowed=false`,
  `api_mutation_ready=false`; scoped
  `POST /api/codex/context-pack {"skill":"wilq-content-strategist"}` returns
  `bytes=137994`, active actions `act_review_ga4_tracking_quality` and
  `act_prepare_content_refresh_queue`, `content_preview_count=4` and
  `content_decisions=5`. `wilq-content-strategist` smoke now requires the
  content ActionObject preview when live content decisions exist, while still
  accepting an empty clean runtime with no live decisions. Final proof:
  `scripts/verify.sh` green, including 151 backend tests, 17 dashboard unit
  tests, Skill API smoke, 14 Playwright e2e tests and dashboard production
  build.
- Custom segments apply/audit safety contract, 2026-06-22 04:55 CEST.
  `AdsCustomSegmentPayloadPreview` ma teraz typed
  `safety_review.safety_contract=custom_segment_apply_safety_v1`. Apply
  pozostaje zablokowany (`apply_allowed=false`, `api_mutation_ready=false`,
  `destructive=false`), a safety review jawnie wymaga
  `forecast_or_audience_size`, `keyword_planner_enrichment`,
  `google_ads_mutation_audit` i `human_confirm_before_apply`.
  RED/GREEN proof: `test_ads_diagnostics_exposes_live_campaign_metric_facts`
  najpierw failował na `KeyError: safety_review`, a
  `test_codex_context_pack_scopes_custom_segments_payload` failował, bo
  scoped `wilq-custom-segments` context-pack gubił safety review w compaction;
  oba testy przechodzą po dodaniu kontraktu. Live proof po
  `scripts/local_stack.sh restart`: `/api/ads/diagnostics` i
  `POST /api/codex/context-pack {"skill":"wilq-custom-segments"}` pokazują ten
  sam `custom_segment_apply_safety_v1`, `audit_required=true`,
  `custom_segment_payload_preview_included=1`, ActionObject
  `act_prepare_custom_segments_from_search_terms` i forecast blocker. Smoke
  `.agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py` passed.
  Final proof: `scripts/verify.sh` green, w tym 150 backend tests, 17
  dashboard unit tests, Skill API smoke, 14 Playwright e2e tests i dashboard
  production build.
- Ads search-term review summary contract, 2026-06-22 04:28 CEST.
  `/api/ads/diagnostics` ma teraz typed
  `search_term_review_summary_contract`, który agreguje live search-term rows
  do kolejki ręcznego review bez claimów o waste, CPA, ROAS ani apply
  wykluczeń. RED/GREEN proof:
  `tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts`
  najpierw failował na `KeyError: search_term_review_summary_contract`, potem
  przeszedł po dodaniu kontraktu. Live proof po `scripts/local_stack.sh
  restart`: `status=ready`, `total_search_term_count=50`,
  `zero_conversion_search_term_count=50`, `total_clicks=7`,
  `total_impressions=70`, `total_cost_micros=45969902`,
  `campaign_review_rows=1`, top kosztowe zapytania zaczynają się od
  `asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a`,
  `alba czeladź`, `darmowy odbiór elektrośmieci`. Blocked claims pozostają:
  `search-term waste`, `negative keyword apply`, `CPA`, `ROAS`.
  `POST /api/codex/context-pack` dla `wilq-ads-doctor` niesie ten sam
  kontrakt, a smoke skilla przeszedł z `context_pack_bytes=195569`, czyli
  poniżej limitu 200 KB. Dashboard `/ads-doctor` pokazuje panel
  `Kolejność review zapytań` przed surową tabelą search terms. Wąskie proofy:
  ruff OK, mypy OK, dashboard unit tests 17/17 OK.
- GA4 conversion/key-event readiness contract, 2026-06-22 04:01 CEST.
  `/api/ga4/diagnostics` ma teraz typed
  `conversion_readiness_contract`, który rozdziela gotowość review jakości
  ruchu od gotowości do claimów o konwersjach, ROAS, revenue i profitability.
  RED/GREEN proof:
  `tests/test_api_contracts.py::test_ga4_diagnostics_exposes_landing_quality_contract`
  najpierw failował na braku `conversion_readiness_contract`, potem przeszedł
  po dodaniu kontraktu. Live proof po `scripts/local_stack.sh restart`:
  `live_data_available=true`, `landing_group_count=10`, `blocker_count=1`,
  `conversion_readiness_contract.status=blocked`,
  `missing_read_contracts=[conversion_or_key_event_mapping]`,
  `conversion_like_metric_count=0`, `dimensioned_behavior_metric_count=50` i
  ActionObject `act_review_ga4_tracking_quality`. `POST /api/codex/context-pack`
  dla `wilq-ga4-analyst` zwraca ten sam kontrakt, a smoke
  `.agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py` passed.
  Dashboard `/ga4` pokazuje polski blocker `mapowanie konwersji / key events`
  w panelu bezpiecznej analityki. Final proof: `scripts/verify.sh` green, w
  tym 150 backend tests, 17 dashboard unit tests, Skill API smoke,
  14 Playwright e2e tests i dashboard production build.
- Ads n-gram review missing-contract precision, 2026-06-22 03:38 CEST.
  N-gramy search terms mają teraz własny blocker
  `ngram_to_negative_keyword_payload_preview`, zamiast mylącego generycznego
  `negative_keyword_payload_preview`. To utrzymuje rozdział między review
  powtarzających się tematów zapytań a właściwą kolejką negative keywords.
  RED/GREEN proof:
  `tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts`
  najpierw failował na starym `negative_keyword_payload_preview`, potem
  przeszedł po zmianie API contract. Live proof po `scripts/local_stack.sh
  restart`: `/api/ads/diagnostics.search_term_ngram_read_contract` i decyzja
  `ads_review_search_term_ngrams` pokazują missing contracts
  `[human_intent_review, ngram_to_negative_keyword_payload_preview]`, a
  `negative_keywords_read_contract.missing_read_contracts=[]`. Dashboard ma
  polską etykietę `podgląd payloadu wykluczeń z n-gramów`, a smoke
  `wilq-ads-doctor` failuje, jeśli n-gram contract wróci do generycznego
  negative-keyword preview. Final proof: `scripts/verify.sh` green, w tym
  150 backend tests, 17 dashboard unit tests, Skill API smoke,
  14 Playwright e2e tests i dashboard production build.
- Ads Doctor ActionObject scope compaction, 2026-06-22 01:40 CEST.
  `wilq-ads-doctor` ma teraz explicit ActionObject allowlist zamiast brać
  każdy `google_ads` ActionObject. Demand Gen readiness zostaje w
  `wilq-demand-gen-operator`, ale nie puchnie już Ads Doctor context-pack.
  RED/GREEN proof:
  `test_codex_context_pack_scopes_ads_doctor_payload` najpierw failował, bo
  `act_review_demand_gen_readiness` był w Ads Doctor context, potem razem z
  `test_codex_context_pack_scopes_demand_gen_payload` przeszedł. Live smoke po
  `scripts/local_stack.sh restart`: `context_pack_bytes=191793`, active Ads
  action IDs: campaign review, recommendation review, n-gram review, custom
  segments, negative keywords, target guardrails, strategy review i Keyword
  Planner access. Demand Gen action nadal jest scoped do
  `wilq-demand-gen-operator`.
- Ads shared-budget distribution contract, 2026-06-22 01:25 CEST.
  `/api/ads/diagnostics.budget_pacing_read_contract` ma teraz typed
  `shared_budget_distribution_rows`. WILQ grupuje kampanie po Google Ads
  `budget_id`, pokazuje podział kosztu wspólnego budżetu per kampania i usuwa
  `shared_budget_distribution` z `missing_read_contracts`, gdy live budget rows
  mają `budget_id`. Live proof po `scripts/local_stack.sh restart`:
  `budget_rows=18`, `shared_rows=0`, `missing=[]`; decyzja
  `ads_review_budget_context` ma `missing_read_contracts=[]`, a metric tiles
  nie pokazują bezsensownego zera `wspólne budżety`, gdy nie ma shared-budget
  groups. Dashboard `/ads-doctor` ma panel `Podział wspólnych budżetów` i
  uczciwy empty-state, a `wilq-ads-doctor` smoke wymaga tego samego kontraktu w
  scoped context-packu. Non-interactive eval passed:
  `.local-lab/evals/codex-skill/20260621T232046Z/wilq-ads-doctor/result.json`
  z `language=pl-PL`, `api_used=true`, source `google_ads` i Google Ads
  evidence IDs. Final proof: `scripts/verify.sh` green, w tym 150 backend
  tests, 17 dashboard unit tests, Skill API smoke, 14 Playwright e2e tests i
  dashboard production build. Later follow-up: Ads Doctor ActionObject scope
  compaction reduced smoke context from `198997` to `191793` bytes.
- Ads change-history empty-read semantics + Ads Doctor context budget,
  2026-06-22 00:56 CEST. WILQ rozróżnia teraz "change history read wykonany,
  ale Google Ads zwrócił 0 change_event rows" od "brak kontraktu
  change_history". Live `/api/ads/diagnostics` po `scripts/local_stack.sh
  restart`: `change_history_read_contract.status=blocked`,
  `missing_read_contracts=[change_event_rows, pre_change_performance_window,
  post_change_performance_window, human_change_impact_review, apply_preview]`,
  `change_history_rows=[]`. Decyzje `ads_review_campaign_activity`,
  `ads_review_derived_kpis`, `ads_review_recommendations` i
  `ads_review_impression_share` nie pokazują już ogólnego `change_history` jako
  missing contract. W tym historycznym slice'u `ads_review_budget_context`
  zostawiał jeszcze `shared_budget_distribution`; późniejszy shared-budget
  slice usunął tę lukę. Sama decyzja `ads_review_change_history`
  pozostaje `blocked` z `zmiany=0`, co jest właściwym blockerem. Scoped
  `wilq-ads-doctor` context-pack został skompaktowany: common Ads row limit w
  context-packu to 3, pełny `/api/ads/diagnostics` pozostaje bez tego cięcia.
  Live context-pack proof: około 188 KB przez HTTP/JQ, smoke script raportuje
  `context_pack_bytes=198343`, czyli poniżej limitu 200 KB. `wilq-ads-doctor`
  smoke passed i non-interactive eval passed:
  `.local-lab/evals/codex-skill/20260621T223847Z/wilq-ads-doctor/result.json`
  z `language=pl-PL`, `api_used=true`, `operator_usefulness_score=5`, source
  connector `google_ads` i Google Ads evidence IDs. Final proof:
  `scripts/verify.sh` green, w tym 149 backend tests, 17 dashboard unit tests,
  Skill API smoke, 14 Playwright e2e tests i dashboard production build.
- Custom segments audience forecast readiness contract, 2026-06-22 00:21 CEST.
  `ads_diagnostics.custom_segments_read_contract` ma teraz nested
  `audience_forecast_read_contract` zamiast samej tekstowej luki
  `forecast_or_audience_size`. Live HTTP proof po `scripts/local_stack.sh restart`:
  `custom_segments_read_contract.status=ready`, `candidates=1`,
  `payload_preview=1`, missing contracts `keyword_planner_enrichment` i
  `forecast_or_audience_size`, a
  `audience_forecast_read_contract.status=blocked`,
  `checked_candidate_count=1`, `forecast_row_count=1`. Forecast row pokazuje
  `status=missing_forecast`, `forecast_available=false`, `audience_size=null`,
  source terms i evidence IDs z Google Ads. Decision
  `ads_prepare_custom_segments_from_search_terms` niesie
  `custom_segment_audience_forecast_rows`, więc dashboard, API i Codex skill
  widzą tę samą blokadę. `/custom-segments` i Ads Doctor pokazują osobny panel
  forecast/audience-size. `wilq-custom-segments` smoke passed, a
  non-interactive eval passed:
  `.local-lab/evals/codex-skill/20260621T221018Z/wilq-custom-segments/result.json`
  z `language=pl-PL`, `api_used=true`, `operator_usefulness_score=4`,
  source connectors `google_ads`, `google_search_console`, evidence IDs,
  ActionObject `act_prepare_custom_segments_from_search_terms`, blocked action
  candidate dla `audience_forecast_read_contract.status=blocked`,
  `missing_forecast` i zablokowanych claimów `audience size`, `ROAS`,
  `targeting applied`, `campaign performance`. Final proof:
  `scripts/verify.sh` green, w tym 149 backend tests, 17 dashboard unit tests,
  Skill API smoke, 14 Playwright e2e tests i dashboard production build.
- Demand Gen landing/migration empty-read contracts, 2026-06-21 23:40 CEST.
  `/api/demand-gen/diagnostics` nadal uczciwie zwraca `status=blocked`, bo w
  bieżącym evidence nie ma kampanii Demand Gen/Discovery do rekomendacji, ale
  missing implementation blocker zniknął. Readiness contract ma teraz
  `demand_gen_ad_group_ad_rows`, `demand_gen_creative_asset_rows`,
  `demand_gen_landing_quality_by_campaign` i
  `demand_gen_migration_constraints` jako available read contracts.
  `demand_gen_asset_group_rows` nie jest używany. Live HTTP proof po
  `scripts/local_stack.sh restart`: `kampanie Ads=18`, `kanały=2`,
  `wiersze DG=0`, `reklamy DG=0`, `assety DG=0`, `landingi DG=0`,
  `ograniczenia=0`, `braki=0`, `missing_read_contracts=[]`. Payload preview
  pokazuje `demand_gen_landing_quality_row_count=0`,
  `demand_gen_migration_constraint_row_count=0`, `apply_allowed=false`,
  `api_mutation_ready=false`, `destructive=false`. Izolowany regression test
  seeduje kampanię Demand Gen + matching GA4 landing facts i wymaga 1 landing
  row oraz 1 migration constraint row. `wilq-demand-gen-operator` smoke passed,
  a non-interactive eval passed:
  `.local-lab/evals/codex-skill/20260621T212918Z/wilq-demand-gen-operator/result.json`
  z `language=pl-PL`, `api_used=true`, source connectors Google Ads + GA4,
  `action_candidates=[act_review_demand_gen_readiness]`,
  `operator_usefulness_score=4`, `blocked=true`. Final proof:
  `scripts/verify.sh` green, w tym 149 backend tests, 17 dashboard unit tests,
  Skill API smoke, 14 Playwright e2e tests i dashboard production build.
- Ads Doctor context-pack impact-row consistency, 2026-06-21 20:59 CEST.
  Naprawiono rozjazd między `/api/ads/diagnostics` i scoped
  `POST /api/codex/context-pack {"skill":"wilq-ads-doctor"}`: generic
  compaction obcinał `recommendation_rows` do pierwszych 3 rekordów i gubił
  jeden z dwóch `impact_available=true` rows. To blokowało non-interactive
  `wilq-ads-doctor`, bo smoke wykrywał, że Codex dostałby słabszy obraz niż
  pełny endpoint. Nowa compaction zachowuje wszystkie impact rows i dopiero
  obcina mniej ważne rows. Live proof po `scripts/local_stack.sh restart`:
  endpoint ma `recommendation_rows=4`, `impact_rows=2`, context-pack ma
  `recommendation_rows=3`, `impact_rows=2`, `payload_preview=4`,
  `context_pack_bytes=198755`. Regression test:
  `test_ads_doctor_context_pack_preserves_recommendation_impact_rows`.
  `wilq-ads-doctor` smoke passed. Non-interactive eval passed z artefaktem
  `.local-lab/evals/codex-skill/20260621T185704Z/wilq-ads-doctor/result.json`,
  `language=pl-PL`, `api_used=true`, `operator_usefulness_score=5`,
  source `google_ads`, evidence IDs, Ads knowledge cards i expert rules. Nadal
  zablokowane: CPA/ROAS verdicts, wasted/search-term waste claims, budget/
  recommendation/negative-keyword/targeting apply bez human review,
  walidowanego ActionObject i audit/apply contracts. Final proof
  2026-06-21 21:18 CEST: `scripts/verify.sh` green, w tym 147 backend tests,
  17 dashboard unit tests, API/skill smokes, 14 Playwright e2e tests i
  dashboard production build. Pierwszy full verify miał transient Playwright
  `ERR_NETWORK_CHANGED` na `/workflows`; wąski rerun `/workflows` + `/knowledge`
  przeszedł, a pełny rerun verify był zielony.
- Ads search-term visibility over large refreshes, 2026-06-21 20:30 CEST.
  Naprawiono root cause, przez który duży Google Ads refresh mógł pokazywać
  campaign facts, ale ukrywać `search_term_*` facts przed Ads diagnostics,
  ActionObjects i Command Center. Store miał ukryty cap 2000, diagnostics
  prosiło o 2500, a `list_actions()` osobno ucinał Google Ads do 2000. Teraz
  `MAX_METRIC_FACT_READ_LIMIT=5000` jest jawny w DuckDB metric store, a Google
  Ads ActionObject seeding używa tego samego limitu. Regression test dodaje
  ponad 2000 neutralnych filler facts przed prawdziwymi search-term facts i
  wymaga, żeby `search_terms_read_contract`, n-gram ActionObject, negative
  keyword review i custom segments nadal działały. Live HTTP proof po
  `scripts/local_stack.sh restart`: `/api/ads/diagnostics` pokazuje
  `search_terms=ready/50`, `ngrams=ready/30` z
  `act_review_ads_search_term_ngrams`, `negative_keywords=ready/6`,
  `custom_segments=ready/1`, a `/api/dashboard/command-center` ma Ads daily
  decision `ready` z tiles `kampanie=18`, `zapytania=50`,
  `podgląd budżetu=18`, `rekomendacje=4`, `wykluczenia=6`, `segmenty=1`.
  Final proof 2026-06-21 20:45 CEST: `scripts/verify.sh` green, w tym
  146 backend tests, 17 dashboard unit tests, API/skill smokes,
  14 Playwright e2e i dashboard production build.
- Merchant feed issue review payload preview, 2026-06-21 19:35 CEST.
  `act_review_merchant_feed_issues` ma teraz typed
  `merchant_feed_issue_review_preview_v1` w `payload.payload_preview`: top
  issue clusters z Merchant, `cluster_id` zgodny z `/api/merchant/diagnostics`,
  `metric_snapshot`, required validation, blocked claims i twarde
  `apply_allowed=false`, `api_mutation_ready=false`, `destructive=false`.
  Skill-scoped context-pack dla `wilq-merchant-feed-operator` zachowuje
  kompaktowany preview, więc Codex widzi ten sam ActionObject contract co
  `/api/actions` i `/merchant`. Live smoke zwraca
  `action_preview_contract=merchant_feed_issue_review_preview_v1`, a
  `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300
  scripts/codex_skill_eval.sh --skill wilq-merchant-feed-operator --api-base
  http://127.0.0.1:8000` passed z artefaktem
  `.local-lab/evals/codex-skill/20260621T173358Z/wilq-merchant-feed-operator/result.json`.
  Eval ma `language=pl-PL`, `api_used=true`, `operator_usefulness_score=5`,
  source `google_merchant_center`, evidence IDs i ActionObject
  `act_review_merchant_feed_issues`. Nadal zablokowane: automatyczna edycja
  feedu, approval/revenue recovery, primary feed overwrite i mutacje produktu.
  Final proof 2026-06-21 20:15 CEST: `scripts/verify.sh` green, w tym
  146 backend tests, 17 dashboard unit tests, skill smokes, 14 Playwright e2e
  i dashboard production build. Po drodze usunięto niestabilność testów:
  Ads/custom-segments API tests seedują własne search-term facts zamiast czytać
  prywatny `.local-lab`, a Playwright smoke dla Ads/Custom Segments/Ahrefs
  akceptuje obecny evidence-backed blocker state zamiast wymagać starych
  ready-only tekstów.
- Localo visibility review payload preview, 2026-06-21 18:59 CEST.
  `/api/actions/act_review_localo_visibility_facts` ma teraz typed
  `local_visibility_review_preview_v1` w `payload.payload_preview`: skrócony
  metric snapshot Localo, allowed contracts (`place_inventory`,
  `local_rankings`, `reviews`), missing contracts (`gbp_visibility`,
  `competitor_visibility`, `local_tasks`), required validation i twarde
  `apply_allowed=false`, `api_mutation_ready=false`, `destructive=false`.
  Context-pack dla `wilq-localo-operator` zachowuje 1 mały Localo preview
  zamiast zerować `payload_preview`, więc Codex widzi ten sam kontrakt co
  dashboard/actions API. Live proof: context-pack pokazuje
  `payload_preview_included=1`, smoke skilla zwraca
  `localo_action_preview_contract=local_visibility_review_preview_v1`, a
  `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300
  scripts/codex_skill_eval.sh --skill wilq-localo-operator --api-base
  http://127.0.0.1:8000` passed z artefaktem
  `.local-lab/evals/codex-skill/20260621T165825Z/wilq-localo-operator/result.json`.
  Finalny proof slice'a: `scripts/verify.sh` passed o 2026-06-21 19:21 CEST,
  w tym 145 backend tests, 17 dashboard unit tests, skill smokes, 14 Playwright
  e2e i dashboard build. Po drodze naprawiono tylko outdated Ahrefs e2e smoke:
  widok `/ahrefs` pokazuje obecnie typed `competitor_page` records, a nie dawny
  marker `Luka treści:`, bo content/backlink gap contracts nadal są brakujące.
- Dashboard trace line extraction, 2026-06-21 18:36 CEST.
  Czwarty mały code-quality slice: `TraceLine` i `LinkedTraceLine` zostały
  przeniesione z `App.tsx` do `apps/dashboard/src/components/TraceLine.tsx`.
  To współdzielona warstwa evidence/action traceability używana przez wiele
  tras. File-size proof: `App.tsx` spadł do 7101 linii; `TraceLine.tsx` ma
  49 linii. Focused proof: `pnpm --filter @wilq/dashboard lint`, typecheck i
  `pnpm --filter @wilq/dashboard test -- --run App.test.tsx` zielone
  (`17 passed`).
- Dashboard metric fact chips extraction, 2026-06-21 18:25 CEST.
  Trzeci mały code-quality slice: `MetricFactChips` i jego formattery zostały
  przeniesione z `App.tsx` do
  `apps/dashboard/src/components/MetricFactChips.tsx`. To współdzielony
  komponent evidence/metric trace używany w wielu trasach. File-size proof:
  `App.tsx` spadł do 7148 linii; `MetricFactChips.tsx` ma 61 linii.
  Focused proof: `pnpm --filter @wilq/dashboard lint`, typecheck i
  `pnpm --filter @wilq/dashboard test -- --run App.test.tsx` zielone
  (`17 passed`).
- Dashboard operator primitives extraction, 2026-06-21 18:04 CEST.
  Drugi mały code-quality slice: `LoadingBand`, `BlockerNotice` i `MetricTile`
  zostały przeniesione z `App.tsx` do
  `apps/dashboard/src/components/OperatorPrimitives.tsx`. To są czyste UI
  primitives używane przez wiele tras, więc ekstrakcja idzie po realnej granicy
  komponentowej, bez zmiany API i bez osłabiania traceability. File-size proof:
  `App.tsx` spadł do 7203 linii; `OperatorPrimitives.tsx` ma 34 linie.
  Focused proof: `pnpm --filter @wilq/dashboard lint`, typecheck i
  `pnpm --filter @wilq/dashboard test -- --run App.test.tsx` zielone
  (`17 passed`).
- Dashboard query-client extraction, 2026-06-21 17:52 CEST.
  Pierwszy mały code-quality slice po nowych zasadach goalu: konfiguracja
  TanStack Query została wyciągnięta z `App.tsx` do
  `apps/dashboard/src/lib/queryClient.ts`, a `App.tsx` zachowuje publiczny
  re-export `createWilqQueryClient` dla testów i importów. File-size proof:
  `App.tsx` spadł z ok. 7251 do 7230 linii; nowy `queryClient.ts` ma 24 linie.
  Zachowanie dashboardu bez zmian. Proof:
  `pnpm --filter @wilq/dashboard typecheck` i
  `pnpm --filter @wilq/dashboard test -- --run App.test.tsx` zielone
  (`17 passed`).
- Code quality baseline, 2026-06-21 17:05 CEST.
  Goal 001 ma teraz jawny `Code Quality and Maintainability Slice`.
  Aktualne monolity są traktowane jako produktowy dług po szybkim discovery,
  nie jako docelowy standard: `App.tsx` ok. 7251 linii, `App.test.tsx` ok.
  5335 linii, `ads_diagnostics.py` ok. 5690 linii, `actions/service.py` ok.
  2076 linii, `shared-schemas/src/index.ts` ok. 1918 linii. Refaktor ma iść
  tylko po realnych granicach produktu/API i pod `scripts/verify.sh`, bez
  szerokiego przepisywania oraz bez osłabiania evidence IDs, ActionObject IDs,
  blocked claims, source connectors albo polskiej kopii operatora.
- Ads human strategy review outcome state, 2026-06-21 16:51 CEST.
  WILQ ma teraz osobny typed guardrail dla decyzji Ads: local-state
  `AdsStrategyReviewRecord` i review-only `act_record_ads_strategy_review`.
  Wynik review jest zapisywany przez standardowy `/api/actions/{id}/review`
  path razem z audit eventem. `/api/ads/diagnostics` pokazuje
  `strategy_review_status`, `strategy_reviewed_by`,
  `strategy_reviewed_at`, `strategy_review_summary`, brakujący kontrakt
  `human_strategy_review` albo `approved_human_strategy_review`, oraz polityki
  `block_target_verdict_until_strategy_review_approved` /
  `use_approved_strategy_review_before_target_verdict`. Sam target ROAS/CPA nie
  wystarcza już do target verdict: dopiero target + `approved_for_prepare`
  zmienia `target_interpretation.status` na `ready`; wcześniej pozostaje
  `preliminary`. Live proof po `scripts/local_stack.sh restart`: obecny lokalny
  operator state ma `missing_read_contracts=["target_roas_or_cpa",
  "human_strategy_review"]`, `strategy_review_status=missing`,
  `target_interpretation.status=preliminary`, action IDs
  `act_confirm_ads_target_guardrails` i `act_record_ads_strategy_review`.
  `POST /api/actions/act_record_ads_strategy_review/validate` zwraca
  `valid=true`. Wąski proof: `tests/test_api_contracts.py` zielony, ruff,
  mypy i `@wilq/shared-schemas` typecheck zielone.
- Ads target guardrail confirmation state, 2026-06-21 16:05 CEST.
  `act_confirm_ads_target_guardrails` nie jest już tylko instrukcją ustawienia
  `.env`. `ActionConfirmRequest` przyjmuje opcjonalnie `target_roas` albo
  `target_cpa_micros`; dla `confirm_ads_target_guardrails` wymagany jest
  dokładnie jeden target i nie jest wymagany wcześniejszy preview apply, bo to
  jest zapis guardraila decyzyjnego, nie mutacja Google Ads. Udany confirm
  zapisuje `AdsTargetGuardrailConfirmation` w SQLite local state razem z audit
  eventem `ads_target_guardrail_confirmed`. Ads diagnostics czyta najpierw
  `.env`, a jeśli targetu tam nie ma, używa najnowszego local-state
  confirmation jako `local_state:act_confirm_ads_target_guardrails`.
  Po potwierdzeniu znika tylko `target_roas_or_cpa`; human strategy review jest
  nadal osobnym guardrailem. `target_interpretation.status=ready` jest poprawne
  dopiero po zatwierdzonym `act_record_ads_strategy_review`. Nadal zablokowane:
  profitability verdict, budget/recommendation apply, automatic scaling i realne
  mutacje Ads.
- Ads search-term n-gram review ActionObject, 2026-06-21 15:38 CEST.
  `ads_review_search_term_ngrams` nie jest już tylko tabelą tematów bez
  workflow. Gdy WILQ ma search-term evidence, `/api/ads/diagnostics` wystawia
  `act_review_ads_search_term_ngrams` w top-level `action_ids`,
  `search_term_ngram_read_contract.action_ids`, sekcji
  `ads_search_term_ngrams` i decision `ads_review_search_term_ngrams`.
  ActionObject ma payload `google_ads_search_term_ngram_review`,
  `preview_contract=search_term_ngram_review_v1`, `ngram_preview` z
  sample search terms i metric snapshot, required validation dla
  `review_ngram_intent`, `review_source_search_terms`,
  `compare_90_day_safety_read`, `negative_keyword_action_validation` i
  `human_confirm_before_apply`, oraz hard `apply_allowed=false`,
  `api_mutation_ready=false`, `destructive=false`. Live proof po restarcie:
  n-gram contract `status=ready`, `rows=30`, action validation `valid=true`,
  full ActionObject preview count `8`. Scoped `wilq-ads-doctor` context-pack ma
  około `182599` chars, zachowuje jawny
  `action_type=google_ads_search_term_ngram_review` i kompaktuje n-gram action
  do `ngram_preview_included=1`. Nadal zablokowane: search-term waste,
  negative keyword apply, conversion loss, CPA i ROAS.
- Ads change history impact review ActionObject, 2026-06-21 15:12 CEST.
  Change history nie jest już martwą sekcją bez kolejnego kroku, gdy WILQ ma
  `change_event_*` evidence. Po pojawieniu się change-event metric facts WILQ
  wystawia review-only `act_review_ads_change_history_impact` z payloadem
  `google_ads_change_history_impact_review`,
  `preview_contract=change_history_impact_review_v1`,
  `operation_type=ChangeHistoryImpactReview`, listą
  `change_history_preview`, required validation dla review change history,
  pre/post performance windows, human impact review i business goal review,
  oraz hard `apply_allowed=false`, `api_mutation_ready=false`,
  `destructive=false`. Targeted test fixture potwierdza, że
  `/api/ads/diagnostics.change_history_read_contract.action_ids`,
  sekcja `ads_change_history`, decision `ads_review_change_history` i
  `/api/actions/act_review_ads_change_history_impact/validate` są spięte, gdy
  change rows istnieją. Live state po restarcie stacka: Ads ma live data, ale
  `change_history_read_contract.status=blocked`, `rows=0`, `action_ids=[]`,
  więc ActionObject nie jest pokazywany i `/api/actions/act_review_ads_change_history_impact`
  zwraca 404. To jest intencjonalne: brak `change_event_rows` nadal blokuje
  claimy `change impact`, `performance uplift`, `budget scaling`,
  `budget apply` i `campaign mutation`.
- Ads target guardrail confirmation ActionObject, 2026-06-21 14:31 CEST.
  Brak `target_roas_or_cpa` nie jest już tylko opisowym blockerem w Ads
  business context. WILQ wystawia review-only
  `act_confirm_ads_target_guardrails` z payload
  `action_type=confirm_ads_target_guardrails`, aktualnym
  `current_context` (profit margin, business goal, budget goal, brak target
  ROAS/CPA), `target_env_options=[WILQ_ADS_TARGET_ROAS,
  WILQ_ADS_TARGET_CPA_MICROS]`, `missing_read_contracts=[target_roas_or_cpa]`,
  hard `apply_allowed=false` i `destructive=false`. Live
  `/api/ads/diagnostics.business_context_read_contract.target_interpretation.action_ids`
  oraz decision `ads_review_business_context.action_ids` pokazują
  `act_confirm_ads_target_guardrails`. Walidacja
  `/api/actions/act_confirm_ads_target_guardrails/validate` zwraca
  `valid=true`. Nadal zablokowane: target KPI verdict, profitability verdict,
  budget/recommendation apply i realna mutacja Ads, dopóki operator nie
  potwierdzi target ROAS albo CPA oraz apply gates. Scoped `wilq-ads-doctor`
  context-pack zachowuje `credential_source=repo_env` i
  `created_by=system_ads_target_confirmation_seed` bez `[REDACTED]` na tym
  ActionObject. Full `scripts/verify.sh` passed po tym slice: backend
  `144 passed`, dashboard unit `17 passed`, Playwright `14 passed`, skill
  smokes i dashboard build.
- Ads business target interpretation gate, 2026-06-21 14:11 CEST.
  `business_context_read_contract` ma teraz typed
  `target_interpretation.interpretation_contract=ads_business_target_interpretation_v1`.
  Live stan Ekologus: `status=preliminary`, bo WILQ ma marżę, cel biznesowy i
  cel budżetu jako context review, ale nadal brakuje `target_roas_or_cpa`.
  Kontrakt jawnie rozdziela `allowed_uses` (`campaign_review_context`,
  `budget_review_context`, `margin_context`, `business_goal_alignment`) od
  `blocked_uses` (`target_kpi_verdict`, `profitability_verdict`,
  `budget_scaling`, `budget_apply`, `recommendation_apply`). Scoped
  `wilq-ads-doctor` context-pack zachowuje ten kontrakt bez `[REDACTED]`
  (`redacted=false`, około `185814` bytes), a `/ads-doctor` pokazuje panel
  `Interpretacja celu biznesowego Ads`. Nadal zablokowane: target KPI verdict,
  profitability verdict i apply, dopóki operator nie potwierdzi target ROAS/CPA
  oraz apply gates. Full `scripts/verify.sh` passed po tym slice: backend
  `144 passed`, dashboard unit `17 passed`, Playwright `14 passed`, skill
  smokes i dashboard build.
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
  nie kłamie już o brakującym campaign-row/ad/creative read contract. Live API
  proof po restarcie portu 8000: `demand_gen_readiness.status=blocked`,
  `campaign_rows_evaluated=18`, `campaign_channel_counts={PERFORMANCE_MAX: 8,
  SEARCH: 10}`, `demand_gen_campaign_rows=[]`,
  `demand_gen_ad_group_ad_rows=[]`, `demand_gen_creative_asset_rows=[]`,
  `active_action_objects=[act_review_demand_gen_readiness]` i
  `ads_diagnostics.action_ids=[]`. `demand_gen_campaign_rows`,
  `demand_gen_ad_group_ad_rows` i `demand_gen_creative_asset_rows` są teraz w
  `available_read_contracts`; missing zostają tylko
  `demand_gen_landing_quality_by_campaign`,
  `demand_gen_migration_constraints`. Skill smoke
  failuje, jeśli adjacent ActionObject wróci jako aktywna akcja Demand Gen albo
  jeśli campaign/ad/creative read contracts są ponownie raportowane jako
  missing. Full
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

7. Localo marketer snapshot, 2026-06-23 05:23 CEST.
   `/localo` now renders a dedicated `Snapshot lokalnej widoczności` above the
   technical MCP/OAuth proof. It uses existing `/api/localo/diagnostics`
   `decision_queue` metric tiles, so marketer-facing Localo facts appear before
   adapter proof while blocked claims remain explicit.
   Focused proof passed: Localo route unit test, dashboard lint and dashboard
   typecheck.

8. GA4 measurement-first route cleanup, 2026-06-23 05:26 CEST.
   `/ga4` now labels the first status section as `pomiar i jakość ruchu` and
   renders `Problemy pomiaru GA4` as a separate block above operator decisions.
   `(not set)`/tracking-gap decisions are treated as measurement/attribution
   review, not as landing quality or campaign-performance conclusions.
   Focused proof passed: GA4 route unit test, dashboard lint and dashboard
   typecheck.

9. Ads Doctor first-screen snapshot cleanup, 2026-06-23 05:31 CEST.
   `/ads-doctor` now renders `Ads snapshot marketera` before the detailed
   operator decision queue. The snapshot condenses campaigns, search terms,
   recommendations, budgets, ready/blocked areas, missing contracts and blocked
   claims. The `Operator Ads` metric grid was reduced from the broad technical
   inventory to the core review counts; deeper contracts remain available below.
   Focused proof passed: Ads Doctor route unit test, dashboard lint and
   dashboard typecheck.

10. Merchant proof compaction, 2026-06-23 05:39 CEST.
    `/merchant` now keeps the operator issue queue as the primary surface and
    compacts `Dowody i ograniczenia Merchant` into readable metric tiles,
    section/source labels, example evidence IDs and counts. The proof section no
    longer expands every route-level evidence ID as the main marketer-facing
    content. Focused proof passed: Merchant route unit test, dashboard lint and
    dashboard typecheck.

11. Content Planner proof compaction, 2026-06-23 05:43 CEST.
    `/content-planner` now renders content metric facts as Polish metric tiles
    such as `Kliknięcia`, `Wyświetlenia`, `Obiekty WP` and `Luki Ahrefs` instead
    of raw `clicks: 12` chips. `Dowody i ograniczenia Content` now shows example
    evidence IDs and total evidence count instead of turning the proof block into
    a long trace list. Focused proof passed: content route unit test, dashboard
    lint and dashboard typecheck.

12. Ahrefs proof compaction, 2026-06-23 05:47 CEST.
    `/ahrefs` now renders Ahrefs metric facts as Polish metric tiles such as
    `Domain Rating`, `Ahrefs Rank`, `Luki treści` and `Luki domen linkujących`
    instead of raw `domain_rating: 90` chips. `Dowody i ograniczenia Ahrefs`
    now shows example evidence IDs and total evidence count. Focused proof
    passed: Ahrefs route unit test, dashboard lint and dashboard typecheck.

13. GA4 proof compaction, 2026-06-23 05:50 CEST.
    `/ga4` now renders GA4 metric facts in decisions/proof as Polish metric
    tiles such as `Aktywni użytkownicy`, `Sesje`, `Zaangażowanie` and
    `Wyświetlenia stron` instead of raw `active_users: 20` chips. `Dowody i
    ograniczenia GA4` now shows example evidence IDs and total evidence count.
    Focused proof passed: GA4/GSC route unit test, dashboard lint and dashboard
    typecheck.

14. Shared MetricFact chip localization, 2026-06-23 05:52 CEST.
    Shared `MetricFactChips` now maps common metric and dimension keys to
    readable Polish labels, so lower shared surfaces such as `ActionObjectFocus`
    no longer show raw strings like `active_users: 20` for common Ads/GA4/GSC/
    Merchant/Ahrefs facts. Focused proof passed through the GA4 route test,
    dashboard lint and dashboard typecheck.

15. Ads Doctor lower-fold compaction, 2026-06-23 06:00 CEST.
    `/ads-doctor` now keeps heavy diagnostic tables behind the
    `Pokaż pełne tabele diagnostyczne` toggle. The default marketer view keeps
    Ads snapshot, operator decisions, campaign triage, strategy readiness,
    search-term review summary, review-only negative keyword candidates and
    custom segment candidates, while shared budget, recommendation, campaign
    rows and other technical drilldown tables do not render on entry. Ads
    decision cards also stop showing raw knowledge card and expert rule IDs as
    marketer-facing trace text. Focused proof passed: Ads Doctor route unit
    test, dashboard lint and dashboard typecheck.

16. ActionObject payload folding, 2026-06-23 06:05 CEST.
    `/actions` and shared `ActionObjectFocus` no longer render full
    `JSON.stringify(action.payload)` blocks by default. Each card now shows a
    short payload key summary and a `Pokaż payload ActionObject` toggle for
    drilldown. This keeps review/action cards focused on diagnosis, risk,
    validation and audit gates while preserving access to payload details.
    Focused proof passed: actions route unit test, dashboard lint and dashboard
    typecheck.

17. Merchant decision grouping, 2026-06-23 11:25 CEST.
    `/api/merchant/diagnostics` now groups the same Merchant issue across
    reporting contexts into one operator decision. Detailed issue clusters stay
    available for ActionObject payload preview, but the marketer decision queue
    no longer shows `ALL_CONTEXTS`, `FREE_LISTINGS` and `SHOPPING_ADS` as
    separate duplicate decisions for the same issue/attribute/country/severity.
    Live Ekologus proof after stack restart: Merchant decisions dropped from 8
    to 4 while 11 detailed clusters remain for traceability. Focused proof
    passed: RED/GREEN Merchant API contract tests, Python ruff OK and mypy OK.

18. Command Center Merchant count alignment, 2026-06-23 11:40 CEST.
    Command Center now uses the same grouped Merchant decision count as
    `/api/merchant/diagnostics`. The first screen no longer says Merchant has
    8 decisions when `/merchant` shows 4 grouped operator decisions. Live
    browser proof on `http://127.0.0.1:5173/command-center`: Merchant card now
    shows `decyzje=4` with `10900` products and `1887` issue occurrences.
    Focused proof passed: RED/GREEN Command Center Merchant API test, related
    Merchant tests, Python ruff OK and mypy OK.

19. Content Planner WordPress overlap labeling, 2026-06-23 11:55 CEST.
    `/content-planner` now separates WordPress overlap sources in top metrics:
    `GSC↔WP` for GSC URL to WordPress inventory matches and `Ahrefs↔WP` for
    Ahrefs topic overlap with WordPress inventory. Live browser proof shows
    `0 GSC↔WP` and `6 Ahrefs↔WP`, removing the confusing generic
    `Dopasowania WP` label that looked contradictory next to Ahrefs overlap
    cards. Focused proof passed: RED/GREEN Content route test, dashboard lint
    OK and dashboard typecheck OK.

## Active Gaps

- Content now has typed Ahrefs candidate rows and review-only
  `content_brief_preview_v1` payload previews in
  `act_prepare_content_refresh_queue`, operator selection/review persistence,
  stronger GSC/WP overlap for Ahrefs candidates and review-gated
  `wordpress_draft_payload_preview_v1` that now also survives scoped
  `wilq-content-strategist` context-pack compaction after review. Remaining
  work is better final brief selection, eventual WordPress write adapter/safety
  after explicit review and richer content impact contracts. Do not claim
  ranking, traffic, authority, lead or revenue uplift.
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
   useful decisions. Current likely candidates from browser/repo audit:
   remaining route-specific wording/compaction issues, then the largest route
   modules that still mix marketer view-model rendering with technical drilldown.
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
