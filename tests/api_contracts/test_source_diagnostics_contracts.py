"""GA4, Localo and Ahrefs source diagnostics API contract tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.ads_review_seed import seed_google_ads_live_review_metric_facts
from tests._contract_support.api_client import client
from tests._contract_support.assertions import assert_preview_items_are_operator_view_models
from tests._contract_support.env import (
    clear_ahrefs_env,
    clear_google_ads_env,
    clear_google_service_env,
    clear_localo_env,
    clear_wordpress_env,
)
from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
)
from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.actions.merchant import _merchant_attribute_key as _action_merchant_attribute_key
from wilq.briefing.command_center import build_daily_decisions
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.merchant_diagnostics import (
    _merchant_attribute_key as _diagnostic_merchant_attribute_key,
)
from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    CommandCenterActionPlanItem,
    ConnectorCapability,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
    KnowledgeCard,
    MetricFact,
    OpportunityDomain,
    TacticalQueueResponse,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store


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
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["live_data_status_label"] == "metryki GA4 dostępne"
    if payload["latest_refresh"] is not None:
        assert payload["latest_refresh_status_label"] == "zakończony"
    assert payload["landing_group_count"] >= 1
    assert payload["low_engagement_count"] >= 1
    assert payload["wordpress_match_count"] >= 1
    assert payload["freshness_assessment"]["state"] == "fresh"
    assert payload["freshness_assessment"]["state_label"] == "dane świeże"
    assert payload["freshness_assessment"]["requires_refresh"] is False
    assert payload["freshness_assessment"]["stale_after_hours"] == 48
    assert "GA4" in payload["freshness_assessment"]["summary"]
    assert payload["source_connector_labels"]
    assert "GA4" in payload["source_connector_labels"]
    assert not any("_" in label for label in payload["source_connector_labels"])
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
    assert all(decision["status_label"] for decision in decision_by_id.values())
    assert all(decision["decision_type_label"] for decision in decision_by_id.values())
    assert all(decision["risk_label"] for decision in decision_by_id.values())
    assert all(decision["blocked_claim_labels"] for decision in decision_by_id.values())
    assert all(
        fact["metric_label"]
        for decision in decision_by_id.values()
        for fact in decision["metric_facts"]
    )
    assert all(
        fact["dimension_labels"].get("source_medium") == "źródło i medium ruchu"
        for decision in decision_by_id.values()
        for fact in decision["metric_facts"]
        if "source_medium" in fact["dimensions"]
    )
    measurement_metric_facts = [
        fact
        for decision in decision_by_id.values()
        for fact in decision["metric_facts"]
        if fact["dimensions"].get("landing_page") == "(not set)"
    ]
    assert all(
        fact["dimension_value_labels"]["landing_page"] == "brak strony wejścia w raporcie"
        for fact in measurement_metric_facts
    )
    assert all(isinstance(decision["priority"], int) for decision in decision_by_id.values())
    assert all(decision["metric_tiles"] for decision in decision_by_id.values())
    assert any("zaangażowanie" in decision["metric_tiles"] for decision in decision_by_id.values())
    assert all(
        decision["knowledge_card_ids"] == ["card_ga4_behavior_diagnostics_playbook"]
        for decision in decision_by_id.values()
    )
    assert all(
        decision["expert_rule_ids"] == ["ga4_diagnostics_v1", "ga4_platform_traps_v1"]
        for decision in decision_by_id.values()
    )
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
    measurement_decisions = [
        decision
        for decision in payload["decision_queue"]
        if decision["decision_type"] == "fix_measurement"
    ]
    measurement_titles = [decision["title"] for decision in measurement_decisions]
    assert len(measurement_titles) == len(set(measurement_titles))
    assert all(
        decision["landing_page"] in decision["title"]
        or decision["source_medium"] in decision["title"]
        or decision["campaign_name"] in decision["title"]
        for decision in measurement_decisions
    )
    assert operator_summary["wordpress_missing_count"] == sum(
        1 for decision in payload["decision_queue"] if decision.get("wordpress_match") == "missing"
    )
    assert operator_summary["action_ids"] == payload["action_ids"]
    assert operator_summary["conversion_readiness_status"] == readiness_contract["status"]
    assert "zwrot z reklam" in operator_summary["blocked_claims"]
    assert "zwrot z reklam" in operator_summary["blocked_claim_labels"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    sections = {section["id"]: section for section in payload["sections"]}
    assert sections["ga4_landing_behavior"]["status"] == "ready"
    assert sections["ga4_landing_behavior"]["label"] == "Jakość ruchu ze stron wejścia"
    assert sections["ga4_landing_behavior"]["status_label"] == "gotowe"
    assert all(
        fact["metric_label"] for section in sections.values() for fact in section["metric_facts"]
    )
    assert "zwrot z reklam" in sections["ga4_landing_behavior"]["blocked_claim_labels"]
    assert sections["ga4_landing_behavior"]["tactical_items"]
    assert (
        sections["ga4_landing_behavior"]["tactical_items"][0]["dimensions"]["landing_page"]
        == "/europejski-zielony-lad-co-to-takiego/"
    )
    assert sections["ga4_tracking_readiness"]["status"] == "missing"
    assert sections["ga4_tracking_readiness"]["status_label"] == (
        "metryki konwersji niepotwierdzone"
    )
    assert "spadek konwersji" in sections["ga4_tracking_readiness"]["blocked_claims"]

    assert sections["ga4_action_safety"]["status"] == "ready"
    assert readiness_contract["id"] == "ga4_conversion_readiness_contract"
    assert readiness_contract["status"] == "blocked"
    assert readiness_contract["status_label"] == "blokuje wnioski o konwersjach"
    assert readiness_contract["conversion_like_metric_count"] == 0
    assert readiness_contract["dimensioned_behavior_metric_count"] >= 1
    assert readiness_contract["landing_group_count"] >= 1
    assert readiness_contract["missing_read_contracts"] == ["conversion_or_key_event_mapping"]
    assert readiness_contract["missing_read_contract_labels"] == [
        "powiązanie konwersji i zdarzeń kluczowych"
    ]
    assert readiness_contract["missing_read_contract_summary_label"] == (
        "1 brakujący zakres danych"
    )
    assert "powiązanie konwersji" in readiness_contract["next_step"]
    assert "mapowanie konwersji" not in json.dumps(payload, ensure_ascii=False)
    assert {
        "conversions",
        "key_events",
        "purchase_revenue",
        "total_revenue",
        "transactions",
    }.issubset(set(readiness_contract["allowed_metrics"]))
    assert "współczynnik konwersji" in readiness_contract["blocked_claims"]
    assert "act_review_ga4_tracking_quality" in readiness_contract["action_ids"]
    assert readiness_contract["evidence_ids"]
    assert payload["blocker_count"] >= 1
    assert payload["decision_blocker_count"] == sum(
        1 for decision in payload["decision_queue"] if decision["status"] == "blocked"
    )

    action_response = client.get("/api/actions/act_review_ga4_tracking_quality")
    assert action_response.status_code == 200
    ga4_action = action_response.json()
    assert ga4_action["payload"]["preview_contract"] == "ga4_tracking_quality_review_v1"
    preview = ga4_action["payload"]["payload_preview"][0]
    assert preview["preview_contract"] == "ga4_tracking_quality_review_v1"
    assert preview["operation_type"] == "tracking_quality_review"
    assert preview["operation_type_label"] == "ocena jakości pomiaru"
    assert len(preview["tracking_dimension_gap_labels"]) == len(preview["tracking_dimension_gaps"])
    assert preview["operation_type_label"] != preview["operation_type"]
    assert preview["metric_snapshot_labels"]["active_users"] == "aktywni użytkownicy"
    assert preview["metric_snapshot_labels"]["engagement_rate"] == "zaangażowanie"
    assert preview["blocked_claim_labels"] == preview["blocked_claims"]
    assert "wniosek GA4 do sprawdzenia" not in preview["blocked_claim_labels"]
    assert len(preview["blocked_claim_labels"]) == len(set(preview["blocked_claim_labels"]))
    assert "review_conversion_or_key_event_mapping" in preview["required_validation"]
    assert preview["apply_allowed"] is False
    assert preview["api_mutation_ready"] is False
    assert preview["destructive"] is False
    assert ga4_action["preview_cards"]
    ga4_preview_card = ga4_action["preview_cards"][0]
    assert ga4_preview_card["kind"] == "ga4_tracking_quality_review"
    assert ga4_preview_card["title_label"] == "Jakość pomiaru GA4 do sprawdzenia"
    ga4_preview_rows = {row["label"]: row["value"] for row in ga4_preview_card["rows"]}
    assert ga4_preview_rows["Strona wejścia"]
    assert ga4_preview_rows["Źródło"]
    assert ga4_preview_rows["Kampania"]
    ga4_marketer_card_text = str(
        {
            key: ga4_preview_card[key]
            for key in ("title_label", "subtitle_label", "status_label", "rows")
        }
    )
    assert "tracking_quality_review" not in ga4_marketer_card_text
    assert "ga4_tracking_quality_review_v1" not in ga4_marketer_card_text
    assert "active_users" not in ga4_marketer_card_text
    assert "source_metric_names" not in ga4_marketer_card_text
    assert "wniosek GA4 do sprawdzenia" not in ga4_marketer_card_text

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
    assert set(context_action_by_id) == {"act_review_ga4_tracking_quality"}
    assert "payload" not in context_action_by_id["act_review_ga4_tracking_quality"]
    assert "action_plan" in context_action_by_id["act_review_ga4_tracking_quality"]
    context_action_plan = context_action_by_id["act_review_ga4_tracking_quality"]["action_plan"]
    assert "required_breakdowns" not in context_action_plan
    assert "required_breakdown_labels" not in context_action_plan
    assert context_action_plan["required_dimension_labels"] == [
        "strona wejścia",
        "źródło i medium ruchu",
        "kampania",
    ]
    context_preview = context_action_plan["preview_items"][0]
    assert (
        context_preview["metric_tiles"]["aktywni użytkownicy"]
        == preview["metric_snapshot"]["active_users"]
    )
    assert context_preview["apply_status_label"] == "zablokowane do sprawdzenia"
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "google_adc.json" not in serialized


def test_ga4_operator_summary_uses_conversion_ready_copy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_ready_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_ready_metrics.duckdb"))
    facts = [
        MetricFact(
            name="active_users",
            value=12,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_ready_conversion",
            dimensions={
                "landing_page": "/oferta/",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
        MetricFact(
            name="key_events",
            value=0,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_ready_conversion",
            dimensions={
                "landing_page": "/oferta/",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
        MetricFact(
            name="purchase_revenue",
            value=0,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_ready_conversion",
            dimensions={
                "landing_page": "/oferta/",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
    ]

    payload = build_ga4_diagnostics(tactical_items=[], actions=[], metric_facts=facts)

    assert payload.conversion_readiness_contract.status == "ready"
    assert payload.conversion_readiness_contract.conversion_like_metric_count == 2
    assert payload.conversion_readiness_contract.missing_read_contracts == []
    assert (
        payload.conversion_readiness_contract.missing_read_contract_summary_label
        == "Dane kompletne dla tej decyzji"
    )
    assert "Brak metryk konwersji" not in payload.operator_summary.summary
    assert "metryki konwersji" in payload.operator_summary.summary
    assert "zwrot z reklam" in payload.operator_summary.blocked_claims


def test_ga4_diagnostics_preserves_dimensioned_landing_facts_after_aggregate_noise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_wide_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_wide_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    clear_wordpress_env(monkeypatch)
    service_account_json = tmp_path / "google_adc.json"
    service_account_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(service_account_json))
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")
    landing_path = "/europejski-zielony-lad-co-to-takiego/"
    landing_url = f"https://www.ekologus.pl{landing_path}"
    homepage_path = "/"
    homepage_url = "https://www.ekologus.pl/"
    completed_at = datetime(2026, 6, 23, 8, 0, tzinfo=UTC)
    ga4_dimensioned_run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_wide_dimensioned_test",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_analytics_4_wide_dimensioned_test"],
        completed_at=completed_at,
        metric_summary={},
        vendor_data_collected=True,
        summary="GA4 wide dimensioned test seed.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ekologus_ga4_wide_match_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ekologus_ga4_wide_match_test"],
        metric_summary={"content_object_count": 1},
        vendor_data_collected=True,
        summary="WordPress GA4 wide match seed.",
    )
    local_state_store().save_connector_refresh_run(ga4_dimensioned_run)
    local_state_store().save_connector_refresh_run(wordpress_run)
    metric_store().save_connector_refresh_metrics(
        ga4_dimensioned_run,
        detailed_facts=[
            *[
                VendorMetricFact(
                    name="noise_metric",
                    value=index,
                    dimensions={"aaa_noise": f"{index:03d}"},
                )
                for index in range(350)
            ],
            VendorMetricFact(
                name="active_users",
                value=41,
                dimensions={
                    "landing_page": landing_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=54,
                dimensions={
                    "landing_page": landing_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="engagement_rate",
                value=0.12,
                dimensions={
                    "landing_page": landing_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="active_users",
                value=80,
                dimensions={
                    "landing_page": homepage_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=100,
                dimensions={
                    "landing_page": homepage_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
                },
            ),
            VendorMetricFact(
                name="engagement_rate",
                value=0.42,
                dimensions={
                    "landing_page": homepage_path,
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Ogólna",
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
                    "content_type": "sitemap",
                    "content_url": landing_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            ),
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": homepage_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                },
            ),
        ],
    )

    response = client.get("/api/ga4/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["wordpress_match_count"] >= 1
    decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["landing_page"] == landing_path
    )
    assert decision["wordpress_match"] == "found"
    assert decision["wordpress_match_confidence"] == "path_fallback"
    assert decision["wordpress_content_url"] == landing_url
    homepage_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["landing_page"] == homepage_path
    )
    assert homepage_decision["wordpress_match"] == "found"
    assert homepage_decision["wordpress_match_confidence"] == "path_fallback"
    assert homepage_decision["wordpress_content_url"] == homepage_url


def test_ga4_diagnostics_marks_stale_refresh_as_stale_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_stale_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_stale_metrics.duckdb"))
    completed_at = datetime.now(UTC) - timedelta(hours=72)
    run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_stale_test",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=completed_at,
        evidence_ids=["ev_refresh_refresh_google_analytics_4_stale_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"active_users": 20, "sessions": 30},
        summary="GA4 stale diagnostics seed.",
    )
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name="active_users",
                value=20,
                dimensions={
                    "landing_page": "/oferta/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Test",
                },
            ),
            VendorMetricFact(
                name="sessions",
                value=30,
                dimensions={
                    "landing_page": "/oferta/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Test",
                },
            ),
        ],
    )

    response = client.get("/api/ga4/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    freshness = payload["freshness_assessment"]
    assert freshness["state"] == "stale"
    assert freshness["requires_refresh"] is True
    assert freshness["stale_after_hours"] == 48
    assert freshness["latest_refresh_id"] == "refresh_google_analytics_4_stale_test"
    assert freshness["age_hours"] >= 72
    assert "do odświeżenia" in freshness["summary"]
    assert "odczyt danych GA4" in freshness["next_step"]
    assert "odświeżenia" in payload["operator_summary"]["summary"]


def test_ga4_diagnostics_exposes_incomplete_metric_persistence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ga4_incomplete_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ga4_incomplete_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")
    run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_incomplete_metrics_test",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_analytics_4_incomplete_metrics_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metrics_persisted=False,
        metric_summary={"active_users": 20, "sessions": 30},
        summary="GA4 vendor read completed, but metrics were not persisted.",
    )
    local_state_store().save_connector_refresh_run(run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name="active_users",
                value=20,
                dimensions={
                    "landing_page": "/oferta/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Ekologus Test",
                },
            )
        ],
    )

    response = client.get("/api/ga4/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is False
    assert payload["freshness_assessment"]["state"] == "blocked"
    assert "odczyt niepełny - metryki nieutrwalone" in payload["freshness_assessment"]["summary"]
    assert payload["latest_refresh"]["metrics_persisted"] is False
    assert payload["latest_refresh"]["status_label"] == "odczyt niepełny - metryki nieutrwalone"
    assert payload["latest_refresh_status_label"] == "odczyt niepełny - metryki nieutrwalone"


def test_ga4_measurement_decision_titles_include_reporting_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GA4_PROPERTY_ID", "411974093")
    facts = [
        MetricFact(
            name="active_users",
            value=179,
            period="last_7_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_not_set",
            dimensions={
                "landing_page": "(not set)",
                "source_medium": "(not set)",
                "campaign_name": "(not set)",
            },
        ),
        MetricFact(
            name="active_users",
            value=89,
            period="last_7_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_organic",
            dimensions={
                "landing_page": "(not set)",
                "source_medium": "google / organic",
                "campaign_name": "(organic)",
            },
        ),
    ]

    payload = build_ga4_diagnostics(tactical_items=[], actions=[], metric_facts=facts)

    decisions = [
        decision
        for decision in payload.decision_queue
        if decision.decision_type == "fix_measurement"
    ]
    titles = [decision.title for decision in decisions]
    assert titles == [
        "GA4: napraw pomiar - brak strony wejścia w raporcie; źródło ruchu: "
        "brak źródła i medium w raporcie",
        "GA4: napraw pomiar - brak strony wejścia w raporcie; źródło ruchu: google / organic",
    ]
    assert all(" / brak" not in title for title in titles)
    assert decisions[0].landing_page_label == "brak strony wejścia w raporcie"
    assert decisions[0].source_medium_label == "brak źródła i medium w raporcie"
    assert decisions[0].campaign_name_label == "brak kampanii w raporcie"
    assert decisions[0].source_connector_labels == ["GA4"]
    assert decisions[0].evidence_summary_label == "1 dowód źródłowy"
    assert decisions[0].action_summary_label == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    assert payload.evidence_summary_label == "4 dowody źródłowe"
    assert payload.action_summary_label == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    assert (
        payload.operator_summary.action_summary_label
        == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
    assert (
        payload.conversion_readiness_contract.action_summary_label
        == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )


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
    assert brief_by_id["daily_content_queue"]["title"] == ("Treści: kolejka SEO z GSC i WordPress")
    assert "WordPress potwierdza istniejącą stronę" in brief_by_id["daily_content_queue"]["summary"]
    assert "ahrefs" in brief_by_id["daily_content_queue"]["source_connectors"]
    assert (
        "ev_refresh_refresh_ahrefs_action_test"
        in brief_by_id["daily_content_queue"]["evidence_ids"]
    )
    if (
        "ev_refresh_refresh_google_analytics_4_action_test"
        in brief_by_id["daily_content_queue"]["evidence_ids"]
    ):
        assert "google_analytics_4" in brief_by_id["daily_content_queue"]["source_connectors"]
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["zapytania i adresy z GSC"] >= 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["decyzje"] >= 2
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["ocena Ahrefs"] == 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["luki Ahrefs"] == 1
    assert brief_by_id["daily_content_queue"]["metric_tiles"]["wyświetlenia"] >= 1
    assert "query/page" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "WP match" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "Ahrefs review" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "link gaps" not in brief_by_id["daily_content_queue"]["metric_tiles"]
    assert "act_prepare_content_refresh_queue" in brief_by_id["daily_content_queue"]["action_ids"]
    assert brief_by_id["daily_ga4_landing_quality"]["status"] == "blocked"
    assert "pomiar i jakość ruchu" in brief_by_id["daily_ga4_landing_quality"]["title"]
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["grupy ruchu"] >= 1
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["decyzje"] >= 1
    assert brief_by_id["daily_ga4_landing_quality"]["metric_tiles"]["brakujące dane"] == 1
    assert "werdykt zwrotu z reklam" in brief_by_id["daily_ga4_landing_quality"]["blocked_claims"]
    assert (
        "act_review_ga4_tracking_quality" in brief_by_id["daily_ga4_landing_quality"]["action_ids"]
    )
    assert all(item["evidence_ids"] for item in payload["operator_brief"])
    assert payload["demo_script"] == []
    plan_by_id = {item["id"]: item for item in payload["action_plan"]}
    assert plan_by_id["plan_review_merchant_feed_issues"]["route"] == "/merchant"
    assert plan_by_id["plan_review_merchant_feed_issues"]["skill_id"] == (
        "wilq-merchant-feed-operator"
    )
    assert (
        "Użyj skilla wilq-merchant-feed-operator"
        in plan_by_id["plan_review_merchant_feed_issues"]["codex_prompt"]
    )
    assert plan_by_id["plan_review_merchant_feed_issues"]["codex_context_endpoint"] == (
        "/api/codex/context-pack"
    )
    assert plan_by_id["plan_prepare_content_refresh_queue"]["route"] == "/content-workflow"
    assert plan_by_id["plan_prepare_content_refresh_queue"]["skill_id"] == (
        "wilq-content-strategist"
    )
    if (
        "ev_refresh_refresh_google_analytics_4_action_test"
        in plan_by_id["plan_prepare_content_refresh_queue"]["evidence_ids"]
    ):
        assert (
            "google_analytics_4"
            in plan_by_id["plan_prepare_content_refresh_queue"]["source_connectors"]
        )
    assert plan_by_id["plan_review_ga4_landing_quality"]["route"] == "/ga4"
    assert plan_by_id["plan_review_ga4_landing_quality"]["skill_id"] == "wilq-ga4-analyst"
    assert plan_by_id["plan_review_ga4_landing_quality"]["status"] == "blocked"
    assert "pomiar i jakość ruchu" in plan_by_id["plan_review_ga4_landing_quality"]["title"]
    assert (
        "decyzję GA4 do sprawdzenia"
        in plan_by_id["plan_review_ga4_landing_quality"]["why_it_matters"]
    )
    assert (
        "propozycję przeglądu GA4 w WILQ"
        in plan_by_id["plan_review_ga4_landing_quality"]["operator_action"]
    )
    assert (
        "Zapis zmian wymaga sprawdzenia"
        in plan_by_id["plan_review_ga4_landing_quality"]["operator_action"]
    )
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["status"] == "blocked"
    assert plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["skill_id"] == ("wilq-ads-doctor")
    assert (
        "blokada do sprawdzenia"
        not in plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["blocked_claims"]
    )
    assert (
        "wydatki reklamowe"
        in plan_by_id["plan_fix_ads_oauth_before_spend_analysis"]["blocked_claims"]
    )
    decisions_by_id = {item["id"]: item for item in payload["daily_decisions"]}
    visible_blocked_claims = [
        claim
        for surface in (
            payload["operator_brief"],
            payload["action_plan"],
            payload["daily_decisions"],
        )
        for item in surface
        for claim in [
            *item.get("blocked_claims", []),
            *item.get("blocked_claim_labels", []),
        ]
    ]
    assert "blokada do sprawdzenia" not in visible_blocked_claims
    merchant_decision = decisions_by_id["decision_review_merchant_feed_issues"]
    merchant_metric_facts = merchant_decision["metric_facts"]
    assert merchant_metric_facts
    assert all(fact["metric_label"] for fact in merchant_metric_facts)
    assert not any(
        label == "wymiar"
        for fact in merchant_metric_facts
        for label in fact["dimension_labels"].values()
    )
    assert not any(
        label == "wartość wymiaru do sprawdzenia"
        for fact in merchant_metric_facts
        for label in fact["dimension_value_labels"].values()
    )
    assert not any(
        label == "wymiar Merchant do sprawdzenia"
        for fact in merchant_metric_facts
        for label in fact["dimension_labels"].values()
    )
    assert not any(
        label == "wartość Merchant do sprawdzenia"
        for fact in merchant_metric_facts
        for label in fact["dimension_value_labels"].values()
    )
    reporting_context_labels = [
        fact["dimension_value_labels"]["reporting_context"]
        for fact in merchant_metric_facts
        if "reporting_context" in fact["dimension_value_labels"]
    ]
    if reporting_context_labels:
        assert set(reporting_context_labels).issubset(
            {"reklamy produktowe", "bezpłatne wyniki produktowe", "wszystkie konteksty"}
        )
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
    assert merchant_decision["domain"] == "merchant"
    assert merchant_decision["freshness"]["state"] in {"fresh", "stale", "unknown", "missing"}
    assert merchant_decision["freshness_label"] in {
        "świeże dane",
        "dane wymagają odświeżenia",
        "świeżość danych niepotwierdzona",
        "świeżość niepotwierdzona",
    }
    assert merchant_decision["decision_state"] in {
        "ready",
        "stale",
        "blocked",
        "missing",
        "unknown",
    }
    if merchant_decision["freshness"]["state"] == "stale":
        assert merchant_decision["decision_state"] == "stale"
    assert "Świeżość źródeł decyzji" in merchant_decision["freshness"]["notes"]
    assert "google_merchant_center=" not in merchant_decision["freshness"]["notes"]
    assert "=fresh" not in merchant_decision["freshness"]["notes"]
    assert "=stale" not in merchant_decision["freshness"]["notes"]
    assert "Merchant Center:" in merchant_decision["freshness"]["notes"]
    assert merchant_decision["co_widzimy"].startswith("Merchant Center ma")
    assert merchant_decision["priority_label"] == "najpierw"
    assert merchant_decision["decision_state_label"] in {
        "gotowe",
        "do odświeżenia",
        "zablokowane",
        "dane niepotwierdzone",
        "status niepotwierdzony",
    }
    assert merchant_decision["route_label"] == "Merchant Center"
    assert merchant_decision["cta_label"] == "Otwórz Merchant Center"
    assert merchant_decision["source_connector_labels"]
    assert merchant_decision["evidence_summary"].endswith("śladów w WILQ") or (
        merchant_decision["evidence_summary"].endswith("ślad w WILQ")
    )
    assert merchant_decision["action_summary"].endswith("akcja do sprawdzenia") or (
        merchant_decision["action_summary"].endswith("akcji do sprawdzenia")
    )
    assert merchant_decision["blocked_claim_labels"]
    assert merchant_decision["skill_label"] == "plik produktowy Merchant"
    assert merchant_decision["metric_tiles"]["produkty"] == 10900
    assert merchant_decision["metric_tiles"]["zgłoszenia"] == 3
    assert merchant_decision["metric_tiles"]["decyzje"] >= 1
    assert merchant_decision["metric_facts"]
    assert len(merchant_decision["metric_facts"]) <= 8
    assert {fact["source_connector"] for fact in merchant_decision["metric_facts"]} == {
        "google_merchant_center"
    }
    assert "status=ready" not in merchant_decision["co_widzimy"]
    for decision in decisions_by_id.values():
        assert "Źródła=" not in decision["co_widzimy"]
        assert "dowody=" not in decision["co_widzimy"]
        assert "akcje=" not in decision["co_widzimy"]
    assert (
        merchant_decision["dlaczego_to_ma_znaczenie"]
        == plan_by_id["plan_review_merchant_feed_issues"]["why_it_matters"]
    )
    assert (
        merchant_decision["why_it_matters"]
        == plan_by_id["plan_review_merchant_feed_issues"]["why_it_matters"]
    )
    if merchant_decision["decision_state"] == "ready":
        assert (
            merchant_decision["bezpieczny_next_step"]
            == plan_by_id["plan_review_merchant_feed_issues"]["operator_action"]
        )
    else:
        assert merchant_decision["bezpieczny_next_step"].startswith("Najpierw")
        assert any(
            phrase in merchant_decision["bezpieczny_next_step"]
            for phrase in ("odśwież dane", "potwierdź dostęp")
        )
    assert merchant_decision["operator_action"] == merchant_decision["bezpieczny_next_step"]
    assert merchant_decision["skill_id"] == "wilq-merchant-feed-operator"
    assert "Użyj skilla wilq-merchant-feed-operator" in merchant_decision["codex_prompt"]
    assert merchant_decision["evidence_ids"]
    assert merchant_decision["blocked_claims"]
    ga4_decision = decisions_by_id["decision_review_ga4_landing_quality"]
    content_decision = decisions_by_id["decision_prepare_content_refresh_queue"]
    assert content_decision["domain"] == "content"
    assert "act_prepare_content_refresh_queue" in content_decision["action_ids"]
    assert "act_prepare_wordpress_draft_handoff" in content_decision["action_ids"]
    content_fact_sources = {fact["source_connector"] for fact in content_decision["metric_facts"]}
    assert {"google_search_console", "ahrefs"}.issubset(content_fact_sources)
    if "google_analytics_4" in content_fact_sources:
        assert "google_analytics_4" in content_decision["source_connectors"]
    content_ahrefs_facts = [
        fact for fact in content_decision["metric_facts"] if fact["source_connector"] == "ahrefs"
    ]
    assert content_ahrefs_facts
    assert all(
        fact["dimensions"].get("competitor_domain") != "cuk.pl" for fact in content_ahrefs_facts
    )
    assert all(
        "prawo jazdy" not in fact["dimensions"].get("keyword", "") for fact in content_ahrefs_facts
    )
    if "decision_review_ads_campaign_metrics" in decisions_by_id:
        assert decisions_by_id["decision_review_ads_campaign_metrics"]["domain"] == "google_ads"
    assert ga4_decision["status"] == "blocked"
    assert ga4_decision["decision_state"] == "blocked"
    assert ga4_decision["domain"] == "ga4"
    assert "pomiar i jakość ruchu" in ga4_decision["title"]
    assert ga4_decision["metric_tiles"]["grupy ruchu"] >= 1
    assert ga4_decision["metric_tiles"]["decyzje"] >= 1
    assert "stron wejścia, źródeł ruchu i kampanii" in ga4_decision["co_widzimy"]
    assert "Blokada oznacza" in ga4_decision["co_widzimy"]
    assert "Status blocked" not in ga4_decision["co_widzimy"]
    assert "brak kontraktu" not in ga4_decision["co_widzimy"]
    assert ga4_decision["co_widzimy"].count("Blokada oznacza") == 1
    operator_guidance_text = "\n".join(
        [
            *[item["next_step"] for item in payload["operator_brief"] if item["next_step"]],
            *[item["operator_action"] for item in payload["action_plan"]],
            *[item["bezpieczny_next_step"] for item in payload["daily_decisions"]],
        ]
    )
    assert "`act_" not in operator_guidance_text
    assert "act_review_ga4_tracking_quality" not in operator_guidance_text
    assert "act_confirm_ads_target_guardrails" not in operator_guidance_text

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    context_command = context_response.json()["command_center"]
    assert "operator_brief" not in context_command
    assert "action_plan" not in context_command
    assert "demo_script" not in context_command
    assert context_command["evidence_ids"] == payload["evidence_ids"]
    assert context_command["action_ids"] == payload["action_ids"]
    assert context_command["source_connectors"] == payload["source_connectors"]
    assert context_command["evidence_summary"] == payload["evidence_summary"]
    assert context_command["action_summary"] == payload["action_summary"]
    assert [
        {
            "id": item["id"],
            "domain": item["domain"],
            "decision_state": item["decision_state"],
            "freshness_state": item["freshness"]["state"],
            "metric_fact_count": len(item["metric_facts"]),
            "route": item["route"],
            "status": item["status"],
            "why_it_matters": item["why_it_matters"],
            "operator_action": item["operator_action"],
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
            "domain": item["domain"],
            "decision_state": item["decision_state"],
            "freshness_state": item["freshness"]["state"],
            "metric_fact_count": len(item["metric_facts"]),
            "route": item["route"],
            "status": item["status"],
            "why_it_matters": item["why_it_matters"],
            "operator_action": item["operator_action"],
            "source_connectors": item["source_connectors"],
            "evidence_ids": item["evidence_ids"],
            "action_ids": item["action_ids"],
            "blocked_claims": item["blocked_claims"],
            "skill_id": item["skill_id"],
        }
        for item in payload["daily_decisions"]
    ]
    assert context_command["primary_next_step"] == payload["primary_next_step"]


def test_daily_decision_with_stale_sources_refreshes_before_review() -> None:
    plan_item = CommandCenterActionPlanItem(
        id="plan_review_merchant_feed_issues",
        title="Przejrzyj kolejkę problemów Merchant Center",
        route="/merchant",
        status="ready",
        priority=10,
        category="Merchant Center",
        why_it_matters="WILQ widzi zgłoszenia problemów pliku produktowego.",
        operator_action="Otwórz Merchant i sprawdź kolejkę problemów.",
        expected_codex_output="Polskie podsumowanie problemów pliku produktowego.",
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_refresh_refresh_google_merchant_center_stale"],
        action_ids=["act_review_merchant_feed_issues"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        risk=ActionRisk.medium,
    )
    connector = ConnectorStatus(
        id="google_merchant_center",
        label="Merchant Center",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="stale", notes="Dane wymagają odświeżenia."),
        capabilities=ConnectorCapability(read=True, write=False),
        health_check="test",
    )

    decisions = build_daily_decisions(
        [plan_item],
        operator_brief=[],
        connectors=[connector],
        refresh_runs=[],
    )

    decision = decisions[0]
    assert decision.decision_state == "stale"
    assert decision.decision_state_label == "do odświeżenia"
    assert decision.bezpieczny_next_step.startswith("Najpierw odśwież dane Merchant Center")
    assert decision.operator_action == decision.bezpieczny_next_step
    assert "potem wróć do kolejki problemów" in decision.operator_action
    assert decision.expected_codex_output is not None
    assert "dane wymagają odświeżenia" in decision.expected_codex_output
    assert "ścieżkę odczytu przed ręcznym review" in decision.expected_codex_output


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
    assert ads_item["title"] == "Google Ads: kolejki budżetu, rekomendacji i zapytań"
    assert ads_item["priority"] == 16
    assert ads_item["metric_tiles"]["kampanie"] == 1
    assert ads_item["metric_tiles"]["zapytania"] == 1
    assert ads_item["metric_tiles"]["kliknięcia"] == 12
    assert ads_item["metric_tiles"]["wyświetlenia"] == 120
    assert ads_item["metric_tiles"]["koszt"] == "12 PLN"
    assert "koszt_micros" not in ads_item["metric_tiles"]
    assert ads_item["metric_tiles"]["konwersje"] == 1
    assert ads_item["metric_tiles"]["wartość konwersji"] == "150 PLN"
    assert ads_item["metric_tiles"]["podgląd budżetu"] == 1
    assert ads_item["metric_tiles"]["rekomendacje"] == 1
    assert ads_item["metric_tiles"]["wskaźniki do sprawdzenia"] == 1
    assert ads_item["metric_tiles"]["wiersze kosztu pozyskania celu"] == 1
    assert ads_item["metric_tiles"]["wiersze zwrotu z reklam"] == 1
    assert "kolejki oceny" in ads_item["summary"]
    assert "12 kliknięć" in ads_item["summary"]
    assert "koszt 12 PLN" in ads_item["summary"]
    assert "1 konwersja" in ads_item["summary"]
    assert "1 wiersz wskaźników kampanii" in ads_item["summary"]
    assert "Wskaźniki są sygnałem" in ads_item["summary"]
    assert "Zapis zmian wymaga sprawdzenia" in ads_item["next_step"]
    assert "apply" not in ads_item["next_step"]
    assert "wskaźniki kampanii" in ads_item["next_step"]
    assert "blokada do sprawdzenia" not in ads_item["blocked_claims"]
    assert "werdykt kosztu pozyskania celu" in ads_item["blocked_claims"]
    assert "werdykt zwrotu z reklam" in ads_item["blocked_claims"]
    assert "dodanie wykluczających słów kluczowych" in ads_item["blocked_claims"]
    assert "opłacalność" in ads_item["blocked_claims"]
    assert "zmarnowany budżet" in ads_item["blocked_claims"]
    assert "propozycje wykluczeń" not in ads_item["blocked_claims"]
    assert "act_prepare_ads_campaign_review_queue" in ads_item["action_ids"]
    assert "act_prepare_google_ads_recommendation_review_queue" in ads_item["action_ids"]
    assert "act_review_demand_gen_readiness" not in ads_item["action_ids"]
    assert "act_review_ads_search_term_ngrams" not in ads_item["action_ids"]
    assert ADS_TARGET_CONFIRMATION_ACTION_ID not in ads_item["action_ids"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID not in ads_item["action_ids"]
    ads_business_item = brief_by_id["daily_ads_business_context"]
    assert ads_business_item["status"] == "blocked"
    assert ads_business_item["priority"] == 18
    assert "kontekstu biznesowego" in ads_business_item["title"]
    assert ads_business_item["metric_tiles"]["braki"] == 5
    assert ads_business_item["metric_tiles"]["marża"] == "marża niepodana"
    assert ads_business_item["metric_tiles"]["cel biznesowy"] == "cel niepotwierdzony"
    assert "opłacalność" in ads_business_item["blocked_claims"]
    assert "zmarnowany budżet" in ads_business_item["blocked_claims"]
    assert ads_business_item["action_ids"] == [ADS_BUSINESS_CONTEXT_ACTION_ID]

    plan_by_id = {item["id"]: item for item in payload["action_plan"]}
    ads_plan = plan_by_id["plan_review_ads_campaign_metrics"]
    assert ads_plan["status"] == "ready"
    assert ads_plan["title"] == "Przejrzyj aktualny odczyt Ads bez zapisu zmian"
    assert "12 kliknięć" in ads_plan["why_it_matters"]
    assert "koszt 12 PLN" in ads_plan["why_it_matters"]
    assert "1 konwersja" in ads_plan["why_it_matters"]
    assert "wartość konwersji 150 PLN" in ads_plan["why_it_matters"]
    assert "1 wiersz wskaźników kampanii" in ads_plan["why_it_matters"]
    assert "ocena opłacalności" in ads_plan["why_it_matters"]
    assert "aktualny odczyt" in ads_plan["operator_action"]
    assert "podgląd budżetów" in ads_plan["operator_action"]
    assert "wskaźniki kampanii" in ads_plan["operator_action"]
    assert "nie zapisuj zmian" in ads_plan["operator_action"]
    assert "Użyj skilla wilq-ads-doctor" in ads_plan["codex_prompt"]
    assert "zablokowanymi obietnicami" in ads_plan["expected_codex_output"]
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
    assert ads_decision["metric_tiles"]["wskaźniki do sprawdzenia"] == 1
    assert ads_decision["metric_tiles"]["wiersze kosztu pozyskania celu"] == 1
    assert ads_decision["metric_tiles"]["wiersze zwrotu z reklam"] == 1
    assert "1 budżet do sprawdzenia" in ads_decision["co_widzimy"]
    assert "1 wiersz wskaźników kampanii" in ads_decision["co_widzimy"]
    assert "kolejki oceny" in ads_decision["co_widzimy"]
    assert (
        "kosztu pozyskania celu, zwrotu z reklam i zmarnowanego budżetu"
        in ads_decision["co_widzimy"]
    )
    assert ads_decision["action_ids"] == ads_item["action_ids"]
    assert ads_decision["blocked_claims"] == ads_item["blocked_claims"]
    assert "decision_ads_business_context_before_budget_decisions" not in decisions_by_id
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "wzrost konwersji" not in serialized
    assert "target CPA" not in serialized
    assert "werdykt target CPA" not in serialized
    assert "werdykt target zwrotu z reklam" not in serialized
    assert "ocena zwrotu z reklam" not in serialized

    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    brief_payload = brief_response.json()
    sections_by_id = {section["id"]: section for section in brief_payload["sections"]}
    brief_serialized = json.dumps(brief_payload, ensure_ascii=False)
    assert brief_serialized.count("Google Ads ma kolejki do oceny") <= 1
    assert "Google Ads ma aktualny odczyt do oceny" not in brief_serialized

    metric_items = sections_by_id["what_we_know"]["items"]
    ads_metric_item = next(
        item
        for item in metric_items
        if item["id"] == "brief_decision_decision_review_ads_campaign_metrics"
    )
    assert ads_metric_item["summary"].count("Google Ads ma") == 1
    assert "To są kolejki oceny" not in ads_metric_item["summary"]

    action_items = sections_by_id["safe_next_actions"]["items"]
    ads_action_item = next(
        item
        for item in action_items
        if "act_prepare_ads_campaign_review_queue" in item["action_ids"]
    )
    assert "12 kliknięć" not in ads_action_item["summary"]
    assert "Google Ads ma kolejki do oceny" not in ads_action_item["summary"]

    blockers = sections_by_id["what_blocks_us"]
    blocker_titles = {item["title"] for item in blockers["items"]}
    assert "Google Ads: brakuje kontekstu biznesowego do decyzji budżetowych" in blocker_titles
    blocker_action_ids = {
        action_id for item in blockers["items"] for action_id in item["action_ids"]
    }
    assert ADS_BUSINESS_CONTEXT_ACTION_ID in blocker_action_ids


def test_command_center_ads_daily_card_filters_deep_ads_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from wilq.briefing import command_center

    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    def ads_action(action_id: str) -> ActionObject:
        return ActionObject(
            id=action_id,
            title=f"Ads action {action_id}",
            domain=OpportunityDomain.google_ads,
            connector="google_ads",
            mode=ActionMode.prepare,
            risk=ActionRisk.medium,
            status=ActionStatus.needs_validation,
            evidence_ids=["ev_refresh_refresh_google_ads_command_center_live"],
            human_diagnosis="Ads action test.",
            recommended_reason="Review only.",
            payload={"action_type": action_id},
            validation_status="not_validated",
            created_by="test",
        )

    item = command_center._ads_item_from_facts(
        metric_store().list_metric_facts("google_ads", limit=100),
        [
            ads_action("act_review_demand_gen_readiness"),
            ads_action("act_prepare_ads_campaign_review_queue"),
            ads_action("act_prepare_google_ads_recommendation_review_queue"),
            ads_action("act_review_ads_search_term_ngrams"),
            ads_action("act_prepare_custom_segments_from_search_terms"),
            ads_action("act_prepare_negative_keyword_review_queue"),
            ads_action(ADS_TARGET_CONFIRMATION_ACTION_ID),
            ads_action(ADS_STRATEGY_REVIEW_ACTION_ID),
        ],
    )

    assert item.status == "ready"
    assert item.action_ids == [
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
    ]


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
    assert ads_item["metric_tiles"]["wartość konwersji"] == "2 PLN"
    assert ads_item["metric_tiles"]["podgląd budżetu"] == 18
    assert ads_item["metric_tiles"]["rekomendacje"] == 4
    assert "18 kampanii" in ads_item["summary"]
    assert "koszt 154.05 PLN" in ads_item["summary"]


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
    assert "23 zgłoszenia problemów" in merchant_item["summary"]
    assert "1 decyzja do przejścia" in merchant_item["summary"]
    assert "ev_refresh_refresh_google_merchant_center_latest" in merchant_item["evidence_ids"]
    assert "ev_refresh_refresh_google_merchant_center_older" not in merchant_item["evidence_ids"]


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
    assert "1 decyzja do przejścia" in merchant_item["summary"]


def test_merchant_attribute_keys_are_canonical_matching_keys_not_labels() -> None:
    values = [
        "n:unit_pricing_measure",
        "unit_pricing_measure",
        "unit pricing measure",
        "Unit-Pricing Measure",
    ]

    action_keys = {_action_merchant_attribute_key(value) for value in values}
    diagnostic_keys = {_diagnostic_merchant_attribute_key(value) for value in values}

    assert action_keys == {"unitpricingmeasure"}
    assert diagnostic_keys == {"unitpricingmeasure"}
    assert "_" not in next(iter(action_keys))
    assert " " not in next(iter(action_keys))


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
        lambda **_kwargs: empty_tactical_queue,
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
    assert "1 problem pomiaru" in ga4_item["summary"]
    assert "1 decyzję jakości ruchu" in ga4_item["summary"]
    assert (
        "ev_refresh_refresh_google_analytics_4_command_center_fallback" in ga4_item["evidence_ids"]
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
        lambda **_kwargs: TacticalQueueResponse(strict_instruction="empty tactical queue"),
    )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    payload = response.json()
    ga4_item = {item["id"]: item for item in payload["operator_brief"]}["daily_ga4_landing_quality"]
    assert ga4_item["metric_tiles"]["grupy ruchu"] == 10
    assert ga4_item["metric_tiles"]["decyzje"] == 6
    assert ga4_item["metric_tiles"]["pomiar"] == 2
    assert ga4_item["metric_tiles"]["jakość ruchu"] == 4
    assert "2 problemy pomiaru" in ga4_item["summary"]
    assert "4 decyzje jakości ruchu" in ga4_item["summary"]


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
        summary="Localo Test dostępu completed with local OAuth access token.",
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
    assert localo_brief["metric_tiles"]["dostęp Localo"] == 0


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
        summary="Localo Test dostępu completed with local OAuth access token.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().save_connector_refresh_metrics(localo_run)

    response = client.get("/api/localo/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "odczyt zakończony"
    assert payload["access_probe"]["status"] == "access_ready"
    assert payload["access_probe"]["status_label"] == "dostęp działa"
    assert payload["access_probe"]["mcp_initialize_status"] == 200
    assert payload["access_probe"]["access_check_label"] == "połączenie potwierdzone"
    assert payload["access_probe"]["authorization_code_supported_label"] == "tak"
    assert payload["access_probe"]["authorization_readiness_label"] == "gotowe do połączenia"
    assert payload["access_probe"]["pkce_s256_supported_label"] == "tak"
    assert payload["access_probe"]["secure_readiness_label"] == "bezpieczne połączenie gotowe"
    assert payload["access_probe"]["access_token_present_label"] == "token obecny"
    assert payload["access_probe"]["credential_readiness_label"] == "dostęp lokalny gotowy"
    assert payload["access_probe"]["evidence_summary_label"] == "1 dowód źródłowy"
    assert payload["live_data_available"] is False
    assert payload["visibility_fact_count"] == 0
    assert payload["evidence_ids"] == ["ev_refresh_refresh_localo_access_ready_diag_test"]
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    access_decision = decision_by_id["localo_access_ready_wait_for_visibility_facts"]
    assert access_decision["status"] == "ready"
    assert access_decision["status_label"] == "gotowe"
    assert access_decision["decision_type_label"] == "status źródła"
    assert access_decision["access_status_label"] == "dostęp działa"
    assert access_decision["priority_label"] == "wysoki priorytet"
    assert access_decision["source_connector_labels"] == ["Localo"]
    assert access_decision["evidence_summary_label"] == "1 dowód źródłowy"
    assert access_decision["priority"] == 30
    assert access_decision["metric_tiles"] == {
        "dostęp Localo": 1,
        "dane Localo": 0,
        "brakujące dane": 5,
    }
    assert "local_rankings" in access_decision["missing_read_contracts"]
    assert "rankingi lokalne" in access_decision["missing_read_contract_labels"]
    assert "potwierdzenie dostępu Localo" in access_decision["allowed_evidence_labels"]
    assert "potwierdzenie autoryzacji" in access_decision["allowed_evidence_labels"]
    assert "potwierdzenie lokalnego dostępu" in access_decision["allowed_evidence_labels"]
    assert "obecność tokenu" not in access_decision["allowed_evidence_labels"]
    assert "wyniki profilu firmy w Google" in access_decision["blocked_claims"]
    assert "wyniki profilu firmy w Google" in access_decision["blocked_claim_labels"]
    block_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert block_decision["status"] == "blocked"
    assert block_decision["status_label"] == "zablokowane"
    assert block_decision["source_connector_labels"] == ["Localo"]
    assert block_decision["evidence_summary_label"] == "1 dowód źródłowy"
    assert payload["operator_summary"]["source_connector_labels"] == ["Localo"]
    assert payload["operator_summary"]["evidence_summary_label"] == "1 dowód źródłowy"
    assert block_decision["decision_type_label"] == "blokada obietnic"
    assert block_decision["priority_label"] == "pilne"
    assert block_decision["priority"] == 10
    assert block_decision["metric_tiles"] == {
        "blokady obietnic": 5,
        "brakujące dane": 5,
    }
    assert "poprawa widoczności lokalnej" in block_decision["blocked_claims"]
    assert all(fact["name"] != "mcp_initialize_status" for fact in block_decision["metric_facts"])
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "localo_operator_summary"
    assert operator_summary["title"] == "Co marketer ma wiedzieć o Localo"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["access_status"] == "access_ready"
    assert operator_summary["access_status_label"] == "dostęp działa"
    assert operator_summary["visibility_fact_count"] == 0
    assert "local_rankings" in operator_summary["missing_read_contracts"]
    assert "rankingi lokalne" in operator_summary["missing_read_contract_labels"]
    assert "localo" in operator_summary["source_connectors"]
    assert "ev_refresh_refresh_localo_access_ready_diag_test" in operator_summary["evidence_ids"]
    assert "wyniki profilu firmy w Google" in operator_summary["blocked_claims"]
    assert "wyniki profilu firmy w Google" in operator_summary["blocked_claim_labels"]
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
        summary="Odczyt danych Localo zakończony agregatami.",
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
            errors=["Localo OAuth authorization is incomplete."],
            summary="Późniejszy test dostępu Localo nie przeszedł po udanym odczycie agregatów.",
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
    assert review_decision["status_label"] == "gotowe"
    assert review_decision["decision_type_label"] == "przejrzyj widoczność"
    assert review_decision["access_status_label"] == "dostęp działa"
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
    assert review_decision["missing_read_contract_labels"] == [
        "widoczność profilu firmy w Google",
        "widoczność konkurencji",
        "zadania lokalne",
    ]
    contract_status_by_id = {item["id"]: item for item in payload["read_contract_statuses"]}
    assert contract_status_by_id["place_inventory"]["status"] == "ready"
    assert contract_status_by_id["place_inventory"]["id_label"] == "lista lokalizacji"
    assert contract_status_by_id["place_inventory"]["status_label"] == "gotowe"
    assert contract_status_by_id["local_rankings"]["status"] == "ready"
    assert (
        contract_status_by_id["local_rankings"]["metric_fact_labels"][
            "localo_tracked_keyword_count"
        ]
        == "monitorowane frazy"
    )
    assert contract_status_by_id["reviews"]["status"] == "ready"
    assert contract_status_by_id["gbp_visibility"]["status"] == "missing"
    assert (
        contract_status_by_id["gbp_visibility"]["status_label"] == "zakres danych niepotwierdzony"
    )
    assert contract_status_by_id["gbp_visibility"]["blocked_claims"] == [
        "wyniki profilu firmy w Google",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert contract_status_by_id["gbp_visibility"]["blocked_claim_labels"] == [
        "wyniki profilu firmy w Google",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert contract_status_by_id["competitor_visibility"]["status"] == "missing"
    assert contract_status_by_id["competitor_visibility"]["blocked_claims"] == [
        "widoczności konkurencji",
        "poprawa widoczności lokalnej",
    ]
    assert contract_status_by_id["local_tasks"]["status"] == "missing"
    assert contract_status_by_id["local_tasks"]["blocked_claims"] == [
        "ukończone zadanie lokalne",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert review_decision["read_contract_statuses"] == payload["read_contract_statuses"]
    assert review_decision["metric_tiles"]["miejsca"] == 4
    assert review_decision["metric_tiles"]["frazy"] == 23
    assert review_decision["metric_tiles"]["średnia widoczność"] == 52.83
    assert review_decision["metric_tiles"]["recenzje"] == 793
    assert "lokalne rankingi" not in review_decision["blocked_claims"]
    assert "wyniki profilu firmy w Google" in review_decision["blocked_claims"]
    assert "widoczności konkurencji" in review_decision["blocked_claims"]
    assert review_decision["knowledge_card_ids"] == ["card_localo_local_seo_playbook"]
    assert review_decision["expert_rule_ids"] == [
        "local_visibility_v1",
        "local_reviews_v1",
    ]
    operator_summary = payload["operator_summary"]
    assert operator_summary["visibility_fact_count"] == 4
    assert "agregaty widoczności" in operator_summary["summary"]
    assert operator_summary["review_card_label"] == "Karta review Localo"
    assert "listę lokalnych obserwacji" in operator_summary["review_decision_after_review"]
    assert "brakujące dane" in operator_summary["review_question_for_operator"]
    assert operator_summary["review_action_ids"] == [LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    assert LOCALO_VISIBILITY_REVIEW_ACTION_ID in operator_summary["review_next_safe_click"]
    assert "bez zapisu" in operator_summary["review_next_safe_click"]
    assert "bez publikacji zmian" in operator_summary["review_next_safe_click"]
    assert "4 agregatów Localo" not in review_decision["summary"]
    assert "Przejrzyj agregaty Localo" in operator_summary["next_step"]
    assert (
        "dopóki odczyt danych Localo nie dostarczy danych widoczności"
        not in (operator_summary["next_step"])
    )
    blocked_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert blocked_decision["metric_tiles"]["brakujące dane"] == 3
    assert blocked_decision["title"] == (
        "Blokuj profil firmy w Google, konkurencję i zadania lokalne bez pełnych danych Localo"
    )
    assert "bez danych Localo" not in blocked_decision["title"]
    assert "Przejrzyj dostępne agregaty Localo" in blocked_decision["next_step"]
    assert "Najpierw dodaj odczyt danych Localo" not in blocked_decision["next_step"]
    section_by_id = {section["id"]: section for section in payload["sections"]}
    assert section_by_id["localo_visibility_contract"]["action_ids"] == [
        LOCALO_VISIBILITY_REVIEW_ACTION_ID
    ]
    assert section_by_id["localo_visibility_contract"]["status_label"] == "gotowe"
    assert "4 agregaty Localo" in section_by_id["localo_visibility_contract"]["summary"]
    assert "4 agregatów Localo" not in section_by_id["localo_visibility_contract"]["summary"]
    assert all(fact["source_connector"] == "localo" for fact in review_decision["metric_facts"])
    metric_labels_by_name = {
        fact["name"]: fact["metric_label"] for fact in review_decision["metric_facts"]
    }
    assert metric_labels_by_name["localo_active_place_count"] == "aktywne lokalizacje"
    assert metric_labels_by_name["localo_avg_visibility_current"] == "średnia widoczność"
    assert all(fact["metric_label"] for fact in review_decision["metric_facts"])
    first_metric_fact = review_decision["metric_facts"][0]
    assert first_metric_fact["dimension_labels"]["contract"] == "obszar"
    assert first_metric_fact["dimension_labels"]["scope"] == "zakres"
    assert first_metric_fact["dimension_value_labels"]["contract"] == "spis miejsc"
    assert first_metric_fact["dimension_value_labels"]["scope"] == "aktywne miejsca"
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
    assert localo_action["payload"]["preview_contract"] == ("local_visibility_review_preview_v1")
    assert localo_action["payload"]["payload_preview"][0]["preview_contract"] == (
        "local_visibility_review_preview_v1"
    )
    localo_preview = localo_action["payload"]["payload_preview"][0]
    assert localo_preview["operation_type"] == "local_visibility_review"
    assert localo_preview["metric_snapshot"]["localo_active_place_count"] == 4
    assert localo_preview["metric_snapshot"]["localo_tracked_keyword_count"] == 23
    assert (
        localo_preview["metric_snapshot_labels"]["localo_avg_visibility_current"]
        == "średnia widoczność"
    )
    assert localo_preview["allowed_contracts"] == [
        "place_inventory",
        "local_rankings",
        "reviews",
    ]
    assert localo_preview["allowed_contract_labels"] == [
        "lista lokalizacji",
        "lokalne pozycje",
        "opinie",
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
    assert localo_action["preview_cards"]
    localo_preview_card = localo_action["preview_cards"][0]
    assert localo_preview_card["kind"] == "localo_visibility_review"
    assert localo_preview_card["title_label"] == "Widoczność lokalna do sprawdzenia"
    localo_preview_rows = {row["label"]: row["value"] for row in localo_preview_card["rows"]}
    assert localo_preview_rows["średnia widoczność"]
    assert localo_preview_rows["monitorowane frazy"] == "23"
    assert "Dozwolone odczyty" in localo_preview_rows
    assert "Braki" in localo_preview_rows
    localo_marketer_card_text = str(
        {
            key: localo_preview_card[key]
            for key in ("title_label", "subtitle_label", "status_label", "rows")
        }
    )
    assert "local_visibility_review_preview_v1" not in localo_marketer_card_text
    assert "local_visibility_review" not in localo_marketer_card_text
    assert "localo_avg_visibility_current" not in localo_marketer_card_text
    assert "source_metric_names" not in localo_marketer_card_text

    validate_response = client.post(f"/api/actions/{LOCALO_VISIBILITY_REVIEW_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True
    preview_response = client.post(f"/api/actions/{LOCALO_VISIBILITY_REVIEW_ACTION_ID}/preview")
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["preview_contract"] == "local_visibility_review_preview_v1"
    assert preview_payload["preview_items_total"] == 1
    assert_preview_items_are_operator_view_models(preview_payload["preview_items"])
    assert preview_payload["preview_cards"]
    localo_card_text = json.dumps(preview_payload["preview_cards"], ensure_ascii=False)
    assert "opinie Localo" in localo_card_text
    assert "793" in localo_card_text
    assert "metric_snapshot" not in json.dumps(preview_payload["preview_items"])
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
    assert "wyniki profilu firmy w Google" in localo_plan["blocked_claims"]

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
    assert "payload" not in localo_context_action
    assert "action_plan" in localo_context_action
    assert localo_context_action["action_plan"]["preview_items_included"] == 1
    assert localo_context_action["action_plan"]["preview_items_total"] == 1
    assert (
        localo_context_action["action_plan"]["preview_items"][0]["metric_tiles"][
            "aktywne lokalizacje"
        ]
        == 4
    )


def test_localo_diagnostics_does_not_block_ready_gbp_or_competitor_contracts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "localo_full_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "localo_full.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")
    localo_run = ConnectorRefreshRun(
        id="refresh_localo_full_diag_test",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_localo_full_diag_test"],
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
            "localo_avg_visibility_current": 53.1739,
            "localo_reviews_count": 798,
            "localo_gbp_impressions_total": 120,
            "localo_competitor_count": 3,
        },
        summary="Odczyt danych Localo zakończony agregatami.",
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
                53.1739,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_reviews_count",
                798,
                {"contract": "reviews", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_gbp_impressions_total",
                120,
                {"contract": "gbp_visibility", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_competitor_count",
                3,
                {"contract": "competitor_visibility", "scope": "active_places"},
                period="localo_mcp_read",
            ),
        ],
    )

    response = client.get("/api/localo/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    review_decision = decision_by_id["localo_review_visibility_facts"]
    assert review_decision["allowed_evidence"] == [
        "place_inventory",
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
    ]
    assert review_decision["missing_read_contracts"] == ["local_tasks"]
    assert review_decision["blocked_claims"] == [
        "ukończone zadanie lokalne",
        "zapis zmian w profilu firmy",
        "poprawa widoczności lokalnej",
    ]
    assert "wyniki profilu firmy w Google" not in review_decision["blocked_claims"]
    assert "widoczności konkurencji" not in review_decision["blocked_claims"]
    blocked_decision = decision_by_id["localo_block_visibility_claims_without_read_contract"]
    assert blocked_decision["missing_read_contracts"] == ["local_tasks"]
    assert "profil firmy w Google, konkurencję" not in blocked_decision["title"]
    assert "profilu firmy w Google, konkurencji" not in blocked_decision["summary"]
    assert "kontrakty profilu firmy w Google, konkurencji" not in blocked_decision["next_step"]

    actions_response = client.get("/api/actions")

    assert actions_response.status_code == 200
    actions_by_id = {action["id"]: action for action in actions_response.json()}
    localo_action = actions_by_id[LOCALO_VISIBILITY_REVIEW_ACTION_ID]
    assert localo_action["payload"]["missing_read_contracts"] == ["local_tasks"]
    assert "wyniki profilu firmy w Google" not in localo_action["payload"]["blocked_claims"]
    assert "widoczności konkurencji" not in localo_action["payload"]["blocked_claims"]
    assert localo_action["payload"]["payload_preview"][0]["missing_read_contracts"] == [
        "local_tasks"
    ]
    assert (
        "profil firmy w Google, konkurencję"
        not in localo_action["payload"]["payload_preview"][0]["reason"]
    )


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
        "dostęp Localo": 0,
        "brakujące dane": 6,
    }
    assert (
        "mcp_initialize"
        in decision_by_id["localo_fix_access_before_visibility_review"]["missing_read_contracts"]
    )
    assert (
        decision_by_id["localo_block_visibility_claims_without_read_contract"]["status"]
        == "blocked"
    )


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
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "odczyt zakończony"
    assert payload["live_data_status_label"] == "metryki Ahrefs dostępne"
    assert payload["authority_fact_count"] == 2
    assert payload["gap_fact_count"] == 0
    assert payload["blocker_count"] == 1
    gap_contract = payload["gap_read_contract"]
    assert gap_contract["status"] == "blocked"
    assert gap_contract["status_label"] == "zablokowane"
    assert gap_contract["gap_records"] == []
    assert gap_contract["cross_check_status"] == "missing"
    assert gap_contract["cross_check_status_label"] == "brak rekordów Ahrefs do cross-checku"
    assert gap_contract["cross_check_gsc_match_count"] == 0
    assert gap_contract["cross_check_wordpress_match_count"] == 0
    assert gap_contract["cross_check_source_connectors"] == []
    assert gap_contract["cross_check_evidence_ids"] == []
    assert gap_contract["cross_check_candidates"] == []
    assert gap_contract["available_read_contracts"] == ["ahrefs_authority_summary"]
    assert "ahrefs_content_gap_records" in gap_contract["missing_read_contracts"]
    assert gap_contract["evidence_summary_label"] == "1 dowód źródłowy"
    assert (
        gap_contract["action_summary_label"] == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
    assert "luka treści" in gap_contract["blocked_claims"]
    assert "luka treści" in gap_contract["blocked_claim_labels"]
    assert gap_contract["operator_review_gates"] == [
        "ahrefs_gap_records_required",
        "content_workflow_review_required",
        "human_strategy_review",
    ]
    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    authority_decision = decision_by_id["ahrefs_review_authority_context"]
    assert authority_decision["status"] == "ready"
    assert authority_decision["status_label"] == "gotowe"
    assert authority_decision["priority_label"] == "wysoki priorytet"
    assert authority_decision["decision_type_label"] == "kontekst autorytetu"
    assert authority_decision["metric_tiles"]["ocena domeny Ahrefs"] == 90
    assert authority_decision["metric_tiles"]["pozycja w rankingu Ahrefs"] == 1450
    assert authority_decision["metric_tiles"]["konkurenci organiczni"] == 0
    assert authority_decision["metric_tiles"]["odczyt konkurencji"] == "zakończony"
    assert authority_decision["metric_tiles"]["zakres konkurencji"] == "subdomeny"
    assert authority_decision["metric_tiles"]["luki Ahrefs"] == 0
    assert authority_decision["evidence_summary_label"] == "1 dowód źródłowy"
    assert (
        authority_decision["action_summary_label"]
        == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
    assert "organic_competitor_rows" in authority_decision["allowed_evidence"]
    assert "konkurenci organiczni" in authority_decision["allowed_evidence_labels"]
    assert "organic_competitor_mode" in authority_decision["allowed_evidence"]
    assert "zakres odczytu konkurencji" in authority_decision["allowed_evidence_labels"]
    assert "rekordy luk treści" in authority_decision["missing_read_contract_labels"]
    assert "liczba konkurentów: 0" in authority_decision["summary"]
    assert "rows=0" not in authority_decision["summary"]
    assert "status=completed" not in authority_decision["summary"]
    assert "subdomains" not in authority_decision["summary"]
    assert "domain_rating=" not in authority_decision["summary"]
    assert "ahrefs_rank=" not in authority_decision["summary"]
    assert "ahrefs_content_gap_records" in authority_decision["missing_read_contracts"]
    assert "luka treści" in authority_decision["blocked_claims"]
    assert "luka treści" in authority_decision["blocked_claim_labels"]
    assert authority_decision["knowledge_card_ids"] == ["card_ahrefs_content_gap_playbook"]
    assert authority_decision["expert_rule_ids"] == ["content_brief_rules_v1"]
    block_decision = decision_by_id["ahrefs_block_gap_claims_without_records"]
    assert block_decision["status"] == "blocked"
    assert block_decision["status_label"] == "zablokowane"
    assert block_decision["priority_label"] == "wysoki priorytet"
    assert block_decision["metric_tiles"]["brakujące dane"] == 5
    assert block_decision["evidence_ids"] == ["ev_refresh_refresh_ahrefs_diag_test"]
    assert block_decision["evidence_summary_label"] == "1 dowód źródłowy"
    assert (
        block_decision["action_summary_label"]
        == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "ahrefs_operator_summary"
    assert operator_summary["title"] == "Co marketer ma wiedzieć o Ahrefs"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["gap_read_status"] == "blocked"
    assert operator_summary["gap_read_status_label"] == "zablokowane"
    assert operator_summary["authority_fact_count"] == 2
    assert operator_summary["gap_fact_count"] == 0
    assert "ahrefs_authority_summary" in operator_summary["available_read_contracts"]
    assert "podsumowanie autorytetu domeny" in operator_summary["available_read_contract_labels"]
    assert "ahrefs_content_gap_records" in operator_summary["missing_read_contracts"]
    assert "rekordy luk treści" in operator_summary["missing_read_contract_labels"]
    assert "ahrefs" in operator_summary["source_connectors"]
    assert "ev_refresh_refresh_ahrefs_diag_test" in operator_summary["evidence_ids"]
    assert operator_summary["evidence_summary_label"] == "1 dowód źródłowy"
    assert (
        operator_summary["action_summary_label"]
        == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
    assert "luka treści" in operator_summary["blocked_claims"]
    assert "luka treści" in operator_summary["blocked_claim_labels"]
    assert operator_summary["review_card_label"] == "Karta review Ahrefs"
    assert "tylko jako kontekstu autorytetu" in operator_summary["review_decision_after_review"]
    assert "rekordy luk treści i linków" in operator_summary["review_question_for_operator"]
    assert operator_summary["review_action_ids"] == []
    assert "nie ma bezpiecznego kliknięcia" in operator_summary["review_next_safe_click"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    assert all(fact["source_connector"] == "ahrefs" for fact in authority_decision["metric_facts"])
    assert payload["sections"][0]["status_label"]
    assert payload["sections"][0]["evidence_summary_label"]
    assert payload["sections"][0]["action_summary_label"]
    assert isinstance(payload["sections"][0]["blocked_claim_labels"], list)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "ahrefs-token-test" not in serialized

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["ahrefs_diagnostics"]["evidence_ids"] == payload["evidence_ids"]
    context_gap_contract = context_payload["ahrefs_diagnostics"]["gap_read_contract"]
    assert context_gap_contract["status"] == gap_contract["status"]
    assert context_gap_contract["evidence_summary_label"] == gap_contract["evidence_summary_label"]
    assert context_gap_contract["action_summary_label"] == gap_contract["action_summary_label"]
    assert context_gap_contract["gap_record_count"] == gap_contract["gap_record_count"]
    assert context_gap_contract["cross_check_status"] == "missing"
    assert context_gap_contract["cross_check_candidates_total"] == 0
    assert context_gap_contract["cross_check_candidates_included"] == 0
    assert context_gap_contract["gap_records_omitted"] is True
    assert "gap_records" not in context_gap_contract
    assert context_payload["ahrefs_diagnostics"]["decision_queue"][0]["id"] in decision_by_id
    assert context_payload["ahrefs_diagnostics"]["context_pack_compaction"] == {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": 3,
        "latest_refresh_compacted": True,
        "gap_records_omitted": True,
        "full_endpoint": "/api/ahrefs/diagnostics",
    }
    assert context_payload["active_action_objects"] == []
    assert "marketing_brief" not in context_payload
    assert "content_diagnostics" not in context_payload
    assert "available_read_contracts" not in context_gap_contract
    assert "allowed_evidence" not in context_gap_contract
    assert context_gap_contract["available_read_contract_labels"]
    assert context_gap_contract["allowed_evidence_labels"]
    assert "competitor_page" not in json.dumps(context_payload, ensure_ascii=False)


def test_ahrefs_skill_context_pack_compacts_historical_raw_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ahrefs_context_raw_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ahrefs_context_raw.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    ahrefs_run = ConnectorRefreshRun(
        id="refresh_ahrefs_raw_history_test",
        connector_id="ahrefs",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_ahrefs_raw_history_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "domain_rating": 90,
            "ahrefs_rank": 1450,
            "ahrefs_content_gap_count": 2,
            "ahrefs_backlink_gap_count": 4,
        },
        summary=(
            "Typed Ahrefs gap records completed. Content gap rows: 2. "
            "Backlink gap rows: 4. Top pages and organic keywords loaded."
        ),
    )
    local_state_store().save_connector_refresh_run(ahrefs_run)
    metric_store().save_connector_refresh_metrics(
        ahrefs_run,
        detailed_facts=[
            VendorMetricFact("domain_rating", 90, period="ahrefs_site_explorer"),
            VendorMetricFact("ahrefs_rank", 1450, period="ahrefs_site_explorer"),
        ],
    )
    dirty_card = KnowledgeCard(
        id="card_dirty_ahrefs_history",
        card_type="seo_context",
        title="Ahrefs luka treścis and luka linkóws playbook",
        summary="Use Content gap rows, Backlink gap rows and top pages as raw skill text.",
        source_type="doc",
        source_id="dirty-ahrefs-doc",
        source_url_or_path="docs/dirty-ahrefs.md",
        confidence=0.9,
        source_lineage=["Content gap rows", "Backlink gap rows"],
    )
    monkeypatch.setattr(
        "apps.api.wilq_api.context_knowledge.knowledge_cards_for_skill",
        lambda skill: [dirty_card],
    )

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["context_pack_compaction"]["mode"] == "skill_default"
    assert payload["context_pack_compaction"]["connector_refresh_runs_compacted"] is True
    assert payload["context_pack_compaction"]["evidence_summaries_compacted"] is True
    assert payload["context_pack_compaction"]["knowledge_card_summaries_compacted"] is True
    assert payload["context_pack_compaction"]["expert_capabilities_compacted"] is True
    assert payload["context_pack_compaction"]["action_review_gates_compacted"] is True
    assert payload["context_pack_compaction"]["raw_history_omitted"] is True
    assert payload["expert_capabilities"]
    assert all(capability["required_inputs"] == [] for capability in payload["expert_capabilities"])
    assert all(
        isinstance(capability["required_inputs_total"], int)
        for capability in payload["expert_capabilities"]
    )
    assert "required_mapping" not in json.dumps(payload["expert_capabilities"])
    assert payload["connector_refresh_runs"][0]["id"] == "refresh_ahrefs_raw_history_test"
    assert payload["connector_refresh_runs"][0]["evidence_ids"] == [
        "ev_refresh_refresh_ahrefs_raw_history_test"
    ]
    assert payload["evidence_summaries"]
    assert payload["evidence_summaries"][0]["source_connector"] == "ahrefs"
    assert payload["evidence_summaries"][0]["raw_ref"] is None
    assert payload["knowledge_card_summaries"][0]["id"] == "card_dirty_ahrefs_history"

    serialized = json.dumps(
        {
            "connector_refresh_runs": payload["connector_refresh_runs"],
            "evidence_summaries": payload["evidence_summaries"],
            "knowledge_card_summaries": payload["knowledge_card_summaries"],
            "ahrefs_diagnostics": payload["ahrefs_diagnostics"],
        },
        ensure_ascii=False,
    )
    forbidden_terms = (
        "Typed Ahrefs",
        "gap records",
        "Content gap rows",
        "Backlink gap rows",
        "luka treścis",
        "luka linkóws",
        "top pages",
        "organic keywords",
    )
    for term in forbidden_terms:
        assert term not in serialized


def test_ahrefs_diagnostics_builds_gap_review_records_from_metric_facts(
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
                    "referenced_public_url": "https://www.ekologus.pl/bdo/",
                },
                period="ahrefs_gap",
            ),
            VendorMetricFact(
                "ahrefs_content_gap_count",
                2,
                {
                    "competitor_domain": "example.pl",
                    "keyword": "bdo szkolenie",
                    "referenced_public_url": "https://www.ekologus.pl/bdo/",
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
                    "referenced_public_url": (
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
                    "referenced_public_url": "https://www.ekologus.pl/bdo/",
                },
                period="ahrefs_gap",
            ),
        ],
    )
    gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_ahrefs_cross_check_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_gsc_ahrefs_cross_check_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"query_page_rows": 1},
        summary="GSC cross-check fixture.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                "impressions",
                10,
                {
                    "query": "bdo szkolenie",
                    "page": "https://www.ekologus.pl/bdo/",
                },
                period="last_28_days",
            ),
        ],
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_ahrefs_cross_check_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_ahrefs_cross_check_test"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"content_object_count": 1},
        summary="WordPress cross-check fixture.",
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                "content_object_seen",
                1,
                {
                    "title": "BDO szkolenie",
                    "content_url": "https://www.ekologus.pl/bdo/",
                },
                period="wordpress_inventory",
            ),
        ],
    )

    response = client.get("/api/ahrefs/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_data_available"] is True
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "odczyt zakończony"
    assert payload["live_data_status_label"] == "metryki Ahrefs dostępne"
    assert payload["gap_fact_count"] == 9
    assert payload["blocker_count"] == 0
    gap_contract = payload["gap_read_contract"]
    assert gap_contract["status"] == "ready"
    assert gap_contract["status_label"] == "gotowe"
    assert gap_contract["cross_check_status"] == "api_backed"
    assert (
        gap_contract["cross_check_status_label"]
        == "sprawdzenie GSC i WordPress ma dopasowania z API"
    )
    assert gap_contract["cross_check_gsc_match_count"] >= 1
    assert gap_contract["cross_check_wordpress_match_count"] >= 1
    assert "google_search_console" in gap_contract["cross_check_source_connectors"]
    assert "wordpress_ekologus" in gap_contract["cross_check_source_connectors"]
    assert "ev_refresh_gsc_ahrefs_cross_check_test" in gap_contract["cross_check_evidence_ids"]
    assert (
        "ev_refresh_wordpress_ahrefs_cross_check_test" in gap_contract["cross_check_evidence_ids"]
    )
    assert "google_search_console" in gap_contract["source_connectors"]
    assert "wordpress_ekologus" in gap_contract["source_connectors"]
    assert "dopasowanie w GSC" in gap_contract["cross_check_summary"]
    assert "dopasowaniem GSC i WordPress" in gap_contract["cross_check_next_step"]
    cross_check_candidate = next(
        candidate
        for candidate in gap_contract["cross_check_candidates"]
        if candidate["topic"] == "bdo szkolenie"
    )
    assert cross_check_candidate["gsc_demand_label"] == "jest w GSC"
    assert cross_check_candidate["wordpress_inventory_match_label"] == "jest w WordPress"
    assert cross_check_candidate["gsc_overlap_terms"] == ["bdo szkolenie"]
    assert cross_check_candidate["wordpress_overlap_urls"] == ["https://www.ekologus.pl/bdo/"]
    assert gap_contract["evidence_summary_label"]
    assert gap_contract["action_ids"] == ["act_prepare_content_refresh_queue"]
    assert gap_contract["action_summary_label"] == "1 akcja do sprawdzenia"
    assert payload["action_ids"] == ["act_prepare_content_refresh_queue"]
    assert payload["action_summary_label"] == "1 akcja do sprawdzenia"
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
    assert gap_contract["available_read_contract_labels"] == [
        "podsumowanie autorytetu domeny",
        "metryki luk z Ahrefs",
        "strony konkurencji",
        "rekordy luk treści",
        "rekordy luk linków",
        "organiczne słowa dla URL",
        "najlepsze strony konkurencji",
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
    assert {record["gap_type_label"] for record in gap_contract["gap_records"]} == {
        "strona konkurencji",
        "luka treści",
        "luka linków",
        "luka słów organicznych",
        "luka najlepszych stron konkurencji",
    }
    assert all("target_url" not in record for record in gap_contract["gap_records"])
    content_record = next(
        record for record in gap_contract["gap_records"] if record["gap_type"] == "content_gap"
    )
    assert content_record["keyword"] == "bdo szkolenie"
    assert content_record["referenced_public_url"] == "https://www.ekologus.pl/bdo/"
    assert content_record["competitor_domain"] == "example.pl"
    assert "2 luki treści" in content_record["summary"]
    assert content_record["metric_fact_labels"]["ahrefs_content_gap_count"] == "luki treści"
    assert "wzrost ruchu" in content_record["blocked_claims"]

    decision_by_id = {item["id"]: item for item in payload["decision_queue"]}
    gap_decision = decision_by_id["ahrefs_review_gap_records"]
    assert gap_decision["status"] == "ready"
    assert gap_decision["status_label"] == "gotowe"
    assert gap_decision["priority_label"] == "wysoki priorytet"
    assert gap_decision["decision_type_label"] == "sprawdzenie luk"
    assert gap_decision["metric_tiles"] == {
        "rekordy luk": 5,
        "luki treści": 1,
        "luki linków zwrotnych": 1,
        "strony konkurencji": 1,
        "słowa organiczne": 1,
        "najlepsze strony": 1,
        "brakujące dane": 0,
    }
    assert gap_decision["missing_read_contracts"] == []
    assert gap_decision["missing_read_contract_labels"] == []
    assert "ocena domeny Ahrefs" in gap_decision["allowed_evidence_labels"]
    assert "luki treści" in gap_decision["allowed_evidence_labels"]
    assert "wzrost ruchu" in gap_decision["blocked_claims"]
    assert "wzrost ruchu" in gap_decision["blocked_claim_labels"]
    assert "ahrefs_block_gap_claims_without_records" not in decision_by_id
    operator_summary = payload["operator_summary"]
    assert operator_summary["gap_read_status"] == "ready"
    assert operator_summary["gap_read_status_label"] == "gotowe"
    assert "rekordami luk Ahrefs" in operator_summary["next_step"]
    assert "bez rekordów" not in operator_summary["next_step"]
    assert operator_summary["action_ids"] == ["act_prepare_content_refresh_queue"]
    assert operator_summary["action_summary_label"] == "1 akcja do sprawdzenia"
    assert operator_summary["review_card_label"] == "Karta review Ahrefs"
    assert "odświeżenia albo scalenia" in operator_summary["review_decision_after_review"]
    assert (
            "Sprawdzenie GSC i WordPress jest dostępne"
        in operator_summary["review_decision_after_review"]
    )
    assert "nowy brief" in operator_summary["review_question_for_operator"]
    assert operator_summary["review_action_ids"] == ["act_prepare_content_refresh_queue"]
    assert "act_prepare_content_refresh_queue" in operator_summary["review_next_safe_click"]
    assert "bez zapisu" in operator_summary["review_next_safe_click"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ahrefs-gap-finder"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_gap_contract = context_payload["ahrefs_diagnostics"]["gap_read_contract"]
    assert context_gap_contract["status"] == gap_contract["status"]
    assert context_gap_contract["gap_record_count"] == gap_contract["gap_record_count"]
    assert context_gap_contract["cross_check_status"] == "api_backed"
    assert context_gap_contract["cross_check_gsc_match_count"] >= 1
    assert context_gap_contract["cross_check_wordpress_match_count"] >= 1
    assert "google_search_console" in context_gap_contract["cross_check_source_connectors"]
    assert "wordpress_ekologus" in context_gap_contract["cross_check_source_connectors"]
    assert (
        "ev_refresh_gsc_ahrefs_cross_check_test" in context_gap_contract["cross_check_evidence_ids"]
    )
    assert context_gap_contract["cross_check_candidates_total"] == len(
        gap_contract["cross_check_candidates"]
    )
    assert context_gap_contract["cross_check_candidates_included"] == min(
        4,
        len(gap_contract["cross_check_candidates"]),
    )
    assert {
        "topic",
        "gsc_demand_label",
        "wordpress_inventory_match_label",
        "next_step",
    }.issubset(context_gap_contract["cross_check_candidates"][0])
    assert context_gap_contract["gap_records_omitted"] is True
    assert context_gap_contract["gap_records_total"] == len(gap_contract["gap_records"])
    assert "gap_records" not in context_gap_contract
    assert "available_read_contracts" not in context_gap_contract
    assert "allowed_evidence" not in context_gap_contract
    assert context_gap_contract["available_read_contract_labels"]
    assert context_gap_contract["allowed_evidence_labels"]
    assert "competitor_page" not in json.dumps(context_payload, ensure_ascii=False)
    assert (
        context_payload["ahrefs_diagnostics"]["context_pack_compaction"]["full_endpoint"]
        == "/api/ahrefs/diagnostics"
    )
    actions_by_id = {action["id"]: action for action in context_payload["active_action_objects"]}
    assert "act_prepare_content_refresh_queue" in actions_by_id
    context_action = actions_by_id["act_prepare_content_refresh_queue"]
    assert context_action["mode_label"] == "przygotowanie"
    assert "action_plan" in context_action
    assert context_action["action_plan"]["content_plan_items"]


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
    assert {record["gap_type"] for record in payload["gap_read_contract"]["gap_records"]} == {
        "competitor_page",
        "content_gap",
        "backlink_gap",
        "organic_keyword_gap",
        "top_page_gap",
    }
    decision_ids = {decision["id"] for decision in payload["decision_queue"]}
    assert "ahrefs_review_gap_records" in decision_ids
    review_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ahrefs_review_gap_records"
    )
    assert review_decision["evidence_summary_label"]
    assert (
        review_decision["action_summary_label"]
        == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
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
                    "referenced_public_url": "https://www.ekologus.pl/bdo/",
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
    gap_decision = {decision["id"]: decision for decision in payload["decision_queue"]}[
        "ahrefs_review_gap_records"
    ]
    assert gap_decision["metric_tiles"]["rekordy luk"] == 2
