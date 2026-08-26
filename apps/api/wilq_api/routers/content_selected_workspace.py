from __future__ import annotations

from fastapi import APIRouter

from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from wilq.content.workflow.pipeline_steps.operator_steps import ContentWorkflowOperatorJourney
from wilq.content.workflow.workspace.selected_workspace import (
    ContentSelectedWorkspace,
    build_content_selected_workspace_with_context,
)


def register_content_selected_workspace_route(router: APIRouter) -> None:
    def content_selected_workspace(work_item_id: str) -> ContentSelectedWorkspace:
        snapshot = snapshot_for_work_item_or_404(
            work_item_id,
            resolve_planning_proposal=False,
        )
        return build_content_selected_workspace_with_context(
            work_item_id,
            operator_journey=ContentWorkflowOperatorJourney(
                current_step_id=snapshot.current_step_id,
                steps=snapshot.operator_steps,
            ),
            revision_context_current=snapshot.revision_workspace.context_current,
            item=snapshot.preflight.item,
        )

    router.add_api_route(
        "/api/content/work-items/{work_item_id}/selected-workspace",
        content_selected_workspace,
        methods=["GET"],
        response_model=ContentSelectedWorkspace,
    )


__all__ = ["register_content_selected_workspace_route"]
