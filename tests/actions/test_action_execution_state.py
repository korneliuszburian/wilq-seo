from __future__ import annotations

from wilq.actions.action_state import with_review_gate
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)


def test_successful_apply_audit_projects_terminal_action_status() -> None:
    action = ActionObject(
        id="act_completed",
        title="Utwórz szkic na dev",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.medium,
        status=ActionStatus.ready_to_apply,
        evidence_ids=["ev_wordpress"],
        human_diagnosis="Dokładny szkic został potwierdzony.",
        recommended_reason="Utwórz jeden szkic.",
        payload={"action_type": "content_dev_draft_create"},
        validation_status="valid",
        created_by="Wilku",
    )

    result = with_review_gate(
        action,
        [
            AuditEvent(
                id="audit_apply",
                action_id=action.id,
                event_type="apply_succeeded",
                actor="wilq_api",
                summary="Zmiany zapisane przez sprawdzoną ścieżkę API.",
                evidence_ids=action.evidence_ids,
            )
        ],
        audit_event_has_raw_contract_text=lambda _event: False,
        content_payload_with_reviewed_previews=lambda payload, **_kwargs: payload,
        payload_with_operator_labels=lambda payload: payload,
        is_raw_content_review_audit_event=lambda _action_id, _event: False,
        action_review_gate=lambda current, _mutation_audits: current.review_gate,
        action_with_operator_labels=lambda current: current,
    )

    assert result.status == ActionStatus.applied
