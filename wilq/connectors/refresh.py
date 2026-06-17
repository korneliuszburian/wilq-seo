from __future__ import annotations

from uuid import uuid4

from wilq.connectors.registry import get_connector_status
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
    errors = _refresh_errors(connector_id, refresh_request.mode, connector.missing_credentials)
    status = ConnectorRefreshStatus.blocked if errors else ConnectorRefreshStatus.completed
    summary = _refresh_summary(
        connector_id,
        refresh_request.mode,
        connector.configured,
        connector.missing_credentials,
        errors,
    )
    run = ConnectorRefreshRun(
        id=run_id,
        connector_id=connector_id,
        mode=refresh_request.mode,
        status=status,
        started_at=started_at,
        completed_at=utc_now(),
        evidence_ids=[
            connector_evidence_id(connector_id),
            refresh_run_evidence_id(run_id),
        ],
        missing_credentials=connector.missing_credentials,
        checked_credentials=connector.required_env,
        external_call_attempted=False,
        vendor_data_collected=False,
        summary=summary,
        errors=errors,
    )
    return local_state_store().save_connector_refresh_run(run)


def list_connector_refresh_runs(connector_id: str | None = None) -> list[ConnectorRefreshRun]:
    return local_state_store().list_connector_refresh_runs(connector_id=connector_id)


def get_connector_refresh_run(run_id: str) -> ConnectorRefreshRun | None:
    return local_state_store().get_connector_refresh_run(run_id)


def _refresh_errors(
    connector_id: str,
    mode: ConnectorRefreshMode,
    missing_credentials: list[str],
) -> list[str]:
    if mode == ConnectorRefreshMode.status_probe:
        return []
    if missing_credentials:
        return [
            "Vendor read blocked by missing credential names: "
            f"{', '.join(missing_credentials)}."
        ]
    return [
        f"Vendor read adapter for connector {connector_id} is not implemented yet. "
        "No external API call was attempted."
    ]


def _refresh_summary(
    connector_id: str,
    mode: ConnectorRefreshMode,
    configured: bool,
    missing_credentials: list[str],
    errors: list[str],
) -> str:
    if mode == ConnectorRefreshMode.status_probe:
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
    return errors[0]
