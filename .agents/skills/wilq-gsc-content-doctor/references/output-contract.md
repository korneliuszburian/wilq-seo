# WILQ Treści z GSC Kontrakt odpowiedzi

## Cel

Przegląd treści z Search Console połączony ze spisem treści WordPress.

Oczekiwany wynik: akcje do sprawdzenia treści oparte na dowodach z GSC i istniejącym spisie treści WordPress.

## Wymagany kontekst API

Najpierw pobierz `GET /api/content/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-gsc-content-doctor"}` i potwierdź, że `content_diagnostics.evidence_ids` oraz `content_diagnostics.action_ids` zgadzają się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_search_console`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych i znane blokady.
2. `Dowody`: `content_diagnostics` identyfikatorów sekcji, identyfikatory dowodów, identyfikatory źródeł danych, notatki o świeżości, fakty o zapytaniach i adresach oraz status dopasowania spisu WordPress wyłącznie z WILQ API.
3. `Diagnoza`: co wspierają dane o zapytaniach, adresach i spisie WordPress, z niepewnością, jeśli dowody są zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: tactical queue item IDs i identyfikatory akcji, szczególnie `act_prepare_content_refresh_queue`, jeśli są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `content_diagnostics.live_data_available=false`, a użytkownik prosi o rekomendacje treści zamiast stan gotowości albo blokady.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.

## Bezpieczeństwo treści

`act_prepare_content_refresh_queue` jest przygotowanie bez zapisu. Może wspierać planowanie refresh/create/merge/block, podgląd zmian i sprawdzenie w WILQ. Nie może obiecywać edycji WordPress, automatycznej publikacji, wzrostu pozycji, wzrostu leadów ani gwarancji braku duplikacji bez przyszłego wsparcia zapisu zmian i audytu.
