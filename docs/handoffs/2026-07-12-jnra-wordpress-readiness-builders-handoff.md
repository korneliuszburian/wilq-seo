# Handoff: `jnra` WordPress readiness builders — 2026-07-12

## Decyzja

Buildery `wordpress_draft_write_readiness` i
`wordpress_draft_activation_packet` zostały przeniesione do istniejącego
`wilq/actions/wordpress_mutation_requirements.py`. `service.py` zachowuje
kompatybilne fasady dla istniejących call sites, ale nie posiada już lokalnej
logiki budowania tych kontraktów.

## Dowody

- `tests/actions/test_mutation_readiness_contracts.py` i
  `tests/actions/test_action_mutation_readiness_api.py`: 7 focused testów
  przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą.
- Live API: health `ok`; mutation readiness dla WordPress nadal pokazuje
  `vendor_write_possible=false`, evidence IDs, blokery review/confirm i
  `publication_allowed=false`.
- Dashboard route `content-workflow` odpowiada; brak zmian UI, nowych endpointów,
  vendor writes, credentiali lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; nie utworzono duplikatu.

## Następny slice

Wykonać świeży audyt pozostałej logiki apply w `service.py`; wybrać jeden
istniejący owner moduł tylko wtedy, gdy seam ma zachowanie testowalne i nie
przenosi orkiestracji ActionObject poza service boundary.

## Otwarte blokery

- Content queue: `blocked` przez `not_enough_actionable_candidates` (1
  actionable candidate przy wymaganych 3).
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
