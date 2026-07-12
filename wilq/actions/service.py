from __future__ import annotations

import os
import re
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from time import monotonic
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import uuid4

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
from wilq.actions.content_preview import (
    content_refresh_preview_cards,
)
from wilq.actions.content_refresh import (
    content_contract_label,
    content_contract_labels,
    content_payload_with_reviewed_wordpress_draft_previews,
    content_refresh_metric_candidate,
    post_publication_measurement_plan,
    post_publication_measurement_summary,
    seed_content_refresh_action,
)
from wilq.actions.content_review_details import (
    content_url_review_details as _content_url_review_details_from_checked_items,
)
from wilq.actions.content_review_details import (
    draft_readiness_review_details as _draft_readiness_review_details_from_checked_items,
)
from wilq.actions.ga4.tracking_preview import (
    ga4_tracking_quality_preview_cards as build_ga4_tracking_quality_preview_cards,
)
from wilq.actions.ga4.tracking_preview import (
    metric_snapshot_preview_rows,
)
from wilq.actions.ga4.tracking_quality import (
    ga4_tracking_quality_action_from_metric_facts,
    seed_ga4_tracking_quality_action,
)
from wilq.actions.gate_labels import (
    action_gate_label as _action_gate_label,
)
from wilq.actions.gate_labels import (
    action_gate_labels,
)
from wilq.actions.google_ads.business_context import (
    ads_business_context_configured,
    ads_business_context_missing_read_contracts,
    ads_strategy_review_state,
    ads_strategy_review_summary,
    business_context_action,
    strategy_review_action,
    target_confirmation_action,
)
from wilq.actions.google_ads.business_context import (
    ads_business_context_preview_rows as build_ads_business_context_preview_rows,
)
from wilq.actions.google_ads.business_context import (
    ads_strategy_review_preview_cards as build_ads_strategy_review_preview_cards,
)
from wilq.actions.google_ads.business_context import (
    ads_target_guardrail_preview_cards as build_ads_target_guardrail_preview_cards,
)
from wilq.actions.google_ads.campaign_review import (
    campaign_review_action_from_metric_facts,
)
from wilq.actions.google_ads.change_history import (
    change_history_impact_action_from_metric_facts,
    change_history_preview_cards,
)
from wilq.actions.google_ads.custom_segments import (
    custom_segment_action_from_metric_facts,
    custom_segment_preview_cards,
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
    KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
    keyword_planner_access_action,
)
from wilq.actions.google_ads.keyword_planner import (
    keyword_planner_access_preview_cards as build_keyword_planner_access_preview_cards,
)
from wilq.actions.google_ads.negative_keywords import (
    negative_keyword_action_from_metric_facts,
    negative_keyword_preview_cards,
)
from wilq.actions.google_ads.oauth import oauth_repair_action
from wilq.actions.google_ads.previews import budget_preview_cards
from wilq.actions.google_ads.recommendations import (
    recommendation_preview_cards,
    recommendation_review_action_from_metric_facts,
    seed_recommendation_review_action,
)
from wilq.actions.google_ads.search_term_ngram_preview import (
    search_term_ngram_preview_cards as build_search_term_ngram_preview_cards,
)
from wilq.actions.google_ads.search_term_ngrams import (
    SEARCH_TERM_NGRAM_PREVIEW_CONTRACT,
    search_term_ngram_action_from_metric_facts,
)
from wilq.actions.localo.visibility import (
    localo_visibility_review_action_from_metric_facts,
    localo_visibility_review_payload_from_metric_facts,
)
from wilq.actions.localo.visibility_preview import (
    local_visibility_preview_cards as build_local_visibility_preview_cards,
)
from wilq.actions.localo.visibility_preview import (
    metric_snapshot_preview_rows_for_keys,
)
from wilq.actions.merchant import (
    MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
    merchant_feed_issue_action_from_metric_facts,
    seed_merchant_feed_issue_action,
)
from wilq.actions.merchant_preview import merchant_preview_cards as build_merchant_preview_cards
from wilq.actions.metric_utils import (
    metric_fact_label,
    unique_values,
)
from wilq.actions.mutation_contract import mutation_apply_contract as _mutation_apply_contract
from wilq.actions.mutation_plan import activation_next_step as _activation_next_step
from wilq.actions.mutation_plan import activation_plan_steps as _activation_plan_steps
from wilq.actions.mutation_plan import first_write_candidate as _first_write_candidate
from wilq.actions.mutation_plan import first_write_candidate_reason as _first_write_candidate_reason
from wilq.actions.mutation_plan import (
    mutation_readiness_summary_next_step as _mutation_readiness_summary_next_step,
)
from wilq.actions.mutation_readiness import mutation_readiness_blockers
from wilq.actions.mutation_requirements import base_mutation_readiness_requirements
from wilq.actions.mutation_response import build_mutation_readiness_response
from wilq.actions.mutation_summary import build_mutation_readiness_summary
from wilq.actions.mutation_target import mutation_readiness_target
from wilq.actions.operator_labels import (
    action_evidence_summary_label as _action_evidence_summary_label,
)
from wilq.actions.operator_labels import (
    action_mode_label as _action_mode_label,
)
from wilq.actions.operator_labels import (
    action_mutation_adapter_label as _action_mutation_adapter_label,
)
from wilq.actions.operator_labels import (
    action_mutation_adapter_reached_label as _action_mutation_adapter_reached_label,
)
from wilq.actions.operator_labels import (
    action_mutation_attempted_label as _action_mutation_attempted_label,
)
from wilq.actions.operator_labels import (
    action_mutation_audit_status_label as _action_mutation_audit_status_label,
)
from wilq.actions.operator_labels import (
    action_mutation_audit_trace_label as _action_mutation_audit_trace_label,
)
from wilq.actions.operator_labels import (
    action_result_status_label as _action_result_status_label,
)
from wilq.actions.operator_labels import (
    action_review_gate_status_label as _action_review_gate_status_label,
)
from wilq.actions.operator_labels import (
    action_risk_label as _action_risk_label,
)
from wilq.actions.operator_labels import (
    action_status_label as _action_status_label,
)
from wilq.actions.operator_labels import (
    action_validation_status_label as _action_validation_status_label,
)
from wilq.actions.payload_readiness import (
    payload_api_mutation_ready,
    payload_apply_allowed,
)
from wilq.actions.payloads import (
    validate_action_payload,
)
from wilq.actions.review_gate import (
    action_review_summary as build_action_review_summary,
)
from wilq.actions.review_gate import (
    build_action_review_gate,
    latest_human_review_event,
    review_outcome_from_event,
    review_outcome_label,
)
from wilq.actions.review_gate import (
    canonical_contract_key as canonical_review_contract_key,
)
from wilq.actions.review_gate import (
    review_blocker_label as build_review_blocker_label,
)
from wilq.actions.review_gate import (
    review_source_type_label as build_review_source_type_label,
)
from wilq.actions.review_gate import (
    review_summary_item as build_review_summary_item,
)
from wilq.actions.service_profile import (
    knowledge_promotion_action,
    knowledge_promotion_preview_cards,
    private_proposal_promotion_action,
    private_proposal_promotion_preview_cards,
)
from wilq.actions.social import social_draft_actions, social_draft_input_preview_cards
from wilq.actions.wordpress_draft import (
    draft_apply_action,
    draft_handoff_action,
    existing_draft_update_action,
)
from wilq.actions.wordpress_mutation_requirements import (
    wordpress_draft_execution_readiness_requirements,
    wordpress_draft_target_content_readiness_requirements,
)
from wilq.actions.wordpress_preview import (
    wordpress_draft_handoff_preview_cards,
    wordpress_draft_payload_preview_card,
)
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.connectors.wordpress.client import create_wordpress_draft_post
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import ContentWordPressDraftHandoff
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftWriteAuthorization,
    execute_content_wordpress_draft_handoff,
)
from wilq.content.knowledge.service_profile import content_service_profile_response
from wilq.content.workflow.api import (
    build_content_wordpress_draft_activation_packet_response,
    build_content_wordpress_draft_write_readiness_response,
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_diagnostics_snapshot_response_for_work_item,
)
from wilq.content.workflow.contracts import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
)
from wilq.content.workflow.store import content_workflow_store
from wilq.credentials.runtime import variable_value
from wilq.evidence.registry import SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID, connector_evidence_id
from wilq.operator_labels import (
    blocker_count_label,
    evidence_count_label,
    impact_comparison_summary_label,
    source_connector_labels,
)
from wilq.schemas import (
    ActionApplyRequest,
    ActionApplyResult,
    ActionConfirmRequest,
    ActionConfirmResult,
    ActionImpactCheckRequest,
    ActionImpactCheckResult,
    ActionMode,
    ActionMutationAuditRecord,
    ActionMutationReadinessBlocker,
    ActionMutationReadinessRequirement,
    ActionMutationReadinessResponse,
    ActionMutationReadinessSummaryResponse,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewItemViewModel,
    ActionPreviewRequest,
    ActionPreviewResult,
    ActionPreviewRowViewModel,
    ActionReviewGate,
    ActionReviewRequest,
    ActionReviewResult,
    ActionRisk,
    ActionStatus,
    ActionValidationResult,
    AuditEvent,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

SERVICE_PROFILE_PUBLIC_REVIEW_SCOPES = {"public_service_card"}
SERVICE_PROFILE_PRIVATE_REVIEW_SCOPES = {
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
}
DEFAULT_ACTION_LIST_CACHE_SECONDS = 15.0


@dataclass(frozen=True)
class WordPressDraftApplyCapability:
    handoff: ContentWordPressDraftHandoff
    draft_package: ContentDraftPackage
    write_authorization: ContentWordPressDraftWriteAuthorization


@dataclass(frozen=True)
class ActionListCacheEntry:
    created_at: float
    actions: list[ActionObject]


_cached_action_list: ActionListCacheEntry | None = None


def seed_static_actions() -> dict[str, ActionObject]:
    actions = seed_core_prepare_actions()
    action = oauth_repair_action()
    actions[action.id] = action
    return actions


def seed_core_prepare_actions() -> dict[str, ActionObject]:
    actions = [
        seed_recommendation_review_action(),
        seed_merchant_feed_issue_action(),
        seed_ga4_tracking_quality_action(),
        seed_content_refresh_action(),
    ]
    service_profile_action = _service_profile_knowledge_promotion_action()
    if service_profile_action is not None:
        actions.append(service_profile_action)
    private_proposal_action = _service_profile_private_proposal_promotion_action()
    if private_proposal_action is not None:
        actions.append(private_proposal_action)
    actions.append(_wordpress_existing_draft_update_action())
    return {action.id: action for action in actions}


def _wordpress_existing_draft_update_action() -> ActionObject:
    return existing_draft_update_action()


def _service_profile_knowledge_promotion_action() -> ActionObject | None:
    profile = content_service_profile_response()
    review_actions_by_target = {
        action.target_card_id: action
        for action in profile.review_actions
        if action.review_scope in SERVICE_PROFILE_PUBLIC_REVIEW_SCOPES
        and action.target_card_id
    }
    rows: list[dict[str, Any]] = []
    for section in profile.service_sections:
        review_action = review_actions_by_target.get(section.card_id)
        if review_action is None:
            continue
        if section.status != "source_backed_review_required":
            continue
        if "public_site" not in section.source_connector_labels:
            continue
        rows.append(
            {
                "id": f"knowledge_promotion_{section.card_id}",
                "preview_contract": "service_profile_knowledge_promotion_preview_v1",
                "operation_type": "knowledge_card_promotion_review",
                "target_card_id": section.card_id,
                "target_card_title": section.title,
                "current_lifecycle": section.status,
                "current_lifecycle_label": section.status_label,
                "target_lifecycle": "approved_current",
                "target_lifecycle_label": "zatwierdzone i aktualne po review człowieka",
                "source_fact_ids": section.source_fact_ids,
                "source_connector_labels": section.source_connector_labels,
                "source_lineage_labels": section.source_lineage_labels,
                "review_action_id": review_action.action_id,
                "required_human_role": review_action.required_human_role,
                "blocked_claims": [claim.label for claim in section.forbidden_claims],
                "claims_needing_review": [
                    claim.label for claim in section.claims_needing_review
                ],
                "required_validation": [
                    "public_source_trace_review",
                    "blocked_claims_review",
                    "owner_human_review_record",
                    "separate_audited_promotion_request",
                ],
                "required_validation_labels": [
                    "sprawdź źródła publiczne",
                    "sprawdź zakazane twierdzenia",
                    "zapisz decyzję Wilka/ownera",
                    "przygotuj osobny audyt awansu",
                ],
                "promotion_blocked_reason": (
                    "Ta akcja tylko przygotowuje request po review. Nie edytuje "
                    "source_facts.json, nie zmienia lifecycle i nie odblokowuje "
                    "production-depth."
                ),
                "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            }
        )
    if not rows:
        return None
    return knowledge_promotion_action(
        source_fact_count=profile.technical_trace.source_fact_count,
        rows=rows,
    )


def _service_profile_private_proposal_promotion_action() -> ActionObject | None:
    profile = content_service_profile_response()
    review_actions_by_target = {
        action.target_card_id: action
        for action in profile.review_actions
        if action.review_scope in SERVICE_PROFILE_PRIVATE_REVIEW_SCOPES
        and action.target_card_id
    }
    rows: list[dict[str, Any]] = []
    for proposal in profile.private_source_proposals:
        review_action = review_actions_by_target.get(proposal.target_card_id)
        if review_action is None:
            continue
        if proposal.review_status != "review_required":
            continue
        rows.append(
            {
                "id": f"private_proposal_promotion_{proposal.proposal_id}",
                "preview_contract": "private_source_proposal_promotion_preview_v1",
                "operation_type": "private_source_proposal_promotion_review",
                "proposal_id": proposal.proposal_id,
                "source_id": proposal.source_id,
                "source_type": proposal.source_type,
                "privacy_class": proposal.privacy_class,
                "scope": proposal.scope,
                "target_card_id": proposal.target_card_id,
                "target_card_title": proposal.target_card_title,
                "review_action_id": review_action.action_id,
                "required_human_role": review_action.required_human_role,
                "support_level": proposal.support_level,
                "risk_tier": proposal.risk_tier,
                "freshness_status": proposal.freshness_status,
                "audience": proposal.audience,
                "data_classes": proposal.data_classes,
                "source_block_refs": proposal.source_block_refs,
                "retention_decision": proposal.retention_decision,
                "deletion_path": proposal.deletion_path,
                "eval_case_ids": proposal.eval_case_ids,
                "confidence_label": proposal.confidence_label,
                "blocked_claims": proposal.blocked_claims,
                "required_validation": [
                    "redacted_source_trace_review",
                    "private_owner_human_review_record",
                    "blocked_claims_review",
                    "separate_source_fact_promotion_request",
                    "focused_eval_before_policy_or_service_use",
                ],
                "required_validation_labels": [
                    "sprawdź redacted źródło",
                    "zapisz decyzję Wilka/ownera",
                    "sprawdź zakazane twierdzenia",
                    "przygotuj osobny request awansu source fact",
                    "uruchom focused eval przed użyciem",
                ],
                "promotion_blocked_reason": (
                    "Ta akcja tylko przygotowuje review prywatnej propozycji. Nie "
                    "edytuje source_facts.json, nie promuje private proposal, nie "
                    "zmienia lifecycle i nie odblokowuje production-depth."
                ),
                "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
                "redacted": True,
                "apply_allowed": False,
                "api_mutation_ready": False,
                "destructive": False,
            }
        )
    if not rows:
        return None
    return private_proposal_promotion_action(
        proposal_count=len(profile.private_source_proposals),
        rows=rows,
    )


_STATIC_ACTIONS = seed_static_actions()
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
    actions = {**_STATIC_ACTIONS, **seed_metric_action_candidates()}
    if _google_ads_live_data_available():
        actions.pop("act_configure_google_ads_env", None)
        business_context_action = _google_ads_business_context_action()
        if business_context_action is not None:
            actions[business_context_action.id] = business_context_action
        target_confirmation_action = _google_ads_target_confirmation_action()
        if target_confirmation_action is not None:
            actions[target_confirmation_action.id] = target_confirmation_action
        strategy_review_action = _google_ads_strategy_review_action()
        if strategy_review_action is not None:
            actions[strategy_review_action.id] = strategy_review_action
        keyword_planner_action = _google_ads_keyword_planner_access_action()
        if keyword_planner_action is not None:
            actions[keyword_planner_action.id] = keyword_planner_action
    return _with_persisted_review_gates(actions.values())


def list_actions_cached() -> list[ActionObject]:
    """Reuse one action registry build across the dashboard list reads."""
    cached = _read_action_list_cache()
    if cached is not None:
        return cached
    actions = list_actions()
    _write_action_list_cache(actions)
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
    return _cached_action_list.actions


def _write_action_list_cache(actions: list[ActionObject]) -> None:
    global _cached_action_list
    if _action_list_cache_seconds() <= 0:
        return
    _cached_action_list = ActionListCacheEntry(created_at=monotonic(), actions=actions)


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


def get_action(action_id: str) -> ActionObject | None:
    actions = {**_STATIC_ACTIONS, **seed_metric_action_candidates()}
    business_context_action = _google_ads_business_context_action()
    if business_context_action is not None:
        actions[business_context_action.id] = business_context_action
    target_confirmation_action = _google_ads_target_confirmation_action()
    if target_confirmation_action is not None:
        actions[target_confirmation_action.id] = target_confirmation_action
    strategy_review_action = _google_ads_strategy_review_action()
    if strategy_review_action is not None:
        actions[strategy_review_action.id] = strategy_review_action
    keyword_planner_action = _google_ads_keyword_planner_access_action()
    if keyword_planner_action is not None:
        actions[keyword_planner_action.id] = keyword_planner_action
    action = actions.get(action_id)
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


def _latest_google_ads_vendor_read() -> ConnectorRefreshRun | None:
    runs = [
        run
        for run in list_connector_refresh_runs(connector_id="google_ads")
        if run.mode == ConnectorRefreshMode.vendor_read
    ]
    if not runs:
        return None
    return max(runs, key=_connector_refresh_recency_key)


def _connector_refresh_recency_key(run: ConnectorRefreshRun) -> tuple[str, str]:
    timestamp = run.completed_at or run.started_at
    return (timestamp.isoformat(), run.id)


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


def _google_ads_keyword_planner_access_action() -> ActionObject | None:
    latest_run = _latest_google_ads_vendor_read()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
    ):
        return None
    blocker = _keyword_planner_access_blocker(latest_run)
    if blocker is None:
        return None
    return keyword_planner_access_action(
        blocker=blocker,
        evidence_ids=unique_values(
            [connector_evidence_id("google_ads"), *latest_run.evidence_ids]
        ),
    )


def _keyword_planner_access_blocker(run: ConnectorRefreshRun) -> str | None:
    status = str(run.metric_summary.get("keyword_planner_status") or "").lower()
    blocker = str(run.metric_summary.get("keyword_planner_blocker") or "").strip()
    http_status = str(run.metric_summary.get("keyword_planner_http_status") or "").strip()
    if status != "blocked":
        return None
    blocker_text = " ".join(part for part in (blocker, http_status) if part)
    if not blocker_text:
        return None
    normalized = blocker_text.lower()
    if (
        "developer_token_not_approved" not in normalized
        and "permission_denied" not in normalized
        and http_status != "403"
    ):
        return None
    return "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera"


def seed_metric_action_candidates() -> dict[str, ActionObject]:
    facts = _action_metric_facts()
    by_connector = _facts_by_connector(facts)
    actions: dict[str, ActionObject] = {}

    _seed_merchant_metric_actions(by_connector, actions)
    _seed_ga4_metric_actions(by_connector, actions)
    _seed_content_metric_actions(by_connector, actions)
    _seed_google_ads_metric_actions(by_connector, actions)
    _seed_localo_metric_actions(by_connector, actions)
    _seed_social_metric_actions(by_connector, actions)
    return actions


def _seed_merchant_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    merchant_facts = by_connector.get("google_merchant_center", [])
    action = merchant_feed_issue_action_from_metric_facts(
        merchant_facts,
        preview_contract=MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
    )
    if action is not None:
        actions[action.id] = action


def _seed_ga4_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    ga4_facts = by_connector.get("google_analytics_4", [])
    action = ga4_tracking_quality_action_from_metric_facts(ga4_facts)
    if action is not None:
        actions[action.id] = action


def _seed_content_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    content_facts = [
        *by_connector.get("wordpress_ekologus", []),
        *by_connector.get("google_search_console", []),
        *by_connector.get("ahrefs", []),
    ]
    candidate = content_refresh_metric_candidate(content_facts)
    if candidate is None:
        return
    actions[candidate.action.id] = candidate.action
    wordpress_draft_action = _wordpress_draft_handoff_action(
        content_payload=candidate.payload,
        content_action_metrics=candidate.action_metrics,
    )
    if wordpress_draft_action is None:
        return
    actions[wordpress_draft_action.id] = wordpress_draft_action
    wordpress_draft_apply_action = _wordpress_draft_apply_action(
        handoff_action=wordpress_draft_action,
    )
    actions[wordpress_draft_apply_action.id] = wordpress_draft_apply_action


def _seed_google_ads_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    google_ads_facts = by_connector.get("google_ads", [])
    demand_gen_action = demand_gen_readiness_action_from_metric_facts(
        google_ads_facts,
        by_connector.get("google_analytics_4", []),
        latest_google_ads_evidence_ids=latest_vendor_read_evidence_ids("google_ads"),
        latest_ga4_evidence_ids=latest_vendor_read_evidence_ids("google_analytics_4"),
    )
    if demand_gen_action is not None:
        actions[demand_gen_action.id] = demand_gen_action

    campaign_review_action_result = campaign_review_action_from_metric_facts(
        google_ads_facts
    )
    if campaign_review_action_result is not None:
        action = campaign_review_action_result
        actions[action.id] = action

    recommendation_action = recommendation_review_action_from_metric_facts(google_ads_facts)
    if recommendation_action is not None:
        action = recommendation_action
        actions[action.id] = action

    change_history_action = change_history_impact_action_from_metric_facts(google_ads_facts)
    if change_history_action is not None:
        action = change_history_action
        actions[action.id] = action

    search_term_ngram_action_result = search_term_ngram_action_from_metric_facts(
        google_ads_facts
    )
    if search_term_ngram_action_result is not None:
        action = search_term_ngram_action_result
        actions[action.id] = action

    custom_segment_action_result = custom_segment_action_from_metric_facts(google_ads_facts)
    if custom_segment_action_result is not None:
        action = custom_segment_action_result
        actions[action.id] = action

    negative_keyword_action_result = negative_keyword_action_from_metric_facts(google_ads_facts)
    if negative_keyword_action_result is not None:
        action = negative_keyword_action_result
        actions[action.id] = action


def _seed_localo_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    localo_facts = _localo_action_metric_facts(by_connector.get("localo", []))
    localo_visibility_payload = localo_visibility_review_payload_from_metric_facts(localo_facts)
    if localo_visibility_payload is None:
        return
    action = localo_visibility_review_action_from_metric_facts(
        localo_facts=localo_facts,
        localo_visibility_payload=localo_visibility_payload,
    )
    actions[action.id] = action


def _seed_social_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    social_facts = [
        *by_connector.get("google_search_console", []),
        *by_connector.get("google_merchant_center", []),
        *by_connector.get("wordpress_ekologus", []),
        *by_connector.get("google_analytics_4", []),
    ]
    if social_facts:
        actions.update(social_draft_actions(social_facts))


def _localo_action_metric_facts(facts: list[MetricFact]) -> list[MetricFact]:
    value_facts = [fact for fact in facts if not _is_probe_only_fact(fact)]
    if value_facts:
        return value_facts
    for run in list_connector_refresh_runs(connector_id="localo"):
        if run.status != ConnectorRefreshStatus.completed or not run.vendor_data_collected:
            continue
        facts_by_evidence = metric_store().list_metric_facts_by_evidence_ids(run.evidence_ids)
        value_facts = [
            fact
            for fact in facts_by_evidence
            if fact.source_connector == "localo" and not _is_probe_only_fact(fact)
        ]
        if value_facts:
            return value_facts
    return []


def _action_metric_facts() -> list[MetricFact]:
    facts: list[MetricFact] = []
    facts_by_connector = metric_store().list_latest_metric_facts_by_connector_limits(
        {
            connector_id: ACTION_METRIC_FACT_LIMITS.get(
                connector_id,
                ACTION_METRIC_FACT_LIMIT,
            )
            for connector_id in ACTION_METRIC_CONNECTORS
        },
    )
    google_ads_latest_facts = _latest_google_ads_metric_facts()
    if google_ads_latest_facts:
        facts_by_connector["google_ads"] = google_ads_latest_facts
    for connector_id in ACTION_METRIC_CONNECTORS:
        facts.extend(
            fact
            for fact in facts_by_connector.get(connector_id, [])
            if not _is_probe_only_fact(fact)
        )
    return _latest_metric_facts_by_identity(facts)


def _latest_google_ads_metric_facts() -> list[MetricFact]:
    latest_run = _latest_google_ads_vendor_read()
    if (
        latest_run is None
        or latest_run.status != ConnectorRefreshStatus.completed
        or not latest_run.vendor_data_collected
        or not latest_run.evidence_ids
    ):
        return []
    return [
        fact
        for fact in metric_store().list_metric_facts_by_evidence_ids(latest_run.evidence_ids)
        if fact.source_connector == "google_ads"
    ]


def _latest_metric_facts_by_identity(metric_facts: list[MetricFact]) -> list[MetricFact]:
    latest_by_key: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in metric_facts:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted(fact.dimensions.items())),
        )
        current = latest_by_key.get(key)
        if current is None or _metric_fact_sort_time(fact) > _metric_fact_sort_time(current):
            latest_by_key[key] = fact
    return sorted(
        latest_by_key.values(),
        key=lambda fact: _metric_fact_sort_time(fact),
        reverse=True,
    )


def _metric_fact_sort_time(fact: MetricFact) -> str:
    if fact.collected_at is None:
        return ""
    return fact.collected_at.isoformat()


def _wordpress_draft_handoff_action(
    *,
    content_payload: dict[str, Any] | None,
    content_action_metrics: list[MetricFact],
) -> ActionObject | None:
    if content_payload is None:
        return None
    brief_previews = [
        item
        for item in content_payload.get("content_brief_preview", [])
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
    ]
    if not brief_previews:
        return None
    preview_items = [_wordpress_draft_handoff_preview_item(item) for item in brief_previews[:4]]
    return draft_handoff_action(
        source_connectors=content_payload.get("source_connectors", []),
        source_metric_names=content_payload.get("source_metric_names", []),
        preview_items=preview_items,
        content_action_metrics=content_action_metrics,
        evidence_ids=unique_values(fact.evidence_id for fact in content_action_metrics),
    )


def _wordpress_draft_apply_action(*, handoff_action: ActionObject) -> ActionObject:
    return draft_apply_action(
        handoff_action=handoff_action,
        apply_contract_payload=_wordpress_draft_apply_contract_payload(handoff_action),
    )


def _wordpress_draft_apply_contract_payload(
    handoff_action: ActionObject,
) -> dict[str, Any]:
    return {
        "contract": "action_apply_contract_v1",
        "action_id": "act_apply_wordpress_draft_handoff",
        "action_type": "wordpress_draft_handoff",
        "connector": "wordpress_ekologus",
        "allowed_operation": "create_wordpress_draft",
        "required_mode": "apply",
        "draft_only": True,
        "publication_allowed": False,
        "destructive_allowed": False,
        "adapter_status": "not_implemented",
        "required_env_flags": ["WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES"],
        "required_input_contracts": handoff_action.payload.get("required_input_contracts", []),
        "required_audit_events": [
            "action_preview_generated",
            "human_review_*",
            "action_apply_confirmed",
        ],
        "blocked_outputs": [
            "wordpress_publish",
            "wordpress_update_existing_post",
            "wordpress_delete_post",
            "production_publish_ready_claim",
        ],
        "operator_summary": (
            "Ten apply-mode obiekt nadal jest zablokowany. Może w przyszłości "
            "utworzyć tylko szkic WordPress po pełnym preview, review, confirm, "
            "impact check, env readiness i adapterze z audytem."
        ),
    }


def _wordpress_draft_handoff_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    source_public_url = (
        item.get("source_public_url") if isinstance(item.get("source_public_url"), str) else None
    )
    intended_final_url = (
        item.get("intended_final_url")
        if isinstance(item.get("intended_final_url"), str)
        else source_public_url
    )
    final_canonical_url = (
        item.get("final_canonical_url")
        if isinstance(item.get("final_canonical_url"), str)
        else intended_final_url
    )
    required_validation = [
        "content_url_preflight_review",
        "final_canonical_review",
        "duplicate_or_cannibalization_check",
        "legal_factual_review",
        "content_draft_readiness_review",
        "human_confirm_before_wordpress_write",
    ]
    blocked_claims = [
        "wordpress_draft_write",
        "wordpress_publish",
        "publish_ready_claim",
        "obietnica wzrostu pozycji albo leadów",
    ]
    measurement_plan = post_publication_measurement_plan(
        final_canonical_url=str(final_canonical_url) if final_canonical_url else None,
    )
    return {
        "preview_contract": "wordpress_draft_handoff_preview_v1",
        "operation_type": "wordpress_draft_handoff_review",
        "candidate_id": item.get("candidate_id"),
        "topic": item.get("topic"),
        "source_public_url": source_public_url,
        "intended_final_url": intended_final_url,
        "final_canonical_url": final_canonical_url,
        "preview_url": item.get("preview_url")
        if isinstance(item.get("preview_url"), str)
        else None,
        "canonical_gate_status": item.get("canonical_gate_status"),
        "canonical_gate_status_label": content_contract_label(
            str(item.get("canonical_gate_status") or "")
        ),
        "duplicate_gate_status": item.get("duplicate_gate_status"),
        "duplicate_gate_status_label": content_contract_label(
            str(item.get("duplicate_gate_status") or "")
        ),
        "wordpress_draft_handoff_status": "blocked_until_draft_checks_complete",
        "wordpress_draft_handoff_summary": [
            "stan przekazania do WordPress: zablokowany do przejścia kontroli szkicu"
        ],
        "required_next_action_contract": "wordpress_draft_handoff_v1",
        "required_next_action_label": content_contract_label("wordpress_draft_handoff_v1"),
        "post_publication_measurement_plan": measurement_plan,
        "post_publication_measurement_summary": post_publication_measurement_summary(
            measurement_plan
        ),
        "required_validation": required_validation,
        "required_validation_labels": content_contract_labels(required_validation),
        "blocked_claims": blocked_claims,
        "blocked_claim_labels": content_contract_labels(blocked_claims),
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
    }


def _facts_by_connector(facts: list[MetricFact]) -> dict[str, list[MetricFact]]:
    grouped: dict[str, list[MetricFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.source_connector, []).append(fact)
    return grouped


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
    errors: list[str] = []
    warnings: list[str] = []
    connector = get_connector_status(action.connector)
    if not action.evidence_ids:
        errors.append("Akcja wymaga co najmniej jednego dowodu źródłowego.")
    if connector is None:
        errors.append(f"Nieznany łącznik danych: {action.connector}")
    elif action.mode == ActionMode.apply and not connector.configured:
        errors.append(f"Łącznik danych {action.connector} nie jest skonfigurowany.")
    errors.extend(validate_action_payload(action.connector, action.payload))
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        warnings.append("Akcje o wysokim i krytycznym ryzyku wymagają osobnego wsparcia produktu.")
    valid = not errors
    action.validation_status = "valid" if valid else "invalid"
    if not valid:
        action.status = ActionStatus.validation_failed
    elif action.mode == ActionMode.apply:
        action.status = ActionStatus.ready_to_apply
    else:
        action.status = ActionStatus.ready
    action.review_gate = _action_review_gate(action)
    local_state_store().save_action_validation_state(
        action_id=action.id,
        status=action.status.value,
        validation_status=action.validation_status,
    )
    return ActionValidationResult(
        action_id=action.id,
        valid=valid,
        status="valid" if valid else "invalid",
        status_label=_action_result_status_label("valid" if valid else "invalid"),
        errors=errors,
        warnings=warnings,
    )


def record_action_review(
    action: ActionObject,
    request: ActionReviewRequest,
) -> ActionReviewResult:
    audit = AuditEvent(
        id=f"audit_{action.id}_human_review_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type=f"human_review_{request.outcome}",
        event_type_label=_action_audit_event_label(f"human_review_{request.outcome}"),
        actor=request.reviewed_by,
        summary=_action_review_summary(request),
        evidence_ids=action.evidence_ids,
        details=_action_review_details(request),
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = _action_review_gate(action)
    return ActionReviewResult(
        action_id=action.id,
        status="recorded",
        status_label=_action_result_status_label("recorded"),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def preview_action(
    action: ActionObject,
    request: ActionPreviewRequest | None = None,
) -> ActionPreviewResult:
    preview_request = request or ActionPreviewRequest()
    action.review_gate = _action_review_gate(action)
    raw_preview_items = _payload_preview_items(action.payload)
    included_items = raw_preview_items[: preview_request.max_items]
    preview_cards = _action_preview_cards(action)
    preview_items = _action_preview_item_view_models(
        action=action,
        raw_items=raw_preview_items,
        preview_cards=preview_cards,
        max_items=preview_request.max_items,
    )
    blockers = _action_preview_blockers(action, raw_preview_items)
    status: Literal["preview_ready", "blocked"] = "blocked" if blockers else "preview_ready"
    audit = AuditEvent(
        id=f"audit_{action.id}_preview_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type="action_preview_generated",
        event_type_label=_action_audit_event_label("action_preview_generated"),
        actor=preview_request.requested_by or "wilq_api",
        summary=_action_preview_summary(
            status=status,
            included_items=len(included_items),
            preview_items=len(raw_preview_items),
        ),
        evidence_ids=action.evidence_ids,
    )
    action.audit_events = [audit, *action.audit_events]
    return ActionPreviewResult(
        action_id=action.id,
        status=status,
        status_label=_action_result_status_label(status),
        dry_run=True,
        mutation_allowed=False,
        preview_contract=_preview_contract(action.payload, raw_preview_items),
        preview_items=preview_items,
        preview_cards=preview_cards,
        preview_items_total=len(raw_preview_items),
        omitted_items=max(len(raw_preview_items) - len(included_items), 0),
        blockers=blockers,
        blocker_labels=_action_gate_labels(blockers),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def confirm_action(
    action: ActionObject,
    request: ActionConfirmRequest,
) -> ActionConfirmResult:
    action.review_gate = _action_review_gate(action)
    latest_preview = _latest_preview_event(action.audit_events)
    blockers = _action_confirmation_blockers(action, request, latest_preview)
    confirmed = not blockers
    audit = AuditEvent(
        id=f"audit_{action.id}_confirm_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type=_action_confirmation_event_type(action, confirmed),
        event_type_label=_action_audit_event_label(
            _action_confirmation_event_type(action, confirmed)
        ),
        actor=request.confirmed_by,
        summary=_action_confirmation_summary(action, request, blockers, latest_preview),
        evidence_ids=action.evidence_ids,
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = _action_review_gate(action)
    return ActionConfirmResult(
        action_id=action.id,
        confirmed=confirmed,
        status="confirmed" if confirmed else "blocked",
        status_label=_action_result_status_label("confirmed" if confirmed else "blocked"),
        blockers=blockers,
        blocker_labels=_action_gate_labels(blockers),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def impact_check_action(
    action: ActionObject,
    request: ActionImpactCheckRequest,
) -> ActionImpactCheckResult:
    action.review_gate = _action_review_gate(action)
    latest_confirmation = _latest_action_confirmation_event(action.audit_events)
    blockers = _action_impact_check_blockers(action, latest_confirmation)
    status: Literal["checked", "blocked"] = "blocked" if blockers else "checked"
    evidence_ids = unique_values(
        [*action.evidence_ids, *(fact.evidence_id for fact in action.metrics)]
    )
    source_connectors = unique_values(
        [fact.source_connector for fact in action.metrics if fact.source_connector]
    )
    if not source_connectors:
        source_connectors = [action.connector]
    audit = AuditEvent(
        id=f"audit_{action.id}_impact_{uuid4().hex[:12]}",
        action_id=action.id,
        event_type="action_impact_check_completed"
        if status == "checked"
        else "action_impact_check_blocked",
        event_type_label=_action_audit_event_label(
            "action_impact_check_completed"
            if status == "checked"
            else "action_impact_check_blocked"
        ),
        actor=request.checked_by,
        summary=_action_impact_check_summary(
            request=request,
            status=status,
            metric_fact_count=len(action.metrics),
            source_connectors=source_connectors,
            blockers=blockers,
        ),
        evidence_ids=evidence_ids,
    )
    action.audit_events = [audit, *action.audit_events]
    action.review_gate = _action_review_gate(action)
    return ActionImpactCheckResult(
        action_id=action.id,
        status=status,
        status_label=_action_result_status_label(status),
        pre_window_days=request.pre_window_days,
        post_window_days=request.post_window_days,
        metric_fact_count=len(action.metrics),
        source_connectors=source_connectors,
        source_connector_labels=source_connector_labels(source_connectors),
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_count_label(evidence_ids),
        blockers=blockers,
        blocker_labels=_action_gate_labels(blockers),
        audit_event=_audit_event_with_operator_label(audit),
        review_gate=_review_gate_with_operator_labels(action.review_gate),
    )


def apply_action(
    action: ActionObject,
    request: ActionApplyRequest | None = None,
) -> ActionApplyResult:
    errors: list[str] = []
    wordpress_capability, capability_errors = _wordpress_draft_apply_capability(action, request)
    errors.extend(capability_errors)
    connector = get_connector_status(action.connector)
    latest_preview = _latest_preview_event(action.audit_events)
    latest_confirmation = _latest_action_confirmation_event(action.audit_events)
    latest_impact_check = _latest_action_impact_check_event(action.audit_events)
    mutation_adapter = _supported_mutation_adapter(action)
    if request is None or request.confirm is not True:
        errors.append("Wymagane jest jawne potwierdzenie zapisu zmian.")
    if request is not None and request.confirm is True and not request.confirmed_by:
        errors.append("Brakuje osoby potwierdzającej zapis zmian.")
    if latest_preview is None:
        errors.append("Przed zapisem zmian wymagany jest podgląd zmian.")
    if latest_confirmation is None:
        errors.append("Przed zapisem zmian wymagany jest zapis audytu potwierdzenia.")
    if _impact_status_from_event(latest_impact_check) != "checked":
        errors.append("Przed zapisem zmian wymagane jest sprawdzenie efektu.")
    if action.validation_status != "valid":
        errors.append("Akcja musi być sprawdzona w WILQ przed zapisem zmian.")
    if action.mode != ActionMode.apply:
        errors.append("Akcja nie ma trybu zapisu zmian w zewnętrznym systemie.")
    if not action.evidence_ids:
        errors.append("Akcja nie może zapisać zmian bez dowodów źródłowych.")
    if connector is None or not connector.configured:
        errors.append("Brakuje skonfigurowanego źródła danych do zapisu zmian.")
    if action.risk in {ActionRisk.high, ActionRisk.critical}:
        errors.append("Zapisy zmian o wysokim i krytycznym ryzyku są zablokowane w Goal 001.")
    if action.payload.get("destructive") is True:
        errors.append("Destrukcyjne zmiany nie są zaimplementowane w Goal 001.")
    if wordpress_capability is None and not _action_payload_apply_allowed(action.payload):
        errors.append("Payload akcji nie pozwala jeszcze na zapis zmian.")
    if wordpress_capability is None and not _action_payload_api_mutation_ready(action.payload):
        errors.append("Payload akcji nie jest gotowy do mutacji API.")
    if mutation_adapter is None:
        errors.append("Brakuje bezpiecznej ścieżki zapisu zmian dla tej akcji.")
    adapter_result: dict[str, Any] | None = None
    if not errors and mutation_adapter is not None:
        adapter_result, adapter_errors = _execute_supported_mutation_adapter(
            action,
            mutation_adapter,
            request,
            wordpress_capability,
        )
        errors.extend(adapter_errors)

    actor = request.confirmed_by if request and request.confirmed_by else "wilq_api"
    audit = AuditEvent(
        id=f"audit_{action.id}_{len(action.audit_events) + 1}",
        action_id=action.id,
        event_type=_apply_audit_event_type(errors),
        event_type_label=_action_audit_event_label(_apply_audit_event_type(errors)),
        actor=actor,
        summary="; ".join(errors) if errors else "Zmiany zapisane przez sprawdzoną ścieżkę API.",
        evidence_ids=action.evidence_ids,
    )
    mutation_audit = _action_mutation_audit_record(
        action=action,
        audit_event=audit,
        actor=actor,
        errors=errors,
        mutation_adapter=mutation_adapter,
        adapter_result=adapter_result,
    )
    action.audit_events.append(audit)
    if errors:
        action.status = ActionStatus.blocked
        action.review_gate = _action_review_gate(action)
        return ActionApplyResult(
            action_id=action.id,
            applied=False,
            status="blocked",
            status_label=_action_result_status_label("blocked"),
            audit_event=_audit_event_with_operator_label(audit),
            mutation_audit=mutation_audit,
            errors=errors,
            adapter_result=adapter_result,
        )
    action.status = ActionStatus.applied
    action.review_gate = _action_review_gate(action)
    return ActionApplyResult(
        action_id=action.id,
        applied=True,
        status="applied",
        status_label=_action_result_status_label("applied"),
        audit_event=_audit_event_with_operator_label(audit),
        mutation_audit=mutation_audit,
        adapter_result=adapter_result,
    )


def _wordpress_draft_apply_capability(
    action: ActionObject,
    request: ActionApplyRequest | None,
) -> tuple[WordPressDraftApplyCapability | None, list[str]]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None, []
    input_contract = request.wordpress_draft if request is not None else None
    if input_contract is None:
        return None, [
            "Apply szkicu WordPress wymaga typed work item, handoff, draft package i target URL."
        ]
    if request is None or not request.confirmed_by:
        return None, ["Apply szkicu WordPress wymaga potwierdzonego aktora operatora."]

    from wilq.briefing.content_diagnostics import build_content_diagnostics_cached

    diagnostics = build_content_diagnostics_cached()
    review = content_workflow_store().latest_human_review(input_contract.work_item_id)
    if review is None:
        return None, ["Brakuje zapisanego review człowieka dla wskazanego work itemu."]
    audit = content_workflow_store().latest_audit_for_review(review.id)
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        input_contract.work_item_id,
        human_review=review,
        audit=audit,
    )
    if snapshot is None:
        return None, ["Wskazany work item nie istnieje w aktualnej kolejce WILQ."]
    draft_package = snapshot.draft_package.draft_package_result.draft_package
    handoff = snapshot.wordpress_handoff.handoff_result.handoff
    if draft_package is None or handoff is None:
        return None, ["Brakuje kompletnej paczki szkicu albo handoffu WordPress."]
    if handoff.id != input_contract.handoff_id:
        return None, ["Handoff WordPress nie pasuje do wskazanego ActionObject apply."]
    if draft_package.id != input_contract.draft_package_id:
        return None, ["Paczka szkicu nie pasuje do wskazanego ActionObject apply."]
    if handoff.work_item_id != input_contract.work_item_id:
        return None, ["Handoff nie pasuje do wskazanego work itemu."]
    if handoff.final_canonical_url != input_contract.target_url:
        return None, ["Canonical URL nie pasuje do zatwierdzonego handoffu."]
    target_host = (urlparse(input_contract.target_url).hostname or "").lower()
    if target_host not in {"ekologus.pl", "www.ekologus.pl"}:
        return None, ["Apply szkicu wymaga publicznego canonical URL Ekologus."]
    if handoff.publish_allowed or handoff.destructive_update_allowed:
        return None, ["Handoff WordPress nie jest draft-only."]

    confirmation = _latest_action_confirmation_event(action.audit_events)
    if confirmation is None or confirmation.actor != request.confirmed_by:
        return None, ["Aktor confirm nie pasuje do zapisanego audytu ActionObject."]
    preview = _latest_preview_event(action.audit_events)
    if preview is None:
        return None, ["Brakuje audytu preview ActionObject."]
    return (
        WordPressDraftApplyCapability(
            handoff=handoff,
            draft_package=draft_package,
            write_authorization=ContentWordPressDraftWriteAuthorization(
                action_id=action.id,
                preview_audit_id=preview.id,
                review_audit_id=review.id,
                confirmation_audit_id=confirmation.id,
                confirmed_by=request.confirmed_by,
            ),
        ),
        [],
    )


def mutation_readiness_action(action: ActionObject) -> ActionMutationReadinessResponse:
    action = _with_review_gate(
        _with_persisted_validation_state(action),
        _persisted_audit_events_for_action(action.id),
        _persisted_mutation_audits_for_action(action.id),
    )
    connector = get_connector_status(action.connector)
    mutation_adapter = _supported_mutation_adapter(action)
    latest_preview = _latest_preview_event(action.audit_events)
    latest_confirmation = _latest_action_confirmation_event(action.audit_events)
    latest_impact_check = _latest_action_impact_check_event(action.audit_events)
    latest_mutation_audit = _latest_mutation_audit(
        _persisted_mutation_audits_for_action(action.id)
    )
    wordpress_draft_readiness = _wordpress_draft_write_readiness(action)
    wordpress_activation_packet = _wordpress_draft_activation_packet(action)
    requirements = base_mutation_readiness_requirements(
        action=action,
        connector_configured=connector is not None and connector.configured,
        connector_evidence=connector.status.value if connector is not None else "missing",
        mutation_adapter=mutation_adapter,
        latest_preview=latest_preview,
        latest_confirmation=latest_confirmation,
        latest_impact_check=latest_impact_check,
        payload_apply_allowed=_action_payload_apply_allowed,
        impact_status=_impact_status_from_event,
        evidence_label=evidence_count_label,
    )
    requirements.extend(
        wordpress_draft_execution_readiness_requirements(
            action,
            activation_packet=wordpress_activation_packet,
        )
    )
    requirements.extend(
        wordpress_draft_target_content_readiness_requirements(
            action,
            activation_packet=wordpress_activation_packet,
            preview_items=_payload_preview_items,
        )
    )
    requirements.extend(
        _wordpress_draft_write_readiness_requirements(
            action,
            wordpress_draft_readiness=wordpress_draft_readiness,
        )
    )
    blockers = _mutation_readiness_blockers(requirements)
    vendor_write_possible = _vendor_write_possible(action, mutation_adapter)
    apply_contract = _mutation_apply_contract(action, mutation_adapter)
    target = mutation_readiness_target(
        action,
        activation_packet=wordpress_activation_packet,
        preview_items=_payload_preview_items,
    )
    return build_mutation_readiness_response(
        action=action,
        mutation_adapter=mutation_adapter,
        wordpress_draft_readiness=wordpress_draft_readiness,
        requirements=requirements,
        blockers=blockers,
        vendor_write_possible=vendor_write_possible,
        apply_contract=apply_contract,
        target=target,
        operator_next_step=_mutation_readiness_next_step(action, blockers),
        latest_mutation_audit=latest_mutation_audit,
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


def _vendor_write_possible(action: ActionObject, mutation_adapter: str | None) -> bool:
    return (
        mutation_adapter is not None
        and action.mode == ActionMode.apply
        and _action_payload_apply_allowed(action.payload)
        and _action_payload_api_mutation_ready(action.payload)
    )


def _wordpress_draft_write_readiness_requirements(
    action: ActionObject,
    *,
    wordpress_draft_readiness: ContentWordPressDraftWriteReadinessResponse | None = None,
) -> list[ActionMutationReadinessRequirement]:
    if action.id != "act_apply_wordpress_draft_handoff":
        return []
    readiness = wordpress_draft_readiness or build_content_wordpress_draft_write_readiness_response(
        action_id=action.id
    )
    authorization_ready = readiness.suggested_write_authorization is not None
    blocker_codes = ", ".join(blocker.code for blocker in readiness.blockers[:4]) or None
    return [
        _mutation_requirement(
            code="wordpress_draft_write_readiness",
            label="WordPress draft write readiness przechodzi",
            satisfied=readiness.ready,
            evidence=blocker_codes or "ready",
        ),
        _mutation_requirement(
            code="wordpress_draft_live_write_env",
            label="Env pozwala na zapis szkicu WordPress",
            satisfied=readiness.live_write_enabled_by_env,
            evidence=str(readiness.live_write_enabled_by_env).lower(),
        ),
        _mutation_requirement(
            code="wordpress_rest_adapter_configured",
            label="REST adapter WordPress jest skonfigurowany",
            satisfied=readiness.rest_adapter_configured,
            evidence=str(readiness.rest_adapter_configured).lower(),
        ),
        _mutation_requirement(
            code="wordpress_write_authorization",
            label="Autoryzacja write z audytu jest gotowa",
            satisfied=authorization_ready,
            evidence="ready" if authorization_ready else "missing",
        ),
    ]


def _wordpress_draft_write_readiness(
    action: ActionObject,
) -> ContentWordPressDraftWriteReadinessResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    return build_content_wordpress_draft_write_readiness_response(action_id=action.id)


def _wordpress_draft_activation_packet(
    action: ActionObject,
) -> ContentWordPressDraftActivationPacketResponse | None:
    if action.id != "act_apply_wordpress_draft_handoff":
        return None
    from wilq.briefing.content_diagnostics import build_content_diagnostics

    diagnostics = build_content_diagnostics(actions=[])
    snapshot = build_content_work_item_diagnostics_snapshot_response(diagnostics)
    return build_content_wordpress_draft_activation_packet_response(
        snapshot,
        action_id=action.id,
    )


def _apply_audit_event_type(errors: list[str]) -> str:
    if not errors:
        return "apply_succeeded"
    confirmation_errors = {
        "Wymagane jest jawne potwierdzenie zapisu zmian.",
        "Brakuje osoby potwierdzającej zapis zmian.",
    }
    if any(error in confirmation_errors for error in errors):
        return "apply_confirmation_missing"
    return "apply_blocked"


def _action_mutation_audit_record(
    *,
    action: ActionObject,
    audit_event: AuditEvent,
    actor: str,
    errors: list[str],
    mutation_adapter: str | None,
    adapter_result: dict[str, Any] | None,
) -> ActionMutationAuditRecord:
    status: Literal["blocked", "applied"] = "blocked" if errors else "applied"
    action_type = action.payload.get("action_type")
    adapter_reached = adapter_result is not None
    external_write_attempted = (
        adapter_result.get("external_write_attempted") is True
        if adapter_result is not None
        else False
    )
    return ActionMutationAuditRecord(
        id=f"mutation_{action.id}_{uuid4().hex[:12]}",
        action_id=action.id,
        connector=action.connector,
        action_type=action_type if isinstance(action_type, str) else None,
        status=status,
        status_label=_action_mutation_audit_status_label(status),
        adapter_reached=adapter_reached,
        external_write_attempted=external_write_attempted,
        mutation_attempted=external_write_attempted,
        mutation_adapter=mutation_adapter,
        actor=actor,
        audit_event_id=audit_event.id,
        evidence_ids=action.evidence_ids,
        blockers=errors,
        summary=_mutation_audit_summary(
            errors,
            mutation_adapter,
            adapter_reached=adapter_reached,
            external_write_attempted=external_write_attempted,
        ),
    )


def _mutation_audit_summary(
    errors: list[str],
    mutation_adapter: str | None,
    *,
    adapter_reached: bool,
    external_write_attempted: bool,
) -> str:
    if errors:
        if adapter_reached:
            attempted = (
                "External vendor write was attempted."
                if external_write_attempted
                else "No external vendor write was attempted."
            )
            return (
                "Mutation adapter reached but did not complete successfully. "
                f"{attempted} Blockers: {', '.join(errors)}"
            )
        return f"Mutation blocked before any vendor API call. Blockers: {', '.join(errors)}"
    adapter = mutation_adapter or "unknown"
    if not external_write_attempted:
        return (
            f"Mutation completed through adapter {adapter}, but no external vendor "
            "write was attempted; vendor payload remains redacted."
        )
    return f"Mutation executed through adapter {adapter}; vendor payload remains redacted."


def _supported_mutation_adapter(action: ActionObject) -> str | None:
    if (
        action.id == "act_apply_wordpress_draft_handoff"
        and action.connector == "wordpress_ekologus"
        and action.payload.get("allowed_operation") == "create_wordpress_draft"
    ):
        return "wordpress_draft_execution_boundary"
    return None


def _execute_supported_mutation_adapter(
    action: ActionObject,
    mutation_adapter: str,
    request: ActionApplyRequest | None,
    wordpress_capability: WordPressDraftApplyCapability | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    _ = request
    if mutation_adapter == "wordpress_draft_execution_boundary":
        if wordpress_capability is not None:
            execution = execute_content_wordpress_draft_handoff(
                handoff=wordpress_capability.handoff,
                draft_package=wordpress_capability.draft_package,
                mode="live",
                live_write_enabled=_wordpress_draft_writes_enabled(),
                create_draft=create_wordpress_draft_post,
                action_apply_authorized=True,
                write_authorization=wordpress_capability.write_authorization,
                write_authorization_verified=True,
            )
            return {
                "adapter": mutation_adapter,
                "connector": action.connector,
                "allowed_operation": "create_wordpress_draft",
                "execution_status": execution.status,
                "execution_mode": execution.mode,
                "external_write_attempted": execution.external_write_attempted,
                "execution_result": execution.model_dump(mode="json"),
                "redacted": True,
            }, _wordpress_draft_execution_errors(execution)
        execution = execute_content_wordpress_draft_handoff(
            handoff=None,
            draft_package=None,
            mode="dry_run",
            live_write_enabled=False,
            create_draft=None,
        )
        return {
            "adapter": mutation_adapter,
            "connector": action.connector,
            "allowed_operation": "create_wordpress_draft",
            "execution_status": execution.status,
            "execution_mode": execution.mode,
            "external_write_attempted": execution.external_write_attempted,
            "execution_result": execution.model_dump(mode="json"),
            "redacted": True,
        }, _wordpress_draft_execution_errors(execution)
    return None, [f"Adapter zapisu {mutation_adapter} nie ma implementacji wykonania."]


def _wordpress_draft_writes_enabled() -> bool:
    return (variable_value("WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _wordpress_draft_execution_errors(execution: Any) -> list[str]:
    if execution.status in {"dry_run_ready", "created"}:
        return []
    blockers = [
        f"{blocker.label}: {blocker.reason}"
        for blocker in execution.blockers
    ]
    if blockers:
        return blockers
    return ["WordPress draft execution contract blocked the adapter."]


def _mutation_requirement(
    *,
    code: str,
    label: str,
    satisfied: bool,
    evidence: str | None = None,
) -> ActionMutationReadinessRequirement:
    return ActionMutationReadinessRequirement(
        code=code,
        label=label,
        satisfied=satisfied,
        evidence=evidence,
    )


def _mutation_readiness_blockers(
    requirements: list[ActionMutationReadinessRequirement],
) -> list[ActionMutationReadinessBlocker]:
    return mutation_readiness_blockers(requirements)


def _mutation_readiness_next_step(
    action: ActionObject,
    blockers: list[ActionMutationReadinessBlocker],
) -> str:
    if not blockers:
        return (
            "Warunki zapisu są spełnione; apply nadal wymaga osobnego POST z "
            "jawnym potwierdzeniem operatora."
        )
    if action.id == "act_apply_wordpress_draft_handoff":
        blocker_codes = {blocker.code for blocker in blockers}
        if {
            "missing_wordpress_draft_handoff_ready",
            "missing_wordpress_draft_package_ready",
        } & blocker_codes:
            return (
                "Najpierw przygotuj zatwierdzony WordPress handoff i paczkę "
                "szkicu dla wybranego content itemu; adapter boundary już "
                "istnieje, ale live write zostaje wyłączony."
            )
        if {
            "missing_preview_audit",
            "missing_confirmation_audit",
            "missing_wordpress_write_authorization",
        } & blocker_codes:
            return (
                "Przejdź preview, human review i confirm w ActionObject, żeby "
                "WILQ mógł zbudować write_authorization; live write nadal stop."
            )
    return blockers[0].next_step


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


def _is_raw_content_review_audit_event(action_id: str, event: AuditEvent) -> bool:
    if action_id != "act_prepare_content_refresh_queue":
        return False
    if not event.event_type.startswith("human_review_"):
        return False
    return _audit_event_has_raw_contract_text(event)


def _action_with_operator_labels(action: ActionObject) -> ActionObject:
    connector = get_connector_status(action.connector)
    return action.model_copy(
        update={
            "connector_label": connector.label if connector is not None else "źródło danych",
            "mode_label": _action_mode_label(action.mode),
            "risk_label": _action_risk_label(action.risk),
            "status_label": _action_status_label(action.status),
            "evidence_summary_label": _action_evidence_summary_label(action.evidence_ids),
            "validation_status_label": _action_validation_status_label(action.validation_status),
            "review_gate": _review_gate_with_operator_labels(action.review_gate),
            "preview_cards": _action_preview_cards(action),
            "audit_events": [
                _audit_event_with_operator_label(event) for event in action.audit_events
            ],
        }
    )


def _action_preview_cards(action: ActionObject) -> list[ActionPreviewCardViewModel]:
    if action.payload.get("preview_contract") == MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT:
        return _merchant_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "budget_apply_preview_v1":
        return _ads_budget_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "recommendation_apply_preview_v1":
        return _ads_recommendation_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "custom_segment_change_preview_v1":
        return _ads_custom_segment_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "negative_keyword_change_preview_v1":
        return _ads_negative_keyword_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "change_history_impact_review_v1":
        return _ads_change_history_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "demand_gen_readiness_review_preview_v1":
        return _demand_gen_readiness_preview_cards(action.payload)
    if action.payload.get("preview_contract") == SEARCH_TERM_NGRAM_PREVIEW_CONTRACT:
        return _search_term_ngram_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "ga4_tracking_quality_review_v1":
        return _ga4_tracking_quality_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "local_visibility_review_preview_v1":
        return _local_visibility_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "content_brief_preview_v1":
        return _content_refresh_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "wordpress_draft_handoff_preview_v1":
        return wordpress_draft_handoff_preview_cards(
            action.payload,
            preview_row=_preview_row,
            string_list=_string_list,
            apply_state_label=_apply_state_label,
            system_readiness_label=_system_readiness_label,
        )
    if action.payload.get("preview_contract") == "wordpress_draft_apply_preview_v1":
        return wordpress_draft_handoff_preview_cards(
            action.payload,
            preview_row=_preview_row,
            string_list=_string_list,
            apply_state_label=_apply_state_label,
            system_readiness_label=_system_readiness_label,
        )
    if (
        action.payload.get("preview_contract")
        == "service_profile_knowledge_promotion_preview_v1"
    ):
        return _service_profile_knowledge_promotion_preview_cards(action.payload)
    if action.payload.get("preview_contract") == "private_source_proposal_promotion_preview_v1":
        return _service_profile_private_proposal_promotion_preview_cards(action.payload)
    if action.payload.get("action_type") == KEYWORD_PLANNER_ACCESS_ACTION_TYPE:
        return _keyword_planner_access_preview_cards(action.payload)
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return _ads_target_guardrail_preview_cards(action.payload)
    if action.payload.get("action_type") == "record_ads_strategy_review":
        return _ads_strategy_review_preview_cards(action.payload)
    if action.payload.get("action_type") in {
        "linkedin_post_candidate",
        "facebook_post_candidate",
    }:
        return _social_draft_input_preview_cards(action.payload)
    return action.preview_cards


def _action_preview_item_view_models(
    *,
    action: ActionObject,
    raw_items: list[dict[str, Any]],
    preview_cards: list[ActionPreviewCardViewModel],
    max_items: int,
) -> list[ActionPreviewItemViewModel]:
    if preview_cards:
        return [
            _preview_item_from_card(
                card=card,
                raw_item=raw_items[index] if index < len(raw_items) else None,
                index=index,
            )
            for index, card in enumerate(preview_cards[:max_items])
        ]
    return [
        _preview_item_from_raw_payload(action, item, index)
        for index, item in enumerate(raw_items[:max_items])
    ]


def _preview_item_from_card(
    *,
    card: ActionPreviewCardViewModel,
    raw_item: dict[str, Any] | None,
    index: int,
) -> ActionPreviewItemViewModel:
    rows = list(card.rows[:4])
    if card.apply_state_label:
        rows.append(_preview_row("Zapis zmian", card.apply_state_label))
    if card.system_readiness_label:
        rows.append(_preview_row("Gotowość systemu", card.system_readiness_label))
    return ActionPreviewItemViewModel(
        id=f"preview_item_{index + 1}",
        preview_contract=_preview_item_contract(raw_item),
        candidate_id=_preview_item_candidate_id(raw_item),
        title_label=card.title_label or f"Pozycja podglądu {index + 1}",
        status_label=card.status_label,
        rows=rows,
    )


def _preview_item_from_raw_payload(
    action: ActionObject,
    item: dict[str, Any],
    index: int,
) -> ActionPreviewItemViewModel:
    rows = _safe_raw_preview_rows(item)
    if not rows:
        rows = [
            _preview_row(
                "Zakres", _preview_contract_label(_preview_contract(action.payload, [item]))
            ),
        ]
    return ActionPreviewItemViewModel(
        id=f"preview_item_{index + 1}",
        preview_contract=_preview_item_contract(item),
        candidate_id=_preview_item_candidate_id(item),
        title_label=_raw_preview_title(item, index),
        status_label=_raw_preview_status(item),
        rows=rows[:6],
    )


def _preview_item_contract(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    value = item.get("preview_contract")
    if isinstance(value, str) and value == "wordpress_draft_payload_preview_v1":
        return value
    return None


def _preview_item_candidate_id(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    if item.get("preview_contract") != "wordpress_draft_payload_preview_v1":
        return None
    value = item.get("candidate_id")
    return value if isinstance(value, str) and value else None


def _safe_raw_preview_rows(item: dict[str, Any]) -> list[ActionPreviewRowViewModel]:
    rows: list[ActionPreviewRowViewModel] = []
    for label, value in _raw_preview_label_values(item):
        rows.append(_preview_row(label, value))
        if len(rows) >= 4:
            break
    if "apply_allowed" in item:
        rows.append(_preview_row("Zapis zmian", _apply_state_label(item.get("apply_allowed"))))
    if "api_mutation_ready" in item:
        rows.append(
            _preview_row(
                "Gotowość systemu", _system_readiness_label(item.get("api_mutation_ready"))
            )
        )
    return rows


def _raw_preview_label_values(item: dict[str, Any]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for key, value in item.items():
        if not key.endswith("_label"):
            continue
        if key in {"id_label", "preview_contract_label"}:
            continue
        label = _raw_preview_row_label(key)
        if isinstance(value, str) and value:
            values.append((label, value))
        elif isinstance(value, list):
            values.extend((label, entry) for entry in value if isinstance(entry, str) and entry)
    return values


def _raw_preview_row_label(key: str) -> str:
    labels = {
        "affected_attribute_label": "Atrybut",
        "issue_type_label": "Problem",
        "mode_label": "Tryb",
        "operation_type_label": "Operacja",
        "readiness_label": "Gotowość",
        "recommendation_type_label": "Rekomendacja",
        "reason_label": "Powód",
        "risk_label": "Ryzyko",
        "status_label": "Status",
        "validation_status_label": "Walidacja",
    }
    return labels.get(key, "Szczegół")


def _raw_preview_title(item: dict[str, Any], index: int) -> str:
    for key in (
        "title_label",
        "issue_type_label",
        "recommendation_type_label",
        "operation_type_label",
        "mode_label",
    ):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return f"Pozycja podglądu {index + 1}"


def _raw_preview_status(item: dict[str, Any]) -> str:
    for key in ("status_label", "validation_status_label", "readiness_label"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _preview_contract_label(value: str | None) -> str:
    labels = {
        MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT: "przegląd problemów Merchant",
        "content_brief_preview_v1": "brief treści do sprawdzenia",
        "wordpress_draft_payload_preview_v1": "szkic WordPress do sprawdzenia",
        "local_visibility_review_preview_v1": "widoczność lokalna do sprawdzenia",
        "ga4_tracking_quality_review_v1": "jakość pomiaru GA4 do sprawdzenia",
    }
    return labels.get(value or "", "podgląd zmian do sprawdzenia")


def _content_refresh_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return content_refresh_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
        wordpress_draft_preview_card=wordpress_draft_payload_preview_card,
    )


def _service_profile_knowledge_promotion_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return knowledge_promotion_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _service_profile_private_proposal_promotion_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return private_proposal_promotion_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _social_draft_input_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return social_draft_input_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        source_connector_labels=_source_connector_labels,
        metric_fact_label=metric_fact_label,
        plain_metric_value_label=_plain_metric_value_label,
        apply_state_label=_apply_state_label,
    )


def _ads_budget_preview_cards(payload: dict[str, Any]) -> list[ActionPreviewCardViewModel]:
    return budget_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        micros_money_label=_micros_money_label,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _ads_recommendation_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return recommendation_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _ads_negative_keyword_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return negative_keyword_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _ads_custom_segment_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return custom_segment_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _ads_change_history_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return change_history_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        action_gate_labels=_action_gate_labels,
        blocked_claims=operator_blocked_claims,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _demand_gen_readiness_preview_cards(
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


def demand_gen_readiness_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return _demand_gen_readiness_preview_cards(payload)


def _search_term_ngram_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return build_search_term_ngram_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        plain_metric_value_label=_plain_metric_value_label,
        micros_money_label=_micros_money_label,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _ga4_tracking_quality_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return build_ga4_tracking_quality_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        metric_snapshot_rows=metric_snapshot_preview_rows,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _local_visibility_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return build_local_visibility_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        metric_snapshot_rows=metric_snapshot_preview_rows_for_keys,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _keyword_planner_access_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return build_keyword_planner_access_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
    )


def _ads_target_guardrail_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return build_ads_target_guardrail_preview_cards(
        payload,
        business_context_rows=_ads_business_context_preview_rows,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _ads_strategy_review_preview_cards(
    payload: dict[str, Any],
) -> list[ActionPreviewCardViewModel]:
    return build_ads_strategy_review_preview_cards(
        payload,
        business_context_rows=_ads_business_context_preview_rows,
        preview_row=_preview_row,
        string_list=_string_list,
        strategy_summary=ads_strategy_review_summary,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _ads_business_context_preview_rows(
    payload: dict[str, Any],
) -> list[ActionPreviewRowViewModel]:
    return build_ads_business_context_preview_rows(
        payload,
        preview_row=_preview_row,
        plain_metric_value_label=_plain_metric_value_label,
        micros_money_label=_micros_money_label,
    )


def _merchant_preview_cards(payload: dict[str, Any]) -> list[ActionPreviewCardViewModel]:
    return build_merchant_preview_cards(
        payload,
        preview_row=_preview_row,
        string_list=_string_list,
        apply_state_label=_apply_state_label,
        system_readiness_label=_system_readiness_label,
    )


def _preview_row(label: str, value: str) -> ActionPreviewRowViewModel:
    return ActionPreviewRowViewModel(label=label, value=value)


def _micros_money_label(
    value: Any,
    currency_code: str = "PLN",
    *,
    missing_label: str = "kwota niepotwierdzona",
) -> str:
    if not isinstance(value, int | float):
        return missing_label
    return f"{value / 1_000_000:.2f} {currency_code}"


def _apply_state_label(value: Any) -> str:
    return "zapis zmian dopuszczony" if value is True else "zapis zmian zablokowany"


def _system_readiness_label(value: Any) -> str:
    return "system gotowy do zapisu" if value is True else "system zablokowany przed zapisem"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _review_gate_with_operator_labels(gate: ActionReviewGate) -> ActionReviewGate:
    return gate.model_copy(
        update={
            "status_label": _action_review_gate_status_label(gate.status),
            "apply_blocker_summary_label": blocker_count_label(
                gate.apply_blocker_labels or gate.apply_blockers
            ),
            "last_mutation_blocker_summary_label": blocker_count_label(
                gate.last_mutation_blocker_labels or gate.last_mutation_blockers
            ),
            "last_review_outcome_label": review_outcome_label(gate.last_review_outcome)
            if gate.last_review_outcome
            else None,
            "last_impact_check_status_label": _action_result_status_label(
                gate.last_impact_check_status
            )
            if gate.last_impact_check_status
            else None,
            "last_mutation_audit_status_label": _action_mutation_audit_status_label(
                gate.last_mutation_audit_status
            )
            if gate.last_mutation_audit_status
            else None,
            "last_mutation_attempted_label": _action_mutation_attempted_label(
                gate.last_mutation_attempted
            ),
            "last_mutation_adapter_reached_label": _action_mutation_adapter_reached_label(
                gate.last_mutation_adapter_reached
            ),
            "last_external_write_attempted_label": _action_mutation_attempted_label(
                gate.last_external_write_attempted
            ),
            "last_mutation_adapter_label": _action_mutation_adapter_label(
                gate.last_mutation_adapter
            ),
            "last_mutation_audit_trace_label": _action_mutation_audit_trace_label(
                gate.last_mutation_audit_event_id
            ),
        }
    )


def _audit_event_with_operator_label(event: AuditEvent) -> AuditEvent:
    return event.model_copy(
        update={
            "event_type_label": event.event_type_label
            or _action_audit_event_label(event.event_type),
            "summary": _action_audit_summary_for_operator(event),
            "details": _audit_details_for_operator(event.details),
        }
    )


def _audit_details_for_operator(details: dict[str, Any]) -> dict[str, Any]:
    operator_details: dict[str, Any] = {}
    for key, value in details.items():
        if _contains_raw_audit_contract_text(str(key)):
            continue
        clean_value = _audit_detail_value_for_operator(value)
        if clean_value is not None:
            operator_details[str(key)] = clean_value
    checked_items = _string_list(operator_details.get("checked_items"))
    if checked_items:
        operator_details["checked_items"] = [_review_summary_item(item) for item in checked_items]
    blockers = _string_list(operator_details.get("blockers"))
    if blockers:
        operator_details["blockers"] = [_review_blocker_label(item) for item in blockers]
    return operator_details


def _audit_detail_value_for_operator(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if _contains_raw_audit_contract_text(str(key)):
                continue
            clean_item = _audit_detail_value_for_operator(item)
            if clean_item is not None:
                clean[str(key)] = clean_item
        return clean or None
    if isinstance(value, list):
        clean_items = [
            clean_item
            for item in value
            if (clean_item := _audit_detail_value_for_operator(item)) is not None
        ]
        return clean_items or None
    if isinstance(value, str) and _contains_raw_audit_contract_text(value):
        return None
    return value


def _action_review_gate(
    action: ActionObject,
    mutation_audits: list[ActionMutationAuditRecord] | None = None,
) -> ActionReviewGate:
    required_checks = _action_required_checks(action.payload)
    operator_checklist = _action_operator_checklist(action.payload)
    apply_allowed = _action_payload_apply_allowed(action.payload)
    last_review = latest_human_review_event(action.audit_events)
    last_confirmation = _latest_action_confirmation_event(action.audit_events)
    last_impact_check = _latest_action_impact_check_event(action.audit_events)
    last_mutation_audit = _latest_mutation_audit(mutation_audits or [])
    apply_blockers = _action_apply_blockers(
        action=action,
        required_checks=required_checks,
        apply_allowed=apply_allowed,
        confirmation_satisfied=last_confirmation is not None,
        impact_sanity_satisfied=_impact_status_from_event(last_impact_check) == "checked",
    )
    return build_action_review_gate(
        action=action,
        required_checks=required_checks,
        operator_checklist=operator_checklist,
        apply_allowed=apply_allowed,
        last_review=last_review,
        last_confirmation=last_confirmation,
        last_impact_check=last_impact_check,
        last_mutation_audit=last_mutation_audit,
        apply_blockers=apply_blockers,
        gate_labels=_action_gate_labels,
        confirmation_required=_action_confirmation_required,
        review_outcome=review_outcome_from_event,
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
    details: dict[str, Any] = {
        "review_outcome": request.outcome,
        "reviewed_by": request.reviewed_by,
        "checked_items": request.checked_items,
        "blockers": request.blockers,
    }
    url_review = _content_url_review_details_from_checked_items(request.checked_items)
    if url_review:
        details["content_url_review"] = url_review
    draft_readiness_review = _draft_readiness_review_details_from_checked_items(
        request.checked_items
    )
    if draft_readiness_review:
        details["content_draft_readiness_review"] = draft_readiness_review
    return details




def _action_preview_blockers(
    action: ActionObject,
    preview_items: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if not preview_items:
        blockers.append("payload_preview_missing")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    blockers.extend(action.review_gate.apply_blockers)
    return unique_values(blockers)


def _action_confirmation_blockers(
    action: ActionObject,
    request: ActionConfirmRequest,
    latest_preview: AuditEvent | None,
) -> list[str]:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return _ads_target_confirmation_blockers(request)

    blockers: list[str] = []
    if not request.preview_acknowledged:
        blockers.append("preview_acknowledgement_required")
    if latest_preview is None:
        blockers.append("dry_run_preview_required")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    return unique_values(blockers)


def _action_confirmation_event_type(action: ActionObject, confirmed: bool) -> str:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return (
            "ads_target_guardrail_confirmed"
            if confirmed
            else "ads_target_guardrail_confirmation_blocked"
        )
    return "action_apply_confirmed" if confirmed else "action_confirmation_blocked"


def _action_confirmation_summary(
    action: ActionObject,
    request: ActionConfirmRequest,
    blockers: list[str],
    latest_preview: AuditEvent | None,
) -> str:
    if action.payload.get("action_type") == "confirm_ads_target_guardrails":
        return _ads_target_confirmation_summary(request, blockers)

    if blockers:
        return (
            "Potwierdzenie zapisu zmian zablokowane: "
            f"{', '.join(_action_gate_labels(blockers))}. "
            f"{_operator_note_sentence(request.notes)}"
            "Ten krok nie zapisuje zmian w zewnętrznych systemach."
        )
    return (
        "Potwierdzenie podglądu zapisane. "
        f"{_operator_note_sentence(request.notes)}"
        "Ten krok nie zapisuje zmian w zewnętrznych systemach."
    )


def _ads_target_confirmation_blockers(request: ActionConfirmRequest) -> list[str]:
    blockers: list[str] = []
    target_count = int(request.target_roas is not None) + int(request.target_cpa_micros is not None)
    if target_count == 0:
        blockers.append("target_roas_or_cpa_required")
    if target_count > 1:
        blockers.append("exactly_one_target_guardrail_allowed")
    return blockers


def _ads_target_confirmation_summary(
    request: ActionConfirmRequest,
    blockers: list[str],
) -> str:
    if blockers:
        return (
            "Potwierdzenie celu Ads zablokowane: "
            f"{', '.join(_action_gate_labels(blockers))}. "
            f"Notatka: {request.notes}. "
            "Ten krok nie zapisuje zmian w Google Ads."
        )
    if request.target_roas is not None:
        target_summary = f"docelowy zwrot z reklam: {request.target_roas:g}"
    else:
        target_summary = (
            f"docelowy koszt pozyskania celu: {_micros_money_label(request.target_cpa_micros)}"
        )
    return (
        f"Potwierdzono roboczą zasadę bezpieczeństwa celu Ads: {target_summary}. "
        f"Notatka: {request.notes}. "
        "Ten zapis odblokowuje tylko kontekst przeglądu celu; nie zapisuje zmian, "
        "nie potwierdza rentowności i nie skaluje budżetu."
    )


def _action_impact_check_blockers(
    action: ActionObject,
    latest_confirmation: AuditEvent | None,
) -> list[str]:
    blockers: list[str] = []
    if latest_confirmation is None:
        blockers.append("action_confirmation_required")
    if not action.metrics:
        blockers.append("metric_facts_required")
    if not action.evidence_ids:
        blockers.append("evidence_ids_required")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    return unique_values(blockers)


def _action_impact_check_summary(
    *,
    request: ActionImpactCheckRequest,
    status: Literal["checked", "blocked"],
    metric_fact_count: int,
    source_connectors: list[str],
    blockers: list[str],
) -> str:
    parts = [
        f"Sprawdzenie efektu: {_action_result_status_label(status)}.",
        f"Porównanie sprzed zmiany: {request.pre_window_days} dni.",
        f"Porównanie po zmianie: {request.post_window_days} dni.",
        f"Metryki z dowodami: {metric_fact_count}.",
        "Źródła: "
        + (
            f"{', '.join(_source_connector_labels(source_connectors))}."
            if source_connectors
            else "brak."
        ),
    ]
    if blockers:
        parts.append(f"Blokady: {', '.join(_action_gate_labels(blockers))}.")
    parts.append(f"Notatka: {request.notes}.")
    parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(parts)


def _preview_contract(payload: dict[str, Any], preview_items: list[dict[str, Any]]) -> str | None:
    if isinstance(payload.get("preview_contract"), str):
        return str(payload["preview_contract"])
    for item in preview_items:
        contract = item.get("preview_contract")
        if isinstance(contract, str):
            return contract
    return None


def _action_required_checks(payload: dict[str, Any]) -> list[str]:
    checks = _string_list(payload.get("required_validation"))
    if checks:
        return checks
    preview_checks: list[str] = []
    for preview in _payload_preview_items(payload):
        preview_checks.extend(_string_list(preview.get("required_validation")))
    if preview_checks:
        return unique_values(preview_checks)
    for key in ("review_steps", "queue_steps", "draft_constraints"):
        values = _string_list(payload.get(key))
        if values:
            return values
    return ["validate_action_object", "human_review_before_apply"]


def _action_operator_checklist(payload: dict[str, Any]) -> list[str]:
    checklist = _string_list(payload.get("operator_review_gates"))
    if checklist:
        return checklist
    for key in ("review_steps", "queue_steps"):
        values = _string_list(payload.get(key))
        if values:
            return values
    return _action_required_checks(payload)


def _action_apply_blockers(
    *,
    action: ActionObject,
    required_checks: list[str],
    apply_allowed: bool,
    confirmation_satisfied: bool,
    impact_sanity_satisfied: bool,
) -> list[str]:
    blockers: list[str] = []
    if action.mode != ActionMode.apply:
        blockers.append("action_mode_prepare_only")
    if action.validation_status != "valid":
        blockers.append("action_validation_required")
    if not apply_allowed:
        blockers.append("payload_apply_allowed_false")
    if action.payload.get("destructive") is True:
        blockers.append("destructive_actions_blocked")
    if _requires_human_confirmation(required_checks) and not confirmation_satisfied:
        blockers.append("human_confirm_before_apply")
    if not impact_sanity_satisfied:
        blockers.append("impact_sanity_check_required")
    if action.mode == ActionMode.apply and _supported_mutation_adapter(action) is None:
        blockers.append("vendor_mutation_adapter_required")
    blocked_claims = _string_list(action.payload.get("blocked_claims"))
    blockers.extend(f"blocked_claim:{claim}" for claim in blocked_claims[:8])
    return unique_values(blockers)


def _action_gate_labels(values: Iterable[str]) -> list[str]:
    return action_gate_labels(values)


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


def _action_preview_summary(
    *,
    status: Literal["preview_ready", "blocked"],
    included_items: int,
    preview_items: int,
) -> str:
    if status == "blocked":
        return (
            f"Podgląd zmian przygotowany, ale zapis zmian pozostaje zablokowany. "
            f"Pokazano {included_items} z {preview_items} pozycji do sprawdzenia. "
            "Nie zapisano zmian w zewnętrznych systemach."
        )
    return (
        f"Podgląd zmian przygotowany. Pokazano {included_items} z {preview_items} "
        "pozycji do sprawdzenia. Nie zapisano zmian w zewnętrznych systemach."
    )


def _action_audit_summary_for_operator(event: AuditEvent) -> str:
    if event.event_type == "action_preview_generated":
        return _operator_preview_summary_from_audit(event.summary)
    if event.event_type in {"action_apply_confirmed", "action_apply_confirmation_confirmed"}:
        return _operator_audit_summary_text(event.summary) or (
            "Podgląd zmian potwierdzony. Nie zapisano zmian w zewnętrznych systemach."
        )
    if event.event_type in {"action_confirmation_blocked", "action_apply_confirmation_blocked"}:
        return _operator_audit_summary_text(event.summary) or (
            "Potwierdzenie podglądu zablokowane. Nie zapisano zmian w zewnętrznych systemach."
        )
    if event.event_type in {"action_impact_check_completed", "action_impact_check_blocked"}:
        return _operator_impact_summary_from_audit(event.summary)
    if event.event_type == "action_apply_blocked":
        return "Zapis zmian zablokowany przez warunki bezpieczeństwa WILQ."
    if event.event_type == "action_apply_completed":
        return "Zapis zmian wykonany i zapisany w audycie bezpieczeństwa."
    return _operator_audit_summary_text(event.summary)


def _operator_audit_summary_text(summary: str) -> str:
    clean_summary = str(summary or "").strip()
    if _contains_raw_audit_contract_text(clean_summary):
        return "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
    clean_summary = _remove_raw_audit_identifiers(clean_summary)
    return _normalize_operator_summary_text(clean_summary)


RAW_AUDIT_IDENTIFIER_RE = re.compile(r"\baudit_[A-Za-z0-9_:-]+\b")
RAW_AUDIT_REFERENCE_CLAUSE_RE = re.compile(
    r"\s*(Audyt podglądu|ID audytu|Ślad audytu):\s*audit_[A-Za-z0-9_:-]+\.?\s*",
    flags=re.IGNORECASE,
)


def _remove_raw_audit_identifiers(summary: str) -> str:
    if not RAW_AUDIT_IDENTIFIER_RE.search(summary):
        return summary
    without_reference_clause = RAW_AUDIT_REFERENCE_CLAUSE_RE.sub(" ", summary)
    if RAW_AUDIT_IDENTIFIER_RE.search(without_reference_clause):
        return "Zdarzenie audytu zapisane. Szczegóły techniczne są dostępne w audycie."
    return " ".join(without_reference_clause.split())


def _operator_note_sentence(notes: str) -> str:
    note = str(notes or "").strip().rstrip(".")
    note = re.sub(
        r"\s*Ten krok nie zapisuje zmian(?: w zewnętrznych systemach)?\.?$",
        "",
        note,
        flags=re.IGNORECASE,
    ).strip()
    if not note:
        return ""
    return f"Notatka: {note}. "


def _normalize_operator_summary_text(summary: str) -> str:
    compact = " ".join(str(summary or "").split())
    compact = re.sub(r"\.{2,}", ".", compact)
    return re.sub(
        r"Ten krok nie zapisuje zmian\. (?=Ten krok nie zapisuje zmian w zewnętrznych systemach\.)",
        "",
        compact,
    )


def _audit_event_has_raw_contract_text(event: AuditEvent) -> bool:
    if _contains_raw_audit_contract_text(event.summary):
        return True
    return _audit_detail_contains_raw_contract_text(event.details)


def _audit_detail_contains_raw_contract_text(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_raw_audit_contract_text(str(key))
            or _audit_detail_contains_raw_contract_text(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_audit_detail_contains_raw_contract_text(item) for item in value)
    if isinstance(value, str):
        return _contains_raw_audit_contract_text(value)
    return False


def _contains_raw_audit_contract_text(summary: str) -> bool:
    raw_fragments = (
        "blocked_claim:",
        "candidate:",
        "ekologus.dev.proudsite.pl",
        "mapping_",
        "payload_",
        "source_type:",
        "staging handoff",
        "target" "_site",
        "target" "_site" "_",
        "target" "_site" "_migration",
        "Explicit apply confirmation is required",
        "Action must be validated before apply",
        "Action mode must be apply before external execution",
    )
    return any(fragment in summary for fragment in raw_fragments)


def _operator_preview_summary_from_audit(summary: str) -> str:
    item_summary = ""
    if "pozycje=" in summary:
        item_fragment = summary.split("pozycje=", 1)[1].split(",", 1)[0].split(".", 1)[0]
        if item_fragment:
            item_summary = f" Pokazano {item_fragment} pozycji do sprawdzenia."
    if "blocked" in summary or "zablokowany" in summary:
        return (
            "Podgląd zmian przygotowany, ale zapis zmian pozostaje zablokowany."
            f"{item_summary} Nie zapisano zmian w zewnętrznych systemach."
        )
    return f"Podgląd zmian przygotowany.{item_summary} Nie zapisano zmian w zewnętrznych systemach."


def _operator_impact_summary_from_audit(summary: str) -> str:
    if "status=blocked" in summary or "zablok" in summary:
        prefix = "Sprawdzenie efektu zablokowane."
    else:
        prefix = "Sprawdzenie efektu zapisane."
    window_parts = [
        _operator_impact_summary_part(part.strip())
        for part in summary.split(".")
        if part.strip().startswith(
            (
                "Okno przed zmianą",
                "Okno po zmianie",
                "Porównanie sprzed zmiany",
                "Porównanie po zmianie",
                "Metryki z dowodami",
            )
        )
    ]
    clean_parts = [prefix, *[f"{part}." for part in window_parts]]
    if "Ten krok nie zapisuje zmian" not in " ".join(clean_parts):
        clean_parts.append("Ten krok nie zapisuje zmian w zewnętrznych systemach.")
    return " ".join(clean_parts)


def _operator_impact_summary_part(part: str) -> str:
    return impact_comparison_summary_label(part) or part


def _action_audit_event_label(event_type: str) -> str:
    labels = {
        "action_preview_generated": "Podgląd zmian wygenerowany",
        "human_review_approved_for_prepare": "Przegląd operatora zapisany",
        "human_review_needs_changes": "Przegląd wymaga poprawek",
        "human_review_rejected": "Przegląd odrzucony",
        "human_review_deferred": "Przegląd odłożony",
        "action_apply_confirmed": "Podgląd potwierdzony",
        "action_confirmation_blocked": "Potwierdzenie zablokowane",
        "action_apply_confirmation_blocked": "Potwierdzenie zablokowane",
        "action_impact_check_completed": "Sprawdzenie efektu zapisane",
        "action_impact_check_blocked": "Sprawdzenie efektu zablokowane",
        "apply_confirmation_missing": "Zapis zmian zablokowany",
        "action_apply_blocked": "Zapis zmian zablokowany",
        "action_apply_completed": "Zapis zmian wykonany",
    }
    return labels.get(event_type, "Zdarzenie audytu")


def _payload_with_operator_labels(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    _hydrate_operator_labels_recursive(enriched)
    return enriched


def _hydrate_operator_labels_recursive(value: Any) -> None:
    if isinstance(value, dict):
        _hydrate_operator_label_fields(value)
        for item in value.values():
            _hydrate_operator_labels_recursive(item)
    elif isinstance(value, list):
        for item in value:
            _hydrate_operator_labels_recursive(item)


def _hydrate_operator_label_fields(item: dict[str, Any]) -> None:
    if item.get("status_label") in (None, "") and isinstance(item.get("status"), str):
        item["status_label"] = _operator_state_label(item["status"])
    if item.get("post_status_label") in (None, "") and isinstance(item.get("post_status"), str):
        item["post_status_label"] = _wordpress_post_status_label(item["post_status"])
    label_fields = {
        "required_validation": "required_validation_labels",
        "operator_review_gates": "operator_review_gate_labels",
        "human_review_gates": "human_review_gate_labels",
        "draft_constraints": "draft_constraint_labels",
        "missing_read_contracts": "missing_read_contract_labels",
        "missing_requirements": "missing_requirement_labels",
        "required_google_ads_state": "required_google_ads_state_labels",
        "allowed_uses_after_confirmation": "allowed_uses_after_confirmation_labels",
        "allowed_contracts": "allowed_contract_labels",
        "target_roas_or_cpa": "target_roas_or_cpa_labels",
        "blocked_claims": "blocked_claim_labels",
    }
    for source_key, label_key in label_fields.items():
        existing_labels = _string_list(item.get(label_key))
        if existing_labels:
            continue
        source_values = _string_list(item.get(source_key))
        if source_values:
            item[label_key] = _action_gate_labels(source_values)
    if item.get("recommendation_type_label") in (None, "") and isinstance(
        item.get("recommendation_type"),
        str,
    ):
        item["recommendation_type_label"] = _ads_recommendation_type_label(
            item["recommendation_type"]
        )
    if item.get("match_type_label") in (None, "") and isinstance(
        item.get("match_type"),
        str,
    ):
        item["match_type_label"] = _ads_keyword_match_type_label(item["match_type"])
    if item.get("level_label") in (None, "") and isinstance(item.get("level"), str):
        item["level_label"] = _ads_negative_keyword_level_label(item["level"])


def _operator_state_label(value: str) -> str:
    labels = {
        "blocked": "zablokowane",
        "ready": "gotowe",
        "allowed": "dopuszczone",
        "missing": "status niepotwierdzony",
        "pending_validation": "czeka na sprawdzenie",
        "validated_prepare_only": "kontrola WILQ poprawna",
        "ready_to_apply": "gotowe do potwierdzenia",
        "blocked_apply": "zapis zmian zablokowany",
    }
    return labels.get(value, "do sprawdzenia")


def _ads_recommendation_type_label(value: str) -> str:
    labels = {
        "CAMPAIGN_BUDGET": "budżet kampanii",
        "KEYWORD": "słowa kluczowe",
        "RESPONSIVE_SEARCH_AD": "elastyczna reklama w wyszukiwarce",
        "TARGET_CPA_OPT_IN": "strategia kosztu pozyskania celu",
        "TARGET_ROAS_OPT_IN": "strategia zwrotu z reklam",
        "MAXIMIZE_CONVERSIONS_OPT_IN": "maksymalizacja konwersji",
        "MAXIMIZE_CONVERSION_VALUE_OPT_IN": "maksymalizacja wartości konwersji",
        "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH": "jakość zasobów Performance Max",
        "DISPLAY_EXPANSION_OPT_IN": "rozszerzenie kampanii na sieć reklamową",
        "DYNAMIC_IMAGE_EXTENSION_OPT_IN": "dynamiczne rozszerzenia graficzne",
        "SEARCH_PARTNERS_OPT_IN": "rozszerzenie kampanii na partnerów wyszukiwania",
        "UNKNOWN": "typ rekomendacji nieznany",
        "UNSPECIFIED": "typ rekomendacji nieokreślony",
    }
    return labels.get(value, "typ rekomendacji do sprawdzenia")


def _ads_keyword_match_type_label(value: str) -> str:
    labels = {
        "BROAD": "dopasowanie przybliżone",
        "PHRASE": "dopasowanie do wyrażenia",
        "EXACT": "dopasowanie ścisłe",
        "UNKNOWN": "dopasowanie nieznane",
        "UNSPECIFIED": "dopasowanie nieokreślone",
    }
    return labels.get(value, "dopasowanie do sprawdzenia")


def _ads_negative_keyword_level_label(value: str) -> str:
    labels = {
        "ad_group": "grupa reklam",
        "campaign_review_required": "poziom kampanii wymaga sprawdzenia",
    }
    return labels.get(value, "poziom do sprawdzenia")


def _wordpress_post_status_label(value: str) -> str:
    labels = {
        "draft": "szkic",
        "pending": "czeka na sprawdzenie",
        "private": "prywatny",
        "publish": "opublikowany",
    }
    return labels.get(value, "status wpisu do sprawdzenia")


def _action_payload_apply_allowed(payload: dict[str, Any]) -> bool:
    return payload_apply_allowed(payload, _payload_preview_items(payload))


def _action_payload_api_mutation_ready(payload: dict[str, Any]) -> bool:
    return payload_api_mutation_ready(payload, _payload_preview_items(payload))


def _action_confirmation_required(required_checks: list[str], mode: ActionMode) -> bool:
    if _requires_human_confirmation(required_checks):
        return True
    return mode in {ActionMode.prepare, ActionMode.apply}


def _requires_human_confirmation(required_checks: list[str]) -> bool:
    return any("human" in check and "confirm" in check for check in required_checks)


def _payload_preview_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "wordpress_draft_payload_preview",
        "budget_payload_preview",
        "custom_segment_payload_preview",
        "negative_keyword_payload_preview",
        "ngram_preview",
    ):
        preview = payload.get(key)
        if isinstance(preview, list):
            items = [item for item in preview if isinstance(item, dict)]
            if items:
                return items
        if isinstance(preview, dict):
            return [preview]
    preview = payload.get("payload_preview")
    if isinstance(preview, list):
        return [item for item in preview if isinstance(item, dict)]
    if isinstance(preview, dict):
        return [preview]
    preview_items: list[dict[str, Any]] = []
    for value in payload.values():
        if isinstance(value, list):
            preview_items.extend(
                item for item in value if isinstance(item, dict) and "apply_allowed" in item
            )
    return preview_items


def _latest_preview_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type == "action_preview_generated":
            return event
    return None


def _latest_action_confirmation_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type in {
            "action_apply_confirmed",
            "ads_target_guardrail_confirmed",
        }:
            return event
    return None


def _latest_action_impact_check_event(events: list[AuditEvent]) -> AuditEvent | None:
    for event in sorted(events, key=lambda item: item.created_at, reverse=True):
        if event.event_type in {"action_impact_check_completed", "action_impact_check_blocked"}:
            return event
    return None


def _latest_mutation_audit(
    audits: list[ActionMutationAuditRecord],
) -> ActionMutationAuditRecord | None:
    if not audits:
        return None
    return sorted(audits, key=lambda item: item.created_at, reverse=True)[0]


def _impact_status_from_event(event: AuditEvent | None) -> Literal["checked", "blocked"] | None:
    if event is None:
        return None
    if event.event_type == "action_impact_check_completed":
        return "checked"
    if event.event_type == "action_impact_check_blocked":
        return "blocked"
    return None
