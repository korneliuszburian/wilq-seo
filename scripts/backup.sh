#!/usr/bin/env bash
# Usage (from the repository root):
#   scripts/backup.sh
#   WILQ_BACKUP_DIR=/secure/backup/path scripts/backup.sh
#
# The default destination is .local-lab/backup/. Create and verify a backup
# before maintenance, then restore it to alternate paths during the maintenance
# window to prove that the stored state is recoverable without replacing live data.
set -euo pipefail
umask 077

state_source="${WILQ_STATE_DB:-.local-lab/state/wilq.sqlite3}"
metric_source="${WILQ_METRIC_DB:-.local-lab/state/wilq.duckdb}"
backup_dir="${WILQ_BACKUP_DIR:-.local-lab/backup}"

if [[ ! -f "$state_source" ]]; then
  printf '%s\n' 'Błąd: brak pliku źródłowego SQLite.' >&2
  exit 1
fi
if [[ ! -f "$metric_source" ]]; then
  printf '%s\n' 'Błąd: brak pliku źródłowego DuckDB.' >&2
  exit 1
fi

mkdir -p "$backup_dir"
chmod 700 "$backup_dir"

utc_timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
state_destination="${backup_dir}/wilq-${utc_timestamp}.sqlite3"
metric_destination="${backup_dir}/wilq-${utc_timestamp}.duckdb"

uv run python - \
  "$state_source" \
  "$metric_source" \
  "$state_destination" \
  "$metric_destination" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

from wilq.storage.recovery import copy_storage_pair, storage_proof


state_source = Path(sys.argv[1])
metric_source = Path(sys.argv[2])
state_destination = Path(sys.argv[3])
metric_destination = Path(sys.argv[4])


def remove_created_backup() -> None:
    state_destination.unlink(missing_ok=True)
    metric_destination.unlink(missing_ok=True)


backup_created = False
try:
    before = storage_proof(state_source, metric_source)
    copied = copy_storage_pair(
        sqlite_source=state_source,
        duckdb_source=metric_source,
        sqlite_destination=state_destination,
        duckdb_destination=metric_destination,
    )
    backup_created = True
    after = storage_proof(state_destination, metric_destination)
except Exception:
    if backup_created:
        remove_created_backup()
    print(
        "Błąd: nie udało się utworzyć i zweryfikować kopii WILQ. "
        "Sprawdź pliki źródłowe i użyj świeżej ścieżki docelowej.",
        file=sys.stderr,
    )
    raise SystemExit(1) from None

if copied != before or after != before:
    remove_created_backup()
    print(
        "Błąd: dowód kopii zapasowej różni się od stanu źródłowego.",
        file=sys.stderr,
    )
    raise SystemExit(1)

print("Kopia zapasowa WILQ została utworzona i zweryfikowana.")
print(f"SQLite: {state_destination}")
print(f"DuckDB: {metric_destination}")
print(f"Liczba rewizji: {after['revision_count']}")
print(f"Liczba zdarzeń audytowych: {after['audit_count']}")
print(f"Liczba faktów metrycznych: {after['metric_fact_count']}")
PY
