# Rotacja poświadczeń WILQ

Rola dokumentu: `reference` / runbook operacyjny. Opisuje procedurę L6, ale nie
jest zgodą na rotację, zgodą OAuth ani dowodem jej wykonania. Każdą decyzję o
rotacji, zmianę po stronie dostawcy i unieważnienie poprzedniego poświadczenia
wykonuje wyłącznie właściciel WILQ (`OWNER`).

## Zasada obowiązująca zawsze

- Wartości poświadczeń nie trafiają do gita, terminalowego outputu, logów,
  dokumentacji, Beada, zrzutu ekranu ani podsumowania. W dowodzie wolno zapisać
  nazwę pola, bezpieczną etykietę źródła, status, czas oraz identyfikator runu i
  evidence.
- `wilq/security/redaction.py` redaguje dane przed logami i context packami.
  Redakcja jest dodatkową barierą, a nie zgodą na wklejanie wartości do wejścia.
- Źródłem lokalnym jest `.env` wskazany opcjonalnie przez `WILQ_ENV_FILE`;
  fallbackiem jest access pack wskazany przez `WILQ_ACCESS_PACK_PATH`. Istniejąca
  zmienna procesu ma pierwszeństwo, dlatego po zmianie pliku działający stack
  trzeba przeładować.
- Po każdej rotacji `OWNER` najpierw sprawdza stan stacka przez
  `scripts/local_stack.sh`, następnie `GET /api/connectors`, a potem uruchamia
  świeży, tylko-do-odczytu refresh właściwego konektora. Samo `configured`
  potwierdza obecność wymaganych nazw, nie działanie poświadczenia u dostawcy.
- Dowodem jest świeży refresh zakończony odczytem danych, z bezpiecznym statusem,
  czasem, identyfikatorem runu i evidence. Dowód nie zawiera wartości ani ścieżki
  prywatnego pliku.

Nazwy objęte tą procedurą obejmują między innymi
`WORDPRESS_EKOLOGUS_APP_PASSWORD` (alias
`EKOLOGUS_WP_STAGING_APP_PASSWORD`), `GOOGLE_ADS_DEVELOPER_TOKEN`,
`AHREFS_API_TOKEN` (alias `AHREFS_API_KEY`) oraz
`GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID` (alias
`GOOGLE_SHEETS_SPREADSHEET_ID`). Alias nie jest drugim miejscem na kopię tej
samej wartości: `OWNER` wybiera jedno źródło i usuwa konflikt pierwszeństwa.

## Hasło aplikacyjne WordPress — `WORDPRESS_EKOLOGUS_APP_PASSWORD`

**Operator:** wyłącznie `OWNER`, zalogowany do właściwego profilu WordPress i
mający lokalny dostęp do prywatnego źródła runtime.

### Kroki

1. `OWNER` zatwierdza zakres, konektor `wordpress_ekologus`, czas oraz bezpieczne
   miejsce przechowania poprzedniej wartości na czas weryfikacji. Nie unieważnia
   jej jeszcze.
2. W WordPress przechodzi do profilu użytkownika, do sekcji **Application
   Passwords / Hasła aplikacyjne**, i generuje nowe hasło dla jednoznacznie
   nazwanej integracji WILQ.
3. Aktualizuje tylko `WORDPRESS_EKOLOGUS_APP_PASSWORD` w repo-local `.env` albo
   w `ekologus.env` bieżącego access packa. Nie wpisuje wartości do komendy,
   dokumentu ani drugiego, konkurencyjnego źródła.
4. Przeładowuje zarządzany stack przez właściwą operację
   `scripts/local_stack.sh`, bez wyświetlania środowiska procesu.
5. Sprawdza `GET /api/connectors`: `wordpress_ekologus` ma być `configured` bez
   ujawnienia wartości. Następnie uruchamia świeży refresh konektora i odczytuje
   jego zredagowany wynik.
6. Dopiero po pozytywnej weryfikacji unieważnia poprzednie hasło aplikacyjne w
   profilu WordPress i zapisuje wyłącznie bezpieczny dowód unieważnienia.

### Weryfikacja

Dowód zawiera operatora `OWNER`, czas, ID konektora, bezpieczną etykietę źródła,
status `configured`, ID świeżego refresh runu, status odczytu i evidence ID.
Brak fresh vendor read albo błąd autoryzacji oznacza, że rotacja nie została
zweryfikowana.

### Rollback

Przed unieważnieniem starego hasła `OWNER` przywraca poprzednią wartość w tym
samym prywatnym źródle, ponownie przeładowuje stack i wykonuje świeży refresh.
Po unieważnieniu nie wolno próbować użyć starego hasła: `OWNER` generuje kolejne
hasło aplikacyjne i powtarza procedurę od początku.

## Google OAuth — Google Ads, GSC i GA4

Zakres obejmuje token developerski Google Ads oraz komplet OAuth używany przez
Google Ads, Google Search Console i Google Analytics 4. Pliki JSON OAuth lub
Google application credentials zawsze pozostają poza gitem.

**Operator:** wyłącznie `OWNER`, mający uprawnienia do właściwego konta Google
Cloud, konta menedżera Google Ads i prywatnego źródła runtime WILQ.

### Kroki

1. `OWNER` zatwierdza zakres konektorów i zabezpiecza poprzedni, spójny komplet
   poświadczeń do czasu zakończenia weryfikacji.
2. W konsoli właściwego dostawcy odnawia albo zastępuje developer token Google
   Ads i wymagane poświadczenia OAuth. Dla Google Ads utrzymuje spójny komplet
   nazw `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`,
   `GOOGLE_ADS_CLIENT_SECRET` oraz `GOOGLE_ADS_REFRESH_TOKEN`. Dla GSC i GA4
   prywatny plik może być wskazany przez `GOOGLE_APPLICATION_CREDENTIALS` albo
   umieszczony w katalogu `credentials/` access packa.
3. Zapisuje nowy komplet w jednym prywatnym źródle: `.env` albo access packu.
   Nie dodaje JSON do repozytorium, nie wkleja jego treści do logu ani Beada i
   nie miesza elementów starego oraz nowego kompletu.
4. Przeładowuje zarządzany stack. Sprawdza w `GET /api/connectors`, że
   `google_ads`, `google_search_console` i `google_analytics_4` mają oczekiwany
   stan konfiguracji.
5. Uruchamia oddzielny świeży, tylko-do-odczytu vendor refresh dla każdego
   konektora objętego rotacją i zachowuje wyłącznie zredagowane metadane runu.
6. Dopiero po udanych odczytach wycofuje poprzedni komplet po stronie Google i
   zapisuje bezpieczny dowód tej decyzji.

### Weryfikacja

Każdy objęty konektor musi mieć świeży zakończony vendor read, evidence ID i
brak błędu autoryzacji. `DEVELOPER_TOKEN_NOT_APPROVED` jest zewnętrznym blockerem
akceptacji tokenu Google Ads: nawet gdy konektor raportuje `configured`, taki
wynik nie jest dowodem działającego dostępu i wymaga decyzji `OWNER` po stronie
Google.

### Rollback

`OWNER` przywraca cały poprzedni komplet — nie pojedynczy element — w tym samym
prywatnym źródle, przeładowuje stack i ponawia trzy właściwe refreshe. Jeśli
poprzedni komplet został już unieważniony, rollback przez ponowne użycie jest
niemożliwy; trzeba wydać kolejny komplet i powtórzyć weryfikację.

## Rotacja całego access packa — `WILQ_ACCESS_PACK_PATH`

Access pack jest prywatnym katalogiem poza repozytorium. `WILQ_ACCESS_PACK_PATH`
wskazuje jego aktywną lokalizację; bez tej zmiennej runtime korzysta z
datowanego katalogu domowego zdefiniowanego w `wilq/credentials/runtime.py`.
Pakiet może zawierać `ekologus.env` oraz prywatny katalog `credentials/`.

**Operator:** wyłącznie `OWNER`, mający dostęp do bieżącego i nowego prywatnego
katalogu pakietu.

### Kroki

1. `OWNER` zatwierdza rotację całego pakietu i pozostawia poprzedni katalog
   niezmieniony do końca weryfikacji.
2. Tworzy nowy, prywatny katalog poza gitem, umieszcza w nim nowy spójny zestaw
   `ekologus.env` i potrzebnych plików `credentials/`, a następnie sprawdza jego
   prywatne uprawnienia bez odczytywania wartości do outputu.
3. Inspekcja przez `scripts/access_pack_check.sh` może raportować tylko obecność,
   liczniki i `secrets_redacted`; nie używa się szczegółowego manifestu jako
   artefaktu rotacji. Nazwy/presence są dozwolone, wartości nie.
4. `OWNER` przełącza prywatną konfigurację `WILQ_ACCESS_PACK_PATH` na nowy
   katalog i przeładowuje zarządzany stack.
5. Sprawdza `GET /api/connectors`, a dla każdego konektora zależnego od pakietu
   wykonuje świeży, tylko-do-odczytu refresh. Dotyczy to także pól takich jak
   `AHREFS_API_TOKEN` i `GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID`, jeśli są częścią
   zatwierdzonego zakresu; konektor celowo wyłączony nie staje się błędem
   rotacji tylko dlatego, że pozostaje `disabled`.
6. Dopiero po akceptacji dowodu `OWNER` wycofuje poprzedni pakiet i unieważnia
   zastąpione poświadczenia u ich dostawców.

### Weryfikacja

Bezpieczny artefakt zawiera operatora, czas, etykietę `access_pack_env` lub
`access_pack_credentials`, stan `configured` oraz świeże refresh run IDs i
evidence IDs dla objętych konektorów. Inspekcja pakietu potwierdza tylko
nazwy/presence i liczniki; nie wolno interpretować samej obecności jako udanego
vendor read.

### Rollback

`OWNER` ponownie wskazuje niezmieniony poprzedni katalog przez
`WILQ_ACCESS_PACK_PATH`, przeładowuje stack i powtarza status oraz refreshe.
Poprzedniego pakietu nie usuwa się ani nie unieważnia przed pomyślną
weryfikacją nowego.

## Zapis dowodu i warunek zakończenia

Do aktywnego Beada trafiają wyłącznie: operator, czas, zakres, ID konektorów,
bezpieczne etykiety źródeł, refresh run IDs, evidence IDs, statusy oraz blocker.
Runbook nie dowodzi, że rotacja została wykonana. L6 można uznać za operacyjnie
zweryfikowane dopiero po osobno autoryzowanej rotacji, świeżych odczytach i
potwierdzonym unieważnieniu poprzednich poświadczeń — nadal bez zapisania ich
wartości.
