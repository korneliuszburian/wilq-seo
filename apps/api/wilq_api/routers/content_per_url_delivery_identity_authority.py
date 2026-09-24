"""Preview and readback for audited per-URL delivery identity receipts."""

from __future__ import annotations

from fastapi import APIRouter

from wilq.content.workflow.per_url_delivery_identity_authority import (
    PerUrlDeliveryIdentityCandidate,
    PerUrlDeliveryIdentityPreviewResponse,
    PerUrlDeliveryIdentityProjection,
    prepare_per_url_delivery_identity_preview,
    read_per_url_delivery_identity_authority,
)
from wilq.content.workflow.store.store import content_workflow_store


def register_content_per_url_delivery_identity_authority_routes(
    router: APIRouter,
) -> None:
    router.add_api_route(
        "/api/content/per-url-delivery-identity-authorities/preview",
        content_per_url_delivery_identity_preview_endpoint,
        methods=["POST"],
        response_model=PerUrlDeliveryIdentityPreviewResponse,
        tags=["content"],
    )
    router.add_api_route(
        "/api/content/per-url-delivery-identity-authorities/{action_id}",
        content_per_url_delivery_identity_read_endpoint,
        methods=["GET"],
        response_model=PerUrlDeliveryIdentityProjection,
        tags=["content"],
    )


def content_per_url_delivery_identity_preview_endpoint(
    candidate: PerUrlDeliveryIdentityCandidate,
) -> PerUrlDeliveryIdentityPreviewResponse:
    return prepare_per_url_delivery_identity_preview(content_workflow_store(), candidate)


def content_per_url_delivery_identity_read_endpoint(
    action_id: str,
) -> PerUrlDeliveryIdentityProjection:
    return read_per_url_delivery_identity_authority(
        content_workflow_store(), action_id=action_id
    )


__all__ = ["register_content_per_url_delivery_identity_authority_routes"]
