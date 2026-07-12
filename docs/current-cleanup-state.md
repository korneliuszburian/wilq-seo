# Current Cleanup State — 2026-07-13

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

`wilq-seo-v9ab.4`, `v9ab.5` i pierwszy zakres `v9ab.7` są domknięte jako osobne
produktowe slice'y: platform traps mają typed kontrakt, source lineage i safe
next steps, a ExpertRule ma teraz pełne warunki, kontrakty, false-positive gates
i safety. Istniejące diagnostyki nie wymyślają tych ograniczeń w React ani
skillach. Daily-check korzysta z istniejącego runtime i zwraca typed projection
z traceability; live stan `blocked` przy realnej blokadzie nie jest maskowany.
`wilq-seo-v9ab.8` jest rozpoczęty: source-trace guard blokuje stale/missing
source i brak dowodu/reguły przed rekomendacją, `missing_conversion` korzysta
z istniejącego `Ga4ConversionReadinessContract`, a content `date_window` z
`ContentGscSearchAnalyticsContract`. `v9ab.8.1` dodaje dla aggregate daily
content queue evidence-backed `multi_source_required`: komplet nazw connectorów
nie wystarcza, każdy wymagany WordPress source musi mieć typed MetricFact z
evidence; indywidualne publiczne work ordery nie dziedziczą scope sklepu.
Zamknięty `v9ab.8.2` wymaga dodatkowo actionable `ContentOpportunityMeasurementBaseline`
z metrykami, connectorami i evidence; publiczny URL, zablokowany Ahrefs record,
mismatch albo wyjątek nie mogą udawać bazy pomiaru. Jeden gotowy temat może być
review-ready, ale daily output musi nadal nazwać queue density blocker (obecnie
1 z 3), więc nie myli pojedynczego review z gotowym backlogiem.
Pozostałe false-positive guards pozostają otwarte; nie zaczynaj od kolejnego
wrappera Ads ani drugiego expert endpointu.

Po domknięciu boundary `wilq-seo-4wwo`, seamie `jnra/audit_store.py` i optimizer
readiness w `kgvy`, najnowszy wykonany slice to

`wilq-seo-c9h9.18`: Ahrefs branch tactical queue został wydzielony do
`wilq/briefing/tactical_ahrefs.py`. Matcher cross-source jest kompilowany raz na
batch, a live queue zachowuje 24 itemy, 19 grup i 3 action IDs. Focused tests,
Ruff i mypy przechodzą. Complexity audit nadal pokazuje istniejący budżet
`tactical_queue.py` (1311 LOC) oraz `_merchant_feed_items` (115 LOC); nie jest to
ukrywane jako sukces i pozostaje zakresem dalszego Beada.

Następnie `wilq-seo-ipps` wydzielił Merchant issue/status assembly do
`wilq/briefing/tactical_merchant.py`. Live kolejka zachowuje 24 elementy, w tym
4 Merchant, oraz dotychczasowe evidence/action semantics. Complexity
`tactical_queue.py` spadła do 1195 LOC; pozostały monolit jest kolejnym,
potwierdzonym zakresem, a nie ukrytym wyjątkiem.

`wilq-seo-c9h9.16` wydziela orchestrację snapshotu workflow do
`wilq/content/workflow/snapshot_assembly.py`. Publiczne API zachowuje istniejące
stage callbacks i response contract, ale składanie kolejności preflight → brief
→ draft → review → handoff → measurement ma jednego typed ownera. Live snapshot
pozostaje fresh/evidence-first, a Service Profile i handoff blokują finalne
twierdzenia/zapis zgodnie z kontraktem. `api.py` ma 1470 LOC; dalszy split jest
osobnym potwierdzonym zadaniem.
`wilq-seo-zdm2` wydzielił preflight i Sales Brief adapters do
`wilq/content/workflow/stage_preparation.py`. Snapshot nadal zachowuje fresh
evidence z GSC/WordPress oraz blokadę Service Profile/handoff. `api.py` ma
1416 LOC; draft/review/handoff extraction jest osobnym Beadem `wilq-seo-mseb`.
`wilq-seo-mseb` wydzielił draft package, structured-generation i variants do
`wilq/content/workflow/stage_drafts.py`. Live snapshot pozostaje fresh i
evidence-first, a `api.py` ma 1352 LOC. Human review/handoff są teraz osobnym
zakresem `wilq-seo-frgd`.
`wilq-seo-frgd` wydzielił human-review i WordPress handoff adapters do
`wilq/content/workflow/stage_review.py`. Live snapshot zachowuje fresh evidence,
0 human-review blockers dla bieżącego kandydata, ale 1 handoff blocker i brak
publikacji. `api.py` ma 1313 LOC; measurement extraction śledzi `wilq-seo-s8dl`.
`wilq-seo-s8dl` wydzielił measurement window/outcome adapters do
`wilq/content/workflow/stage_measurement.py`. Live snapshot zachowuje fresh
evidence, 1 measurement blocker i brak success claim. `api.py` ma 1272 LOC;
pozostałe readiness helpers śledzi `wilq-seo-kvgd`.
`wilq-seo-kvgd` wydzielił existing-draft update readiness projection do
`wilq/content/workflow/stage_readiness.py`. Live kontrakt nadal blokuje update
istniejącego draftu i nie odblokowuje publikacji. `api.py` ma 1201 LOC;
pozostałe activation/write-readiness orchestration śledzi `wilq-seo-eieh`.
`wilq-seo-eieh` wydzielił typed WordPress activation packet projection do
`wilq/content/workflow/stage_activation.py`. Live dry-run pozostaje
fail-closed, bez publikacji i bez vendor write. `api.py` ma 1148 LOC;
pozostałe readback/label helpers śledzi `wilq-seo-nlax`.
`wilq-seo-nlax` wydzielił readback/activation label helpers do
`wilq/content/workflow/stage_activation.py`. Live dry-run/readback pozostają
fail-closed, bez publikacji. `api.py` ma 1017 LOC; pozostałe write-readiness
orchestration śledzi `wilq-seo-b0ja`.
`_build_ads_action_enriched_contracts` w `ads_diagnostics.py`. Reconciliation i search-term assembly są teraz
domknięte; custom-segments/negative-keywords, campaign-triage/optimizer
readiness, sections, blocked-handoff, decision_queue, response model i wszystkie
label hydration groups są wydzielone. Summary compaction i primary read-contract
bootstrap są wydzielone, parity jest potwierdzone. Następny krok to świeży review
pozostałego orchestratora, nie kolejny sztuczny wrapper.
Polityka automatycznego stale-triggera (cooldown, backoff, audit) pozostaje
jawnie wyłączona do czasu osobnego kontraktu; `r564.3` jest zamknięty, a parent
`r564` blokuje się wyłącznie na candidate density: jeden unikalny publiczny URL
z GSC i Ahrefs bez bezpiecznego referenced public URL. Nie twórz sztucznego
tematu ani nie przywracaj direct WordPress write.
`r564.5` jest zamknięty: Ahrefs cross-check ma jeden pure typed seam
`wilq/content/planning/ahrefs_overlap.py`, wspólny dla planera i tactical queue.
Tylko `exact` URL/phrase lineage może dać `present`, punkty relevance,
review-only ActionObject albo preflight duplicate URL; `weak` ma być widocznym
manualnym cross-checkiem bez akcji. Nie przywracaj matcherów z dowolnego tokenu,
`source_url` lub domeny konkurenta i nie doklejaj tej reguły w React/skillach.
WordPress bez publicznego URL, także dev Proudsite z identycznym tytułem, nie
jest rekordem inventory dla tego seamu i nie może przejść do `exact`.
`r564.6` jest zamknięty: istniejący work-item snapshot projektuje compact typed
Service Profile context z istniejącego matcher'a kart wiedzy. Context zawiera
binding/status usługi, policy wyłącznie dopasowanej karty (pełny Claim Ledger
pozostaje niżej), freshness, source/evidence lineage, missing contracts i jeden
safe next step; nie ma nowego endpointu ani inferencji z enrichmentowego
`service_fit`. Snapshot zablokowany przed workflow zwraca
`not_evaluated`, a nie zgadywanie usługi. Dashboard renderuje jedną sekcję przy
  publicznej stronie; raw IDs są wyłącznie w disclosure. Mobile 390 px ma
  `scrollWidth=390` po naprawie shrinku workbenchu. Live homepage jest `bound`,
  ale `blocked` do finalnych treści, więc slice nie omija review, ActionObjectu
  ani draft-only/publish gates.
`3bst.7` jest zamknięty: `/ahrefs` nie zaczyna już od równorzędnych kart
`gotowe`, gdy `gap_read_contract.cross_check_status=manual_required`.
Istniejący API-owned blocker, podsumowanie, liczba tematów/zero potwierdzeń,
dowody i safe next step są jednym priorytetowym regionem nad kartami. React
wyłącznie renderuje typed kontrakt — nie klasyfikuje dopasowań i nie tworzy
ActionObjectu. W pierwszym viewportcie nie ma surowych ID; desktop/mobile proof
jest w `.local-lab/proof/3bst7-ahrefs/`, a re-review marketer/operator to 7/10.
`c9h9.17` jest zamknięty: root cause nie był w readach DuckDB, lecz w 338-krotnym
budowaniu tych samych rekordów GSC/WordPress podczas oceny 338 luk. Immutable
`AhrefsCrossSourceMatcher` kompiluje je raz na batch; raw helper zachowuje się
jak kompatybilny adapter dla pojedynczego wywołania. Po restarcie trzy live HTTP
reads wyniosły 1.354044 s, 1.351506 s i 1.212189 s przy zachowanym
`manual_required`, 6 kandydatach i 0 ActionObjectach. Nie dodano cache'a, więc
nie ma ryzyka podania stale evidence. Osobny `c9h9.18` śledzi tactical queue
monolith: jego Ahrefs branch może przyjąć ten matcher dopiero po typed
extraction, nie przez wyjątek od budgetu.
`c9h9.15` jest zamknięty: detect-secrets ma jedną localną pragma allowlist
wyłącznie przy testowej nazwie pola redakcji. Scoped test dowodzi, że identyczne
pole bez pragma nadal jest wykrywane w innym pliku, a `scripts/security.sh`
przechodzi z pustymi wynikami detect-secrets. Nie dopisuj credentiali na tej
samej fizycznej linii fixture; semgrep nadal nie jest zainstalowany i jego
nieuruchomienie pozostaje jawne.

## Prawda produktu

- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`.
- Publiczny `ekologus.pl` jest SEO truth; Proudsite jest draft/dev workspace.
- Live queue: `blocked`, 2 kandydatów, 1 actionable, minimum 3.
- Managed runtime: 104 362 metric facts i 4 580 refresh runs; konektory
  12/9 configured/2 missing
  credentials/1 disabled.
- Źródła contentowe są teraz świeże po read-only refreshu 2026-07-12. Queue i
  selected snapshot pokazują typed freshness `fresh`, a blockerem pozostaje
  `not_enough_actionable_candidates`.
- Refresh zakończył się dla WordPress sklep, GA4 i Ahrefs; kolejka ma 2
  kandydatów, 1 actionable i minimum 3. Nie twórz sztucznego trzeciego tematu.
- Queue-owned first decision renderuje przed snapshotem; cold queue po API
  prewarm ma budżet `<5 s`, a selected snapshot/enrichment mają lokalne stany
  (`c9h9.6` zamknięty).
- Desktop pokazuje konkretną homepage, public/dev sections, GSC, typed preview
  i preview-only CTA. Mobile ma teraz kompaktową decyzję/blocker/CTA przed
  ciężkim kontekstem; świeżość jest potwierdzona, ale próg kolejki nadal wymaga
  kolejnych evidence-backed kandydatów.
- Review-only CTA dla kanonicznego apply jest warunkowy: wymaga gotowej paczki i
  handoffu, prowadzi wyłącznie do `/actions/act_apply_wordpress_draft_handoff`
  i nie wywołuje `/apply`; stale live queue pozostaje bez CTA. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-workflow-desktop.png`.
- `r564.3` ma mobile-only decision card przed ciężkim kontekstem: temat/URL,
  rekomendacja, blocker i przycisk „Otwórz decyzję i dowody”. Przy świeżym live
  queue karta nie udaje gotowości przy progu 1/3; screenshot
  `.local-lab/proof/continuation-2026-07-12/content-workflow-mobile.png` jest
  aktualnym proof.
- Mobile freshness został skondensowany, a source status bar jest poziomym
  scrollem; nie usuwamy statusów, tylko skracamy ich udział w first viewport.
- Live work item ma teraz przy publicznej stronie typed Service Profile binding
  i approval policy: homepage jest `bound` do
  `ekologus_service_homepage_overview`, ale `blocked` przez review-required
  publiczne karty usług. Marketer widzi dowód, świeżość, pierwszy bloker i safe
  next step bez przechodzenia do osobnej trasy; ID, evidence i review action
  są pod disclosure. `v9ab.11` pozostaje osobnym zadaniem pamięci Workspace
  Dossier.
- `4wwo` jest zamknięty przez `3gre`: `/settings` automatycznie zleca tylko
  jedno read-only odświeżenie, gdy istniejąca API-owned polityka zwraca
  `automatic_refresh.eligible=true`. POST zwraca utrwalony `queued` run,
  istniejący GET przechodzi przez `running` do terminalnego statusu, a dopiero
  wtedy dashboard invaliduje `connectors` i cache decyzji wskazanych przez
  `refresh_state.affected_decisions`. React nie rozstrzyga stale/cooldown.
  Nieudany odczyt statusu pozostaje blockerem „stan niepotwierdzony” z retry,
  nie jest klasyfikowany jako błąd vendora ani nie tworzy write path.
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

- `r564.3` — **closed** po świeżym desktop/mobile proof; parent `r564` nadal
  ma tylko 1 actionable candidate z minimum 3.
- `c9h9.9`, `c9h9.10`, `c9h9.11`, `c9h9.12` i `c9h9.8` są zamknięte po
  API/browser proof; obecny pełny `dashboard-api.spec.ts` przechodzi 13/13.

`ho41` jest wyłącznie route/component boundary. `jnra` jest splitem action
service. Żaden z nich nie może przejąć product semantics freshness/write.

## Complexity checkpoint

- `wilq/briefing/ads_diagnostics.py`: 6 616 LOC;
- `wilq/actions/service.py`: 1 608 non-empty LOC;
- `wilq/actions/merchant.py`: 308 non-empty LOC;
- `wilq/actions/social.py`: 154 non-empty LOC;
- `wilq/actions/metric_utils.py`: 25 non-empty LOC;
- `wilq/actions/content_refresh.py`: 1 985 non-empty LOC;
- `apps/dashboard/src/routes/ContentWorkflowSurface.tsx`: ok. 3 000 LOC;
- `wilq/content/workflow/api.py`: 1 478 LOC;
- `tests/api_contracts/test_ads_contracts.py`: 4 971 LOC; największy test
  2 914 linii.

Aktualny rebaseline complexity (2026-07-12): 423 pliki Python / 136751
non-empty LOC; `service.py` ma 1608 LOC po canonical registry, Keyword Planner
eligibility i confirmation policy seamu. Cache zapisuje inventory tylko, gdy
fingerprint Google Ads jest taki sam przed i po buildzie. Standardowy
`--changed` jawnie wymaga akceptacji frozen facade i istniejącego dużego pliku
testowego; wariant `--allow-frozen --allow-budget-violations` przechodzi, a
raportowane przekroczenia testów są wcześniejsze i niezwiązane z asercją parity.
Nie przenoś gotowych WordPress/readiness/preview granic tylko po to, by obniżyć
ten licznik.
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
- W kolejnym seamu `jnra` wybór pierwszej kandydatury zapisu, plan aktywacji i
  operator summary next step przeniesiono do `wilq/actions/mutation_plan.py`.
  Service nadal składa readiness z istniejących requirements/blockers i przekazuje
  callback, bez zmiany payloadów ani write gates. Live summary po restarcie ma
  21 akcji, 0 vendor-write possible i 0 attempted; `service.py` ma 4046 LOC.
- Kontrakt apply dla WordPress draft-only jest teraz w
  `wilq/actions/mutation_contract.py`; nieobsługiwane akcje nadal dostają `None`,
  a apply contract zachowuje blokadę publikacji/destrukcji i wymagane audyty.
  `service.py` ma 3868 LOC po target projection; następny seam wymaga nowego
  complexity/runtime review.
- Najnowszy `jnra` seam przeniósł WordPress-specific execution/target readiness
  do `wilq/actions/wordpress_mutation_requirements.py`; `service.py` ma 3897 LOC.
  Live readiness nadal raportuje 21 akcji, 0 vendor-write possible i 0 attempted;
  publikacja i destructive writes pozostają false.
- Target projection readiness jest teraz w `wilq/actions/mutation_target.py`;
  service przekazuje istniejący preview-items callback i nie składa targetu z
  raw payloadu. `service.py` ma 3868 LOC; payloady i safety gates bez zmian.
- WordPress draft payload/handoff preview cards są teraz w
  `wilq/actions/wordpress_preview.py`; dispatcher zachowuje istniejące preview
  contracts i callbacki operator labels. `service.py` ma 3782 LOC; brak nowej
  ścieżki write/publish.
- Payload assembly dla `wordpress_draft_payload_preview_v1` jest teraz w
  `wilq/actions/wordpress_payload_preview.py`; `content_refresh` pozostaje
  właścicielem reguł, labels i blockerów przez jawny support boundary. Nie ma
  zmiany w evidence IDs, canonical/duplicate gates, blocked claims ani
  `apply_allowed=false`. Nowy moduł nie dodaje budżetowych naruszeń funkcji.
- Po restart/reload live API pozostaje zdrowe: 99 906 metric facts, 4 577
  refresh runs, queue `fresh`/1 actionable z minimum 3, WordPress readiness
  nadal fail-closed.
- Social preview builder jest teraz w istniejącym `wilq/actions/social.py`;
  service nie duplikuje już źródłowych rows, labels ani blokady publikacji.
  Live akcje LinkedIn/Facebook mają `prepare`, evidence IDs, cztery typed
  `social_draft_input_review` cards i nie tworzą write-capable path.
- Ads budget preview builder jest teraz w `wilq/actions/google_ads/previews.py`;
  service zachowuje dispatcher i przekazuje jawne presentation callbacks.
  Live action `act_prepare_ads_campaign_review_queue` ma cztery karty budżetu,
  evidence ID i blokadę `apply_allowed=false`/`api_mutation_ready=false`;
  technical IDs pozostają poza kartą operatora.
- Recommendation preview renderer jest teraz w istniejącym
  `wilq/actions/google_ads/recommendations.py`; live action ma cztery typed
  cards, evidence ID, blokadę zapisu i blocked claims bez raw vendor payloadu.
- Negative-keyword preview renderer jest teraz w istniejącym
  `wilq/actions/google_ads/negative_keywords.py`; live action zachowuje
  evidence, 90-dniowe safety gates, blocked claims i brak ścieżki zapisu.
- Custom-segment preview renderer jest teraz w istniejącym
  `wilq/actions/google_ads/custom_segments.py`; live action zachowuje source
  terms, safety blockers, audience-size/Keyword Planner gates i brak zapisu.
- Change-history preview renderer jest teraz w istniejącym
  `wilq/actions/google_ads/change_history.py`; raw event IDs, resource/operation
  enums i field names są schowane z operator card, a technical details pozostają
  dostępne niżej przez istniejący disclosure.
- Demand Gen readiness preview renderer jest teraz w
  `wilq/actions/google_ads/demand_gen_preview.py`; service przekazuje jawne
  callbacks, a live card zachowuje 4 evidence IDs, freshness, missing landing
  quality/mode contracts, blocked claims oraz `apply_allowed=false` i
  `api_mutation_ready=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-demand-gen-preview-cards.png`.
- Search-term n-gram preview renderer jest teraz w
  `wilq/actions/google_ads/search_term_ngram_preview.py`; service przekazuje
  callbacks do labels i metryk, a live cztery karty zachowują evidence,
  przykłady zapytań, blocked claims oraz `apply_allowed=false`/
  `api_mutation_ready=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-search-ngram-preview-cards.png`.
- GA4 tracking-quality preview renderer jest teraz w
  `wilq/actions/ga4/tracking_preview.py`; service przekazuje callback do typed
  metric rows, a live karta zachowuje landing/source/campaign evidence,
  tracking gaps, blocked claims i brak zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ga4-tracking-preview-cards.png`.
- Localo visibility preview renderer jest teraz w
  `wilq/actions/localo/visibility_preview.py`; service przekazuje callback do
  metric rows, a live karta zachowuje kontrakty odczytu, freshness/evidence,
  blocked claims i brak zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/localo-visibility-preview-cards.png`.
- Merchant feed preview renderer jest teraz w
  `wilq/actions/merchant_preview.py`; service przekazuje callbacki do rows,
  próbek i safety labels, a live cztery karty zachowują issue context, evidence,
  blocked claims i brak zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/merchant-feed-preview-cards.png`.
- Keyword Planner access preview renderer jest teraz w istniejącym
  `wilq/actions/google_ads/keyword_planner.py`; karta zachowuje zewnętrzny
  blocker dostępu, evidence, wymagany next step, blocked claims i brak zapisu.
  Browser proof:
  `.local-lab/proof/continuation-2026-07-12/keyword-planner-access-preview.png`.
- Ads target-guardrail preview renderer jest teraz w istniejącym
  `wilq/actions/google_ads/business_context.py`; service przekazuje typed
  business-context rows, a live karta zachowuje brak potwierdzonego celu,
  blocked claims i brak zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-target-guardrail-preview.png`.
- Ads strategy-review preview renderer jest teraz w istniejącym
  `wilq/actions/google_ads/business_context.py`; service przekazuje typed
  business-context rows i summary. Wspólne etykiety kontekstu i summary są
  współdzielone w module domenowym przez callbacki, a live karta zachowuje brak ludzkiego review,
  blocked claims i brak zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-strategy-review-preview.png`.
- Service Profile public knowledge-promotion oraz redacted private-proposal
  preview renderery są teraz w `wilq/actions/service_profile.py`; service
  deleguje przez typed callbacks, a live karty zachowują evidence, review gates,
  blocked claims i `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/service-profile-private-preview-live.png`.
- Content brief preview renderer jest teraz w nowym
  `wilq/actions/content_preview.py`; service pozostaje dispatcherem, a live
  content-refresh zachowuje evidence, publiczne URL-e, review gates i
  `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-brief-preview-live.png`.
- Content-refresh preview composition jest teraz w
  `wilq/actions/content_preview.py`; service zachowuje tylko dispatcher i
  callback do istniejącej karty WordPress draft. Live content action nadal ma
  evidence, publiczne URL-e i `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-refresh-composition-live.png`.
- Localo metric snapshot row helper jest teraz w
  `wilq/actions/localo/visibility_preview.py`; live Localo karta zachowuje
  agregaty, evidence, brakujące kontrakty, blocked claims i `apply_allowed=false`.
  Browser proof:
  `.local-lab/proof/continuation-2026-07-12/localo-metric-helper-live.png`.
- GA4 metric snapshot row helper jest teraz w
  `wilq/actions/ga4/tracking_preview.py`; live GA4 karta zachowuje evidence,
  landing/source/campaign rows, blocked conversion/ROAS/revenue claims i
  `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/ga4-metric-helper-live.png`.
- Review summary, checked-item i blocker label assembly jest teraz w
  `wilq/actions/review_gate.py`; service przekazuje typed callbacks, a live
  ActionObject zachowuje review gates, blocked claims i brak zapisu. Browser
  proof: `.local-lab/proof/continuation-2026-07-12/review-gate-summary-live.png`.
- Parsery content URL review i draft-readiness są teraz w
  `wilq/actions/content_review_details.py`; live content action zachowuje
  evidence, publiczne URL-e, review gates i `apply_allowed=false`. Browser
  proof: `.local-lab/proof/continuation-2026-07-12/content-review-details-live.png`.
- Review outcome label i human-review event projection są teraz w
  `wilq/actions/review_gate.py`; live Ads strategy karta zachowuje review gate,
  evidence i blokadę zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/review-outcome-projection-live.png`.
- Action preview/confirmation/impact/apply blocker rules są teraz w
  `wilq/actions/action_blockers.py`; live Ads karta zachowuje blocked claims,
  review gates i `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/action-blockers-live.png`.
- Confirmation/impact summary assembly jest teraz w
  `wilq/actions/action_blockers.py`; live Ads karta zachowuje safety labels,
  blocked claims i brak zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/action-summary-live.png`.
- Audit summary/operator text normalization i raw identifier redaction są teraz
  w `wilq/actions/audit_store.py`; live Ads karta zachowuje review gates,
  evidence i brak zapisu. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/audit-summary-live.png`.
- Etykiety zdarzeń audytu są teraz własnością istniejącego
  `wilq/actions/audit_store.py`; service zachowuje tylko delegowanie, a znane
  preview/review/confirm/impact/apply eventy i fallback mają ten sam bezpieczny
  polski kontrakt. Live Ads strategy action: HTTP 200, 2 evidence IDs,
  `apply_allowed=false`, `Zapis zablokowany`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/event-label-live.png`.
- Hydracja operatorowych etykiet payloadów akcji została przeniesiona do
  istniejącego `wilq/actions/operator_labels.py`; statusy, wymagane bramki,
  typy rekomendacji/match/level Ads i status WordPress nie są już kodowane w
  service. Live strategy action po restarcie zachowuje 2 evidence IDs,
  `apply_allowed=false`, `Zapis zablokowany`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/operator-labels-live.png`.
- Read-only deduplikacja i grupowanie faktów metrycznych zostały przeniesione do
  istniejącego `wilq/actions/metric_utils.py`; service zachowuje fasady, a
  najnowszy fakt po `(source_connector, name, dimensions)` oraz sortowanie po
  `collected_at` pozostają bez zmian. Live po restarcie: `/api/actions` HTTP 200,
  21 akcji, 0 write-capable; strategy action ma 2 evidence IDs i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/metric-utils-live.png`.
- Localo fallback po probe-only faktach jest teraz w istniejącym
  `wilq/actions/localo/visibility.py`, z callbackami na storage i refresh runs;
  runtime po rozgrzaniu zachowuje 10 metryk, evidence i `apply_allowed=false`.
  Browser proof: `.local-lab/proof/continuation-2026-07-12/localo-metric-fallback-live.png`.
- `wilq-seo-zbre` jest domknięty: detail akcji korzysta z kopii istniejącego
  prewarmed registry cache, a świeży audit/review gate pozostaje nakładany przy
  każdym odczycie. Cold Localo detail po restarcie: HTTP 200 w `0.013299 s`,
  10 metryk, evidence i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/localo-cold-fixed-live.png`.
- Preview payload extraction jest teraz w istniejącym
  `wilq/actions/payload_readiness.py`; wspólny parser zachowuje priorytet
  WordPress/budget/custom/negative/ngram, `payload_preview` i ostatni fallback
  wierszy z `apply_allowed`. Live Localo i Ads detail po restarcie zachowują
  evidence, blokadę zapisu i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/payload-readiness-live.png`.
- Review-gate buildery `required_checks` i `operator_checklist` są teraz w
  istniejącym `wilq/actions/review_gate.py`; service zachowuje tylko callbacks,
  a Localo/Ads detail zachowuje 5 checks, 5 checklist, świeży gate i
  `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/review-gate-builders-live.png`.
- Najnowszy Google Ads `vendor_read` jest wybierany w istniejącym
  `wilq/actions/google_ads/business_context.py` z deterministycznym
  tie-breakerem `(completed_at|started_at, id)`; service zachowuje tylko I/O.
  Live Ads detail ma 2 evidence IDs, 5 checks, `kontrola WILQ poprawna` i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-vendor-read-selection-live.png`.
- Latest Google Ads metric facts są filtrowane w
  `google_ads/business_context.py` tylko dla completed vendor-read i właściwego
  connectora; service zachowuje I/O callback. Ads strategy detail po restarcie
  nadal ma 2 evidence IDs, `kontrola WILQ poprawna` i `apply_allowed=false`;
  browser proof:
  `.local-lab/proof/continuation-2026-07-12/ads-latest-facts-live.png`.
- Action detail proof po restart pokazuje cztery typed WordPress preview cards,
  canonical/public URL rows i blocked claims; artefakt jest w
  `.local-lab/proof/continuation-2026-07-12/action-preview-cards.png`.
- `4wwo` ma teraz istniejący `/api/connectors` rozszerzony o typed
  `refresh_state`: stan odczytu, `refresh_allowed`, ostatni run, safe next step i
  affected decisions. `/settings` pokazuje tę informację ponad ręcznym CTA;
  browser proof jest w `.local-lab/proof/4wwo-sources-refresh-state.png`.
- Aktualne screenshoty desktop/mobile/action są w lokalnym, ignorowanym
  `.local-lab/proof/independent-review-2026-07-10/`.
- Full cold E2E ma jawne otwarte blockers; nie nazywaj całego `verify.sh`
  zielonym, dopóki nie zostaną rozwiązane. Goal 005 nadal czeka na realny Wilku
  UAT albo owner defer.

## Ostatni seam audytowy

- Selektory najnowszych zdarzeń preview/confirmation/impact oraz mutation audit
  są teraz własnością istniejącego `wilq/actions/audit_store.py`; `service.py`
  deleguje bez zmiany typów eventów, kolejności `created_at` ani świeżej
  walidacji/review gate. Focused audit/review tests (10 passed), a live Ads i
  Localo detail zachowuje evidence, `Zapis zmian zablokowany` oraz
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/audit-selectors-live.png`.
- Generyczna projekcja `preview_items` (typed cards i bezpieczne surowe rows)
  jest teraz w istniejącym `wilq/actions/payload_readiness.py`; service
  zachowuje callbacki etykiet i ten sam limit/kontrakt candidate ID. Focused
  payload/preview/confirmation tests: 19 passed, a live Ads detail zachowuje
  evidence, `Zapis zmian zablokowany` i `apply_allowed=false`. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/payload-items-live.png`.
- Wspólne fabryki preview row, state/readiness labels, string-list sanitization
  i preview-contract label są teraz w `wilq/actions/payload_readiness.py`;
  service nie duplikuje tego copy. Focused payload suite: 20 passed, a live
  Ads detail zachowuje evidence, `Zapis zmian zablokowany` i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/payload-labels-live.png`.
- Google Ads formatter wartości micros jest teraz w istniejącym
  `wilq/actions/google_ads/business_context.py`; service nie posiada już tego
  Ads-specific helpera. Brak wartości pozostaje `kwota niepotwierdzona`.
  Focused Ads preview suite: 26 passed, a live Ads action zachowuje evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/money-label-live.png`.
- Summary podglądu akcji jest teraz w istniejącym
  `wilq/actions/action_blockers.py`; service zachowuje tylko orkiestrację.
  Zachowano polski komunikat braku zapisu i count pozycji. Focused
  preview/confirmation/review tests: 26 passed, a live Ads detail zachowuje
  evidence, `Zapis zmian zablokowany` i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/preview-summary-live.png`.
- Składanie szczegółów human review jest teraz w istniejącym
  `wilq/actions/review_gate.py`; service zachowuje callbacki content URL/draft
  readiness. Focused preview/confirmation/review tests: 26 passed, a live Ads
  detail zachowuje evidence, `Zapis zmian zablokowany` i `apply_allowed=false`;
  browser proof: `.local-lab/proof/continuation-2026-07-12/review-details-live.png`.
- Redakcja technicznych szczegółów audytu jest teraz w istniejącym
  `wilq/actions/audit_store.py`; service przekazuje callbacki etykiet review.
  Focused audit/preview/review tests: 29 passed, a live Ads detail zachowuje
  evidence, `Zapis zmian zablokowany` i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/audit-details-live.png`.
- Projekcja etykiet `ActionReviewGate` jest teraz w istniejącym
  `wilq/actions/operator_labels.py`; service zachowuje callbacki review outcome
  i count blockerów. Focused audit/preview/review tests: 30 passed, a live Ads
  detail zachowuje evidence, `Zapis zmian zablokowany` i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/gate-labels-live.png`.
- Projekcja `AuditEvent` dla operatora jest teraz w istniejącym
  `wilq/actions/audit_store.py`; service zachowuje callbacki etykiet review.
  Focused audit/preview/review tests: 31 passed, a live Ads detail zachowuje
  evidence, `Zapis zmian zablokowany` i `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/event-projection-live.png`.
- Składanie operatorowego `ActionObject` view-modelu jest teraz w istniejącym
  `wilq/actions/operator_labels.py`; service przekazuje callbacki typed
  projection. Focused audit/preview/review tests: 32 passed, a live Ads detail
  zachowuje evidence, `Zapis zmian zablokowany` i `apply_allowed=false`;
  browser proof: `.local-lab/proof/continuation-2026-07-12/action-projection-live.png`.
- Filtr raw human-review audit events dla content refresh jest teraz w
  istniejącym `wilq/actions/content_review_details.py`; service nie posiada
  content-specific wyjątku. Focused audit/preview/review tests: 33 passed, a
  live Ads detail zachowuje evidence, `Zapis zmian zablokowany` i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/content-filter-live.png`.
- Wyznaczanie `operator_next_step` dla mutation readiness jest teraz w
  istniejącym `wilq/actions/mutation_readiness.py`; service deleguje bez zmiany
  kolejności blockerów ani fail-closed apply. Focused mutation/audit/preview/
  review tests: 34 passed, live readiness zachowuje `vendor_write_possible=false`;
  browser proof: `.local-lab/proof/continuation-2026-07-12/mutation-next-live.png`.
- Reguła `vendor_write_possible` jest teraz w istniejącym
  `wilq/actions/mutation_readiness.py`; service deleguje bez zmiany bramki
  `apply + adapter + payload readiness`. Live readiness nadal raportuje
  `vendor_write_possible=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/vendor-write-live.png`.
- WordPress draft write-readiness requirements są teraz w istniejącym
  `wilq/actions/wordpress_mutation_requirements.py`; service deleguje bez
  zmiany typed requirements i fail-closed authorization. Live readiness nadal
  raportuje `vendor_write_possible=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/wp-readiness-live.png`.
- Budowanie `ActionMutationAuditRecord` i mutation summary jest teraz w
  istniejącym `wilq/actions/audit_store.py`; service deleguje assembly bez
  zmiany redaction i external-write flags. Live readiness nadal raportuje
  `vendor_write_possible=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/mutation-audit-live.png`.
- Mapowanie błędów apply na event audytu jest teraz w istniejącym
  `wilq/actions/audit_store.py`; service zachowuje kompatybilną fasadę.
  Live Ads detail nadal zachowuje evidence, `Zapis zmian zablokowany` i
  `apply_allowed=false`; browser proof:
  `.local-lab/proof/continuation-2026-07-12/apply-event-live.png`.
- Odczyt env `WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES` jest teraz w istniejącym
  `wilq/actions/wordpress_mutation_requirements.py`; service nie duplikuje
  WordPress write policy. Live readiness pozostaje fail-closed; browser proof:
  `.local-lab/proof/continuation-2026-07-12/wp-env-live.png`.
- Formatowanie blockerów wykonania WordPress draft jest teraz w istniejącym
  `wilq/content/handoff/wordpress_execution.py`; service deleguje typed result
  bez zmiany fail-closed labels/reasons i redacted trace. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/wp-errors-live.png`.
- Rozpoznawanie obsługiwanego mutation adaptera jest teraz w istniejącym
  `wilq/actions/mutation_contract.py`; canonical WordPress draft-only operation
  pozostaje jedyną obsługiwaną ścieżką. Browser proof:
  `.local-lab/proof/continuation-2026-07-12/adapter-boundary-live.png`.
- Buildery `wordpress_draft_write_readiness` i
  `wordpress_draft_activation_packet` są teraz własnością istniejącego
  `wilq/actions/wordpress_mutation_requirements.py`; `service.py` deleguje
  bez zmiany kontraktu. Focused mutation readiness/action tests i live API
  smoke przechodzą, a apply nadal raportuje `vendor_write_possible=false`.
- Usunięto nieużywany helper `_mutation_requirement` z `service.py`; `rg` nie
  znajduje pozostałych referencji, bez zmiany kontraktu readiness ani safety
  loop. 48 focused testów akcji przechodzi.
- `service.py` nie ma już lokalnej fasady `_wordpress_draft_execution_errors`;
  apply używa bezpośrednio istniejącego formattera WordPress execution.
  Focused mutation/WordPress tests przechodzą, a fail-closed labels/reasons
  pozostają bez zmian.
- Usunięto nieużywany `_mutation_audit_summary` i import z `service.py`; aktywna
  implementacja nadal znajduje się w `wilq/actions/audit_store.py`. 21 focused
  audit/mutation tests przechodzi bez zmiany eventów audytu.
- `service.py` korzysta bezpośrednio z `mutation_readiness.vendor_write_possible`
  zamiast lokalnej fasady; live WordPress readiness nadal pokazuje
  `vendor_write_possible=false`, a apply pozostaje fail-closed.
- Usunięto lokalne fasady `_wordpress_draft_*`, `_apply_audit_event_type` i
  `_action_mutation_audit_record`; service wywołuje istniejące moduły readiness,
  audit i WordPress bezpośrednio. API nadal pokazuje
  `ready_to_request_apply=false` i `publication_allowed=false`.
- Typed `WordPressDraftApplyCapability` oraz exact binding bieżącego snapshotu
  są teraz własnością `wilq/actions/wordpress_mutation_requirements.py`;
  service ma tylko kompatybilną fasadę. Po restarcie managed stack API jest
  zdrowe, a browser proof desktop/mobile potwierdza marketer-facing route i
  preview-only dev boundary:
  `.local-lab/proof/continuation-2026-07-12/wordpress-capability-mobile-after-restart.png`.
- Wykonanie obsługiwanego adaptera WordPress jest teraz w
  `wilq/actions/wordpress_mutation_requirements.py`; service deleguje bez
  duplikowania live/dry-run result assembly. Cold diagnostics nadal ma znany
  koszt rozgrzewki (pierwszy readiness request >20 s, po rozgrzaniu HTTP 200
  w 18.9 s), więc nie przypisuję tego temu seamowi bezpośrednio. Safety
  pozostaje fail-closed.
- `wilq-seo-c9h9.14` zamknięto jako external-state false positive: po zamknięciu
  osieroconych Chrome quiet cold queue wyniósł 0.003760 s, readiness 1.442645 s.
  Niezależnie utrwalono bezpieczne hardening: diagnostics cache 60 s i cached
  activation packet, z zachowaniem jawnej invalidacji po refresh/mutacji.
- Browser proof po quiet stack: `.local-lab/proof/continuation-2026-07-12/c9h9-14-cache-mobile.png`.
- `_action_review_gate` jest teraz własnością `wilq/actions/review_gate.py`;
  `service.py` przekazuje callbacki domenowe przez mały typed seam. Status
  review, blockerów, confirm/impact/mutation audit i apply safety pozostaje
  bez zmian.
- Preflight apply blocker ordering jest teraz własnością
  `wilq/actions/action_blockers.py`; service nadal kontroluje kolejność
  validate → preview → review → confirm → impact → audit → adapter, ale reguły
  blockerów są w jednym typed owner module.
- Apply `AuditEvent` assembly jest teraz własnością `audit_store.py`; event type,
  label, summary, actor i evidence nie są już składane lokalnie w service.
  Mutation audit i fail-closed status pozostają bez zmian.
- Routing typed previewów jest teraz własnością
  `wilq/actions/action_previews.py`; dispatcher używa map kontraktów/action types
  i deleguje renderowanie do modułów domenowych. `service.py` zachowuje tylko
  callbacki operator labels oraz publiczny compatibility wrapper Demand Gen;
  usunięto 311 lokalnych preview wrapperów. Merchant dispatcher regression,
  focused action preview/object tests, Ruff, mypy, complexity, diff check i
  managed API smoke przechodzą; payloady, safety i endpointy pozostają bez zmian.
- Konstrukcja human-review `AuditEvent` jest teraz własnością
  `wilq/actions/audit_store.py` (`build_human_review_audit_event`); service
  przekazuje tylko dane review i nadal aktualizuje review gate oraz projekcję
  operatora. Event type, actor, summary, details i evidence pozostają bez
  zmian, a focused audit/review/preview tests, Ruff, mypy i diff check przechodzą.
- Dry-run `action_preview_generated` event jest teraz składany przez
  `audit_store.py` (`build_preview_audit_event`); `preview_action` zachowuje
  `mutation_allowed=false`, bieżące blockery/status i istniejącą projekcję
  operatora. Audit/preview tests, Ruff i mypy przechodzą, bez zmian w API,
  payloadach lub adapterach vendorów.
- Confirmation `AuditEvent` jest teraz składany przez
  `audit_store.build_confirmation_audit_event`; `confirm_action` nadal posiada
  blocker evaluation, Ads target summary i review-gate orchestration. Event
  type/label, actor, summary i evidence nie zmieniły się; 39 focused tests,
  Ruff, mypy, diff check oraz managed API readiness smoke przechodzą.
- Impact-check `AuditEvent` jest teraz składany przez
  `audit_store.build_impact_check_audit_event`; `impact_check_action` zachowuje
  status checked/blocked, metryki, source connectors, blocker i union evidence.
  Focused audit/review/preview tests, Ruff, mypy, diff check i API smoke
  przechodzą; brak zmian w measurement claims albo vendor writes.
- `wilq-seo-xu5s` dodał typed API-owned policy do
  `ConnectorRefreshState.automatic_refresh`: eligibility, reason, Polish copy,
  safe next step i 900 s cooldown. `wilq-seo-3gre` konsumuje już wyłącznie
  `eligible=true`: `/settings` zleca jeden istniejący async `vendor_read` na
  connector identity, odpytuje refresh-run i po terminalnym wyniku invaliduje
  sources oraz tylko API-wskazane decision view-models. Nie ma nowego endpointu
  ani write-capable action.
  Live dashboard po odczytach Ads, Merchant i Localo pokazuje 0 źródeł do
  odświeżenia; LinkedIn/Facebook nadal są uczciwie zablokowane brakiem dostępu.

## Resume

1. Potwierdź clean/synced `main` po commicie `3gre`; `3gre` i parent `4wwo`
   są już zamknięte w Beads.
2. Odczytaj live connectors, diagnostics i queue; nie używaj liczb z pamięci.
3. `4wwo` jest zamknięty; nie twórz drugiego dashboardowego triggera ani
   reguły stale/cooldown w React.
4. `jnra.1`, `jnra.2` i `jnra.3` są zamknięte po parity/cache, Keyword Planner
   i review-gate safety proof. Kontynuuj `jnra` wyłącznie od kolejnego małego,
   potwierdzonego seamu z aktualnego complexity/runtime review; nie przenoś
   ponownie gotowych mutation/readiness ani WordPress preview boundaries.
5. `r564.3` jest zamknięty po świeżym browser proof 390×844; parent `r564`
   nadal wymaga evidence-backed candidate density bez sztucznego tematu.
6. `r564.5` i `r564.6` są zamknięte. Nie zgaduj usługi z `service_fit`: istnieje
   tylko typed binding snapshotu, a blocked snapshot pozostaje `not_evaluated`.
7. Parent `r564` jest zablokowany zewnętrznie przy 1 actionable z wymaganych 3;
   nie twórz tematu dla wypełnienia progu. `3bst.7` i `c9h9.17` są domknięte;
   `c9h9.18` ma osobno wydzielić Ahrefs branch tactical queue przed przeniesieniem
   compiled matcher do tego monolitu.
