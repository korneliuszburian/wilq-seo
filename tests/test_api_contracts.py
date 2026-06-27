from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.wilq_api.main import app
from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
)
from wilq.actions.google_ads.change_history import CHANGE_HISTORY_IMPACT_ACTION_ID
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID
from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.actions.service import _social_draft_actions, apply_action, list_actions
from wilq.briefing.ads_diagnostics import (
    ADS_METRIC_FACT_LIMIT,
    _custom_segment_review_reason,
    _custom_segment_source_quality,
    build_ads_diagnostics,
)
from wilq.briefing.content_diagnostics import build_content_diagnostics, build_content_preflight
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.marketing_brief import build_marketing_brief
from wilq.briefing.merchant_diagnostics import (
    _merchant_price_impact_readiness,
    _merchant_product_performance_readiness,
)
from wilq.connectors.ahrefs.client import refresh_ahrefs_domain_rating
from wilq.connectors.google_ads.client import (
    _fetch_optional_shopping_product_performance,
    refresh_google_ads_campaign_summary,
)
from wilq.connectors.google_analytics_4.client import refresh_ga4_behavior_summary
from wilq.connectors.google_auth import GOOGLE_CREDENTIAL_ENV_NAMES
from wilq.connectors.google_merchant_center.client import (
    refresh_merchant_product_status_summary,
)
from wilq.connectors.google_search_console.client import refresh_search_console_site_summary
from wilq.connectors.google_sheets.client import refresh_google_sheets_review_surface
from wilq.connectors.localo.client import (
    _competitor_visibility_summary,
    refresh_localo_visibility_summary,
)
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.connectors.wordpress.client import refresh_wordpress_content_inventory
from wilq.evidence.registry import list_evidence_by_ids, refresh_run_evidence_id
from wilq.schemas import (
    ActionApplyRequest,
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AdsSearchTermMetricRow,
    AuditEvent,
    CommandCenterBriefItem,
    CommandCenterResponse,
    ConnectorCapability,
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    ConnectorSummary,
    DailyDecision,
    FreshnessState,
    KnowledgeCard,
    MarketingBrief,
    MerchantIssueCluster,
    MerchantProductPerformanceReadiness,
    MerchantProductPerformanceRow,
    MerchantProductSampleReadiness,
    MetricFact,
    Opportunity,
    OpportunityDomain,
    TacticalQueueResponse,
)
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

client = TestClient(app)

GOOGLE_ADS_TEST_ENV = (
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_ADS_CUSTOMER_ID",
    "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
)
GOOGLE_ADS_BUSINESS_CONTEXT_ENV = (
    "WILQ_ADS_PROFIT_MARGIN",
    "WILQ_ADS_PROFIT_MARGIN_PCT",
    "WILQ_ADS_BUSINESS_GOAL",
    "WILQ_ADS_BUDGET_GOAL",
    "WILQ_ADS_TARGET_ROAS",
    "WILQ_ADS_TARGET_CPA_MICROS",
)


def clear_google_ads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (*GOOGLE_ADS_TEST_ENV, *GOOGLE_ADS_BUSINESS_CONTEXT_ENV):
        monkeypatch.delenv(key, raising=False)


def clear_google_service_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GOOGLE_CREDENTIALS",
        "GOOGLE_SEARCH_CONSOLE_SITE_URL",
        "GSC_SITE_URL",
        "GA4_PROPERTY_ID",
        "GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID",
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def clear_wordpress_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "WORDPRESS_EKOLOGUS_URL",
        "WORDPRESS_EKOLOGUS_PUBLIC_URL",
        "WORDPRESS_EKOLOGUS_USERNAME",
        "WORDPRESS_EKOLOGUS_APP_PASSWORD",
        "WORDPRESS_SKLEP_URL",
        "WORDPRESS_SKLEP_PUBLIC_URL",
        "WORDPRESS_SKLEP_USERNAME",
        "WORDPRESS_SKLEP_APP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)


def clear_ahrefs_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "AHREFS_API_TOKEN",
        "AHREFS_API_KEY",
        "AHREFS_TARGET",
        "WORDPRESS_EKOLOGUS_URL",
        "MIS_PRIMARY_SITE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def clear_localo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "LOCALO_API_TOKEN",
        "LOCALO_ORGANIZATION_ID",
        "LOCALO_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)


def ga4_decision_trace(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": decision["id"],
            "decision_type": decision["decision_type"],
            "status": decision["status"],
            "priority": decision["priority"],
            "metric_tiles": decision["metric_tiles"],
            "source_connectors": decision["source_connectors"],
            "evidence_ids": decision["evidence_ids"],
            "action_ids": decision["action_ids"],
        }
        for decision in decisions
    ]


def seed_action_candidate_metric_facts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "action_candidates.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "action_candidates.duckdb"))
    runs = [
        ConnectorRefreshRun(
            id="refresh_google_merchant_center_action_test",
            connector_id="google_merchant_center",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_merchant_center_action_test"],
            metric_summary={
                "total_products": 10900,
                "active_products": 12,
                "disapproved_products": 3,
                "item_level_issue_count": 3,
            },
            summary="Merchant Center action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_google_analytics_4_action_test",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_analytics_4_action_test"],
            metric_summary={"active_users": 20, "sessions": 30},
            summary="GA4 action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_wordpress_ekologus_action_test",
            connector_id="wordpress_ekologus",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_wordpress_ekologus_action_test"],
            metric_summary={"content_object_count": 16, "pages_total": 4},
            summary="WordPress action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_google_search_console_action_test",
            connector_id="google_search_console",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_search_console_action_test"],
            metric_summary={"clicks": 12, "impressions": 120},
            summary="GSC action candidate metric seed.",
        ),
        ConnectorRefreshRun(
            id="refresh_ahrefs_action_test",
            connector_id="ahrefs",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_ahrefs_action_test"],
            metric_summary={"domain_rating": 90, "ahrefs_rank": 1450},
            summary="Ahrefs action candidate metric seed.",
        ),
    ]
    detailed_facts_by_run = {
        "refresh_google_search_console_action_test": [
            VendorMetricFact(
                name="clicks",
                value=12,
                dimensions={
                    "query": "zielony ład",
                    "page": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=120,
                dimensions={
                    "query": "zielony ład",
                    "page": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
                },
            ),
            VendorMetricFact(
                name="ctr",
                value=0.1,
                dimensions={
                    "query": "zielony ład",
                    "page": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
                },
            ),
            VendorMetricFact(
                name="average_position",
                value=2.1,
                dimensions={
                    "query": "zielony ład",
                    "page": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
                },
            ),
            VendorMetricFact(
                name="clicks",
                value=2,
                dimensions={
                    "query": "audyt środowiskowy",
                    "page": "https://www.ekologus.pl/audyt-srodowiskowy/",
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=88,
                dimensions={
                    "query": "audyt środowiskowy",
                    "page": "https://www.ekologus.pl/audyt-srodowiskowy/",
                },
            ),
        ],
        "refresh_google_analytics_4_action_test": [
            VendorMetricFact(
                name="active_users",
                value=41,
                dimensions={
                    "landing_page": "/europejski-zielony-lad-co-to-takiego/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=54,
                dimensions={
                    "landing_page": "/europejski-zielony-lad-co-to-takiego/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="engagement_rate",
                value=0.12,
                dimensions={
                    "landing_page": "/europejski-zielony-lad-co-to-takiego/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
        ],
        "refresh_wordpress_ekologus_action_test": [
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "site_kind": "primary",
                    "content_type": "pages",
                    "object_id": "42",
                    "content_url": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
                    "status": "publish",
                    "modified_gmt": "2026-06-15T10:00:00",
                },
            ),
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "site_kind": "primary",
                    "content_type": "pages",
                    "object_id": "84",
                    "content_url": "https://www.ekologus.pl/audyt-srodowiskowy/",
                    "title": "Audyt środowiskowy",
                    "status": "publish",
                    "modified_gmt": "2026-06-16T10:00:00",
                },
            )
        ],
        "refresh_ahrefs_action_test": [
            VendorMetricFact(
                name="ahrefs_content_gap_count",
                value=1,
                dimensions={
                    "gap_type": "content_gap",
                    "keyword": "audyt środowiskowy",
                    "competitor_domain": "denios.pl",
                    "source_url": "https://www.denios.pl/audyt-srodowiskowy/",
                },
            ),
            VendorMetricFact(
                name="ahrefs_top_page_gap_count",
                value=1,
                dimensions={
                    "gap_type": "top_page_gap",
                    "keyword": "beczka",
                    "competitor_domain": "denios.pl",
                    "source_url": "https://www.denios.pl/beczki/",
                },
            ),
            VendorMetricFact(
                name="ahrefs_competitor_page_count",
                value=2207,
                dimensions={
                    "gap_type": "competitor_page",
                    "competitor_domain": "cuk.pl",
                },
            ),
        ],
        "refresh_google_merchant_center_action_test": [
            VendorMetricFact(
                name="issue_product_count",
                value=3,
                dimensions={
                    "country": "PL",
                    "severity": "DISAPPROVED",
                    "resolution": "MERCHANT_ACTION",
                    "issue_type": "missing_image",
                    "issue_title": "Missing image",
                    "affected_attribute": "image_link",
                },
            ),
            VendorMetricFact(
                name="expiring_products",
                value=2,
                dimensions={"country": "PL", "reporting_context": "SHOPPING_ADS"},
            ),
        ],
    }
    for run in runs:
        metric_store().save_connector_refresh_metrics(
            run,
            detailed_facts=detailed_facts_by_run.get(run.id),
        )


def seed_google_ads_live_review_metric_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_command_center.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_command_center.duckdb"))
    completed_at = datetime.now(UTC)
    run = ConnectorRefreshRun(
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
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name="customer_currency_code",
                value="PLN",
                dimensions={"customer_id": "1234567890"},
            ),
            *[
                VendorMetricFact(
                    name=name,
                    value=value,
                    dimensions={
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                )
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
            ],
            VendorMetricFact(
                name="recommendation_available",
                value=1,
                dimensions={
                    "recommendation_id": "rec-1",
                    "recommendation_resource_name": "customers/123/recommendations/rec-1",
                    "recommendation_type": "CAMPAIGN_BUDGET",
                    "campaign_id": "101",
                    "campaign_budget_id": "701",
                    "dismissed": "false",
                },
            ),
            VendorMetricFact(
                name="recommendation_campaign_count",
                value=1,
                dimensions={
                    "recommendation_id": "rec-1",
                    "recommendation_type": "CAMPAIGN_BUDGET",
                    "campaign_id": "101",
                    "campaign_budget_id": "701",
                },
            ),
            VendorMetricFact(
                name="search_term_clicks",
                value=6,
                dimensions={
                    "campaign_id": "101",
                    "campaign_name": "Brand Search",
                    "ad_group_id": "202",
                    "ad_group_name": "BDO",
                    "search_term": "odpady cena",
                    "search_term_status": "NONE",
                },
            ),
            VendorMetricFact(
                name="search_term_cost_micros",
                value=5000000,
                dimensions={
                    "campaign_id": "101",
                    "campaign_name": "Brand Search",
                    "ad_group_id": "202",
                    "ad_group_name": "BDO",
                    "search_term": "odpady cena",
                    "search_term_status": "NONE",
                },
            ),
            VendorMetricFact(
                name="search_term_conversions",
                value=0.0,
                dimensions={
                    "campaign_id": "101",
                    "campaign_name": "Brand Search",
                    "ad_group_id": "202",
                    "ad_group_name": "BDO",
                    "search_term": "odpady cena",
                    "search_term_status": "NONE",
                },
            ),
        ],
    )


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
            "recommendation_resource_name": (
                f"customers/123/recommendations/{recommendation_id}"
            ),
            "recommendation_type": "CAMPAIGN_BUDGET",
            "campaign_id": "101",
            "campaign_budget_id": "701",
            "dismissed": "false",
        }
        facts.extend(
            [
                VendorMetricFact(
                    name="recommendation_available",
                    value=1,
                    dimensions=dimensions,
                ),
                VendorMetricFact(
                    name="recommendation_campaign_count",
                    value=1,
                    dimensions=dimensions,
                ),
            ]
        )
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
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(run, detailed_facts=facts)


def save_localo_visibility_metric_facts() -> None:
    localo_run = ConnectorRefreshRun(
        id="refresh_localo_opportunity_seed",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_localo_opportunity_seed"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "api": "localo_mcp_oauth_probe",
            "mcp_initialize_status": 200,
            "authorization_code_supported": 1,
            "pkce_s256_supported": 1,
            "access_token_present": 1,
            "localo_active_place_count": 4,
            "localo_tracked_keyword_count": 23,
            "localo_avg_visibility_current": 52.8261,
            "localo_reviews_count": 793,
        },
        summary="Odczyt danych Localo zakończony agregatami.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().save_connector_refresh_metrics(
        localo_run,
        detailed_facts=[
            VendorMetricFact(
                "localo_active_place_count",
                4,
                {"contract": "place_inventory", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_tracked_keyword_count",
                23,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_avg_visibility_current",
                52.8261,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_reviews_count",
                793,
                {"contract": "reviews", "scope": "active_places"},
                period="localo_mcp_read",
            ),
        ],
    )


def large_ads_metric_fact_fillers(count: int = 2050) -> list[VendorMetricFact]:
    return [
        VendorMetricFact(
            "diagnostic_filler",
            index,
            {
                "campaign_id": "101",
                "campaign_name": "Brand Search",
                "filler_id": str(index),
            },
            period="ads_metric_limit_regression",
        )
        for index in range(count)
    ]


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_local_dashboard_e2e_origin_is_allowed_by_cors() -> None:
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:5373",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5373"


def test_dynamic_local_dashboard_e2e_origin_is_allowed_by_cors() -> None:
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:39241",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:39241"


def test_root_endpoint_points_to_api_entrypoints() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "wilq-api"
    assert data["health"] == "/api/health"
    assert data["system_status"] == "/api/system/status"
    assert data["connectors"] == "/api/connectors"
    assert data["docs"] == "/docs"


def test_connector_registry_contains_required_connectors() -> None:
    response = client.get("/api/connectors")
    assert response.status_code == 200
    connector_ids = {item["id"] for item in response.json()}
    assert {
        "google_ads",
        "google_search_console",
        "google_analytics_4",
        "google_merchant_center",
        "google_sheets",
        "ahrefs",
        "localo",
        "wordpress_ekologus",
        "wordpress_sklep",
        "linkedin",
        "facebook",
        "openai_codex",
    }.issubset(connector_ids)


def test_google_sheets_is_optional_disabled_current_scope() -> None:
    response = client.get("/api/connectors/google_sheets/status")
    assert response.status_code == 200
    connector = response.json()
    assert connector["status"] == "disabled"
    assert connector["configured"] is False
    assert connector["missing_credentials"] == []
    assert connector["health_check"] == "disabled_optional"
    assert connector["error"] == "Connector disabled by current product scope."


def test_localo_status_requires_api_token_and_organization_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")

    response = client.get("/api/connectors/localo/status")

    assert response.status_code == 200
    connector = response.json()
    assert connector["status"] == "missing_credentials"
    assert connector["configured"] is False
    assert connector["required_env"] == [
        "LOCALO_API_TOKEN",
        "LOCALO_ORGANIZATION_ID",
        "LOCALO_ACCESS_TOKEN",
    ]
    assert connector["missing_credentials"] == ["LOCALO_ACCESS_TOKEN"]


def test_connector_status_does_not_expose_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "gho_supersecretvalue1234567890",  # pragma: allowlist secret
    )
    response = client.get("/api/connectors")
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "gho_supersecretvalue1234567890" not in serialized
    assert "GOOGLE_ADS_DEVELOPER_TOKEN" in serialized


def test_redaction_preserves_env_names_but_redacts_token_values() -> None:
    redacted = redact_mapping(
        {
            "api": "ahrefs_site_explorer_domain_rating",
            "audit_event_id": "audit_action_preview_generated_1234567890abcdef",
            "summary": (
                "Vendor read blocked by missing credential names: "
                "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID."
            ),
            "error": "failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
            "api_key": "sk-testsecretvalue1234567890",  # pragma: allowlist secret
            "decision_type": "merge_create_after_inventory_check",
            "credential_source": "repo_env",
            "created_by": "system_ads_target_confirmation_seed",
            "knowledge_card_ids": ["card_google_ads_budget_review_playbook"],
            "expert_rule_ids": ["ads_scaling_candidates_v1"],
            "business_policy_ids": [
                "use_margin_as_context_not_profitability_verdict",
            ],
            "operator_review_gates": ["google_ads_rmf_compliance_review"],
            "human_review_gates": [
                "review_search_terms_before_budget_decision",
            ],
            "review_gate": {
                "required_checks": [
                    "google_ads_rmf_compliance_review",
                    "reject_brand_or_low_intent_terms",
                ],
                "operator_checklist": ["check_existing_keywords_and_match_types"],
                "apply_blockers": [
                    "payload_apply_allowed_false",
                    "blocked_claim:zapis rekomendacji",
                ],
            },
            "operations": ["custom_segment_candidate"],
            "supported_actions": ["custom_segment_candidate"],
            "required_validation": ["google_ads_rmf_compliance_review"],
            "preview_contract": "custom_segment_change_preview_v1",
            "custom_segment_preview_id": "preview_ads_custom_segment_23848569273",
            "operation_type": "custom_segment_targeting_review",
            "recommended_actions": ["prepare_custom_segment_review"],
            "source_metric_names": ["search_term_clicks"],
            "available_read_contracts": ["ga4_landing_source_campaign_quality"],
            "missing_read_contracts": [
                "demand_gen_landing_quality_by_campaign",
                "demand_gen_transition_constraints",
            ],
            "omitted_contracts": [
                "keyword_match_context_read_contract",
                "search_term_safety_read_contract",
            ],
            "blocked_claims": ["rekomendacja uruchomienia Demand Gen"],
            "cluster_id": (
                "merchant_issue_pl_not_impacted_missing_potentially_required_attribute"
            ),
            "issue_type": "missing_potentially_required_attribute",
            "affected_attribute": "n:unit_pricing_measure",
            "country": "PL",
            "reporting_context": "SHOPPING_ADS",
            "severity": "NOT_IMPACTED",
            "resolution": "MERCHANT_ACTION",
            "normalized_page_path": "/europejski-zielony-lad-co-to-takiego",
            "wordpress_content_url": (
                "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
            ),
            "allowed_evidence": ["ahrefs_organic_keyword_gap_count"],
            "gap_type": "organic_keyword_gap",
            "source_url": "https://example.pl/poradnik/",
            "target_url": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
            "source_site_host": "www.ekologus.pl",
            "source_public_url": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
            "intended_final_url": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
            "final_canonical_url": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
            "preview_url": None,
            "competitor_domain": "example.pl",
            "keyword": "zielony ład obowiązki",
            "gsc_overlap_terms": ["zielony ład"],
            "wordpress_overlap_urls": [
                "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
            ],
        }
    )

    assert redacted["api"] == "ahrefs_site_explorer_domain_rating"
    assert redacted["audit_event_id"] == "audit_action_preview_generated_1234567890abcdef"
    assert redacted["summary"] == (
        "Vendor read blocked by missing credential names: "
        "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID."
    )
    assert redacted["error"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["decision_type"] == "merge_create_after_inventory_check"
    assert redacted["credential_source"] == "repo_env"
    assert redacted["created_by"] == "system_ads_target_confirmation_seed"
    assert redacted["knowledge_card_ids"] == ["card_google_ads_budget_review_playbook"]
    assert redacted["expert_rule_ids"] == ["ads_scaling_candidates_v1"]
    assert redacted["business_policy_ids"] == [
        "use_margin_as_context_not_profitability_verdict"
    ]
    assert redacted["operator_review_gates"] == ["google_ads_rmf_compliance_review"]
    assert redacted["human_review_gates"] == [
        "review_search_terms_before_budget_decision"
    ]
    assert redacted["review_gate"]["required_checks"] == [
        "google_ads_rmf_compliance_review",
        "reject_brand_or_low_intent_terms",
    ]
    assert redacted["review_gate"]["operator_checklist"] == [
        "check_existing_keywords_and_match_types"
    ]
    assert redacted["review_gate"]["apply_blockers"] == [
        "payload_apply_allowed_false",
        "blocked_claim:zapis rekomendacji",
    ]
    assert redacted["operations"] == ["custom_segment_candidate"]
    assert redacted["supported_actions"] == ["custom_segment_candidate"]
    assert redacted["required_validation"] == ["google_ads_rmf_compliance_review"]
    assert redacted["preview_contract"] == "custom_segment_change_preview_v1"
    assert redacted["custom_segment_preview_id"] == (
        "preview_ads_custom_segment_23848569273"
    )
    assert redacted["operation_type"] == "custom_segment_targeting_review"
    assert redacted["recommended_actions"] == ["prepare_custom_segment_review"]
    assert redacted["source_metric_names"] == ["search_term_clicks"]
    assert redacted["available_read_contracts"] == [
        "ga4_landing_source_campaign_quality"
    ]
    assert redacted["missing_read_contracts"] == [
        "demand_gen_landing_quality_by_campaign",
        "demand_gen_transition_constraints",
    ]
    assert redacted["omitted_contracts"] == [
        "keyword_match_context_read_contract",
        "search_term_safety_read_contract",
    ]
    assert redacted["blocked_claims"] == ["rekomendacja uruchomienia Demand Gen"]
    assert redact_mapping({"name": "localo_latest_grid_position_count"})["name"] == (
        "localo_latest_grid_position_count"
    )
    assert redact_mapping({"metric_name": "localo_avg_visibility_current"})["metric_name"] == (
        "localo_avg_visibility_current"
    )
    assert redacted["cluster_id"] == (
        "merchant_issue_pl_not_impacted_missing_potentially_required_attribute"
    )
    assert redacted["issue_type"] == "missing_potentially_required_attribute"
    assert redacted["affected_attribute"] == "n:unit_pricing_measure"
    assert redacted["country"] == "PL"
    assert redacted["reporting_context"] == "SHOPPING_ADS"
    assert redacted["severity"] == "NOT_IMPACTED"
    assert redacted["resolution"] == "MERCHANT_ACTION"
    assert redacted["normalized_page_path"] == "/europejski-zielony-lad-co-to-takiego"
    assert redacted["wordpress_content_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert redacted["allowed_evidence"] == ["ahrefs_organic_keyword_gap_count"]
    assert redacted["gap_type"] == "organic_keyword_gap"
    assert redacted["source_url"] == "https://example.pl/poradnik/"
    assert redacted["target_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert redacted["source_site_host"] == "www.ekologus.pl"
    assert redacted["source_public_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert redacted["intended_final_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert redacted["final_canonical_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert redacted["preview_url"] is None
    assert redacted["competitor_domain"] == "example.pl"
    assert redacted["keyword"] == "zielony ład obowiązki"
    assert redacted["gsc_overlap_terms"] == ["zielony ład"]
    assert redacted["wordpress_overlap_urls"] == [
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    ]
    assert redact_mapping(
        {
            "summary": (
                "Sprawdzone: "
                "candidate:content_brief_gsc_europejski_zielony_lad_co_to_takiego."
            )
        }
    )["summary"] == (
        "Sprawdzone: "
        "candidate:content_brief_gsc_europejski_zielony_lad_co_to_takiego."
    )
    assert redact_mapping(
        {
            "summary": (
                "Nadal brakujące kontrakty: "
                "demand_gen_landing_quality_by_campaign, "
                "demand_gen_transition_constraints."
            )
        }
    )["summary"] == (
        "Nadal brakujące kontrakty: "
        "demand_gen_landing_quality_by_campaign, "
        "demand_gen_transition_constraints."
    )
    assert redact_mapping({"summary": "token sk-this_must_be_hidden"})["summary"] == (
        "[REDACTED]"
    )


def test_google_first_party_status_accepts_authorized_user_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    oauth_json = tmp_path / "oauth-client.json"
    oauth_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(oauth_json))
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")

    response = client.get("/api/connectors")

    assert response.status_code == 200
    connectors = {item["id"]: item for item in response.json()}
    missing_label = "|".join(GOOGLE_CREDENTIAL_ENV_NAMES)
    for connector_id in ("google_search_console", "google_analytics_4"):
        connector = connectors[connector_id]
        assert connector["configured"] is True
        assert connector["status"] == "configured"
        assert missing_label not in connector["missing_credentials"]
        assert connector["error"] is None
        assert set(GOOGLE_CREDENTIAL_ENV_NAMES).issubset(connector["required_env"])


def test_system_status_reports_credential_runtime_without_paths_or_filenames() -> None:
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "access_pack" not in data
    credential_runtime = data["credential_runtime"]
    assert credential_runtime["secrets_redacted"] is True
    assert "repo_env_path" not in credential_runtime
    assert "access_pack_path" not in credential_runtime
    assert "credential_files_present" not in credential_runtime
    assert "manifest_files" not in credential_runtime


def test_codex_run_redacts_token_like_error_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "codex_state.sqlite3"))
    response = client.post(
        "/api/codex/runs",
        json={
            "id": "codex_redaction_test",
            "status": "failed",
            "source": "test",
            "error": "failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
        },
    )
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "sk-testsecretvalue1234567890" not in serialized
    assert "[REDACTED]" in serialized
    list_response = client.get("/api/codex/runs")
    assert list_response.status_code == 200
    listed = json.dumps(list_response.json())
    assert "codex_redaction_test" in listed
    assert "sk-testsecretvalue1234567890" not in listed


def test_api_is_local_only_by_default() -> None:
    remote_client = TestClient(app, base_url="http://example.com")
    response = remote_client.get("/api/health")
    assert response.status_code == 403


def test_opportunity_requires_source_connector() -> None:
    with pytest.raises(ValidationError):
        Opportunity(
            id="bad",
            type="bad",
            title="Bad",
            domain=OpportunityDomain.google_ads,
            source_connectors=[],
            evidence_ids=["ev_1"],
            human_diagnosis="Missing source connector should fail.",
            recommended_action="Fix schema.",
        )


def test_opportunity_requires_evidence_id() -> None:
    with pytest.raises(ValidationError):
        Opportunity(
            id="bad",
            type="bad",
            title="Bad",
            domain=OpportunityDomain.google_ads,
            source_connectors=["google_ads"],
            evidence_ids=[],
            human_diagnosis="Missing evidence should fail.",
            recommended_action="Fix schema.",
        )


def test_action_requires_evidence_id() -> None:
    with pytest.raises(ValidationError):
        ActionObject(
            id="bad",
            title="Bad action",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.apply,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=[],
            human_diagnosis="No evidence.",
            recommended_reason="Should fail.",
            payload={"action_type": "bad"},
            validation_status="not_validated",
            created_by="test",
        )


def test_action_apply_requires_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "audit_state.sqlite3"))
    response = client.post("/api/actions/act_configure_google_ads_env/apply")
    assert response.status_code == 409
    body = response.json()["detail"]
    serialized = json.dumps(body, ensure_ascii=False)
    assert body["mutation_audit"]["status"] == "blocked"
    assert body["mutation_audit"]["mutation_attempted"] is False
    assert body["mutation_audit"]["mutation_adapter"] is None
    assert "Wymagane jest jawne potwierdzenie zapisu zmian" in serialized
    assert "Przed zapisem zmian" in serialized
    audit_response = client.get(
        "/api/audit/events?action_id=act_configure_google_ads_env"
    )
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "apply_confirmation_missing"
    mutation_audit_response = client.get(
        "/api/action-mutation-audits?action_id=act_configure_google_ads_env"
    )
    assert mutation_audit_response.status_code == 200
    mutation_audits = mutation_audit_response.json()
    assert len(mutation_audits) == 1
    assert mutation_audits[0]["status"] == "blocked"
    assert mutation_audits[0]["mutation_attempted"] is False
    assert mutation_audits[0]["audit_event_id"] == body["audit_event"]["id"]

    action_response = client.get("/api/actions/act_configure_google_ads_env")
    assert action_response.status_code == 200
    review_gate = action_response.json()["review_gate"]
    assert review_gate["last_mutation_audit_status"] == "blocked"
    assert review_gate["last_mutation_attempted"] is False
    assert review_gate["last_mutation_adapter"] is None
    assert review_gate["last_mutation_audit_event_id"] == body["audit_event"]["id"]
    assert "Wymagane jest jawne potwierdzenie zapisu zmian" in json.dumps(
        review_gate["last_mutation_blockers"]
    )
    assert "Wymagane jest jawne potwierdzenie zapisu zmian." in review_gate[
        "last_mutation_blocker_labels"
    ]


def test_action_apply_requires_explicit_confirmation_actor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirm_audit_state.sqlite3"))

    response = client.post(
        "/api/actions/act_configure_google_ads_env/apply",
        json={"confirm": True},
    )

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["status"] == "blocked"
    assert "Brakuje osoby potwierdzającej zapis zmian" in json.dumps(
        body, ensure_ascii=False
    )
    assert body["audit_event"]["event_type"] == "apply_confirmation_missing"
    assert body["mutation_audit"]["status"] == "blocked"
    assert body["mutation_audit"]["actor"] == "wilq_api"


def test_action_apply_confirmed_prepare_action_still_blocks_with_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirmed_prepare_audit.sqlite3"))
    validate_response = client.post("/api/actions/act_configure_google_ads_env/validate")
    assert validate_response.status_code == 200

    response = client.post(
        "/api/actions/act_configure_google_ads_env/apply",
        json={"confirm": True, "confirmed_by": "operator_test"},
    )

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["status"] == "blocked"
    assert body["audit_event"]["event_type"] == "apply_blocked"
    assert body["audit_event"]["actor"] == "operator_test"
    assert body["mutation_audit"]["actor"] == "operator_test"
    assert body["mutation_audit"]["mutation_attempted"] is False
    assert "Akcja nie ma trybu zapisu zmian w zewnętrznym systemie" in json.dumps(
        body, ensure_ascii=False
    )


def test_apply_ready_action_blocks_without_mutation_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")
    action = ActionObject(
        id="act_synthetic_apply_ready",
        title="Synthetic apply-ready action",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_synthetic_apply_ready"],
        metrics=[
            MetricFact(
                name="cost_micros",
                value=1000,
                period="last_7_days",
                source_connector="google_ads",
                evidence_id="ev_synthetic_apply_ready",
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
                id="audit_preview",
                action_id="act_synthetic_apply_ready",
                event_type="action_preview_generated",
                actor="operator_test",
                summary="Preview generated.",
                evidence_ids=["ev_synthetic_apply_ready"],
            ),
            AuditEvent(
                id="audit_confirm",
                action_id="act_synthetic_apply_ready",
                event_type="action_apply_confirmed",
                actor="operator_test",
                summary="Preview confirmed.",
                evidence_ids=["ev_synthetic_apply_ready"],
            ),
            AuditEvent(
                id="audit_impact",
                action_id="act_synthetic_apply_ready",
                event_type="action_impact_check_completed",
                actor="operator_test",
                summary="Impact checked.",
                evidence_ids=["ev_synthetic_apply_ready"],
            ),
        ],
    )

    result = apply_action(
        action,
        ActionApplyRequest(confirm=True, confirmed_by="operator_test"),
    )

    assert result.applied is False
    assert result.status == "blocked"
    assert result.audit_event.event_type == "apply_blocked"
    assert result.mutation_audit.status == "blocked"
    assert result.mutation_audit.mutation_attempted is False
    assert result.mutation_audit.mutation_adapter is None
    assert "vendor_mutation_adapter_required" in action.review_gate.apply_blockers
    assert (
        "brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"
        in action.review_gate.apply_blocker_labels
    )
    assert action.review_gate.apply_allowed is False
    assert "Brakuje bezpiecznej ścieżki zapisu zmian dla tej akcji" in json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
    )


def test_action_operator_labels_are_specific(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "action_labels.sqlite3"))
    leaks: list[tuple[str, str]] = []

    def walk(action_id: str, value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                if key.endswith("_labels") and isinstance(item, list):
                    if (
                        "warunek techniczny do sprawdzenia" in item
                        or "brak opisu w kontrakcie WILQ" in item
                    ):
                        leaks.append((action_id, item_path))
                walk(action_id, item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(action_id, item, f"{path}[{index}]")

    for action in list_actions():
        walk(action.id, action.model_dump(mode="json"))

    assert leaks == []


def test_action_review_records_human_outcome_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "human_review_state.sqlite3"))

    review_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": "Sprawdzono kolejkę feedu; można kontynuować przygotowanie.",
            "checked_items": ["group_issue_reasons", "prepare_feed_fix_preview"],
            "blockers": ["payload_apply_allowed_false"],
        },
    )

    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["status"] == "recorded"
    assert review_payload["status_label"] == "zapisane"
    assert review_payload["audit_event"]["event_type"] == "human_review_approved_for_prepare"
    assert review_payload["audit_event"]["event_type_label"] == "Przegląd operatora zapisany"
    assert review_payload["audit_event"]["actor"] == "operator_test"
    assert review_payload["review_gate"]["last_review_outcome"] == "approved_for_prepare"
    assert (
        review_payload["review_gate"]["last_review_outcome_label"]
        == "zatwierdzone do dalszego przygotowania"
    )
    assert review_payload["review_gate"]["status_label"]
    assert review_payload["review_gate"]["apply_allowed"] is False
    assert "zmian w zewnętrznych systemach" in review_payload["audit_event"]["summary"]

    audit_response = client.get(
        "/api/audit/events?action_id=act_review_merchant_feed_issues"
    )
    assert audit_response.status_code == 200
    audit_events = audit_response.json()
    assert audit_events[0]["event_type"] == "human_review_approved_for_prepare"

    action_response = client.get("/api/actions/act_review_merchant_feed_issues")
    assert action_response.status_code == 200
    action = action_response.json()
    assert action["connector_label"] == "Google Merchant Center"
    assert action["mode_label"] == "przygotowanie"
    assert action["status_label"]
    assert action["risk_label"]
    assert action["validation_status_label"]
    assert action["audit_events"][0]["event_type"] == "human_review_approved_for_prepare"
    assert action["audit_events"][0]["event_type_label"] == "Przegląd operatora zapisany"
    assert action["review_gate"]["last_review_outcome"] == "approved_for_prepare"
    assert (
        action["review_gate"]["last_review_outcome_label"]
        == "zatwierdzone do dalszego przygotowania"
    )
    assert action["review_gate"]["last_reviewed_by"] == "operator_test"
    assert action["review_gate"]["apply_allowed"] is False


def test_action_preview_generates_dry_run_audit_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "preview_state.sqlite3"))

    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 3},
    )

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["status"] in {"preview_ready", "blocked"}
    assert preview["status_label"] in {"podgląd gotowy", "zablokowany"}
    assert preview["dry_run"] is True
    assert preview["mutation_allowed"] is False
    assert preview["audit_event"]["event_type"] == "action_preview_generated"
    assert preview["audit_event"]["event_type_label"] == "Podgląd zmian wygenerowany"
    assert preview["audit_event"]["actor"] == "operator_test"
    assert preview["preview_items_total"] >= len(preview["preview_items"])
    assert len(preview["preview_items"]) <= 3
    assert preview["review_gate"]["apply_allowed"] is False
    assert preview["review_gate"]["status_label"]
    assert len(preview["blocker_labels"]) == len(preview["blockers"])
    assert "warunek techniczny do sprawdzenia" not in preview["blocker_labels"]
    assert "status=" not in preview["audit_event"]["summary"]
    assert "zapis zmian=" not in preview["audit_event"]["summary"]
    assert "zapis zmian pozostaje zablokowany" in preview["audit_event"]["summary"]

    audit_response = client.get(
        "/api/audit/events?action_id=act_review_merchant_feed_issues"
    )
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "action_preview_generated"


def test_content_action_preview_exposes_review_only_brief_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_preview_state.sqlite3"))

    preview_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/preview",
        json={"requested_by": "operator_test", "max_items": 4},
    )

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["preview_contract"] == "content_brief_preview_v1"
    assert preview["dry_run"] is True
    assert preview["mutation_allowed"] is False
    assert preview["status"] == "blocked"
    assert preview["preview_items_total"] >= 2
    assert any(
        item["source_type"] == "gsc_query_page" for item in preview["preview_items"]
    )
    assert any(
        item["source_type"] == "ahrefs_gap_review" for item in preview["preview_items"]
    )
    assert not any(
        item.get("preview_contract") == "wordpress_draft_payload_preview_v1"
        for item in preview["preview_items"]
    )
    for item in preview["preview_items"]:
        assert item["apply_allowed"] is False
        assert item["api_mutation_ready"] is False
        assert item["evidence_ids"]
        assert "gwarancja pozycji" in item["blocked_claims"]
    assert "action_mode_prepare_only" in preview["blockers"]


def test_content_brief_preview_keeps_dev_site_as_optional_preview_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_target_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_target.duckdb"))
    source_url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    dev_preview_url = (
        "https://ekologus.dev.proudsite.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    )
    gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_content_public_url_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_gsc_content_public_url_test"],
        metric_summary={"query_page_rows": 1},
        summary="GSC source URL for public content review.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_content_public_url_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_content_public_url_test"],
        metric_summary={"content_object_count": 1},
        summary="Dev preview URL should not become public content inventory.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=8,
                dimensions={"query": "bdo przedsiębiorca", "page": source_url},
            ),
            VendorMetricFact(
                name="impressions",
                value=220,
                dimensions={"query": "bdo przedsiębiorca", "page": source_url},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": dev_preview_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                    "modified_gmt": "2026-06-20T08:15:00+00:00",
                    "title_or_h1": "BDO - co musi wiedzieć przedsiębiorca?",
                    "canonical_url": dev_preview_url,
                },
            )
        ],
    )

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    diagnostics_response = client.get("/api/content/diagnostics")

    assert action_response.status_code == 200
    assert diagnostics_response.status_code == 200
    action = action_response.json()
    diagnostics = diagnostics_response.json()
    decision = next(
        item
        for item in diagnostics["decision_queue"]
        if item["page"] == source_url
    )
    assert decision["source_public_url"] == source_url
    assert decision["final_canonical_url"] == source_url
    assert decision["intended_final_url"] == source_url
    assert "ekologus.dev.proudsite.pl" not in decision["final_canonical_url"]
    assert decision["preview_url"] is None
    assert not any(key.startswith("target_site_") for key in decision)
    assert not any(key.startswith("mapping_review_") for key in decision)
    assert not any(key.startswith("transition_candidate") for key in decision)
    assert decision["inventory_gate_status"] == "missing_inventory_match"
    assert decision["inventory_gate_status_label"] == "brak dopasowania w spisie treści"
    assert decision["canonical_gate_status"] == "blocked_until_inventory_review"
    assert decision["canonical_gate_status_label"] == "zablokowane do sprawdzenia spisu"
    assert decision["duplicate_gate_status"] == "create_blocked_until_duplicate_check"
    assert decision["duplicate_gate_status_label"] == (
        "utworzenie zablokowane do kontroli duplikacji"
    )
    assert decision["decision_type_label"]
    assert decision["blocked_claim_labels"]
    assert "adresu kanonicznego" in decision["content_gate_summary"]
    assert "duplik" in decision["content_gate_summary"]
    assert diagnostics["operator_summary"]["current_site_match_count"] == 1
    assert not any(
        key.startswith("target_site_") for key in diagnostics["operator_summary"]
    )
    preview = next(
        item
        for item in action["payload"]["content_brief_preview"]
        if item["final_canonical_url"] == source_url
    )
    assert preview["source_public_url"] == source_url
    assert preview["final_canonical_url"] == source_url
    assert preview["intended_final_url"] == source_url
    assert preview["preview_url"] is None
    assert not any(key.startswith("target_site_") for key in preview)
    assert not any(key.startswith("mapping_review_") for key in preview)
    assert not any(key.startswith("transition_candidate") for key in preview)


def test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "content_target_alternative_state.sqlite3"),
    )
    monkeypatch.setenv(
        "WILQ_METRIC_DB",
        str(tmp_path / "content_target_alternative.duckdb"),
    )
    source_url = (
        "https://www.ekologus.pl/"
        "remediacja-czym-jest-na-czym-polega-kiedy-jest-wymagana/"
    )
    dev_same_path_url = (
        "https://ekologus.dev.proudsite.pl/"
        "remediacja-czym-jest-na-czym-polega-kiedy-jest-wymagana/"
    )
    alternative_url = (
        "https://ekologus.dev.proudsite.pl/uslugi/ekodokumentacje/"
        "remediacje-monitoring-gruntow-i-wod-podziemnych/"
    )
    normalized_alternative_url = alternative_url.rstrip("/")
    gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_content_dev_ignored_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_gsc_content_dev_ignored_test"],
        metric_summary={"query_page_rows": 1},
        summary="GSC source URL with dev preview alternatives ignored.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_content_dev_ignored_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_content_dev_ignored_test"],
        metric_summary={"content_object_count": 2},
        summary="WordPress inventory with current URL and one dev preview alternative.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=11,
                dimensions={"query": "remediacja co to", "page": source_url},
            ),
            VendorMetricFact(
                name="impressions",
                value=440,
                dimensions={"query": "remediacja co to", "page": source_url},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "post",
                    "content_url": source_url,
                    "status": "publish",
                    "inventory_source": "wordpress_rest",
                    "modified_gmt": "2024-05-01T08:00:00+00:00",
                    "title_or_h1": "Remediacja - czym jest?",
                    "canonical_url": source_url,
                },
            ),
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "uslugi",
                    "content_url": alternative_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                    "modified_gmt": "2025-09-05T09:13:12+00:00",
                    "title_or_h1": (
                        "Remediacje, monitoring gruntów i wód podziemnych"
                    ),
                    "canonical_url": alternative_url,
                },
            ),
        ],
    )

    diagnostics_response = client.get("/api/content/diagnostics")
    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")

    assert diagnostics_response.status_code == 200
    assert action_response.status_code == 200
    diagnostics = diagnostics_response.json()
    decision = next(
        item
        for item in diagnostics["decision_queue"]
        if item["page"] == source_url
    )
    assert decision["source_public_url"] == source_url
    assert decision["final_canonical_url"] == source_url
    assert decision["intended_final_url"] == source_url
    assert not any(key.startswith("target_site_") for key in decision)
    assert not any(key.startswith("mapping_review_") for key in decision)
    assert not any(key.startswith("transition_candidate") for key in decision)
    assert normalized_alternative_url not in str(decision)
    assert dev_same_path_url not in str(decision)
    assert not any(
        key.startswith("target_site_") for key in diagnostics["operator_summary"]
    )

    action = action_response.json()
    preview = next(
        item
        for item in action["payload"]["content_brief_preview"]
        if item["final_canonical_url"] == source_url
    )
    assert preview["source_public_url"] == source_url
    assert preview["final_canonical_url"] == source_url
    assert preview["intended_final_url"] == source_url
    assert not any(key.startswith("target_site_") for key in preview)
    assert not any(key.startswith("mapping_review_") for key in preview)
    assert not any(key.startswith("transition_candidate") for key in preview)
    assert normalized_alternative_url not in str(preview)
    assert dev_same_path_url not in str(preview)
    assert preview["inventory_gate_status"] == "confirmed_current_inventory"
    assert preview["canonical_gate_status"] == "current_url_confirmed"
    assert preview["duplicate_gate_status"] == "refresh_or_merge_required"
    assert "duplik" in preview["content_gate_summary"]
    assert preview["seo_title_direction"]
    assert preview["meta_description_direction"]
    assert preview["schema_direction"]
    assert preview["publication_readiness_status"] == "blocked_until_review"
    assert "legal_factual_review" in preview["publication_blockers"]
    assert "human_confirm_before_wordpress_write" in preview["publication_blockers"]
    assert preview["legal_review_notes"]
    assert preview["brand_voice_notes"]
    assert preview["wordpress_inventory_match"] == "present"
    assert preview["apply_allowed"] is False
    assert preview["api_mutation_ready"] is False


def test_content_action_preview_keeps_dimensioned_decisions_after_newer_aggregate_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_action_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_action.duckdb"))
    older = datetime(2026, 6, 18, 8, 0, tzinfo=UTC)
    newer = older + timedelta(hours=2)
    page = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    gsc_dimensioned_run = ConnectorRefreshRun(
        id="refresh_gsc_action_dimensioned_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=older,
        completed_at=older,
        evidence_ids=["ev_refresh_gsc_action_dimensioned_test"],
        metric_summary={"query_page_rows": 1},
        summary="Dimensioned GSC facts for action preview regression.",
    )
    wordpress_inventory_run = ConnectorRefreshRun(
        id="refresh_wordpress_action_dimensioned_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=older,
        completed_at=older,
        evidence_ids=["ev_refresh_wordpress_action_dimensioned_test"],
        metric_summary={"content_object_count": 1},
        summary="Dimensioned WordPress inventory for action preview regression.",
    )
    noisy_gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_action_noisy_aggregate_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=newer,
        completed_at=newer,
        evidence_ids=["ev_refresh_gsc_action_noisy_aggregate_test"],
        metric_summary={"clicks": 2, "impressions": 200},
        summary="Newer non-query/page GSC facts should not erase action previews.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_dimensioned_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=4,
                dimensions={"query": "bdo co to", "page": page},
            ),
            VendorMetricFact(
                name="impressions",
                value=4429,
                dimensions={"query": "bdo co to", "page": page},
            ),
            VendorMetricFact(
                name="ctr",
                value=0.000903,
                dimensions={"query": "bdo co to", "page": page},
            ),
            VendorMetricFact(
                name="average_position",
                value=9.44,
                dimensions={"query": "bdo co to", "page": page},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_inventory_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "pages",
                    "content_url": page,
                    "status": "publish",
                },
            )
        ],
    )
    metric_store().save_connector_refresh_metrics(
        noisy_gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=index,
                dimensions={"date": f"2026-06-{index % 28 + 1:02d}", "row": str(index)},
            )
            for index in range(160)
        ],
    )

    diagnostics_response = client.get("/api/content/diagnostics")
    assert diagnostics_response.status_code == 200
    diagnostics = diagnostics_response.json()
    assert diagnostics["decision_queue"]
    assert diagnostics["decision_queue"][0]["evidence_ids"]

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert action_response.status_code == 200
    action = action_response.json()
    previews = action["payload"].get("content_brief_preview") or []

    assert previews
    assert previews[0]["preview_contract"] == "content_brief_preview_v1"
    assert previews[0]["candidate_id"].startswith("content_brief_gsc_")
    assert previews[0]["evidence_ids"]
    assert previews[0]["intent"]
    assert previews[0]["content_angle"]
    assert previews[0]["audience"]
    assert previews[0]["key_objections"]
    assert previews[0]["h1_direction"]
    assert previews[0]["h2_direction"]
    assert previews[0]["faq_direction"]
    assert previews[0]["cta_direction"]
    assert previews[0]["internal_link_direction"]
    assert previews[0]["source_facts"]
    assert previews[0]["missing_evidence"]
    assert "gwarancja pozycji" in previews[0]["forbidden_claims"]
    assert previews[0]["apply_allowed"] is False
    assert previews[0]["api_mutation_ready"] is False
    assert "gwarancja pozycji" in previews[0]["blocked_claims"]


def test_content_brief_preview_homepage_candidate_id_is_traceable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    homepage = "https://www.ekologus.pl/"
    homepage_gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_homepage_candidate_id_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_gsc_homepage_candidate_id_test"],
        metric_summary={"query_page_rows": 1},
        summary="Homepage GSC fact for content candidate ID regression.",
    )
    homepage_wordpress_run = ConnectorRefreshRun(
        id="refresh_wp_homepage_candidate_id_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wp_homepage_candidate_id_test"],
        metric_summary={"content_object_count": 1},
        summary="Homepage WordPress inventory fact for content candidate ID regression.",
    )
    metric_store().save_connector_refresh_metrics(
        homepage_gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=6,
                dimensions={"query": "ekologus", "page": homepage},
            ),
            VendorMetricFact(
                name="impressions",
                value=80,
                dimensions={"query": "ekologus", "page": homepage},
            ),
            VendorMetricFact(
                name="ctr",
                value=0.075,
                dimensions={"query": "ekologus", "page": homepage},
            ),
            VendorMetricFact(
                name="average_position",
                value=1.01,
                dimensions={"query": "ekologus", "page": homepage},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        homepage_wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "pages",
                    "content_url": homepage,
                    "status": "publish",
                },
            )
        ],
    )

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")

    assert action_response.status_code == 200
    action = action_response.json()
    previews = action["payload"].get("content_brief_preview") or []
    homepage_preview = next(
        item for item in previews if item.get("final_canonical_url") == homepage
    )
    assert homepage_preview["candidate_id"] == "content_brief_gsc_www_ekologus_pl"
    assert not homepage_preview["candidate_id"].endswith("_")


def test_content_brief_candidate_review_persists_audit_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_review_state.sqlite3"))

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert action_response.status_code == 200
    action = action_response.json()
    candidate = action["payload"]["content_brief_preview"][0]
    candidate_id = candidate["candidate_id"]
    reviewed_url = candidate["final_canonical_url"] or candidate["source_public_url"]

    review_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": f"Wybrano kandydata briefu {candidate_id} do dalszego review.",
            "checked_items": [
                f"candidate:{candidate_id}",
                f"source_type:{candidate['source_type']}",
                f"mode:{candidate['mode']}",
                "url_review_outcome:confirm_final_canonical_url",
                f"reviewed_url:{reviewed_url}",
                "review_notes:operator potwierdzil publiczny URL do dalszego review",
                "draft_readiness_outcome:needs_duplicate_resolution",
                "canonical_review_outcome:canonical_needs_target_confirmation",
                "duplicate_review_outcome:merge_required_before_draft",
                "legal_factual_review_outcome:needs_expert_review",
                "human_review_outcome:prepare_only_review_recorded",
                "draft_readiness_notes:canonical i duplikaty wymagaja dalszego review",
            ],
            "blockers": [
                "payload_apply_allowed_false",
                "wordpress_write_not_requested",
                "blocked_claim:gwarancja pozycji",
            ],
        },
    )

    assert review_response.status_code == 200
    result = review_response.json()
    assert result["status"] == "recorded"
    assert result["audit_event"]["event_type"] == "human_review_approved_for_prepare"
    assert result["review_gate"]["apply_allowed"] is False
    assert result["review_gate"]["last_review_outcome"] == "approved_for_prepare"
    assert f"candidate:{candidate_id}" in result["audit_event"]["summary"]
    assert "url_review_outcome:confirm_final_canonical_url" in result["audit_event"]["summary"]
    assert "reviewed_url:[stored in audit details]" in result["audit_event"]["summary"]
    assert result["audit_event"]["details"]["content_url_review"] == {
        "candidate": candidate_id,
        "url_review_outcome": "confirm_final_canonical_url",
        "reviewed_url": reviewed_url,
        "review_notes": "operator potwierdzil publiczny URL do dalszego review",
    }
    assert result["audit_event"]["details"]["content_draft_readiness_review"] == {
        "candidate": candidate_id,
        "draft_readiness_outcome": "needs_duplicate_resolution",
        "canonical_review_outcome": "canonical_needs_target_confirmation",
        "duplicate_review_outcome": "merge_required_before_draft",
        "legal_factual_review_outcome": "needs_expert_review",
        "human_review_outcome": "prepare_only_review_recorded",
        "draft_readiness_notes": "canonical i duplikaty wymagaja dalszego review",
    }
    assert (
        "Ten krok nie zapisuje zmian w zewnętrznych systemach"
        in result["audit_event"]["summary"]
    )

    audit_response = client.get(
        "/api/audit/events?action_id=act_prepare_content_refresh_queue"
    )
    assert audit_response.status_code == 200
    persisted_audit = audit_response.json()[0]
    assert persisted_audit["event_type"] == "human_review_approved_for_prepare"
    assert f"candidate:{candidate_id}" in persisted_audit["summary"]
    assert persisted_audit["details"]["content_url_review"]["reviewed_url"] == (
        reviewed_url
    )

    reviewed_action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert reviewed_action_response.status_code == 200
    reviewed_action = reviewed_action_response.json()
    draft_previews = reviewed_action["payload"]["wordpress_draft_payload_preview"]
    assert len(draft_previews) == 1
    draft_preview = draft_previews[0]
    assert draft_preview["preview_contract"] == "wordpress_draft_payload_preview_v1"
    assert draft_preview["source_preview_contract"] == "content_brief_preview_v1"
    assert draft_preview["candidate_id"] == candidate_id
    assert draft_preview["intent"]
    assert draft_preview["post_status"] == "draft"
    assert draft_preview["mutation_allowed"] is False
    assert draft_preview["apply_allowed"] is False
    assert draft_preview["api_mutation_ready"] is False
    assert draft_preview["destructive"] is False
    assert (
        draft_preview["content_url_review_recorded_outcome"]
        == "confirm_final_canonical_url"
    )
    assert draft_preview["content_url_review_reviewed_url"] == reviewed_url
    assert draft_preview["content_url_review_notes"] == (
        "operator potwierdzil publiczny URL do dalszego review"
    )
    assert not any(
        key.startswith("target_site_")
        or key.startswith("mapping_review_")
        or key.startswith("transition_candidate")
        for key in draft_preview
    )
    assert "current_transition_candidate_url" not in draft_preview
    assert (
        draft_preview["draft_readiness_review_recorded_outcome"]
        == "needs_duplicate_resolution"
    )
    assert (
        draft_preview["canonical_review_recorded_outcome"]
        == "canonical_needs_target_confirmation"
    )
    assert (
        draft_preview["duplicate_review_recorded_outcome"]
        == "merge_required_before_draft"
    )
    assert draft_preview["legal_factual_review_recorded_outcome"] == "needs_expert_review"

    assert draft_preview["human_review_recorded_outcome"] == "prepare_only_review_recorded"
    assert (
        draft_preview["draft_readiness_review_notes"]
        == "canonical i duplikaty wymagaja dalszego review"
    )
    assert draft_preview["draft_generation_status"] in {
        "blocked_until_content_review",
        "blocked_pending_canonical_duplicate_review",
        "blocked_pending_canonical_duplicate_review_after_url_review",
        "blocked_missing_public_inventory",
        "ready_for_review",
    }
    assert draft_preview["draft_generation_status"] == "blocked_pending_canonical_duplicate_review"
    assert "final_canonical_review" in draft_preview["draft_blockers"]
    assert "duplicate_or_cannibalization_check" in draft_preview["draft_blockers"]
    assert "human_confirm_before_wordpress_write" in draft_preview["draft_blockers"]
    assert draft_preview["inventory_gate_status"]
    assert draft_preview["canonical_gate_status"]
    assert draft_preview["duplicate_gate_status"]
    assert draft_preview["content_gate_summary"]
    assert "spis treści: spis potwierdzony na obecnej stronie" in draft_preview[
        "content_gate_status_summary"
    ]
    assert "URL kanoniczny: obecny URL potwierdzony" in draft_preview[
        "content_gate_status_summary"
    ]
    assert "duplikaty: odśwież albo scal zamiast pisać od nowa" in draft_preview[
        "content_gate_status_summary"
    ]
    draft_contract = draft_preview["draft_generation_contract"]
    assert draft_contract["contract_version"] == "content_draft_generation_v1"
    assert draft_contract["language"] == "pl-PL"
    assert draft_contract["status"] == draft_preview["draft_generation_status"]
    assert draft_contract["allowed_output_kind"] in {
        "outline_only_until_gates_pass",
        "reviewable_polish_draft_preview",
    }
    assert "duplicate_or_cannibalization_check" in draft_contract[
        "requires_passed_gates"
    ]
    assert "publish_ready_claim" in draft_contract["forbidden_outputs"]
    readiness_contract = draft_preview["draft_readiness_review_contract"]
    assert readiness_contract["contract_version"] == "content_draft_readiness_review_v1"
    assert readiness_contract["scope"] == "review_only"
    assert "needs_duplicate_resolution" in readiness_contract["allowed_outcomes"]
    assert "canonical_review_outcome" in readiness_contract["required_fields"]
    assert "wordpress_draft_write" in readiness_contract["blocked_outputs"]
    assert draft_preview["wordpress_draft_handoff_status"] == "blocked_until_draft_gates_pass"
    assert "wordpress_draft_write_not_requested" in draft_preview[
        "wordpress_draft_handoff_blockers"
    ]
    wordpress_draft_contract = draft_preview["wordpress_draft_handoff_contract"]
    assert wordpress_draft_contract["contract_version"] == "wordpress_draft_handoff_v1"
    assert wordpress_draft_contract["scope"] == "blocked_preview_only"
    assert wordpress_draft_contract["final_canonical_url"] == draft_preview["final_canonical_url"]
    assert "target_site_url" not in wordpress_draft_contract
    assert (
        wordpress_draft_contract["required_next_action_contract"]
        == "wordpress_draft_handoff_v1"
    )
    assert "content_draft_readiness_review" in wordpress_draft_contract["requires_passed_gates"]
    assert "wordpress_draft_write" in wordpress_draft_contract["blocked_outputs"]
    measurement_plan = draft_preview["post_publication_measurement_plan"]
    assert (
        measurement_plan["contract_version"]
        == "post_publication_measurement_plan_v1"
    )
    assert measurement_plan["scope"] == "blocked_preview_only"
    assert measurement_plan["final_canonical_url"] == draft_preview["final_canonical_url"]
    assert "target_site_url" not in measurement_plan
    assert measurement_plan["status"] == "blocked_until_publish_and_followup_data"
    assert "google_search_console" in measurement_plan["required_source_connectors"]
    assert "google_analytics_4" in measurement_plan["required_source_connectors"]
    assert "28d_after_publish" in measurement_plan["followup_windows"]
    assert "followup_window_captured" in measurement_plan["requires_before_claims"]
    assert "ranking_gain_claim" in measurement_plan["blocked_outputs"]
    assert "obietnica wzrostu leadów" in measurement_plan["blocked_outputs"]
    assert draft_preview["draft_payload"]["post_status"] == "draft"
    assert draft_preview["draft_payload"]["post_title"]
    assert "human_confirm_before_wordpress_write" in draft_preview[
        "required_validation"
    ]
    assert "gwarancja pozycji" in draft_preview["blocked_claims"]
    assert draft_preview["evidence_ids"]

    preview_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/preview",
        json={"requested_by": "operator_test", "max_items": 12},
    )
    assert preview_response.status_code == 200
    preview_items = preview_response.json()["preview_items"]
    assert any(
        item.get("preview_contract") == "wordpress_draft_payload_preview_v1"
        and item.get("candidate_id") == candidate_id
        for item in preview_items
    )


def test_actions_api_normalizes_legacy_content_review_audit_terms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "legacy_content_review.sqlite3"))

    local_state_store().save_audit_event(
        AuditEvent(
            id="audit_legacy_content_url_review",
            action_id="act_prepare_content_refresh_queue",
            event_type="human_review_approved_for_prepare",
            actor="operator_legacy_review",
            summary=(
                "Wynik review: zatwierdzone. Sprawdzone: "
                "mapping_outcome:confirm_alternative_candidate, "
                "selected_target_url:[stored in audit details], "
                "mapping_notes:target wybrany tylko do review staging handoff."
            ),
            evidence_ids=["ev_refresh_wordpress_content_contract_test"],
            details={
                "review_outcome": "approved_for_prepare",
                "reviewed_by": "operator_legacy_review",
                "checked_items": [
                    "candidate:content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca",
                    "mapping_outcome:confirm_alternative_candidate",
                    "selected_target_url:https://ekologus.dev.proudsite.pl/bdo/",
                    "mapping_notes:target wybrany tylko do review staging handoff",
                    "draft_readiness_outcome:needs_duplicate_resolution",
                ],
                "target_site_mapping_review": {
                    "candidate": "content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca",
                    "mapping_outcome": "confirm_alternative_candidate",
                    "mapping_notes": "target wybrany tylko do review staging handoff",
                    "selected_target_url": "https://ekologus.dev.proudsite.pl/bdo/",
                },
                "content_draft_readiness_review": {
                    "draft_readiness_notes": "staging handoff pozostaje zablokowany",
                },
            },
        )
    )

    response = client.get("/api/actions")

    assert response.status_code == 200
    actions = response.json()
    content_action = next(
        action for action in actions if action["id"] == "act_prepare_content_refresh_queue"
    )
    serialized = json.dumps(content_action, ensure_ascii=False)
    for stale_term in (
        "target_site",
        "mapping_review",
        "mapping_outcome",
        "selected_target_url",
        "staging handoff",
        "ekologus.dev.proudsite.pl",
    ):
        assert stale_term not in serialized
    review = content_action["audit_events"][0]["details"]["content_url_review"]
    assert review["url_review_outcome"] == "needs_public_final_url_review"
    assert "publicznego finalnego URL-a ekologus.pl" in review["review_notes"]
    assert "publicznego finalnego URL-a ekologus.pl" in content_action["audit_events"][0][
        "summary"
    ]


def test_content_strategist_context_pack_preserves_reviewed_draft_preview(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "content_review_context_state.sqlite3"),
    )

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert action_response.status_code == 200
    action = action_response.json()
    candidate = action["payload"]["content_brief_preview"][0]
    candidate_id = candidate["candidate_id"]

    review_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": f"Wybrano propozycję briefu {candidate_id} do context-pack proof.",
            "checked_items": [
                f"candidate:{candidate_id}",
                f"source_type:{candidate['source_type']}",
                f"mode:{candidate['mode']}",
            ],
            "blockers": [
                "payload_apply_allowed_false",
                "wordpress_write_not_requested",
                "blocked_claim:gwarancja pozycji",
            ],
        },
    )
    assert review_response.status_code == 200

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-content-strategist"},
    )

    assert context_response.status_code == 200
    context = context_response.json()
    actions_by_id = {item["id"]: item for item in context["active_action_objects"]}
    content_action = actions_by_id["act_prepare_content_refresh_queue"]
    payload = content_action["payload"]

    assert payload["content_brief_preview_total"] >= 1
    assert payload["content_brief_preview_included"] >= 1
    brief_preview = next(
        item
        for item in payload["content_brief_preview"]
        if item["candidate_id"] == candidate_id
    )
    assert brief_preview["intent"]
    assert brief_preview["content_angle"]
    assert brief_preview["audience"]
    assert brief_preview["h1_direction"]
    assert brief_preview["seo_title_direction"]
    assert brief_preview["meta_description_direction"]
    assert brief_preview["h2_direction"]
    assert brief_preview["faq_direction"]
    assert brief_preview["schema_direction"]
    assert brief_preview["key_objections"]
    assert brief_preview["cta_direction"]
    assert brief_preview["internal_link_direction"]
    assert brief_preview["publication_readiness_status"] == "blocked_until_review"
    assert "legal_factual_review" in brief_preview["publication_blockers"]
    assert "kontrola prawna i faktograficzna" in brief_preview[
        "publication_blocker_labels"
    ]
    assert brief_preview["legal_review_notes"]
    assert brief_preview["brand_voice_notes"]
    assert brief_preview["source_facts"]
    assert brief_preview["missing_evidence"]
    assert brief_preview["metric_snapshot_labels"]["clicks"] == "kliknięcia"
    assert "gwarancja pozycji" in brief_preview["forbidden_claims"]
    assert brief_preview["source_public_url"]
    assert brief_preview["final_canonical_url"]
    assert brief_preview["intended_final_url"]
    assert "ekologus.dev.proudsite.pl" not in brief_preview["final_canonical_url"]
    assert not [
        key
        for key in brief_preview
        if key.startswith(("target_site_", "mapping_review_", "transition_candidate"))
        or key == "current_transition_candidate_url"
    ]
    assert (
        "duplicate_or_cannibalization_check"
        in brief_preview["required_validation"]
    )
    assert "kontrola duplikacji i kanibalizacji" in brief_preview[
        "required_validation_labels"
    ]
    assert "odśwież istniejącą treść" in brief_preview["decision_option_labels"]
    assert payload["wordpress_draft_payload_preview_total"] == 1
    assert payload["wordpress_draft_payload_preview_included"] == 1
    draft_preview = payload["wordpress_draft_payload_preview"][0]
    assert draft_preview["preview_contract"] == "wordpress_draft_payload_preview_v1"
    assert draft_preview["source_preview_contract"] == "content_brief_preview_v1"
    assert draft_preview["candidate_id"] == candidate_id
    assert draft_preview["intent"]
    assert draft_preview["post_status"] == "draft"
    assert draft_preview["draft_payload"]["post_title"].startswith("Odświeżenie:")
    assert any(
        block.get("section_label") == "intencja"
        for block in draft_preview["draft_payload"]["content_blocks"]
    )
    assert draft_preview["source_public_url"]
    assert draft_preview["final_canonical_url"]
    assert draft_preview["intended_final_url"]
    assert not [
        key
        for key in draft_preview
        if key.startswith(("target_site_", "mapping_review_", "transition_candidate"))
        or key == "current_transition_candidate_url"
    ]
    assert draft_preview["draft_generation_status"] in {
        "blocked_until_content_review",
        "blocked_pending_canonical_duplicate_review",
        "blocked_pending_canonical_duplicate_review_after_url_review",
        "blocked_missing_public_inventory",
        "ready_for_review",
    }
    assert draft_preview["inventory_gate_status"]
    assert draft_preview["canonical_gate_status"]
    assert draft_preview["duplicate_gate_status"]
    assert draft_preview["content_gate_summary"]
    draft_contract = draft_preview["draft_generation_contract"]
    assert draft_contract["contract_version"] == "content_draft_generation_v1"
    assert draft_contract["language"] == "pl-PL"
    assert draft_contract["status"] == draft_preview["draft_generation_status"]
    assert draft_contract["allowed_output_kind"] in {
        "outline_only_until_gates_pass",
        "reviewable_polish_draft_preview",
    }
    assert "duplicate_or_cannibalization_check" in draft_contract[
        "requires_passed_gates"
    ]
    assert "publish_ready_claim" in draft_contract["forbidden_outputs"]
    assert "warunek: kontrola duplikacji i kanibalizacji" in draft_preview[
        "draft_generation_summary"
    ]
    assert "zakaz: obietnica gotowości do publikacji" in draft_preview[
        "draft_generation_summary"
    ]
    assert draft_preview["wordpress_draft_handoff_status"] in {
        "blocked_until_draft_gates_pass",
        "blocked_until_draft_readiness_review",
        "blocked_until_wordpress_draft_handoff_action",
    }
    assert "wordpress_draft_write_not_requested" in draft_preview[
        "wordpress_draft_handoff_blockers"
    ]
    assert "zapis szkicu WordPress nie został zlecony" in draft_preview[
        "wordpress_draft_handoff_blocker_labels"
    ]
    assert "blokada: zapis szkicu WordPress nie został zlecony" in draft_preview[
        "wordpress_draft_handoff_summary"
    ]
    wordpress_draft_contract = draft_preview["wordpress_draft_handoff_contract"]
    assert wordpress_draft_contract["contract_version"] == "wordpress_draft_handoff_v1"
    assert wordpress_draft_contract["scope"] == "blocked_preview_only"
    assert "wordpress_publish" in wordpress_draft_contract["blocked_outputs"]
    assert "blokuje: publikacja WordPress" in draft_preview[
        "wordpress_draft_handoff_contract_summary"
    ]
    measurement_plan = draft_preview["post_publication_measurement_plan"]
    assert (
        measurement_plan["contract_version"]
        == "post_publication_measurement_plan_v1"
    )
    assert measurement_plan["scope"] == "blocked_preview_only"
    assert measurement_plan["status"] == "blocked_until_publish_and_followup_data"
    assert "google_search_console" in measurement_plan["required_source_connectors"]
    assert "google_analytics_4" in measurement_plan["required_source_connectors"]
    assert "content_success_verdict" in measurement_plan["blocked_outputs"]
    assert "blokuje: werdykt skuteczności treści" in draft_preview[
        "post_publication_measurement_summary"
    ]
    assert "human_confirm_before_wordpress_write" in draft_preview["draft_blockers"]
    assert "potwierdzenie człowieka przed zapisem WordPress" in draft_preview[
        "draft_blocker_labels"
    ]
    assert "wymaga: wynik decyzji człowieka" in draft_preview[
        "draft_readiness_review_contract_summary"
    ]
    assert (
        "duplicate_or_cannibalization_check"
        in draft_preview["required_validation"]
    )
    assert "kontrola duplikacji i kanibalizacji" in draft_preview[
        "required_validation_labels"
    ]
    assert draft_preview["apply_allowed"] is False
    assert draft_preview["api_mutation_ready"] is False
    assert draft_preview["evidence_ids"]
    assert "gwarancja pozycji" in draft_preview["blocked_claims"]
    assert content_action["review_gate"]["last_review_outcome"] == "approved_for_prepare"


def test_daily_context_pack_preserves_action_preview_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "preview_context_state.sqlite3"),
    )
    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 2},
    )
    assert preview_response.status_code == 200

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )

    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    latest_audit_event = merchant_action["latest_audit_event"]
    assert latest_audit_event["event_type"] == "action_preview_generated"
    assert "szczegóły techniczne są dostępne w szczegółach akcji WILQ" in (
        latest_audit_event["summary"]
    )
    assert "details_keys" not in latest_audit_event
    assert merchant_action["review_gate"]["apply_allowed"] is False


def test_action_confirm_requires_prior_preview(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirm_without_preview.sqlite3"))

    confirm_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Operator tried to confirm without preview.",
            "preview_acknowledged": True,
        },
    )

    assert confirm_response.status_code == 200
    confirmation = confirm_response.json()
    assert confirmation["confirmed"] is False
    assert confirmation["status"] == "blocked"
    assert confirmation["status_label"] == "zablokowany"
    assert "dry_run_preview_required" in confirmation["blockers"]
    assert "wymagany wcześniejszy podgląd zmian" in confirmation["blocker_labels"]
    assert "warunek techniczny do sprawdzenia" not in confirmation["blocker_labels"]
    assert confirmation["audit_event"]["event_type"] == "action_confirmation_blocked"
    assert confirmation["audit_event"]["event_type_label"] == "Potwierdzenie zablokowane"
    assert confirmation["review_gate"]["apply_allowed"] is False
    assert confirmation["review_gate"]["status_label"]

    audit_response = client.get(
        "/api/audit/events?action_id=act_review_merchant_feed_issues"
    )
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "action_confirmation_blocked"


def test_action_confirm_records_preview_confirmation_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "confirm_after_preview.sqlite3"))
    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 2},
    )
    assert preview_response.status_code == 200

    confirm_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Operator confirms the generated preview.",
            "preview_acknowledged": True,
        },
    )

    assert confirm_response.status_code == 200
    confirmation = confirm_response.json()
    assert confirmation["confirmed"] is True
    assert confirmation["status"] == "confirmed"
    assert confirmation["blockers"] == []
    assert confirmation["blocker_labels"] == []
    assert confirmation["audit_event"]["event_type"] == "action_apply_confirmed"
    assert confirmation["audit_event"]["actor"] == "operator_test"
    assert confirmation["review_gate"]["last_confirmation_by"] == "operator_test"
    assert confirmation["review_gate"]["apply_allowed"] is False
    assert "human_confirm_before_apply" not in confirmation["review_gate"]["apply_blockers"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    assert merchant_action["latest_audit_event"]["event_type"] == "action_apply_confirmed"
    assert merchant_action["review_gate"]["last_confirmation_by"] == "operator_test"
    assert merchant_action["review_gate"]["apply_allowed"] is False


def test_action_impact_check_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "impact_without_confirm.sqlite3"))

    response = client.post(
        "/api/actions/act_review_merchant_feed_issues/impact-check",
        json={
            "checked_by": "operator_test",
            "notes": "Impact check before confirmation should block.",
            "pre_window_days": 7,
            "post_window_days": 7,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "blocked"
    assert "action_confirmation_required" in result["blockers"]
    assert "wymagane potwierdzenie podglądu zmian" in result["blocker_labels"]
    assert "warunek techniczny do sprawdzenia" not in result["blocker_labels"]
    assert result["audit_event"]["event_type"] == "action_impact_check_blocked"
    assert "status=" not in result["audit_event"]["summary"]
    assert "google_merchant_center" not in result["audit_event"]["summary"]
    assert result["review_gate"]["last_impact_check_status"] == "blocked"
    assert result["review_gate"]["apply_allowed"] is False
    assert "impact_sanity_check_required" in result["review_gate"]["apply_blockers"]


def test_action_impact_check_records_pre_apply_sanity_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "impact_after_confirm.sqlite3"))
    action_id = "act_review_merchant_feed_issues"
    preview_response = client.post(
        f"/api/actions/{action_id}/preview",
        json={"requested_by": "operator_test", "max_items": 2},
    )
    assert preview_response.status_code == 200
    confirm_response = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Operator confirms the generated preview.",
            "preview_acknowledged": True,
        },
    )
    assert confirm_response.status_code == 200

    response = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={
            "checked_by": "operator_test",
            "notes": "Operator checks pre/post sanity before apply.",
            "pre_window_days": 7,
            "post_window_days": 14,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "checked"
    assert "status=" not in result["audit_event"]["summary"]
    assert "google_merchant_center" not in result["audit_event"]["summary"]
    assert result["pre_window_days"] == 7
    assert result["post_window_days"] == 14
    assert result["metric_fact_count"] > 0
    assert "google_merchant_center" in result["source_connectors"]
    assert result["blocker_labels"] == []
    assert result["audit_event"]["event_type"] == "action_impact_check_completed"
    assert result["review_gate"]["last_impact_check_status"] == "checked"
    assert result["review_gate"]["last_impact_checked_by"] == "operator_test"
    assert result["review_gate"]["apply_allowed"] is False
    assert "impact_sanity_check_required" not in result["review_gate"]["apply_blockers"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id[action_id]
    assert merchant_action["latest_audit_event"]["event_type"] == "action_impact_check_completed"
    assert merchant_action["review_gate"]["last_impact_check_status"] == "checked"
    assert merchant_action["review_gate"]["apply_allowed"] is False


def test_daily_context_pack_preserves_human_review_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "human_review_context_state.sqlite3"),
    )
    review_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/review",
        json={
            "outcome": "needs_changes",
            "reviewed_by": "operator_test",
            "notes": "Brakuje podglądu zmian do zapisu.",
            "checked_items": ["prepare_feed_fix_preview"],
            "blockers": ["payload_apply_allowed_false"],
        },
    )
    assert review_response.status_code == 200

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )

    assert context_response.status_code == 200
    payload = context_response.json()
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    assert merchant_action["review_gate"]["last_review_outcome"] == "needs_changes"
    assert merchant_action["review_gate"]["last_reviewed_by"] == "operator_test"
    assert merchant_action["review_gate"]["apply_allowed"] is False
    serialized = json.dumps(merchant_action, ensure_ascii=False)
    assert "[REDACTED]" not in serialized
    assert "Brakuje podglądu zmian" not in serialized
    assert merchant_action["latest_audit_event"]["event_type"] == "human_review_needs_changes"
    assert "szczegóły techniczne są dostępne w szczegółach akcji WILQ" in (
        merchant_action["latest_audit_event"]["summary"]
    )


def test_google_ads_oauth_repair_action_is_explicit_and_redacted() -> None:
    response = client.get("/api/actions/act_configure_google_ads_env")
    assert response.status_code == 200
    action = response.json()
    serialized = json.dumps(action)

    assert action["title"] == "Odnow Google Ads OAuth refresh token"
    assert action["payload"]["action_type"] == "repair_google_ads_oauth"
    assert action["payload"]["oauth_scope"] == "https://www.googleapis.com/auth/adwords"
    assert "oauth_error=invalid_grant" in action["human_diagnosis"]
    assert "client_secret" in action["payload"]["oauth_client_json_path"]
    assert "GOOGLE_ADS_REFRESH_TOKEN" in action["payload"]["required_env"]
    assert "ya29." not in serialized
    assert "refresh-token" not in serialized.lower()
    assert "client-secret-test" not in serialized


def test_google_ads_business_context_action_is_review_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert ADS_BUSINESS_CONTEXT_ACTION_ID in actions
    assert "act_configure_google_ads_env" not in actions

    action_response = client.get(f"/api/actions/{ADS_BUSINESS_CONTEXT_ACTION_ID}")
    assert action_response.status_code == 200
    action = action_response.json()
    serialized = json.dumps(action)
    assert action["title"] == "Uzupełnij kontekst biznesowy Google Ads"
    assert action["mode"] == "prepare"
    assert action["risk"] == "low"
    assert action["payload"]["action_type"] == "configure_ads_business_context"
    assert action["payload"]["mode"] == "prepare_only"
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False
    assert action["payload"]["missing_read_contracts"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert "WILQ_ADS_PROFIT_MARGIN" in action["payload"]["required_env"]
    assert "WILQ_ADS_TARGET_ROAS" in action["payload"]["alternative_env"][
        "target_roas_or_cpa"
    ]
    assert "WILQ_ADS_TARGET_CPA_MICROS" in action["payload"]["alternative_env"][
        "target_roas_or_cpa"
    ]
    assert "GOOGLE_ADS_REFRESH_TOKEN" not in serialized
    assert "client_secret" not in serialized

    validate_response = client.post(f"/api/actions/{ADS_BUSINESS_CONTEXT_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    validation = validate_response.json()
    assert validation["valid"] is True
    assert validation["errors"] == []

    apply_response = client.post(f"/api/actions/{ADS_BUSINESS_CONTEXT_ACTION_ID}/apply")
    assert apply_response.status_code == 409
    apply_detail = apply_response.json()["detail"]
    assert apply_detail["status"] == "blocked"
    assert apply_detail["applied"] is False
    assert apply_detail["audit_event"]["event_type"] == "apply_confirmation_missing"


def test_google_ads_business_context_allows_empty_preliminary_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_ADS_PROFIT_MARGIN", "0.35")
    monkeypatch.setenv("WILQ_ADS_BUSINESS_GOAL", "lead quality review")
    monkeypatch.setenv("WILQ_ADS_BUDGET_GOAL", "protect current monthly budget")
    monkeypatch.setenv("WILQ_ADS_TARGET_ROAS", "")
    monkeypatch.setenv("WILQ_ADS_TARGET_CPA_MICROS", "")

    response = client.get("/api/ads/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    business_context_contract = payload["business_context_read_contract"]
    assert business_context_contract["status"] == "ready"
    assert business_context_contract["profit_margin"] == 0.35
    assert business_context_contract["business_goal"] == "lead quality review"
    assert business_context_contract["budget_goal"] == "protect current monthly budget"
    assert business_context_contract["target_roas"] is None
    assert business_context_contract["target_cpa_micros"] is None
    assert business_context_contract["allowed_metrics"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
    ]
    assert business_context_contract["business_policy_ids"] == [
        "use_margin_as_context_not_profitability_verdict",
        "align_campaign_review_to_business_goal",
        "honor_human_budget_goal_before_budget_changes",
        "block_target_verdict_until_roas_or_cpa_confirmed",
        "block_target_verdict_until_strategy_review_approved",
    ]
    assert business_context_contract["target_interpretation"][
        "interpretation_contract"
    ] == "ads_business_target_interpretation_v1"
    assert business_context_contract["target_interpretation"]["status"] == "preliminary"
    assert "campaign_review_context" in business_context_contract[
        "target_interpretation"
    ]["allowed_uses"]
    assert "target_kpi_verdict" in business_context_contract["target_interpretation"][
        "blocked_uses"
    ]
    assert business_context_contract["target_interpretation"]["missing_requirements"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert business_context_contract["target_interpretation"]["action_ids"] == [
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]
    assert business_context_contract["target_interpretation"]["apply_allowed"] is False
    assert business_context_contract["target_interpretation"]["destructive"] is False
    strategy_readiness = business_context_contract["strategy_review_readiness_contract"]
    assert strategy_readiness["id"] == "ads_strategy_review_readiness_contract"
    assert strategy_readiness["status"] == "blocked"
    assert strategy_readiness["latest_review_status"] == "missing"
    assert strategy_readiness["latest_review_outcome"] is None
    assert strategy_readiness["apply_allowed"] is False
    assert strategy_readiness["action_ids"] == [ADS_STRATEGY_REVIEW_ACTION_ID]
    assert strategy_readiness["current_context"]["profit_margin"] == 0.35
    assert strategy_readiness["current_context"]["business_goal"] == "lead quality review"
    assert strategy_readiness["current_context"]["budget_goal"] == (
        "protect current monthly budget"
    )
    assert strategy_readiness["current_context"]["target_roas"] is None
    assert strategy_readiness["current_context"]["target_cpa_micros"] is None
    assert strategy_readiness["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert "human_strategy_review" in strategy_readiness["required_validation"]
    assert "ocena opłacalności" in strategy_readiness["blocked_claims"]
    assert business_context_contract["operator_review_gates"] == [
        "human_strategy_review",
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
    ]
    assert business_context_contract["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert "wstępny lokalny kontekst" in business_context_contract["summary"]
    assert "werdykt celu zostaje zablokowany" in business_context_contract["next_step"]

    business_context_section = next(
        section for section in payload["sections"] if section["id"] == "ads_business_context"
    )
    assert business_context_section["status"] == "ready"
    assert business_context_section["action_ids"] == [
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]

    business_context_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_business_context"
    )
    assert business_context_decision["status"] == "ready"
    assert business_context_decision["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert business_context_decision["metric_tiles"] == {
        "braki": 2,
        "blokady": 6,
        "ustawione pola": 3,
        "warunki sprawdzenia": 5,
        "polityki": 5,
    }
    assert business_context_decision["operator_review_gates"] == (
        business_context_contract["operator_review_gates"]
    )
    assert business_context_decision["action_ids"] == [
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert ADS_BUSINESS_CONTEXT_ACTION_ID not in actions
    assert ADS_TARGET_CONFIRMATION_ACTION_ID in actions
    assert ADS_STRATEGY_REVIEW_ACTION_ID in actions

    action_response = client.get(f"/api/actions/{ADS_TARGET_CONFIRMATION_ACTION_ID}")
    assert action_response.status_code == 200
    action = action_response.json()
    assert action["title"] == "Potwierdź docelowy zwrot z reklam albo koszt pozyskania celu dla Ads"
    assert action["mode"] == "prepare"
    assert action["payload"]["action_type"] == "confirm_ads_target_guardrails"
    assert action["payload"]["mode"] == "prepare_only"
    assert action["payload"]["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert action["payload"]["current_context"]["profit_margin"] == 0.35
    assert action["payload"]["current_context"]["business_goal"] == "lead quality review"
    assert action["payload"]["current_context"]["budget_goal"] == "protect current monthly budget"
    assert action["payload"]["current_context"]["target_roas"] is None
    assert action["payload"]["current_context"]["target_cpa_micros"] is None
    assert action["payload"]["target_env_options"]["target_roas_or_cpa"] == [
        "WILQ_ADS_TARGET_ROAS",
        "WILQ_ADS_TARGET_CPA_MICROS",
    ]
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False

    validate_response = client.post(f"/api/actions/{ADS_TARGET_CONFIRMATION_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    strategy_response = client.get(f"/api/actions/{ADS_STRATEGY_REVIEW_ACTION_ID}")
    assert strategy_response.status_code == 200
    strategy_action = strategy_response.json()
    assert strategy_action["payload"]["action_type"] == "record_ads_strategy_review"
    assert strategy_action["payload"]["apply_allowed"] is False
    assert strategy_action["payload"]["destructive"] is False
    strategy_validate_response = client.post(
        f"/api/actions/{ADS_STRATEGY_REVIEW_ACTION_ID}/validate"
    )
    assert strategy_validate_response.status_code == 200
    assert strategy_validate_response.json()["valid"] is True


def test_google_ads_target_guardrail_confirmation_persists_local_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_ADS_PROFIT_MARGIN", "0.35")
    monkeypatch.setenv("WILQ_ADS_BUSINESS_GOAL", "lead quality review")
    monkeypatch.setenv("WILQ_ADS_BUDGET_GOAL", "protect current monthly budget")
    monkeypatch.delenv("WILQ_ADS_TARGET_ROAS", raising=False)
    monkeypatch.delenv("WILQ_ADS_TARGET_CPA_MICROS", raising=False)

    before_response = client.get("/api/ads/diagnostics")
    assert before_response.status_code == 200
    before_payload = before_response.json()
    assert before_payload["business_context_read_contract"]["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert ADS_TARGET_CONFIRMATION_ACTION_ID in before_payload["action_ids"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID in before_payload["action_ids"]

    confirm_response = client.post(
        f"/api/actions/{ADS_TARGET_CONFIRMATION_ACTION_ID}/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Potwierdzam roboczy target zwrotu z reklam 4.2 do sprawdzenia kampanii.",
            "target_roas": 4.2,
        },
    )

    assert confirm_response.status_code == 200
    confirmation = confirm_response.json()
    assert confirmation["confirmed"] is True
    assert confirmation["status"] == "confirmed"
    assert confirmation["blockers"] == []
    assert confirmation["audit_event"]["event_type"] == "ads_target_guardrail_confirmed"
    assert confirmation["review_gate"]["last_confirmation_by"] == "operator_test"
    assert confirmation["review_gate"]["apply_allowed"] is False

    after_response = client.get("/api/ads/diagnostics")
    assert after_response.status_code == 200
    after_payload = after_response.json()
    business_context = after_payload["business_context_read_contract"]
    assert business_context["target_roas"] == 4.2
    assert business_context["target_cpa_micros"] is None
    assert business_context["missing_read_contracts"] == ["human_strategy_review"]
    assert f"local_state:{ADS_TARGET_CONFIRMATION_ACTION_ID}" in business_context[
        "configured_sources"
    ]
    assert business_context["target_interpretation"]["status"] == "preliminary"
    assert "target_roas_review_context" in business_context["target_interpretation"][
        "allowed_uses"
    ]
    assert "budget_apply" in business_context["target_interpretation"]["blocked_uses"]
    assert ADS_TARGET_CONFIRMATION_ACTION_ID not in after_payload["action_ids"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID in after_payload["action_ids"]

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    action_ids = {action["id"] for action in actions_response.json()}
    assert ADS_TARGET_CONFIRMATION_ACTION_ID not in action_ids
    assert ADS_STRATEGY_REVIEW_ACTION_ID in action_ids

    audit_response = client.get(
        f"/api/audit/events?action_id={ADS_TARGET_CONFIRMATION_ACTION_ID}"
    )
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "ads_target_guardrail_confirmed"

    strategy_review_response = client.post(
        f"/api/actions/{ADS_STRATEGY_REVIEW_ACTION_ID}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": "Strategia Ads zatwierdzona do dalszego sprawdzenia bez zapisu zmian.",
            "checked_items": [
                "review_profit_margin_model",
                "review_business_goal",
                "review_target_fit",
            ],
            "blockers": ["apply nadal zablokowany"],
        },
    )
    assert strategy_review_response.status_code == 200
    strategy_review = strategy_review_response.json()
    assert strategy_review["status"] == "recorded"
    assert strategy_review["audit_event"]["event_type"] == "human_review_approved_for_prepare"

    final_response = client.get("/api/ads/diagnostics")
    assert final_response.status_code == 200
    final_payload = final_response.json()
    final_business_context = final_payload["business_context_read_contract"]
    assert final_business_context["missing_read_contracts"] == []
    assert final_business_context["strategy_review_status"] == "approved_for_prepare"
    assert final_business_context["strategy_reviewed_by"] == "operator_test"
    assert f"local_state:{ADS_STRATEGY_REVIEW_ACTION_ID}" in final_business_context[
        "configured_sources"
    ]
    assert final_business_context["target_interpretation"]["status"] == "ready"
    assert "target_roas_review" in final_business_context["target_interpretation"][
        "allowed_uses"
    ]
    assert ADS_STRATEGY_REVIEW_ACTION_ID not in final_payload["action_ids"]


def test_google_ads_keyword_planner_access_blocker_action_is_review_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    blocked_run = ConnectorRefreshRun(
        id="refresh_google_ads_keyword_planner_blocked",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=datetime.now(UTC) + timedelta(seconds=1),
        evidence_ids=["ev_refresh_refresh_google_ads_keyword_planner_blocked"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "campaign_row_count": 1,
            "search_term_row_count": 1,
            "keyword_planner_status": "blocked",
            "keyword_planner_http_status": 403,
            "keyword_planner_blocker": (
                "api_code=403, api_status=PERMISSION_DENIED, "
                "ads_error=authorizationError.DEVELOPER_TOKEN_NOT_APPROVED"
            ),
            "keyword_planner_seed_term_count": 1,
            "keyword_planner_idea_count": 0,
        },
        summary="Google Ads Keyword Planner access blocked seed.",
    )
    local_state_store().save_connector_refresh_run(blocked_run)

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID in actions
    action = actions[KEYWORD_PLANNER_ACCESS_ACTION_ID]
    serialized = json.dumps(action)

    assert action["title"] == "Odblokuj Keyword Planner dla Google Ads"
    assert action["mode"] == "prepare"
    assert action["risk"] == "low"
    assert action["payload"]["action_type"] == "configure_google_ads_keyword_planner_access"
    assert action["payload"]["blocked_api"] == "Keyword Planner"
    assert "DEVELOPER_TOKEN_NOT_APPROVED" in action["payload"]["blocked_reason"]
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False
    assert "rozmiar odbiorców" in action["payload"]["blocked_claims"]
    assert "GOOGLE_ADS_REFRESH_TOKEN" not in serialized
    assert "client_secret" not in serialized

    validate_response = client.post(f"/api/actions/{KEYWORD_PLANNER_ACCESS_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    validation = validate_response.json()
    assert validation["valid"] is True
    assert validation["errors"] == []

    diagnostics_response = client.get("/api/ads/diagnostics")
    assert diagnostics_response.status_code == 200
    diagnostics = diagnostics_response.json()
    keyword_planner_contract = diagnostics["keyword_planner_read_contract"]
    assert keyword_planner_contract["status"] == "blocked"
    assert "keyword_planner_enrichment" in keyword_planner_contract[
        "missing_read_contracts"
    ]
    keyword_planner_section = next(
        section
        for section in diagnostics["sections"]
        if section["id"] == "ads_keyword_planner"
    )
    assert keyword_planner_section["status"] == "blocked"
    assert keyword_planner_section["action_ids"] == [
        KEYWORD_PLANNER_ACCESS_ACTION_ID
    ]
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID in diagnostics["action_ids"]
    sections_by_id = {section["id"]: section for section in diagnostics["sections"]}
    assert sections_by_id["ads_live_data_status"]["action_ids"] == []
    assert sections_by_id["ads_campaign_overview"]["action_ids"] == [
        "act_prepare_ads_campaign_review_queue"
    ]
    assert sections_by_id["ads_search_terms"]["action_ids"] == [
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
    ]
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID not in sections_by_id[
        "ads_live_data_status"
    ]["action_ids"]
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID not in sections_by_id[
        "ads_campaign_overview"
    ]["action_ids"]
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID not in sections_by_id["ads_search_terms"][
        "action_ids"
    ]


def test_metric_backed_prepare_actions_are_evidence_grounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/actions")
    assert response.status_code == 200
    actions = {action["id"]: action for action in response.json()}

    expected_actions = {
        "act_review_merchant_feed_issues": {
            "connector": "google_merchant_center",
            "action_type": "merchant_feed_issue",
            "metric_names": {"issue_product_count"},
        },
        "act_review_ga4_tracking_quality": {
            "connector": "google_analytics_4",
            "action_type": "ga4_tracking_gap",
            "metric_names": {"active_users", "sessions"},
        },
        "act_prepare_content_refresh_queue": {
            "connector": "wordpress_ekologus",
            "action_type": "wordpress_content_refresh",
            "metric_names": {"content_object_count", "clicks", "domain_rating"},
        },
        "act_prepare_wordpress_draft_handoff": {
            "connector": "wordpress_ekologus",
            "action_type": "wordpress_draft_handoff",
            "metric_names": {"content_object_count", "clicks", "domain_rating"},
        },
        "act_prepare_linkedin_social_drafts": {
            "connector": "linkedin",
            "action_type": "linkedin_post_candidate",
            "metric_names": {"clicks", "impressions", "issue_product_count"},
        },
        "act_prepare_facebook_social_drafts": {
            "connector": "facebook",
            "action_type": "facebook_post_candidate",
            "metric_names": {"clicks", "impressions", "issue_product_count"},
        },
    }

    for action_id, expected in expected_actions.items():
        action = actions[action_id]
        assert action["mode"] == "prepare"
        assert action["status"] == "needs_validation"
        assert action["connector"] == expected["connector"]
        assert action["payload"]["action_type"] == expected["action_type"]
        assert action["payload"]["mode"] == "prepare_only"
        assert action["payload"]["destructive"] is False
        assert action["review_gate"]["status"] == "pending_validation"
        assert action["review_gate"]["confirmation_required"] is True
        assert action["review_gate"]["apply_allowed"] is False
        assert "action_validation_required" in action["review_gate"]["apply_blockers"]
        assert "payload_apply_allowed_false" in action["review_gate"]["apply_blockers"]
        assert "wymagane sprawdzenie w WILQ" in action["review_gate"][
            "apply_blocker_labels"
        ]
        assert "podgląd zmian nie pozwala na zapis" in action["review_gate"][
            "apply_blocker_labels"
        ]
        assert action["evidence_ids"]
        for preview_key in (
            "payload_preview",
            "budget_payload_preview",
            "content_brief_preview",
            "wordpress_draft_payload_preview",
        ):
            preview_items = action["payload"].get(preview_key)
            if isinstance(preview_items, dict):
                preview_items = [preview_items]
            if not isinstance(preview_items, list):
                continue
            for preview in preview_items:
                if not isinstance(preview, dict) or not preview.get("required_validation"):
                    continue
                assert preview.get("required_validation_labels"), (
                    action_id,
                    preview_key,
                    preview.get("required_validation"),
                )
                assert not any(
                    "_" in label
                    for label in preview["required_validation_labels"]
                    if isinstance(label, str)
                )
                assert "warunek techniczny do sprawdzenia" not in preview[
                    "required_validation_labels"
                ]
                assert "brak opisu w kontrakcie WILQ" not in preview[
                    "required_validation_labels"
                ]
        if action_id.startswith("act_prepare_") and "social_drafts" in action_id:
            assert action["domain"] == "social"
            assert action["payload"]["source_inputs"]
            assert "candidate_inputs" not in action["payload"]
            assert "no_publishing_without_connector_credentials" in action["payload"][
                "draft_constraints"
            ]
            assert {"ev_connector_linkedin_status", "ev_connector_facebook_status"}.issubset(
                set(action["evidence_ids"])
            )
        if action_id == "act_prepare_content_refresh_queue":
            content_payload = action["payload"]
            assert content_payload["preview_contract"] == "content_brief_preview_v1"
            assert content_payload["apply_allowed"] is False
            assert content_payload["api_mutation_ready"] is False
            assert "target_site_mapping_review_contract" not in content_payload
            url_contract = content_payload["content_url_review_contract"]
            assert url_contract["contract"] == "content_url_preflight_review_v1"
            assert url_contract["scope"] == "review_only"
            assert "confirm_final_canonical_url" in url_contract["allowed_outcomes"]
            assert "potwierdź finalny URL kanoniczny" in url_contract[
                "allowed_outcome_labels"
            ]
            assert "docelowy URL publiczny" in url_contract["required_field_labels"]
            assert "wordpress_publish" in url_contract["blocked_outputs"]
            assert "publikacja WordPress" in url_contract["blocked_output_labels"]
            assert "obietnica braku duplikacji" in url_contract[
                "blocked_output_labels"
            ]
            assert "content_url_preflight_review" in content_payload["required_validation"]
            assert "target_site_mapping_review" not in content_payload["required_validation"]
            assert "content_brief_preview" in content_payload
            assert len(content_payload["content_brief_preview"]) >= 2
            gsc_preview = next(
                item
                for item in content_payload["content_brief_preview"]
                if item["source_type"] == "gsc_query_page"
            )
            assert gsc_preview["mode"] == "refresh"
            assert gsc_preview["wordpress_inventory_match"] == "present"
            assert gsc_preview["metric_snapshot"]["clicks"] == 12
            assert gsc_preview["metric_snapshot"]["impressions"] == 120
            assert gsc_preview["apply_allowed"] is False
            assert "gwarancja pozycji" in gsc_preview["blocked_claims"]
            assert "human_confirm_before_wordpress_write" in gsc_preview[
                "required_validation"
            ]
            ahrefs_preview = next(
                item
                for item in content_payload["content_brief_preview"]
                if item["source_type"] == "ahrefs_gap_review"
            )
            serialized_content_preview = json.dumps(
                content_payload["content_brief_preview"],
                ensure_ascii=False,
            )
        if action_id == "act_prepare_wordpress_draft_handoff":
            wordpress_draft_payload = action["payload"]
            assert wordpress_draft_payload["preview_contract"] == (
                "wordpress_draft_handoff_preview_v1"
            )
            assert wordpress_draft_payload["depends_on_action_id"] == (
                "act_prepare_content_refresh_queue"
            )
            assert "content_draft_readiness_review_v1" in wordpress_draft_payload[
                "required_input_contracts"
            ]
            assert "post_publication_measurement_plan_v1" in wordpress_draft_payload[
                "required_input_contracts"
            ]
            assert wordpress_draft_payload["apply_allowed"] is False
            assert wordpress_draft_payload["api_mutation_ready"] is False
            assert "wordpress_draft_payload_preview" in wordpress_draft_payload[
                "required_validation"
            ]
            assert "wordpress_publish" in wordpress_draft_payload["blocked_claims"]
            assert len(wordpress_draft_payload["payload_preview"]) >= 1
            first_wordpress_draft_preview = wordpress_draft_payload["payload_preview"][0]
            assert first_wordpress_draft_preview["preview_contract"] == (
                "wordpress_draft_handoff_preview_v1"
            )
            assert first_wordpress_draft_preview["operation_type"] == (
                "wordpress_draft_handoff_review"
            )
            assert first_wordpress_draft_preview["apply_allowed"] is False
            assert first_wordpress_draft_preview["api_mutation_ready"] is False
            assert first_wordpress_draft_preview["final_canonical_url"]
            assert "selected_target_url" not in first_wordpress_draft_preview
            assert "mapping_review_status" not in first_wordpress_draft_preview
            assert not any(
                key.startswith("target_site_")
                or key.startswith("mapping_review_")
                or key.startswith("transition_candidate")
                for key in first_wordpress_draft_preview
            )
            wordpress_draft_measurement_plan = first_wordpress_draft_preview[
                "post_publication_measurement_plan"
            ]
            assert (
                wordpress_draft_measurement_plan["contract_version"]
                == "post_publication_measurement_plan_v1"
            )
            assert wordpress_draft_measurement_plan["scope"] == "blocked_preview_only"
            assert "wordpress_ekologus" in wordpress_draft_measurement_plan[
                "required_source_connectors"
            ]
            assert "obietnica wzrostu leadów" in wordpress_draft_measurement_plan["blocked_outputs"]
            assert first_wordpress_draft_preview["canonical_gate_status_label"]
            assert first_wordpress_draft_preview["duplicate_gate_status_label"]
            assert (
                "status: zablokowany do przejścia kontroli szkicu"
                in first_wordpress_draft_preview["wordpress_draft_handoff_summary"]
            )
            assert (
                first_wordpress_draft_preview["required_next_action_label"]
                == "zapis szkicu WordPress"
            )
            assert "potwierdzenie publicznego URL-a" in first_wordpress_draft_preview[
                "required_validation_labels"
            ]
            assert "publikacja WordPress" in first_wordpress_draft_preview[
                "blocked_claim_labels"
            ]
            assert "blokuje: obietnica wzrostu pozycji" in (
                " ".join(
                    first_wordpress_draft_preview[
                        "post_publication_measurement_summary"
                    ]
                )
            )
            assert ahrefs_preview["mode"] == "review"
            assert ahrefs_preview["topic"] == "audyt środowiskowy"
            assert ahrefs_preview["gsc_demand"] == "unknown"
            assert ahrefs_preview["apply_allowed"] is False
            assert "gsc_demand_check" in ahrefs_preview["required_validation"]
            assert ahrefs_preview["evidence_ids"] == ["ev_refresh_refresh_ahrefs_action_test"]
            assert "cuk.pl" not in serialized_content_preview
        metric_names = {str(metric["name"]) for metric in action["metrics"]}
        assert metric_names.issuperset(expected["metric_names"])
        assert "prepare" in json.dumps(action["payload"])
    serialized = json.dumps(response.json(), ensure_ascii=False)
    assert "active_products=12" not in serialized
    assert "disapproved_products=3" not in serialized
    assert "active_users=20" not in serialized
    assert "sessions=30" not in serialized


def test_action_metric_facts_use_latest_batch_read_for_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.actions import service as action_service

    fact = MetricFact(
        name="clicks",
        value=7,
        period="last_28_days",
        source_connector="google_search_console",
        evidence_id="ev_action_latest",
    )
    seen: dict[str, Any] = {}

    class FastMetricStore:
        def list_metric_facts(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("Action candidates must use batched latest metric reads")

        def list_latest_metric_facts_by_connector(
            self,
            *_args: object,
            **_kwargs: object,
        ) -> object:
            raise AssertionError("Action candidates must use connector-specific limits")

        def list_latest_metric_facts_by_connector_limits(
            self,
            connector_limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["connector_limits"] = connector_limits
            return {connector_id: [] for connector_id in connector_limits} | {
                "google_search_console": [fact]
            }

        def list_metric_facts_by_evidence_ids(
            self,
            _evidence_ids: list[str],
        ) -> list[MetricFact]:
            return []

    monkeypatch.setattr(action_service, "metric_store", lambda: FastMetricStore())

    facts = action_service._action_metric_facts()

    assert facts == [fact]
    assert seen["connector_limits"]["google_ads"] == action_service.ACTION_METRIC_FACT_LIMIT
    assert (
        seen["connector_limits"]["google_search_console"]
        == action_service.ACTION_METRIC_FACT_LIMIT
    )


def test_metric_backed_prepare_actions_validate_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    for action_id in (
        "act_review_merchant_feed_issues",
        "act_review_ga4_tracking_quality",
        "act_prepare_content_refresh_queue",
        "act_prepare_linkedin_social_drafts",
        "act_prepare_facebook_social_drafts",
    ):
        validate_response = client.post(f"/api/actions/{action_id}/validate")
        assert validate_response.status_code == 200
        validation = validate_response.json()
        assert validation["valid"] is True
        assert validation["errors"] == []

        apply_response = client.post(f"/api/actions/{action_id}/apply")
        assert apply_response.status_code == 409
        apply_detail = apply_response.json()["detail"]
        assert apply_detail["status"] == "blocked"
        assert apply_detail["applied"] is False
        assert apply_detail["audit_event"]["event_type"] == "apply_confirmation_missing"


def test_daily_context_pack_preserves_action_review_gates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})

    assert response.status_code == 200
    payload = response.json()
    actions = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions["act_review_merchant_feed_issues"]
    assert merchant_action["review_gate"]["status"] == "pending_validation"
    assert merchant_action["review_gate"]["apply_allowed"] is False
    assert "action_validation_required" in merchant_action["review_gate"]["apply_blockers"]
    assert "payload_apply_allowed_false" in merchant_action["review_gate"]["apply_blockers"]
    assert "wymagane sprawdzenie w WILQ" in merchant_action["review_gate"][
        "apply_blocker_labels"
    ]
    assert "podgląd zmian nie pozwala na zapis" in merchant_action["review_gate"][
        "apply_blocker_labels"
    ]
    assert "last_mutation_adapter" not in merchant_action["review_gate"]


def test_action_validation_rejects_unsupported_payload_action_type() -> None:
    action = ActionObject(
        id="bad_payload",
        title="Bad payload",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_1"],
        human_diagnosis="Invalid payload action should fail.",
        recommended_reason="Unsupported connector action.",
        payload={"action_type": "not_supported_by_google_ads", "connector": "google_ads"},
        validation_status="not_validated",
        created_by="test",
    )

    from wilq.actions.service import validate_action

    result = validate_action(action)
    assert not result.valid
    assert "not supported by connector google_ads" in " ".join(result.errors)


def test_command_center_returns_valid_shape() -> None:
    response = client.get("/api/dashboard/command-center")
    assert response.status_code == 200
    data = response.json()
    assert data["strict_instruction"]
    assert data["connector_summary"]["total"] >= 12
    assert data["sections"] == {}
    assert data["demo_script"] == []
    assert data["action_plan"]
    assert data["action_plan"][0]["evidence_ids"]


def test_command_center_endpoint_uses_daily_runtime_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj decyzje.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    calls = {"command_center": 0}

    def fake_command_center() -> CommandCenterResponse:
        calls["command_center"] += 1
        return command

    monkeypatch.setattr(
        "apps.api.wilq_api.main.build_daily_command_center",
        fake_command_center,
    )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    assert response.json()["primary_next_step"] == "Przejrzyj decyzje."
    assert calls == {"command_center": 1}


def test_daily_command_center_does_not_build_full_action_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj decyzje.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        items=[],
    )

    def fail_list_actions() -> list[ActionObject]:
        raise AssertionError("Command Center first-screen path must not build full actions")

    shared_facts: dict[str, list[MetricFact]] = {"google_merchant_center": []}
    seen: dict[str, Any] = {}

    class FakeMetricStore:
        def list_latest_metric_facts_by_connector_limits(
            self,
            limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["metric_limits"] = limits
            return shared_facts

    def fake_tactical_queue(
        use_cache: bool = True,
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
    ) -> TacticalQueueResponse:
        seen["tactical_facts"] = facts_by_connector
        return tactical_queue

    def fake_command_center_response(
        connectors: list[ConnectorStatus] | None = None,
        tactical_queue: TacticalQueueResponse | None = None,
        actions: list[ActionObject] | None = None,
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
        refresh_runs: list[ConnectorRefreshRun] | None = None,
    ) -> CommandCenterResponse:
        seen["response_facts"] = facts_by_connector
        seen["response_refresh_runs"] = refresh_runs
        return command

    monkeypatch.setattr(daily_runtime, "list_actions", fail_list_actions)
    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [])
    monkeypatch.setattr(daily_runtime, "metric_store", lambda: FakeMetricStore())
    monkeypatch.setattr(daily_runtime, "build_tactical_queue", fake_tactical_queue)
    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        fake_command_center_response,
    )

    assert daily_runtime.build_daily_command_center(use_cache=False) == command
    assert seen["tactical_facts"] is shared_facts
    assert seen["response_facts"] is shared_facts
    assert "google_merchant_center" in seen["metric_limits"]


def test_marketing_brief_endpoint_uses_daily_runtime_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = MarketingBrief(
        strict_instruction="Brief z testowego DailyRuntime.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections=[],
        evidence_ids=["ev_test_daily_runtime_brief"],
    )
    calls = {"marketing_brief": 0}

    def fake_marketing_brief() -> MarketingBrief:
        calls["marketing_brief"] += 1
        return brief

    monkeypatch.setattr(
        "apps.api.wilq_api.main.build_daily_marketing_brief",
        fake_marketing_brief,
    )

    response = client.get("/api/marketing/brief")

    assert response.status_code == 200
    assert response.json()["strict_instruction"] == "Brief z testowego DailyRuntime."
    assert response.json()["evidence_ids"] == ["ev_test_daily_runtime_brief"]
    assert calls == {"marketing_brief": 1}


def test_daily_runtime_cache_seconds_default_and_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", raising=False)
    assert daily_runtime._cache_seconds() == 30.0

    monkeypatch.setenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", "7.5")
    assert daily_runtime._cache_seconds() == 7.5

    monkeypatch.setenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", "-1")
    assert daily_runtime._cache_seconds() == 0.0

    monkeypatch.setenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", "invalid")
    assert daily_runtime._cache_seconds() == 30.0


def test_tactical_queue_uses_short_ttl_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import tactical_queue

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_TACTICAL_QUEUE_CACHE_SECONDS", "30")
    tactical_queue.clear_tactical_queue_cache()
    calls = {"build": 0}

    def fake_build(
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
    ) -> TacticalQueueResponse:
        assert facts_by_connector is None
        calls["build"] += 1
        return TacticalQueueResponse(
            strict_instruction=f"cached tactical queue {calls['build']}",
            items=[],
            evidence_ids=[],
            action_ids=[],
        )

    monkeypatch.setattr(tactical_queue, "_build_tactical_queue", fake_build)

    first = tactical_queue.build_tactical_queue()
    second = tactical_queue.build_tactical_queue()
    tactical_queue.clear_tactical_queue_cache()
    third = tactical_queue.build_tactical_queue()

    assert first.strict_instruction == "cached tactical queue 1"
    assert second.strict_instruction == "cached tactical queue 1"
    assert third.strict_instruction == "cached tactical queue 2"
    assert calls == {"build": 2}
    tactical_queue.clear_tactical_queue_cache()


def test_tactical_queue_uses_latest_metric_fact_batch_for_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import tactical_queue

    fact = MetricFact(
        name="clicks",
        value=4,
        period="last_28_days",
        source_connector="google_search_console",
        evidence_id="ev_tactical_latest",
    )
    seen: dict[str, Any] = {}

    class FastMetricStore:
        def list_metric_facts_by_connector(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("Tactical queue must use latest facts without delta windows")

        def list_latest_metric_facts_by_connector(
            self,
            connector_ids: list[str],
            limit_per_connector: int = 100,
        ) -> dict[str, list[MetricFact]]:
            seen["connector_ids"] = connector_ids
            seen["limit_per_connector"] = limit_per_connector
            return {connector_id: [] for connector_id in connector_ids} | {
                "google_search_console": [fact]
            }

        def list_latest_metric_facts_by_connector_limits(
            self,
            connector_limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["connector_limits"] = connector_limits
            return {connector_id: [] for connector_id in connector_limits} | {
                "google_search_console": [fact]
            }

    monkeypatch.setattr(tactical_queue, "metric_store", lambda: FastMetricStore())

    facts = tactical_queue._tactical_metric_facts()

    assert facts == [fact]
    assert "google_search_console" in seen["connector_limits"]
    assert (
        seen["connector_limits"]["wordpress_ekologus"]
        == tactical_queue.WORDPRESS_INVENTORY_FACT_LIMIT
    )


def test_command_center_reuses_batched_localo_facts_before_evidence_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import command_center

    run = ConnectorRefreshRun(
        id="refresh_localo_latest",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        evidence_ids=["ev_refresh_localo_latest"],
        metric_summary={},
        summary="Localo latest facts.",
    )
    fact = MetricFact(
        name="localo_active_place_count",
        value=4,
        period="connector_refresh",
        source_connector="localo",
        evidence_id="ev_refresh_localo_latest",
    )

    class FailingMetricStore:
        def list_metric_facts_by_evidence_ids(self, *_args: object) -> list[MetricFact]:
            raise AssertionError("Command Center must reuse batched Localo facts first")

    monkeypatch.setattr(command_center, "metric_store", lambda: FailingMetricStore())

    assert command_center._localo_metric_facts_for_run(run, [fact]) == [fact]


def test_marketing_brief_aggregates_metric_facts_and_blockers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "brief_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "brief_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ahrefs_domain_rating",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Ahrefs domain rating completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"domain_rating": 24.0, "ahrefs_rank": 6433882},
        ),
    )

    refresh_response = client.post(
        "/api/connectors/ahrefs/refresh",
        json={"mode": "vendor_read", "reason": "marketing brief contract test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/marketing/brief")

    assert response.status_code == 200
    brief = response.json()
    assert brief["language"] == "pl-PL"
    assert "metryki" in brief["strict_instruction"].lower()
    sections = {section["id"]: section for section in brief["sections"]}
    metric_items = sections["what_we_know"]["items"]
    assert any(item["source_connectors"] == ["ahrefs"] for item in metric_items)
    ahrefs_item = next(item for item in metric_items if item["source_connectors"] == ["ahrefs"])
    assert ahrefs_item["evidence_ids"] == refresh_response.json()["evidence_ids"][-1:]
    assert ahrefs_item["metric_facts"]
    blocker_items = sections["what_blocks_us"]["items"]
    assert any(item["source_connectors"] == ["google_ads"] for item in blocker_items)
    assert all(item["source_connectors"] != ["google_sheets"] for item in blocker_items)
    assert all(item["source_connectors"] != ["linkedin"] for item in blocker_items)
    assert all(item["source_connectors"] != ["facebook"] for item in blocker_items)
    assert all(item["source_connectors"] != ["openai_codex"] for item in blocker_items)
    assert all(
        item["kind"] in {"metric", "blocker", "action", "recommendation"}
        for section in sections.values()
        for item in section["items"]
    )


def test_marketing_brief_does_not_turn_successful_reads_into_blockers() -> None:
    connectors = [
        ConnectorStatus(
            id=connector_id,
            label=label,
            status=ConnectorStatusValue.configured,
            configured=True,
            freshness=FreshnessState(state="fresh"),
            capabilities=ConnectorCapability(read=True),
            health_check="configured",
        )
        for connector_id, label in (
            ("google_search_console", "Google Search Console"),
            ("google_analytics_4", "GA4"),
            ("google_merchant_center", "Merchant Center"),
        )
    ]
    refresh_runs = [
        ConnectorRefreshRun(
            id=f"refresh_{connector.id}_success",
            connector_id=connector.id,
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            completed_at=datetime.now(UTC),
            evidence_ids=[f"ev_refresh_{connector.id}_success"],
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"row_count": 10, "total_products": 10776},
            summary=f"{connector.label} read completed.",
        )
        for connector in connectors
    ]

    brief = build_marketing_brief(
        connectors=connectors,
        refresh_runs=refresh_runs,
        actions=[],
    )

    blockers = next(section for section in brief.sections if section.id == "what_blocks_us").items
    assert blockers == []
    assert brief.blocker_count == 0


def test_marketing_brief_exposes_metric_backed_prepare_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/marketing/brief")
    assert response.status_code == 200
    brief = response.json()
    for connector_id in (
        "google_merchant_center",
        "google_analytics_4",
        "google_search_console",
    ):
        item = next(
            item
            for section in brief["sections"]
            if section["id"] == "what_we_know"
            for item in section["items"]
            if connector_id in item["source_connectors"]
        )
        assert item["evidence_ids"]
        assert item["summary"]
    action_items = {
        item["action_ids"][0]: item
        for section in brief["sections"]
        if section["id"] == "safe_next_actions"
        for item in section["items"]
        if item["action_ids"]
    }

    for action_id in (
        "act_review_merchant_feed_issues",
        "act_review_ga4_tracking_quality",
        "act_prepare_content_refresh_queue",
    ):
        assert action_id in brief["action_ids"]
        item = action_items[action_id]
        assert item["evidence_ids"]
        assert item["risk"] in {"low", "medium"}
        assert item["summary"]
        assert item["next_step"]
    assert "act_prepare_linkedin_social_drafts" not in brief["action_ids"]
    assert "act_prepare_facebook_social_drafts" not in brief["action_ids"]
    assert "act_prepare_linkedin_social_drafts" not in action_items
    assert "act_prepare_facebook_social_drafts" not in action_items
    serialized = json.dumps(brief)
    assert "feed/product issues" not in serialized


def test_marketing_tactical_queue_uses_dimensioned_metric_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    queue = response.json()
    assert queue["language"] == "pl-PL"
    assert queue["items"]
    intents = {item["intent"] for item in queue["items"]}
    assert "content_refresh" in intents
    assert "landing_page_quality" in intents
    assert "merchant_feed_triage" in intents
    assert queue["evidence_ids"]
    assert queue["action_ids"]
    assert queue["compact_groups"]
    assert len(queue["compact_groups"]) <= len(queue["items"])
    gsc_groups = [
        group
        for group in queue["compact_groups"]
        if "google_search_console" in group["source_connectors"]
    ]
    assert gsc_groups
    assert any("powiązanych zapytań" in group["diagnosis"] for group in gsc_groups)
    assert all(group["evidence_ids"] for group in queue["compact_groups"])
    assert all(group["blocked_claims"] for group in queue["compact_groups"])
    content_items = [item for item in queue["items"] if item["intent"] == "content_refresh"]
    assert any(item["dimensions"]["wordpress_match"] == "found" for item in content_items)
    assert any(
        item["dimensions"]["wordpress_match_confidence"] == "exact_url"
        for item in content_items
    )
    assert any("wordpress_ekologus" in item["source_connectors"] for item in content_items)
    ga4_items = [item for item in queue["items"] if item["intent"] == "landing_page_quality"]
    assert any(item["dimensions"]["wordpress_match"] == "found" for item in ga4_items)
    assert all("wordpress_match_confidence" in item["dimensions"] for item in ga4_items)
    merchant_items = [item for item in queue["items"] if item["intent"] == "merchant_feed_triage"]
    assert any(item["dimensions"].get("issue_type") == "missing_image" for item in merchant_items)
    assert any(
        item["dimensions"].get("affected_attribute") == "image_link"
        for item in merchant_items
    )
    ahrefs_items = [
        item for item in queue["items"] if item["source_connectors"] == ["ahrefs"]
    ]
    assert ahrefs_items
    assert any(
        item["dimensions"].get("keyword") == "audyt środowiskowy"
        and item["dimensions"].get("gap_type") == "content_gap"
        for item in ahrefs_items
    )
    ahrefs_audit_item = next(
        item
        for item in ahrefs_items
        if item["dimensions"].get("keyword") == "audyt środowiskowy"
    )
    assert ahrefs_audit_item["dimensions"]["gsc_demand"] == "present"
    assert ahrefs_audit_item["dimensions"]["wordpress_inventory_match"] == "present"
    assert "audyt środowiskowy" in ahrefs_audit_item["dimensions"]["gsc_overlap_terms"]
    assert (
        "https://www.ekologus.pl/audyt-srodowiskowy/"
        in ahrefs_audit_item["dimensions"]["wordpress_overlap_urls"]
    )
    assert "GSC" in ahrefs_audit_item["next_step"]
    assert "WordPress" in ahrefs_audit_item["next_step"]
    ahrefs_beczka_item = next(
        item for item in ahrefs_items if item["dimensions"].get("keyword") == "beczka"
    )
    assert ahrefs_beczka_item["dimensions"]["gsc_demand"] == "missing"
    assert ahrefs_beczka_item["dimensions"]["wordpress_inventory_match"] == "missing"
    assert ahrefs_beczka_item["dimensions"]["gsc_overlap_terms"] == ""
    assert ahrefs_beczka_item["dimensions"]["wordpress_overlap_urls"] == ""
    assert all(item["domain"] == "content" for item in ahrefs_items)
    assert all("wzrost ruchu" in item["blocked_claims"] for item in ahrefs_items)
    assert all(
        item["dimensions"].get("competitor_domain") != "cuk.pl"
        for item in ahrefs_items
    )
    for item in queue["items"]:
        assert item["dimensions"]
        assert item["evidence_ids"]
        assert item["source_connectors"]
        assert item["metric_facts"]
        assert item["blocked_claims"]
        assert item["next_step"]


def test_ga4_diagnostics_exposes_landing_quality_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_state.sqlite3"))
    clear_google_service_env(monkeypatch)
    service_account_json = tmp_path / "google_adc.json"
    service_account_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")

    response = client.get("/api/ga4/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["live_data_available"] is True
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["live_data_status_label"] == "metryki GA4 dostępne"
    if payload["latest_refresh"] is not None:
        assert payload["latest_refresh_status_label"] == "zakończony"
    assert payload["landing_group_count"] >= 1
    assert payload["low_engagement_count"] >= 1
    assert payload["wordpress_match_count"] >= 1
    assert payload["freshness_assessment"]["state"] == "fresh"
    assert payload["freshness_assessment"]["state_label"] == "dane świeże"
    assert payload["freshness_assessment"]["requires_refresh"] is False
    assert payload["freshness_assessment"]["stale_after_hours"] == 48
    assert "GA4" in payload["freshness_assessment"]["summary"]
    assert "act_review_ga4_tracking_quality" in payload["action_ids"]
    decision_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    assert decision_by_id
    assert {
        "fix_measurement",
        "review_landing_mapping",
        "review_traffic_quality",
    } & {decision["decision_type"] for decision in decision_by_id.values()}
    assert any(
        "act_review_ga4_tracking_quality" in decision["action_ids"]
        for decision in decision_by_id.values()
    )
    assert all(decision["evidence_ids"] for decision in decision_by_id.values())
    assert all(
        "google_analytics_4" in decision["source_connectors"]
        for decision in decision_by_id.values()
    )
    assert all(decision["next_step"] for decision in decision_by_id.values())
    assert all(decision["status"] in {"ready", "blocked"} for decision in decision_by_id.values())
    assert all(decision["status_label"] for decision in decision_by_id.values())
    assert all(decision["decision_type_label"] for decision in decision_by_id.values())
    assert all(decision["risk_label"] for decision in decision_by_id.values())
    assert all(decision["blocked_claim_labels"] for decision in decision_by_id.values())
    assert all(isinstance(decision["priority"], int) for decision in decision_by_id.values())
    assert all(decision["metric_tiles"] for decision in decision_by_id.values())
    assert any("zaangażowanie" in decision["metric_tiles"] for decision in decision_by_id.values())
    assert all(
        decision["knowledge_card_ids"] == ["card_ga4_behavior_diagnostics_playbook"]
        for decision in decision_by_id.values()
    )
    assert all(
        decision["expert_rule_ids"] == ["ga4_diagnostics_v1"]
        for decision in decision_by_id.values()
    )
    readiness_contract = payload["conversion_readiness_contract"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "ga4_operator_summary"
    assert operator_summary["title"] == "Co marketer ma sprawdzić teraz w jakości ruchu"
    assert operator_summary["top_decision_ids"] == [
        decision["id"]
        for decision in sorted(
            payload["decision_queue"],
            key=lambda decision: (decision["priority"], decision["id"]),
        )[:4]
    ]
    assert operator_summary["measurement_issue_count"] == sum(
        1
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "fix_measurement"
    )
    measurement_decisions = [
        decision
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "fix_measurement"
    ]
    measurement_titles = [decision["title"] for decision in measurement_decisions]
    assert len(measurement_titles) == len(set(measurement_titles))
    assert all(
        decision["landing_page"] in decision["title"]
        or decision["source_medium"] in decision["title"]
        or decision["campaign_name"] in decision["title"]
        for decision in measurement_decisions
    )
    assert operator_summary["wordpress_missing_count"] == sum(
        1
        for decision in payload["decision_queue"]
        if decision.get("wordpress_match") == "missing"
    )
    assert operator_summary["action_ids"] == payload["action_ids"]
    assert operator_summary["conversion_readiness_status"] == readiness_contract["status"]
    assert "zwrot z reklam" in operator_summary["blocked_claims"]
    assert "zwrot z reklam" in operator_summary["blocked_claim_labels"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    sections = {section["id"]: section for section in payload["sections"]}
    assert sections["ga4_landing_behavior"]["status"] == "ready"
    assert sections["ga4_landing_behavior"]["label"] == "Jakość ruchu ze stron wejścia"
    assert sections["ga4_landing_behavior"]["status_label"] == "gotowe"
    assert "zwrot z reklam" in sections["ga4_landing_behavior"]["blocked_claim_labels"]
    assert sections["ga4_landing_behavior"]["tactical_items"]
    assert sections["ga4_landing_behavior"]["tactical_items"][0]["dimensions"][
        "landing_page"
    ] == "/europejski-zielony-lad-co-to-takiego/"
    assert sections["ga4_tracking_readiness"]["status"] == "missing"
    assert sections["ga4_tracking_readiness"]["status_label"] == "brak metryk konwersji"
    assert "spadek konwersji" in sections["ga4_tracking_readiness"]["blocked_claims"]

    assert sections["ga4_action_safety"]["status"] == "ready"
    assert readiness_contract["id"] == "ga4_conversion_readiness_contract"
    assert readiness_contract["status"] == "blocked"
    assert readiness_contract["status_label"] == "blokuje wnioski o konwersjach"
    assert readiness_contract["conversion_like_metric_count"] == 0
    assert readiness_contract["dimensioned_behavior_metric_count"] >= 1
    assert readiness_contract["landing_group_count"] >= 1
    assert readiness_contract["missing_read_contracts"] == [
        "conversion_or_key_event_mapping"
    ]
    assert readiness_contract["missing_read_contract_labels"] == [
        "powiązanie konwersji i zdarzeń kluczowych"
    ]
    assert "powiązanie konwersji" in readiness_contract["next_step"]
    assert "mapowanie konwersji" not in json.dumps(payload, ensure_ascii=False)
    assert {
        "conversions",
        "key_events",
        "purchase_revenue",
        "total_revenue",
        "transactions",
    }.issubset(set(readiness_contract["allowed_metrics"]))
    assert "współczynnik konwersji" in readiness_contract["blocked_claims"]
    assert "act_review_ga4_tracking_quality" in readiness_contract["action_ids"]
    assert readiness_contract["evidence_ids"]
    assert payload["blocker_count"] >= 1
    assert payload["decision_blocker_count"] == sum(
        1 for decision in payload["decision_queue"] if decision["status"] == "blocked"
    )

    action_response = client.get("/api/actions/act_review_ga4_tracking_quality")
    assert action_response.status_code == 200
    ga4_action = action_response.json()
    assert ga4_action["payload"]["preview_contract"] == "ga4_tracking_quality_review_v1"
    preview = ga4_action["payload"]["payload_preview"][0]
    assert preview["preview_contract"] == "ga4_tracking_quality_review_v1"
    assert preview["operation_type"] == "tracking_quality_review"
    assert preview["metric_snapshot_labels"]["active_users"] == "aktywni użytkownicy"
    assert preview["metric_snapshot_labels"]["engagement_rate"] == "zaangażowanie"
    assert "review_conversion_or_key_event_mapping" in preview["required_validation"]
    assert preview["apply_allowed"] is False
    assert preview["api_mutation_ready"] is False
    assert preview["destructive"] is False

    validation_response = client.post(
        "/api/actions/act_review_ga4_tracking_quality/validate",
        json={},
    )
    assert validation_response.status_code == 200
    assert validation_response.json()["valid"] is True

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-ga4-analyst"})
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_ga4 = context_payload["ga4_diagnostics"]
    assert context_ga4["evidence_ids"] == payload["evidence_ids"]
    assert context_ga4["action_ids"] == payload["action_ids"]
    assert context_ga4["conversion_readiness_contract"] == readiness_contract
    assert ga4_decision_trace(context_ga4["decision_queue"]) == ga4_decision_trace(
        payload["decision_queue"]
    )
    context_action_by_id = {
        action["id"]: action for action in context_payload["active_action_objects"]
    }
    context_preview = context_action_by_id["act_review_ga4_tracking_quality"]["payload"][
        "payload_preview"
    ][0]
    assert context_preview["preview_contract"] == "ga4_tracking_quality_review_v1"
    assert context_preview["metric_snapshot_labels"]["active_users"] == "aktywni użytkownicy"
    assert context_preview["apply_allowed"] is False
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "google_adc.json" not in serialized


def test_ga4_operator_summary_uses_conversion_ready_copy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_ready_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_ready_metrics.duckdb"))
    facts = [
        MetricFact(
            name="active_users",
            value=12,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_ready_conversion",
            dimensions={
                "landing_page": "/oferta/",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
        MetricFact(
            name="key_events",
            value=0,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_ready_conversion",
            dimensions={
                "landing_page": "/oferta/",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
        MetricFact(
            name="purchase_revenue",
            value=0,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_ready_conversion",
            dimensions={
                "landing_page": "/oferta/",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
    ]

    payload = build_ga4_diagnostics(tactical_items=[], actions=[], metric_facts=facts)

    assert payload.conversion_readiness_contract.status == "ready"
    assert payload.conversion_readiness_contract.conversion_like_metric_count == 2
    assert "Brak metryk konwersji" not in payload.operator_summary.summary
    assert "metryki konwersji" in payload.operator_summary.summary
    assert "zwrot z reklam" in payload.operator_summary.blocked_claims


def test_ga4_diagnostics_preserves_dimensioned_landing_facts_after_aggregate_noise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_wide_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_wide_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)
    service_account_json = tmp_path / "google_adc.json"
    service_account_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")
    landing_path = "/europejski-zielony-lad-co-to-takiego/"
    landing_url = f"https://www.ekologus.pl{landing_path}"
    homepage_path = "/"
    homepage_url = "https://www.ekologus.pl/"
    completed_at = datetime(2026, 6, 23, 8, 0, tzinfo=UTC)
    ga4_dimensioned_run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_wide_dimensioned_test",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_analytics_4_wide_dimensioned_test"],
        completed_at=completed_at,
        metric_summary={},
        vendor_data_collected=True,
        summary="GA4 wide dimensioned test seed.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_ga4_wide_match_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_ga4_wide_match_test"],
        metric_summary={"content_object_count": 1},
        vendor_data_collected=True,
        summary="WordPress GA4 wide match seed.",
    )
    local_state_store().save_connector_refresh_run(ga4_dimensioned_run)
    local_state_store().save_connector_refresh_run(wordpress_run)
    metric_store().save_connector_refresh_metrics(
        ga4_dimensioned_run,
        detailed_facts=[
            *[
                VendorMetricFact(
                    name="noise_metric",
                    value=index,
                    dimensions={"aaa_noise": f"{index:03d}"},
                )
                for index in range(350)
            ],
            VendorMetricFact(
                name="active_users",
                value=41,
                dimensions={
                    "landing_page": landing_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=54,
                dimensions={
                    "landing_page": landing_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="engagement_rate",
                value=0.12,
                dimensions={
                    "landing_page": landing_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="active_users",
                value=80,
                dimensions={
                    "landing_page": homepage_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=100,
                dimensions={
                    "landing_page": homepage_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="engagement_rate",
                value=0.42,
                dimensions={
                    "landing_page": homepage_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": landing_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            ),
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": homepage_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            )
        ],
    )

    response = client.get("/api/ga4/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["wordpress_match_count"] >= 1
    decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["landing_page"] == landing_path
    )
    assert decision["wordpress_match"] == "found"
    assert decision["wordpress_match_confidence"] == "path_fallback"
    assert decision["wordpress_content_url"] == landing_url
    homepage_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["landing_page"] == homepage_path
    )
    assert homepage_decision["wordpress_match"] == "found"
    assert homepage_decision["wordpress_match_confidence"] == "path_fallback"
    assert homepage_decision["wordpress_content_url"] == homepage_url


def test_ga4_diagnostics_marks_stale_refresh_as_stale_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_stale_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_stale_metrics.duckdb"))
    completed_at = datetime.now(UTC) - timedelta(hours=72)
    run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_stale_test",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=completed_at,
        evidence_ids=["ev_refresh_refresh_google_analytics_4_stale_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"active_users": 20, "sessions": 30},
        summary="GA4 stale diagnostics seed.",
    )
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name="active_users",
                value=20,
                dimensions={
                    "landing_page": "/oferta/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Test",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=30,
                dimensions={
                    "landing_page": "/oferta/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Test",
                },
            ),
        ],
    )

    response = client.get("/api/ga4/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    freshness = payload["freshness_assessment"]
    assert freshness["state"] == "stale"
    assert freshness["requires_refresh"] is True
    assert freshness["stale_after_hours"] == 48
    assert freshness["latest_refresh_id"] == "refresh_google_analytics_4_stale_test"
    assert freshness["age_hours"] >= 72
    assert "do odświeżenia" in freshness["summary"]
    assert "odczyt danych GA4" in freshness["next_step"]
    assert "odświeżenia" in payload["operator_summary"]["summary"]


def test_ga4_measurement_decision_titles_include_reporting_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")
    facts = [
        MetricFact(
            name="active_users",
            value=179,
            period="last_7_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_not_set",
            dimensions={
                "landing_page": "(not set)",
                "source_medium": "(not set)",
                "campaign_name": "(not set)",
            },
        ),
        MetricFact(
            name="active_users",
            value=89,
            period="last_7_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_organic",
            dimensions={
                "landing_page": "(not set)",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
    ]

    payload = build_ga4_diagnostics(tactical_items=[], actions=[], metric_facts=facts)

    decisions = [
        decision
        for decision in payload.decision_queue
        if decision.decision_type == "fix_measurement"
    ]
    titles = [decision.title for decision in decisions]
    assert titles == [
        "GA4: napraw pomiar - (not set) / (not set)",
        "GA4: napraw pomiar - (not set) / google / organic",
    ]


def test_command_center_exposes_polish_operator_brief(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    assert "WILQ pokazuje tylko metryki" in payload["strict_instruction"]
    assert payload["primary_next_step"].startswith("Najpierw")
    assert payload["tactical_item_count"] >= 3
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    assert {
        "daily_ads_status",
        "daily_merchant_feed",
        "daily_content_queue",
        "daily_ga4_landing_quality",
    }.issubset(brief_by_id)
    assert brief_by_id["daily_ads_status"]["status"] == "blocked"
    assert "act_configure_google_ads_env" in brief_by_id["daily_ads_status"]["action_ids"]
    assert brief_by_id["daily_merchant_feed"]["metric_tiles"]["zgłoszenia"] == 3
    assert brief_by_id["daily_merchant_feed"]["metric_tiles"]["decyzje"] >= 1
    assert "act_review_merchant_feed_issues" in brief_by_id["daily_merchant_feed"]["action_ids"]
    assert brief_by_id["daily_content_queue"]["title"] == (
        "Content: kolejka SEO z GSC i WordPress"
    )
    assert "WordPress potwierdza istniejącą stronę" in brief_by_id[
        "daily_content_queue"
    ]["summary"]
    assert "ahrefs" in brief_by_id["daily_content_queue"]["source_connectors"]
    assert "ev_refresh_refresh_ahrefs_action_test" in brief_by_id[
        "daily_content_queue"
    ]["evidence_ids"]
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["zapytania/URL"] >= 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["decyzje"] >= 2
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["ocena Ahrefs"] == 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["luki Ahrefs"] == 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["wyświetlenia"] >= 1
    assert "query/page" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "WP match" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "Ahrefs review" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "link gaps" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "act_prepare_content_refresh_queue" in brief_by_id["daily_content_queue"]["action_ids"]
    assert brief_by_id["daily_ga4_landing_quality"]["status"] == "blocked"
    assert "pomiar i jakość ruchu" in brief_by_id["daily_ga4_landing_quality"]["title"]
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["grupy ruchu"] >= 1
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["decyzje"] >= 1
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["brakujące dane"] == 1
    assert "zwrot z reklam" in brief_by_id[
        "daily_ga4_landing_quality"
    ]["blocked_claims"]
    assert (
        "act_review_ga4_tracking_quality"
        in brief_by_id["daily_ga4_landing_quality"]["action_ids"]
    )
    assert all(item["evidence_ids"] for item in payload["operator_brief"])
    assert payload["demo_script"] == []
    plan_by_id = {item["id"]: item for item in payload["action_plan"]}
    assert plan_by_id["plan_review_merchant_feed_issues"]["route"] == "/merchant"
    assert plan_by_id["plan_review_merchant_feed_issues"]["skill_id"] == (
        "wilq-merchant-feed-operator"
    )
    assert "Użyj skilla wilq-merchant-feed-operator" in plan_by_id[
        "plan_review_merchant_feed_issues"
    ]["codex_prompt"]
    assert plan_by_id["plan_review_merchant_feed_issues"]["codex_context_endpoint"] == (
        "/api/codex/context-pack"
    )
    assert plan_by_id["plan_prepare_content_refresh_queue"]["route"] == "/content-planner"
    assert plan_by_id["plan_prepare_content_refresh_queue"]["skill_id"] == (
        "wilq-content-strategist"
    )
    assert plan_by_id["plan_review_ga4_landing_quality"]["route"] == "/ga4"
    assert plan_by_id["plan_review_ga4_landing_quality"]["skill_id"] == "wilq-ga4-analyst"
    assert plan_by_id["plan_review_ga4_landing_quality"]["status"] == "blocked"
    assert "pomiar i jakość ruchu" in plan_by_id["plan_review_ga4_landing_quality"]["title"]
    assert "decyzji GA4 do sprawdzenia" in plan_by_id[
        "plan_review_ga4_landing_quality"
    ]["why_it_matters"]
    assert "propozycję przeglądu GA4 w WILQ" in plan_by_id[
        "plan_review_ga4_landing_quality"
    ]["operator_action"]
    assert "Zapis zmian wymaga sprawdzenia" in plan_by_id[
        "plan_review_ga4_landing_quality"
    ]["operator_action"]
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["status"] == "blocked"
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["skill_id"] == (
        "wilq-ads-doctor"
    )
    assert "wydatki reklamowe" in plan_by_id[
        "plan_fix_ads_oauth_before_spend_analysis"
    ]["blocked_claims"]
    decisions_by_id = {item["id"]: item for item in payload["daily_decisions"]}
    assert len(decisions_by_id) <= 4
    assert "decision_review_localo_visibility_facts" not in decisions_by_id
    assert "decision_finish_localo_access_before_local_visibility" not in decisions_by_id
    assert {
        "decision_review_merchant_feed_issues",
        "decision_prepare_content_refresh_queue",
        "decision_review_ga4_landing_quality",
    }.issubset(decisions_by_id)
    assert set(decisions_by_id) == {
        item_id.replace("plan_", "decision_", 1)
        for item_id in plan_by_id
        if "localo" not in item_id
    }
    merchant_decision = decisions_by_id["decision_review_merchant_feed_issues"]
    assert merchant_decision["domain"] == "merchant"
    assert merchant_decision["freshness"]["state"] in {"fresh", "stale", "unknown", "missing"}
    assert merchant_decision["decision_state"] in {
        "ready",
        "stale",
        "blocked",
        "missing",
        "unknown",
    }
    if merchant_decision["freshness"]["state"] == "stale":
        assert merchant_decision["decision_state"] == "stale"
    assert "Świeżość źródeł decyzji" in merchant_decision["freshness"]["notes"]
    assert merchant_decision["co_widzimy"].startswith("Merchant Center ma")
    assert merchant_decision["priority_label"] == "najpierw"
    assert merchant_decision["decision_state_label"] in {
        "gotowe",
        "do odświeżenia",
        "zablokowane",
        "brak danych",
        "nieznane",
    }
    assert merchant_decision["route_label"] == "Merchant"
    assert merchant_decision["cta_label"] == "Otwórz Merchant"
    assert merchant_decision["source_connector_labels"]
    assert merchant_decision["evidence_summary"].endswith("śladów w WILQ") or (
        merchant_decision["evidence_summary"].endswith("ślad w WILQ")
    )
    assert merchant_decision["action_summary"].endswith("akcja do sprawdzenia") or (
        merchant_decision["action_summary"].endswith("akcji do sprawdzenia")
    )
    assert merchant_decision["blocked_claim_labels"]
    assert merchant_decision["skill_label"] == "feed Merchant"
    assert merchant_decision["metric_tiles"]["produkty"] == 10900
    assert merchant_decision["metric_tiles"]["zgłoszenia"] == 3
    assert merchant_decision["metric_tiles"]["decyzje"] >= 1
    assert merchant_decision["metric_facts"]
    assert len(merchant_decision["metric_facts"]) <= 8
    assert {
        fact["source_connector"] for fact in merchant_decision["metric_facts"]
    } == {"google_merchant_center"}
    assert "status=ready" not in merchant_decision["co_widzimy"]
    for decision in decisions_by_id.values():
        assert "Źródła=" not in decision["co_widzimy"]
        assert "dowody=" not in decision["co_widzimy"]
        assert "akcje=" not in decision["co_widzimy"]
    assert merchant_decision["dlaczego_to_ma_znaczenie"] == plan_by_id[
        "plan_review_merchant_feed_issues"
    ]["why_it_matters"]
    assert merchant_decision["why_it_matters"] == plan_by_id[
        "plan_review_merchant_feed_issues"
    ]["why_it_matters"]
    assert merchant_decision["bezpieczny_next_step"] == plan_by_id[
        "plan_review_merchant_feed_issues"
    ]["operator_action"]
    assert merchant_decision["operator_action"] == plan_by_id[
        "plan_review_merchant_feed_issues"
    ]["operator_action"]
    assert merchant_decision["skill_id"] == "wilq-merchant-feed-operator"
    assert "Użyj skilla wilq-merchant-feed-operator" in merchant_decision["codex_prompt"]
    assert merchant_decision["evidence_ids"]
    assert merchant_decision["blocked_claims"]
    ga4_decision = decisions_by_id["decision_review_ga4_landing_quality"]
    content_decision = decisions_by_id["decision_prepare_content_refresh_queue"]
    assert content_decision["domain"] == "content"
    assert "act_prepare_content_refresh_queue" in content_decision["action_ids"]
    assert "act_prepare_wordpress_draft_handoff" in content_decision["action_ids"]
    content_fact_sources = {
        fact["source_connector"] for fact in content_decision["metric_facts"]
    }
    assert {"google_search_console", "ahrefs"}.issubset(content_fact_sources)
    content_ahrefs_facts = [
        fact
        for fact in content_decision["metric_facts"]
        if fact["source_connector"] == "ahrefs"
    ]
    assert content_ahrefs_facts
    assert all(
        fact["dimensions"].get("competitor_domain") != "cuk.pl"
        for fact in content_ahrefs_facts
    )
    assert all(
        "prawo jazdy" not in fact["dimensions"].get("keyword", "")
        for fact in content_ahrefs_facts
    )
    if "decision_review_ads_campaign_metrics" in decisions_by_id:
        assert decisions_by_id["decision_review_ads_campaign_metrics"]["domain"] == "google_ads"
    assert ga4_decision["status"] == "blocked"
    assert ga4_decision["decision_state"] == "blocked"
    assert ga4_decision["domain"] == "ga4"
    assert "pomiar i jakość ruchu" in ga4_decision["title"]
    assert ga4_decision["metric_tiles"]["grupy ruchu"] >= 1
    assert ga4_decision["metric_tiles"]["decyzje"] >= 1
    assert "grup stron wejścia, źródeł ruchu i kampanii" in ga4_decision[
        "co_widzimy"
    ]
    assert "Blokada oznacza" in ga4_decision["co_widzimy"]
    assert "Status blocked" not in ga4_decision["co_widzimy"]
    assert "brak kontraktu" not in ga4_decision["co_widzimy"]
    assert ga4_decision["co_widzimy"].count("Blokada oznacza") == 1
    operator_guidance_text = "\n".join(
        [
            *[item["next_step"] for item in payload["operator_brief"] if item["next_step"]],
            *[item["operator_action"] for item in payload["action_plan"]],
            *[item["bezpieczny_next_step"] for item in payload["daily_decisions"]],
        ]
    )
    assert "`act_" not in operator_guidance_text
    assert "act_review_ga4_tracking_quality" not in operator_guidance_text
    assert "act_confirm_ads_target_guardrails" not in operator_guidance_text

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    context_command = context_response.json()["command_center"]
    assert "operator_brief" not in context_command
    assert "action_plan" not in context_command
    assert "demo_script" not in context_command
    assert [
        {
            "id": item["id"],
            "domain": item["domain"],
            "decision_state": item["decision_state"],
            "freshness_state": item["freshness"]["state"],
            "metric_fact_count": len(item["metric_facts"]),
            "route": item["route"],
            "status": item["status"],
            "why_it_matters": item["why_it_matters"],
            "operator_action": item["operator_action"],
            "source_connectors": item["source_connectors"],
            "evidence_ids": item["evidence_ids"],
            "action_ids": item["action_ids"],
            "blocked_claims": item["blocked_claims"],
            "skill_id": item["skill_id"],
        }
        for item in context_command["daily_decisions"]
    ] == [
        {
            "id": item["id"],
            "domain": item["domain"],
            "decision_state": item["decision_state"],
            "freshness_state": item["freshness"]["state"],
            "metric_fact_count": len(item["metric_facts"]),
            "route": item["route"],
            "status": item["status"],
            "why_it_matters": item["why_it_matters"],
            "operator_action": item["operator_action"],
            "source_connectors": item["source_connectors"],
            "evidence_ids": item["evidence_ids"],
            "action_ids": item["action_ids"],
            "blocked_claims": item["blocked_claims"],
            "skill_id": item["skill_id"],
        }
        for item in payload["daily_decisions"]
    ]
    assert context_command["primary_next_step"] == payload["primary_next_step"]


def test_command_center_ads_plan_uses_live_review_queues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    ads_item = brief_by_id["daily_ads_status"]
    assert ads_item["status"] == "ready"
    assert ads_item["title"] == "Ads: kolejki budżetu, rekomendacji i zapytań"
    assert ads_item["priority"] == 16
    assert ads_item["metric_tiles"]["kampanie"] == 1
    assert ads_item["metric_tiles"]["zapytania"] == 1
    assert ads_item["metric_tiles"]["kliknięcia"] == 12
    assert ads_item["metric_tiles"]["wyświetlenia"] == 120
    assert ads_item["metric_tiles"]["koszt"] == "12 PLN"
    assert "koszt_micros" not in ads_item["metric_tiles"]
    assert ads_item["metric_tiles"]["konwersje"] == 1
    assert ads_item["metric_tiles"]["wartość konwersji"] == "150 PLN"
    assert ads_item["metric_tiles"]["podgląd budżetu"] == 1
    assert ads_item["metric_tiles"]["rekomendacje"] == 1
    assert ads_item["metric_tiles"]["wskaźniki do sprawdzenia"] == 1
    assert ads_item["metric_tiles"]["wiersze kosztu pozyskania celu"] == 1
    assert ads_item["metric_tiles"]["wiersze zwrotu z reklam"] == 1
    assert "kolejki oceny" in ads_item["summary"]
    assert "kliknięcia=12" in ads_item["summary"]
    assert "koszt=12 PLN" in ads_item["summary"]
    assert "konwersje=1" in ads_item["summary"]
    assert "wskaźniki do sprawdzenia=1" in ads_item["summary"]
    assert "Wskaźniki są sygnałem" in ads_item["summary"]
    assert "Zapis zmian wymaga sprawdzenia" in ads_item["next_step"]
    assert "apply" not in ads_item["next_step"]
    assert "wskaźniki kampanii" in ads_item["next_step"]
    assert "zmiana budżetu" in ads_item["blocked_claims"]
    assert "koszt pozyskania celu" in ads_item["blocked_claims"]
    assert "zwrot z reklam" in ads_item["blocked_claims"]
    assert "opłacalność" in ads_item["blocked_claims"]
    assert "zmarnowany budżet" in ads_item["blocked_claims"]
    assert "propozycje wykluczeń" not in ads_item["blocked_claims"]
    assert "act_prepare_ads_campaign_review_queue" in ads_item["action_ids"]
    assert "act_prepare_google_ads_recommendation_review_queue" in ads_item["action_ids"]
    assert "act_review_demand_gen_readiness" not in ads_item["action_ids"]
    assert "act_review_ads_search_term_ngrams" not in ads_item["action_ids"]
    assert ADS_TARGET_CONFIRMATION_ACTION_ID not in ads_item["action_ids"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID not in ads_item["action_ids"]
    ads_business_item = brief_by_id["daily_ads_business_context"]
    assert ads_business_item["status"] == "blocked"
    assert ads_business_item["priority"] == 18
    assert "kontekstu biznesowego" in ads_business_item["title"]
    assert ads_business_item["metric_tiles"]["braki"] == 5
    assert ads_business_item["metric_tiles"]["marża"] == "brak"
    assert ads_business_item["metric_tiles"]["cel biznesowy"] == "brak"
    assert "opłacalność" in ads_business_item["blocked_claims"]
    assert "zmarnowany budżet" in ads_business_item["blocked_claims"]
    assert ads_business_item["action_ids"] == [ADS_BUSINESS_CONTEXT_ACTION_ID]

    plan_by_id = {item["id"]: item for item in payload["action_plan"]}
    ads_plan = plan_by_id["plan_review_ads_campaign_metrics"]
    assert ads_plan["status"] == "ready"
    assert ads_plan["title"] == "Przejrzyj aktualny odczyt Ads bez zapisu zmian"
    assert "kliknięcia=12" in ads_plan["why_it_matters"]
    assert "koszt=12 PLN" in ads_plan["why_it_matters"]
    assert "konwersje=1" in ads_plan["why_it_matters"]
    assert "wartość konwersji=150 PLN" in ads_plan["why_it_matters"]
    assert "wskaźniki do sprawdzenia=1" in ads_plan["why_it_matters"]
    assert "ocena opłacalności" in ads_plan["why_it_matters"]
    assert "aktualny odczyt" in ads_plan["operator_action"]
    assert "podgląd budżetów" in ads_plan["operator_action"]
    assert "wskaźniki kampanii" in ads_plan["operator_action"]
    assert "nie zapisuj zmian" in ads_plan["operator_action"]
    assert "Użyj skilla wilq-ads-doctor" in ads_plan["codex_prompt"]
    assert "zablokowanymi obietnicami" in ads_plan["expected_codex_output"]
    assert ads_plan["blocked_claims"] == ads_item["blocked_claims"]
    ads_business_plan = plan_by_id["plan_ads_business_context_before_budget_decisions"]
    assert ads_business_plan["status"] == "blocked"
    assert ads_business_plan["title"] == (
        "Uzupełnij kontekst biznesowy Ads przed decyzjami budżetowymi"
    )
    assert "marży, celu biznesowego" in ads_business_plan["why_it_matters"]
    assert "WILQ_ADS_PROFIT_MARGIN" in ads_business_plan["operator_action"]
    assert "rentowności" in ads_business_plan["codex_prompt"]
    assert ads_business_plan["blocked_claims"] == ads_business_item["blocked_claims"]
    assert ads_business_plan["action_ids"] == [ADS_BUSINESS_CONTEXT_ACTION_ID]

    decisions_by_id = {item["id"]: item for item in payload["daily_decisions"]}
    ads_decision = decisions_by_id["decision_review_ads_campaign_metrics"]
    assert ads_decision["metric_tiles"]["podgląd budżetu"] == 1
    assert ads_decision["metric_tiles"]["rekomendacje"] == 1
    assert ads_decision["metric_tiles"]["wskaźniki do sprawdzenia"] == 1
    assert ads_decision["metric_tiles"]["wiersze kosztu pozyskania celu"] == 1
    assert ads_decision["metric_tiles"]["wiersze zwrotu z reklam"] == 1
    assert "podgląd budżetu=1" in ads_decision["co_widzimy"]
    assert "wskaźniki do sprawdzenia=1" in ads_decision["co_widzimy"]
    assert "kolejki oceny" in ads_decision["co_widzimy"]
    assert "kosztu pozyskania celu, zwrotu z reklam i zmarnowanego budżetu" in ads_decision[
        "co_widzimy"
    ]
    assert ads_decision["action_ids"] == ads_item["action_ids"]
    assert ads_decision["blocked_claims"] == ads_item["blocked_claims"]
    assert "decision_ads_business_context_before_budget_decisions" not in decisions_by_id
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "wzrost konwersji" not in serialized
    assert "target CPA" not in serialized
    assert "werdykt target CPA" not in serialized
    assert "werdykt target zwrotu z reklam" not in serialized
    assert "ocena zwrotu z reklam" not in serialized

    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    sections_by_id = {section["id"]: section for section in brief_response.json()["sections"]}
    blockers = sections_by_id["what_blocks_us"]
    blocker_titles = {item["title"] for item in blockers["items"]}
    assert "Ads: brakuje kontekstu biznesowego do decyzji budżetowych" in blocker_titles
    blocker_action_ids = {
        action_id for item in blockers["items"] for action_id in item["action_ids"]
    }
    assert ADS_BUSINESS_CONTEXT_ACTION_ID in blocker_action_ids


def test_command_center_ads_daily_card_filters_deep_ads_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from wilq.briefing import command_center

    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    def ads_action(action_id: str) -> ActionObject:
        return ActionObject(
            id=action_id,
            title=f"Ads action {action_id}",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=["ev_refresh_refresh_google_ads_command_center_live"],
            human_diagnosis="Ads action test.",
            recommended_reason="Review only.",
            payload={"action_type": action_id},
            validation_status="not_validated",
            created_by="test",
        )

    item = command_center._ads_item_from_facts(
        metric_store().list_metric_facts("google_ads", limit=100),
        [
            ads_action("act_review_demand_gen_readiness"),
            ads_action("act_prepare_ads_campaign_review_queue"),
            ads_action("act_prepare_google_ads_recommendation_review_queue"),
            ads_action("act_review_ads_search_term_ngrams"),
            ads_action("act_prepare_custom_segments_from_search_terms"),
            ads_action("act_prepare_negative_keyword_review_queue"),
            ads_action(ADS_TARGET_CONFIRMATION_ACTION_ID),
            ads_action(ADS_STRATEGY_REVIEW_ACTION_ID),
        ],
    )

    assert item.status == "ready"
    assert item.action_ids == [
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
    ]


def test_command_center_ads_totals_use_latest_refresh_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_summary_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_summary_metrics.duckdb"))
    completed_at = datetime.now(UTC)
    run = ConnectorRefreshRun(
        id="refresh_google_ads_summary_totals",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=completed_at,
        evidence_ids=["ev_refresh_refresh_google_ads_summary_totals"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "row_count": 18,
            "search_term_row_count": 50,
            "clicks": 117,
            "impressions": 2968,
            "cost_micros": 154049650,
            "conversions": 2.0,
            "conversion_value": 2.0,
            "customer_currency_code": "PLN",
            "budgeted_campaign_count": 18,
            "recommendation_row_count": 4,
        },
        summary="Google Ads summary totals seed.",
    )
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name="search_term_clicks",
                value=7,
                dimensions={
                    "campaign_id": "101",
                    "campaign_name": "Brand Search",
                    "ad_group_id": "202",
                    "ad_group_name": "BDO",
                    "search_term": "odpady cena",
                    "search_term_status": "NONE",
                },
            ),
        ],
    )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    ads_item = brief_by_id["daily_ads_status"]
    assert ads_item["status"] == "ready"
    assert ads_item["metric_tiles"]["kampanie"] == 18
    assert ads_item["metric_tiles"]["zapytania"] == 50
    assert ads_item["metric_tiles"]["kliknięcia"] == 117
    assert ads_item["metric_tiles"]["wyświetlenia"] == 2968
    assert ads_item["metric_tiles"]["koszt"] == "154.05 PLN"
    assert ads_item["metric_tiles"]["konwersje"] == 2
    assert ads_item["metric_tiles"]["wartość konwersji"] == "2 PLN"
    assert ads_item["metric_tiles"]["podgląd budżetu"] == 18
    assert ads_item["metric_tiles"]["rekomendacje"] == 4
    assert "kampanie=18" in ads_item["summary"]
    assert "koszt=154.05 PLN" in ads_item["summary"]


def test_command_center_merchant_uses_latest_refresh_issue_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_latest_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_latest_metrics.duckdb"))
    older_run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_older",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=datetime.now(UTC) - timedelta(hours=1),
        evidence_ids=["ev_refresh_refresh_google_merchant_center_older"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"total_products": 100, "item_level_issue_count": 99},
        summary="Older Merchant seed.",
    )
    latest_run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_latest",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=datetime.now(UTC),
        evidence_ids=["ev_refresh_refresh_google_merchant_center_latest"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"total_products": 10900, "item_level_issue_count": 23},
        summary="Latest Merchant seed.",
    )
    for run, issue_count in ((older_run, 99), (latest_run, 23)):
        local_state_store().save_connector_refresh_run(run)
        metric_store().save_connector_refresh_metrics(
            run,
            detailed_facts=[
                VendorMetricFact(name="total_products", value=10900),
                VendorMetricFact(
                    name="issue_product_count",
                    value=issue_count,
                    dimensions={
                        "issue_type": "availability_updated",
                        "affected_attribute": "n:availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                    },
                ),
            ],
        )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    merchant_item = brief_by_id["daily_merchant_feed"]
    assert merchant_item["status"] == "ready"
    assert merchant_item["metric_tiles"]["produkty"] == 10900
    assert merchant_item["metric_tiles"]["zgłoszenia"] == 23
    assert merchant_item["metric_tiles"]["decyzje"] == 1
    assert "zgłoszenia=23" in merchant_item["summary"]
    assert "decyzje=1" in merchant_item["summary"]
    assert "ev_refresh_refresh_google_merchant_center_latest" in merchant_item[
        "evidence_ids"
    ]
    assert "ev_refresh_refresh_google_merchant_center_older" not in merchant_item[
        "evidence_ids"
    ]


def test_command_center_merchant_decision_count_matches_grouped_issue_decisions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_grouped_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_grouped_metrics.duckdb"))
    latest_run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_grouped",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=datetime.now(UTC),
        evidence_ids=["ev_refresh_refresh_google_merchant_center_grouped"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"total_products": 10900, "item_level_issue_count": 15},
        summary="Latest Merchant grouped seed.",
    )
    local_state_store().save_connector_refresh_run(latest_run)
    issue_dimensions = {
        "issue_type": "missing_potentially_required_attribute",
        "affected_attribute": "n:unit_pricing_measure",
        "country": "PL",
        "severity": "NOT_IMPACTED",
        "resolution": "MERCHANT_ACTION",
    }
    metric_store().save_connector_refresh_metrics(
        latest_run,
        detailed_facts=[
            VendorMetricFact(name="total_products", value=10900),
            VendorMetricFact(
                name="issue_product_count",
                value=892,
                dimensions={**issue_dimensions, "reporting_context": "ALL_CONTEXTS"},
            ),
            VendorMetricFact(
                name="issue_product_count",
                value=446,
                dimensions={**issue_dimensions, "reporting_context": "FREE_LISTINGS"},
            ),
            VendorMetricFact(
                name="issue_product_count",
                value=446,
                dimensions={**issue_dimensions, "reporting_context": "SHOPPING_ADS"},
            ),
        ],
    )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    merchant_item = brief_by_id["daily_merchant_feed"]
    assert merchant_item["metric_tiles"]["typy problemów"] == 1
    assert merchant_item["metric_tiles"]["decyzje"] == 1
    assert "decyzje=1" in merchant_item["summary"]


def test_command_center_uses_ga4_metric_facts_without_ga4_tactical_items(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_command_center.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_command_center.duckdb"))
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_google_analytics_4_command_center_fallback",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_analytics_4_command_center_fallback"],
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"active_users": 10, "sessions": 12},
            summary="GA4 command center fallback metric seed.",
        ),
        detailed_facts=[
            VendorMetricFact(
                name="active_users",
                value=10,
                dimensions={
                    "landing_page": "/ga4-fallback/",
                    "source_medium": "google / organic",
                    "campaign_name": "(organic)",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=12,
                dimensions={
                    "landing_page": "/ga4-fallback/",
                    "source_medium": "google / organic",
                    "campaign_name": "(organic)",
                },
            ),
            VendorMetricFact(
                name="active_users",
                value=8,
                dimensions={
                    "landing_page": "(not set)",
                    "source_medium": "(not set)",
                    "campaign_name": "(not set)",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=8,
                dimensions={
                    "landing_page": "(not set)",
                    "source_medium": "(not set)",
                    "campaign_name": "(not set)",
                },
            ),
        ],
    )
    empty_tactical_queue = TacticalQueueResponse(
        strict_instruction="test tactical queue intentionally empty",
    )
    monkeypatch.setattr(
        "wilq.briefing.daily_runtime.build_tactical_queue",
        lambda **_kwargs: empty_tactical_queue,
    )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    ga4_item = brief_by_id["daily_ga4_landing_quality"]
    assert ga4_item["status"] == "blocked"
    assert "pomiar i jakość ruchu" in ga4_item["title"]
    assert ga4_item["metric_tiles"]["grupy ruchu"] == 2
    assert ga4_item["metric_tiles"]["decyzje"] == 2
    assert ga4_item["metric_tiles"]["pomiar"] == 1
    assert ga4_item["metric_tiles"]["jakość ruchu"] == 1
    assert "GA4 ma 2 grup" in ga4_item["summary"]
    assert "1 problemów pomiaru" in ga4_item["summary"]
    assert "1 decyzji jakości ruchu" in ga4_item["summary"]
    assert (
        "ev_refresh_refresh_google_analytics_4_command_center_fallback"
        in ga4_item["evidence_ids"]
    )
    assert "grupy ruchu=0" not in json.dumps(payload, ensure_ascii=False)


def test_command_center_ga4_uses_visible_decision_cap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_decision_cap.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_decision_cap.duckdb"))
    facts: list[VendorMetricFact] = []
    for index in range(8):
        facts.append(
            VendorMetricFact(
                name="active_users",
                value=10 + index,
                dimensions={
                    "landing_page": f"/landing-{index}/",
                    "source_medium": "google / organic",
                    "campaign_name": "(organic)",
                },
            )
        )
    for index in range(2):
        facts.append(
            VendorMetricFact(
                name="active_users",
                value=5 + index,
                dimensions={
                    "landing_page": "(not set)",
                    "source_medium": "(not set)",
                    "campaign_name": f"missing-{index}",
                },
            )
        )
    metric_store().save_connector_refresh_metrics(
        ConnectorRefreshRun(
            id="refresh_google_analytics_4_command_center_cap",
            connector_id="google_analytics_4",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_refresh_refresh_google_analytics_4_command_center_cap"],
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"active_users": 100},
            summary="GA4 command center decision cap seed.",
        ),
        detailed_facts=facts,
    )
    monkeypatch.setattr(
        "wilq.briefing.daily_runtime.build_tactical_queue",
        lambda **_kwargs: TacticalQueueResponse(strict_instruction="empty tactical queue"),
    )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    ga4_item = {
        item["id"]: item for item in payload["operator_brief"]
    }["daily_ga4_landing_quality"]
    assert ga4_item["metric_tiles"]["grupy ruchu"] == 10
    assert ga4_item["metric_tiles"]["decyzje"] == 6
    assert ga4_item["metric_tiles"]["pomiar"] == 2
    assert ga4_item["metric_tiles"]["jakość ruchu"] == 4
    assert "2 problemów pomiaru" in ga4_item["summary"]
    assert "4 decyzji jakości ruchu" in ga4_item["summary"]


def test_command_center_demotes_localo_access_ready_without_visibility_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_command.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "localo_command.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")
    localo_run = ConnectorRefreshRun(
        id="refresh_localo_access_ready_test",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_localo_access_ready_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "api": "localo_mcp_oauth_probe",
            "mcp_initialize_status": 200,
            "authorization_code_supported": 1,
            "pkce_s256_supported": 1,
            "access_token_present": 1,
        },
        summary="Localo Test dostępu completed with local OAuth access token.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().status()

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    assert "daily_localo_readiness" not in brief_by_id
    plan_by_id = {item["id"]: item for item in payload["action_plan"]}
    assert "plan_localo_access_ready_wait_for_visibility_facts" not in plan_by_id
    assert "plan_finish_localo_access_before_local_visibility" not in plan_by_id


def test_command_center_keeps_localo_access_blocker_in_primary_brief(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_blocker_command.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "localo_blocker_command.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    metric_store().status()

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    brief_by_id = {item["id"]: item for item in payload["operator_brief"]}
    localo_brief = brief_by_id["daily_localo_readiness"]
    assert localo_brief["status"] == "blocked"
    assert "brak dostępu" in localo_brief["title"]
    assert localo_brief["metric_tiles"]["dostęp Localo"] == 0


def test_localo_diagnostics_shows_access_ready_without_visibility_claims(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_diag_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "localo_diag.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")
    localo_run = ConnectorRefreshRun(
        id="refresh_localo_access_ready_diag_test",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_localo_access_ready_diag_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "api": "localo_mcp_oauth_probe",
            "mcp_initialize_status": 200,
            "authorization_code_supported": 1,
            "pkce_s256_supported": 1,
            "access_token_present": 1,
        },
        summary="Localo Test dostępu completed with local OAuth access token.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().save_connector_refresh_metrics(localo_run)

    response = client.get("/api/localo/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "zakończony"
    assert payload["access_probe"]["status"] == "access_ready"
    assert payload["access_probe"]["status_label"] == "dostęp działa"
    assert payload["access_probe"]["mcp_initialize_status"] == 200
    assert payload["access_probe"]["authorization_code_supported_label"] == "tak"
    assert payload["access_probe"]["pkce_s256_supported_label"] == "tak"
    assert payload["access_probe"]["access_token_present_label"] == "obecny"
    assert payload["live_data_available"] is False
    assert payload["visibility_fact_count"] == 0
    assert payload["evidence_ids"] == ["ev_refresh_refresh_localo_access_ready_diag_test"]
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    access_decision = decision_by_id["localo_access_ready_wait_for_visibility_facts"]
    assert access_decision["status"] == "ready"
    assert access_decision["status_label"] == "gotowe"
    assert access_decision["decision_type_label"] == "status źródła"
    assert access_decision["access_status_label"] == "dostęp działa"
    assert access_decision["priority_label"] == "wysoki priorytet"
    assert access_decision["priority"] == 30
    assert access_decision["metric_tiles"] == {
        "dostęp Localo": 1,
        "dane Localo": 0,
        "brakujące dane": 5,
    }
    assert "local_rankings" in access_decision["missing_read_contracts"]
    assert "rankingi lokalne" in access_decision["missing_read_contract_labels"]
    assert "potwierdzenie dostępu Localo" in access_decision["allowed_evidence_labels"]
    assert "wyniki profilu firmy w Google" in access_decision["blocked_claims"]
    assert "wyniki profilu firmy w Google" in access_decision["blocked_claim_labels"]
    block_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert block_decision["status"] == "blocked"
    assert block_decision["status_label"] == "zablokowane"
    assert block_decision["decision_type_label"] == "blokada obietnic"
    assert block_decision["priority_label"] == "wysoki priorytet"
    assert block_decision["priority"] == 10
    assert block_decision["metric_tiles"] == {
        "blokady obietnic": 5,
        "brakujące dane": 5,
    }
    assert "poprawa widoczności lokalnej" in block_decision["blocked_claims"]
    assert all(fact["name"] != "mcp_initialize_status" for fact in block_decision["metric_facts"])
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "localo_operator_summary"
    assert operator_summary["title"] == "Co marketer ma wiedzieć o Localo"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["access_status"] == "access_ready"
    assert operator_summary["access_status_label"] == "dostęp działa"
    assert operator_summary["visibility_fact_count"] == 0
    assert "local_rankings" in operator_summary["missing_read_contracts"]
    assert "rankingi lokalne" in operator_summary["missing_read_contract_labels"]
    assert "localo" in operator_summary["source_connectors"]
    assert "ev_refresh_refresh_localo_access_ready_diag_test" in operator_summary["evidence_ids"]
    assert "wyniki profilu firmy w Google" in operator_summary["blocked_claims"]
    assert "wyniki profilu firmy w Google" in operator_summary["blocked_claim_labels"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "localo-access-test" not in serialized
    assert "localo-token-test" not in serialized

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-localo-operator"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["localo_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
    assert context_payload["localo_diagnostics"]["decision_queue"][0]["id"] in decision_by_id
    assert "marketing_brief" not in context_payload


def test_localo_diagnostics_exposes_partial_visibility_contracts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_value_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "localo_value.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")
    localo_run = ConnectorRefreshRun(
        id="refresh_localo_value_diag_test",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_localo_value_diag_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "api": "localo_mcp_oauth_probe",
            "mcp_initialize_status": 200,
            "authorization_code_supported": 1,
            "pkce_s256_supported": 1,
            "access_token_present": 1,
            "localo_active_place_count": 4,
            "localo_tracked_keyword_count": 23,
            "localo_avg_visibility_current": 52.8261,
            "localo_reviews_count": 793,
        },
        summary="Odczyt danych Localo zakończony agregatami.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().save_connector_refresh_metrics(
        localo_run,
        detailed_facts=[
            VendorMetricFact(
                "localo_active_place_count",
                4,
                {"contract": "place_inventory", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_tracked_keyword_count",
                23,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_avg_visibility_current",
                52.8261,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_reviews_count",
                793,
                {"contract": "reviews", "scope": "active_places"},
                period="localo_mcp_read",
            ),
        ],
    )
    for index in range(30):
        later_probe_run = ConnectorRefreshRun(
            id=f"refresh_localo_later_probe_{index}",
            connector_id="localo",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.blocked,
            evidence_ids=[f"ev_refresh_refresh_localo_later_probe_{index}"],
            external_call_attempted=True,
            vendor_data_collected=False,
            metric_summary={
                "api": "localo_mcp_oauth_probe",
                "mcp_initialize_status": 401,
                "authorization_code_supported": 1,
                "pkce_s256_supported": 1,
                "access_token_present": 1,
            },
            errors=["Localo OAuth authorization is incomplete."],
            summary="Późniejszy test dostępu Localo nie przeszedł po udanym odczycie agregatów.",
        )
        local_state_store().save_connector_refresh_run(later_probe_run)
        metric_store().save_connector_refresh_metrics(later_probe_run)

    response = client.get("/api/localo/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is True
    assert payload["visibility_fact_count"] == 4
    assert payload["action_ids"] == [LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    review_decision = decision_by_id["localo_review_visibility_facts"]
    assert review_decision["status"] == "ready"
    assert review_decision["status_label"] == "gotowe"
    assert review_decision["decision_type_label"] == "przejrzyj widoczność"
    assert review_decision["access_status_label"] == "dostęp działa"
    assert review_decision["action_ids"] == [LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    assert review_decision["allowed_evidence"] == [
        "place_inventory",
        "local_rankings",
        "reviews",
    ]
    assert review_decision["missing_read_contracts"] == [
        "gbp_visibility",
        "competitor_visibility",
        "local_tasks",
    ]
    assert review_decision["missing_read_contract_labels"] == [
        "widoczność profilu firmy w Google",
        "widoczność konkurencji",
        "zadania lokalne",
    ]
    contract_status_by_id = {
        item["id"]: item for item in payload["read_contract_statuses"]
    }
    assert contract_status_by_id["place_inventory"]["status"] == "ready"
    assert contract_status_by_id["place_inventory"]["id_label"] == "lista lokalizacji"
    assert contract_status_by_id["place_inventory"]["status_label"] == "gotowe"
    assert contract_status_by_id["local_rankings"]["status"] == "ready"
    assert (
        contract_status_by_id["local_rankings"]["metric_fact_labels"][
            "localo_tracked_keyword_count"
        ]
        == "monitorowane frazy"
    )
    assert contract_status_by_id["reviews"]["status"] == "ready"
    assert contract_status_by_id["gbp_visibility"]["status"] == "missing"
    assert contract_status_by_id["gbp_visibility"]["status_label"] == "brak danych"
    assert contract_status_by_id["gbp_visibility"]["blocked_claims"] == [
        "wyniki profilu firmy w Google",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert contract_status_by_id["gbp_visibility"]["blocked_claim_labels"] == [
        "wyniki profilu firmy w Google",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert contract_status_by_id["competitor_visibility"]["status"] == "missing"
    assert contract_status_by_id["competitor_visibility"]["blocked_claims"] == [
        "widoczności konkurencji",
        "poprawa widoczności lokalnej",
    ]
    assert contract_status_by_id["local_tasks"]["status"] == "missing"
    assert contract_status_by_id["local_tasks"]["blocked_claims"] == [
        "ukończone zadanie lokalne",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert review_decision["read_contract_statuses"] == payload["read_contract_statuses"]
    assert review_decision["metric_tiles"]["miejsca"] == 4
    assert review_decision["metric_tiles"]["frazy"] == 23
    assert review_decision["metric_tiles"]["średnia widoczność"] == 52.8261
    assert review_decision["metric_tiles"]["recenzje"] == 793
    assert "lokalne rankingi" not in review_decision["blocked_claims"]
    assert "wyniki profilu firmy w Google" in review_decision["blocked_claims"]
    assert "widoczności konkurencji" in review_decision["blocked_claims"]
    assert review_decision["knowledge_card_ids"] == ["card_localo_local_seo_playbook"]
    assert review_decision["expert_rule_ids"] == [
        "local_visibility_v1",
        "local_reviews_v1",
    ]
    operator_summary = payload["operator_summary"]
    assert operator_summary["visibility_fact_count"] == 4
    assert "agregaty widoczności" in operator_summary["summary"]
    assert "Przejrzyj agregaty Localo" in operator_summary["next_step"]
    assert "dopóki odczyt danych Localo nie dostarczy danych widoczności" not in (
        operator_summary["next_step"]
    )
    blocked_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert blocked_decision["metric_tiles"]["brakujące dane"] == 3
    assert blocked_decision["title"] == (
        "Blokuj profil firmy w Google, konkurencję i zadania lokalne bez pełnych danych Localo"
    )
    assert "bez danych Localo" not in blocked_decision["title"]
    assert "Przejrzyj dostępne agregaty Localo" in blocked_decision["next_step"]
    assert "Najpierw dodaj odczyt danych Localo" not in blocked_decision["next_step"]
    section_by_id = {section["id"]: section for section in payload["sections"]}
    assert section_by_id["localo_visibility_contract"]["action_ids"] == [
        LOCALO_VISIBILITY_REVIEW_ACTION_ID
    ]
    assert section_by_id["localo_visibility_contract"]["status_label"] == "gotowe"
    assert all(fact["source_connector"] == "localo" for fact in review_decision["metric_facts"])
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "localo-access-test" not in serialized
    assert "localo-token-test" not in serialized

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions_by_id = {action["id"]: action for action in actions_response.json()}
    localo_action = actions_by_id[LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    assert localo_action["connector"] == "localo"
    assert localo_action["mode"] == "prepare"
    assert localo_action["risk"] == "low"
    assert localo_action["payload"]["action_type"] == "local_visibility_task"
    assert localo_action["payload"]["apply_allowed"] is False
    assert localo_action["payload"]["destructive"] is False
    assert localo_action["payload"]["preview_contract"] == (
        "local_visibility_review_preview_v1"
    )
    assert localo_action["payload"]["payload_preview"][0]["preview_contract"] == (
        "local_visibility_review_preview_v1"
    )
    localo_preview = localo_action["payload"]["payload_preview"][0]
    assert localo_preview["operation_type"] == "local_visibility_review"
    assert localo_preview["metric_snapshot"]["localo_active_place_count"] == 4
    assert localo_preview["metric_snapshot"]["localo_tracked_keyword_count"] == 23
    assert localo_preview["allowed_contracts"] == [
        "place_inventory",
        "local_rankings",
        "reviews",
    ]
    assert localo_preview["missing_read_contracts"] == [
        "gbp_visibility",
        "competitor_visibility",
        "local_tasks",
    ]
    assert localo_preview["apply_allowed"] is False
    assert localo_preview["api_mutation_ready"] is False
    assert localo_preview["destructive"] is False
    assert "gbp_visibility" in localo_action["payload"]["missing_read_contracts"]
    assert "local_visibility_task" in json.dumps(localo_action, ensure_ascii=False)
    assert "localo-access-test" not in json.dumps(localo_action, ensure_ascii=False)

    validate_response = client.post(
        f"/api/actions/{LOCALO_VISIBILITY_REVIEW_ACTION_ID}/validate"
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True
    preview_response = client.post(
        f"/api/actions/{LOCALO_VISIBILITY_REVIEW_ACTION_ID}/preview"
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["preview_contract"] == "local_visibility_review_preview_v1"
    assert preview_payload["preview_items_total"] == 1
    assert preview_payload["preview_items"][0]["metric_snapshot"][
        "localo_reviews_count"
    ] == 793
    assert "payload_preview_missing" not in preview_payload["blockers"]

    command_response = client.get("/api/dashboard/command-center")

    assert command_response.status_code == 200
    command_payload = command_response.json()
    brief_by_id = {item["id"]: item for item in command_payload["operator_brief"]}
    assert "daily_localo_readiness" not in brief_by_id
    localo_brief = brief_by_id["daily_localo_visibility_facts"]
    assert localo_brief["status"] == "ready"
    assert localo_brief["metric_tiles"]["miejsca"] == 4
    assert localo_brief["metric_tiles"]["frazy"] == 23
    plan_by_id = {item["id"]: item for item in command_payload["action_plan"]}
    assert "plan_localo_access_ready_wait_for_visibility_facts" not in plan_by_id
    localo_plan = plan_by_id["plan_review_localo_visibility_facts"]
    assert localo_plan["status"] == "ready"
    assert localo_plan["action_ids"] == [LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    assert "wyniki profilu firmy w Google" in localo_plan["blocked_claims"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-localo-operator"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["localo_diagnostics"]["action_ids"] == [
        LOCALO_VISIBILITY_REVIEW_ACTION_ID
    ]
    context_actions_by_id = {
        action["id"]: action for action in context_payload["active_action_objects"]
    }
    localo_context_action = context_actions_by_id[LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    assert localo_context_action["payload"]["payload_preview_included"] == 1
    assert localo_context_action["payload"]["payload_preview_total"] == 1
    assert localo_context_action["payload"]["payload_preview"][0]["preview_contract"] == (
        "local_visibility_review_preview_v1"
    )
    assert localo_context_action["payload"]["payload_preview"][0]["metric_snapshot"][
        "localo_active_place_count"
    ] == 4


def test_localo_diagnostics_does_not_block_ready_gbp_or_competitor_contracts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_full_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "localo_full.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")
    localo_run = ConnectorRefreshRun(
        id="refresh_localo_full_diag_test",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_localo_full_diag_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "api": "localo_mcp_oauth_probe",
            "mcp_initialize_status": 200,
            "authorization_code_supported": 1,
            "pkce_s256_supported": 1,
            "access_token_present": 1,
            "localo_active_place_count": 4,
            "localo_tracked_keyword_count": 23,
            "localo_avg_visibility_current": 53.1739,
            "localo_reviews_count": 798,
            "localo_gbp_impressions_total": 120,
            "localo_competitor_count": 3,
        },
        summary="Odczyt danych Localo zakończony agregatami.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().save_connector_refresh_metrics(
        localo_run,
        detailed_facts=[
            VendorMetricFact(
                "localo_active_place_count",
                4,
                {"contract": "place_inventory", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_tracked_keyword_count",
                23,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_avg_visibility_current",
                53.1739,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_reviews_count",
                798,
                {"contract": "reviews", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_gbp_impressions_total",
                120,
                {"contract": "gbp_visibility", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_competitor_count",
                3,
                {"contract": "competitor_visibility", "scope": "active_places"},
                period="localo_mcp_read",
            ),
        ],
    )

    response = client.get("/api/localo/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    review_decision = decision_by_id["localo_review_visibility_facts"]
    assert review_decision["allowed_evidence"] == [
        "place_inventory",
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
    ]
    assert review_decision["missing_read_contracts"] == ["local_tasks"]
    assert review_decision["blocked_claims"] == [
        "ukończone zadanie lokalne",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert "wyniki profilu firmy w Google" not in review_decision["blocked_claims"]
    assert "widoczności konkurencji" not in review_decision["blocked_claims"]
    blocked_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert blocked_decision["missing_read_contracts"] == ["local_tasks"]
    assert "profil firmy w Google, konkurencję" not in blocked_decision["title"]
    assert "profilu firmy w Google, konkurencji" not in blocked_decision["summary"]
    assert "kontrakty profilu firmy w Google, konkurencji" not in blocked_decision["next_step"]

    actions_response = client.get("/api/actions")

    assert actions_response.status_code == 200
    actions_by_id = {action["id"]: action for action in actions_response.json()}
    localo_action = actions_by_id[LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    assert localo_action["payload"]["missing_read_contracts"] == ["local_tasks"]
    assert "wyniki profilu firmy w Google" not in localo_action["payload"]["blocked_claims"]
    assert "widoczności konkurencji" not in localo_action["payload"]["blocked_claims"]
    assert localo_action["payload"]["payload_preview"][0]["missing_read_contracts"] == [
        "local_tasks"
    ]
    assert (
        "profil firmy w Google, konkurencję"
        not in localo_action["payload"]["payload_preview"][0]["reason"]
    )


def test_localo_diagnostics_blocks_visibility_when_access_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_diag_blocked_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "localo_diag_blocked.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    metric_store().status()

    response = client.get("/api/localo/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_probe"]["status"] == "access_blocked"
    assert payload["live_data_available"] is False
    assert payload["visibility_fact_count"] == 0
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    assert decision_by_id["localo_fix_access_before_visibility_review"]["status"] == "blocked"
    assert decision_by_id["localo_fix_access_before_visibility_review"]["metric_tiles"] == {
        "dostęp Localo": 0,
        "brakujące dane": 6,
    }
    assert "mcp_initialize" in decision_by_id[
        "localo_fix_access_before_visibility_review"
    ]["missing_read_contracts"]
    assert decision_by_id["localo_block_visibility_claims_without_read_contract"][
        "status"
    ] == "blocked"


def test_ahrefs_diagnostics_exposes_authority_context_and_blocks_gap_claims(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_diag_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_diag.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    ahrefs_run = ConnectorRefreshRun(
        id="refresh_ahrefs_diag_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_ahrefs_diag_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "api": "ahrefs_site_explorer_domain_rating",
            "domain_rating": 90,
            "ahrefs_rank": 1450,
            "organic_competitor_read_status": "completed",
            "organic_competitor_rows": 0,
            "organic_competitor_country": "pl",
            "organic_competitor_mode": "subdomains",
        },
        summary="Ahrefs domain rating completed through test adapter.",
    )
    local_state_store().save_connector_refresh_run(ahrefs_run)
    metric_store().save_connector_refresh_metrics(
        ahrefs_run,
        detailed_facts=[
            VendorMetricFact(
                "domain_rating",
                90,
                {"contract": "authority_summary"},
                period="ahrefs_site_explorer",
            ),
            VendorMetricFact(
                "ahrefs_rank",
                1450,
                {"contract": "authority_summary"},
                period="ahrefs_site_explorer",
            ),
        ],
    )
    orphan_run = ConnectorRefreshRun(
        id="refresh_ahrefs_orphan_diag_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_ahrefs_orphan_diag_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"domain_rating": 99, "ahrefs_rank": 999},
        summary="Orphan Ahrefs fixture that is not in local_state.",
    )
    metric_store().save_connector_refresh_metrics(orphan_run)

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["live_data_available"] is True
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "zakończony"
    assert payload["live_data_status_label"] == "metryki Ahrefs dostępne"
    assert payload["authority_fact_count"] == 2
    assert payload["gap_fact_count"] == 0
    assert payload["blocker_count"] == 1
    gap_contract = payload["gap_read_contract"]
    assert gap_contract["status"] == "blocked"
    assert gap_contract["status_label"] == "zablokowane"
    assert gap_contract["gap_records"] == []
    assert gap_contract["available_read_contracts"] == ["ahrefs_authority_summary"]
    assert "ahrefs_content_gap_records" in gap_contract["missing_read_contracts"]
    assert "luka treści" in gap_contract["blocked_claims"]
    assert "luka treści" in gap_contract["blocked_claim_labels"]
    assert gap_contract["operator_review_gates"] == [
        "ahrefs_gap_records_required",
        "content_planner_review_required",
        "human_strategy_review",
    ]
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    authority_decision = decision_by_id["ahrefs_review_authority_context"]
    assert authority_decision["status"] == "ready"
    assert authority_decision["status_label"] == "gotowe"
    assert authority_decision["priority_label"] == "wysoki priorytet"
    assert authority_decision["decision_type_label"] == "kontekst autorytetu"
    assert authority_decision["metric_tiles"]["ocena domeny Ahrefs"] == 90
    assert authority_decision["metric_tiles"]["pozycja w rankingu Ahrefs"] == 1450
    assert authority_decision["metric_tiles"]["konkurenci organiczni"] == 0
    assert authority_decision["metric_tiles"]["odczyt konkurencji"] == "zakończony"
    assert authority_decision["metric_tiles"]["zakres konkurencji"] == "subdomeny"
    assert authority_decision["metric_tiles"]["luki Ahrefs"] == 0
    assert "organic_competitor_rows" in authority_decision["allowed_evidence"]
    assert "konkurenci organiczni" in authority_decision["allowed_evidence_labels"]
    assert "organic_competitor_mode" in authority_decision["allowed_evidence"]
    assert "zakres odczytu konkurencji" in authority_decision["allowed_evidence_labels"]
    assert "rekordy luk treści" in authority_decision["missing_read_contract_labels"]
    assert "liczba konkurentów: 0" in authority_decision["summary"]
    assert "rows=0" not in authority_decision["summary"]
    assert "status=completed" not in authority_decision["summary"]
    assert "subdomains" not in authority_decision["summary"]
    assert "domain_rating=" not in authority_decision["summary"]
    assert "ahrefs_rank=" not in authority_decision["summary"]
    assert "ahrefs_content_gap_records" in authority_decision["missing_read_contracts"]
    assert "luka treści" in authority_decision["blocked_claims"]
    assert "luka treści" in authority_decision["blocked_claim_labels"]
    assert authority_decision["knowledge_card_ids"] == [
        "card_ahrefs_content_gap_playbook"
    ]
    assert authority_decision["expert_rule_ids"] == ["content_brief_rules_v1"]
    block_decision = decision_by_id["ahrefs_block_gap_claims_without_records"]
    assert block_decision["status"] == "blocked"
    assert block_decision["status_label"] == "zablokowane"
    assert block_decision["priority_label"] == "wysoki priorytet"
    assert block_decision["metric_tiles"]["brakujące dane"] == 5
    assert block_decision["evidence_ids"] == ["ev_refresh_refresh_ahrefs_diag_test"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "ahrefs_operator_summary"
    assert operator_summary["title"] == "Co marketer ma wiedzieć o Ahrefs"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["gap_read_status"] == "blocked"
    assert operator_summary["gap_read_status_label"] == "zablokowane"
    assert operator_summary["authority_fact_count"] == 2
    assert operator_summary["gap_fact_count"] == 0
    assert "ahrefs_authority_summary" in operator_summary["available_read_contracts"]
    assert "podsumowanie autorytetu domeny" in operator_summary["available_read_contract_labels"]
    assert "ahrefs_content_gap_records" in operator_summary["missing_read_contracts"]
    assert "rekordy luk treści" in operator_summary["missing_read_contract_labels"]
    assert "ahrefs" in operator_summary["source_connectors"]
    assert "ev_refresh_refresh_ahrefs_diag_test" in operator_summary["evidence_ids"]
    assert "luka treści" in operator_summary["blocked_claims"]
    assert "luka treści" in operator_summary["blocked_claim_labels"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    assert all(fact["source_connector"] == "ahrefs" for fact in authority_decision["metric_facts"])
    assert payload["sections"][0]["status_label"]
    assert isinstance(payload["sections"][0]["blocked_claim_labels"], list)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "ahrefs-token-test" not in serialized

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["ahrefs_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
    context_gap_contract = context_payload["ahrefs_diagnostics"]["gap_read_contract"]
    assert context_gap_contract["status"] == gap_contract["status"]
    assert context_gap_contract["gap_record_count"] == gap_contract["gap_record_count"]
    assert context_gap_contract["gap_records_omitted"] is True
    assert "gap_records" not in context_gap_contract
    assert context_payload["ahrefs_diagnostics"]["decision_queue"][0]["id"] in decision_by_id
    assert context_payload["ahrefs_diagnostics"]["context_pack_compaction"] == {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": 3,
        "latest_refresh_compacted": True,
        "gap_records_omitted": True,
        "full_endpoint": "/api/ahrefs/diagnostics",
    }
    assert context_payload["active_action_objects"] == []
    assert "marketing_brief" not in context_payload
    assert "content_diagnostics" not in context_payload


def test_ahrefs_skill_context_pack_compacts_historical_raw_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_context_raw_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_context_raw.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    ahrefs_run = ConnectorRefreshRun(
        id="refresh_ahrefs_raw_history_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_ahrefs_raw_history_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "domain_rating": 90,
            "ahrefs_rank": 1450,
            "ahrefs_content_gap_count": 2,
            "ahrefs_backlink_gap_count": 4,
        },
        summary=(
            "Typed Ahrefs gap records completed. Content gap rows: 2. "
            "Backlink gap rows: 4. Top pages and organic keywords loaded."
        ),
    )
    local_state_store().save_connector_refresh_run(ahrefs_run)
    metric_store().save_connector_refresh_metrics(
        ahrefs_run,
        detailed_facts=[
            VendorMetricFact("domain_rating", 90, period="ahrefs_site_explorer"),
            VendorMetricFact("ahrefs_rank", 1450, period="ahrefs_site_explorer"),
        ],
    )
    dirty_card = KnowledgeCard(
        id="card_dirty_ahrefs_history",
        card_type="seo_context",
        title="Ahrefs luka treścis and luka linkóws playbook",
        summary="Use Content gap rows, Backlink gap rows and top pages as raw skill text.",
        source_type="doc",
        source_id="dirty-ahrefs-doc",
        source_url_or_path="docs/dirty-ahrefs.md",
        confidence=0.9,
        source_lineage=["Content gap rows", "Backlink gap rows"],
    )
    monkeypatch.setattr(
        "apps.api.wilq_api.main._knowledge_cards_for_skill",
        lambda skill: [dirty_card],
    )

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["context_pack_compaction"]["mode"] == "skill_default"
    assert payload["context_pack_compaction"]["connector_refresh_runs_compacted"] is True
    assert payload["context_pack_compaction"]["evidence_summaries_compacted"] is True
    assert payload["context_pack_compaction"]["knowledge_card_summaries_compacted"] is True
    assert payload["context_pack_compaction"]["expert_capabilities_compacted"] is True
    assert payload["context_pack_compaction"]["action_review_gates_compacted"] is True
    assert payload["context_pack_compaction"]["raw_history_omitted"] is True
    assert payload["expert_capabilities"]
    assert all(
        capability["required_mapping"] == []
        for capability in payload["expert_capabilities"]
    )
    assert all(
        isinstance(capability["required_mapping_total"], int)
        for capability in payload["expert_capabilities"]
    )
    assert payload["connector_refresh_runs"][0]["id"] == "refresh_ahrefs_raw_history_test"
    assert payload["connector_refresh_runs"][0]["evidence_ids"] == [
        "ev_refresh_refresh_ahrefs_raw_history_test"
    ]
    assert payload["evidence_summaries"]
    assert payload["evidence_summaries"][0]["source_connector"] == "ahrefs"
    assert payload["evidence_summaries"][0]["raw_ref"] is None
    assert payload["knowledge_card_summaries"][0]["id"] == "card_dirty_ahrefs_history"

    serialized = json.dumps(
        {
            "connector_refresh_runs": payload["connector_refresh_runs"],
            "evidence_summaries": payload["evidence_summaries"],
            "knowledge_card_summaries": payload["knowledge_card_summaries"],
            "ahrefs_diagnostics": payload["ahrefs_diagnostics"],
        },
        ensure_ascii=False,
    )
    forbidden_terms = (
        "Typed Ahrefs",
        "gap records",
        "Content gap rows",
        "Backlink gap rows",
        "luka treścis",
        "luka linkóws",
        "top pages",
        "organic keywords",
    )
    for term in forbidden_terms:
        assert term not in serialized


def test_ahrefs_diagnostics_builds_gap_review_records_from_metric_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_gap_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_gap.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    ahrefs_run = ConnectorRefreshRun(
        id="refresh_ahrefs_gap_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_ahrefs_gap_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "domain_rating": 90,
            "ahrefs_rank": 1450,
            "ahrefs_competitor_page_count": 3,
            "ahrefs_content_gap_count": 2,
            "ahrefs_backlink_gap_count": 4,
            "ahrefs_organic_keyword_gap_count": 5,
        },
        summary="Ahrefs gap read completed through test adapter.",
    )
    local_state_store().save_connector_refresh_run(ahrefs_run)
    metric_store().save_connector_refresh_metrics(
        ahrefs_run,
        detailed_facts=[
            VendorMetricFact("domain_rating", 90, period="ahrefs_site_explorer"),
            VendorMetricFact("ahrefs_rank", 1450, period="ahrefs_site_explorer"),
            VendorMetricFact(
                "ahrefs_competitor_page_count",
                3,
                {
                    "competitor_domain": "example.pl",
                    "source_url": "https://example.pl/bdo/",
                    "target_url": "https://www.ekologus.pl/bdo/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                2,
                {
                    "competitor_domain": "example.pl",
                    "keyword": "bdo szkolenie",
                    "target_url": "https://www.ekologus.pl/bdo/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_backlink_gap_count",
                4,
                {
                    "competitor_domain": "example.pl",
                    "source_url": "https://example.pl/poradnik/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_organic_keyword_gap_count",
                5,
                {
                    "keyword": "zielony ład obowiązki",
                    "target_url": (
                        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
                    ),
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_top_page_gap_count",
                1,
                {
                    "competitor_domain": "example.pl",
                    "source_url": "https://example.pl/top-bdo/",
                    "target_url": "https://www.ekologus.pl/bdo/",
                },
                period="ahrefs_gap",
            ),
        ],
    )

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is True
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "zakończony"
    assert payload["live_data_status_label"] == "metryki Ahrefs dostępne"
    assert payload["gap_fact_count"] == 9
    assert payload["blocker_count"] == 0
    gap_contract = payload["gap_read_contract"]
    assert gap_contract["status"] == "ready"
    assert gap_contract["status_label"] == "gotowe"
    assert gap_contract["missing_read_contracts"] == []
    assert gap_contract["available_read_contracts"] == [
        "ahrefs_authority_summary",
        "ahrefs_gap_metric_facts",
        "ahrefs_competitor_pages",
        "ahrefs_content_gap_records",
        "ahrefs_backlink_gap_records",
        "ahrefs_organic_keywords_by_url",
        "ahrefs_top_pages_by_competitor",
    ]
    assert gap_contract["available_read_contract_labels"] == [
        "podsumowanie autorytetu domeny",
        "metryki luk z Ahrefs",
        "strony konkurencji",
        "rekordy luk treści",
        "rekordy luk linków",
        "organiczne słowa per URL",
        "najlepsze strony konkurencji",
    ]
    assert set(gap_contract["allowed_evidence"]) == {
        "domain_rating",
        "ahrefs_rank",
        "ahrefs_competitor_page_count",
        "ahrefs_content_gap_count",
        "ahrefs_backlink_gap_count",
        "ahrefs_organic_keyword_gap_count",
        "ahrefs_top_page_gap_count",
    }
    assert {record["gap_type"] for record in gap_contract["gap_records"]} == {
        "competitor_page",
        "content_gap",
        "backlink_gap",
        "organic_keyword_gap",
        "top_page_gap",
    }
    assert {record["gap_type_label"] for record in gap_contract["gap_records"]} == {
        "strona konkurencji",
        "luka treści",
        "luka linków",
        "luka słów organicznych",
        "luka najlepszych stron konkurencji",
    }
    content_record = next(
        record
        for record in gap_contract["gap_records"]
        if record["gap_type"] == "content_gap"
    )
    assert content_record["keyword"] == "bdo szkolenie"
    assert content_record["competitor_domain"] == "example.pl"
    assert "luki treści=2" in content_record["summary"]
    assert content_record["metric_fact_labels"]["ahrefs_content_gap_count"] == "luki treści"
    assert "wzrost ruchu" in content_record["blocked_claims"]

    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    gap_decision = decision_by_id["ahrefs_review_gap_records"]
    assert gap_decision["status"] == "ready"
    assert gap_decision["status_label"] == "gotowe"
    assert gap_decision["priority_label"] == "wysoki priorytet"
    assert gap_decision["decision_type_label"] == "sprawdzenie luk"
    assert gap_decision["metric_tiles"] == {
        "rekordy luk": 5,
        "luki treści": 1,
        "luki backlinków": 1,
        "strony konkurencji": 1,
        "słowa organiczne": 1,
        "najlepsze strony": 1,
        "brakujące dane": 0,
    }
    assert gap_decision["missing_read_contracts"] == []
    assert gap_decision["missing_read_contract_labels"] == []
    assert "ocena domeny Ahrefs" in gap_decision["allowed_evidence_labels"]
    assert "luki treści" in gap_decision["allowed_evidence_labels"]
    assert "wzrost ruchu" in gap_decision["blocked_claims"]
    assert "wzrost ruchu" in gap_decision["blocked_claim_labels"]
    assert "ahrefs_block_gap_claims_without_records" not in decision_by_id
    operator_summary = payload["operator_summary"]
    assert operator_summary["gap_read_status"] == "ready"
    assert operator_summary["gap_read_status_label"] == "gotowe"
    assert "rekordami luk Ahrefs" in operator_summary["next_step"]
    assert "bez rekordów" not in operator_summary["next_step"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_gap_contract = context_payload["ahrefs_diagnostics"]["gap_read_contract"]
    assert context_gap_contract["status"] == gap_contract["status"]
    assert context_gap_contract["gap_record_count"] == gap_contract["gap_record_count"]
    assert context_gap_contract["gap_records_omitted"] is True
    assert context_gap_contract["gap_records_total"] == len(gap_contract["gap_records"])
    assert "gap_records" not in context_gap_contract
    assert context_payload["ahrefs_diagnostics"]["context_pack_compaction"][
        "full_endpoint"
    ] == "/api/ahrefs/diagnostics"
    assert context_payload["active_action_objects"] == []


def test_ahrefs_diagnostics_keeps_gap_records_when_newer_authority_reads_are_noisy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_buried_gap_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_buried_gap.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    gap_run = ConnectorRefreshRun(
        id="refresh_ahrefs_buried_gap_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=datetime(2026, 6, 18, 9, 0, tzinfo=UTC),
        completed_at=datetime(2026, 6, 18, 9, 0, tzinfo=UTC),
        evidence_ids=["ev_refresh_refresh_ahrefs_buried_gap_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "ahrefs_competitor_page_count": 1,
            "ahrefs_content_gap_count": 1,
            "ahrefs_backlink_gap_count": 1,
            "ahrefs_organic_keyword_gap_count": 1,
            "ahrefs_top_page_gap_count": 1,
        },
        summary="Older Ahrefs gap read that must remain visible.",
    )
    local_state_store().save_connector_refresh_run(gap_run)
    metric_store().save_connector_refresh_metrics(
        gap_run,
        detailed_facts=[
            VendorMetricFact(
                "ahrefs_competitor_page_count",
                1,
                {
                    "gap_type": "competitor_page",
                    "competitor_domain": "denios.pl",
                    "source_url": "https://www.denios.pl/audyt-srodowiskowy/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "audyt środowiskowy",
                    "competitor_domain": "denios.pl",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_backlink_gap_count",
                1,
                {
                    "gap_type": "backlink_gap",
                    "competitor_domain": "denios.pl",
                    "source_url": "https://www.denios.pl/poradnik/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_organic_keyword_gap_count",
                1,
                {
                    "gap_type": "organic_keyword_gap",
                    "keyword": "pozwolenie zintegrowane",
                    "competitor_domain": "denios.pl",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_top_page_gap_count",
                1,
                {
                    "gap_type": "top_page_gap",
                    "competitor_domain": "denios.pl",
                    "source_url": "https://www.denios.pl/top/",
                },
                period="ahrefs_gap",
            ),
        ],
    )
    for index in range(170):
        collected_at = datetime(2026, 6, 19, 9, 0, tzinfo=UTC) + timedelta(minutes=index)
        authority_run = ConnectorRefreshRun(
            id=f"refresh_ahrefs_noisy_authority_{index}",
            connector_id="ahrefs",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=collected_at,
            completed_at=collected_at,
            evidence_ids=[f"ev_refresh_refresh_ahrefs_noisy_authority_{index}"],
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"domain_rating": 90, "ahrefs_rank": 1450},
            summary="Newer authority-only Ahrefs read.",
        )
        local_state_store().save_connector_refresh_run(authority_run)
        metric_store().save_connector_refresh_metrics(
            authority_run,
            detailed_facts=[
                VendorMetricFact("domain_rating", 90, period="ahrefs_site_explorer"),
                VendorMetricFact("ahrefs_rank", 1450, period="ahrefs_site_explorer"),
            ],
        )

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is True
    assert payload["gap_fact_count"] >= 2
    assert payload["gap_read_contract"]["status"] == "ready"
    assert "ev_refresh_refresh_ahrefs_buried_gap_test" in payload["evidence_ids"]
    assert {
        record["gap_type"] for record in payload["gap_read_contract"]["gap_records"]
    } == {
        "competitor_page",
        "content_gap",
        "backlink_gap",
        "organic_keyword_gap",
        "top_page_gap",
    }
    decision_ids = {decision["id"] for decision in payload["decision_queue"]}
    assert "ahrefs_review_gap_records" in decision_ids
    assert "ahrefs_block_gap_claims_without_records" not in decision_ids


def test_ahrefs_diagnostics_prioritizes_reviewable_ekologus_gap_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_relevance_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_relevance.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    ahrefs_run = ConnectorRefreshRun(
        id="refresh_ahrefs_relevance_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_ahrefs_relevance_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "domain_rating": 90,
            "ahrefs_rank": 1450,
            "ahrefs_content_gap_count": 4,
            "ahrefs_backlink_gap_count": 6,
            "ahrefs_organic_keyword_gap_count": 2,
        },
        summary="Ahrefs mixed relevance gap read completed through test adapter.",
    )
    local_state_store().save_connector_refresh_run(ahrefs_run)
    metric_store().save_connector_refresh_metrics(
        ahrefs_run,
        detailed_facts=[
            VendorMetricFact("domain_rating", 90, period="ahrefs_site_explorer"),
            VendorMetricFact("ahrefs_rank", 1450, period="ahrefs_site_explorer"),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                2,
                {
                    "gap_type": "content_gap",
                    "keyword": "bdo szkolenia środowiskowe",
                    "competitor_domain": "denios.pl",
                    "target_url": "https://www.ekologus.pl/bdo/",
                    "source_url": "https://www.denios.pl/bdo/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_organic_keyword_gap_count",
                2,
                {
                    "gap_type": "organic_keyword_gap",
                    "keyword": "magazynowanie odpadów",
                    "competitor_domain": "dla-przemyslu.pl",
                    "source_url": "https://dla-przemyslu.pl/magazynowanie-odpadow/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_backlink_gap_count",
                6,
                {
                    "gap_type": "backlink_gap",
                    "competitor_domain": "cuk.pl",
                    "source_url": "apple.com",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_backlink_gap_count",
                4,
                {
                    "gap_type": "backlink_gap",
                    "competitor_domain": "cuk.pl",
                    "source_url": "google.com",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                4,
                {
                    "gap_type": "content_gap",
                    "keyword": "prawo jazdy b1",
                    "competitor_domain": "cuk.pl",
                    "source_url": "https://cuk.pl/porady/prawo-jazdy-B1",
                },
                period="ahrefs_gap",
            ),
        ],
    )

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    records = payload["gap_read_contract"]["gap_records"]
    assert [record["keyword"] for record in records if record["keyword"]] == [
        "bdo szkolenia środowiskowe",
        "magazynowanie odpadów",
    ]
    record_text = " ".join(record["title"] for record in records)
    assert "apple.com" not in record_text
    assert "google.com" not in record_text
    assert "prawo jazdy" not in record_text
    gap_decision = {
        decision["id"]: decision for decision in payload["decision_queue"]
    }["ahrefs_review_gap_records"]
    assert gap_decision["metric_tiles"]["rekordy luk"] == 2


def test_marketing_tactical_queue_rejects_dev_preview_sitemap_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "dev_preview_queue.duckdb"))
    gsc_run = ConnectorRefreshRun(
        id="refresh_google_search_console_dev_preview_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_search_console_dev_preview_test"],
        metric_summary={"clicks": 8, "impressions": 220},
        summary="GSC dev preview rejection test seed.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_dev_preview_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_wordpress_ekologus_dev_preview_test"],
        metric_summary={"content_object_count": 1, "sitemap_url_count": 1},
        summary="WordPress dev preview sitemap seed.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=8,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=220,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
            VendorMetricFact(
                name="ctr",
                value=0.036,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
            VendorMetricFact(
                name="average_position",
                value=6.2,
                dimensions={
                    "query": "bdo przedsiębiorca",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "site_kind": "primary",
                    "content_type": "sitemap",
                    "object_id": "",
                    "content_url": (
                        "https://ekologus.dev.proudsite.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/"
                    ),
                    "status": "indexed",
                    "modified_gmt": "2026-06-17T20:00:00+00:00",
                    "inventory_source": "sitemap",
                },
            )
        ],
    )

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    item = next(
        item
        for item in response.json()["items"]
        if item["dimensions"].get("query") == "bdo przedsiębiorca"
    )
    assert item["dimensions"]["wordpress_match"] == "missing"
    assert item["dimensions"]["wordpress_match_confidence"] == "missing"
    assert "wordpress_content_host" not in item["dimensions"]
    assert item["dimensions"].get("wordpress_host_alias_applied") in {None, "false"}
    assert "wordpress_inventory_source" not in item["dimensions"]
    assert "wordpress_ekologus" not in item["source_connectors"]
    assert (
        "ev_refresh_refresh_wordpress_ekologus_dev_preview_test"
        not in item["evidence_ids"]
    )


def test_marketing_tactical_queue_uses_full_wordpress_inventory_for_url_matching(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "large_inventory.duckdb"))
    gsc_run = ConnectorRefreshRun(
        id="refresh_google_search_console_large_inventory_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_search_console_large_inventory_test"],
        metric_summary={"clicks": 29, "impressions": 651},
        summary="GSC large inventory test seed.",
    )
    target_wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_target_inventory_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_target_inventory_test"],
        metric_summary={"content_object_count": 1},
        summary="WordPress target URL seed.",
    )
    noisy_wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_noisy_inventory_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_noisy_inventory_test"],
        metric_summary={"content_object_count": 350},
        summary="Newer noisy WordPress inventory seed.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=29,
                dimensions={
                    "query": "co to jest zielony ład",
                    "page": (
                        "https://www.ekologus.pl/"
                        "europejski-zielony-lad-co-to-takiego/"
                    ),
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=651,
                dimensions={
                    "query": "co to jest zielony ład",
                    "page": (
                        "https://www.ekologus.pl/"
                        "europejski-zielony-lad-co-to-takiego/"
                    ),
                },
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        target_wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": (
                        "https://www.ekologus.pl/"
                        "europejski-zielony-lad-co-to-takiego/"
                    ),
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            )
        ],
    )
    metric_store().save_connector_refresh_metrics(
        noisy_wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": f"https://www.ekologus.pl/noisy-page-{index}/",
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            )
            for index in range(350)
        ],
    )

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    item = next(
        item
        for item in response.json()["items"]
        if item["dimensions"].get("query") == "co to jest zielony ład"
    )
    assert item["dimensions"]["wordpress_match"] == "found"
    assert item["dimensions"]["wordpress_match_confidence"] == "exact_url"
    assert item["dimensions"]["wordpress_requested_path"] == (
        "/europejski-zielony-lad-co-to-takiego"
    )
    assert item["dimensions"]["wordpress_matched_path"] == (
        "/europejski-zielony-lad-co-to-takiego"
    )
    assert item["intent"] in {"content_refresh", "content_merge"}
    assert "ev_refresh_wordpress_ekologus_target_inventory_test" in item["evidence_ids"]


def test_marketing_tactical_queue_does_not_slice_wordpress_inventory_url_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "wide_inventory.duckdb"))
    gsc_run = ConnectorRefreshRun(
        id="refresh_google_search_console_wide_inventory_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_search_console_wide_inventory_test"],
        metric_summary={"clicks": 4, "impressions": 4429},
        summary="GSC wide inventory test seed.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_wide_inventory_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_wide_inventory_test"],
        metric_summary={"content_object_count": 1301},
        summary="Wide WordPress inventory seed.",
    )
    target_url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=4,
                dimensions={
                    "query": "bdo co to",
                    "page": target_url,
                },
            ),
            VendorMetricFact(
                name="impressions",
                value=4429,
                dimensions={
                    "query": "bdo co to",
                    "page": target_url,
                },
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            *[
                VendorMetricFact(
                    name="content_object_seen",
                    value=1,
                    dimensions={
                        "connector_id": "wordpress_ekologus",
                        "content_type": "sitemap",
                        "content_url": f"https://www.ekologus.pl/a-noise-{index:04d}/",
                        "status": "indexed",
                        "inventory_source": "public_sitemap",
                    },
                )
                for index in range(1250)
            ],
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": target_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            ),
        ],
    )

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    item = next(
        item
        for item in response.json()["items"]
        if item["dimensions"].get("query") == "bdo co to"
    )
    assert item["dimensions"]["wordpress_match"] == "found"
    assert item["dimensions"]["wordpress_match_confidence"] == "exact_url"
    assert item["dimensions"]["wordpress_content_url"] == target_url


def test_evidence_registry_exposes_connector_status_without_secret_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "gho_supersecretvalue1234567890",  # pragma: allowlist secret
    )
    response = client.get("/api/evidence")
    assert response.status_code == 200
    evidence = response.json()
    evidence_ids = {item["id"] for item in evidence}
    assert "ev_connector_google_ads_status" in evidence_ids
    serialized = json.dumps(evidence)
    assert "gho_supersecretvalue1234567890" not in serialized


def test_opportunities_are_derived_from_evidence_and_rule_mappings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")
    save_localo_visibility_metric_facts()

    response = client.get("/api/opportunities")
    assert response.status_code == 200
    opportunities = response.json()
    opportunity_ids = {item["id"] for item in opportunities}
    assert opportunity_ids == {
        "opp_decision_review_merchant_feed_issues",
        "opp_decision_prepare_content_refresh_queue",
        "opp_decision_review_ga4_landing_quality",
        "opp_decision_review_ads_campaign_metrics",
        "opp_decision_review_localo_visibility_facts",
    }
    google_ads = next(
        item for item in opportunities if item["id"] == "opp_decision_review_ads_campaign_metrics"
    )
    assert google_ads["type"] == "google_ads_review_queue"
    assert google_ads["domain"] == "google_ads"
    assert google_ads["metric_tiles"]["kampanie"] >= 1
    assert google_ads["action_ids"] == [
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
    ]
    assert google_ads["is_fixture"] is False
    localo = next(
        item
        for item in opportunities
        if item["id"] == "opp_decision_review_localo_visibility_facts"
    )
    assert localo["type"] == "localo_visibility_drop"
    assert localo["domain"] == "localo"
    assert localo["action_ids"] == ["act_review_localo_visibility_facts"]
    assert localo["is_fixture"] is False
    content = next(
        item
        for item in opportunities
        if item["id"] == "opp_decision_prepare_content_refresh_queue"
    )
    assert content["type"] == "content_brief_candidate"
    assert content["domain"] == "gsc_seo"
    assert content["action_ids"] == ["act_prepare_content_refresh_queue"]
    assert content["is_fixture"] is False
    serialized = json.dumps(opportunities, ensure_ascii=False)
    assert "opp_connector_" not in serialized
    assert "rejestr reguł i playbooków" not in serialized
    assert "connector_configured" not in serialized
    assert "Run a read-only" not in serialized


def test_actions_reference_registered_evidence_ids() -> None:
    evidence_response = client.get("/api/evidence")
    assert evidence_response.status_code == 200
    evidence_ids = {item["id"] for item in evidence_response.json()}

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    for action in actions_response.json():
        assert set(action["evidence_ids"]).issubset(evidence_ids)


def test_connector_refresh_run_persists_redacted_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv(
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "gho_refreshsecretvalue1234567890",  # pragma: allowlist secret
    )

    response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )
    assert response.status_code == 200
    run = response.json()
    assert run["connector_id"] == "google_ads"
    assert run["mode"] == "vendor_read"
    assert run["status"] == "blocked"
    assert run["external_call_attempted"] is False
    assert run["vendor_data_collected"] is False
    assert "ev_connector_google_ads_status" in run["evidence_ids"]

    list_response = client.get("/api/connectors/refresh-runs")
    assert list_response.status_code == 200
    serialized_runs = json.dumps(list_response.json())
    assert run["id"] in serialized_runs
    assert "gho_refreshsecretvalue1234567890" not in serialized_runs

    evidence_response = client.get("/api/evidence")
    assert evidence_response.status_code == 200
    evidence_ids = {item["id"] for item in evidence_response.json()}
    assert f"ev_refresh_{run['id']}" in evidence_ids
    serialized_evidence = json.dumps(evidence_response.json())
    assert "gho_refreshsecretvalue1234567890" not in serialized_evidence

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert context_response.status_code == 200
    context_runs = {item["id"] for item in context_response.json()["connector_refresh_runs"]}
    assert run["id"] in context_runs


def test_google_ads_vendor_read_uses_oauth_and_search_stream(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "developer-token-test")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id-test")
    monkeypatch.setenv(
        "GOOGLE_ADS_CLIENT_SECRET",
        "client-secret-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv(
        "GOOGLE_ADS_REFRESH_TOKEN",
        "refresh-token-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "123-456-7890")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "999-888-7777")

    search_stream_queries: list[str] = []
    keyword_planner_requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            assert "grant_type=refresh_token" in request.content.decode()
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        assert request.url.host == "googleads.googleapis.com"
        if request.url.path == "/v24/customers/1234567890:generateKeywordIdeas":
            assert request.headers["developer-token"] == "developer-token-test"
            assert request.headers["login-customer-id"] == "9998887777"
            assert request.headers["authorization"] == "Bearer ya29.mocktoken"
            payload = json.loads(request.content.decode())
            keyword_planner_requests.append(payload)
            assert payload["keywordSeed"]["keywords"] == ["bdo rejestracja"]
            assert payload["keywordPlanNetwork"] == "GOOGLE_SEARCH_AND_PARTNERS"
            assert payload["geoTargetConstants"] == ["geoTargetConstants/2616"]
            assert payload["language"] == "languageConstants/1045"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "text": "bdo szkolenie",
                            "keywordIdeaMetrics": {
                                "avgMonthlySearches": "100",
                                "competition": "MEDIUM",
                                "competitionIndex": "55",
                                "lowTopOfPageBidMicros": "1200000",
                                "highTopOfPageBidMicros": "4400000",
                            },
                        }
                    ]
                },
            )
        assert request.url.path == "/v24/customers/1234567890/googleAds:searchStream"
        assert request.headers["developer-token"] == "developer-token-test"
        assert request.headers["login-customer-id"] == "9998887777"
        assert request.headers["authorization"] == "Bearer ya29.mocktoken"
        query = json.loads(request.content.decode())["query"]
        search_stream_queries.append(query)
        if "FROM campaign" in query:
            assert "customer.currency_code" in query
            assert "campaign.name" in query
            assert "campaign.status" in query
            assert "campaign.advertising_channel_type" in query
            assert "campaign_budget.amount_micros" in query
            assert "campaign_budget.period" in query
            assert "campaign_budget.has_recommended_budget" in query
            assert "campaign_budget.recommended_budget_amount_micros" in query
            assert "metrics.conversions" in query
            assert "metrics.conversions_value" in query
            assert "metrics.search_impression_share" in query
            assert "metrics.search_budget_lost_impression_share" in query
            assert "metrics.search_rank_lost_impression_share" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "customer": {"currencyCode": "PLN"},
                                "campaign": {
                                    "id": "101",
                                    "name": "Brand Search",
                                    "status": "ENABLED",
                                    "advertisingChannelType": "SEARCH",
                                },
                                "campaignBudget": {
                                    "id": "701",
                                    "name": "Brand budget",
                                    "amountMicros": "30000000",
                                    "period": "DAILY",
                                    "status": "ENABLED",
                                    "hasRecommendedBudget": True,
                                    "recommendedBudgetAmountMicros": "42000000",
                                },
                                "metrics": {
                                    "clicks": "2",
                                    "impressions": "10",
                                    "costMicros": "3000000",
                                    "conversions": "1.5",
                                    "conversionsValue": "250.75",
                                    "searchImpressionShare": 0.73,
                                    "searchBudgetLostImpressionShare": 0.18,
                                    "searchRankLostImpressionShare": 0.09,
                                }
                            },
                            {
                                "customer": {"currencyCode": "PLN"},
                                "campaign": {
                                    "id": "102",
                                    "name": "PMax Feed",
                                    "status": "ENABLED",
                                    "advertisingChannelType": "PERFORMANCE_MAX",
                                },
                                "campaignBudget": {
                                    "id": "702",
                                    "name": "PMax budget",
                                    "amountMicros": "10000000",
                                    "period": "DAILY",
                                    "status": "ENABLED",
                                    "hasRecommendedBudget": False,
                                },
                                "metrics": {
                                    "clicks": "1",
                                    "impressions": "5",
                                    "costMicros": "1000000",
                                    "conversions": "0",
                                    "conversionsValue": "0",
                                }
                            },
                        ]
                    }
                ],
            )
        if "FROM recommendation" in query:
            assert "recommendation.resource_name" in query
            assert "recommendation.type" in query
            assert "recommendation.dismissed" in query
            assert "recommendation.campaign_budget" in query
            assert "recommendation.campaigns" in query
            assert "recommendation.impact" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "recommendation": {
                                    "resourceName": (
                                        "customers/test/recommendations/rec-1"
                                    ),
                                    "type": "CAMPAIGN_BUDGET",
                                    "dismissed": False,
                                    "campaign": "customers/test/campaigns/101",
                                    "campaignBudget": (
                                        "customers/test/campaignBudgets/701"
                                    ),
                                    "campaigns": [
                                        "customers/test/campaigns/101",
                                    ],
                                    "impact": {
                                        "baseMetrics": {
                                            "clicks": "20",
                                            "impressions": "200",
                                            "costMicros": "10000000",
                                        },
                                        "potentialMetrics": {
                                            "clicks": "25",
                                            "impressions": "260",
                                            "costMicros": "12000000",
                                        },
                                    },
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM change_event" in query:
            assert "change_event.resource_name" in query
            assert "change_event.change_date_time" in query
            assert "change_event.change_resource_name" in query
            assert "change_event.client_type" in query
            assert "change_event.change_resource_type" in query
            assert "change_event.resource_change_operation" in query
            assert "change_event.changed_fields" in query
            assert "change_event.campaign" in query
            assert "change_event.user_email" not in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "changeEvent": {
                                    "resourceName": "customers/test/changeEvents/change-1",
                                    "changeDateTime": "2026-06-18 12:30:00.000000",
                                    "changeResourceName": "customers/test/campaigns/101",
                                    "clientType": "GOOGLE_ADS_WEB_CLIENT",
                                    "changeResourceType": "CAMPAIGN",
                                    "resourceChangeOperation": "UPDATE",
                                    "changedFields": {
                                        "paths": [
                                            "campaign.status",
                                            "campaign_budget.amount_micros",
                                        ]
                                    },
                                    "campaign": "customers/test/campaigns/101",
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM ad_group_ad_asset_view" in query:
            assert "ad_group_ad_asset_view.field_type = DEMAND_GEN_CAROUSEL_CARD" in query
            assert "asset.id" in query
            assert "asset.type" in query
            assert "metrics.impressions" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "asset": {
                                    "id": "901",
                                    "type": "DEMAND_GEN_CAROUSEL_CARD",
                                },
                                "adGroupAdAssetView": {
                                    "fieldType": "DEMAND_GEN_CAROUSEL_CARD",
                                },
                                "metrics": {"impressions": "44"},
                            },
                        ]
                    }
                ],
            )
        if "FROM ad_group_ad" in query:
            assert "campaign.advertising_channel_type = DEMAND_GEN" in query
            assert "ad_group_ad.ad.type" in query
            assert "ad_group_ad.ad.final_urls" in query
            assert "demand_gen_multi_asset_ad.marketing_images" in query
            assert "demand_gen_carousel_ad.carousel_cards" in query
            assert "demand_gen_video_responsive_ad.videos" in query
            assert "ad_group_ad.ad.demand_gen_multi_asset_ad.headlines" not in query
            assert "ad_group_ad.ad.demand_gen_multi_asset_ad.descriptions" not in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {
                                    "id": "103",
                                    "name": "Demand Gen Test",
                                    "status": "ENABLED",
                                    "advertisingChannelType": "DEMAND_GEN",
                                },
                                "adGroup": {"id": "203", "name": "DG grupa"},
                                "adGroupAd": {
                                    "status": "ENABLED",
                                    "ad": {
                                        "id": "803",
                                        "type": "DEMAND_GEN_MULTI_ASSET_AD",
                                        "finalUrls": [
                                            "https://www.ekologus.pl/oferta/"
                                        ],
                                        "demandGenMultiAssetAd": {
                                            "marketingImages": [
                                                "customers/123/assets/901",
                                                "customers/123/assets/902",
                                            ],
                                            "squareMarketingImages": [
                                                "customers/123/assets/903",
                                            ],
                                            "portraitMarketingImages": [],
                                            "classicDisplayImages": [],
                                            "logoImages": ["customers/123/assets/904"],
                                        },
                                    },
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM shopping_performance_view" in query:
            assert "segments.product_item_id" in query
            assert "segments.product_title" in query
            assert "metrics.clicks" in query
            assert "metrics.impressions" in query
            assert "metrics.cost_micros" in query
            assert "metrics.conversions" in query
            assert "metrics.conversions_value" in query
            assert "segments.date BETWEEN" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {
                                    "id": "102",
                                    "name": "Shopping sorbenty",
                                    "advertisingChannelType": "PERFORMANCE_MAX",
                                },
                                "segments": {
                                    "productItemId": "SKU-001",
                                    "productTitle": "Sorbent chemiczny 10 kg",
                                },
                                "metrics": {
                                    "clicks": "14",
                                    "impressions": "120",
                                    "costMicros": "2750000",
                                    "conversions": "1.5",
                                    "conversionsValue": "320",
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM shopping_product" in query:
            assert "shopping_product.resource_name" in query
            assert "shopping_product.item_id" in query
            assert "shopping_product.title" in query
            assert "shopping_product.status" in query
            assert "shopping_product.availability" in query
            assert "shopping_product.price_micros" in query
            assert "shopping_product.issues" not in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "shoppingProduct": {
                                    "resourceName": (
                                        "customers/1234567890/"
                                        "shoppingProducts/"  # pragma: allowlist secret
                                        "5519957373~ONLINE~pl~PL~SKU-001"
                                    ),
                                    "merchantCenterId": "5519957373",
                                    "channel": "ONLINE",
                                    "languageCode": "pl",
                                    "feedLabel": "PL",
                                    "itemId": "SKU-001",
                                    "title": "Sorbent chemiczny 10 kg",
                                    "status": "ELIGIBLE",
                                    "availability": "IN_STOCK",
                                    "currencyCode": "PLN",
                                    "priceMicros": "123450000",
                                    "targetCountries": ["PL"],
                                }
                            }
                        ]
                    }
                ],
            )
        if "FROM ad_group_criterion" in query:
            assert "ad_group_criterion.keyword.text" in query
            assert "ad_group_criterion.keyword.match_type" in query
            assert "ad_group_criterion.negative" in query
            assert "ad_group_criterion.status" in query
            assert "ad_group_criterion.type = 'KEYWORD'" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {"id": "101", "name": "Brand Search"},
                                "adGroup": {"id": "201", "name": "BDO"},
                                "adGroupCriterion": {
                                    "criterionId": "301",
                                    "status": "ENABLED",
                                    "negative": False,
                                    "keyword": {
                                        "text": "bdo rejestracja",
                                        "matchType": "PHRASE",
                                    },
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM search_term_view" in query and "BETWEEN" in query:
            assert "segments.date BETWEEN" in query
            assert "LAST_90_DAYS" not in query
            assert "search_term_view.search_term" in query
            assert "metrics.conversions" in query
            assert "metrics.conversions_value" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {"id": "101", "name": "Brand Search"},
                                "adGroup": {"id": "201", "name": "BDO"},
                                "searchTermView": {
                                    "searchTerm": "bdo rejestracja",
                                    "status": "ADDED",
                                },
                                "metrics": {
                                    "clicks": "8",
                                    "impressions": "70",
                                    "costMicros": "9000000",
                                    "conversions": "2",
                                    "conversionsValue": "240",
                                },
                            },
                        ]
                    }
                ],
            )
        assert "FROM search_term_view" in query
        assert "search_term_view.search_term" in query
        assert "metrics.conversions" in query
        assert "metrics.conversions_value" in query
        return httpx.Response(
            200,
            json=[
                {
                    "results": [
                        {
                            "campaign": {"id": "101", "name": "Brand Search"},
                            "adGroup": {"id": "201", "name": "BDO"},
                            "searchTermView": {
                                "searchTerm": "bdo rejestracja",
                                "status": "ADDED",
                            },
                            "metrics": {
                                "clicks": "4",
                                "impressions": "20",
                                "costMicros": "5000000",
                                "conversions": "1",
                                "conversionsValue": "120",
                            },
                        },
                    ]
                }
            ],
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary["row_count"] == 2
    assert result.metric_summary["clicks"] == 3
    assert result.metric_summary["impressions"] == 15
    assert result.metric_summary["cost_micros"] == 4000000
    assert result.metric_summary["conversions"] == 1.5
    assert result.metric_summary["conversion_value"] == 250.75
    assert result.metric_summary["customer_currency_code"] == "PLN"
    assert result.metric_summary["budgeted_campaign_count"] == 2
    assert result.metric_summary["recommended_budget_count"] == 1
    assert result.metric_summary["impression_share_row_count"] == 1
    assert result.metric_summary["search_term_row_count"] == 1
    assert result.metric_summary["search_term_clicks"] == 4
    assert result.metric_summary["search_term_impressions"] == 20
    assert result.metric_summary["search_term_cost_micros"] == 5000000
    assert result.metric_summary["search_term_conversions"] == 1.0
    assert result.metric_summary["search_term_conversion_value"] == 120.0
    assert result.metric_summary["search_term_safety_query"] == "search_term_last_90_days"
    assert result.metric_summary["search_term_safety_row_count"] == 1
    assert result.metric_summary["search_term_safety_clicks"] == 8
    assert result.metric_summary["search_term_safety_impressions"] == 70
    assert result.metric_summary["search_term_safety_cost_micros"] == 9000000
    assert result.metric_summary["search_term_safety_conversions"] == 2.0
    assert result.metric_summary["search_term_safety_conversion_value"] == 240.0
    assert result.metric_summary["shopping_product_performance_status"] == "ready"
    assert result.metric_summary["shopping_product_performance_query"] == (
        "shopping_performance_view_last_30_days"
    )
    assert result.metric_summary["shopping_product_performance_lookback_days"] == 30
    assert result.metric_summary["shopping_product_performance_row_count"] == 1
    assert result.metric_summary["shopping_product_performance_product_count"] == 1
    assert result.metric_summary["shopping_product_clicks"] == 14
    assert result.metric_summary["shopping_product_impressions"] == 120
    assert result.metric_summary["shopping_product_cost_micros"] == 2750000
    assert result.metric_summary["shopping_product_conversions"] == 1.5
    assert result.metric_summary["shopping_product_conversion_value"] == 320.0
    assert result.metric_summary["shopping_product_state_status"] == "ready"
    assert result.metric_summary["shopping_product_state_query"] == (
        "shopping_product_current_state"
    )
    assert result.metric_summary["shopping_product_state_row_count"] == 1
    assert result.metric_summary["shopping_product_state_product_count"] == 1
    assert result.metric_summary["shopping_product_state_eligible_count"] == 1
    assert result.metric_summary["shopping_product_state_availability_values"] == "IN_STOCK"
    assert result.metric_summary["recommendation_query"] == "active_recommendations"
    assert result.metric_summary["recommendation_row_count"] == 1
    assert result.metric_summary["recommendation_campaign_count"] == 1
    assert result.metric_summary["recommendation_impact_row_count"] == 1
    assert result.metric_summary["recommendation_impact_metric_count"] == 6
    assert result.metric_summary["recommendation_types"] == "CAMPAIGN_BUDGET"
    assert result.metric_summary["change_event_query"] == "change_event_last_14_days"
    assert result.metric_summary["change_event_row_count"] == 1
    assert result.metric_summary["change_event_campaign_count"] == 1
    assert result.metric_summary["change_event_resource_types"] == "CAMPAIGN"
    assert result.metric_summary["change_event_operations"] == "UPDATE"
    assert result.metric_summary["change_event_client_types"] == "GOOGLE_ADS_WEB_CLIENT"
    assert result.metric_summary["keyword_match_context_query"] == (
        "ad_group_criterion_keyword_context"
    )
    assert result.metric_summary["keyword_match_context_row_count"] == 1
    assert result.metric_summary["keyword_match_context_keyword_count"] == 1
    assert result.metric_summary["keyword_match_context_negative_count"] == 0
    assert result.metric_summary["keyword_match_context_match_types"] == "PHRASE"
    assert result.metric_summary["keyword_planner_status"] == "ready"
    assert result.metric_summary["keyword_planner_seed_term_count"] == 1
    assert result.metric_summary["keyword_planner_idea_count"] == 1
    assert result.metric_summary["keyword_planner_avg_monthly_searches_max"] == 100
    assert result.metric_summary["keyword_planner_competition_values"] == "MEDIUM"
    assert result.metric_summary["demand_gen_ad_group_ad_status"] == "ready"
    assert result.metric_summary["demand_gen_ad_group_ad_row_count"] == 1
    assert result.metric_summary["demand_gen_multi_asset_ad_count"] == 1
    assert result.metric_summary["demand_gen_final_url_count"] == 1
    assert result.metric_summary["demand_gen_asset_reference_count"] == 4
    assert result.metric_summary["demand_gen_creative_asset_status"] == "ready"
    assert result.metric_summary["demand_gen_creative_asset_row_count"] == 1
    assert result.metric_summary["demand_gen_creative_asset_impressions"] == 44
    assert keyword_planner_requests
    assert any("FROM campaign" in query for query in search_stream_queries)
    assert any("FROM search_term_view" in query for query in search_stream_queries)
    assert any(
        "FROM search_term_view" in query and "segments.date BETWEEN" in query
        for query in search_stream_queries
    )
    assert any("FROM recommendation" in query for query in search_stream_queries)
    assert any("FROM change_event" in query for query in search_stream_queries)
    assert any("FROM ad_group_criterion" in query for query in search_stream_queries)
    assert any("FROM ad_group_ad\n" in query for query in search_stream_queries)
    assert any("FROM ad_group_ad_asset_view" in query for query in search_stream_queries)
    assert any("FROM shopping_performance_view" in query for query in search_stream_queries)
    assert any("FROM shopping_product" in query for query in search_stream_queries)
    assert result.metric_facts[0].dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "campaign_status": "ENABLED",
        "advertising_channel_type": "SEARCH",
        "budget_id": "701",
        "budget_name": "Brand budget",
        "budget_period": "DAILY",
        "budget_status": "ENABLED",
    }
    assert result.metric_facts[0].name == "clicks"
    assert result.metric_facts[0].value == 2
    conversion_fact = next(fact for fact in result.metric_facts if fact.name == "conversions")
    assert conversion_fact.value == 1.5
    conversion_value_fact = next(
        fact for fact in result.metric_facts if fact.name == "conversion_value"
    )
    assert conversion_value_fact.value == 250.75
    currency_fact = next(
        fact for fact in result.metric_facts if fact.name == "account_currency_code"
    )
    assert currency_fact.value == "PLN"
    assert currency_fact.period == "account_context"
    budget_amount_fact = next(
        fact for fact in result.metric_facts if fact.name == "budget_amount_micros"
    )
    assert budget_amount_fact.value == 30000000
    assert budget_amount_fact.dimensions["budget_period"] == "DAILY"
    recommended_budget_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "budget_recommended_amount_micros"
    )
    assert recommended_budget_fact.value == 42000000
    search_term_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_term_clicks"
    )
    assert search_term_fact.value == 4
    assert search_term_fact.dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "ad_group_id": "201",
        "ad_group_name": "BDO",
        "search_term": "bdo rejestracja",
        "search_term_status": "ADDED",
    }
    search_term_conversion_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_term_conversions"
    )
    assert search_term_conversion_fact.value == 1.0
    search_term_safety_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_term_90d_clicks"
    )
    assert search_term_safety_fact.value == 8
    assert search_term_safety_fact.period == "search_term_safety_90d"
    assert search_term_safety_fact.dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "ad_group_id": "201",
        "ad_group_name": "BDO",
        "search_term": "bdo rejestracja",
        "search_term_status": "ADDED",
    }
    keyword_match_type_fact = next(
        fact for fact in result.metric_facts if fact.name == "keyword_match_type"
    )
    assert keyword_match_type_fact.value == "PHRASE"
    assert keyword_match_type_fact.period == "keyword_match_context"
    assert keyword_match_type_fact.dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "ad_group_id": "201",
        "ad_group_name": "BDO",
        "criterion_id": "301",
        "criterion_status": "ENABLED",
        "keyword_negative": "false",
        "keyword_text": "bdo rejestracja",
        "keyword_match_type": "PHRASE",
    }
    shopping_product_clicks_fact = next(
        fact for fact in result.metric_facts if fact.name == "shopping_product_clicks"
    )
    assert shopping_product_clicks_fact.value == 14
    assert shopping_product_clicks_fact.period == "shopping_product_performance_30d"
    assert shopping_product_clicks_fact.dimensions == {
        "campaign_id": "102",
        "campaign_name": "Shopping sorbenty",
        "advertising_channel_type": "PERFORMANCE_MAX",
        "product_id": "SKU-001",
        "item_id": "SKU-001",
        "product_item_id": "SKU-001",
        "product_title": "Sorbent chemiczny 10 kg",
    }
    shopping_product_value_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "shopping_product_conversion_value"
    )
    assert shopping_product_value_fact.value == 320.0
    shopping_product_state_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "shopping_product_state_available"
    )
    assert shopping_product_state_fact.value == 1
    assert shopping_product_state_fact.period == "shopping_product_state"
    assert shopping_product_state_fact.dimensions["product_item_id"] == "SKU-001"
    assert shopping_product_state_fact.dimensions["product_status"] == "ELIGIBLE"
    assert shopping_product_state_fact.dimensions["product_availability"] == "IN_STOCK"
    assert shopping_product_state_fact.dimensions["target_countries"] == "PL"
    shopping_product_price_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "shopping_product_price_micros"
    )
    assert shopping_product_price_fact.value == 123450000
    impression_share_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_impression_share"
    )
    assert impression_share_fact.value == 0.73
    assert impression_share_fact.dimensions["campaign_id"] == "101"
    budget_lost_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "search_budget_lost_impression_share"
    )
    assert budget_lost_fact.value == 0.18
    recommendation_fact = next(
        fact for fact in result.metric_facts if fact.name == "recommendation_available"
    )
    assert recommendation_fact.value == 1
    assert recommendation_fact.period == "recommendation"
    assert recommendation_fact.dimensions == {
        "recommendation_id": "rec-1",
        "recommendation_resource_name": "customers/test/recommendations/rec-1",
        "recommendation_type": "CAMPAIGN_BUDGET",
        "dismissed": "false",
        "campaign_id": "101",
        "campaign_budget_id": "701",
        "recommendation_campaign_count": "1",
    }
    recommendation_impact_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "recommendation_impact_potential_cost_micros"
    )
    assert recommendation_impact_fact.value == 12000000
    assert recommendation_impact_fact.period == "recommendation_impact"
    assert recommendation_impact_fact.dimensions["recommendation_id"] == "rec-1"
    change_event_fact = next(
        fact for fact in result.metric_facts if fact.name == "change_event_available"
    )
    assert change_event_fact.value == 1
    assert change_event_fact.period == "change_history"
    assert change_event_fact.dimensions == {
        "change_event_id": "change-1",
        "change_date_time": "2026-06-18 12:30:00.000000",
        "change_resource_id": "101",
        "client_type": "GOOGLE_ADS_WEB_CLIENT",
        "change_resource_type": "CAMPAIGN",
        "resource_change_operation": "UPDATE",
        "campaign_id": "101",
        "changed_field_count": "2",
        "changed_fields": "campaign.status,campaign_budget.amount_micros",
    }
    changed_field_count_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "change_event_changed_field_count"
    )
    assert changed_field_count_fact.value == 2
    keyword_planner_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "keyword_planner_avg_monthly_searches"
    )
    assert keyword_planner_fact.value == 100
    assert keyword_planner_fact.period == "keyword_planner"
    assert keyword_planner_fact.dimensions == {
        "keyword_idea_text": "bdo szkolenie",
        "seed_terms": "bdo rejestracja",
        "seed_terms_count": "1",
        "language_resource": "languageConstants/1045",
        "geo_target_resource": "geoTargetConstants/2616",
        "competition": "MEDIUM",
    }
    demand_gen_ad_fact = next(
        fact for fact in result.metric_facts if fact.name == "demand_gen_ad_available"
    )
    assert demand_gen_ad_fact.value == 1
    assert demand_gen_ad_fact.period == "demand_gen_ad_inventory"
    assert demand_gen_ad_fact.dimensions == {
        "campaign_id": "103",
        "campaign_name": "Demand Gen Test",
        "campaign_status": "ENABLED",
        "advertising_channel_type": "DEMAND_GEN",
        "ad_group_id": "203",
        "ad_group_name": "DG grupa",
        "ad_id": "803",
        "ad_type": "DEMAND_GEN_MULTI_ASSET_AD",
        "ad_status": "ENABLED",
    }
    demand_gen_asset_count_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "demand_gen_ad_asset_reference_count"
    )
    assert demand_gen_asset_count_fact.value == 4
    assert demand_gen_asset_count_fact.dimensions["ad_id"] == "803"
    demand_gen_asset_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "demand_gen_creative_asset_impressions"
    )
    assert demand_gen_asset_fact.value == 44
    assert demand_gen_asset_fact.period == "demand_gen_creative_asset"
    assert demand_gen_asset_fact.dimensions == {
        "asset_id": "901",
        "asset_type": "DEMAND_GEN_CAROUSEL_CARD",
        "field_type": "DEMAND_GEN_CAROUSEL_CARD",
    }
    serialized = json.dumps(result.metric_summary)
    assert "developer-token-test" not in serialized
    assert "refresh-token-test" not in serialized
    serialized_facts = json.dumps([fact.__dict__ for fact in result.metric_facts])
    assert "user_email" not in serialized_facts
    assert "https://www.ekologus.pl/oferta/" not in serialized_facts


def test_google_ads_shopping_product_performance_falls_back_to_90_day_lookback() -> None:
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "googleads.googleapis.com"
        assert request.url.path == "/v24/customers/1234567890/googleAds:searchStream"
        query = json.loads(request.content.decode())["query"]
        queries.append(query)
        assert "FROM shopping_performance_view" in query
        assert "segments.date BETWEEN" in query
        assert "segments.product_item_id" in query
        if len(queries) == 1:
            return httpx.Response(200, json=[{"results": []}])
        return httpx.Response(
            200,
            json=[
                {
                    "results": [
                        {
                            "campaign": {
                                "id": "102",
                                "name": "Shopping sorbenty",
                                "advertisingChannelType": "PERFORMANCE_MAX",
                            },
                            "segments": {
                                "productItemId": "SKU-001",
                                "productTitle": "Sorbent chemiczny 10 kg",
                            },
                            "metrics": {
                                "clicks": "3",
                                "impressions": "33",
                                "costMicros": "990000",
                                "conversions": "1",
                                "conversionsValue": "120",
                            },
                        },
                    ]
                }
            ],
        )

    summary, facts = _fetch_optional_shopping_product_performance(
        httpx.Client(transport=httpx.MockTransport(handler)),
        {
            "developer_token": "developer-token-test",
            "login_customer_id": "9998887777",
            "customer_id": "1234567890",
            "client_id": "unused",
            "client_secret": "unused",  # pragma: allowlist secret
            "refresh_token": "unused",
        },
        "ya29.mocktoken",
    )

    assert len(queries) == 2
    assert queries[0] != queries[1]
    assert summary["shopping_product_performance_status"] == "ready"
    assert summary["shopping_product_performance_query"] == (
        "shopping_performance_view_last_90_days"
    )
    assert summary["shopping_product_performance_lookback_days"] == 90
    assert summary["shopping_product_performance_zero_row_lookbacks"] == "30"
    assert summary["shopping_product_performance_row_count"] == 1
    assert summary["shopping_product_clicks"] == 3
    clicks_fact = next(fact for fact in facts if fact.name == "shopping_product_clicks")
    assert clicks_fact.period == "shopping_product_performance_90d"
    assert clicks_fact.dimensions["product_item_id"] == "SKU-001"


def test_google_ads_vendor_read_discovers_child_accounts_for_manager_customer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "developer-token-test")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id-test")
    monkeypatch.setenv(
        "GOOGLE_ADS_CLIENT_SECRET",
        "client-secret-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv(
        "GOOGLE_ADS_REFRESH_TOKEN",
        "refresh-token-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "596-895-8639")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "596-895-8639")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        body = request.content.decode()
        if "FROM customer_client" in body:
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "customerClient": {
                                    "clientCustomer": "customers/1112223333",
                                    "manager": False,
                                    "level": "1",
                                    "status": "ENABLED",
                                }
                            }
                        ]
                    }
                ],
                request=request,
            )
        return httpx.Response(
            400,
            json=[
                {
                    "error": {
                        "code": 400,
                        "status": "INVALID_ARGUMENT",
                        "details": [
                            {
                                "requestId": "safe-request-id",
                                "errors": [
                                    {
                                        "errorCode": {
                                            "queryError": "REQUESTED_METRICS_FOR_MANAGER"
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                }
            ],
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps(
        {
            "summary": result.summary,
            "errors": result.errors,
            "metric_summary": result.metric_summary,
            "metric_facts": [
                {"name": fact.name, "value": fact.value, "dimensions": fact.dimensions}
                for fact in result.metric_facts
            ],
        }
    )
    assert result.status == ConnectorRefreshStatus.blocked
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary["customer_client_count"] == 1
    assert result.metric_summary["non_manager_customer_client_count"] == 1
    assert result.metric_facts[0].name == "customer_client_available"
    assert result.metric_facts[0].dimensions["child_customer_id"] == "1112223333"
    assert "REQUESTED_METRICS_FOR_MANAGER" in serialized
    assert "client-secret-test" not in serialized
    assert "refresh-token-test" not in serialized


def test_google_ads_vendor_read_reports_sanitized_oauth_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "developer-token-test")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id-test")
    monkeypatch.setenv(
        "GOOGLE_ADS_CLIENT_SECRET",
        "client-secret-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv(
        "GOOGLE_ADS_REFRESH_TOKEN",
        "refresh-token-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "123-456-7890")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "999-888-7777")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "oauth2.googleapis.com"
        return httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": (
                    "Raw OAuth detail mentioning refresh-token-test and client-secret-test."
                ),
            },
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps(
        {
            "summary": result.summary,
            "errors": result.errors,
            "metric_summary": result.metric_summary,
        }
    )
    assert result.status == ConnectorRefreshStatus.failed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is False
    assert result.metric_summary == {}
    assert "oauth_error=invalid_grant" in serialized
    assert "error_description" not in serialized
    assert "Raw OAuth detail" not in serialized
    assert "refresh-token-test" not in serialized
    assert "client-secret-test" not in serialized


def test_google_ads_vendor_read_reports_sanitized_search_stream_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "developer-token-test")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id-test")
    monkeypatch.setenv(
        "GOOGLE_ADS_CLIENT_SECRET",
        "client-secret-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv(
        "GOOGLE_ADS_REFRESH_TOKEN",
        "refresh-token-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "123-456-7890")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "999-888-7777")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": 400,
                    "status": "INVALID_ARGUMENT",
                    "details": [
                        {
                            "requestId": "safe-request-id",
                            "errors": [
                                {
                                    "errorCode": {"queryError": "BAD_FIELD_NAME"},
                                    "message": (
                                        "Raw detail mentioning refresh-token-test and "
                                        "client-secret-test."
                                    ),
                                }
                            ],
                        }
                    ],
                }
            },
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps({"summary": result.summary, "errors": result.errors})
    assert result.status == ConnectorRefreshStatus.failed
    assert "api_code=400" in serialized
    assert "api_status=INVALID_ARGUMENT" in serialized
    assert "request_id=safe-request-id" in serialized
    assert "ads_error=queryError.BAD_FIELD_NAME" in serialized
    assert "Raw detail" not in serialized
    assert "refresh-token-test" not in serialized
    assert "client-secret-test" not in serialized


def test_google_ads_vendor_read_reports_sanitized_search_stream_list_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "developer-token-test")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "client-id-test")
    monkeypatch.setenv(
        "GOOGLE_ADS_CLIENT_SECRET",
        "client-secret-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv(
        "GOOGLE_ADS_REFRESH_TOKEN",
        "refresh-token-test",  # pragma: allowlist secret
    )
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "123-456-7890")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "999-888-7777")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        return httpx.Response(
            400,
            json=[
                {
                    "error": {
                        "code": 400,
                        "status": "INVALID_ARGUMENT",
                        "details": [
                            {
                                "requestId": "safe-request-id",
                                "errors": [
                                    {
                                        "errorCode": {
                                            "authorizationError": "USER_PERMISSION_DENIED"
                                        },
                                        "message": "Raw detail mentioning refresh-token-test.",
                                    }
                                ],
                            }
                        ],
                    }
                }
            ],
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps({"summary": result.summary, "errors": result.errors})
    assert result.status == ConnectorRefreshStatus.failed
    assert "api_code=400" in serialized
    assert "api_status=INVALID_ARGUMENT" in serialized
    assert "request_id=safe-request-id" in serialized
    assert "ads_error=authorizationError.USER_PERMISSION_DENIED" in serialized
    assert "Raw detail" not in serialized
    assert "refresh-token-test" not in serialized


def test_google_ads_vendor_read_endpoint_persists_metric_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "refresh_success_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, f"{key.lower()}_test")

    def fake_refresh(request: ConnectorRefreshRequest) -> VendorReadResult:
        assert request.mode == ConnectorRefreshMode.vendor_read
        return VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Google Ads zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"row_count": 2, "clicks": 3},
        )

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        fake_refresh,
    )

    response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )
    assert response.status_code == 200
    run = response.json()
    assert run["connector_id"] == "google_ads"
    assert run["status"] == "completed"
    assert run["external_call_attempted"] is True
    assert run["vendor_data_collected"] is True
    assert run["metric_summary"] == {"row_count": 2, "clicks": 3}

    list_response = client.get("/api/connectors/refresh-runs")
    assert list_response.status_code == 200
    assert list_response.json()[0]["metric_summary"] == {"row_count": 2, "clicks": 3}

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert context_response.status_code == 200
    context_runs = {item["id"] for item in context_response.json()["connector_refresh_runs"]}
    assert run["id"] in context_runs


def test_ads_change_history_treats_empty_read_as_ready_no_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_change_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_change_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary=(
                "Odczyt Google Ads zakończony z wierszami kampanii i bez "
                "change_event rows."
            ),
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "row_count": 1,
                "clicks": 9,
                "impressions": 90,
                "cost_micros": 12000000,
                "conversions": 2.5,
                "conversion_value": 450.75,
                "customer_currency_code": "PLN",
                "recommendation_query": "active_recommendations",
                "recommendation_row_count": 1,
                "recommendation_campaign_count": 1,
                "change_event_query": "change_event_last_14_days",
                "change_event_row_count": 0,
            },
            metric_facts=[
                VendorMetricFact(
                    "account_currency_code",
                    "PLN",
                    period="account_context",
                ),
                VendorMetricFact(
                    "clicks",
                    9,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "impressions",
                    90,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "cost_micros",
                    12000000,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversions",
                    2.5,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversion_value",
                    450.75,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "budget_has_recommended_budget",
                    0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "recommendation_available",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": (
                            "customers/test/recommendations/rec-1"
                        ),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
                VendorMetricFact(
                    "recommendation_campaign_count",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": (
                            "customers/test/recommendations/rec-1"
                        ),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "empty change history contract test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    change_history_contract = payload["change_history_read_contract"]
    assert change_history_contract["status"] == "ready"
    assert change_history_contract["change_history_rows"] == []
    assert "change_event_rows" not in change_history_contract["missing_read_contracts"]
    assert "pre_change_performance_window" in change_history_contract[
        "missing_read_contracts"
    ]
    change_impact_contract = payload["change_impact_readiness_contract"]
    assert change_impact_contract["status"] == "blocked"
    assert change_impact_contract["readiness_rows"] == []
    assert change_impact_contract["apply_allowed"] is False
    assert "change_event_rows" in change_impact_contract["missing_read_contracts"]
    assert "pre_change_performance_window" in change_impact_contract[
        "missing_read_contracts"
    ]
    assert "wpływ zmian" in change_impact_contract["blocked_claims"]
    decisions_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    change_history_decision = decisions_by_id["ads_review_change_history"]
    assert change_history_decision["status"] == "ready"
    assert "brak zdarzeń" in change_history_decision["title"]
    assert change_history_decision["metric_tiles"] == {"zmiany": 0, "kampanie": 0}
    assert "change_event_rows" not in change_history_decision["missing_read_contracts"]
    assert change_history_decision["action_ids"] == []
    assert "Nie przypisuj wyników kampanii do zmian" in change_history_decision["next_step"]
    optimizer_contract = payload["optimizer_readiness_contract"]
    assert optimizer_contract["id"] == "ads_optimizer_readiness_contract"
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["api_mutation_ready"] is False
    assert optimizer_contract["apply_allowed"] is False
    assert optimizer_contract["ready_area_count"] == 2
    assert optimizer_contract["blocked_area_count"] >= 1
    assert "change_event_rows" in optimizer_contract["missing_read_contracts"]
    assert "wpływ zmian" in optimizer_contract["blocked_claims"]
    readiness_items_by_id = {
        item["id"]: item for item in optimizer_contract["readiness_items"]
    }
    assert readiness_items_by_id["change_history_impact_review"]["status"] == "blocked"
    assert "change_event_rows" in readiness_items_by_id[
        "change_history_impact_review"
    ]["missing_read_contracts"]
    assert "checklisty readiness" in readiness_items_by_id[
        "change_history_impact_review"
    ]["next_step"]

    for decision_id in (
        "ads_review_campaign_activity",
        "ads_review_derived_kpis",
        "ads_review_budget_context",
        "ads_review_recommendations",
    ):
        decision = decisions_by_id[decision_id]
        assert decision["status"] == "ready"
        assert "change_history" not in decision["missing_read_contracts"]


def test_ads_budget_context_exposes_shared_budget_distribution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_shared_budget.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_shared_budget.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")

    shared_budget_dimensions = {
        "campaign_status": "ENABLED",
        "advertising_channel_type": "SEARCH",
        "budget_id": "701",
        "budget_name": "Shared search budget",
        "budget_period": "DAILY",
        "budget_status": "ENABLED",
    }
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Google Ads zakończony z wierszami wspólnego budżetu.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "row_count": 2,
                "cost_micros": 18000000,
                "customer_currency_code": "PLN",
                "change_event_query": "change_event_last_14_days",
                "change_event_row_count": 0,
            },
            metric_facts=[
                VendorMetricFact("account_currency_code", "PLN", period="account_context"),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                    },
                ),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "102",
                        "campaign_name": "Generic Search",
                    },
                ),
                VendorMetricFact(
                    "cost_micros",
                    12000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                    },
                ),
                VendorMetricFact(
                    "cost_micros",
                    6000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "102",
                        "campaign_name": "Generic Search",
                    },
                ),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "shared budget distribution test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    budget_contract = payload["budget_pacing_read_contract"]
    assert budget_contract["status"] == "ready"
    assert "shared_budget_distribution" not in budget_contract["missing_read_contracts"]
    assert budget_contract["shared_budget_distribution_rows"] == [
        {
            "budget_id": "701",
            "budget_name": "Shared search budget",
            "campaign_count": 2,
            "budget_amount_micros": 30000000,
            "seven_day_budget_micros": 210000000,
            "total_cost_micros_7d": 18000000,
            "spend_to_budget_ratio_7d": 0.085714,
            "campaign_shares": [
                {
                    "campaign_id": "101",
                    "campaign_name": "Brand Search",
                    "campaign_status": "ENABLED",
                    "advertising_channel_type": "SEARCH",
                    "cost_micros_7d": 12000000,
                    "spend_share_7d": 0.666667,
                    "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
                },
                {
                    "campaign_id": "102",
                    "campaign_name": "Generic Search",
                    "campaign_status": "ENABLED",
                    "advertising_channel_type": "SEARCH",
                    "cost_micros_7d": 6000000,
                    "spend_share_7d": 0.333333,
                    "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
                },
            ],
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "blocked_claims": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "wstrzymanie kampanii",
                "zmarnowany budżet",
                "opłacalność",
                "ocena kosztu pozyskania celu",
                "ocena zwrotu z reklam",
                "zapis rekomendacji",
            ],
        }
    ]
    decisions_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    budget_decision = decisions_by_id["ads_review_budget_context"]
    assert "shared_budget_distribution" not in budget_decision["missing_read_contracts"]
    assert budget_decision["shared_budget_distribution_rows"] == budget_contract[
        "shared_budget_distribution_rows"
    ]


def test_ads_diagnostics_exposes_oauth_blocker_without_fake_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_diag_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_diag_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Google Ads zakończony przez nieświeży test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"row_count": 1, "clicks": 99},
            metric_facts=[
                VendorMetricFact(
                    "clicks",
                    99,
                    {"campaign_id": "stale", "campaign_name": "Stale Campaign"},
                )
            ],
        ),
    )
    stale_refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "ads diagnostics stale metric seed"},
    )
    assert stale_refresh_response.status_code == 200

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.failed,
            summary=(
                "Google Ads OAuth token refresh failed with HTTP 401 "
                "(oauth_error=deleted_client)."
            ),
            external_call_attempted=True,
            vendor_data_collected=False,
            errors=[
                "Google Ads OAuth token refresh HTTP 401 (oauth_error=deleted_client)."
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "ads diagnostics blocker test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["live_data_available"] is False
    assert payload["action_ids"] == ["act_configure_google_ads_env"]
    assert payload["blocker_count"] >= 1
    assert payload["latest_refresh"]["status"] == "failed"
    assert payload["latest_refresh"]["vendor_data_collected"] is False
    oauth_section = next(
        section for section in payload["sections"] if section["id"] == "ads_oauth_blocker"
    )
    assert oauth_section["status"] == "blocked"
    assert "oauth_error=deleted_client" in oauth_section["summary"]
    assert "act_configure_google_ads_env" in oauth_section["action_ids"]
    assert oauth_section["metric_facts"] == []
    campaign_section = next(
        section for section in payload["sections"] if section["id"] == "ads_campaign_overview"
    )
    assert campaign_section["status"] == "blocked"
    assert campaign_section["metric_facts"] == []
    search_terms_contract = payload["search_terms_read_contract"]
    assert search_terms_contract["status"] == "blocked"
    assert "search_term_view" in search_terms_contract["missing_read_contracts"]
    assert search_terms_contract["search_term_rows"] == []
    ngram_contract = payload["search_term_ngram_read_contract"]
    assert ngram_contract["status"] == "blocked"
    assert "search_term_view" in ngram_contract["missing_read_contracts"]
    assert ngram_contract["ngram_rows"] == []
    custom_segments_contract = payload["custom_segments_read_contract"]
    assert custom_segments_contract["status"] == "blocked"
    assert "search_term_view" in custom_segments_contract["missing_read_contracts"]
    assert custom_segments_contract["candidates"] == []
    handoff = payload["blocked_handoff"]
    assert handoff["status"] == "blocked"
    assert handoff["title"] == "Google Ads: końcowe przekazanie blokady OAuth"
    assert "oauth_error=deleted_client" in handoff["summary"]
    assert "act_configure_google_ads_env" in handoff["action_ids"]
    assert "google_ads" in handoff["source_connectors"]
    assert "zwrot z reklam" in handoff["blocked_claims"]
    assert any("nie zmyśla metryk Ads" in claim for claim in handoff["allowed_demo_claims"])
    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    brief_metric_item_ids = {
        item["id"]
        for section in brief_response.json()["sections"]
        for item in section["items"]
    }
    assert "brief_metric_google_ads" not in brief_metric_item_ids
    serialized = json.dumps(payload)
    assert "refresh-token-test" not in serialized
    assert "client-secret-test" not in serialized


def test_ads_diagnostics_exposes_live_campaign_metric_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_diag_live_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_diag_live_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Google Ads zakończony przez googleAds:searchStream. Wiersze kampanii: 1.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "row_count": 1,
                "clicks": 9,
                "impressions": 90,
                "cost_micros": 12000000,
                "conversions": 2.5,
                "conversion_value": 450.75,
                "customer_currency_code": "PLN",
                "search_term_row_count": 2,
                "search_term_clicks": 10,
                "search_term_impressions": 100,
                "search_term_cost_micros": 12000000,
                "search_term_conversions": 1.0,
                "search_term_conversion_value": 120.0,
                "search_term_safety_query": "search_term_last_90_days",
                "search_term_safety_row_count": 1,
                "search_term_safety_clicks": 10,
                "search_term_safety_impressions": 120,
                "search_term_safety_cost_micros": 8000000,
                "search_term_safety_conversions": 0.0,
                "search_term_safety_conversion_value": 0.0,
                "recommendation_query": "active_recommendations",
                "recommendation_row_count": 1,
                "recommendation_campaign_count": 1,
                "recommendation_impact_row_count": 1,
                "recommendation_impact_metric_count": 6,
                "recommendation_types": "CAMPAIGN_BUDGET",
                "impression_share_row_count": 1,
                "change_event_query": "change_event_last_14_days",
                "change_event_row_count": 1,
                "change_event_campaign_count": 1,
                "change_event_resource_types": "CAMPAIGN",
                "change_event_operations": "UPDATE",
                "change_event_client_types": "GOOGLE_ADS_WEB_CLIENT",
                "keyword_match_context_query": "ad_group_criterion_keyword_context",
                "keyword_match_context_row_count": 1,
                "keyword_match_context_keyword_count": 1,
                "keyword_match_context_negative_count": 0,
                "keyword_match_context_match_types": "BROAD",
                "keyword_planner_status": "ready",
                "keyword_planner_seed_term_count": 2,
                "keyword_planner_idea_count": 1,
                "keyword_planner_avg_monthly_searches_max": 100,
                "keyword_planner_competition_values": "MEDIUM",
            },
            metric_facts=[
                VendorMetricFact(
                    "account_currency_code",
                    "PLN",
                    period="account_context",
                ),
                VendorMetricFact(
                    "clicks",
                    9,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "impressions",
                    90,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "cost_micros",
                    12000000,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversions",
                    2.5,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversion_value",
                    450.75,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "budget_has_recommended_budget",
                    1,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "budget_recommended_amount_micros",
                    42000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "search_impression_share",
                    0.73,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                    },
                ),
                VendorMetricFact(
                    "search_budget_lost_impression_share",
                    0.18,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                    },
                ),
                VendorMetricFact(
                    "search_rank_lost_impression_share",
                    0.09,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                    },
                ),
                VendorMetricFact(
                    "recommendation_available",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
                VendorMetricFact(
                    "recommendation_campaign_count",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
                VendorMetricFact(
                    "recommendation_impact_base_clicks",
                    20,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_potential_clicks",
                    25,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_base_impressions",
                    200,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_potential_impressions",
                    260,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_base_cost_micros",
                    10000000,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": (
                            "customers/test/recommendations/rec-1"
                        ),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_potential_cost_micros",
                    12000000,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": (
                            "customers/test/recommendations/rec-1"
                        ),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "change_event_available",
                    1,
                    {
                        "change_event_id": "change-1",
                        "change_date_time": "2026-06-18 12:30:00.000000",
                        "change_resource_id": "101",
                        "client_type": "GOOGLE_ADS_WEB_CLIENT",
                        "change_resource_type": "CAMPAIGN",
                        "resource_change_operation": "UPDATE",
                        "campaign_id": "101",
                        "changed_field_count": "2",
                        "changed_fields": "campaign.status,campaign_budget.amount_micros",
                    },
                    period="change_history",
                ),
                VendorMetricFact(
                    "change_event_changed_field_count",
                    2,
                    {
                        "change_event_id": "change-1",
                        "change_date_time": "2026-06-18 12:30:00.000000",
                        "change_resource_id": "101",
                        "client_type": "GOOGLE_ADS_WEB_CLIENT",
                        "change_resource_type": "CAMPAIGN",
                        "resource_change_operation": "UPDATE",
                        "campaign_id": "101",
                        "changed_field_count": "2",
                        "changed_fields": "campaign.status,campaign_budget.amount_micros",
                    },
                    period="change_history",
                ),
                VendorMetricFact(
                    "search_term_clicks",
                    4,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_impressions",
                    40,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_cost_micros",
                    7000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversions",
                    1.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversion_value",
                    120.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_clicks",
                    6,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_impressions",
                    60,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_cost_micros",
                    5000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversions",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversion_value",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_90d_clicks",
                    10,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_impressions",
                    120,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_cost_micros",
                    8000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_conversions",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_conversion_value",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "keyword_match_context_available",
                    1,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "criterion_id": "401",
                        "criterion_status": "ENABLED",
                        "keyword_negative": "false",
                        "keyword_text": "odpady",
                        "keyword_match_type": "BROAD",
                    },
                    period="keyword_match_context",
                ),
                VendorMetricFact(
                    "keyword_match_type",
                    "BROAD",
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "criterion_id": "401",
                        "criterion_status": "ENABLED",
                        "keyword_negative": "false",
                        "keyword_text": "odpady",
                        "keyword_match_type": "BROAD",
                    },
                    period="keyword_match_context",
                ),
                VendorMetricFact(
                    "keyword_match_context_negative",
                    0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "criterion_id": "401",
                        "criterion_status": "ENABLED",
                        "keyword_negative": "false",
                        "keyword_text": "odpady",
                        "keyword_match_type": "BROAD",
                    },
                    period="keyword_match_context",
                ),
                VendorMetricFact(
                    "keyword_planner_idea_available",
                    1,
                    {
                        "keyword_idea_text": "bdo szkolenie",
                        "seed_terms": "bdo rejestracja, odpady cena",
                        "seed_terms_count": "2",
                        "language_resource": "languageConstants/1045",
                        "geo_target_resource": "geoTargetConstants/2616",
                        "competition": "MEDIUM",
                    },
                    period="keyword_planner",
                ),
                VendorMetricFact(
                    "keyword_planner_avg_monthly_searches",
                    100,
                    {
                        "keyword_idea_text": "bdo szkolenie",
                        "seed_terms": "bdo rejestracja, odpady cena",
                        "seed_terms_count": "2",
                        "language_resource": "languageConstants/1045",
                        "geo_target_resource": "geoTargetConstants/2616",
                        "competition": "MEDIUM",
                    },
                    period="keyword_planner",
                ),
                VendorMetricFact(
                    "keyword_planner_competition_index",
                    55,
                    {
                        "keyword_idea_text": "bdo szkolenie",
                        "seed_terms": "bdo rejestracja, odpady cena",
                        "seed_terms_count": "2",
                        "language_resource": "languageConstants/1045",
                        "geo_target_resource": "geoTargetConstants/2616",
                        "competition": "MEDIUM",
                    },
                    period="keyword_planner",
                ),
                *large_ads_metric_fact_fillers(),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "ads diagnostics live test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is True
    assert payload["latest_refresh"]["status"] == "completed"
    assert payload["blocked_handoff"] is None
    read_contract = payload["campaign_read_contract"]
    assert read_contract["status"] == "ready"
    assert read_contract["allowed_metrics"] == [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    assert "conversions" not in read_contract["missing_read_contracts"]
    assert "conversion_value" not in read_contract["missing_read_contracts"]
    assert "recommendations" not in read_contract["missing_read_contracts"]
    assert "impression_share" not in read_contract["missing_read_contracts"]
    assert "change_history" not in read_contract["missing_read_contracts"]
    assert "zwrot z reklam" in read_contract["blocked_claims"]
    assert "search_term_view" not in read_contract["missing_read_contracts"]
    assert read_contract["campaign_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "advertising_channel_type": "SEARCH",
            "clicks": 9,
            "impressions": 90,
            "cost_micros": 12000000,
            "conversions": 2.5,
            "conversion_value": 450.75,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": read_contract["campaign_rows"][0]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "marnowanie budżetu na zapytaniach",
                "zmarnowany budżet",
            ],
            "target_status": "no_target",
            "target_status_label": "brak celu",
            "review_priority": "wysokie",
            "review_score": 50,
            "review_reason": read_contract["campaign_rows"][0]["review_reason"],
                "human_review_gates": [
                    "review_campaign_goal",
                    "review_conversion_quality",
                    "review_budget_context",
                    "review_search_terms_before_budget_decision",
                    "human_strategy_review",
                ],
                "human_review_gate_labels": [
                    "sprawdzenie celu kampanii",
                    "sprawdzenie jakości konwersji",
                    "sprawdzenie kontekstu budżetu",
                    "wyszukiwane hasła przed decyzją budżetową",
                    "ocena strategii przez człowieka",
                ],
            }
        ]
    assert "Kolejność oceny kampanii" in read_contract["campaign_rows"][0]["review_reason"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "ads_operator_summary"
    assert operator_summary["title"] == "Co marketer ma sprawdzić teraz w Google Ads"
    assert operator_summary["top_decision_ids"] == [
        decision["id"]
        for decision in sorted(
            payload["decision_queue"],
            key=lambda decision: (
                0 if decision["status"] == "ready" else 1,
                decision["priority"],
            ),
        )[:5]
    ]
    assert operator_summary["campaign_count"] == len(read_contract["campaign_rows"])
    assert operator_summary["search_term_count"] == len(
        payload["search_terms_read_contract"]["search_term_rows"]
    )
    assert operator_summary["total_clicks"] == 9
    assert operator_summary["total_impressions"] == 90
    assert operator_summary["total_cost_micros"] == 12000000
    assert operator_summary["total_conversions"] == 2.5
    assert operator_summary["total_conversion_value"] == 450.75
    assert operator_summary["ready_area_count"] == payload["optimizer_readiness_contract"][
        "ready_area_count"
    ]
    assert operator_summary["blocked_area_count"] == payload["optimizer_readiness_contract"][
        "blocked_area_count"
    ]
    assert "clicks" in operator_summary["allowed_metrics"]
    assert "google_ads" in operator_summary["source_connectors"]
    assert refresh_response.json()["evidence_ids"][-1] in operator_summary["evidence_ids"]
    assert "act_prepare_ads_campaign_review_queue" in operator_summary["action_ids"]
    assert "zwrot z reklam" in operator_summary["blocked_claims"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    marketer_text = "\n".join(
        [
            payload["campaign_read_contract"]["summary"],
            payload["search_terms_read_contract"]["summary"],
            payload["search_term_review_summary_contract"]["summary"],
            payload["search_term_ngram_read_contract"]["summary"],
            payload["search_term_safety_read_contract"]["summary"],
            *[decision["summary"] for decision in payload["decision_queue"]],
        ]
    )
    assert "koszt_micros=" not in marketer_text
    assert "koszt=12 PLN" in marketer_text
    campaign_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_campaign_activity"
    )
    assert campaign_decision["metric_tiles"]["koszt"] == "12 PLN"
    budget_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_budget_context"
    )
    assert budget_decision["metric_tiles"]["koszt 7 dni"] == "12 PLN"
    currency_contract = payload["account_currency_read_contract"]
    assert currency_contract["status"] == "ready"
    assert currency_contract["currency_code"] == "PLN"
    assert currency_contract["allowed_metrics"] == ["account_currency_code"]
    assert currency_contract["missing_read_contracts"] == []
    assert "zmiana budżetu" in currency_contract["blocked_claims"]
    business_context_contract = payload["business_context_read_contract"]
    assert business_context_contract["status"] == "blocked"
    assert business_context_contract["profit_margin"] is None
    assert business_context_contract["business_goal"] is None
    assert business_context_contract["budget_goal"] is None
    assert business_context_contract["target_roas"] is None
    assert business_context_contract["target_cpa_micros"] is None
    assert business_context_contract["configured_sources"] == []
    assert business_context_contract["business_policy_ids"] == [
        "complete_business_context_before_ads_verdicts",
        "block_target_verdict_until_roas_or_cpa_confirmed",
        "block_target_verdict_until_strategy_review_approved",
    ]
    assert business_context_contract["operator_review_gates"] == [
        "human_strategy_review",
        "configure_profit_margin_or_value_model",
        "configure_business_goal",
        "configure_human_budget_goal",
        "confirm_target_roas_or_cpa",
    ]
    assert business_context_contract["operator_review_gate_labels"] == [
        "ocena strategii przez człowieka",
        "uzupełnienie marży albo modelu wartości",
        "uzupełnienie celu biznesowego",
        "uzupełnienie celu budżetu",
        "potwierdzenie docelowego zwrotu z reklam albo kosztu pozyskania celu",
    ]
    assert business_context_contract["allowed_metrics"] == []
    assert business_context_contract["missing_read_contracts"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert business_context_contract["target_interpretation"]["status"] == "blocked"
    assert business_context_contract["target_interpretation"]["allowed_uses"] == []
    assert business_context_contract["target_interpretation"]["missing_requirements"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    expected_business_context_actions = [
        ADS_BUSINESS_CONTEXT_ACTION_ID,
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]
    assert business_context_contract["target_interpretation"]["action_ids"] == [
        *expected_business_context_actions
    ]
    assert business_context_contract["target_interpretation"]["apply_allowed"] is False
    assert "skalowanie budżetu" in business_context_contract["blocked_claims"]
    assert business_context_contract["metric_tiles"]["marża"] == "brak"
    business_context_section = next(
        section for section in payload["sections"] if section["id"] == "ads_business_context"
    )
    assert business_context_section["status"] == "blocked"
    assert business_context_section["action_ids"] == expected_business_context_actions
    business_context_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_business_context"
    )
    assert business_context_decision["status"] == "blocked"
    assert business_context_decision["decision_type"] == "review_business_context"
    assert business_context_decision["missing_read_contracts"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert business_context_decision["metric_tiles"] == {
        "braki": 5,
        "blokady": 6,
        "ustawione pola": 0,
        "warunki sprawdzenia": 5,
        "polityki": 3,
    }
    assert business_context_decision["operator_review_gates"] == (
        business_context_contract["operator_review_gates"]
    )
    assert business_context_decision["operator_review_gate_labels"] == (
        business_context_contract["operator_review_gate_labels"]
    )
    assert operator_summary["operator_review_gate_labels"]
    assert "human_strategy_review" not in operator_summary["operator_review_gate_labels"]
    assert business_context_decision["action_ids"] == expected_business_context_actions
    derived_kpi_contract = payload["derived_kpi_read_contract"]
    assert derived_kpi_contract["status"] == "ready"
    assert derived_kpi_contract["allowed_metrics"] == [
        "ctr",
        "average_cpc_micros",
        "conversion_rate",
        "cost_per_conversion_micros",
        "roas",
        "value_per_conversion",
    ]
    assert "profit_margin" in derived_kpi_contract["missing_read_contracts"]
    assert "account_currency" not in derived_kpi_contract["missing_read_contracts"]
    assert "recommendations" not in derived_kpi_contract["missing_read_contracts"]
    assert "impression_share" not in derived_kpi_contract["missing_read_contracts"]
    assert "change_history" not in derived_kpi_contract["missing_read_contracts"]
    assert "opłacalność" in derived_kpi_contract["blocked_claims"]
    assert derived_kpi_contract["kpi_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "ctr": 0.1,
            "average_cpc_micros": 1333333.333333,
            "conversion_rate": 0.277778,
            "cost_per_conversion_micros": 4800000,
            "roas": 37.5625,
            "value_per_conversion": 180.3,
            "target_roas": None,
            "roas_vs_target": None,
            "target_cpa_micros": None,
            "cpa_vs_target_micros": None,
            "target_status": "no_target",
            "target_status_label": "brak celu",
            "target_review_priority": 90,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "source_metric_names": [
                "clicks",
                "conversion_value",
                "conversions",
                "cost_micros",
                "impressions",
            ],
            "missing_metrics": [],
            "blocked_claims": [
                "opłacalność",
                "skalowanie budżetu",
                "zmarnowany budżet",
                "zapis rekomendacji",
            ],
        }
    ]
    live_section = next(
        section for section in payload["sections"] if section["id"] == "ads_live_data_status"
    )
    assert live_section["status"] == "ready"
    campaign_section = next(
        section for section in payload["sections"] if section["id"] == "ads_campaign_overview"
    )
    assert campaign_section["status"] == "ready"
    assert campaign_section["title"] == "Aktywność kampanii Google Ads"
    derived_kpi_section = next(
        section for section in payload["sections"] if section["id"] == "ads_derived_kpi"
    )
    assert derived_kpi_section["status"] == "ready"
    assert "rentowności" in derived_kpi_section["diagnosis"]
    budget_contract = payload["budget_pacing_read_contract"]
    assert budget_contract["status"] == "ready"
    assert budget_contract["allowed_metrics"] == [
        "budget_amount_micros",
        "cost_micros_7d",
        "seven_day_budget_micros",
        "spend_to_budget_ratio_7d",
        "shared_budget_distribution",
        "budget_has_recommended_budget",
        "budget_recommended_amount_micros",
    ]
    assert "skalowanie budżetu" in budget_contract["blocked_claims"]
    assert "budget_pacing" not in budget_contract["missing_read_contracts"]
    assert "recommendations" not in budget_contract["missing_read_contracts"]
    assert "impression_share" not in budget_contract["missing_read_contracts"]
    assert "change_history" not in budget_contract["missing_read_contracts"]
    assert "budget_apply_preview" not in budget_contract["missing_read_contracts"]
    assert "shared_budget_distribution" not in budget_contract["missing_read_contracts"]
    assert budget_contract["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert budget_contract["payload_preview"] == [
        {
            "id": "budget_apply_preview_101_701",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_budget_id": "701",
            "campaign_budget_name": "Brand budget",
            "operation_type": "CampaignBudgetOperation",
            "current_budget_amount_micros": 30000000,
            "proposed_budget_amount_micros": 42000000,
            "proposed_budget_delta_micros": 12000000,
            "reason": budget_contract["payload_preview"][0]["reason"],
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "source_metric_names": budget_contract["payload_preview"][0][
                "source_metric_names"
            ],
            "required_validation": [
                "review_campaign_activity",
                "verify_account_currency",
                "budget_pacing",
                "impression_share",
                "change_history",
                "human_budget_goal",
                "campaign_budget_apply_safety",
                "campaign_budget_operation_preview",
                "human_confirm_before_apply",
            ],
            "blocked_claims": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "wstrzymanie kampanii",
                "zmarnowany budżet",
                "opłacalność",
                "ocena kosztu pozyskania celu",
                "ocena zwrotu z reklam",
                "zapis rekomendacji",
            ],
            "safety_review": budget_contract["payload_preview"][0]["safety_review"],
            "api_mutation_ready": False,
            "apply_allowed": False,
            "destructive": False,
        }
    ]
    budget_safety_review = budget_contract["payload_preview"][0]["safety_review"]
    assert budget_safety_review["safety_contract"] == "campaign_budget_apply_safety_v1"
    assert budget_safety_review["status"] == "blocked"
    assert budget_safety_review["status_label"] == "zablokowane"
    assert budget_safety_review["max_allowed_delta_percent"] == 0.3
    assert budget_safety_review["proposed_delta_percent"] == 0.4
    assert "budget_delta_within_30_percent" in budget_safety_review[
        "missing_requirements"
    ]
    assert budget_safety_review["api_mutation_ready"] is False
    assert budget_safety_review["apply_allowed"] is False
    assert budget_safety_review["destructive"] is False
    assert budget_contract["budget_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "advertising_channel_type": "SEARCH",
            "budget_id": "701",
            "budget_name": "Brand budget",
            "budget_period": "DAILY",
            "budget_status": "ENABLED",
            "budget_amount_micros": 30000000,
            "cost_micros_7d": 12000000,
            "seven_day_budget_micros": 210000000,
            "spend_to_budget_ratio_7d": 0.057143,
            "has_recommended_budget": True,
            "recommended_budget_amount_micros": 42000000,
            "recommended_budget_delta_micros": 12000000,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": budget_contract["budget_rows"][0]["metric_facts"],
            "payload_preview": budget_contract["payload_preview"][0],
            "missing_metrics": [],
            "blocked_claims": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "wstrzymanie kampanii",
                "zmarnowany budżet",
                "opłacalność",
                "ocena kosztu pozyskania celu",
                "ocena zwrotu z reklam",
                "zapis rekomendacji",
            ],
        }
    ]
    assert budget_contract["shared_budget_distribution_rows"] == []
    budget_section = next(
        section for section in payload["sections"] if section["id"] == "ads_budget_pacing"
    )
    assert budget_section["status"] == "ready"
    assert "skalowania" in budget_section["diagnosis"]
    assert budget_section["knowledge_card_ids"] == ["card_google_ads_budget_review_playbook"]
    assert budget_section["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]
    recommendations_contract = payload["recommendations_read_contract"]
    assert recommendations_contract["status"] == "ready"
    assert recommendations_contract["allowed_metrics"] == [
        "recommendation_available",
        "recommendation_campaign_count",
        "recommendation_impact_base_clicks",
        "recommendation_impact_potential_clicks",
        "recommendation_impact_base_impressions",
        "recommendation_impact_potential_impressions",
        "recommendation_impact_base_cost_micros",
        "recommendation_impact_potential_cost_micros",
        "recommendation_impact_base_conversions",
        "recommendation_impact_potential_conversions",
        "recommendation_impact_base_conversion_value",
        "recommendation_impact_potential_conversion_value",
    ]
    assert "recommendations" not in recommendations_contract["missing_read_contracts"]
    assert "recommendation_impact_preview" not in recommendations_contract[
        "missing_read_contracts"
    ]
    assert "recommendation_apply_preview" not in recommendations_contract[
        "missing_read_contracts"
    ]
    assert "impression_share" not in recommendations_contract["missing_read_contracts"]
    assert "change_history" not in recommendations_contract["missing_read_contracts"]
    assert "human_strategy_review" not in recommendations_contract[
        "missing_read_contracts"
    ]
    assert recommendations_contract["operator_review_gates"] == [
        "human_strategy_review",
        "review_recommendation_type",
        "review_impact_metrics",
        "review_change_history",
        "review_business_goal",
        "recommendation_apply_preview",
        "google_ads_rmf_compliance_review",
        "human_confirm_before_apply",
    ]
    assert recommendations_contract["action_ids"] == [
        "act_prepare_google_ads_recommendation_review_queue"
    ]
    assert "zapis rekomendacji" in recommendations_contract["blocked_claims"]
    assert recommendations_contract["recommendation_rows"] == [
        {
            "recommendation_id": "rec-1",
            "recommendation_resource_name": "customers/test/recommendations/rec-1",
            "recommendation_type": "CAMPAIGN_BUDGET",
            "review_priority": "pilne",
            "review_score": 70,
            "review_reason": recommendations_contract["recommendation_rows"][0][
                "review_reason"
            ],
                "human_review_gates": [
                    "sprawdź typ rekomendacji",
                    "sprawdź metryki wpływu",
                    "porównaj z historią zmian",
                    "porównaj z celem biznesowym",
                    "zweryfikuj RMF/compliance",
                    "potwierdź człowiekiem przed zapisem",
                ],
                "human_review_gate_labels": [
                    "sprawdź typ rekomendacji",
                    "sprawdź metryki wpływu",
                    "porównaj z historią zmian",
                    "porównaj z celem biznesowym",
                    "zweryfikuj RMF/compliance",
                    "potwierdź człowiekiem przed zapisem",
                ],
                "dismissed": False,
            "campaign_id": "101",
            "campaign_budget_id": "701",
            "campaign_count": 1,
            "impact_available": True,
            "base_clicks": 20,
            "potential_clicks": 25,
            "delta_clicks": 5,
            "base_impressions": 200,
            "potential_impressions": 260,
            "delta_impressions": 60,
            "base_cost_micros": 10000000,
            "potential_cost_micros": 12000000,
            "delta_cost_micros": 2000000,
            "base_conversions": None,
            "potential_conversions": None,
            "delta_conversions": None,
            "base_conversion_value": None,
            "potential_conversion_value": None,
            "delta_conversion_value": None,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": recommendations_contract["recommendation_rows"][0][
                "metric_facts"
            ],
            "payload_preview": recommendations_contract["payload_preview"][0],
            "missing_metrics": [],
            "blocked_claims": [
                "zapis rekomendacji",
                "automatyczne przyjęcie rekomendacji",
                "zmiana budżetu",
                "zapis zmian kampanii",
            ],
        }
    ]
    assert "kolejność przeglądu rekomendacji" in recommendations_contract[
        "recommendation_rows"
    ][0]["review_reason"]
    assert "nie zgoda na zapis zmian" in recommendations_contract[
        "recommendation_rows"
    ][0]["review_reason"]
    assert recommendations_contract["payload_preview"] == [
        {
            "id": "recommendation_apply_preview_rec-1",
            "recommendation_id": "rec-1",
            "recommendation_resource_name": "customers/test/recommendations/rec-1",
            "recommendation_type": "CAMPAIGN_BUDGET",
            "campaign_id": "101",
            "campaign_budget_id": "701",
            "operation_type": "ApplyRecommendationOperation",
            "reason": recommendations_contract["payload_preview"][0]["reason"],
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "source_metric_names": recommendations_contract["payload_preview"][0][
                "source_metric_names"
            ],
            "required_validation": [
                "review_recommendation_type",
                "review_impact_metrics",
                "review_change_history",
                "review_business_goal",
                "recommendation_apply_preview",
                "google_ads_rmf_compliance_review",
                "human_confirm_before_apply",
            ],
            "blocked_claims": [
                "zapis rekomendacji",
                "automatyczne przyjęcie rekomendacji",
                "zmiana budżetu",
                "zapis zmian kampanii",
                "obietnica poprawy wyniku",
            ],
            "api_mutation_ready": False,
            "apply_allowed": False,
            "destructive": False,
        }
    ]
    recommendations_section = next(
        section for section in payload["sections"] if section["id"] == "ads_recommendations"
    )
    assert recommendations_section["status"] == "ready"
    assert recommendations_section["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert recommendations_section["expert_rule_ids"] == [
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]
    impression_share_contract = payload["impression_share_read_contract"]
    assert impression_share_contract["status"] == "ready"
    assert impression_share_contract["allowed_metrics"] == [
        "search_impression_share",
        "search_budget_lost_impression_share",
        "search_rank_lost_impression_share",
    ]
    assert "impression_share" not in impression_share_contract["missing_read_contracts"]
    assert "change_history" not in impression_share_contract["missing_read_contracts"]
    assert "zmiana budżetu" in impression_share_contract["blocked_claims"]
    assert impression_share_contract["impression_share_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "advertising_channel_type": "SEARCH",
            "search_impression_share": 0.73,
            "search_budget_lost_impression_share": 0.18,
            "search_rank_lost_impression_share": 0.09,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": impression_share_contract["impression_share_rows"][0][
                "metric_facts"
            ],
            "missing_metrics": [],
            "blocked_claims": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "zmarnowany budżet",
                "obietnica poprawy wyniku",
            ],
        }
    ]
    impression_share_section = next(
        section for section in payload["sections"] if section["id"] == "ads_impression_share"
    )
    assert impression_share_section["status"] == "ready"
    assert impression_share_section["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert impression_share_section["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_principles_v1",
    ]
    campaign_triage_contract = payload["campaign_triage_read_contract"]
    assert campaign_triage_contract["status"] == "ready"
    assert campaign_triage_contract["title"] == "Kolejność oceny kampanii Ads"
    assert campaign_triage_contract["allowed_metrics"] == [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
        "ctr",
        "average_cpc_micros",
        "conversion_rate",
        "cost_per_conversion_micros",
        "roas",
        "spend_to_budget_ratio_7d",
        "search_budget_lost_impression_share",
        "recommendation_count",
    ]
    assert campaign_triage_contract["missing_read_contracts"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert campaign_triage_contract["action_ids"] == [
        "act_prepare_ads_campaign_review_queue"
    ]
    assert "zmarnowany budżet" in campaign_triage_contract["blocked_claims"]
    assert campaign_triage_contract["triage_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "advertising_channel_type": "SEARCH",
            "review_priority": "wysokie",
            "review_score": campaign_triage_contract["triage_rows"][0]["review_score"],
            "review_reason": campaign_triage_contract["triage_rows"][0][
                "review_reason"
            ],
            "next_step": campaign_triage_contract["triage_rows"][0]["next_step"],
            "target_status": "no_target",
            "target_status_label": "brak celu",
            "clicks": 9,
            "impressions": 90,
            "cost_micros": 12000000,
            "conversions": 2.5,
            "conversion_value": 450.75,
            "ctr": 0.1,
            "average_cpc_micros": 1333333.333333,
            "conversion_rate": 0.277778,
            "cost_per_conversion_micros": 4800000,
            "roas": 37.5625,
            "spend_to_budget_ratio_7d": 0.057143,
            "search_budget_lost_impression_share": 0.18,
            "recommendation_count": 1,
            "recommendation_types": ["CAMPAIGN_BUDGET"],
            "has_budget_apply_preview": True,
            "has_recommendation_apply_preview": True,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "action_ids": ["act_prepare_ads_campaign_review_queue"],
            "source_metric_names": campaign_triage_contract["triage_rows"][0][
                "source_metric_names"
            ],
            "missing_read_contracts": [
                "profit_margin",
                "business_goal",
                "human_budget_goal",
                "target_roas_or_cpa",
                "human_strategy_review",
            ],
            "blocked_claims": [
                "zmarnowany budżet",
                "opłacalność",
                "skalowanie budżetu",
                "zmiana budżetu",
                "zapis rekomendacji",
                "zapis zmian kampanii",
            ],
                "human_review_gates": [
                    "review_campaign_goal",
                    "review_conversion_quality",
                    "review_budget_context",
                    "review_search_terms_before_budget_decision",
                    "human_strategy_review",
                    "review_recommendation_type",
                    "review_impact_metrics",
                    "review_change_history",
                    "review_business_goal",
                    "campaign_budget_apply_safety",
                ],
                "human_review_gate_labels": [
                    "sprawdzenie celu kampanii",
                    "sprawdzenie jakości konwersji",
                    "sprawdzenie kontekstu budżetu",
                    "wyszukiwane hasła przed decyzją budżetową",
                    "ocena strategii przez człowieka",
                    "sprawdzenie typu rekomendacji",
                    "sprawdzenie wpływu rekomendacji",
                    "sprawdzenie historii zmian",
                    "sprawdzenie celu biznesowego",
                    "bezpieczeństwo zmiany budżetu",
                ],
            }
        ]
    assert "Kolejność oceny kampanii" in campaign_triage_contract["triage_rows"][0][
        "review_reason"
    ]
    assert "nie jest ocena zmarnowanego budżetu" in campaign_triage_contract["summary"]
    optimizer_contract = payload["optimizer_readiness_contract"]
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["apply_allowed"] is False
    assert "zapis zmian kampanii" in optimizer_contract["blocked_claims"]
    assert "change_event_rows" not in optimizer_contract["missing_read_contracts"]
    assert "pre_change_performance_window" in optimizer_contract[
        "missing_read_contracts"
    ]
    optimizer_items_by_id = {
        item["id"]: item for item in optimizer_contract["readiness_items"]
    }
    assert optimizer_items_by_id["campaign_review_queue"]["status"] == "ready"
    assert optimizer_items_by_id["change_history_impact_review"]["status"] == "blocked"
    assert "pre_change_performance_window" in optimizer_items_by_id[
        "change_history_impact_review"
    ]["missing_read_contracts"]
    change_history_contract = payload["change_history_read_contract"]
    assert change_history_contract["status"] == "ready"
    assert change_history_contract["action_ids"] == [CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_contract["allowed_metrics"] == [
        "change_event_available",
        "change_event_changed_field_count",
    ]
    assert "change_history" not in change_history_contract["missing_read_contracts"]
    assert "wpływ zmian" in change_history_contract["blocked_claims"]
    assert change_history_contract["change_history_rows"] == [
        {
            "change_event_id": "change-1",
            "change_date_time": "2026-06-18 12:30:00.000000",
            "change_resource_id": "101",
            "change_resource_type": "CAMPAIGN",
            "resource_change_operation": "UPDATE",
            "client_type": "GOOGLE_ADS_WEB_CLIENT",
            "campaign_id": "101",
            "changed_field_count": 2,
            "changed_fields": ["campaign.status", "campaign_budget.amount_micros"],
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": change_history_contract["change_history_rows"][0][
                "metric_facts"
            ],
            "missing_metrics": [],
            "blocked_claims": [
                "wpływ zmian",
                "obietnica poprawy wyniku",
                "zmiana budżetu",
                "zapis zmian kampanii",
            ],
        }
    ]
    change_impact_contract = payload["change_impact_readiness_contract"]
    assert change_impact_contract["id"] == "ads_change_impact_readiness_contract"
    assert change_impact_contract["status"] == "blocked"
    assert change_impact_contract["apply_allowed"] is False
    assert "snapshot kampanii" not in change_impact_contract["next_step"]
    assert "aktualny odczyt kampanii" in change_impact_contract["next_step"]
    assert "wpływ zmian" in change_impact_contract["blocked_claims"]
    assert "change_event_rows" not in change_impact_contract["missing_read_contracts"]
    assert "current_campaign_snapshot" not in change_impact_contract[
        "missing_read_contracts"
    ]
    assert "pre_change_performance_window" in change_impact_contract[
        "missing_read_contracts"
    ]
    assert change_impact_contract["allowed_metrics"] == [
        "change_event_available",
        "change_event_changed_field_count",
        "current_campaign_clicks",
        "current_campaign_impressions",
        "current_campaign_cost_micros",
        "current_campaign_conversions",
        "current_campaign_conversion_value",
    ]
    assert change_impact_contract["readiness_rows"] == [
        {
            "change_event_id": "change-1",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "change_date_time": "2026-06-18 12:30:00.000000",
            "changed_fields": ["campaign.status", "campaign_budget.amount_micros"],
            "current_campaign_metrics_available": True,
            "pre_window_available": False,
            "post_window_available": False,
            "current_clicks": 9,
            "current_impressions": 90,
            "current_cost_micros": 12000000,
            "current_conversions": 2.5,
            "current_conversion_value": 450.75,
            "missing_read_contracts": [
                "pre_change_performance_window",
                "post_change_performance_window",
                "human_change_impact_review",
                "apply_preview",
            ],
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "blocked_claims": [
                "wpływ zmian",
                "obietnica poprawy wyniku",
                "skalowanie budżetu",
                "zmiana budżetu",
                "zapis zmian kampanii",
            ],
        }
    ]
    assert optimizer_items_by_id["change_history_impact_review"][
        "source_contract_ids"
    ] == [
        "ads_change_history_read_contract",
        "ads_change_impact_readiness_contract",
    ]
    assert "current_campaign_snapshot" not in optimizer_items_by_id[
        "change_history_impact_review"
    ]["missing_read_contracts"]
    change_history_section = next(
        section for section in payload["sections"] if section["id"] == "ads_change_history"
    )
    assert change_history_section["status"] == "ready"
    assert change_history_section["action_ids"] == [CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_section["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert change_history_section["expert_rule_ids"] == [
        "ads_diagnostics_v1",
        "ads_principles_v1",
    ]
    facts_by_name = {fact["name"]: fact for fact in campaign_section["metric_facts"]}
    assert facts_by_name["clicks"]["value"] == 9
    assert facts_by_name["conversions"]["value"] == 2.5
    assert facts_by_name["conversion_value"]["value"] == 450.75
    assert any(
        fact["name"] == "cost_micros"
        and fact["dimensions"].get("campaign_name") == "Brand Search"
        for fact in campaign_section["metric_facts"]
    )
    assert "act_configure_google_ads_env" not in payload["action_ids"]
    search_terms_contract = payload["search_terms_read_contract"]
    assert search_terms_contract["status"] == "ready"
    assert search_terms_contract["allowed_metrics"] == [
        "search_term",
        "campaign",
        "ad_group",
        "status",
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    assert "conversions" not in search_terms_contract["missing_read_contracts"]
    assert "conversion_value" not in search_terms_contract["missing_read_contracts"]
    assert "90_day_safety_check" not in search_terms_contract["missing_read_contracts"]
    assert "negative_keyword_action_validation" not in search_terms_contract[
        "missing_read_contracts"
    ]
    assert search_terms_contract["operator_review_gates"] == [
        "negative_keyword_action_validation"
    ]
    assert "dodanie wykluczających słów kluczowych" in search_terms_contract["blocked_claims"]
    assert search_terms_contract["search_term_rows"] == [
        {
            "search_term": "bdo rejestracja",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "ad_group_id": "201",
            "ad_group_name": "BDO",
            "search_term_status": "ADDED",
            "clicks": 4,
            "impressions": 40,
            "cost_micros": 7000000,
            "conversions": 1.0,
            "conversion_value": 120.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": search_terms_contract["search_term_rows"][0]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "dodanie wykluczających słów kluczowych",
                "zmarnowany budżet",
            ],
        },
        {
            "search_term": "odpady cena",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "ad_group_id": "202",
            "ad_group_name": "Odpady",
            "search_term_status": "NONE",
            "clicks": 6,
            "impressions": 60,
            "cost_micros": 5000000,
            "conversions": 0.0,
            "conversion_value": 0.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": search_terms_contract["search_term_rows"][1]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "dodanie wykluczających słów kluczowych",
                "zmarnowany budżet",
            ],
        },
    ]
    search_term_review_contract = payload["search_term_review_summary_contract"]
    assert search_term_review_contract["status"] == "ready"
    assert search_term_review_contract["total_search_term_count"] == 2
    assert search_term_review_contract["zero_conversion_search_term_count"] == 1
    assert search_term_review_contract["total_clicks"] == 10
    assert search_term_review_contract["total_impressions"] == 100
    assert search_term_review_contract["total_cost_micros"] == 12000000
    assert search_term_review_contract["total_conversions"] == 1.0
    assert search_term_review_contract["top_cost_search_terms"][0]["search_term"] == (
        "bdo rejestracja"
    )
    assert search_term_review_contract["campaign_review_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "search_term_count": 2,
            "zero_conversion_search_term_count": 1,
            "clicks": 10,
            "impressions": 100,
            "cost_micros": 12000000,
            "conversions": 1.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "blocked_claims": [
                "marnowanie budżetu na zapytaniach",
                "dodanie wykluczających słów kluczowych",
                "koszt pozyskania celu",
                "zwrot z reklam",
            ],
        }
    ]
    assert "marnowanie budżetu na zapytaniach" in search_term_review_contract["blocked_claims"]
    assert "dodanie wykluczających słów kluczowych" in search_term_review_contract["blocked_claims"]
    search_terms_section = next(
        section for section in payload["sections"] if section["id"] == "ads_search_terms"
    )
    assert search_terms_section["status"] == "ready"
    assert search_terms_section["title"] == "Zapytania użytkowników Google Ads"
    ngram_contract = payload["search_term_ngram_read_contract"]
    assert ngram_contract["status"] == "ready"
    assert ngram_contract["allowed_metrics"] == [
        "ngram",
        "ngram_size",
        "source_search_term_count",
        "sample_search_terms",
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    assert ngram_contract["missing_read_contracts"] == [
        "human_intent_review",
        "ngram_to_negative_keyword_change_preview",
    ]
    assert "negative_keyword_change_preview" not in ngram_contract[
        "missing_read_contracts"
    ]
    assert ngram_contract["operator_review_gates"] == [
        "human_intent_review",
        "negative_keyword_action_validation",
    ]
    assert ngram_contract["action_ids"] == [SEARCH_TERM_NGRAM_ACTION_ID]
    assert "marnowanie budżetu na zapytaniach" in ngram_contract["blocked_claims"]
    assert "dodanie wykluczających słów kluczowych" in ngram_contract["blocked_claims"]
    assert ngram_contract["ngram_rows"]
    ngrams_by_name = {row["ngram"]: row for row in ngram_contract["ngram_rows"]}
    assert ngrams_by_name["bdo"]["source_search_term_count"] == 1
    assert ngrams_by_name["bdo"]["clicks"] == 4
    assert ngrams_by_name["bdo rejestracja"]["ngram_size"] == 2
    assert ngrams_by_name["odpady cena"]["cost_micros"] == 5000000
    assert all(row["evidence_ids"] for row in ngram_contract["ngram_rows"])
    assert all("marnowanie budżetu na zapytaniach" in row["blocked_claims"] for row in ngram_contract["ngram_rows"])
    ngram_section = next(
        section for section in payload["sections"] if section["id"] == "ads_search_term_ngrams"
    )
    assert ngram_section["status"] == "ready"
    assert ngram_section["title"] == "N-gramy zapytań Google Ads"
    assert ngram_section["action_ids"] == [SEARCH_TERM_NGRAM_ACTION_ID]
    ngram_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_search_term_ngrams"
    )
    assert ngram_decision["decision_type"] == "review_search_term_ngrams"
    assert ngram_decision["priority"] == 42
    assert ngram_decision["metric_tiles"]["n-gramy"] == len(ngram_contract["ngram_rows"])
    assert ngram_decision["metric_tiles"]["pokazane"] == len(
        ngram_decision["search_term_ngram_rows"]
    )
    assert ngram_decision["metric_tiles"]["max query/temat"] >= 1
    assert ngram_decision["metric_tiles"]["top kliknięcia"] >= 4
    assert "top koszt" in ngram_decision["metric_tiles"]
    assert ngram_decision["search_term_ngram_rows"]
    assert ngram_decision["action_ids"] == [SEARCH_TERM_NGRAM_ACTION_ID]
    assert "ngram_to_negative_keyword_change_preview" in ngram_decision[
        "missing_read_contracts"
    ]
    assert "negative_keyword_change_preview" not in ngram_decision[
        "missing_read_contracts"
    ]
    assert "card_google_ads_search_playbook" in ngram_decision["knowledge_card_ids"]
    search_term_safety_contract = payload["search_term_safety_read_contract"]
    assert search_term_safety_contract["status"] == "ready"
    assert search_term_safety_contract["allowed_metrics"] == [
        "search_term",
        "campaign",
        "ad_group",
        "status",
        "search_term_90d_clicks",
        "search_term_90d_impressions",
        "search_term_90d_cost_micros",
        "search_term_90d_conversions",
        "search_term_90d_conversion_value",
    ]
    assert "90_day_safety_check" not in search_term_safety_contract[
        "missing_read_contracts"
    ]
    assert "negative_keyword_change_preview" not in search_term_safety_contract[
        "missing_read_contracts"
    ]
    assert "keyword match context" not in search_term_safety_contract[
        "missing_read_contracts"
    ]
    assert "human_intent_review" not in search_term_safety_contract[
        "missing_read_contracts"
    ]
    assert search_term_safety_contract["operator_review_gates"] == [
        "human_intent_review"
    ]
    assert "dodanie wykluczających słów kluczowych" in search_term_safety_contract["blocked_claims"]
    assert search_term_safety_contract["safety_rows"] == [
        {
            "search_term": "odpady cena",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "ad_group_id": "202",
            "ad_group_name": "Odpady",
            "search_term_status": "NONE",
            "clicks_90d": 10,
            "impressions_90d": 120,
            "cost_micros_90d": 8000000,
            "conversions_90d": 0.0,
            "conversion_value_90d": 0.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": search_term_safety_contract["safety_rows"][0][
                "metric_facts"
            ],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "dodanie wykluczających słów kluczowych",
                "zmarnowany budżet",
            ],
        }
    ]
    search_term_safety_section = next(
        section for section in payload["sections"] if section["id"] == "ads_search_term_safety"
    )
    assert search_term_safety_section["status"] == "ready"
    assert search_term_safety_section["knowledge_card_ids"] == [
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_search_playbook",
    ]
    keyword_context_contract = payload["keyword_match_context_read_contract"]
    assert keyword_context_contract["status"] == "ready"
    assert keyword_context_contract["allowed_metrics"] == [
        "keyword_text",
        "keyword_match_type",
        "criterion_status",
        "keyword_negative",
        "campaign",
        "ad_group",
    ]
    assert keyword_context_contract["missing_read_contracts"] == []
    assert keyword_context_contract["operator_review_gates"] == [
        "human_intent_review"
    ]
    assert keyword_context_contract["context_rows"][0]["keyword_text"] == "odpady"
    assert keyword_context_contract["context_rows"][0]["match_type"] == "BROAD"
    assert keyword_context_contract["context_rows"][0]["negative"] is False
    keyword_context_section = next(
        section for section in payload["sections"] if section["id"] == "ads_keyword_match_context"
    )
    assert keyword_context_section["status"] == "ready"
    assert keyword_context_section["knowledge_card_ids"] == [
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_search_playbook",
    ]
    keyword_planner_contract = payload["keyword_planner_read_contract"]
    assert keyword_planner_contract["status"] == "ready"
    assert keyword_planner_contract["missing_read_contracts"] == [
        "forecast_or_audience_size"
    ]
    assert keyword_planner_contract["idea_rows"][0]["idea_text"] == "bdo szkolenie"
    assert keyword_planner_contract["idea_rows"][0]["avg_monthly_searches"] == 100
    assert keyword_planner_contract["idea_rows"][0]["competition"] == "MEDIUM"
    keyword_planner_section = next(
        section for section in payload["sections"] if section["id"] == "ads_keyword_planner"
    )
    assert keyword_planner_section["status"] == "ready"
    custom_segments_contract = payload["custom_segments_read_contract"]
    assert custom_segments_contract["status"] == "ready"
    assert custom_segments_contract["title"] == "Segmenty z realnych wyszukiwanych haseł"
    assert custom_segments_contract["action_ids"] == [
        "act_prepare_custom_segments_from_search_terms"
    ]
    assert "keyword_planner_enrichment" not in custom_segments_contract[
        "missing_read_contracts"
    ]
    assert "forecast_or_audience_size" in custom_segments_contract["missing_read_contracts"]
    assert custom_segments_contract["operator_review_gates"] == [
        "review_source_terms",
        "reject_brand_or_low_intent_terms",
        "keyword_planner_enrichment",
        "forecast_or_audience_size",
        "human_confirm_before_apply",
    ]
    assert "custom_segment_change_preview" not in custom_segments_contract[
        "missing_read_contracts"
    ]
    assert "rozmiar odbiorców" in custom_segments_contract["blocked_claims"]
    audience_forecast_contract = custom_segments_contract[
        "audience_forecast_read_contract"
    ]
    assert audience_forecast_contract["status"] == "blocked"
    assert audience_forecast_contract["checked_candidate_count"] == 1
    assert audience_forecast_contract["forecast_row_count"] == 1
    assert audience_forecast_contract["missing_read_contracts"] == [
        "forecast_or_audience_size",
    ]
    assert audience_forecast_contract["operator_review_gates"] == [
        "forecast_or_audience_size",
        "human_confirm_before_apply",
    ]
    assert "rozmiar odbiorców" in audience_forecast_contract["blocked_claims"]
    forecast_row = audience_forecast_contract["forecast_rows"][0]
    assert forecast_row["candidate_id"] == custom_segments_contract["candidates"][0]["id"]
    assert forecast_row["custom_segment_name"] == (
        custom_segments_contract["candidates"][0]["name"]
    )
    assert forecast_row["status"] == "missing_forecast"
    assert forecast_row["forecast_available"] is False
    assert forecast_row["audience_size"] is None
    assert forecast_row["source_terms"] == ["bdo rejestracja", "odpady cena"]
    assert "prognozy albo rozmiaru odbiorców" in forecast_row["reason"]
    assert forecast_row["evidence_ids"] == [
        refresh_response.json()["evidence_ids"][-1]
    ]
    assert custom_segments_contract["candidates"][0]["source_terms"] == [
        "bdo rejestracja",
        "odpady cena",
    ]
    assert custom_segments_contract["candidates"][0]["source_quality"] == {
        "total_terms": 2,
        "accepted_terms": 2,
        "rejected_terms": 0,
        "missing_metric_terms": 0,
        "rejection_reasons": {},
    }
    assert custom_segments_contract["candidates"][0]["review_priority"] == "pilne"
    assert custom_segments_contract["candidates"][0]["review_score"] == 85
    assert "kolejność oceny segmentu" in custom_segments_contract["candidates"][0][
        "review_reason"
    ]
    assert "nie dowód rozmiaru odbiorców" in custom_segments_contract["candidates"][0][
        "review_reason"
    ]
    assert custom_segments_contract["candidates"][0]["human_review_gates"] == [
        "sprawdź intencję haseł źródłowych",
        "odrzuć brand, konkurencję i frazy o niskiej intencji",
        "sprawdź wzbogacenie Keyword Planner",
        "sprawdź prognozę albo rozmiar odbiorców",
        "zatwierdź segment przed zapisem zmian",
    ]
    assert custom_segments_contract["candidates"][0]["keyword_planner_ideas"][0][
        "idea_text"
    ] == "bdo szkolenie"
    assert custom_segments_contract["payload_preview"][0] == (
        custom_segments_contract["candidates"][0]["payload_preview"]
    )
    assert custom_segments_contract["payload_preview"][0]["member_type"] == "KEYWORD"
    assert custom_segments_contract["payload_preview"][0]["apply_allowed"] is False
    assert custom_segments_contract["payload_preview"][0]["api_mutation_ready"] is False
    assert custom_segments_contract["payload_preview"][0]["destructive"] is False
    targeting_preview = custom_segments_contract["payload_preview"][0][
        "targeting_preview"
    ][0]
    assert targeting_preview["operation_type"] == "custom_segment_targeting_review"
    assert targeting_preview["target_scope"] == "campaign_context_review"
    assert targeting_preview["campaign_id"] == "101"
    assert targeting_preview["campaign_name"] == "Brand Search"
    assert targeting_preview["apply_allowed"] is False
    assert targeting_preview["api_mutation_ready"] is False
    assert targeting_preview["destructive"] is False
    assert "forecast_or_audience_size" in targeting_preview["required_validation"]
    assert custom_segments_contract["candidates"][0]["confidence"] == "low"
    assert custom_segments_contract["candidates"][0]["validation_status"] == (
        "pending_validation"
    )
    assert custom_segments_contract["candidates"][0]["evidence_ids"] == [
        refresh_response.json()["evidence_ids"][-1]
    ]
    custom_segments_section = next(
        section for section in payload["sections"] if section["id"] == "ads_custom_segments"
    )
    assert custom_segments_section["status"] == "ready"
    negative_keywords_contract = payload["negative_keywords_read_contract"]
    assert negative_keywords_contract["status"] == "ready"
    assert negative_keywords_contract["title"] == "Ocena wykluczeń z wyszukiwanych haseł"
    assert negative_keywords_contract["action_ids"] == [
        "act_prepare_negative_keyword_review_queue"
    ]
    assert "90_day_safety_check" not in negative_keywords_contract["missing_read_contracts"]
    assert "negative_keyword_change_preview" not in negative_keywords_contract[
        "missing_read_contracts"
    ]
    assert negative_keywords_contract["missing_read_contracts"] == []
    assert "dodanie wykluczających słów kluczowych" in negative_keywords_contract["blocked_claims"]
    assert negative_keywords_contract["candidates"][0]["search_term"] == "odpady cena"
    assert negative_keywords_contract["candidates"][0]["review_priority"] == "wysokie"
    assert negative_keywords_contract["candidates"][0]["review_score"] == 53
    assert "kolejność oceny" in negative_keywords_contract["candidates"][0][
        "review_reason"
    ]
    assert "nie ocena zmarnowanego budżetu" in negative_keywords_contract[
        "candidates"
    ][0]["review_reason"]
    assert negative_keywords_contract["candidates"][0]["human_review_gates"] == [
        "sprawdź intencję zapytania",
        "porównaj z istniejącymi słowami kluczowymi i typami dopasowania",
        "sprawdź 90-dniowy odczyt bezpieczeństwa",
        "zatwierdź poziom wykluczenia przed zapisem zmian",
    ]
    assert negative_keywords_contract["candidates"][0]["keyword_context_rows"][0][
        "keyword_text"
    ] == "odpady"
    assert negative_keywords_contract["candidates"][0]["keyword_context_rows"][0][
        "match_type"
    ] == "BROAD"
    assert negative_keywords_contract["payload_preview"][0] == (
        negative_keywords_contract["candidates"][0]["payload_preview"]
    )
    assert negative_keywords_contract["payload_preview"][0]["match_type"] == "EXACT"
    assert negative_keywords_contract["payload_preview"][0]["level"] == "ad_group"
    assert negative_keywords_contract["payload_preview"][0]["api_mutation_ready"] is False
    assert negative_keywords_contract["payload_preview"][0]["apply_allowed"] is False
    assert negative_keywords_contract["payload_preview"][0]["destructive"] is False
    assert negative_keywords_contract["candidates"][0]["clicks_90d"] == 10
    assert negative_keywords_contract["candidates"][0]["cost_micros_90d"] == 8000000
    assert negative_keywords_contract["candidates"][0]["conversions_90d"] == 0
    assert negative_keywords_contract["candidates"][0]["safety_evidence_ids"] == [
        refresh_response.json()["evidence_ids"][-1]
    ]
    assert negative_keywords_contract["candidates"][0]["safety_status"] == (
        "read_ready_needs_human_review"
    )
    assert negative_keywords_contract["candidates"][0]["validation_status"] == (
        "pending_validation"
    )
    assert "90_day_safety_check" in negative_keywords_contract["candidates"][0][
        "required_checks"
    ]
    negative_keywords_section = next(
        section for section in payload["sections"] if section["id"] == "ads_negative_keyword_safety"
    )
    assert negative_keywords_section["status"] == "ready"
    decisions_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    assert set(decisions_by_id) == {
        "ads_review_campaign_activity",
        "ads_review_campaign_triage",
        "ads_review_business_context",
        "ads_review_derived_kpis",
        "ads_review_budget_context",
        "ads_review_recommendations",
        "ads_review_impression_share",
        "ads_review_change_history",
        "ads_review_search_terms",
        "ads_review_search_term_ngrams",
        "ads_review_search_term_safety",
        "ads_review_negative_keyword_safety",
        "ads_prepare_custom_segments_from_search_terms",
        "ads_block_write_actions_without_actionobject",
    }
    campaign_decision = decisions_by_id["ads_review_campaign_activity"]
    assert campaign_decision["status"] == "ready"
    assert campaign_decision["priority"] == 20
    assert campaign_decision["metric_tiles"] == {
        "kampanie": 1,
        "pilne": 0,
        "wysokie": 1,
        "kliknięcia": 9,
        "wyświetlenia": 90,
        "koszt": "12 PLN",
        "konwersje": 2.5,
    }
    assert campaign_decision["title"] == "Przejrzyj aktywność kampanii Google Ads"
    assert campaign_decision["campaign_rows"][0]["campaign_name"] == "Brand Search"
    assert campaign_decision["campaign_rows"][0]["review_priority"] == "wysokie"
    assert campaign_decision["campaign_rows"][0]["review_score"] == 50
    assert campaign_decision["search_term_rows"] == []
    assert campaign_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert campaign_decision["operator_review_gates"] == [
        "review_campaign_goal",
        "review_conversion_quality",
        "review_budget_context",
        "review_search_terms_before_budget_decision",
        "human_strategy_review",
    ]
    campaign_triage_decision = decisions_by_id["ads_review_campaign_triage"]
    assert campaign_triage_decision["status"] == "ready"
    assert campaign_triage_decision["priority"] == 18
    assert campaign_triage_decision["decision_type"] == "review_campaign_triage"
    assert campaign_triage_decision["title"] == "Ustal kolejność oceny kampanii Ads"
    assert campaign_triage_decision["campaign_triage_rows"][0]["campaign_name"] == (
        "Brand Search"
    )
    assert campaign_triage_decision["campaign_triage_rows"][0]["roas"] == 37.5625
    assert campaign_triage_decision["action_ids"] == [
        "act_prepare_ads_campaign_review_queue"
    ]
    assert campaign_triage_decision["metric_tiles"] == {
        "kampanie": 1,
        "pilne": 0,
        "wysokie": 1,
        "rekomendacje": 1,
        "podglądy": 2,
    }
    assert "zmarnowany budżet" in campaign_triage_decision["blocked_claims"]
    derived_kpi_decision = decisions_by_id["ads_review_derived_kpis"]
    assert derived_kpi_decision["status"] == "ready"
    assert derived_kpi_decision["priority"] == 25
    assert derived_kpi_decision["metric_tiles"] == {
        "kampanie": 1,
        "wiersze kosztu pozyskania celu": 1,
        "wiersze zwrotu z reklam": 1,
    }
    assert derived_kpi_decision["decision_type"] == "review_derived_kpi"
    assert derived_kpi_decision["derived_kpi_rows"][0]["campaign_name"] == "Brand Search"
    assert derived_kpi_decision["derived_kpi_rows"][0]["roas"] == 37.5625
    assert derived_kpi_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert "opłacalność" in derived_kpi_decision["blocked_claims"]
    assert "budget_pacing" not in derived_kpi_decision["missing_read_contracts"]
    budget_decision = decisions_by_id["ads_review_budget_context"]
    assert budget_decision["status"] == "ready"
    assert budget_decision["priority"] == 30
    assert budget_decision["metric_tiles"] == {
        "budżety": 1,
        "podgląd budżetu": 1,
        "koszt 7 dni": "12 PLN",
    }
    assert budget_decision["decision_type"] == "review_budget_context"
    assert budget_decision["budget_rows"][0]["campaign_name"] == "Brand Search"
    assert budget_decision["budget_rows"][0]["spend_to_budget_ratio_7d"] == 0.057143
    assert budget_decision["budget_apply_preview"][0]["operation_type"] == (
        "CampaignBudgetOperation"
    )
    assert budget_decision["budget_apply_preview"][0]["api_mutation_ready"] is False
    assert budget_decision["budget_apply_preview"][0]["apply_allowed"] is False
    assert budget_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert budget_decision["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert budget_decision["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]
    assert "zmiana budżetu" in budget_decision["blocked_claims"]
    recommendations_decision = decisions_by_id["ads_review_recommendations"]
    assert recommendations_decision["status"] == "ready"
    assert recommendations_decision["priority"] == 35
    assert recommendations_decision["metric_tiles"] == {
        "rekomendacje": 1,
        "pilne": 1,
        "wysokie": 0,
        "podgląd wpływu": 1,
        "podgląd akcji": 1,
    }
    assert recommendations_decision["decision_type"] == "review_recommendations"
    assert recommendations_decision["recommendation_rows"][0]["recommendation_type"] == (
        "CAMPAIGN_BUDGET"
    )
    assert recommendations_decision["recommendation_rows"][0]["review_priority"] == "pilne"
    assert recommendations_decision["recommendation_rows"][0]["review_score"] == 70
    assert recommendations_decision["metric_tiles"] == {
        "rekomendacje": 1,
        "pilne": 1,
        "wysokie": 0,
        "podgląd wpływu": 1,
        "podgląd akcji": 1,
    }
    assert recommendations_decision["recommendation_apply_preview"][0][
        "operation_type"
    ] == "ApplyRecommendationOperation"
    assert recommendations_decision["recommendation_apply_preview"][0][
        "apply_allowed"
    ] is False
    assert recommendations_decision["action_ids"] == [
        "act_prepare_google_ads_recommendation_review_queue"
    ]
    assert recommendations_decision["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert recommendations_decision["expert_rule_ids"] == [
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]
    assert recommendations_decision["missing_read_contracts"] == []
    assert recommendations_decision["operator_review_gates"] == [
        "human_strategy_review",
        "review_recommendation_type",
        "review_impact_metrics",
        "review_change_history",
        "review_business_goal",
        "recommendation_apply_preview",
        "google_ads_rmf_compliance_review",
        "human_confirm_before_apply",
    ]
    assert "zapis rekomendacji" in recommendations_decision["blocked_claims"]
    impression_share_decision = decisions_by_id["ads_review_impression_share"]
    assert impression_share_decision["status"] == "ready"
    assert impression_share_decision["priority"] == 60
    assert impression_share_decision["metric_tiles"] == {
        "kampanie": 1,
        "utrata przez budżet": 1,
    }
    assert impression_share_decision["decision_type"] == "review_impression_share"
    assert impression_share_decision["impression_share_rows"][0]["campaign_name"] == (
        "Brand Search"
    )
    assert impression_share_decision["action_ids"] == []
    assert impression_share_decision["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert impression_share_decision["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_principles_v1",
    ]
    assert "zmiana budżetu" in impression_share_decision["blocked_claims"]
    change_history_decision = decisions_by_id["ads_review_change_history"]
    assert change_history_decision["status"] == "ready"
    assert change_history_decision["priority"] == 65
    assert change_history_decision["metric_tiles"] == {"zmiany": 1, "kampanie": 1}
    assert change_history_decision["decision_type"] == "review_change_history"
    assert change_history_decision["change_history_rows"][0]["change_resource_type"] == (
        "CAMPAIGN"
    )
    assert change_history_decision["action_ids"] == [CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_decision["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert change_history_decision["expert_rule_ids"] == [
        "ads_diagnostics_v1",
        "ads_principles_v1",
    ]
    assert "wpływ zmian" in change_history_decision["blocked_claims"]

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert CHANGE_HISTORY_IMPACT_ACTION_ID in actions
    change_history_action = actions[CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_action["payload"]["action_type"] == (
        "google_ads_change_history_impact_review"
    )
    assert change_history_action["payload"]["preview_contract"] == (
        "change_history_impact_review_v1"
    )
    assert change_history_action["payload"]["change_history_preview"][0][
        "change_event_id"
    ] == "change-1"
    assert change_history_action["payload"]["apply_allowed"] is False
    assert change_history_action["payload"]["destructive"] is False
    assert change_history_action["payload"]["api_mutation_ready"] is False
    assert "pre_change_performance_window" in change_history_action["payload"][
        "missing_read_contracts"
    ]
    validate_response = client.post(f"/api/actions/{CHANGE_HISTORY_IMPACT_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True
    assert SEARCH_TERM_NGRAM_ACTION_ID in actions
    ngram_action = actions[SEARCH_TERM_NGRAM_ACTION_ID]
    assert ngram_action["payload"]["action_type"] == (
        "google_ads_search_term_ngram_review"
    )
    assert ngram_action["payload"]["preview_contract"] == "search_term_ngram_review_v1"
    assert ngram_action["payload"]["ngram_preview"][0]["ngram"]
    assert ngram_action["payload"]["ngram_preview"][0]["sample_search_terms"]
    assert ngram_action["payload"]["ngram_preview"][0]["apply_allowed"] is False
    assert ngram_action["payload"]["ngram_preview"][0]["destructive"] is False
    assert ngram_action["payload"]["ngram_preview"][0]["api_mutation_ready"] is False
    assert ngram_action["payload"]["apply_allowed"] is False
    assert ngram_action["payload"]["destructive"] is False
    assert ngram_action["payload"]["api_mutation_ready"] is False
    ngram_validate_response = client.post(
        f"/api/actions/{SEARCH_TERM_NGRAM_ACTION_ID}/validate"
    )
    assert ngram_validate_response.status_code == 200
    assert ngram_validate_response.json()["valid"] is True
    search_terms_decision = decisions_by_id["ads_review_search_terms"]
    assert search_terms_decision["status"] == "ready"
    assert search_terms_decision["priority"] == 40
    assert search_terms_decision["metric_tiles"] == {
        "zapytania": 2,
        "kliknięcia": 10,
        "koszt": "12 PLN",
    }
    assert search_terms_decision["search_term_rows"][0]["search_term"] == "bdo rejestracja"
    assert search_terms_decision["missing_read_contracts"] == []
    assert search_terms_decision["operator_review_gates"] == [
        "negative_keyword_action_validation"
    ]
    assert "dodanie wykluczających słów kluczowych" in search_terms_decision["blocked_claims"]
    search_term_safety_decision = decisions_by_id["ads_review_search_term_safety"]
    assert search_term_safety_decision["status"] == "ready"
    assert search_term_safety_decision["priority"] == 50
    assert search_term_safety_decision["metric_tiles"] == {
        "90 dni": 1,
        "kliknięcia": 10,
        "koszt": "8.00 PLN",
    }
    assert search_term_safety_decision["decision_type"] == "review_search_term_safety"
    assert search_term_safety_decision["search_term_safety_rows"][0]["search_term"] == (
        "odpady cena"
    )
    assert "dodanie wykluczających słów kluczowych" in search_term_safety_decision["blocked_claims"]
    assert search_term_safety_decision["missing_read_contracts"] == []
    assert search_term_safety_decision["operator_review_gates"] == [
        "human_intent_review"
    ]
    assert search_term_safety_decision["knowledge_card_ids"] == [
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_search_playbook",
    ]
    negative_keyword_decision = decisions_by_id["ads_review_negative_keyword_safety"]
    assert negative_keyword_decision["status"] == "ready"
    assert negative_keyword_decision["priority"] == 45
    assert negative_keyword_decision["metric_tiles"] == {
        "propozycje": 1,
        "pilne": 0,
        "wysokie": 1,
        "podgląd akcji": 1,
        "kontekst słów": 1,
    }
    assert negative_keyword_decision["decision_type"] == "review_negative_keyword_safety"
    assert negative_keyword_decision["negative_keyword_candidates"][0]["search_term"] == (
        "odpady cena"
    )
    assert negative_keyword_decision["search_term_safety_rows"][0]["clicks_90d"] == 10
    assert negative_keyword_decision["negative_keyword_payload_preview"][0][
        "negative_keyword_text"
    ] == "odpady cena"
    assert negative_keyword_decision["missing_read_contracts"] == []
    assert negative_keyword_decision["operator_review_gates"] == [
        "human_intent_review"
    ]
    assert negative_keyword_decision["keyword_match_context_rows"][0]["keyword_text"] == (
        "odpady"
    )
    assert negative_keyword_decision["action_ids"] == [
        "act_prepare_negative_keyword_review_queue"
    ]
    assert "marnowanie budżetu na zapytaniach" in negative_keyword_decision["blocked_claims"]
    custom_segments_decision = decisions_by_id["ads_prepare_custom_segments_from_search_terms"]
    assert custom_segments_decision["status"] == "ready"
    assert custom_segments_decision["priority"] == 55
    assert custom_segments_decision["metric_tiles"] == {
        "segmenty": 1,
        "pilne": 1,
        "wysokie": 0,
        "podgląd akcji": 1,
        "źródłowe zapytania": 2,
        "KP ideas": 1,
    }
    assert custom_segments_decision["decision_type"] == "prepare_custom_segments"
    assert custom_segments_decision["missing_read_contracts"] == [
        "forecast_or_audience_size",
    ]
    assert custom_segments_decision["custom_segment_audience_forecast_rows"][0][
        "status"
    ] == "missing_forecast"
    assert custom_segments_decision["custom_segment_audience_forecast_rows"][0][
        "candidate_id"
    ] == custom_segments_decision["custom_segment_candidates"][0]["id"]
    assert custom_segments_decision["custom_segment_audience_forecast_rows"][0][
        "audience_size"
    ] is None
    assert custom_segments_decision["operator_review_gates"] == [
        "review_source_terms",
        "reject_brand_or_low_intent_terms",
        "keyword_planner_enrichment",
        "forecast_or_audience_size",
        "human_confirm_before_apply",
    ]
    assert custom_segments_decision["custom_segment_candidates"][0]["source_terms"] == [
        "bdo rejestracja",
        "odpady cena",
    ]
    assert custom_segments_decision["custom_segment_candidates"][0][
        "source_quality"
    ]["accepted_terms"] == 2
    assert custom_segments_decision["keyword_planner_idea_rows"][0]["idea_text"] == (
        "bdo szkolenie"
    )
    assert custom_segments_decision["custom_segment_payload_preview"][0][
        "custom_segment_name"
    ] == "Wyszukiwane hasła: Brand Search"
    assert custom_segments_decision["custom_segment_payload_preview"][0][
        "apply_allowed"
    ] is False
    assert custom_segments_decision["custom_segment_payload_preview"][0][
        "targeting_preview"
    ][0]["apply_allowed"] is False
    assert custom_segments_decision["action_ids"] == [
        "act_prepare_custom_segments_from_search_terms"
    ]
    assert "zwrot z reklam" in custom_segments_decision["blocked_claims"]
    safety_decision = decisions_by_id["ads_block_write_actions_without_actionobject"]
    assert safety_decision["status"] == "blocked"
    assert safety_decision["priority"] == 10
    assert safety_decision["metric_tiles"] == {"akcje do sprawdzenia": 10, "blokady": 3}
    assert "campaign creation" in safety_decision["blocked_claims"]
    assert payload["blocker_count"] == 2

    status_probe_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "status_probe", "reason": "ads diagnostics status probe regression"},
    )
    assert status_probe_response.status_code == 200

    after_probe_response = client.get("/api/ads/diagnostics")
    assert after_probe_response.status_code == 200
    after_probe_payload = after_probe_response.json()
    assert after_probe_payload["live_data_available"] is True
    assert after_probe_payload["latest_refresh"]["id"] == refresh_response.json()["id"]
    assert after_probe_payload["blocked_handoff"] is None
    assert after_probe_payload["campaign_read_contract"]["campaign_rows"]
    assert after_probe_payload["budget_pacing_read_contract"]["budget_rows"]
    assert after_probe_payload["recommendations_read_contract"]["recommendation_rows"]
    assert after_probe_payload["impression_share_read_contract"]["impression_share_rows"]
    assert after_probe_payload["change_history_read_contract"]["change_history_rows"]
    assert after_probe_payload["search_terms_read_contract"]["search_term_rows"]
    assert after_probe_payload["search_term_safety_read_contract"]["safety_rows"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_decisions = {
        decision["id"]: decision
        for decision in context_payload["ads_diagnostics"]["decision_queue"]
    }
    context_budget_decision = context_decisions["ads_review_budget_context"]
    assert context_budget_decision["priority"] == budget_decision["priority"]
    assert context_budget_decision["metric_tiles"] == budget_decision["metric_tiles"]
    assert context_budget_decision["knowledge_card_ids"] == budget_decision[
        "knowledge_card_ids"
    ]
    assert context_budget_decision["expert_rule_ids"] == budget_decision["expert_rule_ids"]
    context_card_ids = {
        card["id"] for card in context_payload["knowledge_card_summaries"]
    }
    assert "card_google_ads_budget_review_playbook" in context_card_ids
    context_rule_ids = {
        rule["id"] for rule in context_payload["expert_rule_summaries"]
    }
    assert "ads_scaling_candidates_v1" in context_rule_ids
    assert "ads_recommendations_v1" in context_rule_ids

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions_payload = actions_response.json()
    action_ids = {action["id"] for action in actions_payload}
    assert "act_configure_google_ads_env" not in action_ids
    assert "act_prepare_ads_campaign_review_queue" in action_ids
    assert CHANGE_HISTORY_IMPACT_ACTION_ID in action_ids
    assert SEARCH_TERM_NGRAM_ACTION_ID in action_ids
    assert "act_prepare_google_ads_recommendation_review_queue" in action_ids
    assert "act_prepare_custom_segments_from_search_terms" in action_ids
    assert "act_prepare_negative_keyword_review_queue" in action_ids
    campaign_review_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_ads_campaign_review_queue"
    )
    assert campaign_review_action["payload"]["action_type"] == "campaign_change_review"
    assert campaign_review_action["payload"]["campaign_candidates"][0]["campaign_name"] == (
        "Brand Search"
    )
    assert campaign_review_action["payload"]["campaign_candidates"][0][
        "review_priority"
    ] == "wysokie"
    assert campaign_review_action["payload"]["campaign_candidates"][0]["review_score"] == 50
    assert (
        "Kolejność oceny kampanii"
        in campaign_review_action["payload"]["campaign_candidates"][0]["review_reason"]
    )
    assert campaign_review_action["payload"]["campaign_candidates"][0][
        "human_review_gates"
    ] == [
        "review_campaign_goal",
        "review_conversion_quality",
        "review_budget_context",
        "review_search_terms_before_budget_decision",
        "human_strategy_review",
    ]
    assert campaign_review_action["payload"]["campaign_candidates"][0][
        "target_context"
    ]["target_status"] == "no_target"
    assert campaign_review_action["payload"]["campaign_candidates"][0]["derived_kpis"][
        "roas"
    ] == 37.5625
    assert campaign_review_action["payload"]["campaign_candidates"][0]["budget_context"] == {
        "budget_amount_micros": 30000000,
        "cost_micros_7d": 12000000,
        "seven_day_budget_micros": 210000000,
        "spend_to_budget_ratio_7d": 0.057143,
        "has_recommended_budget": True,
        "recommended_budget_amount_micros": 42000000,
    }
    assert campaign_review_action["payload"]["preview_contract"] == (
        "budget_apply_preview_v1"
    )
    assert campaign_review_action["payload"]["budget_payload_preview"][0][
        "operation_type"
    ] == "CampaignBudgetOperation"
    assert campaign_review_action["payload"]["budget_payload_preview"][0][
        "proposed_budget_amount_micros"
    ] == 42000000
    assert campaign_review_action["payload"]["budget_payload_preview"][0][
        "api_mutation_ready"
    ] is False
    assert campaign_review_action["payload"]["budget_payload_preview"][0][
        "apply_allowed"
    ] is False
    budget_safety_review = campaign_review_action["payload"]["budget_payload_preview"][0][
        "safety_review"
    ]
    assert budget_safety_review["safety_contract"] == "campaign_budget_apply_safety_v1"
    assert budget_safety_review["apply_allowed"] is False
    assert budget_safety_review["api_mutation_ready"] is False
    assert budget_safety_review["destructive"] is False
    assert campaign_review_action["payload"]["apply_allowed"] is False
    assert campaign_review_action["payload"]["destructive"] is False
    assert "budget_pacing" in campaign_review_action["payload"]["required_validation"]
    assert "budget_apply_preview" in campaign_review_action["payload"][
        "required_validation"
    ]
    assert "campaign_budget_apply_safety" in campaign_review_action["payload"][
        "required_validation"
    ]
    assert "skalowanie budżetu" in campaign_review_action["payload"]["blocked_claims"]
    campaign_review_validation_response = client.post(
        "/api/actions/act_prepare_ads_campaign_review_queue/validate",
        json={},
    )
    assert campaign_review_validation_response.status_code == 200
    assert campaign_review_validation_response.json()["valid"] is True
    recommendation_review_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_google_ads_recommendation_review_queue"
    )
    assert recommendation_review_action["payload"]["action_type"] == (
        "google_ads_recommendation_review"
    )
    assert recommendation_review_action["payload"]["preview_contract"] == (
        "recommendation_apply_preview_v1"
    )
    assert recommendation_review_action["payload"]["payload_preview"][0][
        "operation_type"
    ] == "ApplyRecommendationOperation"
    assert recommendation_review_action["payload"]["payload_preview"][0][
        "apply_allowed"
    ] is False
    assert recommendation_review_action["payload"]["apply_allowed"] is False
    assert recommendation_review_action["payload"]["destructive"] is False
    assert "human_confirm_before_apply" in recommendation_review_action["payload"][
        "required_validation"
    ]
    recommendation_review_validation_response = client.post(
        "/api/actions/act_prepare_google_ads_recommendation_review_queue/validate",
        json={},
    )
    assert recommendation_review_validation_response.status_code == 200
    assert recommendation_review_validation_response.json()["valid"] is True
    custom_segment_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_custom_segments_from_search_terms"
    )
    assert custom_segment_action["payload"]["terms"] == [
        "bdo rejestracja",
        "odpady cena",
    ]
    assert custom_segment_action["payload"]["invented_terms"] is False
    assert custom_segment_action["payload"]["preview_contract"] == (
        "custom_segment_change_preview_v1"
    )
    assert custom_segment_action["payload"]["payload_preview"][0]["member_type"] == "KEYWORD"
    assert custom_segment_action["payload"]["payload_preview"][0]["member_type_label"] == (
        "słowa kluczowe"
    )
    assert custom_segment_action["payload"]["payload_preview"][0]["apply_allowed"] is False
    custom_segment_safety_review = custom_segment_action["payload"]["payload_preview"][0][
        "safety_review"
    ]
    assert custom_segment_safety_review["safety_contract"] == (
        "custom_segment_apply_safety_v1"
    )
    assert custom_segment_safety_review["status"] == "blocked"
    assert custom_segment_safety_review["status_label"] == "zablokowane"
    assert custom_segment_safety_review["apply_allowed"] is False
    assert custom_segment_safety_review["api_mutation_ready"] is False
    assert custom_segment_safety_review["destructive"] is False
    assert custom_segment_safety_review["audit_required"] is True
    assert "forecast_or_audience_size" in custom_segment_safety_review[
        "missing_requirements"
    ]
    assert "google_ads_mutation_audit" in custom_segment_safety_review[
        "missing_requirements"
    ]
    custom_segment_targeting_preview = custom_segment_action["payload"][
        "payload_preview"
    ][0]["targeting_preview"][0]
    assert custom_segment_targeting_preview["operation_type"] == (
        "custom_segment_targeting_review"
    )
    assert custom_segment_targeting_preview["apply_allowed"] is False
    assert custom_segment_targeting_preview["api_mutation_ready"] is False
    assert custom_segment_action["payload"]["destructive"] is False
    validation_response = client.post(
        "/api/actions/act_prepare_custom_segments_from_search_terms/validate",
        json={},
    )
    assert validation_response.status_code == 200
    assert validation_response.json()["valid"] is True
    negative_keyword_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_negative_keyword_review_queue"
    )
    assert negative_keyword_action["payload"]["terms"] == ["odpady cena"]
    assert negative_keyword_action["payload"]["preview_contract"] == (
        "negative_keyword_change_preview_v1"
    )
    assert negative_keyword_action["payload"]["api_mutation_ready"] is False
    assert negative_keyword_action["payload"]["payload_preview"][0]["match_type"] == "EXACT"
    assert negative_keyword_action["payload"]["payload_preview"][0]["apply_allowed"] is False
    assert negative_keyword_action["payload"]["keyword_match_context_available"] is True
    assert negative_keyword_action["payload"]["keyword_match_context"][0][
        "keyword_text"
    ] == "odpady"
    assert negative_keyword_action["payload"]["keyword_match_context"][0][
        "match_type"
    ] == "BROAD"
    assert "search_term_90d_clicks" in negative_keyword_action["payload"][
        "source_metric_names"
    ]
    assert negative_keyword_action["payload"]["apply_allowed"] is False
    assert negative_keyword_action["payload"]["destructive"] is False
    assert "90_day_safety_check" in negative_keyword_action["payload"]["required_validation"]
    negative_keyword_validation_response = client.post(
        "/api/actions/act_prepare_negative_keyword_review_queue/validate",
        json={},
    )
    assert negative_keyword_validation_response.status_code == 200
    assert negative_keyword_validation_response.json()["valid"] is True

    monkeypatch.setenv("WILQ_ADS_PROFIT_MARGIN", "0.35")
    monkeypatch.setenv("WILQ_ADS_BUSINESS_GOAL", "lead quality review")
    monkeypatch.setenv("WILQ_ADS_BUDGET_GOAL", "protect current monthly budget")
    monkeypatch.setenv("WILQ_ADS_TARGET_ROAS", "5.0")
    business_ready_response = client.get("/api/ads/diagnostics")
    assert business_ready_response.status_code == 200
    business_ready_payload = business_ready_response.json()
    business_ready_contract = business_ready_payload["business_context_read_contract"]
    assert business_ready_contract["status"] == "ready"
    assert business_ready_contract["profit_margin"] == 0.35
    assert business_ready_contract["business_goal"] == "lead quality review"
    assert business_ready_contract["budget_goal"] == "protect current monthly budget"
    assert business_ready_contract["target_roas"] == 5.0
    assert business_ready_contract["missing_read_contracts"] == [
        "human_strategy_review"
    ]
    assert business_ready_contract["allowed_metrics"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas",
    ]
    assert business_ready_contract["business_policy_ids"] == [
        "use_margin_as_context_not_profitability_verdict",
        "align_campaign_review_to_business_goal",
        "honor_human_budget_goal_before_budget_changes",
        "compare_kpis_to_confirmed_target_in_review",
        "block_target_verdict_until_strategy_review_approved",
    ]
    assert business_ready_contract["target_interpretation"]["status"] == "preliminary"
    assert "target_roas_review_context" in business_ready_contract[
        "target_interpretation"
    ]["allowed_uses"]
    assert "target_roas_or_cpa" not in business_ready_contract[
        "target_interpretation"
    ]["missing_requirements"]
    assert "human_strategy_review" in business_ready_contract["target_interpretation"][
        "missing_requirements"
    ]
    assert business_ready_contract["target_interpretation"]["apply_allowed"] is False
    assert business_ready_contract["target_interpretation"]["action_ids"] == [
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]
    assert business_ready_contract["operator_review_gates"] == [
        "human_strategy_review",
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "review_target_fit",
    ]
    derived_ready_contract = business_ready_payload["derived_kpi_read_contract"]
    campaign_ready_row = business_ready_payload["campaign_read_contract"][
        "campaign_rows"
    ][0]
    assert campaign_ready_row["target_status"] == "within_target"
    assert campaign_ready_row["target_status_label"] == "zwrot z reklam w granicy celu"
    assert "target=zwrot z reklam w granicy celu" in campaign_ready_row["review_reason"]
    assert "review_target_context" in campaign_ready_row["human_review_gates"]
    assert "profit_margin" not in derived_ready_contract["missing_read_contracts"]
    assert "target_roas" in derived_ready_contract["allowed_metrics"]
    assert "roas_vs_target" in derived_ready_contract["allowed_metrics"]
    assert derived_ready_contract["kpi_rows"][0]["target_roas"] == 5.0
    assert derived_ready_contract["kpi_rows"][0]["roas_vs_target"] == 32.5625
    assert derived_ready_contract["kpi_rows"][0]["target_cpa_micros"] is None
    assert derived_ready_contract["kpi_rows"][0]["cpa_vs_target_micros"] is None
    assert derived_ready_contract["kpi_rows"][0]["target_status"] == "within_target"
    assert derived_ready_contract["kpi_rows"][0]["target_status_label"] == (
        "zwrot z reklam w granicy celu"
    )
    assert "human_budget_goal" not in business_ready_payload[
        "budget_pacing_read_contract"
    ]["missing_read_contracts"]
    assert "budget_target_or_seasonality" not in business_ready_payload[
        "budget_pacing_read_contract"
    ]["missing_read_contracts"]
    assert "human_budget_goal" not in business_ready_payload[
        "impression_share_read_contract"
    ]["missing_read_contracts"]
    business_ready_decision = next(
        decision
        for decision in business_ready_payload["decision_queue"]
        if decision["id"] == "ads_review_business_context"
    )
    assert business_ready_decision["status"] == "ready"
    assert business_ready_decision["metric_tiles"] == {
        "braki": 1,
        "blokady": 6,
        "ustawione pola": 4,
        "warunki sprawdzenia": 5,
        "polityki": 5,
    }
    assert business_ready_decision["operator_review_gates"] == (
        business_ready_contract["operator_review_gates"]
    )
    assert business_ready_decision["action_ids"] == [
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]
    business_ready_campaign_decision = next(
        decision
        for decision in business_ready_payload["decision_queue"]
        if decision["id"] == "ads_review_campaign_activity"
    )
    assert business_ready_campaign_decision["metric_tiles"]["targety"] == 1
    derived_ready_decision = next(
        decision
        for decision in business_ready_payload["decision_queue"]
        if decision["id"] == "ads_review_derived_kpis"
    )
    assert derived_ready_decision["metric_tiles"]["targety"] == 1
    assert derived_ready_decision["metric_tiles"]["w celu"] == 1
    assert derived_ready_decision["derived_kpi_rows"][0]["roas_vs_target"] == 32.5625
    assert derived_ready_decision["derived_kpi_rows"][0]["target_status"] == "within_target"

    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    brief_action_ids = {
        action_id
        for section in brief_response.json()["sections"]
        for item in section["items"]
        for action_id in item["action_ids"]
    }
    assert "act_configure_google_ads_env" not in brief_action_ids


def test_ads_diagnostics_summary_view_compacts_heavy_payload() -> None:
    full_response = client.get("/api/ads/diagnostics")
    summary_response = client.get("/api/ads/diagnostics?view=summary")

    assert full_response.status_code == 200
    assert summary_response.status_code == 200
    full_payload = full_response.json()
    summary_payload = summary_response.json()
    full_bytes = len(json.dumps(full_payload, ensure_ascii=False).encode())
    summary_bytes = len(json.dumps(summary_payload, ensure_ascii=False).encode())

    assert summary_bytes < full_bytes
    assert summary_payload["operator_summary"] == full_payload["operator_summary"]
    assert summary_payload["connector_status_label"]
    assert summary_payload["live_data_status_label"]
    if summary_payload["latest_refresh"]:
        assert summary_payload["latest_refresh_status_label"]
    assert summary_payload["operator_summary"]["missing_read_contract_labels"] == (
        full_payload["operator_summary"]["missing_read_contract_labels"]
    )
    assert summary_payload["operator_summary"]["blocked_claim_labels"] == (
        full_payload["operator_summary"]["blocked_claim_labels"]
    )
    assert len(summary_payload["decision_queue"]) <= len(full_payload["decision_queue"])
    assert all(decision["status_label"] for decision in summary_payload["decision_queue"])
    assert all(decision["decision_type_label"] for decision in summary_payload["decision_queue"])
    assert all(decision["priority_label"] for decision in summary_payload["decision_queue"])
    assert all(decision["risk_label"] for decision in summary_payload["decision_queue"])
    assert all(
        isinstance(decision["missing_read_contract_labels"], list)
        for decision in summary_payload["decision_queue"]
    )
    assert all(
        isinstance(decision["blocked_claim_labels"], list)
        for decision in summary_payload["decision_queue"]
    )
    assert all(section["status_label"] for section in summary_payload["sections"])
    assert all(
        isinstance(section["blocked_claim_labels"], list)
        for section in summary_payload["sections"]
    )
    assert set(summary_payload["operator_summary"]["top_decision_ids"]).issubset(
        {decision["id"] for decision in summary_payload["decision_queue"]}
    )
    assert len(summary_payload["search_term_safety_read_contract"]["safety_rows"]) <= 5
    assert len(summary_payload["keyword_match_context_read_contract"]["context_rows"]) <= 5


def test_ads_diagnostics_summary_action_ids_are_validatable() -> None:
    response = client.get("/api/ads/diagnostics?view=summary")
    assert response.status_code == 200
    payload = response.json()

    action_ids = {
        *payload["operator_summary"]["action_ids"],
        *(
            action_id
            for item in payload["optimizer_readiness_contract"]["readiness_items"]
            for action_id in item["action_ids"]
        ),
        *(
            action_id
            for decision in payload["decision_queue"]
            for action_id in decision["action_ids"]
        ),
    }

    assert action_ids
    for action_id in sorted(action_ids):
        action_response = client.get(f"/api/actions/{action_id}")
        assert action_response.status_code == 200, action_id
        validate_response = client.post(f"/api/actions/{action_id}/validate")
        assert validate_response.status_code == 200, action_id
        validation = validate_response.json()
        assert validation["valid"] is True, action_id
        assert validation["status"] == "valid", action_id


def test_ads_diagnostics_summary_view_uses_smaller_metric_fact_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_limits: list[int] = []

    class RecordingMetricStore:
        def list_metric_facts(self, connector_id: str, limit: int) -> list[MetricFact]:
            assert connector_id == "google_ads"
            captured_limits.append(limit)
            return []

    monkeypatch.setattr(
        "wilq.briefing.ads_diagnostics.metric_store",
        lambda: RecordingMetricStore(),
    )
    monkeypatch.setattr("wilq.briefing.ads_diagnostics._latest_google_ads_refresh", lambda: None)

    build_ads_diagnostics(view="summary")

    assert captured_limits
    assert captured_limits[0] < ADS_METRIC_FACT_LIMIT
    assert captured_limits[0] <= 2000


def test_ads_diagnostics_summary_view_reads_latest_refresh_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_evidence_ids: list[list[str]] = []
    latest_refresh = ConnectorRefreshRun(
        id="refresh_google_ads_summary_latest_evidence",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=[
            "ev_connector_google_ads_status",
            "ev_refresh_refresh_google_ads_summary_latest_evidence",
        ],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"row_count": 1},
        summary="Latest Google Ads read for summary evidence test.",
    )

    class RecordingMetricStore:
        def list_metric_facts(self, connector_id: str, limit: int) -> list[MetricFact]:
            assert connector_id == "google_ads"
            return []

        def list_metric_facts_by_evidence_ids(
            self,
            evidence_ids: list[str],
        ) -> list[MetricFact]:
            captured_evidence_ids.append(evidence_ids)
            return []

    monkeypatch.setattr(
        "wilq.briefing.ads_diagnostics.metric_store",
        lambda: RecordingMetricStore(),
    )
    monkeypatch.setattr(
        "wilq.briefing.ads_diagnostics._latest_google_ads_refresh",
        lambda: latest_refresh,
    )

    build_ads_diagnostics(view="summary")

    assert captured_evidence_ids == [latest_refresh.evidence_ids]


def test_ads_diagnostics_uses_lightweight_action_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_full_action_list() -> list[ActionObject]:
        raise AssertionError("Ads diagnostics must not seed the full ActionObject list")

    monkeypatch.setattr(
        "wilq.actions.service.list_actions",
        fail_full_action_list,
    )

    response = client.get("/api/ads/diagnostics?view=summary")

    assert response.status_code == 200
    assert response.json()["action_ids"]


def test_ads_custom_segment_review_reason_keeps_missing_metrics_unknown() -> None:
    reason = _custom_segment_review_reason(
        source_terms=["bdo szkolenie"],
        rows=[
            AdsSearchTermMetricRow(
                search_term="bdo szkolenie",
                campaign_id="101",
                campaign_name="Brand Search",
                clicks=7,
                conversions=0.0,
                evidence_ids=["ev_test"],
                missing_metrics=[
                    "search_term_impressions",
                    "search_term_cost_micros",
                ],
            )
        ],
        rejected_terms=[],
    )

    assert "wyświetlenia=brak danych" in reason
    assert "koszt=brak danych" in reason
    assert "wyświetlenia=0" not in reason
    assert "koszt=0.00" not in reason


def test_ads_custom_segment_source_quality_counts_rejections() -> None:
    quality = _custom_segment_source_quality(
        source_terms=["bdo szkolenie"],
        rows=[
            AdsSearchTermMetricRow(
                search_term="bdo szkolenie",
                campaign_id="101",
                campaign_name="Brand Search",
                clicks=7,
                evidence_ids=["ev_test"],
                missing_metrics=["search_term_cost_micros"],
            )
        ],
        rejected_pairs=[
            ("ekologus kontakt", "termin wygląda na własny brand albo zapytanie nawigacyjne"),
            ("19115 odpady", "termin nie ma aktywności w dostępnych metrykach"),
            ("bdo katowice", "termin nie ma aktywności w dostępnych metrykach"),
        ],
    )

    assert quality.total_terms == 4
    assert quality.accepted_terms == 1
    assert quality.rejected_terms == 3
    assert quality.missing_metric_terms == 1
    assert quality.rejection_reasons == {
        "termin nie ma aktywności w dostępnych metrykach": 2,
        "termin wygląda na własny brand albo zapytanie nawigacyjne": 1,
    }


def test_merchant_diagnostics_exposes_feed_issue_queue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_diag_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_diag_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    adc_json = tmp_path / "adc.json"
    adc_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(adc_json))
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "5519957373")
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_merchant_product_status_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Merchant Center zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "total_products": 10900,
                "item_level_issue_count": 23,
                "merchant_action_issue_count": 15,
            },
            metric_facts=[
                VendorMetricFact(
                    "issue_product_count",
                    23,
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "n:availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                    },
                ),
                VendorMetricFact(
                    "sample_product_id",
                    "online~pl~PL~SKU-001",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "1",
                    },
                ),
                VendorMetricFact(
                    "sample_product_id",
                    "online~pl~PL~SKU-002",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "2",
                    },
                ),
                VendorMetricFact(
                    "sample_product_title",
                    "Sorbent chemiczny 10 kg",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "1",
                    },
                ),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_merchant_center/refresh",
        json={"mode": "vendor_read", "reason": "merchant diagnostics test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/merchant/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["live_data_available"] is True
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "zakończony"
    assert payload["live_data_status_label"] == "metryki feedu dostępne"
    assert payload["product_count"] == 10900
    assert payload["issue_count"] == 23
    assert payload["latest_refresh"]["status"] == "completed"
    assert payload["freshness_assessment"]["state"] == "fresh"
    assert payload["freshness_assessment"]["state_label"] == "dane świeże"
    assert payload["freshness_assessment"]["requires_refresh"] is False
    assert payload["freshness_assessment"]["stale_after_hours"] == 48
    sample_readiness = payload["product_sample_readiness"]
    assert sample_readiness["status"] == "ready"
    assert sample_readiness["status_label"] == "próbki produktów dostępne"
    assert sample_readiness["sample_products_available"] is True
    assert sample_readiness["sample_count"] == 2
    assert sample_readiness["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert sample_readiness["sample_product_titles"] == ["Sorbent chemiczny 10 kg"]
    assert sample_readiness["current_read_contract"] == "merchant_aggregate_product_statuses"
    assert sample_readiness["required_read_contracts"] == [
        "merchant_products_list_product_status",
        "merchant_reports_product_view_issue_filter",
    ]
    assert sample_readiness["source_endpoint"] == "aggregateProductStatuses"
    assert "products.list" in sample_readiness["next_step"]
    assert "zapis do feedu" in sample_readiness["blocked_claims"]
    assert "zapis do feedu" in sample_readiness["blocked_claim_labels"]
    performance_readiness = payload["product_performance_readiness"]
    assert performance_readiness["id"] == "merchant_product_performance_readiness"
    assert performance_readiness["status"] == "blocked"
    assert performance_readiness["status_label"] == "dane Ads/GA4 zablokowane"
    assert performance_readiness["merchant_sample_count"] == 2
    assert performance_readiness["joined_product_count"] == 0
    assert performance_readiness["ads_product_fact_count"] == 0
    assert performance_readiness["ga4_product_fact_count"] == 0
    assert performance_readiness["required_read_contracts"] == [
        "merchant_product_id_join_key",
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    ]
    assert performance_readiness["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert performance_readiness["performance_rows"] == []
    assert performance_readiness["current_read_contracts"] == [
        "merchant_aggregate_product_statuses"
    ]
    assert "google_merchant_center" in performance_readiness["source_connectors"]
    assert refresh_response.json()["evidence_ids"][-1] in performance_readiness[
        "evidence_ids"
    ]
    assert "zwrot z reklam na poziomie produktu" in performance_readiness["blocked_claims"]
    assert "odzyskany przychód produktu" in performance_readiness["blocked_claims"]
    assert "efekt naprawy produktu" in performance_readiness["blocked_claims"]
    assert (
        "zwrot z reklam na poziomie produktu"
        in performance_readiness["blocked_claim_labels"]
    )
    assert "act_review_merchant_feed_issues" in payload["action_ids"]
    assert payload["unknowns"]
    unknown_ids = {unknown["id"] for unknown in payload["unknowns"]}
    assert "merchant_product_examples_missing" not in unknown_ids
    assert "merchant_unique_product_count_unknown" in unknown_ids
    assert "merchant_product_performance_join_missing" in unknown_ids
    assert payload["issue_clusters"]
    cluster = payload["issue_clusters"][0]
    assert cluster["issue_type"] == "availability_updated"
    assert cluster["issue_type_label"] == "zmiana dostępności do sprawdzenia"
    assert cluster["affected_attribute"] == "n:availability"
    assert cluster["affected_attribute_label"] == "dostępność"
    assert cluster["country"] == "PL"
    assert cluster["reporting_context"] == "SHOPPING_ADS"
    assert cluster["reporting_context_label"] == "reklamy produktowe"
    assert cluster["severity"] == "NOT_IMPACTED"
    assert cluster["severity_label"] == "bez wpływu"
    assert cluster["resolution"] == "MERCHANT_ACTION"
    assert cluster["resolution_label"] == "wymaga działania po stronie Merchant"
    assert cluster["product_count"] == 23
    assert cluster["count_semantics"] == "reported_issue_occurrences"
    assert cluster["action_id"] == "act_review_merchant_feed_issues"
    assert cluster["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert cluster["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert cluster["sample_unavailable_reason"] is None
    assert "ponowne zatwierdzenie produktu" in cluster["blocked_claims"]
    assert payload["decision_queue"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "merchant_operator_summary"
    assert operator_summary["title"] == "Co marketer ma zrobić teraz z feedem"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["top_issue_cluster_ids"] == [
        cluster["id"] for cluster in payload["issue_clusters"][:4]
    ]
    assert operator_summary["reported_issue_occurrences"] == sum(
        cluster["product_count"] for cluster in payload["issue_clusters"]
    )
    assert operator_summary["decision_source"] == "decision_queue"
    assert operator_summary["decision_source_label"] == "kolejka decyzji Merchant"
    assert operator_summary["drilldown_source"] == "issue_clusters"
    assert operator_summary["drilldown_source_label"] == "grupy problemów feedu"
    assert operator_summary["count_semantics"] == "reported_issue_occurrences"
    assert operator_summary["count_semantics_label"] == "wystąpienia problemów w raportach"
    assert "zmiana dostępności do sprawdzenia" in operator_summary["issue_types"]
    assert operator_summary["source_connectors"] == ["google_merchant_center"]
    assert refresh_response.json()["evidence_ids"][-1] in operator_summary["evidence_ids"]
    assert "act_review_merchant_feed_issues" in operator_summary["action_ids"]
    assert "ponowne zatwierdzenie produktu" in operator_summary["blocked_claims"]
    assert "ponowne zatwierdzenie produktu" in operator_summary["blocked_claim_labels"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    decision = payload["decision_queue"][0]
    assert decision["decision_type"] == "review_issue_cluster"
    assert decision["decision_type_label"] == "przegląd problemu feedu"
    assert decision["status"] == "ready"
    assert decision["status_label"] == "gotowe"
    assert decision["title"] == (
        "Merchant: sprawdź zmiana dostępności do sprawdzenia / dostępność"
    )
    assert decision["issue_type"] == "availability_updated"
    assert decision["issue_type_label"] == "zmiana dostępności do sprawdzenia"
    assert decision["affected_attribute"] == "n:availability"
    assert decision["affected_attribute_label"] == "dostępność"
    assert decision["reporting_context_label"] == "reklamy produktowe"
    assert decision["product_count"] == 23
    assert decision["issue_count"] == 23
    assert decision["priority"] == 23
    assert decision["metric_tiles"] == {"zgłoszenia": 23}
    assert decision["cluster_id"] == cluster["id"]
    assert decision["issue_cluster_ids"] == [cluster["id"]]
    assert decision["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert decision["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert decision["payload_preview"][0]["preview_contract"] == (
        "merchant_feed_issue_review_preview_v1"
    )
    decision_preview = decision["payload_preview"][0]
    assert decision_preview["operation_type"] == "MerchantIssueClusterReview"
    assert decision_preview["cluster_id"] == cluster["id"]
    assert decision_preview["issue_type"] == "availability_updated"
    assert decision_preview["issue_type_label"] == "zmiana dostępności do sprawdzenia"
    assert decision_preview["affected_attribute"] == "n:availability"
    assert decision_preview["affected_attribute_label"] == "dostępność"
    assert decision_preview["metric_snapshot"] == {"issue_product_count": 23}
    assert decision_preview["metric_snapshot_labels"] == {
        "issue_product_count": "zgłoszenia problemów"
    }
    assert decision_preview["sample_products_available"] is True
    assert decision_preview["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert decision_preview["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert decision_preview["apply_allowed"] is False
    assert decision_preview["api_mutation_ready"] is False
    assert decision_preview["destructive"] is False
    assert decision["count_semantics"] == "reported_issue_occurrences"
    assert "ponowne zatwierdzenie produktu" in decision["blocked_claim_labels"]
    assert decision["risk_label"] == "średnie ryzyko"
    assert decision["action_ids"] == ["act_review_merchant_feed_issues"]
    assert "zgłoszeń problemu" in decision["summary"]
    assert "wystąpienia problemu" in decision["rationale"]
    assert "act_review_merchant_feed_issues" not in decision["next_step"]
    assert "akcję do sprawdzenia" in decision["next_step"]
    assert decision["why_it_matters"] == decision["rationale"]
    assert decision["operator_action"] == decision["next_step"]
    assert decision["knowledge_card_ids"] == [
        "card_merchant_feed_optimization_playbook",
        "card_google_ads_pmax_playbook",
    ]
    assert decision["expert_rule_ids"] == [
        "merchant_feed_rules_v1",
        "merchant_product_diagnostics_v1",
    ]
    feed_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_feed_health"
    )
    assert feed_section["status"] == "ready"
    assert feed_section["label"] == "Metryki produktów"
    assert feed_section["status_label"] == "gotowe"
    assert "ponowne zatwierdzenie produktu" in feed_section["blocked_claim_labels"]
    assert feed_section["risk_label"] == "średnie ryzyko"
    assert feed_section["summary"].startswith("Metryki Merchant:")
    assert "total_products=10900" in feed_section["summary"]
    issue_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_issue_queue"
    )
    assert issue_section["status"] == "ready"
    assert issue_section["label"] == "Kolejka problemów feedu"
    assert issue_section["status_label"] == "gotowe"
    assert "automatyczna zmiana feedu" in issue_section["blocked_claim_labels"]
    assert issue_section["risk_label"] == "średnie ryzyko"
    assert "problemów feedu" in issue_section["summary"]
    assert "wystąpieniami problemu" in issue_section["summary"]
    assert issue_section["tactical_items"]
    assert operator_summary["top_tactical_item_ids"] == [
        item["id"] for item in issue_section["tactical_items"][:3]
    ]
    assert any(
        item["dimensions"].get("issue_type") == "availability_updated"
        for item in issue_section["tactical_items"]
    )
    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    merchant_action = next(
        action
        for action in actions_response.json()
        if action["id"] == "act_review_merchant_feed_issues"
    )
    assert merchant_action["evidence_summary_label"]
    assert "issue_product_count" not in merchant_action["human_diagnosis"]
    assert "zgłoszenia problemów" in merchant_action["human_diagnosis"]
    assert "ev_refresh" not in merchant_action["human_diagnosis"]
    assert merchant_action["payload"]["issue_clusters"][0]["issue_type"] == (
        "availability_updated"
    )
    assert merchant_action["payload"]["issue_clusters"][0]["product_count"] == 23
    assert merchant_action["payload"]["preview_contract"] == (
        "merchant_feed_issue_review_preview_v1"
    )
    assert merchant_action["payload"]["payload_preview"][0]["preview_contract"] == (
        "merchant_feed_issue_review_preview_v1"
    )
    merchant_preview = merchant_action["payload"]["payload_preview"][0]
    assert merchant_preview["operation_type"] == "MerchantIssueClusterReview"
    assert merchant_preview["cluster_id"] == cluster["id"]
    assert merchant_preview["issue_type"] == "availability_updated"
    assert merchant_preview["issue_type_label"] == "zmiana dostępności do sprawdzenia"
    assert merchant_preview["affected_attribute"] == "n:availability"
    assert merchant_preview["affected_attribute_label"] == "dostępność"
    assert merchant_preview["metric_snapshot"] == {"issue_product_count": 23}
    assert merchant_preview["metric_snapshot_labels"] == {
        "issue_product_count": "zgłoszenia problemów"
    }
    assert merchant_preview["sample_products_available"] is True
    assert merchant_preview["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert merchant_preview["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert merchant_preview["sample_unavailable_reason"] is None
    assert merchant_preview["apply_allowed"] is False
    assert merchant_preview["api_mutation_ready"] is False
    assert merchant_preview["destructive"] is False
    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 1},
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["preview_contract"] == "merchant_feed_issue_review_preview_v1"
    assert "payload_preview_missing" not in preview_payload["blockers"]
    assert preview_payload["preview_items"][0]["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert preview_payload["preview_items"][0]["issue_type_label"] == (
        "zmiana dostępności do sprawdzenia"
    )
    assert preview_payload["preview_items"][0]["affected_attribute_label"] == "dostępność"
    assert preview_payload["preview_items"][0]["sample_titles"] == [
        "Sorbent chemiczny 10 kg"
    ]
    assert preview_payload["preview_items"][0]["apply_allowed"] is False
    serialized = json.dumps(payload)
    assert "5519957373" not in serialized
    assert "adc.json" not in serialized


def test_merchant_product_performance_readiness_joins_sample_ids_to_ads_and_ga4() -> None:
    product_id = "online~pl~PL~SKU-001"
    issue_cluster = MerchantIssueCluster(
        id="merchant_issue_test",
        issue_type="availability_updated",
        severity="NOT_IMPACTED",
        resolution="MERCHANT_ACTION",
        affected_attribute="n:availability",
        country="PL",
        reporting_context="SHOPPING_ADS",
        product_count=23,
        sample_product_ids=[product_id],
        sample_titles=["Sorbent chemiczny 10 kg"],
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_merchant_issue"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        action_id="act_review_merchant_feed_issues",
        next_step="Review produktu.",
    )
    sample_readiness = MerchantProductSampleReadiness(
        status="ready",
        sample_products_available=True,
        sample_count=1,
        sample_product_ids=[product_id],
        sample_product_titles=["Sorbent chemiczny 10 kg"],
        required_read_contracts=[
            "merchant_products_list_product_status",
            "merchant_reports_product_view_issue_filter",
        ],
        source_endpoint="aggregateProductStatuses",
        summary="Merchant read ma sample product ID.",
        next_step="Review próbki.",
    )
    ads_facts = [
        MetricFact(
            name="clicks",
            value=14,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_clicks",
            dimensions={"product_id": "SKU-001"},
        ),
        MetricFact(
            name="cost_micros",
            value=2750000,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_cost",
            dimensions={"product_id": "SKU-001"},
        ),
        MetricFact(
            name="conversions",
            value=1.5,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_conversions",
            dimensions={"product_id": "SKU-001"},
        ),
        MetricFact(
            name="conversion_value",
            value=320.0,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_value",
            dimensions={"product_id": "SKU-001"},
        ),
    ]
    ga4_facts = [
        MetricFact(
            name="ecommerce_purchases",
            value=2,
            period="last_30_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_purchases",
            dimensions={"item_id": "SKU-001"},
        ),
        MetricFact(
            name="purchase_revenue",
            value=410.0,
            period="last_30_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_revenue",
            dimensions={"item_id": "SKU-001"},
        ),
    ]

    readiness = _merchant_product_performance_readiness(
        issue_clusters=[issue_cluster],
        product_sample_readiness=sample_readiness,
        product_metric_facts_by_connector={
            "google_ads": ads_facts,
            "google_analytics_4": ga4_facts,
        },
    )

    assert readiness.status == "ready"
    assert readiness.joined_product_count == 1
    assert readiness.merchant_sample_count == 1
    assert readiness.ads_product_fact_count == 4
    assert readiness.ga4_product_fact_count == 2
    assert readiness.current_read_contracts == [
        "merchant_aggregate_product_statuses",
        "google_ads_product_metric_facts",
        "ga4_item_metric_facts",
    ]
    assert readiness.missing_read_contracts == []
    assert readiness.source_connectors == [
        "google_merchant_center",
        "google_ads",
        "google_analytics_4",
    ]
    assert "ev_merchant_issue" in readiness.evidence_ids
    assert "ev_ads_clicks" in readiness.evidence_ids
    assert "ev_ga4_revenue" in readiness.evidence_ids
    row = readiness.performance_rows[0]
    assert row.product_id == product_id
    assert row.sample_title == "Sorbent chemiczny 10 kg"
    assert row.ads_clicks == 14
    assert row.ads_cost_micros == 2750000
    assert row.ads_conversions == 1.5
    assert row.ads_conversion_value == 320.0
    assert row.ga4_ecommerce_purchases == 2.0
    assert row.ga4_purchase_revenue == 410.0
    assert row.missing_metrics == []
    assert "efekt naprawy produktu" in row.blocked_claims
    assert "zapis do feedu" in row.blocked_claims


def test_merchant_product_performance_readiness_reports_ready_ads_contract_without_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_id = "online~pl~PL~SKU-001"
    issue_cluster = MerchantIssueCluster(
        id="merchant_issue_test",
        issue_type="availability_updated",
        affected_attribute="n:availability",
        country="PL",
        reporting_context="SHOPPING_ADS",
        severity="NOT_IMPACTED",
        resolution="MERCHANT_ACTION",
        product_count=23,
        sample_product_ids=[product_id],
        sample_titles=["Sorbent chemiczny 10 kg"],
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_merchant_issue"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        action_id="act_review_merchant_feed_issues",
        next_step="Review produktu.",
        risk=ActionRisk.medium,
    )
    sample_readiness = MerchantProductSampleReadiness(
        status="ready",
        sample_products_available=True,
        sample_count=1,
        sample_product_ids=[product_id],
        sample_product_titles=["Sorbent chemiczny 10 kg"],
        required_read_contracts=[
            "merchant_products_list_product_status",
            "merchant_reports_product_view_issue_filter",
        ],
        source_endpoint="aggregateProductStatuses",
        summary="Merchant read ma sample product ID.",
        next_step="Review próbki.",
    )
    ga4_facts = [
        MetricFact(
            name="item_purchases",
            value=2,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_item",
            dimensions={"item_id": "SKU-001"},
        )
    ]

    monkeypatch.setattr(
        "wilq.briefing.merchant_diagnostics._product_performance_metric_facts_by_connector",
        lambda _sample_product_ids: {
            "google_ads": [],
            "google_analytics_4": ga4_facts,
        },
    )
    monkeypatch.setattr(
        "wilq.briefing.merchant_diagnostics._latest_connector_refresh",
        lambda connector_id: ConnectorRefreshRun(
            id="refresh_google_ads_shopping_zero_rows",
            connector_id="google_ads",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            evidence_ids=["ev_ads_shopping_zero_rows"],
            metric_summary={
                "shopping_product_performance_status": "ready",
                "shopping_product_performance_lookback_days": 90,
                "shopping_product_performance_row_count": 0,
            },
            summary="Shopping product read returned zero rows.",
        )
        if connector_id == "google_ads"
        else None,
    )

    readiness = _merchant_product_performance_readiness(
        issue_clusters=[issue_cluster],
        product_sample_readiness=sample_readiness,
    )

    assert readiness.status == "ready"
    assert readiness.joined_product_count == 1
    assert readiness.ads_product_fact_count == 0
    assert readiness.ga4_product_fact_count == 1
    assert readiness.current_read_contracts == [
        "merchant_aggregate_product_statuses",
        "google_ads_shopping_product_performance",
        "ga4_item_metric_facts",
    ]
    assert readiness.missing_read_contracts == []
    assert readiness.performance_rows[0].missing_metrics == [
        "ads_clicks",
        "ads_cost_micros",
        "ads_conversions",
        "ads_conversion_value",
        "ga4_purchase_revenue",
    ]


def test_merchant_product_performance_readiness_blocks_state_only_product_join() -> None:
    product_id = "pl~PL~gla_107365"
    issue_cluster = MerchantIssueCluster(
        id="merchant_issue_state_only",
        issue_type="availability_updated",
        affected_attribute="n:availability",
        country="PL",
        reporting_context="SHOPPING_ADS",
        severity="NOT_IMPACTED",
        resolution="MERCHANT_ACTION",
        product_count=1,
        sample_product_ids=[product_id],
        sample_titles=["Dywan sorpcyjny"],
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_merchant_issue"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        action_id="act_review_merchant_feed_issues",
        next_step="Review produktu.",
        risk=ActionRisk.medium,
    )
    sample_readiness = MerchantProductSampleReadiness(
        status="ready",
        sample_products_available=True,
        sample_count=1,
        sample_product_ids=[product_id],
        sample_product_titles=["Dywan sorpcyjny"],
        required_read_contracts=["merchant_products_list_product_status"],
        source_endpoint="aggregateProductStatuses",
        summary="Merchant read ma sample product ID.",
        next_step="Review próbki.",
    )
    state_facts = [
        MetricFact(
            name="shopping_product_state_available",
            value=1,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "gla_107365",
                "product_title": "Dywan sorpcyjny",
                "currency_code": "PLN",
            },
        ),
        MetricFact(
            name="shopping_product_status",
            value="NOT_ELIGIBLE",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "gla_107365",
                "product_status": "NOT_ELIGIBLE",
            },
        ),
        MetricFact(
            name="shopping_product_availability",
            value="OUT_OF_STOCK",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "gla_107365",
                "product_availability": "OUT_OF_STOCK",
            },
        ),
        MetricFact(
            name="shopping_product_price_micros",
            value=123450000,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={"product_item_id": "gla_107365"},
        ),
    ]

    readiness = _merchant_product_performance_readiness(
        issue_clusters=[issue_cluster],
        product_sample_readiness=sample_readiness,
        product_metric_facts_by_connector={
            "google_ads": state_facts,
            "google_analytics_4": [],
        },
    )

    assert readiness.status == "blocked"
    assert readiness.joined_product_count == 1
    assert readiness.current_read_contracts == [
        "merchant_aggregate_product_statuses",
        "google_ads_shopping_product_state",
    ]
    assert readiness.missing_read_contracts == [
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    ]
    assert "stan produktu z Ads" in readiness.summary
    assert "Zwrot z reklam" in readiness.next_step
    row = readiness.performance_rows[0]
    assert row.issue_type == "availability_updated"
    assert row.affected_attribute == "n:availability"
    assert row.country == "PL"
    assert row.reporting_context == "SHOPPING_ADS"
    assert row.ads_product_title == "Dywan sorpcyjny"
    assert row.ads_product_status == "NOT_ELIGIBLE"
    assert row.ads_product_availability == "OUT_OF_STOCK"
    assert row.ads_product_price_micros == 123450000
    assert row.ads_product_currency_code == "PLN"
    assert readiness.performance_rows[0].missing_metrics == [
        "ads_clicks",
        "ads_cost_micros",
        "ads_conversions",
        "ads_conversion_value",
        "ga4_ecommerce_purchases",
        "ga4_purchase_revenue",
    ]


def test_merchant_diagnostics_promotes_ads_product_state_review_decision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_state_review.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_state_review.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    adc_json = tmp_path / "adc.json"
    adc_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(adc_json))
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "5519957373")
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_merchant_product_status_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Merchant Center zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "total_products": 10900,
                "item_level_issue_count": 14,
                "merchant_action_issue_count": 14,
            },
            metric_facts=[
                VendorMetricFact(
                    "issue_product_count",
                    14,
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "n:availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                    },
                ),
                VendorMetricFact(
                    "sample_product_id",
                    "online~pl~PL~SKU-001",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "n:availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "1",
                    },
                ),
            ],
        ),
    )
    state_facts = [
        MetricFact(
            name="shopping_product_state_available",
            value=1,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "SKU-001",
                "product_title": "Sorbent chemiczny 10 kg",
                "currency_code": "PLN",
            },
        ),
        MetricFact(
            name="shopping_product_status",
            value="NOT_ELIGIBLE",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={"product_item_id": "SKU-001"},
        ),
        MetricFact(
            name="shopping_product_availability",
            value="OUT_OF_STOCK",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={"product_item_id": "SKU-001"},
        ),
        MetricFact(
            name="shopping_product_price_micros",
            value=123450000,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "SKU-001",
                "currency_code": "PLN",
            },
            previous_value=120000000,
            delta=3450000,
            delta_percent=2.875,
        ),
    ]
    current_price_collected_at = datetime(2026, 6, 24, 8, 0, tzinfo=UTC)
    previous_price_collected_at = datetime(2026, 6, 23, 8, 0, tzinfo=UTC)
    state_facts[-1] = state_facts[-1].model_copy(
        update={
            "collected_at": current_price_collected_at,
            "previous_collected_at": previous_price_collected_at,
            "previous_evidence_id": "ev_ads_product_state_previous",
        }
    )
    monkeypatch.setattr(
        "wilq.briefing.merchant_diagnostics._product_performance_metric_facts_by_connector",
        lambda _sample_product_ids: {
            "google_ads": state_facts,
            "google_analytics_4": [],
        },
    )

    refresh_response = client.post(
        "/api/connectors/google_merchant_center/refresh",
        json={"mode": "vendor_read", "reason": "merchant state review decision test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/merchant/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    decision = next(
        item
        for item in payload["decision_queue"]
        if item["id"] == "merchant_decision_review_ads_product_state_mapping"
    )
    assert decision["decision_type"] == "review_product_state_mapping"
    assert decision["status"] == "ready"
    assert decision["metric_tiles"] == {
        "powiązane produkty": 1,
        "NOT_ELIGIBLE": 1,
        "OUT_OF_STOCK": 1,
    }
    assert "zwrot z reklam na poziomie produktu" in decision["blocked_claims"]
    assert decision["payload_preview"][0]["preview_contract"] == (
        "merchant_product_state_review_preview_v1"
    )
    assert decision["payload_preview"][0]["products"][0]["product_id"] == (
        "online~pl~PL~SKU-001"
    )
    assert decision["payload_preview"][0]["products"][0]["ads_product_status"] == (
        "NOT_ELIGIBLE"
    )
    supplemental_preview = next(
        preview
        for preview in decision["payload_preview"]
        if preview["preview_contract"] == "merchant_supplemental_feed_review_preview_v1"
    )
    assert supplemental_preview["apply_allowed"] is False
    assert supplemental_preview["api_mutation_ready"] is False
    assert supplemental_preview["primary_feed_mutation_allowed"] is False
    assert supplemental_preview["candidates"][0]["product_id"] == (
        "online~pl~PL~SKU-001"
    )
    assert supplemental_preview["candidates"][0]["review_fields"] == [
        "availability",
        "price",
    ]
    assert supplemental_preview["candidates"][0]["candidate_status"] == (
        "requires_human_value_confirmation"
    )
    price_readiness = payload["price_impact_readiness"]
    assert price_readiness["status"] == "blocked"
    assert price_readiness["products_with_current_price"] == 1
    assert price_readiness["products_with_previous_price"] == 1
    assert price_readiness["products_with_price_change"] == 1
    assert price_readiness["products_with_unchanged_price_history"] == 0
    assert price_readiness["products_with_performance_metrics"] == 0
    assert price_readiness["missing_read_contracts"] == [
        "google_ads_or_ga4_product_performance_window"
    ]
    price_preview = price_readiness["payload_preview"][0]
    assert price_preview["preview_contract"] == "merchant_price_impact_readiness_preview_v1"
    assert price_preview["products"][0]["current_price_micros"] == 123450000
    assert price_preview["products"][0]["current_price_collected_at"] == (
        "2026-06-24T08:00:00+00:00"
    )
    assert price_preview["products"][0]["previous_price_micros"] == 120000000
    assert price_preview["products"][0]["previous_price_collected_at"] == (
        "2026-06-23T08:00:00+00:00"
    )
    assert price_preview["products"][0]["previous_price_evidence_id"] == (
        "ev_ads_product_state_previous"
    )
    assert price_preview["products"][0]["has_price_snapshot_history"] is True
    assert price_preview["products"][0]["has_price_change"] is True
    assert price_preview["products"][0]["price_delta_micros"] == 3450000
    assert price_preview["products"][0]["has_product_performance_metrics"] is False
    price_decision = next(
        item
        for item in payload["decision_queue"]
        if item["id"] == "merchant_decision_review_price_impact_readiness"
    )
    assert price_decision["decision_type"] == "review_price_impact_readiness"
    assert price_decision["status"] == "blocked"
    assert price_decision["metric_tiles"] == {
        "ceny bieżące": 1,
        "historia ceny": 1,
        "zmiany ceny": 1,
        "performance": 0,
    }
    assert price_decision["payload_preview"] == price_readiness["payload_preview"]
    assert price_decision["source_connectors"] == price_readiness["source_connectors"]
    assert price_decision["evidence_ids"] == price_readiness["evidence_ids"]
    assert price_decision["blocked_claims"] == price_readiness["blocked_claims"]
    assert price_decision["risk"] == "medium"
    readiness = payload["product_performance_readiness"]
    assert readiness["status"] == "blocked"
    assert readiness["missing_read_contracts"] == [
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    ]
    row = readiness["performance_rows"][0]
    assert row["product_id"] == "online~pl~PL~SKU-001"
    assert row["issue_type"] == "availability_updated"
    assert row["ads_product_title"] == "Sorbent chemiczny 10 kg"
    assert row["ads_product_status"] == "NOT_ELIGIBLE"
    assert row["ads_product_availability"] == "OUT_OF_STOCK"


def test_merchant_price_impact_blocks_snapshot_history_without_price_change() -> None:
    readiness = _merchant_price_impact_readiness(
        MerchantProductPerformanceReadiness(
            status="blocked",
            joined_product_count=1,
            merchant_sample_count=1,
            ads_product_fact_count=4,
            ga4_product_fact_count=0,
            current_read_contracts=["google_ads_shopping_product_state"],
            required_read_contracts=["google_ads_shopping_product_performance"],
            missing_read_contracts=["google_ads_shopping_product_performance"],
            join_key_candidates=["product_item_id"],
            sample_product_ids=["SKU-001"],
            performance_rows=[
                MerchantProductPerformanceRow(
                    product_id="SKU-001",
                    sample_title="Sorbent chemiczny",
                    source_connectors=["google_ads"],
                    evidence_ids=["ev_ads_product_state"],
                    ads_product_price_micros=123450000,
                    ads_product_currency_code="PLN",
                    ads_product_price_collected_at=datetime(
                        2026, 6, 24, 8, 0, tzinfo=UTC
                    ),
                    ads_product_previous_price_micros=123450000,
                    ads_product_previous_price_collected_at=datetime(
                        2026, 6, 23, 8, 0, tzinfo=UTC
                    ),
                    ads_product_previous_price_evidence_id="ev_ads_previous",
                    ads_product_price_delta_micros=0,
                    ads_product_price_delta_percent=0.0,
                )
            ],
            source_connectors=["google_merchant_center", "google_ads"],
            evidence_ids=["ev_merchant", "ev_ads_product_state"],
            summary="State-only price snapshot.",
            next_step="Zatrzymaj ocenę wpływu ceny.",
            blocked_claims=["wpływ zmiany ceny"],
        )
    )

    assert readiness.status == "blocked"
    assert readiness.products_with_previous_price == 1
    assert readiness.products_with_price_change == 0
    assert readiness.products_with_unchanged_price_history == 1
    assert "google_ads_shopping_product_price_history" in readiness.current_read_contracts
    assert "merchant_price_change_event_or_snapshot" not in readiness.current_read_contracts
    assert "merchant_price_change_event_or_snapshot" in readiness.missing_read_contracts
    assert "bez wykrytej zmiany ceny" in readiness.summary
    preview_product = readiness.payload_preview[0]["products"][0]
    assert preview_product["has_price_snapshot_history"] is True
    assert preview_product["has_price_change"] is False


def test_merchant_diagnostics_groups_reporting_contexts_into_one_operator_decision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_context_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_context_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    adc_json = tmp_path / "adc.json"
    adc_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(adc_json))
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "5519957373")
    issue_dimensions = {
        "issue_type": "missing_potentially_required_attribute",
        "affected_attribute": "n:unit_pricing_measure",
        "country": "PL",
        "severity": "NOT_IMPACTED",
        "resolution": "MERCHANT_ACTION",
    }
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_merchant_product_status_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Merchant Center zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "total_products": 10900,
                "item_level_issue_count": 15,
                "merchant_action_issue_count": 15,
            },
            metric_facts=[
                VendorMetricFact(
                    "issue_product_count",
                    892,
                    {**issue_dimensions, "reporting_context": "ALL_CONTEXTS"},
                ),
                VendorMetricFact(
                    "issue_product_count",
                    446,
                    {**issue_dimensions, "reporting_context": "FREE_LISTINGS"},
                ),
                VendorMetricFact(
                    "issue_product_count",
                    446,
                    {**issue_dimensions, "reporting_context": "SHOPPING_ADS"},
                ),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_merchant_center/refresh",
        json={"mode": "vendor_read", "reason": "merchant reporting context grouping test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/merchant/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    issue_decisions = [
        decision
        for decision in payload["decision_queue"]
        if decision["issue_type"] == "missing_potentially_required_attribute"
        and decision["affected_attribute"] == "n:unit_pricing_measure"
    ]
    assert len(issue_decisions) == 1
    decision = issue_decisions[0]
    assert decision["reporting_context"] is None
    assert decision["metric_tiles"] == {
        "max zgłoszeń": 892,
        "raporty razem": 1784,
        "konteksty": 3,
    }
    assert "wszystkie konteksty, bezpłatne wyniki produktowe, reklamy produktowe" in decision[
        "summary"
    ]
    assert "nie jest liczbą unikalnych produktów" in decision["rationale"]
    assert set(decision["issue_cluster_ids"]) == {
        cluster["id"] for cluster in payload["issue_clusters"]
    }
    assert decision["count_semantics"] == "reported_issue_occurrences"
    assert len(decision["metric_facts"]) == 3
    decision_preview = decision["payload_preview"][0]
    assert decision_preview["metric_snapshot"] == {
        "max_issue_product_count": 892,
        "reported_issue_occurrences": 1784,
        "reporting_contexts": 3,
    }
    assert decision_preview["reported_issue_occurrences"] == 1784
    assert len(payload["issue_clusters"]) == 3
    assert payload["operator_summary"]["decision_source"] == "decision_queue"


def test_content_diagnostics_blocks_until_vendor_read_when_no_content_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_block_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_block_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)

    diagnostics = build_content_diagnostics(
        tactical_items=[],
        metric_facts=[],
        actions=[],
    )

    assert diagnostics.live_data_available is False
    assert len(diagnostics.decision_queue) == 1
    decision = diagnostics.decision_queue[0]
    assert decision.id == "content_block_vendor_read"
    assert decision.decision_type == "block_until_vendor_read"
    assert decision.status == "blocked"
    assert decision.source_connectors == [
        "google_search_console",
        "wordpress_ekologus",
    ]
    assert decision.evidence_ids == [
        "ev_connector_google_search_console_status",
        "ev_connector_wordpress_ekologus_status",
    ]
    assert decision.metric_tiles == {"blockery": 2}
    assert "rekomendacja bez danych źródłowych" in decision.blocked_claims
    assert "odczyt danych" in decision.next_step
    assert diagnostics.operator_summary.top_decision_ids == [decision.id]
    assert "blokada do czasu odczytu danych" in (
        diagnostics.operator_summary.decision_type_labels
    )
    assert diagnostics.marketer_decision is not None
    assert diagnostics.marketer_decision.technical_decision_id == decision.id
    assert diagnostics.marketer_decision.status == "blocked"
    assert "GSC" in diagnostics.marketer_decision.decision
    assert "automatyczna publikacja" in diagnostics.marketer_decision.blocked_claims
    assert all("_" not in value for value in diagnostics.marketer_decision.missing_inputs)

    preflight = build_content_preflight(diagnostics)
    assert preflight.primary_item is not None
    assert preflight.primary_item.recommended_mode == "block"
    assert preflight.primary_item.status == "blocked"
    assert preflight.primary_item.create_allowed is False
    assert preflight.primary_item.draft_allowed is False
    assert preflight.primary_item.wordpress_draft_allowed is False
    assert preflight.primary_item.sales_brief_allowed is False
    assert preflight.blocker_count == 1


def test_content_diagnostics_exposes_query_page_inventory_queue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_diag_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_diag_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)
    service_account_json = tmp_path / "google_adc.json"
    service_account_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_search_console_site_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt GSC zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"clicks": 12, "impressions": 120},
            metric_facts=[
                VendorMetricFact(
                    "clicks",
                    12,
                    {
                        "query": "zielony ład",
                        "page": (
                            "https://www.ekologus.pl/"
                            "europejski-zielony-lad-co-to-takiego/"
                        ),
                    },
                ),
                VendorMetricFact(
                    "impressions",
                    120,
                    {
                        "query": "zielony ład",
                        "page": (
                            "https://www.ekologus.pl/"
                            "europejski-zielony-lad-co-to-takiego/"
                        ),
                    },
                ),
            ],
        ),
    )
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_wordpress_content_inventory",
        lambda connector_id, request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="WordPress inventory completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"content_object_count": 16, "pages_total": 4},
            metric_facts=[
                VendorMetricFact("content_object_count", 16, {}),
                VendorMetricFact(
                    "content_object_seen",
                    1,
                    {
                        "connector_id": "wordpress_ekologus",
                        "content_type": "sitemap",
                        "status": "indexed",
                        "content_url": (
                            "https://www.ekologus.pl/"
                            "europejski-zielony-lad-co-to-takiego/"
                        ),
                        "modified_gmt": "2024-07-11T07:04:02+00:00",
                        "inventory_source": "public_sitemap",
                    },
                ),
            ],
        ),
    )

    gsc_response = client.post(
        "/api/connectors/google_search_console/refresh",
        json={"mode": "vendor_read", "reason": "content diagnostics test"},
    )
    wordpress_response = client.post(
        "/api/connectors/wordpress_ekologus/refresh",
        json={"mode": "vendor_read", "reason": "content diagnostics test"},
    )
    assert gsc_response.status_code == 200
    assert wordpress_response.status_code == 200
    ahrefs_collected_at = datetime(2026, 6, 18, 9, 0, tzinfo=UTC)
    ahrefs_run = ConnectorRefreshRun(
        id="refresh_ahrefs_gap_records",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=ahrefs_collected_at,
        completed_at=ahrefs_collected_at,
        evidence_ids=["ev_refresh_ahrefs_gap_records"],
        metric_summary={"ahrefs_content_gap_count": 2, "ahrefs_backlink_gap_count": 1},
        vendor_data_collected=True,
        summary="Dane luk Ahrefs odczytane przez test adapter.",
    )
    metric_store().save_connector_refresh_metrics(
        ahrefs_run,
        detailed_facts=[
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "zielony ład",
                    "competitor_domain": "konkurent.example",
                },
            ),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "audyt środowiskowy",
                    "competitor_domain": "konkurent.example",
                },
            ),
            VendorMetricFact(
                "ahrefs_organic_keyword_gap_count",
                1,
                {
                    "gap_type": "organic_keyword_gap",
                    "keyword": "pozwolenie zintegrowane",
                    "competitor_domain": "konkurent.example",
                },
            ),
            VendorMetricFact(
                "ahrefs_backlink_gap_count",
                1,
                {
                    "gap_type": "backlink_gap",
                    "competitor_domain": "konkurent.example",
                    "source_url": "branża.example",
                },
            ),
        ],
    )

    response = client.get("/api/content/diagnostics")
    preflight_response = client.get("/api/content/preflight")

    assert response.status_code == 200
    assert preflight_response.status_code == 200
    payload = response.json()
    preflight_payload = preflight_response.json()
    assert payload["language"] == "pl-PL"
    assert payload["live_data_available"] is True
    assert payload["query_page_count"] >= 1
    assert payload["matched_inventory_count"] >= 1
    assert "act_prepare_content_refresh_queue" in payload["action_ids"]
    query_section = next(
        section for section in payload["sections"] if section["id"] == "content_query_page_matrix"
    )
    assert query_section["status"] == "ready"
    assert query_section["tactical_items"]
    assert any(
        item["dimensions"].get("query") == "zielony ład"
        for item in query_section["tactical_items"]
    )
    inventory_section = next(
        section for section in payload["sections"] if section["id"] == "content_inventory_match"
    )
    assert inventory_section["status"] == "ready"
    assert any(
        item["dimensions"].get("wordpress_match") == "found"
        for item in inventory_section["tactical_items"]
    )
    assert payload["decision_queue"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "content_operator_summary"
    assert operator_summary["title"] == "Co marketer ma zrobić teraz z treściami"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["confirmed_wordpress_count"] == sum(
        1
        for decision in payload["decision_queue"]
        if decision.get("wordpress_match") == "found"
    )
    assert operator_summary["missing_wordpress_count"] == sum(
        1
        for decision in payload["decision_queue"]
        if decision.get("wordpress_match") == "missing"
    )
    assert operator_summary["current_site_match_count"] == sum(
        1
        for decision in payload["decision_queue"]
        if decision.get("final_canonical_url")
        and "ekologus.dev.proudsite.pl" not in str(decision.get("final_canonical_url"))
    )
    assert not any(key.startswith("target_site_") for key in operator_summary)
    assert not any(key.startswith("mapping_review_") for key in operator_summary)
    assert not any(key.startswith("transition_candidate") for key in operator_summary)
    assert "odświeżenie albo scalenie" in operator_summary["decision_type_labels"]
    assert "act_prepare_content_refresh_queue" in operator_summary["action_ids"]
    assert "wzrost liczby leadów" in operator_summary["blocked_claims"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    marketer_decision = payload["marketer_decision"]
    assert marketer_decision["technical_decision_id"] == payload["decision_queue"][0]["id"]
    assert marketer_decision["decision"]
    assert marketer_decision["why_it_matters"]
    assert marketer_decision["safe_next_action"]
    assert marketer_decision["evidence_summary"]
    assert marketer_decision["source_connectors"]
    assert marketer_decision["evidence_ids"]
    assert marketer_decision["measurement_plan"]
    if marketer_decision["source_public_url"]:
        assert marketer_decision["source_public_url"].startswith("https://www.ekologus.pl/")
    if marketer_decision["final_canonical_url"]:
        assert "ekologus.dev.proudsite.pl" not in marketer_decision["final_canonical_url"]
        assert marketer_decision["final_canonical_url"].startswith(
            "https://www.ekologus.pl/"
        )
    assert not any(
        "podgląd" in value.lower() for value in marketer_decision["missing_inputs"]
    )
    assert not any("_" in value for value in marketer_decision["missing_inputs"])
    assert not any(
        "ActionObject" in value
        for value in marketer_decision.values()
        if isinstance(value, str)
    )
    first_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "refresh_or_merge"
    )
    assert first_decision["decision_type"] == "refresh_or_merge"
    assert first_decision["status"] == "ready"
    assert first_decision["priority"] == 23
    assert first_decision["metric_tiles"] == {
        "zapytania": 1,
        "WP": "znaleziono",
        "wyświetlenia": 120,
        "kliknięcia": 12,
        "CTR": "10.00%",
    }
    assert first_decision["title"] == 'SEO: odśwież lub scal "zielony ład" (1 zapytanie)'
    assert first_decision["summary"] == (
        'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: '
        '"zielony ład". WordPress potwierdza istniejącą stronę, więc to jest '
        "decyzja odświeżenia albo scalenia, nie nowy artykuł."
    )
    assert first_decision["primary_query"] == "zielony ład"
    assert first_decision["total_clicks"] == 12
    assert first_decision["total_impressions"] == 120
    assert first_decision["aggregate_ctr"] == 0.1
    assert first_decision["wordpress_match"] == "found"
    assert first_decision["wordpress_match_confidence"] == "exact_url"
    assert first_decision["source_public_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert first_decision["final_canonical_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert first_decision["intended_final_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert first_decision["preview_url"] is None
    assert not any(key.startswith("target_site_") for key in first_decision)
    assert not any(key.startswith("mapping_review_") for key in first_decision)
    assert not any(key.startswith("transition_candidate") for key in first_decision)
    assert first_decision["inventory_gate_status"] == "confirmed_current_inventory"
    assert first_decision["canonical_gate_status"] == "current_url_confirmed"
    assert first_decision["duplicate_gate_status"] == "refresh_or_merge_required"
    assert "odświeżenie albo scalenie" in first_decision["content_gate_summary"]
    assert "nowy artykuł" in first_decision["content_gate_summary"]
    assert first_decision["normalized_page_path"] == (
        "/europejski-zielony-lad-co-to-takiego"
    )
    assert first_decision["evidence_ids"]
    assert "act_prepare_content_refresh_queue" in first_decision["action_ids"]
    assert first_decision["knowledge_card_ids"] == [
        "card_gsc_seo_content_playbook",
        "card_wordpress_content_refresh_playbook",
    ]
    assert first_decision["expert_rule_ids"] == [
        "seo_gsc_opportunities_v1",
        "seo_query_page_matrix_v1",
        "seo_content_decay_v1",
        "seo_cannibalization_v1",
        "content_duplication_rules_v1",
        "content_brief_rules_v1",
    ]
    preflight_item = next(
        item
        for item in preflight_payload["items"]
        if item["technical_decision_id"] == first_decision["id"]
    )
    assert preflight_payload["primary_item"] == preflight_item
    assert preflight_item["recommended_mode"] == "refresh"
    assert preflight_item["recommended_mode_label"] == "odświeżyć"
    assert preflight_item["status"] == "review_required"
    assert preflight_item["status_label"] == "wymaga sprawdzenia"
    assert preflight_item["create_allowed"] is False
    assert preflight_item["draft_allowed"] is False
    assert preflight_item["wordpress_draft_allowed"] is False
    assert preflight_item["sales_brief_allowed"] is True
    assert preflight_item["source_public_url"] == first_decision["source_public_url"]
    assert preflight_item["final_canonical_url"] == first_decision["final_canonical_url"]
    assert preflight_item["preview_url"] is None
    assert preflight_item["inventory_gate_status"] == "confirmed_current_inventory"
    assert preflight_item["inventory_gate_status_label"] == (
        "spis potwierdzony na obecnej stronie"
    )
    assert preflight_item["canonical_gate_status"] == "current_url_confirmed"
    assert preflight_item["canonical_gate_status_label"] == "obecny URL potwierdzony"
    assert preflight_item["duplicate_gate_status"] == "refresh_or_merge_required"
    assert preflight_item["duplicate_gate_status_label"] == (
        "odśwież albo scal zamiast pisać od nowa"
    )
    assert preflight_item["claim_gate_status_label"]
    assert preflight_item["service_mapping_status_label"]
    assert preflight_item["similar_existing_urls"] == [
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    ]
    assert "1 zapytań z GSC" in preflight_item["query_overlap_summary"]
    assert "sprawdzeniu ryzykownych obietnic" in preflight_item["next_step"]
    ahrefs_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "review_ahrefs_gap_records"
    )
    assert ahrefs_decision["status"] == "ready"
    assert ahrefs_decision["title"] == (
        "Ahrefs: zweryfikuj luki SEO przed planem treści"
    )
    assert ahrefs_decision["metric_tiles"] == {
        "rekordy Ahrefs": 4,
        "pasujące": 3,
        "do sprawdzenia": 0,
        "poza zakresem": 1,
        "GSC overlap": 1,
        "WP overlap": 1,
        "luki treści": 2,
        "luki backlinków": 1,
    }
    assert {"zielony ład", "audyt środowiskowy", "pozwolenie zintegrowane"}.issubset(
        set(ahrefs_decision["queries"])
    )
    assert "branża.example" not in json.dumps(ahrefs_decision["queries"])
    assert len(ahrefs_decision["ahrefs_candidate_rows"]) == 3
    zielony_lad_candidate = next(
        candidate
        for candidate in ahrefs_decision["ahrefs_candidate_rows"]
        if candidate["topic"] == "zielony ład"
    )
    assert zielony_lad_candidate["relevance_status"] == "relevant"
    assert zielony_lad_candidate["gsc_demand"] == "present"
    assert zielony_lad_candidate["wordpress_inventory_match"] == "present"
    assert zielony_lad_candidate["gsc_overlap_terms"] == ["zielony ład"]
    assert zielony_lad_candidate["wordpress_overlap_urls"] == [
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    ]
    assert "ekologus_domain_term" in zielony_lad_candidate["business_relevance_reasons"]
    assert "gsc_overlap" in zielony_lad_candidate["business_relevance_reasons"]
    assert "wordpress_inventory_overlap" in zielony_lad_candidate[
        "business_relevance_reasons"
    ]
    assert "content_candidate" in zielony_lad_candidate["business_relevance_reasons"]
    assert zielony_lad_candidate["evidence_ids"] == ["ev_refresh_ahrefs_gap_records"]
    assert "Wspólne sygnały: GSC: zielony ład" in zielony_lad_candidate["next_step"]
    assert "branża.example" not in json.dumps(ahrefs_decision["ahrefs_candidate_rows"])
    assert ahrefs_decision["source_connectors"] == ["ahrefs"]
    assert ahrefs_decision["evidence_ids"] == ["ev_refresh_ahrefs_gap_records"]
    assert "act_prepare_content_refresh_queue" in ahrefs_decision["action_ids"]
    assert ahrefs_decision["knowledge_card_ids"] == [
        "card_ahrefs_content_gap_playbook",
        "card_gsc_seo_content_playbook",
        "card_wordpress_content_refresh_playbook",
    ]
    assert ahrefs_decision["expert_rule_ids"] == [
        "content_brief_rules_v1",
        "content_duplication_rules_v1",
    ]
    assert "rekomendacja treści poza zakresem" in ahrefs_decision["blocked_claims"]
    assert "wzrost ruchu" in ahrefs_decision["blocked_claims"]
    assert "ev_refresh_ahrefs_gap_records" in payload["evidence_ids"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-content-strategist"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["content_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
    assert context_payload["content_preflight"]["primary_item"]["technical_decision_id"] == (
        first_decision["id"]
    )
    assert context_payload["content_preflight"]["primary_item"]["recommended_mode"] == "refresh"
    assert context_payload["content_preflight"]["primary_item"]["draft_allowed"] is False
    assert context_payload["content_diagnostics"]["action_ids"] == payload["action_ids"]
    context_decision = next(
        decision
        for decision in context_payload["content_diagnostics"]["decision_queue"]
        if decision["id"] == first_decision["id"]
    )
    assert context_decision["decision_type"] == first_decision["decision_type"]
    assert context_decision["status"] == first_decision["status"]
    assert context_decision["priority"] == first_decision["priority"]
    assert context_decision["metric_tiles"] == first_decision["metric_tiles"]
    assert context_decision["summary"] == first_decision["summary"]
    assert context_decision["primary_query"] == first_decision["primary_query"]
    assert context_decision["total_impressions"] == first_decision["total_impressions"]
    assert context_decision["wordpress_match_confidence"] == first_decision[
        "wordpress_match_confidence"
    ]
    assert context_decision["normalized_page_path"] == first_decision["normalized_page_path"]
    assert context_decision["inventory_gate_status"] == first_decision[
        "inventory_gate_status"
    ]
    assert context_decision["canonical_gate_status"] == first_decision[
        "canonical_gate_status"
    ]
    assert context_decision["duplicate_gate_status"] == first_decision[
        "duplicate_gate_status"
    ]
    assert context_decision["content_gate_summary"] == first_decision[
        "content_gate_summary"
    ]
    assert context_decision["source_connectors"] == first_decision["source_connectors"]
    assert context_decision["evidence_ids"] == first_decision["evidence_ids"]
    assert context_decision["action_ids"] == first_decision["action_ids"]
    assert context_decision["knowledge_card_ids"] == first_decision["knowledge_card_ids"]
    assert context_decision["expert_rule_ids"] == first_decision["expert_rule_ids"]
    context_knowledge_card_ids = {
        card["id"] for card in context_payload["knowledge_card_summaries"]
    }
    context_expert_rule_ids = {
        rule["id"] for rule in context_payload["expert_rule_summaries"]
    }
    assert set(context_decision["knowledge_card_ids"]).issubset(
        context_knowledge_card_ids
    )
    assert set(context_decision["expert_rule_ids"]).issubset(context_expert_rule_ids)
    assert any(
        decision["decision_type"] == "review_ahrefs_gap_records"
        for decision in context_payload["content_diagnostics"]["decision_queue"]
    )
    context_ahrefs_decision = next(
        decision
        for decision in context_payload["content_diagnostics"]["decision_queue"]
        if decision["decision_type"] == "review_ahrefs_gap_records"
    )
    assert context_ahrefs_decision["ahrefs_candidate_rows"] == ahrefs_decision[
        "ahrefs_candidate_rows"
    ]

    gsc_context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-gsc-content-doctor"},
    )
    assert gsc_context_response.status_code == 200
    gsc_context_payload = gsc_context_response.json()
    assert all(
        decision["decision_type"] != "review_ahrefs_gap_records"
        for decision in gsc_context_payload["content_diagnostics"]["decision_queue"]
    )
    assert all(
        "_ahrefs" not in str(evidence_id)
        for evidence_id in gsc_context_payload["content_diagnostics"]["evidence_ids"]
    )
    serialized = json.dumps(payload)
    assert "google_adc.json" not in serialized
    assert "app-password" not in serialized


def test_content_diagnostics_preserves_gsc_query_page_after_newer_aggregate_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_window_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_window_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)
    service_account_json = tmp_path / "google_adc.json"
    service_account_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    dimensioned_at = datetime(2026, 6, 18, 8, 0, tzinfo=UTC)
    query_page_run = ConnectorRefreshRun(
        id="refresh_gsc_query_page",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=dimensioned_at,
        completed_at=dimensioned_at,
        evidence_ids=["ev_refresh_gsc_query_page"],
        metric_summary={"clicks": 4, "impressions": 4429},
        vendor_data_collected=True,
        summary="Older GSC query/page vendor read.",
    )
    metric_store().save_connector_refresh_metrics(
        query_page_run,
        detailed_facts=[
            VendorMetricFact(
                "clicks",
                4,
                {
                    "query": "bdo co to",
                    "page": (
                        "https://www.ekologus.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/"
                    ),
                },
            ),
            VendorMetricFact(
                "impressions",
                4429,
                {
                    "query": "bdo co to",
                    "page": (
                        "https://www.ekologus.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/"
                    ),
                },
            ),
            VendorMetricFact(
                "ctr",
                0.0009031384059607134,
                {
                    "query": "bdo co to",
                    "page": (
                        "https://www.ekologus.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/"
                    ),
                },
            ),
            VendorMetricFact(
                "average_position",
                9.441183111311808,
                {
                    "query": "bdo co to",
                    "page": (
                        "https://www.ekologus.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/"
                    ),
                },
            ),
        ],
    )

    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_inventory",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=dimensioned_at,
        completed_at=dimensioned_at,
        evidence_ids=["ev_refresh_wordpress_inventory"],
        metric_summary={"content_object_count": 16, "pages_total": 4},
        vendor_data_collected=True,
        summary="WordPress inventory vendor read.",
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                "content_object_seen",
                1,
                {
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "status": "indexed",
                    "content_url": (
                        "https://www.ekologus.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/"
                    ),
                    "inventory_source": "public_sitemap",
                },
            )
        ],
    )
    local_state_store().save_connector_refresh_run(wordpress_run)

    latest_aggregate_run: ConnectorRefreshRun | None = None
    for index in range(151):
        collected_at = datetime(2026, 6, 19, 8, index % 60, tzinfo=UTC)
        aggregate_run = ConnectorRefreshRun(
            id=f"refresh_gsc_aggregate_{index}",
            connector_id="google_search_console",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=collected_at,
            completed_at=collected_at,
            evidence_ids=[f"ev_refresh_gsc_aggregate_{index}"],
            metric_summary={"clicks": 12, "impressions": 120},
            vendor_data_collected=True,
            summary="Newer aggregate GSC vendor read.",
        )
        metric_store().save_connector_refresh_metrics(aggregate_run)
        latest_aggregate_run = aggregate_run
    assert latest_aggregate_run is not None
    local_state_store().save_connector_refresh_run(latest_aggregate_run)

    response = client.get("/api/content/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is True
    assert payload["query_page_count"] >= 1
    assert payload["decision_queue"]
    assert any(
        decision["page"]
        == "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
        for decision in payload["decision_queue"]
    )
    query_section = next(
        section for section in payload["sections"] if section["id"] == "content_query_page_matrix"
    )
    assert query_section["status"] == "ready"
    assert any(
        item["dimensions"].get("query") == "bdo co to"
        for item in query_section["tactical_items"]
    )


def test_gsc_vendor_read_uses_search_analytics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setattr(
        "wilq.connectors.google_search_console.client.google_access_token",
        lambda scopes: "gsc-access-token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "searchconsole.googleapis.com"
        assert (
            request.url.path
            == "/webmasters/v3/sites/sc-domain:ekologus.pl/searchAnalytics/query"
        )
        assert request.headers["authorization"] == "Bearer gsc-access-token"
        body = json.loads(request.content.decode())
        assert body["dimensions"] == ["query", "page"]
        assert body["rowLimit"] == 10
        assert "startDate" in body
        assert "endDate" in body
        return httpx.Response(
            200,
            json={
                "rows": [
                    {
                        "keys": ["odpady przemysłowe", "https://ekologus.pl/oferta/"],
                        "clicks": 12,
                        "impressions": 120,
                        "ctr": 0.1,
                        "position": 4.5,
                    }
                ]
            },
        )

    result = refresh_search_console_site_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary["row_count"] == 1
    assert result.metric_summary["clicks"] == 12
    assert result.metric_summary["impressions"] == 120
    assert result.metric_summary["ctr"] == 0.1
    assert result.metric_summary["average_position"] == 4.5
    assert result.metric_facts[0].name == "clicks"
    assert result.metric_facts[0].value == 12
    assert result.metric_facts[0].dimensions == {
        "query": "odpady przemysłowe",
        "page": "https://ekologus.pl/oferta/",
    }


def test_ga4_vendor_read_uses_run_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GA4_PROPERTY_ID", "properties/411974093")
    monkeypatch.setattr(
        "wilq.connectors.google_analytics_4.client.google_access_token",
        lambda scopes: "ga4-access-token",
    )

    requests_seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "analyticsdata.googleapis.com"
        assert request.url.path == "/v1beta/properties/411974093:runReport"
        assert request.headers["authorization"] == "Bearer ga4-access-token"
        body = json.loads(request.content.decode())
        requests_seen.append(body)
        dimensions = [dimension["name"] for dimension in body["dimensions"]]
        if dimensions == [
            "landingPagePlusQueryString",
            "sessionSourceMedium",
            "sessionCampaignName",
        ]:
            assert [metric["name"] for metric in body["metrics"]] == [
                "activeUsers",
                "sessions",
                "screenPageViews",
                "eventCount",
                "engagementRate",
                "keyEvents",
                "ecommercePurchases",
                "purchaseRevenue",
                "totalRevenue",
                "transactions",
            ]
            assert body["limit"] == "10"
            return httpx.Response(
                200,
                json={
                    "dimensionHeaders": [
                        {"name": "landingPagePlusQueryString"},
                        {"name": "sessionSourceMedium"},
                        {"name": "sessionCampaignName"},
                    ],
                    "metricHeaders": [
                        {"name": "activeUsers"},
                        {"name": "sessions"},
                        {"name": "screenPageViews"},
                        {"name": "eventCount"},
                        {"name": "engagementRate"},
                        {"name": "keyEvents"},
                        {"name": "ecommercePurchases"},
                        {"name": "purchaseRevenue"},
                        {"name": "totalRevenue"},
                        {"name": "transactions"},
                    ],
                    "rows": [
                        {
                            "dimensionValues": [
                                {"value": "/oferta/"},
                                {"value": "google / cpc"},
                                {"value": "PMax odpady"},
                            ],
                            "metricValues": [
                                {"value": "20"},
                                {"value": "30"},
                                {"value": "50"},
                                {"value": "75"},
                                {"value": "0.62"},
                                {"value": "3"},
                                {"value": "1"},
                                {"value": "125.50"},
                                {"value": "150.75"},
                                {"value": "1"},
                            ],
                        }
                    ],
                },
            )
        assert dimensions == ["itemId", "itemName"]
        assert [metric["name"] for metric in body["metrics"]] == [
            "itemsViewed",
            "itemsAddedToCart",
            "itemsCheckedOut",
            "itemsPurchased",
            "itemRevenue",
        ]
        assert body["limit"] == "50"
        return httpx.Response(
            200,
            json={
                "dimensionHeaders": [{"name": "itemId"}, {"name": "itemName"}],
                "metricHeaders": [
                    {"name": "itemsViewed"},
                    {"name": "itemsAddedToCart"},
                    {"name": "itemsCheckedOut"},
                    {"name": "itemsPurchased"},
                    {"name": "itemRevenue"},
                ],
                "rows": [
                    {
                        "dimensionValues": [
                            {"value": "pl~PL~gla_107394"},
                            {"value": "Sorbent chemiczny 10 kg"},
                        ],
                        "metricValues": [
                            {"value": "9"},
                            {"value": "4"},
                            {"value": "3"},
                            {"value": "2"},
                            {"value": "410.25"},
                        ],
                    }
                ],
            },
        )

    result = refresh_ga4_behavior_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary["row_count"] == 1
    assert result.metric_summary["active_users"] == 20
    assert result.metric_summary["sessions"] == 30
    assert result.metric_summary["screen_page_views"] == 50
    assert result.metric_summary["event_count"] == 75
    assert result.metric_summary["engagement_rate"] == 0.62
    assert result.metric_summary["key_events"] == 3
    assert result.metric_summary["ecommerce_purchases"] == 1
    assert result.metric_summary["purchase_revenue"] == 125.50
    assert result.metric_summary["total_revenue"] == 150.75
    assert result.metric_summary["transactions"] == 1
    assert result.metric_summary["ga4_item_product_row_count"] == 1
    assert result.metric_summary["ga4_items_viewed"] == 9
    assert result.metric_summary["ga4_items_added_to_cart"] == 4
    assert result.metric_summary["ga4_items_checked_out"] == 3
    assert result.metric_summary["ga4_items_purchased"] == 2
    assert result.metric_summary["ga4_item_revenue"] == 410.25
    assert result.metric_facts[0].name == "active_users"
    assert result.metric_facts[0].value == 20
    assert result.metric_facts[0].dimensions == {
        "landing_page": "/oferta/",
        "source_medium": "google / cpc",
        "campaign_name": "PMax odpady",
    }
    facts_by_name = {fact.name: fact for fact in result.metric_facts}
    assert facts_by_name["key_events"].value == 3
    assert facts_by_name["ecommerce_purchases"].value == 1
    assert facts_by_name["purchase_revenue"].value == 125.50
    assert facts_by_name["total_revenue"].value == 150.75
    assert facts_by_name["transactions"].value == 1
    assert facts_by_name["item_purchases"].value == 2
    assert facts_by_name["item_purchases"].dimensions == {
        "item_id": "pl~PL~gla_107394",
        "item_name": "Sorbent chemiczny 10 kg",
    }
    assert facts_by_name["item_revenue"].value == 410.25
    assert len(requests_seen) == 2


def test_google_first_party_vendor_reads_route_through_refresh_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "google_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:ekologus.pl")
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")
    service_account_json = tmp_path / "sa.json"
    service_account_json.write_text('{"type":"service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_search_console_site_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="GSC read completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"clicks": 12, "impressions": 120},
        ),
    )
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ga4_behavior_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="GA4 read completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"active_users": 20, "sessions": 30},
        ),
    )

    gsc_response = client.post(
        "/api/connectors/google_search_console/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )
    ga4_response = client.post(
        "/api/connectors/google_analytics_4/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert gsc_response.status_code == 200
    assert ga4_response.status_code == 200
    assert gsc_response.json()["metric_summary"] == {"clicks": 12, "impressions": 120}
    assert ga4_response.json()["metric_summary"] == {"active_users": 20, "sessions": 30}


def test_google_sheets_vendor_read_uses_spreadsheets_get(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID", "sheet-id")
    monkeypatch.setattr(
        "wilq.connectors.google_sheets.client.google_access_token",
        lambda scopes: "sheets-access-token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "sheets.googleapis.com"
        assert request.url.path == "/v4/spreadsheets/sheet-id"
        assert request.headers["authorization"] == "Bearer sheets-access-token"
        assert "sheets(properties(" in request.url.params["fields"]
        assert request.url.params["includeGridData"] == "false"
        return httpx.Response(
            200,
            json={
                "sheets": [
                    {
                        "properties": {
                            "sheetId": 1,
                            "gridProperties": {"rowCount": 100, "columnCount": 8},
                        }
                    },
                    {
                        "properties": {
                            "sheetId": 2,
                            "gridProperties": {"rowCount": 20, "columnCount": 4},
                        }
                    },
                ]
            },
        )

    result = refresh_google_sheets_review_surface(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary == {
        "api": "google_sheets_spreadsheets_get",
        "spreadsheet_configured": 1,
        "sheet_count": 2,
        "total_grid_rows": 120,
        "total_grid_columns": 12,
        "max_grid_rows": 100,
        "max_grid_columns": 8,
    }


def test_google_sheets_vendor_read_is_blocked_when_disabled_by_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "sheets_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID", "sheet-id")
    response = client.post(
        "/api/connectors/google_sheets/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "blocked"
    assert run["external_call_attempted"] is False
    assert run["vendor_data_collected"] is False
    assert run["metric_summary"] == {}
    assert "disabled by current product scope" in run["summary"]


def test_merchant_vendor_read_uses_aggregate_product_statuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "accounts/123456")
    monkeypatch.setattr(
        "wilq.connectors.google_merchant_center.client.google_access_token",
        lambda scopes: "merchant-access-token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "merchantapi.googleapis.com"
        assert request.url.path == (
            "/issueresolution/v1/accounts/123456/aggregateProductStatuses"
        )
        assert request.headers["authorization"] == "Bearer merchant-access-token"
        assert request.url.params["pageSize"] == "100"
        return httpx.Response(
            200,
            json={
                "aggregateProductStatuses": [
                    {
                        "reportingContext": "SHOPPING_ADS",
                        "country": "PL",
                        "stats": {
                            "activeCount": "8",
                            "pendingCount": "1",
                            "disapprovedCount": "2",
                            "expiringCount": "0",
                        },
                        "itemLevelIssues": [
                            {
                                "severity": "DISAPPROVED",
                                "resolution": "MERCHANT_ACTION",
                                "issueType": "missing_image",
                                "title": "Missing image",
                                "attribute": "image_link",
                                "numProducts": "2",
                                "sampleProducts": [
                                    "accounts/123456/products/online~pl~PL~SKU-001",
                                    "accounts/123456/products/online~pl~PL~SKU-002",
                                ],
                            },
                            {
                                "severity": "NOT_IMPACTED",
                                "resolution": "PENDING_PROCESSING",
                                "productCount": "1",
                                "issueType": "pending_review",
                                "title": "Pending review",
                            },
                        ],
                    },
                    {
                        "reportingContext": "FREE_LISTINGS",
                        "country": "PL",
                        "stats": {
                            "activeCount": "4",
                            "pendingCount": "0",
                            "disapprovedCount": "1",
                            "expiringCount": "1",
                        },
                        "itemLevelIssues": [
                            {
                                "severity": "DEMOTED",
                                "resolution": "MERCHANT_ACTION",
                                "issueType": "limited_performance",
                                "productCount": "1",
                            }
                        ],
                    },
                ],
                "nextPageToken": "next-page",
            },
        )

    result = refresh_merchant_product_status_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary == {
        "api": "merchant_aggregate_product_statuses",
        "status_group_count": 2,
        "country_count": 1,
        "reporting_context_count": 2,
        "active_products": 12,
        "pending_products": 1,
        "disapproved_products": 3,
        "expiring_products": 1,
        "total_products": 17,
        "item_level_issue_count": 3,
        "merchant_action_issue_count": 2,
        "merchant_action_product_count": 3,
        "disapproved_issue_count": 1,
        "demoted_issue_count": 1,
        "warning_issue_count": 1,
        "next_page_present": 1,
    }
    assert result.metric_facts[0].name == "active_products"
    assert result.metric_facts[0].value == 8
    assert result.metric_facts[0].dimensions == {
        "country": "PL",
        "reporting_context": "SHOPPING_ADS",
    }
    issue_fact = next(fact for fact in result.metric_facts if fact.name == "issue_product_count")
    assert issue_fact.value == 2
    assert issue_fact.dimensions == {
        "country": "PL",
        "reporting_context": "SHOPPING_ADS",
        "severity": "DISAPPROVED",
        "resolution": "MERCHANT_ACTION",
        "issue_type": "missing_image",
        "issue_title": "Missing image",
        "affected_attribute": "image_link",
    }
    sample_facts = [fact for fact in result.metric_facts if fact.name == "sample_product_id"]
    assert [fact.value for fact in sample_facts] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert sample_facts[0].dimensions == {
        "country": "PL",
        "reporting_context": "SHOPPING_ADS",
        "severity": "DISAPPROVED",
        "resolution": "MERCHANT_ACTION",
        "issue_type": "missing_image",
        "issue_title": "Missing image",
        "affected_attribute": "image_link",
        "sample_index": "1",
    }


def test_merchant_vendor_read_uses_products_list_for_issue_samples(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "accounts/123456")
    monkeypatch.setattr(
        "wilq.connectors.google_merchant_center.client.google_access_token",
        lambda scopes: "merchant-access-token",
    )

    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/issueresolution/v1/accounts/123456/aggregateProductStatuses":
            return httpx.Response(
                200,
                json={
                    "aggregateProductStatuses": [
                        {
                            "reportingContext": "SHOPPING_ADS",
                            "country": "PL",
                            "statistics": {"approvedCount": "8"},
                            "issues": [
                                {
                                    "severity": "DISAPPROVED",
                                    "resolution": "MERCHANT_ACTION",
                                    "issueType": "landing_page_error",
                                    "attribute": "link",
                                    "numProducts": "2",
                                }
                            ],
                        }
                    ]
                },
            )
        if request.url.path == "/products/v1/accounts/123456/products":
            assert request.url.params["pageSize"] == "1000"
            return httpx.Response(
                200,
                json={
                    "products": [
                        {
                            "name": "accounts/123456/products/online~pl~PL~SKU-LINK-001",
                            "offerId": "SKU-LINK-001",
                            "productAttributes": {"title": "Sorbent chemiczny 10 kg"},
                            "productStatus": {
                                "itemLevelIssues": [
                                    {
                                        "code": "landing_page_error",
                                        "severity": "DISAPPROVED",
                                        "resolution": "MERCHANT_ACTION",
                                        "attribute": "link",
                                        "reportingContext": "SHOPPING_ADS",
                                        "applicableCountries": ["PL"],
                                    }
                                ]
                            },
                        }
                    ]
                },
            )
        raise AssertionError(f"Unexpected Merchant path: {request.url.path}")

    result = refresh_merchant_product_status_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert requested_paths == [
        "/issueresolution/v1/accounts/123456/aggregateProductStatuses",
        "/products/v1/accounts/123456/products",
    ]
    sample_id = next(fact for fact in result.metric_facts if fact.name == "sample_product_id")
    assert sample_id.value == "online~pl~PL~SKU-LINK-001"
    assert sample_id.dimensions == {
        "country": "PL",
        "reporting_context": "SHOPPING_ADS",
        "severity": "DISAPPROVED",
        "resolution": "MERCHANT_ACTION",
        "issue_type": "landing_page_error",
        "affected_attribute": "link",
        "sample_index": "1",
        "sample_source": "products.list",
    }
    sample_title = next(
        fact for fact in result.metric_facts if fact.name == "sample_product_title"
    )
    assert sample_title.value == "Sorbent chemiczny 10 kg"
    assert sample_title.dimensions == sample_id.dimensions


def test_merchant_vendor_read_routes_through_refresh_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "123456")
    service_account_json = tmp_path / "sa.json"
    service_account_json.write_text('{"type":"service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_merchant_product_status_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Merchant aggregate statuses completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"active_products": 12, "disapproved_products": 3},
        ),
    )

    response = client.post(
        "/api/connectors/google_merchant_center/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["metric_summary"] == {"active_products": 12, "disapproved_products": 3}


def test_ahrefs_vendor_read_uses_site_explorer_domain_rating(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    monkeypatch.setenv("AHREFS_TARGET", "https://www.ekologus.pl/oferta")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.host == "api.ahrefs.com"
        assert request.headers["authorization"] == "Bearer ahrefs-token-test"
        assert request.headers["accept"] == "application/json"
        assert request.url.params["output"] == "json"
        if request.url.path == "/v3/site-explorer/domain-rating":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["target"] == "ekologus.pl"
            return httpx.Response(
                200,
                json={"domain_rating": {"ahrefs_rank": 1450, "domain_rating": 90.0}},
            )
        if request.url.path == "/v3/site-explorer/organic-competitors":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["target"] == "ekologus.pl"
            assert request.url.params["mode"] == "subdomains"
            assert request.url.params["country"] == "pl"
            assert request.url.params["limit"] == "10"
            assert "competitor_domain" in request.url.params["select"]
            return httpx.Response(
                200,
                json={
                    "competitors": [
                        {
                            "competitor_domain": None,
                            "competitor_url": "https://konkurent.pl/bdo/",
                            "keywords_common": 8,
                            "keywords_competitor": 42,
                            "keywords_target": 12,
                            "pages": 7,
                            "share": 0.17,
                        }
                    ]
                },
            )
        if request.url.path == "/v3/site-explorer/top-pages":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["target"] == "konkurent.pl"
            assert request.url.params["mode"] == "subdomains"
            assert request.url.params["country"] == "pl"
            assert request.url.params["limit"] == "3"
            assert request.url.params["order_by"] == "sum_traffic:desc"
            assert "top_keyword" in request.url.params["select"]
            return httpx.Response(
                200,
                json={
                    "pages": [
                        {
                            "raw_url": "https://konkurent.pl/top-bdo/",
                            "top_keyword": "bdo szkolenie",
                            "sum_traffic": 121,
                            "keywords": 31,
                            "referring_domains": 4,
                            "top_keyword_best_position": 2,
                            "top_keyword_country": "pl",
                        }
                    ]
                },
            )
        if request.url.path == "/v3/site-explorer/organic-keywords":
            assert len(request.url.params["date"]) == 10
            assert request.url.params["country"] == "pl"
            assert request.url.params["order_by"] == "sum_traffic:desc"
            assert "keyword" in request.url.params["select"]
            if request.url.params["target"] == "https://konkurent.pl/top-bdo/":
                assert request.url.params["mode"] == "exact"
                assert request.url.params["limit"] == "3"
                return httpx.Response(
                    200,
                    json={
                        "keywords": [
                            {
                                "keyword": "bdo szkolenie online",
                                "best_position": 3,
                                "best_position_url": "https://konkurent.pl/top-bdo/",
                                "volume": 150,
                                "sum_traffic": 24,
                                "keyword_difficulty": 8,
                                "cpc": 1.21,
                                "is_branded": False,
                                "is_commercial": True,
                                "is_informational": False,
                                "is_local": False,
                                "is_transactional": True,
                            }
                        ]
                    },
                )
            assert request.url.params["target"] == "ekologus.pl"
            assert request.url.params["mode"] == "subdomains"
            assert request.url.params["limit"] == "1000"
            return httpx.Response(
                200,
                json={
                    "keywords": [
                        {"keyword": "ekologus"},
                        {"keyword": "audyt środowiskowy"},
                    ]
                },
            )
        assert request.url.path == "/v3/site-explorer/refdomains"
        assert request.url.params["mode"] == "subdomains"
        assert request.url.params["history"] == "live"
        assert request.url.params["order_by"] == "domain_rating:desc"
        assert "domain" in request.url.params["select"]
        if request.url.params["target"] == "ekologus.pl":
            assert request.url.params["limit"] == "1000"
            return httpx.Response(
                200,
                json={"refdomains": [{"domain": "shared-source.pl", "domain_rating": 44}]},
            )
        assert request.url.params["target"] == "konkurent.pl"
        assert request.url.params["limit"] == "10"
        return httpx.Response(
            200,
            json={
                "refdomains": [
                    {"domain": "shared-source.pl", "domain_rating": 44},
                    {
                        "domain": "gap-source.pl",
                        "domain_rating": 66,
                        "links_to_target": 3,
                        "dofollow_links": 2,
                        "dofollow_refdomains": 1,
                        "traffic_domain": 1200,
                        "positions_source_domain": 82,
                        "first_seen": "2025-01-02",
                        "last_seen": "2026-06-19",
                        "is_spam": False,
                        "is_root_domain": True,
                    },
                ]
            },
        )

    result = refresh_ahrefs_domain_rating(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary == {
        "api": "ahrefs_site_explorer_domain_rating",
        "date": result.metric_summary["date"],
        "target_source": "process_env",
        "domain_rating": 90.0,
        "ahrefs_rank": 1450,
        "organic_competitor_read_status": "completed",
        "organic_competitor_rows": 1,
        "organic_competitor_country": "pl",
        "organic_competitor_mode": "subdomains",
        "top_pages_by_competitor_read_status": "completed",
        "top_pages_by_competitor_rows": 1,
        "top_pages_by_competitor_competitors": 1,
        "top_pages_by_competitor_country": "pl",
        "top_pages_by_competitor_mode": "subdomains",
        "organic_keywords_by_url_read_status": "completed",
        "organic_keywords_by_url_rows": 1,
        "organic_keywords_by_url_urls": 1,
        "organic_keywords_by_url_country": "pl",
        "organic_keywords_by_url_mode": "exact",
        "organic_keywords_by_url_keyword_limit": 3,
        "content_gap_read_status": "completed",
        "content_gap_rows": 1,
        "content_gap_target_keywords": 2,
        "content_gap_target_keyword_limit": 1000,
        "content_gap_competitor_keywords": 1,
        "content_gap_mode": "subdomains",
        "backlink_gap_read_status": "completed",
        "backlink_gap_rows": 1,
        "backlink_gap_competitors": 1,
        "backlink_gap_target_refdomains": 1,
        "backlink_gap_target_refdomain_limit": 1000,
        "backlink_gap_competitor_refdomain_limit": 10,
        "backlink_gap_mode": "subdomains",
        "backlink_gap_history": "live",
    }
    assert result.metric_facts == [
        VendorMetricFact(
            "ahrefs_competitor_page_count",
            7,
            {
                "gap_type": "competitor_page",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/bdo/",
                "country": "pl",
                "target_mode": "subdomains",
                "keywords_common": "8",
                "keywords_competitor": "42",
                "keywords_target": "12",
                "share": "0.17",
            },
            period="ahrefs_organic_competitors",
        ),
        VendorMetricFact(
            "ahrefs_top_page_gap_count",
            1,
            {
                "gap_type": "top_page_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/top-bdo/",
                "keyword": "bdo szkolenie",
                "country": "pl",
                "target_mode": "subdomains",
                "sum_traffic": "121",
                "keywords": "31",
                "referring_domains": "4",
                "top_keyword_best_position": "2",
                "top_keyword_country": "pl",
            },
            period="ahrefs_top_pages",
        ),
        VendorMetricFact(
            "ahrefs_organic_keyword_gap_count",
            1,
            {
                "gap_type": "organic_keyword_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/top-bdo/",
                "keyword": "bdo szkolenie online",
                "country": "pl",
                "target_mode": "exact",
                "best_position": "3",
                "best_position_url": "https://konkurent.pl/top-bdo/",
                "volume": "150",
                "sum_traffic": "24",
                "keyword_difficulty": "8",
                "cpc": "1.21",
                "is_branded": "False",
                "is_commercial": "True",
                "is_informational": "False",
                "is_local": "False",
                "is_transactional": "True",
            },
            period="ahrefs_organic_keywords",
        ),
        VendorMetricFact(
            "ahrefs_content_gap_count",
            1,
            {
                "gap_type": "content_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "https://konkurent.pl/top-bdo/",
                "target_domain": "ekologus.pl",
                "keyword": "bdo szkolenie online",
                "country": "pl",
                "target_mode": "subdomains",
                "competitor_target_mode": "exact",
                "best_position": "3",
                "best_position_url": "https://konkurent.pl/top-bdo/",
                "volume": "150",
                "sum_traffic": "24",
                "keyword_difficulty": "8",
                "cpc": "1.21",
                "is_branded": "False",
                "is_commercial": "True",
                "is_informational": "False",
                "is_local": "False",
                "is_transactional": "True",
                "target_keyword_sample_size": "2",
                "target_keyword_limit": "1000",
            },
            period="ahrefs_content_gap",
        ),
        VendorMetricFact(
            "ahrefs_referring_domain_gap_count",
            1,
            {
                "gap_type": "backlink_gap",
                "competitor_domain": "konkurent.pl",
                "source_url": "gap-source.pl",
                "referring_domain": "gap-source.pl",
                "target_domain": "ekologus.pl",
                "target_mode": "subdomains",
                "history": "live",
                "domain_rating": "66",
                "links_to_target": "3",
                "dofollow_links": "2",
                "dofollow_refdomains": "1",
                "traffic_domain": "1200",
                "positions_source_domain": "82",
                "first_seen": "2025-01-02",
                "last_seen": "2026-06-19",
                "is_spam": "False",
                "is_root_domain": "True",
                "target_refdomain_sample_size": "1",
                "target_refdomain_limit": "1000",
            },
            period="ahrefs_refdomains_gap",
        ),
    ]
    assert [request.url.path for request in requests] == [
        "/v3/site-explorer/domain-rating",
        "/v3/site-explorer/organic-competitors",
        "/v3/site-explorer/top-pages",
        "/v3/site-explorer/organic-keywords",
        "/v3/site-explorer/organic-keywords",
        "/v3/site-explorer/refdomains",
        "/v3/site-explorer/refdomains",
    ]
    serialized = json.dumps(result.metric_summary)
    assert "ahrefs-token-test" not in serialized
    assert "ekologus.pl" not in serialized


def test_ahrefs_vendor_read_prefers_marketing_site_over_wordpress_runtime_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    monkeypatch.setenv("MIS_PRIMARY_SITE_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl")
    requested_targets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_targets.append(request.url.params["target"])
        if request.url.path == "/v3/site-explorer/domain-rating":
            return httpx.Response(
                200,
                json={"domain_rating": {"ahrefs_rank": 1450, "domain_rating": 90.0}},
            )
        return httpx.Response(200, json={"competitors": []})

    result = refresh_ahrefs_domain_rating(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert requested_targets == ["ekologus.pl", "ekologus.pl"]
    assert result.metric_summary["target_source"] == "process_env"


def test_ahrefs_vendor_read_routes_through_refresh_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ahrefs_domain_rating",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Ahrefs domain rating completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"domain_rating": 90.0, "ahrefs_rank": 1450},
        ),
    )

    response = client.post(
        "/api/connectors/ahrefs/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["metric_summary"] == {"domain_rating": 90.0, "ahrefs_rank": 1450}


def test_localo_vendor_read_routes_through_mcp_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_localo_visibility_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="Localo MCP endpoint reachable; OAuth authorization required.",
            external_call_attempted=True,
            vendor_data_collected=False,
            metric_summary={
                "api": "localo_mcp_oauth_probe",
                "mcp_initialize_status": 401,
                "authorization_code_supported": 1,
                "pkce_s256_supported": 1,
                "access_token_present": 1,
            },
            errors=["Localo OAuth authorization is incomplete."],
        ),
    )

    response = client.post(
        "/api/connectors/localo/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "blocked"
    assert run["external_call_attempted"] is True
    assert run["vendor_data_collected"] is False
    assert run["metric_summary"]["api"] == "localo_mcp_oauth_probe"
    assert run["metric_summary"]["access_token_present"] == 1


def test_localo_vendor_read_collects_read_only_aggregate_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://api.localo.com/.well-known/oauth-protected-resource":
            return httpx.Response(
                200,
                json={"authorization_servers": ["https://api.localo.com"]},
            )
        if str(request.url) == "https://api.localo.com/.well-known/oauth-authorization-server":
            return httpx.Response(
                200,
                json={
                    "grant_types_supported": ["authorization_code"],
                    "code_challenge_methods_supported": ["S256"],
                },
            )
        assert str(request.url) == "https://api.localo.com/api/mcp"
        assert request.headers["authorization"] == "Bearer localo-access-test"
        payload = json.loads(request.content.decode())
        method = payload["method"]
        if method == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": {}})
        if method == "notifications/initialized":
            return httpx.Response(204)
        assert method == "tools/call"
        arguments = payload["params"]["arguments"]
        query = arguments["query"]
        variables = arguments["variables"]
        if "placesList" in query:
            assert variables == {"input": {"active": True, "pageNo": 1, "pageSize": 20}}
            return _localo_mcp_text_response(
                {
                    "data": {
                        "placesList": {
                            "places": [{"id": "place-one"}, {"id": "place-two"}],
                            "placesTags": [],
                        }
                    }
                }
            )
        if "activePlaceKeywords" in query:
            if variables["placeId"] == "place-one":
                return _localo_mcp_text_response(
                    {
                        "data": {
                            "place": {
                                "latestPlaceSnapshot": {"rating": 4.5, "reviewsCount": 10},
                                "activePlaceKeywords": [
                                    {
                                        "visibility": {"current": 50, "change": 2},
                                        "ahrefsOverview": {"volume": 100},
                                        "latestGrids": [{"orderedPlacePosition": 3}],
                                    },
                                    {
                                        "visibility": {"current": 70, "change": -1},
                                        "ahrefsOverview": {"volume": 200},
                                        "latestGrids": [{"orderedPlacePosition": 5}],
                                    },
                                ],
                            }
                        }
                    }
                )
            return _localo_mcp_text_response(
                {
                    "data": {
                        "place": {
                            "latestPlaceSnapshot": {"rating": 4.0, "reviewsCount": 20},
                            "activePlaceKeywords": [
                                {
                                    "visibility": {"current": 30, "change": 0},
                                    "ahrefsOverview": {"volume": 50},
                                    "latestGrids": [],
                                }
                            ],
                        }
                    }
                }
            )
        if "reviewsStats" in query:
            if variables["placeId"] == "place-one":
                return _localo_mcp_text_response(
                    {
                        "data": {
                            "reviewsStats": {
                                "reviewsCount": 10,
                                "repliedCount": 8,
                                "removedCount": 1,
                            }
                        }
                    }
                )
            return _localo_mcp_text_response(
                {
                    "data": {
                        "reviewsStats": {
                            "reviewsCount": 20,
                            "repliedCount": 10,
                            "removedCount": 2,
                        }
                    }
                    }
                )
        if "googleMetricSeries" in query:
            metric = variables["args"]["metrics"][0]
            assert variables["args"]["placeId"] in {"place-one", "place-two"}
            assert variables["args"]["dateStart"]
            assert variables["args"]["dateEnd"]
            if metric in {
                "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
                "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
                "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
                "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
            }:
                return _localo_mcp_text_response(
                    {"data": {"googleMetricSeries": [{"value": 10}, {"value": 5}]}}
                )
            return _localo_mcp_text_response(
                {"data": {"googleMetricSeries": [{"value": 2}, {"value": 1}]}}
            )
        if "listPlaceActionTrackerFavoriteCompetitors" in query:
            if variables["placeId"] == "place-one":
                return _localo_mcp_text_response(
                    {
                        "data": {
                            "competitors": [
                                {"favorite": True, "changesCount": 3},
                                {"favorite": False, "changesCount": 1},
                            ]
                        }
                    }
                )
            return _localo_mcp_text_response(
                {"data": {"competitors": [{"favorite": True, "changesCount": 2}]}}
            )
        return httpx.Response(500, json={"error": "Unexpected Localo query"})

    result = refresh_localo_visibility_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read, reason="contract test"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.vendor_data_collected is True
    assert result.metric_summary["api"] == "localo_mcp_oauth_probe"
    assert result.metric_summary["localo_active_place_count"] == 2
    assert result.metric_summary["localo_tracked_keyword_count"] == 3
    assert result.metric_summary["localo_avg_visibility_current"] == 50.0
    assert result.metric_summary["localo_avg_visibility_change"] == 0.3333
    assert result.metric_summary["localo_avg_latest_grid_position"] == 4.0
    assert result.metric_summary["localo_total_keyword_volume"] == 350
    assert result.metric_summary["localo_reviews_count"] == 30
    assert result.metric_summary["localo_review_reply_rate"] == 0.6
    assert result.metric_summary["localo_gbp_impressions_total"] == 120
    assert result.metric_summary["localo_gbp_actions_total"] == 18
    assert result.metric_summary["localo_competitor_count"] == 3
    assert result.metric_summary["localo_favorite_competitor_count"] == 2
    assert result.metric_summary["localo_competitor_change_count"] == 6
    fact_by_name = {fact.name: fact for fact in result.metric_facts}
    assert fact_by_name["localo_active_place_count"].dimensions == {
        "contract": "place_inventory",
        "scope": "active_places",
    }
    assert fact_by_name["localo_avg_visibility_current"].dimensions["contract"] == (
        "local_rankings"
    )
    assert fact_by_name["localo_reviews_count"].dimensions["contract"] == "reviews"
    assert fact_by_name["localo_gbp_impressions_total"].dimensions["contract"] == (
        "gbp_visibility"
    )
    assert fact_by_name["localo_competitor_count"].dimensions["contract"] == (
        "competitor_visibility"
    )
    serialized = json.dumps(
        {
            "summary": result.metric_summary,
            "facts": [fact.__dict__ for fact in result.metric_facts],
        },
        ensure_ascii=False,
    )
    assert "place-one" not in serialized
    assert "place-two" not in serialized
    assert "localo-access-test" not in serialized
    assert "localo-token-test" not in serialized


def _localo_mcp_text_response(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload),
                    }
                ]
            },
        },
    )


def test_localo_competitor_summary_treats_graphql_errors_as_missing_optional_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["method"] == "tools/call"
        return _localo_mcp_text_response(
            {"errors": [{"message": "Competitor visibility is unavailable for this place."}]}
        )

    summary = _competitor_visibility_summary(
        httpx.Client(transport=httpx.MockTransport(handler)),
        "localo-access-test",
        "place-without-competitor-contract",
    )

    assert summary == {
        "competitor_count": 0,
        "favorite_competitor_count": 0,
        "competitor_change_count": 0,
    }


def test_wordpress_vendor_read_uses_rest_content_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://ekologus.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "ekologus.test"
        if request.url.path == "/wp-json/wp/v2/posts":
            assert request.headers["authorization"].startswith("Basic ")
            assert request.url.params["per_page"] == "100"
            assert (
                request.url.params["_fields"]
                == "id,status,modified_gmt,date_gmt,link,slug,title"
            )
            return httpx.Response(
                200,
                headers={"X-WP-Total": "12"},
                json=[
                    {
                        "id": 1,
                        "status": "publish",
                        "modified_gmt": "2026-06-15T10:00:00",
                        "link": "https://ekologus.test/blog/remediacja/",
                        "title": {"rendered": "Remediacja środowiska"},
                    }
                ],
            )
        if request.url.path == "/wp-json/wp/v2/pages":
            assert request.headers["authorization"].startswith("Basic ")
            assert request.url.params["per_page"] == "100"
            assert (
                request.url.params["_fields"]
                == "id,status,modified_gmt,date_gmt,link,slug,title"
            )
            return httpx.Response(
                200,
                headers={"X-WP-Total": "4"},
                json=[
                    {
                        "id": 2,
                        "status": "publish",
                        "modified_gmt": "2026-06-16T10:00:00",
                        "link": "https://ekologus.test/oferta/",
                        "title": {"rendered": "Oferta Ekologus"},
                    }
                ],
            )
        if request.url.path == "/wp-sitemap.xml":
            return httpx.Response(
                200,
                text=(
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    "<sitemap><loc>https://ekologus.test/page-sitemap.xml</loc>"
                    "<lastmod>2026-06-16T12:00:00+00:00</lastmod></sitemap>"
                    "</sitemapindex>"
                ),
            )
        if request.url.path == "/page-sitemap.xml":
            return httpx.Response(
                200,
                text=(
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    "<url><loc>https://ekologus.test/europejski-zielony-lad-co-to-takiego/</loc>"
                    "<lastmod>2026-06-16T12:00:00+00:00</lastmod></url>"
                    "</urlset>"
                ),
            )
        return httpx.Response(404)

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary == {
        "api": "wordpress_rest_and_sitemap_content_inventory",
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_object_count": 16,
        "posts_total": 12,
        "pages_total": 4,
        "sitemap_url_count": 1,
        "public_sitemap_url_count": 0,
        "latest_modified_gmt": "2026-06-16T10:00:00",
        "latest_post_modified_gmt": "2026-06-15T10:00:00",
        "latest_page_modified_gmt": "2026-06-16T10:00:00",
    }
    assert result.metric_facts[0].name == "content_object_count"
    assert result.metric_facts[0].value == 12
    assert result.metric_facts[0].dimensions == {
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_type": "posts",
    }
    content_url_fact = next(
        fact for fact in result.metric_facts if fact.name == "content_object_seen"
    )
    assert content_url_fact.value == 1
    assert content_url_fact.dimensions == {
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_type": "posts",
        "object_id": "1",
        "content_url": "https://ekologus.test/blog/remediacja/",
        "status": "publish",
        "modified_gmt": "2026-06-15T10:00:00",
        "title_or_h1": "Remediacja środowiska",
        "canonical_url": "",
        "inventory_source": "wordpress_rest",
    }
    sitemap_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "content_object_seen"
        and fact.dimensions.get("inventory_source") == "sitemap"
    )
    assert sitemap_fact.value == 1
    assert sitemap_fact.dimensions == {
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_type": "sitemap",
        "object_id": "",
        "content_url": "https://ekologus.test/europejski-zielony-lad-co-to-takiego/",
        "status": "indexed",
        "modified_gmt": "2026-06-16T12:00:00+00:00",
        "title_or_h1": "",
        "canonical_url": "",
        "inventory_source": "sitemap",
    }
    assert any(fact.name == "sitemap_url_count" for fact in result.metric_facts)


def test_wordpress_vendor_read_adds_public_production_sitemap_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "ekologus.dev.proudsite.pl":
            if request.url.path == "/wp-json/wp/v2/posts":
                return httpx.Response(200, headers={"X-WP-Total": "0"}, json=[])
            if request.url.path == "/wp-json/wp/v2/pages":
                return httpx.Response(200, headers={"X-WP-Total": "0"}, json=[])
            if request.url.path == "/wp-sitemap.xml":
                return httpx.Response(404)
        if request.url.host == "www.ekologus.pl":
            if request.url.path == "/wp-sitemap.xml":
                return httpx.Response(404)
            if request.url.path == "/sitemap_index.xml":
                return httpx.Response(
                    200,
                    text=(
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        "<sitemap><loc>https://www.ekologus.pl/post-sitemap.xml</loc>"
                        "<lastmod>2026-06-17T12:00:00+00:00</lastmod></sitemap>"
                        "</sitemapindex>"
                    ),
                )
            if request.url.path == "/post-sitemap.xml":
                return httpx.Response(
                    200,
                    text=(
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        "<url><loc>https://www.ekologus.pl/"
                        "bdo-co-musi-wiedziec-przedsiebiorca/</loc>"
                        "<lastmod>2026-06-17T12:00:00+00:00</lastmod></url>"
                        "</urlset>"
                    ),
                )
            if request.url.path == "/bdo-co-musi-wiedziec-przedsiebiorca/":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html; charset=utf-8"},
                    text=(
                        "<html><head>"
                        "<title>BDO - co musi wiedzieć przedsiębiorca?</title>"
                        '<link rel="canonical" href="https://www.ekologus.pl/'
                        'bdo-co-musi-wiedziec-przedsiebiorca/" />'
                        "</head><body><h1>BDO dla przedsiębiorcy</h1></body></html>"
                    ),
                )
        return httpx.Response(404)

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.metric_summary["public_sitemap_url_count"] == 1
    public_sitemap_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "content_object_seen"
        and fact.dimensions.get("inventory_source") == "public_sitemap"
    )
    assert public_sitemap_fact.dimensions["content_url"] == (
        "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    )
    assert public_sitemap_fact.dimensions["title_or_h1"] == (
        "BDO - co musi wiedzieć przedsiębiorca?"
    )
    assert public_sitemap_fact.dimensions["canonical_url"] == (
        "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    )
    assert any(fact.name == "public_sitemap_url_count" for fact in result.metric_facts)


def test_wordpress_vendor_read_routes_through_refresh_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wordpress_refresh_state.sqlite3"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_wordpress_content_inventory",
        lambda connector_id, request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="WordPress inventory completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"content_object_count": 16, "posts_total": 12, "pages_total": 4},
        ),
    )

    response = client.post(
        "/api/connectors/wordpress_ekologus/refresh",
        json={"mode": "vendor_read", "reason": "contract test"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["metric_summary"] == {
        "content_object_count": 16,
        "posts_total": 12,
        "pages_total": 4,
    }


def test_expert_rules_are_loaded_from_structured_files() -> None:
    response = client.get("/api/expert/rules")
    assert response.status_code == 200
    rules = response.json()
    rule_ids = {rule["id"] for rule in rules}
    assert "ads_search_terms_v1" in rule_ids
    search_terms_rule = next(rule for rule in rules if rule["id"] == "ads_search_terms_v1")
    assert search_terms_rule["domain"] == "ads"
    assert search_terms_rule["requires_evidence"] is True
    assert "evidence_ids" in search_terms_rule["required_inputs"]
    assert search_terms_rule["source_path"].startswith("wilq/expert/")


def test_expert_capabilities_are_available_through_api() -> None:
    response = client.get("/api/expert/capabilities")
    assert response.status_code == 200
    capabilities = response.json()
    capability_ids = {capability["id"] for capability in capabilities}
    assert "ads_daily_check" in capability_ids
    assert "ads_custom_segments" in capability_ids
    assert all(capability["requires_evidence"] for capability in capabilities)


def test_codex_context_pack_contains_no_metric_invention_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CODEX_API_KEY",
        "sk-supersecretvalue1234567890",  # pragma: allowlist secret
    )
    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "must not invent metrics" in serialized
    assert "sk-supersecretvalue1234567890" not in serialized


def test_marketing_brief_dedupes_command_center_blockers() -> None:
    blocked_decision = DailyDecision(
        id="decision_review_ga4_landing_quality",
        title="GA4: pomiar i jakość ruchu do kontroli",
        route="/ga4",
        status="blocked",
        priority=14,
        co_widzimy="GA4 ma problemy pomiaru.",
        dlaczego_to_ma_znaczenie="Brak kontraktu na zwrot z reklam i przychody.",
        bezpieczny_next_step="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        why_it_matters="Brak kontraktu na zwrot z reklam i przychody.",
        operator_action="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        source_connectors=["google_analytics_4"],
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        action_ids=["act_review_ga4_tracking_quality"],
        blocked_claims=["zwrot z reklam", "przychód"],
        risk=ActionRisk.low,
    )
    operator_brief_item = CommandCenterBriefItem(
        id="daily_ga4_landing_quality",
        title="GA4: pomiar i jakość ruchu do kontroli",
        route="/ga4",
        status="blocked",
        priority=14,
        summary="GA4 ma problemy pomiaru.",
        next_step="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        source_connectors=["google_analytics_4"],
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        action_ids=["act_review_ga4_tracking_quality"],
        blocked_claims=["zwrot z reklam", "przychód"],
        risk=ActionRisk.low,
    )
    command_center = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Otwórz /ga4.",
        blocker_count=1,
        daily_decisions=[blocked_decision],
        operator_brief=[operator_brief_item],
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )

    brief = build_marketing_brief(
        connectors=[],
        refresh_runs=[],
        actions=[],
        command_center=command_center,
    )

    blockers = next(section for section in brief.sections if section.id == "what_blocks_us").items
    assert len(blockers) == 1
    assert blockers[0].title == "GA4: pomiar i jakość ruchu do kontroli"


def test_marketing_brief_daily_context_limits_safe_actions_to_daily_decisions() -> None:
    daily_decision = DailyDecision(
        id="decision_review_ga4_landing_quality",
        title="GA4: pomiar i jakość ruchu do kontroli",
        route="/ga4",
        status="blocked",
        priority=14,
        co_widzimy="GA4 ma problemy pomiaru.",
        dlaczego_to_ma_znaczenie="Brak kontraktu na zwrot z reklam i przychody.",
        bezpieczny_next_step="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        why_it_matters="Brak kontraktu na zwrot z reklam i przychody.",
        operator_action="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        source_connectors=["google_analytics_4"],
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        action_ids=["act_review_ga4_tracking_quality"],
        blocked_claims=["zwrot z reklam", "przychód"],
        risk=ActionRisk.low,
    )
    command_center = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Otwórz /ga4.",
        blocker_count=1,
        daily_decisions=[daily_decision],
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    daily_action = ActionObject(
        id="act_review_ga4_tracking_quality",
        title="Sprawdź jakość pomiaru GA4 przed oceną kampanii",
        domain=OpportunityDomain.ga4,
        connector="google_analytics_4",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        human_diagnosis="GA4 wymaga sprawdzenia.",
        recommended_reason="Sprawdź pomiar GA4.",
        payload={"action_type": "ga4_review"},
        validation_status="not_validated",
        created_by="test",
    )
    noisy_action = ActionObject(
        id="act_review_demand_gen_readiness",
        title="Przygotuj sprawdzenie gotowości Demand Gen",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_refresh_refresh_google_ads_test"],
        human_diagnosis="Demand Gen nie należy do daily decision.",
        recommended_reason="Nie promuj w daily brief.",
        payload={"action_type": "demand_gen_review"},
        validation_status="not_validated",
        created_by="test",
    )

    brief = build_marketing_brief(
        connectors=[],
        refresh_runs=[],
        actions=[daily_action, noisy_action],
        command_center=command_center,
    )

    action_items = next(
        section for section in brief.sections if section.id == "safe_next_actions"
    ).items
    action_ids = [item.action_ids[0] for item in action_items]
    assert action_ids == ["act_review_ga4_tracking_quality"]


def test_marketing_brief_localo_metric_headline_is_marketer_friendly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class LocaloMetricStore:
        def list_metric_facts_by_connector(
            self,
            connector_ids: list[str],
            limit_per_connector: int,
        ) -> dict[str, list[MetricFact]]:
            assert connector_ids == ["localo"]
            assert limit_per_connector > 0
            return {
                "localo": [
                    MetricFact(
                        name="localo_tracked_keyword_count",
                        value=23,
                        period="connector_refresh",
                        source_connector="localo",
                        evidence_id="ev_refresh_refresh_localo_test",
                    ),
                    MetricFact(
                        name="localo_avg_visibility_current",
                        value=53.1739,
                        period="connector_refresh",
                        source_connector="localo",
                        evidence_id="ev_refresh_refresh_localo_test",
                    ),
                    MetricFact(
                        name="localo_reviews_count",
                        value=798,
                        period="connector_refresh",
                        source_connector="localo",
                        evidence_id="ev_refresh_refresh_localo_test",
                    ),
                    MetricFact(
                        name="localo_total_keyword_volume",
                        value=69420,
                        period="connector_refresh",
                        source_connector="localo",
                        evidence_id="ev_refresh_refresh_localo_test",
                    ),
                ]
            }

    monkeypatch.setattr("wilq.briefing.marketing_brief.metric_store", LocaloMetricStore)
    connectors = [
        ConnectorStatus(
            id="localo",
            label="Localo",
            status=ConnectorStatusValue.configured,
            configured=True,
            missing_credentials=[],
            freshness=FreshnessState(state="fresh"),
            capabilities=ConnectorCapability(read=True),
            health_check="configured",
        )
    ]

    brief = build_marketing_brief(
        connectors=connectors,
        refresh_runs=[],
        actions=[],
    )

    what_we_know = next(section for section in brief.sections if section.id == "what_we_know")
    localo_item = next(item for item in what_we_know.items if item.source_connectors == ["localo"])
    assert localo_item.title == "Localo: widoczność lokalna i opinie do sprawdzenia"
    assert "localo_total_keyword_volume =" not in localo_item.title
    assert "23" in localo_item.summary
    assert "798" in localo_item.summary


def test_codex_context_pack_embeds_marketing_brief_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "context_pack.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "context_pack.duckdb"))
    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    brief = brief_response.json()

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_brief = context_payload["marketing_brief"]

    assert context_payload["context_scope"]["mode"] == "daily"
    assert context_payload["context_scope"]["skill"] == "wilq-daily-command"
    assert context_payload["context_scope"]["full_context_available"] is True
    assert context_payload["context_pack_compaction"]["mode"] == "daily_default"
    assert context_payload["context_pack_compaction"]["full_context_available"] is True
    assert context_payload["context_pack_compaction"]["command_center_daily_decisions_only"] is True
    assert context_payload["context_pack_compaction"]["expert_capabilities_compacted"] is True
    assert context_payload["context_pack_compaction"]["action_review_gates_compacted"] is True
    assert (
        context_payload["context_pack_compaction"]["full_marketing_brief_endpoint"]
        == "/api/marketing/brief"
    )
    assert context_payload["context_pack_compaction"]["evidence_summaries_limit"] == 32
    assert "command_center" in context_payload
    assert "tactical_queue" not in context_payload
    assert "ads_diagnostics" not in context_payload
    assert "merchant_diagnostics" not in context_payload
    assert len(context_payload["evidence_summaries"]) <= 32
    assert context_brief["language"] == "pl-PL"
    assert context_brief["language"] == brief["language"]
    assert context_brief["blocker_count"] == brief["blocker_count"]
    assert context_brief["recommendation_count"] == brief["recommendation_count"]
    assert context_brief["evidence_ids"] == brief["evidence_ids"]
    assert context_brief["action_ids"] == brief["action_ids"]
    assert [section["id"] for section in context_brief["sections"]] == [
        section["id"] for section in brief["sections"]
    ]
    assert len(context_brief["top_metric_facts"]) <= 8
    assert "connector_health" not in context_payload["command_center"]
    assert context_payload["command_center"]["daily_decisions"]
    assert "operator_brief" not in context_payload["command_center"]
    assert "action_plan" not in context_payload["command_center"]
    assert "demo_script" not in context_payload["command_center"]
    for action in context_payload["active_action_objects"]:
        assert "metrics" not in action
        assert "payload" not in action
        assert action["api_endpoint_template"] == "/api/actions/{action_id}"
    for section in context_brief["sections"]:
        for item in section["items"]:
            assert item["metric_fact_count"] >= len(item["metric_facts"])
            assert len(item["metric_facts"]) <= 3
    serialized_operator_context = json.dumps(
        {
            "connector_status": context_payload["connector_status"],
            "connector_refresh_runs": context_payload["connector_refresh_runs"],
            "active_action_objects": context_payload["active_action_objects"],
            "expert_rule_summaries": context_payload["expert_rule_summaries"],
        },
        ensure_ascii=False,
    )
    for forbidden_term in (
        "target_site",
        "mapping_review",
        "vendor_read",
        "Read-only",
        "read-only",
        "review-only",
        "ActionObject",
    ):
        assert forbidden_term not in serialized_operator_context


def test_daily_context_pack_uses_daily_decisions_for_action_summaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})

    assert response.status_code == 200
    payload = response.json()
    assert len(json.dumps(payload, ensure_ascii=False).encode()) < 180_000
    actions_by_id = {action["id"]: action for action in payload["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    ga4_action = actions_by_id["act_review_ga4_tracking_quality"]
    assert merchant_action["decision_id"]
    assert merchant_action["decision_id"] != "[REDACTED]"
    assert merchant_action["decision_id"].startswith("decision_")
    assert merchant_action["metric_tiles"]
    assert ga4_action["decision_id"]
    assert ga4_action["decision_id"] != "[REDACTED]"
    assert ga4_action["decision_id"].startswith("decision_")
    assert ga4_action["metric_tiles"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "active_products=12" not in serialized
    assert "disapproved_products=3" not in serialized
    assert "active_users=20" not in serialized
    assert "sessions=30" not in serialized


def test_list_evidence_by_ids_returns_metric_fact_evidence_without_full_scan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "targeted_evidence.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "targeted_evidence.duckdb"))
    run = ConnectorRefreshRun(
        id="refresh_targeted_metric_evidence",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=[refresh_run_evidence_id("refresh_targeted_metric_evidence")],
        summary="Targeted metric evidence test run.",
    )
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                "clicks",
                12,
                {
                    "query": "bdo co to",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            )
        ],
    )

    evidence = list_evidence_by_ids(
        [
            refresh_run_evidence_id("refresh_targeted_metric_evidence"),
            "ev_missing_not_returned",
        ]
    )

    assert [item.id for item in evidence] == [
        refresh_run_evidence_id("refresh_targeted_metric_evidence")
    ]
    assert evidence[0].source_connector == "google_search_console"
    assert evidence[0].source_type == "metric_fact_store"
    assert "clicks" in evidence[0].summary


def test_daily_runtime_reuses_preloaded_daily_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    connector = ConnectorStatus(
        id="google_merchant_center",
        label="Merchant Center",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="fresh"),
        capabilities=ConnectorCapability(read=True),
        health_check="configured",
    )
    action = ActionObject(
        id="act_review_merchant_feed_issues",
        title="Przejrzyj problemy feedu",
        domain=OpportunityDomain.merchant,
        connector="google_merchant_center",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_merchant"],
        human_diagnosis="Merchant wymaga sprawdzenia.",
        recommended_reason="Przygotuj sprawdzenie.",
        payload={},
        validation_status="not_validated",
        created_by="wilq",
    )
    refresh_run = ConnectorRefreshRun(
        id="refresh_merchant",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_merchant"],
        summary="Merchant read.",
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        items=[],
    )
    metric_fact = MetricFact(
        name="issue_product_count",
        value=3,
        period="connector_refresh",
        source_connector="google_merchant_center",
        evidence_id="ev_merchant",
    )
    facts_by_connector = {"google_merchant_center": [metric_fact]}

    class FakeMetricStore:
        def list_latest_metric_facts_by_connector_limits(
            self,
            limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["metric_fact_limits"] = limits
            return facts_by_connector

    monkeypatch.setattr(daily_runtime, "metric_store", lambda: FakeMetricStore())
    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj Merchant.",
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[connector],
        codex_operator_status={},
    )
    brief = MarketingBrief(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections=[],
    )
    seen: dict[str, object] = {}

    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [connector])
    monkeypatch.setattr(daily_runtime, "list_actions", lambda: [action])
    monkeypatch.setattr(daily_runtime, "list_connector_refresh_runs", lambda: [refresh_run])
    monkeypatch.setattr(
        daily_runtime,
        "build_tactical_queue",
        lambda facts_by_connector=None: tactical_queue,
    )

    def command_builder(
        connectors: list[ConnectorStatus] | None = None,
        tactical_queue: TacticalQueueResponse | None = None,
        actions: list[ActionObject] | None = None,
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
        refresh_runs: list[ConnectorRefreshRun] | None = None,
    ) -> CommandCenterResponse:
        seen["command_connectors"] = connectors
        seen["command_tactical_queue"] = tactical_queue
        seen["command_actions"] = actions
        seen["command_facts_by_connector"] = facts_by_connector
        seen["command_refresh_runs"] = refresh_runs
        return command

    def brief_builder(
        connectors: list[ConnectorStatus] | None = None,
        refresh_runs: list[ConnectorRefreshRun] | None = None,
        actions: list[ActionObject] | None = None,
        command_center: CommandCenterResponse | None = None,
        metric_facts_by_connector: dict[str, list[MetricFact]] | None = None,
    ) -> MarketingBrief:
        seen["brief_connectors"] = connectors
        seen["brief_refresh_runs"] = refresh_runs
        seen["brief_actions"] = actions
        seen["brief_command_center"] = command_center
        seen["brief_metric_facts_by_connector"] = metric_facts_by_connector
        return brief

    monkeypatch.setattr(daily_runtime, "build_command_center_response", command_builder)
    monkeypatch.setattr(daily_runtime, "build_marketing_brief", brief_builder)

    runtime = daily_runtime.build_daily_runtime()

    assert runtime.connectors == [connector]
    assert runtime.actions == [action]
    assert runtime.refresh_runs == [refresh_run]
    assert runtime.core_actions == [action]
    assert runtime.command_center == command
    assert runtime.marketing_brief == brief
    assert seen["command_connectors"] == [connector]
    assert seen["command_tactical_queue"] == tactical_queue
    assert seen["command_actions"] == [action]
    assert seen["command_facts_by_connector"] == facts_by_connector
    assert seen["command_refresh_runs"] == [refresh_run]
    assert seen["brief_connectors"] == [connector]
    assert seen["brief_refresh_runs"] == [refresh_run]
    assert seen["brief_actions"] == [action]
    assert seen["brief_command_center"] == command
    assert seen["brief_metric_facts_by_connector"] == facts_by_connector


def test_daily_command_center_does_not_build_marketing_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj Command Center.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    base = daily_runtime.DailyRuntimeBase(
        connectors=[],
        actions=[],
        refresh_runs=[],
        tactical_queue=TacticalQueueResponse(
            strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
            items=[],
        ),
    )

    monkeypatch.setattr(daily_runtime, "build_daily_runtime_base", lambda use_cache=True: base)
    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        lambda connectors=None,
        tactical_queue=None,
        actions=None,
        facts_by_connector=None,
        refresh_runs=None: command,
    )

    def fail_marketing_brief(*args: object, **kwargs: object) -> MarketingBrief:
        raise AssertionError("Command Center endpoint must not build Marketing Brief")

    monkeypatch.setattr(daily_runtime, "build_marketing_brief", fail_marketing_brief)

    assert daily_runtime.build_daily_command_center(use_cache=False) == command


def test_command_center_uses_preloaded_refresh_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import command_center

    connector = ConnectorStatus(
        id="google_ads",
        label="Google Ads",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="fresh"),
        capabilities=ConnectorCapability(read=True),
        health_check="configured",
    )
    refresh_run = ConnectorRefreshRun(
        id="refresh_google_ads_live",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_ads_live"],
        vendor_data_collected=True,
        metric_summary={"row_count": 1},
        summary="Google Ads live read.",
    )
    metric_fact = MetricFact(
        name="clicks",
        value=4,
        period="connector_refresh",
        source_connector="google_ads",
        evidence_id="ev_refresh_google_ads_live",
    )

    class FailingLocalState:
        def list_connector_refresh_runs(self, connector_id: str | None = None) -> list[object]:
            raise AssertionError("Command Center must use preloaded refresh runs")

    monkeypatch.setattr(command_center, "local_state_store", lambda: FailingLocalState())

    response = command_center.build_command_center_response(
        connectors=[connector],
        tactical_queue=TacticalQueueResponse(
            strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
            items=[],
        ),
        actions=[],
        facts_by_connector={"google_ads": [metric_fact]},
        refresh_runs=[refresh_run],
    )

    ads_item = next(item for item in response.operator_brief if item.id == "daily_ads_status")
    assert ads_item.status == "ready"
    assert "ev_refresh_google_ads_live" in ads_item.evidence_ids


def test_command_center_brief_uses_lightweight_daily_item_builders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import command_center
    from wilq.briefing import tactical_queue as tactical_queue_module

    action = ActionObject(
        id="act_prepare_ads_campaign_review_queue",
        title="Przygotuj kolejkę przeglądu kampanii Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_ads"],
        human_diagnosis="Ads wymaga sprawdzenia.",
        recommended_reason="Przygotuj sprawdzenie.",
        payload={},
        validation_status="not_validated",
        created_by="wilq",
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        items=[],
    )
    seen: dict[str, object] = {}

    def ads_item_builder(
        facts: list[object],
        actions: list[ActionObject],
        **_kwargs: object,
    ) -> CommandCenterBriefItem:
        seen["ads_metric_facts"] = facts
        seen["actions"] = actions
        return CommandCenterBriefItem(
            id="daily_ads_status",
            title="Ads: aktualne metryki kampanii dostępne",
            route="/ads-doctor",
            status="ready",
            priority=30,
            summary="Google Ads ma aktualne metryki źródłowe.",
            next_step="Otwórz /ads-doctor.",
            source_connectors=["google_ads"],
            evidence_ids=["ev_ads"],
            action_ids=[action.id],
        )

    def merchant_item_builder(
        tactical_items: list[object],
        actions: list[ActionObject],
        metric_facts: list[object],
        **_kwargs: object,
    ) -> CommandCenterBriefItem:
        seen["merchant_tactical_items"] = tactical_items
        seen["merchant_actions"] = actions
        seen["merchant_metric_facts"] = metric_facts
        return CommandCenterBriefItem(
            id="daily_merchant_feed",
            title="Merchant",
            route="/merchant",
            status="ready",
            priority=10,
            summary="Merchant.",
            next_step="Otwórz /merchant.",
        )

    def content_item_builder(
        queue: TacticalQueueResponse,
        ahrefs_facts: list[object],
        actions: list[ActionObject],
        **_kwargs: object,
    ) -> CommandCenterBriefItem:
        seen["content_tactical_queue"] = queue
        seen["content_ahrefs_facts"] = ahrefs_facts
        seen["content_actions"] = actions
        return CommandCenterBriefItem(
            id="daily_content_queue",
            title="Content",
            route="/content-planner",
            status="ready",
            priority=12,
            summary="Content.",
            next_step="Otwórz /content-planner.",
        )

    def ga4_item_builder(
        tactical_items: list[object],
        actions: list[ActionObject],
        metric_facts: list[object],
    ) -> CommandCenterBriefItem:
        seen["ga4_tactical_items"] = tactical_items
        seen["ga4_actions"] = actions
        seen["ga4_metric_facts"] = metric_facts
        return CommandCenterBriefItem(
            id="daily_ga4_landing_quality",
            title="GA4",
            route="/ga4",
            status="blocked",
            priority=14,
            summary="GA4.",
            next_step="Otwórz /ga4.",
        )

    monkeypatch.setattr(command_center, "_ads_item_from_facts", ads_item_builder)
    monkeypatch.setattr(
        command_center,
        "_ads_business_context_item_from_facts",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(command_center, "_merchant_item_from_tactical", merchant_item_builder)
    monkeypatch.setattr(command_center, "_content_item_from_tactical", content_item_builder)
    monkeypatch.setattr(command_center, "_ga4_item_from_tactical", ga4_item_builder)

    class EmptyMetricStore:
        def list_metric_facts(self, *_args: object) -> list[object]:
            raise AssertionError("Command Center must use batched metric fact reads")

        def list_metric_facts_by_connector(
            self,
            *_args: object,
            **_kwargs: object,
        ) -> dict[str, list[object]]:
            raise AssertionError("Command Center must use latest facts without delta windows")

        def list_latest_metric_facts_by_connector(
            self,
            *_args: object,
            **_kwargs: object,
        ) -> object:
            raise AssertionError("Command Center must use connector-specific limits")

        def list_latest_metric_facts_by_connector_limits(
            self,
            connector_limits: dict[str, int],
        ) -> dict[str, list[object]]:
            seen["metric_connector_limits"] = connector_limits
            return {connector_id: [] for connector_id in connector_limits}

    monkeypatch.setattr(command_center, "metric_store", lambda: EmptyMetricStore())
    monkeypatch.setattr(command_center, "get_connector_status", lambda _connector_id: None)

    command_center.build_command_center_brief(
        tactical_queue=tactical_queue,
        actions=[action],
    )

    assert seen["actions"] == [action]
    assert seen["ads_metric_facts"] == []
    assert seen["merchant_tactical_items"] == tactical_queue.items
    assert seen["merchant_actions"] == [action]
    assert seen["merchant_metric_facts"] == []
    assert seen["content_tactical_queue"] == tactical_queue
    assert seen["content_ahrefs_facts"] == []
    assert seen["content_actions"] == [action]
    assert seen["ga4_tactical_items"] == tactical_queue.items
    assert seen["ga4_actions"] == [action]
    assert seen["ga4_metric_facts"] == []
    assert seen["metric_connector_limits"] == {
        "google_ads": command_center.GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "google_merchant_center": command_center.MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "google_analytics_4": command_center.GA4_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "ahrefs": command_center.AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "localo": 120,
        "google_search_console": tactical_queue_module.GSC_QUERY_PAGE_FACT_LIMIT,
        "wordpress_ekologus": tactical_queue_module.WORDPRESS_INVENTORY_FACT_LIMIT,
        "wordpress_sklep": tactical_queue_module.WORDPRESS_INVENTORY_FACT_LIMIT,
    }


def test_codex_context_pack_full_context_keeps_diagnostic_surfaces(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "context_pack_full.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "context_pack_full.duckdb"))
    ads_response = client.get("/api/ads/diagnostics")
    assert ads_response.status_code == 200
    ads_diagnostics = ads_response.json()
    merchant_response = client.get("/api/merchant/diagnostics")
    assert merchant_response.status_code == 200
    merchant_diagnostics = merchant_response.json()

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command", "full_context": True},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()

    assert "context_scope" not in context_payload
    assert context_payload["tactical_queue"]["language"] == "pl-PL"
    assert "items" in context_payload["tactical_queue"]
    assert context_payload["ads_diagnostics"]["language"] == "pl-PL"
    assert context_payload["ads_diagnostics"]["live_data_available"] == ads_diagnostics[
        "live_data_available"
    ]
    assert context_payload["ads_diagnostics"]["evidence_ids"] == ads_diagnostics["evidence_ids"]
    assert context_payload["ads_diagnostics"]["action_ids"] == ads_diagnostics["action_ids"]
    assert context_payload["merchant_diagnostics"]["language"] == "pl-PL"
    assert context_payload["merchant_diagnostics"]["live_data_available"] == merchant_diagnostics[
        "live_data_available"
    ]
    assert context_payload["merchant_diagnostics"]["evidence_ids"] == merchant_diagnostics[
        "evidence_ids"
    ]
    assert context_payload["merchant_diagnostics"]["action_ids"] == merchant_diagnostics[
        "action_ids"
    ]


def test_daily_context_pack_excludes_social_draft_action_objects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    all_action_ids = {action["id"] for action in actions_response.json()}
    assert "act_prepare_linkedin_social_drafts" in all_action_ids
    assert "act_prepare_facebook_social_drafts" in all_action_ids

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    daily_action_ids = {
        action["id"] for action in context_payload["active_action_objects"]
    }

    assert {
        "act_review_merchant_feed_issues",
        "act_review_ga4_tracking_quality",
        "act_prepare_content_refresh_queue",
    }.issubset(daily_action_ids)
    assert "act_prepare_linkedin_social_drafts" not in daily_action_ids
    assert "act_prepare_facebook_social_drafts" not in daily_action_ids


def test_social_context_pack_keeps_explicit_social_draft_action_objects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-social-publisher"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    social_action_ids = {
        action["id"] for action in context_payload["active_action_objects"]
    }

    assert "act_prepare_linkedin_social_drafts" in social_action_ids
    assert "act_prepare_facebook_social_drafts" in social_action_ids
    assert social_action_ids == {
        "act_prepare_linkedin_social_drafts",
        "act_prepare_facebook_social_drafts",
    }


def test_social_context_pack_exposes_review_only_draft_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-social-publisher"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()

    social_context = context_payload["social_draft_context"]
    assert social_context["mode"] == "review_only"
    assert social_context["publish_allowed"] is False
    assert social_context["missing_publish_access"] == {
        "linkedin": ["LINKEDIN_ORGANIZATION_ID", "LINKEDIN_ACCESS_TOKEN"],
        "facebook": ["FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN"],
    }
    assert "missing_publish_permissions" not in social_context
    assert social_context["draft_action_ids"] == [
        "act_prepare_facebook_social_drafts",
        "act_prepare_linkedin_social_drafts",
    ]
    assert social_context["source_inputs"]
    assert "candidate_inputs" not in social_context
    assert {
        "source_connector",
        "metric_name",
        "value",
        "context_summary",
        "evidence_id",
    }.issubset(social_context["source_inputs"][0])
    assert "no_publishing_without_connector_credentials" in social_context[
        "draft_constraints"
    ]
    assert "opublikowanie posta" in social_context["blocked_claims"]
    assert "wzrost skuteczności social" in social_context["blocked_claims"]
    assert "przychód" in social_context["blocked_claims"]
    assert "wzrost konwersji" in social_context["blocked_claims"]
    old_post_publish_claim = "post " + "published"
    old_social_growth_claim = "social performance " + "up" + "lift"
    assert old_post_publish_claim not in social_context["blocked_claims"]
    assert old_social_growth_claim not in social_context["blocked_claims"]
    serialized_social_context = json.dumps(social_context, ensure_ascii=False)
    assert "candidate_inputs" not in serialized_social_context
    assert "availability_updated" not in serialized_social_context
    assert "FREE_LISTINGS" not in serialized_social_context
    assert "MERCHANT_ACTION" not in serialized_social_context
    assert "n:availability" not in serialized_social_context
    assert context_payload["marketing_brief"]["context_pack_compaction"][
        "sections_compacted"
    ] is True
    assert context_payload["tactical_queue"]["context_pack_compaction"][
        "items_compacted"
    ] is True
    assert context_payload["tactical_queue"]["context_pack_compaction"][
        "metric_facts_removed"
    ] is True
    assert len(json.dumps(context_payload, ensure_ascii=False).encode()) < 140_000


def test_social_draft_actions_exclude_dev_site_inventory_inputs() -> None:
    actions = _social_draft_actions(
        [
            MetricFact(
                name="clicks",
                value=4,
                period="connector_refresh",
                source_connector="google_search_console",
                evidence_id="ev_gsc_social_candidate",
                dimensions={
                    "query": "ekologus bielsko",
                    "page": "https://www.ekologus.pl/",
                },
            ),
            MetricFact(
                name="content_object_seen",
                value=1,
                period="connector_refresh",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wordpress_dev_site_candidate",
                dimensions={
                    "content_url": "https://ekologus.dev.proudsite.pl/",
                    "site_kind": "primary",
                    "status": "publish",
                },
            ),
        ]
    )

    linkedin_action = actions["act_prepare_linkedin_social_drafts"]
    source_inputs = linkedin_action.payload["source_inputs"]
    serialized_inputs = json.dumps(source_inputs, ensure_ascii=False)

    assert source_inputs
    assert "candidate_inputs" not in linkedin_action.payload
    assert "ev_gsc_social_candidate" in linkedin_action.evidence_ids
    assert "ev_wordpress_dev_site_candidate" not in linkedin_action.evidence_ids
    assert "ekologus.dev.proudsite.pl" not in serialized_inputs


def test_codex_context_pack_scopes_content_strategist_payload() -> None:
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-content-strategist"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-content-strategist"
    assert "content_diagnostics" in data
    assert "ads_diagnostics" not in data
    assert "merchant_diagnostics" not in data
    assert "command_center" not in data
    assert len(data["evidence_summaries"]) <= 80
    connector_ids = {connector["id"] for connector in data["connector_status"]}
    assert connector_ids.issubset(
        {
            "google_search_console",
            "google_analytics_4",
            "ahrefs",
            "wordpress_ekologus",
            "wordpress_sklep",
        }
    )
    assert data["content_diagnostics"]["language"] == "pl-PL"
    assert data["content_diagnostics"]["evidence_ids"]
    assert "sections" not in data["content_diagnostics"]
    assert '"metric_facts":' not in json.dumps(data["content_diagnostics"])
    assert data["context_pack_compaction"]["connector_refresh_runs_compacted"] is True
    assert data["context_pack_compaction"]["evidence_summaries_compacted"] is True
    assert data["context_pack_compaction"]["knowledge_card_summaries_compacted"] is True
    assert data["context_pack_compaction"]["raw_history_omitted"] is True
    content_compaction = data["content_diagnostics"]["context_pack_compaction"]
    assert content_compaction["metric_facts_removed"] is True
    assert content_compaction["sections_omitted"] is True
    assert content_compaction["sections_total"] == 3
    assert content_compaction["connectors_compacted"] is True
    assert content_compaction["latest_refreshes_compacted"] is True
    assert content_compaction["full_endpoint"] == "/api/content/diagnostics"
    serialized_operator_context = json.dumps(
        {
            "connector_status": data["connector_status"],
            "connector_refresh_runs": data["connector_refresh_runs"],
            "evidence_summaries": data["evidence_summaries"],
            "knowledge_card_summaries": data["knowledge_card_summaries"],
            "expert_rule_summaries": data["expert_rule_summaries"],
            "active_action_objects": data["active_action_objects"],
            "content_diagnostics_connectors": data["content_diagnostics"].get("connectors"),
            "content_diagnostics_latest_refreshes": data["content_diagnostics"].get(
                "latest_refreshes"
            ),
        },
        ensure_ascii=False,
    )
    for forbidden_term in (
        "target_site",
        "mapping_review",
        "vendor_read",
        "Read-only",
        "read-only",
        "review-only",
        "ActionObject",
    ):
        assert forbidden_term not in serialized_operator_context


def test_codex_context_pack_scopes_gsc_content_doctor_without_ahrefs_decisions() -> None:
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-gsc-content-doctor"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-gsc-content-doctor"
    assert "content_diagnostics" in data
    assert "ahrefs_diagnostics" not in data
    content = data["content_diagnostics"]
    assert content["language"] == "pl-PL"
    assert "sections" not in content
    assert content["decision_queue"]
    assert all(
        decision["decision_type"] != "review_ahrefs_gap_records"
        for decision in content["decision_queue"]
    )
    assert all(
        "ahrefs" not in decision.get("source_connectors", [])
        for decision in content["decision_queue"]
    )
    assert "ahrefs" not in {
        connector
        for decision in content["decision_queue"]
        for connector in decision.get("source_connectors", [])
    }
    assert all(
        "_ahrefs" not in str(evidence_id)
        for evidence_id in content["evidence_ids"]
    )
    assert content["context_pack_compaction"]["purpose"] == "gsc_content_doctor_context"
    assert content["context_pack_compaction"]["ahrefs_decisions_removed"] is True


def test_codex_context_pack_scopes_merchant_payload_preview(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-merchant-feed-operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-merchant-feed-operator"
    assert data["context_scope"]["source_connectors"] == ["google_merchant_center"]
    assert "merchant_diagnostics" in data
    assert "ads_diagnostics" not in data
    assert "command_center" not in data
    assert data["merchant_diagnostics"]["action_ids"] == [
        "act_review_merchant_feed_issues"
    ]
    actions_by_id = {action["id"]: action for action in data["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    payload = merchant_action["payload"]
    assert payload["preview_contract"] == "merchant_feed_issue_review_preview_v1"
    assert payload["payload_preview_total"] == 1
    assert payload["payload_preview_included"] == 1
    preview = payload["payload_preview"][0]
    assert preview["preview_contract"] == "merchant_feed_issue_review_preview_v1"
    assert preview["operation_type"] == "MerchantIssueClusterReview"
    assert "issue_type" not in preview
    assert "cluster_id" not in preview
    assert "reporting_context" not in preview
    assert "issue_summary" in preview
    assert preview["metric_snapshot"] == {"issue_product_count": 3}
    assert preview["apply_allowed"] is False
    assert preview["api_mutation_ready"] is False
    assert preview["destructive"] is False
    assert "zapis do feedu" in preview["blocked_claims"]
    serialized = json.dumps(data, ensure_ascii=False)
    assert "landing_page_error" not in serialized
    assert "SHOPPING_ADS" not in serialized
    assert "MERCHANT_ACTION" not in serialized
    assert "command_center" not in data
    assert len(serialized.encode()) < 80_000

    alias_response = client.post(
        "/api/codex/context-pack",
        json={"skill_id": "wilq-merchant-feed-operator"},
    )
    assert alias_response.status_code == 200
    alias_data = alias_response.json()
    assert alias_data["context_scope"]["mode"] == "skill"
    assert alias_data["context_scope"]["skill"] == "wilq-merchant-feed-operator"
    assert "command_center" not in alias_data


def test_ads_doctor_context_pack_uses_summary_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    captured_views: list[str] = []

    def recording_build_ads_diagnostics(
        actions: list[ActionObject] | None = None,
        *,
        view: Literal["full", "summary"] = "full",
    ) -> Any:
        captured_views.append(view)
        return build_ads_diagnostics(actions=actions, view=view)

    monkeypatch.setattr(
        "apps.api.wilq_api.main.build_ads_diagnostics",
        recording_build_ads_diagnostics,
    )

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )

    assert response.status_code == 200
    assert captured_views == ["summary"]


def test_codex_context_pack_scopes_ads_doctor_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    ads_response = client.get("/api/ads/diagnostics")
    assert ads_response.status_code == 200
    ads_diagnostics = ads_response.json()

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )

    assert response.status_code == 200
    data = response.json()
    ads_context = data["ads_diagnostics"]
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-ads-doctor"
    referenced_knowledge_card_ids = {
        card_id
        for decision in ads_context["decision_queue"]
        for card_id in decision.get("knowledge_card_ids", [])
    }
    referenced_expert_rule_ids = {
        rule_id
        for decision in ads_context["decision_queue"]
        for rule_id in decision.get("expert_rule_ids", [])
    }
    context_knowledge_card_ids = {
        card["id"] for card in data["knowledge_card_summaries"]
    }
    context_expert_rule_ids = {rule["id"] for rule in data["expert_rule_summaries"]}
    assert referenced_knowledge_card_ids
    assert referenced_expert_rule_ids
    assert referenced_knowledge_card_ids.issubset(context_knowledge_card_ids)
    assert referenced_expert_rule_ids.issubset(context_expert_rule_ids)
    assert "ads_diagnostics" in data
    assert "content_diagnostics" not in data
    assert "command_center" not in data
    assert ads_context["evidence_ids"] == ads_diagnostics["evidence_ids"]
    assert ads_context["action_ids"] == ads_diagnostics["action_ids"]
    assert ads_context["context_pack_compaction"]["metric_facts_removed"] is True
    assert ads_context["context_pack_compaction"]["sections_omitted"] is True
    assert ads_context["context_pack_compaction"]["sections_total"] >= 0
    assert ads_context["context_pack_compaction"]["decision_row_payloads_omitted"] is True
    assert ads_context["context_pack_compaction"]["empty_decision_row_lists_omitted"] is True
    assert ads_context["context_pack_compaction"]["full_endpoint"] == "/api/ads/diagnostics"
    assert "sections" not in ads_context
    triage_contract = ads_context["campaign_triage_read_contract"]
    assert triage_contract["status"] == "ready"
    assert triage_contract["triage_rows"]
    assert len(triage_contract["triage_rows"]) <= 4
    assert triage_contract["triage_rows"][0]["action_ids"] == [
        "act_prepare_ads_campaign_review_queue"
    ]
    assert "zmarnowany budżet" in triage_contract["blocked_claims"]
    assert (
        ads_context["context_pack_compaction"]["campaign_triage_rows_included"]
        == len(triage_contract["triage_rows"])
    )
    optimizer_contract = ads_context["optimizer_readiness_contract"]
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["apply_allowed"] is False
    assert "campaign_review_queue" in [
        item["id"] for item in optimizer_contract["readiness_items"]
    ]
    assert "zapis zmian kampanii" in optimizer_contract["blocked_claims"]
    assert ads_context["change_impact_readiness_contract"]["status"] == "blocked"
    assert "wpływ zmian" in ads_context["change_impact_readiness_contract"][
        "blocked_claims"
    ]
    if ads_context["change_history_read_contract"]["change_history_rows"]:
        assert ads_context["change_impact_readiness_contract"]["readiness_rows"]
        assert (
            "current_campaign_snapshot"
            not in ads_context["change_impact_readiness_contract"][
                "missing_read_contracts"
            ]
        )
    custom_segment_candidate = ads_context["custom_segments_read_contract"]["candidates"][0]
    assert "source_quality" in custom_segment_candidate
    assert "rejection_reasons" not in custom_segment_candidate
    assert ads_context["context_pack_compaction"][
        "custom_segment_candidate_search_term_rows_compacted"
    ] is True
    assert custom_segment_candidate["search_term_rows_included"] == len(
        custom_segment_candidate["search_term_rows"]
    )
    assert custom_segment_candidate["search_term_rows_total"] >= len(
        custom_segment_candidate["search_term_rows"]
    )
    for row in custom_segment_candidate["search_term_rows"]:
        assert set(row) == {
            "search_term",
            "clicks",
            "cost_micros",
            "conversions",
            "evidence_ids",
            "missing_metrics",
        }
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000
    target_interpretation = ads_context["business_context_read_contract"][
        "target_interpretation"
    ]
    assert target_interpretation["interpretation_contract"] == (
        "ads_business_target_interpretation_v1"
    )
    strategy_readiness = ads_context["business_context_read_contract"][
        "strategy_review_readiness_contract"
    ]
    assert strategy_readiness["id"] == "ads_strategy_review_readiness_contract"
    assert strategy_readiness["apply_allowed"] is False
    assert "human_strategy_review" in strategy_readiness["required_validation"]
    assert "ocena opłacalności" in strategy_readiness["blocked_claims"]
    assert "[REDACTED]" not in json.dumps(target_interpretation, ensure_ascii=False)
    assert len(data["connector_refresh_runs"]) <= 3
    for action in data["active_action_objects"]:
        payload = action.get("payload") or {}
        for rows_key in (
            "campaign_candidates",
            "budget_payload_preview",
            "recommendations",
            "terms",
            "source_terms",
            "payload_preview",
            "keyword_match_context",
        ):
            rows = payload.get(rows_key)
            if isinstance(rows, list):
                if rows_key == "campaign_candidates" and action["id"] == (
                    "act_prepare_ads_campaign_review_queue"
                ):
                    assert 0 < len(rows) <= 3
                    assert payload[f"{rows_key}_included"] == len(rows)
                elif rows_key == "payload_preview" and action["id"] == (
                    "act_prepare_custom_segments_from_search_terms"
                ):
                    assert len(rows) == 1
                    assert rows[0]["safety_review"]["safety_contract"] == (
                        "custom_segment_apply_safety_v1"
                    )
                    assert rows[0]["safety_review"]["apply_allowed"] is False
                    assert payload[f"{rows_key}_included"] == 1
                else:
                    assert rows == []
                    assert payload[f"{rows_key}_included"] == 0
                assert payload[f"{rows_key}_total"] >= 0
    actions_by_id = {action["id"]: action for action in data["active_action_objects"]}
    assert "act_review_demand_gen_readiness" not in actions_by_id
    campaign_review_action = actions_by_id["act_prepare_ads_campaign_review_queue"]
    campaign_candidate = campaign_review_action["payload"]["campaign_candidates"][0]
    full_action_response = client.get("/api/actions/act_prepare_ads_campaign_review_queue")
    assert full_action_response.status_code == 200
    full_campaign_candidate = full_action_response.json()["payload"][
        "campaign_candidates"
    ][0]
    assert campaign_candidate["campaign_name"] == full_campaign_candidate["campaign_name"]
    assert campaign_candidate["review_priority"] == full_campaign_candidate[
        "review_priority"
    ]
    assert campaign_candidate["review_score"] == full_campaign_candidate["review_score"]
    assert "Kolejność oceny kampanii" in campaign_candidate["review_reason"]
    assert campaign_candidate["review_reason"] == full_campaign_candidate[
        "review_reason"
    ]
    assert campaign_candidate["human_review_gates"] == full_campaign_candidate[
        "human_review_gates"
    ]
    assert campaign_candidate["target_context"] == full_campaign_candidate[
        "target_context"
    ]
    assert "review_campaign_goal" in campaign_candidate["human_review_gates"]
    assert campaign_candidate["apply_allowed"] is False
    assert len(ads_context["search_terms_read_contract"]["search_term_rows"]) <= 8
    assert len(ads_context["search_term_ngram_read_contract"]["ngram_rows"]) <= 8
    assert len(ads_context["search_term_safety_read_contract"]["safety_rows"]) <= 8
    assert len(ads_context["keyword_match_context_read_contract"]["context_rows"]) <= 8
    assert len(ads_context["budget_pacing_read_contract"]["payload_preview"]) <= 4
    budget_preview = ads_context["budget_pacing_read_contract"]["payload_preview"][0]
    assert budget_preview["safety_review"]["safety_contract"] == (
        "campaign_budget_apply_safety_v1"
    )
    assert budget_preview["safety_review"]["apply_allowed"] is False
    assert len(ads_context["recommendations_read_contract"]["payload_preview"]) <= 8
    assert ads_context["context_pack_compaction"][
        "recommendation_row_payload_previews_omitted"
    ] is True
    for recommendation_row in ads_context["recommendations_read_contract"][
        "recommendation_rows"
    ]:
        assert "payload_preview" not in recommendation_row
        assert recommendation_row["payload_preview_total"] >= 0
        assert recommendation_row["payload_preview_included"] == 0
    assert len(ads_context["negative_keywords_read_contract"]["payload_preview"]) <= 8
    assert ads_context["context_pack_compaction"][
        "negative_keyword_candidate_context_rows_compacted"
    ] is True
    assert (
        ads_context["context_pack_compaction"]["budget_payload_preview_included"]
        <= 4
    )
    for candidate in ads_context["negative_keywords_read_contract"]["candidates"]:
        assert len(candidate["keyword_context_rows"]) <= 2
        assert candidate["keyword_context_rows_included"] == len(
            candidate["keyword_context_rows"]
        )
        assert candidate["keyword_context_rows_total"] >= len(
            candidate["keyword_context_rows"]
        )
        for row in candidate["keyword_context_rows"]:
            assert set(row) == {
                "keyword_text",
                "match_type",
                "criterion_status",
                "negative",
                "evidence_ids",
            }
    for decision in ads_context["decision_queue"]:
        assert "budget_apply_preview" not in decision
        assert len(decision.get("recommendation_apply_preview", [])) <= 4
        assert len(decision.get("search_term_safety_rows", [])) <= 4
        assert len(decision.get("keyword_match_context_rows", [])) <= 4
        assert len(decision.get("negative_keyword_payload_preview", [])) <= 4
        assert decision.get("omitted_empty_row_lists_count", 0) > 0
        for candidate in decision.get("negative_keyword_candidates", []):
            assert len(candidate["keyword_context_rows"]) <= 4
    assert (
        ads_context["context_pack_compaction"]["keyword_match_context_rows_included"]
        <= 8
    )
    assert (
        ads_context["context_pack_compaction"]["search_term_safety_rows_included"]
        <= 8
    )
    assert (
        ads_context["context_pack_compaction"][
            "recommendation_apply_preview_included"
        ]
        <= 8
    )
    assert '"metric_facts":' not in json.dumps(ads_context)
    assert "safety_metric_facts" not in json.dumps(ads_context)
    ngram_context_action = next(
        action
        for action in data["active_action_objects"]
        if action["id"] == SEARCH_TERM_NGRAM_ACTION_ID
    )
    assert ngram_context_action["payload"]["ngram_preview_included"] <= 4


def test_ads_doctor_context_pack_preserves_recommendation_impact_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    save_google_ads_recommendation_rows_for_context_pack()

    ads_response = client.get("/api/ads/diagnostics")
    assert ads_response.status_code == 200
    ads_recommendations = ads_response.json()["recommendations_read_contract"]
    endpoint_impact_ids = [
        row["recommendation_id"]
        for row in ads_recommendations["recommendation_rows"]
        if row["impact_available"]
    ]

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )

    assert response.status_code == 200
    pack_recommendations = response.json()["ads_diagnostics"][
        "recommendations_read_contract"
    ]
    pack_impact_ids = [
        row["recommendation_id"]
        for row in pack_recommendations["recommendation_rows"]
        if row["impact_available"]
    ]
    assert len(ads_recommendations["recommendation_rows"]) > 3
    assert endpoint_impact_ids == ["rec-a", "rec-d"]
    assert pack_impact_ids == endpoint_impact_ids


def test_codex_context_pack_scopes_custom_segments_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-custom-segments"},
    )

    assert response.status_code == 200
    data = response.json()
    ads_context = data["ads_diagnostics"]
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-custom-segments"
    assert "content_diagnostics" not in data
    assert "command_center" not in data
    assert [action["id"] for action in data["active_action_objects"]] == [
        "act_prepare_custom_segments_from_search_terms"
    ]
    assert data["top_opportunities"] == []
    assert ads_context["action_ids"] == ["act_prepare_custom_segments_from_search_terms"]
    assert [decision["id"] for decision in ads_context["decision_queue"]] == [
        "ads_prepare_custom_segments_from_search_terms"
    ]
    assert ads_context["custom_segments_read_contract"]["payload_preview"]
    context_safety_review = ads_context["custom_segments_read_contract"][
        "payload_preview"
    ][0]["safety_review"]
    assert context_safety_review["safety_contract"] == "custom_segment_apply_safety_v1"
    assert context_safety_review["status"] == "blocked"
    assert context_safety_review["apply_allowed"] is False
    assert context_safety_review["api_mutation_ready"] is False
    assert context_safety_review["audit_required"] is True
    assert "forecast_or_audience_size" in context_safety_review[
        "missing_requirements"
    ]
    assert "google_ads_mutation_audit" in context_safety_review[
        "missing_requirements"
    ]
    action_safety_review = data["active_action_objects"][0]["payload"][
        "payload_preview"
    ][0]["safety_review"]
    assert action_safety_review["safety_contract"] == "custom_segment_apply_safety_v1"
    assert action_safety_review["apply_allowed"] is False
    assert ads_context["custom_segments_read_contract"][
        "audience_forecast_read_contract"
    ]["forecast_rows"]
    assert "custom_segment_change_preview" not in ads_context[
        "custom_segments_read_contract"
    ]["missing_read_contracts"]
    assert "recommendations_read_contract" not in ads_context
    assert "negative_keywords_read_contract" not in ads_context
    assert "budget_pacing_read_contract" not in ads_context
    assert "campaign_read_contract" not in ads_context
    assert "search_terms_read_contract" in ads_context
    assert ads_context["context_pack_compaction"]["purpose"] == "custom_segments_context"
    assert ads_context["context_pack_compaction"][
        "custom_segment_payload_preview_included"
    ] <= 8
    for action in data["active_action_objects"]:
        assert action["metrics_included"] <= 3
        assert action["metrics_total"] >= action["metrics_included"]
        payload = action.get("payload") or {}
        rows = payload.get("payload_preview")
        if isinstance(rows, list):
            if action["id"] == "act_prepare_custom_segments_from_search_terms":
                assert len(rows) == 1
                assert rows[0]["safety_review"]["safety_contract"] == (
                    "custom_segment_apply_safety_v1"
                )
                assert payload["payload_preview_included"] == 1
            else:
                assert rows == []
                assert payload["payload_preview_included"] == 0
            assert payload["payload_preview_total"] >= 0


def test_codex_context_pack_scopes_campaign_builder_payload() -> None:
    content_response = client.get("/api/content/diagnostics")
    assert content_response.status_code == 200
    content_payload = content_response.json()

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-campaign-builder"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-campaign-builder"
    assert set(data["context_scope"]["source_connectors"]) == {
        "google_ads",
        "google_analytics_4",
        "google_search_console",
    }
    assert "ads_diagnostics" in data
    assert "content_landing_context" in data
    assert "command_center" not in data
    assert "merchant_diagnostics" not in data
    assert "content_diagnostics" not in data
    action_ids = {action["id"] for action in data["active_action_objects"]}
    assert action_ids == {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
    }
    assert data["content_landing_context"]["source_connectors"] == [
        "google_search_console"
    ]
    assert data["content_landing_context"]["context_pack_compaction"][
        "full_endpoint"
    ] == "/api/content/diagnostics"
    assert data["content_landing_context"]["context_pack_compaction"][
        "purpose"
    ] == "landing_context"
    if content_payload["query_page_count"] > 0:
        assert data["content_landing_context"]["live_data_available"] is True
        assert data["content_landing_context"]["query_page_candidates"]
        first_candidate = data["content_landing_context"]["query_page_candidates"][0]
        assert first_candidate["page"]
        assert first_candidate["query"]
        assert first_candidate["evidence_ids"]
    if data["content_landing_context"]["live_data_available"]:
        assert data["content_landing_context"]["query_page_candidates"]
        first_candidate = data["content_landing_context"]["query_page_candidates"][0]
        assert first_candidate["page"]
        assert first_candidate["query"]
        assert first_candidate["evidence_ids"]
    assert data["ads_diagnostics"]["context_pack_compaction"][
        "metric_facts_removed"
    ] is True
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000


def test_codex_context_pack_scopes_demand_gen_payload() -> None:
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-demand-gen-operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-demand-gen-operator"
    assert "ads_diagnostics" in data
    assert "ga4_diagnostics" in data
    assert "demand_gen_readiness" in data
    assert "merchant_diagnostics" not in data
    assert "command_center" not in data
    assert set(data["context_scope"]["source_connectors"]) == {
        "google_ads",
        "google_analytics_4",
    }
    assert [action["id"] for action in data["active_action_objects"]] == [
        "act_review_demand_gen_readiness"
    ]
    assert data["active_action_objects"][0]["payload"]["preview_contract"] == (
        "demand_gen_readiness_review_preview_v1"
    )
    assert data["active_action_objects"][0]["payload"]["apply_allowed"] is False
    assert data["ads_diagnostics"]["action_ids"] == []
    readiness = data["demand_gen_readiness"]
    assert readiness["status"] == "blocked"
    assert readiness["title"].startswith("Demand Gen:")
    assert readiness["metric_tiles"]["kampanie Ads"] == readiness["campaign_rows_evaluated"]
    assert readiness["metric_tiles"]["braki"] == len(readiness["missing_read_contracts"])
    assert readiness["action_ids"] == ["act_review_demand_gen_readiness"]
    assert readiness["payload_preview"][0]["preview_contract"] == (
        "demand_gen_readiness_review_preview_v1"
    )
    assert readiness["payload_preview"][0]["api_mutation_ready"] is False
    assert readiness["source_connectors"] == ["google_ads", "google_analytics_4"]
    assert isinstance(readiness["campaign_rows_evaluated"], int)
    assert isinstance(readiness["campaign_channel_counts"], dict)
    assert isinstance(readiness["demand_gen_campaign_rows"], list)
    campaign_rows = data["ads_diagnostics"]["campaign_read_contract"]["campaign_rows"]
    if campaign_rows:
        assert any(row.get("advertising_channel_type") for row in campaign_rows)
        assert readiness["campaign_rows_evaluated"] >= len(campaign_rows)
        assert readiness["campaign_channel_counts"]
        assert "demand_gen_campaign_rows" in readiness["available_read_contracts"]
        assert "demand_gen_campaign_rows" not in readiness["missing_read_contracts"]
    assert "demand_gen_asset_group_rows" not in readiness["missing_read_contracts"]
    assert isinstance(readiness["demand_gen_ad_group_ad_rows"], list)
    assert isinstance(readiness["demand_gen_creative_asset_rows"], list)
    if "demand_gen_ad_group_ad_rows" in readiness["available_read_contracts"]:
        assert "demand_gen_ad_group_ad_rows" not in readiness["missing_read_contracts"]
    else:
        assert "demand_gen_ad_group_ad_rows" in readiness["missing_read_contracts"]
    if "demand_gen_creative_asset_rows" in readiness["available_read_contracts"]:
        assert "demand_gen_creative_asset_rows" not in readiness["missing_read_contracts"]
    else:
        assert "demand_gen_creative_asset_rows" in readiness["missing_read_contracts"]
    assert "demand_gen_readiness_review_action_object" in readiness["available_read_contracts"]
    assert "demand_gen_action_object" not in readiness["missing_read_contracts"]
    assert "rekomendacja uruchomienia Demand Gen" in readiness["blocked_claims"]
    assert "sections" not in data["ga4_diagnostics"]
    assert '"metric_facts":' not in json.dumps(data["ga4_diagnostics"])
    assert data["ga4_diagnostics"]["context_pack_compaction"][
        "full_endpoint"
    ] == "/api/ga4/diagnostics"
    assert data["ads_diagnostics"]["context_pack_compaction"][
        "metric_facts_removed"
    ] is True
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000


def test_codex_context_pack_scopes_demand_gen_without_full_ga4_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_full_ga4_builder(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Demand Gen context must not build full GA4 diagnostics")

    monkeypatch.setattr(
        "apps.api.wilq_api.main.build_ga4_diagnostics",
        fail_full_ga4_builder,
    )

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-demand-gen-operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "demand_gen_readiness" in data
    assert data["ga4_diagnostics"]["context_pack_compaction"][
        "full_endpoint"
    ] == "/api/ga4/diagnostics"


def test_demand_gen_diagnostics_exposes_honest_readiness_contract() -> None:
    response = client.get("/api/demand-gen/diagnostics")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["title"].startswith("Demand Gen:")
    assert data["metric_tiles"]["kampanie Ads"] == data["campaign_rows_evaluated"]
    assert data["metric_tiles"]["braki"] == len(data["missing_read_contracts"])
    assert data["source_connectors"] == ["google_ads", "google_analytics_4"]
    assert data["action_ids"] == ["act_review_demand_gen_readiness"]
    assert data["payload_preview"][0]["preview_contract"] == (
        "demand_gen_readiness_review_preview_v1"
    )
    assert data["payload_preview"][0]["apply_allowed"] is False
    assert data["payload_preview"][0]["destructive"] is False
    assert isinstance(data["campaign_rows_evaluated"], int)
    assert isinstance(data["campaign_channel_counts"], dict)
    assert isinstance(data["demand_gen_campaign_rows"], list)
    if data["campaign_rows_evaluated"] > 0:
        assert "demand_gen_campaign_rows" in data["available_read_contracts"]
        assert "demand_gen_campaign_rows" not in data["missing_read_contracts"]
    assert "demand_gen_asset_group_rows" not in data["missing_read_contracts"]
    assert isinstance(data["demand_gen_ad_group_ad_rows"], list)
    assert isinstance(data["demand_gen_creative_asset_rows"], list)
    if "demand_gen_ad_group_ad_rows" in data["available_read_contracts"]:
        assert "demand_gen_ad_group_ad_rows" not in data["missing_read_contracts"]
    else:
        assert "demand_gen_ad_group_ad_rows" in data["missing_read_contracts"]
    if "demand_gen_creative_asset_rows" in data["available_read_contracts"]:
        assert "demand_gen_creative_asset_rows" not in data["missing_read_contracts"]
    else:
        assert "demand_gen_creative_asset_rows" in data["missing_read_contracts"]
    assert isinstance(data["demand_gen_landing_quality_rows"], list)
    assert isinstance(data["demand_gen_transition_constraint_rows"], list)
    assert "demand_gen_landing_quality_by_campaign" not in data["missing_read_contracts"]
    assert "demand_gen_transition_constraints" not in data["missing_read_contracts"]
    assert "demand_gen_readiness_review_action_object" in data["available_read_contracts"]
    assert "demand_gen_action_object" not in data["missing_read_contracts"]
    assert "rekomendacja uruchomienia Demand Gen" in data["blocked_claims"]


def test_demand_gen_diagnostics_does_not_require_full_ga4_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_full_ga4_builder(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Demand Gen diagnostics must not build full GA4 diagnostics")

    monkeypatch.setattr(
        "apps.api.wilq_api.main.build_ga4_diagnostics",
        fail_full_ga4_builder,
    )

    response = client.get("/api/demand-gen/diagnostics")

    assert response.status_code == 200
    assert response.json()["source_connectors"] == ["google_ads", "google_analytics_4"]


def test_demand_gen_diagnostics_uses_empty_read_ad_and_asset_contracts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "demand_gen.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "demand_gen.duckdb"))
    run = ConnectorRefreshRun(
        id="refresh_google_ads_demand_gen_empty_read",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_ads_demand_gen_empty_read"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "demand_gen_ad_group_ad_status": "ready",
            "demand_gen_ad_group_ad_row_count": 0,
            "demand_gen_asset_reference_count": 0,
            "demand_gen_creative_asset_status": "ready",
            "demand_gen_creative_asset_row_count": 0,
            "demand_gen_creative_asset_impressions": 0,
        },
        summary="Google Ads Demand Gen empty-read proof seed.",
    )
    ga4_run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_demand_gen_landing_read",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_analytics_4_demand_gen_landing_read"],
        external_call_attempted=True,
        vendor_data_collected=True,
        summary="GA4 Demand Gen landing quality seed.",
    )
    local_state_store().save_connector_refresh_run(run)
    local_state_store().save_connector_refresh_run(ga4_run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=12,
                dimensions={
                    "campaign_id": "103",
                    "campaign_name": "Demand Gen Test",
                    "campaign_status": "PAUSED",
                    "advertising_channel_type": "DEMAND_GEN",
                },
            ),
            VendorMetricFact(
                name="demand_gen_ad_available",
                value=1,
                dimensions={
                    "campaign_id": "103",
                    "campaign_name": "Demand Gen Test",
                    "campaign_status": "PAUSED",
                    "advertising_channel_type": "DEMAND_GEN",
                    "ad_group_id": "203",
                    "ad_group_name": "DG grupa",
                    "ad_id": "803",
                    "ad_type": "DEMAND_GEN_MULTI_ASSET_AD",
                    "ad_status": "PAUSED",
                },
                period="demand_gen_ad_inventory",
            ),
            VendorMetricFact(
                name="demand_gen_ad_asset_reference_count",
                value=4,
                dimensions={
                    "campaign_id": "103",
                    "campaign_name": "Demand Gen Test",
                    "campaign_status": "PAUSED",
                    "advertising_channel_type": "DEMAND_GEN",
                    "ad_group_id": "203",
                    "ad_group_name": "DG grupa",
                    "ad_id": "803",
                    "ad_type": "DEMAND_GEN_MULTI_ASSET_AD",
                    "ad_status": "PAUSED",
                },
                period="demand_gen_ad_inventory",
            ),
            VendorMetricFact(
                name="demand_gen_creative_asset_impressions",
                value=44,
                dimensions={
                    "asset_id": "901",
                    "asset_type": "DEMAND_GEN_CAROUSEL_CARD",
                    "field_type": "DEMAND_GEN_CAROUSEL_CARD",
                },
                period="demand_gen_creative_asset",
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        ga4_run,
        detailed_facts=[
            VendorMetricFact(
                name="active_users",
                value=18,
                dimensions={
                    "landing_page": "/dg-test/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Demand Gen Test",
                },
                period="ga4_landing_source_campaign",
            ),
            VendorMetricFact(
                name="sessions",
                value=24,
                dimensions={
                    "landing_page": "/dg-test/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Demand Gen Test",
                },
                period="ga4_landing_source_campaign",
            ),
            VendorMetricFact(
                name="engagement_rate",
                value=0.75,
                dimensions={
                    "landing_page": "/dg-test/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Demand Gen Test",
                },
                period="ga4_landing_source_campaign",
            ),
        ],
    )

    response = client.get("/api/demand-gen/diagnostics")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert "demand_gen_ad_group_ad_rows" in data["available_read_contracts"]
    assert "demand_gen_creative_asset_rows" in data["available_read_contracts"]
    assert "demand_gen_ad_group_ad_rows" not in data["missing_read_contracts"]
    assert "demand_gen_asset_group_rows" not in data["missing_read_contracts"]
    assert "demand_gen_creative_asset_rows" not in data["missing_read_contracts"]
    assert "demand_gen_landing_quality_by_campaign" in data["available_read_contracts"]
    assert "demand_gen_transition_constraints" in data["available_read_contracts"]
    assert "demand_gen_landing_quality_by_campaign" not in data["missing_read_contracts"]
    assert "demand_gen_transition_constraints" not in data["missing_read_contracts"]
    assert data["metric_tiles"]["reklamy Demand Gen"] == 1
    assert data["metric_tiles"]["kreacje Demand Gen"] == 1
    assert data["metric_tiles"]["strony wejścia Demand Gen"] == 1
    assert data["metric_tiles"]["ograniczenia"] == 1
    assert len(data["demand_gen_ad_group_ad_rows"]) == 1
    assert len(data["demand_gen_creative_asset_rows"]) == 1
    assert len(data["demand_gen_landing_quality_rows"]) == 1
    assert len(data["demand_gen_transition_constraint_rows"]) == 1
    assert data["demand_gen_ad_group_ad_rows"][0]["ad_id"] == "803"
    assert data["demand_gen_ad_group_ad_rows"][0]["asset_reference_count"] == 4
    assert data["demand_gen_creative_asset_rows"][0]["asset_id"] == "901"
    assert data["demand_gen_creative_asset_rows"][0]["impressions"] == 44
    assert data["demand_gen_landing_quality_rows"][0]["campaign_name"] == "Demand Gen Test"
    assert data["demand_gen_landing_quality_rows"][0]["landing_page"] == "/dg-test/"
    assert data["demand_gen_landing_quality_rows"][0]["active_users"] == 18
    assert data["demand_gen_landing_quality_rows"][0]["sessions"] == 24
    assert data["demand_gen_landing_quality_rows"][0]["engagement_rate"] == 0.75
    assert data["demand_gen_transition_constraint_rows"][0]["campaign_name"] == (
        "Demand Gen Test"
    )
    assert data["demand_gen_transition_constraint_rows"][0]["transition_candidate"] is False
    assert "already_demand_gen" in data["demand_gen_transition_constraint_rows"][0]["reason"]
    preview = data["payload_preview"][0]
    assert preview["demand_gen_ad_group_ad_row_count"] == 1
    assert preview["demand_gen_creative_asset_row_count"] == 1
    assert preview["demand_gen_landing_quality_row_count"] == 1
    assert preview["demand_gen_transition_constraint_row_count"] == 1
    assert preview["apply_allowed"] is False
    assert "rekomendacja uruchomienia Demand Gen" in data["blocked_claims"]


def test_demand_gen_review_action_is_validate_only_and_scoped() -> None:
    response = client.get("/api/actions/act_review_demand_gen_readiness")

    assert response.status_code == 200
    action = response.json()
    assert action["connector"] == "google_ads"
    assert action["mode"] == "prepare"
    assert action["payload"]["action_type"] == "google_ads_demand_gen_readiness_review"
    assert action["payload"]["preview_contract"] == "demand_gen_readiness_review_preview_v1"
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False
    assert action["payload"]["payload_preview"][0]["api_mutation_ready"] is False
    assert "rekomendacja uruchomienia Demand Gen" in action["payload"]["blocked_claims"]

    validation = client.post(
        "/api/actions/act_review_demand_gen_readiness/validate",
        json={},
    )

    assert validation.status_code == 200
    assert validation.json()["valid"] is True


def test_codex_context_pack_includes_expert_rule_summaries() -> None:
    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert response.status_code == 200
    data = response.json()
    rule_ids = {rule["id"] for rule in data["expert_rule_summaries"]}
    assert "ads_principles_v1" in rule_ids
    assert data["expert_capabilities"]
    assert all(capability["required_mapping"] == [] for capability in data["expert_capabilities"])
    assert all(
        isinstance(capability["required_mapping_total"], int)
        for capability in data["expert_capabilities"]
    )


def test_knowledge_playbooks_are_machine_readable_and_evidence_gated() -> None:
    response = client.get("/api/knowledge/playbooks")
    assert response.status_code == 200
    playbooks = response.json()
    families = {playbook["family"] for playbook in playbooks}
    assert {
        "google_ads_search_playbook",
        "google_ads_budget_review_playbook",
        "google_ads_demand_gen_playbook",
        "google_ads_pmax_playbook",
        "google_ads_negative_keywords_playbook",
        "google_ads_custom_segments_playbook",
        "gsc_seo_content_playbook",
        "ahrefs_content_gap_playbook",
        "localo_local_seo_playbook",
        "ga4_behavior_diagnostics_playbook",
        "merchant_feed_optimization_playbook",
        "linkedin_content_playbook",
        "facebook_content_playbook",
        "wordpress_content_refresh_playbook",
    }.issubset(families)
    assert all("evidence_ids" in playbook["required_evidence"] for playbook in playbooks)
    assert all(playbook["maps_to_opportunity_types"] for playbook in playbooks)
    assert all(playbook["maps_to_action_types"] for playbook in playbooks)


def test_knowledge_compiler_produces_lineage_preserving_card_types() -> None:
    response = client.post("/api/knowledge/condense")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    card_types = {card["card_type"] for card in result["cards"]}
    assert {
        "service_card",
        "content_card",
        "keyword_cluster_card",
        "campaign_card",
        "voice_rule",
        "ads_pattern_card",
        "negative_keyword_pattern_card",
        "competitor_card",
        "local_visibility_card",
        "social_pattern_card",
    }.issubset(card_types)
    assert all(card["source_lineage"] for card in result["cards"])
    assert all(card["source_url_or_path"] for card in result["cards"])


def test_codex_context_pack_includes_compiled_knowledge_cards() -> None:
    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert response.status_code == 200
    data = response.json()
    card_ids = {card["id"] for card in data["knowledge_card_summaries"]}
    assert "card_google_ads_search_playbook" in card_ids
    assert "card_google_ads_budget_review_playbook" in card_ids
    assert "card_goal_001_rules" in card_ids
    evidence_ids = {item["id"] for item in data["evidence_summaries"]}
    assert "ev_connector_google_ads_status" in evidence_ids


def test_knowledge_operating_map_binds_sources_to_decisions() -> None:
    response = client.get("/api/knowledge/operating-map")
    assert response.status_code == 200
    data = response.json()
    assert data["source_card_count"] >= 10
    assert data["playbook_count"] >= 10
    assert data["expert_rule_count"] >= 10
    binding_by_id = {binding["id"]: binding for binding in data["bindings"]}

    daily = binding_by_id["knowledge_daily_command"]
    assert daily["route"] == "/command-center"
    assert daily["skill_id"] == "wilq-daily-command"
    assert daily["knowledge_card_ids"] == ["card_goal_001_rules"]
    assert daily["metric_tiles"]["decyzje"] >= 1
    assert daily["evidence_ids"]

    ads = binding_by_id["knowledge_ads_daily_check"]
    assert ads["route"] == "/ads-doctor"
    assert ads["skill_id"] == "wilq-ads-doctor"
    assert "card_google_ads_search_playbook" in ads["knowledge_card_ids"]
    assert "google_ads_search_playbook" in ads["playbook_ids"]
    assert "ads_search_terms_v1" in ads["expert_rule_ids"]
    assert "search_terms" in ads["required_evidence"]
    assert ads["action_ids"]

    localo = binding_by_id["knowledge_localo_visibility_review"]
    assert localo["status"] == "blocked"
    assert "local_ranking_rows" in localo["missing_contracts"]
    assert "card_localo_local_seo_playbook" in localo["knowledge_card_ids"]


def test_workflows_are_decision_backed_operator_contracts() -> None:
    response = client.get("/api/workflows")
    assert response.status_code == 200
    workflows = response.json()
    workflow_by_id = {workflow["id"]: workflow for workflow in workflows}

    daily_command = workflow_by_id["daily_command"]
    assert daily_command["label"] == "Plan dnia WILQ"
    assert daily_command["route"] == "/command-center"
    assert daily_command["route_label"] == "Plan dnia"
    assert daily_command["status_label"] in {"gotowe", "zablokowane"}
    assert daily_command["risk_label"] in {"niskie ryzyko", "średnie ryzyko"}
    assert daily_command["skill_id"] == "wilq-daily-command"
    assert daily_command["metric_tiles"]["decyzje"] >= 1
    assert daily_command["source_connectors"]
    assert daily_command["evidence_ids"]

    ads_daily = workflow_by_id["ads_daily_check"]
    assert ads_daily["label"] == "Ocena Ads"
    assert ads_daily["route"] == "/ads-doctor"
    assert ads_daily["route_label"] == "Ads"
    assert ads_daily["status_label"] in {"gotowe", "zablokowane"}
    assert ads_daily["skill_id"] == "wilq-ads-doctor"
    assert "kampanie" in ads_daily["metric_tiles"]
    assert any(value >= 1 for value in ads_daily["metric_tiles"].values())
    assert "act_prepare_ads_campaign_review_queue" in ads_daily["action_ids"]

    localo = workflow_by_id["localo_visibility_review"]
    assert localo["label"] == "Widoczność lokalna Localo"
    assert localo["status"] == "blocked"
    assert localo["status_label"] == "zablokowane"
    assert localo["route"] == "/localo"
    assert localo["route_label"] == "Localo"
    assert "local_ranking_rows" in localo["missing_contracts"]

    serialized = json.dumps(workflows, ensure_ascii=False)
    assert "Workflow definition runs against WILQ API" not in serialized
    assert "Fetch WILQ API context" not in serialized
    assert "Ads daily check" not in serialized
    assert "Merchant feed review" not in serialized
    assert "GSC content doctor" not in serialized
    assert "Localo visibility review" not in serialized
    assert "workflow jako" not in serialized
    assert "ocena zwrotu z reklam" not in serialized
    assert "wzrost konwersji" not in serialized
    assert "local ranking " + "up" + "lift" not in serialized
    assert "GBP performance verdict" not in serialized


def test_workflow_run_persists_to_local_state_with_redaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "workflow_state.sqlite3"))
    response = client.post(
        "/api/workflows/daily_command/runs",
        json={
            "id": "run_daily_command_contract",
            "input": {
                "connector_ids": ["google_ads"],
                "parameters": {
                    "api_key": "sk-workflowsecretvalue1234567890",  # pragma: allowlist secret
                },
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "run_daily_command_contract"
    assert data["status"] == "queued"
    assert data["input"]["parameters"]["api_key"] == "[REDACTED]"

    detail_response = client.get("/api/workflow-runs/run_daily_command_contract")
    assert detail_response.status_code == 200
    assert detail_response.json()["input"]["parameters"]["api_key"] == "[REDACTED]"

    list_response = client.get("/api/workflow-runs")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == ["run_daily_command_contract"]


def test_system_status_reports_local_state_without_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "status_state.sqlite3"))
    response = client.get("/api/system/status")
    assert response.status_code == 200
    local_state = response.json()["local_state"]
    assert local_state["backend"] == "sqlite"
    assert "path" not in local_state
