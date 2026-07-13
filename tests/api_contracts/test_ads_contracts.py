"""Google Ads vendor-read and diagnostic API contract tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests._contract_support.api_client import client
from tests._contract_support.env import GOOGLE_ADS_TEST_ENV, clear_google_ads_env
from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
)
from wilq.actions.google_ads.change_history import CHANGE_HISTORY_IMPACT_ACTION_ID
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID
from wilq.briefing.ads_diagnostics import (
    ADS_METRIC_FACT_LIMIT,
    _custom_segment_review_reason,
    _custom_segment_source_quality,
    build_ads_diagnostics,
    build_ads_diagnostics_summary_cached,
    clear_ads_summary_cache,
)
from wilq.connectors.google_ads.client import (
    GOOGLE_ADS_API_VERSION,
    _fetch_optional_shopping_product_performance,
    refresh_google_ads_campaign_summary,
)
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.schemas import (
    ActionObject,
    AdsSearchTermMetricRow,
    ConnectorRefreshMode,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)


def large_ads_metric_fact_fillers(count: int = 2050) -> list[VendorMetricFact]:
    return [
        VendorMetricFact(
            "diagnostic_filler",
            index,
            {
                "campaign_id": "101",
                "campaign_name": "Brand Search",
                "filler_id": str(index),
            },
            period="ads_metric_limit_regression",
        )
        for index in range(count)
    ]


def assert_ads_live_refresh_contract(payload: dict[str, Any]) -> None:
    """Keep freshness/live-data behavior separate from Ads row assertions."""
    assert payload["live_data_available"] is True
    assert payload["latest_refresh"]["status"] == "completed"
    freshness = payload["freshness_assessment"]
    assert freshness["state"] == "fresh"
    assert freshness["state_label"] == "dane świeże"
    assert freshness["requires_refresh"] is False
    assert freshness["stale_after_hours"] == 48
    assert "Google Ads" in freshness["summary"]
    assert payload["blocked_handoff"] is None


def assert_ads_campaign_read_contract_basics(payload: dict[str, Any]) -> None:
    """Keep campaign read-contract gates separate from row rendering proof."""
    read_contract = payload["campaign_read_contract"]
    assert read_contract["status"] == "ready"
    assert read_contract["allowed_metrics"] == [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    for metric in ("conversions", "conversion_value", "recommendations"):
        assert metric not in read_contract["missing_read_contracts"]
    for contract in ("impression_share", "change_history", "search_term_view"):
        assert contract not in read_contract["missing_read_contracts"]
    assert "zwrot z reklam" in read_contract["blocked_claims"]


def assert_ads_campaign_row_contract(
    read_contract: dict[str, Any], evidence_id: str
) -> None:
    """Prove the marketer-facing campaign row without mixing queue assertions."""
    row = read_contract["campaign_rows"][0]
    assert read_contract["campaign_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "campaign_status_label": "aktywna",
            "advertising_channel_type": "SEARCH",
            "advertising_channel_type_label": "sieć wyszukiwania",
            "clicks": 9,
            "clicks_label": "9",
            "impressions": 90,
            "impressions_label": "90",
            "cost_micros": 12000000,
            "cost_label": "12 jedn. konta",
            "conversions": 2.5,
            "conversions_label": "2,5",
            "conversion_value": 450.75,
            "conversion_value_label": "450,75",
            "evidence_ids": [evidence_id],
            "evidence_summary_label": "1 dowód źródłowy",
            "metric_facts": row["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "marnowanie budżetu na zapytaniach",
                "zmarnowany budżet",
            ],
            "blocked_claim_labels": [
                "koszt pozyskania celu",
                "werdykt zwrotu z reklam",
                "werdykt marnowania budżetu na zapytaniach",
                "zmarnowany budżet",
            ],
            "blocked_claim_summary_label": "4 zablokowane obietnice",
            "target_status": "no_target",
            "target_status_label": "brak celu",
            "review_priority": "wysokie",
            "review_score": 50,
            "review_reason": row["review_reason"],
            "human_review_gates": [
                "review_campaign_goal",
                "review_conversion_quality",
                "review_budget_context",
                "review_search_terms_before_budget_decision",
                "human_strategy_review",
            ],
            "human_review_gate_labels": [
                "sprawdzenie celu kampanii",
                "sprawdzenie jakości konwersji",
                "sprawdzenie kontekstu budżetu",
                "wyszukiwane hasła przed decyzją budżetową",
                "ocena strategii przez człowieka",
            ],
            "human_review_gate_summary_label": "5 wymaganych sprawdzeń",
        }
    ]
    assert "Kolejność oceny kampanii" in row["review_reason"]


def assert_ads_operator_summary_contract(
    payload: dict[str, Any], read_contract: dict[str, Any], evidence_id: str
) -> None:
    """Prove the operator summary independently from detailed decision cards."""
    summary = payload["operator_summary"]
    assert summary["id"] == "ads_operator_summary"
    assert summary["title"] == "Co marketer ma sprawdzić teraz w Google Ads"
    assert summary["top_decision_ids"] == [
        decision["id"]
        for decision in sorted(
            payload["decision_queue"],
            key=lambda decision: (0 if decision["status"] == "ready" else 1, decision["priority"]),
        )[:5]
    ]
    assert summary["campaign_count"] == len(read_contract["campaign_rows"])
    assert summary["search_term_count"] == len(
        payload["search_terms_read_contract"]["search_term_rows"]
    )
    assert summary["total_clicks"] == 9
    assert summary["total_impressions"] == 90
    assert summary["total_cost_micros"] == 12000000
    assert summary["total_conversions"] == 2.5
    assert summary["total_conversion_value"] == 450.75
    assert summary["ready_area_count"] == payload["optimizer_readiness_contract"]["ready_area_count"]
    assert summary["blocked_area_count"] == payload["optimizer_readiness_contract"]["blocked_area_count"]
    assert "clicks" in summary["allowed_metrics"]
    assert "google_ads" in summary["source_connectors"]
    assert summary["source_connector_labels"] == ["Google Ads"]
    assert evidence_id in summary["evidence_ids"]
    assert "dowód" in summary["evidence_summary_label"]
    assert "act_prepare_ads_campaign_review_queue" in summary["action_ids"]
    assert "akcj" in summary["action_summary_label"]
    assert "zwrot z reklam" in summary["blocked_claims"]
    assert summary["missing_read_contract_summary_label"]
    assert summary["operator_review_gate_summary_label"]
    assert summary["blocked_claim_summary_label"]
    assert summary["summary"]
    assert summary["next_step"]


def assert_ads_marketer_copy_and_tiles(payload: dict[str, Any]) -> None:
    """Keep Polish copy and human-readable tiles separate from contracts."""
    marketer_text = "\n".join(
        [
            payload["campaign_read_contract"]["summary"],
            payload["search_terms_read_contract"]["summary"],
            payload["search_term_review_summary_contract"]["summary"],
            payload["search_term_ngram_read_contract"]["summary"],
            payload["search_term_safety_read_contract"]["summary"],
            *[decision["summary"] for decision in payload["decision_queue"]],
        ]
    )
    assert "koszt_micros=" not in marketer_text
    assert "koszt 12 PLN" in marketer_text
    campaign_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_campaign_activity"
    )
    assert campaign_decision["metric_tiles"]["koszt"] == "12 PLN"
    budget_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_budget_context"
    )
    assert budget_decision["metric_tiles"]["koszt 7 dni"] == "12 PLN"


def assert_ads_account_currency_contract(payload: dict[str, Any]) -> None:
    """Prove currency context before any budget interpretation."""
    currency_contract = payload["account_currency_read_contract"]
    assert currency_contract["status"] == "ready"
    assert currency_contract["currency_code"] == "PLN"
    assert currency_contract["allowed_metrics"] == ["account_currency_code"]
    assert currency_contract["missing_read_contracts"] == []
    assert "zmiana budżetu" in currency_contract["blocked_claims"]


def assert_ads_business_context_missing_values(payload: dict[str, Any]) -> None:
    """Prove missing business context blocks target and profitability claims."""
    contract = payload["business_context_read_contract"]
    assert contract["status"] == "blocked"
    for field in (
        "profit_margin",
        "business_goal",
        "budget_goal",
        "target_roas",
        "target_cpa_micros",
    ):
        assert contract[field] is None
    assert contract["configured_sources"] == []


def assert_ads_business_context_policy_contract(payload: dict[str, Any]) -> list[str]:
    """Prove policy, review-gate and ActionObject requirements for blocked context."""
    contract = payload["business_context_read_contract"]
    assert contract["business_policy_ids"] == [
        "complete_business_context_before_ads_verdicts",
        "block_target_verdict_until_roas_or_cpa_confirmed",
        "block_target_verdict_until_strategy_review_approved",
    ]
    gates = [
        "human_strategy_review",
        "configure_profit_margin_or_value_model",
        "configure_business_goal",
        "configure_human_budget_goal",
        "confirm_target_roas_or_cpa",
    ]
    assert contract["operator_review_gates"] == gates
    assert contract["operator_review_gate_labels"] == [
        "ocena strategii przez człowieka",
        "uzupełnienie marży albo modelu wartości",
        "uzupełnienie celu biznesowego",
        "uzupełnienie celu budżetu",
        "potwierdzenie docelowego zwrotu z reklam albo kosztu pozyskania celu",
    ]
    assert contract["allowed_metrics"] == []
    assert contract["missing_read_contracts"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    return [
        ADS_BUSINESS_CONTEXT_ACTION_ID,
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]


def assert_ads_business_context_decision_contract(
    payload: dict[str, Any],
    contract: dict[str, Any],
    expected_actions: list[str],
    operator_summary: dict[str, Any],
) -> None:
    """Prove blocked decision card mirrors the API business-context contract."""
    section = next(
        section for section in payload["sections"] if section["id"] == "ads_business_context"
    )
    assert section["status"] == "blocked"
    assert section["action_ids"] == expected_actions
    decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_business_context"
    )
    assert decision["status"] == "blocked"
    assert decision["decision_type"] == "review_business_context"
    assert decision["missing_read_contracts"] == contract["missing_read_contracts"]
    assert decision["metric_tiles"] == {
        "braki": 5,
        "blokady": 6,
        "ustawione pola": 0,
        "warunki sprawdzenia": 5,
        "polityki": 3,
    }
    assert decision["operator_review_gates"] == contract["operator_review_gates"]
    assert decision["operator_review_gate_labels"] == contract["operator_review_gate_labels"]
    assert decision["missing_read_contract_summary_label"]
    assert decision["operator_review_gate_summary_label"]
    assert decision["blocked_claim_summary_label"]
    assert operator_summary["operator_review_gate_labels"]
    assert "human_strategy_review" not in operator_summary["operator_review_gate_labels"]
    assert decision["action_ids"] == expected_actions


def assert_ads_derived_kpi_contract_basics(payload: dict[str, Any]) -> None:
    """Prove derived KPIs are available but profitability claims stay gated."""
    contract = payload["derived_kpi_read_contract"]
    assert contract["status"] == "ready"
    assert contract["allowed_metrics"] == [
        "ctr",
        "average_cpc_micros",
        "conversion_rate",
        "cost_per_conversion_micros",
        "roas",
        "value_per_conversion",
    ]
    assert "profit_margin" in contract["missing_read_contracts"]
    for available in ("account_currency", "recommendations", "impression_share", "change_history"):
        assert available not in contract["missing_read_contracts"]
    assert "opłacalność" in contract["blocked_claims"]


def assert_ads_derived_kpi_row_contract(
    contract: dict[str, Any], evidence_id: str
) -> None:
    """Prove KPI values, lineage and blocked profitability semantics."""
    assert contract["kpi_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "ctr": 0.1,
            "average_cpc_micros": 1333333.333333,
            "conversion_rate": 0.277778,
            "cost_per_conversion_micros": 4800000.0,
            "roas": 37.5625,
            "value_per_conversion": 180.3,
            "target_roas": None,
            "roas_vs_target": None,
            "target_cpa_micros": None,
            "cpa_vs_target_micros": None,
            "target_status": "no_target",
            "target_status_label": "brak celu",
            "target_review_priority": 90,
            "evidence_ids": [evidence_id],
            "source_metric_names": [
                "clicks",
                "conversion_value",
                "conversions",
                "cost_micros",
                "impressions",
            ],
            "missing_metrics": [],
            "blocked_claims": [
                "opłacalność",
                "skalowanie budżetu",
                "zmarnowany budżet",
                "zapis rekomendacji",
            ],
            "blocked_claim_labels": [
                "opłacalność",
                "skalowanie budżetu",
                "zmarnowany budżet",
                "zapis rekomendacji",
            ],
            "blocked_claim_summary_label": "4 zablokowane obietnice",
        }
    ]


def assert_ads_diagnostic_section_contract(payload: dict[str, Any]) -> None:
    """Prove first-screen diagnostic sections remain ready and source-traced."""
    live_section = next(
        section for section in payload["sections"] if section["id"] == "ads_live_data_status"
    )
    assert live_section["status"] == "ready"
    assert "wskazać dowód w WILQ" in live_section["diagnosis"]
    assert "ID dowodu" not in live_section["diagnosis"]
    assert live_section["expert_rule_ids"] == [
        "ads_diagnostics_v1",
        "ads_principles_v1",
        "ads_platform_traps_v1",
    ]
    campaign_section = next(
        section for section in payload["sections"] if section["id"] == "ads_campaign_overview"
    )
    assert campaign_section["status"] == "ready"
    assert campaign_section["title"] == "Aktywność kampanii Google Ads"
    kpi_section = next(
        section for section in payload["sections"] if section["id"] == "ads_derived_kpi"
    )
    assert kpi_section["status"] == "ready"
    assert "rentowności" in kpi_section["diagnosis"]


def assert_ads_budget_contract_basics(payload: dict[str, Any]) -> None:
    """Prove budget pacing is readable but remains review/apply gated."""
    contract = payload["budget_pacing_read_contract"]
    assert contract["status"] == "ready"
    assert contract["empty_state_message"] == (
        "Brak wierszy budżetu kampanii w tym widoku. Odśwież dane Google Ads, "
        "żeby pokazać koszt względem budżetu dziennego."
    )
    for forbidden in (
        "campaign_budget.amount_micros",
        "budget_amount_micros",
        "recommended budget",
        "impression share",
        "review",
    ):
        assert forbidden not in f"{contract['empty_state_message']} {contract['next_step']} {contract['summary']}"
    assert contract["allowed_metrics"] == [
        "budget_amount_micros",
        "cost_micros_7d",
        "seven_day_budget_micros",
        "spend_to_budget_ratio_7d",
        "shared_budget_distribution",
        "budget_has_recommended_budget",
        "budget_recommended_amount_micros",
    ]
    assert "skalowanie budżetu" in contract["blocked_claims"]
    for available in (
        "budget_pacing",
        "recommendations",
        "impression_share",
        "change_history",
        "budget_apply_preview",
        "shared_budget_distribution",
    ):
        assert available not in contract["missing_read_contracts"]
    assert contract["action_ids"] == ["act_prepare_ads_campaign_review_queue"]


def assert_ads_budget_preview_safety_contract(
    contract: dict[str, Any], evidence_id: str
) -> None:
    """Prove budget preview is review-only and mutation-safe."""
    assert len(contract["payload_preview"]) == 1
    preview = contract["payload_preview"][0]
    assert preview["id"] == "budget_apply_preview_101_701"
    assert preview["campaign_id"] == "101"
    assert preview["campaign_name"] == "Brand Search"
    assert preview["campaign_budget_id"] == "701"
    assert preview["campaign_budget_name"] == "Brand budget"
    assert preview["operation_type"] == "CampaignBudgetOperation"
    assert preview["operation_type_label"] == "zmiana budżetu kampanii"
    assert preview["current_budget_amount_micros"] == 30000000
    assert preview["proposed_budget_amount_micros"] == 42000000
    assert preview["proposed_budget_delta_micros"] == 12000000
    assert preview["evidence_ids"] == [evidence_id]
    assert preview["required_validation"] == [
        "review_campaign_activity",
        "verify_account_currency",
        "budget_pacing",
        "impression_share",
        "change_history",
        "human_budget_goal",
        "campaign_budget_apply_safety",
        "campaign_budget_operation_preview",
        "human_confirm_before_apply",
    ]
    assert preview["required_validation_labels"] == [
        "sprawdzenie aktywności kampanii",
        "sprawdzenie waluty konta",
        "tempo wydawania budżetu",
        "udział w wyświetleniach",
        "historia zmian",
        "cel budżetu od człowieka",
        "bezpieczeństwo zmiany budżetu",
        "sprawdzenie zapisu budżetu w Google Ads",
        "potwierdzenie człowieka przed zapisem",
    ]
    assert preview["blocked_claims"] == [
        "skalowanie budżetu",
        "zmiana budżetu",
        "wstrzymanie kampanii",
        "zmarnowany budżet",
        "opłacalność",
        "werdykt kosztu pozyskania celu",
        "werdykt zwrotu z reklam",
        "zapis rekomendacji",
    ]
    assert preview["blocked_claim_labels"] == preview["blocked_claims"]
    assert preview["api_mutation_ready"] is False
    assert preview["apply_allowed"] is False
    assert preview["destructive"] is False
    safety = preview["safety_review"]
    assert safety["safety_contract"] == "campaign_budget_apply_safety_v1"
    assert safety["status"] == "blocked"
    assert safety["status_label"] == "zablokowane"
    assert safety["max_allowed_delta_percent"] == 0.3
    assert safety["proposed_delta_percent"] == 0.4
    assert "budget_delta_within_30_percent" in safety["missing_requirements"]
    assert safety["api_mutation_ready"] is False
    assert safety["apply_allowed"] is False
    assert safety["destructive"] is False


def assert_ads_budget_preview_card_contract(contract: dict[str, Any]) -> None:
    """Prove technical IDs stay below the marketer-facing budget card."""
    card = contract["budget_rows"][0]["preview_card"]
    assert card["kind"] == "google_ads_budget_review"
    assert card["title_label"] == "Budżet kampanii do sprawdzenia"
    rows = {row["label"]: row["value"] for row in card["rows"]}
    assert rows["Budżet teraz"] == "30 PLN"
    assert rows["Propozycja do sprawdzenia"] == "42 PLN"
    assert rows["Operacja"] == "zmiana budżetu kampanii"
    assert rows["Powiązanie"] == "kampania albo budżet do sprawdzenia w szczegółach technicznych"
    assert "CampaignBudgetOperation" not in str(card)
    assert "101" not in str(card)
    assert "701" not in str(card)


def assert_ads_budget_row_contract(
    contract: dict[str, Any], evidence_id: str
) -> None:
    """Prove budget metrics, evidence and blocked claims stay aligned."""
    row = contract["budget_rows"][0]
    assert contract["budget_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "campaign_status_label": "aktywna",
            "advertising_channel_type": "SEARCH",
            "advertising_channel_type_label": "sieć wyszukiwania",
            "budget_id": "701",
            "budget_name": "Brand budget",
            "budget_period": "DAILY",
            "budget_period_label": "dzienny",
            "budget_status": "ENABLED",
            "budget_status_label": "aktywna",
            "budget_amount_micros": 30000000,
            "cost_micros_7d": 12000000,
            "seven_day_budget_micros": 210000000,
            "spend_to_budget_ratio_7d": 0.057143,
            "has_recommended_budget": True,
            "recommended_budget_amount_micros": 42000000,
            "recommended_budget_delta_micros": 12000000,
            "evidence_ids": [evidence_id],
            "metric_facts": row["metric_facts"],
            "payload_preview": contract["payload_preview"][0],
            "preview_card": row["preview_card"],
            "missing_metrics": [],
            "blocked_claims": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "wstrzymanie kampanii",
                "zmarnowany budżet",
                "opłacalność",
                "werdykt kosztu pozyskania celu",
                "werdykt zwrotu z reklam",
                "zapis rekomendacji",
            ],
            "blocked_claim_labels": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "wstrzymanie kampanii",
                "zmarnowany budżet",
                "opłacalność",
                "werdykt kosztu pozyskania celu",
                "werdykt zwrotu z reklam",
                "zapis rekomendacji",
            ],
            "blocked_claim_summary_label": "8 zablokowanych obietnic",
        }
    ]
    assert contract["shared_budget_distribution_rows"] == []


def assert_ads_budget_section_contract(payload: dict[str, Any]) -> None:
    """Prove budget section is ready, knowledge-backed and still review-led."""
    section = next(
        section for section in payload["sections"] if section["id"] == "ads_budget_pacing"
    )
    assert section["status"] == "ready"
    assert "skalowania" in section["diagnosis"]
    assert section["knowledge_card_ids"] == ["card_google_ads_budget_review_playbook"]
    assert section["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]


def assert_ads_recommendations_contract_basics(payload: dict[str, Any]) -> None:
    """Prove recommendation metrics and review gates are available, not applied."""
    contract = payload["recommendations_read_contract"]
    assert contract["status"] == "ready"
    assert contract["allowed_metrics"] == [
        "recommendation_available",
        "recommendation_campaign_count",
        "recommendation_impact_base_clicks",
        "recommendation_impact_potential_clicks",
        "recommendation_impact_base_impressions",
        "recommendation_impact_potential_impressions",
        "recommendation_impact_base_cost_micros",
        "recommendation_impact_potential_cost_micros",
        "recommendation_impact_base_conversions",
        "recommendation_impact_potential_conversions",
        "recommendation_impact_base_conversion_value",
        "recommendation_impact_potential_conversion_value",
    ]
    for available in (
        "recommendations",
        "recommendation_impact_preview",
        "recommendation_apply_preview",
        "impression_share",
        "change_history",
        "human_strategy_review",
    ):
        assert available not in contract["missing_read_contracts"]
    assert contract["operator_review_gates"] == [
        "human_strategy_review",
        "review_recommendation_type",
        "review_impact_metrics",
        "review_change_history",
        "review_business_goal",
        "recommendation_apply_preview",
        "google_ads_rmf_compliance_review",
        "human_confirm_before_apply",
    ]
    assert contract["action_ids"] == [
        "act_prepare_google_ads_recommendation_review_queue"
    ]
    assert "zapis rekomendacji" in contract["blocked_claims"]


def assert_ads_recommendation_row_basics(
    contract: dict[str, Any], evidence_id: str
) -> None:
    """Prove recommendation identity, impact facts and evidence lineage."""
    row = contract["recommendation_rows"][0]
    assert row["recommendation_id"] == "rec-1"
    assert row["recommendation_type"] == "CAMPAIGN_BUDGET"
    assert row["recommendation_type_label"] == "budżet kampanii"
    assert row["review_priority"] == "pilne"
    assert row["review_score"] == 70
    assert row["dismissed"] is False
    assert row["campaign_id"] == "101"
    assert row["campaign_budget_id"] == "701"
    assert row["campaign_count"] == 1
    assert row["impact_available"] is True
    assert row["delta_clicks"] == 5
    assert row["delta_impressions"] == 60
    assert row["delta_cost_micros"] == 2000000
    assert row["evidence_ids"] == [evidence_id]
    assert row["missing_metrics"] == []
    assert row["blocked_claims"] == [
        "zapis rekomendacji",
        "automatyczne przyjęcie rekomendacji",
        "zmiana budżetu",
        "zapis zmian kampanii",
    ]
    assert row["blocked_claim_labels"] == row["blocked_claims"]


def assert_ads_recommendation_review_copy(
    contract: dict[str, Any], row: dict[str, Any]
) -> None:
    """Prove recommendation copy hides vendor IDs and explains review order."""
    card = row["preview_card"]
    assert card["kind"] == "google_ads_recommendation_review"
    assert "101" not in str(card)
    assert "701" not in str(card)
    assert "CAMPAIGN_BUDGET" not in str(card)
    assert "ApplyRecommendationOperation" not in str(card)
    reason = row["review_reason"]
    assert "budżet kampanii" in reason
    assert "podgląd wpływu" in reason
    assert "CAMPAIGN_BUDGET" not in reason
    assert "impact preview" not in reason
    assert "kolejność przeglądu rekomendacji" in reason
    assert "nie zgoda na zapis zmian" in reason
    preview = contract["recommendation_rows"][0]["preview_card"]
    assert preview["title_label"] == "Rekomendacja Google Ads do sprawdzenia"
    values = {entry["label"]: entry["value"] for entry in preview["rows"]}
    assert values["Rekomendacja"] == "budżet kampanii"
    assert values["Operacja"] == "zastosowanie rekomendacji Google Ads"
    assert values["Powiązanie"] == "kampania albo budżet do sprawdzenia w szczegółach technicznych"
    assert "ApplyRecommendationOperation" not in str(preview)
    assert "CAMPAIGN_BUDGET" not in str(preview)
    assert "101" not in str(preview)
    assert "701" not in str(preview)


def test_ads_summary_cache_reuses_one_build_outside_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_ADS_SUMMARY_CACHE_SECONDS", "60")
    clear_ads_summary_cache()
    calls = 0
    sentinel = object()

    def fake_build(*, view: str = "full"):
        nonlocal calls
        calls += 1
        assert view == "summary"
        return sentinel

    monkeypatch.setattr("wilq.briefing.ads_diagnostics.build_ads_diagnostics", fake_build)
    assert build_ads_diagnostics_summary_cached() is sentinel
    assert build_ads_diagnostics_summary_cached() is sentinel
    assert calls == 1
    clear_ads_summary_cache()
    assert build_ads_diagnostics_summary_cached() is sentinel
    assert calls == 2


def test_google_ads_connector_uses_major_endpoint_for_minor_releases() -> None:
    assert GOOGLE_ADS_API_VERSION == "v24"
    assert "." not in GOOGLE_ADS_API_VERSION
    assert "_" not in GOOGLE_ADS_API_VERSION


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

    search_stream_queries: list[str] = []
    keyword_planner_requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            assert "grant_type=refresh_token" in request.content.decode()
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        assert request.url.host == "googleads.googleapis.com"
        if request.url.path == "/v24/customers/1234567890:generateKeywordIdeas":
            assert request.headers["developer-token"] == "developer-token-test"
            assert request.headers["login-customer-id"] == "9998887777"
            assert request.headers["authorization"] == "Bearer ya29.mocktoken"
            payload = json.loads(request.content.decode())
            keyword_planner_requests.append(payload)
            assert payload["keywordSeed"]["keywords"] == ["bdo rejestracja"]
            assert payload["keywordPlanNetwork"] == "GOOGLE_SEARCH_AND_PARTNERS"
            assert payload["geoTargetConstants"] == ["geoTargetConstants/2616"]
            assert payload["language"] == "languageConstants/1045"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "text": "bdo szkolenie",
                            "keywordIdeaMetrics": {
                                "avgMonthlySearches": "100",
                                "competition": "MEDIUM",
                                "competitionIndex": "55",
                                "lowTopOfPageBidMicros": "1200000",
                                "highTopOfPageBidMicros": "4400000",
                            },
                        }
                    ]
                },
            )
        assert request.url.path == "/v24/customers/1234567890/googleAds:searchStream"
        assert request.headers["developer-token"] == "developer-token-test"
        assert request.headers["login-customer-id"] == "9998887777"
        assert request.headers["authorization"] == "Bearer ya29.mocktoken"
        query = json.loads(request.content.decode())["query"]
        search_stream_queries.append(query)
        if "FROM campaign" in query:
            assert "customer.currency_code" in query
            assert "campaign.name" in query
            assert "campaign.status" in query
            assert "campaign.advertising_channel_type" in query
            assert "campaign_budget.amount_micros" in query
            assert "campaign_budget.period" in query
            assert "campaign_budget.has_recommended_budget" in query
            assert "campaign_budget.recommended_budget_amount_micros" in query
            assert "metrics.conversions" in query
            assert "metrics.conversions_value" in query
            assert "metrics.search_impression_share" in query
            assert "metrics.search_budget_lost_impression_share" in query
            assert "metrics.search_rank_lost_impression_share" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "customer": {"currencyCode": "PLN"},
                                "campaign": {
                                    "id": "101",
                                    "name": "Brand Search",
                                    "status": "ENABLED",
                                    "advertisingChannelType": "SEARCH",
                                },
                                "campaignBudget": {
                                    "id": "701",
                                    "name": "Brand budget",
                                    "amountMicros": "30000000",
                                    "period": "DAILY",
                                    "status": "ENABLED",
                                    "hasRecommendedBudget": True,
                                    "recommendedBudgetAmountMicros": "42000000",
                                },
                                "metrics": {
                                    "clicks": "2",
                                    "impressions": "10",
                                    "costMicros": "3000000",
                                    "conversions": "1.5",
                                    "conversionsValue": "250.75",
                                    "searchImpressionShare": 0.73,
                                    "searchBudgetLostImpressionShare": 0.18,
                                    "searchRankLostImpressionShare": 0.09,
                                },
                            },
                            {
                                "customer": {"currencyCode": "PLN"},
                                "campaign": {
                                    "id": "102",
                                    "name": "PMax Feed",
                                    "status": "ENABLED",
                                    "advertisingChannelType": "PERFORMANCE_MAX",
                                },
                                "campaignBudget": {
                                    "id": "702",
                                    "name": "PMax budget",
                                    "amountMicros": "10000000",
                                    "period": "DAILY",
                                    "status": "ENABLED",
                                    "hasRecommendedBudget": False,
                                },
                                "metrics": {
                                    "clicks": "1",
                                    "impressions": "5",
                                    "costMicros": "1000000",
                                    "conversions": "0",
                                    "conversionsValue": "0",
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM recommendation" in query:
            assert "recommendation.resource_name" in query
            assert "recommendation.type" in query
            assert "recommendation.dismissed" in query
            assert "recommendation.campaign_budget" in query
            assert "recommendation.campaigns" in query
            assert "recommendation.impact" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "recommendation": {
                                    "resourceName": ("customers/test/recommendations/rec-1"),
                                    "type": "CAMPAIGN_BUDGET",
                                    "dismissed": False,
                                    "campaign": "customers/test/campaigns/101",
                                    "campaignBudget": ("customers/test/campaignBudgets/701"),
                                    "campaigns": [
                                        "customers/test/campaigns/101",
                                    ],
                                    "impact": {
                                        "baseMetrics": {
                                            "clicks": "20",
                                            "impressions": "200",
                                            "costMicros": "10000000",
                                        },
                                        "potentialMetrics": {
                                            "clicks": "25",
                                            "impressions": "260",
                                            "costMicros": "12000000",
                                        },
                                    },
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM change_event" in query:
            assert "change_event.resource_name" in query
            assert "change_event.change_date_time" in query
            assert "change_event.change_resource_name" in query
            assert "change_event.client_type" in query
            assert "change_event.change_resource_type" in query
            assert "change_event.resource_change_operation" in query
            assert "change_event.changed_fields" in query
            assert "change_event.campaign" in query
            assert "change_event.user_email" not in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "changeEvent": {
                                    "resourceName": "customers/test/changeEvents/change-1",
                                    "changeDateTime": "2026-06-18 12:30:00.000000",
                                    "changeResourceName": "customers/test/campaigns/101",
                                    "clientType": "GOOGLE_ADS_WEB_CLIENT",
                                    "changeResourceType": "CAMPAIGN",
                                    "resourceChangeOperation": "UPDATE",
                                    "changedFields": {
                                        "paths": [
                                            "campaign.status",
                                            "campaign_budget.amount_micros",
                                        ]
                                    },
                                    "campaign": "customers/test/campaigns/101",
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM ad_group_ad_asset_view" in query:
            assert "ad_group_ad_asset_view.field_type = DEMAND_GEN_CAROUSEL_CARD" in query
            assert "asset.id" in query
            assert "asset.type" in query
            assert "metrics.impressions" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "asset": {
                                    "id": "901",
                                    "type": "DEMAND_GEN_CAROUSEL_CARD",
                                },
                                "adGroupAdAssetView": {
                                    "fieldType": "DEMAND_GEN_CAROUSEL_CARD",
                                },
                                "metrics": {"impressions": "44"},
                            },
                        ]
                    }
                ],
            )
        if "FROM ad_group_ad" in query:
            assert "campaign.advertising_channel_type = DEMAND_GEN" in query
            assert "ad_group_ad.ad.type" in query
            assert "ad_group_ad.ad.final_urls" in query
            assert "demand_gen_multi_asset_ad.marketing_images" in query
            assert "demand_gen_carousel_ad.carousel_cards" in query
            assert "demand_gen_video_responsive_ad.videos" in query
            assert "ad_group_ad.ad.demand_gen_multi_asset_ad.headlines" not in query
            assert "ad_group_ad.ad.demand_gen_multi_asset_ad.descriptions" not in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {
                                    "id": "103",
                                    "name": "Demand Gen Test",
                                    "status": "ENABLED",
                                    "advertisingChannelType": "DEMAND_GEN",
                                },
                                "adGroup": {"id": "203", "name": "DG grupa"},
                                "adGroupAd": {
                                    "status": "ENABLED",
                                    "ad": {
                                        "id": "803",
                                        "type": "DEMAND_GEN_MULTI_ASSET_AD",
                                        "finalUrls": ["https://www.ekologus.pl/oferta/"],
                                        "demandGenMultiAssetAd": {
                                            "marketingImages": [
                                                "customers/123/assets/901",
                                                "customers/123/assets/902",
                                            ],
                                            "squareMarketingImages": [
                                                "customers/123/assets/903",
                                            ],
                                            "portraitMarketingImages": [],
                                            "classicDisplayImages": [],
                                            "logoImages": ["customers/123/assets/904"],
                                        },
                                    },
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM shopping_performance_view" in query:
            assert "segments.product_item_id" in query
            assert "segments.product_title" in query
            assert "metrics.clicks" in query
            assert "metrics.impressions" in query
            assert "metrics.cost_micros" in query
            assert "metrics.conversions" in query
            assert "metrics.conversions_value" in query
            assert "segments.date BETWEEN" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {
                                    "id": "102",
                                    "name": "Shopping sorbenty",
                                    "advertisingChannelType": "PERFORMANCE_MAX",
                                },
                                "segments": {
                                    "productItemId": "SKU-001",
                                    "productTitle": "Sorbent chemiczny 10 kg",
                                },
                                "metrics": {
                                    "clicks": "14",
                                    "impressions": "120",
                                    "costMicros": "2750000",
                                    "conversions": "1.5",
                                    "conversionsValue": "320",
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM shopping_product" in query:
            assert "shopping_product.resource_name" in query
            assert "shopping_product.item_id" in query
            assert "shopping_product.title" in query
            assert "shopping_product.status" in query
            assert "shopping_product.availability" in query
            assert "shopping_product.price_micros" in query
            assert "shopping_product.issues" not in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "shoppingProduct": {
                                    "resourceName": (
                                        "customers/1234567890/"
                                        "shoppingProducts/"  # pragma: allowlist secret
                                        "5519957373~ONLINE~pl~PL~SKU-001"
                                    ),
                                    "merchantCenterId": "5519957373",
                                    "channel": "ONLINE",
                                    "languageCode": "pl",
                                    "feedLabel": "PL",
                                    "itemId": "SKU-001",
                                    "title": "Sorbent chemiczny 10 kg",
                                    "status": "ELIGIBLE",
                                    "availability": "IN_STOCK",
                                    "currencyCode": "PLN",
                                    "priceMicros": "123450000",
                                    "targetCountries": ["PL"],
                                }
                            }
                        ]
                    }
                ],
            )
        if "FROM ad_group_criterion" in query:
            assert "ad_group_criterion.keyword.text" in query
            assert "ad_group_criterion.keyword.match_type" in query
            assert "ad_group_criterion.negative" in query
            assert "ad_group_criterion.status" in query
            assert "ad_group_criterion.type = 'KEYWORD'" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {"id": "101", "name": "Brand Search"},
                                "adGroup": {"id": "201", "name": "BDO"},
                                "adGroupCriterion": {
                                    "criterionId": "301",
                                    "status": "ENABLED",
                                    "negative": False,
                                    "keyword": {
                                        "text": "bdo rejestracja",
                                        "matchType": "PHRASE",
                                    },
                                },
                            },
                        ]
                    }
                ],
            )
        if "FROM search_term_view" in query and "BETWEEN" in query:
            assert "segments.date BETWEEN" in query
            assert "LAST_90_DAYS" not in query
            assert "search_term_view.search_term" in query
            assert "metrics.conversions" in query
            assert "metrics.conversions_value" in query
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "campaign": {"id": "101", "name": "Brand Search"},
                                "adGroup": {"id": "201", "name": "BDO"},
                                "searchTermView": {
                                    "searchTerm": "bdo rejestracja",
                                    "status": "ADDED",
                                },
                                "metrics": {
                                    "clicks": "8",
                                    "impressions": "70",
                                    "costMicros": "9000000",
                                    "conversions": "2",
                                    "conversionsValue": "240",
                                },
                            },
                        ]
                    }
                ],
            )
        assert "FROM search_term_view" in query
        assert "search_term_view.search_term" in query
        assert "metrics.conversions" in query
        assert "metrics.conversions_value" in query
        return httpx.Response(
            200,
            json=[
                {
                    "results": [
                        {
                            "campaign": {"id": "101", "name": "Brand Search"},
                            "adGroup": {"id": "201", "name": "BDO"},
                            "searchTermView": {
                                "searchTerm": "bdo rejestracja",
                                "status": "ADDED",
                            },
                            "metrics": {
                                "clicks": "4",
                                "impressions": "20",
                                "costMicros": "5000000",
                                "conversions": "1",
                                "conversionsValue": "120",
                            },
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
    assert result.metric_summary["conversions"] == 1.5
    assert result.metric_summary["conversion_value"] == 250.75
    assert result.metric_summary["customer_currency_code"] == "PLN"
    assert result.metric_summary["budgeted_campaign_count"] == 2
    assert result.metric_summary["recommended_budget_count"] == 1
    assert result.metric_summary["impression_share_row_count"] == 1
    assert result.metric_summary["search_term_row_count"] == 1
    assert result.metric_summary["search_term_clicks"] == 4
    assert result.metric_summary["search_term_impressions"] == 20
    assert result.metric_summary["search_term_cost_micros"] == 5000000
    assert result.metric_summary["search_term_conversions"] == 1.0
    assert result.metric_summary["search_term_conversion_value"] == 120.0
    assert result.metric_summary["search_term_safety_query"] == "search_term_last_90_days"
    assert result.metric_summary["search_term_safety_row_count"] == 1
    assert result.metric_summary["search_term_safety_clicks"] == 8
    assert result.metric_summary["search_term_safety_impressions"] == 70
    assert result.metric_summary["search_term_safety_cost_micros"] == 9000000
    assert result.metric_summary["search_term_safety_conversions"] == 2.0
    assert result.metric_summary["search_term_safety_conversion_value"] == 240.0
    assert result.metric_summary["shopping_product_performance_status"] == "ready"
    assert result.metric_summary["shopping_product_performance_query"] == (
        "shopping_performance_view_last_30_days"
    )
    assert result.metric_summary["shopping_product_performance_lookback_days"] == 30
    assert result.metric_summary["shopping_product_performance_row_count"] == 1
    assert result.metric_summary["shopping_product_performance_product_count"] == 1
    assert result.metric_summary["shopping_product_clicks"] == 14
    assert result.metric_summary["shopping_product_impressions"] == 120
    assert result.metric_summary["shopping_product_cost_micros"] == 2750000
    assert result.metric_summary["shopping_product_conversions"] == 1.5
    assert result.metric_summary["shopping_product_conversion_value"] == 320.0
    assert result.metric_summary["shopping_product_state_status"] == "ready"
    assert result.metric_summary["shopping_product_state_query"] == (
        "shopping_product_current_state"
    )
    assert result.metric_summary["shopping_product_state_row_count"] == 1
    assert result.metric_summary["shopping_product_state_product_count"] == 1
    assert result.metric_summary["shopping_product_state_eligible_count"] == 1
    assert result.metric_summary["shopping_product_state_availability_values"] == "IN_STOCK"
    assert result.metric_summary["recommendation_query"] == "active_recommendations"
    assert result.metric_summary["recommendation_row_count"] == 1
    assert result.metric_summary["recommendation_campaign_count"] == 1
    assert result.metric_summary["recommendation_impact_row_count"] == 1
    assert result.metric_summary["recommendation_impact_metric_count"] == 6
    assert result.metric_summary["recommendation_types"] == "CAMPAIGN_BUDGET"
    assert result.metric_summary["change_event_query"] == "change_event_last_14_days"
    assert result.metric_summary["change_event_row_count"] == 1
    assert result.metric_summary["change_event_campaign_count"] == 1
    assert result.metric_summary["change_event_resource_types"] == "CAMPAIGN"
    assert result.metric_summary["change_event_operations"] == "UPDATE"
    assert result.metric_summary["change_event_client_types"] == "GOOGLE_ADS_WEB_CLIENT"
    assert result.metric_summary["keyword_match_context_query"] == (
        "ad_group_criterion_keyword_context"
    )
    assert result.metric_summary["keyword_match_context_row_count"] == 1
    assert result.metric_summary["keyword_match_context_keyword_count"] == 1
    assert result.metric_summary["keyword_match_context_negative_count"] == 0
    assert result.metric_summary["keyword_match_context_match_types"] == "PHRASE"
    assert result.metric_summary["keyword_planner_status"] == "ready"
    assert result.metric_summary["keyword_planner_seed_term_count"] == 1
    assert result.metric_summary["keyword_planner_idea_count"] == 1
    assert result.metric_summary["keyword_planner_avg_monthly_searches_max"] == 100
    assert result.metric_summary["keyword_planner_competition_values"] == "MEDIUM"
    assert result.metric_summary["demand_gen_ad_group_ad_status"] == "ready"
    assert result.metric_summary["demand_gen_ad_group_ad_row_count"] == 1
    assert result.metric_summary["demand_gen_multi_asset_ad_count"] == 1
    assert result.metric_summary["demand_gen_final_url_count"] == 1
    assert result.metric_summary["demand_gen_asset_reference_count"] == 4
    assert result.metric_summary["demand_gen_creative_asset_status"] == "ready"
    assert result.metric_summary["demand_gen_creative_asset_row_count"] == 1
    assert result.metric_summary["demand_gen_creative_asset_impressions"] == 44
    assert keyword_planner_requests
    assert any("FROM campaign" in query for query in search_stream_queries)
    assert any("FROM search_term_view" in query for query in search_stream_queries)
    assert any(
        "FROM search_term_view" in query and "segments.date BETWEEN" in query
        for query in search_stream_queries
    )
    assert any("FROM recommendation" in query for query in search_stream_queries)
    assert any("FROM change_event" in query for query in search_stream_queries)
    assert any("FROM ad_group_criterion" in query for query in search_stream_queries)
    assert any("FROM ad_group_ad\n" in query for query in search_stream_queries)
    assert any("FROM ad_group_ad_asset_view" in query for query in search_stream_queries)
    assert any("FROM shopping_performance_view" in query for query in search_stream_queries)
    assert any("FROM shopping_product" in query for query in search_stream_queries)
    assert result.metric_facts[0].dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "campaign_status": "ENABLED",
        "advertising_channel_type": "SEARCH",
        "budget_id": "701",
        "budget_name": "Brand budget",
        "budget_period": "DAILY",
        "budget_status": "ENABLED",
    }
    assert result.metric_facts[0].name == "clicks"
    assert result.metric_facts[0].value == 2
    conversion_fact = next(fact for fact in result.metric_facts if fact.name == "conversions")
    assert conversion_fact.value == 1.5
    conversion_value_fact = next(
        fact for fact in result.metric_facts if fact.name == "conversion_value"
    )
    assert conversion_value_fact.value == 250.75
    currency_fact = next(
        fact for fact in result.metric_facts if fact.name == "account_currency_code"
    )
    assert currency_fact.value == "PLN"
    assert currency_fact.period == "account_context"
    budget_amount_fact = next(
        fact for fact in result.metric_facts if fact.name == "budget_amount_micros"
    )
    assert budget_amount_fact.value == 30000000
    assert budget_amount_fact.dimensions["budget_period"] == "DAILY"
    recommended_budget_fact = next(
        fact for fact in result.metric_facts if fact.name == "budget_recommended_amount_micros"
    )
    assert recommended_budget_fact.value == 42000000
    search_term_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_term_clicks"
    )
    assert search_term_fact.value == 4
    assert search_term_fact.dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "ad_group_id": "201",
        "ad_group_name": "BDO",
        "search_term": "bdo rejestracja",
        "search_term_status": "ADDED",
    }
    search_term_conversion_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_term_conversions"
    )
    assert search_term_conversion_fact.value == 1.0
    search_term_safety_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_term_90d_clicks"
    )
    assert search_term_safety_fact.value == 8
    assert search_term_safety_fact.period == "search_term_safety_90d"
    assert search_term_safety_fact.dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "ad_group_id": "201",
        "ad_group_name": "BDO",
        "search_term": "bdo rejestracja",
        "search_term_status": "ADDED",
    }
    keyword_match_type_fact = next(
        fact for fact in result.metric_facts if fact.name == "keyword_match_type"
    )
    assert keyword_match_type_fact.value == "PHRASE"
    assert keyword_match_type_fact.period == "keyword_match_context"
    assert keyword_match_type_fact.dimensions == {
        "campaign_id": "101",
        "campaign_name": "Brand Search",
        "ad_group_id": "201",
        "ad_group_name": "BDO",
        "criterion_id": "301",
        "criterion_status": "ENABLED",
        "keyword_negative": "false",
        "keyword_text": "bdo rejestracja",
        "keyword_match_type": "PHRASE",
    }
    shopping_product_clicks_fact = next(
        fact for fact in result.metric_facts if fact.name == "shopping_product_clicks"
    )
    assert shopping_product_clicks_fact.value == 14
    assert shopping_product_clicks_fact.period == "shopping_product_performance_30d"
    assert shopping_product_clicks_fact.dimensions == {
        "campaign_id": "102",
        "campaign_name": "Shopping sorbenty",
        "advertising_channel_type": "PERFORMANCE_MAX",
        "product_id": "SKU-001",
        "item_id": "SKU-001",
        "product_item_id": "SKU-001",
        "product_title": "Sorbent chemiczny 10 kg",
    }
    shopping_product_value_fact = next(
        fact for fact in result.metric_facts if fact.name == "shopping_product_conversion_value"
    )
    assert shopping_product_value_fact.value == 320.0
    shopping_product_state_fact = next(
        fact for fact in result.metric_facts if fact.name == "shopping_product_state_available"
    )
    assert shopping_product_state_fact.value == 1
    assert shopping_product_state_fact.period == "shopping_product_state"
    assert shopping_product_state_fact.dimensions["product_item_id"] == "SKU-001"
    assert shopping_product_state_fact.dimensions["product_status"] == "ELIGIBLE"
    assert shopping_product_state_fact.dimensions["product_availability"] == "IN_STOCK"
    assert shopping_product_state_fact.dimensions["target_countries"] == "PL"
    shopping_product_price_fact = next(
        fact for fact in result.metric_facts if fact.name == "shopping_product_price_micros"
    )
    assert shopping_product_price_fact.value == 123450000
    impression_share_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_impression_share"
    )
    assert impression_share_fact.value == 0.73
    assert impression_share_fact.dimensions["campaign_id"] == "101"
    budget_lost_fact = next(
        fact for fact in result.metric_facts if fact.name == "search_budget_lost_impression_share"
    )
    assert budget_lost_fact.value == 0.18
    recommendation_fact = next(
        fact for fact in result.metric_facts if fact.name == "recommendation_available"
    )
    assert recommendation_fact.value == 1
    assert recommendation_fact.period == "recommendation"
    assert recommendation_fact.dimensions == {
        "recommendation_id": "rec-1",
        "recommendation_resource_name": "customers/test/recommendations/rec-1",
        "recommendation_type": "CAMPAIGN_BUDGET",
        "dismissed": "false",
        "campaign_id": "101",
        "campaign_budget_id": "701",
        "recommendation_campaign_count": "1",
    }
    recommendation_impact_fact = next(
        fact
        for fact in result.metric_facts
        if fact.name == "recommendation_impact_potential_cost_micros"
    )
    assert recommendation_impact_fact.value == 12000000
    assert recommendation_impact_fact.period == "recommendation_impact"
    assert recommendation_impact_fact.dimensions["recommendation_id"] == "rec-1"
    change_event_fact = next(
        fact for fact in result.metric_facts if fact.name == "change_event_available"
    )
    assert change_event_fact.value == 1
    assert change_event_fact.period == "change_history"
    assert change_event_fact.dimensions == {
        "change_event_id": "change-1",
        "change_date_time": "2026-06-18 12:30:00.000000",
        "change_resource_id": "101",
        "client_type": "GOOGLE_ADS_WEB_CLIENT",
        "change_resource_type": "CAMPAIGN",
        "resource_change_operation": "UPDATE",
        "campaign_id": "101",
        "changed_field_count": "2",
        "changed_fields": "campaign.status,campaign_budget.amount_micros",
    }
    changed_field_count_fact = next(
        fact for fact in result.metric_facts if fact.name == "change_event_changed_field_count"
    )
    assert changed_field_count_fact.value == 2
    keyword_planner_fact = next(
        fact for fact in result.metric_facts if fact.name == "keyword_planner_avg_monthly_searches"
    )
    assert keyword_planner_fact.value == 100
    assert keyword_planner_fact.period == "keyword_planner"
    assert keyword_planner_fact.dimensions == {
        "keyword_idea_text": "bdo szkolenie",
        "seed_terms": "bdo rejestracja",
        "seed_terms_count": "1",
        "language_resource": "languageConstants/1045",
        "geo_target_resource": "geoTargetConstants/2616",
        "competition": "MEDIUM",
    }
    demand_gen_ad_fact = next(
        fact for fact in result.metric_facts if fact.name == "demand_gen_ad_available"
    )
    assert demand_gen_ad_fact.value == 1
    assert demand_gen_ad_fact.period == "demand_gen_ad_inventory"
    assert demand_gen_ad_fact.dimensions == {
        "campaign_id": "103",
        "campaign_name": "Demand Gen Test",
        "campaign_status": "ENABLED",
        "advertising_channel_type": "DEMAND_GEN",
        "ad_group_id": "203",
        "ad_group_name": "DG grupa",
        "ad_id": "803",
        "ad_type": "DEMAND_GEN_MULTI_ASSET_AD",
        "ad_status": "ENABLED",
    }
    demand_gen_asset_count_fact = next(
        fact for fact in result.metric_facts if fact.name == "demand_gen_ad_asset_reference_count"
    )
    assert demand_gen_asset_count_fact.value == 4
    assert demand_gen_asset_count_fact.dimensions["ad_id"] == "803"
    demand_gen_asset_fact = next(
        fact for fact in result.metric_facts if fact.name == "demand_gen_creative_asset_impressions"
    )
    assert demand_gen_asset_fact.value == 44
    assert demand_gen_asset_fact.period == "demand_gen_creative_asset"
    assert demand_gen_asset_fact.dimensions == {
        "asset_id": "901",
        "asset_type": "DEMAND_GEN_CAROUSEL_CARD",
        "field_type": "DEMAND_GEN_CAROUSEL_CARD",
    }
    serialized = json.dumps(result.metric_summary)
    assert "developer-token-test" not in serialized
    assert "refresh-token-test" not in serialized
    serialized_facts = json.dumps([fact.__dict__ for fact in result.metric_facts])
    assert "user_email" not in serialized_facts
    assert "https://www.ekologus.pl/oferta/" not in serialized_facts


def test_google_ads_shopping_product_performance_falls_back_to_90_day_lookback() -> None:
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "googleads.googleapis.com"
        assert request.url.path == "/v24/customers/1234567890/googleAds:searchStream"
        query = json.loads(request.content.decode())["query"]
        queries.append(query)
        assert "FROM shopping_performance_view" in query
        assert "segments.date BETWEEN" in query
        assert "segments.product_item_id" in query
        if len(queries) == 1:
            return httpx.Response(200, json=[{"results": []}])
        return httpx.Response(
            200,
            json=[
                {
                    "results": [
                        {
                            "campaign": {
                                "id": "102",
                                "name": "Shopping sorbenty",
                                "advertisingChannelType": "PERFORMANCE_MAX",
                            },
                            "segments": {
                                "productItemId": "SKU-001",
                                "productTitle": "Sorbent chemiczny 10 kg",
                            },
                            "metrics": {
                                "clicks": "3",
                                "impressions": "33",
                                "costMicros": "990000",
                                "conversions": "1",
                                "conversionsValue": "120",
                            },
                        },
                    ]
                }
            ],
        )

    summary, facts = _fetch_optional_shopping_product_performance(
        httpx.Client(transport=httpx.MockTransport(handler)),
        {
            "developer_token": "developer-token-test",
            "login_customer_id": "9998887777",
            "customer_id": "1234567890",
            "client_id": "unused",
            "client_secret": "unused",  # pragma: allowlist secret
            "refresh_token": "unused",
        },
        "ya29.mocktoken",
    )

    assert len(queries) == 2
    assert queries[0] != queries[1]
    assert summary["shopping_product_performance_status"] == "ready"
    assert summary["shopping_product_performance_query"] == (
        "shopping_performance_view_last_90_days"
    )
    assert summary["shopping_product_performance_lookback_days"] == 90
    assert summary["shopping_product_performance_zero_row_lookbacks"] == "30"
    assert summary["shopping_product_performance_row_count"] == 1
    assert summary["shopping_product_clicks"] == 3
    clicks_fact = next(fact for fact in facts if fact.name == "shopping_product_clicks")
    assert clicks_fact.period == "shopping_product_performance_90d"
    assert clicks_fact.dimensions["product_item_id"] == "SKU-001"


def test_google_ads_vendor_read_discovers_child_accounts_for_manager_customer(
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
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "596-895-8639")
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "596-895-8639")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        body = request.content.decode()
        if "FROM customer_client" in body:
            return httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "customerClient": {
                                    "clientCustomer": "customers/1112223333",
                                    "manager": False,
                                    "level": "1",
                                    "status": "ENABLED",
                                }
                            }
                        ]
                    }
                ],
                request=request,
            )
        return httpx.Response(
            400,
            json=[
                {
                    "error": {
                        "code": 400,
                        "status": "INVALID_ARGUMENT",
                        "details": [
                            {
                                "requestId": "safe-request-id",
                                "errors": [
                                    {"errorCode": {"queryError": "REQUESTED_METRICS_FOR_MANAGER"}}
                                ],
                            }
                        ],
                    }
                }
            ],
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps(
        {
            "summary": result.summary,
            "errors": result.errors,
            "metric_summary": result.metric_summary,
            "metric_facts": [
                {"name": fact.name, "value": fact.value, "dimensions": fact.dimensions}
                for fact in result.metric_facts
            ],
        }
    )
    assert result.status == ConnectorRefreshStatus.blocked
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is True
    assert result.metric_summary["customer_client_count"] == 1
    assert result.metric_summary["non_manager_customer_client_count"] == 1
    assert result.metric_facts[0].name == "customer_client_available"
    assert result.metric_facts[0].dimensions["child_customer_id"] == "1112223333"
    assert "REQUESTED_METRICS_FOR_MANAGER" in serialized
    assert "client-secret-test" not in serialized
    assert "refresh-token-test" not in serialized


def test_google_ads_vendor_read_reports_sanitized_oauth_error(
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
        assert request.url.host == "oauth2.googleapis.com"
        return httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": (
                    "Raw OAuth detail mentioning refresh-token-test and client-secret-test."
                ),
            },
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps(
        {
            "summary": result.summary,
            "errors": result.errors,
            "metric_summary": result.metric_summary,
        }
    )
    assert result.status == ConnectorRefreshStatus.failed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is False
    assert result.metric_summary == {}
    assert "oauth_error=invalid_grant" in serialized
    assert "error_description" not in serialized
    assert "Raw OAuth detail" not in serialized
    assert "refresh-token-test" not in serialized
    assert "client-secret-test" not in serialized


def test_google_ads_vendor_read_reports_sanitized_search_stream_error(
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
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": 400,
                    "status": "INVALID_ARGUMENT",
                    "details": [
                        {
                            "requestId": "safe-request-id",
                            "errors": [
                                {
                                    "errorCode": {"queryError": "BAD_FIELD_NAME"},
                                    "message": (
                                        "Raw detail mentioning refresh-token-test and "
                                        "client-secret-test."
                                    ),
                                }
                            ],
                        }
                    ],
                }
            },
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps({"summary": result.summary, "errors": result.errors})
    assert result.status == ConnectorRefreshStatus.failed
    assert "api_code=400" in serialized
    assert "api_status=INVALID_ARGUMENT" in serialized
    assert "request_id=safe-request-id" in serialized
    assert "ads_error=queryError.BAD_FIELD_NAME" in serialized
    assert "Raw detail" not in serialized
    assert "refresh-token-test" not in serialized
    assert "client-secret-test" not in serialized


def test_google_ads_vendor_read_reports_sanitized_search_stream_list_error(
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
            return httpx.Response(200, json={"access_token": "ya29.mocktoken"})
        return httpx.Response(
            400,
            json=[
                {
                    "error": {
                        "code": 400,
                        "status": "INVALID_ARGUMENT",
                        "details": [
                            {
                                "requestId": "safe-request-id",
                                "errors": [
                                    {
                                        "errorCode": {
                                            "authorizationError": "USER_PERMISSION_DENIED"
                                        },
                                        "message": "Raw detail mentioning refresh-token-test.",
                                    }
                                ],
                            }
                        ],
                    }
                }
            ],
            request=request,
        )

    result = refresh_google_ads_campaign_summary(
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    serialized = json.dumps({"summary": result.summary, "errors": result.errors})
    assert result.status == ConnectorRefreshStatus.failed
    assert "api_code=400" in serialized
    assert "api_status=INVALID_ARGUMENT" in serialized
    assert "request_id=safe-request-id" in serialized
    assert "ads_error=authorizationError.USER_PERMISSION_DENIED" in serialized
    assert "Raw detail" not in serialized
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
            summary="Odczyt Google Ads zakończony przez test adapter.",
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


def test_ads_change_history_treats_empty_read_as_ready_no_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_change_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_change_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary=("Odczyt Google Ads zakończony z wierszami kampanii i bez change_event rows."),
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "row_count": 1,
                "clicks": 9,
                "impressions": 90,
                "cost_micros": 12000000,
                "conversions": 2.5,
                "conversion_value": 450.75,
                "customer_currency_code": "PLN",
                "recommendation_query": "active_recommendations",
                "recommendation_row_count": 1,
                "recommendation_campaign_count": 1,
                "change_event_query": "change_event_last_14_days",
                "change_event_row_count": 0,
            },
            metric_facts=[
                VendorMetricFact(
                    "account_currency_code",
                    "PLN",
                    period="account_context",
                ),
                VendorMetricFact(
                    "clicks",
                    9,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "impressions",
                    90,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "cost_micros",
                    12000000,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversions",
                    2.5,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversion_value",
                    450.75,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "budget_has_recommended_budget",
                    0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "recommendation_available",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": ("customers/test/recommendations/rec-1"),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
                VendorMetricFact(
                    "recommendation_campaign_count",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": ("customers/test/recommendations/rec-1"),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "empty change history contract test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    change_history_contract = payload["change_history_read_contract"]
    assert change_history_contract["status"] == "ready"
    assert change_history_contract["change_history_rows"] == []
    assert "change_event_rows" not in change_history_contract["missing_read_contracts"]
    assert "pre_change_performance_window" in change_history_contract["missing_read_contracts"]
    change_impact_contract = payload["change_impact_readiness_contract"]
    assert change_impact_contract["status"] == "blocked"
    assert change_impact_contract["readiness_rows"] == []
    assert change_impact_contract["apply_allowed"] is False
    assert "change_event_rows" in change_impact_contract["missing_read_contracts"]
    assert "pre_change_performance_window" in change_impact_contract["missing_read_contracts"]
    assert "wpływ zmian" in change_impact_contract["blocked_claims"]
    decisions_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    change_history_decision = decisions_by_id["ads_review_change_history"]
    assert change_history_decision["status"] == "ready"
    assert "brak zdarzeń" in change_history_decision["title"]
    assert change_history_decision["metric_tiles"] == {"zmiany": 0, "kampanie": 0}
    assert "change_event_rows" not in change_history_decision["missing_read_contracts"]
    assert change_history_decision["action_ids"] == []
    assert "Nie przypisuj wyników kampanii do zmian" in change_history_decision["next_step"]
    optimizer_contract = payload["optimizer_readiness_contract"]
    assert optimizer_contract["id"] == "ads_optimizer_readiness_contract"
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["status_label"] == "gotowe do oceny"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["mode_label"] == "ocena bez zapisu"
    assert optimizer_contract["api_mutation_ready"] is False
    assert optimizer_contract["apply_allowed"] is False
    assert optimizer_contract["ready_area_count"] == 2
    assert optimizer_contract["blocked_area_count"] >= 1
    assert "change_event_rows" in optimizer_contract["missing_read_contracts"]
    assert "zdarzenia historii zmian" in optimizer_contract["missing_read_contract_labels"]
    assert "wpływ zmian" in optimizer_contract["blocked_claims"]
    assert "wpływ zmian" in optimizer_contract["blocked_claim_labels"]
    readiness_items_by_id = {item["id"]: item for item in optimizer_contract["readiness_items"]}
    assert readiness_items_by_id["change_history_impact_review"]["status"] == "blocked"
    assert readiness_items_by_id["change_history_impact_review"]["status_label"] == ("zablokowane")
    assert readiness_items_by_id["change_history_impact_review"]["risk_label"] == ("wysokie")
    assert readiness_items_by_id["change_history_impact_review"]["label"] == ("historia zmian")
    assert (
        "change_event_rows"
        in readiness_items_by_id["change_history_impact_review"]["missing_read_contracts"]
    )
    assert (
        "zdarzenia historii zmian"
        in readiness_items_by_id["change_history_impact_review"]["missing_read_contract_labels"]
    )
    assert (
        "checklisty gotowości" in readiness_items_by_id["change_history_impact_review"]["next_step"]
    )

    for decision_id in (
        "ads_review_campaign_activity",
        "ads_review_derived_kpis",
        "ads_review_budget_context",
        "ads_review_recommendations",
    ):
        decision = decisions_by_id[decision_id]
        assert decision["status"] == "ready"
        assert "change_history" not in decision["missing_read_contracts"]


def test_ads_budget_context_exposes_shared_budget_distribution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_shared_budget.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_shared_budget.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")

    shared_budget_dimensions = {
        "campaign_status": "ENABLED",
        "advertising_channel_type": "SEARCH",
        "budget_id": "701",
        "budget_name": "Shared search budget",
        "budget_period": "DAILY",
        "budget_status": "ENABLED",
    }
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Google Ads zakończony z wierszami wspólnego budżetu.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "row_count": 2,
                "cost_micros": 18000000,
                "customer_currency_code": "PLN",
                "change_event_query": "change_event_last_14_days",
                "change_event_row_count": 0,
            },
            metric_facts=[
                VendorMetricFact("account_currency_code", "PLN", period="account_context"),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                    },
                ),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "102",
                        "campaign_name": "Generic Search",
                    },
                ),
                VendorMetricFact(
                    "cost_micros",
                    12000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                    },
                ),
                VendorMetricFact(
                    "cost_micros",
                    6000000,
                    {
                        **shared_budget_dimensions,
                        "campaign_id": "102",
                        "campaign_name": "Generic Search",
                    },
                ),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "shared budget distribution test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    budget_contract = payload["budget_pacing_read_contract"]
    assert budget_contract["status"] == "ready"
    assert "shared_budget_distribution" not in budget_contract["missing_read_contracts"]
    assert budget_contract["shared_budget_distribution_rows"] == [
        {
            "budget_id": "701",
            "budget_name": "Shared search budget",
            "campaign_count": 2,
            "budget_amount_micros": 30000000,
            "seven_day_budget_micros": 210000000,
            "total_cost_micros_7d": 18000000,
            "spend_to_budget_ratio_7d": 0.085714,
            "campaign_shares": [
                {
                    "campaign_id": "101",
                    "campaign_name": "Brand Search",
                    "campaign_status": "ENABLED",
                    "campaign_status_label": "aktywna",
                    "advertising_channel_type": "SEARCH",
                    "advertising_channel_type_label": "sieć wyszukiwania",
                    "cost_micros_7d": 12000000,
                    "spend_share_7d": 0.666667,
                    "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
                },
                {
                    "campaign_id": "102",
                    "campaign_name": "Generic Search",
                    "campaign_status": "ENABLED",
                    "campaign_status_label": "aktywna",
                    "advertising_channel_type": "SEARCH",
                    "advertising_channel_type_label": "sieć wyszukiwania",
                    "cost_micros_7d": 6000000,
                    "spend_share_7d": 0.333333,
                    "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
                },
            ],
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "blocked_claims": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "wstrzymanie kampanii",
                "zmarnowany budżet",
                "opłacalność",
                "werdykt kosztu pozyskania celu",
                "werdykt zwrotu z reklam",
                "zapis rekomendacji",
            ],
            "blocked_claim_labels": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "wstrzymanie kampanii",
                "zmarnowany budżet",
                "opłacalność",
                "werdykt kosztu pozyskania celu",
                "werdykt zwrotu z reklam",
                "zapis rekomendacji",
            ],
            "blocked_claim_summary_label": "8 zablokowanych obietnic",
        }
    ]
    decisions_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    budget_decision = decisions_by_id["ads_review_budget_context"]
    assert "shared_budget_distribution" not in budget_decision["missing_read_contracts"]
    assert (
        budget_decision["shared_budget_distribution_rows"]
        == budget_contract["shared_budget_distribution_rows"]
    )


def test_ads_diagnostics_exposes_oauth_blocker_without_fake_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_diag_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_diag_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Odczyt Google Ads zakończony przez nieświeży test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"row_count": 1, "clicks": 99},
            metric_facts=[
                VendorMetricFact(
                    "clicks",
                    99,
                    {"campaign_id": "stale", "campaign_name": "Stale Campaign"},
                )
            ],
        ),
    )
    stale_refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "ads diagnostics stale metric seed"},
    )
    assert stale_refresh_response.status_code == 200

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.failed,
            summary=(
                "Google Ads OAuth token refresh failed with HTTP 401 (oauth_error=deleted_client)."
            ),
            external_call_attempted=True,
            vendor_data_collected=False,
            errors=["Google Ads OAuth token refresh HTTP 401 (oauth_error=deleted_client)."],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "ads diagnostics blocker test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "pl-PL"
    assert payload["live_data_available"] is False
    assert payload["action_ids"] == ["act_configure_google_ads_env"]
    assert payload["blocker_count"] >= 1
    assert payload["latest_refresh"]["status"] == "failed"
    assert payload["latest_refresh"]["vendor_data_collected"] is False
    assert payload["freshness_assessment"]["state"] == "blocked"
    assert payload["freshness_assessment"]["requires_refresh"] is True
    assert "nie zakończył się pełnym pobraniem metryk" in payload["freshness_assessment"]["summary"]
    assert (
        "uruchom ponownie odczyt danych Google Ads" in payload["freshness_assessment"]["next_step"]
    )
    oauth_section = next(
        section for section in payload["sections"] if section["id"] == "ads_oauth_blocker"
    )
    assert oauth_section["status"] == "blocked"
    assert "oauth_error=deleted_client" in oauth_section["summary"]
    assert "act_configure_google_ads_env" in oauth_section["action_ids"]
    assert oauth_section["metric_facts"] == []
    campaign_section = next(
        section for section in payload["sections"] if section["id"] == "ads_campaign_overview"
    )
    assert campaign_section["status"] == "blocked"
    assert campaign_section["metric_facts"] == []
    search_terms_contract = payload["search_terms_read_contract"]
    assert search_terms_contract["status"] == "blocked"
    assert "search_term_view" in search_terms_contract["missing_read_contracts"]
    assert search_terms_contract["search_term_rows"] == []
    ngram_contract = payload["search_term_ngram_read_contract"]
    assert ngram_contract["status"] == "blocked"
    assert "search_term_view" in ngram_contract["missing_read_contracts"]
    assert ngram_contract["ngram_rows"] == []
    custom_segments_contract = payload["custom_segments_read_contract"]
    assert custom_segments_contract["status"] == "blocked"
    assert "search_term_view" in custom_segments_contract["missing_read_contracts"]
    assert custom_segments_contract["candidates"] == []
    handoff = payload["blocked_handoff"]
    assert handoff["status"] == "blocked"
    assert handoff["title"] == "Google Ads: końcowe przekazanie blokady OAuth"
    assert "oauth_error=deleted_client" in handoff["summary"]
    assert "act_configure_google_ads_env" in handoff["action_ids"]
    assert "google_ads" in handoff["source_connectors"]
    assert "zwrot z reklam" in handoff["blocked_claims"]
    assert any("nie zmyśla metryk Ads" in claim for claim in handoff["allowed_demo_claims"])
    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    brief_metric_item_ids = {
        item["id"] for section in brief_response.json()["sections"] for item in section["items"]
    }
    assert "brief_metric_google_ads" not in brief_metric_item_ids
    serialized = json.dumps(payload)
    assert "refresh-token-test" not in serialized
    assert "client-secret-test" not in serialized


def test_ads_diagnostics_exposes_live_campaign_metric_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_diag_live_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "ads_diag_live_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    for key in GOOGLE_ADS_TEST_ENV:
        monkeypatch.setenv(key, "configured")
    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_google_ads_campaign_summary",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary=(
                "Odczyt Google Ads zakończony przez googleAds:searchStream. Wiersze kampanii: 1."
            ),
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={
                "row_count": 1,
                "clicks": 9,
                "impressions": 90,
                "cost_micros": 12000000,
                "conversions": 2.5,
                "conversion_value": 450.75,
                "customer_currency_code": "PLN",
                "search_term_row_count": 2,
                "search_term_clicks": 10,
                "search_term_impressions": 100,
                "search_term_cost_micros": 12000000,
                "search_term_conversions": 1.0,
                "search_term_conversion_value": 120.0,
                "search_term_safety_query": "search_term_last_90_days",
                "search_term_safety_row_count": 1,
                "search_term_safety_clicks": 10,
                "search_term_safety_impressions": 120,
                "search_term_safety_cost_micros": 8000000,
                "search_term_safety_conversions": 0.0,
                "search_term_safety_conversion_value": 0.0,
                "recommendation_query": "active_recommendations",
                "recommendation_row_count": 1,
                "recommendation_campaign_count": 1,
                "recommendation_impact_row_count": 1,
                "recommendation_impact_metric_count": 6,
                "recommendation_types": "CAMPAIGN_BUDGET",
                "impression_share_row_count": 1,
                "change_event_query": "change_event_last_14_days",
                "change_event_row_count": 1,
                "change_event_campaign_count": 1,
                "change_event_resource_types": "CAMPAIGN",
                "change_event_operations": "UPDATE",
                "change_event_client_types": "GOOGLE_ADS_WEB_CLIENT",
                "keyword_match_context_query": "ad_group_criterion_keyword_context",
                "keyword_match_context_row_count": 1,
                "keyword_match_context_keyword_count": 1,
                "keyword_match_context_negative_count": 0,
                "keyword_match_context_match_types": "BROAD",
                "keyword_planner_status": "ready",
                "keyword_planner_seed_term_count": 2,
                "keyword_planner_idea_count": 1,
                "keyword_planner_avg_monthly_searches_max": 100,
                "keyword_planner_competition_values": "MEDIUM",
            },
            metric_facts=[
                VendorMetricFact(
                    "account_currency_code",
                    "PLN",
                    period="account_context",
                ),
                VendorMetricFact(
                    "clicks",
                    9,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "impressions",
                    90,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "cost_micros",
                    12000000,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversions",
                    2.5,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "conversion_value",
                    450.75,
                    {"campaign_id": "101", "campaign_name": "Brand Search"},
                ),
                VendorMetricFact(
                    "budget_amount_micros",
                    30000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "budget_has_recommended_budget",
                    1,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "budget_recommended_amount_micros",
                    42000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                        "budget_id": "701",
                        "budget_name": "Brand budget",
                        "budget_period": "DAILY",
                        "budget_status": "ENABLED",
                    },
                ),
                VendorMetricFact(
                    "search_impression_share",
                    0.73,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                    },
                ),
                VendorMetricFact(
                    "search_budget_lost_impression_share",
                    0.18,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                    },
                ),
                VendorMetricFact(
                    "search_rank_lost_impression_share",
                    0.09,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "campaign_status": "ENABLED",
                        "advertising_channel_type": "SEARCH",
                    },
                ),
                VendorMetricFact(
                    "recommendation_available",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
                VendorMetricFact(
                    "recommendation_campaign_count",
                    1,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation",
                ),
                VendorMetricFact(
                    "recommendation_impact_base_clicks",
                    20,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_potential_clicks",
                    25,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_base_impressions",
                    200,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_potential_impressions",
                    260,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": "customers/test/recommendations/rec-1",
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_base_cost_micros",
                    10000000,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": ("customers/test/recommendations/rec-1"),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "recommendation_impact_potential_cost_micros",
                    12000000,
                    {
                        "recommendation_id": "rec-1",
                        "recommendation_resource_name": ("customers/test/recommendations/rec-1"),
                        "recommendation_type": "CAMPAIGN_BUDGET",
                        "dismissed": "false",
                        "campaign_id": "101",
                        "campaign_budget_id": "701",
                        "recommendation_campaign_count": "1",
                    },
                    period="recommendation_impact",
                ),
                VendorMetricFact(
                    "change_event_available",
                    1,
                    {
                        "change_event_id": "change-1",
                        "change_date_time": "2026-06-18 12:30:00.000000",
                        "change_resource_id": "101",
                        "client_type": "GOOGLE_ADS_WEB_CLIENT",
                        "change_resource_type": "CAMPAIGN",
                        "resource_change_operation": "UPDATE",
                        "campaign_id": "101",
                        "changed_field_count": "2",
                        "changed_fields": "campaign.status,campaign_budget.amount_micros",
                    },
                    period="change_history",
                ),
                VendorMetricFact(
                    "change_event_changed_field_count",
                    2,
                    {
                        "change_event_id": "change-1",
                        "change_date_time": "2026-06-18 12:30:00.000000",
                        "change_resource_id": "101",
                        "client_type": "GOOGLE_ADS_WEB_CLIENT",
                        "change_resource_type": "CAMPAIGN",
                        "resource_change_operation": "UPDATE",
                        "campaign_id": "101",
                        "changed_field_count": "2",
                        "changed_fields": "campaign.status,campaign_budget.amount_micros",
                    },
                    period="change_history",
                ),
                VendorMetricFact(
                    "search_term_clicks",
                    4,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_impressions",
                    40,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_cost_micros",
                    7000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversions",
                    1.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversion_value",
                    120.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "201",
                        "ad_group_name": "BDO",
                        "search_term": "bdo rejestracja",
                        "search_term_status": "ADDED",
                    },
                ),
                VendorMetricFact(
                    "search_term_clicks",
                    6,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_impressions",
                    60,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_cost_micros",
                    5000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversions",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_conversion_value",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                ),
                VendorMetricFact(
                    "search_term_90d_clicks",
                    10,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_impressions",
                    120,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_cost_micros",
                    8000000,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_conversions",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "search_term_90d_conversion_value",
                    0.0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "search_term": "odpady cena",
                        "search_term_status": "NONE",
                    },
                    period="search_term_safety_90d",
                ),
                VendorMetricFact(
                    "keyword_match_context_available",
                    1,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "criterion_id": "401",
                        "criterion_status": "ENABLED",
                        "keyword_negative": "false",
                        "keyword_text": "odpady",
                        "keyword_match_type": "BROAD",
                    },
                    period="keyword_match_context",
                ),
                VendorMetricFact(
                    "keyword_match_type",
                    "BROAD",
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "criterion_id": "401",
                        "criterion_status": "ENABLED",
                        "keyword_negative": "false",
                        "keyword_text": "odpady",
                        "keyword_match_type": "BROAD",
                    },
                    period="keyword_match_context",
                ),
                VendorMetricFact(
                    "keyword_match_context_negative",
                    0,
                    {
                        "campaign_id": "101",
                        "campaign_name": "Brand Search",
                        "ad_group_id": "202",
                        "ad_group_name": "Odpady",
                        "criterion_id": "401",
                        "criterion_status": "ENABLED",
                        "keyword_negative": "false",
                        "keyword_text": "odpady",
                        "keyword_match_type": "BROAD",
                    },
                    period="keyword_match_context",
                ),
                VendorMetricFact(
                    "keyword_planner_idea_available",
                    1,
                    {
                        "keyword_idea_text": "bdo szkolenie",
                        "seed_terms": "bdo rejestracja, odpady cena",
                        "seed_terms_count": "2",
                        "language_resource": "languageConstants/1045",
                        "geo_target_resource": "geoTargetConstants/2616",
                        "competition": "MEDIUM",
                    },
                    period="keyword_planner",
                ),
                VendorMetricFact(
                    "keyword_planner_avg_monthly_searches",
                    100,
                    {
                        "keyword_idea_text": "bdo szkolenie",
                        "seed_terms": "bdo rejestracja, odpady cena",
                        "seed_terms_count": "2",
                        "language_resource": "languageConstants/1045",
                        "geo_target_resource": "geoTargetConstants/2616",
                        "competition": "MEDIUM",
                    },
                    period="keyword_planner",
                ),
                VendorMetricFact(
                    "keyword_planner_competition_index",
                    55,
                    {
                        "keyword_idea_text": "bdo szkolenie",
                        "seed_terms": "bdo rejestracja, odpady cena",
                        "seed_terms_count": "2",
                        "language_resource": "languageConstants/1045",
                        "geo_target_resource": "geoTargetConstants/2616",
                        "competition": "MEDIUM",
                    },
                    period="keyword_planner",
                ),
                *large_ads_metric_fact_fillers(),
            ],
        ),
    )

    refresh_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "vendor_read", "reason": "ads diagnostics live test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/ads/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert_ads_live_refresh_contract(payload)
    assert_ads_campaign_read_contract_basics(payload)
    read_contract = payload["campaign_read_contract"]
    assert_ads_campaign_row_contract(read_contract, refresh_response.json()["evidence_ids"][-1])
    assert_ads_operator_summary_contract(
        payload, read_contract, refresh_response.json()["evidence_ids"][-1]
    )
    operator_summary = payload["operator_summary"]
    assert_ads_marketer_copy_and_tiles(payload)
    assert_ads_account_currency_contract(payload)
    assert_ads_business_context_missing_values(payload)
    business_context_contract = payload["business_context_read_contract"]
    expected_business_context_actions = assert_ads_business_context_policy_contract(payload)
    assert business_context_contract["target_interpretation"]["status"] == "blocked"
    assert business_context_contract["target_interpretation"]["allowed_uses"] == []
    assert business_context_contract["target_interpretation"]["missing_requirements"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert business_context_contract["target_interpretation"]["action_ids"] == [
        *expected_business_context_actions
    ]
    assert business_context_contract["target_interpretation"]["apply_allowed"] is False
    assert "skalowanie budżetu" in business_context_contract["blocked_claims"]
    assert business_context_contract["metric_tiles"]["marża"] == "marża niepodana"
    assert_ads_business_context_decision_contract(
        payload,
        business_context_contract,
        expected_business_context_actions,
        operator_summary,
    )
    assert_ads_derived_kpi_contract_basics(payload)
    derived_kpi_contract = payload["derived_kpi_read_contract"]
    assert_ads_derived_kpi_row_contract(
        derived_kpi_contract, refresh_response.json()["evidence_ids"][-1]
    )
    assert_ads_diagnostic_section_contract(payload)
    campaign_section = next(
        section for section in payload["sections"] if section["id"] == "ads_campaign_overview"
    )
    assert_ads_budget_contract_basics(payload)
    budget_contract = payload["budget_pacing_read_contract"]
    assert_ads_budget_preview_safety_contract(
        budget_contract, refresh_response.json()["evidence_ids"][-1]
    )
    budget_preview = budget_contract["payload_preview"][0]
    assert_ads_budget_preview_card_contract(budget_contract)
    assert_ads_budget_row_contract(
        budget_contract, refresh_response.json()["evidence_ids"][-1]
    )
    assert_ads_budget_section_contract(payload)
    assert_ads_recommendations_contract_basics(payload)
    recommendations_contract = payload["recommendations_read_contract"]
    assert_ads_recommendation_row_basics(
        recommendations_contract, refresh_response.json()["evidence_ids"][-1]
    )
    recommendation_row = recommendations_contract["recommendation_rows"][0]
    assert recommendation_row["payload_preview"] == recommendations_contract["payload_preview"][0]
    assert_ads_recommendation_review_copy(recommendations_contract, recommendation_row)
    assert recommendations_contract["payload_preview"] == [
        {
            "id": "recommendation_apply_preview_rec-1",
            "recommendation_id": "rec-1",
            "recommendation_resource_name": "customers/test/recommendations/rec-1",
            "recommendation_type": "CAMPAIGN_BUDGET",
            "recommendation_type_label": "budżet kampanii",
            "campaign_id": "101",
            "campaign_budget_id": "701",
            "operation_type": "ApplyRecommendationOperation",
            "operation_type_label": "zastosowanie rekomendacji Google Ads",
            "reason": recommendations_contract["payload_preview"][0]["reason"],
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "source_metric_names": recommendations_contract["payload_preview"][0][
                "source_metric_names"
            ],
            "required_validation": [
                "review_recommendation_type",
                "review_impact_metrics",
                "review_change_history",
                "review_business_goal",
                "recommendation_apply_preview",
                "google_ads_rmf_compliance_review",
                "human_confirm_before_apply",
            ],
            "required_validation_labels": [
                "sprawdzenie typu rekomendacji",
                "sprawdzenie wpływu rekomendacji",
                "sprawdzenie historii zmian",
                "sprawdzenie celu biznesowego",
                "podgląd zapisu rekomendacji",
                "ocena zgodności Google Ads RMF",
                "potwierdzenie człowieka przed zapisem",
            ],
            "blocked_claims": [
                "zapis rekomendacji",
                "automatyczne przyjęcie rekomendacji",
                "zmiana budżetu",
                "zapis zmian kampanii",
                "obietnica poprawy wyniku",
            ],
            "blocked_claim_labels": [
                "zapis rekomendacji",
                "automatyczne przyjęcie rekomendacji",
                "zmiana budżetu",
                "zapis zmian kampanii",
                "obietnica poprawy wyniku",
            ],
            "api_mutation_ready": False,
            "apply_allowed": False,
            "destructive": False,
        }
    ]
    recommendations_section = next(
        section for section in payload["sections"] if section["id"] == "ads_recommendations"
    )
    assert recommendations_section["status"] == "ready"
    assert recommendations_section["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert recommendations_section["expert_rule_ids"] == [
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]
    impression_share_contract = payload["impression_share_read_contract"]
    assert impression_share_contract["status"] == "ready"
    assert impression_share_contract["empty_state_message"] == (
        "Brak wierszy udziału w wyświetleniach. WILQ nie może ocenić utraconej "
        "ekspozycji przez budżet albo ranking bez metryk udziału w wyświetleniach."
    )
    assert "impression share" not in impression_share_contract["summary"]
    assert "impression share" not in impression_share_contract["empty_state_message"]
    assert "budget-lost" not in impression_share_contract["summary"]
    assert "rank-lost" not in impression_share_contract["summary"]
    assert impression_share_contract["allowed_metrics"] == [
        "search_impression_share",
        "search_budget_lost_impression_share",
        "search_rank_lost_impression_share",
    ]
    assert "impression_share" not in impression_share_contract["missing_read_contracts"]
    assert "change_history" not in impression_share_contract["missing_read_contracts"]
    assert "zmiana budżetu" in impression_share_contract["blocked_claims"]
    assert impression_share_contract["impression_share_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "campaign_status_label": "aktywna",
            "advertising_channel_type": "SEARCH",
            "advertising_channel_type_label": "sieć wyszukiwania",
            "search_impression_share": 0.73,
            "search_budget_lost_impression_share": 0.18,
            "search_rank_lost_impression_share": 0.09,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": impression_share_contract["impression_share_rows"][0]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "zmarnowany budżet",
                "obietnica poprawy wyniku",
            ],
            "blocked_claim_labels": [
                "skalowanie budżetu",
                "zmiana budżetu",
                "zmarnowany budżet",
                "obietnica poprawy wyniku",
            ],
            "blocked_claim_summary_label": "4 zablokowane obietnice",
        }
    ]
    impression_share_section = next(
        section for section in payload["sections"] if section["id"] == "ads_impression_share"
    )
    assert impression_share_section["status"] == "ready"
    assert impression_share_section["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert impression_share_section["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_principles_v1",
    ]
    campaign_triage_contract = payload["campaign_triage_read_contract"]
    assert campaign_triage_contract["status"] == "ready"
    assert campaign_triage_contract["title"] == "Kolejność oceny kampanii Ads"
    assert campaign_triage_contract["allowed_metrics"] == [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
        "ctr",
        "average_cpc_micros",
        "conversion_rate",
        "cost_per_conversion_micros",
        "roas",
        "spend_to_budget_ratio_7d",
        "search_budget_lost_impression_share",
        "recommendation_count",
    ]
    assert campaign_triage_contract["missing_read_contracts"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert campaign_triage_contract["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert "zmarnowany budżet" in campaign_triage_contract["blocked_claims"]
    assert campaign_triage_contract["triage_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_status": "ENABLED",
            "campaign_status_label": "aktywna",
            "advertising_channel_type": "SEARCH",
            "advertising_channel_type_label": "sieć wyszukiwania",
            "review_priority": "wysokie",
            "review_score": campaign_triage_contract["triage_rows"][0]["review_score"],
            "review_reason": campaign_triage_contract["triage_rows"][0]["review_reason"],
            "next_step": campaign_triage_contract["triage_rows"][0]["next_step"],
            "target_status": "no_target",
            "target_status_label": "brak celu",
            "clicks": 9,
            "impressions": 90,
            "cost_micros": 12000000,
            "conversions": 2.5,
            "conversion_value": 450.75,
            "ctr": 0.1,
            "average_cpc_micros": 1333333.333333,
            "conversion_rate": 0.277778,
            "cost_per_conversion_micros": 4800000,
            "roas": 37.5625,
            "spend_to_budget_ratio_7d": 0.057143,
            "search_budget_lost_impression_share": 0.18,
            "recommendation_count": 1,
            "recommendation_types": ["CAMPAIGN_BUDGET"],
            "has_budget_apply_preview": True,
            "has_recommendation_apply_preview": True,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "evidence_summary_label": "1 dowód źródłowy",
            "action_ids": ["act_prepare_ads_campaign_review_queue"],
            "action_summary_label": "1 akcja do sprawdzenia",
            "source_metric_names": campaign_triage_contract["triage_rows"][0][
                "source_metric_names"
            ],
            "missing_read_contracts": [
                "profit_margin",
                "business_goal",
                "human_budget_goal",
                "target_roas_or_cpa",
                "human_strategy_review",
            ],
            "missing_read_contract_labels": [
                "marża albo model rentowności",
                "cel biznesowy",
                "cel budżetu od człowieka",
                "docelowy zwrot z reklam albo koszt pozyskania celu",
                "ocena strategii przez człowieka",
            ],
            "missing_read_contract_summary_label": "2 brakujące zakresy danych",
            "blocked_claims": [
                "zmarnowany budżet",
                "opłacalność",
                "skalowanie budżetu",
                "zmiana budżetu",
                "zapis rekomendacji",
                "zapis zmian kampanii",
            ],
            "blocked_claim_labels": [
                "zmarnowany budżet",
                "opłacalność",
                "skalowanie budżetu",
                "zmiana budżetu",
                "zapis rekomendacji",
                "zapis zmian kampanii",
            ],
            "blocked_claim_summary_label": "6 zablokowanych obietnic",
            "human_review_gates": [
                "review_campaign_goal",
                "review_conversion_quality",
                "review_budget_context",
                "review_search_terms_before_budget_decision",
                "human_strategy_review",
                "review_recommendation_type",
                "review_impact_metrics",
                "review_change_history",
                "review_business_goal",
                "campaign_budget_apply_safety",
            ],
            "human_review_gate_labels": [
                "sprawdzenie celu kampanii",
                "sprawdzenie jakości konwersji",
                "sprawdzenie kontekstu budżetu",
                "wyszukiwane hasła przed decyzją budżetową",
                "ocena strategii przez człowieka",
                "sprawdzenie typu rekomendacji",
                "sprawdzenie wpływu rekomendacji",
                "sprawdzenie historii zmian",
                "sprawdzenie celu biznesowego",
                "bezpieczeństwo zmiany budżetu",
            ],
            "human_review_gate_summary_label": "10 wymaganych sprawdzeń",
        }
    ]
    assert "Kolejność oceny kampanii" in campaign_triage_contract["triage_rows"][0]["review_reason"]
    assert "nie jest ocena zmarnowanego budżetu" in campaign_triage_contract["summary"]
    optimizer_contract = payload["optimizer_readiness_contract"]
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["apply_allowed"] is False
    assert "zapis zmian kampanii" in optimizer_contract["blocked_claims"]
    assert "change_event_rows" not in optimizer_contract["missing_read_contracts"]
    assert "pre_change_performance_window" in optimizer_contract["missing_read_contracts"]
    optimizer_items_by_id = {item["id"]: item for item in optimizer_contract["readiness_items"]}
    assert optimizer_items_by_id["campaign_review_queue"]["status"] == "ready"
    assert optimizer_items_by_id["change_history_impact_review"]["status"] == "blocked"
    assert (
        "pre_change_performance_window"
        in optimizer_items_by_id["change_history_impact_review"]["missing_read_contracts"]
    )
    change_history_contract = payload["change_history_read_contract"]
    assert change_history_contract["status"] == "ready"
    assert change_history_contract["status_label"] == "gotowe"
    assert change_history_contract["action_ids"] == [CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_contract["allowed_metrics"] == [
        "change_event_available",
        "change_event_changed_field_count",
    ]
    assert change_history_contract["allowed_metric_labels"] == [
        "historia zmian dostępna",
        "liczba zmienionych pól",
    ]
    assert "change_history" not in change_history_contract["missing_read_contracts"]
    assert change_history_contract["missing_read_contract_labels"] == [
        "wyniki sprzed zmiany",
        "wyniki po zmianie",
        "ręczna ocena wpływu zmian",
        "podgląd zmian",
    ]
    assert "wpływ zmian" in change_history_contract["blocked_claims"]
    assert change_history_contract["blocked_claim_labels"] == [
        "wpływ zmian",
        "obietnica poprawy wyniku",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis zmian kampanii",
    ]
    assert "CAMPAIGN" not in change_history_contract["summary"]
    assert "UPDATE" not in change_history_contract["summary"]
    assert change_history_contract["change_history_rows"] == [
        {
            "change_event_id": "change-1",
            "change_date_time": "2026-06-18 12:30:00.000000",
            "change_resource_id": "101",
            "change_resource_type": "CAMPAIGN",
            "change_resource_type_label": "kampania",
            "change_resource_label": ("zasób zmiany do sprawdzenia w szczegółach technicznych"),
            "resource_change_operation": "UPDATE",
            "resource_change_operation_label": "zmiana",
            "client_type": "GOOGLE_ADS_WEB_CLIENT",
            "client_type_label": "panel Google Ads",
            "campaign_id": "101",
            "campaign_label": "kampania do sprawdzenia w szczegółach technicznych",
            "changed_field_count": 2,
            "changed_fields": ["campaign.status", "campaign_budget.amount_micros"],
            "changed_field_labels": ["status kampanii", "kwota budżetu kampanii"],
            "changed_field_summary_label": "status kampanii, kwota budżetu kampanii",
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "metric_facts": change_history_contract["change_history_rows"][0]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "wpływ zmian",
                "obietnica poprawy wyniku",
                "zmiana budżetu",
                "zapis zmian kampanii",
            ],
            "blocked_claim_labels": [
                "wpływ zmian",
                "obietnica poprawy wyniku",
                "zmiana budżetu",
                "zapis zmian kampanii",
            ],
        }
    ]
    change_impact_contract = payload["change_impact_readiness_contract"]
    assert change_impact_contract["id"] == "ads_change_impact_readiness_contract"
    assert change_impact_contract["status"] == "blocked"
    assert change_impact_contract["status_label"] == "zablokowane"
    assert change_impact_contract["apply_allowed"] is False
    assert "snapshot kampanii" not in change_impact_contract["next_step"]
    assert "aktualny odczyt kampanii" in change_impact_contract["next_step"]
    assert "change_event" not in change_impact_contract["next_step"]
    assert "Impact review" not in change_impact_contract["next_step"]
    assert "wpływ zmian" in change_impact_contract["blocked_claims"]
    assert change_impact_contract["blocked_claim_labels"] == [
        "wpływ zmian",
        "obietnica poprawy wyniku",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis zmian kampanii",
    ]
    assert "change_event_rows" not in change_impact_contract["missing_read_contracts"]
    assert "current_campaign_snapshot" not in change_impact_contract["missing_read_contracts"]
    assert "pre_change_performance_window" in change_impact_contract["missing_read_contracts"]
    assert change_impact_contract["allowed_metrics"] == [
        "change_event_available",
        "change_event_changed_field_count",
        "current_campaign_clicks",
        "current_campaign_impressions",
        "current_campaign_cost_micros",
        "current_campaign_conversions",
        "current_campaign_conversion_value",
    ]
    assert change_impact_contract["allowed_metric_labels"] == [
        "historia zmian dostępna",
        "liczba zmienionych pól",
        "bieżące kliknięcia kampanii",
        "bieżące wyświetlenia kampanii",
        "bieżący koszt kampanii",
        "bieżące konwersje kampanii",
        "bieżąca wartość konwersji kampanii",
    ]
    assert change_impact_contract["readiness_rows"] == [
        {
            "change_event_id": "change-1",
            "change_event_label": "zmiana do sprawdzenia w szczegółach technicznych",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_label": "Brand Search",
            "change_date_time": "2026-06-18 12:30:00.000000",
            "changed_fields": ["campaign.status", "campaign_budget.amount_micros"],
            "changed_field_labels": ["status kampanii", "kwota budżetu kampanii"],
            "current_campaign_metrics_available": True,
            "pre_window_available": False,
            "post_window_available": False,
            "current_clicks": 9,
            "current_impressions": 90,
            "current_cost_micros": 12000000,
            "current_conversions": 2.5,
            "current_conversion_value": 450.75,
            "missing_read_contracts": [
                "pre_change_performance_window",
                "post_change_performance_window",
                "human_change_impact_review",
                "apply_preview",
            ],
            "missing_read_contract_labels": [
                "wyniki sprzed zmiany",
                "wyniki po zmianie",
                "ręczna ocena wpływu zmian",
                "podgląd zmian",
            ],
            "missing_read_contract_summary_label": "1 brakujący zakres danych",
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "blocked_claims": [
                "wpływ zmian",
                "obietnica poprawy wyniku",
                "skalowanie budżetu",
                "zmiana budżetu",
                "zapis zmian kampanii",
            ],
            "blocked_claim_labels": [
                "wpływ zmian",
                "obietnica poprawy wyniku",
                "skalowanie budżetu",
                "zmiana budżetu",
                "zapis zmian kampanii",
            ],
            "blocked_claim_summary_label": "5 zablokowanych obietnic",
        }
    ]
    assert optimizer_items_by_id["change_history_impact_review"]["source_contract_ids"] == [
        "ads_change_history_read_contract",
        "ads_change_impact_readiness_contract",
    ]
    assert (
        "current_campaign_snapshot"
        not in optimizer_items_by_id["change_history_impact_review"]["missing_read_contracts"]
    )
    change_history_section = next(
        section for section in payload["sections"] if section["id"] == "ads_change_history"
    )
    assert change_history_section["status"] == "ready"
    assert change_history_section["action_ids"] == [CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_section["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert change_history_section["expert_rule_ids"] == [
        "ads_diagnostics_v1",
        "ads_principles_v1",
    ]
    facts_by_name = {fact["name"]: fact for fact in campaign_section["metric_facts"]}
    assert facts_by_name["clicks"]["value"] == 9
    assert facts_by_name["conversions"]["value"] == 2.5
    assert facts_by_name["conversion_value"]["value"] == 450.75
    assert any(
        fact["name"] == "cost_micros" and fact["dimensions"].get("campaign_name") == "Brand Search"
        for fact in campaign_section["metric_facts"]
    )
    assert "act_configure_google_ads_env" not in payload["action_ids"]
    search_terms_contract = payload["search_terms_read_contract"]
    assert search_terms_contract["status"] == "ready"
    assert search_terms_contract["allowed_metrics"] == [
        "search_term",
        "campaign",
        "ad_group",
        "status",
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    assert "conversions" not in search_terms_contract["missing_read_contracts"]
    assert "conversion_value" not in search_terms_contract["missing_read_contracts"]
    assert "90_day_safety_check" not in search_terms_contract["missing_read_contracts"]
    assert (
        "negative_keyword_action_validation" not in search_terms_contract["missing_read_contracts"]
    )
    assert search_terms_contract["operator_review_gates"] == ["negative_keyword_action_validation"]
    assert "dodanie wykluczających słów kluczowych" in search_terms_contract["blocked_claims"]
    assert search_terms_contract["search_term_rows"] == [
        {
            "search_term": "bdo rejestracja",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_label": "Brand Search",
            "ad_group_id": "201",
            "ad_group_name": "BDO",
            "ad_group_label": "BDO",
            "search_term_status": "ADDED",
            "clicks": 4,
            "impressions": 40,
            "cost_micros": 7000000,
            "conversions": 1.0,
            "conversion_value": 120.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "evidence_summary_label": "1 dowód źródłowy",
            "metric_facts": search_terms_contract["search_term_rows"][0]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "dodanie wykluczających słów kluczowych",
                "zmarnowany budżet",
            ],
        },
        {
            "search_term": "odpady cena",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_label": "Brand Search",
            "ad_group_id": "202",
            "ad_group_name": "Odpady",
            "ad_group_label": "Odpady",
            "search_term_status": "NONE",
            "clicks": 6,
            "impressions": 60,
            "cost_micros": 5000000,
            "conversions": 0.0,
            "conversion_value": 0.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "evidence_summary_label": "1 dowód źródłowy",
            "metric_facts": search_terms_contract["search_term_rows"][1]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "dodanie wykluczających słów kluczowych",
                "zmarnowany budżet",
            ],
        },
    ]
    search_term_review_contract = payload["search_term_review_summary_contract"]
    assert search_term_review_contract["status"] == "ready"
    assert search_term_review_contract["total_search_term_count"] == 2
    assert search_term_review_contract["zero_conversion_search_term_count"] == 1
    assert search_term_review_contract["total_clicks"] == 10
    assert search_term_review_contract["total_impressions"] == 100
    assert search_term_review_contract["total_cost_micros"] == 12000000
    assert search_term_review_contract["total_conversions"] == 1.0
    assert search_term_review_contract["top_cost_search_terms"][0]["search_term"] == (
        "bdo rejestracja"
    )
    assert search_term_review_contract["campaign_review_rows"] == [
        {
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_label": "Brand Search",
            "search_term_count": 2,
            "zero_conversion_search_term_count": 1,
            "clicks": 10,
            "impressions": 100,
            "cost_micros": 12000000,
            "conversions": 1.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "evidence_summary_label": "1 dowód źródłowy",
            "blocked_claims": [
                "marnowanie budżetu na zapytaniach",
                "dodanie wykluczających słów kluczowych",
                "koszt pozyskania celu",
                "zwrot z reklam",
            ],
        }
    ]
    assert "marnowanie budżetu na zapytaniach" in search_term_review_contract["blocked_claims"]
    assert "dodanie wykluczających słów kluczowych" in search_term_review_contract["blocked_claims"]
    assert search_term_review_contract["missing_read_contract_summary_label"]
    assert search_term_review_contract["operator_review_gate_summary_label"]
    assert search_term_review_contract["blocked_claim_summary_label"]
    search_terms_section = next(
        section for section in payload["sections"] if section["id"] == "ads_search_terms"
    )
    assert search_terms_section["status"] == "ready"
    assert search_terms_section["title"] == "Zapytania użytkowników Google Ads"
    ngram_contract = payload["search_term_ngram_read_contract"]
    assert ngram_contract["status"] == "ready"
    assert ngram_contract["allowed_metrics"] == [
        "ngram",
        "ngram_size",
        "source_search_term_count",
        "sample_search_terms",
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    assert ngram_contract["missing_read_contracts"] == [
        "human_intent_review",
        "ngram_to_negative_keyword_change_preview",
    ]
    assert "negative_keyword_change_preview" not in ngram_contract["missing_read_contracts"]
    assert ngram_contract["operator_review_gates"] == [
        "human_intent_review",
        "negative_keyword_action_validation",
    ]
    assert ngram_contract["action_ids"] == [SEARCH_TERM_NGRAM_ACTION_ID]
    assert "marnowanie budżetu na zapytaniach" in ngram_contract["blocked_claims"]
    assert "dodanie wykluczających słów kluczowych" in ngram_contract["blocked_claims"]
    assert ngram_contract["ngram_rows"]
    ngrams_by_name = {row["ngram"]: row for row in ngram_contract["ngram_rows"]}
    assert ngrams_by_name["bdo"]["source_search_term_count"] == 1
    assert ngrams_by_name["bdo"]["clicks"] == 4
    assert ngrams_by_name["bdo rejestracja"]["ngram_size"] == 2
    assert ngrams_by_name["odpady cena"]["cost_micros"] == 5000000
    assert all(row["evidence_ids"] for row in ngram_contract["ngram_rows"])
    assert all(
        "marnowanie budżetu na zapytaniach" in row["blocked_claims"]
        for row in ngram_contract["ngram_rows"]
    )
    ngram_section = next(
        section for section in payload["sections"] if section["id"] == "ads_search_term_ngrams"
    )
    assert ngram_section["status"] == "ready"
    assert ngram_section["title"] == "N-gramy zapytań Google Ads"
    assert ngram_section["action_ids"] == [SEARCH_TERM_NGRAM_ACTION_ID]
    ngram_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_search_term_ngrams"
    )
    assert ngram_decision["decision_type"] == "review_search_term_ngrams"
    assert ngram_decision["priority"] == 42
    assert ngram_decision["metric_tiles"]["n-gramy"] == len(ngram_contract["ngram_rows"])
    assert ngram_decision["metric_tiles"]["pokazane"] == len(
        ngram_decision["search_term_ngram_rows"]
    )
    assert ngram_decision["metric_tiles"]["max query/temat"] >= 1
    assert ngram_decision["metric_tiles"]["top kliknięcia"] >= 4
    assert "top koszt" in ngram_decision["metric_tiles"]
    assert ngram_decision["search_term_ngram_rows"]
    assert ngram_decision["action_ids"] == [SEARCH_TERM_NGRAM_ACTION_ID]
    assert "ngram_to_negative_keyword_change_preview" in ngram_decision["missing_read_contracts"]
    assert "negative_keyword_change_preview" not in ngram_decision["missing_read_contracts"]
    assert "card_google_ads_search_playbook" in ngram_decision["knowledge_card_ids"]
    search_term_safety_contract = payload["search_term_safety_read_contract"]
    assert search_term_safety_contract["status"] == "ready"
    assert search_term_safety_contract["allowed_metrics"] == [
        "search_term",
        "campaign",
        "ad_group",
        "status",
        "search_term_90d_clicks",
        "search_term_90d_impressions",
        "search_term_90d_cost_micros",
        "search_term_90d_conversions",
        "search_term_90d_conversion_value",
    ]
    assert "90_day_safety_check" not in search_term_safety_contract["missing_read_contracts"]
    assert (
        "negative_keyword_change_preview"
        not in search_term_safety_contract["missing_read_contracts"]
    )
    assert "keyword match context" not in search_term_safety_contract["missing_read_contracts"]
    assert "human_intent_review" not in search_term_safety_contract["missing_read_contracts"]
    assert search_term_safety_contract["operator_review_gates"] == ["human_intent_review"]
    assert "dodanie wykluczających słów kluczowych" in search_term_safety_contract["blocked_claims"]
    assert search_term_safety_contract["safety_rows"] == [
        {
            "search_term": "odpady cena",
            "campaign_id": "101",
            "campaign_name": "Brand Search",
            "campaign_label": "Brand Search",
            "ad_group_id": "202",
            "ad_group_name": "Odpady",
            "ad_group_label": "Odpady",
            "search_term_status": "NONE",
            "clicks_90d": 10,
            "impressions_90d": 120,
            "cost_micros_90d": 8000000,
            "conversions_90d": 0.0,
            "conversion_value_90d": 0.0,
            "evidence_ids": [refresh_response.json()["evidence_ids"][-1]],
            "evidence_summary_label": "1 dowód źródłowy",
            "metric_facts": search_term_safety_contract["safety_rows"][0]["metric_facts"],
            "missing_metrics": [],
            "blocked_claims": [
                "koszt pozyskania celu",
                "zwrot z reklam",
                "dodanie wykluczających słów kluczowych",
                "zmarnowany budżet",
            ],
        }
    ]
    search_term_safety_section = next(
        section for section in payload["sections"] if section["id"] == "ads_search_term_safety"
    )
    assert search_term_safety_section["status"] == "ready"
    assert search_term_safety_section["knowledge_card_ids"] == [
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_search_playbook",
    ]
    keyword_context_contract = payload["keyword_match_context_read_contract"]
    assert keyword_context_contract["status"] == "ready"
    assert keyword_context_contract["allowed_metrics"] == [
        "keyword_text",
        "keyword_match_type",
        "criterion_status",
        "keyword_negative",
        "campaign",
        "ad_group",
    ]
    assert keyword_context_contract["missing_read_contracts"] == []
    assert keyword_context_contract["operator_review_gates"] == ["human_intent_review"]
    assert keyword_context_contract["context_rows"][0]["keyword_text"] == "odpady"
    assert keyword_context_contract["context_rows"][0]["match_type"] == "BROAD"
    assert keyword_context_contract["context_rows"][0]["negative"] is False
    keyword_context_section = next(
        section for section in payload["sections"] if section["id"] == "ads_keyword_match_context"
    )
    assert keyword_context_section["status"] == "ready"
    assert keyword_context_section["knowledge_card_ids"] == [
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_search_playbook",
    ]
    keyword_planner_contract = payload["keyword_planner_read_contract"]
    assert keyword_planner_contract["status"] == "ready"
    assert keyword_planner_contract["missing_read_contracts"] == ["forecast_or_audience_size"]
    assert keyword_planner_contract["idea_rows"][0]["idea_text"] == "bdo szkolenie"
    assert keyword_planner_contract["idea_rows"][0]["avg_monthly_searches"] == 100
    assert keyword_planner_contract["idea_rows"][0]["competition"] == "MEDIUM"
    keyword_planner_section = next(
        section for section in payload["sections"] if section["id"] == "ads_keyword_planner"
    )
    assert keyword_planner_section["status"] == "ready"
    custom_segments_contract = payload["custom_segments_read_contract"]
    assert custom_segments_contract["status"] == "ready"
    assert custom_segments_contract["title"] == "Segmenty z realnych wyszukiwanych haseł"
    assert custom_segments_contract["action_ids"] == [
        "act_prepare_custom_segments_from_search_terms"
    ]
    assert custom_segments_contract["evidence_summary_label"] == "1 dowód źródłowy"
    assert custom_segments_contract["action_summary_label"] == "1 akcja do sprawdzenia"
    assert "keyword_planner_enrichment" not in custom_segments_contract["missing_read_contracts"]
    assert "forecast_or_audience_size" in custom_segments_contract["missing_read_contracts"]
    assert (
        "prognoza albo rozmiar odbiorców"
        in custom_segments_contract["missing_read_contract_labels"]
    )
    assert custom_segments_contract["operator_review_gates"] == [
        "review_source_terms",
        "reject_brand_or_low_intent_terms",
        "keyword_planner_enrichment",
        "forecast_or_audience_size",
        "human_confirm_before_apply",
    ]
    assert "custom_segment_change_preview" not in custom_segments_contract["missing_read_contracts"]
    assert "rozmiar odbiorców" in custom_segments_contract["blocked_claims"]
    assert "rozmiar odbiorców" in custom_segments_contract["blocked_claim_labels"]
    audience_forecast_contract = custom_segments_contract["audience_forecast_read_contract"]
    assert audience_forecast_contract["status"] == "blocked"
    assert audience_forecast_contract["evidence_summary_label"] == "1 dowód źródłowy"
    assert audience_forecast_contract["checked_candidate_count"] == 1
    assert audience_forecast_contract["forecast_row_count"] == 1
    assert audience_forecast_contract["missing_read_contracts"] == [
        "forecast_or_audience_size",
    ]
    assert audience_forecast_contract["missing_read_contract_labels"] == [
        "prognoza albo rozmiar odbiorców",
    ]
    assert audience_forecast_contract["operator_review_gates"] == [
        "forecast_or_audience_size",
        "human_confirm_before_apply",
    ]
    assert "rozmiar odbiorców" in audience_forecast_contract["blocked_claims"]
    assert "rozmiar odbiorców" in audience_forecast_contract["blocked_claim_labels"]
    forecast_row = audience_forecast_contract["forecast_rows"][0]
    assert forecast_row["candidate_id"] == custom_segments_contract["candidates"][0]["id"]
    assert (
        forecast_row["custom_segment_name"] == (custom_segments_contract["candidates"][0]["name"])
    )
    assert forecast_row["status"] == "missing_forecast"
    assert forecast_row["forecast_available"] is False
    assert forecast_row["audience_size"] is None
    assert forecast_row["source_terms"] == ["bdo rejestracja", "odpady cena"]
    assert "prognozy albo rozmiaru odbiorców" in forecast_row["reason"]
    assert "zwrot z reklam" in forecast_row["blocked_claim_labels"]
    assert forecast_row["evidence_ids"] == [refresh_response.json()["evidence_ids"][-1]]
    assert forecast_row["evidence_summary_label"] == "1 dowód źródłowy"
    assert custom_segments_contract["candidates"][0]["source_terms"] == [
        "bdo rejestracja",
        "odpady cena",
    ]
    assert custom_segments_contract["candidates"][0]["evidence_summary_label"] == (
        "1 dowód źródłowy"
    )
    assert custom_segments_contract["candidates"][0]["source_quality"] == {
        "total_terms": 2,
        "accepted_terms": 2,
        "rejected_terms": 0,
        "missing_metric_terms": 0,
        "rejection_reasons": {},
        "rejection_reason_labels": {},
    }
    assert custom_segments_contract["candidates"][0]["review_priority"] == "pilne"
    assert custom_segments_contract["candidates"][0]["review_score"] == 85
    assert custom_segments_contract["candidates"][0]["confidence_label"] == "niska"
    assert custom_segments_contract["candidates"][0]["validation_status_label"] == (
        "do sprawdzenia"
    )
    preview_card = custom_segments_contract["candidates"][0]["preview_card"]
    assert preview_card["kind"] == "google_ads_custom_segment_review"
    assert preview_card["title_label"] == "Segment odbiorców do sprawdzenia"
    assert preview_card["status_label"] == "zapis zmian zablokowany"
    assert preview_card["rows"][0] == {
        "label": "Nazwa",
        "value": custom_segments_contract["candidates"][0]["name"],
    }
    assert "zapis zmian zablokowany" in preview_card["apply_state_label"]
    assert "zwrot z reklam" in custom_segments_contract["candidates"][0]["blocked_claim_labels"]
    assert "kolejność oceny segmentu" in custom_segments_contract["candidates"][0]["review_reason"]
    assert (
        "nie dowód rozmiaru odbiorców" in custom_segments_contract["candidates"][0]["review_reason"]
    )
    assert custom_segments_contract["candidates"][0]["human_review_gates"] == [
        "sprawdź intencję haseł źródłowych",
        "odrzuć brand, konkurencję i frazy o niskiej intencji",
        "sprawdź wzbogacenie Keyword Planner",
        "sprawdź prognozę albo rozmiar odbiorców",
        "zatwierdź segment przed zapisem zmian",
    ]
    assert (
        custom_segments_contract["candidates"][0]["keyword_planner_ideas"][0]["idea_text"]
        == "bdo szkolenie"
    )
    assert (
        custom_segments_contract["payload_preview"][0]
        == (custom_segments_contract["candidates"][0]["payload_preview"])
    )
    assert custom_segments_contract["payload_preview"][0]["member_type"] == "KEYWORD"
    assert custom_segments_contract["payload_preview"][0]["apply_allowed"] is False
    assert custom_segments_contract["payload_preview"][0]["api_mutation_ready"] is False
    assert custom_segments_contract["payload_preview"][0]["destructive"] is False
    assert (
        "prognoza albo rozmiar odbiorców"
        in custom_segments_contract["payload_preview"][0]["required_validation_labels"]
    )
    assert (
        "zwrot z reklam" in custom_segments_contract["payload_preview"][0]["blocked_claim_labels"]
    )
    assert (
        "prognoza albo rozmiar odbiorców"
        in custom_segments_contract["payload_preview"][0]["safety_review"][
            "missing_requirement_labels"
        ]
    )
    assert (
        "sprawdzenie zapisu zmian w Google Ads"
        in custom_segments_contract["payload_preview"][0]["safety_review"][
            "required_validation_labels"
        ]
    )
    targeting_preview = custom_segments_contract["payload_preview"][0]["targeting_preview"][0]
    assert "prognoza albo rozmiar odbiorców" in targeting_preview["required_validation_labels"]
    assert targeting_preview["operation_type"] == "custom_segment_targeting_review"
    assert targeting_preview["target_scope"] == "campaign_context_review"
    assert targeting_preview["campaign_id"] == "101"
    assert targeting_preview["campaign_name"] == "Brand Search"
    assert targeting_preview["apply_allowed"] is False
    assert targeting_preview["api_mutation_ready"] is False
    assert targeting_preview["destructive"] is False
    assert "forecast_or_audience_size" in targeting_preview["required_validation"]
    assert custom_segments_contract["candidates"][0]["confidence"] == "low"
    assert custom_segments_contract["candidates"][0]["validation_status"] == ("pending_validation")
    assert custom_segments_contract["candidates"][0]["evidence_ids"] == [
        refresh_response.json()["evidence_ids"][-1]
    ]
    custom_segments_section = next(
        section for section in payload["sections"] if section["id"] == "ads_custom_segments"
    )
    assert custom_segments_section["status"] == "ready"
    negative_keywords_contract = payload["negative_keywords_read_contract"]
    assert negative_keywords_contract["status"] == "ready"
    assert negative_keywords_contract["title"] == "Ocena wykluczeń z wyszukiwanych haseł"
    assert negative_keywords_contract["action_ids"] == ["act_prepare_negative_keyword_review_queue"]
    assert "90_day_safety_check" not in negative_keywords_contract["missing_read_contracts"]
    assert (
        "negative_keyword_change_preview"
        not in negative_keywords_contract["missing_read_contracts"]
    )
    assert negative_keywords_contract["missing_read_contracts"] == []
    assert negative_keywords_contract["missing_read_contract_labels"] == []
    assert negative_keywords_contract["missing_read_contract_summary_label"] == (
        "Dane kompletne dla tej decyzji"
    )
    assert "dodanie wykluczających słów kluczowych" in negative_keywords_contract["blocked_claims"]
    assert (
        "dodanie wykluczających słów kluczowych"
        in negative_keywords_contract["blocked_claim_labels"]
    )
    assert negative_keywords_contract["blocked_claim_summary_label"]
    assert negative_keywords_contract["candidates"][0]["search_term"] == "odpady cena"
    assert negative_keywords_contract["candidates"][0]["review_priority"] == "wysokie"
    assert negative_keywords_contract["candidates"][0]["review_score"] == 53
    assert "kolejność oceny" in negative_keywords_contract["candidates"][0]["review_reason"]
    assert (
        "nie ocena zmarnowanego budżetu"
        in negative_keywords_contract["candidates"][0]["review_reason"]
    )
    assert negative_keywords_contract["candidates"][0]["human_review_gates"] == [
        "sprawdź intencję zapytania",
        "porównaj z istniejącymi słowami kluczowymi i typami dopasowania",
        "sprawdź 90-dniowy odczyt bezpieczeństwa",
        "zatwierdź poziom wykluczenia przed zapisem zmian",
    ]
    assert (
        negative_keywords_contract["candidates"][0]["keyword_context_rows"][0]["keyword_text"]
        == "odpady"
    )
    assert (
        negative_keywords_contract["candidates"][0]["keyword_context_rows"][0]["match_type"]
        == "BROAD"
    )
    assert (
        negative_keywords_contract["candidates"][0]["keyword_context_rows"][0]["match_type_label"]
        == "dopasowanie przybliżone"
    )
    assert (
        negative_keywords_contract["payload_preview"][0]
        == (negative_keywords_contract["candidates"][0]["payload_preview"])
    )
    assert negative_keywords_contract["payload_preview"][0]["match_type"] == "EXACT"
    assert negative_keywords_contract["payload_preview"][0]["match_type_label"] == (
        "dopasowanie ścisłe"
    )
    assert negative_keywords_contract["payload_preview"][0]["level"] == "ad_group"
    assert negative_keywords_contract["payload_preview"][0]["level_label"] == "grupa reklam"
    assert negative_keywords_contract["payload_preview"][0]["required_validation_labels"] == [
        "sprawdzenie intencji zapytania",
        "sprawdzenie istniejących słów kluczowych i typów dopasowania",
        "90-dniowa kontrola bezpieczeństwa",
        "potwierdzenie człowieka przed zapisem",
    ]
    assert (
        negative_keywords_contract["payload_preview"][0]["blocked_claim_labels"]
        == (negative_keywords_contract["payload_preview"][0]["blocked_claims"])
    )
    assert negative_keywords_contract["payload_preview"][0]["api_mutation_ready"] is False
    assert negative_keywords_contract["payload_preview"][0]["apply_allowed"] is False
    assert negative_keywords_contract["payload_preview"][0]["destructive"] is False
    assert negative_keywords_contract["candidates"][0]["clicks_90d"] == 10
    assert negative_keywords_contract["candidates"][0]["cost_micros_90d"] == 8000000
    assert negative_keywords_contract["candidates"][0]["conversions_90d"] == 0
    assert negative_keywords_contract["candidates"][0]["safety_evidence_ids"] == [
        refresh_response.json()["evidence_ids"][-1]
    ]
    assert negative_keywords_contract["candidates"][0]["safety_status"] == (
        "read_ready_needs_human_review"
    )
    assert negative_keywords_contract["candidates"][0]["safety_status_label"] == (
        "90-dniowy odczyt gotowy"
    )
    assert negative_keywords_contract["candidates"][0]["validation_status"] == (
        "pending_validation"
    )
    assert negative_keywords_contract["candidates"][0]["validation_status_label"] == (
        "do sprawdzenia"
    )
    assert "90_day_safety_check" in negative_keywords_contract["candidates"][0]["required_checks"]
    assert negative_keywords_contract["candidates"][0]["required_check_labels"] == [
        "sprawdzenie intencji zapytania",
        "sprawdzenie istniejących słów kluczowych i typów dopasowania",
        "90-dniowa kontrola bezpieczeństwa",
        "podgląd zmian wykluczeń",
        "potwierdzenie człowieka przed zapisem",
    ]
    assert (
        negative_keywords_contract["candidates"][0]["blocked_claim_labels"]
        == (negative_keywords_contract["candidates"][0]["blocked_claims"])
    )
    negative_keywords_section = next(
        section for section in payload["sections"] if section["id"] == "ads_negative_keyword_safety"
    )
    assert negative_keywords_section["status"] == "ready"
    decisions_by_id = {decision["id"]: decision for decision in payload["decision_queue"]}
    assert set(decisions_by_id) == {
        "ads_review_campaign_activity",
        "ads_review_campaign_triage",
        "ads_review_business_context",
        "ads_review_derived_kpis",
        "ads_review_budget_context",
        "ads_review_recommendations",
        "ads_review_impression_share",
        "ads_review_change_history",
        "ads_review_search_terms",
        "ads_review_search_term_ngrams",
        "ads_review_search_term_safety",
        "ads_review_negative_keyword_safety",
        "ads_prepare_custom_segments_from_search_terms",
        "ads_block_write_actions_without_actionobject",
    }
    campaign_decision = decisions_by_id["ads_review_campaign_activity"]
    assert campaign_decision["status"] == "ready"
    assert campaign_decision["priority"] == 20
    assert campaign_decision["metric_tiles"] == {
        "kampanie": 1,
        "pilne": 0,
        "wysokie": 1,
        "kliknięcia": 9,
        "wyświetlenia": 90,
        "koszt": "12 PLN",
        "konwersje": 2.5,
    }
    assert campaign_decision["title"] == "Przejrzyj aktywność kampanii Google Ads"
    assert campaign_decision["campaign_rows"][0]["campaign_name"] == "Brand Search"
    assert campaign_decision["campaign_rows"][0]["review_priority"] == "wysokie"
    assert campaign_decision["campaign_rows"][0]["review_score"] == 50
    assert campaign_decision["search_term_rows"] == []
    assert campaign_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert campaign_decision["source_connector_labels"] == ["Google Ads"]
    assert "dowód" in campaign_decision["evidence_summary_label"]
    assert "akcj" in campaign_decision["action_summary_label"]
    assert campaign_decision["operator_review_gates"] == [
        "review_campaign_goal",
        "review_conversion_quality",
        "review_budget_context",
        "review_search_terms_before_budget_decision",
        "human_strategy_review",
    ]
    campaign_triage_decision = decisions_by_id["ads_review_campaign_triage"]
    assert campaign_triage_decision["status"] == "ready"
    assert campaign_triage_decision["priority"] == 18
    assert campaign_triage_decision["decision_type"] == "review_campaign_triage"
    assert campaign_triage_decision["title"] == "Ustal kolejność oceny kampanii Ads"
    assert "Pilne=" not in campaign_triage_decision["summary"]
    assert "wysokie=" not in campaign_triage_decision["summary"]
    assert "0 pilnych kampanii" in campaign_triage_decision["summary"]
    assert "1 kampania o wysokim sygnale" in campaign_triage_decision["summary"]
    assert campaign_triage_decision["campaign_triage_rows"][0]["campaign_name"] == ("Brand Search")
    assert campaign_triage_decision["campaign_triage_rows"][0]["roas"] == 37.5625
    assert campaign_triage_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert campaign_triage_decision["metric_tiles"] == {
        "kampanie": 1,
        "pilne": 0,
        "wysokie": 1,
        "rekomendacje": 1,
        "podglądy": 2,
    }
    assert "zmarnowany budżet" in campaign_triage_decision["blocked_claims"]
    derived_kpi_decision = decisions_by_id["ads_review_derived_kpis"]
    assert derived_kpi_decision["status"] == "ready"
    assert derived_kpi_decision["priority"] == 25
    assert derived_kpi_decision["metric_tiles"] == {
        "kampanie": 1,
        "wiersze kosztu pozyskania celu": 1,
        "wiersze zwrotu z reklam": 1,
    }
    assert derived_kpi_decision["decision_type"] == "review_derived_kpi"
    assert derived_kpi_decision["derived_kpi_rows"][0]["campaign_name"] == "Brand Search"
    assert derived_kpi_decision["derived_kpi_rows"][0]["roas"] == 37.5625
    assert derived_kpi_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert "opłacalność" in derived_kpi_decision["blocked_claims"]
    assert "budget_pacing" not in derived_kpi_decision["missing_read_contracts"]
    budget_decision = decisions_by_id["ads_review_budget_context"]
    assert budget_decision["status"] == "ready"
    assert budget_decision["priority"] == 30
    assert budget_decision["metric_tiles"] == {
        "budżety": 1,
        "podgląd budżetu": 1,
        "koszt 7 dni": "12 PLN",
    }
    assert budget_decision["decision_type"] == "review_budget_context"
    assert budget_decision["budget_rows"][0]["campaign_name"] == "Brand Search"
    assert budget_decision["budget_rows"][0]["spend_to_budget_ratio_7d"] == 0.057143
    assert budget_decision["budget_apply_preview"][0]["operation_type"] == (
        "CampaignBudgetOperation"
    )
    assert budget_decision["budget_apply_preview"][0]["api_mutation_ready"] is False
    assert budget_decision["budget_apply_preview"][0]["apply_allowed"] is False
    assert budget_decision["action_ids"] == ["act_prepare_ads_campaign_review_queue"]
    assert budget_decision["knowledge_card_ids"] == ["card_google_ads_budget_review_playbook"]
    assert budget_decision["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]
    assert "zmiana budżetu" in budget_decision["blocked_claims"]
    recommendations_decision = decisions_by_id["ads_review_recommendations"]
    assert recommendations_decision["status"] == "ready"
    assert recommendations_decision["priority"] == 35
    assert recommendations_decision["metric_tiles"] == {
        "rekomendacje": 1,
        "pilne": 1,
        "wysokie": 0,
        "podgląd wpływu": 1,
        "podgląd akcji": 1,
    }
    assert recommendations_decision["decision_type"] == "review_recommendations"
    assert recommendations_decision["recommendation_rows"][0]["recommendation_type"] == (
        "CAMPAIGN_BUDGET"
    )
    assert recommendations_decision["recommendation_rows"][0]["review_priority"] == "pilne"
    assert recommendations_decision["recommendation_rows"][0]["review_score"] == 70
    assert recommendations_decision["metric_tiles"] == {
        "rekomendacje": 1,
        "pilne": 1,
        "wysokie": 0,
        "podgląd wpływu": 1,
        "podgląd akcji": 1,
    }
    assert (
        recommendations_decision["recommendation_apply_preview"][0]["operation_type"]
        == "ApplyRecommendationOperation"
    )
    assert recommendations_decision["recommendation_apply_preview"][0]["apply_allowed"] is False
    assert recommendations_decision["action_ids"] == [
        "act_prepare_google_ads_recommendation_review_queue"
    ]
    assert recommendations_decision["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert recommendations_decision["expert_rule_ids"] == [
        "ads_recommendations_v1",
        "ads_principles_v1",
    ]
    assert recommendations_decision["missing_read_contracts"] == []
    assert recommendations_decision["operator_review_gates"] == [
        "human_strategy_review",
        "review_recommendation_type",
        "review_impact_metrics",
        "review_change_history",
        "review_business_goal",
        "recommendation_apply_preview",
        "google_ads_rmf_compliance_review",
        "human_confirm_before_apply",
    ]
    assert "zapis rekomendacji" in recommendations_decision["blocked_claims"]
    impression_share_decision = decisions_by_id["ads_review_impression_share"]
    assert impression_share_decision["status"] == "ready"
    assert impression_share_decision["priority"] == 60
    assert impression_share_decision["metric_tiles"] == {
        "kampanie": 1,
        "utrata przez budżet": 1,
    }
    assert impression_share_decision["decision_type"] == "review_impression_share"
    assert impression_share_decision["impression_share_rows"][0]["campaign_name"] == (
        "Brand Search"
    )
    assert impression_share_decision["action_ids"] == []
    assert impression_share_decision["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert impression_share_decision["expert_rule_ids"] == [
        "ads_scaling_candidates_v1",
        "ads_principles_v1",
    ]
    assert "zmiana budżetu" in impression_share_decision["blocked_claims"]
    change_history_decision = decisions_by_id["ads_review_change_history"]
    assert change_history_decision["status"] == "ready"
    assert change_history_decision["priority"] == 65
    assert change_history_decision["metric_tiles"] == {"zmiany": 1, "kampanie": 1}
    assert change_history_decision["decision_type"] == "review_change_history"
    assert change_history_decision["change_history_rows"][0]["change_resource_type"] == ("CAMPAIGN")
    assert change_history_decision["action_ids"] == [CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_decision["knowledge_card_ids"] == [
        "card_google_ads_budget_review_playbook"
    ]
    assert change_history_decision["expert_rule_ids"] == [
        "ads_diagnostics_v1",
        "ads_principles_v1",
    ]
    assert "wpływ zmian" in change_history_decision["blocked_claims"]

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert CHANGE_HISTORY_IMPACT_ACTION_ID in actions
    change_history_action = actions[CHANGE_HISTORY_IMPACT_ACTION_ID]
    assert change_history_action["payload"]["action_type"] == (
        "google_ads_change_history_impact_review"
    )
    assert change_history_action["payload"]["preview_contract"] == (
        "change_history_impact_review_v1"
    )
    assert (
        change_history_action["payload"]["change_history_preview"][0]["change_event_id"]
        == "change-1"
    )
    assert change_history_action["payload"]["apply_allowed"] is False
    assert change_history_action["payload"]["destructive"] is False
    assert change_history_action["payload"]["api_mutation_ready"] is False
    assert (
        "pre_change_performance_window"
        in change_history_action["payload"]["missing_read_contracts"]
    )
    validate_response = client.post(f"/api/actions/{CHANGE_HISTORY_IMPACT_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True
    assert SEARCH_TERM_NGRAM_ACTION_ID in actions
    ngram_action = actions[SEARCH_TERM_NGRAM_ACTION_ID]
    assert ngram_action["payload"]["action_type"] == ("google_ads_search_term_ngram_review")
    assert ngram_action["payload"]["preview_contract"] == "search_term_ngram_review_v1"
    assert ngram_action["payload"]["ngram_preview"][0]["ngram"]
    assert ngram_action["payload"]["ngram_preview"][0]["sample_search_terms"]
    assert ngram_action["payload"]["ngram_preview"][0]["apply_allowed"] is False
    assert ngram_action["payload"]["ngram_preview"][0]["destructive"] is False
    assert ngram_action["payload"]["ngram_preview"][0]["api_mutation_ready"] is False
    assert ngram_action["payload"]["apply_allowed"] is False
    assert ngram_action["payload"]["destructive"] is False
    assert ngram_action["payload"]["api_mutation_ready"] is False
    ngram_operator_text = "\n".join(
        [
            ngram_action["human_diagnosis"],
            ngram_action["recommended_reason"],
        ]
    )
    assert "negative keyword queue" not in ngram_operator_text
    assert "search-term evidence" not in ngram_operator_text
    assert "kolejki sprawdzenia wykluczeń" in ngram_operator_text
    assert ngram_action["preview_cards"]
    ngram_preview_card = ngram_action["preview_cards"][0]
    assert ngram_preview_card["kind"] == "google_ads_search_term_ngram_review"
    assert ngram_preview_card["title_label"] == "Temat zapytań do sprawdzenia"
    ngram_preview_rows = {row["label"]: row["value"] for row in ngram_preview_card["rows"]}
    assert ngram_preview_rows["Temat"]
    assert ngram_preview_rows["Przykłady"]
    assert "SearchTermNgramReview" not in str(ngram_preview_card)
    assert "search_term_ngram_review_v1" not in str(ngram_preview_card)
    assert "ngram_to_negative_keyword_change_preview" not in str(ngram_preview_card)
    ngram_validate_response = client.post(f"/api/actions/{SEARCH_TERM_NGRAM_ACTION_ID}/validate")
    assert ngram_validate_response.status_code == 200
    assert ngram_validate_response.json()["valid"] is True
    search_terms_decision = decisions_by_id["ads_review_search_terms"]
    assert search_terms_decision["status"] == "ready"
    assert search_terms_decision["priority"] == 40
    assert search_terms_decision["metric_tiles"] == {
        "zapytania": 2,
        "kliknięcia": 10,
        "koszt": "12 PLN",
    }
    assert search_terms_decision["search_term_rows"][0]["search_term"] == "bdo rejestracja"
    assert search_terms_decision["missing_read_contracts"] == []
    assert search_terms_decision["operator_review_gates"] == ["negative_keyword_action_validation"]
    assert "dodanie wykluczających słów kluczowych" in search_terms_decision["blocked_claims"]
    search_term_safety_decision = decisions_by_id["ads_review_search_term_safety"]
    assert search_term_safety_decision["status"] == "ready"
    assert search_term_safety_decision["priority"] == 50
    assert search_term_safety_decision["metric_tiles"] == {
        "90 dni": 1,
        "kliknięcia": 10,
        "koszt": "8.00 PLN",
    }
    assert search_term_safety_decision["decision_type"] == "review_search_term_safety"
    assert search_term_safety_decision["search_term_safety_rows"][0]["search_term"] == (
        "odpady cena"
    )
    assert "dodanie wykluczających słów kluczowych" in search_term_safety_decision["blocked_claims"]
    assert search_term_safety_decision["missing_read_contracts"] == []
    assert search_term_safety_decision["operator_review_gates"] == ["human_intent_review"]
    assert search_term_safety_decision["knowledge_card_ids"] == [
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_search_playbook",
    ]
    negative_keyword_decision = decisions_by_id["ads_review_negative_keyword_safety"]
    assert negative_keyword_decision["status"] == "ready"
    assert negative_keyword_decision["priority"] == 45
    assert negative_keyword_decision["metric_tiles"] == {
        "propozycje": 1,
        "pilne": 0,
        "wysokie": 1,
        "podgląd akcji": 1,
        "kontekst słów": 1,
    }
    assert negative_keyword_decision["decision_type"] == "review_negative_keyword_safety"
    assert negative_keyword_decision["negative_keyword_candidates"][0]["search_term"] == (
        "odpady cena"
    )
    assert negative_keyword_decision["search_term_safety_rows"][0]["clicks_90d"] == 10
    assert (
        negative_keyword_decision["negative_keyword_payload_preview"][0]["negative_keyword_text"]
        == "odpady cena"
    )
    assert negative_keyword_decision["missing_read_contracts"] == []
    assert negative_keyword_decision["operator_review_gates"] == ["human_intent_review"]
    assert negative_keyword_decision["keyword_match_context_rows"][0]["keyword_text"] == ("odpady")
    assert negative_keyword_decision["action_ids"] == ["act_prepare_negative_keyword_review_queue"]
    assert "marnowanie budżetu na zapytaniach" in negative_keyword_decision["blocked_claims"]
    custom_segments_decision = decisions_by_id["ads_prepare_custom_segments_from_search_terms"]
    assert custom_segments_decision["status"] == "ready"
    assert custom_segments_decision["priority"] == 55
    assert custom_segments_decision["metric_tiles"] == {
        "segmenty": 1,
        "pilne": 1,
        "wysokie": 0,
        "podgląd akcji": 1,
        "źródłowe zapytania": 2,
        "KP ideas": 1,
    }
    assert custom_segments_decision["decision_type"] == "prepare_custom_segments"
    assert custom_segments_decision["missing_read_contracts"] == [
        "forecast_or_audience_size",
    ]
    assert (
        custom_segments_decision["custom_segment_audience_forecast_rows"][0]["status"]
        == "missing_forecast"
    )
    assert (
        custom_segments_decision["custom_segment_audience_forecast_rows"][0]["candidate_id"]
        == custom_segments_decision["custom_segment_candidates"][0]["id"]
    )
    assert (
        custom_segments_decision["custom_segment_audience_forecast_rows"][0]["audience_size"]
        is None
    )
    assert custom_segments_decision["operator_review_gates"] == [
        "review_source_terms",
        "reject_brand_or_low_intent_terms",
        "keyword_planner_enrichment",
        "forecast_or_audience_size",
        "human_confirm_before_apply",
    ]
    assert custom_segments_decision["custom_segment_candidates"][0]["source_terms"] == [
        "bdo rejestracja",
        "odpady cena",
    ]
    assert (
        custom_segments_decision["custom_segment_candidates"][0]["source_quality"]["accepted_terms"]
        == 2
    )
    assert custom_segments_decision["keyword_planner_idea_rows"][0]["idea_text"] == (
        "bdo szkolenie"
    )
    assert (
        custom_segments_decision["custom_segment_payload_preview"][0]["custom_segment_name"]
        == "Wyszukiwane hasła: Brand Search"
    )
    assert custom_segments_decision["custom_segment_payload_preview"][0]["apply_allowed"] is False
    assert (
        custom_segments_decision["custom_segment_payload_preview"][0]["targeting_preview"][0][
            "apply_allowed"
        ]
        is False
    )
    assert custom_segments_decision["action_ids"] == [
        "act_prepare_custom_segments_from_search_terms"
    ]
    assert "zwrot z reklam" in custom_segments_decision["blocked_claims"]
    safety_decision = decisions_by_id["ads_block_write_actions_without_actionobject"]
    assert safety_decision["status"] == "blocked"
    assert safety_decision["priority"] == 10
    assert safety_decision["metric_tiles"] == {"akcje do sprawdzenia": 10, "blokady": 3}
    assert "campaign creation" in safety_decision["blocked_claims"]
    assert payload["blocker_count"] == 2

    status_probe_response = client.post(
        "/api/connectors/google_ads/refresh",
        json={"mode": "status_probe", "reason": "ads diagnostics status probe regression"},
    )
    assert status_probe_response.status_code == 200

    after_probe_response = client.get("/api/ads/diagnostics")
    assert after_probe_response.status_code == 200
    after_probe_payload = after_probe_response.json()
    assert after_probe_payload["live_data_available"] is True
    assert after_probe_payload["latest_refresh"]["id"] == refresh_response.json()["id"]
    assert after_probe_payload["blocked_handoff"] is None
    assert after_probe_payload["campaign_read_contract"]["campaign_rows"]
    assert after_probe_payload["budget_pacing_read_contract"]["budget_rows"]
    assert after_probe_payload["recommendations_read_contract"]["recommendation_rows"]
    assert after_probe_payload["impression_share_read_contract"]["impression_share_rows"]
    assert after_probe_payload["change_history_read_contract"]["change_history_rows"]
    assert after_probe_payload["search_terms_read_contract"]["search_term_rows"]
    assert after_probe_payload["search_term_safety_read_contract"]["safety_rows"]

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_decisions = {
        decision["id"]: decision
        for decision in context_payload["ads_diagnostics"]["decision_queue"]
    }
    context_budget_decision = context_decisions["ads_review_budget_context"]
    assert context_budget_decision["priority"] == budget_decision["priority"]
    assert context_budget_decision["metric_tiles"] == budget_decision["metric_tiles"]
    assert context_budget_decision["knowledge_card_ids"] == budget_decision["knowledge_card_ids"]
    assert context_budget_decision["expert_rule_ids"] == budget_decision["expert_rule_ids"]
    context_card_ids = {card["id"] for card in context_payload["knowledge_card_summaries"]}
    assert "card_google_ads_budget_review_playbook" in context_card_ids
    context_rule_ids = {rule["id"] for rule in context_payload["expert_rule_summaries"]}
    assert "ads_scaling_candidates_v1" in context_rule_ids
    assert "ads_recommendations_v1" in context_rule_ids

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions_payload = actions_response.json()
    action_ids = {action["id"] for action in actions_payload}
    assert "act_configure_google_ads_env" not in action_ids
    assert "act_prepare_ads_campaign_review_queue" in action_ids
    assert CHANGE_HISTORY_IMPACT_ACTION_ID in action_ids
    assert SEARCH_TERM_NGRAM_ACTION_ID in action_ids
    assert "act_prepare_google_ads_recommendation_review_queue" in action_ids
    assert "act_prepare_custom_segments_from_search_terms" in action_ids
    assert "act_prepare_negative_keyword_review_queue" in action_ids
    campaign_review_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_ads_campaign_review_queue"
    )
    assert campaign_review_action["payload"]["action_type"] == "campaign_change_review"
    assert campaign_review_action["payload"]["campaign_candidates"][0]["campaign_name"] == (
        "Brand Search"
    )
    assert (
        campaign_review_action["payload"]["campaign_candidates"][0]["review_priority"] == "wysokie"
    )
    assert campaign_review_action["payload"]["campaign_candidates"][0]["review_score"] == 50
    assert (
        "Kolejność oceny kampanii"
        in campaign_review_action["payload"]["campaign_candidates"][0]["review_reason"]
    )
    assert campaign_review_action["payload"]["campaign_candidates"][0]["human_review_gates"] == [
        "review_campaign_goal",
        "review_conversion_quality",
        "review_budget_context",
        "review_search_terms_before_budget_decision",
        "human_strategy_review",
    ]
    assert (
        campaign_review_action["payload"]["campaign_candidates"][0]["target_context"][
            "target_status"
        ]
        == "no_target"
    )
    assert (
        campaign_review_action["payload"]["campaign_candidates"][0]["derived_kpis"]["roas"]
        == 37.5625
    )
    assert campaign_review_action["payload"]["campaign_candidates"][0]["budget_context"] == {
        "budget_amount_micros": 30000000,
        "cost_micros_7d": 12000000,
        "seven_day_budget_micros": 210000000,
        "spend_to_budget_ratio_7d": 0.057143,
        "has_recommended_budget": True,
        "recommended_budget_amount_micros": 42000000,
    }
    assert campaign_review_action["payload"]["preview_contract"] == ("budget_apply_preview_v1")
    assert (
        campaign_review_action["payload"]["budget_payload_preview"][0]["operation_type"]
        == "CampaignBudgetOperation"
    )
    assert campaign_review_action["preview_cards"]
    budget_preview_card = campaign_review_action["preview_cards"][0]
    assert budget_preview_card["kind"] == "google_ads_budget_review"
    assert budget_preview_card["title_label"] == "Budżet kampanii do sprawdzenia"
    budget_preview_rows = {row["label"]: row["value"] for row in budget_preview_card["rows"]}
    assert budget_preview_rows["Kampania"] == "Brand Search"
    assert budget_preview_rows["Budżet"] == "Brand budget"
    assert budget_preview_rows["Obecny budżet"] == "30.00 PLN"
    assert budget_preview_rows["Propozycja"] == "42.00 PLN"
    assert "CampaignBudgetOperation" not in str(budget_preview_card)
    assert "101" not in str(budget_preview_card)
    assert "701" not in str(budget_preview_card)
    assert (
        campaign_review_action["payload"]["budget_payload_preview"][0][
            "proposed_budget_amount_micros"
        ]
        == 42000000
    )
    assert (
        campaign_review_action["payload"]["budget_payload_preview"][0]["api_mutation_ready"]
        is False
    )
    assert campaign_review_action["payload"]["budget_payload_preview"][0]["apply_allowed"] is False
    budget_safety_review = campaign_review_action["payload"]["budget_payload_preview"][0][
        "safety_review"
    ]
    assert budget_safety_review["safety_contract"] == "campaign_budget_apply_safety_v1"
    assert budget_safety_review["apply_allowed"] is False
    assert budget_safety_review["api_mutation_ready"] is False
    assert budget_safety_review["destructive"] is False
    assert campaign_review_action["payload"]["apply_allowed"] is False
    assert campaign_review_action["payload"]["destructive"] is False
    assert "budget_pacing" in campaign_review_action["payload"]["required_validation"]
    assert "budget_apply_preview" in campaign_review_action["payload"]["required_validation"]
    assert (
        "campaign_budget_apply_safety" in campaign_review_action["payload"]["required_validation"]
    )
    assert "skalowanie budżetu" in campaign_review_action["payload"]["blocked_claims"]
    campaign_review_validation_response = client.post(
        "/api/actions/act_prepare_ads_campaign_review_queue/validate",
        json={},
    )
    assert campaign_review_validation_response.status_code == 200
    assert campaign_review_validation_response.json()["valid"] is True
    recommendation_review_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_google_ads_recommendation_review_queue"
    )
    assert recommendation_review_action["payload"]["action_type"] == (
        "google_ads_recommendation_review"
    )
    assert recommendation_review_action["payload"]["preview_contract"] == (
        "recommendation_apply_preview_v1"
    )
    assert (
        recommendation_review_action["payload"]["payload_preview"][0]["operation_type"]
        == "ApplyRecommendationOperation"
    )
    assert recommendation_review_action["payload"]["payload_preview"][0]["apply_allowed"] is False
    assert recommendation_review_action["preview_cards"]
    recommendation_preview_card = recommendation_review_action["preview_cards"][0]
    assert recommendation_preview_card["kind"] == "google_ads_recommendation_review"
    assert recommendation_preview_card["title_label"] == ("Rekomendacja Google Ads do sprawdzenia")
    recommendation_preview_rows = {
        row["label"]: row["value"] for row in recommendation_preview_card["rows"]
    }
    assert recommendation_preview_rows["Typ rekomendacji"] == "budżet kampanii"
    assert recommendation_preview_rows["Kampania"] == "powiązana kampania do sprawdzenia"
    assert recommendation_preview_rows["Budżet kampanii"] == ("powiązany budżet do sprawdzenia")
    assert "CAMPAIGN_BUDGET" not in str(recommendation_preview_card)
    assert "101" not in str(recommendation_preview_card)
    assert "701" not in str(recommendation_preview_card)
    assert recommendation_review_action["payload"]["apply_allowed"] is False
    assert recommendation_review_action["payload"]["destructive"] is False
    assert (
        "human_confirm_before_apply"
        in recommendation_review_action["payload"]["required_validation"]
    )
    recommendation_review_validation_response = client.post(
        "/api/actions/act_prepare_google_ads_recommendation_review_queue/validate",
        json={},
    )
    assert recommendation_review_validation_response.status_code == 200
    assert recommendation_review_validation_response.json()["valid"] is True
    custom_segment_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_custom_segments_from_search_terms"
    )
    assert custom_segment_action["payload"]["terms"] == [
        "bdo rejestracja",
        "odpady cena",
    ]
    assert custom_segment_action["payload"]["invented_terms"] is False
    assert custom_segment_action["payload"]["preview_contract"] == (
        "custom_segment_change_preview_v1"
    )
    assert custom_segment_action["payload"]["payload_preview"][0]["member_type"] == "KEYWORD"
    assert custom_segment_action["payload"]["payload_preview"][0]["member_type_label"] == (
        "słowa kluczowe"
    )
    assert custom_segment_action["payload"]["payload_preview"][0]["apply_allowed"] is False
    custom_segment_reason = custom_segment_action["payload"]["payload_preview"][0]["reason"]
    assert "search-term evidence" not in custom_segment_reason
    assert "dowodów z wyszukiwanych haseł" in custom_segment_reason
    assert custom_segment_action["preview_cards"]
    custom_segment_preview_card = custom_segment_action["preview_cards"][0]
    assert custom_segment_preview_card["kind"] == "google_ads_custom_segment_review"
    assert custom_segment_preview_card["title_label"] == "Segment odbiorców do sprawdzenia"
    custom_segment_preview_rows = {
        row["label"]: row["value"] for row in custom_segment_preview_card["rows"]
    }
    assert custom_segment_preview_rows["Nazwa"] == "Wyszukiwane hasła: Brand Search"
    assert custom_segment_preview_rows["Typ odbiorców"] == "słowa kluczowe"
    assert custom_segment_preview_rows["Kampania do sprawdzenia"] == "Brand Search"
    assert "KEYWORD" not in str(custom_segment_preview_card)
    assert "101" not in str(custom_segment_preview_card)
    custom_segment_safety_review = custom_segment_action["payload"]["payload_preview"][0][
        "safety_review"
    ]
    assert custom_segment_safety_review["safety_contract"] == ("custom_segment_apply_safety_v1")
    assert custom_segment_safety_review["status"] == "blocked"
    assert custom_segment_safety_review["status_label"] == "zablokowane"
    assert custom_segment_safety_review["apply_allowed"] is False
    assert custom_segment_safety_review["api_mutation_ready"] is False
    assert custom_segment_safety_review["destructive"] is False
    assert custom_segment_safety_review["audit_required"] is True
    assert "forecast," not in custom_segment_safety_review["reason"]
    assert "prognozy rozmiaru odbiorców" in custom_segment_safety_review["reason"]
    assert "forecast_or_audience_size" in custom_segment_safety_review["missing_requirements"]
    assert "google_ads_mutation_audit" in custom_segment_safety_review["missing_requirements"]
    custom_segment_targeting_preview = custom_segment_action["payload"]["payload_preview"][0][
        "targeting_preview"
    ][0]
    assert custom_segment_targeting_preview["operation_type"] == ("custom_segment_targeting_review")
    assert custom_segment_targeting_preview["apply_allowed"] is False
    assert custom_segment_targeting_preview["api_mutation_ready"] is False
    assert custom_segment_action["payload"]["destructive"] is False
    validation_response = client.post(
        "/api/actions/act_prepare_custom_segments_from_search_terms/validate",
        json={},
    )
    assert validation_response.status_code == 200
    assert validation_response.json()["valid"] is True
    negative_keyword_action = next(
        action
        for action in actions_payload
        if action["id"] == "act_prepare_negative_keyword_review_queue"
    )
    assert negative_keyword_action["payload"]["terms"] == ["odpady cena"]
    assert negative_keyword_action["payload"]["preview_contract"] == (
        "negative_keyword_change_preview_v1"
    )
    assert negative_keyword_action["payload"]["api_mutation_ready"] is False
    assert negative_keyword_action["payload"]["payload_preview"][0]["match_type"] == "EXACT"
    assert negative_keyword_action["payload"]["payload_preview"][0]["apply_allowed"] is False
    assert negative_keyword_action["preview_cards"]
    negative_keyword_preview_card = negative_keyword_action["preview_cards"][0]
    assert negative_keyword_preview_card["kind"] == "google_ads_negative_keyword_review"
    assert negative_keyword_preview_card["title_label"] == "Wykluczenie słowa do sprawdzenia"
    negative_keyword_preview_rows = {
        row["label"]: row["value"] for row in negative_keyword_preview_card["rows"]
    }
    assert negative_keyword_preview_rows["Dopasowanie"] == "dopasowanie ścisłe"
    assert negative_keyword_preview_rows["Poziom"] == "grupa reklam"
    assert "EXACT" not in str(negative_keyword_preview_card)
    assert "ad_group" not in str(negative_keyword_preview_card)
    assert "101" not in str(negative_keyword_preview_card)
    assert negative_keyword_action["payload"]["keyword_match_context_available"] is True
    assert (
        negative_keyword_action["payload"]["keyword_match_context"][0]["keyword_text"] == "odpady"
    )
    assert negative_keyword_action["payload"]["keyword_match_context"][0]["match_type"] == "BROAD"
    assert "search_term_90d_clicks" in negative_keyword_action["payload"]["source_metric_names"]
    assert negative_keyword_action["payload"]["apply_allowed"] is False
    assert negative_keyword_action["payload"]["destructive"] is False
    assert "90_day_safety_check" in negative_keyword_action["payload"]["required_validation"]
    negative_keyword_validation_response = client.post(
        "/api/actions/act_prepare_negative_keyword_review_queue/validate",
        json={},
    )
    assert negative_keyword_validation_response.status_code == 200
    assert negative_keyword_validation_response.json()["valid"] is True

    monkeypatch.setenv("WILQ_ADS_PROFIT_MARGIN", "0.35")
    monkeypatch.setenv("WILQ_ADS_BUSINESS_GOAL", "lead quality review")
    monkeypatch.setenv("WILQ_ADS_BUDGET_GOAL", "protect current monthly budget")
    monkeypatch.setenv("WILQ_ADS_TARGET_ROAS", "5.0")
    business_ready_response = client.get("/api/ads/diagnostics")
    assert business_ready_response.status_code == 200
    business_ready_payload = business_ready_response.json()
    business_ready_contract = business_ready_payload["business_context_read_contract"]
    assert business_ready_contract["status"] == "ready"
    assert business_ready_contract["profit_margin"] == 0.35
    assert business_ready_contract["business_goal"] == "lead quality review"
    assert business_ready_contract["budget_goal"] == "protect current monthly budget"
    assert business_ready_contract["target_roas"] == 5.0
    assert business_ready_contract["missing_read_contracts"] == ["human_strategy_review"]
    assert business_ready_contract["allowed_metrics"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas",
    ]
    assert business_ready_contract["business_policy_ids"] == [
        "use_margin_as_context_not_profitability_verdict",
        "align_campaign_review_to_business_goal",
        "honor_human_budget_goal_before_budget_changes",
        "compare_kpis_to_confirmed_target_in_review",
        "block_target_verdict_until_strategy_review_approved",
    ]
    assert business_ready_contract["target_interpretation"]["status"] == "preliminary"
    assert (
        "target_roas_review_context"
        in business_ready_contract["target_interpretation"]["allowed_uses"]
    )
    assert (
        "target_roas_or_cpa"
        not in business_ready_contract["target_interpretation"]["missing_requirements"]
    )
    assert (
        "human_strategy_review"
        in business_ready_contract["target_interpretation"]["missing_requirements"]
    )
    assert business_ready_contract["target_interpretation"]["apply_allowed"] is False
    assert business_ready_contract["target_interpretation"]["action_ids"] == [
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]
    assert business_ready_contract["operator_review_gates"] == [
        "human_strategy_review",
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "review_target_fit",
    ]
    derived_ready_contract = business_ready_payload["derived_kpi_read_contract"]
    campaign_ready_row = business_ready_payload["campaign_read_contract"]["campaign_rows"][0]
    assert campaign_ready_row["target_status"] == "within_target"
    assert campaign_ready_row["target_status_label"] == "zwrot z reklam w granicy celu"
    assert "cel: zwrot z reklam w granicy celu" in campaign_ready_row["review_reason"]
    assert "review_target_context" in campaign_ready_row["human_review_gates"]
    assert "profit_margin" not in derived_ready_contract["missing_read_contracts"]
    assert "target_roas" in derived_ready_contract["allowed_metrics"]
    assert "roas_vs_target" in derived_ready_contract["allowed_metrics"]
    assert derived_ready_contract["kpi_rows"][0]["target_roas"] == 5.0
    assert derived_ready_contract["kpi_rows"][0]["roas_vs_target"] == 32.5625
    assert derived_ready_contract["kpi_rows"][0]["target_cpa_micros"] is None
    assert derived_ready_contract["kpi_rows"][0]["cpa_vs_target_micros"] is None
    assert derived_ready_contract["kpi_rows"][0]["target_status"] == "within_target"
    assert derived_ready_contract["kpi_rows"][0]["target_status_label"] == (
        "zwrot z reklam w granicy celu"
    )
    assert (
        "human_budget_goal"
        not in business_ready_payload["budget_pacing_read_contract"]["missing_read_contracts"]
    )
    assert (
        "budget_target_or_seasonality"
        not in business_ready_payload["budget_pacing_read_contract"]["missing_read_contracts"]
    )
    assert (
        "human_budget_goal"
        not in business_ready_payload["impression_share_read_contract"]["missing_read_contracts"]
    )
    business_ready_decision = next(
        decision
        for decision in business_ready_payload["decision_queue"]
        if decision["id"] == "ads_review_business_context"
    )
    assert business_ready_decision["status"] == "ready"
    assert business_ready_decision["metric_tiles"] == {
        "braki": 1,
        "blokady": 6,
        "ustawione pola": 4,
        "warunki sprawdzenia": 5,
        "polityki": 5,
    }
    assert (
        business_ready_decision["operator_review_gates"]
        == (business_ready_contract["operator_review_gates"])
    )
    assert business_ready_decision["action_ids"] == [
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]
    business_ready_campaign_decision = next(
        decision
        for decision in business_ready_payload["decision_queue"]
        if decision["id"] == "ads_review_campaign_activity"
    )
    assert business_ready_campaign_decision["metric_tiles"]["targety"] == 1
    derived_ready_decision = next(
        decision
        for decision in business_ready_payload["decision_queue"]
        if decision["id"] == "ads_review_derived_kpis"
    )
    assert derived_ready_decision["metric_tiles"]["targety"] == 1
    assert derived_ready_decision["metric_tiles"]["w celu"] == 1
    assert derived_ready_decision["derived_kpi_rows"][0]["roas_vs_target"] == 32.5625
    assert derived_ready_decision["derived_kpi_rows"][0]["target_status"] == "within_target"

    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    brief_action_ids = {
        action_id
        for section in brief_response.json()["sections"]
        for item in section["items"]
        for action_id in item["action_ids"]
    }
    assert "act_configure_google_ads_env" not in brief_action_ids


def test_ads_diagnostics_summary_view_compacts_heavy_payload() -> None:
    full_response = client.get("/api/ads/diagnostics")
    summary_response = client.get("/api/ads/diagnostics?view=summary")

    assert full_response.status_code == 200
    assert summary_response.status_code == 200
    full_payload = full_response.json()
    summary_payload = summary_response.json()
    full_bytes = len(json.dumps(full_payload, ensure_ascii=False).encode())
    summary_bytes = len(json.dumps(summary_payload, ensure_ascii=False).encode())

    assert summary_bytes < full_bytes
    assert summary_payload["operator_summary"] == full_payload["operator_summary"]
    assert summary_payload["evidence_summary_label"] == full_payload["evidence_summary_label"]
    assert summary_payload["source_connector_labels"] == full_payload["source_connector_labels"]
    assert summary_payload["source_connector_labels"] == ["Google Ads"]
    assert summary_payload["action_summary_label"] == full_payload["action_summary_label"]
    assert summary_payload["evidence_summary_label"]
    assert summary_payload["source_connector_labels"]
    assert summary_payload["action_summary_label"]
    assert summary_payload["business_context_read_contract"]["target_interpretation"][
        "action_summary_label"
    ]
    assert summary_payload["business_context_read_contract"]["strategy_review_readiness_contract"][
        "action_summary_label"
    ]
    assert all(
        row["action_summary_label"]
        for row in summary_payload["campaign_triage_read_contract"]["triage_rows"]
    )
    assert summary_payload["change_impact_readiness_contract"]["action_summary_label"]
    assert summary_payload["connector_status_label"]
    assert summary_payload["live_data_status_label"]
    if summary_payload["latest_refresh"]:
        assert summary_payload["latest_refresh_status_label"]
    assert (
        summary_payload["operator_summary"]["missing_read_contract_labels"]
        == (full_payload["operator_summary"]["missing_read_contract_labels"])
    )
    assert (
        summary_payload["operator_summary"]["blocked_claim_labels"]
        == (full_payload["operator_summary"]["blocked_claim_labels"])
    )
    assert summary_payload["operator_summary"]["top_blocked_claim_labels"]
    assert len(summary_payload["operator_summary"]["top_blocked_claim_labels"]) <= 5
    assert (
        summary_payload["operator_summary"]["top_blocked_claim_labels"]
        == full_payload["operator_summary"]["top_blocked_claim_labels"]
    )
    assert summary_payload["operator_summary"]["top_blocked_claim_summary_label"]
    assert len(summary_payload["decision_queue"]) <= len(full_payload["decision_queue"])
    assert all(decision["status_label"] for decision in summary_payload["decision_queue"])
    assert all(decision["decision_type_label"] for decision in summary_payload["decision_queue"])
    assert all(decision["priority_label"] for decision in summary_payload["decision_queue"])
    assert all(decision["risk_label"] for decision in summary_payload["decision_queue"])
    assert all(
        isinstance(decision["source_connector_labels"], list)
        for decision in summary_payload["decision_queue"]
    )
    assert all(decision["evidence_summary_label"] for decision in summary_payload["decision_queue"])
    assert all(decision["action_summary_label"] for decision in summary_payload["decision_queue"])
    assert all(
        isinstance(decision["missing_read_contract_labels"], list)
        for decision in summary_payload["decision_queue"]
    )
    assert all(
        isinstance(decision["blocked_claim_labels"], list)
        for decision in summary_payload["decision_queue"]
    )
    assert all(section["status_label"] for section in summary_payload["sections"])
    assert all(
        isinstance(section["source_connector_labels"], list)
        for section in summary_payload["sections"]
    )
    assert all(section["evidence_summary_label"] for section in summary_payload["sections"])
    assert all(section["action_summary_label"] for section in summary_payload["sections"])
    assert all(
        isinstance(section["blocked_claim_labels"], list) for section in summary_payload["sections"]
    )
    assert set(summary_payload["operator_summary"]["top_decision_ids"]).issubset(
        {decision["id"] for decision in summary_payload["decision_queue"]}
    )
    assert len(summary_payload["search_term_safety_read_contract"]["safety_rows"]) <= 5
    assert len(summary_payload["keyword_match_context_read_contract"]["context_rows"]) <= 5


def test_ads_diagnostics_summary_action_ids_are_validatable() -> None:
    response = client.get("/api/ads/diagnostics?view=summary")
    assert response.status_code == 200
    payload = response.json()

    action_ids = {
        *payload["operator_summary"]["action_ids"],
        *(
            action_id
            for item in payload["optimizer_readiness_contract"]["readiness_items"]
            for action_id in item["action_ids"]
        ),
        *(
            action_id
            for decision in payload["decision_queue"]
            for action_id in decision["action_ids"]
        ),
    }

    assert action_ids
    for action_id in sorted(action_ids):
        action_response = client.get(f"/api/actions/{action_id}")
        assert action_response.status_code == 200, action_id
        validate_response = client.post(f"/api/actions/{action_id}/validate")
        assert validate_response.status_code == 200, action_id
        validation = validate_response.json()
        assert validation["valid"] is True, action_id
        assert validation["status"] == "valid", action_id


def test_ads_diagnostics_summary_view_uses_smaller_metric_fact_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_limits: list[int] = []

    class RecordingMetricStore:
        def list_metric_facts(self, connector_id: str, limit: int) -> list[MetricFact]:
            assert connector_id == "google_ads"
            captured_limits.append(limit)
            return []

    monkeypatch.setattr(
        "wilq.briefing.ads_diagnostics.metric_store",
        lambda: RecordingMetricStore(),
    )
    monkeypatch.setattr("wilq.briefing.ads_diagnostics._latest_google_ads_refresh", lambda: None)

    build_ads_diagnostics(view="summary")

    assert captured_limits
    assert captured_limits[0] < ADS_METRIC_FACT_LIMIT
    assert captured_limits[0] <= 2000


def test_ads_diagnostics_summary_view_reads_latest_refresh_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_evidence_ids: list[list[str]] = []
    latest_refresh = ConnectorRefreshRun(
        id="refresh_google_ads_summary_latest_evidence",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=[
            "ev_connector_google_ads_status",
            "ev_refresh_refresh_google_ads_summary_latest_evidence",
        ],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={"row_count": 1},
        summary="Latest Google Ads read for summary evidence test.",
    )

    class RecordingMetricStore:
        def list_metric_facts(self, connector_id: str, limit: int) -> list[MetricFact]:
            assert connector_id == "google_ads"
            return []

        def list_metric_facts_by_evidence_ids(
            self,
            evidence_ids: list[str],
        ) -> list[MetricFact]:
            captured_evidence_ids.append(evidence_ids)
            return []

    monkeypatch.setattr(
        "wilq.briefing.ads_diagnostics.metric_store",
        lambda: RecordingMetricStore(),
    )
    monkeypatch.setattr(
        "wilq.briefing.ads_diagnostics._latest_google_ads_refresh",
        lambda: latest_refresh,
    )

    build_ads_diagnostics(view="summary")

    assert captured_evidence_ids == [latest_refresh.evidence_ids]


def test_ads_diagnostics_uses_lightweight_action_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_full_action_list() -> list[ActionObject]:
        raise AssertionError("Ads diagnostics must not seed the full ActionObject list")

    monkeypatch.setattr(
        "wilq.actions.service.list_actions",
        fail_full_action_list,
    )

    response = client.get("/api/ads/diagnostics?view=summary")

    assert response.status_code == 200
    assert response.json()["action_ids"]


def test_ads_custom_segment_review_reason_keeps_missing_metrics_unknown() -> None:
    reason = _custom_segment_review_reason(
        source_terms=["bdo szkolenie"],
        rows=[
            AdsSearchTermMetricRow(
                search_term="bdo szkolenie",
                campaign_id="101",
                campaign_name="Brand Search",
                clicks=7,
                conversions=0.0,
                evidence_ids=["ev_test"],
                missing_metrics=[
                    "search_term_impressions",
                    "search_term_cost_micros",
                ],
            )
        ],
        rejected_terms=[],
    )

    assert "wyświetlenia niepotwierdzone" in reason
    assert "koszt niepotwierdzony" in reason
    assert "wyświetlenia=0" not in reason
    assert "koszt=0.00" not in reason


def test_ads_custom_segment_source_quality_counts_rejections() -> None:
    quality = _custom_segment_source_quality(
        source_terms=["bdo szkolenie"],
        rows=[
            AdsSearchTermMetricRow(
                search_term="bdo szkolenie",
                campaign_id="101",
                campaign_name="Brand Search",
                clicks=7,
                evidence_ids=["ev_test"],
                missing_metrics=["search_term_cost_micros"],
            )
        ],
        rejected_pairs=[
            ("ekologus kontakt", "termin wygląda na własny brand albo zapytanie nawigacyjne"),
            ("19115 odpady", "termin nie ma aktywności w dostępnych metrykach"),
            ("bdo katowice", "termin nie ma aktywności w dostępnych metrykach"),
        ],
    )

    assert quality.total_terms == 4
    assert quality.accepted_terms == 1
    assert quality.rejected_terms == 3
    assert quality.missing_metric_terms == 1
    assert quality.rejection_reasons == {
        "termin nie ma aktywności w dostępnych metrykach": 2,
        "termin wygląda na własny brand albo zapytanie nawigacyjne": 1,
    }


def test_ads_negative_keyword_candidate_exposes_marketer_preview_card() -> None:
    from wilq.briefing.ads_diagnostics import _hydrate_negative_keywords_marketer_labels
    from wilq.schemas import (
        AdsNegativeKeywordCandidate,
        AdsNegativeKeywordPayloadPreview,
        AdsNegativeKeywordsReadContract,
    )

    preview = AdsNegativeKeywordPayloadPreview(
        id="negative_keyword_preview_test",
        search_term="odpady cena",
        negative_keyword_text="odpady cena",
        match_type="EXACT",
        level="ad_group",
        campaign_name="Ekologus Search",
        ad_group_name="Odpady",
        reason="Do sprawdzenia przed zapisem zmian.",
        required_validation=[
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
        ],
        blocked_claims=["dodanie wykluczających słów kluczowych"],
    )
    contract = AdsNegativeKeywordsReadContract(
        status="ready",
        title="Ocena wykluczeń z wyszukiwanych haseł",
        summary="Kandydaci wykluczeń do sprawdzenia.",
        candidates=[
            AdsNegativeKeywordCandidate(
                id="ads_negative_keyword_review_test",
                search_term="odpady cena",
                review_reason="Kandydat do ręcznej oceny.",
                payload_preview=preview,
                next_step="Sprawdź intencję i historię przed wykluczeniem.",
            )
        ],
        payload_preview=[preview],
        next_step="Sprawdź intencję i historię przed wykluczeniem.",
    )

    _hydrate_negative_keywords_marketer_labels(contract)

    card = contract.candidates[0].preview_card
    assert card is not None
    assert card.kind == "google_ads_negative_keyword_review"
    assert card.title_label == "Wykluczenie słowa do sprawdzenia"
    rows = {row.label: row.value for row in card.rows}
    assert rows["Dopasowanie"] == "dopasowanie ścisłe"
    assert rows["Poziom"] == "grupa reklam"
    assert "sprawdzenie intencji zapytania" in rows["Warunki sprawdzenia"]
    assert "dodanie wykluczających słów kluczowych" in rows["Czego nie wolno twierdzić"]
    assert "EXACT" not in str(card.model_dump())
    assert "ad_group" not in str(card.model_dump())


def test_ads_budget_row_exposes_marketer_preview_card() -> None:
    from wilq.briefing.ads_diagnostics import _hydrate_budget_pacing_marketer_labels
    from wilq.schemas import (
        AdsBudgetApplyPreview,
        AdsBudgetApplySafetyReview,
        AdsBudgetPacingReadContract,
        AdsBudgetPacingRow,
    )

    preview = AdsBudgetApplyPreview(
        id="budget_apply_preview_test",
        campaign_id="101",
        campaign_name="Brand Search",
        campaign_budget_id="701",
        campaign_budget_name="Brand budget",
        operation_type="CampaignBudgetOperation",
        current_budget_amount_micros=30000000,
        proposed_budget_amount_micros=42000000,
        proposed_budget_delta_micros=12000000,
        reason="Budżet do sprawdzenia przed zapisem zmian.",
        required_validation=[
            "review_campaign_activity",
            "verify_account_currency",
            "budget_pacing",
        ],
        blocked_claims=["zmiana budżetu"],
        safety_review=AdsBudgetApplySafetyReview(
            id="budget_apply_preview_test_safety",
            budget_preview_id="budget_apply_preview_test",
            reason="Zapis zmian zablokowany.",
            missing_requirements=[
                "change_history",
                "human_budget_goal",
                "mutation_audit",
            ],
            blocked_claims=["zmiana budżetu"],
        ),
    )
    contract = AdsBudgetPacingReadContract(
        status="ready",
        title="Budżety kampanii",
        summary="Budżety do sprawdzenia.",
        budget_rows=[
            AdsBudgetPacingRow(
                campaign_id="101",
                campaign_name="Brand Search",
                budget_id="701",
                budget_name="Brand budget",
                payload_preview=preview,
            )
        ],
        payload_preview=[preview],
        next_step="Sprawdź budżet przed zapisem zmian.",
    )

    _hydrate_budget_pacing_marketer_labels(contract, "PLN")

    card = contract.budget_rows[0].preview_card
    assert card is not None
    assert card.kind == "google_ads_budget_review"
    assert card.title_label == "Budżet kampanii do sprawdzenia"
    rows = {row.label: row.value for row in card.rows}
    assert rows["Budżet teraz"] == "30 PLN"
    assert rows["Propozycja do sprawdzenia"] == "42 PLN"
    assert rows["Operacja"] == "zmiana budżetu kampanii"
    assert rows["Powiązanie"] == ("kampania albo budżet do sprawdzenia w szczegółach technicznych")
    assert "sprawdzenie aktywności kampanii" in rows["Warunki sprawdzenia"]
    assert "historia zmian" in rows["Braki bezpieczeństwa"]
    assert "audyt zapisu zmian" in rows["Braki bezpieczeństwa"]
    assert "mutation_audit" not in rows["Braki bezpieczeństwa"]
    dumped = str(card.model_dump())
    assert "CampaignBudgetOperation" not in dumped
    assert "101" not in dumped
    assert "701" not in dumped


def test_ads_budget_preview_explains_missing_proposal() -> None:
    from wilq.briefing.ads_diagnostics import _hydrate_budget_pacing_marketer_labels
    from wilq.schemas import (
        AdsBudgetApplyPreview,
        AdsBudgetApplySafetyReview,
        AdsBudgetPacingReadContract,
        AdsBudgetPacingRow,
    )

    preview = AdsBudgetApplyPreview(
        id="budget_apply_preview_missing_proposal",
        campaign_id="101",
        campaign_name="Brand Search",
        campaign_budget_id="701",
        campaign_budget_name="Brand budget",
        operation_type="CampaignBudgetOperation",
        current_budget_amount_micros=30000000,
        proposed_budget_amount_micros=None,
        proposed_budget_delta_micros=None,
        reason=("Podgląd budżetu do sprawdzenia. Google Ads nie zwrócił rekomendowanego budżetu."),
        required_validation=[
            "review_campaign_activity",
            "human_budget_goal",
            "campaign_budget_apply_safety",
        ],
        blocked_claims=["zmiana budżetu"],
        safety_review=AdsBudgetApplySafetyReview(
            id="budget_apply_preview_missing_proposal_safety",
            budget_preview_id="budget_apply_preview_missing_proposal",
            reason="Zapis zmiany budżetu zablokowany: brak proponowanej kwoty.",
            missing_requirements=["human_budget_goal", "recommended_budget_missing"],
            blocked_claims=["zmiana budżetu"],
        ),
    )
    contract = AdsBudgetPacingReadContract(
        status="blocked",
        title="Budżety kampanii",
        summary="Budżety do sprawdzenia.",
        budget_rows=[
            AdsBudgetPacingRow(
                campaign_id="101",
                campaign_name="Brand Search",
                budget_id="701",
                budget_name="Brand budget",
                payload_preview=preview,
            )
        ],
        payload_preview=[preview],
        next_step="Sprawdź budżet przed zapisem zmian.",
    )

    _hydrate_budget_pacing_marketer_labels(contract, "PLN")

    card = contract.budget_rows[0].preview_card
    assert card is not None
    rows = {row.label: row.value for row in card.rows}
    assert rows["Budżet teraz"] == "30 PLN"
    assert (
        rows["Propozycja do sprawdzenia"] == "brak proponowanej kwoty; WILQ blokuje zapis budżetu"
    )
    assert rows["Propozycja do sprawdzenia"] != "brak danych"
    assert "brak rekomendowanego budżetu z Google Ads" in rows["Braki bezpieczeństwa"]


def test_ads_recommendation_row_exposes_marketer_preview_card() -> None:
    from wilq.briefing.ads_diagnostics import _hydrate_recommendations_marketer_labels
    from wilq.schemas import (
        AdsRecommendationApplyPreview,
        AdsRecommendationRow,
        AdsRecommendationsReadContract,
    )

    preview = AdsRecommendationApplyPreview(
        id="recommendation_apply_preview_test",
        recommendation_id="rec-1",
        recommendation_type="CAMPAIGN_BUDGET",
        campaign_id="101",
        campaign_budget_id="701",
        operation_type="ApplyRecommendationOperation",
        reason="Do sprawdzenia przed zapisem zmian.",
        required_validation=[
            "review_recommendation_type",
            "review_impact_metrics",
        ],
        blocked_claims=["zapis rekomendacji"],
    )
    contract = AdsRecommendationsReadContract(
        status="ready",
        title="Rekomendacje Google Ads",
        summary="Rekomendacje do sprawdzenia.",
        recommendation_rows=[
            AdsRecommendationRow(
                recommendation_id="rec-1",
                recommendation_type="CAMPAIGN_BUDGET",
                review_reason="Rekomendacja do ręcznej oceny.",
                payload_preview=preview,
            )
        ],
        payload_preview=[preview],
        next_step="Sprawdź rekomendację przed zapisem zmian.",
    )

    _hydrate_recommendations_marketer_labels(contract)

    card = contract.recommendation_rows[0].preview_card
    assert card is not None
    assert card.kind == "google_ads_recommendation_review"
    assert card.title_label == "Rekomendacja Google Ads do sprawdzenia"
    rows = {row.label: row.value for row in card.rows}
    assert rows["Rekomendacja"] == "budżet kampanii"
    assert rows["Operacja"] == "zastosowanie rekomendacji Google Ads"
    assert rows["Powiązanie"] == ("kampania albo budżet do sprawdzenia w szczegółach technicznych")
    assert "sprawdzenie typu rekomendacji" in rows["Warunki sprawdzenia"]
    assert "zapis rekomendacji" in rows["Czego nie wolno twierdzić"]
    dumped = str(card.model_dump())
    assert "ApplyRecommendationOperation" not in dumped
    assert "CAMPAIGN_BUDGET" not in dumped
    assert "101" not in dumped
    assert "701" not in dumped


def test_ads_recommendation_impact_reason_does_not_turn_missing_cost_into_zero() -> None:
    from wilq.briefing.ads_recommendations import _recommendation_review_reason

    reason = _recommendation_review_reason(
        recommendation_type="CAMPAIGN_BUDGET",
        impact_available=True,
        delta_clicks=None,
        delta_cost_micros=None,
        delta_conversions=None,
        missing_metrics=[],
    )

    assert "zmiana kliknięć niepotwierdzona" in reason
    assert "zmiana kosztu niepotwierdzona" in reason
    assert "zmiana konwersji niepotwierdzona" in reason
    assert "zmiana kosztu 0" not in reason
