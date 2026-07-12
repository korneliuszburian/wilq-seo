# Handoff — jnra Google Ads custom-segment preview seam

Data: 2026-07-12 Europe/Warsaw

## Zrobione

Renderer `custom_segment_change_preview_v1` został wydzielony z
`wilq/actions/service.py` do istniejącego
`wilq/actions/google_ads/custom_segments.py`. Service zachowuje dispatcher i
przekazuje callbacks do rows, labels oraz apply/readiness state. Payload,
source terms, evidence IDs, Keyword Planner/audience-size gates, blocked claims,
prepare mode i ActionObject safety loop pozostały bez zmian.

## Weryfikacja

- Custom-segment API/action tests — zielone.
- Ruff, mypy i `git diff --check` — zielone.
- Complexity: `service.py` 3565 LOC; jedyny changed-code finding to znany
  frozen-file budget monolitu.
- Live action `act_prepare_custom_segments_from_search_terms`: health `ok`,
  jeden evidence ID, jeden `google_ads_custom_segment_review` card,
  `apply_allowed=false`, `api_mutation_ready=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/`
  (`ads-custom-preview-cards.png` i `.txt`) pokazuje source terms, safety,
  Keyword Planner/audience-size blockers i blocked claims.

## Stan grafu

`wilq-seo-jnra` pozostaje `in_progress`; WordPress `7b285df2`, social
`3895ca5a`, Ads budget `65df313f`, recommendation `ca1f2bcc`, negative-keyword
`0146a70f`, custom-segment `6b10dd03`.

## Następny krok

Po commicie uruchom ponowny complexity/runtime review i wybierz kolejny
niezakończony Ads preview seam. Nie dodawaj direct vendor write ani nie omijaj
validate → preview → human review → confirm → audit.
