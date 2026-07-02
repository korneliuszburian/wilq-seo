# WILQ Luki z Ahrefs Kontrakt odpowiedzi

## Cel

Analiza luk z Ahrefs ograniczona do istniejących dowodów WILQ i spisu treści.

Oczekiwany wynik: okazje do sprawdzenia SEO z notatkami pewności, identyfikatory dowodów i następnymi krokami sprawdzenia w WILQ.

## Wymagany kontekst API

Pobierz `GET /api/ahrefs/diagnostics` przed analizą marketingową. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ahrefs-gap-finder"}` i potwierdź, że osadzone `ahrefs_diagnostics` zgadza się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `ahrefs`
- `google_search_console`
- `wordpress_ekologus`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych i znane blokady.
2. `Dowody`: identyfikatory dowodów, identyfikatory źródeł danych, notatki freshness i podsumowania metryk wyłącznie z WILQ API.
3. `Diagnoza`: co wspierają dowody, z niepewnością gdy dowody są zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane i dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do krótkiej informacji o blokadzie, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo błąd dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w kontekście WILQ, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `ahrefs_diagnostics` ma tylko dane autorytetu (`domain_rating`, `ahrefs_rank`) i nie ma rekordów luk; wtedy wolno użyć Ahrefs jako kontekstu autorytetu, ale trzeba zablokować wnioski o luce treści, luce backlinków i przewadze konkurencji.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

Jeśli `gap_read_contract.status=ready` oraz `gap_record_count > 0`, nie ustawiaj
top-level `blocked=true` tylko dlatego, że `gap_records_omitted=true` w
context-packu albo że istnieją `blocked_claims`. `gap_records_omitted=true`
oznacza kompaktowanie pakietu kontekstu; pełne rekordy są w
`GET /api/ahrefs/diagnostics`. W takim stanie można dać decyzję review-only
o lukach Ahrefs. Blokuj wyłącznie obietnice wzrostu ruchu, wzrostu autorytetu,
przewagi konkurencyjnej, produkcyjnej treści albo efektu SEO bez dodatkowego
sprawdzenia GSC/WordPress/człowieka.

W odpowiedzi używaj dokładnych nazw pól kontraktu, gdy są ważne dla audytu:
`gap_read_contract`, `gap_record_count`, `missing_read_contracts`,
`gap_records_omitted`, `ahrefs_content_gap_records`,
`ahrefs_backlink_gap_records`, `ahrefs_organic_keywords_by_url`,
`ahrefs_competitor_pages` i `ahrefs_top_pages_by_competitor`.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu.
