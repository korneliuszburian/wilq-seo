# WILQ Treści z GSC Kontrakt odpowiedzi

## Cel

Przegląd treści z Search Console połączony ze spisem treści WordPress.

Oczekiwany wynik: akcje do sprawdzenia treści oparte na dowodach z GSC i istniejącym spisie treści WordPress.

## Wymagany kontekst API

Najpierw pobierz `GET /api/content/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-gsc-content-doctor"}` i potwierdź, że `content_diagnostics.evidence_ids` oraz `content_diagnostics.action_ids` zgadzają się z endpointem. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_search_console`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Zacznij od krótkiej decyzji operatorskiej, a nie od surowego raportu API. Widoczna odpowiedź musi zawierać polskie etykiety: `Można zrobić teraz`, `Dlaczego`, `Mapa decyzji`, `Co sprawdzić ręcznie`, `Jak sprawdzić na stronie`, `Brief do pokazania Wilkowi` i `Zablokowane`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Można zrobić teraz`: jedna bezpieczna decyzja lub akcja do sprawdzenia, np. która strona/temat idzie do ręcznej oceny refresh/merge/create/block.
2. `Dlaczego`: jednozdaniowe uzasadnienie z WILQ API, np. GSC pokazuje sygnał zapytań/adresu, a WordPress potwierdza istniejący URL lub brak inventory.
3. `Mapa decyzji`: wskaż tryb decyzji (`odświeżyć`, `scalić`, `utworzyć` albo `zablokować`), URL albo temat, poziom gotowości i powód z kolejki WILQ.
4. `Co sprawdzić ręcznie`: użyj dokładnie tej etykiety. Wypisz krótką checklistę: intencja zapytań, nagłówki/CTA, kanibalizacja/duplikacja, canonical/inventory i decyzja odświeżyć vs scalić vs utworzyć.
5. `Jak sprawdzić na stronie`: podaj konkretny przegląd strony: title/meta, H1/H2, brakujące sekcje pod intencję, CTA/usługa, canonical i linkowanie wewnętrzne.
6. `Brief do pokazania Wilkowi`: 3-5 zdań bez technicznego żargonu: co WILQ proponuje, z czego to wynika, co jest tylko sygnałem i jaka decyzja review jest potrzebna.
7. `Zablokowane`: co nie jest gotową decyzją publikacyjną, jakich claims nie wolno powiedzieć i czego brakuje do zapisu albo publikacji.
8. `Ślad techniczny`: identyfikatory dowodów, źródeł danych, tactical queue item IDs i identyfikatory akcji, szczególnie `act_prepare_content_refresh_queue`, jeśli są dostępne. Surowe endpointy i walidacje pokazuj tu, nie na początku odpowiedzi.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `content_diagnostics.live_data_available=false`, a użytkownik prosi o rekomendacje treści zamiast stan gotowości albo blokady.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.

## Reguły Search Analytics

GSC Search Analytics nie jest traktowane jak pełny raport całego ruchu. Skill
musi użyć metadanych z najnowszego `google_search_console` `vendor_read`:

- `data_availability_checked=true` i `date_availability_status=available`
  oznaczają, że WILQ najpierw sprawdził dostępne daty przez wymiar `date`;
- `date_start`/`date_end` w metric summary oznaczają najnowszy dostępny dzień
  szczegółów, a nie automatycznie dzisiejszą datę;
- `expected_data_delay_days_min=2` i `expected_data_delay_days_max=3`
  oznaczają typowe opóźnienie dostępności danych Search Analytics;
- `search_type=web` ogranicza interpretację do web search;
- `detail_dimensions=query,page` i
  `detail_data_completeness=partial_possible` oznaczają, że wiersze
  zapytań i adresów są sygnałem do decyzji treściowej, ale nie pełną sumą ruchu;
- `aggregate_dimensions=country,device`,
  `aggregate_aggregation_type=byProperty` i
  `aggregate_data_completeness=aggregate_without_query_page_dimensions`
  oznaczają osobny agregat ruchu bez wymiarów zapytań i adresów; można go użyć jako
  kontekstu wolumenu, ale nie jako dowodu skuteczności konkretnej frazy lub URL;
- `read_granularity=single_day_latest_available`,
  `api_recommended_page_size=25000` i
  `api_daily_row_cap_per_search_type=50000` opisują oficjalny wzorzec
  pobierania większych zbiorów danych;
- `query_page_row_limit`, `query_page_max_rows` i
  `query_page_rows_truncated` mówią, jak WILQ ograniczył bieżący odczyt
  operacyjny i czy wynik mógł zostać ucięty.

W odpowiedzi dla operatora powiedz po polsku, jeśli decyzja opiera się na
najnowszym dostępnym dniu i częściowych danych zapytań i adresów. Nie obiecuj pełnej
diagnostyki ruchu, kanibalizacji ani wzrostu pozycji bez dodatkowych dowodów.

## Bezpieczeństwo treści

`act_prepare_content_refresh_queue` jest przygotowanie bez zapisu. Może wspierać planowanie refresh/create/merge/block, podgląd zmian i sprawdzenie w WILQ. Nie może obiecywać edycji WordPress, automatycznej publikacji, wzrostu pozycji, wzrostu leadów ani gwarancji braku duplikacji bez przyszłego wsparcia zapisu zmian i audytu.
