from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tests._contract_support.api_client import client
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    utc_now,
)
from wilq.storage.local_state import local_state_store


def test_process_loss_recovery_api_contract_is_bodyless_and_conflict_safe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "recovery-api-contract.sqlite3"))
    run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_api_contract",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.running,
        started_at=datetime(2026, 8, 7, 8, 27, 10, tzinfo=UTC),
        completed_at=None,
        external_call_attempted=False,
        vendor_data_collected=False,
        metrics_persisted=False,
        summary="Odczyt źródła trwa w trybie read-only.",
    )
    local_state_store().save_connector_refresh_run(run)

    response = client.post(f"/api/connectors/refresh-runs/{run.id}/recover-process-loss")

    assert response.status_code == 200
    payload = response.json()
    assert payload["process_loss"] is True
    assert payload["recovery_vendor_call_attempted"] is False
    assert payload["interrupted_run_vendor_call_state"] == "unverified"
    assert payload["retry_scheduled"] is False
    assert payload["human_approval_recorded"] is False
    assert payload["audit_event_id"]
    assert payload["run"]["status"] == "failed"
    assert payload["run"]["completed_at"] is not None
    assert [event.id for event in local_state_store().list_audit_events()] == [
        payload["audit_event_id"]
    ]

    second_response = client.post(f"/api/connectors/refresh-runs/{run.id}/recover-process-loss")
    assert second_response.status_code == 409

    unknown_response = client.post(
        "/api/connectors/refresh-runs/refresh_google_merchant_center_unknown/recover-process-loss"
    )
    assert unknown_response.status_code == 404


def test_process_loss_recovery_api_exposes_safe_typed_rejection_codes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "recovery-api-rejections.sqlite3"))
    current_process_run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_current_process_rejection",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.running,
        started_at=utc_now(),
        completed_at=None,
        external_call_attempted=False,
        vendor_data_collected=False,
        metrics_persisted=False,
        summary="Odczyt źródła trwa w trybie read-only.",
    )
    local_state_store().save_connector_refresh_run(current_process_run)

    current_response = client.post(
        f"/api/connectors/refresh-runs/{current_process_run.id}/recover-process-loss"
    )

    assert current_response.status_code == 409
    current_detail = current_response.json()["detail"]
    assert current_detail["code"] == "started_in_current_process"
    assert current_detail["label"]

    invalid_snapshot = ConnectorRefreshRun(
        id="refresh_google_merchant_center_invalid_rejection",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=datetime(2026, 8, 7, 8, 27, 10, tzinfo=UTC),
        completed_at=datetime(2026, 8, 7, 8, 27, 11, tzinfo=UTC),
        external_call_attempted=False,
        vendor_data_collected=False,
        metrics_persisted=False,
        summary="Niekwalifikujący się snapshot.",
    )
    local_state_store().save_connector_refresh_run(invalid_snapshot)

    invalid_response = client.post(
        f"/api/connectors/refresh-runs/{invalid_snapshot.id}/recover-process-loss"
    )

    assert invalid_response.status_code == 409
    invalid_detail = invalid_response.json()["detail"]
    assert invalid_detail["code"] == "snapshot_not_recoverable"
    assert invalid_detail["label"]
