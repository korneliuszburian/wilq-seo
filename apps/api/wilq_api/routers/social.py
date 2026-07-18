from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from wilq.connectors.registry import list_connector_statuses
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas.core import utc_now
from wilq.social.history import (
    SocialHistoryImportAudit,
    SocialHistoryInventory,
    audit_social_history_metadata_payload,
    build_social_history_inventory_from_env,
)
from wilq.social.reuse import (
    SocialReuseProposalRequest,
    SocialReuseProposalResponse,
    build_social_reuse_proposal,
    social_history_inventory_digest,
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


@router.post(
    "/api/social/reuse-proposals",
    response_model=SocialReuseProposalResponse,
    responses={409: {"model": SocialReuseProposalResponse}},
)
def create_social_reuse_proposal(
    request: SocialReuseProposalRequest,
) -> SocialReuseProposalResponse | JSONResponse:
    state = content_workflow_store().load_draft_revision_state(request.work_item_id)
    revision = state.latest_revision
    if revision is None:
        return _social_reuse_blocked(
            "content_revision_missing",
            "Najpierw przygotuj pełną rewizję treści dla wybranej strony.",
        )
    if (
        revision.revision_id != request.expected_revision_id
        or revision.content_digest != request.expected_revision_digest
    ):
        return _social_reuse_conflict(
            "stale_revision",
            "Treść zmieniła się. Odśwież aktualną rewizję przed przygotowaniem propozycji social.",
        )
    if state.status != "approved":
        return _social_reuse_blocked(
            "content_revision_not_approved",
            "Propozycja social wymaga zatwierdzonej rewizji treści.",
        )
    inventory = _current_social_history_inventory()
    if inventory.status != "review_ready":
        return _social_reuse_blocked(
            "social_history_not_reviewed",
            inventory.operator_next_step,
        )
    try:
        proposal = build_social_reuse_proposal(
            request,
            revision,
            inventory,
            now=utc_now(),
        )
    except ValueError as error:
        return _social_reuse_blocked("unsupported_claim_lineage", str(error))
    persisted = content_workflow_store().save_social_reuse_proposal(proposal)
    return SocialReuseProposalResponse(
        status="created",
        proposal=persisted,
        next_step="Przejrzyj propozycję i zatwierdź ją osobno; publikacja pozostaje wyłączona.",
    )


@router.get(
    "/api/social/reuse-proposals/{proposal_id}",
    response_model=SocialReuseProposalResponse,
)
def get_social_reuse_proposal(proposal_id: str) -> SocialReuseProposalResponse:
    proposal = content_workflow_store().get_social_reuse_proposal(proposal_id)
    if proposal is None:
        return SocialReuseProposalResponse(
            status="blocked",
            blocker="social_reuse_proposal_not_found",
            next_step="Utwórz propozycję na podstawie aktualnej rewizji treści.",
        )
    state = content_workflow_store().load_draft_revision_state(proposal.work_item_id)
    current = state.latest_revision
    if current is None or current.content_digest != proposal.source_revision_digest:
        return SocialReuseProposalResponse(
            status="stale",
            blocker="source_revision_changed",
            next_step="Przygotuj nową propozycję dla aktualnej rewizji treści.",
        )
    inventory = _current_social_history_inventory()
    if (
        inventory.status != "review_ready"
        or social_history_inventory_digest(inventory)
        != proposal.duplicate_risk_inventory_digest
    ):
        return SocialReuseProposalResponse(
            status="stale",
            blocker="social_history_changed",
            next_step=(
                "Historia social zmieniła się albo wymaga ponownego review; "
                "przygotuj nową propozycję."
            ),
        )
    return SocialReuseProposalResponse(
        status="created",
        proposal=proposal,
        next_step="Propozycja wymaga review człowieka; publikacja jest wyłączona.",
    )


def _social_reuse_blocked(blocker: str, next_step: str) -> JSONResponse:
    payload = SocialReuseProposalResponse(
        status="blocked",
        blocker=blocker,
        next_step=next_step,
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


def _social_reuse_conflict(blocker: str, next_step: str) -> JSONResponse:
    payload = SocialReuseProposalResponse(
        status="stale",
        blocker=blocker,
        next_step=next_step,
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


def _current_social_history_inventory() -> SocialHistoryInventory:
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
