"""Local receipt-only ActionObject for an exact current full-text generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wilq.actions.action_chain import ActionChain, revision_bound_action_chain
from wilq.content.drafts.full_draft_generation_v3_contracts import (
    FullDraftGenerationV3Receipt,
    FullDraftGenerationV3Snapshot,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.proposal_v3_packet_read import resolve_v3_planning_packet_context
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.decisions.production import canonical_json_digest
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

FULL_DRAFT_GENERATION_V3_ACTION_TYPE = "content_full_draft_generation_v3"
FULL_DRAFT_GENERATION_V3_ADAPTER = "content_full_draft_generation_v3_local_authority"


def full_draft_generation_v3_snapshot(
    proposal: ContentPlanningProposal,
    *,
    store: ContentWorkflowStore,
) -> FullDraftGenerationV3Snapshot:
    context_read = resolve_v3_planning_packet_context(
        proposal=proposal,
        workflow_store=store,
        proposal_store=ContentPlanningProposalStore(store.path),
    )
    context = context_read.context
    if context is None or not context.current_authority:
        raise ValueError(context_read.blocker_code or "full_draft_v3_context_unavailable")
    packet = context.packet
    return FullDraftGenerationV3Snapshot(
        work_item_id=proposal.work_item_id,
        subject_key=context.subject.subject_key,
        content_kind=proposal.content_kind,
        service_card_id=proposal.service_card_id,
        page_url=context.planning_input.final_canonical_url or "",
        proposal_id=proposal.proposal_id or "",
        proposal_payload_digest=canonical_json_digest(proposal.model_dump(mode="json")),
        planning_digest=proposal.planning_digest,
        planning_input_digest=context.planning_input.planning_input_digest,
        frozen_input_digest=canonical_json_digest(context.planning_input.model_dump(mode="json")),
        packet_id=context.receipt.packet_id,
        packet_digest=context.receipt.packet_digest,
        packet_receipt_digest=context.receipt.receipt_digest,
        identity_action_id=packet.per_url_delivery_identity_action_id or "",
        identity_digest=packet.identity_digest or "",
        source_pack_id=packet.source_pack_id or "",
        source_pack_hash=packet.source_pack_hash or "",
        evidence_ids=tuple(sorted(set(context.planning_input.evidence_ids))),
    )


def full_draft_generation_v3_action(snapshot: FullDraftGenerationV3Snapshot) -> ActionObject:
    return ActionObject(
        id=snapshot.action_id,
        title="Przygotuj pełny tekst z dokładnego planu v3",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(snapshot.evidence_ids),
        human_diagnosis=(
            "Apply zapisuje lokalną zgodę na jeden pełny tekst. Dispatch uruchamia tekst."
        ),
        recommended_reason="Sprawdź dokładny plan, pakiet, stronę i źródła.",
        created_by="system_core_full_draft_generation_v3",
        validation_status="not_validated",
        payload={
            "action_type": FULL_DRAFT_GENERATION_V3_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "full_draft_generation_v3": snapshot.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": snapshot.action_id,
                    "operation_type": "authorize_one_full_draft_v3",
                    "apply_allowed": True,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "generation_performed_at_apply": False,
            "model_enqueued_at_apply": False,
            "external_write_attempted": False,
        },
    )


def load_full_draft_generation_v3_action(
    action_id: str, *, store: ContentWorkflowStore
) -> ActionObject | None:
    snapshot = store.load_full_draft_generation_v3_snapshot(action_id)
    return None if snapshot is None else full_draft_generation_v3_action(snapshot)


def validate_full_draft_generation_v3_payload(payload: dict[str, Any]) -> list[str]:
    try:
        snapshot = FullDraftGenerationV3Snapshot.model_validate(payload["full_draft_generation_v3"])
        if full_draft_generation_v3_action(snapshot).payload == payload:
            return []
    except (ValueError, KeyError, TypeError):
        pass
    return ["Full draft v3 payload must match the exact authorization snapshot."]


def full_draft_generation_v3_chain(
    snapshot: FullDraftGenerationV3Snapshot, events: list[AuditEvent], confirmed_by: str
) -> ActionChain:
    action = full_draft_generation_v3_action(snapshot)
    chain, _errors = revision_bound_action_chain(
        [event for event in events if event.action_id == action.id],
        confirmed_by=confirmed_by,
        binding_from_event=_audit_binding,
        expected_binding=(snapshot.context_digest, canonical_json_digest(action.payload)),
    )
    if chain is None or "reviewed_exact_full_draft_v3" not in chain[1].details.get(
        "checked_items", []
    ):
        raise ValueError("full_draft_v3_audit_chain_incomplete")
    return chain


def execute_full_draft_generation_v3_action(
    action: ActionObject,
    *,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
) -> tuple[dict[str, Any], list[str]]:
    try:
        snapshot = store.load_full_draft_generation_v3_snapshot(action.id)
        if snapshot is None or action.payload != full_draft_generation_v3_action(snapshot).payload:
            raise ValueError("full_draft_v3_action_changed")
        proposal = ContentPlanningProposalStore(store.path).latest_for_planning_digest(
            snapshot.work_item_id, snapshot.planning_digest
        )
        if proposal is None or full_draft_generation_v3_snapshot(proposal, store=store) != snapshot:
            raise ValueError("full_draft_v3_plan_changed")
        preview, review, confirmation, impact = full_draft_generation_v3_chain(
            snapshot, audit_events, confirmed_by
        )
        receipt = FullDraftGenerationV3Receipt(
            snapshot=snapshot,
            action_payload_digest=canonical_json_digest(action.payload),
            preview_audit_id=preview.id,
            review_audit_id=review.id,
            confirmation_audit_id=confirmation.id,
            impact_audit_id=impact.id,
            reviewed_by=review.actor,
            confirmed_by=confirmation.actor,
            created_at=review.created_at,
        )
        status = store.record_full_draft_generation_v3_receipt(receipt)
        if status == "conflict":
            raise ValueError("full_draft_v3_receipt_conflict")
        return {
            "status": status,
            "receipt_digest": receipt.receipt_digest,
            "generation_performed": False,
            "model_enqueued": False,
            "external_write_attempted": False,
        }, []
    except ValueError as error:
        return {
            "status": "blocked",
            "blocker": {
                "code": str(error),
                "owner": "WILQ content workflow",
                "evidence_ids": action.evidence_ids,
                "safe_next_step": "Odśwież exact plan i ponów pełny lifecycle autoryzacji tekstu.",
            },
        }, ["Autoryzacja pełnego tekstu nie jest aktualna."]


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("context_digest")
    payload = event.details.get("payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None
