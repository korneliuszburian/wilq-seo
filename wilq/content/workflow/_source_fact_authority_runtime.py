"""Private runtime implementation for source-fact authority."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow._source_fact_authority_contracts import (
    SOURCE_FACT_AUTHORITY_ACTION_TYPE,
    SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT,
    ContentSourceFactAuthorityBlocker,
    ContentSourceFactAuthorityCandidateProjection,
    ContentSourceFactAuthorityPreviewCommand,
    ContentSourceFactAuthorityPreviewResponse,
    ContentSourceFactAuthorityProposal,
    ContentSourceFactAuthorityReadProjection,
    ContentSourceFactAuthorityReceipt,
    ContentSourceFactAuthoritySnapshot,
    parse_source_fact_authority_snapshot_json,
    source_fact_authority_action_payload_digest,
    source_fact_authority_receipt_digest,
)
from wilq.content.workflow._source_fact_authority_snapshot import (
    build_source_fact_authority_snapshot as _build_source_fact_authority_snapshot,
)
from wilq.content.workflow.decisions.production import ContentProductionClassificationProjection
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.source_fact_candidate_projection import (
    build_content_source_fact_authority_candidate_projection as _build_candidate_projection,
)
from wilq.evidence.registry import SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)


def execute_content_source_fact_authority(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[AuditEvent],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Create a local receipt only from exact current state and persisted gates."""

    if action.payload.get("local_authority_only") is not True:
        return None, ["Source fact authority action is not local-only."]
    proposal = store.load_content_source_fact_authority_proposal(action.id)
    if proposal is None:
        return None, ["Source fact authority proposal is missing."]
    expected = source_fact_authority_action_for_proposal(proposal, store=store)
    try:
        actual_snapshot = parse_source_fact_authority_snapshot_json(
            action.payload.get("source_fact_authority", {})
        )
    except Exception:
        return None, ["Source fact authority snapshot is invalid."]
    try:
        expected_snapshot = parse_source_fact_authority_snapshot_json(
            expected.payload.get("source_fact_authority", {})
        )
    except Exception:
        return None, ["Source fact authority context changed before apply."]
    if actual_snapshot != expected_snapshot or source_fact_authority_action_payload_digest(
        action
    ) != source_fact_authority_action_payload_digest(expected):
        return None, ["Source fact authority context changed before apply."]
    event_by_type = {
        event.event_type: event for event in audit_events if event.action_id == action.id
    }
    required = (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    )
    if any(name not in event_by_type for name in required):
        return None, ["Exact preview, approved review, confirmation and impact check are required."]
    preview, review, confirmation, impact = (event_by_type[name] for name in required)
    ordered_events = sorted(
        (preview, review, confirmation, impact), key=lambda event: event.created_at
    )
    if [event.event_type for event in ordered_events] != list(required):
        return None, ["Source fact authority audit chain is out of order."]
    payload_digest = source_fact_authority_action_payload_digest(action)
    if any(
        event.details.get("source_fact_authority_snapshot_digest")
        != actual_snapshot.context_digest
        or event.details.get("source_fact_authority_action_payload_digest") != payload_digest
        for event in (preview, review, confirmation, impact)
    ):
        return None, ["Audit chain does not bind the exact current authority snapshot."]
    timestamp = datetime.now(UTC)
    provisional = ContentSourceFactAuthorityReceipt.model_construct(
        action_id=action.id, action_payload_digest=payload_digest,
        authority_snapshot=actual_snapshot, preview_audit_id=preview.id,
        review_audit_id=review.id, confirmation_audit_id=confirmation.id,
        impact_audit_id=impact.id, reviewed_by=review.actor, confirmed_by=confirmation.actor,
        recorded_by="wilq_local_action_executor", recorded_at=timestamp,
        receipt_id="", receipt_digest="",
    )
    digest = source_fact_authority_receipt_digest(provisional)
    receipt = ContentSourceFactAuthorityReceipt.model_validate(
        provisional.model_copy(update={
            "receipt_id": f"content_source_fact_authority_{digest[:24]}",
            "receipt_digest": digest,
        })
    )
    status, stored = store.record_content_source_fact_authority_receipt(receipt)
    if status == "conflict":
        return None, ["Source fact authority receipt conflicts with this action."]
    return {
        "receipt_id": stored.receipt_id,
        "status": status,
        "external_write_attempted": False,
    }, []


def read_content_source_fact_authority(
    store: Any,
    *,
    action_id: str,
) -> ContentSourceFactAuthorityReadProjection:
    """Read persisted authority only when it still matches current server state."""

    proposal = store.load_content_source_fact_authority_proposal(action_id)
    if proposal is None:
        raise ValueError("Source fact authority proposal is missing.")
    expected = source_fact_authority_action_for_proposal(proposal, store=store)
    snapshot_data = expected.payload.get("source_fact_authority")
    snapshot = (
        None
        if not isinstance(snapshot_data, dict)
        else parse_source_fact_authority_snapshot_json(snapshot_data)
    )
    receipt = store.load_content_source_fact_authority_receipt(action_id)
    common = {
        "identity_binding_id": proposal.identity_binding_id,
        "current_work_item_id": None if snapshot is None else snapshot.current_work_item_id,
        "canonical_path": None if snapshot is None else snapshot.canonical_path,
        "public_url": None if snapshot is None else snapshot.public_url,
        "current_snapshot": snapshot,
    }
    if receipt is None:
        return ContentSourceFactAuthorityReadProjection(
            status="missing",
            **common,
            safe_next_step="Przejdź exact ActionObject preview, review, confirm i impact check.",
        )
    if hasattr(store, "list_content_source_fact_authority_receipts"):
        current_receipts = store.list_content_source_fact_authority_receipts(
            identity_binding_id=proposal.identity_binding_id,
            current_work_item_id=receipt.authority_snapshot.current_work_item_id,
        )
        if current_receipts and current_receipts[-1].action_id != action_id:
            return ContentSourceFactAuthorityReadProjection(
                status="blocked",
                receipt=receipt,
                blockers=(_blocker("current_context", "authority_receipt_superseded"),),
                **common,
                safe_next_step=(
                    "Bieżący receipt został zastąpiony nowszą selekcją; użyj nowego authority."
                ),
            )
    if snapshot is None or receipt.authority_snapshot != snapshot:
        return ContentSourceFactAuthorityReadProjection(
            status="blocked",
            receipt=receipt,
            blockers=(_blocker("current_context", "authority_snapshot_drift"),),
            **common,
            safe_next_step=(
                "Odśwież preview i przejdź nowy pełny lifecycle dla bieżącego kontekstu."
            ),
        )
    return ContentSourceFactAuthorityReadProjection(
        status="current",
        receipt=receipt,
        blockers=(),
        **common,
        safe_next_step=(
            "Authority jest aktualna; source-pack consumer nadal wymaga osobnego bindingu."
        ),
    )


def _blocker(
    seam: str,
    reason: str,
    evidence_ids: tuple[str, ...] = (),
    next_step: str = "Odśwież exact dane i przygotuj nowy preview.",
) -> ContentSourceFactAuthorityBlocker:
    return ContentSourceFactAuthorityBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step=next_step,
    )


def build_content_source_fact_authority_candidate_projection(
    identity_binding_id: str,
    *,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[Any, ...] | None = None,
    checked_at: datetime | None = None,
) -> ContentSourceFactAuthorityCandidateProjection:
    """Compatibility wrapper for the focused candidate projection module."""

    return _build_candidate_projection(
        identity_binding_id,
        identity=identity,
        classification=classification,
        facts=facts,
        cards=cards,
        checked_at=checked_at,
    )


def build_source_fact_authority_snapshot(
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    source_fact_ids: tuple[str, ...],
    *,
    facts: tuple[ContentSourceFact, ...] | None = None,
    identity_binding_id: str | None = None,
) -> tuple[
    ContentSourceFactAuthoritySnapshot | None,
    tuple[ContentSourceFactAuthorityBlocker, ...],
]:
    """Build current exact state without inferring any URL, slug or card."""

    return _build_source_fact_authority_snapshot(
        identity,
        classification,
        source_fact_ids,
        facts=facts,
        identity_binding_id=identity_binding_id,
    )


def build_source_fact_authority_action(
    proposal: ContentSourceFactAuthorityProposal,
    *,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    facts: tuple[ContentSourceFact, ...] | None = None,
) -> ActionObject:
    snapshot, blockers = build_source_fact_authority_snapshot(
        identity,
        classification,
        proposal.proposed_source_fact_ids,
        facts=facts,
        identity_binding_id=proposal.identity_binding_id,
    )
    if proposal.prepared_snapshot_digest is not None and (
        snapshot is None or snapshot.context_digest != proposal.prepared_snapshot_digest
    ):
        blockers = (
            *blockers,
            _blocker(
                "proposal",
                "proposal_snapshot_drift",
                () if snapshot is None else snapshot.evidence_ids,
                "Odśwież preview dla bieżącego S1/classification/registry.",
            ),
        )
        snapshot = None
    exact = snapshot is not None and not blockers
    evidence_ids = list(
        snapshot.evidence_ids
        if snapshot is not None
        else (SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,)
    )
    blocker_reasons = [item.reason for item in blockers]
    preview_context = None if snapshot is None else snapshot.model_dump(mode="json")
    payload_preview = {
        "id": f"source_fact_authority_{proposal.action_id}",
        "preview_contract": SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT,
        "operation_type": "record_source_fact_authority_receipt",
        "current_work_item_id": (
            snapshot.current_work_item_id if snapshot is not None else None
        ),
        "canonical_path": snapshot.canonical_path if snapshot is not None else None,
        "public_url": snapshot.public_url if snapshot is not None else None,
        "source_fact_ids": list(proposal.proposed_source_fact_ids),
        "source_facts_digest": (
            snapshot.source_facts_digest if snapshot is not None else None
        ),
        "source_fact_provenance_digest": (
            snapshot.source_fact_provenance_digest if snapshot is not None else None
        ),
        "required_validation": [
            "exact_s1_identity",
            "current_classification",
            "source_fact_registry",
            "approved_source_facts",
            "human_review_before_apply",
            "human_confirm_before_apply",
        ],
        "apply_allowed": exact,
        "api_mutation_ready": exact,
        "destructive": False,
    }
    return ActionObject(
        id=proposal.action_id,
        title="Zatwierdź source facts dla exact wiersza S1",
        domain=OpportunityDomain.knowledge,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply if exact else ActionStatus.blocked,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "To jest osobny row-authority receipt. Zatwierdzenie source fact w registry "
            "nie daje jeszcze prawa użycia go dla tego exact work itemu."
        ),
        recommended_reason=(
            "Sprawdź exact S1 identity, bieżącą klasyfikację, registry i provenance faktów; "
            "dopiero potem wykonaj canonical ActionObject lifecycle."
        ),
        payload={
            "action_type": SOURCE_FACT_AUTHORITY_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "preview_contract": SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT,
            "local_authority_only": True,
            "proposal_digest": proposal.proposal_digest,
            "source_fact_authority": preview_context,
            "payload_preview": [payload_preview],
            "payload_preview_total": 1,
            "payload_preview_included": 1,
            "required_validation": payload_preview["required_validation"],
            "apply_allowed": exact,
            "api_mutation_ready": exact,
            "destructive": False,
            "runtime_blockers": blocker_reasons,
        },
        validation_status="not_validated",
        created_by="system_core_source_fact_authority",
    )


def validate_source_fact_authority_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("action_type") != SOURCE_FACT_AUTHORITY_ACTION_TYPE:
        errors.append("Source fact authority action type is invalid.")
    if payload.get("mode") != "apply":
        errors.append("Source fact authority action must use apply mode.")
    if payload.get("preview_contract") != SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT:
        errors.append("Source fact authority preview contract is missing.")
    if payload.get("local_authority_only") is not True:
        errors.append("Source fact authority must remain local-only.")
    if payload.get("destructive") is not False:
        errors.append("Source fact authority cannot be destructive.")
    try:
        parse_source_fact_authority_snapshot_json(payload.get("source_fact_authority", {}))
    except Exception:
        # A blocked preview deliberately has no self-authenticating snapshot;
        # runtime revalidation will expose the typed blocker instead.
        if not payload.get("runtime_blockers"):
            errors.append("Source fact authority exact context is missing.")
    return errors


def source_fact_authority_action_for_proposal(
    proposal: ContentSourceFactAuthorityProposal,
    *,
    store: Any,
) -> ActionObject:
    identity = store.load_content_delivery_identity(proposal.identity_binding_id)
    classification = (
        None
        if identity is None
        else store.load_production_classification_for_work_item(identity.current_work_item_id)
    )
    return build_source_fact_authority_action(
        proposal,
        identity=identity,
        classification=classification,
    )


def load_content_source_fact_authority_action(action_id: str) -> ActionObject | None:
    """Resolve a persisted proposal for the canonical `/api/actions` routes."""

    from wilq.content.workflow.store.store import content_workflow_store

    store = content_workflow_store()
    proposal = store.load_content_source_fact_authority_proposal(action_id)
    if proposal is None:
        return None
    return source_fact_authority_action_for_proposal(proposal, store=store)


def prepare_content_source_fact_authority_preview(
    store: Any,
    command: ContentSourceFactAuthorityPreviewCommand,
) -> ContentSourceFactAuthorityPreviewResponse:
    proposal = store.record_content_source_fact_authority_proposal(command)
    action = source_fact_authority_action_for_proposal(proposal, store=store)
    blockers = tuple(
        _blocker("action", reason, next_step="Odśwież exact preview i sprawdź blocker.")
        for reason in action.payload.get("runtime_blockers", [])
        if isinstance(reason, str)
    )
    return ContentSourceFactAuthorityPreviewResponse(
        status="blocked" if blockers else "preview_ready",
        action=action,
        identity_binding_id=command.identity_binding_id,
        proposed_source_fact_ids=command.proposed_source_fact_ids,
        blockers=blockers,
    )
