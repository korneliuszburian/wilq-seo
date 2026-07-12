# Handoff: `jnra` payload preview item projection — 2026-07-12

## Decyzja

Generyczna projekcja `ActionPreviewItemViewModel` została przeniesiona z
`wilq/actions/service.py` do istniejącego `wilq/actions/payload_readiness.py`.
Moduł przyjmuje callbacki dla polskich etykiet i wierszy, więc nie przejmuje
reguł domenowych ani nie omija ActionObject safety loop.

## Dowody

- Karty zachowują maksymalnie cztery istniejące rows oraz dopinają status zapisu
  i gotowości systemu; surowe payload rows zachowują tytuł/status, limit sześciu
  rows, WordPress `candidate_id` i fallback kontraktu.
- `tests/actions/test_payload_readiness.py`, preview i confirmation contracts:
  `19 passed`.
- Ruff, mypy, complexity i `git diff --check` przechodzą; `service.py` spadł do
  2374 LOC, a istniejący frozen-file budget violation pozostaje jawny.
- Managed stack po restarcie: `/api/health` `ok`; Ads action detail HTTP 200,
  jedna typed preview card, evidence IDs, `zapis zmian zablokowany` i
  `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/payload-items-live.png`
  oraz snapshot z technicznymi szczegółami za disclosure.
- Brak nowych endpointów, POST/vendor write, zmian credentiali lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress`.
- Nie utworzono nowego Beada: zakres mieści się w istniejącym bounded seamie
  `jnra`, a nie znaleziono osobnego aktywnego zadania o tym samym zakresie.

## Następny slice

Ponowny odczyt pozostałych helperów review/preview w `service.py` i wybór jednego
potwierdzonego seamu, bez powtarzania gotowych payload/readiness boundaries.

## Otwarte blokery

- Content queue: `blocked`, `not_enough_actionable_candidates` (1 actionable,
  minimum 3).
- Goal 005: brak realnego Wilku UAT albo owner defer.
