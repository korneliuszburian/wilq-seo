from __future__ import annotations

from datetime import timedelta

import pytest

from wilq.connectors.registry import get_connector_status
from wilq.schemas import (
    AdsCampaignMetricRow,
    AdsCampaignTriageRow,
    ConnectorCapability,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
    MetricFact,
    connector_status_label,
    utc_now,
)


def test_connector_status_hydrates_operator_status_label() -> None:
    connector = ConnectorStatus(
        id="google_analytics_4",
        label="Google Analytics 4",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="unknown"),
        capabilities=ConnectorCapability(read=True),
        health_check="credential_presence",
    )

    assert connector.status_label == "dostęp skonfigurowany"
    assert connector.missing_credentials_summary_label == "brak brakujących pól dostępu"
    assert connector.credential_source_summary_label == "brak źródeł konfiguracji"


def test_connector_status_unknown_fallback_is_neutral_polish_copy() -> None:
    assert connector_status_label("vendor_status_that_drifted") == ("status źródła do sprawdzenia")


def test_connector_status_uses_latest_successful_vendor_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed_at = utc_now() - timedelta(minutes=10)
    run = ConnectorRefreshRun(
        id="refresh_google_merchant_center_test",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=completed_at,
        vendor_data_collected=True,
        summary="Odczyt Merchant Center zakończony.",
    )

    class FakeStateStore:
        def list_connector_refresh_runs(
            self,
            connector_id: str | None = None,
        ) -> list[ConnectorRefreshRun]:
            assert connector_id == "google_merchant_center"
            return [run]

    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "123456789")
    monkeypatch.setattr("wilq.connectors.registry.google_credentials_available", lambda: True)
    monkeypatch.setattr("wilq.connectors.registry.local_state_store", lambda: FakeStateStore())

    connector = get_connector_status("google_merchant_center")

    assert connector is not None
    assert connector.configured is True
    assert connector.last_success_at == completed_at
    assert connector.freshness.state == "fresh"
    assert connector.freshness.last_success_at == completed_at
    assert "udany odczyt danych zewnętrznych" in (connector.freshness.notes or "")


def test_metric_fact_hydrates_operator_metric_label() -> None:
    fact = MetricFact(
        name="clicks",
        value=42,
        period="connector_refresh",
        source_connector="google_search_console",
        evidence_id="ev_metric_fact_label",
    )

    assert fact.metric_label == "kliknięcia z GSC"
    assert fact.dimension_labels == {}
    assert fact.dimension_value_labels == {}


def test_metric_fact_unknown_raw_name_uses_neutral_polish_label() -> None:
    fact = MetricFact(
        name="vendor_metric_that_drifted",
        value=1,
        period="connector_refresh",
        source_connector="vendor",
        evidence_id="ev_metric_fact_unknown_label",
    )

    assert fact.metric_label == "metryka źródłowa"


def test_metric_fact_hydrates_known_ahrefs_metric_label() -> None:
    fact = MetricFact(
        name="ahrefs_competitor_page_count",
        value=5,
        period="connector_refresh",
        source_connector="ahrefs",
        evidence_id="ev_metric_fact_ahrefs_label",
    )

    assert fact.metric_label == "strony konkurencji"


def test_metric_fact_preserves_marketer_useful_dimension_values() -> None:
    fact = MetricFact(
        name="clicks",
        value=14,
        period="connector_refresh",
        source_connector="google_search_console",
        evidence_id="ev_metric_fact_dimension_values",
        dimensions={
            "page": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
            "query": "zielony ład co to",
            "country": "PL",
            "landing_page": "(not set)",
            "campaign_name": "(organic)",
        },
    )

    assert fact.dimension_value_labels["page"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert fact.dimension_value_labels["query"] == "zielony ład co to"
    assert fact.dimension_value_labels["country"] == "Polska"
    assert fact.dimension_value_labels["landing_page"] == ("brak wartości w danych źródłowych")
    assert fact.dimension_value_labels["campaign_name"] == "ruch organiczny"


def test_ads_campaign_rows_hydrate_operator_enum_labels() -> None:
    metric_row = AdsCampaignMetricRow(
        campaign_name="Brand Search",
        campaign_status="ENABLED",
        advertising_channel_type="SEARCH",
    )
    triage_row = AdsCampaignTriageRow(
        campaign_name="Brand Search",
        campaign_status="PAUSED",
        advertising_channel_type="DEMAND_GEN",
        review_reason="Do sprawdzenia.",
        next_step="Sprawdź kampanię.",
    )

    assert metric_row.campaign_status_label == "aktywna"
    assert metric_row.advertising_channel_type_label == "sieć wyszukiwania"
    assert triage_row.campaign_status_label == "wstrzymana"
    assert triage_row.advertising_channel_type_label == "Demand Gen"
