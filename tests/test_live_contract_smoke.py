from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_live_smoke_module() -> Any:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "live_contract_smoke.py"
    spec = importlib.util.spec_from_file_location("live_contract_smoke", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payloads_with_metric_value(value: int) -> dict[str, Any]:
    return {
        "health": {"status": "ok", "service": "wilq-api"},
        "command_center": {
            "strict_instruction": "WILQ pokazuje tylko metryki z API/evidence.",
            "daily_decisions": [
                {
                    "id": "decision_review_ads",
                    "title": "Przejrzyj Ads",
                    "domain": "google_ads",
                    "freshness": {"state": "fresh"},
                    "decision_state": "ready",
                    "status": "ready",
                    "why_it_matters": "Ads evidence exists.",
                    "operator_action": "Review Ads safely.",
                    "evidence_ids": ["ev_refresh_refresh_google_ads_123"],
                    "source_connectors": ["google_ads"],
                    "action_ids": ["act_prepare_ads_campaign_review_queue"],
                    "metric_tiles": {"kliknięcia": value},
                    "metric_facts": [
                        {
                            "name": "clicks",
                            "value": value,
                            "period": "connector_refresh",
                            "source_connector": "google_ads",
                            "evidence_id": "ev_refresh_refresh_google_ads_123",
                        }
                    ],
                }
            ],
            "action_plan": [
                {
                    "id": "plan_review_ads",
                    "title": "Przejrzyj Ads",
                    "status": "ready",
                    "evidence_ids": ["ev_refresh_refresh_google_ads_123"],
                    "source_connectors": ["google_ads"],
                }
            ],
        },
        "marketing_brief": {
            "strict_instruction": "WILQ pokazuje tylko metryki z API/evidence.",
            "sections": [
                {
                    "id": "what_we_know",
                    "title": "Co wiemy",
                    "items": [
                        {
                            "id": "brief_ads",
                            "title": "Ads",
                            "evidence_ids": ["ev_refresh_refresh_google_ads_123"],
                            "source_connectors": ["google_ads"],
                        }
                    ],
                }
            ],
            "evidence_ids": ["ev_refresh_refresh_google_ads_123"],
        },
        "ads_diagnostics": {
            "language": "pl-PL",
            "evidence_ids": ["ev_refresh_refresh_google_ads_123"],
            "decision_queue": [
                {
                    "id": "ads_review_campaign_activity",
                    "status": "ready",
                    "evidence_ids": ["ev_refresh_refresh_google_ads_123"],
                }
            ],
        },
        "merchant_diagnostics": {
            "language": "pl-PL",
            "evidence_ids": ["ev_refresh_refresh_google_merchant_center_123"],
            "decision_queue": [],
            "action_ids": ["act_review_merchant_feed_issues"],
        },
        "content_diagnostics": {
            "language": "pl-PL",
            "evidence_ids": ["ev_refresh_refresh_google_search_console_123"],
            "tactical_items": [],
            "action_ids": ["act_prepare_content_refresh_queue"],
        },
        "ga4_diagnostics": {
            "language": "pl-PL",
            "evidence_ids": ["ev_refresh_refresh_google_analytics_4_123"],
            "decision_queue": [],
            "action_ids": ["act_review_ga4_tracking_quality"],
        },
        "localo_diagnostics": {
            "language": "pl-PL",
            "evidence_ids": ["ev_refresh_refresh_localo_123"],
            "decision_queue": [],
            "action_ids": ["act_review_localo_visibility_facts"],
        },
    }


def test_live_contract_smoke_accepts_variable_metric_values() -> None:
    smoke = _load_live_smoke_module()

    low_value_errors = smoke.evaluate_contracts(_payloads_with_metric_value(1))
    high_value_errors = smoke.evaluate_contracts(_payloads_with_metric_value(9999))

    assert low_value_errors == []
    assert high_value_errors == []


def test_live_contract_smoke_rejects_missing_evidence_and_decisions() -> None:
    smoke = _load_live_smoke_module()
    payloads = _payloads_with_metric_value(12)
    payloads["command_center"]["daily_decisions"] = []
    payloads["marketing_brief"]["evidence_ids"] = []

    errors = smoke.evaluate_contracts(payloads)

    assert "command_center.daily_decisions must not be empty" in errors
    assert "marketing_brief.evidence_ids must not be empty" in errors


def test_live_contract_smoke_rejects_daily_decision_without_decision_state() -> None:
    smoke = _load_live_smoke_module()
    payloads = _payloads_with_metric_value(12)
    del payloads["command_center"]["daily_decisions"][0]["decision_state"]

    errors = smoke.evaluate_contracts(payloads)

    assert "command_center.daily_decisions[0].decision_state must be present" in errors
