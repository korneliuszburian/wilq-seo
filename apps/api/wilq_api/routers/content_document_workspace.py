from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from wilq.content.workflow.workspace.document_workspace import (
    ContentDocumentWorkspace,
    build_content_document_workspace,
)


def register_content_document_workspace_route(router: APIRouter) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/document-workspace",
        response_model=ContentDocumentWorkspace,
    )
    def content_document_workspace(work_item_id: str) -> ContentDocumentWorkspace:
        snapshot = snapshot_for_work_item_or_404(work_item_id)
        workspace = build_content_document_workspace(
            work_item_id,
            revision_context_current=snapshot.revision_workspace.context_current,
            item=snapshot.preflight.item,
        )
        if workspace is None:
            raise HTTPException(
                status_code=404, detail="Nie znaleziono istniejącej strony do odświeżenia."
            )
        return workspace


__all__ = ["register_content_document_workspace_route"]
