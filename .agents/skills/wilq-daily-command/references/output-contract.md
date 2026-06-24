# WILQ Daily Command - Output Contract

## Cel

Daily command-center triage przez connectory, evidence, opportunities, actions, expert rules i knowledge cards.

Oczekiwany wynik: zwięzły operating brief z source connector status,
CommandCenter action-plan items, evidence IDs, opportunity IDs, action IDs,
blockers i następnymi bezpiecznymi krokami.

Daily Command pokazuje core daily loop: Merchant, Content/GSC/WordPress, GA4 i
Ads. Nie jest pełnym registry connectorów, Localo dashboardem ani social
planning surface. Localo może pojawić się w daily briefie tylko wtedy, gdy
`command_center.daily_decisions` je zwraca albo użytkownik jawnie pyta o
lokalną widoczność. Social draft ActionObjects należą do
`wilq-social-publisher`, nie do daily briefu.

## Wymagany kontekst API

Pobierz `GET /api/dashboard/command-center` przed analizą marketingową.
To jest kanoniczny first-screen operator view-model używany przez dashboard i
Codex skills.

Następnie pobierz `GET /api/marketing/brief` jako wsparcie daily sections i
metric summaries.

Następnie pobierz `POST /api/codex/context-pack` z
`{"skill":"wilq-daily-command"}` dla szerszego kontekstu: connector status,
refresh runs, evidence summaries, opportunities, ActionObjects, expert rules
and knowledge cards. Osadzony `command_center` jest celowo kompaktowy: użyj
`daily_decisions` jako kanonicznej daily decision list i potwierdź, że zgadza się z
`GET /api/dashboard/command-center` dla `primary_next_step`, blocker count,
tactical item count i daily decision trace fields. Nie odbudowuj daily planu
z legacy list `operator_brief` albo `action_plan`. Osadzony `marketing_brief`
w context packu musi zgadzać się z `GET /api/marketing/brief` dla language,
section IDs, blocker count, recommendation count, evidence IDs i action IDs.

Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

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

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów, status `CommandCenter.daily_decisions` oraz znane blockery.
2. `Dowody`: evidence IDs, connector IDs, freshness notes i metric summaries wyłącznie z `CommandCenter`/`MarketingBrief`/WILQ API.
3. `Diagnoza`: co wspierają daily decisions, z niepewnością, jeśli evidence jest zagregowane, stare albo niepełne.
4. `Kandydaci działań`: `daily_decisions.action_ids`, opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

Core ActionObject IDs oczekiwane w daily loop, jeśli WILQ API je zwraca:

- `act_review_merchant_feed_issues`
- `act_review_ga4_tracking_quality`
- `act_prepare_content_refresh_queue`

Nie promuj w daily loop:

- `act_prepare_linkedin_social_drafts`
- `act_prepare_facebook_social_drafts`

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.
