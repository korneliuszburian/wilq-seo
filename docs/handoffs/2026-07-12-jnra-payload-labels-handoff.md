# Handoff: `jnra` payload preview labels — 2026-07-12

## Decyzja

Wspólne fabryki `preview_row`, etykiety stanu zapisu/system readiness,
sanityzacja list stringów i label kontraktu preview zostały przeniesione do
istniejącego `wilq/actions/payload_readiness.py`. `service.py` zachowuje
callbacki domenowe oraz istniejące facade names przez import alias.

## Dowody

- Zachowano polskie safety copy: `zapis zmian dopuszczony` vs
  `zapis zmian zablokowany`, `system gotowy do zapisu` vs blokada oraz fallback
  kontraktu `podgląd zmian do sprawdzenia`.
- Focused `tests/actions/test_payload_readiness.py`, preview i confirmation:
  `20 passed`; Ruff, mypy, complexity i `git diff --check` przechodzą.
- Po managed stack restart `/api/health` jest `ok`; Ads detail HTTP 200 ma
  evidence, `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/payload-labels-live.png`.
- Brak nowych endpointów, vendor writes, POST mutations lub sekretów.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress`; nie ma nowego duplikatu.

## Następny slice

Świeży re-audyt pozostałych domenowych helperów końcówki `service.py`; wybierz
tylko seam z istniejącym modułem właścicielskim i testem zachowania.

## Otwarte blokery

- Content queue: `blocked`, `not_enough_actionable_candidates` (1 actionable,
  minimum 3).
- Goal 005: brak realnego Wilku UAT albo owner defer.
