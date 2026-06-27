# WILQ Ads Doctor Output Contract

## Cel

Diagnostyka Google Ads, jakość kampanii, wyszukiwane hasła, wykluczające słowa kluczowe i bezpieczne akcje do sprawdzenia Ads.

Oczekiwany wynik: ustalenia Ads oparte na dowodach, z akcjami do sprawdzenia pozostającymi do sprawdzenia przez WILQ API.

WILQ API pozostaje kanoniczne dla evidence IDs, opportunity IDs, sprawdzenia akcji i audytu. Zewnętrzne narzędzia lub MCP adaptery mogą być tylko źródłem dowodów zapisanych w WILQ po zapisaniu do WILQ kontraktów.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` przed analizą Ads. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor"}` i użyj osadzonego `ads_diagnostics` jako consistency check, także opcjonalnego `blocked_handoff`. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_ads`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i action IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów, `blocked_handoff.status` jeśli istnieje, i znane blockery.
2. `Dowody`: Ads diagnostics section IDs, evidence IDs, connector IDs, latest refresh status, freshness notes i metric summaries wyłącznie z WILQ API.
3. `Diagnoza`: co wspiera `/api/ads/diagnostics`, z niepewnością, jeśli dowody są zagregowane, stare, niepełne albo zablokowane przez OAuth. Używaj `allowed_metrics`, `missing_read_contracts` i `blocked_claims` z kontraktów API zamiast własnych reguł w opisie.
4. `Akcje do sprawdzenia`: opportunity IDs i action IDs, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia. Akcje do sprawdzenia opisuj jako kolejkę sprawdzenia bezpieczeństwa, dopóki akcja nie ma wsparcia sprawdzonego w WILQ zapisu zmian, potwierdzenia i audytu.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- `/api/ads/diagnostics` zwraca `live_data_available=false`, a użytkownik pyta o koszt reklam, koszt pozyskania celu, zwrot z reklam, wyszukiwane hasła, wykluczające słowa kluczowe, skalowanie kampanii albo zmiany budżetu.
- Użytkownik prosi o zmianę budżetów, pauzowanie kampanii albo skalowanie kampanii zanim `act_prepare_ads_campaign_review_queue` istnieje, jest sprawdzony w WILQ i ma wsparcie pozostałych kontraktów odczytu danych: change history, recommendations, impression share, business goal i podgląd zapisu zmian.
- `negative_keywords_read_contract` jest missing, blocked albo nie ma akcji do sprawdzenia, a użytkownik pyta o propozycje wykluczeń.
- Użytkownik prosi o zapis zmian wykluczających słów kluczowych zanim `act_prepare_negative_keyword_review_queue` istnieje i jest sprawdzony w WILQ.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, odczytach źródeł danych, expert rules ani akcjach do sprawdzenia.
- Użytkownik prosi o zapis zmian bez akcji sprawdzonej w WILQ i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak akcji sprawdzonej w WILQ oznacza brak zapisu zmian. Brak audit event oznacza brak write.

## Granica MCP

Jeśli Google Ads MCP server będzie dostępny później, używaj go tylko jako adaptera odczytu danych, dopóki WILQ nie ma sprawdzonej ścieżki zapisu zmian dla żądanej operacji. Output z narzędzia MCP musi zostać przekształcony w WILQ evidence albo refresh-run state, zanim stanie się rekomendacją.
