# WILQ Social Publisher Output Contract

## Cel

Gotowość publikacji LinkedIn/Facebook i social ActionObjects oparte na evidence.

Oczekiwany wynik: kandydaci postów social z source evidence, stanem review i blockerami connectorów.

## Wymagany kontekst API

Pobierz `POST /api/codex/context-pack` z
`{"skill":"wilq-social-publisher"}` przed analizą marketingową. Skillowy
context-pack musi zawierać `social_draft_context`; traktuj go jako typed draft
contract, a nie promptowy generator postów. Użyj
`GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy
readiness ma znaczenie.

Wymagane connectory:

- `linkedin`
- `facebook`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: `social_draft_context`, candidate inputs, evidence IDs, connector IDs, notatki freshness i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy evidence jest zagregowane, stare albo niepełne.
4. `Kandydaci działań`: użyj `social_draft_context.candidate_inputs`, `draft_action_ids`, `draft_constraints`, `missing_publish_permissions` i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- Skillowy context-pack nie zawiera `social_draft_context`.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.
