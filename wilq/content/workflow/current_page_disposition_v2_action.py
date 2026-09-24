"""ActionObject lifecycle for local, append-only current-page KEEP decisions."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from wilq.content.workflow.current_disposition_authority import (
    CURRENT_DISPOSITION_MUTATION_ADAPTER,
)
from wilq.content.workflow.current_page_disposition_v2 import (
    CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE,
    CurrentPageDispositionV2Proposal,
    build_current_page_disposition_v2_receipt,
)
from wilq.content.workflow.current_page_evidence import (
    CurrentPageEvidenceResponse,
    current_page_material_is_current,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)


def current_page_disposition_v2_action(
    proposal: CurrentPageDispositionV2Proposal,
    *,
    current_evidence: CurrentPageEvidenceResponse | None = None,
) -> ActionObject:
    snapshot = proposal.snapshot
    stale = current_evidence is not None and (
        not current_page_material_is_current(current_evidence)
        or current_evidence.material_meaning_digest != snapshot.material_meaning_digest
    )
    payload = {
        "action_type": CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE,
        "connector": "wordpress_ekologus",
        "mode": "apply",
        "local_authority_only": True,
        "current_page_disposition_v2": proposal.model_dump(mode="json"),
        "payload_preview": [
            {
                "id": proposal.proposal_id,
                "operation_type": "record_current_page_disposition_v2_receipt",
                "work_item_id": snapshot.work_item_id,
                "page_url": snapshot.page_url,
                "disposition": "keep",
                "apply_allowed": not stale,
                "api_mutation_ready": not stale,
            }
        ],
        "apply_allowed": not stale,
        "api_mutation_ready": not stale,
        "destructive": False,
        "generation_allowed": False,
    }
    if stale:
        payload["runtime_blockers"] = [
            "Current page material or WordPress freshness changed after this proposal."
        ]
    return ActionObject(
        id=proposal.proposal_id,
        title="Zatwierdź zachowanie exact adresu strony",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.blocked if stale else ActionStatus.ready_to_apply,
        evidence_ids=sorted(set(snapshot.current_evidence_ids + snapshot.catalog_evidence_ids)),
        human_diagnosis=(
            "To jest lokalna propozycja KEEP dla dokładnego bieżącego materiału strony."
        ),
        recommended_reason="Sprawdź oryginalny zestaw dowodów przed review i potwierdzeniem.",
        payload=payload,
        validation_status="not_validated",
        created_by="system_core_current_page_disposition_v2",
    )


def load_current_page_disposition_v2_action(action_id: str) -> ActionObject | None:
    from wilq.content.workflow.store.store import content_workflow_store

    proposal = content_workflow_store().load_current_page_disposition_v2_proposal(action_id)
    if proposal is None:
        return None
    return current_page_disposition_v2_action(
        proposal,
        current_evidence=_read_latest_evidence(proposal.snapshot.work_item_id),
    )


def validate_current_page_disposition_v2_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("action_type") != CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE:
        errors.append("Current page disposition v2 action type is invalid.")
    if payload.get("local_authority_only") is not True:
        errors.append("Current page disposition v2 must remain local-only.")
    try:
        CurrentPageDispositionV2Proposal.model_validate_json(
            json.dumps(payload.get("current_page_disposition_v2", {}), sort_keys=True),
            strict=True,
        )
    except (TypeError, ValueError, ValidationError):
        errors.append("Current page disposition v2 proposal is invalid.")
    return errors


def execute_current_page_disposition_v2(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[AuditEvent],
    current_evidence: CurrentPageEvidenceResponse | None = None,
    confirmed_by: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    proposal = store.load_current_page_disposition_v2_proposal(action.id)
    if proposal is None:
        return None, ["Current page disposition v2 proposal is missing."]
    current_evidence = current_evidence or _read_latest_evidence(proposal.snapshot.work_item_id)
    expected = current_page_disposition_v2_action(proposal)
    if action.payload != expected.payload:
        return None, ["Current page disposition v2 ActionObject payload changed before apply."]
    if (
        not current_page_material_is_current(current_evidence)
        or current_evidence.material_meaning_digest != proposal.snapshot.material_meaning_digest
    ):
        return None, ["Current page material or WordPress freshness changed before apply."]
    from wilq.actions.action_chain import revision_bound_action_chain

    payload_digest = canonical_json_digest(action.payload)
    scoped_events = [event for event in audit_events if event.action_id == action.id]
    chain, blockers = revision_bound_action_chain(
        scoped_events,
        confirmed_by=confirmed_by or _confirmation_actor(scoped_events),
        binding_from_event=_current_page_v2_audit_binding,
        expected_binding=(proposal.snapshot.context_digest, payload_digest),
    )
    if chain is None:
        return None, [blockers[0].reason]
    preview, review, confirmation, impact = chain
    receipt = build_current_page_disposition_v2_receipt(
        action=action,
        proposal=proposal,
        preview_audit_id=preview.id,
        review_audit_id=review.id,
        confirmation_audit_id=confirmation.id,
        impact_audit_id=impact.id,
        reviewed_by=review.actor,
        confirmed_by=confirmation.actor,
        verification_evidence_ids=tuple(
            sorted(
                set(current_evidence.current_evidence_ids + current_evidence.catalog_evidence_ids)
            )
        ),
    )
    status, stored = store.record_current_page_disposition_v2_receipt(receipt)
    if status == "conflict":
        return None, ["Current page disposition v2 receipt conflicts with its stored proposal."]
    return {
        "receipt_id": stored.receipt_id,
        "status": status,
        "generation_allowed": False,
        "external_write_attempted": False,
        "mutation_adapter": CURRENT_DISPOSITION_MUTATION_ADAPTER,
    }, []


def _current_page_v2_audit_binding(event: Any) -> tuple[str, str] | None:
    context = event.details.get("current_disposition_snapshot_digest")
    payload = event.details.get("current_disposition_action_payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


def _confirmation_actor(events: list[Any]) -> str:
    confirmations = sorted(
        (event for event in events if event.event_type == "action_apply_confirmed"),
        key=lambda event: (event.created_at, event.id),
    )
    return confirmations[-1].actor if confirmations else ""


def _read_latest_evidence(work_item_id: str) -> CurrentPageEvidenceResponse:
    from wilq.content.workflow.current_page_evidence import (
        read_current_page_evidence_current,
    )

    return read_current_page_evidence_current(work_item_id)


__all__ = [
    "CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE",
    "current_page_disposition_v2_action",
    "execute_current_page_disposition_v2",
    "load_current_page_disposition_v2_action",
    "validate_current_page_disposition_v2_payload",
]
