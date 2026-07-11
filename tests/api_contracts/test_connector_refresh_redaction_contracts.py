from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.api.wilq_api.routers import connectors as connectors_router
from tests._contract_support.api_client import client
from tests._contract_support.env import clear_google_ads_env


def test_connector_refresh_run_persists_redacted_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv(
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "gho_refreshsecretvalue1234567890",  # pragma: allowlist secret
    )

    response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )
    assert response.status_code == 200
    run = response.json()
    assert run["connector_id"] == "google_ads"
    assert run["mode"] == "vendor_read"
    assert run["status"] == "blocked"
    assert run["external_call_attempted"] is False
    assert run["vendor_data_collected"] is False
    assert "ev_connector_google_ads_status" in run["evidence_ids"]

    list_response = client.get("/api/connectors/refresh-runs")
    assert list_response.status_code == 200
    serialized_runs = json.dumps(list_response.json())
    assert run["id"] in serialized_runs
    assert "gho_refreshsecretvalue1234567890" not in serialized_runs

    evidence_response = client.get("/api/evidence")
    assert evidence_response.status_code == 200
    evidence_ids = {item["id"] for item in evidence_response.json()}
    assert f"ev_refresh_{run['id']}" in evidence_ids
    serialized_evidence = json.dumps(evidence_response.json())
    assert "gho_refreshsecretvalue1234567890" not in serialized_evidence

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert context_response.status_code == 200
    context_runs = {item["id"] for item in context_response.json()["connector_refresh_runs"]}
    assert run["id"] in context_runs


def test_connector_status_exposes_typed_refresh_state_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "refresh_status.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)

    response = client.get("/api/connectors/google_ads/status")

    assert response.status_code == 200
    refresh_state = response.json()["refresh_state"]
    assert refresh_state["state"] in {"unknown", "stale", "blocked"}
    assert refresh_state["refresh_allowed"] is False
    assert refresh_state["state_label"]
    assert refresh_state["safe_next_step"]
    assert refresh_state["affected_decisions"] == ["ads_diagnostics", "command_center"]
    serialized = json.dumps(refresh_state)
    assert "GOOGLE_ADS_CLIENT_SECRET" not in serialized
    assert "refresh_token" not in serialized.lower()


def test_async_connector_refresh_returns_queued_run_and_finishes_read_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "async_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)

    response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "run_async": True, "reason": "async contract test"},
    )

    assert response.status_code == 200
    queued = response.json()
    assert queued["status"] == "queued"
    assert queued["completed_at"] is None
    assert queued["external_call_attempted"] is False
    detail = client.get(f"/api/connectors/refresh-runs/{queued['id']}")
    assert detail.status_code == 200
    finished = detail.json()
    assert finished["status"] in {"blocked", "failed", "completed"}
    assert finished["external_call_attempted"] is False
    assert "async contract test" not in json.dumps(finished)


def test_async_connector_refresh_reuses_active_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "async_dedupe_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setattr(connectors_router, "complete_queued_connector_refresh", lambda *args: None)

    first = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "run_async": True, "reason": "dedupe contract test"},
    )
    second = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "run_async": True, "reason": "dedupe contract test"},
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["status"] == "queued"
