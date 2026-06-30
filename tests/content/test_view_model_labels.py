from __future__ import annotations

from wilq.content.view_models.labels import (
    content_connector_with_api_label,
    content_live_data_status_label,
    content_metric_fact_with_api_label,
    content_refresh_with_api_label,
    content_section_with_api_labels,
)
from wilq.schemas import (
    ActionRisk,
    ConnectorCapability,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    ContentDiagnosticSection,
    FreshnessState,
    MetricFact,
)


def test_content_view_labels_keep_content_specific_connector_copy() -> None:
    connector = ConnectorStatus(
        id="wordpress_ekologus",
        label="WordPress Ekologus",
        status=ConnectorStatusValue.missing_credentials,
        configured=False,
        freshness=FreshnessState(state="missing"),
        capabilities=ConnectorCapability(read=True, write=False),
        health_check="missing_credentials",
    )
    labelled = content_connector_with_api_label(connector)

    assert labelled.status_label == "brakuje dostępu"
    assert content_live_data_status_label(True) == "dane GSC i WordPress dostępne"
    assert content_live_data_status_label(False) == "brak danych GSC lub WordPress do decyzji"


def test_content_view_labels_metric_refresh_and_section_fields() -> None:
    fact = MetricFact(
        name="content_object_seen",
        value=1,
        period="last_28_days",
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp_seen",
    )
    refresh = ConnectorRefreshRun(
        id="refresh_wp",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_wp_seen"],
        vendor_data_collected=True,
        summary="Spis treści odczytany.",
    )
    section = ContentDiagnosticSection(
        id="content_inventory_match",
        title="WordPress: ochrona przed duplikacją",
        status="ready",
        summary="WILQ ma spis treści.",
        diagnosis="Spis treści chroni przed duplikacją.",
        next_step="Sprawdź plan odświeżenia.",
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_seen"],
        metric_facts=[fact],
        action_ids=["act_prepare_content_refresh_queue"],
        blocked_claims=["ranking_guarantee"],
        risk=ActionRisk.low,
    )

    assert content_metric_fact_with_api_label(fact).metric_label == "Treść w spisie"
    assert content_refresh_with_api_label(refresh).status_label == "zakończony"

    labelled_section = content_section_with_api_labels(section)

    assert labelled_section.metric_facts[0].metric_label == "Treść w spisie"
    assert labelled_section.evidence_summary_label
    assert labelled_section.action_summary_label
    assert labelled_section.blocked_claim_labels == ["gwarancja wzrostu pozycji"]
