from __future__ import annotations

from pathlib import Path

import pytest

import wilq.schemas as schemas
from wilq.briefing.diagnostic_readiness import build_diagnostic_data_readiness
from wilq.schemas import (
    ConnectorCapability,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshState,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    DiagnosticDataReadiness,
    DiagnosticDataReadinessState,
    FreshnessState,
    MetricFact,
)


def _connector(*, refresh_allowed: bool) -> ConnectorStatus:
    return ConnectorStatus(
        id="localo",
        label="Localo",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="unknown"),
        refresh_state=ConnectorRefreshState(
            refresh_allowed=refresh_allowed,
            safe_next_step="Uruchom bezpieczny odczyt Localo przed oceną widoczności.",
        ),
        capabilities=ConnectorCapability(read=True),
        health_check="credential_presence",
    )


def _connector_with_status(status: ConnectorStatusValue) -> ConnectorStatus:
    return ConnectorStatus(
        id="localo",
        label="Localo",
        status=status,
        configured=False,
        freshness=FreshnessState(state="missing"),
        refresh_state=ConnectorRefreshState(
            refresh_allowed=False,
            safe_next_step="Sprawdź stan dostępu Localo bez używania metryk.",
        ),
        capabilities=ConnectorCapability(read=True),
        health_check="credential_presence",
    )


def test_readiness_builder_is_available_from_the_schema_facade() -> None:
    assert schemas.build_diagnostic_data_readiness is build_diagnostic_data_readiness


def test_readiness_state_contract_contains_all_dashboard_states() -> None:
    required_states = {
        "ready",
        "partial",
        "refresh_available",
        "unavailable",
        "missing",
        "blocked",
        "failed",
    }

    assert required_states <= {state.value for state in DiagnosticDataReadinessState}


def test_configured_connector_without_facts_is_recovery_not_zero() -> None:
    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=True),
        latest_refresh=None,
        factual_metrics=[],
    )

    assert readiness.state == "refresh_available"
    assert readiness.factual_metric_count == 0
    assert readiness.factual_metrics == []
    assert readiness.refresh_allowed is True
    assert readiness.reason
    assert readiness.coverage_label == "Brak potwierdzonych metryk do pokazania."
    assert readiness.safe_next_step == (
        "Uruchom bezpieczny odczyt Localo przed oceną widoczności."
    )


def test_observed_zero_is_ready_factual_metric_with_trace() -> None:
    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=False),
        latest_refresh=None,
        factual_metrics=[
            MetricFact(
                name="localo_competitor_change_count",
                value=0,
                period="localo_mcp_read",
                source_connector="localo",
                evidence_id="ev_localo_observed_zero",
            )
        ],
    )

    assert readiness.state == "ready"
    assert readiness.factual_metric_count == 1
    fact = readiness.factual_metrics[0]
    assert fact.value == 0
    assert fact.source_connector_label == "Localo"
    assert fact.period_label == "ostatni odczyt Localo"
    assert readiness.evidence_ids == ["ev_localo_observed_zero"]


def test_nonfactual_readiness_rejects_observed_metric_values() -> None:
    with pytest.raises(ValueError, match="nie może zwracać metryk jako faktów"):
        DiagnosticDataReadiness(
            state="blocked",
            connector_id="localo",
            factual_metric_count=1,
            factual_metrics=[
                MetricFact(
                    name="localo_competitor_change_count",
                    value=0,
                    period="localo_mcp_read",
                    source_connector="localo",
                    evidence_id="ev_localo_observed_zero",
                )
            ],
            evidence_ids=["ev_localo_observed_zero"],
        )


def test_ready_readiness_requires_an_observed_metric_with_evidence() -> None:
    with pytest.raises(ValueError, match="wymaga co najmniej jednej metryki"):
        DiagnosticDataReadiness(
            state="ready",
            connector_id="localo",
            evidence_ids=["ev_localo_access_only"],
        )


def test_partial_readiness_requires_an_observed_metric() -> None:
    with pytest.raises(ValueError, match="wymaga zaobserwowanych metryk"):
        DiagnosticDataReadiness(
            state="partial",
            connector_id="localo",
            evidence_ids=["ev_localo_partial_without_facts"],
        )


def test_readiness_count_cannot_hide_displayed_facts() -> None:
    with pytest.raises(ValueError, match="nie może być mniejsza"):
        DiagnosticDataReadiness(
            state="ready",
            connector_id="localo",
            factual_metric_count=0,
            factual_metrics=[
                MetricFact(
                    name="localo_competitor_change_count",
                    value=0,
                    period="localo_mcp_read",
                    source_connector="localo",
                    evidence_id="ev_localo_count_mismatch",
                )
            ],
            evidence_ids=["ev_localo_count_mismatch"],
        )


@pytest.mark.parametrize(
    ("refresh_allowed", "expected_state"),
    [(True, "refresh_available"), (False, "unavailable")],
)
def test_stale_facts_require_recovery_instead_of_metric_rendering(
    refresh_allowed: bool,
    expected_state: str,
) -> None:
    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=refresh_allowed),
        latest_refresh=None,
        factual_metrics=[
            MetricFact(
                name="localo_competitor_change_count",
                value=0,
                period="localo_mcp_read",
                source_connector="localo",
                evidence_id="ev_localo_stale_zero",
            )
        ],
        stale=True,
    )

    assert readiness.state == expected_state
    assert readiness.state != "ready"
    assert readiness.factual_metric_count == 0
    assert readiness.factual_metrics == []
    assert readiness.evidence_ids == ["ev_localo_stale_zero"]
    assert "wcześniejszy odczyt" in readiness.reason
    assert readiness.coverage_label == (
        "Metryki z wcześniejszego odczytu nie są pokazane jako bieżące."
    )


@pytest.mark.parametrize(
    ("refresh_status", "expected_state"),
    [
        (ConnectorRefreshStatus.blocked, "blocked"),
        (ConnectorRefreshStatus.failed, "failed"),
    ],
)
def test_unsuccessful_refresh_is_explicit_and_never_exposes_metrics(
    refresh_status: ConnectorRefreshStatus,
    expected_state: str,
) -> None:
    latest_refresh = ConnectorRefreshRun(
        id=f"refresh_localo_{expected_state}",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=refresh_status,
        evidence_ids=[f"ev_localo_{expected_state}"],
        summary="Odczyt Localo nie dostarczył metryk.",
    )

    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=True),
        latest_refresh=latest_refresh,
        factual_metrics=[],
    )

    assert readiness.state == expected_state
    assert readiness.factual_metric_count == 0
    assert readiness.factual_metrics == []
    assert readiness.evidence_ids == [f"ev_localo_{expected_state}"]
    assert readiness.reason


@pytest.mark.parametrize(
    "refresh_status",
    [ConnectorRefreshStatus.queued, ConnectorRefreshStatus.running],
)
def test_active_refresh_is_explicit_and_never_exposes_metrics(
    refresh_status: ConnectorRefreshStatus,
) -> None:
    latest_refresh = ConnectorRefreshRun(
        id=f"refresh_localo_{refresh_status.value}",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=refresh_status,
        evidence_ids=[f"ev_localo_{refresh_status.value}"],
        summary="Odczyt Localo jest aktywny.",
    )

    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=False),
        latest_refresh=latest_refresh,
        factual_metrics=[],
    )

    assert readiness.state == "refresh_running"
    assert readiness.state_label == "Trwa odczyt danych"
    assert readiness.factual_metrics == []


@pytest.mark.parametrize(
    ("connector_status", "expected_state"),
    [
        (ConnectorStatusValue.missing_credentials, "blocked"),
        (ConnectorStatusValue.auth_error, "blocked"),
        (ConnectorStatusValue.missing_dependency, "blocked"),
        (ConnectorStatusValue.disabled, "blocked"),
        (ConnectorStatusValue.unreachable, "failed"),
        (ConnectorStatusValue.rate_limited, "failed"),
        (ConnectorStatusValue.error, "failed"),
    ],
)
def test_connector_failure_state_is_explicit_without_metrics(
    connector_status: ConnectorStatusValue,
    expected_state: str,
) -> None:
    readiness = build_diagnostic_data_readiness(
        connector=_connector_with_status(connector_status),
        latest_refresh=None,
        factual_metrics=[],
    )

    assert readiness.state == expected_state
    assert readiness.factual_metrics == []
    assert readiness.reason


def test_partial_readiness_exposes_only_observed_facts_and_coverage() -> None:
    coverage_label = "Potwierdzone 3 z 6 zakresów danych Localo."
    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=True),
        latest_refresh=None,
        factual_metrics=[
            MetricFact(
                name="localo_competitor_change_count",
                value=0,
                period="localo_mcp_read",
                source_connector="localo",
                evidence_id="ev_localo_partial_zero",
            )
        ],
        factual_metric_count=3,
        evidence_ids=["ev_localo_scope", "ev_localo_partial_zero"],
        partial=True,
        partial_coverage_label=coverage_label,
    )

    assert readiness.state == "partial"
    assert readiness.factual_metric_count == 3
    assert [fact.value for fact in readiness.factual_metrics] == [0]
    assert readiness.evidence_ids == ["ev_localo_scope", "ev_localo_partial_zero"]
    assert readiness.coverage_label == coverage_label
    assert readiness.safe_next_step == (
        "Uruchom bezpieczny odczyt Localo przed oceną widoczności."
    )


@pytest.mark.parametrize(
    "field",
    ["evidence_id", "metric_label", "period_label", "source_connector_label"],
)
@pytest.mark.parametrize("blank_value", ["", "   "])
def test_metric_fact_rejects_blank_marketer_context(
    field: str,
    blank_value: str,
) -> None:
    payload = {
        "name": "localo_competitor_change_count",
        "metric_label": "Zmiany konkurencji",
        "value": 0,
        "period": "localo_mcp_read",
        "period_label": "ostatni odczyt Localo",
        "source_connector": "localo",
        "source_connector_label": "Localo",
        "evidence_id": "ev_localo_observed_zero",
    }
    payload[field] = blank_value

    with pytest.raises(ValueError, match="pełnego kontekstu marketera"):
        MetricFact(**payload)


# --- Ahrefs / Merchant diagnostic wiring (cmrf truth foundation) ---


def test_ahrefs_diagnostics_expose_data_readiness_for_observed_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tests._contract_support.env import clear_ahrefs_env

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_readiness_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_readiness_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")
    run = ConnectorRefreshRun(
        id="refresh_ahrefs_readiness_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_ahrefs_readiness_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"domain_rating": 42},
        summary="Ahrefs readiness fixture.",
    )
    from wilq.connectors.vendor import VendorMetricFact
    from wilq.storage.local_state import local_state_store
    from wilq.storage.metric_store import metric_store

    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                "ahrefs_content_gap_count",
                1,
                {
                    "gap_type": "content_gap",
                    "keyword": "bdo odpady",
                    "competitor_domain": "denios.pl",
                    "target_domain": "ekologus.pl",
                    "target_keyword_sample_size": "100",
                    "target_keyword_limit": "1000",
                },
                period="ahrefs_gap",
            ),
        ],
    )

    from tests._contract_support.api_client import client

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    data_readiness = response.json()["data_readiness"]
    assert data_readiness["state"] == "ready"
    assert data_readiness["factual_metric_count"] >= 1
    assert data_readiness["factual_metrics"]
    assert data_readiness["evidence_ids"]
    assert response.json()["live_data_available"] is True


def test_ahrefs_diagnostics_without_facts_expose_recovery_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tests._contract_support.env import clear_ahrefs_env

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_empty_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_empty_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    from tests._contract_support.api_client import client

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    data_readiness = response.json()["data_readiness"]
    assert data_readiness["state"] in {"refresh_available", "unavailable", "blocked"}
    assert data_readiness["factual_metric_count"] == 0
    assert data_readiness["factual_metrics"] == []
    assert response.json()["live_data_available"] is False


def test_merchant_diagnostics_expose_data_readiness_for_trusted_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tests._contract_support.env import clear_google_service_env
    from wilq.connectors.vendor import VendorMetricFact
    from wilq.storage.local_state import local_state_store
    from wilq.storage.metric_store import metric_store

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_readiness_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_readiness_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    adc_json = tmp_path / "adc.json"
    adc_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(adc_json))
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "5519957373")
    run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_readiness_test",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_merchant_readiness_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"total_products": 10900, "item_level_issue_count": 23},
        summary="Merchant readiness fixture.",
    )
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
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
                period="merchant_feed",
            ),
        ],
    )

    from tests._contract_support.api_client import client

    response = client.get("/api/merchant/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    data_readiness = payload["data_readiness"]
    assert data_readiness["state"] == "ready"
    assert data_readiness["factual_metric_count"] >= 1
    assert data_readiness["factual_metrics"]
    assert payload["live_data_available"] is True
