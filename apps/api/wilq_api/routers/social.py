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
    SocialReuseReview,
    SocialReuseReviewRequest,
    SocialReuseReviewResponse,
    SocialReuseRevisionRequest,
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
        review=content_workflow_store().latest_social_reuse_review(proposal_id),
        next_step="Propozycja wymaga review człowieka; publikacja jest wyłączona.",
    )


@router.post(
    "/api/social/reuse-proposals/{proposal_id}/review",
    response_model=SocialReuseReviewResponse,
    responses={409: {"model": SocialReuseReviewResponse}},
)
def review_social_reuse_proposal(
    proposal_id: str,
    request: SocialReuseReviewRequest,
) -> SocialReuseReviewResponse | JSONResponse:
    store = content_workflow_store()
    proposal = store.get_social_reuse_proposal(proposal_id)
    if proposal is None:
        return _social_review_blocked(
            "social_reuse_proposal_not_found",
            "Utwórz propozycję na podstawie aktualnej rewizji treści.",
        )
    if request.expected_proposal_digest != proposal.proposal_digest:
        return _social_review_conflict(
            "stale_proposal",
            "Propozycja zmieniła się. Otwórz jej aktualną wersję przed review.",
        )
    state = store.load_draft_revision_state(proposal.work_item_id)
    current = state.latest_revision
    if current is None or current.content_digest != proposal.source_revision_digest:
        return _social_review_conflict(
            "source_revision_changed",
            "Rewizja treści zmieniła się. Przygotuj nową propozycję social.",
        )
    inventory = _current_social_history_inventory()
    if (
        inventory.status != "review_ready"
        or social_history_inventory_digest(inventory)
        != proposal.duplicate_risk_inventory_digest
    ):
        return _social_review_conflict(
            "social_history_changed",
            "Historia social zmieniła się albo wymaga ponownego review.",
        )
    latest = store.latest_social_reuse_review(proposal_id)
    if (
        latest is not None
        and latest.proposal_digest == proposal.proposal_digest
        and latest.reviewed_by == request.reviewed_by
        and latest.decision == request.decision
        and latest.notes == request.notes
        and latest.checked_items == request.checked_items
        and latest.evidence_ids == request.evidence_ids
    ):
        return SocialReuseReviewResponse(
            status="idempotent",
            proposal=proposal,
            review=latest,
            next_step=_social_review_next_step(latest.decision),
        )
    review = SocialReuseReview(
        review_id=(
            f"social_review_{proposal_id}_"
            f"{1 if latest is None else latest.review_number + 1}"
        ),
        proposal_id=proposal_id,
        proposal_digest=proposal.proposal_digest,
        review_number=1 if latest is None else latest.review_number + 1,
        decision=request.decision,
        reviewed_by=request.reviewed_by,
        notes=request.notes,
        checked_items=request.checked_items,
        evidence_ids=request.evidence_ids,
        created_at=utc_now(),
    )
    persisted = store.save_social_reuse_review(review)
    return SocialReuseReviewResponse(
        status="recorded",
        proposal=proposal,
        review=persisted,
        next_step=_social_review_next_step(persisted.decision),
    )


@router.post(
    "/api/social/reuse-proposals/{proposal_id}/revise",
    response_model=SocialReuseProposalResponse,
    responses={409: {"model": SocialReuseProposalResponse}},
)
def revise_social_reuse_proposal(
    proposal_id: str,
    request: SocialReuseRevisionRequest,
) -> SocialReuseProposalResponse | JSONResponse:
    store = content_workflow_store()
    parent = store.get_social_reuse_proposal(proposal_id)
    if parent is None:
        return _social_reuse_blocked(
            "social_reuse_proposal_not_found",
            "Utwórz propozycję na podstawie aktualnej rewizji treści.",
        )
    if request.expected_proposal_digest != parent.proposal_digest:
        return _social_reuse_conflict(
            "stale_proposal",
            "Propozycja zmieniła się. Otwórz jej aktualną wersję przed poprawą.",
        )
    state = store.load_draft_revision_state(parent.work_item_id)
    current = state.latest_revision
    if current is None or current.content_digest != parent.source_revision_digest:
        return _social_reuse_conflict(
            "source_revision_changed",
            "Rewizja treści zmieniła się. Przygotuj propozycję od nowa.",
        )
    inventory = _current_social_history_inventory()
    if (
        inventory.status != "review_ready"
        or social_history_inventory_digest(inventory)
        != parent.duplicate_risk_inventory_digest
    ):
        return _social_reuse_conflict(
            "social_history_changed",
            "Historia social zmieniła się albo wymaga ponownego review.",
        )
    number = store.next_social_reuse_child_number(proposal_id)
    revised = build_social_reuse_proposal(
        SocialReuseProposalRequest(
            work_item_id=parent.work_item_id,
            expected_revision_id=parent.source_revision_id,
            expected_revision_digest=parent.source_revision_digest,
            platform=parent.platform,
            audience=request.audience,
            angle=request.angle,
            body=request.body,
            claim_ids=request.claim_ids,
            measurement_hypothesis=request.measurement_hypothesis,
        ),
        current,
        inventory,
        now=utc_now(),
        parent_proposal_id=proposal_id,
        proposal_number=number,
    )
    persisted = store.save_social_reuse_child_proposal(revised)
    return SocialReuseProposalResponse(
        status="created",
        proposal=persisted,
        next_step=(
            "Nowa propozycja wymaga osobnego review człowieka; "
            "poprzednia pozostaje niezmieniona."
        ),
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


def _social_review_blocked(blocker: str, next_step: str) -> JSONResponse:
    payload = SocialReuseReviewResponse(
        status="blocked",
        blocker=blocker,
        next_step=next_step,
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


def _social_review_conflict(blocker: str, next_step: str) -> JSONResponse:
    payload = SocialReuseReviewResponse(
        status="stale",
        blocker=blocker,
        next_step=next_step,
    )
    return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))


def _social_review_next_step(decision: str) -> str:
    if decision == "approved":
        return (
            "Propozycja ma decyzję człowieka; publikacja nadal wymaga osobnej "
            "akcji i pozostaje wyłączona."
        )
    if decision == "needs_changes":
        return "Przygotuj nową propozycję na podstawie uwag; ta rewizja nie jest zatwierdzona."
    return "Nie używaj tej propozycji; wróć do aktualnej rewizji treści."


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
