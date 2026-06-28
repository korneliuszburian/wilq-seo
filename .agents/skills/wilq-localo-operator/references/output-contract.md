# WILQ Localo Operator Kontrakt odpowiedzi

## Cel

Gotowość lokalnej widoczności oraz akcje do sprawdzenia Localo/GBP.

Oczekiwany wynik: status status dostępu Localo, lokalne blokady widoczności i bezpieczne następne kroki. Jeśli OAuth działa, ale brakuje danych, powiedz to wprost. Korzystaj z `statusów odczytu danych`: obietnicę wolno oprzeć tylko na kontrakcie ze statusem `ready`. Gotowe dane Localo traktuj jako evidence zapisanym w WILQ, a `zadania lokalne`, zapis zmian i każdy kontrakt bez statusu `ready` trzymaj jako blocker.

## Wymagany kontekst API

Pobierz `GET /api/localo/diagnostics` przed analizą marketingową. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-localo-operator"}` i potwierdź, że osadzone `localo_diagnostics` zgadza się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `localo`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych i znane blokady.
2. `Dowody`: identyfikatory dowodów, identyfikatory źródeł danych, notatki freshness i podsumowania metryk wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy dowody są zagregowane, stare albo niepełne. Dla Localo agregatów danych wolno mówić o liczbie lokalizacji, monitorowanych fraz, średniej widoczności/grid position i recenzjach tylko wtedy, gdy te metryki są w `localo_diagnostics`.
4. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Żądana obietnica wymaga danych Localo, których nie ma w `allowed_evidence`; np. `wyniki GBP`, `widoczność konkurencji`, `ukończone zadanie lokalne`, `zapis zmian GBP` albo `poprawa widoczności lokalnej`.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
