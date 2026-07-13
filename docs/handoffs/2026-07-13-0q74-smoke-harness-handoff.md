# Handoff — 2026-07-13 — 0q74 smoke harness

## Stan

- `wilq-seo-c9h9.4` i `wilq-seo-d380` są zamknięte po aktualnym proofie.
- Live WILQ API po managed restart: `ok`, 104362 metric facts, 4580 refresh
  runs, 12 connectorów / 9 skonfigurowanych; content queue fresh, 2 kandydatów,
  1 actionable, blocker `not_enough_actionable_candidates`.
- `wilq-seo-0q74` pozostaje otwarty.

## Wykonane

- Dodano `scripts/skill_smoke_harness.py` z `request_json` i wspólnym
  `has_polish_metric_source_guardrails`.
- Ads, GSC, Content Strategist, Merchant, Localo, GA4, Demand Gen, Ahrefs,
  Campaign Builder, Social, Custom Segments i Content Operator smoke importują
  wspólny transport; wszystkie dwanaście live smoke przechodzą.
- GSC smoke assertion została poprawiona, aby porównywać
  `review_action_ids` z decyzją wskazaną przez `technical_decision_id`, a nie z
  globalną listą akcji. GSC smoke przechodzi po poprawce.
- Content Strategist smoke ma ten sam fail-closed wyjątek dla Ahrefs-only
  decyzji: brak akcji jest poprawny, a akcja nie może zostać zmyślona.
- Merchant smoke przechodzi z tym samym timeout/transport seamem; blocked claims
  nadal obejmują reapproval, revenue i automatyczne zmiany feedu.
- Localo smoke przechodzi bez refresh write (`access_ready`, 4 lokalizacje, 23
  monitorowane frazy, action review-only), zachowując blokadę zmian GBP i
  publikacji.
- GA4 smoke przechodzi z live contractem `fix_measurement`/`review_traffic_quality`;
  `(not set)` pozostaje problemem pomiaru, a ROAS/przychód są blokowane.
- Demand Gen smoke przechodzi: 18 kampanii bazowych, 0 kampanii Demand Gen,
  status `blocked`, action review-only; nie powstaje rekomendacja uruchomienia.
- Ahrefs smoke przechodzi: 338 gap facts, 2 authority facts, 6 manual
  cross-check candidates i zero action IDs; słabe podobieństwo nie odblokowuje
  briefu ani publikacji.
- Campaign Builder smoke przechodzi z review-only Ads planem; Social smoke
  przechodzi z brakującymi credentials i historią postów jawnie zablokowanymi.
- Custom Segments smoke przechodzi z 1 kandydatem i jawnie zablokowanym
  Keyword Planner/forecast/audience size oraz `apply_allowed=false`.
- Content Operator smoke przechodzi z kolejką `blocked` (2 kandydatów, 1
  actionable przy minimum 3), dry-run WordPress i `publish_allowed=false`.
- Pierwszy shared assertion seam dodany do harnessu: `require_polish_language`
  oraz `require_evidence_sources`; GA4, Merchant i GSC używają tych samych
  guardrails. Ich live smoke przechodzą po migracji.
- Drugi assertion seam: `validate_action_ids` centralizuje validate → status
  valid → błędy dla Campaign Builder i Social; oba live smoke nadal przechodzą.
- Complexity re-audit po tych zmianach: 443 Python files / 139381 non-empty LOC,
  changed files 0, changed-code violations 0. Pozostają potwierdzone hotspoty:
  Ads `main` 1006 LOC/290 branches, GSC `main` 499/132, Merchant 367/115,
  Localo 302/92 i Content Strategist `validate_content_action_preview`
  171/67.
- Content Strategist preview seam jest teraz w
  `scripts/content_action_preview.py`; jego własny moduł mieści się w lokalnym
  budżecie. Pozostały w dotkniętym smoke file istniejące hotspoty: `main`
  199 LOC/26 branches, `validate_content_decision_queue` 26 branches i
  `validate_wordpress_draft_handoff_action_preview` 29 branches.
- Drugi Content Strategist seam jest domknięty: asercje decision queue i
  WordPress draft handoff są w `scripts/content_strategy_assertions.py`.
  Live smoke, Ruff i `git diff --check` przechodzą. Re-audit zmienionego kodu
  zostawia tylko `smoke_skill_contract.py::main` (206 LOC/26 branches); nowy
  moduł assertion mieści się w budżecie. Następny slice powinien rozdzielić
  orkiestrację `main`, zanim zaczniemy Ads.
- Orkiestracja została wydzielona do `scripts/content_strategy_runtime.py`.
  Smoke main ma teraz 94 LOC/11 branches, runtime zachowuje walidację health,
  context-pack, diagnostics, actionów, briefu i konektorów. Live smoke, Ruff,
  complexity i diff check przechodzą; nie zmieniono API ani write safety.
- GSC refresh/Search Analytics contract jest w
  `scripts/gsc_refresh_contract.py`; live smoke przechodzi (1 978 query/page
  metric facts), a main spadł do 434 LOC/122 branches. Ads payload jest duży:
  endpoint ma 8,6 MB, full-context 11,2 MB; pierwsze krótkie uruchomienie
  przekroczyło limit sesji, ale dłuższy live proof został zaliczony.
- Ads bootstrap jest wydzielony do `scripts/ads_smoke_runtime.py`. Długi live
  smoke (około 73 s) kończy się `exit 0`, z 6 poprawnymi action validations,
  18 kampaniami i `apply_allowed=false`; `main` ma 970 LOC/274 branches.
- Ads readiness/budget assertion seam jest teraz w
  `scripts/ads_readiness_assertions.py`; drugi długi live smoke kończy się
  `exit 0`, a `main` ma 934 LOC/255 branches. Następny seam może wyjmować
  pojedynczy kontrakt raportowania, bez zmiany API ani safety.
- Recommendations read contract jest w
  `scripts/ads_recommendation_assertions.py`, z osobnymi walidatorami ready i
  packed preview. Live smoke przechodzi po zmianie; `main` ma 838 LOC/214
  branches. Następny seam może dotyczyć impression-share/change-history.
- Impression-share read contract jest w
  `scripts/ads_impression_share_assertions.py`; live smoke przechodzi, a
  `main` ma 820 LOC/207 branches. Następny seam: change-history/readiness.
- Change-history read contract jest w
  `scripts/ads_change_history_assertions.py`; live smoke przechodzi, a
  `main` ma 794 LOC/196 branches. Następny seam: change-impact readiness.
- Change-impact readiness jest w
  `scripts/ads_change_impact_assertions.py`; live smoke przechodzi, a
  `main` ma 770 LOC/180 branches. Blokady pre/post performance window,
  human review i `apply_allowed=false` są nadal jawne.
- Search-term review summary jest w
  `scripts/ads_search_term_review_assertions.py`; live smoke przechodzi, a
  `main` ma 756 LOC/174 branches. Następny seam: search-term safety.
- Search-term safety contract jest w
  `scripts/ads_search_term_safety_assertions.py`; live smoke przechodzi, a
  `main` ma 737 LOC/167 branches. Następny seam: keyword-match context.
- Keyword-match context contract jest w
  `scripts/ads_keyword_match_assertions.py`; live smoke przechodzi, a
  `main` ma 723 LOC/161 branches. Następny seam: Keyword Planner contract.
- Keyword Planner contract jest w
  `scripts/ads_keyword_planner_assertions.py`; live smoke przechodzi, a
  `main` ma 692 LOC/150 branches. Enrichment i forecast/audience-size nadal
  pozostają jawnie zablokowane.
- Custom-segments contract jest w
  `scripts/ads_custom_segments_assertions.py`; live smoke przechodzi, a
  `main` ma 675 LOC/140 branches. Audience-size, skuteczność i zapis kierowania
  pozostają jawnie zablokowane.
- Search-term n-gram contract jest w
  `scripts/ads_search_term_ngram_assertions.py`; live smoke przechodzi, a
  `main` ma 664 LOC/135 branches. N-gram-specific change-preview blocker
  pozostaje jawny; następny seam to negative-keyword contract.
- Negative-keyword contract jest w
  `scripts/ads_negative_keyword_assertions.py`; live smoke przechodzi, a
  `main` ma 644 LOC/125 branches. Payload preview i action ID są sprawdzane,
  automatyczne wykluczenie pozostaje zablokowane.
- Ads review action loop korzysta ze wspólnego `validate_action_ids` harnessu;
  live smoke przechodzi z 6 walidacjami `valid/status=valid`, a `main` ma 633
  LOC/122 branches. Następny seam: compact raportu/briefu.
- Ads brief compaction jest w `scripts/ads_report_compaction.py`; live smoke
  przechodzi, a `main` ma 619 LOC/121 branches. Output pozostaje ograniczony do
  operatorowych evidence/action fields, bez vendor payloadów.
- Connector status compaction używa tego samego modułu; live smoke przechodzi,
  a `main` ma 607 LOC/120 branches. Statusy są ograniczone do pól potrzebnych
  do freshness/blocker decyzji, bez zmiany API.
- Context-pack lineage assertion jest w `scripts/ads_context_lineage.py`; live
  smoke przechodzi, a `main` ma 607 LOC/120 branches. Knowledge card/expert
  rule IDs są wymagane w compact context; następny seam to final report shaping.
- Final report shaping helpers są w `scripts/ads_report_compaction.py`; live
  smoke przechodzi, output pozostaje compact/operator-safe, a `main` ma 607
  LOC/120 branches. Następny potwierdzony zakres: kolejny skill smoke hotspot.
- GSC content action validation używa wspólnego `validate_action_ids`; live
  smoke przechodzi z 1 walidacją `valid/status=valid`, a `main` ma 425 LOC/120
  branches. Następny GSC seam: compact brief/status.
- GSC brief/status compaction jest w `scripts/gsc_report_compaction.py`; live
  smoke przechodzi (4 brief items, 3 konektory), a `main` ma 398 LOC/118
  branches. Output pozostaje ograniczony do operatorowych fields.
- GSC freshness/Search Analytics assertions są w
  `scripts/gsc_freshness_assertions.py`; live smoke przechodzi ze stanem
  `fresh`, a `main` ma 336 LOC/82 branches. Następny seam: decision parity.
- GSC decision parity jest w `scripts/gsc_decision_parity.py`; live smoke
  przechodzi z 1 scoped decision, evidence/action subset parity i blokadą
  Ahrefs scope. `main` ma 315 LOC/72 branches. Następny seam: marketer card
  parity.
- GSC marketer decision card parity jest w
  `scripts/gsc_marketer_card_assertions.py`; live smoke przechodzi z kartą
  `Karta decyzji dla Wilka`, review fields i selected action IDs. `main` ma 278
  LOC/59 branches. Następny re-audyt wybierze Merchant/Localo hotspot.
- Merchant Feed context parity jest w
  `scripts/merchant_context_parity.py`; live smoke przechodzi z 19 issue items,
  evidence/action parity i price readiness parity. Merchant `main` ma 343
  LOC/107 branches. Następny seam: product sample/performance readiness.
- Merchant product sample/performance readiness jest w
  `scripts/merchant_product_readiness.py`; live smoke przechodzi ze statusem
  performance `blocked`, a `main` ma 288 LOC/87 branches. Blokady przychodu,
  ROAS i write pozostają jawne.
- Merchant price impact readiness jest w
  `scripts/merchant_price_readiness.py`; live smoke przechodzi ze statusem
  `blocked`, preview contract i `apply_allowed=false`. `main` ma 242 LOC/67
  branches. Następny seam: Merchant issue/decision queue parity.
- `wilq-seo-c9h9.19` zamknięty jako redundantny: marketer review card była już
  w API; pierwszy `null` był cold/prewarm artefaktem.

## Commity

- `7e275f4e` — shared smoke transport harness
- `049bb114` — selected-decision GSC assertion

## Następny slice

Następny slice: wydzielić Content Strategist decision-queue/handoff assertions
do kolejnych nazwanych helperów, zachowując live smoke; dopiero potem wejść w
największy Ads `main`.
następnie wydzielić wspólne asercje evidence/source/action safety.
Nie zmieniać product logic w harnessie. Największe funkcje `main` nadal są
otwarte i wymagają osobnych, testowalnych modułów asercji.

## Blokery

- `wilq-seo-pidl`: query-client defaults extracted from `App.test.tsx` into
  `queryClientDefaults.test.ts`; focused Vitest 31/31, dashboard lint and
  typecheck pass. No API or UI behavior changed.
- Shared `ConnectorRefreshRun` fixture now lives in
  `connectorRefreshRun.fixture.ts`; App and component test consume the same
  typed data. Focused Vitest 32/32, lint/typecheck pass.
- Merchant output shaping and action/brief/connector runtime assertions now
  live in named helpers; live smoke remains 19 occurrences, 14 clusters and 7
  decisions, and changed-code complexity passes without an exception.
- Localo smoke is now split into refresh, runtime and report helpers. Live
  proof: `access_ready`, refresh `completed`, one review action; claim/write
  gates remain blocked as designed. Ruff, smoke and complexity pass.
- Custom Segments smoke is now split into candidate assertions, runtime
  transport and report shaping. Live proof: read contract `ready`, one
  candidate, one action; apply remains blocked. Ruff, smoke and complexity pass.
- Ahrefs smoke is now split into contract assertions, runtime transport and
  report shaping. Live proof: `manual_required`, 8 gap records, 0 actions;
  freshness/evidence/blocked-claim gates remain explicit. Ruff, smoke and
  complexity pass.
- Demand Gen smoke now delegates readiness/read-contract assertions to
  `demand_gen_assertions.py`. Live proof: `blocked`, 18 evaluated campaigns,
  one review action, apply/write disabled; Ruff, smoke and complexity pass.
- GA4 smoke now delegates route/context/readiness and decision assertions to
  `ga4_assertions.py`. Live proof: conversion readiness `ready`, four
  decisions, one action; evidence/source trace and measurement-claim gates pass.
- Goal 005 nadal wymaga realnego Wilku UAT albo owner defer z residual risk.
- LinkedIn/Facebook credentials pozostają brakujące; nie traktować social jako
  gotowego workflow.
- Merchant issue/decision queue parity: `scripts/merchant_issue_parity.py`;
  live smoke 19 occurrences, 14 clusters, 7 decisions; API unchanged.
