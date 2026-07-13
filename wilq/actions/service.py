from __future__ import annotations

import os
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from time import monotonic
from typing import Any, Literal

from wilq.actions.action_blockers import (
    action_apply_blockers as _action_apply_blockers_impl,
)
from wilq.actions.action_blockers import (
    action_confirmation_blockers,
    action_confirmation_event_type,
    action_confirmation_summary,
    action_preview_blockers,
    ads_target_confirmation_summary,
)
from wilq.actions.action_blockers import (
    action_preview_summary as _action_preview_summary,
)
from wilq.actions.action_previews import action_preview_cards as build_action_preview_cards
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
from wilq.actions.content_candidates import seed_metric_actions as seed_content_metric_actions
from wilq.actions.content_refresh import (
    content_contract_label,
    content_contract_labels,
    content_payload_with_reviewed_wordpress_draft_previews,
    content_refresh_metric_candidate,
    post_publication_measurement_plan,
    post_publication_measurement_summary,
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
from wilq.actions.ga4.tracking_quality import ga4_tracking_quality_action_from_metric_facts
from wilq.actions.gate_labels import (
    action_gate_label as _action_gate_label,
)
from wilq.actions.gate_labels import (
    action_gate_labels,
)
from wilq.actions.google_ads.action_candidates import (
    seed_metric_actions as seed_google_ads_metric_actions,
)
from wilq.actions.google_ads.business_context import (
    ads_business_context_configured,
    ads_business_context_missing_read_contracts,
    ads_strategy_review_state,
    ads_strategy_review_summary,
    business_context_action,
    latest_google_ads_metric_facts,
    latest_google_ads_vendor_read,
    strategy_review_action,
    target_confirmation_action,
)
from wilq.actions.google_ads.business_context import (
    connector_refresh_recency_key as ads_connector_refresh_recency_key,
)
from wilq.actions.google_ads.business_context import (
    micros_money_label as _micros_money_label,
)
from wilq.actions.google_ads.campaign_review import (
    campaign_review_action_from_metric_facts,
)
from wilq.actions.google_ads.change_history import (
    change_history_impact_action_from_metric_facts,
)
from wilq.actions.google_ads.custom_segments import (
    custom_segment_action_from_metric_facts,
)
from wilq.actions.google_ads.demand_gen import (
    demand_gen_channel_label,
    demand_gen_readiness_action_from_metric_facts,
    latest_vendor_read_evidence_ids,
)
from wilq.actions.google_ads.demand_gen_preview import (
    demand_gen_readiness_preview_cards as build_demand_gen_readiness_preview_cards,
)
from wilq.actions.google_ads.keyword_planner import (
    keyword_planner_access_action_from_vendor_read,
)
from wilq.actions.google_ads.negative_keywords import (
    negative_keyword_action_from_metric_facts,
)
from wilq.actions.google_ads.recommendations import (
    recommendation_review_action_from_metric_facts,
)
from wilq.actions.google_ads.search_term_ngrams import (
    search_term_ngram_action_from_metric_facts,
)
from wilq.actions.impact_lifecycle import impact_check_action as impact_check_action_lifecycle
from wilq.actions.localo.visibility import (
    localo_action_metric_facts,
    localo_visibility_review_action_from_metric_facts,
    localo_visibility_review_payload_from_metric_facts,
)
from wilq.actions.merchant import (
    MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
    merchant_feed_issue_action_from_metric_facts,
)
from wilq.actions.metric_action_candidates import (
    seed_non_ads_metric_actions,
)
from wilq.actions.metric_action_facts import load_action_metric_facts
from wilq.actions.metric_utils import (
    facts_by_connector as _facts_by_connector_impl,
)
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
from wilq.actions.registry_assembly import (
    assemble_action_registry,
    seed_static_actions,
)
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
from wilq.actions.service_profile import (
    service_profile_knowledge_promotion_action,
    service_profile_private_proposal_promotion_action,
)
from wilq.actions.social import social_draft_actions
from wilq.actions.wordpress_draft import (
    draft_apply_action,
    draft_handoff_action,
)
from wilq.actions.wordpress_handoff import (
    build_draft_apply_action,
    build_draft_apply_contract_payload,
    build_draft_handoff_action,
    build_draft_handoff_preview_item,
)
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
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.content.knowledge.service_profile import content_service_profile_response
from wilq.evidence.registry import connector_evidence_id
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
    ActionStatus,
    ActionValidationResult,
    AuditEvent,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

DEFAULT_ACTION_LIST_CACHE_SECONDS = 15.0


@dataclass(frozen=True)
class ActionListCacheEntry:
    created_at: float
    actions: list[ActionObject]
    google_ads_registry_key: tuple[str, str, bool] | None = None


_cached_action_list: ActionListCacheEntry | None = None


def _service_profile_knowledge_promotion_action() -> ActionObject | None:
    return service_profile_knowledge_promotion_action(profile=content_service_profile_response())


def _service_profile_private_proposal_promotion_action() -> ActionObject | None:
    return service_profile_private_proposal_promotion_action(
        profile=content_service_profile_response()
    )


_STATIC_ACTIONS = seed_static_actions(
    additional_actions=(
        _service_profile_knowledge_promotion_action(),
        _service_profile_private_proposal_promotion_action(),
    )
)
ACTION_METRIC_CONNECTORS = (
    "google_ads",
    "google_merchant_center",
    "google_analytics_4",
    "google_search_console",
    "wordpress_ekologus",
    "ahrefs",
    "localo",
)
ACTION_METRIC_FACT_LIMIT = 500
ACTION_METRIC_FACT_LIMITS = {
    "google_ads": ACTION_METRIC_FACT_LIMIT,
    "google_analytics_4": ACTION_METRIC_FACT_LIMIT,
    "google_merchant_center": ACTION_METRIC_FACT_LIMIT,
    "google_search_console": ACTION_METRIC_FACT_LIMIT,
    "wordpress_ekologus": ACTION_METRIC_FACT_LIMIT,
    "ahrefs": ACTION_METRIC_FACT_LIMIT,
    "localo": ACTION_METRIC_FACT_LIMIT,
}


def list_actions() -> list[ActionObject]:
    return _with_persisted_review_gates(_action_registry().values())


def list_actions_cached() -> list[ActionObject]:
    """Reuse one action registry build across the dashboard list reads."""
    cached = _read_action_list_cache()
    if cached is not None:
        return cached
    actions: list[ActionObject] = []
    for _ in range(2):
        registry_key = _google_ads_registry_cache_key()
        actions = list_actions()
        if registry_key == _google_ads_registry_cache_key():
            _write_action_list_cache(actions, google_ads_registry_key=registry_key)
            return actions
    return actions


def clear_action_list_cache() -> None:
    global _cached_action_list
    _cached_action_list = None


def _read_action_list_cache() -> list[ActionObject] | None:
    cache_seconds = _action_list_cache_seconds()
    if cache_seconds <= 0 or _cached_action_list is None:
        return None
    if monotonic() - _cached_action_list.created_at > cache_seconds:
        return None
    if _cached_action_list.google_ads_registry_key != _google_ads_registry_cache_key():
        return None
    return _cached_action_list.actions


def _write_action_list_cache(
    actions: list[ActionObject],
    *,
    google_ads_registry_key: tuple[str, str, bool] | None,
) -> None:
    global _cached_action_list
    if _action_list_cache_seconds() <= 0:
        return
    _cached_action_list = ActionListCacheEntry(
        created_at=monotonic(),
        actions=actions,
        google_ads_registry_key=google_ads_registry_key,
    )


def _action_list_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_ACTION_LIST_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_ACTION_LIST_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_ACTION_LIST_CACHE_SECONDS


def _action_registry() -> dict[str, ActionObject]:
    return assemble_action_registry(
        _STATIC_ACTIONS,
        seed_metric_action_candidates(),
        live_data_available=_google_ads_live_data_available(),
        configure_action_id="act_configure_google_ads_env",
        live_actions=(
            _google_ads_business_context_action(),
            _google_ads_target_confirmation_action(),
            _google_ads_strategy_review_action(),
            keyword_planner_access_action_from_vendor_read(_latest_google_ads_vendor_read()),
        ),
    )


def get_action(action_id: str) -> ActionObject | None:
    cached_actions = _read_action_list_cache()
    action = next(
        (cached_action for cached_action in cached_actions or [] if cached_action.id == action_id),
        None,
    )
    if action is not None:
        action = action.model_copy(deep=True)
    else:
        action = _action_registry().get(action_id)
    if action is None:
        return None
    action = _with_persisted_validation_state(action)
    return _with_review_gate(
        action,
        _persisted_audit_events_for_action(action.id),
        _persisted_mutation_audits_for_action(action.id),
    )


def _google_ads_live_data_available() -> bool:
    latest_run = _latest_google_ads_vendor_read()
    if latest_run is None:
        return False
    return (
        latest_run.status == ConnectorRefreshStatus.completed
        and latest_run.vendor_data_collected is True
    )


def _google_ads_registry_cache_key() -> tuple[str, str, bool] | None:
    latest_run = _latest_google_ads_vendor_read()
    if latest_run is None:
        return None
    return (latest_run.id, latest_run.status.value, latest_run.vendor_data_collected)


def _latest_google_ads_vendor_read() -> ConnectorRefreshRun | None:
    return latest_google_ads_vendor_read(
        list_connector_refresh_runs(connector_id="google_ads")
    )


def _connector_refresh_recency_key(run: ConnectorRefreshRun) -> tuple[str, str]:
    return ads_connector_refresh_recency_key(run)


def _google_ads_business_context_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or ads_business_context_configured()
    ):
        return None
    missing_read_contracts = ads_business_context_missing_read_contracts()
    return business_context_action(
        missing_read_contracts=missing_read_contracts,
        evidence_ids=unique_values(
            [connector_evidence_id("google_ads"), *latest_run.evidence_ids]
        ),
    )


def _google_ads_target_confirmation_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    missing_read_contracts = ads_business_context_missing_read_contracts()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or not ads_business_context_configured()
        or "target_roas_or_cpa" not in missing_read_contracts
    ):
        return None
    return target_confirmation_action(
        missing_read_contracts=missing_read_contracts,
        evidence_ids=unique_values(
            [connector_evidence_id("google_ads"), *latest_run.evidence_ids]
        ),
    )


def _google_ads_strategy_review_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    latest_review = ads_strategy_review_state()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or not ads_business_context_configured()
        or (latest_review is not None and latest_review.outcome == "approved_for_prepare")
    ):
        return None
    return strategy_review_action(
        evidence_ids=unique_values(
            [connector_evidence_id("google_ads"), *latest_run.evidence_ids]
        ),
    )


def seed_metric_action_candidates() -> dict[str, ActionObject]:
    facts = _action_metric_facts()
    by_connector = _facts_by_connector(facts)
    actions: dict[str, ActionObject] = {}

    actions.update(
        seed_non_ads_metric_actions(
            by_connector=by_connector,
            merchant_action=lambda facts: merchant_feed_issue_action_from_metric_facts(
                facts,
                preview_contract=MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
            ),
            ga4_action=ga4_tracking_quality_action_from_metric_facts,
            localo_facts=_localo_action_metric_facts,
            localo_payload=localo_visibility_review_payload_from_metric_facts,
            localo_action=localo_visibility_review_action_from_metric_facts,
            social_action=social_draft_actions,
        )
    )
    _seed_content_metric_actions(by_connector, actions)
    _seed_google_ads_metric_actions(by_connector, actions)
    return actions


def _seed_content_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    content_facts = [
        *by_connector.get("wordpress_ekologus", []),
        *by_connector.get("google_search_console", []),
        *by_connector.get("ahrefs", []),
    ]
    actions.update(
        seed_content_metric_actions(
            content_facts=content_facts,
            candidate_builder=content_refresh_metric_candidate,
            draft_handoff_builder=_wordpress_draft_handoff_action,
            draft_apply_builder=_wordpress_draft_apply_action,
        )
    )


def _seed_google_ads_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    google_ads_facts = by_connector.get("google_ads", [])
    actions.update(
        seed_google_ads_metric_actions(
            google_ads_facts=google_ads_facts,
            ga4_facts=by_connector.get("google_analytics_4", []),
            latest_google_ads_evidence_ids=latest_vendor_read_evidence_ids("google_ads"),
            latest_ga4_evidence_ids=latest_vendor_read_evidence_ids("google_analytics_4"),
            demand_gen_action=demand_gen_readiness_action_from_metric_facts,
            campaign_review_action=campaign_review_action_from_metric_facts,
            recommendation_action=recommendation_review_action_from_metric_facts,
            change_history_action=change_history_impact_action_from_metric_facts,
            search_term_ngram_action=search_term_ngram_action_from_metric_facts,
            custom_segment_action=custom_segment_action_from_metric_facts,
            negative_keyword_action=negative_keyword_action_from_metric_facts,
        )
    )


def _localo_action_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return localo_action_metric_facts(
        facts=facts,
        refresh_runs=list_connector_refresh_runs(connector_id="localo"),
        metric_facts_by_evidence_ids=metric_store().list_metric_facts_by_evidence_ids,
        is_probe_only_fact=_is_probe_only_fact,
    )


def _action_metric_facts() -> list[MetricFact]:
    return load_action_metric_facts(
        store=metric_store(),
        connector_ids=ACTION_METRIC_CONNECTORS,
        limits=ACTION_METRIC_FACT_LIMITS,
        latest_google_ads_facts=_latest_google_ads_metric_facts,
        is_probe_only_fact=_is_probe_only_fact,
    )


def _latest_google_ads_metric_facts() -> list[MetricFact]:
    return latest_google_ads_metric_facts(
        _latest_google_ads_vendor_read(),
        metric_facts_by_evidence_ids=metric_store().list_metric_facts_by_evidence_ids,
    )


def _wordpress_draft_handoff_action(
    *,
    content_payload: dict[str, Any] | None,
    content_action_metrics: list[MetricFact],
) -> ActionObject | None:
    return build_draft_handoff_action(
        content_payload=content_payload,
        content_action_metrics=content_action_metrics,
        preview_item=_wordpress_draft_handoff_preview_item,
        handoff_builder=draft_handoff_action,
        unique_values=unique_values,
    )


def _wordpress_draft_apply_action(*, handoff_action: ActionObject) -> ActionObject:
    return build_draft_apply_action(
        handoff_action=handoff_action,
        apply_builder=draft_apply_action,
        apply_contract_payload=_wordpress_draft_apply_contract_payload,
    )


def _wordpress_draft_apply_contract_payload(
    handoff_action: ActionObject,
) -> dict[str, Any]:
    return build_draft_apply_contract_payload(handoff_action)


def _wordpress_draft_handoff_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    return build_draft_handoff_preview_item(
        item,
        contract_label=content_contract_label,
        contract_labels=content_contract_labels,
        measurement_plan=post_publication_measurement_plan,
        measurement_summary=post_publication_measurement_summary,
    )


def _facts_by_connector(facts: list[MetricFact]) -> dict[str, list[MetricFact]]:
    return _facts_by_connector_impl(facts)


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


def _is_probe_only_fact(fact: MetricFact) -> bool:
    if (
        fact.source_connector == "localo"
        and fact.name == "api"
        and fact.value == "localo_mcp_oauth_probe"
    ):
        return True
    return fact.source_connector == "localo" and fact.name in {
        "access_token_present",
        "authorization_code_supported",
        "pkce_s256_supported",
        "mcp_initialize_status",
    }


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
    return record_action_review_lifecycle(
        action,
        request,
        review_summary=_action_review_summary,
        review_details=_action_review_details,
        review_gate=_action_review_gate,
        status_label=_action_result_status_label,
        audit_event_label=_audit_event_with_operator_label,
        review_gate_labels=_review_gate_with_operator_labels,
    )


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
    return confirm_action_lifecycle(
        action,
        request,
        review_gate=_action_review_gate,
        latest_preview=_latest_preview_event,
        confirmation_blockers=action_confirmation_blockers,
        confirmation_event_type=action_confirmation_event_type,
        confirmation_summary=action_confirmation_summary,
        ads_target_blockers=_ads_target_confirmation_blockers,
        ads_target_summary=ads_target_confirmation_summary,
        gate_labels=_action_gate_labels,
        money_label=_micros_money_label,
        operator_note=_operator_note_sentence,
        build_confirmation_audit=build_confirmation_audit_event,
        status_label=_action_result_status_label,
        audit_event_label=_audit_event_with_operator_label,
        review_gate_labels=_review_gate_with_operator_labels,
    )


def impact_check_action(
    action: ActionObject,
    request: ActionImpactCheckRequest,
) -> ActionImpactCheckResult:
    return impact_check_action_lifecycle(
        action,
        request,
        review_gate=_action_review_gate,
        latest_confirmation=_latest_action_confirmation_event,
        status_label=_action_result_status_label,
        connector_labels=source_connector_labels,
        gate_labels=_action_gate_labels,
        evidence_summary_label=evidence_count_label,
        audit_event_label=_audit_event_with_operator_label,
        review_gate_labels=_review_gate_with_operator_labels,
    )


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
) -> ActionApplyResult:
    return apply_action_lifecycle(
        action,
        request,
        review_gate=_action_review_gate,
        wordpress_apply_capability=_wordpress_draft_apply_capability,
        connector_status=get_connector_status,
        impact_status=_impact_status_from_event,
        status_label=_action_result_status_label,
        audit_event_label=_audit_event_with_operator_label,
    )


def _wordpress_draft_apply_capability(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[WordPressDraftApplyCapability | None, list[str]]:
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
    action_list = list(actions)
    action_ids = {action.id for action in action_list}
    audit_events_by_action_id = _persisted_audit_events_by_action_id(action_ids)
    mutation_audits_by_action_id = _persisted_mutation_audits_by_action_id(action_ids)
    return [
        _with_review_gate(
            _with_persisted_validation_state(action),
            audit_events_by_action_id.get(action.id, []),
            mutation_audits_by_action_id.get(action.id, []),
        )
        for action in action_list
    ]


def _with_persisted_validation_state(action: ActionObject) -> ActionObject:
    state = local_state_store().get_action_validation_state(action.id)
    if state is None:
        return action
    validation_status = state.get("validation_status")
    status = state.get("status")
    if validation_status in {"valid", "invalid", "not_validated"}:
        action.validation_status = validation_status
    if isinstance(status, str):
        with suppress(ValueError):
            action.status = ActionStatus(status)
    return action


def _with_review_gate(
    action: ActionObject,
    audit_events: list[AuditEvent] | None = None,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
) -> ActionObject:
    if audit_events is not None:
        action.audit_events = audit_events[:10]
    state_audit_events = [
        event for event in action.audit_events if not _audit_event_has_raw_contract_text(event)
    ]
    action.payload = content_payload_with_reviewed_wordpress_draft_previews(
        action.payload,
        review_event_summaries=(
            event.summary
            for event in state_audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
        review_event_details=(
            event.details
            for event in state_audit_events
            if event.event_type == "human_review_approved_for_prepare"
        ),
    )
    action.payload = _payload_with_operator_labels(action.payload)
    review_gate_events = [
        event
        for event in action.audit_events
        if not _is_raw_content_review_audit_event(action.id, event)
    ]
    action.review_gate = _action_review_gate(
        action.model_copy(update={"audit_events": review_gate_events}),
        mutation_audits,
    )
    return _action_with_operator_labels(action)


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

def _ads_target_confirmation_blockers(request: ActionConfirmRequest) -> list[str]:
    blockers: list[str] = []
    target_count = int(request.target_roas is not None) + int(request.target_cpa_micros is not None)
    if target_count == 0:
        blockers.append("target_roas_or_cpa_required")
    if target_count > 1:
        blockers.append("exactly_one_target_guardrail_allowed")
    return blockers


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
