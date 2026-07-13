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
- Ads i GSC smoke importują wspólny transport; Ads live smoke przechodzi.
- GSC smoke assertion została poprawiona, aby porównywać
  `review_action_ids` z decyzją wskazaną przez `technical_decision_id`, a nie z
  globalną listą akcji. GSC smoke przechodzi po poprawce.
- `wilq-seo-c9h9.19` zamknięty jako redundantny: marketer review card była już
  w API; pierwszy `null` był cold/prewarm artefaktem.

## Commity

- `7e275f4e` — shared smoke transport harness
- `049bb114` — selected-decision GSC assertion

## Następny slice

Wybrać kolejny konkretny smoke do migracji (najlepiej GSC/merchant lub
Ads), a następnie wydzielić wspólne asercje evidence/source/action safety.
Nie zmieniać product logic w harnessie. Największe funkcje `main` nadal są
otwarte i wymagają osobnych, testowalnych modułów asercji.

## Blokery

- Goal 005 nadal wymaga realnego Wilku UAT albo owner defer z residual risk.
- LinkedIn/Facebook credentials pozostają brakujące; nie traktować social jako
  gotowego workflow.
