"""Read-only assembly and cache ownership for the ActionObject catalogue."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from wilq.actions.content_candidates import seed_metric_actions as seed_content_metric_actions
from wilq.actions.content_refresh import (
    content_contract_label,
    content_contract_labels,
    content_refresh_metric_candidate,
    post_publication_measurement_plan,
    post_publication_measurement_summary,
)
from wilq.actions.ga4.tracking_quality import ga4_tracking_quality_action_from_metric_facts
from wilq.actions.google_ads.action_candidates import (
    seed_metric_actions as seed_google_ads_metric_actions,
)
from wilq.actions.google_ads.business_context import (
    latest_google_ads_metric_facts,
    latest_google_ads_vendor_read,
    live_business_context_actions,
)
from wilq.actions.google_ads.campaign_review import campaign_review_action_from_metric_facts
from wilq.actions.google_ads.change_history import change_history_impact_action_from_metric_facts
from wilq.actions.google_ads.custom_segments import custom_segment_action_from_metric_facts
from wilq.actions.google_ads.demand_gen import (
    demand_gen_readiness_action_from_metric_facts,
    latest_vendor_read_evidence_ids,
)
from wilq.actions.google_ads.keyword_planner import keyword_planner_access_action_from_vendor_read
from wilq.actions.google_ads.negative_keywords import negative_keyword_action_from_metric_facts
from wilq.actions.google_ads.recommendations import recommendation_review_action_from_metric_facts
from wilq.actions.google_ads.search_term_ngrams import search_term_ngram_action_from_metric_facts
from wilq.actions.localo.visibility import (
    localo_action_metric_facts,
    localo_visibility_review_action_from_metric_facts,
    localo_visibility_review_payload_from_metric_facts,
)
from wilq.actions.merchant import (
    MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT,
    merchant_feed_issue_action_from_metric_facts,
)
from wilq.actions.metric_action_candidates import seed_non_ads_metric_actions
from wilq.actions.metric_action_facts import load_action_metric_facts
from wilq.actions.metric_utils import facts_by_connector, unique_values
from wilq.actions.registry_assembly import assemble_action_registry, seed_static_actions
from wilq.actions.service_profile import (
    service_profile_knowledge_promotion_action,
    service_profile_private_proposal_promotion_action,
)
from wilq.actions.social import social_draft_actions
from wilq.actions.wordpress_draft import draft_apply_action, draft_handoff_action
from wilq.actions.wordpress_handoff import (
    build_draft_apply_action,
    build_draft_apply_contract_payload,
    build_draft_handoff_action,
    build_draft_handoff_preview_item,
)
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.content.knowledge.service_profile import content_service_profile_response
from wilq.content.workflow.dev_draft_action import load_content_target_draft_action
from wilq.content.workflow.dev_draft_discard_action import load_content_dev_draft_discard_action
from wilq.content.workflow.new_page_draft_action import load_new_page_draft_action
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import ActionObject, ConnectorRefreshRun, ConnectorRefreshStatus, MetricFact
from wilq.storage.metric_store import metric_store

DEFAULT_ACTION_LIST_CACHE_SECONDS = 15.0
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
    connector_id: ACTION_METRIC_FACT_LIMIT for connector_id in ACTION_METRIC_CONNECTORS
}


@dataclass(frozen=True)
class ActionListCacheEntry:
    created_at: float
    actions: list[ActionObject]
    google_ads_registry_key: tuple[str, str, bool] | None = None


_cached_action_list: ActionListCacheEntry | None = None


def list_actions() -> list[ActionObject]:
    return list(_action_registry().values())


def list_actions_cached(
    decorate: Callable[[Iterable[ActionObject]], list[ActionObject]],
) -> list[ActionObject]:
    """Reuse a stable decorated catalogue across dashboard list reads."""
    cached = _read_action_list_cache()
    if cached is not None:
        return cached
    actions: list[ActionObject] = []
    for _ in range(2):
        registry_key = _google_ads_registry_cache_key()
        actions = decorate(list_actions())
        if registry_key == _google_ads_registry_cache_key():
            _write_action_list_cache(actions, google_ads_registry_key=registry_key)
            return actions
    return actions


def clear_action_list_cache() -> None:
    global _cached_action_list
    _cached_action_list = None


def get_action(action_id: str) -> ActionObject | None:
    cached_actions = _read_action_list_cache()
    action = next(
        (cached_action for cached_action in cached_actions or [] if cached_action.id == action_id),
        None,
    )
    if action is not None:
        return action.model_copy(deep=True)
    return (
        load_content_target_draft_action(action_id)
        or load_content_dev_draft_discard_action(action_id)
        or load_new_page_draft_action(action_id)
        or _action_registry().get(action_id)
    )


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
    actions: list[ActionObject], *, google_ads_registry_key: tuple[str, str, bool] | None
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


def _action_registry() -> dict[str, ActionObject]:
    latest_google_ads_run = _latest_google_ads_vendor_read()
    return assemble_action_registry(
        _STATIC_ACTIONS,
        seed_metric_action_candidates(),
        live_data_available=_google_ads_live_data_available(),
        configure_action_id="act_configure_google_ads_env",
        live_actions=(
            *live_business_context_actions(
                latest_google_ads_run,
                evidence_ids=unique_values(
                    [
                        connector_evidence_id("google_ads"),
                        *(latest_google_ads_run.evidence_ids if latest_google_ads_run else []),
                    ]
                ),
            ),
            keyword_planner_access_action_from_vendor_read(latest_google_ads_run),
        ),
    )


def _google_ads_live_data_available() -> bool:
    latest_run = _latest_google_ads_vendor_read()
    return latest_run is not None and (
        latest_run.status == ConnectorRefreshStatus.completed
        and latest_run.vendor_data_collected is True
    )


def _google_ads_registry_cache_key() -> tuple[str, str, bool] | None:
    latest_run = _latest_google_ads_vendor_read()
    if latest_run is None:
        return None
    return (latest_run.id, latest_run.status.value, latest_run.vendor_data_collected)


def _latest_google_ads_vendor_read() -> ConnectorRefreshRun | None:
    return latest_google_ads_vendor_read(list_connector_refresh_runs(connector_id="google_ads"))


def seed_metric_action_candidates() -> dict[str, ActionObject]:
    facts = _action_metric_facts()
    by_connector = facts_by_connector(facts)
    actions = seed_non_ads_metric_actions(
        by_connector=by_connector,
        merchant_action=lambda facts: merchant_feed_issue_action_from_metric_facts(
            facts, preview_contract=MERCHANT_FEED_ISSUE_PREVIEW_CONTRACT
        ),
        ga4_action=ga4_tracking_quality_action_from_metric_facts,
        localo_facts=_localo_action_metric_facts,
        localo_payload=localo_visibility_review_payload_from_metric_facts,
        localo_action=localo_visibility_review_action_from_metric_facts,
        social_action=social_draft_actions,
    )
    _seed_content_metric_actions(by_connector, actions)
    _seed_google_ads_metric_actions(by_connector, actions)
    return actions


def _seed_content_metric_actions(
    by_connector: dict[str, list[MetricFact]], actions: dict[str, ActionObject]
) -> None:
    actions.update(
        seed_content_metric_actions(
            content_facts=[
                *by_connector.get("wordpress_ekologus", []),
                *by_connector.get("google_search_console", []),
                *by_connector.get("ahrefs", []),
            ],
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
    *, content_payload: dict[str, Any] | None, content_action_metrics: list[MetricFact]
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


def _wordpress_draft_apply_contract_payload(handoff_action: ActionObject) -> dict[str, Any]:
    return build_draft_apply_contract_payload(handoff_action)


def _wordpress_draft_handoff_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    return build_draft_handoff_preview_item(
        item,
        contract_label=content_contract_label,
        contract_labels=content_contract_labels,
        measurement_plan=post_publication_measurement_plan,
        measurement_summary=post_publication_measurement_summary,
    )


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
