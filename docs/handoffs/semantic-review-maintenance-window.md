# Semantic review storage — maintenance handoff

Status: przygotowane, **nieuruchomione**. Wymaga jawnej zgody na maintenance
window i operatora posiadającego dostęp do lokalnego storage. Normalny API GET,
POST planowania ani dashboard nie mogą wykonywać tej migracji.

2026-07-21 isolated restore drill: PASS on the alternate copy only. Restoring
the pre-activation SQLite/DuckDB backup to new paths preserved schema versions
3/1, 12 revisions, 979 audits and 168707 metric facts; both destination files
were mode `0600`. The restored pre-activation pair correctly has no
`content_semantic_reviews` table. Proof:
`.local-lab/proof/semantic-review/2026-07-21/restore-drill-2026-07-21.json`.
This is recovery proof, not authorization or activation of the main state.

## Cel

Aktywować tabelę `content_semantic_reviews` dla trwałego advisory review
związanego z exact `revision_digest`, `criteria_version` i `codex_run_id`.
Migracja nie zatwierdza treści, nie tworzy ActionObjectu i nie wykonuje zapisu
do WordPress.

## Przed oknem

- [ ] potwierdzić właściciela i czas maintenance window;
- [ ] zatrzymać procesy zapisujące local state albo zapewnić wyłączność SQLite;
- [ ] sprawdzić, że ścieżki SQLite/DuckDB wskazują lokalny stan WILQ, bez
  wpisywania credentiali do terminala, logu ani dokumentu;
- [ ] wybrać nowe, nieistniejące ścieżki backupu poza repozytorium;
- [ ] zachować wynik `storage_proof` jako punkt odniesienia.

## Jedyna komenda aktywacji

Uruchomić z repozytorium przez `uv run` i podać jawny przełącznik zgody:

```bash
uv run wilq storage activate-semantic-review \
  --sqlite-source /ABS/LOCAL/state.sqlite3 \
  --duckdb-source /ABS/LOCAL/metrics.duckdb \
  --sqlite-backup /ABS/BACKUP/state-before-semantic-review.sqlite3 \
  --duckdb-backup /ABS/BACKUP/metrics-before-semantic-review.duckdb \
  --approved-maintenance-window
```

Komenda najpierw kopiuje oba magazyny, porównuje ich proof, a dopiero potem
wykonuje transakcyjne `BEGIN IMMEDIATE` i sprawdza wersję schematu. Nie wolno
tworzyć tabeli ręcznie ani przez endpoint GET.

## Oczekiwany proof

Zachować wynik JSON komendy. `status` powinien być `activated` (albo
`already_active` przy bezpiecznym ponowieniu), a `before` i `after` muszą mieć
identyczne liczniki istniejących rewizji, audytów i faktów metrycznych.

Po migracji wykonać wyłącznie lokalny readback:

1. GET semantic review dla nieistniejącej rewizji — powinien zwrócić typed
   `not_generated`, bez wywołania modelu;
2. test store/readback na kopii lub zaakceptowanym stanie testowym;
3. sprawdzenie, że `content_semantic_reviews` istnieje i wersja SQLite nie jest
   nowsza od klienta;
4. porównanie liczników z proofem `before`.

## Restore drill

Jeśli proof liczników się różni, migracja kończy się niepowodzeniem i nie należy
kontynuować review. Przywrócić do **nowych alternatywnych ścieżek**, nie nadpisywać
źródła w ciemno:

```bash
uv run wilq storage restore \
  --sqlite-backup /ABS/BACKUP/state-before-semantic-review.sqlite3 \
  --duckdb-backup /ABS/BACKUP/metrics-before-semantic-review.duckdb \
  --sqlite-destination /ABS/RESTORE/state-restored.sqlite3 \
  --duckdb-destination /ABS/RESTORE/metrics-restored.duckdb
```

Następnie porównać proof przywróconej pary z `before`, opisać wynik w Beadzie i
dopiero wtedy zdecydować o dalszym oknie. Nie przedstawiać lokalnego dry-runu
ani syntetycznego review jako realnego UAT.

## Po oknie

- [ ] zapisać JSON proof, backup paths, operatora i czas w Beadzie;
- [ ] sprawdzić API GET semantic review bez model call;
- [ ] dopiero po osobnym owner-review uruchomić semantic review exact revision;
- [ ] zachować `unreviewed` i `publish_ready=false`; WordPress pozostaje
  draft-only.
