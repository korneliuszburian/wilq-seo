# Handoff: `jnra` audit details redaction — 2026-07-12

## Decyzja

Redakcja szczegółów audytu dla operatora została przeniesiona z
`wilq/actions/service.py` do istniejącego `wilq/actions/audit_store.py`.
Funkcja zachowuje redakcję raw payload/mapping/claim identifiers i przyjmuje
callbacki dla domenowych etykiet checked items oraz blockers.

## Dowody

- Raw contract keys/values są odrzucane rekurencyjnie; bezpieczne pola i polskie
  etykiety review pozostają widoczne.
- Focused audit/preview/review tests: `29 passed`; Ruff, mypy, complexity i
  `git diff --check` przechodzą.
- `service.py` ma 2312 LOC; istniejący frozen-file budget violation pozostaje
  jawny, bez nowego naruszenia.
- Po managed restart `/api/health` jest `ok`; Ads detail HTTP 200 ma evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/audit-details-live.png`.
- Brak nowych endpointów, vendor writes, credential changes lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress`; nie utworzono duplikatu.

## Następny slice

Świeży odczyt końcówki `service.py`; wybierz kolejny helper tylko wtedy, gdy
istnieje właściwy moduł domenowy i test zachowania.

## Otwarte blokery

- Content queue: `blocked`, `not_enough_actionable_candidates` (1 actionable,
  minimum 3).
- Goal 005: brak realnego Wilku UAT albo owner defer.
