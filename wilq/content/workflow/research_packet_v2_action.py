"""Local ActionObject authority for an immutable reviewed v2 research packet."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v2_receipt import (
    ResearchPacketV2ApprovalReceipt,
    ResearchPacketV2PreviewRecord,
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

RESEARCH_PACKET_V2_ACTION_TYPE = "content_research_packet_v2_approval"
RESEARCH_PACKET_V2_ACTION_ADAPTER = "content_research_packet_v2_local_authority"
_ACTION_PREFIX = "act_content_research_packet_v2_"


def research_packet_v2_action_id(preview_hash: str) -> str:
    return f"{_ACTION_PREFIX}{preview_hash}"


def research_packet_v2_action(record: ResearchPacketV2PreviewRecord) -> ActionObject:
    preview = record.snapshot
    return ActionObject(
        id=research_packet_v2_action_id(record.preview_hash),
        title="Zatwierdź dokładny pakiet badawczy v2",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(preview.evidence_ids),
        human_diagnosis="Lokalna decyzja dotyczy całego dokładnego pakietu i jego źródeł.",
        recommended_reason="Sprawdź wszystkie fakty, wymagania i kontekst przed zatwierdzeniem.",
        payload={
            "action_type": RESEARCH_PACKET_V2_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "research_packet_v2_preview": record.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": record.preview_hash,
                    "operation_type": "approve_exact_research_packet_v2",
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
        created_by="system_core_research_packet_v2",
    )


def load_research_packet_v2_action(
    action_id: str, *, store: ContentWorkflowStore | None = None
) -> ActionObject | None:
    if not action_id.startswith(_ACTION_PREFIX):
        return None
    preview_hash = action_id.removeprefix(_ACTION_PREFIX)
    if len(preview_hash) != 64 or any(char not in "0123456789abcdef" for char in preview_hash):
        return None
    record = (store or content_workflow_store()).load_research_packet_v2_preview(preview_hash)
    return None if record is None else research_packet_v2_action(record)


def prepare_research_packet_v2_action(
    record: ResearchPacketV2PreviewRecord,
    *,
    store: ContentWorkflowStore | None = None,
) -> ActionObject:
    workflow_store = store or content_workflow_store()
    status = workflow_store.record_research_packet_v2_preview(record)
    if status == "conflict":
        raise ValueError("research_packet_v2_preview_conflict")
    stored = workflow_store.load_research_packet_v2_preview(record.preview_hash)
    if stored != record:
        raise ValueError("research_packet_v2_stored_preview_missing_or_changed")
    return research_packet_v2_action(stored)


def parse_research_packet_v2_action_record(value: object) -> ResearchPacketV2PreviewRecord:
    return ResearchPacketV2PreviewRecord.model_validate_json(
        json.dumps(value, sort_keys=True), strict=True
    )


def validate_research_packet_v2_action_payload(payload: dict[str, Any]) -> list[str]:
    try:
        record = parse_research_packet_v2_action_record(
            payload.get("research_packet_v2_preview", {})
        )
    except (TypeError, ValueError, ValidationError):
        return ["Exact research packet v2 action preview is invalid."]
    return (
        []
        if payload == research_packet_v2_action(record).payload
        else ["Research packet v2 ActionObject payload is not exact."]
    )


def execute_research_packet_v2_action(
    action: ActionObject,
    *,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        record = parse_research_packet_v2_action_record(
            action.payload.get("research_packet_v2_preview", {})
        )
    except (TypeError, ValueError, ValidationError):
        return None, ["Research packet v2 ActionObject preview is invalid."]
    stored = store.load_research_packet_v2_preview(record.preview_hash)
    if (
        stored != record
        or action.id != research_packet_v2_action_id(record.preview_hash)
        or action.payload != research_packet_v2_action(record).payload
    ):
        return None, ["Research packet v2 ActionObject changed before apply."]
    payload_digest = canonical_json_digest(action.payload)
    chain, blockers = revision_bound_action_chain(
        [event for event in audit_events if event.action_id == action.id],
        confirmed_by=confirmed_by,
        binding_from_event=_audit_binding,
        expected_binding=(record.preview_hash, payload_digest),
    )
    if chain is None:
        return None, [blockers[0].reason]
    preview_audit, review, confirmation, impact = chain
    checked = review.details.get("checked_items", [])
    if not isinstance(checked, list) or "reviewed_full_packet" not in checked:
        return None, ["reviewed_full_packet attestation is required."]
    receipt = ResearchPacketV2ApprovalReceipt.from_action_chain(
        preview_hash=record.preview_hash,
        action_id=action.id,
        action_payload_digest=payload_digest,
        preview_audit_event_id=preview_audit.id,
        review_audit_event_id=review.id,
        confirmation_audit_event_id=confirmation.id,
        impact_audit_event_id=impact.id,
        review_actor=review.actor,
        approved_at=review.created_at,
    )
    status = store._record_research_packet_v2_approval_receipt(receipt)
    if status == "conflict":
        return None, ["Research packet v2 approval receipt conflicts with an earlier decision."]
    return {
        "packet_id": receipt.packet_id,
        "packet_digest": receipt.packet_digest,
        "receipt_digest": receipt.receipt_digest,
        "review_audit_event_id": receipt.review_audit_event_id,
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


__all__ = [
    "RESEARCH_PACKET_V2_ACTION_ADAPTER",
    "RESEARCH_PACKET_V2_ACTION_TYPE",
    "execute_research_packet_v2_action",
    "load_research_packet_v2_action",
    "parse_research_packet_v2_action_record",
    "prepare_research_packet_v2_action",
    "research_packet_v2_action",
    "research_packet_v2_action_id",
    "validate_research_packet_v2_action_payload",
]
