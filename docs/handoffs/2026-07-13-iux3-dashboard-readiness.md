# Handoff — `iux3` dashboard usefulness readiness

Data: 2026-07-13 Europe/Warsaw

## Wykonane

`scripts/dashboard_usefulness_audit.py` oddziela structural usefulness score od
API-owned semantic readiness. `status` albo `queue_status` równe `blocked`
ustawia `blocked`; `production_depth_readiness.ready_for_daily_content=false`
albo review-required ustawia `review_ready`. Gotowe powierzchnie nadal mogą
być `demo_ready`.

Nie zmieniono API, tras dashboardu, metryk ani zasad biznesowych.

## Dowód

- Bead: `wilq-seo-iux3` zamknięty.
- Focused dashboard audit tests: 16 passed.
- Ruff i mypy dla skryptu przechodzą.
- Live audit: 14 powierzchni, 11 `demo_ready`, 2 `review_ready`, 1 `blocked`,
  `pass=true` dla production surfaces.
- Live Service Profile nie jest już fałszywie `demo_ready`: ma
  `ready_for_daily_content=false`, 0 approved production-depth cards.
- API `health=ok`; `git diff --check` przechodzi.

Commity: `b2d211ca`, `7d470468`.

## Nie powtarzać

Nie zmieniać API readiness ani UI na podstawie tego Beada. Kolejny krok to
realny Wilku review/owner defer (`v9ab.13`/`jst`) albo osobny potwierdzony
problem. Lokalne zmiany `apps/api/wilq_api/main.py`, `.beads/interactions.jsonl`
i `tests/test_daily_runtime_prewarm.py` należą do innego zakresu i nie zostały
ruszone.

