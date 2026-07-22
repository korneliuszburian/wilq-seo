from __future__ import annotations

from uuid import uuid4

from wilq.connectors.ahrefs.client import refresh_ahrefs_domain_rating
from wilq.connectors.google_ads.client import refresh_google_ads_campaign_summary
from wilq.connectors.google_analytics_4.client import refresh_ga4_behavior_summary
from wilq.connectors.google_merchant_center.client import (
    refresh_merchant_product_status_summary,
)
from wilq.connectors.google_search_console.client import refresh_search_console_site_summary
from wilq.connectors.google_sheets.client import refresh_google_sheets_review_surface
from wilq.connectors.localo.client import refresh_localo_visibility_summary
from wilq.connectors.registry import get_connector_status
from wilq.connectors.vendor import VendorReadResult
from wilq.connectors.wordpress.client import refresh_wordpress_content_inventory
from wilq.evidence.registry import connector_evidence_id, refresh_run_evidence_id
from wilq.operator_labels import connector_refresh_status_label
from wilq.schemas import (
    ConnectorCoveredWindow,
    ConnectorQualityState,
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorSettlementState,
    ConnectorStatusValue,
    utc_now,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store


def _quality_contract(
    connector_id: str,
    summary: dict[str, float | int | str],
) -> tuple[ConnectorCoveredWindow, ConnectorSettlementState, ConnectorQualityState]:
    date_start = summary.get("date_start")
    date_end = summary.get("date_end")
    completeness = summary.get("detail_data_completeness") or summary.get(
        "aggregate_data_completeness"
    )
    truncated = summary.get("query_page_rows_truncated")
    cap = str(truncated) if truncated is not None else None
    caveats: list[str] = []
    if cap == "true":
        caveats.append("Szczegóły źródła osiągnęły limit wierszy.")
    if connector_id == "google_analytics_4":
        settlement = ConnectorSettlementState.settling
        caveats.append(
            "GA4 może zmieniać się po zebraniu danych; "
            "okno pozostaje w stanie rozliczania, a jakość wymaga ostrożnej interpretacji."
        )
    elif connector_id == "ahrefs":
        settlement = ConnectorSettlementState.not_applicable
        caveats.append(
            "Ahrefs jest ręcznym snapshotem; czas zebrania WILQ nie jest datą snapshotu danych."
        )
    elif connector_id == "localo":
        settlement = ConnectorSettlementState.not_applicable
        caveats.append(
            "Localo agreguje zakres miejsc i fraz; interpretuj wynik wyłącznie "
            "z podanym oknem i coverage."
        )
        if summary.get("localo_place_detail_truncated") == "true":
            cap = "place_detail_limit"
            caveats.append(
                "Szczegóły Localo obejmują tylko część aktywnych miejsc; "
                "wnioski nie są account-wide."
            )
    elif connector_id == "google_search_console":
        settlement = ConnectorSettlementState.settled
    else:
        settlement = ConnectorSettlementState.unknown
    quality = (
        ConnectorQualityState.partial
        if cap in {"true", "place_detail_limit"} or completeness == "partial_possible"
        else (
            ConnectorQualityState.unverified
            if connector_id in {"google_analytics_4", "ahrefs", "localo"}
            else (
                ConnectorQualityState.verified
                if date_start and date_end
                else ConnectorQualityState.unverified
            )
        )
    )
    return (
        ConnectorCoveredWindow(
            date_start=date_start if isinstance(date_start, str) else None,
            date_end=date_end if isinstance(date_end, str) else None,
            completeness=str(completeness) if completeness is not None else None,
            cap_or_truncation=cap,
            cadence=(
                "manual_lag_1_snapshot"
                if connector_id == "ahrefs"
                else "trailing_30_days"
                if connector_id == "localo"
                else None
            ),
            coverage_scope=(
                "domain_snapshot"
                if connector_id == "ahrefs"
                else "active_places"
                if connector_id == "localo"
                else None
            ),
            coverage_count=(
                int(summary["localo_active_place_count"])
                if connector_id == "localo"
                and isinstance(summary.get("localo_active_place_count"), (int, float))
                else None
            ),
            requested_count=(
                int(summary["localo_requested_place_count"])
                if connector_id == "localo"
                and isinstance(summary.get("localo_requested_place_count"), (int, float))
                else None
            ),
            covered_count=(
                int(summary["localo_covered_place_count"])
                if connector_id == "localo"
                and isinstance(summary.get("localo_covered_place_count"), (int, float))
                else None
            ),
            proxy_source=(
                str(summary["localo_proxy_source"])
                if connector_id == "localo" and summary.get("localo_proxy_source")
                else None
            ),
            interpretation_caveats=caveats,
        ),
        settlement,
        quality,
    )


def run_connector_refresh(
    connector_id: str,
    request: ConnectorRefreshRequest | None = None,
) -> ConnectorRefreshRun | None:
    connector = get_connector_status(connector_id)
    if connector is None:
        return None

    refresh_request = request or ConnectorRefreshRequest()
    started_at = utc_now()
    run_id = f"refresh_{connector_id}_{uuid4().hex[:12]}"
    result = _refresh_result(
        connector_id=connector_id,
        request=refresh_request,
        connector_status=connector.status,
        configured=connector.configured,
        missing_credentials=connector.missing_credentials,
    )
    covered_window, settlement_state, quality_state = _quality_contract(
        connector_id, result.metric_summary
    )
    run = ConnectorRefreshRun(
        id=run_id,
        connector_id=connector_id,
        mode=refresh_request.mode,
        status=result.status,
        started_at=started_at,
        completed_at=utc_now(),
        evidence_ids=[
            connector_evidence_id(connector_id),
            refresh_run_evidence_id(run_id),
        ],
        missing_credentials=connector.missing_credentials,
        checked_credentials=connector.required_env,
        external_call_attempted=result.external_call_attempted,
        vendor_data_collected=result.vendor_data_collected,
        metrics_persisted=False,
        metric_summary=result.metric_summary,
        covered_window=covered_window,
        settlement_state=settlement_state,
        quality_state=quality_state,
        summary=result.summary,
        errors=result.errors,
    )
    saved_run = local_state_store().save_connector_refresh_run(run)
    try:
        metric_store().save_connector_refresh_metrics(saved_run, detailed_facts=result.metric_facts)
    except Exception as error:
        failed_run = saved_run.model_copy(
            update={
                "status": ConnectorRefreshStatus.failed,
                "completed_at": utc_now(),
                "metrics_persisted": False,
                "summary": (
                    f"{saved_run.summary} Metric persistence failed; refresh run marked failed."
                ),
                "errors": [
                    *saved_run.errors,
                    f"metric_persistence_failed:{type(error).__name__}",
                ],
            }
        )
        return local_state_store().save_connector_refresh_run(failed_run)
    saved_run = saved_run.model_copy(update={"metrics_persisted": True})
    saved_run = local_state_store().save_connector_refresh_run(saved_run)
    return saved_run


def queue_connector_refresh(
    connector_id: str,
    request: ConnectorRefreshRequest,
) -> ConnectorRefreshRun | None:
    connector = get_connector_status(connector_id)
    if connector is None:
        return None
    active_runs = [
        run
        for run in local_state_store().list_connector_refresh_runs(connector_id=connector_id)
        if run.status in {ConnectorRefreshStatus.queued, ConnectorRefreshStatus.running}
    ]
    if active_runs:
        return active_runs[0]
    started_at = utc_now()
    run_id = f"refresh_{connector_id}_{uuid4().hex[:12]}"
    return local_state_store().save_connector_refresh_run(
        ConnectorRefreshRun(
            id=run_id,
            connector_id=connector_id,
            mode=request.mode,
            status=ConnectorRefreshStatus.queued,
            started_at=started_at,
            completed_at=None,
            evidence_ids=[
                connector_evidence_id(connector_id),
                refresh_run_evidence_id(run_id),
            ],
            missing_credentials=connector.missing_credentials,
            checked_credentials=connector.required_env,
            metrics_persisted=False,
            summary="Odczyt źródła dodany do kolejki read-only.",
        )
    )


def complete_queued_connector_refresh(
    run_id: str,
    connector_id: str,
    request: ConnectorRefreshRequest,
) -> ConnectorRefreshRun | None:
    queued_run = get_connector_refresh_run(run_id)
    connector = get_connector_status(connector_id)
    if queued_run is None or connector is None:
        return None
    running_run = queued_run.model_copy(
        update={
            "status": ConnectorRefreshStatus.running,
            "status_label": connector_refresh_status_label(ConnectorRefreshStatus.running),
            "summary": "Odczyt źródła trwa w trybie read-only.",
        }
    )
    local_state_store().save_connector_refresh_run(running_run)
    result = _refresh_result(
        connector_id=connector_id,
        request=request,
        connector_status=connector.status,
        configured=connector.configured,
        missing_credentials=connector.missing_credentials,
    )
    return _persist_refresh_result(running_run, result)


def _persist_refresh_result(
    run: ConnectorRefreshRun,
    result: VendorReadResult,
) -> ConnectorRefreshRun:
    covered_window, settlement_state, quality_state = _quality_contract(
        run.connector_id, result.metric_summary
    )
    saved_run = local_state_store().save_connector_refresh_run(
        run.model_copy(
            update={
                "status": result.status,
                "status_label": connector_refresh_status_label(result.status),
                "completed_at": utc_now(),
                "external_call_attempted": result.external_call_attempted,
                "vendor_data_collected": result.vendor_data_collected,
                "metrics_persisted": False,
                "metric_summary": result.metric_summary,
                "covered_window": covered_window,
                "settlement_state": settlement_state,
                "quality_state": quality_state,
                "summary": result.summary,
                "errors": result.errors,
            }
        )
    )
    try:
        metric_store().save_connector_refresh_metrics(saved_run, detailed_facts=result.metric_facts)
    except Exception as error:
        failed_run = saved_run.model_copy(
            update={
                "status": ConnectorRefreshStatus.failed,
                "status_label": connector_refresh_status_label(ConnectorRefreshStatus.failed),
                "completed_at": utc_now(),
                "metrics_persisted": False,
                "summary": (
                    f"{saved_run.summary} Metric persistence failed; refresh run marked failed."
                ),
                "errors": [
                    *saved_run.errors,
                    f"metric_persistence_failed:{type(error).__name__}",
                ],
            }
        )
        return local_state_store().save_connector_refresh_run(failed_run)
    return local_state_store().save_connector_refresh_run(
        saved_run.model_copy(update={"metrics_persisted": True})
    )


def list_connector_refresh_runs(connector_id: str | None = None) -> list[ConnectorRefreshRun]:
    return local_state_store().list_connector_refresh_runs(connector_id=connector_id)


def get_connector_refresh_run(run_id: str) -> ConnectorRefreshRun | None:
    return local_state_store().get_connector_refresh_run(run_id)


def _refresh_result(
    connector_id: str,
    request: ConnectorRefreshRequest,
    connector_status: ConnectorStatusValue,
    configured: bool,
    missing_credentials: list[str],
) -> VendorReadResult:
    if connector_status == ConnectorStatusValue.disabled:
        summary = (
            f"Connector {connector_id} is disabled by current product scope. "
            "No external API call was attempted."
        )
        return VendorReadResult(
            status=ConnectorRefreshStatus.completed
            if request.mode == ConnectorRefreshMode.status_probe
            else ConnectorRefreshStatus.blocked,
            summary=summary,
            errors=[] if request.mode == ConnectorRefreshMode.status_probe else [summary],
        )
    if request.mode == ConnectorRefreshMode.status_probe:
        return VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary=_status_probe_summary(connector_id, configured, missing_credentials),
        )
    errors = _vendor_read_errors(connector_id, missing_credentials)
    if errors:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=errors[0],
            errors=errors,
        )
    if connector_id == "google_ads":
        return refresh_google_ads_campaign_summary(request)
    if connector_id == "google_search_console":
        return refresh_search_console_site_summary(request)
    if connector_id == "google_analytics_4":
        return refresh_ga4_behavior_summary(request)
    if connector_id == "google_merchant_center":
        return refresh_merchant_product_status_summary(request)
    if connector_id == "google_sheets":
        return refresh_google_sheets_review_surface(request)
    if connector_id == "ahrefs":
        return refresh_ahrefs_domain_rating(request)
    if connector_id == "localo":
        return refresh_localo_visibility_summary(request)
    if connector_id in {"wordpress_ekologus", "wordpress_sklep"}:
        return refresh_wordpress_content_inventory(connector_id, request)
    summary = (
        f"Vendor read adapter for connector {connector_id} is not implemented yet. "
        "No external API call was attempted."
    )
    return VendorReadResult(
        status=ConnectorRefreshStatus.blocked,
        summary=summary,
        errors=[summary],
    )


def _vendor_read_errors(
    connector_id: str,
    missing_credentials: list[str],
) -> list[str]:
    if missing_credentials:
        return [
            f"Vendor read blocked by missing credential names: {', '.join(missing_credentials)}."
        ]
    return []


def _status_probe_summary(
    connector_id: str,
    configured: bool,
    missing_credentials: list[str],
) -> str:
    if configured:
        return (
            f"Connector {connector_id} status probe completed from credential-name "
            "presence. No external API call was attempted."
        )
    return (
        f"Connector {connector_id} status probe completed and found missing "
        f"credential names: {', '.join(missing_credentials)}. No secret values "
        "are exposed."
    )
