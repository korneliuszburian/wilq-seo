from __future__ import annotations

from fastapi import APIRouter

from wilq.content.workflow.selected_workspace import (
    ContentSelectedWorkspace,
    build_content_selected_workspace,
)


def register_content_selected_workspace_route(router: APIRouter) -> None:
    def content_selected_workspace(work_item_id: str) -> ContentSelectedWorkspace:
        return build_content_selected_workspace(work_item_id)

    router.add_api_route(
        "/api/content/work-items/{work_item_id}/selected-workspace",
        content_selected_workspace,
        methods=["GET"],
        response_model=ContentSelectedWorkspace,
    )


__all__ = ["register_content_selected_workspace_route"]
