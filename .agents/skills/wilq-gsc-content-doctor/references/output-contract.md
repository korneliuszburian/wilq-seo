# WILQ GSC Content Doctor Output Contract

## Cel

Search Console content triage joined with WordPress inventory boundaries.

Oczekiwany wynik: akcje do sprawdzenia SEO/content oparci na GSC evidence i istniejącym content inventory.

## Wymagany kontekst API

Najpierw pobierz `GET /api/content/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-gsc-content-doctor"}` i potwierdź, że `content_diagnostics.evidence_ids` oraz `content_diagnostics.action_ids` zgadzają się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_search_console`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i action IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: `content_diagnostics` section IDs, evidence IDs, connector IDs, freshness notes, query/page facts i WordPress inventory match status wyłącznie z WILQ API.
3. `Diagnoza`: co wspierają query/page matrix i WordPress inventory, z niepewnością, jeśli evidence jest zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: tactical queue item IDs i action IDs, szczególnie `act_prepare_content_refresh_queue`, jeśli są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, odczytach źródeł danych, expert rules ani akcjach do sprawdzenia.
- `content_diagnostics.live_data_available=false`, a użytkownik prosi o content recommendations zamiast readiness/blocker status.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak audit event oznacza brak write.

## Bezpieczeństwo treści

`act_prepare_content_refresh_queue` jest przygotowanie bez zapisu. Może wspierać planowanie refresh/create/merge/block, podgląd zmian i sprawdzenie w WILQ. Nie może obiecywać edycji WordPress, automatycznej publikacji, wzrostu pozycji, wzrostu leadów ani gwarancji braku duplikacji bez przyszłego wsparcia zapisu zmian i audytu.
