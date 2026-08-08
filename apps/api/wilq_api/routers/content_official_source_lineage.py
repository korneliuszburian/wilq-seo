from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.planning.generated_proposal import with_explicit_content_service_selection
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionConflictResponse,
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionSaveResponse,
    ContentOfficialSourceLineageRebaseRequest,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.documents.official_source_lineage import (
    build_official_source_lineage_rebase_command,
)
from wilq.content.workflow.documents.official_source_lineage_store import (
    content_official_source_lineage_store,
)

ContentOfficialSourceLineageSnapshotLoader = Callable[
    [str], ContentWorkItemWorkflowSnapshotResponse
]


def register_content_official_source_lineage_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentOfficialSourceLineageSnapshotLoader,
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/official-source-lineage-rebase",
        response_model=ContentDraftRevisionSaveResponse,
        responses={409: {"model": ContentDraftRevisionConflictResponse}},
    )
    def content_work_item_official_source_lineage_rebase(
        work_item_id: str,
        revision_id: str,
        request: ContentOfficialSourceLineageRebaseRequest,
    ) -> ContentDraftRevisionSaveResponse | JSONResponse:
        snapshot = snapshot_loader(work_item_id)
        workspace = snapshot.revision_workspace
        base_revision = workspace.latest_revision
        if base_revision is None or base_revision.revision_id != revision_id:
            return _conflict(
                snapshot,
                "stale_revision",
                "Odśwież dokument i wybierz jego bieżącą rewizję.",
            )
        if base_revision.content_digest != request.expected_revision_digest:
            return _conflict(
                snapshot,
                "digest_mismatch",
                "Odśwież dokument przed uzupełnieniem źródeł urzędowych.",
            )
        if (
            base_revision.schema_version != "wilq_content_draft_revision_v2"
            or base_revision.official_source_references
            or workspace.status not in {"unreviewed", "deferred"}
            or not workspace.context_current
        ):
            return _conflict(
                snapshot,
                "official_source_lineage_unavailable",
                "Źródła można uzupełnić wyłącznie dla bieżącej, niezatwierdzonej "
                "rewizji bez zapisanej lineage.",
            )
        planning = snapshot.planning_workspace
        if planning is None or base_revision.service_card_id is None:
            return _conflict(
                snapshot,
                "official_source_lineage_unavailable",
                "Odśwież bieżący plan i wybór usługi przed uzupełnieniem źródeł urzędowych.",
            )
        planning_input_result = build_content_planning_input(
            with_explicit_content_service_selection(snapshot, base_revision.service_card_id),
            service_card_id=base_revision.service_card_id,
        )
        if planning_input_result.planning_input is None or planning_input_result.blockers:
            return _conflict(
                snapshot,
                "official_source_lineage_unavailable",
                "Bieżący plan nie ma kompletnego, bezpiecznego pokrycia źródeł urzędowych.",
            )
        try:
            command = build_official_source_lineage_rebase_command(
                base_revision=base_revision,
                planning_input=planning_input_result.planning_input,
                proposal=planning.proposal,
                requested_by=request.requested_by,
            )
        except ValueError:
            return _conflict(
                snapshot,
                "official_source_lineage_unavailable",
                "Bieżący plan nie odpowiada dokładnie rewizji lub nie ma kompletnej "
                "lineage źródeł urzędowych.",
            )
        expected_review_decision_id = (
            None
            if workspace.status == "unreviewed"
            else None if workspace.latest_review is None else workspace.latest_review.decision_id
        )
        result = content_official_source_lineage_store().append_rebase(
            command,
            expected_latest_review_decision_id=expected_review_decision_id,
        )
        if result.status == "conflict":
            return _conflict(
                snapshot_loader(work_item_id),
                result.conflict.code if result.conflict is not None else "stale_revision",
                "Stan review zmienił się w trakcie operacji. Odśwież dokument przed kolejną próbą.",
            )
        if result.revision is None:
            return _conflict(
                snapshot_loader(work_item_id),
                "stale_revision",
                "Nie zapisano rewizji źródeł urzędowych. Odśwież dokument przed kolejną próbą.",
            )
        refreshed_workspace = snapshot_loader(work_item_id).revision_workspace
        return ContentDraftRevisionSaveResponse(
            status=result.status,
            revision=result.revision,
            workspace=refreshed_workspace,
        )


def _conflict(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    code: ContentDraftRevisionPublicConflictCode,
    safe_next_step: str,
) -> JSONResponse:
    latest_revision = snapshot.revision_workspace.latest_revision
    return JSONResponse(
        status_code=409,
        content=ContentDraftRevisionConflictResponse(
            code=code,
            current_revision_id=(None if latest_revision is None else latest_revision.revision_id),
            current_digest=(None if latest_revision is None else latest_revision.content_digest),
            safe_next_step=safe_next_step,
        ).model_dump(mode="json"),
    )


__all__ = ["register_content_official_source_lineage_route"]
