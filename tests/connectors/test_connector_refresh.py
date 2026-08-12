from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event, Lock
from types import SimpleNamespace

import pytest

import wilq.connectors.refresh as refresh_module
from wilq.connectors.vendor import VendorReadResult
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatusValue,
)
from wilq.storage.local_state import local_state_store


def test_parallel_queue_reuses_one_run_and_only_one_worker_claims_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "parallel-refresh.sqlite3"))
    queue_barrier = Barrier(2)
    lookup_lock = Lock()
    lookup_count = 0
    connector = SimpleNamespace(
        status=ConnectorStatusValue.configured,
        configured=True,
        missing_credentials=[],
        required_env=[],
    )

    def synchronized_connector_status(_connector_id: str) -> SimpleNamespace:
        nonlocal lookup_count
        with lookup_lock:
            synchronize_queue = lookup_count < 2
            lookup_count += 1
        if synchronize_queue:
            queue_barrier.wait(timeout=5)
        return connector

    monkeypatch.setattr(refresh_module, "get_connector_status", synchronized_connector_status)
    request = ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(refresh_module.queue_connector_refresh, "google_ads", request)
            for _ in range(2)
        ]
        queued = [future.result(timeout=5) for future in futures]

    assert queued[0] is not None
    assert queued[1] is not None
    assert queued[0].id == queued[1].id
    assert queued[0].status == queued[1].status == ConnectorRefreshStatus.queued
    persisted = local_state_store().list_connector_refresh_runs(connector_id="google_ads")
    assert [run.id for run in persisted] == [queued[0].id]

    vendor_started = Event()
    release_vendor = Event()
    vendor_call_lock = Lock()
    vendor_call_count = 0

    def vendor_read(**_kwargs: object) -> VendorReadResult:
        nonlocal vendor_call_count
        with vendor_call_lock:
            vendor_call_count += 1
        vendor_started.set()
        assert release_vendor.wait(timeout=5)
        return VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="completed",
        )

    class FakeMetricStore:
        def save_connector_refresh_metrics(self, *_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(refresh_module, "_refresh_result", vendor_read)
    monkeypatch.setattr(refresh_module, "metric_store", lambda: FakeMetricStore())

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_worker = executor.submit(
            refresh_module.complete_queued_connector_refresh,
            queued[0].id,
            "google_ads",
            request,
        )
        assert vendor_started.wait(timeout=5)
        second_worker = executor.submit(
            refresh_module.complete_queued_connector_refresh,
            queued[1].id,
            "google_ads",
            request,
        )
        try:
            assert second_worker.result(timeout=5) is None
        finally:
            release_vendor.set()
        assert first_worker.result(timeout=5) is not None

    assert vendor_call_count == 1
    assert len(local_state_store().list_connector_refresh_runs(connector_id="google_ads")) == 1


def test_async_refresh_terminalizes_unexpected_vendor_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved = []
    queued_run = ConnectorRefreshRun(
        id="refresh_wordpress_exception",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.queued,
        summary="queued",
    )

    class FakeLocalState:
        def save_connector_refresh_run(self, run):
            saved.append(run)
            return run

    class FakeMetricStore:
        def save_connector_refresh_metrics(self, *_args, **_kwargs) -> None:
            return None

    monkeypatch.setattr(refresh_module, "local_state_store", lambda: FakeLocalState())
    monkeypatch.setattr(refresh_module, "get_connector_refresh_run", lambda _run_id: queued_run)
    monkeypatch.setattr(
        refresh_module,
        "claim_queued_connector_refresh_run",
        lambda _store, run: saved.append(run) or run,
    )
    monkeypatch.setattr(refresh_module, "metric_store", lambda: FakeMetricStore())
    monkeypatch.setattr(
        refresh_module,
        "get_connector_status",
        lambda _connector_id: SimpleNamespace(
            status=ConnectorStatusValue.configured,
            configured=True,
            missing_credentials=[],
        ),
    )

    def explode(**_kwargs: object) -> VendorReadResult:
        raise RuntimeError("credential-value-must-not-leak")

    monkeypatch.setattr(refresh_module, "_refresh_result", explode)

    completed = refresh_module.complete_queued_connector_refresh(
        queued_run.id,
        queued_run.connector_id,
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
    )

    assert completed is not None
    assert completed.status == ConnectorRefreshStatus.failed
    assert completed.completed_at is not None
    assert completed.vendor_data_collected is False
    assert completed.errors == ["connector_refresh_failed:RuntimeError"]
    assert "credential-value" not in completed.model_dump_json()
    assert saved[-1].status == ConnectorRefreshStatus.failed
