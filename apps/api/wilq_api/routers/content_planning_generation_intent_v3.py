"""Public typed preview/read boundary for exact v3 packet planning intents."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.planning.generation_intent_v3 import (
    PlanningGenerationIntentV3Blocked,
    PlanningGenerationIntentV3Snapshot,
    load_planning_generation_intent_v3_action,
    planning_generation_intent_v3_action,
    prepare_planning_generation_intent_v3_action,
)
from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Preview
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import ActionObject

StoreFactory = Callable[[], ContentWorkflowStore]
PreviewLoader = Callable[[str], ResearchPacketV3Preview]


class PlanningGenerationIntentV3PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlanningGenerationIntentV3Response(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["planning_generation_intent_v3"] = "planning_generation_intent_v3"
    status: Literal["preview_ready"] = "preview_ready"
    action_id: str
    action: ActionObject
    snapshot: PlanningGenerationIntentV3Snapshot
    generation_performed: Literal[False] = False
    model_enqueued: Literal[False] = False
    external_write_attempted: Literal[False] = False


class PlanningGenerationIntentV3BlockedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["planning_generation_intent_v3"] = "planning_generation_intent_v3"
    status: Literal["blocked"] = "blocked"
    work_item_id: str = Field(min_length=1)
    blocker_code: str = Field(min_length=1)
    blocker_owner: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1)
    generation_performed: Literal[False] = False
    model_enqueued: Literal[False] = False
    external_write_attempted: Literal[False] = False


def register_content_planning_generation_intent_v3_routes(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    current_preview_loader: PreviewLoader | None = None,
) -> None:
    make_store = store_factory or content_workflow_store

    @router.post(
        "/api/content/work-items/{work_item_id}/planning-generation-intent-v3/preview",
        response_model=PlanningGenerationIntentV3Response,
        responses={409: {"model": PlanningGenerationIntentV3BlockedResponse}},
    )
    def preview_intent_v3(
        work_item_id: str, request: PlanningGenerationIntentV3PreviewRequest
    ) -> PlanningGenerationIntentV3Response | JSONResponse:
        try:
            store = make_store()
            proposal = prepare_planning_generation_intent_v3_action(
                work_item_id=work_item_id,
                packet_id=request.packet_id,
                packet_digest=request.packet_digest,
                store=store,
                current_preview_loader=current_preview_loader,
            )
            saved = store.record_planning_generation_intent_v3_proposal(proposal)
            if saved == "conflict":
                return _blocked(
                    work_item_id,
                    "generation_intent_v3_conflict",
                    "WILQ content workflow",
                    proposal.snapshot.evidence_ids,
                    "Odczytaj aktualny pakiet v3 i przygotuj nowy zamiar.",
                )
        except PlanningGenerationIntentV3Blocked as error:
            blocker = error.blocker
            return _blocked(
                work_item_id,
                blocker.code,
                blocker.owner,
                blocker.evidence_ids,
                blocker.safe_next_step,
            )
        except (OSError, RuntimeError, ValueError, sqlite3.Error):
            return _blocked(
                work_item_id,
                "generation_intent_v3_preview_unavailable",
                "WILQ content workflow",
                (),
                "Odczytaj aktualny receipt i pakiet v3, a następnie ponów podgląd.",
            )
        action = planning_generation_intent_v3_action(proposal)
        return PlanningGenerationIntentV3Response(
            action_id=action.id,
            action=action,
            snapshot=proposal.snapshot,
        )

    @router.get(
        "/api/content/work-items/{work_item_id}/planning-generation-intent-v3/{action_id}",
        response_model=PlanningGenerationIntentV3Response,
    )
    def read_intent_v3(
        work_item_id: str, action_id: str
    ) -> PlanningGenerationIntentV3Response:
        action = load_planning_generation_intent_v3_action(action_id, store=make_store())
        if action is None:
            raise HTTPException(
                status_code=404, detail="planning_generation_intent_v3_not_found"
            )
        snapshot = PlanningGenerationIntentV3Snapshot.model_validate(
            action.payload["planning_generation_intent_v3"]
        )
        if snapshot.work_item_id != work_item_id:
            raise HTTPException(
                status_code=404, detail="planning_generation_intent_v3_not_found"
            )
        return PlanningGenerationIntentV3Response(
            action_id=action.id, action=action, snapshot=snapshot
        )


def _blocked(
    work_item_id: str,
    code: str,
    owner: str,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> JSONResponse:
    result = PlanningGenerationIntentV3BlockedResponse(
        work_item_id=work_item_id,
        blocker_code=code,
        blocker_owner=owner,
        evidence_ids=list(evidence_ids),
        safe_next_step=next_step,
    )
    return JSONResponse(status_code=409, content=result.model_dump(mode="json"))


__all__ = ["register_content_planning_generation_intent_v3_routes"]
