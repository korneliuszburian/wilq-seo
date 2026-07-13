# Handoff — `djly` Ads business-context extraction

Data: 2026-07-13 Europe/Warsaw

## Wykonane

Wydzielono `strategy_review_operator_state` i
`strategy_review_readiness_contract` do
`wilq/briefing/ads_business_context_contracts.py`. `ads_diagnostics.py` nadal
orkiestruje całość, ale nie posiada już tej projection boundary.

Następnie wydzielono do tego ownera `business_context_contract_state` oraz
`business_context_review_gates`. Kolejność brakujących kontraktów, status
fail-closed i nazwy bramek review pozostają bez zmian.

## Dowód

- `tests/test_ads_business_context_contracts.py` potwierdza blocked,
  evidence lineage i `apply_allowed=false`/`destructive=false`.
- `tests/api_contracts/test_ads_contracts.py` oraz
  `tests/api_contracts/test_source_diagnostics_contracts.py` przechodzą.
- Ruff, mypy i `git diff --check` przechodzą.
- Live API po restarcie zachowuje Ads action IDs i brak vendor writes.
- Live Ads: 16 sekcji, 9 action IDs, 1 blocker, 2 evidence IDs,
  `live_data_available=true`; daily-check: `blocked`, świeży, 23 evidence IDs,
  3 safe next actions i 1 blocked recommendation.
- Browser `/ads-doctor` pokazuje polskie blokady ROAS/przychodu/waste, kolejkę
  decyzji i review-only ActionObject.

## Nie powtarzać

Nie przenosić ponownie strategy-review projection, contract state ani review
gates. Pozostałe kontrakty business-context (target interpretation, policy,
summary i metric tiles) wymagają osobnych seamów z parytetem; nie scalać ich
mechanicznie bez testu.
