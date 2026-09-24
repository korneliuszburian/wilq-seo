"""Local ActionObject authority for an immutable reviewed v3 research packet."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_receipt import (
    ResearchPacketV3ApprovalReceipt,
    ResearchPacketV3PreviewRecord,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)

RESEARCH_PACKET_V3_ACTION_TYPE = "content_research_packet_v3_approval"
RESEARCH_PACKET_V3_ACTION_ADAPTER = "content_research_packet_v3_local_authority"
_ACTION_PREFIX = "act_content_research_packet_v3_"


class ResearchPacketV3ApplyBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["blocked"] = "blocked"
    code: str = Field(min_length=1)
    owner: Literal["WILQ content workflow", "WILQ WordPress connector", "Wilku"]
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)
    generation_allowed: Literal[False] = False
    external_write_attempted: Literal[False] = False


def research_packet_v3_action_id(preview_hash: str) -> str:
    return f"{_ACTION_PREFIX}{preview_hash}"


def research_packet_v3_action(record: ResearchPacketV3PreviewRecord) -> ActionObject:
    if not record.has_exact_page_identity():
        raise ValueError("research_packet_v3_page_identity_missing")
    preview = record.snapshot
    return ActionObject(
        id=research_packet_v3_action_id(record.preview_hash),
        title="Zatwierdź dokładny pakiet badawczy v3",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(preview.verification_evidence_ids),
        human_diagnosis="Lokalna decyzja dotyczy całego dokładnego pakietu i jego źródeł.",
        recommended_reason="Sprawdź wszystkie fakty, wymagania i kontekst przed zatwierdzeniem.",
        payload={
            "action_type": RESEARCH_PACKET_V3_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "research_packet_v3_preview": record.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": record.preview_hash,
                    "operation_type": "approve_exact_research_packet_v3",
                    "work_item_id": record.work_item_id,
                    "preview_hash": record.preview_hash,
                    "source_pack_hash": preview.source_pack_hash,
                    "apply_allowed": True,
                    "api_mutation_ready": True,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "generation_allowed": False,
            "packet_write_allowed": False,
        },
        validation_status="not_validated",
        created_by="system_core_research_packet_v3",
    )


def load_research_packet_v3_action(
    action_id: str, *, store: ContentWorkflowStore | None = None
) -> ActionObject | None:
    if not action_id.startswith(_ACTION_PREFIX):
        return None
    preview_hash = action_id.removeprefix(_ACTION_PREFIX)
    if len(preview_hash) != 64 or any(char not in "0123456789abcdef" for char in preview_hash):
        return None
    record = (store or content_workflow_store()).load_research_packet_v3_preview(preview_hash)
    if record is None or not record.has_exact_page_identity():
        return None
    return research_packet_v3_action(record)


def prepare_research_packet_v3_action(
    record: ResearchPacketV3PreviewRecord,
    *,
    store: ContentWorkflowStore | None = None,
) -> ActionObject:
    if not record.has_exact_page_identity():
        raise ValueError("research_packet_v3_page_identity_missing")
    workflow_store = store or content_workflow_store()
    status = workflow_store.record_research_packet_v3_preview(record)
    if status == "conflict":
        raise ValueError("research_packet_v3_preview_conflict")
    stored = workflow_store.load_research_packet_v3_preview(record.preview_hash)
    if stored is None or stored.snapshot.semantic_payload() != record.snapshot.semantic_payload():
        raise ValueError("research_packet_v3_stored_preview_missing_or_changed")
    return research_packet_v3_action(stored)


def parse_research_packet_v3_action_record(value: object) -> ResearchPacketV3PreviewRecord:
    return ResearchPacketV3PreviewRecord.model_validate_json(
        json.dumps(value, sort_keys=True), strict=True
    )


def validate_research_packet_v3_action_payload(payload: dict[str, Any]) -> list[str]:
    try:
        record = parse_research_packet_v3_action_record(
            payload.get("research_packet_v3_preview", {})
        )
    except (TypeError, ValueError, ValidationError):
        return ["Exact research packet v3 action preview is invalid."]
    if not record.has_exact_page_identity():
        return ["Exact research packet v3 page identity is missing."]
    return (
        []
        if payload == research_packet_v3_action(record).payload
        else ["Research packet v3 ActionObject payload is not exact."]
    )


def execute_research_packet_v3_action(
    action: ActionObject,
    *,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        record = parse_research_packet_v3_action_record(
            action.payload.get("research_packet_v3_preview", {})
        )
    except (TypeError, ValueError, ValidationError):
        return _blocked("research_packet_v3_action_invalid", tuple(action.evidence_ids),
                        "Odczytaj ponownie dokładną akcję pakietu v3.")
    if not record.has_exact_page_identity():
        return _blocked(
            "research_packet_v3_page_identity_missing",
            record.snapshot.verification_evidence_ids,
            "Odczytaj ponownie dokładny adres strony i ścieżkę kanoniczną przed review.",
        )
    stored = store.load_research_packet_v3_preview(record.preview_hash)
    if (
        stored != record
        or action.id != research_packet_v3_action_id(record.preview_hash)
        or action.payload != research_packet_v3_action(record).payload
    ):
        return _blocked("research_packet_v3_action_changed", tuple(action.evidence_ids),
                        "Przygotuj nową dokładną akcję pakietu v3.")
    try:
        from apps.api.wilq_api.routers.content_research_packet_v3_preview import (
            read_current_research_packet_v3_preview,
        )

        current = read_current_research_packet_v3_preview(record.work_item_id)
    except Exception:
        return _blocked("research_packet_v3_current_read_unavailable",
                        record.snapshot.verification_evidence_ids,
                        "Ponów odczyt bieżącego pakietu v3 przed zatwierdzeniem.")
    if current.status != "ready":
        blocker = current.blocker
        if blocker is None:
            return _blocked("research_packet_v3_current_blocked",
                            record.snapshot.verification_evidence_ids,
                            "Ponów odczyt bieżącego pakietu v3.")
        return _blocked(blocker.code, blocker.evidence_ids,
                        blocker.safe_next_step, blocker.owner)
    if not current.has_exact_page_identity():
        return _blocked(
            "research_packet_v3_page_identity_missing",
            current.verification_evidence_ids,
            "Odczytaj ponownie dokładny adres strony i ścieżkę kanoniczną przed review.",
        )
    if current.preview_hash != record.preview_hash:
        return _blocked("research_packet_v3_current_drift",
                        current.verification_evidence_ids,
                        "Treść pakietu zmieniła się. Przygotuj nowy dokładny review.")
    payload_digest = canonical_json_digest(action.payload)
    chain, blockers = revision_bound_action_chain(
        [event for event in audit_events if event.action_id == action.id],
        confirmed_by=confirmed_by,
        binding_from_event=_audit_binding,
        expected_binding=(record.preview_hash, payload_digest),
    )
    if chain is None:
        return _blocked("research_packet_v3_action_chain_missing",
                        current.verification_evidence_ids,
                        "Przeprowadź ponownie pełny review dokładnej akcji.")
    preview_audit, review, confirmation, impact = chain
    checked = review.details.get("checked_items", [])
    if not isinstance(checked, list) or "reviewed_full_packet" not in checked:
        return _blocked("reviewed_full_packet_missing", current.verification_evidence_ids,
                        "Przeczytaj pełny pakiet i zapisz dokładną decyzję review.")
    receipt = ResearchPacketV3ApprovalReceipt.from_action_chain(
        preview_hash=record.preview_hash,
        action_id=action.id,
        action_payload_digest=payload_digest,
        preview_audit_event_id=preview_audit.id,
        review_audit_event_id=review.id,
        confirmation_audit_event_id=confirmation.id,
        impact_audit_event_id=impact.id,
        review_actor=review.actor,
        verification_evidence_ids=current.verification_evidence_ids,
        verification_evidence_digest=current.verification_evidence_digest or "",
        approved_at=review.created_at,
    )
    status, stored_receipt = store._record_research_packet_v3_approval_receipt(receipt)
    if status == "conflict":
        return _blocked("research_packet_v3_receipt_conflict",
                        current.verification_evidence_ids,
                        "Odczytaj wcześniejszy receipt i przygotuj nową akcję "
                        "dla zmienionego pakietu.")
    return {
        "packet_id": stored_receipt.packet_id,
        "packet_digest": stored_receipt.packet_digest,
        "receipt_digest": stored_receipt.receipt_digest,
        "review_audit_event_id": stored_receipt.review_audit_event_id,
        "verification_evidence_ids": list(stored_receipt.verification_evidence_ids),
        "verification_evidence_digest": stored_receipt.verification_evidence_digest,
        "status": status,
        "currentness": "not_asserted",
        "external_write_attempted": False,
        "generation_allowed": False,
    }, []


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context_digest = event.details.get("context_digest")
    payload_digest = event.details.get("payload_digest")
    if isinstance(context_digest, str) and isinstance(payload_digest, str):
        return context_digest, payload_digest
    return None


def _blocked(
    code: str,
    evidence_ids: tuple[str, ...],
    next_step: str,
    owner: str = "WILQ content workflow",
) -> tuple[dict[str, Any], list[str]]:
    accepted_owner: Literal["WILQ content workflow", "WILQ WordPress connector", "Wilku"] = (
        "WILQ WordPress connector" if owner == "WILQ WordPress connector"
        else "Wilku" if owner == "Wilku" else "WILQ content workflow"
    )
    blocker = ResearchPacketV3ApplyBlocker(
        code=code,
        owner=accepted_owner,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=next_step,
    )
    return blocker.model_dump(mode="json"), [next_step]


__all__ = [
    "RESEARCH_PACKET_V3_ACTION_ADAPTER",
    "RESEARCH_PACKET_V3_ACTION_TYPE",
    "execute_research_packet_v3_action",
    "load_research_packet_v3_action",
    "parse_research_packet_v3_action_record",
    "prepare_research_packet_v3_action",
    "research_packet_v3_action",
    "research_packet_v3_action_id",
    "validate_research_packet_v3_action_payload",
]
