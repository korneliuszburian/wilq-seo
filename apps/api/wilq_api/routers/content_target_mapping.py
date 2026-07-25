from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.actions.service import clear_action_list_cache
from wilq.content.workflow.dev_draft_action import (
    ContentTargetDraftActionCommand,
    create_content_target_draft_action,
    persist_content_target_draft_action,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.content.workflow.target_discovery import (
    ContentTargetDiscovery,
    build_content_target_discovery,
)
from wilq.content.workflow.target_mapping import (
    ContentTargetDraftPreview,
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingConfirmationResult,
    ContentTargetMappingPreview,
    build_content_target_draft_preview,
    build_content_target_mapping_preview,
)
from wilq.schemas import ActionObject


def register_content_target_mapping_route(router: APIRouter) -> None:
    router.add_api_route(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping",
        content_target_mapping_preview_endpoint,
        methods=["GET"],
        response_model=ContentTargetMappingPreview,
    )
    router.add_api_route(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping/draft-preview",
        content_target_draft_preview_endpoint,
        methods=["GET"],
        response_model=ContentTargetDraftPreview,
    )
    router.add_api_route(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping/confirmation",
        confirm_content_target_mapping_endpoint,
        methods=["POST"],
        response_model=ContentTargetMappingConfirmationResult,
    )
    router.add_api_route(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping/draft-action",
        create_content_target_draft_action_endpoint,
        methods=["POST"],
        response_model=ActionObject,
    )


def content_target_mapping_preview_endpoint(
    work_item_id: str,
    revision_id: str,
) -> ContentTargetMappingPreview:
    store = content_workflow_store()
    mapping, _ = _mapping_preview(work_item_id, revision_id, store)
    if mapping.target is None or mapping.binding_digest is None:
        return mapping
    confirmation = store.load_target_mapping_confirmation(
        work_item_id=work_item_id,
        revision_id=revision_id,
        target_contract_digest=mapping.target.target_contract_digest,
        binding_digest=mapping.binding_digest,
    )
    return mapping.model_copy(update={"confirmation": confirmation})


def content_target_draft_preview_endpoint(
    work_item_id: str,
    revision_id: str,
) -> ContentTargetDraftPreview:
    store = content_workflow_store()
    mapping, revisions = _mapping_preview(work_item_id, revision_id, store)
    confirmation = _mapping_confirmation(store, work_item_id, revision_id, mapping)
    try:
        return build_content_target_draft_preview(
            work_item_id=work_item_id,
            revision_id=revision_id,
            revisions=revisions,
            mapping_preview=mapping,
            confirmation=confirmation,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def confirm_content_target_mapping_endpoint(
    work_item_id: str,
    revision_id: str,
    command: ContentTargetMappingConfirmationCommand,
) -> ContentTargetMappingConfirmationResult:
    store = content_workflow_store()
    mapping, _ = _mapping_preview(work_item_id, revision_id, store)
    try:
        return store.record_target_mapping_confirmation(
            work_item_id=work_item_id,
            preview=mapping,
            command=command,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def create_content_target_draft_action_endpoint(
    work_item_id: str,
    revision_id: str,
    command: ContentTargetDraftActionCommand,
) -> ActionObject:
    preview = content_target_draft_preview_endpoint(work_item_id, revision_id)
    try:
        action = create_content_target_draft_action(preview, command)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    persisted = persist_content_target_draft_action(action)
    clear_action_list_cache()
    return persisted


def _mapping_preview(work_item_id: str, revision_id: str, store):
    discovery = _discovery_or_404(work_item_id)
    revisions = store.list_draft_revisions(work_item_id)
    try:
        return (
            build_content_target_mapping_preview(
                work_item_id=work_item_id,
                revision_id=revision_id,
                revisions=revisions,
                human_review=store.load_draft_revision_review(
                    work_item_id=work_item_id,
                    revision_id=revision_id,
                ),
                discovery=discovery,
            ),
            revisions,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _mapping_confirmation(store, work_item_id: str, revision_id: str, mapping):
    if mapping.target is None or mapping.binding_digest is None:
        return None
    return store.load_target_mapping_confirmation(
        work_item_id=work_item_id,
        revision_id=revision_id,
        target_contract_digest=mapping.target.target_contract_digest,
        binding_digest=mapping.binding_digest,
    )


def _discovery_or_404(work_item_id: str) -> ContentTargetDiscovery:
    discovery = build_content_target_discovery(work_item_id)
    if discovery is None:
        raise HTTPException(
            status_code=404,
            detail="Nie znaleziono strony do sprawdzenia na dev.",
        )
    return discovery


__all__ = ["register_content_target_mapping_route"]
