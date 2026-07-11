# Current Cleanup State — 2026-07-12

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

`wilq-seo-v9ab.4`, `v9ab.5` i pierwszy zakres `v9ab.7` są domknięte jako osobne
produktowe slice'y: platform traps mają typed kontrakt, source lineage i safe
next steps, a ExpertRule ma teraz pełne warunki, kontrakty, false-positive gates
i safety. Istniejące diagnostyki nie wymyślają tych ograniczeń w React ani
skillach. Daily-check korzysta z istniejącego runtime i zwraca typed projection
z traceability; live stan `blocked` przy stale źródłach nie jest maskowany.
`wilq-seo-v9ab.8` jest rozpoczęty: source-trace guard blokuje stale/missing
source i brak dowodu/reguły przed rekomendacją. Pozostałe false-positive guards
pozostają otwarte; nie zaczynaj od kolejnego wrappera Ads ani drugiego expert
endpointu.

Po domknięciu boundary `wilq-seo-4wwo`, seamie `jnra/audit_store.py` i optimizer
readiness w `kgvy`, najnowszy wykonany slice to
`_build_ads_action_enriched_contracts` w `ads_diagnostics.py`. Reconciliation i search-term assembly są teraz
domknięte; custom-segments/negative-keywords, campaign-triage/optimizer
readiness, sections, blocked-handoff, decision_queue, response model i wszystkie
label hydration groups są wydzielone. Summary compaction i primary read-contract
bootstrap są wydzielone, parity jest potwierdzone. Następny krok to świeży review
pozostałego orchestratora, nie kolejny sztuczny wrapper.
Polityka
automatycznego stale-triggera (cooldown,
backoff, audit) pozostaje jawnie wyłączona do czasu osobnego kontraktu; `r564.3`
pozostaje zewnętrznie blokowany. Nie przywracaj direct WordPress write.

## Prawda produktu

- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`.
- Publiczny `ekologus.pl` jest SEO truth; Proudsite jest draft/dev workspace.
- Live queue: `blocked`, 2 kandydatów, 1 actionable, minimum 3.
- Managed runtime: 98 919 metric facts i 4 574 refresh runs; konektory
  12/9 configured/2 missing
  credentials/1 disabled.
- Źródła contentowe są stale. Queue i selected snapshot pokazują typed freshness,
  a primary stale proof daje `content_sources_require_refresh`.
- Read-only refresh 2026-07-11 nie odblokował kolejki: GSC zwrócił niepełny
  odczyt (2 evidence), WordPress ekologus przekroczył 60 s timeout; kolejka ma
  nadal 2 kandydatów, 1 actionable i `not_enough_actionable_candidates`.
- Queue-owned first decision renderuje przed snapshotem; cold queue po API
  prewarm ma budżet `<5 s`, a selected snapshot/enrichment mają lokalne stany
  (`c9h9.6` zamknięty).
- Desktop pokazuje konkretną homepage, public/dev sections, GSC, typed preview
  i preview-only CTA. Mobile ma teraz kompaktową decyzję/blocker/CTA przed
  ciężkim kontekstem; realny świeży kandydat nadal czeka na zewnętrzny proof.
- Review-only CTA dla kanonicznego apply jest warunkowy: wymaga gotowej paczki i
  handoffu, prowadzi wyłącznie do `/actions/act_apply_wordpress_draft_handoff`
  i nie wywołuje `/apply`; stale live queue pozostaje bez CTA. Browser proof:
  `.local-lab/proof/content-workflow-c9h9-4-review-only.png`.
- `r564.3` ma mobile-only decision card przed ciężkim kontekstem: temat/URL,
  rekomendacja, blocker i przycisk „Otwórz decyzję i dowody”. Przy stale live
  queue karta nie udaje gotowości; screenshot
  `.local-lab/proof/r564-3-mobile-stale-blocker.png` jest aktualnym proof.
- Mobile freshness został skondensowany, a source status bar jest poziomym
  scrollem; nie usuwamy statusów, tylko skracamy ich udział w first viewport.
- `4wwo` ma teraz opcjonalny async read-only refresh przez istniejący endpoint:
  POST zwraca utrwalony `queued` run, background completion przechodzi przez
  `running` do terminalnego statusu, a `/settings` polluje `GET
  /api/connectors/refresh-runs/{run_id}` i invaliduje źródła/diagnostyki/command
  center po zakończeniu. Live proof 2026-07-11 dla wyłączonego Google Sheets:
  `refresh_google_sheets_1204e9337620`, queued → completed, bez external call.
  Automatyczny trigger stale pozostaje wyłączony do czasu osobnego kontraktu
  rate-limit/backoff/audit.
- Async slice utrzymuje 392 pliki Pythona i 132 145 niepustych linii; raport
  complexity wskazuje tylko istniejące przekroczenie `_metric_dimension_value_label`
  w dotkniętym `schemas/core.py`, bez zamrożonego wzrostu.
- Kolejny `4wwo` seam deduplikuje async refresh: drugi request dla tego samego
  źródła zwraca istniejący `queued`/`running` refresh-run zamiast uruchamiać drugi
  odczyt. To jest minimalna ochrona przed podwójnym kliknięciem i przyszłym
  auto-refresh storm; pełne trigger/rate-limit/backoff/audit nadal pozostają poza
  zakresem.
- `refresh_state.refresh_allowed` jest teraz także `false` dla aktywnego
  `queued`/`running` runu, więc odświeżenie po przeładowaniu strony nie wygląda na
  dostępne, gdy źródło już jest w trakcie odczytu. Focused API contract suite ma
  5 passed; runtime po restarcie pozostaje zdrowy.
- Dashboard `/settings` respektuje ten sam warunek API: stale źródło z
  `refresh_allowed=true` ma CTA, a `queued/running` nie renderuje drugiego CTA.
  Focused dashboard tests (refresh success + active-run CTA hidden) mają 2 passed;
  desktop render proof został ponownie obejrzany po zmianie.
- `c9h9.13` Merchant ma cache 15 s i prewarm w managed lifespan; HTTP proof po
  restarcie to `0.004860 s` / `0.007203 s`, a desktop/mobile screenshoty pokazują
  decyzję przed kolejką szczegółów. Bead jest zamknięty.
- `c9h9.11` `/api/actions` ma istniejący list seam z cache/prewarm; po restarcie
  pomiar HTTP po restarcie to `0.082513 s` / `0.021151 s`. Dashboard pokazuje akcję i bezpieczny
  CTA podczas oczekiwania na readiness, bez udawania gotowego zapisu. Proof:
  `.local-lab/proof/c9h9-11-actions-cold-browser-final.png` i
  `.local-lab/proof/c9h9-11-actions-detail-cold-browser-loaded.png`. Bead jest zamknięty.
- `c9h9.9` Ads ma summary cache read-through (15 s) bez blokowania API startupu;
  HTTP proof po restarcie `1.426757 s` / `0.016956 s`. Shared schema defaults
  naprawiają zgodność API/frontend, a Ads route pokazuje bezpieczny shell podczas
  oczekiwania na dane. Pełny desktop proof: `.local-lab/proof/c9h9-9-ads-first-decision-fixed-loaded.png`;
  focused current Playwright 1/1 (7.8 s) przechodzi, ale route-level cold first
  measured heading first paint `1.853 s` (<5 s), a Bead jest zamknięty. Lazy-route
  shell proof przy 2 s: `.local-lab/proof/c9h9-9-ads-route-shell-2s.png`.
- `c9h9.12` Knowledge ma progressive disclosure: operating-map ładuje się jako
  pierwszy odczyt, cards/playbooks dopiero po kliknięciu. `list_workflows()` nie
  buduje już marketing briefu; standalone map core to `4.878 s`, HTTP po restarcie
  ma nieblokujący prewarm uruchamiany po rozpoczęciu lifespan; health pozostaje
  gotowy, a pierwszy/ponowny odczyt po rozgrzaniu wyniósł `0.003550 s` / `0.003175 s`.
  Proof: `.local-lab/proof/c9h9-12-knowledge-progressive-3s.png`; focused current
  Playwright `1/1` w `2.7 s` (29.2 s z harnessem).
- `c9h9.10` Custom Segments jest zamknięty po przejściu na istniejący Ads
  summary projection i focused Playwright `1/1` w `4.4 s`; pełny Ads payload
  nie wraca do tej trasy.
- `jnra` ma kolejny mały seam: konstruktory ActionObjectów Google Ads dla
  kontekstu biznesowego i potwierdzenia celu są teraz w istniejącym module
  `wilq/actions/google_ads/business_context.py`; `service.py` zachowuje gating
  odczytu, evidence i delegację. Keyword Planner ma analogiczny konstruktor w
  `wilq/actions/google_ads/keyword_planner.py`. Focused action contract
  `business_context` / `keyword_planner` / `strategy_review`, Ruff, mypy i diff
  check przechodzą. Static OAuth repair ma teraz konstruktor w
  `wilq/actions/google_ads/oauth.py`, bez zmiany helper commands, evidence ani
  no-write posture. Bead pozostaje otwarty dla kolejnych niezależnych seamów;
  nie wolno upraszczać ActionObject safety loop. Publiczny Service Profile
  knowledge-promotion constructor jest teraz w `wilq/actions/service_profile.py`;
  private proposal constructor jest w tym samym module, więc oba Service Profile
  review seams są zakończone. WordPress draft-handoff constructor jest teraz w
  `wilq/actions/wordpress_draft.py`; apply-mode constructor pozostaje osobnym
  seamem, bo korzysta z service-owned apply contract buildera. Apply-mode
  constructor jest teraz również domenowym delegatem; sam builder kontraktu
  pozostaje w service jako granica bezpieczeństwa. Static Google Ads
  recommendation-review seed deleguje teraz do `google_ads/recommendations.py`;
  read-required payload i blokada apply pozostają bez zmian. Static Merchant
  feed-issue seed deleguje teraz do `wilq/actions/merchant.py`; GA4 pełny
  konstruktor faktów deleguje do `wilq/actions/ga4/tracking_quality.py`, a
  content refresh seed deleguje do
  `wilq/actions/content_refresh.py`. Static seed slice w
  `seed_core_prepare_actions` jest zamknięty; większa logika content workflow
  pozostaje poza tym seamem.
  `seed_metric_action_candidates` jest teraz cienkim orkiestratorem domenowych
  grup Merchant, GA4, Content, Google Ads, Localo i Social; Social działa w
  `wilq/actions/social.py`, Merchant ma pełny konstruktor faktów, klastrów i
  preview w `wilq/actions/merchant.py`, Localo ma konstruktor oparty na faktach w
  `wilq/actions/localo/visibility.py`, a Content ma typed candidate factory w
  `wilq/actions/content_refresh.py`. Wspólne priorytety, etykiety i deduplikacja
  są w `wilq/actions/metric_utils.py`; pierwszy Ads campaign candidate factory
  jest w `wilq/actions/google_ads/campaign_review.py`. Payloady i kolejność
  rejestracji pozostają bez zmian; campaign, recommendation, change-history i
  search-term, custom-segment i negative-keyword candidate factories są w
  modułach Google Ads. Demand Gen ma teraz pełny typed candidate factory wraz z
  evidence/freshness i blokadą brakujących kontraktów; `jnra` pozostaje otwarty
  dla kolejnych grup. Ostatni seam `audit_store.py` wyciągnął read-only projekcje
  historii audytu i mutation auditów z `service.py`, zachowując limit 10 wpisów
  na akcję oraz istniejące aliasy/funkcje wywołujące. Focused action suite ma
  9 passed; ActionObject safety loop pozostaje service-owned.
- `kgvy` ma teraz wydzielony `wilq/briefing/ads_optimizer.py`: osiem typed
  readiness items i summary kontraktu optymalizacji Ads nie siedzą już w
  `ads_diagnostics.py`. Evidence/source connectors, brakujące kontrakty,
  bezpieczne next steps i blokady CPA/ROAS/waste/mutacji są zachowane. Plik
  diagnostyki zmniejszył się o 358 linii; pełny Ads contract suite, runtime
  `/api/ads/diagnostics` po restarcie i complexity audit przechodzą.
- Priority map decyzji Ads jest teraz w istniejącym `ads_decision_queue.py` jako
  `decision_priority`; kolejność blokad bezpieczeństwa i kolejki review ma focused
  contract test. Metric tiles pozostają osobnym seamem, bo wymagają rozbicia
  formatter-heavy gałęzi.
- Pierwszy metric-tile seam jest wykonany: wspólne formatowanie liczb oraz tile
  builders `campaign_activity`/`campaign_triage` są w `ads_metric_utils.py` i
  `ads_metric_tiles.py`; dispatcher w `ads_diagnostics.py` deleguje tylko te
  dwa typy. Pozostałe gałęzie pozostają świadomie nietknięte.
- Drugi metric-tile fragment obejmuje `business_context` i `derived_kpi`; target
  buckets, formatowanie oraz blokady CPA/ROAS pozostają w typed builderach.
  Dispatcher jest krótszy, ale pozostałe typy nadal czekają na osobne seamy.
- Trzeci fragment obejmuje `budget_context` i `recommendations`; zachowuje
  currency formatting, shared-budget tile, impact/priority/action counts oraz
  blokady zapisu. Complexity dispatcher obniżył się do 122 linii; reszta gałęzi
  nadal jest osobnym zakresem.
- Czwarty fragment obejmuje `search_term_ngrams` i `impression_share`; zachowuje
  n-gramowy koszt/kliknięcia oraz licznik utraty udziału przez budżet. Dispatcher
  ma teraz 12 pozostałych, jawnie znanych budget violations w audycie.
- Piąty fragment obejmuje `search_terms` i `search_term_safety`; zachowuje query/
  click/cost summary oraz 90-dniowy safety context. Pozostałe gałęzie nadal są
  osobnymi, nieprzeniesionymi seamami.
- Szósty fragment obejmuje `negative_keyword_safety` i `custom_segments`; zachowuje
  urgent/high counts, action previews, keyword context, source queries i KP ideas.
  Dispatcher pozostał bezpiecznie mały, a pozostałe gałęzie są jawnie śledzone.
- Siódmy fragment obejmuje `change_history` oraz wspólne `block_write_actions`/
  `fix_ads_access`; zachowuje change/campaign counts i safety blocker counts.
  Proste metric tiles są już poza dispatcherem; osobny pozostaje label hydration.
- Label hydration ma teraz cztery focused orchestration helpers: summary,
  decision queue, sections/handoff i nested contracts. Response labels, evidence
  summaries i blocked-claim labels pozostają bez zmian; complexity ma 11 znanych
  pozostałych monolith violations.
- Decision queue ma wydzieloną fail-closed gałąź `blocked_handoff`; OAuth/access
  blocker jest składany osobno, a główny assembler nie zmienia lineage ani claim
  safety. Pozostały większe grupy ready-decision assembly.
- Ready-decision assembly ma teraz domenowy builder `build_search_term_safety_decision`
  w `ads_decision_queue.py`; 90-dniowy safety rationale, evidence/source i blocked
  claims nie są już inline w `ads_diagnostics.py`.
- Ready-decision assembly ma także `build_business_context_decision` w
  `ads_decision_queue.py`; policy metric, rationale, evidence/action lineage i
  blokady rentowności/scalingu pozostają typed.
- Safety decision `ads_block_write_actions_without_actionobject` jest teraz w
  `build_block_write_actions_decision`; status blocked, blokady zapisów i
  lineage sekcji bezpieczeństwa nie są już inline w dispatcherze.
- Campaign/triage/business-context/derived-KPI ready decisions są teraz składane
  przez `_build_campaign_context_decisions`, a safety section przez
  `_build_ads_safety_decisions`; `_ads_decision_queue` ma 10 znanych violations
  poza budżetem, bez zmiany kolejności ani lineage.
- Fail-closed business-target interpretation jest w
  `_blocked_business_target_interpretation`; brak marży/celu nadal blokuje te
  same użycia biznesowe, a główny helper ma teraz krótszą ścieżkę statusu.
- Ready/preliminary business-target interpretation jest teraz w
  `_preliminary_business_target_interpretation`; target ROAS/CPA context,
  strategy-review gate, blocked uses i evidence lineage pozostały bez zmian.
  Complexity: 398 / 132572 LOC; 9 znanych violations.
- Operator-facing summary i safe next step business context są teraz w
  `_business_context_summary_and_next_step`; blocked/ready copy pozostaje bez
  zmian, a `_business_context_read_contract` ma 149 linii po tym seamie.
- Missing contracts, allowed metrics i status business context są teraz składane
  przez `_business_context_contract_state`; read contract pozostaje typed,
  a aktualny helper ma 131 linii. Complexity: 398 / 132597 LOC.
- Business-context metric tiles są teraz w `_business_context_metric_tiles`,
  bez zmiany nazw pól, formatowania waluty/procentów ani statusu strategii.
  Complexity: 398 / 132616 LOC; helper read contract ma 127 linii.
- Końcowa konstrukcja `AdsBusinessContextReadContract` jest teraz w
  `_build_business_context_read_contract`; blocked claims, target interpretation,
  strategy-review contract i evidence lineage pozostają typed. Complexity:
  398 / 132665 LOC; 8 znanych violations, strategy review jest już wydzielony.
- Strategy-review status, summary, safe next step, missing contracts i action IDs
  są teraz w `_strategy_review_operator_state`; readiness contract zachowuje
  `apply_allowed=false` i `destructive=false`. Complexity: 398 / 132668 LOC;
  7 znanych violations; następny target to `_compact_ads_diagnostics_summary`.
- Compact summary candidate payloads są teraz w `_compact_ads_candidate_contracts`;
  custom segments, forecast rows i negative-keyword previews nadal mają ten sam
  limit 5, a complexity spadł do 6 znanych violations.
- Campaign triage source metric/evidence context jest teraz w
  `_campaign_triage_source_context`; preview flags i lineage pozostają bez zmian.
  Complexity: 398 / 132695 LOC; 5 znanych violations, następny target to
  `_negative_keyword_candidates`.
- Negative-keyword candidate indexing jest teraz w `_negative_keyword_context_indexes`;
  90-day safety joins, keyword-context rows i evidence IDs pozostają bez zmian.
  Complexity: 398 / 132710 LOC; 4 znane violations, następny target to
  `_negative_keywords_read_contract`.
- Blocked negative-keyword read states są teraz w
  `_negative_keywords_missing_search_terms_contract` i
  `_negative_keywords_no_candidates_contract`; 90-day safety, blocked claims i
  `apply_allowed=false` pozostają bez zmian. Complexity: 398 / 132728 LOC;
  3 znane violations, następny target to `_custom_segment_candidates`.
- Custom-segment grouping oraz payload/score assembly są teraz w
  `_custom_segment_group_rows` i `_custom_segment_payload_and_score`; source-term
  filtering, Keyword Planner evidence i `apply_allowed=false` pozostają bez zmian.
  Complexity: 398 / 132760 LOC; 2 znane violations, następny target to
  `build_ads_diagnostics` orchestration.
- Typed section assembly `build_ads_diagnostics` jest teraz w
  `_build_ads_diagnostic_sections`; kolejność sekcji, lineage, blocked claims i
  safe action section pozostają bez zmian. Complexity: 398 / 132801 LOC;
  2 znane violations (plik + główny orchestrator).
- Search-term reconciliation (`90_day_safety_check` i `keyword match context`)
  jest teraz w `_reconcile_search_term_read_contracts`; freshness/read-contract
  semantics pozostają bez zmian. Complexity: 398 / 132815 LOC; 2 znane violations.
- Recommendations/impression-share reconciliation jest teraz w
  `_reconcile_ads_recommendation_and_impression_contracts`; missing-contract
  lineage i readiness semantics pozostają bez zmian. Complexity: 398 / 132848 LOC;
  2 znane violations.
- Change-history reconciliation jest teraz w
  `_reconcile_ads_change_history_contracts`; gotowy odczyt historii zmian nadal
  jedynie usuwa odpowiednie missing contracts, bez zmiany evidence/source/freshness
  ani ActionObject safety. Focused Ads contracts, Ruff, mypy, complexity i diff
  check przechodzą.
- Budget/business-context reconciliation jest teraz w
  `_reconcile_ads_budget_and_business_context_contracts`; `budget_apply_preview`,
  `profit_margin` i `human_budget_goal` pozostają kontraktowo zależne od gotowych
  odczytów. Reconciliation inline w `build_ads_diagnostics` jest domknięty;
  complexity po seamu to 398 plików / 133264 LOC i dwa jawne frozen/file-orchestrator
  violations do dalszego, niezależnego wyboru.
- Core search-term read-contract assembly (`terms`, `safety`, `keyword match`,
  `planner`) jest teraz w `_build_ads_search_term_read_contracts`; kolejność
  builderów, evidence/source connectors, freshness i missing contracts pozostają
  bez zmian. Focused/full Ads contracts, Ruff, mypy, complexity i diff check są
  zielone.
- Search-term review assembly (`review_summary`, `ngram`) jest teraz w
  `_build_ads_search_term_review_contracts`; późniejsze action-ID hydration
  pozostaje osobno. Nie zmieniono kolejności, evidence/source/freshness ani
  blokad twierdzeń.
- Candidate read-contract assembly (`custom_segments`, `negative_keywords`) jest
  teraz w `_build_ads_candidate_read_contracts`; action-ID hydration i safety
  pozostają zachowane.
- Campaign-triage i optimizer readiness assembly jest teraz w
  `_build_ads_campaign_optimizer_contracts`; target/freshness/evidence lineage,
  blocked claims i ActionObject safety pozostają bez zmian.
- Sections i blocked-handoff assembly jest teraz w
  `_build_ads_sections_and_blocked_handoff`; zachowano kolejność sekcji,
  opcjonalność fail-closed handoffu, evidence/source/freshness i safety.
- Decision queue response assembly jest teraz w
  `_build_ads_decision_queue_response`; zachowano blocked priority, decision order,
  evidence/source/freshness i ActionObject safety.
- Typed `AdsDiagnosticsResponse` construction jest teraz w
  `_build_ads_diagnostics_response`; operator summary, evidence/action aggregation
  i blocker count pozostają bez zmian. Label hydration jest osobnym seamem.
- Lifecycle label hydration jest teraz w `_hydrate_ads_response_labels`; kolejność
  review-gate labels → marketer labels pozostaje jawna, bez zmiany polskich copy.
- Search contract-label hydration jest teraz w `_hydrate_ads_search_contract_labels`;
  review summary, negative keywords i keyword match context zachowują wszystkie
  missing-contract, blocked-claim i review-gate summaries.
- Budget/performance contract-label hydration jest teraz w
  `_hydrate_ads_budget_performance_contract_labels`; currency preview labels,
  blocked-claim summaries i evidence/freshness labels pozostają bez zmian.
- Optimizer/change-impact contract-label hydration jest teraz w
  `_hydrate_ads_optimization_contract_labels`; readiness status, missing contracts
  i blocked claims pozostają bez zmian.
- Core campaign/business/custom/derived contract-label hydration jest teraz w
  `_hydrate_ads_core_contract_labels`; status/channel/missing-contract i blocked-
  claim labels pozostają bez zmian.
- Summary decision/candidate compaction jest teraz w
  `_prepare_ads_summary_compaction`; top-decision selection, fallback order,
  candidate limits i summary response shape pozostają bez zmian.
- Summary response field compaction jest teraz w
  `_compact_ads_summary_response_fields`; row limits, `sections=[]` oraz
  evidence/action lineage pozostają bez zmian.
- Primary Ads read-contract bootstrap jest teraz w
  `_build_ads_primary_read_contracts`; fallback evidence, read-attempt flags,
  currency i missing-contract semantics pozostają bez zmian.
- Summary/full parity proof: oba endpointy mają `live_data_available=true` i
  blocker count 1; summary ma `sections=[]`, full zachowuje sekcje.
- Search-term review assembly (`review_summary`, `ngram`) jest teraz w
  `_build_ads_search_term_review_contracts`; późniejsze action-ID hydration
  pozostaje osobno. Nie zmieniono kolejności, evidence/source/freshness ani
  blokad twierdzeń.

## Granica bezpieczeństwa

- Content router zawsze przekazuje `create_draft=None` i
  `action_apply_authorized=False`.
- Direct live zwraca `action_apply_required` przed adapterem.
- Readiness: `ready=false`,
  `write_authorization_status=blocked_outside_action_apply`, suggested `null`.
- Central mutation summary: 0 vendor-write possible i 0 attempted.
- React ma wyłącznie builder `mode=dry_run`, `write_authorization=null`; UI nie
  utrwala już niemożliwego direct live contractu.
- Existing draft jest otwierany/podglądany; brak create/duplicate CTA.
- Create należy do zamkniętego `c9h9.4`: canonical apply buduje typed capability
  wewnątrz `apply_action` i wiąże exact action, work item, handoff, draft package,
  dev host, operatora i mutation audit. Publish, update i delete pozostają poza
  zakresem.

## Bieżący graf

Zamknięte w tym slice:

- `c9h9.3` — direct WordPress live fail-closed;
- `r564.2` — duplicate create usunięty wraz z direct live CTA;
- `r564.4` — typed existing-draft preview card;
- `c9h9.7` — stabilny full-suite Service Profile test.
- `c9h9.5` — freshness w queue/snapshot i refresh-first blocker.
- `c9h9.6` — queue/snapshot cold waterfall usunięty przez prewarm, reuse builda
  i progressive first card.
- `c9h9.4` — backend i shared frontend mają ten sam typed apply input,
  `applyAction` używa istniejącej granicy `/apply`, a realny capability builder
  wiąże bieżący snapshot, review/audit, canonical URL i aktora. Dev-host guard
  blokuje public/arbitrary host przed HTTP. Bead jest zamknięty po route-level
  readiness proof i review-only CTA.

Otwarte product blockers:

- `r564.3` — mobile first viewport; świeży, nieblokowany content candidate nadal
  zależy od zewnętrznego refreshu.
- `c9h9.9`, `c9h9.10`, `c9h9.11`, `c9h9.12` i `c9h9.8` są zamknięte po
  API/browser proof; obecny pełny `dashboard-api.spec.ts` przechodzi 13/13.

`ho41` jest wyłącznie route/component boundary. `jnra` jest splitem action
service. Żaden z nich nie może przejąć product semantics freshness/write.

## Complexity checkpoint

- `wilq/briefing/ads_diagnostics.py`: 6 475 LOC;
- `wilq/actions/service.py`: 4 244 non-empty LOC;
- `wilq/actions/merchant.py`: 308 non-empty LOC;
- `wilq/actions/social.py`: 154 non-empty LOC;
- `wilq/actions/metric_utils.py`: 25 non-empty LOC;
- `wilq/actions/content_refresh.py`: 1 985 non-empty LOC;
- `apps/dashboard/src/routes/ContentWorkflowSurface.tsx`: ok. 3 000 LOC;
- `wilq/content/workflow/api.py`: 1 478 LOC;
- `tests/api_contracts/test_ads_contracts.py`: 4 971 LOC; największy test
  2 914 linii.

Latest complexity report (2026-07-11): 398 plików Python,
132485 non-empty LOC. Bounded content seed extraction, metric-candidate
orchestration, Social, Localo, Merchant, GA4, Content and Ads campaign/
recommendation/change-history/search-term/custom-segment/negative-keyword/
Demand Gen module extraction were audited with
`--allow-frozen --allow-budget-violations`: service.py remains a frozen-growth
file because the seam removes inline code, while pre-existing content/service
budget findings remain tracked for the broader `jnra` cleanup. This 4wwo schema
slice also surfaces the pre-existing `_metric_dimension_value_label` budget
finding in `schemas/core.py`; it is unrelated to refresh-state behavior and is
tracked separately. Historyczne duże
testy pozostają osobnym otwartym cleanup scope; bieżący seed seam nie zwiększa
ich rozmiaru.

## Proof checkpoint

- 765 backend passed / 2 skipped baseline; c9h9.5 i c9h9.6 focused content tests
  green;
- c9h9.4 pod-slice: action mutation + WordPress adapter + content execution tests
  green; public/arbitrary host ma zero HTTP; dashboard ContentWorkflow
  review-only CTA ma focused Vitest 15/15, lint i typecheck green;
  Ruff i mypy green.
- Shared 31 passed / 10 skipped; dashboard 138/138; lint/typecheck/build green.
- Security, API/CLI smoke i wszystkie deterministic skill smokes green.
- 13/13 skill evals fresh/passing, scores 9–10; strict coverage bez gaps.
- Live direct POST i readiness są fail-closed.
- Google Ads Demand Gen readiness działa przez factory w
  `wilq/actions/google_ads/demand_gen.py`; runtime ma `prepare`, pięć evidence,
  dwa brakujące kontrakty, `apply_allowed=false` i centralne `write_capable=0`.
  `service.py` spadł do 4 777 LOC; focused Demand Gen/action tests, Ruff,
  mypy i `git diff --check` przechodzą.
- Predykaty bezpieczeństwa payloadu (`apply_allowed` i
  `api_mutation_ready`) mają teraz mały typed seam w
  `wilq/actions/payload_readiness.py`; service zachowuje istniejącą granicę
  preview i zachowanie centralnego apply gate.
- Action status/risk/mode/evidence/mutation labels mają teraz typed seam w
  `wilq/actions/operator_labels.py`; service zachowuje te same polskie etykiety,
  źródła connectorów i safety semantics.
- Pełne mapowanie `_action_gate_label` jest teraz w
  `wilq/actions/gate_labels.py`; service zachowuje kompatybilny delegat i te same
  blokady claims, evidence, review i apply.
- Review-gate assembly jest teraz w `wilq/actions/review_gate.py`; service
  zachowuje odczyt eventów, blocker calculation i callbacki audit/labels, a
  moduł składa ten sam typed `ActionReviewGate`. Complexity po seamu: service.py
  4 468 LOC, bez zmiany `write_capable=0`.
- Mapping blockerów mutation readiness jest teraz w
  `wilq/actions/mutation_readiness.py`; wymagania i kolejność blokad pozostają
  service-owned, a każdy niespełniony warunek nadal daje polski blocker i safe
  next step. Complexity po seamu: service.py 4 341 LOC.
- Bazowa lista requirements mutation readiness jest w
  `wilq/actions/mutation_requirements.py`, a typed response assembly w
  `wilq/actions/mutation_response.py`. Service zachowuje WordPress-specific
  readiness i adapter gates; obecny runtime nadal ma 0 write-capable actions.
- Mutation readiness summary assembly jest teraz w
  `wilq/actions/mutation_summary.py`; service zachowuje wybór kandydatów,
  blocker counts i operator next-step callbacks, a typed summary nadal raportuje
  21 akcji i 0 write-capable.
- `4wwo` ma teraz istniejący `/api/connectors` rozszerzony o typed
  `refresh_state`: stan odczytu, `refresh_allowed`, ostatni run, safe next step i
  affected decisions. `/settings` pokazuje tę informację ponad ręcznym CTA;
  browser proof jest w `.local-lab/proof/4wwo-sources-refresh-state.png`.
- Aktualne screenshoty desktop/mobile/action są w lokalnym, ignorowanym
  `.local-lab/proof/independent-review-2026-07-10/`.
- Full cold E2E ma jawne otwarte blockers; nie nazywaj całego `verify.sh`
  zielonym, dopóki nie zostaną rozwiązane. Goal 005 nadal czeka na realny Wilku
  UAT albo owner defer.

## Resume

1. Potwierdź clean/synced `main` po commicie tego slice’a.
2. Odczytaj live connectors, diagnostics i queue; nie używaj liczb z pamięci.
3. Kontynuuj `jnra`: wydziel review-gate assembly z zachowaniem pełnego
   ActionObject safety loop i testów zachowania.
4. `r564.3` może zostać zamknięty dopiero po browser proof 390×844 ze świeżym,
   nieblokowanym kandydatem; obecny stan zewnętrzny tego nie dowodzi.
