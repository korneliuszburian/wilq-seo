"""Explicit preview and dispatch for the local full-text ActionObject."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from apps.api.wilq_api.routers.content_initial_draft_refresh import (
    read_authorized_refresh_initial_draft_status,
)
from wilq.codex.app_server import CodexAppServerClientProtocol, StdioCodexAppServerClient
from wilq.content.drafts.full_draft_generation_v3 import (
    full_draft_generation_v3_action,
    full_draft_generation_v3_snapshot,
)
from wilq.content.drafts.full_draft_generation_v3_dispatch import dispatch_full_draft_generation_v3
from wilq.content.drafts.initial_draft_authority import (
    InitialDraftAuthorityIntent,
    InitialDraftAuthorityResolution,
    StatusRead,
    map_initial_draft_authority_response,
)
from wilq.content.drafts.initial_draft_queue import (
    ContentInitialDraftSnapshotLoader,
    InitialDraftExecutor,
)
from wilq.content.drafts.initial_draft_runtime_contract import initial_draft_timeout_seconds
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftResponse
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.workflow.refresh_preparation import ContentRefreshPreparationAuthority
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.storage.local_state import LocalStateStore, local_state_store


class FullDraftGenerationV3PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposal_id: str = Field(min_length=1)


def register_content_full_draft_generation_v3_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentInitialDraftSnapshotLoader,
    workflow_store_factory: Callable[[], ContentWorkflowStore] | None = None,
    proposal_store_factory: Callable[[], ContentPlanningProposalStore] | None = None,
    audit_store_factory: Callable[[], LocalStateStore] | None = None,
    client_factory: Callable[[], CodexAppServerClientProtocol] | None = None,
    executor: InitialDraftExecutor | None = None,
) -> None:
    make_store = workflow_store_factory or content_workflow_store
    make_run_store = audit_store_factory or local_state_store
    make_plan_store = proposal_store_factory or content_planning_proposal_store

    @router.post("/api/content/work-items/{work_item_id}/full-draft-generation-v3/preview")
    def preview(work_item_id: str, request: FullDraftGenerationV3PreviewRequest) -> dict[str, Any]:
        snapshot = snapshot_loader(work_item_id)
        planning = snapshot.planning_workspace
        if (
            planning is None
            or not planning.section_map_current
            or planning.proposal.proposal_id != request.proposal_id
            or snapshot.revision_workspace.latest_revision is not None
        ):
            raise HTTPException(409, "full_draft_v3_plan_changed")
        store = make_store()
        retained = make_plan_store().latest_for_planning_digest(
            work_item_id, planning.proposal.planning_digest
        )
        if retained != planning.proposal or retained.work_item_id != work_item_id:
            raise HTTPException(409, "full_draft_v3_proposal_mismatch")
        try:
            authority = full_draft_generation_v3_snapshot(planning.proposal, store=store)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        if store.record_full_draft_generation_v3_snapshot(authority) == "conflict":
            raise HTTPException(409, "full_draft_v3_snapshot_conflict")
        return {
            "action_id": authority.action_id,
            "action": full_draft_generation_v3_action(authority),
            "generation_performed": False,
            "model_enqueued": False,
        }

    @router.post(
        "/api/content/full-draft-generations-v3/{action_id}/dispatch",
        response_model=ContentInitialDraftResponse,
    )
    def dispatch(action_id: str) -> ContentInitialDraftResponse | JSONResponse:
        from apps.api.wilq_api.routers.content_initial_draft import _INITIAL_DRAFT_EXECUTOR

        outcome = dispatch_full_draft_generation_v3(
            action_id,
            workflow_store=make_store(),
            run_store=make_run_store(),
            snapshot_loader=snapshot_loader,
            executor=executor or _INITIAL_DRAFT_EXECUTOR,
            client_factory=client_factory
            or (lambda: StdioCodexAppServerClient(timeout_seconds=initial_draft_timeout_seconds())),
        )
        if outcome.status == "blocked":
            return JSONResponse(status_code=409, content=outcome.model_dump(mode="json"))
        return outcome


def read_initial_draft_status_with_authority(
    work_item_id: str,
    *,
    snapshot_loader: ContentInitialDraftSnapshotLoader | None = None,
    authority_resolver: Callable[
        [str, InitialDraftAuthorityIntent], InitialDraftAuthorityResolution
    ]
    | None = None,
    refresh_authority_factory: Callable[[], ContentRefreshPreparationAuthority] | None = None,
) -> ContentInitialDraftResponse:
    from apps.api.wilq_api.routers import content_initial_draft as legacy
    from wilq.content.drafts.full_draft_generation_v3_dispatch import (
        read_full_draft_generation_v3_status,
    )

    modern = read_full_draft_generation_v3_status(
        work_item_id, workflow_store=content_workflow_store(), run_store=local_state_store()
    )
    if modern is not None:
        return modern
    resolution = (authority_resolver or legacy._canonical_initial_draft_authority_resolver)(
        work_item_id,
        StatusRead(),
    )
    guarded = map_initial_draft_authority_response(resolution)
    if guarded is not None:
        classification_decision = getattr(resolution, "classification_decision", None)
        refresh_status_allowed = classification_decision == "refresh" or (
            classification_decision == "blocked"
            and tuple(getattr(resolution, "source_codes", ()))
            == ("current_content_binding_missing",)
        )
        if authority_resolver is None and refresh_status_allowed:
            refresh_status = read_authorized_refresh_initial_draft_status(
                work_item_id=work_item_id,
                refresh_authority=(
                    refresh_authority_factory or legacy._canonical_refresh_preparation_authority
                )(),
                proposal_store=content_planning_proposal_store(),
                workflow_store=content_workflow_store(),
                legacy_status_reader=lambda item_id, loader: (
                    legacy._read_legacy_initial_draft_status(
                        item_id,
                        snapshot_loader=loader,
                    )
                ),
            )
            if refresh_status is not None:
                return refresh_status
            if getattr(resolution, "classification_decision", None) == "refresh":
                return legacy._read_legacy_initial_draft_status(
                    work_item_id,
                    snapshot_loader=snapshot_loader,
                )
        return guarded
    return legacy._read_legacy_initial_draft_status(
        work_item_id,
        snapshot_loader=snapshot_loader,
    )
