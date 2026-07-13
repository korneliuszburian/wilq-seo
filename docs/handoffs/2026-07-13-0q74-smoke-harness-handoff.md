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
  Campaign Builder, Social i Custom Segments smoke importują wspólny transport;
  wszystkie jedenaście live smoke przechodzą.
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
- `wilq-seo-c9h9.19` zamknięty jako redundantny: marketer review card była już
  w API; pierwszy `null` był cold/prewarm artefaktem.

## Commity

- `7e275f4e` — shared smoke transport harness
- `049bb114` — selected-decision GSC assertion

## Następny slice

Wybrać kolejny konkretny smoke do migracji (najlepiej Content Operator/GA4), a
następnie wydzielić wspólne asercje evidence/source/action safety.
Nie zmieniać product logic w harnessie. Największe funkcje `main` nadal są
otwarte i wymagają osobnych, testowalnych modułów asercji.

## Blokery

- Goal 005 nadal wymaga realnego Wilku UAT albo owner defer z residual risk.
- LinkedIn/Facebook credentials pozostają brakujące; nie traktować social jako
  gotowego workflow.
