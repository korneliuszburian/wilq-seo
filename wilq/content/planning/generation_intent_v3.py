"""Exact approved v3 packet projection and local-only planning intent receipt."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_preview import (
    ResearchPacketV3Blocker,
    ResearchPacketV3InternalLink,
    ResearchPacketV3LegalRequirement,
    ResearchPacketV3PlanningContext,
    ResearchPacketV3Preview,
)
from wilq.content.workflow.research_packet_v3_receipt import (
    ResearchPacketV3ApprovalReceipt,
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

PLANNING_GENERATION_INTENT_V3_ACTION_TYPE = "content_planning_generation_intent_v3"
PLANNING_GENERATION_INTENT_V3_ADAPTER = "content_planning_generation_intent_v3_local_authority"
_ACTION_PREFIX = "act_content_planning_generation_intent_v3_"
_HEX64 = r"^[0-9a-f]{64}$"
_CURRENT_PACKET_LOADER = Callable[[str], ResearchPacketV3Preview]
PacketBlockerOwner = Literal["WILQ content workflow", "WILQ WordPress connector", "Wilku"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ApprovedPacketV3PlanningView(_FrozenModel):
    """One exact approval receipt plus the same currently observed semantic packet."""

    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1, max_length=240)
    receipt: ResearchPacketV3ApprovalReceipt
    approved_preview: ResearchPacketV3Preview


class ApprovedPacketV3PlanningProjection(_FrozenModel):
    """Whitelisted packet fields that may enter a planning-generation intent."""

    approval_receipt_digest: str = Field(pattern=_HEX64)
    approval_action_id: str = Field(min_length=1, max_length=240)
    work_item_id: str = Field(min_length=1, max_length=240)
    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=_HEX64)
    page_url: str = Field(min_length=1, max_length=2048)
    canonical_path: str = Field(min_length=1, max_length=2048)
    identity_digest: str = Field(pattern=_HEX64)
    material_meaning_digest: str = Field(pattern=_HEX64)
    source_pack_id: str = Field(min_length=1, max_length=240)
    source_pack_hash: str = Field(pattern=_HEX64)
    selected_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    planning_context: ResearchPacketV3PlanningContext
    cta_direction: str = Field(min_length=1)
    minimum_cta_blocks: int = Field(ge=1, le=4)
    required_cta_patterns: tuple[str, ...] = ()
    internal_links: tuple[ResearchPacketV3InternalLink, ...] = Field(min_length=1)
    regulatory_profile_id: str = Field(min_length=1, max_length=240)
    regulatory_profile_version: str = Field(min_length=1, max_length=120)
    legal_requirements: tuple[ResearchPacketV3LegalRequirement, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_projection(self) -> Self:
        if (
            self.packet_id != f"content_research_packet_v3_{self.packet_digest[:24]}"
            or not content_is_safe_public_url(self.page_url)
            or content_normalized_path(self.page_url) != self.canonical_path
        ):
            raise ValueError("Approved packet v3 planning projection identity does not match.")
        for name in ("selected_fact_ids", "evidence_ids", "required_cta_patterns"):
            values = getattr(self, name)
            if values != tuple(sorted(set(values))) or any(not item.strip() for item in values):
                raise ValueError(f"{name} must be sorted, unique and non-blank.")
        return self


class PlanningGenerationIntentV3Snapshot(_FrozenModel):
    schema_version: Literal["wilq_planning_generation_intent_snapshot_v3"] = (
        "wilq_planning_generation_intent_snapshot_v3"
    )
    intent_digest: str = Field(pattern=_HEX64)
    context_digest: str = Field(pattern=_HEX64)
    approval_receipt_digest: str = Field(pattern=_HEX64)
    approval_action_id: str = Field(min_length=1, max_length=240)
    work_item_id: str = Field(min_length=1, max_length=240)
    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=_HEX64)
    page_url: str = Field(min_length=1, max_length=2048)
    canonical_path: str = Field(min_length=1, max_length=2048)
    identity_digest: str = Field(pattern=_HEX64)
    material_meaning_digest: str = Field(pattern=_HEX64)
    source_pack_id: str = Field(min_length=1, max_length=240)
    source_pack_hash: str = Field(pattern=_HEX64)
    selected_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    planning_context: ResearchPacketV3PlanningContext
    cta_direction: str = Field(min_length=1)
    minimum_cta_blocks: int = Field(ge=1, le=4)
    required_cta_patterns: tuple[str, ...] = ()
    internal_links: tuple[ResearchPacketV3InternalLink, ...] = Field(min_length=1)
    regulatory_profile_id: str = Field(min_length=1, max_length=240)
    regulatory_profile_version: str = Field(min_length=1, max_length=120)
    legal_requirements: tuple[ResearchPacketV3LegalRequirement, ...] = Field(min_length=1)
    generation_performed: Literal[False] = False
    model_enqueued: Literal[False] = False
    external_write_attempted: Literal[False] = False

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        projection = ApprovedPacketV3PlanningProjection.model_validate(
            self.model_dump(mode="python", exclude={
                "schema_version", "intent_digest", "context_digest",
                "generation_performed", "model_enqueued", "external_write_attempted",
            }),
            strict=True,
        )
        if (
            self.context_digest != planning_generation_intent_v3_context_digest(projection)
            or self.intent_digest != planning_generation_intent_v3_digest(self.context_digest)
        ):
            raise ValueError("Planning generation intent v3 digest does not match.")
        return self


class PlanningGenerationIntentV3Proposal(_FrozenModel):
    schema_version: Literal["wilq_planning_generation_intent_proposal_v3"] = (
        "wilq_planning_generation_intent_proposal_v3"
    )
    action_id: str = Field(min_length=1, max_length=240)
    snapshot: PlanningGenerationIntentV3Snapshot

    @model_validator(mode="after")
    def require_exact_action_id(self) -> Self:
        if self.action_id != planning_generation_intent_v3_action_id(self.snapshot.intent_digest):
            raise ValueError("Planning generation intent v3 action ID does not match.")
        return self


class PlanningGenerationIntentV3Receipt(_FrozenModel):
    schema_version: Literal["wilq_planning_generation_intent_receipt_v3"] = (
        "wilq_planning_generation_intent_receipt_v3"
    )
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    snapshot: PlanningGenerationIntentV3Snapshot
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
            raise ValueError("Generation intent v3 receipt timestamp must be timezone-aware.")
        if self.receipt_digest != planning_generation_intent_v3_receipt_digest(self):
            raise ValueError("Planning generation intent v3 receipt digest does not match.")
        expected_id = f"content_planning_generation_intent_v3_receipt_{self.receipt_digest}"
        if self.receipt_id != expected_id:
            raise ValueError("Planning generation intent v3 receipt ID does not match.")
        return self


def resolve_approved_packet_v3_for_planning(
    *,
    store: ContentWorkflowStore,
    work_item_id: str,
    packet_id: str,
    expected_digest: str,
    current_preview_loader: _CURRENT_PACKET_LOADER | None = None,
) -> ApprovedPacketV3PlanningView | ResearchPacketV3Blocker:
    """Require the exact receipt, immutable reviewed record, and current semantic packet."""

    load_current = current_preview_loader or _load_current_packet
    try:
        receipt = store.load_research_packet_v3_approval_receipt(packet_id)
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        return _blocked(
            "research_packet_v3_receipt_unavailable",
            (),
            "Odczytaj ponownie receipt pakietu v3.",
        )
    if receipt is None:
        return _blocked(
            "research_packet_v3_approval_missing",
            _current_evidence_ids(load_current, work_item_id),
            "Zatwierdź dokładny pakiet v3 przez ActionObject przed przygotowaniem zamiaru.",
        )
    if receipt.packet_id != packet_id or receipt.packet_digest != expected_digest:
        return _blocked(
            "research_packet_v3_digest_mismatch",
            receipt.verification_evidence_ids,
            "Wybierz receipt zgodny z dokładnym ID i digestem pakietu v3.",
        )
    try:
        record = store.load_research_packet_v3_preview(receipt.packet_digest)
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        return _blocked(
            "research_packet_v3_snapshot_unavailable",
            receipt.verification_evidence_ids,
            "Odczytaj ponownie dokładny zapisany podgląd pakietu v3.",
        )
    if record is None:
        return _blocked(
            "research_packet_v3_snapshot_missing",
            receipt.verification_evidence_ids,
            "Odtwórz dokładny zapisany podgląd zatwierdzonego pakietu v3.",
        )
    approved = record.snapshot
    if (
        record.work_item_id != work_item_id
        or approved.work_item_id != work_item_id
        or record.preview_hash != expected_digest
        or approved.preview_hash != expected_digest
        or not record.has_exact_page_identity()
    ):
        return _blocked(
            "research_packet_v3_identity_mismatch",
            receipt.verification_evidence_ids,
            "Odczytaj receipt i pakiet v3 przypisane do dokładnej strony.",
        )
    try:
        current = load_current(work_item_id)
    except Exception:
        return _blocked(
            "research_packet_v3_current_read_unavailable",
            receipt.verification_evidence_ids,
            "Ponów dokładny odczyt bieżącego pakietu v3 przed przygotowaniem zamiaru.",
        )
    if current.status != "ready":
        blocker = current.blocker
        if blocker is not None:
            return blocker
        return _blocked(
            "research_packet_v3_current_blocked",
            receipt.verification_evidence_ids,
            "Ponów odczyt bieżącego pakietu v3.",
        )
    if (
        current.work_item_id != work_item_id
        or not current.has_exact_page_identity()
        or current.page_url != approved.page_url
        or current.canonical_path != approved.canonical_path
        or current.identity_digest != approved.identity_digest
    ):
        return _blocked(
            "research_packet_v3_identity_mismatch",
            current.verification_evidence_ids,
            "Odczytaj tożsamość dokładnej bieżącej strony i zatwierdź nowy pakiet v3.",
        )
    if current.preview_hash != expected_digest:
        return _blocked(
            "research_packet_v3_current_drift",
            current.verification_evidence_ids,
            "Pakiet v3 zmienił się semantycznie. Przygotuj i zatwierdź nowy dokładny pakiet.",
        )
    return ApprovedPacketV3PlanningView(
        packet_id=receipt.packet_id,
        packet_digest=receipt.packet_digest,
        work_item_id=work_item_id,
        receipt=receipt,
        approved_preview=approved,
    )


def project_approved_packet_v3_for_planning(
    view: ApprovedPacketV3PlanningView,
) -> ApprovedPacketV3PlanningProjection:
    """Project approved IDs, evidence, and bounded planning context without source text."""

    packet = view.approved_preview
    if packet.status != "ready" or packet.page_url is None or packet.canonical_path is None:
        raise ValueError("Approved research packet v3 is missing exact page identity.")
    if packet.planning_context is None or packet.preview_hash is None:
        raise ValueError("Approved research packet v3 is missing planning context.")
    evidence = set(view.receipt.verification_evidence_ids)
    evidence.update(
        evidence_id for fact in packet.selected_facts for evidence_id in fact.evidence_ids
    )
    evidence.update(
        evidence_id for link in packet.internal_links for evidence_id in link.evidence_ids
    )
    evidence.update(
        evidence_id for requirement in packet.legal_requirements
        for evidence_id in requirement.evidence_ids
    )
    return ApprovedPacketV3PlanningProjection(
        approval_receipt_digest=view.receipt.receipt_digest,
        approval_action_id=view.receipt.action_id,
        work_item_id=view.work_item_id,
        packet_id=view.packet_id,
        packet_digest=view.packet_digest,
        page_url=packet.page_url,
        canonical_path=packet.canonical_path,
        identity_digest=packet.identity_digest or "",
        material_meaning_digest=packet.material_meaning_digest or "",
        source_pack_id=packet.source_pack_id or "",
        source_pack_hash=packet.source_pack_hash or "",
        selected_fact_ids=tuple(sorted(fact.source_fact_id for fact in packet.selected_facts)),
        evidence_ids=tuple(sorted(evidence)),
        planning_context=packet.planning_context,
        cta_direction=packet.cta_direction or "",
        minimum_cta_blocks=packet.minimum_cta_blocks or 1,
        required_cta_patterns=tuple(sorted(set(packet.required_cta_patterns))),
        internal_links=packet.internal_links,
        regulatory_profile_id=packet.regulatory_profile_id or "",
        regulatory_profile_version=packet.regulatory_profile_version or "",
        legal_requirements=packet.legal_requirements,
    )


def planning_generation_intent_v3_context_digest(
    value: ApprovedPacketV3PlanningProjection | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    return canonical_json_digest(payload)


def planning_generation_intent_v3_digest(context_digest: str) -> str:
    return canonical_json_digest({
        "schema_version": "wilq_planning_generation_intent_snapshot_v3",
        "context_digest": context_digest,
    })


def planning_generation_intent_v3_action_id(intent_digest: str) -> str:
    return f"{_ACTION_PREFIX}{intent_digest}"


def build_planning_generation_intent_v3_proposal(
    projection: ApprovedPacketV3PlanningProjection,
) -> PlanningGenerationIntentV3Proposal:
    context_digest = planning_generation_intent_v3_context_digest(projection)
    intent_digest = planning_generation_intent_v3_digest(context_digest)
    snapshot = PlanningGenerationIntentV3Snapshot.model_validate(
        projection.model_dump(mode="python")
        | {
            "schema_version": "wilq_planning_generation_intent_snapshot_v3",
            "context_digest": context_digest,
            "intent_digest": intent_digest,
            "generation_performed": False,
            "model_enqueued": False,
            "external_write_attempted": False,
        },
        strict=True,
    )
    return PlanningGenerationIntentV3Proposal(
        action_id=planning_generation_intent_v3_action_id(intent_digest),
        snapshot=snapshot,
    )


def prepare_planning_generation_intent_v3_action(
    *,
    work_item_id: str,
    packet_id: str,
    packet_digest: str,
    store: ContentWorkflowStore,
    current_preview_loader: _CURRENT_PACKET_LOADER | None = None,
) -> PlanningGenerationIntentV3Proposal:
    view = resolve_approved_packet_v3_for_planning(
        store=store,
        work_item_id=work_item_id,
        packet_id=packet_id,
        expected_digest=packet_digest,
        current_preview_loader=current_preview_loader,
    )
    if isinstance(view, ResearchPacketV3Blocker):
        raise PlanningGenerationIntentV3Blocked(view)
    return build_planning_generation_intent_v3_proposal(
        project_approved_packet_v3_for_planning(view)
    )


class PlanningGenerationIntentV3Blocked(ValueError):
    def __init__(self, blocker: ResearchPacketV3Blocker) -> None:
        super().__init__(blocker.code)
        self.blocker = blocker


def planning_generation_intent_v3_action(
    proposal: PlanningGenerationIntentV3Proposal,
) -> ActionObject:
    snapshot = proposal.snapshot
    return ActionObject(
        id=proposal.action_id,
        title="Zatwierdź lokalny zamiar planowania z pakietu v3",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(snapshot.evidence_ids),
        human_diagnosis=(
            "Apply zapisuje wyłącznie lokalny receipt zamiaru dla dokładnego zatwierdzonego "
            "pakietu v3. Nie uruchamia modelu ani WordPressa."
        ),
        recommended_reason="Sprawdź dokładny pakiet v3, stronę, fakty i kontekst planowania.",
        payload={
            "action_type": PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "planning_generation_intent_v3": snapshot.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": proposal.action_id,
                    "operation_type": "record_one_v3_planning_generation_intent",
                    "work_item_id": snapshot.work_item_id,
                    "packet_id": snapshot.packet_id,
                    "packet_digest": snapshot.packet_digest,
                    "page_url": snapshot.page_url,
                    "canonical_path": snapshot.canonical_path,
                    "selected_fact_ids": list(snapshot.selected_fact_ids),
                    "evidence_ids": list(snapshot.evidence_ids),
                    "planning_context": snapshot.planning_context.model_dump(mode="json"),
                    "apply_allowed": True,
                    "generation_performed": False,
                    "model_enqueued": False,
                    "external_write_attempted": False,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "generation_performed_at_apply": False,
            "model_enqueued_at_apply": False,
            "external_write_attempted": False,
        },
        validation_status="not_validated",
        created_by="system_core_planning_generation_intent_v3",
    )


def load_planning_generation_intent_v3_action(
    action_id: str,
    *,
    store: ContentWorkflowStore,
) -> ActionObject | None:
    proposal = store.load_planning_generation_intent_v3_proposal(action_id)
    return None if proposal is None else planning_generation_intent_v3_action(proposal)


def validate_planning_generation_intent_v3_action_payload(payload: dict[str, Any]) -> list[str]:
    try:
        snapshot = PlanningGenerationIntentV3Snapshot.model_validate_json(
            json.dumps(payload.get("planning_generation_intent_v3", {}), sort_keys=True),
            strict=True,
        )
        proposal = PlanningGenerationIntentV3Proposal(
            action_id=planning_generation_intent_v3_action_id(snapshot.intent_digest),
            snapshot=snapshot,
        )
    except (TypeError, ValueError, ValidationError):
        return ["Planning generation intent v3 snapshot is invalid."]
    return (
        []
        if payload == planning_generation_intent_v3_action(proposal).payload
        else ["Planning generation intent v3 ActionObject payload is not exact."]
    )


def execute_planning_generation_intent_v3_action(
    action: ActionObject,
    *,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
    current_preview_loader: _CURRENT_PACKET_LOADER | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        proposal = store.load_planning_generation_intent_v3_proposal(action.id)
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        return _apply_blocked(
            "generation_intent_v3_proposal_unavailable",
            "Odczytaj ponownie dokładny lokalny zamiar v3.",
            (),
        )
    if proposal is None:
        return _apply_blocked(
            "generation_intent_v3_proposal_missing",
            "Odczytaj ponownie dokładny lokalny zamiar v3.",
            (),
        )
    if action.payload != planning_generation_intent_v3_action(proposal).payload:
        return _apply_blocked(
            "generation_intent_v3_action_changed",
            "Odczytaj ponownie niezmieniony ActionObject zamiaru v3.",
            proposal.snapshot.evidence_ids,
        )
    view = resolve_approved_packet_v3_for_planning(
        store=store,
        work_item_id=proposal.snapshot.work_item_id,
        packet_id=proposal.snapshot.packet_id,
        expected_digest=proposal.snapshot.packet_digest,
        current_preview_loader=current_preview_loader,
    )
    if isinstance(view, ResearchPacketV3Blocker):
        return _apply_blocked(view.code, view.safe_next_step, view.evidence_ids, view.owner)
    current_projection = project_approved_packet_v3_for_planning(view)
    current_proposal = build_planning_generation_intent_v3_proposal(current_projection)
    if current_proposal.snapshot != proposal.snapshot:
        return _apply_blocked(
            "generation_intent_v3_projection_changed",
            "Odczytaj ponownie zatwierdzony pakiet v3 i przygotuj nowy zamiar.",
            current_projection.evidence_ids,
        )
    return _record_generation_intent_v3_receipt(
        action=action,
        proposal=proposal,
        store=store,
        audit_events=audit_events,
        confirmed_by=confirmed_by,
    )


def _record_generation_intent_v3_receipt(
    *,
    action: ActionObject,
    proposal: PlanningGenerationIntentV3Proposal,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
) -> tuple[dict[str, Any], list[str]]:
    payload_digest = canonical_json_digest(action.payload)
    try:
        chain, _blockers = revision_bound_action_chain(
            [event for event in audit_events if event.action_id == action.id],
            confirmed_by=confirmed_by,
            binding_from_event=_generation_intent_v3_audit_binding,
            expected_binding=(proposal.snapshot.context_digest, payload_digest),
        )
    except Exception:
        return _apply_blocked(
            "generation_intent_v3_audit_chain_unavailable",
            "Odtwórz pełny audyt preview, review, confirm i impact dla zamiaru v3.",
            proposal.snapshot.evidence_ids,
        )
    if chain is None:
        return _apply_blocked(
            "generation_intent_v3_audit_chain_incomplete",
            "Wykonaj ponownie pełny lifecycle preview, review, confirm i impact.",
            proposal.snapshot.evidence_ids,
        )
    preview, review, confirmation, impact = chain
    checked = review.details.get("checked_items", [])
    if not isinstance(checked, list) or "reviewed_exact_generation_intent_v3" not in checked:
        return _apply_blocked(
            "generation_intent_v3_review_attestation_missing",
            "Przeczytaj dokładny zamiar v3 i zapisz decyzję review.",
            proposal.snapshot.evidence_ids,
        )
    receipt = _generation_intent_v3_receipt(
        action=action,
        proposal=proposal,
        preview=preview,
        review=review,
        confirmation=confirmation,
        impact=impact,
        payload_digest=payload_digest,
    )
    try:
        status = store.record_planning_generation_intent_v3_receipt(receipt)
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        return _apply_blocked(
            "generation_intent_v3_receipt_unavailable",
            "Odczytaj stan lokalnego receipt zamiaru v3 i ponów apply.",
            proposal.snapshot.evidence_ids,
        )
    if status == "conflict":
        return _apply_blocked(
            "generation_intent_v3_receipt_conflict",
            "Odczytaj istniejący receipt i przygotuj nowy zamiar v3.",
            proposal.snapshot.evidence_ids,
        )
    try:
        stored = store.load_planning_generation_intent_v3_receipt(action.id)
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        return _apply_blocked(
            "generation_intent_v3_receipt_unavailable",
            "Odczytaj ponownie lokalny receipt zamiaru v3.",
            proposal.snapshot.evidence_ids,
        )
    if stored is None:
        return _apply_blocked(
            "generation_intent_v3_receipt_unavailable",
            "Odczytaj ponownie lokalny receipt zamiaru v3.",
            proposal.snapshot.evidence_ids,
        )
    return (
        {
            "status": status,
            "receipt_id": stored.receipt_id,
            "receipt_digest": stored.receipt_digest,
            "action_id": stored.action_id,
            "generation_performed": False,
            "model_enqueued": False,
            "external_write_attempted": False,
        },
        [],
    )


def _generation_intent_v3_receipt(
    *,
    action: ActionObject,
    proposal: PlanningGenerationIntentV3Proposal,
    preview: AuditEvent,
    review: AuditEvent,
    confirmation: AuditEvent,
    impact: AuditEvent,
    payload_digest: str,
) -> PlanningGenerationIntentV3Receipt:
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
    provisional = PlanningGenerationIntentV3Receipt.model_construct(**cast(Any, fields))
    digest = planning_generation_intent_v3_receipt_digest(provisional)
    return PlanningGenerationIntentV3Receipt.model_validate(
        provisional.model_dump(mode="python")
        | {
            "receipt_id": f"content_planning_generation_intent_v3_receipt_{digest}",
            "receipt_digest": digest,
        }
    )


def planning_generation_intent_v3_receipt_digest(
    value: PlanningGenerationIntentV3Receipt | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("receipt_id", None)
    payload.pop("receipt_digest", None)
    return canonical_json_digest(payload)


def _generation_intent_v3_audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("context_digest")
    payload = event.details.get("payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


def _apply_blocked(
    code: str,
    next_step: str,
    evidence_ids: tuple[str, ...],
    owner: PacketBlockerOwner = "WILQ content workflow",
) -> tuple[dict[str, Any], list[str]]:
    blocker = ResearchPacketV3Blocker(
        code=code,
        owner=owner,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=next_step,
    )
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


def _blocked(
    code: str,
    evidence_ids: tuple[str, ...],
    next_step: str,
    owner: PacketBlockerOwner = "WILQ content workflow",
) -> ResearchPacketV3Blocker:
    return ResearchPacketV3Blocker(
        code=code,
        owner=owner,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=next_step,
    )


def _current_evidence_ids(
    loader: _CURRENT_PACKET_LOADER,
    work_item_id: str,
) -> tuple[str, ...]:
    try:
        current = loader(work_item_id)
    except Exception:
        return ()
    if current.status == "ready":
        return current.verification_evidence_ids
    return () if current.blocker is None else current.blocker.evidence_ids


def _load_current_packet(work_item_id: str) -> ResearchPacketV3Preview:
    from apps.api.wilq_api.routers.content_research_packet_v3_preview import (
        read_current_research_packet_v3_preview,
    )

    return read_current_research_packet_v3_preview(work_item_id)


__all__ = [
    "PLANNING_GENERATION_INTENT_V3_ACTION_TYPE",
    "PLANNING_GENERATION_INTENT_V3_ADAPTER",
    "ApprovedPacketV3PlanningProjection",
    "ApprovedPacketV3PlanningView",
    "PlanningGenerationIntentV3Blocked",
    "PlanningGenerationIntentV3Proposal",
    "PlanningGenerationIntentV3Receipt",
    "PlanningGenerationIntentV3Snapshot",
    "build_planning_generation_intent_v3_proposal",
    "execute_planning_generation_intent_v3_action",
    "load_planning_generation_intent_v3_action",
    "planning_generation_intent_v3_action",
    "prepare_planning_generation_intent_v3_action",
    "project_approved_packet_v3_for_planning",
    "resolve_approved_packet_v3_for_planning",
    "validate_planning_generation_intent_v3_action_payload",
]
