"""Public request-owned workflow seam over one intake queue item."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal, Self

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from apps.api.wilq_api.routers import content_current_page_evidence
from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    ekologus_content_knowledge_cards,
)
from wilq.content.knowledge.source_facts import (
    ContentSourceFact,
    ekologus_source_facts,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.intake import (
    ContentIntakeQueueItem,
    demand_connector_freshness,
)
from wilq.content.workflow.request_workflow import (
    ContentRequestWorkflowEvent,
    ContentRequestWorkflowState,
    WorkflowEventType,
    build_content_request_workflow_event,
    build_content_request_workflow_state,
)
from wilq.content.workflow.research_read import resolve_content_research_read
from wilq.content.workflow.store.store import content_workflow_store

EvidenceLoader = Callable[[str], CurrentPageEvidenceResponse]
SourceFactsLoader = Callable[[], tuple[ContentSourceFact, ...]]
CardsLoader = Callable[[], tuple[ContentKnowledgeCard, ...]]
FreshnessLoader = Callable[[], Mapping[str, str]]
_ROUTE = "/api/content/intake-requests/{queue_id}/workflow"
_EVENTS_ROUTE = f"{_ROUTE}/events"


class ContentRequestWorkflowEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1, max_length=240)
    event_type: WorkflowEventType
    note: str = Field(min_length=1, max_length=600)
    gate_code: str | None = Field(default=None, max_length=160)
    gate_status: Literal["approved", "rejected"] | None = None
    owner: str | None = Field(default=None, max_length=160)
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_event_request_shape(self) -> Self:
        if self.event_type == "human_gate_requested":
            if not self.gate_code or not self.owner or self.gate_status is not None:
                raise ValueError("A human gate request needs gate_code, owner and no answer.")
        elif self.event_type == "human_gate_answered":
            if not self.gate_code or self.gate_status is None:
                raise ValueError("A human gate answer needs gate_code and gate_status.")
        elif any(value is not None for value in (self.gate_code, self.gate_status, self.owner)):
            raise ValueError("Only human gate events carry gate fields.")
        return self


class ContentRequestWorkflowErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


def register_content_request_workflow_routes(
    router: APIRouter,
    *,
    store_factory: Callable[[], Any] = content_workflow_store,
    evidence_loader: EvidenceLoader | None = None,
    source_facts_loader: SourceFactsLoader = ekologus_source_facts,
    cards_loader: CardsLoader = ekologus_content_knowledge_cards,
    freshness_loader: FreshnessLoader = demand_connector_freshness,
) -> None:
    load_evidence = evidence_loader or (
        lambda work_item_id: content_current_page_evidence.read_current_page_evidence(
            work_item_id=work_item_id
        )
    )

    @router.post(
        _EVENTS_ROUTE,
        response_model=ContentRequestWorkflowEvent,
        responses={
            200: {"model": ContentRequestWorkflowEvent},
            404: {"model": ContentRequestWorkflowErrorResponse},
            409: {"model": ContentRequestWorkflowErrorResponse},
        },
        tags=["content"],
    )
    def append_content_request_workflow_event(
        queue_id: str,
        request: ContentRequestWorkflowEventRequest,
    ) -> JSONResponse:
        store = store_factory()
        item = store.load_content_intake_request(queue_id)
        if item is None or not isinstance(item, ContentIntakeQueueItem):
            return _missing_queue()
        try:
            event = build_content_request_workflow_event(
                queue_id=queue_id,
                idempotency_key=request.idempotency_key,
                event_type=request.event_type,
                note=request.note,
                gate_code=request.gate_code,
                gate_status=request.gate_status,
                owner=request.owner,
                evidence_ids=tuple(request.evidence_ids),
            )
        except ValidationError:
            return JSONResponse(
                status_code=422,
                content=ContentRequestWorkflowErrorResponse(
                    detail="request_workflow_event_invalid",
                    owner="WILQ content workflow",
                    safe_next_step=(
                        "Popraw kształt zdarzenia: bramka wymaga kodu i ownera, a odpowiedź "
                        "statusu approved/rejected."
                    ),
                ).model_dump(mode="json"),
            )
        result, stored = store.append_content_request_workflow_event(event)
        if result == "conflict":
            return JSONResponse(
                status_code=409,
                content=ContentRequestWorkflowErrorResponse(
                    detail="request_workflow_idempotency_conflict",
                    owner="WILQ content workflow",
                    safe_next_step="Użyj nowego klucza idempotencji dla zmienionego zdarzenia.",
                ).model_dump(mode="json"),
            )
        return JSONResponse(
            status_code=201 if result == "created" else 200,
            content=stored.model_dump(mode="json"),
        )

    @router.get(
        _ROUTE,
        response_model=ContentRequestWorkflowState,
        responses={404: {"model": ContentRequestWorkflowErrorResponse}},
        tags=["content"],
    )
    def read_content_request_workflow(
        queue_id: str,
    ) -> ContentRequestWorkflowState | JSONResponse:
        store = store_factory()
        item = store.load_content_intake_request(queue_id)
        if item is None or not isinstance(item, ContentIntakeQueueItem):
            return _missing_queue()
        events = store.list_content_request_workflow_events(queue_id)
        research_read = resolve_content_research_read(
            store,
            queue_id,
            evidence_loader=load_evidence,
            source_facts_loader=source_facts_loader,
            cards_loader=cards_loader,
            connector_freshness=freshness_loader(),
        )
        return build_content_request_workflow_state(item, events, research_read)


def _missing_queue() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ContentRequestWorkflowErrorResponse(
            detail="intake_queue_item_missing",
            owner="WILQ content workflow",
            safe_next_step="Użyj queue ID z odpowiedzi przyjęcia prośby.",
        ).model_dump(mode="json"),
    )


__all__ = [
    "ContentRequestWorkflowErrorResponse",
    "ContentRequestWorkflowEventRequest",
    "register_content_request_workflow_routes",
]
