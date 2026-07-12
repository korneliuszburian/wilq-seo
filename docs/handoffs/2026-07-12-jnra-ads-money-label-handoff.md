# Handoff: `jnra` Ads micros money label — 2026-07-12

## Decyzja

Formatter wartości Google Ads w micros został przeniesiony z `service.py` do
istniejącego `wilq/actions/google_ads/business_context.py`, który już jest
właścicielem Ads business context i jego preview rows. Kontrakt `PLN` oraz
fail-closed `kwota niepotwierdzona` pozostały bez zmian.

## Dowody

- `micros_money_label(1_250_000)` daje `1.25 PLN`; brak/niepoprawny typ nie
  tworzy metryki i daje `kwota niepotwierdzona`.
- Focused Ads preview/review/payload suite: `26 passed`; Ruff, mypy,
  complexity i `git diff --check` przechodzą.
- Po managed restart API health jest `ok`; Ads action detail ma evidence,
  `Zapis zmian zablokowany` i `apply_allowed=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/money-label-live.png`.
- Brak nowych endpointów, vendor writes, credential changes lub publikacji.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress`; zakres jest częścią istniejącego
  Ads bounded seamu, więc nie utworzono duplikatu.

## Następny slice

Świeży odczyt pozostałych helperów końcówki `service.py`; tylko domenowy seam z
istniejącym właścicielem i focused behavior test.

## Otwarte blokery

- Content queue: `blocked`, `not_enough_actionable_candidates` (1 actionable,
  minimum 3).
- Goal 005: brak realnego Wilku UAT albo owner defer.
