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
  metric facts), a main spadł do 434 LOC/122 branches. Ads nie został zmieniony:
  aktualny endpoint ma 8,6 MB, full-context 11,2 MB, a pełny smoke kończy się
  bez outputu przed proof; wymaga osobnej diagnostyki pamięci/raportu.
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

- Goal 005 nadal wymaga realnego Wilku UAT albo owner defer z residual risk.
- LinkedIn/Facebook credentials pozostają brakujące; nie traktować social jako
  gotowego workflow.
