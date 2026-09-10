from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionPublicConflictCode,
    ContentDraftRevisionWorkspace,
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
from wilq.content.workflow.documents.official_source_lineage_store import (
    content_official_source_lineage_store,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevision

ContentLineageCleanupSnapshotLoader = Callable[
    [str], ContentWorkItemWorkflowSnapshotResponse
]


@dataclass(frozen=True, slots=True)
class ContentLineageCleanupConflict:
    status: Literal["conflict"]
    code: ContentDraftRevisionPublicConflictCode
    snapshot: ContentWorkItemWorkflowSnapshotResponse
    safe_next_step: str


@dataclass(frozen=True, slots=True)
class ContentLineageCleanupCreated:
    status: Literal["created"]
    revision: ContentDraftRevision
    workspace: ContentDraftRevisionWorkspace


ContentLineageCleanupResult = ContentLineageCleanupConflict | ContentLineageCleanupCreated


def execute_content_lineage_cleanup(
    *,
    work_item_id: str,
    revision_id: str,
    request: ContentRevisionLineageCleanupRequest,
    snapshot_loader: ContentLineageCleanupSnapshotLoader,
) -> ContentLineageCleanupResult:
    """Append one safe source-lineage cleanup child or return its typed conflict."""

    snapshot = lineage_cleanup_snapshot(snapshot_loader, work_item_id)
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
    if not lineage_cleanup_available(snapshot, base_revision):
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

    with current_editor_draft_context_guard(
        lambda: current_lineage_cleanup_context(
            lineage_cleanup_snapshot(snapshot_loader, work_item_id),
            source_fact_id=request.source_fact_id,
            requested_by=request.requested_by,
        )
    ):
        result = content_official_source_lineage_store().append_cleanup(
            command,
            expected_latest_review_decision_id=expected_latest_review_decision_id(
                workspace
            ),
        )
    if result.status == "conflict":
        return _conflict(
            lineage_cleanup_snapshot(snapshot_loader, work_item_id),
            result.conflict.code if result.conflict is not None else "stale_revision",
            "Stan review lub rewizji zmienił się w trakcie operacji. "
            "Odśwież dokument przed kolejną próbą.",
        )
    if result.revision is None:
        return _conflict(
            lineage_cleanup_snapshot(snapshot_loader, work_item_id),
            "stale_revision",
            "Nie zapisano rewizji cleanupu. Odśwież dokument przed kolejną próbą.",
        )
    refreshed_workspace = lineage_cleanup_snapshot(
        snapshot_loader,
        work_item_id,
    ).revision_workspace
    return ContentLineageCleanupCreated(
        status="created",
        revision=result.revision,
        workspace=refreshed_workspace,
    )


def lineage_cleanup_snapshot(
    snapshot_loader: ContentLineageCleanupSnapshotLoader,
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


def lineage_cleanup_available(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    base_revision: ContentDraftRevision,
) -> bool:
    workspace = snapshot.revision_workspace
    return (
        base_revision.schema_version == "wilq_content_draft_revision_v2"
        and workspace.status in {"unreviewed", "needs_changes", "deferred"}
        and workspace.context_current
        and (workspace.status == "unreviewed" or workspace.latest_review is not None)
    )


def expected_latest_review_decision_id(
    workspace: ContentDraftRevisionWorkspace,
) -> str | None:
    if workspace.status == "unreviewed":
        return None
    if workspace.latest_review is None:
        raise ValueError("Reviewed lineage child requires an exact latest review.")
    return workspace.latest_review.decision_id


def current_lineage_cleanup_context(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    source_fact_id: str,
    requested_by: str,
) -> ContentDraftRevisionContext | None:
    base_revision = snapshot.revision_workspace.latest_revision
    if base_revision is None or not lineage_cleanup_available(snapshot, base_revision):
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
) -> ContentLineageCleanupConflict:
    return ContentLineageCleanupConflict(
        status="conflict",
        code=code,
        snapshot=snapshot,
        safe_next_step=safe_next_step,
    )


__all__ = [
    "ContentLineageCleanupConflict",
    "ContentLineageCleanupCreated",
    "ContentLineageCleanupResult",
    "ContentLineageCleanupSnapshotLoader",
    "current_lineage_cleanup_context",
    "execute_content_lineage_cleanup",
    "expected_latest_review_decision_id",
    "lineage_cleanup_available",
    "lineage_cleanup_snapshot",
]
