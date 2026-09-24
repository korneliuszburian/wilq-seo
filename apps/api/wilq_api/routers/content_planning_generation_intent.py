"""Public typed preview/read boundary for local generation intent actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.planning.generation_intent import (
    PlanningGenerationIntentBlocked,
    PlanningGenerationIntentPreviewCommand,
    PlanningGenerationIntentSnapshot,
    load_planning_generation_intent_action,
    planning_generation_intent_action,
    prepare_planning_generation_intent_action,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.research_packet_v2_preview import ResearchPacketV2Preview
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import ActionObject

SnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]
StoreFactory = Callable[[], ContentWorkflowStore]
PreviewLoader = Callable[[str], ResearchPacketV2Preview]


class PlanningGenerationIntentPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_kind: Literal["service", "editorial"] = "service"
    service_card_id: str | None = Field(default=None, min_length=1, max_length=240)
    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_raw_planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_projected_planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanningGenerationIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["planning_generation_intent"] = "planning_generation_intent"
    status: Literal["preview_ready"] = "preview_ready"
    action_id: str
    action: ActionObject
    snapshot: PlanningGenerationIntentSnapshot
    generation_performed: Literal[False] = False
    model_enqueued: Literal[False] = False
    external_write_attempted: Literal[False] = False


class PlanningGenerationIntentBlockedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["planning_generation_intent"] = "planning_generation_intent"
    status: Literal["blocked"] = "blocked"
    work_item_id: str = Field(min_length=1)
    blocker_code: str = Field(min_length=1)
    blocker_owner: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1)
    external_write_attempted: Literal[False] = False
    generation_performed: Literal[False] = False


def register_content_planning_generation_intent_routes(
    router: APIRouter,
    *,
    snapshot_loader: SnapshotLoader,
    store_factory: StoreFactory | None = None,
    current_preview_loader: PreviewLoader | None = None,
) -> None:
    make_store = store_factory or content_workflow_store

    @router.post(
        "/api/content/work-items/{work_item_id}/planning-generation-intent/preview",
        response_model=PlanningGenerationIntentResponse,
        responses={409: {"model": PlanningGenerationIntentBlockedResponse}},
    )
    def preview_intent(
        work_item_id: str, request: PlanningGenerationIntentPreviewRequest
    ) -> PlanningGenerationIntentResponse | JSONResponse:
        try:
            command = PlanningGenerationIntentPreviewCommand(
                work_item_id=work_item_id,
                content_kind=request.content_kind,
                service_card_id=request.service_card_id,
                packet_id=request.packet_id,
                packet_digest=request.packet_digest,
                expected_raw_planning_input_digest=request.expected_raw_planning_input_digest,
                expected_projected_planning_input_digest=request.expected_projected_planning_input_digest,
            )
            store = make_store()
            proposal = prepare_planning_generation_intent_action(
                request=command,
                snapshot_loader=snapshot_loader,
                store=store,
                current_preview_loader=(
                    None
                    if current_preview_loader is None
                    else lambda item_id, planning_input: current_preview_loader(item_id)
                ),
            )
            saved = store.record_planning_generation_intent_proposal(proposal)
            if saved == "conflict":
                raise PlanningGenerationIntentBlocked(
                    "generation_intent_conflict",
                    "Odczytaj ponownie aktualny planning input i przygotuj nowy zamiar.",
                )
        except PlanningGenerationIntentBlocked as error:
            return _blocked(work_item_id, error.code, error.evidence_ids, error.next_step)
        except (OSError, RuntimeError, ValueError):
            return _blocked(
                work_item_id,
                "generation_intent_preview_unavailable",
                (),
                "Odczytaj aktualny approved packet v2 i planning input.",
            )
        action = planning_generation_intent_action(proposal)
        return PlanningGenerationIntentResponse(
            action_id=action.id,
            action=action,
            snapshot=proposal.snapshot,
        )

    @router.get(
        "/api/content/work-items/{work_item_id}/planning-generation-intent/{action_id}",
        response_model=PlanningGenerationIntentResponse,
    )
    def read_intent(work_item_id: str, action_id: str) -> PlanningGenerationIntentResponse:
        action = load_planning_generation_intent_action(action_id, store=make_store())
        if action is None:
            raise HTTPException(status_code=404, detail="planning_generation_intent_not_found")
        snapshot = PlanningGenerationIntentSnapshot.model_validate(
            action.payload["planning_generation_intent"]
        )
        if snapshot.work_item_id != work_item_id:
            raise HTTPException(status_code=404, detail="planning_generation_intent_not_found")
        return PlanningGenerationIntentResponse(
            action_id=action.id, action=action, snapshot=snapshot
        )


def _blocked(
    work_item_id: str, code: str, evidence_ids: tuple[str, ...], next_step: str
) -> JSONResponse:
    result = PlanningGenerationIntentBlockedResponse(
        work_item_id=work_item_id,
        blocker_code=code,
        blocker_owner="WILQ content workflow",
        evidence_ids=list(evidence_ids),
        safe_next_step=next_step,
    )
    return JSONResponse(status_code=409, content=result.model_dump(mode="json"))


__all__ = ["register_content_planning_generation_intent_routes"]
