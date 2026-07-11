# Handoff — `v9ab.8` source-trace false-positive guard

Data: 2026-07-12 Europe/Warsaw

## Decyzja

Rozpoczęto `v9ab.8` najmniejszym niezależnym guardem: daily recommendation nie
może przejść jako review-ready bez źródła, evidence ID, expert rule ID i świeżego
odczytu.

## Wykonane

- Dodano typed `FalsePositiveGuardResult` i
  `evaluate_source_trace_guard` w `wilq/briefing/false_positive_guards.py`.
- `DailyCheckItem.false_positive_guards` pokazuje konkretny guard ID.
- Aktualny live stale stan zwraca `stale_connector`; brak trace zwraca
  `missing_source_connector`, `missing_evidence` albo `missing_expert_rule`.
- Nie zmieniono write path ani nie dodano drugiego endpointu.
- `missing_conversion` korzysta z istniejącego typed
  `Ga4ConversionReadinessContract`; gotowy kontrakt daje guard
  `conversion_readiness_ready`, a brak kontraktu blokuje.

## Dowody

- `tests/api_contracts/test_false_positive_guards.py` i daily-check API/schema
  tests przechodzą.
- Ruff, mypy i `git diff --check` przechodzą; complexity nie pokazuje nowych
  violations.
- Live po restarcie: `/api/health` `ok`; `/api/metrics/status` raportuje 98 919
  facts i 4 574 refresh runs; daily-check `status=blocked`,
  `freshness=stale`, guard `stale_connector`, 21 evidence IDs i 8 rule IDs.
- Aktualny live GA4 item ma `conversion_readiness_ready` obok
  `stale_connector`; browser proof po restarcie:
  `.local-lab/proof/daily-check-conversion-guard.png`.

## Pozostały zakres Beada

Nie zamykaj `v9ab.8`. Brakuje osobnych, potwierdzonych guardów dla low volume,
no baseline, date window, source conflict i
multi-source-required. Każdy powinien mieć własny test i nie może udawać danych.

## Następny slice

Kontynuuj `v9ab.8` od `low_volume`/`no_baseline` tylko po znalezieniu istniejącego
typed read contractu, który dostarcza te fakty; bez heurystyki z samego copy.
