from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.context_compaction import compact_connector_status_for_operator_context
from apps.api.wilq_api.main import app
from wilq.connectors.google_auth import GOOGLE_CREDENTIAL_ENV_NAMES

client = TestClient(app)


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


def clear_localo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "LOCALO_API_TOKEN",
        "LOCALO_ORGANIZATION_ID",
        "LOCALO_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)


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
    assert connector["product_scope"] == "optional_disabled"
    assert connector["product_scope_label"] == "opcjonalne, wyłączone w tym zakresie"
    assert connector["active_for_daily_work"] is False
    assert connector["configured"] is False
    assert connector["missing_credentials"] == []
    assert connector["health_check"] == "disabled_optional"
    assert connector["error"] == "Connector disabled by current product scope."


def test_connector_registry_marks_experimental_and_runtime_surfaces_outside_daily_work() -> None:
    response = client.get("/api/connectors")
    assert response.status_code == 200
    connectors = {connector["id"]: connector for connector in response.json()}

    for connector in connectors.values():
        capability = connector["capabilities"]
        assert capability["read"] is (capability["read_adapter"] is not None)
        assert capability["write"] is (capability["mutation_adapter"] is not None)
        assert capability["operations"] == connector["supported_actions"]

    for connector_id in ("google_ads", "google_search_console", "wordpress_ekologus"):
        assert connectors[connector_id]["product_scope"] == "production"
        assert connectors[connector_id]["active_for_daily_work"] is True

    assert connectors["linkedin"]["product_scope"] == "experimental"
    assert connectors["linkedin"]["active_for_daily_work"] is False
    assert connectors["facebook"]["product_scope"] == "experimental"
    assert connectors["facebook"]["active_for_daily_work"] is False
    assert connectors["openai_codex"]["product_scope"] == "runtime"
    assert connectors["openai_codex"]["active_for_daily_work"] is False


def test_connector_registry_exposes_only_implemented_adapters_and_review_actions() -> None:
    response = client.get("/api/connectors")
    assert response.status_code == 200
    connectors = {connector["id"]: connector for connector in response.json()}

    wordpress = connectors["wordpress_ekologus"]
    assert wordpress["capabilities"]["write"] is True
    assert (
        wordpress["capabilities"]["mutation_adapter"]
        == "wordpress_draft_execution_boundary"
    )
    assert wordpress["capabilities"]["action_scope"] == "draft_only"

    for connector_id in (
        "google_ads",
        "google_merchant_center",
        "localo",
        "wordpress_sklep",
        "linkedin",
        "facebook",
        "ahrefs",
    ):
        capability = connectors[connector_id]["capabilities"]
        assert capability["write"] is False
        assert capability["mutation_adapter"] is None

    assert connectors["google_merchant_center"]["supported_actions"] == [
        "merchant_feed_issue"
    ]
    assert connectors["localo"]["supported_actions"] == ["local_visibility_task"]
    assert connectors["ahrefs"]["supported_actions"] == []
    assert connectors["wordpress_sklep"]["supported_actions"] == []
    assert connectors["linkedin"]["capabilities"]["read"] is False
    assert connectors["facebook"]["capabilities"]["read"] is False

    ads_context = compact_connector_status_for_operator_context(connectors["google_ads"])
    assert ads_context["capabilities"] == {
        "read": True,
        "write": False,
        "read_adapter_implemented": True,
        "mutation_adapter_implemented": False,
        "action_scope": "review_only",
        "blockers": ["vendor_write_not_implemented"],
    }


def test_codex_connector_reports_local_cli_and_login_without_api_key_or_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "private-codex-home"
    codex_home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_API_KEY", "must-not-be-used")
    monkeypatch.setenv("PATH", "")

    missing_cli = client.get("/api/connectors/openai_codex/status").json()
    assert missing_cli["status"] == "missing_dependency"
    assert missing_cli["configured"] is False
    assert missing_cli["required_env"] == []
    assert missing_cli["missing_credentials"] == []
    assert missing_cli["health_check"] == "local_codex_login"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "codex"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(bin_dir))

    missing_login = client.get("/api/connectors/openai_codex/status").json()
    assert missing_login["status"] == "auth_error"
    assert missing_login["configured"] is False

    (codex_home / "auth.json").write_text("not-read-by-status", encoding="utf-8")
    configured = client.get("/api/connectors/openai_codex/status").json()
    assert configured["status"] == "configured"
    assert configured["configured"] is True
    assert configured["available_credential_sources"] == ["local_codex_login"]

    system_status = client.get("/api/system/status").json()["codex_runtime"]
    assert system_status["readiness_status"] == "ready"
    assert system_status["codex_available"] is True
    assert system_status["login_available"] is True
    serialized = json.dumps({"connector": configured, "runtime": system_status})
    assert "CODEX_API_KEY" not in serialized
    assert str(codex_home) not in serialized
    assert "not-read-by-status" not in serialized


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
