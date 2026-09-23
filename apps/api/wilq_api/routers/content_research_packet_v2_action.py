"""Public local ActionObject review of one exact v2 research packet snapshot."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.api.wilq_api.routers.content_research_packet_v2_preview import (
    read_current_research_packet_v2_preview,
)
from wilq.content.workflow.research_packet_v2_action import (
    load_research_packet_v2_action,
    parse_research_packet_v2_action_record,
    prepare_research_packet_v2_action,
)
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    ResearchPacketV2PreviewBlocker,
)
from wilq.content.workflow.research_packet_v2_receipt import (
    ResearchPacketV2ApprovalReceipt,
    ResearchPacketV2PreviewRecord,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import ActionObject

StoreFactory = Callable[[], ContentWorkflowStore]
PreviewLoader = Callable[[str], ResearchPacketV2Preview]


class ResearchPacketV2ActionReady(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["research_packet_v2_action"] = "research_packet_v2_action"
    status: Literal["preview_ready"] = "preview_ready"
    action_id: str
    action: ActionObject
    preview: ResearchPacketV2Preview
    external_write_attempted: Literal[False] = False
    generation_allowed: Literal[False] = False


class ResearchPacketV2ActionBlocked(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["research_packet_v2_action"] = "research_packet_v2_action"
    status: Literal["blocked"] = "blocked"
    work_item_id: str
    blocker_code: str = Field(min_length=1)
    blocker_owner: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1)
    external_write_attempted: Literal[False] = False
    generation_allowed: Literal[False] = False


class ResearchPacketV2ApprovedRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["research_packet_v2_approved_read"] = "research_packet_v2_approved_read"
    status: Literal["found"] = "found"
    receipt: ResearchPacketV2ApprovalReceipt
    preview: ResearchPacketV2Preview
    currentness_status: Literal["current", "blocked"]
    blocker: ResearchPacketV2PreviewBlocker | None = None
    external_write_attempted: Literal[False] = False
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_currentness_shape(self) -> ResearchPacketV2ApprovedRead:
        if self.currentness_status == "current" and self.blocker is not None:
            raise ValueError("Current packet read cannot carry a blocker.")
        if self.currentness_status == "blocked" and self.blocker is None:
            raise ValueError("Blocked packet read requires a typed blocker.")
        if self.receipt.packet_digest != self.preview.preview_hash:
            raise ValueError("Approved packet read is not exact to its stored preview.")
        return self


def register_content_research_packet_v2_action_routes(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    preview_loader: PreviewLoader | None = None,
) -> None:
    make_store = store_factory or content_workflow_store
    load_preview = preview_loader or read_current_research_packet_v2_preview

    @router.post(
        "/api/content/work-items/{work_item_id}/research-packet-v2-action/preview",
        response_model=ResearchPacketV2ActionReady,
        responses={409: {"model": ResearchPacketV2ActionBlocked}},
    )
    def prepare_action(work_item_id: str) -> ResearchPacketV2ActionReady | JSONResponse:
        try:
            preview = load_preview(work_item_id)
            if preview.status == "blocked":
                blocker = preview.blocker
                if blocker is None:
                    raise ValueError("blocked_packet_without_blocker")
                return _blocked_response(
                    work_item_id,
                    blocker.code,
                    blocker.owner,
                    list(blocker.evidence_ids),
                    blocker.safe_next_step,
                )
            record = ResearchPacketV2PreviewRecord.from_preview(preview)
            action = prepare_research_packet_v2_action(record, store=make_store())
        except (ValueError, RuntimeError, HTTPException):
            return _blocked_response(
                work_item_id,
                "research_packet_v2_preview_unavailable",
                "WILQ content workflow",
                [],
                "Odczytaj ponownie dokładny podgląd pakietu v2.",
            )
        return ResearchPacketV2ActionReady(
            action_id=action.id,
            action=action,
            preview=record.snapshot,
        )

    _register_research_packet_v2_reads(router, make_store, load_preview)


def _register_research_packet_v2_reads(
    router: APIRouter, make_store: StoreFactory, load_preview: PreviewLoader
) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/research-packet-v2-action/{action_id}",
        response_model=ResearchPacketV2ActionReady,
    )
    def read_action(work_item_id: str, action_id: str) -> ResearchPacketV2ActionReady:
        action = load_research_packet_v2_action(action_id, store=make_store())
        if action is None:
            raise HTTPException(status_code=404, detail="research_packet_v2_action_not_found")
        record = parse_research_packet_v2_action_record(
            action.payload["research_packet_v2_preview"]
        )
        if record.work_item_id != work_item_id:
            raise HTTPException(status_code=404, detail="research_packet_v2_action_not_found")
        return ResearchPacketV2ActionReady(
            action_id=action.id,
            action=action,
            preview=record.snapshot,
        )

    @router.get(
        "/api/content/research-packets-v2/{packet_id}",
        response_model=ResearchPacketV2ApprovedRead,
    )
    def read_approved_packet(packet_id: str) -> ResearchPacketV2ApprovedRead:
        store = make_store()
        receipt = store.load_research_packet_v2_approval_receipt(packet_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="research_packet_v2_receipt_not_found")
        record = store.load_research_packet_v2_preview(receipt.packet_digest)
        if record is None:
            raise HTTPException(status_code=409, detail="research_packet_v2_preview_missing")
        try:
            current = load_preview(record.work_item_id)
        except (ValueError, RuntimeError, HTTPException):
            current = ResearchPacketV2Preview(
                status="blocked",
                work_item_id=record.work_item_id,
                blocker=ResearchPacketV2PreviewBlocker(
                    code="research_packet_v2_current_read_unavailable",
                    owner="WILQ content workflow",
                    evidence_ids=(),
                    safe_next_step="Ponów dokładny odczyt bieżącego pakietu v2.",
                ),
            )
        if current.status == "ready" and current.preview_hash == receipt.packet_digest:
            return ResearchPacketV2ApprovedRead(
                receipt=receipt,
                preview=record.snapshot,
                currentness_status="current",
            )
        blocker = current.blocker or ResearchPacketV2PreviewBlocker(
            code="research_packet_v2_current_drift",
            owner="WILQ content workflow",
            evidence_ids=current.evidence_ids,
            safe_next_step="Przygotuj nowy dokładny podgląd pakietu i przeprowadź review.",
        )
        return ResearchPacketV2ApprovedRead(
            receipt=receipt,
            preview=record.snapshot,
            currentness_status="blocked",
            blocker=blocker,
        )


def _blocked_response(
    work_item_id: str,
    code: str,
    owner: str,
    evidence_ids: list[str],
    next_step: str,
) -> JSONResponse:
    blocked = ResearchPacketV2ActionBlocked(
        work_item_id=work_item_id,
        blocker_code=code,
        blocker_owner=owner,
        evidence_ids=evidence_ids,
        safe_next_step=next_step,
    )
    return JSONResponse(status_code=409, content=blocked.model_dump(mode="json"))


__all__ = ["register_content_research_packet_v2_action_routes"]
