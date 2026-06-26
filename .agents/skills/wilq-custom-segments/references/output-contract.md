# WILQ Custom Segments Output Contract

## Cel

Generowanie akcji do sprawdzenia custom segments wyłącznie z terminów i evidence dostępnych w WILQ API.

Oczekiwany wynik: segmenty do sprawdzenia z `source_terms`, `evidence_ids`, poziomem pewności, action IDs i blockerami sprawdzenia w WILQ.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` oraz `POST /api/codex/context-pack` z `{"skill":"wilq-custom-segments"}` przed analizą marketingową. `ads_diagnostics.custom_segments_read_contract` jest źródłem prawdy dla akcji do sprawdzenia segmentów. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_ads`
- `google_search_console`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i action IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: evidence IDs, connector IDs, notatki freshness i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy evidence jest zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: opportunity IDs i action IDs, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Segment do sprawdzenia

Dla każdej propozycji z `custom_segments_read_contract.candidates` pokaż:

- nazwę i intent z API;
- `source_terms` bez dopisywania nowych fraz;
- `review_priority`, `review_score` i dokładny sens `review_reason`, żeby operator
  widział, że ranking kolejki review nie jest dowodem audience size ani wpływu
  na kampanię;
- podgląd zmian z API jako materiał do sprawdzenia w WILQ, z informacją że zapis zmian nie jest dozwolony;
- `evidence_ids` i `source_connectors`;
- `confidence` oraz `validation_status`;
- `action_ids`, jeśli API je wystawia;
- `blocked_claims`, zwłaszcza `audience size`, `ROAS`, `targeting applied` i `campaign performance`.

Jeśli akcji do sprawdzenia nie ma, pokaż `custom_segments_read_contract.missing_read_contracts` i `next_step`.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, odczytach źródeł danych, expert rules ani akcjach do sprawdzenia.
- `custom_segments_read_contract.status=blocked` albo nie ma `source_terms`.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak audit event oznacza brak write.
