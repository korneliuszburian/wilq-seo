from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

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
from wilq.actions.service import apply_action
from wilq.briefing.ads_diagnostics import (
    _custom_segment_review_reason,
    _custom_segment_source_quality,
)
from wilq.connectors.ahrefs.client import refresh_ahrefs_domain_rating
from wilq.connectors.google_ads.client import refresh_google_ads_campaign_summary
from wilq.connectors.google_analytics_4.client import refresh_ga4_behavior_summary
from wilq.connectors.google_auth import GOOGLE_CREDENTIAL_ENV_NAMES
from wilq.connectors.google_merchant_center.client import (
    refresh_merchant_product_status_summary,
)
from wilq.connectors.google_search_console.client import refresh_search_console_site_summary
from wilq.connectors.google_sheets.client import refresh_google_sheets_review_surface
from wilq.connectors.localo.client import refresh_localo_visibility_summary
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
    FreshnessState,
    MarketingBrief,
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
        summary="Localo MCP read completed with aggregate facts.",
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
                    "blocked_claim:recommendation apply",
                ],
            },
            "operations": ["custom_segment_candidate"],
            "supported_actions": ["custom_segment_candidate"],
            "required_validation": ["google_ads_rmf_compliance_review"],
            "preview_contract": "custom_segment_payload_preview_v1",
            "custom_segment_preview_id": "preview_ads_custom_segment_23848569273",
            "operation_type": "custom_segment_targeting_review",
            "recommended_actions": ["prepare_custom_segment_review"],
            "source_metric_names": ["search_term_clicks"],
            "available_read_contracts": ["ga4_landing_source_campaign_quality"],
            "missing_read_contracts": [
                "demand_gen_landing_quality_by_campaign",
                "demand_gen_migration_constraints",
            ],
            "omitted_contracts": [
                "keyword_match_context_read_contract",
                "search_term_safety_read_contract",
            ],
            "blocked_claims": ["Demand Gen launch recommendation"],
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
        "blocked_claim:recommendation apply",
    ]
    assert redacted["operations"] == ["custom_segment_candidate"]
    assert redacted["supported_actions"] == ["custom_segment_candidate"]
    assert redacted["required_validation"] == ["google_ads_rmf_compliance_review"]
    assert redacted["preview_contract"] == "custom_segment_payload_preview_v1"
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
        "demand_gen_migration_constraints",
    ]
    assert redacted["omitted_contracts"] == [
        "keyword_match_context_read_contract",
        "search_term_safety_read_contract",
    ]
    assert redacted["blocked_claims"] == ["Demand Gen launch recommendation"]
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
                "demand_gen_migration_constraints."
            )
        }
    )["summary"] == (
        "Nadal brakujące kontrakty: "
        "demand_gen_landing_quality_by_campaign, "
        "demand_gen_migration_constraints."
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
    serialized = json.dumps(body)
    assert body["mutation_audit"]["status"] == "blocked"
    assert body["mutation_audit"]["mutation_attempted"] is False
    assert body["mutation_audit"]["mutation_adapter"] is None
    assert "Explicit apply confirmation is required" in serialized
    assert "validated before apply" in serialized
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
    assert "Explicit apply confirmation is required" in json.dumps(
        review_gate["last_mutation_blockers"]
    )


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
    assert "confirmed_by is required" in json.dumps(body)
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
    assert "Action mode must be apply" in json.dumps(body)


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
    assert action.review_gate.apply_allowed is False
    assert "Vendor mutation adapter is not implemented" in json.dumps(
        result.model_dump(mode="json")
    )


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
    assert review_payload["audit_event"]["event_type"] == "human_review_approved_for_prepare"
    assert review_payload["audit_event"]["actor"] == "operator_test"
    assert review_payload["review_gate"]["last_review_outcome"] == "approved_for_prepare"
    assert review_payload["review_gate"]["apply_allowed"] is False
    assert "mutacji vendorów" in review_payload["audit_event"]["summary"]

    audit_response = client.get(
        "/api/audit/events?action_id=act_review_merchant_feed_issues"
    )
    assert audit_response.status_code == 200
    audit_events = audit_response.json()
    assert audit_events[0]["event_type"] == "human_review_approved_for_prepare"

    action_response = client.get("/api/actions/act_review_merchant_feed_issues")
    assert action_response.status_code == 200
    action = action_response.json()
    assert action["audit_events"][0]["event_type"] == "human_review_approved_for_prepare"
    assert action["review_gate"]["last_review_outcome"] == "approved_for_prepare"
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
    assert preview["dry_run"] is True
    assert preview["mutation_allowed"] is False
    assert preview["audit_event"]["event_type"] == "action_preview_generated"
    assert preview["audit_event"]["actor"] == "operator_test"
    assert preview["preview_items_total"] >= len(preview["preview_items"])
    assert len(preview["preview_items"]) <= 3
    assert preview["review_gate"]["apply_allowed"] is False
    assert "mutation_allowed=false" in preview["audit_event"]["summary"]

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
        assert "ranking guarantee" in item["blocked_claims"]
    assert "action_mode_prepare_only" in preview["blockers"]


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
    assert previews[0]["apply_allowed"] is False
    assert previews[0]["api_mutation_ready"] is False
    assert "ranking guarantee" in previews[0]["blocked_claims"]


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
        item for item in previews if item.get("target_url") == homepage
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
            ],
            "blockers": [
                "payload_apply_allowed_false",
                "wordpress_write_not_requested",
                "blocked_claim:ranking guarantee",
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
    assert "Ten zapis nie wykonuje apply" in result["audit_event"]["summary"]

    audit_response = client.get(
        "/api/audit/events?action_id=act_prepare_content_refresh_queue"
    )
    assert audit_response.status_code == 200
    persisted_audit = audit_response.json()[0]
    assert persisted_audit["event_type"] == "human_review_approved_for_prepare"
    assert f"candidate:{candidate_id}" in persisted_audit["summary"]

    reviewed_action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert reviewed_action_response.status_code == 200
    reviewed_action = reviewed_action_response.json()
    draft_previews = reviewed_action["payload"]["wordpress_draft_payload_preview"]
    assert len(draft_previews) == 1
    draft_preview = draft_previews[0]
    assert draft_preview["preview_contract"] == "wordpress_draft_payload_preview_v1"
    assert draft_preview["source_preview_contract"] == "content_brief_preview_v1"
    assert draft_preview["candidate_id"] == candidate_id
    assert draft_preview["post_status"] == "draft"
    assert draft_preview["mutation_allowed"] is False
    assert draft_preview["apply_allowed"] is False
    assert draft_preview["api_mutation_ready"] is False
    assert draft_preview["destructive"] is False
    assert draft_preview["draft_payload"]["post_status"] == "draft"
    assert draft_preview["draft_payload"]["post_title"]
    assert "human_confirm_before_wordpress_write" in draft_preview[
        "required_validation"
    ]
    assert "ranking guarantee" in draft_preview["blocked_claims"]
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
            "notes": f"Wybrano kandydata briefu {candidate_id} do context-pack proof.",
            "checked_items": [
                f"candidate:{candidate_id}",
                f"source_type:{candidate['source_type']}",
                f"mode:{candidate['mode']}",
            ],
            "blockers": [
                "payload_apply_allowed_false",
                "wordpress_write_not_requested",
                "blocked_claim:ranking guarantee",
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

    assert payload["wordpress_draft_payload_preview_total"] == 1
    assert payload["wordpress_draft_payload_preview_included"] == 1
    draft_preview = payload["wordpress_draft_payload_preview"][0]
    assert draft_preview["preview_contract"] == "wordpress_draft_payload_preview_v1"
    assert draft_preview["source_preview_contract"] == "content_brief_preview_v1"
    assert draft_preview["candidate_id"] == candidate_id
    assert draft_preview["post_status"] == "draft"
    assert draft_preview["apply_allowed"] is False
    assert draft_preview["api_mutation_ready"] is False
    assert draft_preview["evidence_ids"]
    assert "ranking guarantee" in draft_preview["blocked_claims"]
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
    assert "mutation_allowed=false" in latest_audit_event["summary"]
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
    assert "dry_run_preview_required" in confirmation["blockers"]
    assert confirmation["audit_event"]["event_type"] == "action_confirmation_blocked"
    assert confirmation["review_gate"]["apply_allowed"] is False

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
    assert result["audit_event"]["event_type"] == "action_impact_check_blocked"
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
    assert result["pre_window_days"] == 7
    assert result["post_window_days"] == 14
    assert result["metric_fact_count"] > 0
    assert "google_merchant_center" in result["source_connectors"]
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
            "notes": "Brakuje payload preview do realnego apply.",
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
    assert "Brakuje payload preview" in serialized


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
    assert "Action mode must be apply" in json.dumps(apply_response.json())


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
    assert "profitability verdict" in strategy_readiness["blocked_claims"]
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
    assert "target verdict zostaje zablokowany" in business_context_contract["next_step"]

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
        "review gates": 5,
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
    assert action["title"] == "Potwierdź target ROAS albo CPA dla Ads"
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
            "notes": "Potwierdzam roboczy target ROAS 4.2 do review kampanii.",
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
            "notes": "Strategia Ads zatwierdzona do dalszego review bez apply.",
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
    assert "audience size" in action["payload"]["blocked_claims"]
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
        assert action["evidence_ids"]
        if action_id.startswith("act_prepare_") and "social_drafts" in action_id:
            assert action["domain"] == "social"
            assert action["payload"]["candidate_inputs"]
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
            assert "ranking guarantee" in gsc_preview["blocked_claims"]
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
        assert "Action mode must be apply" in json.dumps(apply_response.json())


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
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
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
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
        primary_next_step="Przejrzyj decyzje.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
        items=[],
    )

    def fail_list_actions() -> list[ActionObject]:
        raise AssertionError("Command Center first-screen path must not build full actions")

    monkeypatch.setattr(daily_runtime, "list_actions", fail_list_actions)
    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [])
    monkeypatch.setattr(daily_runtime, "build_tactical_queue", lambda: tactical_queue)
    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        lambda connectors=None, tactical_queue=None, actions=None: command,
    )

    assert daily_runtime.build_daily_command_center(use_cache=False) == command


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

    def fake_build() -> TacticalQueueResponse:
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
    assert all(
        item["kind"] in {"metric", "blocker", "action", "recommendation"}
        for section in sections.values()
        for item in section["items"]
    )


def test_marketing_brief_exposes_metric_backed_prepare_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/marketing/brief")
    assert response.status_code == 200
    brief = response.json()
    metric_items = {
        item["source_connectors"][0]: item
        for section in brief["sections"]
        if section["id"] == "what_we_know"
        for item in section["items"]
        if item["source_connectors"]
    }
    for connector_id in (
        "google_merchant_center",
        "google_analytics_4",
        "google_search_console",
    ):
        item = metric_items[connector_id]
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
    assert payload["landing_group_count"] >= 1
    assert payload["low_engagement_count"] >= 1
    assert payload["wordpress_match_count"] >= 1
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
    assert all(isinstance(decision["priority"], int) for decision in decision_by_id.values())
    assert all(decision["metric_tiles"] for decision in decision_by_id.values())
    assert any("engagement" in decision["metric_tiles"] for decision in decision_by_id.values())
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
    assert operator_summary["wordpress_missing_count"] == sum(
        1
        for decision in payload["decision_queue"]
        if decision.get("wordpress_match") == "missing"
    )
    assert operator_summary["action_ids"] == payload["action_ids"]
    assert operator_summary["conversion_readiness_status"] == readiness_contract["status"]
    assert "ROAS" in operator_summary["blocked_claims"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    sections = {section["id"]: section for section in payload["sections"]}
    assert sections["ga4_landing_behavior"]["status"] == "ready"
    assert sections["ga4_landing_behavior"]["tactical_items"]
    assert sections["ga4_landing_behavior"]["tactical_items"][0]["dimensions"][
        "landing_page"
    ] == "/europejski-zielony-lad-co-to-takiego/"
    assert sections["ga4_tracking_readiness"]["status"] == "missing"
    assert "conversion drop" in sections["ga4_tracking_readiness"]["blocked_claims"]
    assert sections["ga4_action_safety"]["status"] == "ready"
    assert readiness_contract["id"] == "ga4_conversion_readiness_contract"
    assert readiness_contract["status"] == "blocked"
    assert readiness_contract["conversion_like_metric_count"] == 0
    assert readiness_contract["dimensioned_behavior_metric_count"] >= 1
    assert readiness_contract["landing_group_count"] >= 1
    assert readiness_contract["missing_read_contracts"] == [
        "conversion_or_key_event_mapping"
    ]
    assert {
        "conversions",
        "key_events",
        "purchase_revenue",
        "total_revenue",
        "transactions",
    }.issubset(set(readiness_contract["allowed_metrics"]))
    assert "conversion rate" in readiness_contract["blocked_claims"]
    assert "act_review_ga4_tracking_quality" in readiness_contract["action_ids"]
    assert readiness_contract["evidence_ids"]
    assert payload["blocker_count"] >= 1

    action_response = client.get("/api/actions/act_review_ga4_tracking_quality")
    assert action_response.status_code == 200
    ga4_action = action_response.json()
    assert ga4_action["payload"]["preview_contract"] == "ga4_tracking_quality_review_v1"
    preview = ga4_action["payload"]["payload_preview"][0]
    assert preview["preview_contract"] == "ga4_tracking_quality_review_v1"
    assert preview["operation_type"] == "tracking_quality_review"
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
    assert context_preview["apply_allowed"] is False
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "google_adc.json" not in serialized


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
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["query/page"] >= 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["decyzje"] >= 2
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["Ahrefs review"] == 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["luki Ahrefs"] == 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["wyświetlenia"] >= 1
    assert "act_prepare_content_refresh_queue" in brief_by_id["daily_content_queue"]["action_ids"]
    assert brief_by_id["daily_ga4_landing_quality"]["status"] == "blocked"
    assert "pomiar i jakość ruchu" in brief_by_id["daily_ga4_landing_quality"]["title"]
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["grupy ruchu"] >= 1
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["decyzje"] >= 1
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["braki kontraktu"] == 1
    assert "ROAS" in brief_by_id["daily_ga4_landing_quality"]["blocked_claims"]
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
    assert "decyzji GA4 do review" in plan_by_id[
        "plan_review_ga4_landing_quality"
    ]["why_it_matters"]
    assert "review-only" in plan_by_id[
        "plan_review_ga4_landing_quality"
    ]["operator_action"]
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["status"] == "blocked"
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["skill_id"] == (
        "wilq-ads-doctor"
    )
    assert "spend" in plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["blocked_claims"]
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
    assert merchant_decision["co_widzimy"].startswith("Merchant Center ma")
    assert merchant_decision["metric_tiles"]["produkty"] == 10900
    assert merchant_decision["metric_tiles"]["zgłoszenia"] == 3
    assert merchant_decision["metric_tiles"]["decyzje"] >= 1
    assert "status=ready" not in merchant_decision["co_widzimy"]
    for decision in decisions_by_id.values():
        assert "Źródła=" not in decision["co_widzimy"]
        assert "dowody=" not in decision["co_widzimy"]
        assert "akcje=" not in decision["co_widzimy"]
    assert merchant_decision["dlaczego_to_ma_znaczenie"] == plan_by_id[
        "plan_review_merchant_feed_issues"
    ]["why_it_matters"]
    assert merchant_decision["bezpieczny_next_step"] == plan_by_id[
        "plan_review_merchant_feed_issues"
    ]["operator_action"]
    assert merchant_decision["skill_id"] == "wilq-merchant-feed-operator"
    assert "Użyj skilla wilq-merchant-feed-operator" in merchant_decision["codex_prompt"]
    assert merchant_decision["evidence_ids"]
    assert merchant_decision["blocked_claims"]
    ga4_decision = decisions_by_id["decision_review_ga4_landing_quality"]
    assert ga4_decision["status"] == "blocked"
    assert "pomiar i jakość ruchu" in ga4_decision["title"]
    assert ga4_decision["metric_tiles"]["grupy ruchu"] >= 1
    assert ga4_decision["metric_tiles"]["decyzje"] >= 1
    assert "grup landing/source/campaign" in ga4_decision["co_widzimy"]
    assert "Status blocked oznacza" in ga4_decision["co_widzimy"]
    assert ga4_decision["co_widzimy"].count("Status blocked oznacza") == 1

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    context_command = context_response.json()["command_center"]
    assert context_command["operator_brief"] == payload["operator_brief"]
    assert context_command["demo_script"] == []
    assert [
        {
            "id": item["id"],
            "route": item["route"],
            "status": item["status"],
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
            "route": item["route"],
            "status": item["status"],
            "source_connectors": item["source_connectors"],
            "evidence_ids": item["evidence_ids"],
            "action_ids": item["action_ids"],
            "blocked_claims": item["blocked_claims"],
            "skill_id": item["skill_id"],
        }
        for item in payload["daily_decisions"]
    ]
    context_plan_by_id = {item["id"]: item for item in context_command["action_plan"]}
    assert set(context_plan_by_id) == set(plan_by_id)
    for item_id, item in plan_by_id.items():
        context_item = context_plan_by_id[item_id]
        assert context_item["route"] == item["route"]
        assert context_item["status"] == item["status"]
        assert context_item["skill_id"] == item["skill_id"]
        assert context_item["codex_prompt"] == item["codex_prompt"]
        assert context_item["evidence_ids"] == item["evidence_ids"]
        assert context_item["action_ids"] == item["action_ids"]
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
    assert ads_item["metric_tiles"]["wartość konw."] == "150 PLN"
    assert ads_item["metric_tiles"]["podgląd budżetu"] == 1
    assert ads_item["metric_tiles"]["rekomendacje"] == 1
    assert "kolejki tylko do oceny" in ads_item["summary"]
    assert "kliknięcia=12" in ads_item["summary"]
    assert "koszt=12 PLN" in ads_item["summary"]
    assert "konwersje=1" in ads_item["summary"]
    assert "apply" in ads_item["next_step"]
    assert "budget apply" in ads_item["blocked_claims"]
    assert "negative keyword candidates" not in ads_item["blocked_claims"]
    assert "act_prepare_ads_campaign_review_queue" in ads_item["action_ids"]
    assert "act_prepare_google_ads_recommendation_review_queue" in ads_item["action_ids"]
    ads_business_item = brief_by_id["daily_ads_business_context"]
    assert ads_business_item["status"] == "blocked"
    assert ads_business_item["priority"] == 18
    assert "kontekstu biznesowego" in ads_business_item["title"]
    assert ads_business_item["metric_tiles"]["braki"] == 5
    assert ads_business_item["metric_tiles"]["marża"] == "brak"
    assert ads_business_item["metric_tiles"]["cel biznesowy"] == "brak"
    assert "profitability" in ads_business_item["blocked_claims"]
    assert "wasted budget" in ads_business_item["blocked_claims"]
    assert ads_business_item["action_ids"] == [ADS_BUSINESS_CONTEXT_ACTION_ID]

    plan_by_id = {item["id"]: item for item in payload["action_plan"]}
    ads_plan = plan_by_id["plan_review_ads_campaign_metrics"]
    assert ads_plan["status"] == "ready"
    assert ads_plan["title"] == "Przejrzyj aktualny odczyt Ads bez apply"
    assert "kliknięcia=12" in ads_plan["why_it_matters"]
    assert "koszt=12 PLN" in ads_plan["why_it_matters"]
    assert "konwersje=1" in ads_plan["why_it_matters"]
    assert "wartość konw.=150 PLN" in ads_plan["why_it_matters"]
    assert "aktualny odczyt" in ads_plan["operator_action"]
    assert "podgląd budżetów" in ads_plan["operator_action"]
    assert "nie wdrażaj zmian" in ads_plan["operator_action"]
    assert "Użyj skilla wilq-ads-doctor" in ads_plan["codex_prompt"]
    assert "zablokowanymi claimami" in ads_plan["expected_codex_output"]
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
    assert "podgląd budżetu=1" in ads_decision["co_widzimy"]
    assert "read-only kolejki" in ads_decision["co_widzimy"]
    assert ads_decision["blocked_claims"] == ads_item["blocked_claims"]
    assert "decision_ads_business_context_before_budget_decisions" not in decisions_by_id

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
    assert ads_item["metric_tiles"]["wartość konw."] == "2 PLN"
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
        lambda: empty_tactical_queue,
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
        lambda: TacticalQueueResponse(strict_instruction="empty tactical queue"),
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
        summary="Localo MCP initialize completed with local OAuth access token.",
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
    assert localo_brief["metric_tiles"]["MCP access"] == 0


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
        summary="Localo MCP initialize completed with local OAuth access token.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().save_connector_refresh_metrics(localo_run)

    response = client.get("/api/localo/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["access_probe"]["status"] == "access_ready"
    assert payload["access_probe"]["mcp_initialize_status"] == 200
    assert payload["live_data_available"] is False
    assert payload["visibility_fact_count"] == 0
    assert payload["evidence_ids"] == ["ev_refresh_refresh_localo_access_ready_diag_test"]
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    access_decision = decision_by_id["localo_access_ready_wait_for_visibility_facts"]
    assert access_decision["status"] == "ready"
    assert access_decision["priority"] == 30
    assert access_decision["metric_tiles"] == {
        "dostęp MCP": 1,
        "fakty Localo": 0,
        "braki kontraktu": 5,
    }
    assert "local_rankings" in access_decision["missing_read_contracts"]
    assert "GBP performance" in access_decision["blocked_claims"]
    block_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert block_decision["status"] == "blocked"
    assert block_decision["priority"] == 10
    assert block_decision["metric_tiles"] == {
        "blokady claimów": 5,
        "braki kontraktu": 5,
    }
    assert "local visibility uplift" in block_decision["blocked_claims"]
    assert all(fact["name"] != "mcp_initialize_status" for fact in block_decision["metric_facts"])
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "localo_operator_summary"
    assert operator_summary["title"] == "Co marketer ma wiedzieć o Localo"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["access_status"] == "access_ready"
    assert operator_summary["visibility_fact_count"] == 0
    assert "local_rankings" in operator_summary["missing_read_contracts"]
    assert "localo" in operator_summary["source_connectors"]
    assert "ev_refresh_refresh_localo_access_ready_diag_test" in operator_summary["evidence_ids"]
    assert "GBP performance" in operator_summary["blocked_claims"]
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
        summary="Localo MCP read completed with aggregate facts.",
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
            errors=["Localo MCP OAuth authorization is incomplete."],
            summary="Later Localo MCP probe failed after a successful aggregate read.",
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
    assert review_decision["metric_tiles"]["miejsca"] == 4
    assert review_decision["metric_tiles"]["frazy"] == 23
    assert review_decision["metric_tiles"]["średnia widoczność"] == 52.8261
    assert review_decision["metric_tiles"]["recenzje"] == 793
    assert "local ranking" not in review_decision["blocked_claims"]
    assert "GBP performance" in review_decision["blocked_claims"]
    assert "competitor visibility" in review_decision["blocked_claims"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["visibility_fact_count"] == 4
    assert "agregaty widoczności" in operator_summary["summary"]
    assert "Przejrzyj agregaty Localo" in operator_summary["next_step"]
    assert "dopóki Localo read contract nie dostarczy visibility facts" not in (
        operator_summary["next_step"]
    )
    blocked_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert blocked_decision["metric_tiles"]["braki kontraktu"] == 3
    assert blocked_decision["title"] == (
        "Blokuj GBP, konkurencję i local tasks bez pełnych kontraktów Localo"
    )
    assert "bez Localo facts" not in blocked_decision["title"]
    assert "Przejrzyj dostępne agregaty Localo" in blocked_decision["next_step"]
    assert "Najpierw dodaj typed Localo read contract" not in blocked_decision["next_step"]
    section_by_id = {section["id"]: section for section in payload["sections"]}
    assert section_by_id["localo_visibility_contract"]["action_ids"] == [
        LOCALO_VISIBILITY_REVIEW_ACTION_ID
    ]
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
    assert "GBP performance" in localo_plan["blocked_claims"]

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
        "dostęp MCP": 0,
        "braki kontraktu": 6,
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
    assert payload["authority_fact_count"] == 2
    assert payload["gap_fact_count"] == 0
    assert payload["blocker_count"] == 1
    gap_contract = payload["gap_read_contract"]
    assert gap_contract["status"] == "blocked"
    assert gap_contract["gap_records"] == []
    assert gap_contract["available_read_contracts"] == ["ahrefs_authority_summary"]
    assert "ahrefs_content_gap_records" in gap_contract["missing_read_contracts"]
    assert "content gap" in gap_contract["blocked_claims"]
    assert gap_contract["operator_review_gates"] == [
        "ahrefs_gap_records_required",
        "content_planner_review_required",
        "human_strategy_review",
    ]
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    authority_decision = decision_by_id["ahrefs_review_authority_context"]
    assert authority_decision["status"] == "ready"
    assert authority_decision["metric_tiles"]["DR"] == 90
    assert authority_decision["metric_tiles"]["Ahrefs Rank"] == 1450
    assert authority_decision["metric_tiles"]["konkurenci organiczni"] == 0
    assert authority_decision["metric_tiles"]["odczyt konkurencji"] == "completed"
    assert authority_decision["metric_tiles"]["tryb konkurencji"] == "subdomains"
    assert authority_decision["metric_tiles"]["fakty luk"] == 0
    assert "organic_competitor_rows" in authority_decision["allowed_evidence"]
    assert "organic_competitor_mode" in authority_decision["allowed_evidence"]
    assert "rows=0" in authority_decision["summary"]
    assert "ahrefs_content_gap_records" in authority_decision["missing_read_contracts"]
    assert "content gap" in authority_decision["blocked_claims"]
    block_decision = decision_by_id["ahrefs_block_gap_claims_without_records"]
    assert block_decision["status"] == "blocked"
    assert block_decision["metric_tiles"]["braki kontraktu"] == 5
    assert block_decision["evidence_ids"] == ["ev_refresh_refresh_ahrefs_diag_test"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "ahrefs_operator_summary"
    assert operator_summary["title"] == "Co marketer ma wiedzieć o Ahrefs"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["gap_read_status"] == "blocked"
    assert operator_summary["authority_fact_count"] == 2
    assert operator_summary["gap_fact_count"] == 0
    assert "ahrefs_authority_summary" in operator_summary["available_read_contracts"]
    assert "ahrefs_content_gap_records" in operator_summary["missing_read_contracts"]
    assert "ahrefs" in operator_summary["source_connectors"]
    assert "ev_refresh_refresh_ahrefs_diag_test" in operator_summary["evidence_ids"]
    assert "content gap" in operator_summary["blocked_claims"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    assert all(fact["source_connector"] == "ahrefs" for fact in authority_decision["metric_facts"])
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "ahrefs-token-test" not in serialized

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["ahrefs_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
    assert context_payload["ahrefs_diagnostics"]["gap_read_contract"] == gap_contract
    assert context_payload["ahrefs_diagnostics"]["decision_queue"][0]["id"] in decision_by_id
    assert context_payload["active_action_objects"] == []
    assert "marketing_brief" not in context_payload
    assert "content_diagnostics" not in context_payload


def test_ahrefs_diagnostics_builds_typed_gap_records_from_metric_facts(
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
    assert payload["gap_fact_count"] == 9
    assert payload["blocker_count"] == 0
    gap_contract = payload["gap_read_contract"]
    assert gap_contract["status"] == "ready"
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
    content_record = next(
        record
        for record in gap_contract["gap_records"]
        if record["gap_type"] == "content_gap"
    )
    assert content_record["keyword"] == "bdo szkolenie"
    assert content_record["competitor_domain"] == "example.pl"
    assert "content_gaps=2" in content_record["summary"]
    assert "traffic uplift" in content_record["blocked_claims"]

    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    gap_decision = decision_by_id["ahrefs_review_gap_records"]
    assert gap_decision["status"] == "ready"
    assert gap_decision["metric_tiles"] == {
        "rekordy luk": 5,
        "content gaps": 1,
        "backlink gaps": 1,
        "strony konkurencji": 1,
        "organic keywords": 1,
        "top pages": 1,
        "braki kontraktu": 0,
    }
    assert gap_decision["missing_read_contracts"] == []
    assert "traffic uplift" in gap_decision["blocked_claims"]
    assert "ahrefs_block_gap_claims_without_records" not in decision_by_id
    operator_summary = payload["operator_summary"]
    assert operator_summary["gap_read_status"] == "ready"
    assert "rekordami luk Ahrefs" in operator_summary["next_step"]
    assert "bez rekordów" not in operator_summary["next_step"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["ahrefs_diagnostics"]["gap_read_contract"] == gap_contract
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


def test_marketing_tactical_queue_uses_wordpress_host_alias_sitemap_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "host_alias.duckdb"))
    gsc_run = ConnectorRefreshRun(
        id="refresh_google_search_console_host_alias_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_search_console_host_alias_test"],
        metric_summary={"clicks": 8, "impressions": 220},
        summary="GSC host alias test seed.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_host_alias_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_wordpress_ekologus_host_alias_test"],
        metric_summary={"content_object_count": 1, "sitemap_url_count": 1},
        summary="WordPress host alias sitemap seed.",
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
    assert item["dimensions"]["wordpress_match"] == "found"
    assert item["dimensions"]["wordpress_match_confidence"] == "host_alias_sitemap"
    assert item["dimensions"]["wordpress_content_host"] == "ekologus.dev.proudsite.pl"
    assert item["dimensions"]["wordpress_host_alias_applied"] == "true"
    assert item["dimensions"]["wordpress_inventory_source"] == "sitemap"
    assert "wordpress_ekologus" in item["source_connectors"]
    assert "ev_refresh_refresh_wordpress_ekologus_host_alias_test" in item["evidence_ids"]


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
        "act_review_demand_gen_readiness",
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
        SEARCH_TERM_NGRAM_ACTION_ID,
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
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
    assert content["action_ids"] == []
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
            summary="Google Ads vendor read completed through test adapter.",
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


def test_ads_change_history_blocks_empty_read_attempt(
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
                "Google Ads vendor read completed with campaign rows and without "
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
    assert change_history_contract["status"] == "blocked"
    assert change_history_contract["change_history_rows"] == []
    assert "change_event_rows" in change_history_contract["missing_read_contracts"]
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
    assert "change impact" in change_impact_contract["blocked_claims"]
    decisions_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    change_history_decision = decisions_by_id["ads_review_change_history"]
    assert change_history_decision["status"] == "blocked"
    assert change_history_decision["metric_tiles"] == {"zmiany": 0, "kampanie": 0}
    assert "change_event_rows" in change_history_decision["missing_read_contracts"]
    assert change_history_decision["action_ids"] == []
    assert "impact review zablokowany" in change_history_decision["next_step"]
    optimizer_contract = payload["optimizer_readiness_contract"]
    assert optimizer_contract["id"] == "ads_optimizer_readiness_contract"
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["api_mutation_ready"] is False
    assert optimizer_contract["apply_allowed"] is False
    assert optimizer_contract["ready_area_count"] == 2
    assert optimizer_contract["blocked_area_count"] >= 1
    assert "change_event_rows" in optimizer_contract["missing_read_contracts"]
    assert "change impact" in optimizer_contract["blocked_claims"]
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
            summary="Google Ads vendor read completed with shared budget rows.",
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
                "budget scaling",
                "budget apply",
                "campaign pause",
                "wasted budget",
                "profitability",
                "CPA verdict",
                "ROAS verdict",
                "recommendation apply",
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
            summary="Google Ads vendor read completed through stale test adapter.",
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
    assert handoff["title"] == "Google Ads: finalny handoff blockera OAuth"
    assert "oauth_error=deleted_client" in handoff["summary"]
    assert "act_configure_google_ads_env" in handoff["action_ids"]
    assert "google_ads" in handoff["source_connectors"]
    assert "ROAS" in handoff["blocked_claims"]
    assert any("nie zmyśla Ads metryk" in claim for claim in handoff["allowed_demo_claims"])
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
            summary="Google Ads vendor read completed through googleAds:searchStream. Rows: 1.",
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
    assert "ROAS" in read_contract["blocked_claims"]
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
            "blocked_claims": ["CPA", "ROAS", "search-term waste", "wasted budget"],
            "target_status": "no_target",
            "target_status_label": "brak targetu",
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
        }
    ]
    assert "Kolejność review kampanii" in read_contract["campaign_rows"][0]["review_reason"]
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
    assert "ROAS" in operator_summary["blocked_claims"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    currency_contract = payload["account_currency_read_contract"]
    assert currency_contract["status"] == "ready"
    assert currency_contract["currency_code"] == "PLN"
    assert currency_contract["allowed_metrics"] == ["account_currency_code"]
    assert currency_contract["missing_read_contracts"] == []
    assert "budget apply" in currency_contract["blocked_claims"]
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
    assert business_context_contract["target_interpretation"]["action_ids"] == [
        ADS_BUSINESS_CONTEXT_ACTION_ID
    ]
    assert business_context_contract["target_interpretation"]["apply_allowed"] is False
    assert "budget scaling" in business_context_contract["blocked_claims"]
    assert business_context_contract["metric_tiles"]["marża"] == "brak"
    business_context_section = next(
        section for section in payload["sections"] if section["id"] == "ads_business_context"
    )
    assert business_context_section["status"] == "blocked"
    assert business_context_section["action_ids"] == [ADS_BUSINESS_CONTEXT_ACTION_ID]
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
        "review gates": 5,
        "polityki": 3,
    }
    assert business_context_decision["operator_review_gates"] == (
        business_context_contract["operator_review_gates"]
    )
    assert business_context_decision["action_ids"] == [ADS_BUSINESS_CONTEXT_ACTION_ID]
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
    assert "profitability" in derived_kpi_contract["blocked_claims"]
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
            "target_status_label": "brak targetu",
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
                "profitability",
                "budget scaling",
                "wasted budget",
                "recommendation apply",
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
    assert "budget scaling" in budget_contract["blocked_claims"]
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
                "budget scaling",
                "budget apply",
                "campaign pause",
                "wasted budget",
                "profitability",
                "CPA verdict",
                "ROAS verdict",
                "recommendation apply",
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
                "budget scaling",
                "budget apply",
                "campaign pause",
                "wasted budget",
                "profitability",
                "CPA verdict",
                "ROAS verdict",
                "recommendation apply",
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
    assert "recommendation apply" in recommendations_contract["blocked_claims"]
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
                "potwierdź człowiekiem przed apply",
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
                "recommendation apply",
                "automatic recommendation accept",
                "budget apply",
                "campaign mutation",
            ],
        }
    ]
    assert "kolejność review rekomendacji" in recommendations_contract[
        "recommendation_rows"
    ][0]["review_reason"]
    assert "nie zgoda na apply" in recommendations_contract["recommendation_rows"][0][
        "review_reason"
    ]
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
                "recommendation apply",
                "automatic recommendation accept",
                "budget apply",
                "campaign mutation",
                "performance uplift",
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
    assert "budget apply" in impression_share_contract["blocked_claims"]
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
                "budget scaling",
                "budget apply",
                "wasted budget",
                "performance uplift",
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
    assert campaign_triage_contract["title"] == "Kolejność review kampanii Ads"
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
    assert "wasted budget" in campaign_triage_contract["blocked_claims"]
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
            "target_status_label": "brak targetu",
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
                "wasted budget",
                "profitability",
                "budget scaling",
                "budget apply",
                "recommendation apply",
                "campaign mutation",
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
        }
    ]
    assert "Kolejność review kampanii" in campaign_triage_contract["triage_rows"][0][
        "review_reason"
    ]
    assert "nie jest werdyktem wasted budget" in campaign_triage_contract["summary"]
    optimizer_contract = payload["optimizer_readiness_contract"]
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["apply_allowed"] is False
    assert "campaign mutation" in optimizer_contract["blocked_claims"]
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
    assert "change impact" in change_history_contract["blocked_claims"]
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
                "change impact",
                "performance uplift",
                "budget apply",
                "campaign mutation",
            ],
        }
    ]
    change_impact_contract = payload["change_impact_readiness_contract"]
    assert change_impact_contract["id"] == "ads_change_impact_readiness_contract"
    assert change_impact_contract["status"] == "blocked"
    assert change_impact_contract["apply_allowed"] is False
    assert "snapshot kampanii" not in change_impact_contract["next_step"]
    assert "aktualny odczyt kampanii" in change_impact_contract["next_step"]
    assert "change impact" in change_impact_contract["blocked_claims"]
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
                "change impact",
                "performance uplift",
                "budget scaling",
                "budget apply",
                "campaign mutation",
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
    assert "negative keyword apply" in search_terms_contract["blocked_claims"]
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
            "blocked_claims": ["CPA", "ROAS", "negative keyword apply", "wasted budget"],
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
            "blocked_claims": ["CPA", "ROAS", "negative keyword apply", "wasted budget"],
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
                "search-term waste",
                "negative keyword apply",
                "CPA",
                "ROAS",
            ],
        }
    ]
    assert "search-term waste" in search_term_review_contract["blocked_claims"]
    assert "negative keyword apply" in search_term_review_contract["blocked_claims"]
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
        "ngram_to_negative_keyword_payload_preview",
    ]
    assert "negative_keyword_payload_preview" not in ngram_contract[
        "missing_read_contracts"
    ]
    assert ngram_contract["operator_review_gates"] == [
        "human_intent_review",
        "negative_keyword_action_validation",
    ]
    assert ngram_contract["action_ids"] == [SEARCH_TERM_NGRAM_ACTION_ID]
    assert "search-term waste" in ngram_contract["blocked_claims"]
    assert "negative keyword apply" in ngram_contract["blocked_claims"]
    assert ngram_contract["ngram_rows"]
    ngrams_by_name = {row["ngram"]: row for row in ngram_contract["ngram_rows"]}
    assert ngrams_by_name["bdo"]["source_search_term_count"] == 1
    assert ngrams_by_name["bdo"]["clicks"] == 4
    assert ngrams_by_name["bdo rejestracja"]["ngram_size"] == 2
    assert ngrams_by_name["odpady cena"]["cost_micros"] == 5000000
    assert all(row["evidence_ids"] for row in ngram_contract["ngram_rows"])
    assert all("search-term waste" in row["blocked_claims"] for row in ngram_contract["ngram_rows"])
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
    assert "ngram_to_negative_keyword_payload_preview" in ngram_decision[
        "missing_read_contracts"
    ]
    assert "negative_keyword_payload_preview" not in ngram_decision[
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
    assert "negative_keyword_payload_preview" not in search_term_safety_contract[
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
    assert "negative keyword apply" in search_term_safety_contract["blocked_claims"]
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
            "blocked_claims": ["CPA", "ROAS", "negative keyword apply", "wasted budget"],
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
    assert custom_segments_contract["title"] == "Custom segments z realnych search terms"
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
    assert "custom_segment_payload_preview" not in custom_segments_contract[
        "missing_read_contracts"
    ]
    assert "audience size" in custom_segments_contract["blocked_claims"]
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
    assert "audience size" in audience_forecast_contract["blocked_claims"]
    forecast_row = audience_forecast_contract["forecast_rows"][0]
    assert forecast_row["candidate_id"] == custom_segments_contract["candidates"][0]["id"]
    assert forecast_row["custom_segment_name"] == (
        custom_segments_contract["candidates"][0]["name"]
    )
    assert forecast_row["status"] == "missing_forecast"
    assert forecast_row["forecast_available"] is False
    assert forecast_row["audience_size"] is None
    assert forecast_row["source_terms"] == ["bdo rejestracja", "odpady cena"]
    assert "forecast albo audience size" in forecast_row["reason"]
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
    assert "kolejność review segmentu" in custom_segments_contract["candidates"][0][
        "review_reason"
    ]
    assert "nie dowód audience size" in custom_segments_contract["candidates"][0][
        "review_reason"
    ]
    assert custom_segments_contract["candidates"][0]["human_review_gates"] == [
        "sprawdź intencję source terms",
        "odrzuć brand, konkurencję i low-intent frazy",
        "sprawdź Keyword Planner enrichment",
        "sprawdź forecast albo audience size",
        "zatwierdź segment przed apply",
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
    assert negative_keywords_contract["title"] == "Review wykluczeń z search terms"
    assert negative_keywords_contract["action_ids"] == [
        "act_prepare_negative_keyword_review_queue"
    ]
    assert "90_day_safety_check" not in negative_keywords_contract["missing_read_contracts"]
    assert "negative_keyword_payload_preview" not in negative_keywords_contract[
        "missing_read_contracts"
    ]
    assert negative_keywords_contract["missing_read_contracts"] == []
    assert "negative keyword apply" in negative_keywords_contract["blocked_claims"]
    assert negative_keywords_contract["candidates"][0]["search_term"] == "odpady cena"
    assert negative_keywords_contract["candidates"][0]["review_priority"] == "wysokie"
    assert negative_keywords_contract["candidates"][0]["review_score"] == 53
    assert "kolejność review" in negative_keywords_contract["candidates"][0][
        "review_reason"
    ]
    assert "nie werdykt zmarnowanego budżetu" in negative_keywords_contract[
        "candidates"
    ][0]["review_reason"]
    assert negative_keywords_contract["candidates"][0]["human_review_gates"] == [
        "sprawdź intencję zapytania",
        "porównaj z istniejącymi keywords i match types",
        "sprawdź 90-dniowy safety read",
        "zatwierdź poziom wykluczenia przed apply",
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
        "koszt": "12.0",
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
    assert campaign_triage_decision["title"] == "Ustal kolejność review kampanii Ads"
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
    assert "wasted budget" in campaign_triage_decision["blocked_claims"]
    derived_kpi_decision = decisions_by_id["ads_review_derived_kpis"]
    assert derived_kpi_decision["status"] == "ready"
    assert derived_kpi_decision["priority"] == 25
    assert derived_kpi_decision["metric_tiles"] == {
        "kampanie": 1,
        "wiersze CPA": 1,
        "wiersze ROAS": 1,
    }
    assert derived_kpi_decision["decision_type"] == "review_derived_kpi"
    assert derived_kpi_decision["derived_kpi_rows"][0]["campaign_name"] == "Brand Search"
    assert derived_kpi_decision["derived_kpi_rows"][0]["roas"] == 37.5625
    assert derived_kpi_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert "profitability" in derived_kpi_decision["blocked_claims"]
    assert "budget_pacing" not in derived_kpi_decision["missing_read_contracts"]
    budget_decision = decisions_by_id["ads_review_budget_context"]
    assert budget_decision["status"] == "ready"
    assert budget_decision["priority"] == 30
    assert budget_decision["metric_tiles"] == {
        "budżety": 1,
        "podgląd budżetu": 1,
        "koszt 7 dni": "12.0",
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
    assert "budget apply" in budget_decision["blocked_claims"]
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
    assert "recommendation apply" in recommendations_decision["blocked_claims"]
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
    assert "budget apply" in impression_share_decision["blocked_claims"]
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
    assert "change impact" in change_history_decision["blocked_claims"]

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
        "koszt": "12.0",
    }
    assert search_terms_decision["search_term_rows"][0]["search_term"] == "bdo rejestracja"
    assert search_terms_decision["missing_read_contracts"] == []
    assert search_terms_decision["operator_review_gates"] == [
        "negative_keyword_action_validation"
    ]
    assert "negative keyword apply" in search_terms_decision["blocked_claims"]
    search_term_safety_decision = decisions_by_id["ads_review_search_term_safety"]
    assert search_term_safety_decision["status"] == "ready"
    assert search_term_safety_decision["priority"] == 50
    assert search_term_safety_decision["metric_tiles"] == {
        "90 dni": 1,
        "kliknięcia": 10,
        "koszt": "8.00",
    }
    assert search_term_safety_decision["decision_type"] == "review_search_term_safety"
    assert search_term_safety_decision["search_term_safety_rows"][0]["search_term"] == (
        "odpady cena"
    )
    assert "negative keyword apply" in search_term_safety_decision["blocked_claims"]
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
        "kandydaci": 1,
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
    assert "search-term waste" in negative_keyword_decision["blocked_claims"]
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
    ] == "Search terms: Brand Search"
    assert custom_segments_decision["custom_segment_payload_preview"][0][
        "apply_allowed"
    ] is False
    assert custom_segments_decision["custom_segment_payload_preview"][0][
        "targeting_preview"
    ][0]["apply_allowed"] is False
    assert custom_segments_decision["action_ids"] == [
        "act_prepare_custom_segments_from_search_terms"
    ]
    assert "ROAS" in custom_segments_decision["blocked_claims"]
    safety_decision = decisions_by_id["ads_block_write_actions_without_actionobject"]
    assert safety_decision["status"] == "blocked"
    assert safety_decision["priority"] == 10
    assert safety_decision["metric_tiles"] == {"ActionObjecty": 7, "blokady": 3}
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
        "Kolejność review kampanii"
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
    assert "budget scaling" in campaign_review_action["payload"]["blocked_claims"]
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
        "custom_segment_payload_preview_v1"
    )
    assert custom_segment_action["payload"]["payload_preview"][0]["member_type"] == "KEYWORD"
    assert custom_segment_action["payload"]["payload_preview"][0]["apply_allowed"] is False
    custom_segment_safety_review = custom_segment_action["payload"]["payload_preview"][0][
        "safety_review"
    ]
    assert custom_segment_safety_review["safety_contract"] == (
        "custom_segment_apply_safety_v1"
    )
    assert custom_segment_safety_review["status"] == "blocked"
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
        "negative_keyword_payload_preview_v1"
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
        ADS_STRATEGY_REVIEW_ACTION_ID
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
    assert campaign_ready_row["target_status_label"] == "ROAS w targetcie"
    assert "target=ROAS w targetcie" in campaign_ready_row["review_reason"]
    assert "review_target_context" in campaign_ready_row["human_review_gates"]
    assert "profit_margin" not in derived_ready_contract["missing_read_contracts"]
    assert "target_roas" in derived_ready_contract["allowed_metrics"]
    assert "roas_vs_target" in derived_ready_contract["allowed_metrics"]
    assert derived_ready_contract["kpi_rows"][0]["target_roas"] == 5.0
    assert derived_ready_contract["kpi_rows"][0]["roas_vs_target"] == 32.5625
    assert derived_ready_contract["kpi_rows"][0]["target_cpa_micros"] is None
    assert derived_ready_contract["kpi_rows"][0]["cpa_vs_target_micros"] is None
    assert derived_ready_contract["kpi_rows"][0]["target_status"] == "within_target"
    assert derived_ready_contract["kpi_rows"][0]["target_status_label"] == "ROAS w targetcie"
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
        "review gates": 5,
        "polityki": 5,
    }
    assert business_ready_decision["operator_review_gates"] == (
        business_ready_contract["operator_review_gates"]
    )
    assert ADS_TARGET_CONFIRMATION_ACTION_ID not in business_ready_decision["action_ids"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID in business_ready_decision["action_ids"]
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
    assert derived_ready_decision["metric_tiles"]["w targetcie"] == 1
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
            summary="Merchant Center vendor read completed through test adapter.",
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
    assert payload["product_count"] == 10900
    assert payload["issue_count"] == 23
    assert payload["latest_refresh"]["status"] == "completed"
    assert "act_review_merchant_feed_issues" in payload["action_ids"]
    assert payload["issue_clusters"]
    cluster = payload["issue_clusters"][0]
    assert cluster["issue_type"] == "availability_updated"
    assert cluster["affected_attribute"] == "n:availability"
    assert cluster["country"] == "PL"
    assert cluster["reporting_context"] == "SHOPPING_ADS"
    assert cluster["severity"] == "NOT_IMPACTED"
    assert cluster["resolution"] == "MERCHANT_ACTION"
    assert cluster["product_count"] == 23
    assert cluster["action_id"] == "act_review_merchant_feed_issues"
    assert cluster["sample_product_ids"] == []
    assert cluster["sample_titles"] == []
    assert "nie zwraca przykładowych ID produktów" in cluster["sample_unavailable_reason"]
    assert "wystąpień problemu" in cluster["sample_unavailable_reason"]
    assert "approval restored" in cluster["blocked_claims"]
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
    assert "availability_updated" in operator_summary["issue_types"]
    assert operator_summary["source_connectors"] == ["google_merchant_center"]
    assert refresh_response.json()["evidence_ids"][-1] in operator_summary["evidence_ids"]
    assert "act_review_merchant_feed_issues" in operator_summary["action_ids"]
    assert "approval restored" in operator_summary["blocked_claims"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    decision = payload["decision_queue"][0]
    assert decision["decision_type"] == "review_issue_cluster"
    assert decision["status"] == "ready"
    assert decision["title"] == (
        "Merchant: sprawdź zmiana dostępności do sprawdzenia / dostępność"
    )
    assert decision["issue_type"] == "availability_updated"
    assert decision["affected_attribute"] == "n:availability"
    assert decision["product_count"] == 23
    assert decision["issue_count"] == 23
    assert decision["priority"] == 23
    assert decision["metric_tiles"] == {"zgłoszenia": 23}
    assert decision["cluster_id"] == cluster["id"]
    assert decision["action_ids"] == ["act_review_merchant_feed_issues"]
    assert "zgłoszeń problemu" in decision["summary"]
    assert "wystąpienia problemu" in decision["rationale"]
    assert "act_review_merchant_feed_issues" not in decision["next_step"]
    assert "ActionObject review" in decision["next_step"]
    feed_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_feed_health"
    )
    assert feed_section["status"] == "ready"
    assert feed_section["summary"].startswith("Metryki Merchant:")
    assert "total_products=10900" in feed_section["summary"]
    issue_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_issue_queue"
    )
    assert issue_section["status"] == "ready"
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
    assert merchant_preview["affected_attribute"] == "n:availability"
    assert merchant_preview["metric_snapshot"] == {"issue_product_count": 23}
    assert merchant_preview["sample_products_available"] is False
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
    serialized = json.dumps(payload)
    assert "5519957373" not in serialized
    assert "adc.json" not in serialized


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
            summary="Merchant Center vendor read completed through test adapter.",
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
    assert "ALL_CONTEXTS, FREE_LISTINGS, SHOPPING_ADS" in decision["summary"]
    assert "nie jest liczbą unikalnych produktów" in decision["rationale"]
    assert len(decision["metric_facts"]) == 3
    assert len(payload["issue_clusters"]) == 3


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
            summary="GSC vendor read completed through test adapter.",
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
        summary="Ahrefs gap records completed through test adapter.",
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

    assert response.status_code == 200
    payload = response.json()
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
    assert "refresh/merge" in operator_summary["decision_type_labels"]
    assert "act_prepare_content_refresh_queue" in operator_summary["action_ids"]
    assert "lead uplift" in operator_summary["blocked_claims"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
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
        "decyzja refresh/merge, nie nowy artykuł."
    )
    assert first_decision["primary_query"] == "zielony ład"
    assert first_decision["total_clicks"] == 12
    assert first_decision["total_impressions"] == 120
    assert first_decision["aggregate_ctr"] == 0.1
    assert first_decision["wordpress_match"] == "found"
    assert first_decision["wordpress_match_confidence"] == "exact_url"
    assert first_decision["wordpress_content_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert first_decision["normalized_page_path"] == (
        "/europejski-zielony-lad-co-to-takiego"
    )
    assert first_decision["evidence_ids"]
    assert "act_prepare_content_refresh_queue" in first_decision["action_ids"]
    ahrefs_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "review_ahrefs_gap_records"
    )
    assert ahrefs_decision["status"] == "ready"
    assert ahrefs_decision["title"] == (
        "Ahrefs: zweryfikuj luki SEO przed briefem contentowym"
    )
    assert ahrefs_decision["metric_tiles"] == {
        "rekordy Ahrefs": 4,
        "pasujące": 3,
        "do review": 0,
        "off-topic": 1,
        "GSC overlap": 1,
        "WP overlap": 1,
        "content gaps": 2,
        "backlink gaps": 1,
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
    assert "Overlap: GSC: zielony ład" in zielony_lad_candidate["next_step"]
    assert "branża.example" not in json.dumps(ahrefs_decision["ahrefs_candidate_rows"])
    assert ahrefs_decision["source_connectors"] == ["ahrefs"]
    assert ahrefs_decision["evidence_ids"] == ["ev_refresh_ahrefs_gap_records"]
    assert "act_prepare_content_refresh_queue" in ahrefs_decision["action_ids"]
    assert "off-topic content recommendation" in ahrefs_decision["blocked_claims"]
    assert "traffic uplift" in ahrefs_decision["blocked_claims"]
    assert "ev_refresh_ahrefs_gap_records" in payload["evidence_ids"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-gsc-content-doctor"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["content_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
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
    assert context_decision["source_connectors"] == first_decision["source_connectors"]
    assert context_decision["evidence_ids"] == first_decision["evidence_ids"]
    assert context_decision["action_ids"] == first_decision["action_ids"]
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

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "analyticsdata.googleapis.com"
        assert request.url.path == "/v1beta/properties/411974093:runReport"
        assert request.headers["authorization"] == "Bearer ga4-access-token"
        body = json.loads(request.content.decode())
        assert [metric["name"] for metric in body["metrics"]] == [
            "activeUsers",
            "sessions",
            "screenPageViews",
            "eventCount",
            "engagementRate",
        ]
        assert [dimension["name"] for dimension in body["dimensions"]] == [
            "landingPagePlusQueryString",
            "sessionSourceMedium",
            "sessionCampaignName",
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
                        ]
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
    assert result.metric_facts[0].name == "active_users"
    assert result.metric_facts[0].value == 20
    assert result.metric_facts[0].dimensions == {
        "landing_page": "/oferta/",
        "source_medium": "google / cpc",
        "campaign_name": "PMax odpady",
    }


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
            errors=["Localo MCP OAuth authorization is incomplete."],
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
    fact_by_name = {fact.name: fact for fact in result.metric_facts}
    assert fact_by_name["localo_active_place_count"].dimensions == {
        "contract": "place_inventory",
        "scope": "active_places",
    }
    assert fact_by_name["localo_avg_visibility_current"].dimensions["contract"] == (
        "local_rankings"
    )
    assert fact_by_name["localo_reviews_count"].dimensions["contract"] == "reviews"
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
            assert request.url.params["_fields"] == "id,status,modified_gmt,date_gmt,link,slug"
            return httpx.Response(
                200,
                headers={"X-WP-Total": "12"},
                json=[
                    {
                        "id": 1,
                        "status": "publish",
                        "modified_gmt": "2026-06-15T10:00:00",
                        "link": "https://ekologus.test/blog/remediacja/",
                    }
                ],
            )
        if request.url.path == "/wp-json/wp/v2/pages":
            assert request.headers["authorization"].startswith("Basic ")
            assert request.url.params["per_page"] == "100"
            assert request.url.params["_fields"] == "id,status,modified_gmt,date_gmt,link,slug"
            return httpx.Response(
                200,
                headers={"X-WP-Total": "4"},
                json=[
                    {
                        "id": 2,
                        "status": "publish",
                        "modified_gmt": "2026-06-16T10:00:00",
                        "link": "https://ekologus.test/oferta/",
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
    assert (
        context_payload["context_pack_compaction"]["full_marketing_brief_endpoint"]
        == "/api/marketing/brief"
    )
    assert "command_center" in context_payload
    assert "tactical_queue" not in context_payload
    assert "ads_diagnostics" not in context_payload
    assert "merchant_diagnostics" not in context_payload
    assert len(context_payload["evidence_summaries"]) <= 80
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
        human_diagnosis="Merchant wymaga review.",
        recommended_reason="Przygotuj review.",
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
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
        items=[],
    )
    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
        primary_next_step="Przejrzyj Merchant.",
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[connector],
        codex_operator_status={},
    )
    brief = MarketingBrief(
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections=[],
    )
    seen: dict[str, object] = {}

    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [connector])
    monkeypatch.setattr(daily_runtime, "list_actions", lambda: [action])
    monkeypatch.setattr(daily_runtime, "list_connector_refresh_runs", lambda: [refresh_run])
    monkeypatch.setattr(daily_runtime, "build_tactical_queue", lambda: tactical_queue)

    def command_builder(
        connectors: list[ConnectorStatus] | None = None,
        tactical_queue: TacticalQueueResponse | None = None,
        actions: list[ActionObject] | None = None,
    ) -> CommandCenterResponse:
        seen["command_connectors"] = connectors
        seen["command_tactical_queue"] = tactical_queue
        seen["command_actions"] = actions
        return command

    def brief_builder(
        connectors: list[ConnectorStatus] | None = None,
        refresh_runs: list[ConnectorRefreshRun] | None = None,
        actions: list[ActionObject] | None = None,
        command_center: CommandCenterResponse | None = None,
    ) -> MarketingBrief:
        seen["brief_connectors"] = connectors
        seen["brief_refresh_runs"] = refresh_runs
        seen["brief_actions"] = actions
        seen["brief_command_center"] = command_center
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
    assert seen["brief_connectors"] == [connector]
    assert seen["brief_refresh_runs"] == [refresh_run]
    assert seen["brief_actions"] == [action]
    assert seen["brief_command_center"] == command


def test_daily_command_center_does_not_build_marketing_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
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
            strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
            items=[],
        ),
    )

    monkeypatch.setattr(daily_runtime, "build_daily_runtime_base", lambda use_cache=True: base)
    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        lambda connectors=None, tactical_queue=None, actions=None: command,
    )

    def fail_marketing_brief(*args: object, **kwargs: object) -> MarketingBrief:
        raise AssertionError("Command Center endpoint must not build Marketing Brief")

    monkeypatch.setattr(daily_runtime, "build_marketing_brief", fail_marketing_brief)

    assert daily_runtime.build_daily_command_center(use_cache=False) == command


def test_command_center_brief_uses_lightweight_daily_item_builders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import command_center

    action = ActionObject(
        id="act_prepare_ads_campaign_review_queue",
        title="Przygotuj kolejkę przeglądu kampanii Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_ads"],
        human_diagnosis="Ads wymaga review.",
        recommended_reason="Przygotuj review.",
        payload={},
        validation_status="not_validated",
        created_by="wilq",
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z API/evidence.",
        items=[],
    )
    seen: dict[str, object] = {}

    def ads_item_builder(
        facts: list[object],
        actions: list[ActionObject],
    ) -> CommandCenterBriefItem:
        seen["ads_metric_facts"] = facts
        seen["actions"] = actions
        return CommandCenterBriefItem(
            id="daily_ads_status",
            title="Ads: live campaign metrics dostępne",
            route="/ads-doctor",
            status="ready",
            priority=30,
            summary="Google Ads ma live metric facts.",
            next_step="Otwórz /ads-doctor.",
            source_connectors=["google_ads"],
            evidence_ids=["ev_ads"],
            action_ids=[action.id],
        )

    def merchant_item_builder(
        tactical_items: list[object],
        actions: list[ActionObject],
        metric_facts: list[object],
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
    ) -> CommandCenterBriefItem:
        seen["content_tactical_queue"] = queue
        seen["content_ahrefs_facts"] = ahrefs_facts
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
        lambda *_args: None,
    )
    monkeypatch.setattr(command_center, "_merchant_item_from_tactical", merchant_item_builder)
    monkeypatch.setattr(command_center, "_content_item_from_tactical", content_item_builder)
    monkeypatch.setattr(command_center, "_ga4_item_from_tactical", ga4_item_builder)

    class EmptyMetricStore:
        def list_metric_facts(self, *_args: object) -> list[object]:
            raise AssertionError("Command Center must use batched metric fact reads")

        def list_metric_facts_by_connector(
            self,
            connector_ids: list[str],
            limit_per_connector: int = 100,
        ) -> dict[str, list[object]]:
            seen["metric_connector_ids"] = connector_ids
            seen["metric_limit_per_connector"] = limit_per_connector
            return {connector_id: [] for connector_id in connector_ids}

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
    assert seen["ga4_tactical_items"] == tactical_queue.items
    assert seen["ga4_actions"] == [action]
    assert seen["ga4_metric_facts"] == []
    assert seen["metric_connector_ids"] == [
        "google_ads",
        "google_merchant_center",
        "google_analytics_4",
        "ahrefs",
        "localo",
    ]


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
    assert data["content_diagnostics"]["context_pack_compaction"] == {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": 3,
        "full_endpoint": "/api/content/diagnostics",
    }


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
    assert preview["issue_type"] == "missing_image"
    assert preview["metric_snapshot"] == {"issue_product_count": 3}
    assert preview["apply_allowed"] is False
    assert preview["api_mutation_ready"] is False
    assert preview["destructive"] is False
    assert "feed write" in preview["blocked_claims"]
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000


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
    assert ads_context["context_pack_compaction"]["full_endpoint"] == "/api/ads/diagnostics"
    assert "sections" not in ads_context
    triage_contract = ads_context["campaign_triage_read_contract"]
    assert triage_contract["status"] == "ready"
    assert triage_contract["triage_rows"]
    assert len(triage_contract["triage_rows"]) <= 4
    assert triage_contract["triage_rows"][0]["action_ids"] == [
        "act_prepare_ads_campaign_review_queue"
    ]
    assert "wasted budget" in triage_contract["blocked_claims"]
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
    assert "campaign mutation" in optimizer_contract["blocked_claims"]
    assert ads_context["change_impact_readiness_contract"]["status"] == "blocked"
    assert "change impact" in ads_context["change_impact_readiness_contract"][
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
    assert "profitability verdict" in strategy_readiness["blocked_claims"]
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
    assert "Kolejność review kampanii" in campaign_candidate["review_reason"]
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
    assert len(ads_context["negative_keywords_read_contract"]["payload_preview"]) <= 8
    assert (
        ads_context["context_pack_compaction"]["budget_payload_preview_included"]
        <= 4
    )
    for candidate in ads_context["negative_keywords_read_contract"]["candidates"]:
        assert len(candidate["keyword_context_rows"]) <= 4
    for decision in ads_context["decision_queue"]:
        assert len(decision["budget_apply_preview"]) == 0
        assert len(decision["recommendation_apply_preview"]) <= 4
        assert len(decision["search_term_safety_rows"]) <= 4
        assert len(decision["keyword_match_context_rows"]) <= 4
        assert len(decision["negative_keyword_payload_preview"]) <= 4
        for candidate in decision["negative_keyword_candidates"]:
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
    assert "custom_segment_payload_preview" not in ads_context[
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
    assert "Demand Gen launch recommendation" in readiness["blocked_claims"]
    assert "sections" not in data["ga4_diagnostics"]
    assert '"metric_facts":' not in json.dumps(data["ga4_diagnostics"])
    assert data["ga4_diagnostics"]["context_pack_compaction"][
        "full_endpoint"
    ] == "/api/ga4/diagnostics"
    assert data["ads_diagnostics"]["context_pack_compaction"][
        "metric_facts_removed"
    ] is True
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000


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
    assert isinstance(data["demand_gen_migration_constraint_rows"], list)
    assert "demand_gen_landing_quality_by_campaign" not in data["missing_read_contracts"]
    assert "demand_gen_migration_constraints" not in data["missing_read_contracts"]
    assert "demand_gen_readiness_review_action_object" in data["available_read_contracts"]
    assert "demand_gen_action_object" not in data["missing_read_contracts"]
    assert "Demand Gen launch recommendation" in data["blocked_claims"]


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
    assert "demand_gen_migration_constraints" in data["available_read_contracts"]
    assert "demand_gen_landing_quality_by_campaign" not in data["missing_read_contracts"]
    assert "demand_gen_migration_constraints" not in data["missing_read_contracts"]
    assert data["metric_tiles"]["reklamy DG"] == 1
    assert data["metric_tiles"]["assety DG"] == 1
    assert data["metric_tiles"]["landingi DG"] == 1
    assert data["metric_tiles"]["ograniczenia"] == 1
    assert len(data["demand_gen_ad_group_ad_rows"]) == 1
    assert len(data["demand_gen_creative_asset_rows"]) == 1
    assert len(data["demand_gen_landing_quality_rows"]) == 1
    assert len(data["demand_gen_migration_constraint_rows"]) == 1
    assert data["demand_gen_ad_group_ad_rows"][0]["ad_id"] == "803"
    assert data["demand_gen_ad_group_ad_rows"][0]["asset_reference_count"] == 4
    assert data["demand_gen_creative_asset_rows"][0]["asset_id"] == "901"
    assert data["demand_gen_creative_asset_rows"][0]["impressions"] == 44
    assert data["demand_gen_landing_quality_rows"][0]["campaign_name"] == "Demand Gen Test"
    assert data["demand_gen_landing_quality_rows"][0]["landing_page"] == "/dg-test/"
    assert data["demand_gen_landing_quality_rows"][0]["active_users"] == 18
    assert data["demand_gen_landing_quality_rows"][0]["sessions"] == 24
    assert data["demand_gen_landing_quality_rows"][0]["engagement_rate"] == 0.75
    assert data["demand_gen_migration_constraint_rows"][0]["campaign_name"] == (
        "Demand Gen Test"
    )
    assert data["demand_gen_migration_constraint_rows"][0]["migration_candidate"] is False
    assert "already_demand_gen" in data["demand_gen_migration_constraint_rows"][0]["reason"]
    preview = data["payload_preview"][0]
    assert preview["demand_gen_ad_group_ad_row_count"] == 1
    assert preview["demand_gen_creative_asset_row_count"] == 1
    assert preview["demand_gen_landing_quality_row_count"] == 1
    assert preview["demand_gen_migration_constraint_row_count"] == 1
    assert preview["apply_allowed"] is False
    assert "Demand Gen launch recommendation" in data["blocked_claims"]


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
    assert "Demand Gen launch recommendation" in action["payload"]["blocked_claims"]

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
    assert daily_command["skill_id"] == "wilq-daily-command"
    assert daily_command["metric_tiles"]["decyzje"] >= 1
    assert daily_command["source_connectors"]
    assert daily_command["evidence_ids"]

    ads_daily = workflow_by_id["ads_daily_check"]
    assert ads_daily["route"] == "/ads-doctor"
    assert ads_daily["skill_id"] == "wilq-ads-doctor"
    assert "kampanie" in ads_daily["metric_tiles"]
    assert any(value >= 1 for value in ads_daily["metric_tiles"].values())
    assert "act_prepare_ads_campaign_review_queue" in ads_daily["action_ids"]

    localo = workflow_by_id["localo_visibility_review"]
    assert localo["status"] == "blocked"
    assert localo["route"] == "/localo"
    assert "local_ranking_rows" in localo["missing_contracts"]

    serialized = json.dumps(workflows, ensure_ascii=False)
    assert "Workflow definition runs against WILQ API" not in serialized
    assert "Fetch WILQ API context" not in serialized


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
