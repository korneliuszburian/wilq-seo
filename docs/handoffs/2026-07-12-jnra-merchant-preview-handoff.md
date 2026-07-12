# Handoff: `jnra` Merchant feed preview renderer — 2026-07-12

## Decyzja

Wydzieliłem renderer operator-facing dla `act_review_merchant_feed_issues` z
`wilq/actions/service.py` do `wilq/actions/merchant_preview.py`. Przeniesione
zostały też lokalne helpery presentation-only: priorytety próbek, liczba
zgłoszeń, podtytuł i podsumowanie próbek. Merchant module przejął stałą
`MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT`, aby kontrakt nie był duplikowany.

## Dowód produktu

- Live API: `GET /api/actions/act_review_merchant_feed_issues` zwrócił
  `mode=prepare`, `connector=google_merchant_center`, 1 evidence ID i 4 karty
  `merchant_feed_issue_review`.
- Karty pokazują typ problemu, atrybut, liczbę zgłoszeń, kontekst próbek i
  tytuły produktów; zapis pozostaje zablokowany (`apply_allowed=false`,
  `api_mutation_ready=false`).
- Evidence: `ev_refresh_refresh_google_merchant_center_a4bba675a1ab`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/merchant-feed-preview-cards.png`.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k merchant_preview`:
  1 passed.
- Ruff i mypy dla service/merchant/new module/test: passed.
- Complexity changed audit: brak nowych naruszeń; frozen `service.py` pozostaje
  znanym hotspotem.
- `git diff --check`: passed.
- Live Merchant agregacja jest cięższa od pozostałych akcji, ale pełny API
  response i browser render zakończyły się poprawnie; nie utworzono fałszywego
  performance Bead.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam mieści się w bounded extraction
  scope, bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na świeżej kolejce contentu: 1 actionable z
  minimum 3.
- Następny turn ma odczytać świeży complexity/runtime stan i wybrać kolejny
  istniejący preview seam; nie wracać do Merchant, Localo, GA4, n-gramów ani
  Demand Gen.

## Commit

Hash implementacji zostanie dopisany po pushu w osobnym docs-only commicie.
