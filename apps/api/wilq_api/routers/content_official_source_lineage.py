from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputBuildResult,
    build_content_planning_input,
)
from wilq.content.planning.generated_proposal import with_explicit_content_service_selection
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionConflictResponse,
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionSaveResponse,
    ContentDraftRevisionWorkspace,
    ContentOfficialSourceLineageRebaseRequest,
    ContentRevisionLineageCleanupRequest,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.documents.codex_revision_commit import (
    ContentDraftRevisionContext,
    current_editor_draft_context_guard,
)
from wilq.content.workflow.documents.lineage_cleanup import (
    LineageCleanupBuildError,
    build_lineage_cleanup_command,
)
from wilq.content.workflow.documents.official_source_lineage import (
    build_official_source_lineage_rebase_command,
)
from wilq.content.workflow.documents.official_source_lineage_store import (
    content_official_source_lineage_store,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    content_draft_package_digest,
)

ContentOfficialSourceLineageSnapshotLoader = Callable[
    [str], ContentWorkItemWorkflowSnapshotResponse
]


def register_content_official_source_lineage_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentOfficialSourceLineageSnapshotLoader,
) -> None:
    _register_content_lineage_cleanup_route(router, snapshot_loader=snapshot_loader)

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
        if not _lineage_rebase_available(snapshot, base_revision):
            return _conflict(
                snapshot,
                "official_source_lineage_unavailable",
                "Źródła można uzupełnić wyłącznie dla bieżącej, niezatwierdzonej "
                "rewizji bez zapisanej lineage.",
            )
        planning = snapshot.planning_workspace
        if planning is None:
            return _conflict(
                snapshot,
                "official_source_lineage_unavailable",
                "Odśwież bieżący plan i wybór usługi przed uzupełnieniem źródeł urzędowych.",
            )
        planning_input_result = _planning_input_for_lineage_rebase(snapshot, base_revision)
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
        expected_review_decision_id = _latest_review_decision_id(workspace)
        with current_editor_draft_context_guard(
            lambda: _current_lineage_rebase_context(
                snapshot_loader(work_item_id),
                requested_by=request.requested_by,
            )
        ):
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


def _register_content_lineage_cleanup_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentOfficialSourceLineageSnapshotLoader,
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/lineage-cleanup",
        response_model=ContentDraftRevisionSaveResponse,
        responses={409: {"model": ContentDraftRevisionConflictResponse}},
    )
    def content_revision_lineage_cleanup(
        work_item_id: str,
        revision_id: str,
        request: ContentRevisionLineageCleanupRequest,
    ) -> ContentDraftRevisionSaveResponse | JSONResponse:
        snapshot = _lineage_cleanup_snapshot(snapshot_loader, work_item_id)
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
                "Odśwież dokument przed usunięciem nieaktualnej lineage.",
            )
        if not _lineage_cleanup_available(snapshot, base_revision):
            return _conflict(
                snapshot,
                "lineage_cleanup_unavailable",
                "Cleanup jest dostępny tylko dla bieżącej, edytowalnej rewizji v2 "
                "z aktualnym kontekstem.",
            )
        try:
            command = build_lineage_cleanup_command(
                base_revision=base_revision,
                source_fact_id=request.source_fact_id,
                requested_by=request.requested_by,
            )
        except LineageCleanupBuildError as error:
            return _conflict(
                snapshot,
                error.code,
                "Sprawdź bieżącą lineage źródła przed ponowną próbą.",
            )
        except ValueError:
            return _conflict(
                snapshot,
                "lineage_cleanup_unavailable",
                "Bieżąca lineage nie pozwala na bezpieczny cleanup.",
            )
        expected_review_decision_id = _latest_review_decision_id(workspace)
        with current_editor_draft_context_guard(
            lambda: _current_lineage_cleanup_context(
                _lineage_cleanup_snapshot(snapshot_loader, work_item_id),
                source_fact_id=request.source_fact_id,
                requested_by=request.requested_by,
            )
        ):
            result = content_official_source_lineage_store().append_cleanup(
                command,
                expected_latest_review_decision_id=expected_review_decision_id,
            )
        if result.status == "conflict":
            return _conflict(
                _lineage_cleanup_snapshot(snapshot_loader, work_item_id),
                result.conflict.code if result.conflict is not None else "stale_revision",
                "Stan review lub rewizji zmienił się w trakcie operacji. "
                "Odśwież dokument przed kolejną próbą.",
            )
        if result.revision is None:
            return _conflict(
                _lineage_cleanup_snapshot(snapshot_loader, work_item_id),
                "stale_revision",
                "Nie zapisano rewizji cleanupu. Odśwież dokument przed kolejną próbą.",
            )
        refreshed_workspace = _lineage_cleanup_snapshot(
            snapshot_loader,
            work_item_id,
        ).revision_workspace
        return ContentDraftRevisionSaveResponse(
            status=result.status,
            revision=result.revision,
            workspace=refreshed_workspace,
        )


def _lineage_cleanup_snapshot(
    snapshot_loader: ContentOfficialSourceLineageSnapshotLoader,
    work_item_id: str,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Resolve refresh-bound cleanup against its persisted planning binding."""

    snapshot = snapshot_loader(work_item_id)
    latest_revision = snapshot.revision_workspace.latest_revision
    if latest_revision is None or latest_revision.refresh_preparation_binding is None:
        return snapshot
    from apps.api.wilq_api.routers.content_workflow import (
        semantic_review_snapshot_for_work_item_or_404,
    )

    return semantic_review_snapshot_for_work_item_or_404(work_item_id)


def _planning_input_for_lineage_rebase(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    base_revision: ContentDraftRevision,
) -> ContentPlanningInputBuildResult:
    planning_snapshot = (
        with_explicit_content_service_selection(snapshot, base_revision.service_card_id)
        if base_revision.content_kind == "service" and base_revision.service_card_id is not None
        else snapshot
    )
    return build_content_planning_input(
        planning_snapshot,
        service_card_id=base_revision.service_card_id,
    )


def _lineage_rebase_context_allowed(
    *,
    context_current: bool,
    base_revision: ContentDraftRevision,
    draft_package: ContentDraftPackage | None,
) -> bool:
    return context_current or (
        draft_package is not None
        and content_draft_package_digest(draft_package) == base_revision.draft_package_digest
    )


def _lineage_rebase_available(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    base_revision: ContentDraftRevision,
) -> bool:
    workspace = snapshot.revision_workspace
    return (
        base_revision.schema_version == "wilq_content_draft_revision_v2"
        and workspace.status in {"unreviewed", "deferred"}
        and _lineage_rebase_context_allowed(
            context_current=workspace.context_current,
            base_revision=base_revision,
            draft_package=snapshot.draft_package.draft_package_result.draft_package,
        )
    )


def _lineage_cleanup_available(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    base_revision: ContentDraftRevision,
) -> bool:
    workspace = snapshot.revision_workspace
    return (
        base_revision.schema_version == "wilq_content_draft_revision_v2"
        and workspace.status in {"unreviewed", "needs_changes", "deferred"}
        and workspace.context_current
        and (
            workspace.status == "unreviewed"
            or workspace.latest_review is not None
        )
    )


def _latest_review_decision_id(workspace: ContentDraftRevisionWorkspace) -> str | None:
    if workspace.status == "unreviewed":
        return None
    if workspace.latest_review is None:
        raise ValueError("Reviewed lineage cleanup requires an exact latest review.")
    return workspace.latest_review.decision_id


def _current_lineage_rebase_context(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    requested_by: str,
) -> ContentDraftRevisionContext | None:
    base_revision = snapshot.revision_workspace.latest_revision
    planning = snapshot.planning_workspace
    if (
        base_revision is None
        or planning is None
        or not _lineage_rebase_available(snapshot, base_revision)
    ):
        return None
    planning_input_result = _planning_input_for_lineage_rebase(snapshot, base_revision)
    if planning_input_result.planning_input is None or planning_input_result.blockers:
        return None
    try:
        command = build_official_source_lineage_rebase_command(
            base_revision=base_revision,
            planning_input=planning_input_result.planning_input,
            proposal=planning.proposal,
            requested_by=requested_by,
        )
    except ValueError:
        return None
    return ContentDraftRevisionContext.from_command(command)


def _current_lineage_cleanup_context(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    source_fact_id: str,
    requested_by: str,
) -> ContentDraftRevisionContext | None:
    base_revision = snapshot.revision_workspace.latest_revision
    if base_revision is None or not _lineage_cleanup_available(snapshot, base_revision):
        return None
    try:
        command = build_lineage_cleanup_command(
            base_revision=base_revision,
            source_fact_id=source_fact_id,
            requested_by=requested_by,
        )
    except ValueError:
        return None
    return ContentDraftRevisionContext.from_command(command)


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
