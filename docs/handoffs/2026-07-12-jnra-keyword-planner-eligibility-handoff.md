# Handoff: `jnra.2` Keyword Planner eligibility — 2026-07-12

## Decyzja

Eligibility oraz sanitizacja blokady Keyword Plannera należą do istniejącego
modułu `wilq/actions/google_ads/keyword_planner.py`, razem z konstruktorem,
walidacją i preview tej akcji. `service.py` tylko przekazuje najnowszy Google
Ads vendor-read do jednej factory.

## Dowody

- Factory zwraca akcję wyłącznie dla completed `vendor_read` z
  `vendor_data_collected=true` i rozpoznaną blokadą dostępu; nieznany, ready,
  incomplete lub status-probe zwraca `None`.
- `tests/actions/test_keyword_planner_action_factory.py` sprawdza sanitizację,
  evidence order oraz wszystkie stany niekwalifikujące. Existing API action
  contract i preview contract przechodzą; focused wynik to 7/7 + 1/1.
- Ruff i mypy dla zmienionych modułów przechodzą. Complexity: 423 pliki Python
  / 136735 non-empty LOC, `service.py` 1616 LOC; dopuszczony raport frozen
  facade nie wykazuje nowego funkcjonalnego przekroczenia.
- Managed API po restarcie: akcja jest `prepare`, `apply_allowed=false`,
  `destructive=false`, ma zsanityzowaną blokadę i nie zawiera raw vendor markers.
  WordPress mutation readiness pozostaje `false/false/false`; nie wykonano
  vendor write.

## Granice

Nie zmieniono Google Ads read, developer-token readiness, credentiali,
endpointów, claim policy, ActionObject safety loop ani dashboardu. Browser proof
nie jest wymagany dla tego backendowego seamu.

## Beads

- `wilq-seo-jnra.2`: zamknięty po final review i proof.
- `wilq-seo-jnra`: pozostaje aktywnym parentem; kolejne seamy wymagają świeżego
  dowodu, nie mechanicznego splitu.

## Następny krok

Po commicie wybrać z `jnra` następny potwierdzony seam. Nie wracać do registry,
cache, Keyword Planner, WordPress preview ani mutation-readiness bez nowego
runtime/testowego dowodu.
