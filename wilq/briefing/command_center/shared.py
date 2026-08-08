from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.google_ads.campaign_review import CAMPAIGN_REVIEW_ACTION_ID
from wilq.actions.google_ads.custom_segments import CUSTOM_SEGMENT_ACTION_ID
from wilq.actions.google_ads.negative_keywords import NEGATIVE_KEYWORD_ACTION_ID
from wilq.actions.google_ads.recommendations import RECOMMENDATION_REVIEW_ACTION_ID
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    connector_refresh_has_live_data,
)
from wilq.storage.local_state import local_state_store

STRICT_DAILY_INSTRUCTION = (
    "WILQ pokazuje tylko metryki i dowody z danych źródłowych. Brak danych "
    "oznacza blokadę, nie domysł marketingowy."
)


GA4_CONNECTOR_ID = "google_analytics_4"


GOOGLE_ADS_CONNECTOR_ID = "google_ads"


GOOGLE_MERCHANT_CONNECTOR_ID = "google_merchant_center"


AHREFS_CONNECTOR_ID = "ahrefs"


GA4_COMMAND_CENTER_DECISION_LIMIT = 6


GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT = 1200


MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT = 2000


GA4_COMMAND_CENTER_METRIC_FACT_LIMIT = 2000


AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT = 400


LOCALO_PROBE_METRIC_NAMES = {
    "access_token_present",
    "api",
    "authorization_code_supported",
    "mcp_initialize_status",
    "pkce_s256_supported",
}


LOCALO_COMMAND_CENTER_CONTRACT_FACT_NAMES = {
    "place_inventory": {
        "localo_active_place_count",
        "localo_place_detail_count",
    },
    "local_rankings": {
        "localo_tracked_keyword_count",
        "localo_visibility_score_count",
        "localo_avg_visibility_current",
        "localo_avg_visibility_change",
        "localo_latest_grid_position_count",
        "localo_avg_latest_grid_position",
        "localo_keyword_volume_count",
        "localo_total_keyword_volume",
    },
    "gbp_visibility": {
        "localo_gbp_impressions_total",
        "localo_gbp_actions_total",
        "localo_gbp_metric_point_count",
    },
    "competitor_visibility": {
        "localo_competitor_count",
        "localo_favorite_competitor_count",
        "localo_competitor_change_count",
    },
    "reviews": {
        "localo_avg_rating",
        "localo_snapshot_reviews_count",
        "localo_reviews_count",
        "localo_reviews_replied_count",
        "localo_reviews_removed_count",
        "localo_review_reply_rate",
    },
}


LOCALO_COMMAND_CENTER_CONTRACT_ORDER = [
    "place_inventory",
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks",
]


LOCALO_COMMAND_CENTER_CLAIM_BY_MISSING_CONTRACT = {
    "local_rankings": "lokalne rankingi",
    "gbp_visibility": "wyniki profilu firmy w Google",
    "competitor_visibility": "widoczność konkurencji",
    "reviews": "tempo nowych opinii",
    "local_tasks": "ukończone zadanie lokalne",
}


DAILY_DECISION_FRESH_AFTER_HOURS = 48


DAILY_DECISION_METRIC_FACT_LIMIT = 8


PRIMARY_DAILY_PLAN_IDS = {
    "plan_review_merchant_feed_issues",
    "plan_prepare_content_refresh_queue",
    "plan_review_ga4_landing_quality",
    "plan_review_ads_campaign_metrics",
    "plan_fix_ads_oauth_before_spend_analysis",
}


CONFIGURE_GOOGLE_ADS_ACTION_ID = "act_configure_google_ads_env"


DAILY_ADS_REVIEW_ACTION_IDS = (
    CAMPAIGN_REVIEW_ACTION_ID,
    RECOMMENDATION_REVIEW_ACTION_ID,
    CUSTOM_SEGMENT_ACTION_ID,
    NEGATIVE_KEYWORD_ACTION_ID,
)


def _latest_connector_refresh(connector_id: str) -> ConnectorRefreshRun | None:
    runs = local_state_store().list_connector_refresh_runs(connector_id)
    return runs[0] if runs else None


def _resolve_latest_connector_refresh(
    connector_id: str,
    latest_refresh: ConnectorRefreshRun | None,
    *,
    allow_refresh_lookup: bool,
) -> ConnectorRefreshRun | None:
    if latest_refresh is not None:
        return latest_refresh
    if not allow_refresh_lookup:
        return None
    return _latest_connector_refresh(connector_id)


def _latest_refresh_runs_by_connector(
    refresh_runs: list[ConnectorRefreshRun] | None,
) -> dict[str, ConnectorRefreshRun]:
    latest_by_connector: dict[str, ConnectorRefreshRun] = {}
    if refresh_runs is None:
        return latest_by_connector
    for run in refresh_runs:
        latest_by_connector.setdefault(run.connector_id, run)
    return latest_by_connector


def _refresh_runs_for_connector(
    connector_id: str,
    refresh_runs: list[ConnectorRefreshRun] | None,
) -> list[ConnectorRefreshRun]:
    if refresh_runs is None:
        return local_state_store().list_connector_refresh_runs(connector_id)
    return [run for run in refresh_runs if run.connector_id == connector_id]


def _facts_for_latest_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> list[MetricFact]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return facts
    evidence_ids = set(latest_refresh.evidence_ids)
    current_facts = [fact for fact in facts if fact.evidence_id in evidence_ids]
    return current_facts or facts


def _tactical_items_for_latest_refresh(
    latest_refresh: ConnectorRefreshRun | None,
    items: list[TacticalQueueItem],
) -> list[TacticalQueueItem]:
    if latest_refresh is None or not latest_refresh.evidence_ids:
        return items
    evidence_ids = set(latest_refresh.evidence_ids)
    current_items = [
        item
        for item in items
        if any(evidence_id in evidence_ids for evidence_id in item.evidence_ids)
    ]
    return current_items


def _refresh_has_live_data(run: ConnectorRefreshRun | None) -> bool:
    return connector_refresh_has_live_data(run)


def _risk_rank(risk: ActionRisk) -> int:
    return {
        ActionRisk.critical: 0,
        ActionRisk.high: 1,
        ActionRisk.medium: 2,
        ActionRisk.low: 3,
    }.get(risk, 4)


def _limited_ids(values: list[str], limit: int = 12) -> list[str]:
    return values[:limit]


def _action_ids_for(
    actions: list[ActionObject],
    *,
    connector: str,
    domain: OpportunityDomain | None = None,
) -> list[str]:
    return _unique(
        action.id
        for action in actions
        if action.connector == connector or (domain is not None and action.domain == domain)
    )


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
