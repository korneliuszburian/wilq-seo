from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    MetricFact,
    OpportunityDomain,
)


def synthetic_apply_ready_action(action_id: str = "act_synthetic_apply_ready") -> ActionObject:
    evidence_id = "ev_synthetic_apply_ready"
    return ActionObject(
        id=action_id,
        title="Synthetic apply-ready action",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=[evidence_id],
        metrics=[
            MetricFact(
                name="cost_micros", value=1000, period="last_7_days",
                source_connector="google_ads", evidence_id=evidence_id,
            )
        ],
        human_diagnosis="Synthetic action that should never apply without adapter.",
        recommended_reason="Regression guard for mutation audit boundary.",
        payload={
            "action_type": "synthetic_google_ads_mutation",
            "apply_allowed": True,
            "destructive": False,
            "payload_preview": [
                {
                    "operation_type": "SyntheticOperation",
                    "apply_allowed": True,
                    "required_validation": ["human_confirm_before_apply"],
                }
            ],
        },
        validation_status="valid",
        created_by="test",
        audit_events=[
            AuditEvent(
                id="audit_preview", action_id=action_id,
                event_type="action_preview_generated", actor="operator_test",
                summary="Preview generated.", evidence_ids=[evidence_id],
            ),
            AuditEvent(
                id="audit_confirm", action_id=action_id,
                event_type="action_apply_confirmed", actor="operator_test",
                summary="Preview confirmed.", evidence_ids=[evidence_id],
            ),
            AuditEvent(
                id="audit_impact", action_id=action_id,
                event_type="action_impact_check_completed", actor="operator_test",
                summary="Impact checked.", evidence_ids=[evidence_id],
            ),
        ],
    )
