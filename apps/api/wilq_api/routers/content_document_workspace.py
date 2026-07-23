from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.document_workspace import (
    ContentDocumentWorkspace,
    build_content_document_workspace,
)


def register_content_document_workspace_route(router: APIRouter) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/document-workspace",
        response_model=ContentDocumentWorkspace,
    )
    def content_document_workspace(work_item_id: str) -> ContentDocumentWorkspace:
        workspace = build_content_document_workspace(work_item_id)
        if workspace is None:
            raise HTTPException(
                status_code=404, detail="Nie znaleziono istniejącej strony do odświeżenia."
            )
        return workspace


__all__ = ["register_content_document_workspace_route"]
