# Handoff — `djly` Ads business-context extraction

Data: 2026-07-13 Europe/Warsaw

## Wykonane

Wydzielono `strategy_review_operator_state` i
`strategy_review_readiness_contract` do
`wilq/briefing/ads_business_context_contracts.py`. `ads_diagnostics.py` nadal
orkiestruje całość, ale nie posiada już tej projection boundary.

## Dowód

- `tests/test_ads_business_context_contracts.py` potwierdza blocked,
  evidence lineage i `apply_allowed=false`/`destructive=false`.
- `tests/api_contracts/test_ads_contracts.py` oraz
  `tests/api_contracts/test_source_diagnostics_contracts.py` przechodzą.
- Ruff, mypy i `git diff --check` przechodzą.
- Live API po restarcie zachowuje Ads action IDs i brak vendor writes.

## Nie powtarzać

Nie przenosić ponownie strategy-review projection. Pozostałe kontrakty
business-context (state, target interpretation, policy/gates i metric tiles)
wymagają osobnych seamów z parytetem; nie scalać ich mechanicznie bez testu.
