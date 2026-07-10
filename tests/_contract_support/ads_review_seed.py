"""Google Ads metric scenarios shared by diagnostic and context tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store


def seed_google_ads_live_review_metric_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_command_center.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_command_center.duckdb"))
    run = _live_review_refresh_run(datetime.now(UTC))

    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(run, detailed_facts=_live_review_facts())


def _live_review_refresh_run(completed_at: datetime) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id="refresh_google_ads_command_center_live",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=completed_at,
        evidence_ids=["ev_refresh_refresh_google_ads_command_center_live"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "campaign_row_count": 1,
            "search_term_row_count": 1,
            "recommendation_row_count": 1,
        },
        summary="Google Ads command center live review seed.",
    )


def _live_review_facts() -> list[VendorMetricFact]:
    return [
        VendorMetricFact(
            name="customer_currency_code",
            value="PLN",
            dimensions={"customer_id": "1234567890"},
        ),
        *_campaign_metric_facts(),
        *_recommendation_facts(),
        *_search_term_facts(),
    ]


def _campaign_metric_facts() -> list[VendorMetricFact]:
    dimensions = {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "campaign_status": "ENABLED",
        "advertising_channel_type": "SEARCH",
        "budget_id": "701",
        "budget_name": "Brand budget",
        "budget_period": "DAILY",
        "budget_status": "ENABLED",
    }
    return [
        VendorMetricFact(name=name, value=value, dimensions=dimensions)
        for name, value in (
            ("clicks", 12),
            ("impressions", 120),
            ("cost_micros", 12000000),
            ("conversions", 1.0),
            ("conversion_value", 150.0),
            ("budget_amount_micros", 30000000),
            ("budget_has_recommended_budget", True),
            ("budget_recommended_amount_micros", 42000000),
        )
    ]


def _recommendation_facts() -> list[VendorMetricFact]:
    dimensions = {
        "recommendation_id": "rec-1",
        "recommendation_resource_name": "customers/123/recommendations/rec-1",
        "recommendation_type": "CAMPAIGN_BUDGET",
        "campaign_id": "101",
        "campaign_budget_id": "701",
        "dismissed": "false",
    }
    return [
        VendorMetricFact(name="recommendation_available", value=1, dimensions=dimensions),
        VendorMetricFact(name="recommendation_campaign_count", value=1, dimensions=dimensions),
    ]


def _search_term_facts() -> list[VendorMetricFact]:
    dimensions = {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "ad_group_id": "202",
        "ad_group_name": "BDO",
        "search_term": "odpady cena",
        "search_term_status": "NONE",
    }
    return [
        VendorMetricFact(name=name, value=value, dimensions=dimensions)
        for name, value in (
            ("search_term_clicks", 6),
            ("search_term_cost_micros", 5000000),
            ("search_term_conversions", 0.0),
        )
    ]


def save_google_ads_recommendation_rows_for_context_pack() -> None:
    completed_at = datetime.now(UTC) + timedelta(minutes=1)
    run = ConnectorRefreshRun(
        id="refresh_google_ads_recommendation_context_pack_seed",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=completed_at,
        evidence_ids=["ev_refresh_refresh_google_ads_recommendation_context_pack_seed"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "recommendation_query": "active_recommendations",
            "recommendation_row_count": 4,
            "recommendation_impact_row_count": 2,
        },
        summary="Google Ads recommendation context-pack seed.",
    )
    facts: list[VendorMetricFact] = []
    for recommendation_id, impact_available in (
        ("rec-a", True),
        ("rec-b", False),
        ("rec-c", False),
        ("rec-d", True),
    ):
        dimensions = {
            "recommendation_id": recommendation_id,
            "recommendation_resource_name": f"customers/123/recommendations/{recommendation_id}",
            "recommendation_type": "CAMPAIGN_BUDGET",
            "campaign_id": "101",
            "campaign_budget_id": "701",
            "dismissed": "false",
        }
        facts.extend(_recommendation_row_facts(dimensions, impact_available))

    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(run, detailed_facts=facts)


def _recommendation_row_facts(
    dimensions: dict[str, str],
    impact_available: bool,
) -> list[VendorMetricFact]:
    facts = [
        VendorMetricFact(name="recommendation_available", value=1, dimensions=dimensions),
        VendorMetricFact(name="recommendation_campaign_count", value=1, dimensions=dimensions),
    ]
    if impact_available:
        facts.extend(
            [
                VendorMetricFact(
                    name="recommendation_impact_base_clicks",
                    value=20,
                    dimensions=dimensions,
                ),
                VendorMetricFact(
                    name="recommendation_impact_potential_clicks",
                    value=25,
                    dimensions=dimensions,
                ),
            ]
        )
    return facts
