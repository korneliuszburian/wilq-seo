# Handoff — jnra Google Ads negative-keyword preview seam

Data: 2026-07-12 Europe/Warsaw

## Zrobione

Renderer `negative_keyword_change_preview_v1` został wydzielony z
`wilq/actions/service.py` do istniejącego
`wilq/actions/google_ads/negative_keywords.py`. Service pozostaje dispatcherem
i przekazuje callbacks do rows, labels i apply/readiness state. Payload,
evidence IDs, 90-dniowe safety gates, blocked claims, prepare mode i
ActionObject safety loop pozostały bez zmian.

## Weryfikacja

- Negative-keyword API/action tests — zielone.
- Ruff, mypy i `git diff --check` — zielone.
- Complexity: `service.py` 3616 LOC; jedyny changed-code finding to znany
  frozen-file budget monolitu.
- Live action `act_prepare_negative_keyword_review_queue`: health `ok`, jeden
  evidence ID, dwa `google_ads_negative_keyword_review` cards,
  `apply_allowed=false`, `api_mutation_ready=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/`
  (`ads-negative-preview-cards.png` i `.txt`) pokazuje hasło, dopasowanie,
  poziom, 90-dniowe warunki, blocked claims i blokadę zapisu.

## Stan grafu

`wilq-seo-jnra` pozostaje `in_progress`; WordPress `7b285df2`, social
`3895ca5a`, Ads budget `65df313f`, recommendation `ca1f2bcc`, negative-keyword
`0146a70f`.

## Następny krok

Po commicie uruchom ponowny complexity/runtime review i wybierz kolejny
niezakończony Ads preview seam. Nie dodawaj direct vendor write ani nie omijaj
validate → preview → human review → confirm → audit.
