# Handoff — `v9ab.8.2` measurement baseline guard

Data: 2026-07-12 Europe/Warsaw

## Decyzja

Aggregate daily content queue nie może kierować do review, jeśli żaden
actionable temat nie ma bazy późniejszego pomiaru: metryk, measurement
connectora i evidence ID. WILQ korzysta z istniejącego enrichmentu, nie z
samego publicznego URL-a ani luźnej etykiety queue readiness.

Jeden mierzalny temat może pozostać `review_required`, nawet gdy cała kolejka
jest zbyt krótka. Daily output ma wtedy wprost nazwać oba stany: bezpieczny
review jednego tematu oraz globalną blokadę backlogu (obecnie 1 z 3).

## Dowody

- `evaluate_content_measurement_baseline_guard` wymaga
  `ready_to_plan` oraz niepustych `metrics_to_watch`, `source_connectors` i
  `evidence_ids` z istniejącego `ContentOpportunityMeasurementBaseline`.
- `daily_check` mapuje tylko actionable queue candidates do diagnostics;
  zablokowany Ahrefs candidate, brak mapowania i wyjątek fail-closed.
- Focused command-center/daily-check/queue/guard suites, Ruff, mypy i
  changed-code complexity przechodzą bez nowych violation.
- Live po managed restart: API `ok`; daily aggregate content item ma
  `source_trace_ready`, `multi_source_ready`, `date_window_ready` i
  `measurement_baseline_ready`, 8 evidence IDs/5 source connectors. Jego
  summary i next step mówią o blokadzie całej kolejki `1 z 3`; queue pozostaje
  `blocked` przez `not_enough_actionable_candidates`. Nie wykonano vendor write.

## Następny potwierdzony zakres

- `r564.5`: weak token-only Ahrefs overlap nie może udawać potwierdzonego GSC
  lub WordPress inventory.
- `r564.6`: istniejący workflow snapshot potrzebuje typed per-work-item
  Service Profile context; osobna trasa nie wystarcza do decyzji pisania.
- `r564` pozostaje `blocked_by_external_state`: nie generować sztucznego
  trzeciego tematu.
