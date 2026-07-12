# Handoff: `jnra.1` parity rejestru akcji — 2026-07-12

## Decyzja

`list_actions()` i `get_action()` korzystają z jednej canonical registry
assembly. Przy potwierdzonym live Google Ads read legacy akcja naprawy OAuth nie
jest aktywną prawdą ani na liście, ani pod bezpośrednim URL. Gdy live read nie
istnieje, zachowuje dotychczasowy review-only flow.

## Dowody

- `wilq/actions/service.py`: `_action_registry()` skupia static, metric i
  API-owned dynamiczne akcje Ads; żadna reguła nie trafiła do dashboardu ani
  write adaptera.
- `tests/actions/test_action_object_contracts.py`: live business-context case
  wymaga 404 dla legacy lookupu; OAuth redaction case jawnie ustawia scenariusz
  bez live read i nadal wymaga 200.
- Focused testy: ActionObject contracts 48/48, action evidence 6/6, action
  list cache 4/4; Ruff i mypy dla zmienionej fasady przechodzą. Cache nosi key
  najnowszego Google Ads refreshu i zapisuje wynik tylko przy stabilnym
  fingerprint przed/po buildzie, więc stale no-live inventory nie jest używany
  po przejściu do live read.
- Managed API po restarcie: lista nie zawiera legacy action, direct legacy
  lookup zwraca 404, aktywny Keyword Planner lookup zwraca 200. Mutation
  readiness WordPress pozostaje `false/false/false`; nie wykonano vendor write.
- Complexity: 422 pliki Python / 136631 non-empty LOC, `service.py` 1650 LOC.
  Standardowy changed audit jawnie flaguje frozen facade i wcześniejsze duże
  testy; wariant dopuszczony dla dokumentowanego seamu przechodzi.

## Granice

Nie zmieniono credentiali, odczytu Google Ads, endpointów, ActionObject safety
loop ani canonical WordPress draft-only roli. Brak zmiany dashboardu, więc
browser proof nie jest wymagany dla tego API-only slice'a.

## Beads

- `wilq-seo-jnra.1`: bug parity rejestru jest zamknięty po final review i proof.
- `wilq-seo-jnra`: pozostaje aktywnym parentem; jego opis został zrebaseline'owany
  do aktualnego rozmiaru fasady i zamkniętych granic.

## Następny krok

Po commicie wrócić do `jnra` i wybrać wyłącznie kolejny potwierdzony seam. Obecny
kandydat z review: eligibility Keyword Planner w istniejącym module
`wilq/actions/google_ads/keyword_planner.py`; nie łączyć go z tym bugfixem.
