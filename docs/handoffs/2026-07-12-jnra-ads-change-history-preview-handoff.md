# Handoff — jnra Google Ads change-history preview seam

Data: 2026-07-12 Europe/Warsaw

## Zrobione

Renderer `change_history_impact_review_v1` został wydzielony z
`wilq/actions/service.py` do istniejącego
`wilq/actions/google_ads/change_history.py`. Podczas live/browser proof
potwierdzono i naprawiono realny safety gap: raw event IDs, resource/operation
enumy, field names i raw card IDs nie są już widoczne w operator card above
fold. Technical details pozostają za istniejącym disclosure.

## Weryfikacja

- Change-history API/action tests i nowy behavior test redakcji ID/enumów — zielone.
- Ruff, mypy i `git diff --check` — zielone.
- Complexity: `service.py` 3512 LOC; jedyny changed-code finding to znany
  frozen-file budget monolitu.
- Live action `act_review_ads_change_history_impact`: health `ok`, jeden
  evidence ID, cztery `google_ads_change_history_review` cards,
  `apply_allowed=false`, `api_mutation_ready=false`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/`
  (`ads-change-history-preview-cards.png` i `.txt`) pokazuje genericzne rows,
  blokadę zapisu i blocked claims; raw `178...`, `AD_GROUP_CRITERION`, `CREATE`
  i `adGroup` nie występują w operator snapshot.

## Stan grafu

`wilq-seo-jnra` pozostaje `in_progress`; WordPress `7b285df2`, social
`3895ca5a`, Ads budget `65df313f`, recommendation `ca1f2bcc`, negative-keyword
`0146a70f`, custom-segment `6b10dd03`; ten change-history seam czeka na
commit/push.

## Następny krok

Po commicie uruchom ponowny complexity/runtime review i wybierz kolejny
niezakończony Ads preview seam. Nie dodawaj direct vendor write ani nie omijaj
validate → preview → human review → confirm → audit.
