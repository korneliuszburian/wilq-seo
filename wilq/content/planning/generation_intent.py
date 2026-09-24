"""Local-only ActionObject intent to generate from one approved v2 packet."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.planning.approved_packet_v2 import resolve_approved_packet_v2_for_planning
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    build_content_planning_input,
)
from wilq.content.planning.generation_readiness import planning_generation_blockers
from wilq.content.planning.packet_input_binding import bind_packet_identity_to_planning_input
from wilq.content.planning.service_selection import with_explicit_content_service_selection
from wilq.content.planning.source_pack_projection import project_research_packet_v2_facts
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    ResearchPacketV2PreviewBlocker,
)
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)

if TYPE_CHECKING:
    from wilq.content.workflow.store.store import ContentWorkflowStore

PLANNING_GENERATION_INTENT_ACTION_TYPE = "content_planning_generation_intent_v1"
PLANNING_GENERATION_INTENT_ADAPTER = "content_planning_generation_intent_local_authority"
_ACTION_PREFIX = "act_content_planning_generation_intent_"
_HEX64 = r"^[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlanningGenerationIntentSnapshot(_FrozenModel):
    schema_version: Literal["wilq_planning_generation_intent_snapshot_v1"] = (
        "wilq_planning_generation_intent_snapshot_v1"
    )
    intent_digest: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1, max_length=240)
    content_kind: Literal["service", "editorial"]
    service_card_id: str | None = Field(default=None, min_length=1, max_length=240)
    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=_HEX64)
    raw_planning_input_digest: str = Field(pattern=_HEX64)
    projected_planning_input_digest: str = Field(pattern=_HEX64)
    selected_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    context_digest: str = Field(pattern=_HEX64)

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        if self.content_kind == "service" and self.service_card_id is None:
            raise ValueError("Service generation intent requires the exact selected service.")
        if self.content_kind == "editorial" and self.service_card_id is not None:
            raise ValueError("Editorial generation intent cannot carry a service card.")
        for name in ("selected_fact_ids", "evidence_ids"):
            values = getattr(self, name)
            if values != tuple(sorted(set(values))) or any(not item.strip() for item in values):
                raise ValueError(f"{name} must be sorted, unique and non-blank.")
        if self.context_digest != planning_generation_intent_context_digest(self):
            raise ValueError("Planning generation intent context digest does not match.")
        if self.intent_digest != planning_generation_intent_digest(self.context_digest):
            raise ValueError("Planning generation intent digest does not match.")
        return self


class PlanningGenerationIntentProposal(_FrozenModel):
    schema_version: Literal["wilq_planning_generation_intent_proposal_v1"] = (
        "wilq_planning_generation_intent_proposal_v1"
    )
    action_id: str = Field(min_length=1, max_length=240)
    snapshot: PlanningGenerationIntentSnapshot

    @model_validator(mode="after")
    def require_exact_action_id(self) -> Self:
        if self.action_id != planning_generation_intent_action_id(self.snapshot.intent_digest):
            raise ValueError("Planning generation intent action ID does not match its snapshot.")
        return self


class PlanningGenerationIntentPreviewCommand(_FrozenModel):
    work_item_id: str = Field(min_length=1, max_length=240)
    content_kind: Literal["service", "editorial"]
    service_card_id: str | None = Field(default=None, min_length=1, max_length=240)
    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=_HEX64)
    expected_raw_planning_input_digest: str = Field(pattern=_HEX64)
    expected_projected_planning_input_digest: str = Field(pattern=_HEX64)

    @model_validator(mode="after")
    def require_subject(self) -> Self:
        if self.content_kind == "service" and self.service_card_id is None:
            raise ValueError("Service generation intent requires its exact service card.")
        if self.content_kind == "editorial" and self.service_card_id is not None:
            raise ValueError("Editorial generation intent cannot carry a service card.")
        return self


class PlanningGenerationIntentReceipt(_FrozenModel):
    schema_version: Literal["wilq_planning_generation_intent_receipt_v1"] = (
        "wilq_planning_generation_intent_receipt_v1"
    )
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    snapshot: PlanningGenerationIntentSnapshot
    preview_audit_id: str = Field(min_length=1, max_length=240)
    review_audit_id: str = Field(min_length=1, max_length=240)
    confirmation_audit_id: str = Field(min_length=1, max_length=240)
    impact_audit_id: str = Field(min_length=1, max_length=240)
    reviewed_by: str = Field(min_length=1, max_length=240)
    confirmed_by: str = Field(min_length=1, max_length=240)
    created_at: datetime
    generation_performed: Literal[False] = False
    model_enqueued: Literal[False] = False
    external_write_attempted: Literal[False] = False

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("Generation intent receipt timestamp must be timezone-aware.")
        if self.receipt_digest != planning_generation_intent_receipt_digest(self):
            raise ValueError("Planning generation intent receipt digest does not match.")
        if self.receipt_id != f"content_planning_generation_intent_receipt_{self.receipt_digest}":
            raise ValueError("Planning generation intent receipt ID does not match.")
        return self


class PlanningGenerationIntentApplyBlocker(_FrozenModel):
    code: str = Field(min_length=1)
    owner: Literal["WILQ content workflow"] = "WILQ content workflow"
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)
    external_write_attempted: Literal[False] = False


class PlanningGenerationIntentBlocked(ValueError):
    def __init__(self, code: str, next_step: str, evidence_ids: tuple[str, ...] = ()) -> None:
        super().__init__(code)
        self.code = code
        self.next_step = next_step
        self.evidence_ids = tuple(sorted(set(evidence_ids)))


def planning_generation_intent_context_digest(
    value: PlanningGenerationIntentSnapshot | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("context_digest", None)
    payload.pop("intent_digest", None)
    return canonical_json_digest(payload)


def planning_generation_intent_digest(context_digest: str) -> str:
    return canonical_json_digest(
        {
            "schema_version": "wilq_planning_generation_intent_snapshot_v1",
            "context_digest": context_digest,
        }
    )


def planning_generation_intent_action_id(intent_digest: str) -> str:
    return f"{_ACTION_PREFIX}{intent_digest}"


def planning_generation_intent_action(proposal: PlanningGenerationIntentProposal) -> ActionObject:
    snapshot = proposal.snapshot
    return ActionObject(
        id=proposal.action_id,
        title="Zatwierdź zamiar przygotowania planu dla exact pakietu v2",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(snapshot.evidence_ids),
        human_diagnosis=(
            "ActionObject zapisuje wyłącznie exact lokalny zamiar; nie uruchamia modelu."
        ),
        recommended_reason="Sprawdź pakiet, wybraną usługę i oba digesty wejścia.",
        payload={
            "action_type": PLANNING_GENERATION_INTENT_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "planning_generation_intent": snapshot.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": proposal.action_id,
                    "operation_type": "record_local_planning_generation_intent",
                    "work_item_id": snapshot.work_item_id,
                    "content_kind": snapshot.content_kind,
                    "service_card_id": snapshot.service_card_id,
                    "packet_id": snapshot.packet_id,
                    "packet_digest": snapshot.packet_digest,
                    "raw_planning_input_digest": snapshot.raw_planning_input_digest,
                    "projected_planning_input_digest": snapshot.projected_planning_input_digest,
                    "apply_allowed": True,
                    "generation_performed": False,
                    "model_enqueued": False,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "generation_allowed": False,
            "model_enqueue_allowed": False,
            "external_write_attempted": False,
        },
        validation_status="not_validated",
        created_by="system_core_planning_generation_intent_v1",
    )


def build_planning_generation_intent_proposal(
    *,
    work_item_id: str,
    content_kind: Literal["service", "editorial"],
    service_card_id: str | None,
    packet_id: str,
    packet_digest: str,
    raw_planning_input_digest: str,
    projected_planning_input_digest: str,
    selected_fact_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
) -> PlanningGenerationIntentProposal:
    provisional: dict[str, object] = {
        "schema_version": "wilq_planning_generation_intent_snapshot_v1",
        "work_item_id": work_item_id,
        "content_kind": content_kind,
        "service_card_id": service_card_id,
        "packet_id": packet_id,
        "packet_digest": packet_digest,
        "raw_planning_input_digest": raw_planning_input_digest,
        "projected_planning_input_digest": projected_planning_input_digest,
        "selected_fact_ids": tuple(sorted(set(selected_fact_ids))),
        "evidence_ids": tuple(sorted(set(evidence_ids))),
        "context_digest": "0" * 64,
        "intent_digest": "0" * 64,
    }
    context_digest = planning_generation_intent_context_digest(provisional)
    intent_digest = planning_generation_intent_digest(context_digest)
    snapshot = PlanningGenerationIntentSnapshot.model_validate(
        provisional | {"context_digest": context_digest, "intent_digest": intent_digest}
    )
    return PlanningGenerationIntentProposal(
        action_id=planning_generation_intent_action_id(intent_digest),
        snapshot=snapshot,
    )


def prepare_planning_generation_intent_action(
    *,
    request: PlanningGenerationIntentPreviewCommand,
    snapshot_loader: Callable[[str], ContentWorkItemWorkflowSnapshotResponse],
    store: ContentWorkflowStore,
    current_preview_loader: Callable[[str, ContentPlanningInput], Any] | None = None,
) -> PlanningGenerationIntentProposal:
    snapshot = snapshot_loader(request.work_item_id)
    raw_input = current_planning_input(
        snapshot,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
    )
    if raw_input.planning_input_digest != request.expected_raw_planning_input_digest:
        raise PlanningGenerationIntentBlocked(
            "raw_planning_input_changed",
            "Odczytaj aktualny planning input i przygotuj nowy preview zamiaru.",
            tuple(raw_input.evidence_ids),
        )
    view = resolve_approved_packet_v2_for_planning(
        store=store,
        packet_id=request.packet_id,
        expected_digest=request.packet_digest,
        planning_input=raw_input,
        current_preview_loader=current_preview_loader,
    )
    if isinstance(view, ResearchPacketV2PreviewBlocker):
        raise PlanningGenerationIntentBlocked(view.code, view.safe_next_step, view.evidence_ids)
    if view.packet_id != request.packet_id or view.packet_digest != request.packet_digest:
        raise PlanningGenerationIntentBlocked(
            "approved_packet_identity_changed",
            "Odczytaj actualny approved packet v2 i przygotuj nowy preview zamiaru.",
            view.evidence_ids,
        )
    projected = _project_current_packet_input(raw_input, view.preview)
    if projected.planning_input_digest != request.expected_projected_planning_input_digest:
        raise PlanningGenerationIntentBlocked(
            "projected_planning_input_changed",
            "Odczytaj aktualny pakiet, usługę i projected planning digest.",
            view.evidence_ids,
        )
    return build_planning_generation_intent_proposal(
        work_item_id=view.current_work_item_id,
        content_kind=raw_input.content_kind,
        service_card_id=raw_input.confirmed_service_card_id,
        packet_id=view.packet_id,
        packet_digest=view.packet_digest,
        raw_planning_input_digest=raw_input.planning_input_digest,
        projected_planning_input_digest=projected.planning_input_digest,
        selected_fact_ids=tuple(fact.source_fact_id for fact in view.preview.selected_facts),
        evidence_ids=tuple(sorted(set(view.evidence_ids) | set(projected.evidence_ids))),
    )


def current_planning_input(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    *,
    content_kind: Literal["service", "editorial"],
    service_card_id: str | None,
) -> ContentPlanningInput:
    if content_kind == "service":
        if service_card_id is None:
            raise PlanningGenerationIntentBlocked(
                "generation_service_required",
                "Wybierz dokładną usługę przed przygotowaniem zamiaru planowania.",
            )
        snapshot = with_explicit_content_service_selection(snapshot, service_card_id)
    elif service_card_id is not None:
        raise PlanningGenerationIntentBlocked(
            "editorial_service_forbidden",
            "Editorial planning nie może mieć przypisanej usługi.",
        )
    result = build_content_planning_input(snapshot, service_card_id=service_card_id)
    blockers = planning_generation_blockers(result.blockers)
    if result.planning_input is None or blockers:
        next_step = blockers[0].next_step if blockers else "Odśwież current planning input."
        evidence = tuple(snapshot.preflight.item.evidence_ids)
        raise PlanningGenerationIntentBlocked("planning_input_unavailable", next_step, evidence)
    planning_input = result.planning_input
    if (
        planning_input.work_item_id != snapshot.preflight.item.id
        or planning_input.content_kind != content_kind
        or planning_input.confirmed_service_card_id != service_card_id
    ):
        raise PlanningGenerationIntentBlocked(
            "planning_subject_changed",
            "Odczytaj ponownie dokładny work item i usługę.",
            tuple(planning_input.evidence_ids),
        )
    return planning_input


def _project_current_packet_input(
    raw_input: ContentPlanningInput,
    preview: ResearchPacketV2Preview,
) -> ContentPlanningInput:
    if preview.preview_hash is None:
        raise PlanningGenerationIntentBlocked(
            "approved_packet_digest_missing",
            "Odczytaj ponownie zatwierdzony pakiet v2.",
            preview.evidence_ids,
        )
    projected = project_research_packet_v2_facts(
        raw_input,
        preview.selected_facts,
        ekologus_source_facts(),
    )
    return bind_packet_identity_to_planning_input(
        projected,
        work_item_id=preview.work_item_id,
        packet_id=f"content_research_packet_v2_{preview.preview_hash[:24]}",
        packet_digest=preview.preview_hash,
    )


def load_planning_generation_intent_action(
    action_id: str,
    *,
    store: Any,
) -> ActionObject | None:
    proposal = store.load_planning_generation_intent_proposal(action_id)
    return None if proposal is None else planning_generation_intent_action(proposal)


def validate_planning_generation_intent_action_payload(payload: dict[str, Any]) -> list[str]:
    try:
        snapshot = PlanningGenerationIntentSnapshot.model_validate_json(
            json.dumps(payload.get("planning_generation_intent", {}), sort_keys=True),
            strict=True,
        )
        proposal = PlanningGenerationIntentProposal(
            action_id=planning_generation_intent_action_id(snapshot.intent_digest),
            snapshot=snapshot,
        )
    except (TypeError, ValueError, ValidationError):
        return ["Planning generation intent snapshot is invalid."]
    return (
        []
        if payload == planning_generation_intent_action(proposal).payload
        else ["Planning generation intent ActionObject payload is not exact."]
    )


def execute_planning_generation_intent_action(
    action: ActionObject,
    *,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
    current_snapshot_loader: Callable[[str], ContentWorkItemWorkflowSnapshotResponse] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        proposal = store.load_planning_generation_intent_proposal(action.id)
    except Exception:
        return _apply_blocked(
            "generation_intent_proposal_unavailable",
            "Odczytaj ponownie exact lokalny zamiar.",
            (),
        )
    if proposal is None:
        return _apply_blocked(
            "generation_intent_proposal_missing",
            "Odczytaj ponownie exact lokalny zamiar.",
            (),
        )
    if current_snapshot_loader is None:
        return _apply_blocked(
            "current_planning_snapshot_unavailable",
            "Odczytaj aktualny planning input i ponów sprawdzenie zamiaru.",
            proposal.snapshot.evidence_ids,
        )
    expected_action = planning_generation_intent_action(proposal)
    if action.payload != expected_action.payload:
        return _apply_blocked(
            "generation_intent_action_changed",
            "Odczytaj ponownie niezmieniony ActionObject zamiaru.",
            proposal.snapshot.evidence_ids,
        )
    blocker = _currentness_blocker(proposal, store, current_snapshot_loader)
    if blocker is not None:
        return _apply_blocker_result(blocker)

    return _record_generation_intent_receipt(
        action=action,
        proposal=proposal,
        store=store,
        audit_events=audit_events,
        confirmed_by=confirmed_by,
    )


def _record_generation_intent_receipt(
    *,
    action: ActionObject,
    proposal: PlanningGenerationIntentProposal,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
) -> tuple[dict[str, Any], list[str]]:
    payload_digest = canonical_json_digest(action.payload)
    try:
        chain, _blockers = revision_bound_action_chain(
            [event for event in audit_events if event.action_id == action.id],
            confirmed_by=confirmed_by,
            binding_from_event=_generation_intent_audit_binding,
            expected_binding=(proposal.snapshot.context_digest, payload_digest),
        )
    except Exception:
        return _apply_blocked(
            "generation_intent_audit_chain_unavailable",
            "Odtwórz pełny audyt preview, review, confirm i impact.",
            proposal.snapshot.evidence_ids,
        )
    if chain is None:
        return _apply_blocked(
            "generation_intent_audit_chain_incomplete",
            "Wykonaj ponownie pełny lifecycle preview, review, confirm i impact.",
            proposal.snapshot.evidence_ids,
        )
    preview, review, confirmation, impact = chain
    checked = review.details.get("checked_items", [])
    if not isinstance(checked, list) or "reviewed_exact_generation_intent" not in checked:
        return _apply_blocked(
            "generation_intent_review_attestation_missing",
            "Zatwierdź pełny exact zamiar w human review.",
            proposal.snapshot.evidence_ids,
        )
    try:
        receipt = _generation_intent_receipt(
            action=action,
            proposal=proposal,
            preview=preview,
            review=review,
            confirmation=confirmation,
            impact=impact,
            payload_digest=payload_digest,
        )
        status = store.record_planning_generation_intent_receipt(receipt)
    except Exception:
        return _apply_blocked(
            "generation_intent_receipt_unavailable",
            "Ponów zapis lokalnego zamiaru po sprawdzeniu bieżącego stanu.",
            proposal.snapshot.evidence_ids,
        )
    if status == "conflict":
        return _apply_blocked(
            "generation_intent_receipt_conflict",
            "Odczytaj istniejący receipt zamiaru przed kolejną próbą.",
            proposal.snapshot.evidence_ids,
        )
    return {
        "receipt_id": receipt.receipt_id,
        "intent_id": proposal.action_id,
        "status": status,
        "generation_performed": False,
        "model_enqueued": False,
        "external_write_attempted": False,
    }, []


def _generation_intent_receipt(
    *,
    action: ActionObject,
    proposal: PlanningGenerationIntentProposal,
    preview: AuditEvent,
    review: AuditEvent,
    confirmation: AuditEvent,
    impact: AuditEvent,
    payload_digest: str,
) -> PlanningGenerationIntentReceipt:
    fields: dict[str, object] = {
        "receipt_id": "",
        "receipt_digest": "0" * 64,
        "action_id": action.id,
        "action_payload_digest": payload_digest,
        "snapshot": proposal.snapshot,
        "preview_audit_id": preview.id,
        "review_audit_id": review.id,
        "confirmation_audit_id": confirmation.id,
        "impact_audit_id": impact.id,
        "reviewed_by": review.actor,
        "confirmed_by": confirmation.actor,
        "created_at": review.created_at,
        "generation_performed": False,
        "model_enqueued": False,
        "external_write_attempted": False,
    }
    provisional = PlanningGenerationIntentReceipt.model_construct(**cast(Any, fields))
    digest = planning_generation_intent_receipt_digest(provisional)
    return PlanningGenerationIntentReceipt.model_validate(
        provisional.model_dump(mode="python")
        | {
            "receipt_id": f"content_planning_generation_intent_receipt_{digest}",
            "receipt_digest": digest,
        }
    )


def _apply_blocked(
    code: str, next_step: str, evidence_ids: tuple[str, ...]
) -> tuple[dict[str, Any], list[str]]:
    return _apply_blocker_result(_intent_apply_blocker(code, next_step, evidence_ids))


def _intent_apply_blocker(
    code: str, next_step: str, evidence_ids: tuple[str, ...]
) -> PlanningGenerationIntentApplyBlocker:
    return PlanningGenerationIntentApplyBlocker(
        code=code,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=next_step,
    )


def _apply_blocker_result(
    blocker: PlanningGenerationIntentApplyBlocker,
) -> tuple[dict[str, Any], list[str]]:
    return (
        {
            "status": "blocked",
            "blocker": blocker.model_dump(mode="json"),
            "generation_performed": False,
            "model_enqueued": False,
            "external_write_attempted": False,
        },
        [blocker.safe_next_step],
    )


def _currentness_blocker(
    proposal: PlanningGenerationIntentProposal,
    store: ContentWorkflowStore,
    snapshot_loader: Callable[[str], ContentWorkItemWorkflowSnapshotResponse],
) -> PlanningGenerationIntentApplyBlocker | None:
    snapshot = proposal.snapshot
    try:
        current_snapshot = snapshot_loader(snapshot.work_item_id)
    except Exception:
        return _intent_apply_blocker(
            "current_snapshot_unavailable",
            "Odczytaj ponownie aktualny work item przed zastosowaniem zamiaru.",
            snapshot.evidence_ids,
        )
    try:
        current_input = current_planning_input(
            current_snapshot,
            content_kind=snapshot.content_kind,
            service_card_id=snapshot.service_card_id,
        )
        if current_input.planning_input_digest != snapshot.raw_planning_input_digest:
            return _intent_apply_blocker(
                "raw_planning_input_changed",
                "Odczytaj aktualny planning input i przygotuj nowy zamiar.",
                tuple(current_input.evidence_ids),
            )
        packet = resolve_approved_packet_v2_for_planning(
            store=store,
            packet_id=snapshot.packet_id,
            expected_digest=snapshot.packet_digest,
            planning_input=current_input,
        )
        if isinstance(packet, ResearchPacketV2PreviewBlocker):
            return _intent_apply_blocker(
                packet.code, packet.safe_next_step, packet.evidence_ids
            )
        selected_ids = tuple(fact.source_fact_id for fact in packet.preview.selected_facts)
        if (
            packet.packet_id != snapshot.packet_id
            or packet.packet_digest != snapshot.packet_digest
            or selected_ids != snapshot.selected_fact_ids
        ):
            return _intent_apply_blocker(
                "approved_packet_selection_changed",
                "Odczytaj i zatwierdź aktualny pakiet v2.",
                packet.evidence_ids,
            )
        try:
            projected = _project_current_packet_input(current_input, packet.preview)
        except ValueError:
            return _intent_apply_blocker(
                "selected_packet_fact_not_current",
                "Odczytaj aktualne źródła i zatwierdź nowy pakiet v2.",
                packet.evidence_ids,
            )
        if projected.planning_input_digest != snapshot.projected_planning_input_digest:
            return _intent_apply_blocker(
                "projected_planning_input_changed",
                "Odczytaj aktualny projected planning input i przygotuj nowy zamiar.",
                packet.evidence_ids,
            )
        evidence_ids = tuple(sorted(set(packet.evidence_ids) | set(projected.evidence_ids)))
        if evidence_ids != snapshot.evidence_ids:
            return _intent_apply_blocker(
                "generation_intent_evidence_changed",
                "Odczytaj aktualne evidence i przygotuj nowy zamiar.",
                evidence_ids,
            )
    except PlanningGenerationIntentBlocked as error:
        return _intent_apply_blocker(error.code, error.next_step, error.evidence_ids)
    except Exception:
        return _intent_apply_blocker(
            "generation_intent_currentness_unavailable",
            "Odczytaj aktualny planning input i zatwierdzony pakiet v2.",
            snapshot.evidence_ids,
        )
    return None


def planning_generation_intent_receipt_digest(
    value: PlanningGenerationIntentReceipt | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("receipt_id", None)
    payload.pop("receipt_digest", None)
    return canonical_json_digest(payload)


def _generation_intent_audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("context_digest")
    payload = event.details.get("payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


__all__ = [
    "PLANNING_GENERATION_INTENT_ACTION_TYPE",
    "PLANNING_GENERATION_INTENT_ADAPTER",
    "PlanningGenerationIntentBlocked",
    "PlanningGenerationIntentApplyBlocker",
    "PlanningGenerationIntentPreviewCommand",
    "PlanningGenerationIntentProposal",
    "PlanningGenerationIntentReceipt",
    "PlanningGenerationIntentSnapshot",
    "build_planning_generation_intent_proposal",
    "execute_planning_generation_intent_action",
    "load_planning_generation_intent_action",
    "planning_generation_intent_action",
    "prepare_planning_generation_intent_action",
    "validate_planning_generation_intent_action_payload",
]
