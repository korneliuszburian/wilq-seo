# Handoff: `jnra` mutation readiness next step — 2026-07-12

## Decyzja

Wyznaczanie `operator_next_step` dla mutation readiness zostało przeniesione z
`wilq/actions/service.py` do istniejącego `wilq/actions/mutation_readiness.py`.
Zachowano fail-closed apply oraz kolejność bezpiecznych kroków WordPress:
handoff/package, potem preview/review/confirm.

## Dowody

- WordPress blocker zwraca krok przygotowania handoffu i paczki; brak blockerów
  nadal wymaga osobnego POST z jawnym potwierdzeniem operatora.
- Focused mutation/audit/preview/review tests: `34 passed`; Ruff, mypy,
  complexity i `git diff --check` przechodzą.
- `service.py` ma 2225 LOC; frozen-file budget violation pozostaje jawny.
- Po managed restart `/api/health` jest `ok`; mutation readiness raportuje
  `vendor_write_possible=false`; Ads detail ma evidence, blokadę zapisu i
  `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/mutation-next-live.png`.
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
