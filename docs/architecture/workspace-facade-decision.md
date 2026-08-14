# Workspace facade and catalog module — decision

Rola dokumentu: `decision` — rozstrzyga, czego nie refaktoryzujemy, żeby
przyszłe review architektury nie proponowały tego ponownie. Nie nadpisuje
żadnego bieżącego stanu (kod jest źródłem prawdy).

## Kontekst

Architecture review (2026-08) zgłosił Finding 7: `workspace/api.py` to
"passthrough facade" (18× import `contracts.contracts`, funkcje delegują
do `_build_*`), a `catalog.py` "miesza read + cache + bind".

## Decyzja: odrzucone z dowodem

Obie tezy są nieaktualne względem aktualnego kodu, więc nie wykonujemy
refaktoru:

1. **`catalog.py` nie zawiera żadnego zapisu.** `bind_content_inventory_item`
   (linia 507) to read-only binding: rozwiązuje URL do materiału i zwraca
   response, bez persistencji i bez vendor write. Wszystkie pozostałe
   funkcje to read-y (metric_store, local_state_store list-y). Deletion test:
   usunięcie `catalog.py` zmusiłoby document_workspace do re-implementacji
   inventory reads — complexity reappears, nie znika.

2. **`api.py` to celowy adapter, nie shallow module.** Funkcje
   `build_*_response` są stabilnym interfejsem dla routerów (HTTP
   response-adaptacja), a realna logika mieszka w `stage_*` /
   `snapshot_assembly` — to jest poprawny podział adapter/implementation.
   18 importów z `contracts.contracts` to 18 różnych typów (wszystkie
   używane — ruff F401 czysty), nie duplikacja. Deletion test: usunięcie
   api.py rozproszyłoby response-building po routerach, nie skoncentrowało.

## Co NIE jest objęte

Refaktor `catalog.py` byłby uzasadniony dopiero gdyby bind zaczął
persistować (wtedy write powinien przejść za ActionObject — patrz AGENTS.md
o action services).

## Następca

Ten dokument zastępuje Finding 7 z raportu architektury 2026-08. Przyszłe
review nie powinny ponownie proponować rozbicia api.py/catalog.py bez
nowego dowodu (np. faktycznego zapisu w catalog albo rozrostu api.py do
>1000 linii z duplikacją).
