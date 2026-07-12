# Handoff: `jnra` Ads target-guardrail preview renderer — 2026-07-12

## Decyzja

Wydzieliłem renderer operator-facing dla `act_confirm_ads_target_guardrails`
do istniejącego `wilq/actions/google_ads/business_context.py`. Service zachowuje
dispatcher i przekazuje callback do business-context rows, list oraz safety
labels; reguły celu i lokalnego kontekstu pozostają w module domenowym.

## Dowód produktu

- Live API: `GET /api/actions/act_confirm_ads_target_guardrails` zwrócił
  `mode=prepare`, `connector=google_ads`, 2 evidence IDs i kartę
  `google_ads_target_guardrail_review`.
- Karta pokazuje marżę, cel biznesowy/budżetowy, opcje ROAS/CPA, brakujące
  potwierdzenia i blocked KPI/budget claims; `apply_allowed=false`,
  `api_mutation_ready=false`.
- Evidence: `ev_connector_google_ads_status`,
  `ev_refresh_refresh_google_ads_d71876fb0c4d`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/ads-target-guardrail-preview.png`.

## Weryfikacja

- `tests/actions/test_action_preview_contracts.py -k ads_target_guardrail_preview`:
  1 passed.
- Ruff i mypy dla service/business-context/test: passed.
- Complexity changed audit: brak nowych naruszeń; frozen `service.py` pozostaje
  znanym hotspotem.
- `git diff --check`: passed.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam mieści się w bounded extraction
  scope, bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na świeżej kolejce contentu: 1 actionable z
  minimum 3.
- Następny turn ma odczytać świeży complexity/runtime stan i wybrać kolejny
  istniejący preview seam; nie wracać do target guardrail, Keyword Planner,
  Merchant, Localo, GA4, n-gramów ani Demand Gen.

## Commit

Implementacja: `df04275c` (`refactor: extract ads target guardrail preview`),
wypchnięta na `origin/main`. Ten handoff zostanie domknięty osobnym docs-only
commitem.
