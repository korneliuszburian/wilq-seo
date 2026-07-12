# Handoff — `jnra` mutation plan seam

Data: 2026-07-12 Europe/Warsaw

## Decyzja

Wydzielono z `wilq/actions/service.py` read-only wybór pierwszej kandydatury
zapisu, plan aktywacji oraz operatorowy następny krok readiness do
`wilq/actions/mutation_plan.py`. To jest seam utrzymaniowy: nie dodaje nowej
akcji, endpointu ani możliwości zapisu.

## Dowody

- `service.py` deleguje do `mutation_plan`, zachowując istniejące typy,
  payloady, blocker codes, polskie komunikaty i kolejność safety gates.
- Focused suite: `tests/actions/test_action_mutation_readiness_api.py`,
  `tests/test_goal_005_completion_check.py` oraz kontrakty review/preview/
  confirmation/validation — zielone.
- Ruff i mypy dla `service.py` oraz `mutation_plan.py` — zielone.
- Complexity: `service.py` 4046 LOC; jedyny raportowany changed-code finding
  to znany frozen-file budget, bez nowego wzrostu; `git diff --check` — zielone.
- Live po managed restart:
  `/api/actions/mutation-readiness` → 21 akcji, `vendor_write_possible_count=0`,
  `would_attempt_vendor_write_count=0`, pierwsza kandydatura
  `act_apply_wordpress_draft_handoff`; publikacja i destructive writes pozostają
  blokowane.
- Kolejny bounded seam wydzielił `mutation_apply_contract` do
  `wilq/actions/mutation_contract.py`. Kontrakt nadal zezwala wyłącznie na
  `create_wordpress_draft`, ma `publication_allowed=false`,
  `destructive_allowed=false`, wymagane audyty i env flagę; pozostałe akcje
  zwracają `None` jak wcześniej. Focused readiness/Goal 005 tests, Ruff, mypy,
  complexity i diff check pozostają zielone; `service.py` ma 4003 LOC.

## Bead

`wilq-seo-jnra` pozostaje `in_progress`. Nie zamykaj go: service.py nadal jest
dużym facade/orchestrator, a następny seam wymaga świeżego complexity review.

## Następny krok

Najpierw odczytaj aktualny `git status`, runtime i complexity, potem wybierz
jedną niedublującą się funkcję z `service.py`. Zachowaj ActionObject flow
`validate → preview → human review → confirm → audit → adapter`; po slice’ie
uruchom focused tests, Ruff, mypy, complexity, live HTTP, `git diff --check`,
commit i push na `origin/main`.
