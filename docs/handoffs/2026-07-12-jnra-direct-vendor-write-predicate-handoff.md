# Handoff: `jnra` direct vendor-write predicate — 2026-07-12

## Decyzja

Usunięto jedno-wywołaniową fasadę `_vendor_write_possible` z
`wilq/actions/service.py`. Readiness korzysta bezpośrednio z istniejącego
`vendor_write_possible` w `wilq/actions/mutation_readiness.py`; predicate nadal
wymaga trybu apply, adaptera i obu flag payloadu.

## Dowody

- `tests/actions/test_action_mutation_readiness_api.py`,
  `tests/actions/test_mutation_readiness_contracts.py` i
  `tests/actions/test_action_evidence_contracts.py`: 22 testy przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą.
- Live API health `ok`; WordPress mutation readiness zachowuje evidence IDs,
  `vendor_write_possible=false`, `publication_allowed=false` i blokery audytu.
- Brak nowych endpointów, vendor writes, credentiali, publikacji lub zmian UI.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; nie utworzono duplikatu.

## Następny slice

Świeżo ocenić pozostałe fasady apply/readiness i większy adapter execution;
wybrać tylko seam, który poprawia ownership bez przenoszenia ActionObject
orkiestracji poza service boundary.

## Otwarte blokery

- Content queue: `blocked` przez `not_enough_actionable_candidates` (1
  actionable candidate przy wymaganych 3), mimo świeżych źródeł.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
