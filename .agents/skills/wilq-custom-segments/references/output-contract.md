# WILQ Custom Segments Output Contract

## Cel

Generowanie kandydatów custom segments wyłącznie z terminów i evidence dostępnych w WILQ API.

Oczekiwany wynik: kandydaci segmentów z `source_terms`, `evidence_ids`, poziomem pewności, ActionObject IDs i blockerami walidacji.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` oraz `POST /api/codex/context-pack` z `{"skill":"wilq-custom-segments"}` przed analizą marketingową. `ads_diagnostics.custom_segments_read_contract` jest źródłem prawdy dla kandydatów segmentów. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_ads`
- `google_search_console`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: evidence IDs, connector IDs, notatki freshness i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy evidence jest zagregowane, stare albo niepełne.
4. `Kandydaci działań`: opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Kandydat segmentu

Dla każdego kandydata z `custom_segments_read_contract.candidates` pokaż:

- nazwę i intent z API;
- `source_terms` bez dopisywania nowych fraz;
- `review_priority`, `review_score` i dokładny sens `review_reason`, żeby operator
  widział, że ranking kolejki review nie jest dowodem audience size ani wpływu
  na kampanię;
- `payload_preview` jako review-only podgląd, z informacją że `apply_allowed=false`;
- `evidence_ids` i `source_connectors`;
- `confidence` oraz `validation_status`;
- `action_ids`, jeśli API je wystawia;
- `blocked_claims`, zwłaszcza `audience size`, `ROAS`, `targeting applied` i `campaign performance`.

Jeśli kandydatów nie ma, pokaż `custom_segments_read_contract.missing_read_contracts` i `next_step`.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- `custom_segments_read_contract.status=blocked` albo nie ma `source_terms`.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.
