from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from wilq.connectors.registry import list_connector_statuses
from wilq.social.history import (
    SocialHistoryImportAudit,
    SocialHistoryInventory,
    audit_social_history_metadata_payload,
    build_social_history_inventory_from_env,
)

router = APIRouter()
SOCIAL_HISTORY_AUDIT_BODY = Body(...)


@router.get(
    "/api/social/history-inventory",
    response_model=SocialHistoryInventory,
)
def social_history_inventory() -> SocialHistoryInventory:
    connectors = list_connector_statuses()
    connector_status_by_id = {connector.id: connector for connector in connectors}
    missing_publish_access = {
        connector_id: connector_status_by_id[connector_id].missing_credentials
        for connector_id in ("linkedin", "facebook")
        if connector_id in connector_status_by_id
        and connector_status_by_id[connector_id].missing_credentials
    }
    return build_social_history_inventory_from_env(
        connector_status_by_id,
        missing_publish_access,
    )


@router.post(
    "/api/social/history-inventory/audit",
    response_model=SocialHistoryImportAudit,
)
def social_history_inventory_audit(
    payload: Any = SOCIAL_HISTORY_AUDIT_BODY,  # noqa: ANN401 - accepts arbitrary JSON.
) -> SocialHistoryImportAudit:
    return audit_social_history_metadata_payload(payload)
