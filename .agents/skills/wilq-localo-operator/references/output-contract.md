# WILQ Localo Operator Output Contract

## Cel

Gotowość lokalnej widoczności oraz kandydaci działań Localo/GBP.

Oczekiwany wynik: status Localo access, lokalne blockery widoczności i bezpieczne następne kroki. Jeśli OAuth działa, ale brakuje facts, powiedz to wprost. Jeśli są tylko agregaty Localo (`place_inventory`, `local_rankings`, `reviews`), użyj ich jako read-only evidence i nadal blokuj claimy wymagające `gbp_visibility`, `competitor_visibility`, `local_tasks` albo write path.

## Wymagany kontekst API

Pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-localo-operator"}` przed analizą marketingową. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `localo`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. API identifiers, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: evidence IDs, connector IDs, notatki freshness i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy evidence jest zagregowane, stare albo niepełne. Dla Localo aggregate facts wolno mówić o liczbie lokalizacji, monitorowanych fraz, średniej widoczności/grid position i recenzjach tylko wtedy, gdy te metryki są w `localo_diagnostics`.
4. `Kandydaci działań`: opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- Żądany claim wymaga Localo contracts, których nie ma w `allowed_evidence`; np. `GBP performance`, `competitor visibility`, `local task completed`, `GBP write` albo `local visibility uplift`.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.
