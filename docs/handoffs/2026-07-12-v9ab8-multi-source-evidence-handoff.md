# Handoff — `v9ab.8.1` multi-source evidence guard

Data: 2026-07-12 Europe/Warsaw

## Decyzja

Daily aggregate content queue nie może uznać dwóch źródeł WordPress za
potwierdzone wyłącznie dlatego, że ich ID są na liście. Każdy source wymagany
przez `wordpress_platform_traps_v1` musi mieć typed `MetricFact` z własnym
`evidence_id`.

Guard dotyczy wyłącznie `decision_prepare_content_refresh_queue`, czyli
aggregate work orderu. Indywidualny publiczny work order nie dziedziczy
wymagania sklepu; public/dev URL roles nie zmieniły się.

## Dowody

- `DailyDecision.metric_facts` już niesie `source_connector` i `evidence_id`;
  nie dodano schema ani endpointu.
- `wilq/briefing/daily_check.py` dołącza required evidence IDs do
  `DailyCheckItem`, aby upstreamowy limit summary evidence nie ukrywał proof.
- Focused contracts: 27 passed (`command-center`, `daily-check`, guard).
  Ruff i mypy dla zmienionych modułów przechodzą.
- Live po managed restart: API health `ok`; aggregate content item jest
  `review_required`, ma `source_trace_ready`, `multi_source_ready` i
  `date_window_ready`, a jego evidence zawiera proof publicznego WordPressa i
  sklepu. Nie wykonano vendor write.

## Review finding naprawiony przed commitem

Pierwszy wariant sprawdzał jedynie deklarowane connector IDs. Review wykazał,
że to byłoby false positive, a globalny scope mógłby mieszać publiczny work
order ze sklepem. Wariant nie został commitowany; finalny slice wymaga typed
fact-and-evidence coverage i jest zawężony do aggregate queue. Niezależny
review finalnego diffu nie znalazł dalszego findingu P0/P1/P2.

## Pozostały zakres

- `v9ab.8.2`: content queue bez `ready_to_plan` measurement baseline.
- `r564.5`: token-only Ahrefs overlap nie może udawać potwierdzenia GSC lub
  WordPress.
- `r564` pozostaje `blocked_by_external_state`: 1 actionable candidate z
  minimum 3; nie generować sztucznego tematu.
