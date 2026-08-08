from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from wilq.content.handoff.wordpress_execution import ContentWordPressDraftExecutionResult
from wilq.content.workflow.workspace.api import (
    build_content_wordpress_draft_activation_packet_response,
    build_content_wordpress_draft_write_readiness_response,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
    ContentWorkItemBrowserWorkflowSnapshotResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.store.store import content_workflow_store

ContentSnapshot = (
    ContentWorkItemBrowserWorkflowSnapshotResponse | ContentWorkItemWorkflowSnapshotResponse
)
ContentSnapshotLoader = Callable[[str], ContentSnapshot]
ContentDefaultSnapshotLoader = Callable[[], ContentSnapshot]


def register_content_legacy_wordpress_read_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentSnapshotLoader,
    default_snapshot_loader: ContentDefaultSnapshotLoader,
) -> None:
    """Keep compatibility reads separate from the document-first content journey."""

    @router.get(
        "/api/content/wordpress/draft-write-readiness",
        response_model=ContentWordPressDraftWriteReadinessResponse,
    )
    def content_wordpress_draft_write_readiness(
        action_id: str = "act_prepare_wordpress_draft_handoff",
    ) -> ContentWordPressDraftWriteReadinessResponse:
        return build_content_wordpress_draft_write_readiness_response(action_id=action_id)

    @router.get(
        "/api/content/wordpress/draft-activation-packet",
        response_model=ContentWordPressDraftActivationPacketResponse,
    )
    def content_wordpress_draft_activation_packet(
        work_item_id: str | None = None,
    ) -> ContentWordPressDraftActivationPacketResponse:
        snapshot = snapshot_loader(work_item_id) if work_item_id else default_snapshot_loader()
        if not isinstance(snapshot, ContentWorkItemWorkflowSnapshotResponse):
            raise RuntimeError("Legacy WordPress packet requires the full workflow snapshot.")
        return build_content_wordpress_draft_activation_packet_response(
            snapshot,
            latest_execution_result=_latest_exact_wordpress_execution(snapshot),
        )


def _latest_exact_wordpress_execution(
    snapshot: ContentSnapshot,
) -> ContentWordPressDraftExecutionResult | None:
    handoff = snapshot.wordpress_handoff.handoff_result.handoff
    binding = handoff.revision_binding if handoff is not None else None
    if handoff is None:
        return None
    if binding is None:
        return content_workflow_store().latest_wordpress_draft_execution(snapshot.preflight.item.id)
    return content_workflow_store().latest_wordpress_draft_execution(
        snapshot.preflight.item.id,
        handoff_id=handoff.id,
        revision_id=binding.revision_id,
        revision_digest=binding.content_digest,
    )


__all__ = ["register_content_legacy_wordpress_read_routes"]
