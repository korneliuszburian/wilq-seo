from __future__ import annotations

from wilq.content.workflow.contracts import ContentWordPressDraftWriteReadinessResponse
from wilq.schemas import (
    ActionMutationApplyContract,
    ActionMutationAuditRecord,
    ActionMutationReadinessBlocker,
    ActionMutationReadinessRequirement,
    ActionMutationReadinessResponse,
    ActionObject,
)


def build_mutation_readiness_response(
    *,
    action: ActionObject,
    mutation_adapter: str | None,
    wordpress_draft_readiness: ContentWordPressDraftWriteReadinessResponse | None,
    requirements: list[ActionMutationReadinessRequirement],
    blockers: list[ActionMutationReadinessBlocker],
    vendor_write_possible: bool,
    apply_contract: ActionMutationApplyContract | None,
    target: dict[str, str | None],
    operator_next_step: str,
    latest_mutation_audit: ActionMutationAuditRecord | None,
) -> ActionMutationReadinessResponse:
    ready_to_request_apply = not blockers
    return ActionMutationReadinessResponse(
        action_id=action.id,
        title=action.title,
        connector=action.connector,
        connector_label=action.connector_label,
        mode=action.mode,
        mode_label=action.mode_label,
        risk=action.risk,
        risk_label=action.risk_label,
        validation_status=action.validation_status,
        review_gate_status=action.review_gate.status,
        ready_to_request_apply=ready_to_request_apply,
        vendor_write_possible=vendor_write_possible,
        would_attempt_vendor_write=ready_to_request_apply and vendor_write_possible,
        mutation_adapter=mutation_adapter,
        apply_contract=apply_contract,
        target_candidate_id=target.get("candidate_id"),
        target_label=target.get("label"),
        target_url=target.get("url"),
        write_authorization_status=(
            wordpress_draft_readiness.write_authorization_status
            if wordpress_draft_readiness is not None
            else None
        ),
        missing_audit_event_types=(
            wordpress_draft_readiness.missing_audit_event_types
            if wordpress_draft_readiness is not None
            else []
        ),
        requirements=requirements,
        blockers=blockers,
        operator_next_step=operator_next_step,
        evidence_ids=action.evidence_ids,
        source_connectors=[action.connector],
        latest_mutation_audit_id=(
            latest_mutation_audit.id if latest_mutation_audit is not None else None
        ),
        latest_mutation_audit_status=(
            latest_mutation_audit.status if latest_mutation_audit is not None else None
        ),
    )
