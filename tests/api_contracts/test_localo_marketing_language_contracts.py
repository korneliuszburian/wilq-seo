from __future__ import annotations

from datetime import UTC, datetime

import pytest

from wilq.briefing.marketing_brief import build_marketing_brief
from wilq.schemas import (
    ConnectorCapability,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
    MetricFact,
)


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

    brief = build_marketing_brief(connectors=connectors, refresh_runs=[], actions=[])

    what_we_know = next(section for section in brief.sections if section.id == "what_we_know")
    localo_item = next(item for item in what_we_know.items if item.source_connectors == ["localo"])
    assert localo_item.title == "Localo: widoczność lokalna i opinie do sprawdzenia"
    assert "localo_total_keyword_volume =" not in localo_item.title
    assert "23" in localo_item.summary
    assert "798" in localo_item.summary
    labels_by_name = {fact.name: fact.metric_label for fact in localo_item.metric_facts}
    assert labels_by_name["localo_tracked_keyword_count"] == "monitorowane frazy"
    assert labels_by_name["localo_avg_visibility_current"] == "średnia widoczność"
    assert labels_by_name["localo_reviews_count"] == "opinie"
    assert labels_by_name["localo_total_keyword_volume"] == "łączny wolumen fraz"


def test_marketing_brief_omits_metric_facts_from_blocked_localo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlockedLocaloMetricStore:
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
                        name="localo_avg_visibility_current",
                        value=53.17,
                        period="connector_refresh",
                        source_connector="localo",
                        evidence_id="ev_refresh_localo_blocked_metric",
                    )
                ]
            }

    monkeypatch.setattr("wilq.briefing.marketing_brief.metric_store", BlockedLocaloMetricStore)
    connector = ConnectorStatus(
        id="localo",
        label="Localo",
        status=ConnectorStatusValue.auth_error,
        configured=True,
        missing_credentials=[],
        freshness=FreshnessState(state="stale"),
        capabilities=ConnectorCapability(read=True),
        health_check="auth_error",
    )
    refresh_run = ConnectorRefreshRun(
        id="refresh_localo_blocked_metric",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.blocked,
        completed_at=datetime.now(UTC),
        evidence_ids=["ev_refresh_localo_blocked_metric"],
        external_call_attempted=True,
        vendor_data_collected=False,
        summary="Localo read blocked.",
    )
    brief = build_marketing_brief(
        connectors=[connector],
        refresh_runs=[refresh_run],
        actions=[],
    )

    known = next(section for section in brief.sections if section.id == "what_we_know")
    assert all(item.source_connectors != ["localo"] for item in known.items)
    blockers = next(section for section in brief.sections if section.id == "what_blocks_us")
    assert any(item.source_connectors == ["localo"] for item in blockers.items)
    recommendations = next(
        section for section in brief.sections if section.id == "recommended_focus"
    )
    assert all(item.source_connectors != ["localo"] for item in recommendations.items)


def test_marketing_brief_localo_blocker_uses_marketer_copy() -> None:
    connector = ConnectorStatus(
        id="localo",
        label="Localo",
        status=ConnectorStatusValue.auth_error,
        configured=True,
        missing_credentials=[],
        freshness=FreshnessState(state="stale"),
        capabilities=ConnectorCapability(read=True),
        health_check="auth_error",
    )
    refresh_run = ConnectorRefreshRun(
        id="refresh_localo_access_blocked",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.blocked,
        completed_at=datetime.now(UTC),
        evidence_ids=["ev_refresh_localo_access_blocked"],
        external_call_attempted=True,
        vendor_data_collected=False,
        metric_summary={"access_token_present": 0},
        summary="Localo access blocked.",
        errors=["LOCALO_ACCESS_TOKEN is missing."],
    )
    brief = build_marketing_brief(connectors=[connector], refresh_runs=[refresh_run], actions=[])
    blockers = next(section for section in brief.sections if section.id == "what_blocks_us").items
    localo_blocker = next(item for item in blockers if item.source_connectors == ["localo"])
    visible_copy = " ".join(
        [
            localo_blocker.title,
            localo_blocker.summary,
            localo_blocker.next_step,
            localo_blocker.blocker_reason or "",
            localo_blocker.evidence_summary_label,
            " ".join(localo_blocker.source_connector_labels),
        ]
    )
    assert "Localo" in localo_blocker.source_connector_labels
    assert localo_blocker.evidence_summary_label == "1 dowód źródłowy"
    assert "OAuth" not in visible_copy
    assert "access token" not in visible_copy.lower()
    assert "LOCALO_ACCESS_TOKEN" not in visible_copy
    assert "refresh_localo_access_blocked" not in visible_copy
