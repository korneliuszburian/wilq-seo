from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.target_discovery import build_content_target_discovery
from wilq.content.workflow.target_mapping import (
    ContentTargetMappingPreview,
    build_content_target_mapping_preview,
)


def register_content_target_mapping_route(router: APIRouter) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping",
        response_model=ContentTargetMappingPreview,
    )
    def content_target_mapping_preview(
        work_item_id: str,
        revision_id: str,
    ) -> ContentTargetMappingPreview:
        store = content_workflow_store()
        discovery = build_content_target_discovery(work_item_id)
        if discovery is None:
            raise HTTPException(
                status_code=404,
                detail="Nie znaleziono strony do sprawdzenia na dev.",
            )
        try:
            return build_content_target_mapping_preview(
                work_item_id=work_item_id,
                revision_id=revision_id,
                revisions=store.list_draft_revisions(work_item_id),
                human_review=store.load_draft_revision_review(
                    work_item_id=work_item_id,
                    revision_id=revision_id,
                ),
                discovery=discovery,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error


__all__ = ["register_content_target_mapping_route"]
