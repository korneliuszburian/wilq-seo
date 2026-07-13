# Handoff — `8qqr` GA4 diagnostics cache

Data: 2026-07-13 Europe/Warsaw

## Wykonane

- Dodano typed TTL cache na istniejącej granicy `ga4_diagnostics`.
- Router `/api/ga4/diagnostics` i daily-check używają cached buildera.
- API cache invalidation czyści GA4 cache po refreshach/actions/jobs.
- Daily prewarm przygotowuje również GA4 contract po readiness.

## Dowód

- Baseline HTTP: GA4 `4.354704/2.129338/1.737154 s`; daily-check
  `10.894200/1.812485/2.127347 s`.
- Po zmianie i prewarmie: GA4 `0.003595/0.090934 s`; daily-check
  `0.073996/0.077939/0.054049 s`.
- Focused tests cache/prewarm/daily-check, Ruff, mypy i diff check przechodzą.
- Browser `/content-workflow` 1/1 przechodzi.
- Mutation readiness pozostaje `21` akcji, `0` vendor writes.
- Po dodaniu locka live restart: GA4 `10.038843/0.003666/0.005881 s`; jeden
  cold build, potem cache hits. Contract live: `live_data_available=true`,
  `4` decyzje, `8` evidence IDs.
- Focused 40 testów potwierdza cache hit, TTL expiry, explicit invalidation,
  concurrent cold build oraz niezmienione GA4/daily-check contracts; Ruff i
  mypy przechodzą.
- Rozstrzygający proof invalidacji odbył się bez restartu na API port-owner PID
  `3099299`: cache seed `4.196748 s`, warm hit przed refreshem `0.003541 s`,
  read-only refresh `refresh_google_analytics_4_d345166a05df`, cold rebuild po
  clear `4.580455 s` i kolejny hit `0.004964 s`. Refresh zakończył się jako
  `completed` o `2026-07-13T20:47:34.392824Z`, z
  `vendor_data_collected=true`, `metrics_persisted=true` i `redacted=true`.
  Przed i po pozostają: `live_data_available=true`, 4 decyzje, 8 evidence IDs,
  2 source labels i conversion readiness `ready`; lineage odświeżył się zgodnie
  z nowym refresh runem.
- Mutation audit count przed/po refreshem wynosi `7/7` (delta 0). Mutation
  readiness: 21 akcji, `vendor_write_possible_count=0` i
  `would_attempt_vendor_write_count=0`.
- Realny browser `/ga4` pokazuje kolejność pracy, problemy pomiaru, dowody,
  review-only podgląd i bramę bezpieczeństwa. Mutation readiness pozostaje
  fail-closed. Screenshot:
  `.local-lab/proof/8qqr-ga4-cache-20260713/ga4-full-review.png`.

## Nie powtarzać

Nie dodawać kolejnego endpointu ani cache w React/skillu. TTL, concurrency i
live invalidation są potwierdzone; Bead jest zamknięty. Następny cold-read /
readiness zakres należy do `inoz`, nie do ponownego otwierania `8qqr`.
