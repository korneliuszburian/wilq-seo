# Handoff: `jnra` Keyword Planner access preview renderer — 2026-07-12

## Decyzja

Wydzieliłem renderer operator-facing dla
`act_configure_google_ads_keyword_planner_access` do istniejącego
`wilq/actions/google_ads/keyword_planner.py`. Service zachowuje dispatcher i
przekazuje callbacks do rows, list oraz state label; zewnętrzny blocker API
pozostaje jawny i nie jest zamieniany w rekomendację.

## Dowód produktu

- Live API: `GET /api/actions/act_configure_google_ads_keyword_planner_access`
  zwrócił `mode=prepare`, `connector=google_ads`, 2 evidence IDs i kartę
  `google_ads_keyword_planner_access_review`.
- Karta pokazuje `DEVELOPER_TOKEN_NOT_APPROVED` jako blocker, następny krok do
  Google Ads API, warunki sprawdzenia i blokuje prognozę, rozmiar odbiorców,
  ROAS oraz zapis kierowania; zapis pozostaje false.
- Evidence: `ev_connector_google_ads_status`,
  `ev_refresh_refresh_google_ads_d71876fb0c4d`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/keyword-planner-access-preview.png`.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k keyword_planner_preview`:
  1 passed.
- Ruff i mypy dla service/keyword-planner/test: passed.
- Complexity changed audit: brak nowych naruszeń; frozen `service.py` pozostaje
  znanym hotspotem.
- `git diff --check`: passed.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam mieści się w bounded extraction
  scope, bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na świeżej kolejce contentu: 1 actionable z
  minimum 3.
- Następny turn ma odczytać świeży complexity/runtime stan i wybrać kolejny
  istniejący preview seam; nie wracać do Keyword Planner, Merchant, Localo,
  GA4, n-gramów ani Demand Gen.

## Commit

Hash implementacji zostanie dopisany po pushu w osobnym docs-only commicie.
