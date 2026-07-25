from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.target_discovery import build_content_target_discovery
from wilq.content.workflow.target_mapping import (
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingConfirmationResult,
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
            preview = build_content_target_mapping_preview(
                work_item_id=work_item_id,
                revision_id=revision_id,
                revisions=store.list_draft_revisions(work_item_id),
                human_review=store.load_draft_revision_review(
                    work_item_id=work_item_id,
                    revision_id=revision_id,
                ),
                discovery=discovery,
            )
            if preview.target is not None and preview.binding_digest is not None:
                confirmation = store.load_target_mapping_confirmation(
                    work_item_id=work_item_id,
                    revision_id=revision_id,
                    target_contract_digest=preview.target.target_contract_digest,
                    binding_digest=preview.binding_digest,
                )
                return preview.model_copy(update={"confirmation": confirmation})
            return preview
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping/confirmation",
        response_model=ContentTargetMappingConfirmationResult,
    )
    def confirm_content_target_mapping(
        work_item_id: str,
        revision_id: str,
        command: ContentTargetMappingConfirmationCommand,
    ) -> ContentTargetMappingConfirmationResult:
        store = content_workflow_store()
        discovery = build_content_target_discovery(work_item_id)
        if discovery is None:
            raise HTTPException(
                status_code=404,
                detail="Nie znaleziono strony do sprawdzenia na dev.",
            )
        try:
            preview = build_content_target_mapping_preview(
                work_item_id=work_item_id,
                revision_id=revision_id,
                revisions=store.list_draft_revisions(work_item_id),
                human_review=store.load_draft_revision_review(
                    work_item_id=work_item_id,
                    revision_id=revision_id,
                ),
                discovery=discovery,
            )
            return store.record_target_mapping_confirmation(
                work_item_id=work_item_id,
                preview=preview,
                command=command,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error


__all__ = ["register_content_target_mapping_route"]
