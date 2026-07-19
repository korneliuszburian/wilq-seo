from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests._contract_support.api_client import client
from wilq.schemas import CodexRun
from wilq.storage.local_state import local_state_store


def test_system_status_reports_local_state_without_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "status_state.sqlite3"))
    response = client.get("/api/system/status")
    assert response.status_code == 200
    local_state = response.json()["local_state"]
    assert local_state["backend"] == "sqlite"
    assert "path" not in local_state


def test_system_status_exposes_latest_typed_codex_failure_without_provider_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "codex_status.sqlite3"))
    store = local_state_store()
    store.save_codex_run(
        CodexRun(
            id="codex_content_planning_status_test",
            skill="wilq-content-operator",
            hook="content_planning_proposal",
            source="wilq_api",
            status="failed",
            error="runtime_failed:codex_response_stream_disconnected",
        )
    )
    store.save_codex_run(
        CodexRun(
            id="codex_stop_status_test",
            hook="Stop",
            source="codex_hook",
            status="completed",
            started_at=datetime.now(UTC) + timedelta(minutes=1),
        )
    )

    response = client.get("/api/system/status")

    assert response.status_code == 200
    runtime = response.json()["codex_runtime"]
    assert runtime["operational_status"] == "degraded"
    assert runtime["operational_blocker_code"] == (
        "runtime_failed:codex_response_stream_disconnected"
    )
    assert runtime["operational_blocker_label"]
    assert runtime["last_codex_run"] == {
        "id": "codex_content_planning_status_test",
        "status": "failed",
        "skill": "wilq-content-operator",
        "hook": "content_planning_proposal",
        "started_at": runtime["last_codex_run"]["started_at"],
        "completed_at": None,
        "error": "runtime_failed:codex_response_stream_disconnected",
    }
    assert runtime["last_codex_error"] == "runtime_failed:codex_response_stream_disconnected"


def test_system_status_redacts_untyped_codex_error_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "codex_status_untyped.sqlite3"))
    local_state_store().save_codex_run(
        CodexRun(
            id="codex_untyped_error_status_test",
            skill="wilq-content-operator",
            source="wilq_api",
            status="failed",
            error='runtime_failed:{"provider_payload":"private"}',
        )
    )

    runtime = client.get("/api/system/status").json()["codex_runtime"]

    assert runtime["operational_blocker_code"] == "codex_run_error_unclassified"
    assert "private" not in str(runtime)
