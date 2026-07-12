# Handoff: `jnra` Ads strategy-review preview renderer — 2026-07-12

## Decyzja

Wydzieliłem renderer operator-facing dla `act_record_ads_strategy_review` do
istniejącego `wilq/actions/google_ads/business_context.py`. Service zachowuje
dispatcher i przekazuje callbacks do business-context rows, summary, list oraz
safety labels; strategia i review gates pozostają API-owned.

## Dowód produktu

- Live API: `GET /api/actions/act_record_ads_strategy_review` zwrócił
  `mode=prepare`, `connector=google_ads`, 2 evidence IDs i kartę
  `google_ads_strategy_review`.
- Karta pokazuje kontekst marży/budżetu, brak zapisanego wyniku ludzkiego
  review, warunki sprawdzenia i blocked KPI/budget claims; zapis pozostaje false.
- Evidence: `ev_connector_google_ads_status`,
  `ev_refresh_refresh_google_ads_d71876fb0c4d`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/ads-strategy-review-preview.png`.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k ads_strategy_preview`:
  1 passed.
- Ruff i mypy dla service/business-context/test: passed.
- Complexity changed audit: brak nowych naruszeń; frozen `service.py` pozostaje
  znanym hotspotem.
- `git diff --check`: passed.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam mieści się w bounded extraction
  scope, bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na świeżej kolejce contentu: 1 actionable z
  minimum 3.
- Następny turn ma odczytać świeży complexity/runtime stan i wybrać kolejny
  istniejący preview seam; nie wracać do strategy review, target guardrail,
  Keyword Planner, Merchant, Localo, GA4, n-gramów ani Demand Gen.

## Commit

Hash implementacji zostanie dopisany po pushu w osobnym docs-only commicie.
