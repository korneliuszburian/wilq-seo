# WILQ Ads Doctor Output Contract

## Cel

Diagnostyka Google Ads, jakość kampanii, search terms, negative keywords i bezpieczni kandydaci działań Ads.

Oczekiwany wynik: ustalenia Ads oparte na evidence, z kandydatami działań pozostającymi pending do walidacji przez WILQ API.

WILQ API pozostaje kanoniczne dla evidence IDs, opportunity IDs, action validation i audytu. Zewnętrzne narzędzia lub MCP adaptery mogą być tylko źródłem read-only evidence po zapisaniu do WILQ kontraktów.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` przed analizą Ads. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor"}` i użyj osadzonego `ads_diagnostics` jako consistency check, także opcjonalnego `blocked_handoff`. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_ads`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów, `blocked_handoff.status` jeśli istnieje, i znane blockery.
2. `Dowody`: Ads diagnostics section IDs, evidence IDs, connector IDs, latest refresh status, freshness notes i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera `/api/ads/diagnostics`, z niepewnością, jeśli evidence jest zagregowane, stare, niepełne albo zablokowane przez OAuth. Używaj `allowed_metrics`, `missing_read_contracts` i `blocked_claims` z typed contracts zamiast własnych reguł w prose.
4. `Kandydaci działań`: opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia. Kandydatów zmian opisuj jako review/safety queue, dopóki ActionObject nie ma zwalidowanego apply support, confirm i audit boundary.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- `/api/ads/diagnostics` zwraca `live_data_available=false`, a użytkownik pyta o spend, CPA, ROAS, search terms, negative keywords, campaign scaling albo budget changes.
- Użytkownik prosi o zmianę budżetów, pauzowanie kampanii albo skalowanie kampanii zanim `act_prepare_ads_campaign_review_queue` istnieje, jest zwalidowany i ma wsparcie pozostałych read contracts: change history, recommendations, impression share, business goal i apply preview.
- `negative_keywords_read_contract` jest missing, blocked albo nie ma kandydatów, a użytkownik pyta o negative keyword candidates.
- Użytkownik prosi o apply negative keywords zanim `act_prepare_negative_keyword_review_queue` istnieje i jest zwalidowany.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.

## Granica MCP

Jeśli Google Ads MCP server będzie dostępny później, używaj go tylko jako read-only adaptera, dopóki WILQ nie ma zwalidowanego write ActionObject dla żądanej operacji. Output z narzędzia MCP musi zostać przekształcony w WILQ evidence albo refresh-run state, zanim stanie się rekomendacją.
