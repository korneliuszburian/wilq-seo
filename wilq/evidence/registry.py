from __future__ import annotations

from wilq.connectors.registry import list_connector_statuses
from wilq.schemas import ConnectorRefreshRun, Evidence, FreshnessState
from wilq.storage.local_state import local_state_store


def connector_evidence_id(connector_id: str) -> str:
    return f"ev_connector_{connector_id}_status"


def refresh_run_evidence_id(run_id: str) -> str:
    return f"ev_refresh_{run_id}"


def list_evidence() -> list[Evidence]:
    connector_evidence = [
        Evidence(
            id=connector_evidence_id(connector.id),
            source_connector=connector.id,
            source_type="connector_status",
            source_id=connector.id,
            freshness=connector.freshness,
            summary=_connector_summary(
                connector.id,
                connector.configured,
                connector.missing_credentials,
            ),
            raw_ref=None,
        )
        for connector in list_connector_statuses()
    ]
    refresh_evidence = [
        _refresh_run_evidence(run) for run in local_state_store().list_connector_refresh_runs()
    ]
    return [*connector_evidence, *refresh_evidence]


def get_evidence(evidence_id: str) -> Evidence | None:
    return next(
        (evidence for evidence in list_evidence() if evidence.id == evidence_id),
        None,
    )


def _connector_summary(
    connector_id: str,
    configured: bool,
    missing_credentials: list[str],
) -> str:
    if configured:
        return (
            f"Connector {connector_id} has required credential names available. "
            "No external API refresh has been run yet."
        )
    return (
        f"Connector {connector_id} is missing credential names: "
        f"{', '.join(missing_credentials)}. No secret values are exposed."
    )


def _refresh_run_evidence(run: ConnectorRefreshRun) -> Evidence:
    return Evidence(
        id=refresh_run_evidence_id(run.id),
        source_connector=run.connector_id,
        source_type="connector_refresh_run",
        source_id=run.id,
        collected_at=run.completed_at or run.started_at,
        freshness=FreshnessState(
            state="fresh" if run.status == "completed" else "missing",
            checked_at=run.completed_at or run.started_at,
            notes=run.summary,
        ),
        summary=run.summary,
        raw_ref=f"connector_refresh_runs:{run.id}",
    )
