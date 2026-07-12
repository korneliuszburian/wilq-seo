# Handoff: `jnra` Localo visibility preview renderer — 2026-07-12

## Decyzja

Wydzieliłem renderer operator-facing dla `act_review_localo_visibility_facts` z
`wilq/actions/service.py` do `wilq/actions/localo/visibility_preview.py`.
Service zachowuje dispatcher i przekazuje callbacks do typed metric rows,
labels oraz safety state; reguły Localo i kontrakty pozostają w istniejącym
module `visibility.py`.

## Dowód produktu

- Live API: `GET /api/actions/act_review_localo_visibility_facts` zwrócił
  `mode=prepare`, `connector=localo`, 1 evidence ID i kartę
  `localo_visibility_review`.
- Karta pokazuje agregaty widoczności, dozwolone/brakujące odczyty, warunki
  sprawdzenia i blocked claims. `apply_allowed=false`,
  `api_mutation_ready=false`.
- Evidence: `ev_refresh_refresh_localo_30cd98463f06`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/localo-visibility-preview-cards.png`.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k local_visibility_preview`:
  1 passed.
- Ruff i mypy dla service/new module/test: passed.
- Complexity changed audit: brak nowych naruszeń; frozen `service.py` pozostaje
  znanym hotspotem.
- `git diff --check`: passed.
- Tymczasowy live schema debug test został usunięty po potwierdzeniu, że
  ActionObject i mutation-readiness parse przechodzą.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam mieści się w jego bounded
  extraction scope, bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na świeżej kolejce contentu: 1 actionable z
  minimum 3.
- Następny turn ma odczytać świeży complexity/runtime stan i wybrać kolejny
  istniejący preview seam; nie wracać do Localo, GA4, n-gramów ani Demand Gen.

## Commit

Implementacja: `a86ceba1` (`refactor: extract localo visibility preview cards`),
wypchnięta na `origin/main`. Ten handoff zostanie domknięty osobnym docs-only
commitem.
