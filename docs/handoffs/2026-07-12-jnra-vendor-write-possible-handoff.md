# Handoff: `jnra` vendor-write readiness predicate — 2026-07-12

## Decyzja

Predykat `vendor_write_possible` został przeniesiony z
`wilq/actions/service.py` do istniejącego `wilq/actions/mutation_readiness.py`.
Zachowano fail-closed warunek: adapter, tryb `apply`, `payload_apply_allowed`
oraz `api_mutation_ready` muszą być spełnione jednocześnie.

## Dowody

- Kontrakt testuje `True` tylko przy wszystkich bramkach oraz `False` dla braku
  adaptera albo `api_mutation_ready=false`.
- Source Ruff/mypy, focused mutation tests, complexity i `git diff --check`
  przechodzą; `service.py` ma 2223 LOC.
- Po managed restart `/api/health` jest `ok`; live WordPress readiness raportuje
  `vendor_write_possible=false`, a Ads detail zachowuje evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/vendor-write-live.png`.
- Commit implementacji: `4845101` wypchnięty na `origin/main`.
- Brak nowych endpointów, vendor writes, credential changes lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress`; nie utworzono duplikatu.

## Następny slice

Świeży odczyt pozostałych helperów końcówki `service.py`; kolejny seam tylko
przy istniejącym module właścicielskim i focused behavior test.

## Otwarte blokery

- Content queue: `blocked`, `not_enough_actionable_candidates` (1 actionable,
  minimum 3).
- Goal 005: brak realnego Wilku UAT albo owner defer.
