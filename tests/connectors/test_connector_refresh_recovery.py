from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

import wilq.connectors.refresh as refresh_module
from wilq.connectors.vendor import VendorReadResult
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRecoveryReceipt,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    utc_now,
)
from wilq.storage.local_state import local_state_store


def _orphaned_run(run_id: str) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id=run_id,
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


class _CountingMetricStore:
    def __init__(self) -> None:
        self.calls = 0

    def save_connector_refresh_metrics(self, *_args: object, **_kwargs: object) -> None:
        self.calls += 1


def test_process_loss_recovery_wins_payload_cas_and_late_worker_does_no_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "recovery-race.sqlite3"))
    store = local_state_store()
    run = _orphaned_run("refresh_google_merchant_center_recovery_first")
    store.save_connector_refresh_run(run)
    metrics = _CountingMetricStore()
    monkeypatch.setattr(refresh_module, "local_state_store", lambda: store)
    monkeypatch.setattr(refresh_module, "metric_store", lambda: metrics)

    receipt = refresh_module.recover_connector_refresh_run(run.id, run)
    late_worker = refresh_module._persist_refresh_result(
        run,
        VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="late worker result",
            vendor_data_collected=True,
            metric_summary={"issue_product_count": 1},
        ),
    )

    assert isinstance(receipt, ConnectorRefreshRecoveryReceipt)
    assert receipt.run.status == ConnectorRefreshStatus.failed
    assert receipt.recovery_vendor_call_attempted is False
    assert receipt.interrupted_run_vendor_call_state == "unverified"
    assert late_worker is None
    assert metrics.calls == 0
    persisted = store.get_connector_refresh_run(run.id)
    assert persisted is not None
    assert persisted.status == ConnectorRefreshStatus.failed
    assert persisted.vendor_data_collected is False
    audits = store.list_audit_events()
    assert len(audits) == 1
    assert audits[0].id == f"audit_connector_refresh_process_loss_{run.id}"
    audit_text = f"{audits[0].summary} {audits[0].details}"
    assert "niezweryfikowany" in audit_text
    assert "recovery_vendor_call_attempted" in audit_text
    assert "ponowienia" in audit_text
    assert audits[0].actor != "operator"


def test_process_loss_recovery_accepts_semantically_equal_legacy_payload_format(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "recovery-legacy-payload.sqlite3"))
    store = local_state_store()
    run = _orphaned_run("refresh_google_merchant_center_legacy_payload").model_copy(
        update={"summary": "legacy orphan"}
    )
    store.save_connector_refresh_run(run)
    legacy_payload = json.dumps(run.model_dump(mode="json"), indent=2)
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE connector_refresh_runs SET payload_json = ? WHERE id = ?",
            (legacy_payload, run.id),
        )
    canonical_payload = json.dumps(
        run.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json.loads(legacy_payload) == json.loads(canonical_payload)
    assert legacy_payload != canonical_payload

    metrics = _CountingMetricStore()
    monkeypatch.setattr(refresh_module, "local_state_store", lambda: store)
    monkeypatch.setattr(refresh_module, "metric_store", lambda: metrics)

    receipt = refresh_module.recover_connector_refresh_run(run.id, run)
    late_worker = refresh_module._persist_refresh_result(
        run,
        VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="late worker result",
            vendor_data_collected=True,
            metric_summary={"issue_product_count": 1},
        ),
    )

    assert receipt is not None
    assert receipt.run.status == ConnectorRefreshStatus.failed
    assert late_worker is None
    assert metrics.calls == 0
    assert len(store.list_audit_events()) == 1


def test_worker_payload_cas_wins_and_recovery_cannot_terminal_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "worker-race.sqlite3"))
    store = local_state_store()
    run = _orphaned_run("refresh_google_merchant_center_worker_first")
    store.save_connector_refresh_run(run)
    metrics = _CountingMetricStore()
    monkeypatch.setattr(refresh_module, "local_state_store", lambda: store)
    monkeypatch.setattr(refresh_module, "metric_store", lambda: metrics)

    worker_result = refresh_module._persist_refresh_result(
        run,
        VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="worker result",
            vendor_data_collected=True,
            metric_summary={"issue_product_count": 1},
        ),
    )
    recovery_result = refresh_module.recover_connector_refresh_run(run.id, run)

    assert worker_result is not None
    assert worker_result.status == ConnectorRefreshStatus.completed
    assert recovery_result is None
    assert metrics.calls == 1
    assert store.list_audit_events() == []


def test_recovery_rejects_current_process_owner_and_snapshot_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "recovery-fences.sqlite3"))
    store = local_state_store()
    current_process_run = _orphaned_run("refresh_google_merchant_center_current")
    current_process_run = current_process_run.model_copy(update={"started_at": utc_now()})
    store.save_connector_refresh_run(current_process_run)

    assert (
        refresh_module.recover_connector_refresh_run(
            current_process_run.id,
            current_process_run,
        )
        is None
    )

    orphaned = _orphaned_run("refresh_google_merchant_center_snapshot_conflict")
    store.save_connector_refresh_run(orphaned)
    conflicting_snapshot = orphaned.model_copy(update={"summary": "tampered snapshot"})
    assert refresh_module.recover_connector_refresh_run(orphaned.id, conflicting_snapshot) is None


def test_worker_without_transaction_protocol_fails_closed_before_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _orphaned_run("refresh_google_merchant_center_no_transaction")
    metrics = _CountingMetricStore()

    class NoTransactionStore:
        def save_connector_refresh_run(self, _run: ConnectorRefreshRun) -> ConnectorRefreshRun:
            raise AssertionError("unconditional connector refresh save must not be used")

    monkeypatch.setattr(refresh_module, "local_state_store", lambda: NoTransactionStore())
    monkeypatch.setattr(refresh_module, "metric_store", lambda: metrics)

    result = refresh_module._persist_refresh_result(
        run,
        VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="worker result",
            vendor_data_collected=True,
            metric_summary={"issue_product_count": 1},
        ),
    )

    assert result is None
    assert metrics.calls == 0
