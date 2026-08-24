from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.codex.stop_telemetry import (
    DEFAULT_STOP_TELEMETRY_HIGH_WATERMARK,
    DEFAULT_STOP_TELEMETRY_PURGE_BATCH_SIZE,
    DEFAULT_STOP_TELEMETRY_RETENTION_DAYS,
    stop_telemetry_policy,
)
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore
from wilq.storage.schema_versions import SQLITE_SCHEMA_VERSION

client = TestClient(app)

STOP_TELEMETRY_ENV_NAMES = (
    "WILQ_STOP_TELEMETRY_RETENTION_DAYS",
    "WILQ_STOP_TELEMETRY_PURGE_BATCH_SIZE",
    "WILQ_STOP_TELEMETRY_HIGH_WATERMARK",
)


def _clear_stop_telemetry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in STOP_TELEMETRY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_stop_telemetry_policy_has_bounded_defaults_and_dedicated_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_stop_telemetry_env(monkeypatch)

    assert stop_telemetry_policy().model_dump() == {
        "retention_days": DEFAULT_STOP_TELEMETRY_RETENTION_DAYS,
        "purge_batch_size": DEFAULT_STOP_TELEMETRY_PURGE_BATCH_SIZE,
        "high_watermark": DEFAULT_STOP_TELEMETRY_HIGH_WATERMARK,
    }

    monkeypatch.setenv("WILQ_STOP_TELEMETRY_RETENTION_DAYS", "7")
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_PURGE_BATCH_SIZE", "2")
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_HIGH_WATERMARK", "10")

    assert stop_telemetry_policy().model_dump() == {
        "retention_days": 7,
        "purge_batch_size": 2,
        "high_watermark": 10,
    }


def test_stop_intake_owns_identity_and_persists_only_the_minimal_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "codex_state.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    _clear_stop_telemetry_env(monkeypatch)
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_RETENTION_DAYS", "7")
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_PURGE_BATCH_SIZE", "2")
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_HIGH_WATERMARK", "10")
    assert LocalStateStore(state_path).status()["schema_version"] == SQLITE_SCHEMA_VERSION
    with sqlite3.connect(state_path) as connection:
        connection.executemany(
            """
            INSERT INTO codex_stop_events (
              id, received_at, event_type, contract_version
            )
            VALUES (?, ?, 'stop', 1)
            """,
            [
                ("stale_1", "2000-01-01T00:00:00+00:00"),
                ("stale_2", "2000-01-02T00:00:00+00:00"),
                ("stale_3", "2000-01-03T00:00:00+00:00"),
                ("recent", "2100-01-01T00:00:00+00:00"),
            ],
        )

    before_intake = datetime.now(UTC)
    response = client.post(
        "/api/codex/telemetry/stop-events",
        json={
            "event_id": "caller_owned_event",
            "received_at": "2000-01-01T00:00:00Z",
            "event_type": "not_stop",
            "contract_version": 999,
            "run_id": "caller_owned_run",
            "status": "completed",
            "prompt": "must not be persisted",
        },
    )
    after_intake = datetime.now(UTC)

    assert response.status_code == 201
    receipt = response.json()
    assert set(receipt) == {
        "event_id",
        "received_at",
        "event_type",
        "contract_version",
        "lifecycle",
    }
    assert receipt["event_id"] != "caller_owned_event"
    assert receipt["event_type"] == "stop"
    assert receipt["contract_version"] == 1
    lifecycle = receipt["lifecycle"]
    assert lifecycle["status"] == "accepted"
    assert lifecycle["purged_count"] == 2
    assert lifecycle["count"] == 3
    cutoff = datetime.fromisoformat(lifecycle["cutoff"])
    assert before_intake - timedelta(days=7) <= cutoff <= after_intake - timedelta(
        days=7
    )

    with sqlite3.connect(state_path) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(codex_stop_events)")
        ]
        rows = connection.execute(
            """
            SELECT id, received_at, event_type, contract_version
            FROM codex_stop_events ORDER BY received_at, id
            """
        ).fetchall()
        codex_run_count = connection.execute(
            "SELECT COUNT(*) FROM codex_runs"
        ).fetchone()[0]

    assert columns == ["id", "received_at", "event_type", "contract_version"]
    generated_rows = [row for row in rows if row[0] not in {"stale_3", "recent"}]
    assert len(generated_rows) == 1
    generated = generated_rows[0]
    assert {row[0] for row in rows} == {"stale_3", "recent", generated[0]}
    assert generated[0] != "caller_owned_event"
    assert generated[0].startswith("codex_stop_event_")
    received_at = datetime.fromisoformat(generated[1])
    assert generated[0] == receipt["event_id"]
    assert received_at == datetime.fromisoformat(receipt["received_at"])
    assert before_intake <= received_at <= after_intake
    assert received_at != datetime(2000, 1, 1, tzinfo=UTC)
    assert generated[2:] == ("stop", 1)
    assert codex_run_count == 0


def test_stop_telemetry_health_is_read_only_and_never_purges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "stop_health.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    _clear_stop_telemetry_env(monkeypatch)
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_RETENTION_DAYS", "7")
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_HIGH_WATERMARK", "10")
    assert LocalStateStore(state_path).status()["schema_version"] == SQLITE_SCHEMA_VERSION
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            """
            INSERT INTO codex_stop_events (
              id, received_at, event_type, contract_version
            )
            VALUES ('stale_but_read_only', '2000-01-01T00:00:00+00:00', 'stop', 1)
            """
        )
    bytes_before_health = state_path.read_bytes()

    before_health = datetime.now(UTC)
    response = client.get("/api/codex/telemetry/health")
    after_health = datetime.now(UTC)

    assert response.status_code == 200
    receipt = response.json()
    assert set(receipt) == {"status", "cutoff", "purged_count", "count"}
    assert receipt["status"] == "healthy"
    assert receipt["purged_count"] == 0
    assert receipt["count"] == 1
    cutoff = datetime.fromisoformat(receipt["cutoff"])
    assert before_health - timedelta(days=7) <= cutoff <= after_health - timedelta(
        days=7
    )
    assert state_path.read_bytes() == bytes_before_health
    with sqlite3.connect(state_path) as connection:
        ids = [row[0] for row in connection.execute("SELECT id FROM codex_stop_events")]

    assert ids == ["stale_but_read_only"]


def test_stop_telemetry_high_watermark_returns_typed_503_without_mutating_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "stop_high_watermark.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    _clear_stop_telemetry_env(monkeypatch)
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_PURGE_BATCH_SIZE", "1")
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_HIGH_WATERMARK", "1")
    store = LocalStateStore(state_path)
    original_run = store.save_codex_run(
        CodexRun(id="run_must_remain_started", status="started")
    )
    with sqlite3.connect(state_path) as connection:
        connection.executemany(
            """
            INSERT INTO codex_stop_events (
              id, received_at, event_type, contract_version
            )
            VALUES (?, ?, 'stop', 1)
            """,
            [
                ("stale", "2000-01-01T00:00:00+00:00"),
                ("current", "2100-01-01T00:00:00+00:00"),
            ],
        )

    before_intake = datetime.now(UTC)
    intake_response = client.post("/api/codex/telemetry/stop-events")
    after_intake = datetime.now(UTC)

    assert intake_response.status_code == 503
    intake_error = intake_response.json()
    assert set(intake_error) == {"type", "code", "lifecycle"}
    assert intake_error["type"] == "stop_telemetry_unavailable"
    assert intake_error["code"] == "stop_telemetry_high_watermark"
    intake_lifecycle = intake_error["lifecycle"]
    assert intake_lifecycle["status"] == "high_watermark"
    assert intake_lifecycle["purged_count"] == 1
    assert intake_lifecycle["count"] == 1
    cutoff = datetime.fromisoformat(intake_lifecycle["cutoff"])
    assert before_intake - timedelta(days=30) <= cutoff <= after_intake - timedelta(
        days=30
    )
    assert store.list_codex_runs() == [original_run]
    with sqlite3.connect(state_path) as connection:
        ids_after_intake = [
            row[0] for row in connection.execute("SELECT id FROM codex_stop_events")
        ]
    assert ids_after_intake == ["current"]

    health_response = client.get("/api/codex/telemetry/health")

    assert health_response.status_code == 503
    health_error = health_response.json()
    assert health_error["type"] == "stop_telemetry_unavailable"
    assert health_error["code"] == "stop_telemetry_high_watermark"
    assert health_error["lifecycle"]["status"] == "high_watermark"
    assert health_error["lifecycle"]["purged_count"] == 0
    assert health_error["lifecycle"]["count"] == 1
    assert store.list_codex_runs() == [original_run]


def test_stop_telemetry_storage_failure_returns_typed_503_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "stop_storage_failure.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    _clear_stop_telemetry_env(monkeypatch)
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_PURGE_BATCH_SIZE", "1")
    monkeypatch.setenv("WILQ_STOP_TELEMETRY_HIGH_WATERMARK", "10")
    store = LocalStateStore(state_path)
    original_run = store.save_codex_run(
        CodexRun(id="run_survives_telemetry_failure", status="started")
    )
    with sqlite3.connect(state_path) as connection:
        connection.execute(
            """
            INSERT INTO codex_stop_events (
              id, received_at, event_type, contract_version
            )
            VALUES ('stale_survives_rollback', '2000-01-01T00:00:00+00:00', 'stop', 1)
            """
        )
        connection.execute(
            """
            CREATE TRIGGER reject_generated_stop_event
            BEFORE INSERT ON codex_stop_events
            WHEN NEW.id LIKE 'codex_stop_event_%'
            BEGIN
              SELECT RAISE(FAIL, 'forced stop telemetry failure');
            END
            """
        )

    before_intake = datetime.now(UTC)
    response = client.post("/api/codex/telemetry/stop-events")
    after_intake = datetime.now(UTC)

    assert response.status_code == 503
    error = response.json()
    assert set(error) == {"type", "code", "lifecycle"}
    assert error["type"] == "stop_telemetry_unavailable"
    assert error["code"] == "stop_telemetry_storage_unavailable"
    assert error["lifecycle"]["status"] == "unavailable"
    assert error["lifecycle"]["purged_count"] == 0
    assert error["lifecycle"]["count"] is None
    cutoff = datetime.fromisoformat(error["lifecycle"]["cutoff"])
    assert before_intake - timedelta(days=30) <= cutoff <= after_intake - timedelta(
        days=30
    )
    assert "forced" not in response.text
    assert store.list_codex_runs() == [original_run]
    with sqlite3.connect(state_path) as connection:
        ids = [row[0] for row in connection.execute("SELECT id FROM codex_stop_events")]

    assert ids == ["stale_survives_rollback"]


def test_stop_telemetry_health_storage_failure_is_sanitized_and_read_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "stop_health_storage_failure.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    _clear_stop_telemetry_env(monkeypatch)
    started_at = "2026-08-19T12:00:00+00:00"
    opaque_payload = (
        '{"id":"run_survives_health_failure","status":"started",'
        '"opaque":"preserve_exactly"}'
    )
    with sqlite3.connect(state_path) as connection:
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
            ("run_survives_health_failure", started_at, opaque_payload),
        )
        connection.execute("PRAGMA user_version = 4")
    bytes_before_health = state_path.read_bytes()

    before_health = datetime.now(UTC)
    response = client.get("/api/codex/telemetry/health")
    after_health = datetime.now(UTC)

    assert response.status_code == 503
    error = response.json()
    assert set(error) == {"type", "code", "lifecycle"}
    assert error["type"] == "stop_telemetry_unavailable"
    assert error["code"] == "stop_telemetry_storage_unavailable"
    lifecycle = error["lifecycle"]
    assert set(lifecycle) == {"status", "cutoff", "purged_count", "count"}
    assert lifecycle["status"] == "unavailable"
    assert lifecycle["purged_count"] == 0
    assert lifecycle["count"] is None
    cutoff = datetime.fromisoformat(lifecycle["cutoff"])
    assert before_health - timedelta(days=30) <= cutoff <= after_health - timedelta(
        days=30
    )
    for forbidden_detail in (
        "no such table",
        "codex_stop_events",
        "SELECT",
        str(state_path),
    ):
        assert forbidden_detail not in response.text
    assert state_path.read_bytes() == bytes_before_health

    with sqlite3.connect(state_path) as connection:
        preserved_run = connection.execute(
            "SELECT started_at, payload_json FROM codex_runs WHERE id = ?",
            ("run_survives_health_failure",),
        ).fetchone()
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        stop_table_count = connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name = 'codex_stop_events'
            """
        ).fetchone()[0]

    assert preserved_run == (started_at, opaque_payload)
    assert schema_version == 4
    assert stop_table_count == 0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("WILQ_STOP_TELEMETRY_RETENTION_DAYS", "0"),
        ("WILQ_STOP_TELEMETRY_RETENTION_DAYS", str(10**100)),
        ("WILQ_STOP_TELEMETRY_PURGE_BATCH_SIZE", str(10**100)),
    ],
)
def test_stop_telemetry_invalid_policy_fails_closed_without_opening_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    value: str,
) -> None:
    state_path = tmp_path / "invalid_stop_policy.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    _clear_stop_telemetry_env(monkeypatch)
    monkeypatch.setenv(name, value)

    response = client.post("/api/codex/telemetry/stop-events")

    assert response.status_code == 503
    assert response.json() == {
        "type": "stop_telemetry_unavailable",
        "code": "stop_telemetry_configuration_invalid",
        "lifecycle": {
            "status": "unavailable",
            "cutoff": None,
            "purged_count": 0,
            "count": None,
        },
    }
    assert state_path.exists() is False


def test_stop_telemetry_routes_publish_the_typed_503_contract() -> None:
    schema = app.openapi()

    for path, method in (
        ("/api/codex/telemetry/stop-events", "post"),
        ("/api/codex/telemetry/health", "get"),
    ):
        response_schema = schema["paths"][path][method]["responses"]["503"][
            "content"
        ]["application/json"]["schema"]
        assert response_schema == {
            "$ref": "#/components/schemas/StopTelemetryUnavailable"
        }


def test_stop_telemetry_does_not_hide_unexpected_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "unexpected_runtime_error.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))
    _clear_stop_telemetry_env(monkeypatch)

    def raise_programming_defect(*args: object, **kwargs: object) -> None:
        raise RuntimeError("programming defect")

    monkeypatch.setattr(
        LocalStateStore,
        "intake_stop_telemetry_event",
        raise_programming_defect,
    )

    with pytest.raises(RuntimeError, match="programming defect"):
        client.post("/api/codex/telemetry/stop-events")
