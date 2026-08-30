"""Canonical API composition for the classified-refresh authority."""

from __future__ import annotations

from apps.api.wilq_api.routers.content_selected_snapshot import (
    selected_workspace_snapshot_for_work_item_or_404,
)
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.refresh_preparation import ContentRefreshPreparationAuthority
from wilq.content.workflow.store.store import content_workflow_store


def content_refresh_preparation_authority() -> ContentRefreshPreparationAuthority:
    return ContentRefreshPreparationAuthority(
        store=content_workflow_store(),
        snapshot_loader=_selected_refresh_snapshot,
        proposal_store=content_planning_proposal_store(),
    )


def _selected_refresh_snapshot(
    work_item_id: str,
    service_card_id: str | None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    return selected_workspace_snapshot_for_work_item_or_404(
        work_item_id,
        service_card_id_override=service_card_id,
    )


__all__ = ["content_refresh_preparation_authority"]
