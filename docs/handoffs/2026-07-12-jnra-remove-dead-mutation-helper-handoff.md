# Handoff: `jnra` remove dead mutation helper — 2026-07-12

## Decyzja

Usunięto prywatny helper `_mutation_requirement` z
`wilq/actions/service.py`. Aktualny kod i testy nie miały żadnego wywołania;
readiness requirements nadal są budowane przez istniejące moduły
`wordpress_mutation_requirements` i `mutation_readiness`.

## Dowody

- `rg` po `wilq/actions`, `wilq` i `tests` nie znajduje referencji do helpera.
- `tests/actions/test_mutation_readiness_contracts.py`,
  `tests/actions/test_action_mutation_readiness_api.py` i
  `tests/actions/test_action_object_contracts.py`: 48 testów przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą.
- Brak zmian API, UI, endpointów, vendor writes, credentiali lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; nie utworzono duplikatu.

## Następny slice

Ponownie przejrzeć pozostałe apply helpers z aktualnym `rg` i wybrać tylko
potwierdzony seam lub martwy kod; nie przenosić orkiestracji poza service
boundary bez testowalnej korzyści.

## Otwarte blokery

- Content queue: `blocked` przez `not_enough_actionable_candidates` (1
  actionable candidate przy wymaganych 3).
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
