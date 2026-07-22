from types import SimpleNamespace

import wilq.connectors.refresh as refresh_module
from wilq.connectors.refresh import _persist_refresh_result, _quality_contract
from wilq.connectors.vendor import VendorReadResult
from wilq.schemas import (
    ConnectorQualityState,
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorSettlementState,
)


def test_gsc_refresh_exposes_exact_window_and_partial_detail_quality() -> None:
    window, settlement, quality = _quality_contract(
        "google_search_console",
        {
            "date_start": "2026-07-15",
            "date_end": "2026-07-15",
            "detail_data_completeness": "partial_possible",
            "query_page_rows_truncated": "false",
        },
    )

    assert (window.date_start, window.date_end) == ("2026-07-15", "2026-07-15")
    assert settlement == ConnectorSettlementState.settled
    assert quality == ConnectorQualityState.partial


def test_ga4_without_window_is_unverified_and_carries_settlement_caveat() -> None:
    window, settlement, quality = _quality_contract("google_analytics_4", {})

    assert window.date_start is None
    assert settlement == ConnectorSettlementState.settling
    assert quality == ConnectorQualityState.unverified
    assert window.interpretation_caveats


def test_manual_snapshot_connectors_are_not_claimed_as_settling() -> None:
    ahrefs_window, ahrefs_settlement, ahrefs_quality = _quality_contract("ahrefs", {})
    localo_window, localo_settlement, localo_quality = _quality_contract(
        "localo",
        {
            "localo_active_place_count": 3,
            "date_start": "2026-06-18",
            "date_end": "2026-07-18",
        },
    )

    assert ahrefs_settlement == ConnectorSettlementState.not_applicable
    assert localo_settlement == ConnectorSettlementState.not_applicable
    assert ahrefs_quality == ConnectorQualityState.unverified
    assert localo_quality == ConnectorQualityState.unverified
    assert ahrefs_window.cadence == "manual_lag_1_snapshot"
    assert ahrefs_window.coverage_scope == "domain_snapshot"
    assert localo_window.cadence == "trailing_30_days"
    assert localo_window.coverage_scope == "active_places"
    assert localo_window.coverage_count == 3


def test_localo_proxy_exposes_requested_and_covered_places_when_detail_is_capped() -> None:
    window, settlement, quality = _quality_contract(
        "localo",
        {
            "date_start": "2026-06-18",
            "date_end": "2026-07-18",
            "localo_active_place_count": 20,
            "localo_requested_place_count": 20,
            "localo_covered_place_count": 10,
            "localo_place_detail_truncated": "true",
            "localo_proxy_source": "localo_google_metric_series_and_place_reads",
        },
    )

    assert settlement == ConnectorSettlementState.not_applicable
    assert quality == ConnectorQualityState.partial
    assert window.requested_count == 20
    assert window.covered_count == 10
    assert window.cap_or_truncation == "place_detail_limit"
    assert window.proxy_source == "localo_google_metric_series_and_place_reads"
    assert any("account-wide" in caveat for caveat in window.interpretation_caveats)


def test_async_persist_reuses_quality_contract_for_completed_vendor_read(monkeypatch) -> None:
    saved: list[ConnectorRefreshRun] = []

    class FakeLocalState:
        def save_connector_refresh_run(self, run: ConnectorRefreshRun) -> ConnectorRefreshRun:
            saved.append(run)
            return run

    class FakeMetricStore:
        def save_connector_refresh_metrics(self, *_args, **_kwargs) -> None:
            return None

    monkeypatch.setattr(refresh_module, "local_state_store", lambda: FakeLocalState())
    monkeypatch.setattr(refresh_module, "metric_store", lambda: FakeMetricStore())
    run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_async",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.running,
        summary="async",
    )
    result = VendorReadResult(
        status=ConnectorRefreshStatus.completed,
        summary="completed",
        metric_summary={"date_start": "2026-06-19", "date_end": "2026-07-16"},
    )

    completed = _persist_refresh_result(run, result)

    assert completed.covered_window.date_start == "2026-06-19"
    assert completed.covered_window.date_end == "2026-07-16"
    assert completed.settlement_state == ConnectorSettlementState.settling
    assert completed.quality_state == ConnectorQualityState.unverified
    assert saved[0].covered_window.date_start == "2026-06-19"
    assert completed.status_label == "odczyt zakończony"


def test_async_refresh_transitions_keep_api_owned_status_labels(monkeypatch) -> None:
    saved: list[ConnectorRefreshRun] = []

    class FakeLocalState:
        def save_connector_refresh_run(self, run: ConnectorRefreshRun) -> ConnectorRefreshRun:
            saved.append(run)
            return run

        def get_connector_refresh_run(self, run_id: str) -> ConnectorRefreshRun | None:
            return next((run for run in reversed(saved) if run.id == run_id), None)

    class FakeMetricStore:
        def save_connector_refresh_metrics(self, *_args, **_kwargs) -> None:
            return None

    queued = ConnectorRefreshRun(
        id="refresh_gsc_queued",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.queued,
        summary="queued",
    )
    monkeypatch.setattr(refresh_module, "local_state_store", lambda: FakeLocalState())
    monkeypatch.setattr(refresh_module, "metric_store", lambda: FakeMetricStore())
    monkeypatch.setattr(refresh_module, "get_connector_refresh_run", lambda _run_id: queued)
    monkeypatch.setattr(
        refresh_module,
        "get_connector_status",
        lambda _connector_id: SimpleNamespace(
            status="configured",
            configured=True,
            missing_credentials=[],
        ),
    )
    monkeypatch.setattr(
        refresh_module,
        "_refresh_result",
        lambda **_kwargs: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="completed",
        ),
    )

    completed = refresh_module.complete_queued_connector_refresh(
        queued.id,
        "google_search_console",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
    )

    assert completed is not None
    assert [run.status_label for run in saved] == [
        "odczyt trwa",
        "odczyt zakończony",
        "odczyt zakończony",
    ]
