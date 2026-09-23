"""Exact local ActionObject approval for current WordPress page material."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.material_review import (
    ContentMaterialReviewCommand,
    ContentMaterialReviewPreview,
    build_content_material_review_preview,
    build_content_material_review_receipt,
    material_review_meaning_digest,
    material_review_preview_digest,
    revalidate_content_material_review_preview,
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

MATERIAL_REVIEW_ACTION_V2_TYPE = "content_current_material_review_v2"
MATERIAL_REVIEW_ACTION_V2_ADAPTER = "content_current_material_review_local_authority"


def current_material_review_action_v2(
    preview: ContentMaterialReviewPreview,
) -> ActionObject:
    action_id = material_review_action_id(preview.preview_digest)
    return ActionObject(
        id=action_id,
        title="Zatwierdź exact bieżący materiał WordPress",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(preview.evidence_ids),
        human_diagnosis="Lokalna decyzja dotyczy tylko exact materiału bieżącego URL-a.",
        recommended_reason="Sprawdź pełny materiał i exact audyt przed zatwierdzeniem.",
        payload={
            "action_type": MATERIAL_REVIEW_ACTION_V2_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "material_review_preview": preview.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": preview.preview_id,
                    "operation_type": "record_approved_current_material_review",
                    "work_item_id": preview.work_item_id,
                    "page_url": preview.public_url,
                    "preview_digest": preview.preview_digest,
                    "apply_allowed": True,
                    "api_mutation_ready": True,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "generation_allowed": False,
        },
        validation_status="not_validated",
        created_by="system_core_current_material_review_v2",
    )


def material_review_action_id(preview_digest: str) -> str:
    return f"act_content_material_review_{preview_digest[:24]}"


def load_current_material_review_action_v2(
    action_id: str,
    *,
    store: ContentWorkflowStore | None = None,
) -> ActionObject | None:
    if not action_id.startswith("act_content_material_review_"):
        return None
    preview_digest_prefix = action_id.removeprefix("act_content_material_review_")
    workflow_store = store or content_workflow_store()
    preview = workflow_store.load_content_material_review_preview(
        f"content_material_review_preview_{preview_digest_prefix}"
    )
    if preview is None or material_review_action_id(preview.preview_digest) != action_id:
        return None
    return current_material_review_action_v2(preview)


def build_current_material_review_action_preview_v2(
    work_item_id: str,
    *,
    store: ContentWorkflowStore | None = None,
    **preview_dependencies: Any,
) -> ActionObject:
    candidate = build_content_material_review_preview(
        work_item_id=work_item_id,
        **preview_dependencies,
    )
    workflow_store = store or content_workflow_store()
    saved = workflow_store.record_content_material_review_preview(candidate)
    if saved.status == "conflict":
        raise ValueError("content_material_review_preview_conflict")
    # Only the immutable stored preview may source the ActionObject.
    stored = workflow_store.load_content_material_review_preview(saved.preview.preview_id)
    if stored is None or stored.preview_digest != candidate.preview_digest:
        raise ValueError("content_material_review_stored_preview_missing_or_changed")
    return current_material_review_action_v2(stored)


def validate_current_material_review_action_v2_payload(payload: dict[str, Any]) -> list[str]:
    try:
        preview = parse_material_review_action_preview(payload.get("material_review_preview", {}))
    except (TypeError, ValueError, ValidationError):
        return ["Current material review preview is invalid."]
    errors: list[str] = []
    if payload.get("action_type") != MATERIAL_REVIEW_ACTION_V2_TYPE:
        errors.append("Current material review action type is invalid.")
    if payload.get("local_authority_only") is not True:
        errors.append("Current material review must remain local-only.")
    if payload.get("generation_allowed") is not False or payload.get("destructive") is not False:
        errors.append("Current material review cannot generate content or be destructive.")
    preview_rows = payload.get("payload_preview")
    if not isinstance(preview_rows, list) or len(preview_rows) != 1:
        errors.append("Current material review requires one exact preview row.")
    elif not isinstance(preview_rows[0], dict) or preview_rows[0] != (
        current_material_review_action_v2(preview).payload["payload_preview"][0]
    ):
        errors.append("Current material review preview row is not exact.")
    return errors


def parse_material_review_action_preview(value: object) -> ContentMaterialReviewPreview:
    """Parse the JSON-shaped ActionObject snapshot with strict material contracts."""
    return ContentMaterialReviewPreview.model_validate_json(
        json.dumps(value, sort_keys=True), strict=True
    )


def execute_current_material_review_action_v2(
    action: ActionObject,
    *,
    store: ContentWorkflowStore | None = None,
    audit_events: list[AuditEvent],
    confirmed_by: str,
    **revalidation_dependencies: Any,
) -> tuple[dict[str, Any] | None, list[str]]:
    workflow_store = store or content_workflow_store()
    try:
        preview = parse_material_review_action_preview(
            action.payload.get("material_review_preview", {})
        )
    except (TypeError, ValueError, ValidationError):
        return None, ["Current material review ActionObject preview is invalid."]
    stored = workflow_store.load_content_material_review_preview(preview.preview_id)
    if (
        stored is None
        or stored != preview
        or material_review_preview_digest(preview) != preview.preview_digest
        or action.id != material_review_action_id(preview.preview_digest)
        or action.payload != current_material_review_action_v2(preview).payload
    ):
        return None, ["Current material review ActionObject payload changed before apply."]
    digest_binding = (preview.preview_digest, canonical_json_digest(action.payload))
    chain, blockers = revision_bound_action_chain(
        [event for event in audit_events if event.action_id == action.id],
        confirmed_by=confirmed_by,
        binding_from_event=_audit_binding,
        expected_binding=digest_binding,
    )
    if chain is None:
        return None, [blockers[0].reason]
    _preview_audit, review, confirmation, impact = chain
    checked_items = review.details.get("checked_items", [])
    if not isinstance(checked_items, list) or "reviewed_full_material" not in checked_items:
        return None, ["reviewed_full_material attestation is required before approval."]
    try:
        current_observation = revalidate_content_material_review_preview(
            work_item_id=preview.work_item_id,
            preview=preview,
            **revalidation_dependencies,
        )
    except (ValueError, RuntimeError) as error:
        return None, [str(error)]
    command = ContentMaterialReviewCommand(
        preview_id=preview.preview_id,
        preview_digest=preview.preview_digest,
        decision="approved",
        reviewer=review.actor,
        reviewed_full_material=True,
    )
    receipt = build_content_material_review_receipt(
        work_item_id=preview.work_item_id,
        command=command,
        reviewed_at=review.created_at,
    )
    result = workflow_store.record_content_material_review(receipt)
    if result.status == "conflict":
        return None, ["Current material review receipt conflicts with an existing decision."]
    meaning_digest = material_review_meaning_digest(
        work_item_id=preview.work_item_id,
        preview=preview,
        current_observation=current_observation,
    )
    return {
        "receipt_id": result.review.review_id,
        "status": result.status,
        "work_item_id": preview.work_item_id,
        "preview_digest": preview.preview_digest,
        "material_meaning_digest": meaning_digest,
        "verification_observation_id": current_observation.observation_id,
        "verification_evidence_ids": list(current_observation.evidence_ids),
        "review_audit_event_id": review.id,
        "confirmed_by": confirmation.actor,
        "impact_audit_event_id": impact.id,
        "external_write_attempted": False,
        "generation_allowed": False,
    }, []


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    preview_digest = event.details.get("context_digest")
    payload_digest = event.details.get("payload_digest")
    if isinstance(preview_digest, str) and isinstance(payload_digest, str):
        return preview_digest, payload_digest
    return None


__all__ = [
    "MATERIAL_REVIEW_ACTION_V2_ADAPTER",
    "MATERIAL_REVIEW_ACTION_V2_TYPE",
    "build_current_material_review_action_preview_v2",
    "current_material_review_action_v2",
    "execute_current_material_review_action_v2",
    "load_current_material_review_action_v2",
    "material_review_action_id",
    "parse_material_review_action_preview",
    "validate_current_material_review_action_v2_payload",
]
