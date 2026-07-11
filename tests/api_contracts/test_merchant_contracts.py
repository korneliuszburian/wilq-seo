"""Merchant diagnostics and vendor-read API contract tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from tests._contract_support.assertions import (
    assert_preview_items_are_operator_view_models,
    preview_card_row_values,
)
from tests._contract_support.env import clear_google_service_env
from wilq.briefing.merchant_diagnostics import (
    _merchant_price_impact_readiness,
    _merchant_product_performance_readiness,
    _merchant_product_performance_readiness_with_operator_labels,
    build_merchant_diagnostics_cached,
    clear_merchant_diagnostics_cache,
)
from wilq.connectors.google_merchant_center.client import refresh_merchant_product_status_summary
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MerchantIssueCluster,
    MerchantProductPerformanceReadiness,
    MerchantProductPerformanceRow,
    MerchantProductSampleReadiness,
    MetricFact,
)


def test_merchant_diagnostics_cache_reuses_one_build_outside_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_MERCHANT_DIAGNOSTICS_CACHE_SECONDS", "60")
    clear_merchant_diagnostics_cache()
    calls = 0
    sentinel = object()

    def fake_build():
        nonlocal calls
        calls += 1
        return sentinel

    monkeypatch.setattr("wilq.briefing.merchant_diagnostics.build_merchant_diagnostics", fake_build)
    assert build_merchant_diagnostics_cached() is sentinel
    assert build_merchant_diagnostics_cached() is sentinel
    assert calls == 1
    clear_merchant_diagnostics_cache()
    assert build_merchant_diagnostics_cached() is sentinel
    assert calls == 2


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
            summary="Odczyt Merchant Center zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "total_products": 10900,
                "item_level_issue_count": 23,
                "merchant_action_issue_count": 15,
            },
            metric_facts=[
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
                ),
                VendorMetricFact(
                    "sample_product_id",
                    "online~pl~PL~SKU-001",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "1",
                    },
                ),
                VendorMetricFact(
                    "sample_product_id",
                    "online~pl~PL~SKU-002",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "2",
                    },
                ),
                VendorMetricFact(
                    "sample_product_title",
                    "Sorbent chemiczny 10 kg",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "1",
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
    assert payload["connector_status_label"] == "dostęp skonfigurowany"
    assert payload["latest_refresh_status_label"] == "odczyt zakończony"
    assert payload["live_data_status_label"] == "metryki pliku produktowego dostępne"
    assert payload["product_count"] == 10900
    assert payload["issue_count"] == 23
    assert payload["latest_refresh"]["status"] == "completed"
    assert payload["freshness_assessment"]["state"] == "fresh"
    assert payload["freshness_assessment"]["state_label"] == "dane świeże"
    assert payload["freshness_assessment"]["requires_refresh"] is False
    assert payload["freshness_assessment"]["stale_after_hours"] == 48
    sample_readiness = payload["product_sample_readiness"]
    assert sample_readiness["status"] == "ready"
    assert sample_readiness["status_label"] == "próbki produktów dostępne"
    assert sample_readiness["sample_products_available"] is True
    assert sample_readiness["sample_count"] == 2
    assert sample_readiness["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert sample_readiness["sample_product_titles"] == ["Sorbent chemiczny 10 kg"]
    assert sample_readiness["current_read_contract"] == "merchant_aggregate_product_statuses"
    assert sample_readiness["required_read_contracts"] == [
        "merchant_products_list_product_status",
        "merchant_reports_product_view_issue_filter",
    ]
    assert sample_readiness["source_endpoint"] == "aggregateProductStatuses"
    assert "dokładniejszy odczyt produktów z problemami" in sample_readiness["next_step"]
    assert "products.list" not in sample_readiness["summary"]
    assert "products.list" not in sample_readiness["next_step"]
    assert "product_view" not in sample_readiness["next_step"]
    assert "zapis do pliku produktowego" in sample_readiness["blocked_claims"]
    assert "zapis do pliku produktowego" in sample_readiness["blocked_claim_labels"]
    performance_readiness = payload["product_performance_readiness"]
    assert performance_readiness["id"] == "merchant_product_performance_readiness"
    assert performance_readiness["status"] == "blocked"
    assert performance_readiness["status_label"] == "dane Ads/GA4 zablokowane"
    assert performance_readiness["merchant_sample_count"] == 2
    assert performance_readiness["joined_product_count"] == 0
    assert performance_readiness["ads_product_fact_count"] == 0
    assert performance_readiness["ga4_product_fact_count"] == 0
    assert performance_readiness["required_read_contracts"] == [
        "merchant_product_id_join_key",
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    ]
    assert performance_readiness["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert performance_readiness["performance_rows"] == []
    assert performance_readiness["current_read_contracts"] == [
        "merchant_aggregate_product_statuses"
    ]
    assert "google_merchant_center" in performance_readiness["source_connectors"]
    assert refresh_response.json()["evidence_ids"][-1] in performance_readiness["evidence_ids"]
    assert "zwrot z reklam na poziomie produktu" in performance_readiness["blocked_claims"]
    assert "odzyskany przychód produktu" in performance_readiness["blocked_claims"]
    assert "efekt naprawy produktu" in performance_readiness["blocked_claims"]
    assert "zwrot z reklam na poziomie produktu" in performance_readiness["blocked_claim_labels"]
    assert "act_review_merchant_feed_issues" in payload["action_ids"]
    assert "akcj" in payload["action_summary_label"]
    assert payload["unknowns"]
    unknown_ids = {unknown["id"] for unknown in payload["unknowns"]}
    assert "merchant_product_examples_missing" not in unknown_ids
    assert "merchant_unique_product_count_unknown" in unknown_ids
    assert "merchant_product_performance_join_missing" in unknown_ids
    assert payload["issue_clusters"]
    cluster = payload["issue_clusters"][0]
    assert cluster["issue_type"] == "availability_updated"
    assert cluster["issue_type_label"] == "zmiana dostępności"
    assert cluster["affected_attribute"] == "n:availability"
    assert cluster["affected_attribute_label"] == "dostępność"
    assert cluster["country"] == "PL"
    assert cluster["reporting_context"] == "SHOPPING_ADS"
    assert cluster["reporting_context_label"] == "reklamy produktowe"
    assert cluster["severity"] == "NOT_IMPACTED"
    assert cluster["severity_label"] == "bez wpływu"
    assert cluster["resolution"] == "MERCHANT_ACTION"
    assert cluster["resolution_label"] == "wymaga działania po stronie Merchant"
    assert cluster["product_count"] == 23
    assert cluster["count_semantics"] == "reported_issue_occurrences"
    assert cluster["action_id"] == "act_review_merchant_feed_issues"
    assert cluster["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert cluster["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert cluster["sample_unavailable_reason"] is None
    assert "ponowne zatwierdzenie produktu" in cluster["blocked_claims"]
    assert payload["decision_queue"]
    operator_summary = payload["operator_summary"]
    assert operator_summary["id"] == "merchant_operator_summary"
    assert operator_summary["title"] == "Co marketer ma zrobić teraz z plikiem produktowym"
    assert operator_summary["top_decision_ids"] == [
        decision["id"] for decision in payload["decision_queue"][:4]
    ]
    assert operator_summary["top_issue_cluster_ids"] == [
        cluster["id"] for cluster in payload["issue_clusters"][:4]
    ]
    assert operator_summary["reported_issue_occurrences"] == sum(
        cluster["product_count"] for cluster in payload["issue_clusters"]
    )
    assert operator_summary["decision_source"] == "decision_queue"
    assert operator_summary["decision_source_label"] == "kolejka decyzji Merchant"
    assert operator_summary["drilldown_source"] == "issue_clusters"
    assert operator_summary["drilldown_source_label"] == "grupy problemów pliku produktowego"
    assert operator_summary["count_semantics"] == "reported_issue_occurrences"
    assert operator_summary["count_semantics_label"] == "wystąpienia problemów w raportach"
    assert "zmiana dostępności" in operator_summary["issue_types"]
    assert operator_summary["source_connectors"] == ["google_merchant_center"]
    assert refresh_response.json()["evidence_ids"][-1] in operator_summary["evidence_ids"]
    assert "act_review_merchant_feed_issues" in operator_summary["action_ids"]
    assert "akcj" in operator_summary["action_summary_label"]
    assert "ponowne zatwierdzenie produktu" in operator_summary["blocked_claims"]
    assert "ponowne zatwierdzenie produktu" in operator_summary["blocked_claim_labels"]
    assert operator_summary["summary"]
    assert operator_summary["next_step"]
    decision = payload["decision_queue"][0]
    assert decision["decision_type"] == "review_issue_cluster"
    assert decision["decision_type_label"] == "przegląd problemu pliku produktowego"
    assert decision["status"] == "ready"
    assert decision["status_label"] == "gotowe"
    assert decision["title"] == ("Merchant: problem z atrybutem: dostępność - zmiana dostępności")
    assert " / " not in decision["summary"]
    assert "Status: bez wpływu." in decision["summary"]
    assert "Zalecenie: wymaga działania po stronie Merchant." in decision["summary"]
    assert "kontekst: reklamy produktowe" in decision["summary"]
    assert decision["issue_type"] == "availability_updated"
    assert decision["issue_type_label"] == "zmiana dostępności"
    assert decision["affected_attribute"] == "n:availability"
    assert decision["affected_attribute_label"] == "dostępność"
    assert decision["reporting_context_label"] == "reklamy produktowe"
    assert decision["product_count"] == 23
    assert decision["issue_count"] == 23
    assert decision["priority"] == 23
    assert decision["metric_tiles"] == {"zgłoszenia": 23}
    assert decision["cluster_id"] == cluster["id"]
    assert decision["issue_cluster_ids"] == [cluster["id"]]
    assert decision["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert decision["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert decision["change_preview"][0]["preview_contract"] == (
        "merchant_feed_issue_review_preview_v1"
    )
    decision_preview = decision["change_preview"][0]
    assert decision_preview["preview_contract_label"] == "sprawdzenie problemów pliku produktowego"
    assert decision_preview["operation_type"] == "MerchantIssueClusterReview"
    assert decision_preview["cluster_id"] == cluster["id"]
    assert decision_preview["issue_type"] == "availability_updated"
    assert decision_preview["issue_type_label"] == "zmiana dostępności"
    assert decision_preview["affected_attribute"] == "n:availability"
    assert decision_preview["affected_attribute_label"] == "dostępność"
    assert decision_preview["metric_snapshot"] == {"issue_product_count": 23}
    assert decision_preview["metric_snapshot_labels"] == {
        "issue_product_count": "zgłoszenia problemów"
    }
    assert decision_preview["sample_products_available"] is True
    assert decision_preview["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert decision_preview["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert decision_preview["apply_allowed"] is False
    assert decision_preview["api_mutation_ready"] is False
    assert decision_preview["destructive"] is False
    assert decision["preview_cards"]
    decision_preview_card = decision["preview_cards"][0]
    assert decision_preview_card["title_label"] == "Podgląd sprawdzenia Merchant"
    assert decision_preview_card["subtitle_label"] == "sprawdzenie problemów pliku produktowego"
    assert decision_preview_card["status_label"] == "do sprawdzenia"
    assert {
        "label": "Typ sprawdzenia",
        "value": "sprawdzenie problemów pliku produktowego",
    } in decision_preview_card["rows"]
    assert any(
        row["label"] == "Zakres" and "zgłoszenia" in row["value"]
        for row in decision_preview_card["rows"]
    )
    assert not any(
        "online~pl~PL~SKU" in row["value"] or "MerchantIssueClusterReview" in row["value"]
        for row in decision_preview_card["rows"]
    )
    assert decision_preview_card["apply_state_label"] == "Zapis zmian jest zablokowany."
    assert decision["count_semantics"] == "reported_issue_occurrences"
    assert "ponowne zatwierdzenie produktu" in decision["blocked_claim_labels"]
    assert "wartość Merchant do sprawdzenia" not in decision["blocked_claim_labels"]
    assert decision["risk_label"] == "średnie ryzyko"
    assert decision["action_ids"] == ["act_review_merchant_feed_issues"]
    assert decision["action_summary_label"] == "1 akcja do sprawdzenia"
    decision_metric = decision["metric_facts"][0]
    assert decision_metric["metric_label"] == "zgłoszenia problemów"
    assert decision_metric["dimension_labels"]["reporting_context"] == "kontekst"
    assert decision_metric["dimension_labels"]["resolution"] == "rozwiązanie"
    assert decision_metric["dimension_labels"]["severity"] == "status"
    assert decision_metric["dimension_value_labels"]["reporting_context"] == ("reklamy produktowe")
    assert decision_metric["dimension_value_labels"]["resolution"] == (
        "wymaga działania po stronie Merchant"
    )
    assert decision_metric["dimension_value_labels"]["severity"] == "bez wpływu"
    assert "zgłoszenia problemu" in decision["summary"]
    assert "wystąpienia problemu" in decision["rationale"]
    assert "act_review_merchant_feed_issues" not in decision["next_step"]
    assert "akcję do sprawdzenia" in decision["next_step"]
    assert decision["why_it_matters"] == decision["rationale"]
    assert decision["operator_action"] == decision["next_step"]
    assert decision["knowledge_card_ids"] == [
        "card_merchant_feed_optimization_playbook",
        "card_google_ads_pmax_playbook",
    ]
    assert decision["expert_rule_ids"] == [
        "merchant_feed_rules_v1",
        "merchant_product_diagnostics_v1",
    ]
    feed_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_feed_health"
    )
    assert feed_section["status"] == "ready"
    assert feed_section["label"] == "Metryki produktów"
    assert feed_section["status_label"] == "gotowe"
    assert "ponowne zatwierdzenie produktu" in feed_section["blocked_claim_labels"]
    assert "twierdzenie o odzyskanym przychodzie" in feed_section["blocked_claim_labels"]
    assert "twierdzenie o wzroście zysku" in feed_section["blocked_claim_labels"]
    assert "wartość Merchant do sprawdzenia" not in feed_section["blocked_claim_labels"]
    assert feed_section["risk_label"] == "średnie ryzyko"
    assert feed_section["evidence_summary_label"]
    assert feed_section["action_summary_label"] == "1 akcja do sprawdzenia"
    assert feed_section["summary"].startswith("Najważniejsze metryki Merchant:")
    assert "produkty w pliku produktowym: 10900" in feed_section["summary"]
    assert "total_products=10900" not in feed_section["summary"]
    issue_section = next(
        section for section in payload["sections"] if section["id"] == "merchant_issue_queue"
    )
    assert issue_section["status"] == "ready"
    assert issue_section["label"] == "Kolejka problemów pliku produktowego"
    assert issue_section["status_label"] == "gotowe"
    assert "automatyczna zmiana pliku produktowego" in issue_section["blocked_claim_labels"]
    assert issue_section["risk_label"] == "średnie ryzyko"
    assert issue_section["evidence_summary_label"]
    assert issue_section["action_summary_label"] == "1 akcja do sprawdzenia"
    assert "act_review_merchant_feed_issues" not in issue_section["next_step"]
    assert "problemów pliku produktowego" in issue_section["summary"]
    assert "wystąpieniami problemu" in issue_section["summary"]
    assert issue_section["tactical_items"]
    assert operator_summary["top_tactical_item_ids"] == [
        item["id"] for item in issue_section["tactical_items"][:3]
    ]
    assert any(
        item["dimensions"].get("issue_type") == "availability_updated"
        for item in issue_section["tactical_items"]
    )
    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    merchant_action = next(
        action
        for action in actions_response.json()
        if action["id"] == "act_review_merchant_feed_issues"
    )
    assert merchant_action["evidence_summary_label"]
    assert merchant_action["preview_cards"]
    merchant_preview_card = merchant_action["preview_cards"][0]
    assert merchant_preview_card["kind"] == "merchant_feed_issue_review"
    assert merchant_preview_card["title_label"] == "Problem pliku produktowego do sprawdzenia"
    assert merchant_preview_card["subtitle_label"] == ("dostępność - zmiana dostępności")
    assert merchant_preview_card["status_label"] == "zapis zmian zablokowany"
    assert {"label": "Próbki produktów", "value": "1 próbka z nazwą produktu"} in (
        merchant_preview_card["rows"]
    )
    assert not any("online~pl~PL~SKU" in row["value"] for row in merchant_preview_card["rows"])
    assert "issue_product_count" not in merchant_action["human_diagnosis"]
    assert "zgłoszenia problemów" in merchant_action["human_diagnosis"]
    assert "ev_refresh" not in merchant_action["human_diagnosis"]
    assert merchant_action["payload"]["issue_clusters"][0]["issue_type"] == ("availability_updated")
    assert merchant_action["payload"]["issue_clusters"][0]["product_count"] == 23
    assert merchant_action["payload"]["preview_contract"] == (
        "merchant_feed_issue_review_preview_v1"
    )
    assert merchant_action["payload"]["payload_preview"][0]["preview_contract"] == (
        "merchant_feed_issue_review_preview_v1"
    )
    merchant_preview = merchant_action["payload"]["payload_preview"][0]
    assert merchant_preview["preview_contract_label"] == "sprawdzenie problemów pliku produktowego"
    assert merchant_preview["operation_type"] == "MerchantIssueClusterReview"
    assert merchant_preview["cluster_id"] == cluster["id"]
    assert merchant_preview["issue_type"] == "availability_updated"
    assert merchant_preview["issue_type_label"] == "zmiana dostępności"
    assert merchant_preview["affected_attribute"] == "n:availability"
    assert merchant_preview["affected_attribute_label"] == "dostępność"
    assert merchant_preview["metric_snapshot"] == {"issue_product_count": 23}
    assert merchant_preview["metric_snapshot_labels"] == {
        "issue_product_count": "zgłoszenia problemów"
    }
    assert merchant_preview["sample_products_available"] is True
    assert merchant_preview["sample_product_ids"] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert merchant_preview["sample_titles"] == ["Sorbent chemiczny 10 kg"]
    assert merchant_preview["sample_unavailable_reason"] is None
    assert merchant_preview["apply_allowed"] is False
    assert merchant_preview["api_mutation_ready"] is False
    assert merchant_preview["destructive"] is False
    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 1},
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["preview_contract"] == "merchant_feed_issue_review_preview_v1"
    assert "payload_preview_missing" not in preview_payload["blockers"]
    assert_preview_items_are_operator_view_models(preview_payload["preview_items"])
    assert preview_payload["preview_cards"]
    merchant_card = preview_payload["preview_cards"][0]
    merchant_card_text = json.dumps(merchant_card, ensure_ascii=False)
    assert "online~pl~PL~SKU-001" not in json.dumps(preview_payload["preview_items"])
    assert preview_card_row_values(merchant_card, "Problem") == ["zmiana dostępności"]
    assert preview_card_row_values(merchant_card, "Atrybut") == ["dostępność"]
    assert "Sorbent chemiczny 10 kg" in merchant_card_text
    assert "sample_product_ids" not in json.dumps(preview_payload["preview_items"])
    serialized = json.dumps(payload)
    assert "5519957373" not in serialized
    assert "adc.json" not in serialized


def test_merchant_product_performance_readiness_joins_sample_ids_to_ads_and_ga4() -> None:
    product_id = "online~pl~PL~SKU-001"
    issue_cluster = MerchantIssueCluster(
        id="merchant_issue_test",
        issue_type="availability_updated",
        severity="NOT_IMPACTED",
        resolution="MERCHANT_ACTION",
        affected_attribute="n:availability",
        country="PL",
        reporting_context="SHOPPING_ADS",
        reporting_context_label="reklamy produktowe",
        product_count=23,
        sample_product_ids=[product_id],
        sample_titles=["Sorbent chemiczny 10 kg"],
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_merchant_issue"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        action_id="act_review_merchant_feed_issues",
        next_step="Review produktu.",
    )
    sample_readiness = MerchantProductSampleReadiness(
        status="ready",
        sample_products_available=True,
        sample_count=1,
        sample_product_ids=[product_id],
        sample_product_titles=["Sorbent chemiczny 10 kg"],
        required_read_contracts=[
            "merchant_products_list_product_status",
            "merchant_reports_product_view_issue_filter",
        ],
        source_endpoint="aggregateProductStatuses",
        summary="Merchant read ma sample product ID.",
        next_step="Review próbki.",
    )
    ads_facts = [
        MetricFact(
            name="clicks",
            value=14,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_clicks",
            dimensions={"product_id": "SKU-001"},
        ),
        MetricFact(
            name="cost_micros",
            value=2750000,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_cost",
            dimensions={"product_id": "SKU-001"},
        ),
        MetricFact(
            name="conversions",
            value=1.5,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_conversions",
            dimensions={"product_id": "SKU-001"},
        ),
        MetricFact(
            name="conversion_value",
            value=320.0,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_value",
            dimensions={"product_id": "SKU-001"},
        ),
    ]
    ga4_facts = [
        MetricFact(
            name="ecommerce_purchases",
            value=2,
            period="last_30_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_purchases",
            dimensions={"item_id": "SKU-001"},
        ),
        MetricFact(
            name="purchase_revenue",
            value=410.0,
            period="last_30_days",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_revenue",
            dimensions={"item_id": "SKU-001"},
        ),
    ]

    readiness = _merchant_product_performance_readiness(
        issue_clusters=[issue_cluster],
        product_sample_readiness=sample_readiness,
        product_metric_facts_by_connector={
            "google_ads": ads_facts,
            "google_analytics_4": ga4_facts,
        },
    )

    assert readiness.status == "ready"
    assert readiness.joined_product_count == 1
    assert readiness.merchant_sample_count == 1
    assert readiness.ads_product_fact_count == 4
    assert readiness.ga4_product_fact_count == 2
    assert readiness.current_read_contracts == [
        "merchant_aggregate_product_statuses",
        "google_ads_product_metric_facts",
        "ga4_item_metric_facts",
    ]
    assert readiness.missing_read_contracts == []
    assert readiness.source_connectors == [
        "google_merchant_center",
        "google_ads",
        "google_analytics_4",
    ]
    assert "ev_merchant_issue" in readiness.evidence_ids
    assert "ev_ads_clicks" in readiness.evidence_ids
    assert "ev_ga4_revenue" in readiness.evidence_ids
    row = readiness.performance_rows[0]
    assert row.product_id == product_id
    assert row.sample_title == "Sorbent chemiczny 10 kg"
    assert row.ads_clicks == 14
    assert row.ads_clicks_label == ""
    assert row.ads_cost_micros == 2750000
    assert row.ads_cost_label == ""
    assert row.ads_conversions == 1.5
    assert row.ads_conversions_label == ""
    assert row.ads_conversion_value == 320.0
    assert row.ads_conversion_value_label == ""
    assert row.ga4_ecommerce_purchases == 2.0
    assert row.ga4_ecommerce_purchases_label == ""
    assert row.ga4_purchase_revenue == 410.0
    assert row.ga4_purchase_revenue_label == ""
    assert row.missing_metrics == []
    assert "efekt naprawy produktu" in row.blocked_claims
    assert "zapis do pliku produktowego" in row.blocked_claims


def test_merchant_product_performance_readiness_reports_ready_ads_contract_without_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_id = "online~pl~PL~SKU-001"
    issue_cluster = MerchantIssueCluster(
        id="merchant_issue_test",
        issue_type="availability_updated",
        affected_attribute="n:availability",
        country="PL",
        reporting_context="SHOPPING_ADS",
        reporting_context_label="reklamy produktowe",
        severity="NOT_IMPACTED",
        resolution="MERCHANT_ACTION",
        product_count=23,
        sample_product_ids=[product_id],
        sample_titles=["Sorbent chemiczny 10 kg"],
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_merchant_issue"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        action_id="act_review_merchant_feed_issues",
        next_step="Review produktu.",
        risk=ActionRisk.medium,
    )
    sample_readiness = MerchantProductSampleReadiness(
        status="ready",
        sample_products_available=True,
        sample_count=1,
        sample_product_ids=[product_id],
        sample_product_titles=["Sorbent chemiczny 10 kg"],
        required_read_contracts=[
            "merchant_products_list_product_status",
            "merchant_reports_product_view_issue_filter",
        ],
        source_endpoint="aggregateProductStatuses",
        summary="Merchant read ma sample product ID.",
        next_step="Review próbki.",
    )
    ga4_facts = [
        MetricFact(
            name="item_purchases",
            value=2,
            period="connector_refresh",
            source_connector="google_analytics_4",
            evidence_id="ev_ga4_item",
            dimensions={"item_id": "SKU-001"},
        )
    ]

    monkeypatch.setattr(
        "wilq.briefing.merchant_diagnostics._product_performance_metric_facts_by_connector",
        lambda _sample_product_ids: {
            "google_ads": [],
            "google_analytics_4": ga4_facts,
        },
    )
    monkeypatch.setattr(
        "wilq.briefing.merchant_diagnostics._latest_connector_refresh",
        lambda connector_id: (
            ConnectorRefreshRun(
                id="refresh_google_ads_shopping_zero_rows",
                connector_id="google_ads",
                mode=ConnectorRefreshMode.vendor_read,
                status=ConnectorRefreshStatus.completed,
                evidence_ids=["ev_ads_shopping_zero_rows"],
                metric_summary={
                    "shopping_product_performance_status": "ready",
                    "shopping_product_performance_lookback_days": 90,
                    "shopping_product_performance_row_count": 0,
                },
                summary="Shopping product read returned zero rows.",
            )
            if connector_id == "google_ads"
            else None
        ),
    )

    readiness = _merchant_product_performance_readiness(
        issue_clusters=[issue_cluster],
        product_sample_readiness=sample_readiness,
    )

    assert readiness.status == "ready"
    assert readiness.joined_product_count == 1
    assert readiness.ads_product_fact_count == 0
    assert readiness.ga4_product_fact_count == 1
    assert readiness.current_read_contracts == [
        "merchant_aggregate_product_statuses",
        "google_ads_shopping_product_performance",
        "ga4_item_metric_facts",
    ]
    assert readiness.missing_read_contracts == []
    assert readiness.performance_rows[0].missing_metrics == [
        "ads_clicks",
        "ads_cost_micros",
        "ads_conversions",
        "ads_conversion_value",
        "ga4_purchase_revenue",
    ]
    labeled_readiness = _merchant_product_performance_readiness_with_operator_labels(readiness)
    labeled_row = labeled_readiness.performance_rows[0]
    assert labeled_row.ads_clicks_label == "kliknięcia Ads do potwierdzenia"
    assert labeled_row.ads_cost_label == "koszt Ads do potwierdzenia"
    assert labeled_row.ads_conversions_label == "konwersje Ads do potwierdzenia"
    assert labeled_row.ads_conversion_value_label == ("wartość konwersji Ads do potwierdzenia")
    assert labeled_row.ga4_ecommerce_purchases_label == "2"
    assert labeled_row.ga4_purchase_revenue_label == "przychód GA4 do potwierdzenia"
    assert "brak" not in labeled_row.ads_cost_label


def test_merchant_product_performance_readiness_blocks_state_only_product_join() -> None:
    product_id = "pl~PL~gla_107365"
    issue_cluster = MerchantIssueCluster(
        id="merchant_issue_state_only",
        issue_type="availability_updated",
        affected_attribute="n:availability",
        country="PL",
        reporting_context="SHOPPING_ADS",
        reporting_context_label="reklamy produktowe",
        severity="NOT_IMPACTED",
        resolution="MERCHANT_ACTION",
        product_count=1,
        sample_product_ids=[product_id],
        sample_titles=["Dywan sorpcyjny"],
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_merchant_issue"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        action_id="act_review_merchant_feed_issues",
        next_step="Review produktu.",
        risk=ActionRisk.medium,
    )
    sample_readiness = MerchantProductSampleReadiness(
        status="ready",
        sample_products_available=True,
        sample_count=1,
        sample_product_ids=[product_id],
        sample_product_titles=["Dywan sorpcyjny"],
        required_read_contracts=["merchant_products_list_product_status"],
        source_endpoint="aggregateProductStatuses",
        summary="Merchant read ma sample product ID.",
        next_step="Review próbki.",
    )
    state_facts = [
        MetricFact(
            name="shopping_product_state_available",
            value=1,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "gla_107365",
                "product_title": "Dywan sorpcyjny",
                "currency_code": "PLN",
            },
        ),
        MetricFact(
            name="shopping_product_status",
            value="NOT_ELIGIBLE",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "gla_107365",
                "product_status": "NOT_ELIGIBLE",
            },
        ),
        MetricFact(
            name="shopping_product_availability",
            value="OUT_OF_STOCK",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "gla_107365",
                "product_availability": "OUT_OF_STOCK",
            },
        ),
        MetricFact(
            name="shopping_product_price_micros",
            value=123450000,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={"product_item_id": "gla_107365"},
        ),
    ]

    readiness = _merchant_product_performance_readiness(
        issue_clusters=[issue_cluster],
        product_sample_readiness=sample_readiness,
        product_metric_facts_by_connector={
            "google_ads": state_facts,
            "google_analytics_4": [],
        },
    )

    assert readiness.status == "blocked"
    assert readiness.joined_product_count == 1
    assert readiness.current_read_contracts == [
        "merchant_aggregate_product_statuses",
        "google_ads_shopping_product_state",
    ]
    assert readiness.missing_read_contracts == [
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    ]
    assert "stan produktu z Ads" in readiness.summary
    assert "Zwrot z reklam" in readiness.next_step
    row = readiness.performance_rows[0]
    assert row.issue_type == "availability_updated"
    assert row.affected_attribute == "n:availability"
    assert row.country == "PL"
    assert row.reporting_context == "SHOPPING_ADS"
    assert row.ads_product_title == "Dywan sorpcyjny"
    assert row.ads_product_status == "NOT_ELIGIBLE"
    assert row.ads_product_availability == "OUT_OF_STOCK"
    assert row.ads_product_price_micros == 123450000
    assert row.ads_product_currency_code == "PLN"
    assert readiness.performance_rows[0].missing_metrics == [
        "ads_clicks",
        "ads_cost_micros",
        "ads_conversions",
        "ads_conversion_value",
        "ga4_ecommerce_purchases",
        "ga4_purchase_revenue",
    ]


def test_merchant_diagnostics_promotes_ads_product_state_review_decision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_state_review.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_state_review.duckdb"))
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
            summary="Odczyt Merchant Center zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "total_products": 10900,
                "item_level_issue_count": 14,
                "merchant_action_issue_count": 14,
            },
            metric_facts=[
                VendorMetricFact(
                    "issue_product_count",
                    14,
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "n:availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                    },
                ),
                VendorMetricFact(
                    "sample_product_id",
                    "online~pl~PL~SKU-001",
                    {
                        "issue_type": "availability_updated",
                        "affected_attribute": "n:availability",
                        "country": "PL",
                        "reporting_context": "SHOPPING_ADS",
                        "severity": "NOT_IMPACTED",
                        "resolution": "MERCHANT_ACTION",
                        "sample_index": "1",
                    },
                ),
            ],
        ),
    )
    state_facts = [
        MetricFact(
            name="shopping_product_state_available",
            value=1,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "SKU-001",
                "product_title": "Sorbent chemiczny 10 kg",
                "currency_code": "PLN",
            },
        ),
        MetricFact(
            name="shopping_product_status",
            value="NOT_ELIGIBLE",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={"product_item_id": "SKU-001"},
        ),
        MetricFact(
            name="shopping_product_availability",
            value="OUT_OF_STOCK",
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={"product_item_id": "SKU-001"},
        ),
        MetricFact(
            name="shopping_product_price_micros",
            value=123450000,
            period="shopping_product_state",
            source_connector="google_ads",
            evidence_id="ev_ads_product_state",
            dimensions={
                "product_item_id": "SKU-001",
                "currency_code": "PLN",
            },
            previous_value=120000000,
            delta=3450000,
            delta_percent=2.875,
        ),
    ]
    current_price_collected_at = datetime(2026, 6, 24, 8, 0, tzinfo=UTC)
    previous_price_collected_at = datetime(2026, 6, 23, 8, 0, tzinfo=UTC)
    state_facts[-1] = state_facts[-1].model_copy(
        update={
            "collected_at": current_price_collected_at,
            "previous_collected_at": previous_price_collected_at,
            "previous_evidence_id": "ev_ads_product_state_previous",
        }
    )
    monkeypatch.setattr(
        "wilq.briefing.merchant_diagnostics._product_performance_metric_facts_by_connector",
        lambda _sample_product_ids: {
            "google_ads": state_facts,
            "google_analytics_4": [],
        },
    )

    refresh_response = client.post(
        "/api/connectors/google_merchant_center/refresh",
        json={"mode": "vendor_read", "reason": "merchant state review decision test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/merchant/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    decision = next(
        item
        for item in payload["decision_queue"]
        if item["id"] == "merchant_decision_review_ads_product_state_mapping"
    )
    assert decision["decision_type"] == "review_product_state_mapping"
    assert decision["status"] == "ready"
    assert decision["metric_tiles"] == {
        "powiązane produkty": 1,
        "niekwalifikujące się": 1,
        "niedostępne": 1,
    }
    assert "NOT_ELIGIBLE" not in decision["metric_tiles"]
    assert "OUT_OF_STOCK" not in decision["metric_tiles"]
    assert "zwrot z reklam na poziomie produktu" in decision["blocked_claims"]
    assert decision["change_preview"][0]["preview_contract"] == (
        "merchant_product_state_review_preview_v1"
    )
    assert decision["change_preview"][0]["products"][0]["product_id"] == ("online~pl~PL~SKU-001")
    assert decision["change_preview"][0]["products"][0]["ads_product_status"] == ("NOT_ELIGIBLE")
    supplemental_preview = next(
        preview
        for preview in decision["change_preview"]
        if preview["preview_contract"] == "merchant_supplemental_feed_review_preview_v1"
    )
    assert supplemental_preview["apply_allowed"] is False
    assert supplemental_preview["api_mutation_ready"] is False
    assert supplemental_preview["primary_feed_mutation_allowed"] is False
    assert supplemental_preview["candidates"][0]["product_id"] == ("online~pl~PL~SKU-001")
    assert supplemental_preview["candidates"][0]["review_fields"] == [
        "availability",
        "price",
    ]
    assert supplemental_preview["candidates"][0]["candidate_status"] == (
        "requires_human_value_confirmation"
    )
    assert decision["preview_cards"]
    assert len(decision["preview_cards"]) == len(decision["change_preview"])
    assert not any(
        "online~pl~PL~SKU" in row["value"]
        or "MerchantProductStateReview" in row["value"]
        or "MerchantSupplementalFeedCandidateReview" in row["value"]
        for card in decision["preview_cards"]
        for row in card["rows"]
    )
    price_readiness = payload["price_impact_readiness"]
    assert price_readiness["status"] == "blocked"
    assert price_readiness["products_with_current_price"] == 1
    assert price_readiness["products_with_previous_price"] == 1
    assert price_readiness["products_with_price_change"] == 1
    assert price_readiness["products_with_unchanged_price_history"] == 0
    assert price_readiness["products_with_performance_metrics"] == 0
    assert price_readiness["missing_read_contracts"] == [
        "google_ads_or_ga4_product_performance_window"
    ]
    price_preview = price_readiness["change_preview"][0]
    assert price_preview["preview_contract"] == "merchant_price_impact_readiness_preview_v1"
    assert price_preview["preview_contract_label"] == "sprawdzenie wpływu ceny"
    assert price_preview["products"][0]["current_price_micros"] == 123450000
    assert price_preview["products"][0]["current_price_collected_at"] == (
        "2026-06-24T08:00:00+00:00"
    )
    assert price_preview["products"][0]["previous_price_micros"] == 120000000
    assert price_preview["products"][0]["previous_price_collected_at"] == (
        "2026-06-23T08:00:00+00:00"
    )
    assert price_preview["products"][0]["previous_price_evidence_id"] == (
        "ev_ads_product_state_previous"
    )
    assert price_preview["products"][0]["has_price_snapshot_history"] is True
    assert price_preview["products"][0]["has_price_change"] is True
    assert price_preview["products"][0]["price_delta_micros"] == 3450000
    assert price_preview["products"][0]["has_product_performance_metrics"] is False
    assert price_readiness["preview_cards"]
    price_preview_card = price_readiness["preview_cards"][0]
    assert price_preview_card["title_label"] == "Podgląd sprawdzenia Merchant"
    assert price_preview_card["subtitle_label"] == "sprawdzenie wpływu ceny"
    assert {
        "label": "Typ sprawdzenia",
        "value": "sprawdzenie wpływu ceny",
    } in price_preview_card["rows"]
    assert not any(
        "online~pl~PL~SKU" in row["value"] or "MerchantPriceImpactReadinessReview" in row["value"]
        for row in price_preview_card["rows"]
    )
    price_decision = next(
        item
        for item in payload["decision_queue"]
        if item["id"] == "merchant_decision_review_price_impact_readiness"
    )
    assert price_decision["decision_type"] == "review_price_impact_readiness"
    assert price_decision["status"] == "blocked"
    assert price_decision["metric_tiles"] == {
        "ceny bieżące": 1,
        "historia ceny": 1,
        "zmiany ceny": 1,
        "performance": 0,
    }
    assert price_decision["change_preview"] == price_readiness["change_preview"]
    assert price_decision["preview_cards"] == price_readiness["preview_cards"]
    assert price_decision["source_connectors"] == price_readiness["source_connectors"]
    assert price_decision["evidence_ids"] == price_readiness["evidence_ids"]
    assert price_decision["blocked_claims"] == price_readiness["blocked_claims"]
    assert price_decision["risk"] == "medium"
    readiness = payload["product_performance_readiness"]
    assert readiness["status"] == "blocked"
    assert readiness["missing_read_contracts"] == [
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    ]
    row = readiness["performance_rows"][0]
    assert row["product_id"] == "online~pl~PL~SKU-001"
    assert row["title_label"] == "Sorbent chemiczny 10 kg"
    assert row["product_reference_label"] == (
        "identyfikator produktu dostępny w szczegółach technicznych"
    )
    assert row["issue_type"] == "availability_updated"
    assert row["ads_product_title"] == "Sorbent chemiczny 10 kg"
    assert row["ads_product_status"] == "NOT_ELIGIBLE"
    assert row["ads_product_status_label"] == "nie kwalifikuje się do emisji"
    assert row["ads_product_availability"] == "OUT_OF_STOCK"
    assert row["ads_product_availability_label"] == "niedostępny"
    assert row["ads_product_price_label"] == "123.45 PLN"
    assert row["ads_clicks_label"] == "kliknięcia Ads do potwierdzenia"
    assert row["ads_cost_label"] == "koszt Ads do potwierdzenia"
    assert row["ads_conversions_label"] == "konwersje Ads do potwierdzenia"
    assert row["ads_conversion_value_label"] == "wartość konwersji Ads do potwierdzenia"
    assert row["ga4_ecommerce_purchases_label"] == "zakupy GA4 do potwierdzenia"
    assert row["ga4_purchase_revenue_label"] == "przychód GA4 do potwierdzenia"
    assert "ads_clicks" in row["missing_metrics"]
    assert "kliknięcia Ads" in row["missing_metric_labels"]
    assert "ads_clicks" not in row["missing_metric_labels"]


def test_merchant_price_impact_blocks_snapshot_history_without_price_change() -> None:
    readiness = _merchant_price_impact_readiness(
        MerchantProductPerformanceReadiness(
            status="blocked",
            joined_product_count=1,
            merchant_sample_count=1,
            ads_product_fact_count=4,
            ga4_product_fact_count=0,
            current_read_contracts=["google_ads_shopping_product_state"],
            required_read_contracts=["google_ads_shopping_product_performance"],
            missing_read_contracts=["google_ads_shopping_product_performance"],
            join_key_candidates=["product_item_id"],
            sample_product_ids=["SKU-001"],
            performance_rows=[
                MerchantProductPerformanceRow(
                    product_id="SKU-001",
                    sample_title="Sorbent chemiczny",
                    source_connectors=["google_ads"],
                    evidence_ids=["ev_ads_product_state"],
                    ads_product_price_micros=123450000,
                    ads_product_currency_code="PLN",
                    ads_product_price_collected_at=datetime(2026, 6, 24, 8, 0, tzinfo=UTC),
                    ads_product_previous_price_micros=123450000,
                    ads_product_previous_price_collected_at=datetime(2026, 6, 23, 8, 0, tzinfo=UTC),
                    ads_product_previous_price_evidence_id="ev_ads_previous",
                    ads_product_price_delta_micros=0,
                    ads_product_price_delta_percent=0.0,
                )
            ],
            source_connectors=["google_merchant_center", "google_ads"],
            evidence_ids=["ev_merchant", "ev_ads_product_state"],
            summary="State-only price snapshot.",
            next_step="Zatrzymaj ocenę wpływu ceny.",
            blocked_claims=["wpływ zmiany ceny"],
        )
    )

    assert readiness.status == "blocked"
    assert readiness.products_with_previous_price == 1
    assert readiness.products_with_price_change == 0
    assert readiness.products_with_unchanged_price_history == 1
    assert "google_ads_shopping_product_price_history" in readiness.current_read_contracts
    assert "merchant_price_change_event_or_snapshot" not in readiness.current_read_contracts
    assert "merchant_price_change_event_or_snapshot" in readiness.missing_read_contracts
    assert "bez wykrytej zmiany ceny" in readiness.summary
    preview_product = readiness.change_preview[0]["products"][0]
    assert preview_product["has_price_snapshot_history"] is True
    assert preview_product["has_price_change"] is False


def test_merchant_diagnostics_groups_reporting_contexts_into_one_operator_decision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "merchant_context_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "merchant_context_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    adc_json = tmp_path / "adc.json"
    adc_json.write_text('{"type":"authorized_user"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(adc_json))
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "5519957373")
    issue_dimensions = {
        "issue_type": "missing_potentially_required_attribute",
        "affected_attribute": "n:unit_pricing_measure",
        "country": "PL",
        "severity": "NOT_IMPACTED",
        "resolution": "MERCHANT_ACTION",
    }
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_merchant_product_status_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Merchant Center zakończony przez test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "total_products": 10900,
                "item_level_issue_count": 15,
                "merchant_action_issue_count": 15,
            },
            metric_facts=[
                VendorMetricFact(
                    "issue_product_count",
                    892,
                    {**issue_dimensions, "reporting_context": "ALL_CONTEXTS"},
                ),
                VendorMetricFact(
                    "issue_product_count",
                    446,
                    {**issue_dimensions, "reporting_context": "FREE_LISTINGS"},
                ),
                VendorMetricFact(
                    "issue_product_count",
                    446,
                    {**issue_dimensions, "reporting_context": "SHOPPING_ADS"},
                ),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_merchant_center/refresh",
        json={"mode": "vendor_read", "reason": "merchant reporting context grouping test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/merchant/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    issue_decisions = [
        decision
        for decision in payload["decision_queue"]
        if decision["issue_type"] == "missing_potentially_required_attribute"
        and decision["affected_attribute"] == "n:unit_pricing_measure"
    ]
    assert len(issue_decisions) == 1
    decision = issue_decisions[0]
    assert decision["reporting_context"] is None
    assert decision["reporting_context_label"] == "wiele kontekstów"
    assert decision["metric_tiles"] == {
        "max zgłoszeń": 892,
        "raporty razem": 1784,
        "konteksty": 3,
    }
    assert (
        "wszystkie konteksty, bezpłatne wyniki produktowe, reklamy produktowe"
        in decision["summary"]
    )
    assert "nie jest liczbą unikalnych produktów" in decision["rationale"]
    assert set(decision["issue_cluster_ids"]) == {
        cluster["id"] for cluster in payload["issue_clusters"]
    }
    assert decision["count_semantics"] == "reported_issue_occurrences"
    assert len(decision["metric_facts"]) == 3
    decision_preview = decision["change_preview"][0]
    assert decision_preview["metric_snapshot"] == {
        "max_issue_product_count": 892,
        "reported_issue_occurrences": 1784,
        "reporting_contexts": 3,
    }
    assert decision_preview["reported_issue_occurrences"] == 1784
    assert len(payload["issue_clusters"]) == 3
    assert payload["operator_summary"]["decision_source"] == "decision_queue"


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
        assert request.url.path == ("/issueresolution/v1/accounts/123456/aggregateProductStatuses")
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
                                "sampleProducts": [
                                    "accounts/123456/products/online~pl~PL~SKU-001",
                                    "accounts/123456/products/online~pl~PL~SKU-002",
                                ],
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
    sample_facts = [fact for fact in result.metric_facts if fact.name == "sample_product_id"]
    assert [fact.value for fact in sample_facts] == [
        "online~pl~PL~SKU-001",
        "online~pl~PL~SKU-002",
    ]
    assert sample_facts[0].dimensions == {
        "country": "PL",
        "reporting_context": "SHOPPING_ADS",
        "severity": "DISAPPROVED",
        "resolution": "MERCHANT_ACTION",
        "issue_type": "missing_image",
        "issue_title": "Missing image",
        "affected_attribute": "image_link",
        "sample_index": "1",
    }


def test_merchant_vendor_read_uses_products_list_for_issue_samples(
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

    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/issueresolution/v1/accounts/123456/aggregateProductStatuses":
            return httpx.Response(
                200,
                json={
                    "aggregateProductStatuses": [
                        {
                            "reportingContext": "SHOPPING_ADS",
                            "country": "PL",
                            "statistics": {"approvedCount": "8"},
                            "issues": [
                                {
                                    "severity": "DISAPPROVED",
                                    "resolution": "MERCHANT_ACTION",
                                    "issueType": "landing_page_error",
                                    "attribute": "link",
                                    "numProducts": "2",
                                }
                            ],
                        }
                    ]
                },
            )
        if request.url.path == "/products/v1/accounts/123456/products":
            assert request.url.params["pageSize"] == "1000"
            return httpx.Response(
                200,
                json={
                    "products": [
                        {
                            "name": "accounts/123456/products/online~pl~PL~SKU-LINK-001",
                            "offerId": "SKU-LINK-001",
                            "productAttributes": {"title": "Sorbent chemiczny 10 kg"},
                            "productStatus": {
                                "itemLevelIssues": [
                                    {
                                        "code": "landing_page_error",
                                        "severity": "DISAPPROVED",
                                        "resolution": "MERCHANT_ACTION",
                                        "attribute": "link",
                                        "reportingContext": "SHOPPING_ADS",
                                        "applicableCountries": ["PL"],
                                    }
                                ]
                            },
                        }
                    ]
                },
            )
        raise AssertionError(f"Unexpected Merchant path: {request.url.path}")

    result = refresh_merchant_product_status_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert requested_paths == [
        "/issueresolution/v1/accounts/123456/aggregateProductStatuses",
        "/products/v1/accounts/123456/products",
    ]
    sample_id = next(fact for fact in result.metric_facts if fact.name == "sample_product_id")
    assert sample_id.value == "online~pl~PL~SKU-LINK-001"
    assert sample_id.dimensions == {
        "country": "PL",
        "reporting_context": "SHOPPING_ADS",
        "severity": "DISAPPROVED",
        "resolution": "MERCHANT_ACTION",
        "issue_type": "landing_page_error",
        "affected_attribute": "link",
        "sample_index": "1",
        "sample_source": "products.list",
    }
    sample_title = next(fact for fact in result.metric_facts if fact.name == "sample_product_title")
    assert sample_title.value == "Sorbent chemiczny 10 kg"
    assert sample_title.dimensions == sample_id.dimensions


def test_merchant_vendor_read_retries_transient_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_service_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID", "123456")
    monkeypatch.setattr(
        "wilq.connectors.google_merchant_center.client.google_access_token",
        lambda scopes: "merchant-access-token",
    )

    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("temporary Merchant timeout", request=request)
        assert request.url.path == ("/issueresolution/v1/accounts/123456/aggregateProductStatuses")
        return httpx.Response(
            200,
            json={
                "aggregateProductStatuses": [
                    {
                        "reportingContext": "SHOPPING_ADS",
                        "country": "PL",
                        "stats": {"activeCount": "8"},
                    }
                ]
            },
        )

    result = refresh_merchant_product_status_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert attempts == 2
    assert result.status == ConnectorRefreshStatus.completed
    assert result.vendor_data_collected is True
    assert result.metric_summary["active_products"] == 8


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


def test_codex_context_pack_scopes_merchant_change_preview(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-merchant-feed-operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-merchant-feed-operator"
    assert data["context_scope"]["source_connectors"] == ["google_merchant_center"]
    assert "merchant_diagnostics" in data
    assert "ads_diagnostics" not in data
    assert "command_center" not in data
    assert data["merchant_diagnostics"]["action_ids"] == ["act_review_merchant_feed_issues"]
    actions_by_id = {action["id"]: action for action in data["active_action_objects"]}
    merchant_action = actions_by_id["act_review_merchant_feed_issues"]
    assert "payload" not in merchant_action
    assert merchant_action["api_endpoint_template"] == "/api/actions/{action_id}"
    assert merchant_action["preview_cards"]
    assert merchant_action["preview_cards_total"] >= 1
    assert merchant_action["preview_cards_included"] >= 1
    preview_card = merchant_action["preview_cards"][0]
    assert "id" not in preview_card
    assert preview_card["kind"] == "merchant_feed_issue_review"
    assert preview_card["title_label"] == "Problem pliku produktowego do sprawdzenia"
    preview_rows = {row["label"]: row["value"] for row in preview_card["rows"]}
    assert "Problem" in preview_rows
    assert "Zgłoszenia" in preview_rows
    assert "zgłoszenia" in preview_rows["Zgłoszenia"]
    assert "online~pl~PL~SKU" not in json.dumps(preview_card, ensure_ascii=False)
    serialized = json.dumps(data, ensure_ascii=False)
    serialized_actions = json.dumps(data["active_action_objects"], ensure_ascii=False)
    assert "payload" not in serialized_actions
    assert "landing_page_error" not in serialized
    assert "SHOPPING_ADS" not in serialized
    assert "MERCHANT_ACTION" not in serialized
    assert "missing_potentially_required_attribute" not in serialized
    assert "command_center" not in data
    assert len(serialized.encode()) < 80_000

    alias_response = client.post(
        "/api/codex/context-pack",
        json={"skill_id": "wilq-merchant-feed-operator"},
    )
    assert alias_response.status_code == 200
    alias_data = alias_response.json()
    assert alias_data["context_scope"]["mode"] == "skill"
    assert alias_data["context_scope"]["skill"] == "wilq-merchant-feed-operator"
    assert "command_center" not in alias_data
