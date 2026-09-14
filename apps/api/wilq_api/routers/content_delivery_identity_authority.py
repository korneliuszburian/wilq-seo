"""Preview-only ActionObject entrypoint for receipt-bound delivery identity."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.delivery_identity_authority import (
    ContentDeliveryIdentityAuthorityCandidate,
    delivery_identity_authority_action_for_proposal,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.schemas import ActionObject


def register_content_delivery_identity_authority_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/delivery-identity-authorities/preview",
        content_delivery_identity_authority_preview_endpoint,
        methods=["POST"],
        response_model=ActionObject,
    )


def content_delivery_identity_authority_preview_endpoint(
    candidate: ContentDeliveryIdentityAuthorityCandidate,
) -> ActionObject:
    """Store only receipt IDs; the resulting action is rebuilt server-side."""

    try:
        store = content_workflow_store()
        proposal = store.record_content_delivery_identity_authority_proposal(candidate)
        return delivery_identity_authority_action_for_proposal(store, proposal)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
