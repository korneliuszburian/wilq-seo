# Utrzymanie storage i jobów WILQ

Rola dokumentu: `reference` / runbook operacyjny dla L8. Opisuje istniejące
seamy i warunki dowodowe; nie jest zgodą na maintenance, restore live, migrację,
deploy ani wykonanie vendor write. `OWNER` zatwierdza zakres i okno, a wskazany
operator infrastruktury wykonuje wyłącznie zatwierdzoną procedurę.

## Układ storage: SQLite i DuckDB

WILQ utrzymuje jedną parę plików:

- SQLite: domyślnie `.local-lab/state/wilq.sqlite3`, z opcjonalnym wskazaniem
  przez `WILQ_STATE_DB`;
- DuckDB: domyślnie `.local-lab/state/wilq.duckdb`, z opcjonalnym wskazaniem
  przez `WILQ_METRIC_DB`.

`wilq/storage/private_paths.py` nadaje nowym katalogom prywatnym tryb `0700`, a
plikom store tryb `0600`. `wilq/storage/local_state.py` wywołuje
`reject_newer_sqlite_schema`; `wilq/storage/metric_store.py` używa analogicznego
`reject_newer_duckdb_schema`. Nowszy schemat ma zatrzymać starszy runtime — nie
wolno omijać guarda ani wykonywać cichego downgrade'u.

**Operator:** operator infrastruktury wskazany przez `OWNER`.

**Okno:** odczyt istniejących ścieżek i read-only `storage_proof` nie wymaga
okna. Zmiana ścieżek aktywnej pary, uprawnień albo wersji **requires
owner-approved maintenance window** (wymaga okna serwisowego zatwierdzonego
przez właściciela).

### Kroki

1. Operator zapisuje wyłącznie nazwy `WILQ_STATE_DB` i `WILQ_METRIC_DB` oraz
   rozstrzyga, czy runtime używa ścieżek domyślnych czy zatwierdzonych override'ów.
2. Przed uruchomieniem nowej wersji runtime sprawdza, czy oba pliki są prywatne,
   stanowią jedną zamierzoną parę i nie leżą w ścieżce śledzonej przez git.
3. Pobiera read-only `storage_proof` dla dokładnie tej pary. Nie używa statusu
   store jako preflightu migracji, ponieważ otwarcie store przez runtime może
   uruchomić tworzenie lub podniesienie obsługiwanego schematu.
4. Jeśli wersja jest nowsza niż obsługiwana albo brakuje jednego pliku, zatrzymuje
   procedurę przed uruchomieniem nowego runtime.

### Weryfikacja

Dowód obejmuje ścieżki opisane bez danych uwierzytelniających, tryby `0700` i
`0600` oraz wynik `storage_proof`: wersje SQLite/DuckDB i liczniki rewizji,
audytów oraz faktów metrycznych. `storage_proof` jest dowodem wersji i liczników,
nie hashem całej zawartości.

### Rollback

Sam odczyt nie wymaga rollbacku. Gdy planowana zmiana ścieżki lub wersji nie
przejdzie preflightu, operator nie uruchamia nowego runtime i pozostawia aktywną
parę bez zmian. Każde ponowne wskazanie starej pary jest osobnym cutoverem i
wymaga owner-approved maintenance window.

## Backup i restore z porównaniem proofu

Kanoniczny backup wykonuje `scripts/backup.sh`. Skrypt korzysta z
`copy_storage_pair` i porównuje `storage_proof` źródła oraz kopii. Prymitywy
`copy_sqlite_store`, `copy_duckdb_store`, `copy_storage_pair` i `storage_proof`
są zdefiniowane w `wilq/storage/recovery.py`.

**Operator:** operator infrastruktury wskazany przez `OWNER`; `OWNER` zatwierdza
źródło, cel, retencję i ewentualny cutover.

**Okno:** backup stanowiący podstawę migracji oraz każdy restore/cutover aktywnej
pary **requires owner-approved maintenance window**. Izolowany restore drill do
świeżych ścieżek może odbyć się poza oknem tylko wtedy, gdy nie dotyka aktywnej
pary ani procesu zapisującego.

### Kroki

1. Operator zatrzymuje zarządzany stack i wszystkie niezależne procesy zapisujące
   albo potwierdza zatwierdzoną wyłączność obu store'ów. `scripts/backup.sh` sam
   nie zatrzymuje writerów i nie tworzy wspólnej transakcji między bazami.
2. Wskazuje dokładną parę źródłową oraz nowy, prywatny katalog backupu, po czym
   używa `scripts/backup.sh`. Cele muszą być świeże i różne od źródeł.
3. Zachowuje wynik porównania proofu. Kod sukcesu nie wystarcza bez zgodności
   `before`, wyniku kopii i ponownego `storage_proof` backupu.
4. Restore wykonuje przez `copy_storage_pair` z pary backupowej do dwóch nowych,
   nieistniejących i odmiennych ścieżek. Nie nadpisuje aktywnych plików.
5. Porównuje `storage_proof` backupu z `storage_proof` przywróconej pary. Dopiero
   identyczny wynik pozwala przedstawić ownerowi propozycję cutoveru.
6. Aktywną konfigurację można przełączyć na przywróconą parę tylko w nadal
   zatwierdzonym oknie i po osobnej decyzji `OWNER`.

### Weryfikacja

Dowód zawiera operatora, czas, bezpieczne ścieżki par źródłowej/backupowej/
alternatywnej, tryby plików, kod zakończenia oraz trzy zgodne wyniki
`storage_proof`. Brak zgodności, częściowa para lub istniejąca ścieżka docelowa
przerywa procedurę. Skrypt nie dowodzi harmonogramu, szyfrowania ani kopii
off-host.

### Rollback

Przy błędzie przed cutoverem operator usuwa z rozważań niepełną parę i pozostawia
oryginalne pliki aktywne; prymitywy recovery usuwają świeże cele po częściowej
porażce. Po nieudanym cutoverze zatrzymuje writerów, ponownie wskazuje
niezmienioną poprzednią parę, sprawdza jej `storage_proof`, uruchamia runtime i
wykonuje readback. Nie wykonuje restore in-place i nie nadpisuje plików w ciemno.

## Kandydat backupu przed migracją SQLite

Silniejszy seam dla przyszłych migracji SQLite znajduje się w
`wilq/storage/migration_backup_candidate.py`. Wymaga wcześniej zaakceptowanego,
dokładnego receipt D1 (`exact_post_s5`) z pełnym fingerprintem schematu oraz
tożsamością aplikacji i seedu. Następnie tworzy prywatny kandydat w świeżym
alternatywnym katalogu: dokładną bajtową kopię `wilq.sqlite3` i kanoniczny
`manifest.json`.

Kandydat powstaje najpierw w prywatnym katalogu stagingowym obok celu. Kod
porównuje pełne SHA-256 i rozmiary źródła oraz backupu, inventory/fingerprint D1,
`PRAGMA integrity_check` i readback z próbnego restore do tymczasowej
alternatywnej ścieżki. Następnie atomowo rezerwuje świeży katalog docelowy bez
nadpisania, wiąże zweryfikowany backup i dopiero na końcu manifest jako marker
ważności. SHA-256 dokładnych bajtów manifestu pozostaje poza manifestem w typed
receipt i jest obowiązkowym wejściem do późniejszego verify/restore. Brak
zgodności, zmieniona generacja źródła, niezweryfikowany receipt D1, dodatkowy
plik, alias albo zmieniony backup/manifest kończy procedurę bez ważnego kandydata
i bez zapisu do źródła.

Ten seam dotyczy wyłącznie SQLite, bo jest kandydatem rollbacku dla etapów, które
mutują SQLite. Nie zastępuje ogólnego backupu pary SQLite/DuckDB: `copy_storage_pair`,
komendy `wilq storage backup|restore` i `scripts/backup.sh` pozostają zgodnościowym
fallbackiem operacyjnym bez manifestu. Kandydat D2 nie jest zgodą na migrację,
cutover, dostęp do prywatnego/live storage ani dowodem wykonania restore drill na
docelowym hoście.

## Migracja schematu

Migracja nigdy nie obniża wersji. Nowa migracja musi przejść guard wersji, zostać
wykonana najpierw na świeżej parze odtworzonej z backupu i mieć zdefiniowany
dowód, który może zaprzeczyć zachowaniu danych.

Istniejący jawny seam w `wilq/storage/semantic_review_activation.py` wymaga
`approved_maintenance_window: bool`, świeżych i rozłącznych ścieżek backupu,
porównuje `storage_proof` przed zmianą oraz po niej i blokuje brak zgody przez
`MaintenanceWindowRequired`. Normalny runtime nie wywołuje tej procedury
aktywacji; nie wolno dodawać jej do startupu, endpointu statusowego ani joba.

**Operator:** operator storage wskazany przez `OWNER`, pracujący na dokładnie
zatwierdzonej wersji i parze.

**Okno:** każda migracja aktywnego storage **requires owner-approved maintenance
window**. Ustawienie flagi technicznej nie zastępuje decyzji właściciela.

### Kroki

1. `OWNER` zatwierdza wersję kodu, parę storage, czas, kryteria sukcesu i operatora.
2. Operator zatrzymuje wszystkie writery i tworzy kanoniczny backup z proofem.
3. Odtwarza backup do świeżych ścieżek i wykonuje migrację próbną wyłącznie na
   tej alternatywnej parze. Najpierw musi przejść `reject_newer_sqlite_schema`
   oraz DuckDB version check; wykrycie nowszej wersji kończy procedurę, nigdy nie
   uruchamia downgrade'u.
4. Porównuje wersje, uzgodnione liczniki i readback z punktem odniesienia. Dla
   semantic review sprawdza również raport `before`/`after` i status aktywacji.
5. Dopiero po akceptacji próby wykonuje ten sam zatwierdzony seam na aktywnej
   parze, z `approved_maintenance_window` oraz nowymi ścieżkami backupu.
6. Przed wznowieniem ruchu powtarza proof i minimalny readback. Jakakolwiek
   różnica poza zaakceptowanym kontraktem migracji zatrzymuje wznowienie.

### Weryfikacja

Artefakt zawiera operatora, zatwierdzone okno, fixed revision kodu, proof
źródła/backupów/próby, wersje schematów, wynik guarda i wynik readbacku. Dla
`semantic_review_activation.py` oczekuje się zgodnych istniejących liczników
`before` i `after`; nie jest to zgoda na uruchomienie semantic review modelu.

### Rollback

Operator nie obniża wersji i nie cofa DDL ręcznie. Zatrzymuje runtime, odtwarza
parę sprzed migracji wyłącznie do świeżych ścieżek, porównuje `storage_proof`, a
następnie przedstawia `OWNER` osobną decyzję o repoint/cutover. Jeśli post-check
zawiedzie po commicie migracji, stan pozostaje zatrzymany do czasu tego recovery.

## Zaplanowane i ręczne joby

Background scheduler jest opt-in przez `WILQ_ENABLE_SCHEDULER`; brak tej nazwy
oznacza stan wyłączony. Faktyczny stan procesu pokazuje pole `running` z
`GET /api/jobs/status`. Scheduler nie wykonuje backupów.

Zarejestrowane joby są read-only względem dostawców: interwałowy
`connector_status_probe_all` sprawdza lokalną gotowość bez vendor API, a
`configured_vendor_read_refresh` uruchamia się ręcznie i korzysta wyłącznie z
allowlisty skonfigurowanych adapterów odczytu. Manualne powierzchnie to
`GET /api/jobs`, `POST /api/jobs/{job_id}/run`, `GET /api/job-runs` i
`GET /api/job-runs/{run_id}`. Nie prowadzą do ActionObject write/apply.

**Operator:** `OWNER` zatwierdza włączenie schedulera; operator infrastruktury
zmienia gate i przeładowuje proces. Lokalny operator może uruchomić manualny
read-only job tylko w zatwierdzonym zakresie danych i kosztu API.

**Okno:** manualny read-only run nie wymaga owner-approved maintenance window,
o ile storage nie jest migrowany ani przywracany. Włączenie
`WILQ_ENABLE_SCHEDULER` jest osobną decyzją operacyjną `OWNER`; jeśli wymaga
restartu objętego planowanym przestojem, wykonuje się je w takim oknie.

### Kroki

1. Operator sprawdza definicję joba przez `GET /api/jobs/{job_id}`, w tym tryb,
   konektory, koszt i safety notes.
2. Dla ręcznego uruchomienia wywołuje wyłącznie endpoint konkretnego joba i nie
   łączy tego kroku z maintenance storage.
3. Dla schedulera `OWNER` zatwierdza gate, operator ustawia
   `WILQ_ENABLE_SCHEDULER` w prywatnej konfiguracji i przeładowuje API.
4. Operator sprawdza `running`, a następnie pojedynczy nowy `JobRun`; nie używa
   pola `autostart` jako dowodu działania gate'a.

### Weryfikacja

Dowód zawiera ID joba i job runu, status `completed`, `blocked` albo `failed`,
connector refresh run IDs, evidence IDs, zredagowane błędy oraz stan `running`.
Nie zawiera odpowiedzi vendorów ani poświadczeń. Job `status_probe` nie jest
dowodem świeżego vendor read.

### Rollback

Aby wyłączyć automatyczne uruchamianie, operator usuwa gate z prywatnej
konfiguracji, przeładowuje API i potwierdza `running` jako false. Nie usuwa
zapisanych JobRunów ani evidence. Nieudany manualny run nie jest ponawiany w
pętli: operator zachowuje zredagowany blocker i przekazuje decyzję `OWNER`.

## Warunek zakończenia maintenance

Operator wznawia normalny runtime dopiero po zgodnym proofie, readbacku i
decyzji `OWNER`. Do aktywnego Beada trafiają operator, czas, fixed revision,
bezpieczne ścieżki, wersje, liczniki, run/evidence IDs, wynik i blocker — nigdy
wartości poświadczeń. Sam runbook nie jest dowodem wykonania maintenance.
