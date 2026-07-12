# Handoff: `jnra` search-term n-gram preview renderer — 2026-07-12

## Decyzja

Wydzieliłem operator-facing renderer dla
`act_review_ads_search_term_ngrams` z `wilq/actions/service.py` do
`wilq/actions/google_ads/search_term_ngram_preview.py`. Service zachowuje
dispatcher i przekazuje jawne callbacks do polskich labels, wartości metryk i
bezpiecznego stanu zapisu.

## Dowód produktu

- Live API: `GET /api/actions/act_review_ads_search_term_ngrams` zwrócił
  `mode=prepare`, `connector=google_ads`, 1 evidence ID i 4 karty
  `google_ads_search_term_ngram_review`.
- Karty pokazują temat, rozmiar, liczbę zapytań, przykłady, kliknięcia,
  wyświetlenia, koszt, konwersje, braki i blocked claims. `apply_allowed=false`,
  `api_mutation_ready=false`; n-gram nie jest traktowany jako gotowe
  wykluczenie.
- Evidence: `ev_refresh_refresh_google_ads_d71876fb0c4d`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/ads-search-ngram-preview-cards.png`.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k search_term_ngram_preview`:
  1 passed.
- Ruff i mypy dla service/new module/test: passed.
- Complexity changed audit: brak nowych naruszeń; frozen `service.py` pozostaje
  znanym hotspotem.
- `git diff --check`: passed.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam jest częścią jego bounded
  extraction scope, bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na świeżej kolejce contentu: 1 actionable z
  minimum 3, bez sztucznego candidate.
- Następny turn ma odczytać świeży complexity/runtime stan i wybrać kolejny
  istniejący preview seam; nie wracać do Demand Gen ani n-gramów.

## Commit

Implementacja: `9b7e9cb4` (`refactor: extract search term ngram preview cards`),
wypchnięta na `origin/main`. Ten handoff zostanie domknięty osobnym docs-only
commitem.
