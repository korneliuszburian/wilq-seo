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
from wilq.connectors.vendor import VendorReadResult
from wilq.connectors.wordpress.client import refresh_wordpress_content_inventory
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshStatus,
    Opportunity,
    OpportunityDomain,
)
from wilq.security.redaction import redact_mapping

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
        "WORDPRESS_EKOLOGUS_USERNAME",
        "WORDPRESS_EKOLOGUS_APP_PASSWORD",
        "WORDPRESS_SKLEP_URL",
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


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
    assert "validated before apply" in json.dumps(response.json())
    audit_response = client.get(
        "/api/audit/events?action_id=act_configure_google_ads_env"
    )
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "apply_blocked"


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
    assert "todays_moves" in data["sections"]


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
        return httpx.Response(
            200,
            json=[
                {
                    "results": [
                        {
                            "metrics": {
                                "clicks": "2",
                                "impressions": "10",
                                "costMicros": "3000000",
                            }
                        },
                        {
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
    serialized = json.dumps(result.metric_summary)
    assert "developer-token-test" not in serialized
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
        assert body["rowLimit"] == 1
        assert "startDate" in body
        assert "endDate" in body
        return httpx.Response(
            200,
            json={
                "rows": [
                    {
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
        return httpx.Response(
            200,
            json={
                "metricHeaders": [
                    {"name": "activeUsers"},
                    {"name": "sessions"},
                    {"name": "screenPageViews"},
                    {"name": "eventCount"},
                    {"name": "engagementRate"},
                ],
                "rows": [
                    {
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
                                "productCount": "2",
                            },
                            {
                                "severity": "NOT_IMPACTED",
                                "resolution": "PENDING_PROCESSING",
                                "productCount": "1",
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


def test_wordpress_vendor_read_uses_rest_content_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_wordpress_env(monkeypatch)
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.test")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "ekologus.test"
        assert request.headers["authorization"].startswith("Basic ")
        assert request.url.params["per_page"] == "1"
        assert request.url.params["_fields"] == "id,status,modified_gmt,date_gmt"
        if request.url.path == "/wp-json/wp/v2/posts":
            return httpx.Response(
                200,
                headers={"X-WP-Total": "12"},
                json=[{"id": 1, "status": "publish", "modified_gmt": "2026-06-15T10:00:00"}],
            )
        if request.url.path == "/wp-json/wp/v2/pages":
            return httpx.Response(
                200,
                headers={"X-WP-Total": "4"},
                json=[{"id": 2, "status": "publish", "modified_gmt": "2026-06-16T10:00:00"}],
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
        "api": "wordpress_rest_content_inventory",
        "connector_id": "wordpress_ekologus",
        "site_kind": "primary",
        "content_object_count": 16,
        "posts_total": 12,
        "pages_total": 4,
        "latest_modified_gmt": "2026-06-16T10:00:00",
        "latest_post_modified_gmt": "2026-06-15T10:00:00",
        "latest_page_modified_gmt": "2026-06-16T10:00:00",
    }


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
