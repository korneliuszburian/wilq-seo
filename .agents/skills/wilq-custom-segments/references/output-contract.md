# WILQ Segmenty Niestandardowe Kontrakt odpowiedzi

## Cel

Generowanie akcji do sprawdzenia segmentów niestandardowych wyłącznie z terminów i dowodów dostępnych w WILQ API.

Oczekiwany wynik: segmenty do sprawdzenia z `source_terms`, `evidence_ids`, poziomem pewności, identyfikatory akcji i blokadami sprawdzenia w WILQ.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` przed analizą marketingową. `POST /api/codex/context-pack` z `{"skill":"wilq-custom-segments"}` jest opcjonalnym wzbogaceniem, gdy wąski endpoint nie wystarcza albo trzeba połączyć Ads z inną powierzchnią WILQ. `ads_diagnostics.custom_segments_read_contract` jest źródłem prawdy dla akcji do sprawdzenia segmentów. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_ads`
- `google_search_console`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Mapa segmentu`, `Hasła źródłowe`, `Review intencji`, `Podgląd bez zapisu`, `Decyzja po review`, `Zablokowane`, `Brief dla marketera`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Mapa segmentu`: nazwa/intent segmentu z API, review_priority, review_score i review_reason jako kolejność ręcznej oceny, nie dowód skuteczności.
2. `Hasła źródłowe`: pokaż tylko `source_terms` z WILQ API; nie dopisuj nowych fraz ani synonimów.
3. `Review intencji`: co trzeba odsiać ręcznie: intencję haseł, dopasowanie do usługi, ryzyko zbyt szerokiego segmentu, landing page i przypadkowe terminy.
4. `Podgląd bez zapisu`: jaki action_id/preview można sprawdzić w WILQ bez zmiany kierowania.
5. `Decyzja po review`: po sprawdzeniu operator może przygotować podgląd, zawęzić segment, odłożyć temat albo zablokować segment.
6. `Zablokowane`: zapis kierowania, rozmiar odbiorców, prognoza, skuteczność kampanii, zwrot z reklam i wzrost konwersji.
7. `Brief dla marketera`: 3-5 zdań normalnym językiem: co WILQ może przygotować, z czego to wynika, czego brakuje i jaki jest następny bezpieczny krok.
8. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
9. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
10. `Następny krok`: najmniejszy bezpieczny krok operatora.

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

Zakazane twierdzenia pokazuj jako blokady w `Status`, `Diagnoza`, `Sprawdzenie w WILQ`,
`Następny krok` albo w polu `blocked_reason`. Nie wkładaj ich do etykiety
rekomendacji segmentu jako zwykłego zdania, nawet z negacją. Etykieta segmentu
ma opisywać tylko propozycję, `source_terms`, priorytet review i powód review.

Jeśli akcji do sprawdzenia nie ma, pokaż brakujące dane po ludzku, np. brak wzbogacenia Keyword Planner albo brak prognozy rozmiaru odbiorców. Szczegółowe pola `custom_segments_read_contract.missing_read_contracts` i `next_step` zostaw do technicznych notatek/debugu.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `custom_segments_read_contract.status=blocked` albo nie ma `source_terms`.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
