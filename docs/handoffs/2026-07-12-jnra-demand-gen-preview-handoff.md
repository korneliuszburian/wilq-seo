# Handoff: `jnra` Demand Gen preview renderer — 2026-07-12

## Decyzja

Wydzieliłem składanie operator-facing preview card dla
`act_review_demand_gen_readiness` z `wilq/actions/service.py` do
`wilq/actions/google_ads/demand_gen_preview.py`. Service pozostaje właścicielem
action dispatch i przekazuje jawne callbacks do rows oraz polskich labels.

## Dowód produktu

- Live API: `GET /api/actions/act_review_demand_gen_readiness` zwrócił
  `mode=prepare`, `connector=google_ads`, 4 evidence IDs oraz kartę
  `google_ads_demand_gen_readiness_review`.
- Runtime card pokazuje kampanie, kanały, braki landing-quality/mode-control,
  warunki sprawdzenia i blocked claims; `apply_allowed=false`,
  `api_mutation_ready=false`.
- Źródła evidence: `ev_connector_google_ads_status`,
  `ev_connector_google_analytics_4_status`,
  `ev_refresh_refresh_google_ads_d71876fb0c4d`,
  `ev_refresh_refresh_google_analytics_4_97e331066b90`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/ads-demand-gen-preview-cards.png`.
  UI pokazuje „Zapis zablokowany”; technical payload pozostaje w disclosure.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k demand_gen_preview`: 1 passed.
- Ruff i mypy dla zmienionych backend/test files: passed.
- Complexity changed audit: brak nowych naruszeń w nowym module ani w
  `demand_gen.py`; frozen `service.py` pozostaje znanym hotspotem.
- `git diff --check`: passed.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; ten seam jest częścią jego bounded
  extraction scope, bez nowego duplikatu.
- `wilq-seo-r564` pozostaje zablokowany na aktualnym queue density
  (`1 actionable / minimum 3`); nie dodano sztucznego candidate.
- Następny agent/turn ma najpierw odczytać świeży complexity/runtime stan i wybrać
  kolejny istniejący Ads preview seam, a potem wykonać osobny commit i push.

## Commit

Commit hash zostanie dopisany w follow-up docs-only commit po pushu implementacji.
