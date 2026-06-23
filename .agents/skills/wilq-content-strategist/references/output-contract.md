# WILQ Content Strategist Output Contract

## Cel

Planowanie treści z API evidence, istniejącego inventory i knowledge cards.

Oczekiwany wynik: priorytetowy content plan z evidence IDs, source connectors, kontrolą istniejących treści i kandydatami działań.

## Wymagany kontekst API

Najpierw pobierz `GET /api/content/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-content-strategist"}` i potwierdź, że istnieje osadzone `content_diagnostics`. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_search_console`
- `google_analytics_4`
- `ahrefs`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. API identifiers, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: `content_diagnostics` section IDs, tactical item IDs, evidence IDs, connector IDs, freshness notes, query/page facts i WordPress inventory match status wyłącznie z WILQ API.
3. `Diagnoza`: co evidence wspiera dla refresh/create/merge/block, z niepewnością, jeśli evidence jest zagregowane, stare albo niepełne.
4. `Kandydaci działań`: tactical queue item IDs, opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Kolejka decyzji

Użyj `content_diagnostics.decision_queue` z WILQ API jako kanonicznej kolejki
contentowej. Skill nie powinien sam klasyfikować URL-i ani przepisywać reguł
deduplikacji z promptu.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- `content_diagnostics.live_data_available=false`, a użytkownik prosi o content plan zamiast readiness/blocker status.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.

## Bezpieczeństwo treści

Używaj `act_prepare_content_refresh_queue` wyłącznie jako prepare-only. Skill może sugerować planowanie refresh/create/merge/block i payload preview, ale nie może claimować edycji WordPress, publikacji, wzrostu pozycji, lead uplift ani gwarancji braku duplikacji bez zwalidowanego apply support i audytu.
