# Handoff — `wilq-seo-0hdm` daily runtime prewarm

Data: 2026-07-13 Europe/Warsaw

## Wykonane

Po readiness API uruchamia background `build_daily_runtime` przez
`asyncio.to_thread`. Nie powstał nowy endpoint, cache ani write path; istniejąca
inwalidacja `clear_daily_runtime_cache()` nadal działa po refreshu.

## Dowód

- Cold baseline przed zmianą: `13.038038 s`, potem `1.818062 s` i `2.665879 s`.
- Po managed restarcie i prewarmie: `2.528725 s`, `4.875843 s`, `2.786930 s`.
- `/api/marketing/daily-check`: `blocked`, świeżość `fresh`, 23 evidence IDs,
  7 source connectors, 3 safe next actions.
- `/api/actions/mutation-readiness`: 21 akcji, 0 ready-to-request-apply,
  0 vendor-write possible, 0 attempted.
- Content queue: 2 kandydatów, 1 actionable z minimum 3; blocker pozostaje
  evidence-backed `not_enough_actionable_candidates`.
- Focused pytest, Ruff, mypy, `git diff --check`, API smoke i Playwright
  `/content-workflow` 1/1 przechodzą.

## Nie powtarzać

Nie dodawać kolejnego cache ani prewarma endpointowego. Jeśli latency wróci,
najpierw zmierzyć startup/prewarm i sprawdzić inwalidację po refreshu.

## Pozostałe blokery produktu

- Content queue nie ma jeszcze trzech actionable tematów.
- `v9ab.13`/`jst` wymagają realnego review Wilku/operatora albo jawnego deferu.
- Service Profile nadal ma 0 kart approved production-depth.
