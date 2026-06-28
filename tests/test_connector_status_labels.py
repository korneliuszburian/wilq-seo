from __future__ import annotations

from wilq.schemas import (
    AdsCampaignMetricRow,
    AdsCampaignTriageRow,
    ConnectorCapability,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
    MetricFact,
    connector_status_label,
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
    assert connector_status_label("vendor_status_that_drifted") == (
        "status źródła do sprawdzenia"
    )


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
