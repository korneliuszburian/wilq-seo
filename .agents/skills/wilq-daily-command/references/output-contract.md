# WILQ Dzienny plan - Kontrakt odpowiedzi

## Cel

Poranny przegląd WILQ przez źródła danych, dowody, szanse, akcje, reguły eksperckie i karty wiedzy.

Oczekiwany wynik: zwięzły brief operacyjny ze statusem źródeł danych,
pozycjami planu działań z Centrum pracy, identyfikatorami dowodów,
identyfikatorami szans, identyfikatorami akcji, blokadami i następnymi
bezpiecznymi krokami.

Dzienny plan pokazuje główną pętlę dnia: Merchant, Treści, GSC i WordPress, GA4 i
Google Ads. Nie jest pełnym rejestrem źródeł danych, widokiem Localo ani
widokiem planowania social. Localo może pojawić się w briefie dnia tylko wtedy, gdy
`command_center.daily_decisions` je zwraca albo użytkownik jawnie pyta o
lokalną widoczność. Akcje do sprawdzenia social należą do
`wilq-social-publisher`, nie do briefu dnia.

## Wymagany kontekst API

Pobierz `GET /api/dashboard/command-center` przed analizą marketingową.
To jest kanoniczny first-screen operator view-model używany przez dashboard i
Codex skills.

Następnie pobierz `GET /api/marketing/brief` jako wsparcie daily sections i
podsumowania metryk.

Następnie pobierz `POST /api/codex/context-pack` z
`{"skill":"wilq-daily-command"}` dla szerszego kontekstu: status źródeł danych,
odczyty danych, podsumowania dowodów, szanse, akcje, reguły eksperckie
i karty wiedzy. Osadzony `command_center` jest celowo kompaktowy: użyj
`daily_decisions` jako kanonicznej listy decyzji dnia i potwierdź, że zgadza się z
`GET /api/dashboard/command-center` dla `primary_next_step`, liczby blokad,
liczby zadań taktycznych i pola śladu decyzji dnia. Nie odbudowuj planu dnia
ze starych list `operator_brief` albo `action_plan`. Osadzony `marketing_brief`
w pakiecie kontekstu musi zgadzać się z `GET /api/marketing/brief` dla języka,
identyfikatorów sekcji, liczby blokad, liczby rekomendacji, identyfikatorów dowodów i identyfikatorów akcji.

Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_ads`
- `google_search_console`
- `google_analytics_4`
- `google_merchant_center`
- `ahrefs`
- `localo`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych, status `command_center.daily_decisions` oraz znane blokady.
2. `Dowody`: identyfikatory dowodów, identyfikatory źródeł danych, notatki o świeżości i podsumowania metryk wyłącznie z `Centrum pracy`/`briefu marketingowego`/WILQ API.
3. `Diagnoza`: co wspierają decyzje dnia, z niepewnością, jeśli dowody są zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: `daily_decisions.action_ids`, identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

Oczekiwane identyfikatory akcji w pętli dnia, jeśli WILQ API je zwraca:

- `act_review_merchant_feed_issues`
- `act_review_ga4_tracking_quality`
- `act_prepare_content_refresh_queue`

Nie promuj w pętli dnia:

- `act_prepare_linkedin_social_drafts`
- `act_prepare_facebook_social_drafts`

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu.
