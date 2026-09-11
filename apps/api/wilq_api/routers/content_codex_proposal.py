from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.codex.app_server import StdioCodexAppServerClient
from wilq.content.drafts.codex_section_proposal import (
    propose_content_section_revision,
)
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexSectionProposalRequest,
    ContentRevisionRepairProposalRequest,
    ContentRevisionRepairProposalResponse,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput, build_content_planning_input
from wilq.content.planning.generated_proposal import with_explicit_content_service_selection
from wilq.content.quality.semantic_review_store import content_semantic_review_store
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.store.store import content_workflow_store
from wilq.storage.local_state import local_state_store

ContentSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def content_codex_app_server_client() -> StdioCodexAppServerClient:
    return StdioCodexAppServerClient()


def register_content_revision_repair_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentSnapshotLoader,
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/repair-proposal",
        response_model=ContentRevisionRepairProposalResponse,
        responses={409: {"model": ContentRevisionRepairProposalResponse}},
    )
    def content_work_item_revision_repair_proposal(
        work_item_id: str,
        base_revision_id: str,
        request: ContentRevisionRepairProposalRequest,
    ) -> ContentRevisionRepairProposalResponse | JSONResponse:
        snapshot = snapshot_loader(work_item_id)
        base_revision = snapshot.revision_workspace.latest_revision
        # Refresh-bound editorial revisions must be evaluated against the
        # exact persisted planning binding, not the generic diagnostics
        # fallback (which has no editorial service selection).
        if base_revision is not None and base_revision.refresh_preparation_binding is not None:
            from apps.api.wilq_api.routers.content_workflow import (
                semantic_review_snapshot_for_work_item_or_404,
            )

            snapshot = semantic_review_snapshot_for_work_item_or_404(work_item_id)
            base_revision = snapshot.revision_workspace.latest_revision
        semantic_review = (
            None
            if base_revision is None
            else content_semantic_review_store().for_revision(
                work_item_id,
                base_revision.revision_id,
                base_revision.content_digest,
            )
        )
        planning_input = _current_planning_input(snapshot)
        result = propose_content_section_revision(
            snapshot=snapshot,
            base_revision_id=base_revision_id,
            request=ContentCodexSectionProposalRequest(
                expected_base_digest=request.expected_base_digest,
                selected_section_ids=request.selected_section_ids,
                selected_cta_ids=request.selected_cta_ids,
                requested_by=request.requested_by,
            ),
            client=content_codex_app_server_client(),
            workflow_store=content_workflow_store(),
            run_store=local_state_store(),
            semantic_review=semantic_review,
            planning_input=planning_input,
        )
        if result.status == "conflict":
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return ContentRevisionRepairProposalResponse.model_validate(result.model_dump())


def _current_planning_input(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentPlanningInput | None:
    workspace = getattr(snapshot, "planning_workspace", None)
    proposal = None if workspace is None else workspace.proposal
    if proposal is None:
        return None
    service_card_id = proposal.service_card_id
    if proposal.content_kind == "service" and service_card_id is None:
        return None
    result = build_content_planning_input(
        (
            with_explicit_content_service_selection(snapshot, service_card_id)
            if service_card_id is not None
            else snapshot
        ),
        service_card_id=service_card_id,
    )
    return None if result.blockers else result.planning_input


__all__ = ["register_content_revision_repair_route"]
