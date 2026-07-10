# WILQ widok Google Ads Kontrakt odpowiedzi

## Cel

Diagnostyka Google Ads, jakość kampanii, wyszukiwane hasła, wykluczające słowa kluczowe i bezpieczne akcje do sprawdzenia Ads.

Oczekiwany wynik: ustalenia Ads oparte na dowodach, z akcjami do sprawdzenia wymagającymi sprawdzenia w WILQ.

WILQ API pozostaje kanoniczne dla identyfikatorów dowodów, identyfikatory szans, sprawdzenia akcji i audytu. Zewnętrzne narzędzia lub MCP adaptery mogą być tylko źródłem dowodów zapisanych w WILQ po zapisaniu do WILQ kontraktów.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` przed analizą Ads. `POST /api/codex/context-pack` jest opcjonalnym wzbogaceniem, gdy wąski endpoint nie wystarcza, użytkownik pyta o pełną kolejkę albo trzeba połączyć Ads z inną powierzchnią WILQ. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

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

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Zacznij od kolejności pracy operatora, nie od eksportu diagnostyki. Widoczna odpowiedź musi zawierać polskie etykiety: `Można zrobić teraz`, `Jak sprawdzić`, `Dlaczego teraz`, `Decyzja po review`, `Zablokowane` i `Ślad WILQ`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.
W technicznym rozwinięciu zachowaj również etykiety `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`.


1. `Można zrobić teraz`: 3-5 priorytetów review w kolejności działania. Dla pełnej kolejki Ads zwykle prowadź: kampanie/budżety -> rekomendacje -> wyszukiwane hasła i n-gramy -> wykluczenia -> segmenty niestandardowe. Nie dumpuj wszystkich pól.
2. `Jak sprawdzić`: do każdego priorytetu dodaj jedno pytanie kontrolne lub kryterium decyzji, np. co porównać w kampanii, co odrzucić w rekomendacji, co sprawdzić w intencji wyszukiwanych haseł albo co blokuje segment.
3. `Dlaczego teraz`: krótko pokaż, co wspiera `/api/ads/diagnostics`: gotowość źródła, świeżość odczytu, liczba decyzji/akcji albo konkretne sekcje diagnostyki. Jeśli dowody są stare, niepełne albo zablokowane przez OAuth, zacznij od refresh/blokady.
4. `Decyzja po review`: opisz, co operator może zrobić po ręcznej ocenie: zostawić do obserwacji, odrzucić rekomendację, przygotować pytania do człowieka, poprosić o brakujący kontrakt albo dopiero wtedy przejść do preview akcji.
5. `Zablokowane`: pokaż po ludzku, czego nie wolno twierdzić ani zapisać: zwrot z reklam, koszt pozyskania celu, zmarnowany budżet, wykluczenia, zmiana budżetu, segmenty i prognoza, jeśli brakuje kontraktów, zgody albo podglądu akcji.
6. `Ślad WILQ`: identyfikatory dowodów, źródeł danych, szans i akcji. Wynik walidacji akcji pokaż, jeśli użytkownik pyta o podgląd lub zapis. Szczegółowe kontrakty i nazwy pól API zostaw do debug-notatek albo pokaż tylko na jawne życzenie.

W ustrukturyzowanym JSON eval albo handoffie te etykiety nie mogą zostać tylko w `notes`. `Jak sprawdzić` i `Decyzja po review` muszą pojawić się w widocznych polach decyzyjnych, np. w `operator_next_step`, `recommendations[].label_pl` albo `action_candidates[].label_pl`.

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
