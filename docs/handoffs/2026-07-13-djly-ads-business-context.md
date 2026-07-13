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

W kolejnym bounded seamie przeniesiono `business_context_policy_ids` oraz
`business_context_summary_and_next_step`; fasada zachowuje te same policy IDs,
polski summary i safe next step.

Czwarty seam przeniósł faktyczne `business_target_interpretation` do tego
samego typed ownera. Obsługiwane są blocked, preliminary i ready; target
ROAS/CPA context pozostaje review-only, a blocked uses i missing requirements
zachowują dotychczasową kolejność. Stare prywatne helpery fasady są tymczasowo
pozostawione wyłącznie jako compatibility reference i nie są już ścieżką
runtime; ich usunięcie jest kolejnym cleanup slice'em.

Piąty seam przeniósł również `business_context_read_metric_tiles` do typed
ownera. Formatowanie marży, kosztu, celu i statusu review pozostaje zgodne z
dotychczasowym payloadem.

Cleanup usunął `_business_context_metric_tiles_legacy` oraz osierocone
formatery z fasady. To nie zmienia payloadu; następny proof dotyczy parity/runtime.

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
- Live target interpretation: `status=preliminary`, dozwolone są tylko
  `campaign_review_context`, `budget_review_context`,
  `human_strategy_review_context`, `margin_context`,
  `business_goal_alignment`, `budget_goal_guardrail`; target verdict,
  profitability i budget changes pozostają zablokowane.
- Complexity audit: `ads_diagnostics.py` spadł do 5864 LOC, ale nadal jest
  ponad lokalnym budżetem; extraction-only violation jest jawnie zachowany.
- Complexity recheck po target/metric seamie: 0 changed-code violations;
  stare limity pliku i `build_ads_diagnostics` pozostają znane.

## Nie powtarzać

Nie przenosić ponownie żadnego z tych seamów ani przywracać legacy helpera.
Pozostał pełny parity/runtime audit istniejącego ownera.
