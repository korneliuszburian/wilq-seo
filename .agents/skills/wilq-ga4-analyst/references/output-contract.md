# WILQ GA4 Analyst Output Contract

## Cel

Diagnostyka GA4 behavior, landing-page i tracking oparta o Analytics Data API evidence.

Oczekiwany wynik: diagnostyka GA4 z metric summaries, evidence IDs, caveats i bezpiecznymi akcjami do sprawdzenia.

## Wymagany kontekst API

Najpierw pobierz `GET /api/ga4/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ga4-analyst"}` i potwierdź, że `ga4_diagnostics` istnieje przed analizą marketingową. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_analytics_4`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i action IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: `ga4_diagnostics.decision_queue`, `ga4_diagnostics.sections`, evidence IDs, connector IDs, landing/source/campaign metric facts, tactical item IDs i freshness notes wyłącznie z WILQ API.
3. `Diagnoza`: użyj najpierw `decision_queue`. Raportuj typ, status i następny krok zwrócony przez WILQ API, np. `fix_measurement`, `review_landing_mapping` albo `review_traffic_quality`; nie klasyfikuj elementów samodzielnie w opisie. Wyjaśnij, co evidence wspiera, i dodaj niepewność, gdy evidence jest zagregowane, stare, nie ma conversion-like facts albo ma tylko behavior metrics.
4. `Akcje do sprawdzenia`: decision IDs, opportunity IDs, tactical queue IDs i action IDs, jeśli są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, odczytach źródeł danych, expert rules ani akcjach do sprawdzenia.
- `ga4_diagnostics.live_data_available=false`, a użytkownik prosi o jakość stron wejścia, gotowość konwersji, brak pomiaru, jakość kampanii albo rekomendacje zachowania.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak audit event oznacza brak write.

## Bezpieczeństwo GA4

`active_users`, `sessions` i `engagement_rate` wspierają przegląd jakości ruchu, nie obietnice zwrotu z reklam, przychodu, spadku konwersji ani opłacalności. Jeśli brakuje metryk podobnych do konwersji, powiedz to wprost i utrzymaj następny krok jako przegląd/przygotowanie bez zapisu.

Reguły `decision_queue`:

- `fix_measurement` oznacza najpierw przegląd trackingu/raportowania; nie zamieniaj tego w rekomendację contentową ani kampanijną.
- `review_landing_mapping` oznacza, że trzeba potwierdzić mapowanie URL/WordPress przed oceną strony wejścia.
- `review_traffic_quality` oznacza, że dowody mogą wspierać przegląd jakości ruchu i dopasowania komunikatu, ale nie obietnice zwrotu z reklam, przychodu ani opłacalności.
