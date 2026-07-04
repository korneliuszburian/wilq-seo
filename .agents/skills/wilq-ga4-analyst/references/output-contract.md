# WILQ Analityka GA4 Kontrakt odpowiedzi

## Cel

Diagnostyka zachowania GA4, stron wejścia i pomiaru oparta na dowodach z Analytics Data API.

Oczekiwany wynik: diagnostyka GA4 z podsumowaniem metryk, identyfikatorami dowodów, ograniczeniami i bezpiecznymi akcjami do sprawdzenia.

## Wymagany kontekst API

Najpierw pobierz `GET /api/ga4/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ga4-analyst"}` i potwierdź, że `ga4_diagnostics` istnieje przed analizą marketingową. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_analytics_4`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Pomiar do naprawy`, `Ruch do oceny`, `Kolejność triage`, `Decyzja po review`, `Brief dla marketera`, `Czego nie wolno twierdzić`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Pomiar do naprawy`: wskaż wiersze `(not set)` jako problem przypisania strony wejścia, źródła albo kampanii. Nie oceniaj po nich kampanii, SEO ani strony.
2. `Ruch do oceny`: wskaż czytelne wiersze strony wejścia, źródła i kampanii, które można sprawdzać pod kątem dopasowania komunikatu do strony wejścia.
3. `Kolejność triage`: najpierw `(not set)` i tracking/reporting, potem czytelne wiersze ruchu, potem ActionObject review.
4. `Decyzja po review`: powiedz, jakie decyzje są możliwe po ręcznym sprawdzeniu: problem pomiaru, content/landing review, brak decyzji albo dalsze dane.
5. `Brief dla marketera`: 3-5 zdań bez technicznego żargonu: co GA4 pokazuje, czego nie pokazuje, co jest problemem pomiaru, co jest ruchem do oceny i jaki jest następny bezpieczny krok.
6. `Czego nie wolno twierdzić`: ROI, przychód, spadek konwersji, współczynnik konwersji, zwrot z reklam, naprawiony pomiar i zapis w GA4 bez osobnych dowodów.
7. `Akcje do sprawdzenia`: identyfikatory decyzji, identyfikatory szans, identyfikatory kolejki taktycznej i identyfikatory akcji, jeśli są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
8. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
9. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `ga4_diagnostics.live_data_available=false`, a użytkownik prosi o jakość stron wejścia, gotowość konwersji, brak pomiaru, jakość kampanii albo rekomendacje zachowania.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.

## Bezpieczeństwo GA4

`active_users`, `sessions` i `engagement_rate` wspierają przegląd jakości ruchu, nie obietnice zwrotu z reklam, przychodu, spadku konwersji ani opłacalności. Jeśli brakuje metryk podobnych do konwersji, powiedz to wprost i utrzymaj następny krok jako przegląd/przygotowanie bez zapisu.

Reguły kolejki decyzji:

- Decyzja o pomiarze oznacza najpierw przegląd trackingu i raportowania; nie zamieniaj tego w rekomendację treściową ani kampanijną.
- Decyzja o stronie wejścia oznacza, że trzeba potwierdzić adres i dopasowanie WordPress przed oceną strony wejścia.
- Decyzja o jakości ruchu oznacza, że dowody mogą wspierać przegląd jakości ruchu i dopasowania komunikatu, ale nie obietnice zwrotu z reklam, przychodu ani opłacalności.
