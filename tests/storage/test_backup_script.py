from __future__ import annotations

import os
import re
import sqlite3
import subprocess
from pathlib import Path

import duckdb
import pytest

from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store
from wilq.storage.recovery import copy_storage_pair, storage_proof
from wilq.storage.schema_versions import DUCKDB_SCHEMA_VERSION, SQLITE_SCHEMA_VERSION

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKUP_SCRIPT = REPOSITORY_ROOT / "scripts" / "backup.sh"


def _create_source_stores(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    state_path = tmp_path / "source" / "wilq.sqlite3"
    metric_path = tmp_path / "source" / "wilq.duckdb"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    monkeypatch.setenv("WILQ_METRIC_DB", str(metric_path))

    local_state_store().status()
    ContentWorkflowStore(state_path).list_draft_revisions("missing")
    metric_store().status()

    with sqlite3.connect(state_path) as connection:
        connection.execute(
            """
            INSERT INTO content_draft_revisions (
              revision_id, work_item_id, revision_number, base_revision_id,
              content_digest, created_at, payload_json
            ) VALUES ('revision_1', 'work_1', 1, NULL, 'digest', '2026-08-15', '{}')
            """
        )
        connection.execute(
            """
            INSERT INTO audit_events (id, action_id, created_at, payload_json)
            VALUES ('audit_1', 'action_1', '2026-08-15', '{}')
            """
        )
    with duckdb.connect(str(metric_path)) as connection:
        connection.execute(
            """
            INSERT INTO connector_metric_facts VALUES (
              'run_1', 'google_search_console', 'clicks', 3, NULL, 'number',
              '2026-08-01/2026-08-14', 'clicks', '{}', 'vendor_read', 'completed',
              TIMESTAMP '2026-08-15 00:00:00', 1, 'ev_run_1'
            )
            """
        )
    return state_path, metric_path


def _run_backup(
    *,
    state_path: Path,
    metric_path: Path,
    backup_dir: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "WILQ_STATE_DB": str(state_path),
            "WILQ_METRIC_DB": str(metric_path),
            "WILQ_BACKUP_DIR": str(backup_dir),
        }
    )
    return subprocess.run(
        ["bash", str(BACKUP_SCRIPT)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_backup_script_round_trip_preserves_storage_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path, metric_path = _create_source_stores(monkeypatch, tmp_path)
    backup_dir = tmp_path / "backup"

    result = _run_backup(
        state_path=state_path,
        metric_path=metric_path,
        backup_dir=backup_dir,
    )

    assert result.returncode == 0, result.stderr
    backup_states = list(backup_dir.glob("wilq-*.sqlite3"))
    backup_metrics = list(backup_dir.glob("wilq-*.duckdb"))
    assert len(backup_states) == 1
    assert len(backup_metrics) == 1
    backup_state = backup_states[0]
    backup_metric = backup_metrics[0]
    state_name = re.fullmatch(r"wilq-(\d{8}T\d{6}Z)\.sqlite3", backup_state.name)
    metric_name = re.fullmatch(r"wilq-(\d{8}T\d{6}Z)\.duckdb", backup_metric.name)
    assert state_name is not None
    assert metric_name is not None
    assert state_name.group(1) == metric_name.group(1)

    restored_state = tmp_path / "restored" / "wilq.sqlite3"
    restored_metric = tmp_path / "restored" / "wilq.duckdb"
    restored_copy_proof = copy_storage_pair(
        sqlite_source=backup_state,
        duckdb_source=backup_metric,
        sqlite_destination=restored_state,
        duckdb_destination=restored_metric,
    )
    expected = {
        "sqlite_schema_version": SQLITE_SCHEMA_VERSION,
        "duckdb_schema_version": DUCKDB_SCHEMA_VERSION,
        "revision_count": 1,
        "audit_count": 1,
        "metric_fact_count": 1,
    }
    assert [
        storage_proof(state_path, metric_path),
        storage_proof(backup_state, backup_metric),
        restored_copy_proof,
        storage_proof(restored_state, restored_metric),
    ] == [expected, expected, expected, expected]
    assert backup_dir.stat().st_mode & 0o777 == 0o700
    assert backup_state.stat().st_mode & 0o777 == 0o600
    assert backup_metric.stat().st_mode & 0o777 == 0o600
    assert str(backup_state) in result.stdout
    assert str(backup_metric) in result.stdout
    assert "Liczba rewizji: 1" in result.stdout
    assert "Liczba zdarzeń audytowych: 1" in result.stdout
    assert "Liczba faktów metrycznych: 1" in result.stdout


def test_backup_script_rejects_a_missing_source_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path, metric_path = _create_source_stores(monkeypatch, tmp_path)
    state_path.unlink()
    backup_dir = tmp_path / "backup"

    result = _run_backup(
        state_path=state_path,
        metric_path=metric_path,
        backup_dir=backup_dir,
    )

    assert result.returncode != 0
    assert result.stderr == "Błąd: brak pliku źródłowego SQLite.\n"
    assert not list(backup_dir.glob("wilq-*"))


def test_backup_script_reports_an_unreadable_source_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path, metric_path = _create_source_stores(monkeypatch, tmp_path)
    metric_path.write_bytes(b"not a DuckDB store")
    backup_dir = tmp_path / "backup"

    result = _run_backup(
        state_path=state_path,
        metric_path=metric_path,
        backup_dir=backup_dir,
    )

    assert result.returncode != 0
    assert result.stderr == (
        "Błąd: nie udało się utworzyć i zweryfikować kopii WILQ. "
        "Sprawdź pliki źródłowe i użyj świeżej ścieżki docelowej.\n"
    )
    assert not list(backup_dir.glob("wilq-*"))
