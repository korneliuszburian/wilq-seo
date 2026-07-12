# Handoff: `jnra` apply audit event type — 2026-07-12

## Decyzja

Mapowanie błędów apply na typ audytowego eventu zostało przeniesione z
`wilq/actions/service.py` do istniejącego `wilq/actions/audit_store.py`.
Zachowano rozróżnienie sukcesu, braku potwierdzenia oraz pozostałych blokad.

## Dowody

- Pusty error list daje `apply_succeeded`; confirmation errors dają
  `apply_confirmation_missing`; inne błędy dają `apply_blocked`.
- Focused audit/mutation tests, Ruff, mypy, complexity i `git diff --check`
  przechodzą.
- `service.py` ma 2154 LOC; frozen-file budget violation pozostaje jawny.
- Po managed restart `/api/health` jest `ok`; Ads detail HTTP 200 ma evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/apply-event-live.png`.
- Commit implementacji: `704a971` wypchnięty na `origin/main`.
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
