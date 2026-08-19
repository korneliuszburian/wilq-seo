from __future__ import annotations

import sqlite3
from pathlib import Path

from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


def test_existing_v4_store_gains_stop_telemetry_schema_without_changing_runs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "v4.sqlite3"
    legacy_payload = '{"id":"legacy_run","status":"started","opaque":"preserve"}'
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE codex_runs (
              id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO codex_runs VALUES (?, ?, ?)",
            ("legacy_run", "2026-08-14T12:00:00+00:00", legacy_payload),
        )
        connection.execute("PRAGMA user_version = 4")

    assert LocalStateStore(path).status()["schema_version"] == SQLITE_SCHEMA_VERSION

    with sqlite3.connect(path) as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(codex_stop_events)")
        ]
        legacy_row = connection.execute(
            "SELECT started_at, payload_json FROM codex_runs WHERE id = ?",
            ("legacy_run",),
        ).fetchone()
        telemetry_count = connection.execute(
            "SELECT COUNT(*) FROM codex_stop_events"
        ).fetchone()[0]

    assert schema_version == SQLITE_SCHEMA_VERSION
    assert columns == ["id", "received_at", "event_type", "contract_version"]
    assert legacy_row == ("2026-08-14T12:00:00+00:00", legacy_payload)
    assert telemetry_count == 0


def test_unrelated_store_cannot_claim_v5_before_stop_telemetry_table_exists(
    tmp_path: Path,
) -> None:
    path = tmp_path / "shared-v4.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 4")

    assert ContentWorkflowStore(path).list_draft_revisions("work_1") == []
    with sqlite3.connect(path) as connection:
        version_before_stop_migration = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
        stop_table_before_migration = connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name = 'codex_stop_events'
            """
        ).fetchone()[0]

    assert version_before_stop_migration == 4
    assert stop_table_before_migration == 0

    assert LocalStateStore(path).get_content_section_focus("work_1") is None
    with sqlite3.connect(path) as connection:
        assert (
            connection.execute("PRAGMA user_version").fetchone()[0]
            == SQLITE_SCHEMA_VERSION
        )
        assert connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name = 'codex_stop_events'
            """
        ).fetchone()[0] == 1
