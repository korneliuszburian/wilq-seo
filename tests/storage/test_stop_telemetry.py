from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from wilq.codex.stop_telemetry import (
    StopTelemetryEvent,
    StopTelemetryHighWatermarkError,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION


def _seed_stop_events(path: Path, events: list[StopTelemetryEvent]) -> None:
    with sqlite3.connect(path) as connection:
        connection.executemany(
            """
            INSERT INTO codex_stop_events (
              id, received_at, event_type, contract_version
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    event.event_id,
                    event.received_at.isoformat(),
                    event.event_type,
                    event.contract_version,
                )
                for event in events
            ],
        )


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
        index_columns = [
            row[2]
            for row in connection.execute(
                "PRAGMA index_info(idx_codex_stop_events_received_at_id)"
            )
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
    assert index_columns == ["received_at", "id"]
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


def test_unrelated_store_cannot_claim_v6_before_stop_telemetry_index_exists(
    tmp_path: Path,
) -> None:
    path = tmp_path / "shared-v5.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE codex_stop_events (
              id TEXT PRIMARY KEY,
              received_at TEXT NOT NULL,
              event_type TEXT NOT NULL CHECK (event_type = 'stop'),
              contract_version INTEGER NOT NULL CHECK (contract_version >= 1)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO codex_stop_events (
              id, received_at, event_type, contract_version
            )
            VALUES ('existing_stop', '2026-08-18T12:00:00+00:00', 'stop', 1)
            """
        )
        connection.execute("PRAGMA user_version = 5")

    assert ContentWorkflowStore(path).list_draft_revisions("work_1") == []
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'index'
              AND name = 'idx_codex_stop_events_received_at_id'
            """
        ).fetchone()[0] == 0

    assert LocalStateStore(path).get_content_section_focus("work_1") is None
    with sqlite3.connect(path) as connection:
        assert (
            connection.execute("PRAGMA user_version").fetchone()[0]
            == SQLITE_SCHEMA_VERSION
        )
        index_columns = [
            row[2]
            for row in connection.execute(
                "PRAGMA index_info(idx_codex_stop_events_received_at_id)"
            )
        ]
        existing_stop = connection.execute(
            """
            SELECT id, received_at, event_type, contract_version
            FROM codex_stop_events
            """
        ).fetchone()

    assert index_columns == ["received_at", "id"]
    assert existing_stop == (
        "existing_stop",
        "2026-08-18T12:00:00+00:00",
        "stop",
        1,
    )


def test_stop_intake_purges_old_events_in_bounded_idempotent_batches(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bounded-stop-telemetry.sqlite3"
    store = LocalStateStore(path)
    assert store.status()["schema_version"] == SQLITE_SCHEMA_VERSION
    cutoff = datetime(2026, 8, 19, 12, tzinfo=UTC)
    _seed_stop_events(
        path,
        [
            StopTelemetryEvent(
                event_id="oldest",
                received_at=cutoff - timedelta(days=2),
            ),
            StopTelemetryEvent(
                event_id="old",
                received_at=cutoff - timedelta(seconds=1),
            ),
            StopTelemetryEvent(event_id="at_cutoff", received_at=cutoff),
            StopTelemetryEvent(
                event_id="young",
                received_at=cutoff + timedelta(seconds=1),
            ),
        ],
    )

    first = store.intake_stop_telemetry_event(
        StopTelemetryEvent(
            event_id="accepted_1",
            received_at=cutoff + timedelta(minutes=1),
        ),
        cutoff=cutoff,
        purge_batch_size=1,
        high_watermark=10,
    )
    second = store.intake_stop_telemetry_event(
        StopTelemetryEvent(
            event_id="accepted_2",
            received_at=cutoff + timedelta(minutes=2),
        ),
        cutoff=cutoff,
        purge_batch_size=1,
        high_watermark=10,
    )
    third = store.intake_stop_telemetry_event(
        StopTelemetryEvent(
            event_id="accepted_3",
            received_at=cutoff + timedelta(minutes=3),
        ),
        cutoff=cutoff,
        purge_batch_size=1,
        high_watermark=10,
    )

    assert first.model_dump() == {
        "status": "accepted",
        "cutoff": cutoff,
        "purged_count": 1,
        "count": 4,
    }
    assert second.model_dump() == {
        "status": "accepted",
        "cutoff": cutoff,
        "purged_count": 1,
        "count": 4,
    }
    assert third.model_dump() == {
        "status": "accepted",
        "cutoff": cutoff,
        "purged_count": 0,
        "count": 5,
    }
    with sqlite3.connect(path) as connection:
        ids = {
            row[0]
            for row in connection.execute(
                "SELECT id FROM codex_stop_events ORDER BY received_at, id"
            )
        }

    assert ids == {"at_cutoff", "young", "accepted_1", "accepted_2", "accepted_3"}


def test_stop_intake_commits_bounded_purge_but_refuses_append_at_high_watermark(
    tmp_path: Path,
) -> None:
    path = tmp_path / "full-stop-telemetry.sqlite3"
    store = LocalStateStore(path)
    assert store.status()["schema_version"] == SQLITE_SCHEMA_VERSION
    cutoff = datetime(2026, 8, 19, 12, tzinfo=UTC)
    _seed_stop_events(
        path,
        [
            StopTelemetryEvent(
                event_id="stale",
                received_at=cutoff - timedelta(seconds=1),
            ),
            StopTelemetryEvent(event_id="current", received_at=cutoff),
        ],
    )

    with pytest.raises(StopTelemetryHighWatermarkError) as raised:
        store.intake_stop_telemetry_event(
            StopTelemetryEvent(
                event_id="must_not_append",
                received_at=cutoff + timedelta(minutes=1),
            ),
            cutoff=cutoff,
            purge_batch_size=1,
            high_watermark=1,
        )

    assert raised.value.receipt.model_dump() == {
        "status": "high_watermark",
        "cutoff": cutoff,
        "purged_count": 1,
        "count": 1,
    }
    with sqlite3.connect(path) as connection:
        ids = [row[0] for row in connection.execute("SELECT id FROM codex_stop_events")]

    assert ids == ["current"]
