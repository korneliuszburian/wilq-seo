# Handoff: `jnra` action preview dispatcher — 2026-07-12

## Decyzja

Routing previewów został wyjęty z `wilq/actions/service.py` do
`wilq/actions/action_previews.py`. Dispatcher mapuje stabilne `preview_contract`
i action types do istniejących rendererów domenowych; `ActionObject` pozostaje
źródłem fallbacku, gdy kontrakt nie ma centralnego handlera. Usunięto 311
lokalnych wrapperów, zachowując publiczny `demand_gen_readiness_preview_cards`
dla istniejącego context API.

## Dowody

- `tests/actions/test_action_preview_contracts.py`: nowy test potwierdza
  routing Merchant do domain ownera; istniejące preview contract tests pozostają
  zielone.
- `tests/actions/test_action_object_contracts.py`: pełny focused regression
  przechodzi; typowane preview cards, review copy i fail-closed apply pozostają
  bez zmian.
- `rtk uv run ruff check` i `rtk uv run mypy` dla zmienionych modułów przechodzą;
  complexity nie zgłasza nowego violation w dispatcherze, a `service.py` maleje
  z 1868 do 1648 LOC.
- Managed runtime po restarcie: `/api/health` `ok`, metrics `99906` facts / 4577
  refresh runs / 8 connectors. `/api/content/work-items/queue` nadal jawnie
  zwraca `blocked`, 2 candidates, 1 actionable przy minimum 3.
- WordPress readiness nadal fail-closed: `ready_to_request_apply=false`,
  `vendor_write_possible=false`, 7 typed blockers, operator next step pozostaje
  przygotowanie zatwierdzonego handoffu i paczki szkicu.
- Browser proof pozostaje aktualny, bo slice nie zmienia UI:
  `.local-lab/proof/continuation-2026-07-12/c9h9-14-cache-mobile.png`.
- Brak nowych endpointów, vendor writes, credentiali, publikacji lub zmian w
  kontraktach payloadów.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; komentarz z tym handoffem dodany.
- `wilq-seo-c9h9.14` pozostaje zamknięty jako external-state false positive.
- Nie utworzono nowego Beada: seam wynika z aktywnego zakresu `jnra` i nie
  ujawnił osobnej luki produktowej.

## Następny slice

Ponowny audyt pozostałego `service.py` i runtime; wybrać tylko kolejny
potwierdzony owner boundary, który poprawia utrzymanie bez przenoszenia reguł do
React ani tworzenia nowych endpointów.

## Pozostałe blokery

- Content queue: świeży stan `not_enough_actionable_candidates` — 1 actionable
  przy wymaganych 3; nie wolno dopisać sztucznego tematu.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer z residual risk.
