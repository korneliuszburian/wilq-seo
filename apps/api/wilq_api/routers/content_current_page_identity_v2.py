"""Public read-only current page identity backed by a reviewed KEEP receipt."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers import content_current_page_evidence as current_page_evidence_router
from wilq.content.workflow.current_page_disposition_v2 import (
    build_current_page_disposition_v2_proposal,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v2 import (
    CurrentPageIdentityV2Response,
    project_current_page_identity_v2,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store

StoreFactory = Callable[[], ContentWorkflowStore]
EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]


def register_content_current_page_identity_v2_route(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
) -> None:
    make_store = store_factory or (lambda: content_workflow_store())
    load_evidence = evidence_loader or _read_current_page_evidence

    @router.get(
        "/api/content/work-items/{work_item_id}/current-identity",
        response_model=CurrentPageIdentityV2Response,
    )
    def read_current_page_identity_v2(
        work_item_id: str,
    ) -> CurrentPageIdentityV2Response:
        return resolve_current_page_identity_v2(
            work_item_id,
            store=make_store(),
            evidence=load_evidence(work_item_id),
        )


def resolve_current_page_identity_v2(
    work_item_id: str,
    *,
    store: ContentWorkflowStore,
    evidence: CurrentPageEvidenceResponse,
) -> CurrentPageIdentityV2Response:
    """Resolve the exact current identity for reuse by read-only consumers."""

    latest_receipt = store.load_latest_current_page_disposition_v2_receipt_for_work_item(
        work_item_id
    )
    pending_action_id = None
    if evidence.status == "reviewed_material_current":
        proposal = build_current_page_disposition_v2_proposal(evidence)
        existing = store.load_current_page_disposition_v2_proposal(proposal.proposal_id)
        if (
            existing is not None
            and existing.proposal_id == proposal.proposal_id
            and existing.proposal_digest == proposal.proposal_digest
            and existing.snapshot.work_item_id == proposal.snapshot.work_item_id
            and existing.snapshot.normalized_page_url == proposal.snapshot.normalized_page_url
            and existing.snapshot.canonical_path == proposal.snapshot.canonical_path
            and existing.snapshot.material_meaning_digest
            == proposal.snapshot.material_meaning_digest
        ):
            pending_action_id = existing.proposal_id
    return project_current_page_identity_v2(
        evidence=evidence,
        latest_receipt=latest_receipt,
        pending_action_id=pending_action_id,
    )


def _read_current_page_evidence(work_item_id: str) -> CurrentPageEvidenceResponse:
    return current_page_evidence_router.read_current_page_evidence(work_item_id=work_item_id)


__all__ = [
    "register_content_current_page_identity_v2_route",
    "resolve_current_page_identity_v2",
]
