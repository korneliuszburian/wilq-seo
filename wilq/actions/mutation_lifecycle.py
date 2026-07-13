from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import (
    ActionMutationAuditRecord,
    ActionMutationReadinessBlocker,
    ActionMutationReadinessRequirement,
    ActionMutationReadinessResponse,
    ActionObject,
    AuditEvent,
    ConnectorStatus,
)

ActionWithReviewGate = Callable[
    [ActionObject, list[AuditEvent], list[ActionMutationAuditRecord]], ActionObject
]
PersistedAuditEvents = Callable[[str], list[AuditEvent]]
PersistedMutationAudits = Callable[[str], list[ActionMutationAuditRecord]]
LatestEvent = Callable[[list[AuditEvent]], AuditEvent | None]
LatestMutationAudit = Callable[
    [list[ActionMutationAuditRecord]], ActionMutationAuditRecord | None
]
PayloadApplyAllowed = Callable[[dict[str, object]], bool]
ImpactStatus = Callable[[AuditEvent | None], str | None]
EvidenceLabel = Callable[[list[str]], str]
MutationAdapter = Callable[[ActionObject], str | None]
WordPressReadiness = Callable[[ActionObject], object | None]
WordPressActivationPacket = Callable[[ActionObject], object | None]
RequirementsBuilder = Callable[..., list[ActionMutationReadinessRequirement]]
BlockersBuilder = Callable[
    [list[ActionMutationReadinessRequirement]], list[ActionMutationReadinessBlocker]
]
VendorWritePossible = Callable[[ActionObject, str | None], bool]
ApplyContract = Callable[[ActionObject, str | None], object | None]
TargetBuilder = Callable[..., dict[str, str | None]]
ResponseBuilder = Callable[..., ActionMutationReadinessResponse]
NextStep = Callable[
    [ActionObject, list[ActionMutationReadinessBlocker]], str
]
PreviewItems = Callable[[dict[str, object]], list[dict[str, object]]]


def mutation_readiness_action(
    action: ActionObject,
    *,
    with_review_gate: ActionWithReviewGate,
    persisted_audit_events: PersistedAuditEvents,
    persisted_mutation_audits: PersistedMutationAudits,
    connector_status: Callable[[str], ConnectorStatus | None],
    mutation_adapter: MutationAdapter,
    latest_preview_event: LatestEvent,
    latest_confirmation_event: LatestEvent,
    latest_impact_check_event: LatestEvent,
    latest_mutation_audit: LatestMutationAudit,
    wordpress_draft_readiness: WordPressReadiness,
    wordpress_activation_packet: WordPressActivationPacket,
    base_requirements: RequirementsBuilder,
    wordpress_execution_requirements: RequirementsBuilder,
    wordpress_target_requirements: RequirementsBuilder,
    wordpress_write_requirements: RequirementsBuilder,
    blockers: BlockersBuilder,
    vendor_write_possible: VendorWritePossible,
    apply_contract: ApplyContract,
    target: TargetBuilder,
    response: ResponseBuilder,
    operator_next_step: NextStep,
    payload_apply_allowed: PayloadApplyAllowed,
    impact_status: ImpactStatus,
    evidence_label: EvidenceLabel,
    preview_items: PreviewItems,
) -> ActionMutationReadinessResponse:
    action = with_review_gate(
        action,
        persisted_audit_events(action.id),
        persisted_mutation_audits(action.id),
    )
    connector = connector_status(action.connector)
    adapter = mutation_adapter(action)
    latest_preview = latest_preview_event(action.audit_events)
    latest_confirmation = latest_confirmation_event(action.audit_events)
    latest_impact_check = latest_impact_check_event(action.audit_events)
    latest_audit = latest_mutation_audit(persisted_mutation_audits(action.id))
    wordpress_readiness = wordpress_draft_readiness(action)
    activation_packet = wordpress_activation_packet(action)
    requirements = base_requirements(
        action=action,
        connector_configured=connector is not None and connector.configured,
        connector_evidence=connector.status.value if connector is not None else "missing",
        mutation_adapter=adapter,
        latest_preview=latest_preview,
        latest_confirmation=latest_confirmation,
        latest_impact_check=latest_impact_check,
        payload_apply_allowed=payload_apply_allowed,
        impact_status=impact_status,
        evidence_label=evidence_label,
    )
    requirements.extend(
        wordpress_execution_requirements(
            action,
            activation_packet=activation_packet,
        )
    )
    requirements.extend(
        wordpress_target_requirements(
            action,
            activation_packet=activation_packet,
            preview_items=preview_items,
        )
    )
    requirements.extend(
        wordpress_write_requirements(
            action,
            wordpress_draft_readiness=wordpress_readiness,
        )
    )
    readiness_blockers = blockers(requirements)
    can_write = vendor_write_possible(action, adapter)
    contract = apply_contract(action, adapter)
    readiness_target = target(
        action,
        activation_packet=activation_packet,
        preview_items=preview_items,
    )
    return response(
        action=action,
        mutation_adapter=adapter,
        wordpress_draft_readiness=wordpress_readiness,
        requirements=requirements,
        blockers=readiness_blockers,
        vendor_write_possible=can_write,
        apply_contract=contract,
        target=readiness_target,
        operator_next_step=operator_next_step(action, readiness_blockers),
        latest_mutation_audit=latest_audit,
    )
