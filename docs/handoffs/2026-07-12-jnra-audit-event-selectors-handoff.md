# Handoff: `jnra` audit event selectors — 2026-07-12

## Decyzja

Wydzielono cztery read-only selektory z `wilq/actions/service.py` do istniejącego
`wilq/actions/audit_store.py`: najnowszy preview event, confirmation event,
impact-check event i mutation audit. Service zachowuje cienkie fasady dla
kompatybilności, a ActionObject safety loop pozostaje bez zmian.

## Dowody

- `latest_preview_event`, `latest_action_confirmation_event`,
  `latest_action_impact_check_event` i `latest_mutation_audit` sortują po
  `created_at` malejąco i zachowują dotychczasowe typy eventów oraz fallback.
- `tests/actions/test_audit_store_contracts.py` i review contract tests:
  `10 passed`.
- Ruff i mypy dla zmienionych modułów przechodzą; complexity nie dodał nowego
  naruszenia, a istniejący `service.py` pozostaje zamrożonym hotspotem.
- Po managed restart `GET /api/health` zwraca `status=ok`; Ads i Localo action
  detail mają evidence, `apply_allowed=false`, status `Zapis zmian zablokowany`
  i HTTP 200.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/audit-selectors-live.png`
  oraz snapshot z technicznym disclosure poniżej decyzji.
- Commit implementacji: `b9f5ca3` wypchnięty na `origin/main`.
- Brak POST, vendor write, zmiany credentiali lub nowych endpointów.

## Beads

- `wilq-seo-jnra` pozostaje `P0 / in_progress` dla szerszego splitu monolitu.
- `wilq-seo-c9h9.4`, `wilq-seo-c9h9.11` i `wilq-seo-zbre` pozostają zamknięte.

## Następny slice

Re-audyt pozostałych helperów `service.py` i wybór jednego nowego, potwierdzonego
seamu. Nie przenosić ponownie gotowych boundaries audit/readiness/payload ani
mechanicznie dzielić pliku bez testu zachowania i dowodu użyteczności.

## Otwarte blokery

- `/api/content/work-items/queue` nadal jest `blocked` z powodu
  `not_enough_actionable_candidates` (1 actionable przy minimum 3).
- Goal 005 nadal wymaga realnego Wilku UAT albo jawnego owner defer.
