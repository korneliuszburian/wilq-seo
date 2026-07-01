# WILQ widok Google Ads Kontrakt odpowiedzi

## Cel

Diagnostyka Google Ads, jakość kampanii, wyszukiwane hasła, wykluczające słowa kluczowe i bezpieczne akcje do sprawdzenia Ads.

Oczekiwany wynik: ustalenia Ads oparte na dowodach, z akcjami do sprawdzenia wymagającymi sprawdzenia w WILQ.

WILQ API pozostaje kanoniczne dla identyfikatorów dowodów, identyfikatory szans, sprawdzenia akcji i audytu. Zewnętrzne narzędzia lub MCP adaptery mogą być tylko źródłem dowodów zapisanych w WILQ po zapisaniu do WILQ kontraktów.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` przed analizą Ads. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor"}` i użyj osadzonego `ads_diagnostics` jako consistency check, także opcjonalnego `blocked_handoff`. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Jeżeli użytkownik prosi o pełną kolejkę Ads albo miesza wiele obszarów naraz
budżety, rekomendacje, kampanie, wyszukiwane hasła, wykluczenia i segmenty,
pobierz `POST /api/codex/context-pack` z
`{"skill":"wilq-ads-doctor","full_context":true}` albo oprzyj listę decyzji na
pełnym `GET /api/ads/diagnostics`. Domyślny skillowy context-pack może być
skompaktowany, więc nie wolno go opisywać jako pełnej kolejki, jeśli zawiera
mniej decyzji niż `/api/ads/diagnostics`.

Wymagane źródła danych:

- `google_ads`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych, świeżość ostatniego odczytu, `blocked_handoff.status` jeśli istnieje, i znane blokady. Jeśli odczyt jest stary, najpierw wskaż read-only refresh albo blokadę świeżości.
2. `Dowody`: Ads diagnostics identyfikatorów sekcji, identyfikatory dowodów, identyfikatory źródeł danych, status ostatniego odczytu, notatki o świeżości i podsumowania metryk wyłącznie z WILQ API.
3. `Diagnoza`: 3-5 priorytetów review w kolejności działania, nie dump wszystkich pól. Wyjaśnij krótko, co wspiera `/api/ads/diagnostics`, z niepewnością, jeśli dowody są zagregowane, stare, niepełne albo zablokowane przez OAuth. Używaj `allowed_metrics`, `missing_read_contracts` i `blocked_claims` z kontraktów API zamiast własnych reguł w opisie.
4. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia. Akcje do sprawdzenia opisuj jako kolejkę sprawdzenia bezpieczeństwa, dopóki akcja nie ma wsparcia sprawdzonego w WILQ zapisu zmian, potwierdzenia i audytu.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- `/api/ads/diagnostics` zwraca `live_data_available=false`, a użytkownik pyta o koszt reklam, koszt pozyskania celu, zwrot z reklam, wyszukiwane hasła, wykluczające słowa kluczowe, skalowanie kampanii albo zmiany budżetu.
- Użytkownik prosi o zmianę budżetów, pauzowanie kampanii albo skalowanie kampanii zanim `act_prepare_ads_campaign_review_queue` istnieje, jest sprawdzony w WILQ i ma wsparcie pozostałych kontraktów odczytu danych: change history, recommendations, impression share, business goal i podgląd zapisu zmian.
- `negative_keywords_read_contract` jest missing, blocked albo nie ma akcji do sprawdzenia, a użytkownik pyta o propozycje wykluczeń.
- Użytkownik prosi o zapis zmian wykluczających słów kluczowych zanim `act_prepare_negative_keyword_review_queue` istnieje i jest sprawdzony w WILQ.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.

## Granica MCP

Jeśli Google Ads serwer MCP będzie dostępny później, używaj go tylko jako adaptera odczytu danych, dopóki WILQ nie ma sprawdzonej ścieżki zapisu zmian dla żądanej operacji. Wynik z narzędzia MCP musi zostać przekształcony w dowody WILQ albo stan odczytu danych, zanim stanie się rekomendacją.
