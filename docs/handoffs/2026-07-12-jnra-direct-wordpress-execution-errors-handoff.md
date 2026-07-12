# Handoff: `jnra` direct WordPress execution errors — 2026-07-12

## Decyzja

Usunięto lokalną, jedno-wywołaniową fasadę
`_wordpress_draft_execution_errors` z `wilq/actions/service.py`. Apply używa
bezpośrednio istniejącego `wordpress_draft_execution_errors` z
`wilq/content/handoff/wordpress_execution.py`.

## Dowody

- `rg` nie znajduje już lokalnej fasady ani innych call sites.
- `tests/actions/test_mutation_readiness_contracts.py`,
  `tests/actions/test_action_mutation_readiness_api.py` i
  `tests/content/test_wordpress_execution_api.py`: focused suite przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą.
- Brak zmian endpointów, payloadów, UI, vendor writes, credentiali lub
  publication safety; execution errors nadal są fail-closed i redacted.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; nie utworzono duplikatu.

## Następny slice

Kontynuować audyt apply helperów z aktualnym `rg`; wybierać tylko potwierdzony
dead code lub seam z istniejącym właścicielem i zachowaniem testowalnym.

## Otwarte blokery

- Content queue: `blocked` przez `not_enough_actionable_candidates` (1
  actionable candidate przy wymaganych 3).
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
