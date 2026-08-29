from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.actions.service import clear_action_list_cache
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.content.workflow.target.dev_draft_action import (
    ContentTargetDraftActionCommand,
    create_content_target_draft_action,
    persist_content_target_draft_action,
)
from wilq.content.workflow.target.target_discovery import (
    ContentTargetDiscovery,
    build_content_target_discovery,
)
from wilq.content.workflow.target.target_mapping import (
    ContentTargetDraftPreview,
    ContentTargetMappingConfirmation,
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingConfirmationResult,
    ContentTargetMappingPreview,
    build_content_target_draft_preview,
    build_content_target_mapping_preview,
)
from wilq.content.workflow.target.target_mapping_persistence import (
    ContentTargetMappingDraftState,
    build_legacy_target_mapping_draft_preview,
    build_persisted_target_mapping_preview,
    confirmation_for_live_target_mapping,
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
    state = _persisted_draft_state(store, work_item_id, revision_id)
    if state is not None and state.status == "snapshot_available":
        return _persisted_mapping_preview(store, state)
    mapping, _ = _live_mapping_preview(work_item_id, revision_id, store)
    if mapping.target is None or mapping.binding_digest is None:
        return mapping
    confirmation = _mapping_confirmation(store, work_item_id, revision_id, mapping)
    return mapping.model_copy(update={"confirmation": confirmation})


def content_target_draft_preview_endpoint(
    work_item_id: str,
    revision_id: str,
) -> ContentTargetDraftPreview:
    store = content_workflow_store()
    state = _persisted_draft_state(store, work_item_id, revision_id)
    if state is not None:
        if state.status == "legacy_confirmation":
            return build_legacy_target_mapping_draft_preview(state)
        revisions = store.list_draft_revisions(work_item_id)
        mapping = _persisted_mapping_preview(store, state, revisions=revisions)
        return _draft_preview_from_mapping(
            work_item_id=work_item_id,
            revision_id=revision_id,
            revisions=revisions,
            mapping=mapping,
            confirmation=(
                state.confirmation if mapping.status == "ready_for_human_mapping" else None
            ),
        )
    return _live_content_target_draft_preview(work_item_id, revision_id, store=store)


_PUBLIC_DRAFT_PREVIEW_ENDPOINT = content_target_draft_preview_endpoint


def confirm_content_target_mapping_endpoint(
    work_item_id: str,
    revision_id: str,
    command: ContentTargetMappingConfirmationCommand,
) -> ContentTargetMappingConfirmationResult:
    store = content_workflow_store()
    mapping, _ = _live_mapping_preview(work_item_id, revision_id, store)
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
    preview = _live_content_target_draft_preview(work_item_id, revision_id)
    try:
        action = create_content_target_draft_action(preview, command)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    persisted = persist_content_target_draft_action(action)
    clear_action_list_cache()
    return persisted


def _live_content_target_draft_preview(
    work_item_id: str,
    revision_id: str,
    *,
    store: ContentWorkflowStore | None = None,
) -> ContentTargetDraftPreview:
    if (
        store is None
        and content_target_draft_preview_endpoint is not _PUBLIC_DRAFT_PREVIEW_ENDPOINT
    ):
        # Preserve the established route-level adapter seam used by focused
        # tests. The production endpoint identity always takes the live path.
        return content_target_draft_preview_endpoint(work_item_id, revision_id)
    active_store = content_workflow_store() if store is None else store
    mapping, revisions = _live_mapping_preview(work_item_id, revision_id, active_store)
    return _draft_preview_from_mapping(
        work_item_id=work_item_id,
        revision_id=revision_id,
        revisions=revisions,
        mapping=mapping,
        confirmation=_mapping_confirmation(
            active_store,
            work_item_id,
            revision_id,
            mapping,
        ),
    )


def _draft_preview_from_mapping(
    *,
    work_item_id: str,
    revision_id: str,
    revisions: list[ContentDraftRevision],
    mapping: ContentTargetMappingPreview,
    confirmation: ContentTargetMappingConfirmation | None,
) -> ContentTargetDraftPreview:
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


def _live_mapping_preview(
    work_item_id: str,
    revision_id: str,
    store: ContentWorkflowStore,
) -> tuple[ContentTargetMappingPreview, list[ContentDraftRevision]]:
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


def _persisted_draft_state(
    store: ContentWorkflowStore,
    work_item_id: str,
    revision_id: str,
) -> ContentTargetMappingDraftState | None:
    if not isinstance(store, ContentWorkflowStore):
        return None
    return store.load_target_mapping_draft_state(
        work_item_id=work_item_id,
        revision_id=revision_id,
    )


def _persisted_mapping_preview(
    store: ContentWorkflowStore,
    state: ContentTargetMappingDraftState,
    *,
    revisions: list[ContentDraftRevision] | None = None,
) -> ContentTargetMappingPreview:
    local_revisions = (
        store.list_draft_revisions(state.confirmation.work_item_id)
        if revisions is None
        else revisions
    )
    return build_persisted_target_mapping_preview(
        state=state,
        revisions=local_revisions,
        human_review=store.load_draft_revision_review(
            work_item_id=state.confirmation.work_item_id,
            revision_id=state.confirmation.revision.revision_id,
        ),
    )


def _mapping_confirmation(
    store: ContentWorkflowStore,
    work_item_id: str,
    revision_id: str,
    mapping: ContentTargetMappingPreview,
) -> ContentTargetMappingConfirmation | None:
    if mapping.target is None or mapping.binding_digest is None:
        return None
    if isinstance(store, ContentWorkflowStore):
        return confirmation_for_live_target_mapping(
            state=store.load_target_mapping_draft_state(
                work_item_id=work_item_id,
                revision_id=revision_id,
            ),
            work_item_id=work_item_id,
            revision_id=revision_id,
            mapping=mapping,
        )
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
