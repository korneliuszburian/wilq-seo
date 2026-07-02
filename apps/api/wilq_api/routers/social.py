from __future__ import annotations

from fastapi import APIRouter

from wilq.connectors.registry import list_connector_statuses
from wilq.social.history import SocialHistoryInventory, build_social_history_inventory

router = APIRouter()


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
    return build_social_history_inventory(
        connector_status_by_id,
        missing_publish_access,
    )
