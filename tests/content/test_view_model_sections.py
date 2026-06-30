from __future__ import annotations

from wilq.content.view_models.sections import (
    content_action_safety_section,
    inventory_match_section,
    query_page_section,
)
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)


def _metric_fact(
    name: str,
    value: int | float | str,
    source_connector: str,
    evidence_id: str,
    **dimensions: str,
) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="last_28_days",
        source_connector=source_connector,
        evidence_id=evidence_id,
        dimensions=dimensions,
    )


def _tactical_item(**dimensions: str) -> TacticalQueueItem:
    return TacticalQueueItem(
        id="queue_content_bdo",
        title="BDO",
        domain=OpportunityDomain.gsc_seo,
        intent="content_refresh",
        priority=20,
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_queue_bdo"],
        diagnosis="GSC pokazuje popyt.",
        next_step="Sprawdź plan odświeżenia.",
        dimensions=dimensions,
    )


def _refresh_run(connector_id: str, evidence_id: str) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id=f"refresh_{connector_id}",
        connector_id=connector_id,
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=[evidence_id],
        vendor_data_collected=True,
        summary=f"Odczyt {connector_id} zakończony.",
    )


def test_query_page_section_blocks_without_gsc_query_page_evidence() -> None:
    section = query_page_section(
        latest_refreshes=[],
        facts=[],
        tactical_items=[],
        action_ids=["act_prepare_content_refresh_queue"],
        knowledge_card_ids=("card_gsc_seo_content_playbook",),
        expert_rule_ids=("seo_query_page_matrix_v1",),
    )

    assert section.id == "content_query_page_matrix"
    assert section.status == "blocked"
    assert section.source_connectors == ["google_search_console"]
    assert section.evidence_ids == ["ev_connector_google_search_console_status"]
    assert "GSC" in section.title


def test_query_page_section_uses_gsc_items_and_query_page_facts() -> None:
    item = _tactical_item(query="bdo odpady", page="https://www.ekologus.pl/bdo/")
    facts = [
        _metric_fact(
            "impressions",
            300,
            "google_search_console",
            "ev_gsc_impressions",
            query="bdo odpady",
            page="https://www.ekologus.pl/bdo/",
        )
    ]

    section = query_page_section(
        latest_refreshes=[],
        facts=facts,
        tactical_items=[item],
        action_ids=["act_prepare_content_refresh_queue"],
        knowledge_card_ids=("card_gsc_seo_content_playbook",),
        expert_rule_ids=("seo_query_page_matrix_v1",),
    )

    assert section.status == "ready"
    assert section.metric_facts == facts
    assert section.tactical_items == [item]
    assert section.evidence_ids == ["ev_gsc_impressions", "ev_queue_bdo"]


def test_inventory_match_section_defends_preserve_first_inventory_logic() -> None:
    item = _tactical_item(wordpress_match="found")
    inventory_fact = _metric_fact(
        "content_object_seen",
        1,
        "wordpress_ekologus",
        "ev_wp_seen",
        url="https://www.ekologus.pl/bdo/",
    )

    section = inventory_match_section(
        latest_refreshes=[],
        facts=[inventory_fact],
        tactical_items=[item],
        action_ids=["act_prepare_content_refresh_queue"],
        knowledge_card_ids=("card_wordpress_content_refresh_playbook",),
        expert_rule_ids=("content_duplication_rules_v1",),
    )

    assert section.status == "ready"
    assert section.source_connectors == ["wordpress_ekologus"]
    assert section.metric_facts == [inventory_fact]
    assert section.tactical_items == [item]
    assert "drugi raz tego samego" in section.diagnosis


def test_content_action_safety_section_keeps_prepare_only_guardrail() -> None:
    section = content_action_safety_section(
        latest_refreshes=[_refresh_run("google_search_console", "ev_gsc_refresh")],
        facts=[],
        tactical_items=[_tactical_item()],
        action_ids=["act_prepare_content_refresh_queue"],
        content_connector_ids=("google_search_console", "wordpress_ekologus"),
    )

    assert section.id == "content_action_safety"
    assert section.status == "ready"
    assert section.source_connectors == ["google_search_console", "wordpress_ekologus"]
    assert section.evidence_ids == ["ev_gsc_refresh", "ev_queue_bdo"]
    assert "nie może publikować" in section.diagnosis
