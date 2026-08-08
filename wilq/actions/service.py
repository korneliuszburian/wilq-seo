from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from wilq.actions import action_catalog
from wilq.actions.action_blockers import (
    action_apply_blockers as _action_apply_blockers_impl,
)
from wilq.actions.action_blockers import (
    action_confirmation_blockers,
    action_confirmation_event_type,
    action_confirmation_summary,
    action_preview_blockers,
    ads_target_confirmation_blockers,
    ads_target_confirmation_summary,
)
from wilq.actions.action_blockers import (
    action_preview_summary as _action_preview_summary,
)
from wilq.actions.action_previews import action_preview_cards as build_action_preview_cards
from wilq.actions.action_state import (
    with_persisted_review_gates as with_persisted_review_gates_state,
)
from wilq.actions.action_state import (
    with_persisted_validation_state as with_persisted_validation_state_state,
)
from wilq.actions.action_state import (
    with_review_gate as with_review_gate_state,
)
from wilq.actions.action_validation import validate_action as validate_action_lifecycle
from wilq.actions.apply_lifecycle import apply_action as apply_action_lifecycle
from wilq.actions.audit_store import (
    action_audit_summary_for_operator as _action_audit_summary_for_operator,
)
from wilq.actions.audit_store import (
    audit_event_has_raw_contract_text as _audit_event_has_raw_contract_text,
)
from wilq.actions.audit_store import (
    audit_event_label as _audit_event_label_impl,
)
from wilq.actions.audit_store import (
    audit_event_with_operator_label as _audit_event_with_operator_label_impl,
)
from wilq.actions.audit_store import (
    build_confirmation_audit_event,
    build_preview_audit_event,
)
from wilq.actions.audit_store import (
    latest_action_confirmation_event as _latest_action_confirmation_event_impl,
)
from wilq.actions.audit_store import (
    latest_action_impact_check_event as _latest_action_impact_check_event_impl,
)
from wilq.actions.audit_store import (
    latest_mutation_audit as _latest_mutation_audit_impl,
)
from wilq.actions.audit_store import (
    latest_preview_event as _latest_preview_event_impl,
)
from wilq.actions.audit_store import (
    operator_audit_summary_text as _operator_audit_summary_text_impl,
)
from wilq.actions.audit_store import (
    operator_note_sentence as _operator_note_sentence,
)
from wilq.actions.audit_store import (
    persisted_audit_events_by_action_id as _persisted_audit_events_by_action_id,
)
from wilq.actions.audit_store import (
    persisted_audit_events_for_action as _persisted_audit_events_for_action,
)
from wilq.actions.audit_store import (
    persisted_mutation_audits_by_action_id as _persisted_mutation_audits_by_action_id,
)
from wilq.actions.audit_store import (
    persisted_mutation_audits_for_action as _persisted_mutation_audits_for_action,
)
from wilq.actions.confirmation_lifecycle import confirm_action as confirm_action_lifecycle
from wilq.actions.content_refresh import (
    content_contract_label,
    content_payload_with_reviewed_wordpress_draft_previews,
)
from wilq.actions.content_review_details import (
    content_url_review_details as _content_url_review_details_from_checked_items,
)
from wilq.actions.content_review_details import (
    draft_readiness_review_details as _draft_readiness_review_details_from_checked_items,
)
from wilq.actions.content_review_details import (
    is_raw_content_review_audit_event as _is_raw_content_review_audit_event,
)
from wilq.actions.gate_labels import (
    action_gate_label as _action_gate_label,
)
from wilq.actions.gate_labels import (
    action_gate_labels,
)
from wilq.actions.google_ads.business_context import (
    ads_strategy_review_summary,
)
from wilq.actions.google_ads.business_context import (
    micros_money_label as _micros_money_label,
)
from wilq.actions.google_ads.demand_gen import (
    demand_gen_channel_label,
)
from wilq.actions.google_ads.demand_gen_preview import (
    demand_gen_readiness_preview_cards as build_demand_gen_readiness_preview_cards,
)
from wilq.actions.impact_lifecycle import impact_check_action as impact_check_action_lifecycle
from wilq.actions.metric_utils import (
    metric_fact_label,
    unique_values,
)
from wilq.actions.mutation_contract import mutation_apply_contract as _mutation_apply_contract
from wilq.actions.mutation_contract import (
    supported_mutation_adapter as _supported_mutation_adapter_impl,
)
from wilq.actions.mutation_lifecycle import (
    mutation_readiness_action as mutation_readiness_action_lifecycle,
)
from wilq.actions.mutation_plan import activation_next_step as _activation_next_step
from wilq.actions.mutation_plan import activation_plan_steps as _activation_plan_steps
from wilq.actions.mutation_plan import first_write_candidate as _first_write_candidate
from wilq.actions.mutation_plan import first_write_candidate_reason as _first_write_candidate_reason
from wilq.actions.mutation_plan import (
    mutation_readiness_summary_next_step as _mutation_readiness_summary_next_step,
)
from wilq.actions.mutation_readiness import (
    mutation_readiness_blockers,
)
from wilq.actions.mutation_readiness import (
    mutation_readiness_next_step as _mutation_readiness_next_step_impl,
)
from wilq.actions.mutation_readiness import (
    vendor_write_possible as _vendor_write_possible_impl,
)
from wilq.actions.mutation_requirements import base_mutation_readiness_requirements
from wilq.actions.mutation_response import build_mutation_readiness_response
from wilq.actions.mutation_summary import build_mutation_readiness_summary
from wilq.actions.mutation_target import mutation_readiness_target
from wilq.actions.operator_labels import (
    action_evidence_summary_label as _action_evidence_summary_label,
)
from wilq.actions.operator_labels import (
    action_result_status_label as _action_result_status_label,
)
from wilq.actions.operator_labels import (
    action_validation_status_label as _action_validation_status_label,
)
from wilq.actions.operator_labels import (
    action_with_operator_labels as _action_with_operator_labels_impl,
)
from wilq.actions.operator_labels import (
    ads_recommendation_type_label,
    payload_with_operator_labels,
)
from wilq.actions.operator_labels import (
    review_gate_with_operator_labels as _review_gate_with_operator_labels_impl,
)
from wilq.actions.payload_readiness import (
    action_preview_item_view_models,
    payload_api_mutation_ready,
    payload_apply_allowed,
)
from wilq.actions.payload_readiness import (
    apply_state_label as _apply_state_label,
)
from wilq.actions.payload_readiness import (
    payload_preview_contract as _payload_preview_contract_impl,
)
from wilq.actions.payload_readiness import (
    payload_preview_items as _payload_preview_items_impl,
)
from wilq.actions.payload_readiness import (
    preview_contract_label as _preview_contract_label,
)
from wilq.actions.payload_readiness import (
    preview_row as _preview_row,
)
from wilq.actions.payload_readiness import (
    string_list as _string_list,
)
from wilq.actions.payload_readiness import (
    system_readiness_label as _system_readiness_label,
)
from wilq.actions.preview_lifecycle import preview_action as preview_action_lifecycle
from wilq.actions.review_gate import (
    action_operator_checklist as build_action_operator_checklist,
)
from wilq.actions.review_gate import (
    action_required_checks as build_action_required_checks,
)
from wilq.actions.review_gate import (
    action_review_details as build_action_review_details,
)
from wilq.actions.review_gate import (
    action_review_gate as build_action_review_gate,
)
from wilq.actions.review_gate import (
    action_review_summary as build_action_review_summary,
)
from wilq.actions.review_gate import (
    canonical_contract_key as canonical_review_contract_key,
)
from wilq.actions.review_gate import (
    review_blocker_label as build_review_blocker_label,
)
from wilq.actions.review_gate import (
    review_outcome_label,
)
from wilq.actions.review_gate import (
    review_source_type_label as build_review_source_type_label,
)
from wilq.actions.review_gate import (
    review_summary_item as build_review_summary_item,
)
from wilq.actions.review_lifecycle import record_action_review as record_action_review_lifecycle
from wilq.actions.wordpress_mutation_requirements import (
    WordPressDraftApplyCapability,
    execute_supported_wordpress_mutation_adapter,
    wordpress_draft_activation_packet,
    wordpress_draft_apply_capability,
    wordpress_draft_execution_readiness_requirements,
    wordpress_draft_target_content_readiness_requirements,
    wordpress_draft_write_readiness,
    wordpress_draft_write_readiness_requirements,
)
from wilq.actions.wordpress_preview import (
    wordpress_draft_payload_preview_card,
)
from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.connectors.registry import get_connector_status
from wilq.content.workflow.store.store import (
    content_workflow_store as action_content_workflow_store,
)
from wilq.content.workflow.target.dev_draft_action import (
    refresh_content_target_draft_action,
)
from wilq.operator_labels import (
    blocker_count_label,
    evidence_count_label,
    source_connector_labels,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionConfirmRequest,
    ActionConfirmResult,
    ActionImpactCheckRequest,
    ActionImpactCheckResult,
    ActionMutationAuditRecord,
    ActionMutationReadinessBlocker,
    ActionMutationReadinessRequirement,
    ActionMutationReadinessResponse,
    ActionMutationReadinessSummaryResponse,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRequest,
    ActionPreviewResult,
    ActionReviewGate,
    ActionReviewRequest,
    ActionReviewResult,
    ActionValidationResult,
    ActionWordPressDraftApplyBlocker,
    AuditEvent,
)
from wilq.storage.local_state import local_state_store


def list_actions() -> list[ActionObject]:
    return _with_persisted_review_gates(action_catalog.list_actions())


def list_actions_cached() -> list[ActionObject]:
    return action_catalog.list_actions_cached(_with_persisted_review_gates)


def clear_action_list_cache() -> None:
    action_catalog.clear_action_list_cache()


def get_action(action_id: str) -> ActionObject | None:
    action = action_catalog.get_action(action_id)
    if action is None:
        return None
    action = refresh_content_target_draft_action(_with_persisted_validation_state(action))
    return _with_review_gate(
        action,
        _persisted_audit_events_for_action(action.id),
        _persisted_mutation_audits_for_action(action.id),
    )


def _plain_metric_value_label(
    value: Any,
    *,
    missing_label: str = "wartość niepotwierdzona",
) -> str:
    if isinstance(value, bool):
        return "tak" if value else "nie"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, str) and value:
        return value
    return missing_label


def validate_action(action: ActionObject) -> ActionValidationResult:
    return validate_action_lifecycle(
        action,
        review_gate=_action_review_gate,
        status_label=_action_result_status_label,
    )


def record_action_review(
    action: ActionObject,
    request: ActionReviewRequest,
) -> ActionReviewResult:
    submitted_actor_label = request.reviewed_by
    bound_request = request.model_copy(
        update={"reviewed_by": LOCAL_PILOT_AUDIT_IDENTITY.principal_id}
    )
    result = record_action_review_lifecycle(
        action,
        bound_request,
        review_summary=_action_review_summary,
        review_details=_action_review_details,
        review_gate=_action_review_gate,
        status_label=_action_result_status_label,
        audit_event_label=_audit_event_with_operator_label,
        review_gate_labels=_review_gate_with_operator_labels,
    )
    _stamp_local_audit_identity(result.audit_event, submitted_actor_label)
    return result


def preview_action(
    action: ActionObject,
    request: ActionPreviewRequest | None = None,
) -> ActionPreviewResult:
    return preview_action_lifecycle(
        action,
        request,
        review_gate=_action_review_gate,
        payload_preview_items=_payload_preview_items,
        preview_cards=_action_preview_cards,
        preview_item_view_models=action_preview_item_view_models,
        preview_blockers=action_preview_blockers,
        preview_summary=_action_preview_summary,
        build_preview_audit=build_preview_audit_event,
        preview_contract=_preview_contract,
        status_label=_action_result_status_label,
        gate_labels=_action_gate_labels,
        audit_event_label=_audit_event_with_operator_label,
        review_gate_labels=_review_gate_with_operator_labels,
        preview_row=_preview_row,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
        preview_contract_label=_preview_contract_label,
    )


def confirm_action(
    action: ActionObject,
    request: ActionConfirmRequest,
) -> ActionConfirmResult:
    submitted_actor_label = request.confirmed_by
    bound_request = request.model_copy(
        update={"confirmed_by": LOCAL_PILOT_AUDIT_IDENTITY.principal_id}
    )
    result = confirm_action_lifecycle(
        action,
        bound_request,
        review_gate=_action_review_gate,
        latest_preview=_latest_preview_event,
        confirmation_blockers=action_confirmation_blockers,
        confirmation_event_type=action_confirmation_event_type,
        confirmation_summary=action_confirmation_summary,
        ads_target_blockers=ads_target_confirmation_blockers,
        ads_target_summary=ads_target_confirmation_summary,
        gate_labels=_action_gate_labels,
        money_label=_micros_money_label,
        operator_note=_operator_note_sentence,
        build_confirmation_audit=build_confirmation_audit_event,
        status_label=_action_result_status_label,
        audit_event_label=_audit_event_with_operator_label,
        review_gate_labels=_review_gate_with_operator_labels,
    )
    _stamp_local_audit_identity(result.audit_event, submitted_actor_label)
    return result


def impact_check_action(
    action: ActionObject,
    request: ActionImpactCheckRequest,
) -> ActionImpactCheckResult:
    submitted_actor_label = request.checked_by
    bound_request = request.model_copy(
        update={"checked_by": LOCAL_PILOT_AUDIT_IDENTITY.principal_id}
    )
    result = impact_check_action_lifecycle(
        action,
        bound_request,
        review_gate=_action_review_gate,
        latest_confirmation=_latest_action_confirmation_event,
        status_label=_action_result_status_label,
        connector_labels=source_connector_labels,
        gate_labels=_action_gate_labels,
        evidence_summary_label=evidence_count_label,
        audit_event_label=_audit_event_with_operator_label,
        review_gate_labels=_review_gate_with_operator_labels,
    )
    _stamp_local_audit_identity(result.audit_event, submitted_actor_label)
    return result


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
) -> ActionApplyResult:
    workflow_store = action_content_workflow_store()
    submitted_actor_label = None if request is None else request.confirmed_by
    bound_request = (
        None
        if request is None
        else request
        if submitted_actor_label is None
        else request.model_copy(update={"confirmed_by": LOCAL_PILOT_AUDIT_IDENTITY.principal_id})
    )
    result = apply_action_lifecycle(
        action,
        bound_request,
        review_gate=_action_review_gate,
        wordpress_apply_capability=_wordpress_draft_apply_capability,
        mutation_adapter=_supported_mutation_adapter,
        execute_mutation_adapter=_execute_supported_mutation_adapter,
        connector_status=get_connector_status,
        impact_status=_impact_status_from_event,
        wordpress_apply_claim=workflow_store.claim_wordpress_revision_apply,
        finish_wordpress_apply_claim=workflow_store.finish_wordpress_revision_apply_claim,
        status_label=_action_result_status_label,
        audit_event_label=_audit_event_with_operator_label,
    )
    if submitted_actor_label is not None:
        _stamp_local_audit_identity(result.audit_event, submitted_actor_label)
        result.mutation_audit.principal_id = result.audit_event.principal_id
        result.mutation_audit.workspace_id = result.audit_event.workspace_id
        result.mutation_audit.trust_level = result.audit_event.trust_level
        result.mutation_audit.submitted_actor_label = submitted_actor_label
    return result


def _stamp_local_audit_identity(
    event: AuditEvent,
    submitted_actor_label: str | None,
) -> None:
    event.actor = LOCAL_PILOT_AUDIT_IDENTITY.principal_id
    event.principal_id = LOCAL_PILOT_AUDIT_IDENTITY.principal_id
    event.workspace_id = LOCAL_PILOT_AUDIT_IDENTITY.workspace_id
    event.trust_level = LOCAL_PILOT_AUDIT_IDENTITY.trust_level
    event.submitted_actor_label = submitted_actor_label


def _wordpress_draft_apply_capability(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[WordPressDraftApplyCapability | None, list[ActionWordPressDraftApplyBlocker]]:
    """Compatibility seam for callers/tests while ownership lives in WordPress requirements."""
    return wordpress_draft_apply_capability(action, request)


def mutation_readiness_action(action: ActionObject) -> ActionMutationReadinessResponse:
    return mutation_readiness_action_lifecycle(
        action,
        with_review_gate=lambda current, audits, mutation_audits: _with_review_gate(
            _with_persisted_validation_state(current), audits, mutation_audits
        ),
        persisted_audit_events=_persisted_audit_events_for_action,
        persisted_mutation_audits=_persisted_mutation_audits_for_action,
        connector_status=get_connector_status,
        mutation_adapter=_supported_mutation_adapter,
        latest_preview_event=_latest_preview_event,
        latest_confirmation_event=_latest_action_confirmation_event,
        latest_impact_check_event=_latest_action_impact_check_event,
        latest_mutation_audit=_latest_mutation_audit,
        wordpress_draft_readiness=wordpress_draft_write_readiness,
        wordpress_activation_packet=wordpress_draft_activation_packet,
        base_requirements=base_mutation_readiness_requirements,
        wordpress_execution_requirements=wordpress_draft_execution_readiness_requirements,
        wordpress_target_requirements=wordpress_draft_target_content_readiness_requirements,
        wordpress_write_requirements=wordpress_draft_write_readiness_requirements,
        blockers=_mutation_readiness_blockers,
        vendor_write_possible=_vendor_write_possible_impl,
        apply_contract=_mutation_apply_contract,
        target=mutation_readiness_target,
        response=build_mutation_readiness_response,
        operator_next_step=_mutation_readiness_next_step,
        payload_apply_allowed=_action_payload_apply_allowed,
        impact_status=_impact_status_from_event,
        evidence_label=evidence_count_label,
        preview_items=_payload_preview_items,
    )


def mutation_readiness_actions() -> ActionMutationReadinessSummaryResponse:
    items = [mutation_readiness_action(action) for action in list_actions()]
    blocker_counts: dict[str, int] = {}
    for item in items:
        for blocker in item.blockers:
            blocker_counts[blocker.code] = blocker_counts.get(blocker.code, 0) + 1
    first_write_candidate = _first_write_candidate(items)
    return build_mutation_readiness_summary(
        items=items,
        blocker_counts=blocker_counts,
        first_write_candidate=first_write_candidate,
        first_write_candidate_reason=_first_write_candidate_reason(first_write_candidate),
        activation_plan_steps=_activation_plan_steps(first_write_candidate),
        activation_next_step=_activation_next_step(first_write_candidate),
        operator_next_step=_mutation_readiness_summary_next_step,
    )


def _supported_mutation_adapter(action: ActionObject) -> str | None:
    return _supported_mutation_adapter_impl(action)


def _execute_supported_mutation_adapter(
    action: ActionObject,
    mutation_adapter: str,
    request: ActionApplyRequest | None,
    wordpress_capability: WordPressDraftApplyCapability | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    _ = request
    return execute_supported_wordpress_mutation_adapter(
        action,
        mutation_adapter,
        wordpress_capability,
    )


def _mutation_readiness_blockers(
    requirements: list[ActionMutationReadinessRequirement],
) -> list[ActionMutationReadinessBlocker]:
    return mutation_readiness_blockers(requirements)


def _mutation_readiness_next_step(
    action: ActionObject,
    blockers: list[ActionMutationReadinessBlocker],
) -> str:
    return _mutation_readiness_next_step_impl(action, blockers)


def _with_persisted_review_gates(actions: Iterable[ActionObject]) -> list[ActionObject]:
    return with_persisted_review_gates_state(
        actions,
        audit_events_by_action=_persisted_audit_events_by_action_id,
        mutation_audits_by_action=_persisted_mutation_audits_by_action_id,
        validation_state=_with_persisted_validation_state,
        review_gate=_with_review_gate,
    )


def _with_persisted_validation_state(action: ActionObject) -> ActionObject:
    return with_persisted_validation_state_state(
        action,
        state_loader=local_state_store().get_action_validation_state,
    )


def _with_review_gate(
    action: ActionObject,
    audit_events: list[AuditEvent] | None = None,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
) -> ActionObject:
    return with_review_gate_state(
        action,
        audit_events,
        mutation_audits,
        audit_event_has_raw_contract_text=_audit_event_has_raw_contract_text,
        content_payload_with_reviewed_previews=content_payload_with_reviewed_wordpress_draft_previews,
        payload_with_operator_labels=_payload_with_operator_labels,
        is_raw_content_review_audit_event=_is_raw_content_review_audit_event,
        action_review_gate=_action_review_gate,
        action_with_operator_labels=_action_with_operator_labels,
    )


def _action_with_operator_labels(action: ActionObject) -> ActionObject:
    return _action_with_operator_labels_impl(
        action,
        connector_label=_source_connector_label,
        evidence_summary_label=_action_evidence_summary_label,
        validation_status_label=_action_validation_status_label,
        review_gate=_review_gate_with_operator_labels,
        preview_cards=_action_preview_cards,
        audit_event=_audit_event_with_operator_label,
    )


def _action_preview_cards(action: ActionObject) -> list[ActionPreviewCardViewModel]:
    return build_action_preview_cards(
        action,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
        wordpress_draft_preview_card=wordpress_draft_payload_preview_card,
        source_connector_labels=_source_connector_labels,
        metric_fact_label=metric_fact_label,
        plain_metric_value_label=_plain_metric_value_label,
        action_gate_labels=action_gate_labels,
        business_context_summary=ads_strategy_review_summary,
    )


def demand_gen_readiness_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return build_demand_gen_readiness_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        channel_label=demand_gen_channel_label,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _review_gate_with_operator_labels(gate: ActionReviewGate) -> ActionReviewGate:
    return _review_gate_with_operator_labels_impl(
        gate,
        review_outcome_label=review_outcome_label,
        blocker_count_label=blocker_count_label,
    )


def _audit_event_with_operator_label(event: AuditEvent) -> AuditEvent:
    return _audit_event_with_operator_label_impl(
        event,
        string_list=_string_list,
        review_summary_item=_review_summary_item,
        review_blocker_label=_review_blocker_label,
    )


def _action_review_gate(
    action: ActionObject,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
) -> ActionReviewGate:
    return build_action_review_gate(
        action=action,
        mutation_audits=mutation_audits,
        action_apply_blockers_builder=_action_apply_blockers_impl,
        required_checks_builder=_action_required_checks,
        operator_checklist_builder=_action_operator_checklist,
        payload_apply_allowed=_action_payload_apply_allowed,
        supported_mutation_adapter=_supported_mutation_adapter,
        string_list=_string_list,
        gate_labels=_action_gate_labels,
        review_summary=lambda event: _operator_audit_summary_text(event.summary),
        confirmation_summary=_action_audit_summary_for_operator,
        impact_status=_impact_status_from_event,
    )


def _action_review_summary(request: ActionReviewRequest) -> str:
    return build_action_review_summary(
        request,
        outcome_label=review_outcome_label,
        summary_item=_review_summary_item,
        blocker_label=_review_blocker_label,
    )


def _review_summary_item(item: str) -> str:
    return build_review_summary_item(
        item,
        contract_label=content_contract_label,
        source_type_label=_review_source_type_label,
    )


def _review_blocker_label(item: str) -> str:
    return build_review_blocker_label(
        item,
        gate_label=_action_gate_label,
        contract_label=content_contract_label,
        blocked_claim_labels=operator_blocked_claims,
    )


def _review_source_type_label(value: str) -> str:
    return build_review_source_type_label(value, contract_label=content_contract_label)


def _canonical_contract_key(value: str) -> str:
    return canonical_review_contract_key(value)


def _action_review_details(request: ActionReviewRequest) -> dict[str, Any]:
    return build_action_review_details(
        request,
        content_url_review_details=_content_url_review_details_from_checked_items,
        draft_readiness_review_details=_draft_readiness_review_details_from_checked_items,
    )


def _preview_contract(payload: dict[str, Any], preview_items: list[dict[str, Any]]) -> str | None:
    return _payload_preview_contract_impl(payload, preview_items)


def _action_required_checks(payload: dict[str, Any]) -> list[str]:
    return build_action_required_checks(
        payload,
        string_list=_string_list,
        preview_items=_payload_preview_items,
        unique_values=unique_values,
    )


def _action_operator_checklist(payload: dict[str, Any]) -> list[str]:
    return build_action_operator_checklist(
        payload,
        string_list=_string_list,
        required_checks=lambda: _action_required_checks(payload),
    )


def _action_gate_labels(values: Iterable[str]) -> list[str]:
    return action_gate_labels(values)


def _action_audit_event_label(event_type: str) -> str:
    """Compatibility facade for API context compaction callers."""
    return _audit_event_label_impl(event_type)


def _source_connector_label(connector_id: str) -> str:
    connector = get_connector_status(connector_id)
    return connector.label if connector is not None and connector.label else "źródło danych"


def _source_connector_labels(connector_ids: Iterable[str]) -> list[str]:
    labels: list[str] = []
    for connector_id in connector_ids:
        label = _source_connector_label(connector_id)
        if label not in labels:
            labels.append(label)
    return labels


def _operator_audit_summary_text(summary: str) -> str:
    """Compatibility facade for callers that import the legacy service helper."""
    return _operator_audit_summary_text_impl(summary)


def _payload_with_operator_labels(payload: dict[str, Any]) -> dict[str, Any]:
    return payload_with_operator_labels(payload)


def _ads_recommendation_type_label(value: str) -> str:
    """Compatibility facade for callers that import the legacy service helper."""
    return ads_recommendation_type_label(value)


def _action_payload_apply_allowed(payload: dict[str, Any]) -> bool:
    return payload_apply_allowed(payload, _payload_preview_items(payload))


def _action_payload_api_mutation_ready(payload: dict[str, Any]) -> bool:
    return payload_api_mutation_ready(payload, _payload_preview_items(payload))


def _payload_preview_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _payload_preview_items_impl(payload)


def _latest_preview_event(events: list[AuditEvent]) -> AuditEvent | None:
    return _latest_preview_event_impl(events)


def _latest_action_confirmation_event(events: list[AuditEvent]) -> AuditEvent | None:
    return _latest_action_confirmation_event_impl(events)


def _latest_action_impact_check_event(events: list[AuditEvent]) -> AuditEvent | None:
    return _latest_action_impact_check_event_impl(events)


def _latest_mutation_audit(
    audits: list[ActionMutationAuditRecord],
) -> ActionMutationAuditRecord | None:
    return _latest_mutation_audit_impl(audits)


def _impact_status_from_event(event: AuditEvent | None) -> Literal["checked", "blocked"] | None:
    if event is None:
        return None
    if event.event_type == "action_impact_check_completed":
        return "checked"
    if event.event_type == "action_impact_check_blocked":
        return "blocked"
    return None
