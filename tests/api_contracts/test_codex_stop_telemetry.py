from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app

client = TestClient(app)


def test_stop_intake_owns_identity_and_persists_only_the_minimal_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "codex_state.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(state_path))

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
    }
    assert receipt["event_id"] != "caller_owned_event"
    assert receipt["event_type"] == "stop"
    assert receipt["contract_version"] == 1
    received_at = datetime.fromisoformat(receipt["received_at"])
    assert before_intake <= received_at <= after_intake
    assert received_at != datetime(2000, 1, 1, tzinfo=UTC)

    with sqlite3.connect(state_path) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(codex_stop_events)")
        ]
        row = connection.execute(
            "SELECT id, received_at, event_type, contract_version FROM codex_stop_events"
        ).fetchone()
        codex_run_count = connection.execute(
            "SELECT COUNT(*) FROM codex_runs"
        ).fetchone()[0]

    assert columns == ["id", "received_at", "event_type", "contract_version"]
    assert row is not None
    assert row[0] == receipt["event_id"]
    assert datetime.fromisoformat(row[1]) == received_at
    assert row[2:] == ("stop", 1)
    assert codex_run_count == 0
