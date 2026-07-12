# Handoff — jnra Google Ads budget preview seam

Data: 2026-07-12 Europe/Warsaw

## Zrobione

Renderer kart `budget_apply_preview_v1` został wydzielony z
`wilq/actions/service.py` do `wilq/actions/google_ads/previews.py`.
Service pozostaje dispatcherem i przekazuje callbacks do wspólnych rows,
labels, formatowania kwot i stanu zapisu. Payload, evidence IDs, safety review,
blocked claims, `prepare` mode i ActionObject safety loop pozostały bez zmian.

## Weryfikacja

- Ads budget contract tests i action budget tests — zielone.
- Ruff, mypy i `git diff --check` — zielone.
- Complexity: `service.py` 3694 LOC; jedyny changed-code finding to znany
  frozen-file budget monolitu.
- Live API po managed restart: health `ok`; `act_prepare_ads_campaign_review_queue`
  ma jeden evidence ID, cztery `google_ads_budget_review` cards,
  `apply_allowed=false`, `api_mutation_ready=false`; vendor write nie był
  próbowany.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/`
  (`ads-budget-preview-cards.png` i `.txt`) pokazuje kampanię, budżet,
  blokadę zapisu, bezpieczeństwo i blocked claims bez raw payloadu above fold.

## Stan grafu

`wilq-seo-jnra` pozostaje `in_progress`; WordPress payload preview jest
pushnięty jako `7b285df2`, social preview jako `3895ca5a`, a ten Ads seam czeka
na commit/push.

## Następny krok

Po commicie uruchom ponowny complexity/runtime review i wybierz kolejny
niezakończony Ads preview seam. Nie dodawaj direct vendor write ani nie omijaj
validate → preview → human review → confirm → audit.
