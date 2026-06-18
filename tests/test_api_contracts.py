from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.wilq_api.main import app
from wilq.connectors.ahrefs.client import refresh_ahrefs_domain_rating
from wilq.connectors.google_ads.client import refresh_google_ads_campaign_summary
from wilq.connectors.google_analytics_4.client import refresh_ga4_behavior_summary
from wilq.connectors.google_auth import GOOGLE_CREDENTIAL_ENV_NAMES
from wilq.connectors.google_merchant_center.client import (
    refresh_merchant_product_status_summary,
)
from wilq.connectors.google_search_console.client import refresh_search_console_site_summary
from wilq.connectors.google_sheets.client import refresh_google_sheets_review_surface
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.connectors.wordpress.client import refresh_wordpress_content_inventory
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    Opportunity,
    OpportunityDomain,
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


def clear_google_ads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in GOOGLE_ADS_TEST_ENV:
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
            metric_summary={"active_products": 12, "disapproved_products": 3},
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
            "summary": (
                "Vendor read blocked by missing credential names: "
                "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID."
            ),
            "error": "failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
            "api_key": "sk-testsecretvalue1234567890",  # pragma: allowlist secret
        }
    )

    assert redacted["api"] == "ahrefs_site_explorer_domain_rating"
    assert redacted["summary"] == (
        "Vendor read blocked by missing credential names: "
        "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID."
    )
    assert redacted["error"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"


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
    serialized = json.dumps(response.json())
    assert "Explicit apply confirmation is required" in serialized
    assert "validated before apply" in serialized
    audit_response = client.get(
        "/api/audit/events?action_id=act_configure_google_ads_env"
    )
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "apply_confirmation_missing"


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
    assert "Action mode must be apply" in json.dumps(body)


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
            "metric_names": {"active_products", "disapproved_products"},
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
        metric_names = {str(metric["name"]) for metric in action["metrics"]}
        assert metric_names.issuperset(expected["metric_names"])
        assert "prepare" in json.dumps(action["payload"])


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
        assert item["metric_facts"]
        assert item["risk"] in {"low", "medium"}
    assert "act_prepare_linkedin_social_drafts" not in brief["action_ids"]
    assert "act_prepare_facebook_social_drafts" not in brief["action_ids"]
    assert "act_prepare_linkedin_social_drafts" not in action_items
    assert "act_prepare_facebook_social_drafts" not in action_items


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
    sections = {section["id"]: section for section in payload["sections"]}
    assert sections["ga4_landing_behavior"]["status"] == "ready"
    assert sections["ga4_landing_behavior"]["tactical_items"]
    assert sections["ga4_landing_behavior"]["tactical_items"][0]["dimensions"][
        "landing_page"
    ] == "/europejski-zielony-lad-co-to-takiego/"
    assert sections["ga4_tracking_readiness"]["status"] == "missing"
    assert "conversion drop" in sections["ga4_tracking_readiness"]["blocked_claims"]
    assert sections["ga4_action_safety"]["status"] == "ready"

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-ga4-analyst"})
    assert context_response.status_code == 200
    context_ga4 = context_response.json()["ga4_diagnostics"]
    assert context_ga4["evidence_ids"] == payload["evidence_ids"]
    assert context_ga4["action_ids"] == payload["action_ids"]
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
    assert brief_by_id["daily_merchant_feed"]["metric_tiles"]["issues"] == 3
    assert "act_review_merchant_feed_issues" in brief_by_id["daily_merchant_feed"]["action_ids"]
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["query/page"] >= 1
    assert "act_prepare_content_refresh_queue" in brief_by_id["daily_content_queue"]["action_ids"]
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["landing groups"] >= 1
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
    assert "GA4:" not in plan_by_id["plan_review_ga4_landing_quality"]["why_it_matters"]
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["status"] == "blocked"
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["skill_id"] == (
        "wilq-ads-doctor"
    )
    assert "spend" in plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["blocked_claims"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    context_command = context_response.json()["command_center"]
    assert context_command["operator_brief"] == payload["operator_brief"]
    assert context_command["demo_script"] == []
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


def test_opportunities_are_derived_from_evidence_and_rule_mappings() -> None:
    response = client.get("/api/opportunities")
    assert response.status_code == 200
    opportunities = response.json()
    google_ads = next(item for item in opportunities if item["id"] == "opp_connector_google_ads")
    assert google_ads["evidence_ids"] == ["ev_connector_google_ads_status"]
    assert "google_ads_search_playbook" in google_ads["playbook_ids"]
    assert "ads_search_terms_v1" in google_ads["expert_rule_ids"]
    assert google_ads["is_fixture"] is False
    assert "No performance metrics" not in google_ads["title"]
    assert "connector_configured" not in json.dumps(google_ads)
    assert "Run a read-only" not in json.dumps(google_ads)


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

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            assert "grant_type=refresh_token" in request.content.decode()
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        assert request.url.host == "googleads.googleapis.com"
        assert request.url.path == "/v24/customers/1234567890/googleAds:searchStream"
        assert request.headers["developer-token"] == "developer-token-test"
        assert request.headers["login-customer-id"] == "9998887777"
        assert request.headers["authorization"] == "Bearer ya29.mocktoken"
        assert "FROM campaign" in request.content.decode()
        assert "campaign.name" in request.content.decode()
        return httpx.Response(
            200,
            json=[
                {
                    "results": [
                        {
                            "campaign": {"id": "101", "name": "Brand Search"},
                            "metrics": {
                                "clicks": "2",
                                "impressions": "10",
                                "costMicros": "3000000",
                            }
                        },
                        {
                            "campaign": {"id": "102", "name": "PMax Feed"},
                            "metrics": {
                                "clicks": "1",
                                "impressions": "5",
                                "costMicros": "1000000",
                            }
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
    assert result.metric_facts[0].dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
    }
    assert result.metric_facts[0].name == "clicks"
    assert result.metric_facts[0].value == 2
    serialized = json.dumps(result.metric_summary)
    assert "developer-token-test" not in serialized
    assert "refresh-token-test" not in serialized


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
            },
            metric_facts=[
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
    assert payload["blocked_handoff"]["status"] == "ready"
    assert "Google Ads connector ma live metric facts." in payload["blocked_handoff"][
        "allowed_demo_claims"
    ]
    live_section = next(
        section for section in payload["sections"] if section["id"] == "ads_live_data_status"
    )
    assert live_section["status"] == "ready"
    campaign_section = next(
        section for section in payload["sections"] if section["id"] == "ads_campaign_overview"
    )
    assert campaign_section["status"] == "ready"
    facts_by_name = {fact["name"]: fact for fact in campaign_section["metric_facts"]}
    assert facts_by_name["clicks"]["value"] == 9
    assert any(
        fact["name"] == "cost_micros"
        and fact["dimensions"].get("campaign_name") == "Brand Search"
        for fact in campaign_section["metric_facts"]
    )
    assert "act_configure_google_ads_env" not in payload["action_ids"]


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
                VendorMetricFact("total_products", 10900, {}),
                VendorMetricFact("item_level_issue_count", 23, {}),
                VendorMetricFact(
                    "issue_product_count",
                    23,
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "n:availability",
                        "country": "PL",
                        "severity": "NOT_IMPACTED",
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
    feed_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_feed_health"
    )
    assert feed_section["status"] == "ready"
    issue_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_issue_queue"
    )
    assert issue_section["status"] == "ready"
    assert issue_section["tactical_items"]
    assert any(
        item["dimensions"].get("issue_type") == "availability_updated"
        for item in issue_section["tactical_items"]
    )
    serialized = json.dumps(payload)
    assert "5519957373" not in serialized
    assert "adc.json" not in serialized


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

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-gsc-content-doctor"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["content_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
    assert context_payload["content_diagnostics"]["action_ids"] == payload["action_ids"]
    serialized = json.dumps(payload)
    assert "google_adc.json" not in serialized
    assert "app-password" not in serialized


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

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.ahrefs.com"
        assert request.url.path == "/v3/site-explorer/domain-rating"
        assert request.headers["authorization"] == "Bearer ahrefs-token-test"
        assert request.headers["accept"] == "application/json"
        assert request.url.params["target"] == "ekologus.pl"
        assert len(request.url.params["date"]) == 10
        assert request.url.params["output"] == "json"
        return httpx.Response(
            200,
            json={"domain_rating": {"ahrefs_rank": 1450, "domain_rating": 90.0}},
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
    }
    serialized = json.dumps(result.metric_summary)
    assert "ahrefs-token-test" not in serialized
    assert "ekologus.pl" not in serialized


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
    ads_response = client.get("/api/ads/diagnostics")
    assert ads_response.status_code == 200
    ads_diagnostics = ads_response.json()
    merchant_response = client.get("/api/merchant/diagnostics")
    assert merchant_response.status_code == 200
    merchant_diagnostics = merchant_response.json()

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_brief = context_payload["marketing_brief"]

    assert context_brief["language"] == "pl-PL"
    assert context_brief["language"] == brief["language"]
    assert context_brief["blocker_count"] == brief["blocker_count"]
    assert context_brief["recommendation_count"] == brief["recommendation_count"]
    assert context_brief["evidence_ids"] == brief["evidence_ids"]
    assert context_brief["action_ids"] == brief["action_ids"]
    assert [section["id"] for section in context_brief["sections"]] == [
        section["id"] for section in brief["sections"]
    ]
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
    assert "card_goal_001_rules" in card_ids
    evidence_ids = {item["id"] for item in data["evidence_summaries"]}
    assert "ev_connector_google_ads_status" in evidence_ids


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
