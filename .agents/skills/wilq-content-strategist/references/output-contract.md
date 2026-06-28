# WILQ Strateg treści Kontrakt odpowiedzi

## Cel

Planowanie treści z dowodów WILQ API, istniejącego spisu treści i kart wiedzy.

Oczekiwany wynik: priorytetowy plan treści z identyfikatorami dowodów, identyfikatory źródeł danych, kontrolą istniejących treści i akcjami do sprawdzenia.

## Wymagany kontekst API

Najpierw pobierz `GET /api/content/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-content-strategist"}` i potwierdź, że istnieje osadzone `content_diagnostics`. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_search_console`
- `google_analytics_4`
- `ahrefs`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych i znane blokady.
2. `Dowody`: `content_diagnostics` identyfikatorów sekcji, identyfikatory zadań taktycznych, identyfikatory dowodów, identyfikatory źródeł danych, świeżość danych, fakty o zapytaniach/stronach i status dopasowania w spisie treści WordPress wyłącznie z WILQ API.
3. `Diagnoza`: co dowody wspierają dla zachowania, odświeżenia, scalenia, nowej treści albo blokady, z niepewnością, jeśli dowody są zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: tactical queue item IDs, identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Kolejka decyzji

Użyj `content_diagnostics.decision_queue` z WILQ API jako kanonicznej kolejki
treści. Skill nie powinien sam klasyfikować adresów ani przepisywać reguł
deduplikacji z promptu.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokady, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `content_diagnostics.live_data_available=false`, a użytkownik prosi o plan treści zamiast statusu gotowości/blokady.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.

## Bezpieczeństwo treści

Używaj `act_prepare_content_refresh_queue` wyłącznie jako przygotowanie bez zapisu. Skill może sugerować planowanie refresh/create/merge/block i podgląd zmian, ale nie może obiecywać edycji WordPress, publikacji, wzrostu pozycji, wzrostu leadów ani gwarancji braku duplikacji bez sprawdzonej w WILQ ścieżki zapisu zmian i audytu.
