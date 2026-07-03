# WILQ Demand Gen Operator Kontrakt odpowiedzi

## Cel

Planowanie gotowości Demand Gen na podstawie dowodów z Ads i GA4.

Oczekiwany wynik: ustalenia gotowości Demand Gen, blokady i akcje do sprawdzenia w WILQ.

## Wymagany kontekst API

Pobierz `GET /api/demand-gen/diagnostics` przed analizą marketingową. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-demand-gen-operator"}` i potwierdź, że osadzony kontrakt Demand Gen zgadza się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_ads`
- `google_analytics_4`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Werdykt Demand Gen`, `Dlaczego stop`, `Co mamy z Ads/GA4`, `Czego brakuje do oceny`, `Podgląd bez zapisu`, `Kiedy wrócić`, `Zablokowane obietnice`, `Brief dla marketera`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Werdykt Demand Gen`: czy WILQ widzi kampanie Demand Gen/Discovery i czy ocena jest review-only albo zablokowana.
2. `Dlaczego stop`: konkretny powód blokady, np. 0 kampanii Demand Gen/Discovery mimo dostępnych danych Ads/GA4.
3. `Co mamy z Ads/GA4`: liczba ocenionych kampanii/kanałów i źródła dowodów tylko z WILQ API.
4. `Czego brakuje do oceny`: kampania Demand Gen/Discovery, dane kreacji/assets, landing-quality per kampania, GA4 traffic-quality dla tej kampanii.
5. `Podgląd bez zapisu`: action_id albo review preview, które można sprawdzić w WILQ bez zmiany kampanii.
6. `Kiedy wrócić`: warunki, po których Demand Gen można oceniać dalej, np. po pojawieniu się kampanii i danych kreacji/ruchu.
7. `Zablokowane obietnice`: rekomendacja uruchomienia, gotowość trybu, ocena jakości kreacji, skuteczność assetów, zmiana kampanii i wzrost skuteczności.
8. `Brief dla marketera`: 3-5 zdań normalnym językiem: co wiemy, dlaczego nie rekomendujemy launchu, co sprawdzić teraz i czego potrzeba do kolejnego kroku.
9. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
10. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
11. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
