# WILQ GSC Content Doctor Output Contract

## Cel

Search Console content triage joined with WordPress inventory boundaries.

Oczekiwany wynik: kandydaci działań SEO/content oparci na GSC evidence i istniejącym content inventory.

## Wymagany kontekst API

Najpierw pobierz `GET /api/content/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-gsc-content-doctor"}` i potwierdź, że `content_diagnostics.evidence_ids` oraz `content_diagnostics.action_ids` zgadzają się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_search_console`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: `content_diagnostics` section IDs, evidence IDs, connector IDs, freshness notes, query/page facts i WordPress inventory match status wyłącznie z WILQ API.
3. `Diagnoza`: co wspierają query/page matrix i WordPress inventory, z niepewnością, jeśli evidence jest zagregowane, stare albo niepełne.
4. `Kandydaci działań`: tactical queue item IDs i ActionObject IDs, szczególnie `act_prepare_content_refresh_queue`, jeśli są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- `content_diagnostics.live_data_available=false`, a użytkownik prosi o content recommendations zamiast readiness/blocker status.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.

## Bezpieczeństwo treści

`act_prepare_content_refresh_queue` jest prepare-only. Może wspierać planowanie refresh/create/merge/block, payload preview i walidację. Nie może claimować edycji WordPress, automatycznej publikacji, wzrostu pozycji, lead uplift ani gwarancji braku duplikacji bez przyszłego apply support i audytu.
