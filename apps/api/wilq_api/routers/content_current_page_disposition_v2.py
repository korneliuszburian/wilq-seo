"""Public local preview and readback for current-page KEEP ActionObjects."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.api.wilq_api.routers import content_current_page_evidence as current_page_evidence_router
from wilq.content.workflow.current_page_disposition_v2 import (
    CurrentPageDispositionV2Proposal,
    CurrentPageDispositionV2Receipt,
    build_current_page_disposition_v2_proposal,
)
from wilq.content.workflow.current_page_disposition_v2_action import (
    current_page_disposition_v2_action,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import ActionObject


class CurrentPageDispositionV2PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1, max_length=240)
    expected_material_meaning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class CurrentPageDispositionV2ReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["preview_ready", "current", "blocked"]
    action_id: str | None = None
    action: ActionObject | None = None
    proposal: CurrentPageDispositionV2Proposal | None = None
    receipt: CurrentPageDispositionV2Receipt | None = None
    blocker_code: str | None = None
    blocker_owner: str | None = None
    safe_next_step: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    external_write_attempted: Literal[False] = False

    @model_validator(mode="after")
    def validate_status_shape(self) -> CurrentPageDispositionV2ReadResponse:
        if self.status == "preview_ready":
            if self.action_id is None or self.action is None or self.proposal is None:
                raise ValueError("Preview-ready response requires its ActionObject and proposal.")
            if self.blocker_code or self.blocker_owner or self.safe_next_step or self.receipt:
                raise ValueError("Preview-ready response cannot carry blocker or receipt fields.")
        elif self.status == "current":
            if (
                self.action_id is None
                or self.action is None
                or self.proposal is None
                or self.receipt is None
            ):
                raise ValueError("Current response requires ActionObject, proposal and receipt.")
            if self.blocker_code or self.blocker_owner or self.safe_next_step:
                raise ValueError("Current response cannot carry blocker fields.")
        else:
            if not self.blocker_code or not self.blocker_owner or not self.safe_next_step:
                raise ValueError("Blocked response requires one typed blocker and safe next step.")
            if self.action is not None and self.action.status != "blocked":
                raise ValueError("Blocked response cannot advertise a ready ActionObject.")
        return self


StoreFactory = Callable[[], ContentWorkflowStore]
EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]


def register_content_current_page_disposition_v2_routes(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    evidence_loader: EvidenceLoader | None = None,
) -> None:
    make_store = store_factory or (lambda: content_workflow_store())
    load_evidence = evidence_loader or _read_current_page_evidence

    @router.post(
        "/api/content/current-page-dispositions/preview",
        response_model=CurrentPageDispositionV2ReadResponse,
        responses={409: {"model": CurrentPageDispositionV2ReadResponse}},
    )
    def preview_current_page_disposition_v2(
        request: CurrentPageDispositionV2PreviewRequest,
        response: Response,
    ) -> CurrentPageDispositionV2ReadResponse:
        return _preview_current_page_disposition_v2(
            request,
            response,
            store_factory=make_store,
            evidence_loader=load_evidence,
        )

    @router.get(
        "/api/content/current-page-dispositions/{action_id}",
        response_model=CurrentPageDispositionV2ReadResponse,
    )
    def read_current_page_disposition_v2(
        action_id: str,
    ) -> CurrentPageDispositionV2ReadResponse:
        return _read_current_page_disposition_v2(
            action_id,
            store_factory=make_store,
            evidence_loader=load_evidence,
        )


def _preview_current_page_disposition_v2(
    request: CurrentPageDispositionV2PreviewRequest,
    response: Response,
    *,
    store_factory: StoreFactory,
    evidence_loader: EvidenceLoader,
) -> CurrentPageDispositionV2ReadResponse:
    evidence = evidence_loader(request.work_item_id)
    if (
        evidence.status != "reviewed_material_current"
        or evidence.material_meaning_digest != request.expected_material_meaning_digest
    ):
        response.status_code = 409
        next_step = (
            evidence.safe_next_step
            if evidence.status == "blocked"
            else "Odczytaj nowy material_meaning_digest i przygotuj nowy preview dla tego URL-a."
        )
        return _blocked_current_page_disposition_response(
            evidence,
            blocker_code=evidence.blocker_code or "expected_material_meaning_digest_stale",
            safe_next_step=next_step,
        )
    try:
        candidate = build_current_page_disposition_v2_proposal(evidence)
    except ValueError:
        response.status_code = 409
        return _blocked_current_page_disposition_response(
            evidence,
            blocker_code="current_page_evidence_invalid",
            safe_next_step="Ponów odczyt bieżącego materiału i jego review.",
        )
    candidate_action = current_page_disposition_v2_action(candidate)
    proposal = store_factory().record_current_page_disposition_v2_proposal(candidate)
    action = current_page_disposition_v2_action(proposal)
    if candidate_action.id != action.id:
        raise RuntimeError("Stored current page disposition v2 identity changed.")
    return CurrentPageDispositionV2ReadResponse(
        status="preview_ready",
        action_id=action.id,
        action=action,
        proposal=proposal,
        evidence_ids=sorted(
            set(proposal.snapshot.current_evidence_ids + proposal.snapshot.catalog_evidence_ids)
        ),
    )


def _read_current_page_disposition_v2(
    action_id: str,
    *,
    store_factory: StoreFactory,
    evidence_loader: EvidenceLoader,
) -> CurrentPageDispositionV2ReadResponse:
    store = store_factory()
    proposal = store.load_current_page_disposition_v2_proposal(action_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Current page disposition v2 not found.")
    evidence = evidence_loader(proposal.snapshot.work_item_id)
    receipt = store.load_current_page_disposition_v2_receipt(action_id)
    is_current = (
        evidence.status == "reviewed_material_current"
        and evidence.material_meaning_digest == proposal.snapshot.material_meaning_digest
    )
    safe_next_step = None
    if not is_current:
        safe_next_step = (
            evidence.safe_next_step
            if evidence.status == "blocked"
            else "Odczytaj nowy material_meaning_digest i przygotuj nowy preview dla tego URL-a."
        )
    return CurrentPageDispositionV2ReadResponse(
        status=("current" if receipt is not None else "preview_ready") if is_current else "blocked",
        action_id=action_id,
        action=current_page_disposition_v2_action(proposal, current_evidence=evidence),
        proposal=proposal,
        receipt=receipt,
        blocker_code=None if is_current else evidence.blocker_code or "material_meaning_changed",
        blocker_owner=None if is_current else evidence.blocker_owner or "WILQ content workflow",
        safe_next_step=safe_next_step,
        evidence_ids=sorted(
            set(proposal.snapshot.current_evidence_ids + proposal.snapshot.catalog_evidence_ids)
            | set(evidence.current_evidence_ids + evidence.catalog_evidence_ids)
        ),
    )


def _blocked_current_page_disposition_response(
    evidence: CurrentPageEvidenceResponse,
    *,
    blocker_code: str,
    safe_next_step: str,
) -> CurrentPageDispositionV2ReadResponse:
    return CurrentPageDispositionV2ReadResponse(
        status="blocked",
        blocker_code=blocker_code,
        blocker_owner=evidence.blocker_owner or "WILQ content workflow",
        safe_next_step=safe_next_step,
        evidence_ids=sorted(set(evidence.current_evidence_ids + evidence.catalog_evidence_ids)),
    )


def _read_current_page_evidence(work_item_id: str) -> CurrentPageEvidenceResponse:
    return current_page_evidence_router.read_current_page_evidence(work_item_id=work_item_id)


__all__ = ["register_content_current_page_disposition_v2_routes"]
