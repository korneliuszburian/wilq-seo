# WILQ Ahrefs Gap Finder Output Contract

## Cel

Analiza luk z Ahrefs ograniczona do istniejących dowodów WILQ i spisu treści.

Oczekiwany wynik: okazje do sprawdzenia SEO z notatkami pewności, evidence IDs i następnymi krokami sprawdzenia w WILQ.

## Wymagany kontekst API

Pobierz `GET /api/ahrefs/diagnostics` przed analizą marketingową. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ahrefs-gap-finder"}` i potwierdź, że osadzone `ahrefs_diagnostics` zgadza się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `ahrefs`
- `google_search_console`
- `wordpress_ekologus`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i action IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: evidence IDs, connector IDs, notatki freshness i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy evidence jest zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: opportunity IDs i action IDs, gdy są dostępne; w przeciwnym razie opisz brakujące dane i dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do krótkiej informacji o blokadzie, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo błąd dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w kontekście WILQ, dowodach, odczytach źródeł danych, expert rules ani akcjach do sprawdzenia.
- `ahrefs_diagnostics` ma tylko dane autorytetu (`domain_rating`, `ahrefs_rank`) i nie ma rekordów luk; wtedy wolno użyć Ahrefs jako kontekstu autorytetu, ale trzeba zablokować wnioski o luce treści, luce backlinków i przewadze konkurencji.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak audit event oznacza brak zapisu.
