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

## Nie powtarzać

Nie dodawać kolejnego endpointu ani cache w React/skillu. Pozostał proof TTL
expiry i invalidacji po live connector refreshu; dopiero potem można zamknąć
Bead.
