"""Request-owned workflow state: append-only events and one derived projection."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.intake import ContentIntakeQueueItem
from wilq.content.workflow.research_read import ContentResearchReadResponse
from wilq.schemas.core import utc_now

WorkflowStep = Literal["intake_accepted", "research_read", "human_review", "brief_ready", "failed"]
WorkflowEventType = Literal[
    "intake_accepted",
    "research_ready",
    "human_gate_requested",
    "human_gate_answered",
    "brief_ready",
    "failed",
]
WorkflowGateStatus = Literal["pending", "approved", "rejected", "stale"]
WorkflowStatus = Literal["in_progress", "blocked", "ready_for_brief", "failed"]
_HEX64 = r"^[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentRequestWorkflowEvent(_FrozenModel):
    schema_version: Literal["wilq_request_workflow_event_v1"] = (
        "wilq_request_workflow_event_v1"
    )
    event_id: str = Field(min_length=1, max_length=240)
    queue_id: str = Field(min_length=1, max_length=240)
    idempotency_key: str = Field(min_length=1, max_length=240)
    event_type: WorkflowEventType
    actor_id: str = LOCAL_PILOT_AUDIT_IDENTITY.principal_id
    actor_trust_level: Literal["local_unverified"] = "local_unverified"
    gate_code: str | None = Field(default=None, max_length=160)
    gate_status: Literal["approved", "rejected"] | None = None
    owner: str | None = Field(default=None, max_length=160)
    note: str = Field(min_length=1, max_length=600)
    evidence_ids: tuple[str, ...] = ()
    created_at: datetime

    @model_validator(mode="after")
    def require_exact_event_shape(self) -> Self:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("Request workflow event time must be timezone-aware.")
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))):
            raise ValueError("Request workflow event evidence IDs must be sorted and unique.")
        digest = content_request_workflow_event_digest(self)
        expected_id = f"content_request_workflow_event_{digest[:24]}"
        if self.event_id != expected_id:
            raise ValueError("Request workflow event identity does not match its digest.")
        if self.event_type == "human_gate_requested":
            if not self.gate_code or not self.owner or self.gate_status is not None:
                raise ValueError("A human gate request needs a code, owner and no answer.")
        elif self.event_type == "human_gate_answered":
            if not self.gate_code or self.gate_status is None:
                raise ValueError("Human gate answer needs code and approved/rejected status.")
        elif any(
            value is not None for value in (self.gate_code, self.gate_status, self.owner)
        ):
            raise ValueError("Only human gate events carry gate, status or owner.")
        if self.event_type == "failed" and not self.note:
            raise ValueError("A failed workflow event needs a note.")
        return self


class ContentRequestWorkflowGate(_FrozenModel):
    code: str = Field(min_length=1, max_length=160)
    status: WorkflowGateStatus
    owner: str = Field(min_length=1, max_length=160)
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1, max_length=600)


class ContentRequestWorkflowState(_FrozenModel):
    schema_version: Literal["wilq_request_workflow_state_v1"] = (
        "wilq_request_workflow_state_v1"
    )
    queue_id: str = Field(min_length=1, max_length=240)
    status: WorkflowStatus
    current_step: WorkflowStep
    gates: tuple[ContentRequestWorkflowGate, ...] = ()
    lineage_event_ids: tuple[str, ...] = ()
    latest_idempotency_key: str | None = Field(default=None, max_length=240)
    event_count: int = Field(ge=0)
    evidence_ids: tuple[str, ...] = ()
    blocker_code: str | None = Field(default=None, max_length=160)
    blocker_owner: str | None = Field(default=None, max_length=160)
    safe_next_step: str = Field(min_length=1, max_length=600)
    generation_allowed: Literal[False] = False
    updated_at: datetime

    @model_validator(mode="after")
    def require_exact_state_shape(self) -> Self:
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("Request workflow state time must be timezone-aware.")
        if self.status in {"blocked", "failed"} and (
            not self.blocker_code or not self.blocker_owner
        ):
            raise ValueError("Blocked or failed request workflow needs one typed blocker.")
        if self.status not in {"blocked", "failed"} and (
            self.blocker_code or self.blocker_owner
        ):
            raise ValueError("Only a blocked or failed request workflow carries a blocker.")
        if len({gate.code for gate in self.gates}) != len(self.gates):
            raise ValueError("Request workflow gates must be unique.")
        if self.lineage_event_ids != tuple(sorted(self.lineage_event_ids)):
            raise ValueError("Request workflow lineage must be sorted.")
        if self.evidence_ids != tuple(sorted(set(self.evidence_ids))):
            raise ValueError("Request workflow evidence IDs must be sorted and unique.")
        return self


def content_request_workflow_event_digest(
    value: ContentRequestWorkflowEvent | dict[str, Any],
) -> str:
    payload = (
        value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    )
    payload.pop("event_id", None)
    return canonical_json_digest(payload)


def content_request_workflow_event_request_digest(
    value: ContentRequestWorkflowEvent | dict[str, Any],
) -> str:
    """Digest the client-visible request content for idempotency comparison."""

    payload = (
        value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    )
    for key in ("event_id", "created_at"):
        payload.pop(key, None)
    return canonical_json_digest(payload)


def build_content_request_workflow_event(
    *,
    queue_id: str,
    idempotency_key: str,
    event_type: WorkflowEventType,
    note: str,
    gate_code: str | None = None,
    gate_status: Literal["approved", "rejected"] | None = None,
    owner: str | None = None,
    evidence_ids: Sequence[str] = (),
    created_at: datetime | None = None,
) -> ContentRequestWorkflowEvent:
    """Build one self-authenticating append-only workflow event."""

    provisional = ContentRequestWorkflowEvent.model_construct(
        schema_version="wilq_request_workflow_event_v1",
        event_id="",
        queue_id=queue_id,
        idempotency_key=idempotency_key,
        event_type=event_type,
        actor_id=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
        actor_trust_level="local_unverified",
        gate_code=gate_code,
        gate_status=gate_status,
        owner=owner,
        note=note,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        created_at=created_at or utc_now(),
    )
    digest = content_request_workflow_event_digest(provisional)
    return ContentRequestWorkflowEvent.model_validate(
        provisional.model_dump(mode="json")
        | {"event_id": f"content_request_workflow_event_{digest[:24]}"}
    )


def build_content_request_workflow_state(
    queue_item: ContentIntakeQueueItem,
    events: Sequence[ContentRequestWorkflowEvent],
    research_read: ContentResearchReadResponse | None,
) -> ContentRequestWorkflowState:
    """Derive the current step and gates from append-only events and live sources."""

    ordered = tuple(sorted(events, key=lambda event: (event.created_at, event.event_id)))
    event_types = tuple(event.event_type for event in ordered)
    live_ready = research_read is not None and research_read.status == "ready"
    research_ready_recorded = "research_ready" in event_types
    gates = _project_gates(
        ordered,
        source_changed=research_ready_recorded and not live_ready,
        claim_freshness_blocked=research_read is not None and bool(research_read.claim_gates),
    )
    evidence_ids = tuple(
        sorted({value for event in ordered for value in event.evidence_ids})
    )
    base: dict[str, Any] = {
        "queue_id": queue_item.queue_id,
        "gates": gates,
        "lineage_event_ids": tuple(sorted(event.event_id for event in ordered)),
        "latest_idempotency_key": ordered[-1].idempotency_key if ordered else None,
        "event_count": len(ordered),
        "evidence_ids": evidence_ids,
        "updated_at": ordered[-1].created_at if ordered else queue_item.created_at,
    }
    blocked = _terminal_blocked_state(
        base,
        event_types=event_types,
        research_read=research_read,
        research_ready_recorded=research_ready_recorded,
        live_ready=live_ready,
    )
    if blocked is not None:
        return blocked
    if not ordered:
        return ContentRequestWorkflowState(
            **base,
            status="in_progress",
            current_step="intake_accepted",
            safe_next_step="Uruchom typowany odczyt researchu dla tego queue ID.",
        )
    return _live_progress_state(
        base,
        gates=gates,
        live_ready=live_ready,
        brief_ready_recorded="brief_ready" in event_types,
    )


def _terminal_blocked_state(
    base: dict[str, Any],
    *,
    event_types: tuple[str, ...],
    research_read: ContentResearchReadResponse | None,
    research_ready_recorded: bool,
    live_ready: bool,
) -> ContentRequestWorkflowState | None:
    if "failed" in event_types:
        return ContentRequestWorkflowState(
            **base,
            status="failed",
            current_step="failed",
            blocker_code="request_workflow_failed",
            blocker_owner=LOCAL_PILOT_AUDIT_IDENTITY.principal_id,
            safe_next_step="Przeanalizuj nieudany krok i uruchom ponownie z nowym kluczem.",
        )
    if research_ready_recorded and not live_ready:
        return ContentRequestWorkflowState(
            **base,
            status="blocked",
            current_step="research_read",
            blocker_code="request_workflow_source_changed",
            blocker_owner="WILQ content workflow",
            safe_next_step="Odczytaj ponownie aktualne źródła i oceń zależne bramki.",
        )
    if (
        research_read is not None
        and research_read.status == "blocked"
        and not research_ready_recorded
    ):
        blocker = research_read.blockers[0]
        return ContentRequestWorkflowState(
            **base,
            status="blocked",
            current_step="research_read",
            blocker_code=blocker.code,
            blocker_owner=blocker.owner,
            safe_next_step=research_read.safe_next_step,
        )
    return None


def _live_progress_state(
    base: dict[str, Any],
    *,
    gates: tuple[ContentRequestWorkflowGate, ...],
    live_ready: bool,
    brief_ready_recorded: bool,
) -> ContentRequestWorkflowState:
    pending = tuple(gate for gate in gates if gate.status in {"pending", "stale"})
    rejected = tuple(gate for gate in gates if gate.status == "rejected")
    if rejected:
        return ContentRequestWorkflowState(
            **base,
            status="blocked",
            current_step="human_review",
            blocker_code="request_workflow_gate_rejected",
            blocker_owner=rejected[0].owner,
            safe_next_step="Odpowiedz ponownie na odrzuconą bramkę albo zatrzymaj request.",
        )
    if pending and live_ready:
        return ContentRequestWorkflowState(
            **base,
            status="in_progress",
            current_step="human_review",
            safe_next_step=pending[0].safe_next_step,
        )
    if live_ready and brief_ready_recorded:
        return ContentRequestWorkflowState(
            **base,
            status="ready_for_brief",
            current_step="brief_ready",
            safe_next_step="Otwórz reviewable brief na zatwierdzonych źródłach.",
        )
    if live_ready:
        return ContentRequestWorkflowState(
            **base,
            status="in_progress",
            current_step="brief_ready",
            safe_next_step="Zbuduj reviewable brief na zatwierdzonych źródłach.",
        )
    return ContentRequestWorkflowState(
        **base,
        status="in_progress",
        current_step="human_review" if pending else "research_read",
        safe_next_step=(
            pending[0].safe_next_step
            if pending
            else "Uruchom typowany odczyt researchu dla tego queue ID."
        ),
    )


def _project_gates(
    events: tuple[ContentRequestWorkflowEvent, ...],
    *,
    source_changed: bool,
    claim_freshness_blocked: bool,
) -> tuple[ContentRequestWorkflowGate, ...]:
    gate_state: dict[str, tuple[WorkflowGateStatus, ContentRequestWorkflowEvent]] = {}
    for event in events:
        if event.event_type == "human_gate_requested" and event.gate_code:
            gate_state[event.gate_code] = ("pending", event)
        elif event.event_type == "human_gate_answered" and event.gate_code:
            current = gate_state.get(event.gate_code)
            if current is not None and current[0] == "pending":
                gate_state[event.gate_code] = (
                    event.gate_status or "pending",
                    current[1],
                )
    gates: list[ContentRequestWorkflowGate] = []
    for code, (status, request) in sorted(gate_state.items()):
        stale = source_changed or (claim_freshness_blocked and _claim_bound_gate(code))
        if stale:
            resolved: WorkflowGateStatus = "stale"
            step = "Odczytaj ponownie aktualne źródła przed decyzją o tej bramce."
        elif status == "pending":
            resolved = "pending"
            step = f"Poczekaj na decyzję człowieka dla bramki {code}."
        elif status == "approved":
            resolved = "approved"
            step = "Bramka zatwierdzona; przejdź do kolejnego kroku."
        else:
            resolved = "rejected"
            step = "Bramka odrzucona; popraw request albo zatrzymaj."
        gates.append(
            ContentRequestWorkflowGate(
                code=code,
                status=resolved,
                owner=request.owner or "Wilku",
                evidence_ids=request.evidence_ids,
                safe_next_step=step,
            )
        )
    return tuple(gates)


def _claim_bound_gate(code: str) -> bool:
    tokens = {token for token in re.split(r"[^a-z0-9]+", code.casefold()) if token}
    return bool(tokens & {"claim", "claims", "demand", "competitor", "competitors"})


__all__ = [
    "ContentRequestWorkflowEvent",
    "ContentRequestWorkflowGate",
    "ContentRequestWorkflowState",
    "WorkflowEventType",
    "WorkflowGateStatus",
    "WorkflowStatus",
    "WorkflowStep",
    "build_content_request_workflow_event",
    "build_content_request_workflow_state",
    "content_request_workflow_event_digest",
    "content_request_workflow_event_request_digest",
]
