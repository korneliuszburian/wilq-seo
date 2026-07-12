# Handoff: `jnra` GA4 tracking-quality preview renderer — 2026-07-12

## Decyzja

Wydzieliłem renderer operator-facing dla `act_review_ga4_tracking_quality` z
`wilq/actions/service.py` do `wilq/actions/ga4/tracking_preview.py`. Service
przekazuje callbacks do typed metric rows, labels i safety state; reguły GA4 i
evidence pozostają w istniejącym module tracking quality.

## Dowód produktu

- Live API: `GET /api/actions/act_review_ga4_tracking_quality` zwrócił
  `mode=prepare`, `connector=google_analytics_4`, 1 evidence ID i kartę
  `ga4_tracking_quality_review`.
- Karta pokazuje stronę wejścia, źródło/medium, kampanię, metryki GA4 oraz
  blokuje niepotwierdzone twierdzenia o konwersji, ROAS, przychodzie i
  opłacalności. `apply_allowed=false`, `api_mutation_ready=false`.
- Evidence: `ev_refresh_refresh_google_analytics_4_97e331066b90`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/ga4-tracking-preview-cards.png`.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k ga4_tracking_preview`:
  1 passed.
- Ruff i mypy dla service/new module/test: passed.
- Complexity changed audit: brak nowych naruszeń; frozen `service.py` pozostaje
  znanym hotspotem.
- `git diff --check`: passed.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam mieści się w jego bounded
  extraction scope, bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na świeżej kolejce contentu: 1 actionable z
  minimum 3.
- Następny turn ma odczytać świeży complexity/runtime stan i wybrać kolejny
  istniejący preview seam; nie wracać do GA4, n-gramów ani Demand Gen.

## Commit

Implementacja: `847c53b3` (`refactor: extract ga4 tracking preview cards`),
wypchnięta na `origin/main`. Ten handoff zostanie domknięty osobnym docs-only
commitem.
