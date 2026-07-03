# WILQ Localo Operator Kontrakt odpowiedzi

## Cel

Gotowość lokalnej widoczności oraz akcje do sprawdzenia Localo/GBP.

Oczekiwany wynik: status dostępu Localo, lokalne blokady widoczności i bezpieczne następne kroki. Jeśli OAuth działa, ale brakuje danych, powiedz to wprost. Korzystaj z `statusów odczytu danych`: obietnicę wolno oprzeć tylko na kontrakcie ze statusem `ready`. Gotowe dane Localo traktuj jako dowody zapisane w WILQ, a `zadania lokalne`, zapis zmian i każdy kontrakt bez statusu `ready` trzymaj jako blokadę.

## Wymagany kontekst API

Pobierz `GET /api/localo/diagnostics` przed analizą marketingową. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-localo-operator"}` i potwierdź, że osadzone `localo_diagnostics` zgadza się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `localo`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Czy Localo działa`, `Mapa lokalna`, `Kolejność review`, `Braki i blokady`, `Podgląd bez zapisu`, `Decyzja po review`, `Brief dla marketera`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Czy Localo działa`: zasięg API, dostęp, świeżość odczytu i czy workflow jest review-only.
2. `Mapa lokalna`: miejsca/profile, frazy/rankingi, GBP, konkurencja i opinie tylko z metryk WILQ API. Dla Localo agregatów danych wolno mówić o liczbie lokalizacji, monitorowanych fraz, średniej widoczności/grid position i recenzjach tylko wtedy, gdy te metryki są w `localo_diagnostics`.
3. `Kolejność review`: 3-5 punktów, od których operator ma zacząć, np. średnia widoczność, pozycje w siatce, GBP, konkurencja, recenzje.
4. `Braki i blokady`: stare dane, brak `local_tasks`, brak zapisu GBP, brak obietnicy poprawy widoczności/rankingu.
5. `Podgląd bez zapisu`: action_id albo review preview, które można sprawdzić w WILQ bez mutacji.
6. `Decyzja po review`: po sprawdzeniu operator może odświeżyć Localo, przygotować listę działań lokalnych, odłożyć temat albo zablokować claim.
7. `Brief dla marketera`: 3-5 zdań normalnym językiem: co wiemy, co można sprawdzić, czego brakuje i następny bezpieczny krok.
8. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
9. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
10. `Następny krok`: najmniejszy bezpieczny krok operatora.

Jeśli `connector.freshness.state` jest `stale` albo notatka mówi `do
odświeżenia`, nie nazywaj odczytu świeżym. Powiedz: "dostęp działa, ale odczyt
jest do odświeżenia" i ustaw odświeżenie Localo jako pierwszy krok przed
finalną oceną.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Żądana obietnica wymaga danych Localo, których nie ma w `allowed_evidence`; np. `wyniki GBP`, `widoczność konkurencji`, `ukończone zadanie lokalne`, `zapis zmian GBP` albo `poprawa widoczności lokalnej`.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

Jeśli Localo ma dostęp (`mcp_initialize_status=200` albo status dostępu ready),
metryki agregatów w `localo_diagnostics` i zwalidowaną akcję review, nie ustawiaj
top-level `blocked=true` tylko dlatego, że zablokowane są twierdzenia o zapisie lub wzroście.
W takim stanie workflow jest review-only i powinien jasno mówić: Localo działa
do diagnostyki, a zablokowane pozostają `ukończone zadanie lokalne`, `zapis
zmian w profilu firmy`, `poprawa widoczności lokalnej`, write/apply oraz
obietnice rankingu bez dalszej walidacji.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
