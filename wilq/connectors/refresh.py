from __future__ import annotations

from uuid import uuid4

from wilq.connectors.google_ads.client import refresh_google_ads_campaign_summary
from wilq.connectors.registry import get_connector_status
from wilq.connectors.vendor import VendorReadResult
from wilq.evidence.registry import connector_evidence_id, refresh_run_evidence_id
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    utc_now,
)
from wilq.storage.local_state import local_state_store


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
        configured=connector.configured,
        missing_credentials=connector.missing_credentials,
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
        metric_summary=result.metric_summary,
        summary=result.summary,
        errors=result.errors,
    )
    return local_state_store().save_connector_refresh_run(run)


def list_connector_refresh_runs(connector_id: str | None = None) -> list[ConnectorRefreshRun]:
    return local_state_store().list_connector_refresh_runs(connector_id=connector_id)


def get_connector_refresh_run(run_id: str) -> ConnectorRefreshRun | None:
    return local_state_store().get_connector_refresh_run(run_id)


def _refresh_result(
    connector_id: str,
    request: ConnectorRefreshRequest,
    configured: bool,
    missing_credentials: list[str],
) -> VendorReadResult:
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
            "Vendor read blocked by missing credential names: "
            f"{', '.join(missing_credentials)}."
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
