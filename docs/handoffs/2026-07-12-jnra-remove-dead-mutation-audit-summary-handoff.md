# Handoff: `jnra` remove dead mutation audit summary — 2026-07-12

## Decyzja

Usunięto nieużywany helper `_mutation_audit_summary` i jego import z
`wilq/actions/service.py`. Aktywna implementacja `mutation_audit_summary`
pozostaje w istniejącym `wilq/actions/audit_store.py` i jest używana przez
builder mutation audit record.

## Dowody

- `rg` potwierdza brak call sites lokalnego helpera po zmianie.
- `tests/actions/test_action_mutation_readiness_api.py`,
  `tests/actions/test_action_evidence_contracts.py` i
  `tests/actions/test_audit_store_contracts.py`: 21 testów przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą.
- Brak zmian eventów audytu, API, UI, vendor writes, credentiali lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; nie utworzono duplikatu.

## Następny slice

Kontynuować świeży audyt apply/readiness helpers; nie usuwać fasad używanych
przez testy lub route boundaries bez sprawdzenia kompatybilności.

## Otwarte blokery

- Content queue: `blocked` przez `not_enough_actionable_candidates` (1
  actionable candidate przy wymaganych 3).
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
