"""Exact local read seam for content delivery identity state."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityRecordResult,
)
from wilq.content.workflow.delivery_identity_recovery import (
    ContentDeliveryIdentityDriftRecovery,
    build_content_delivery_identity_drift_recovery,
)
from wilq.content.workflow.store.store import content_workflow_store

_PREFIX = "/api/content/delivery-identities"


async def read_content_delivery_identity(
    binding_id: str,
) -> ContentDeliveryIdentityRecordResult:
    result = await asyncio.to_thread(
        content_workflow_store().load_content_delivery_identity_record, binding_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="content_delivery_identity_not_found")
    return result


async def read_content_delivery_identity_drift_recovery(
    binding_id: str,
) -> ContentDeliveryIdentityDriftRecovery:
    store = content_workflow_store()
    record = await asyncio.to_thread(
        store.load_content_delivery_identity_record, binding_id
    )
    if record is None:
        raise HTTPException(status_code=404, detail="content_delivery_identity_not_found")
    classification = await asyncio.to_thread(
        store.load_content_delivery_classification_lookup, record.binding
    )
    return build_content_delivery_identity_drift_recovery(record.binding, classification)


def register_content_delivery_identity_routes(router: APIRouter) -> None:
    router.add_api_route(
        f"{_PREFIX}/{{binding_id}}",
        read_content_delivery_identity,
        methods=["GET"],
        response_model=ContentDeliveryIdentityRecordResult,
        tags=["content"],
    )
    router.add_api_route(
        f"{_PREFIX}/{{binding_id}}/drift-recovery",
        read_content_delivery_identity_drift_recovery,
        methods=["GET"],
        response_model=ContentDeliveryIdentityDriftRecovery,
        tags=["content"],
    )


__all__ = [
    "read_content_delivery_identity_drift_recovery",
    "register_content_delivery_identity_routes",
]
