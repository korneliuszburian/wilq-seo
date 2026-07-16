from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import duckdb
import pytest
from typer.testing import CliRunner

from wilq.cli import app as cli_app
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore
from wilq.storage.metric_store import DuckDbMetricStore
from wilq.storage.recovery import (
    copy_duckdb_store,
    copy_sqlite_store,
    copy_storage_pair,
    storage_proof,
)
from wilq.storage.schema_versions import DUCKDB_SCHEMA_VERSION, SQLITE_SCHEMA_VERSION


def test_storage_backup_and_restore_preserve_versions_and_pilot_counts(tmp_path: Path) -> None:
    state_path = tmp_path / "source" / "wilq.sqlite3"
    metric_path = tmp_path / "source" / "wilq.duckdb"
    LocalStateStore(state_path).status()
    ContentWorkflowStore(state_path).list_draft_revisions("missing")
    DuckDbMetricStore(metric_path).status()

    with sqlite3.connect(state_path) as connection:
        connection.execute(
            """
            INSERT INTO content_draft_revisions (
              revision_id, work_item_id, revision_number, base_revision_id,
              content_digest, created_at, payload_json
            ) VALUES ('revision_1', 'work_1', 1, NULL, 'digest', '2026-07-16', '{}')
            """
        )
        connection.execute(
            """
            INSERT INTO content_workflow_audits (audit_id, human_review_id, payload_json)
            VALUES ('content_audit_1', 'review_1', '{}')
            """
        )
        connection.execute(
            """
            INSERT INTO action_mutation_audits (
              id, action_id, status, created_at, payload_json
            ) VALUES ('mutation_audit_1', 'action_1', 'blocked', '2026-07-16', '{}')
            """
        )
        connection.execute(
            """
            INSERT INTO audit_events (id, action_id, created_at, payload_json)
            VALUES ('audit_1', 'action_1', '2026-07-16', '{}')
            """
        )
    with duckdb.connect(str(metric_path)) as connection:
        connection.execute(
            """
            INSERT INTO connector_metric_facts VALUES (
              'run_1', 'google_search_console', 'clicks', 3, NULL, 'number',
              '2026-07-01/2026-07-15', 'clicks', '{}', 'vendor_read', 'completed',
              TIMESTAMP '2026-07-16 00:00:00', 'ev_run_1'
            )
            """
        )

    expected = storage_proof(state_path, metric_path)
    assert expected == {
        "sqlite_schema_version": SQLITE_SCHEMA_VERSION,
        "duckdb_schema_version": DUCKDB_SCHEMA_VERSION,
        "revision_count": 1,
        "audit_count": 3,
        "metric_fact_count": 1,
    }

    backup_state = tmp_path / "backup" / "wilq.sqlite3"
    backup_metrics = tmp_path / "backup" / "wilq.duckdb"
    backup_result = CliRunner().invoke(
        cli_app,
        [
            "storage",
            "backup",
            "--sqlite-source",
            str(state_path),
            "--duckdb-source",
            str(metric_path),
            "--sqlite-destination",
            str(backup_state),
            "--duckdb-destination",
            str(backup_metrics),
        ],
    )
    assert backup_result.exit_code == 0, backup_result.output
    assert json.loads(backup_result.output)["proof"] == expected
    restored_state = tmp_path / "restored" / "wilq.sqlite3"
    restored_metrics = tmp_path / "restored" / "wilq.duckdb"
    restore_result = CliRunner().invoke(
        cli_app,
        [
            "storage",
            "restore",
            "--sqlite-backup",
            str(backup_state),
            "--duckdb-backup",
            str(backup_metrics),
            "--sqlite-destination",
            str(restored_state),
            "--duckdb-destination",
            str(restored_metrics),
        ],
    )
    assert restore_result.exit_code == 0, restore_result.output
    assert json.loads(restore_result.output)["proof"] == expected

    assert storage_proof(restored_state, restored_metrics) == expected
    assert restored_state.stat().st_mode & 0o777 == 0o600
    assert restored_metrics.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        copy_sqlite_store(state_path, restored_state)
    with pytest.raises(ValueError, match="must differ"):
        copy_duckdb_store(metric_path, metric_path)

    invalid_duckdb = tmp_path / "invalid.duckdb"
    invalid_duckdb.write_text("not a DuckDB database", encoding="utf-8")
    partial_state = tmp_path / "partial" / "wilq.sqlite3"
    partial_metrics = tmp_path / "partial" / "wilq.duckdb"
    with pytest.raises(duckdb.Error):
        copy_storage_pair(
            sqlite_source=state_path,
            duckdb_source=invalid_duckdb,
            sqlite_destination=partial_state,
            duckdb_destination=partial_metrics,
        )
    assert not partial_state.exists()
    assert not partial_metrics.exists()


def test_interrupted_duckdb_migration_keeps_legacy_table_readable(tmp_path: Path) -> None:
    metric_path = tmp_path / "legacy.duckdb"
    with duckdb.connect(str(metric_path)) as connection:
        connection.execute(
            """
            CREATE TABLE connector_metric_facts (
              run_id VARCHAR NOT NULL,
              connector_id VARCHAR NOT NULL,
              metric_name VARCHAR NOT NULL,
              metric_value_double DOUBLE,
              metric_value_text VARCHAR,
              value_kind VARCHAR NOT NULL,
              mode VARCHAR NOT NULL,
              status VARCHAR NOT NULL,
              collected_at TIMESTAMP NOT NULL,
              evidence_id VARCHAR NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO connector_metric_facts VALUES
              ('run_1', 'gsc', 'clicks', 1, NULL, 'number', 'vendor_read',
               'completed', TIMESTAMP '2026-07-16 00:00:00', 'ev_1'),
              ('run_1', 'gsc', 'clicks', 2, NULL, 'number', 'vendor_read',
               'completed', TIMESTAMP '2026-07-16 00:01:00', 'ev_2')
            """
        )

    with pytest.raises(duckdb.ConstraintException):
        DuckDbMetricStore(metric_path).status()

    with duckdb.connect(str(metric_path), read_only=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM connector_metric_facts").fetchone()[0] == 2
        tables = {
            row[0]
            for row in connection.execute("SHOW TABLES").fetchall()
        }
    assert "connector_metric_facts_v2" not in tables
    assert "wilq_schema_metadata" not in tables


def test_newer_store_versions_are_rejected_before_schema_changes(tmp_path: Path) -> None:
    state_path = tmp_path / "future.sqlite3"
    with sqlite3.connect(state_path) as connection:
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION + 1}")

    with pytest.raises(RuntimeError, match="newer than supported"):
        LocalStateStore(state_path).status()
    with sqlite3.connect(state_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0] == 0

    metric_path = tmp_path / "future.duckdb"
    with duckdb.connect(str(metric_path)) as connection:
        connection.execute(
            """
            CREATE TABLE wilq_schema_metadata (
              store_key VARCHAR PRIMARY KEY,
              version INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO wilq_schema_metadata VALUES ('metric_store', ?)",
            [DUCKDB_SCHEMA_VERSION + 1],
        )

    with pytest.raises(RuntimeError, match="newer than supported"):
        DuckDbMetricStore(metric_path).status()
    with duckdb.connect(str(metric_path), read_only=True) as connection:
        assert connection.execute("SHOW TABLES").fetchall() == [("wilq_schema_metadata",)]
