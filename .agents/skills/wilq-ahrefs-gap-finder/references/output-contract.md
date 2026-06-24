# WILQ Ahrefs Gap Finder Output Contract

## Cel

Analiza luk z Ahrefs ograniczona do istniejącego WILQ evidence i content inventory.

Oczekiwany wynik: okazje gap review z confidence notes, evidence IDs i następnymi krokami walidacji.

## Wymagany kontekst API

Pobierz `GET /api/ahrefs/diagnostics` przed analizą marketingową. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ahrefs-gap-finder"}` i potwierdź, że osadzone `ahrefs_diagnostics` zgadza się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `ahrefs`
- `google_search_console`
- `wordpress_ekologus`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: evidence IDs, connector IDs, notatki freshness i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy evidence jest zagregowane, stare albo niepełne.
4. `Kandydaci działań`: opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące read contracts/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- `ahrefs_diagnostics` ma tylko fakty autorytetu (`domain_rating`, `ahrefs_rank`) i nie ma rekordów luk; wtedy wolno użyć Ahrefs jako kontekstu autorytetu, ale trzeba zablokować claimy o luce treści, luce backlinków i przewadze konkurencji.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.
