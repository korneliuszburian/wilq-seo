from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.registry import list_connector_statuses
from wilq.credentials.runtime import credential_runtime_status
from wilq.jobs.scheduler import scheduler_status
from wilq.opportunities.engine import OPPORTUNITY_TYPES
from wilq.schemas import ConnectorStatus, ConnectorSummary, utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "wilq-api",
        "health": "/api/health",
        "system_status": "/api/system/status",
        "connectors": "/api/connectors",
        "command_center": "/api/dashboard/command-center",
        "docs": "/docs",
    }


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "wilq-api"}


@router.get("/api/system/status")
def system_status() -> dict[str, Any]:
    connectors = list_connector_statuses()
    return redact_mapping(
        {
            "generated_at": utc_now().isoformat(),
            "connector_summary": connector_summary(connectors).model_dump(),
            "credential_runtime": credential_runtime_status(detailed=False),
            "codex_runtime": codex_runtime_status(),
            "job_scheduler": scheduler_status(),
            "local_state": local_state_store().status(),
            "metric_store": metric_store().status(),
            "opportunity_types": list(OPPORTUNITY_TYPES),
        }
    )


def connector_summary(connectors: list[ConnectorStatus]) -> ConnectorSummary:
    missing = sum(1 for connector in connectors if connector.missing_credentials)
    configured = sum(1 for connector in connectors if connector.configured)
    return ConnectorSummary(
        total=len(connectors),
        configured=configured,
        missing_credentials=missing,
    )
