"""Public read-only current page identity backed by a reviewed KEEP receipt."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers import content_current_page_evidence as current_page_evidence_router
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.current_page_identity_v2 import (
    CurrentPageIdentityV2Response,
)
from wilq.content.workflow.current_page_identity_v2 import (
    resolve_current_page_identity_v2 as resolve_current_page_identity_v2_domain,
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
    """API compatibility wrapper around the domain-owned current identity resolver."""
    return resolve_current_page_identity_v2_domain(work_item_id, store=store, evidence=evidence)


def _read_current_page_evidence(work_item_id: str) -> CurrentPageEvidenceResponse:
    return current_page_evidence_router.read_current_page_evidence(work_item_id=work_item_id)


__all__ = [
    "register_content_current_page_identity_v2_route",
    "resolve_current_page_identity_v2",
]
