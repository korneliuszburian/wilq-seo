# WILQ Segmenty Niestandardowe Kontrakt odpowiedzi

## Cel

Generowanie akcji do sprawdzenia segmentów niestandardowych wyłącznie z terminów i dowodów dostępnych w WILQ API.

Oczekiwany wynik: segmenty do sprawdzenia z `source_terms`, `evidence_ids`, poziomem pewności, identyfikatory akcji i blokadami sprawdzenia w WILQ.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` oraz `POST /api/codex/context-pack` z `{"skill":"wilq-custom-segments"}` przed analizą marketingową. `ads_diagnostics.custom_segments_read_contract` jest źródłem prawdy dla akcji do sprawdzenia segmentów. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_ads`
- `google_search_console`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych i znane blokady.
2. `Dowody`: identyfikatory dowodów, identyfikatory źródeł danych, notatki freshness i podsumowania metryk wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera evidence, z niepewnością gdy dowody są zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Segment do sprawdzenia

Dla każdej propozycji z `custom_segments_read_contract.candidates` pokaż:

- nazwę i intent z API;
- `source_terms` bez dopisywania nowych fraz;
- `review_priority`, `review_score` i dokładny sens `review_reason`, żeby operator
  widział, że ranking kolejki sprawdzenia nie jest dowodem rozmiaru odbiorców ani wpływu
  na kampanię;
- podgląd zmian z API jako materiał do sprawdzenia w WILQ, z informacją że zapis zmian nie jest dozwolony;
- `evidence_ids` i `source_connectors`;
- `confidence` oraz `validation_status`;
- `action_ids`, jeśli API je wystawia;
- `blocked_claims`, zwłaszcza `rozmiar odbiorców`, `zwrot z reklam`, `zapis kierowania reklam` i `skuteczność kampanii`.

Jeśli akcji do sprawdzenia nie ma, pokaż `custom_segments_read_contract.missing_read_contracts` i `next_step`.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `custom_segments_read_contract.status=blocked` albo nie ma `source_terms`.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
