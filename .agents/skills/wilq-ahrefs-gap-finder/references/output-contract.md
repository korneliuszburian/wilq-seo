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

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Mapa luk`, `Kolejność review`, `Co porównać ręcznie`, `Decyzja po review`, `Brief dla marketera`, `Zablokowane obietnice`, `Dowody` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Mapa luk`: rozdziel luki treści, luki linków, strony konkurencji, organic keywords i kontekst autorytetu. Nie mieszaj ich w jedną ogólną "szansę SEO".
2. `Kolejność review`: wskaż pierwszy typ luki do ręcznego sprawdzenia i powód z WILQ/Ahrefs, np. rekordy luk są dostępne, ale efekt wymaga dalszego cross-checku.
3. `Co porównać ręcznie`: wypisz checklistę: temat konkurenta, istniejący URL Ekologus, intencja, pokrycie treści, możliwość linkowania/źródeł i czy temat wymaga GSC i WordPress cross-checku.
4. `Decyzja po review`: powiedz, co może się wydarzyć po sprawdzeniu: content brief, link-review, dalszy cross-check albo blokada tematu.
5. `Brief dla marketera`: 3-5 zdań bez technicznego żargonu: co Ahrefs pokazuje, do czego to służy i czego nie wolno jeszcze obiecać.
6. `Zablokowane obietnice`: wzrost ruchu, wzrost autorytetu, przewaga konkurencyjna, produkcyjna treść i efekt SEO bez dalszego sprawdzenia.
7. `Dowody`: identyfikatory dowodów, identyfikatory źródeł danych, notatki freshness i podsumowania metryk wyłącznie z WILQ API.
8. `Następny krok`: najmniejszy bezpieczny krok operatora.

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
sprawdzenia GSC i WordPress albo człowieka.

W odpowiedzi używaj dokładnych nazw pól kontraktu, gdy są ważne dla audytu:
`gap_read_contract`, `gap_record_count`, `missing_read_contracts`,
`gap_records_omitted`, `ahrefs_content_gap_records`,
`ahrefs_backlink_gap_records`, `ahrefs_organic_keywords_by_url`,
`ahrefs_competitor_pages` i `ahrefs_top_pages_by_competitor`.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu.
