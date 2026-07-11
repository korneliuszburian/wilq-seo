from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Literal

from wilq.schemas import (
    ActionMode,
    ActionMutationAuditRecord,
    ActionObject,
    ActionReviewGate,
    ActionReviewOutcome,
    AuditEvent,
)

ReviewGateStatus = Literal[
    "pending_validation",
    "validated_prepare_only",
    "ready_to_apply",
    "blocked_apply",
]
GateLabels = Callable[[Iterable[str]], list[str]]
ConfirmationRequired = Callable[[list[str], ActionMode], bool]
ReviewOutcome = Callable[[AuditEvent | None], ActionReviewOutcome | None]
ImpactStatus = Callable[[AuditEvent | None], Literal["checked", "blocked"] | None]
AuditSummary = Callable[[AuditEvent], str]


def build_action_review_gate(
    *,
    action: ActionObject,
    required_checks: list[str],
    operator_checklist: list[str],
    apply_allowed: bool,
    last_review: AuditEvent | None,
    last_confirmation: AuditEvent | None,
    last_impact_check: AuditEvent | None,
    last_mutation_audit: ActionMutationAuditRecord | None,
    apply_blockers: list[str],
    gate_labels: GateLabels,
    confirmation_required: ConfirmationRequired,
    review_outcome: ReviewOutcome,
    review_summary: AuditSummary,
    confirmation_summary: AuditSummary,
    impact_status: ImpactStatus,
) -> ActionReviewGate:
    status, summary = _review_gate_status_summary(
        action=action,
        apply_allowed=apply_allowed,
        apply_blockers=apply_blockers,
    )
    contract_apply_allowed = (
        apply_allowed and action.mode == ActionMode.apply and not apply_blockers
    )
    impact_check_status = impact_status(last_impact_check)
    return ActionReviewGate(
        status=status,
        summary=summary,
        required_checks=required_checks,
        required_check_labels=gate_labels(required_checks),
        operator_checklist=operator_checklist,
        operator_checklist_labels=gate_labels(operator_checklist),
        apply_blockers=apply_blockers,
        apply_blocker_labels=gate_labels(apply_blockers),
        confirmation_required=confirmation_required(required_checks, action.mode),
        apply_allowed=contract_apply_allowed,
        last_review_outcome=review_outcome(last_review),
        last_reviewed_by=last_review.actor if last_review is not None else None,
        last_reviewed_at=last_review.created_at if last_review is not None else None,
        last_review_summary=review_summary(last_review) if last_review is not None else None,
        last_confirmation_by=last_confirmation.actor if last_confirmation is not None else None,
        last_confirmation_at=last_confirmation.created_at
        if last_confirmation is not None
        else None,
        last_confirmation_summary=(
            confirmation_summary(last_confirmation) if last_confirmation is not None else None
        ),
        last_impact_check_status=impact_check_status,
        last_impact_checked_by=last_impact_check.actor if last_impact_check is not None else None,
        last_impact_checked_at=last_impact_check.created_at
        if last_impact_check is not None
        else None,
        last_impact_check_summary=last_impact_check.summary
        if last_impact_check is not None
        else None,
        last_mutation_audit_id=last_mutation_audit.id if last_mutation_audit is not None else None,
        last_mutation_audit_status=last_mutation_audit.status
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_actor=last_mutation_audit.actor
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_at=last_mutation_audit.created_at
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_summary=last_mutation_audit.summary
        if last_mutation_audit is not None
        else None,
        last_mutation_adapter_reached=last_mutation_audit.adapter_reached
        if last_mutation_audit is not None
        else None,
        last_external_write_attempted=last_mutation_audit.external_write_attempted
        if last_mutation_audit is not None
        else None,
        last_mutation_attempted=last_mutation_audit.mutation_attempted
        if last_mutation_audit is not None
        else None,
        last_mutation_adapter=last_mutation_audit.mutation_adapter
        if last_mutation_audit is not None
        else None,
        last_mutation_audit_event_id=last_mutation_audit.audit_event_id
        if last_mutation_audit is not None
        else None,
        last_mutation_blockers=last_mutation_audit.blockers
        if last_mutation_audit is not None
        else [],
        last_mutation_blocker_labels=(
            gate_labels(last_mutation_audit.blockers) if last_mutation_audit is not None else []
        ),
    )


def _review_gate_status_summary(
    *,
    action: ActionObject,
    apply_allowed: bool,
    apply_blockers: list[str],
) -> tuple[ReviewGateStatus, str]:
    if action.validation_status == "invalid":
        return (
            "blocked_apply",
            "Akcja ma błędne sprawdzenie; zapis zmian pozostaje zablokowany.",
        )
    if (
        action.mode == ActionMode.apply
        and action.validation_status == "valid"
        and apply_allowed
        and apply_blockers
    ):
        return (
            "blocked_apply",
            "Akcja ma przygotowany zakres zapisu zmian, ale blokery bezpieczeństwa nadal "
            "zatrzymują zapis.",
        )
    if action.mode == ActionMode.apply and action.validation_status == "valid" and apply_allowed:
        return (
            "ready_to_apply",
            "Kontrola WILQ potwierdza warunki zapisu; operator nadal musi jawnie "
            "potwierdzić zapis zmian.",
        )
    if action.validation_status == "valid":
        return (
            "validated_prepare_only",
            "Kontrola WILQ potwierdza warunki przygotowania; zapis zmian nadal "
            "wymaga osobnego kontraktu i zgody operatora.",
        )
    return (
        "pending_validation",
        "Wymaga sprawdzenia w WILQ; zapis zmian pozostaje zablokowany osobnymi warunkami.",
    )
