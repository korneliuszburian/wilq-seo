# Handoff: `jnra` ActionObject operator projection — 2026-07-12

## Decyzja

Składanie operatorowego `ActionObject` view-modelu zostało przeniesione z
`wilq/actions/service.py` do istniejącego `wilq/actions/operator_labels.py`.
Service zachowuje orkiestrację i przekazuje callbacki connector/evidence,
review gate, preview cards oraz audit event.

## Dowody

- Zachowano typed labels, preview cards, review-gate projection i audit-detail
  redaction; nie zmieniono ActionObject safety loop.
- Focused audit/preview/review tests: `32 passed`; Ruff, mypy, complexity i
  `git diff --check` przechodzą.
- `service.py` ma 2248 LOC; frozen-file budget violation pozostaje jawny.
- Po managed restart `/api/health` jest `ok`; Ads detail HTTP 200 ma evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/action-projection-live.png`.
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
