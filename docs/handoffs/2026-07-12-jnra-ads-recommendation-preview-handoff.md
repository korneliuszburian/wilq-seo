# Handoff — jnra Google Ads recommendation preview seam

Data: 2026-07-12 Europe/Warsaw

## Zrobione

Renderer `recommendation_apply_preview_v1` został wydzielony z
`wilq/actions/service.py` do istniejącego `wilq/actions/google_ads/recommendations.py`.
Service zachowuje dispatcher, a moduł domenowy dostaje callbacks do rows,
labels i apply/readiness state. Payload, evidence IDs, prepare mode, blocked
claims i ActionObject safety loop pozostały bez zmian.

## Weryfikacja

- Recommendation API contract i action tests — zielone.
- Ruff, mypy i `git diff --check` — zielone.
- Complexity: `service.py` 3655 LOC; jedyny changed-code finding to znany
  frozen-file budget monolitu.
- Live endpoint `act_prepare_google_ads_recommendation_review_queue`: health
  `ok`, jeden evidence ID, cztery `google_ads_recommendation_review` cards,
  `apply_allowed=false`, `api_mutation_ready=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/`
  (`ads-recommendation-preview-cards.png` i `.txt`) pokazuje typ rekomendacji,
  blokadę zapisu i zakazane claims bez technicznych ID above fold.

## Stan grafu

`wilq-seo-jnra` pozostaje `in_progress`; WordPress payload `7b285df2`, social
`3895ca5a`, Ads budget `65df313f`, recommendation preview `ca1f2bcc`.

## Następny krok

Po commicie uruchom ponowny complexity/runtime review i wybierz kolejny
niezakończony Ads preview seam. Nie dodawaj direct vendor write ani nie omijaj
validate → preview → human review → confirm → audit.
