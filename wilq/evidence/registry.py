from __future__ import annotations

from wilq.connectors.registry import list_connector_statuses
from wilq.schemas import Evidence


def connector_evidence_id(connector_id: str) -> str:
    return f"ev_connector_{connector_id}_status"


def list_evidence() -> list[Evidence]:
    return [
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
