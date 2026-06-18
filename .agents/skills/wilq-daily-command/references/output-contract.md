# WILQ Daily Command Output Contract

## Cel

Daily command-center triage across connectors, evidence, opportunities, actions, expert rules and knowledge cards.

Oczekiwany wynik: A concise operating brief with source connector status,
CommandCenter action-plan items, evidence IDs, opportunity IDs, action IDs,
blockers and next safe steps.

Daily Command pokazuje core daily loop: Merchant, Content/GSC/WordPress, GA4 i
Ads. Nie jest pełnym registry connectorów ani social planning surface. Localo
może pojawić się w daily briefie tylko jako realny blocker albo ograniczenie
claimów, dopóki WILQ API nie ma Localo ranking/GBP evidence. Social draft
ActionObjects należą do `wilq-social-publisher`, nie do daily briefu.

## Wymagany kontekst API

Pobierz `GET /api/dashboard/command-center` przed analizą marketingową.
This is the canonical first-screen operator view model used by dashboard and
Codex skills.

Then fetch `GET /api/marketing/brief` for supporting daily sections and metric
summaries.

Then fetch `POST /api/codex/context-pack` with
`{"skill":"wilq-daily-command"}` for wider context: connector status,
refresh runs, evidence summaries, opportunities, ActionObjects, expert rules
and knowledge cards. The embedded `command_center` in the context pack must
match `GET /api/dashboard/command-center` for `operator_brief`, `demo_script`,
`action_plan`, `primary_next_step`, blocker count, tactical item count and
action IDs. The embedded `marketing_brief` in the context pack must match
`GET /api/marketing/brief` for language, section IDs, blocker count,
recommendation count, evidence IDs and action IDs.

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

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. API identifiers, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów, status `CommandCenter.operator_brief` i `CommandCenter.action_plan` oraz znane blockery.
2. `Dowody`: evidence IDs, connector IDs, freshness notes and metric summaries from `CommandCenter`/`MarketingBrief`/WILQ API only.
3. `Diagnoza`: what the operator brief and action plan support, with uncertainty if the evidence is aggregate, stale or incomplete.
4. `Kandydaci działań`: `action_plan.action_ids`, `operator_brief.action_ids`, opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
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
