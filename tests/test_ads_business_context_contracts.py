"""Focused tests for the extracted Ads strategy-review contract owner."""

from __future__ import annotations

from wilq.briefing.ads_business_context_contracts import (
    strategy_review_readiness_contract,
)


def test_strategy_review_readiness_stays_blocked_and_prepare_only() -> None:
    contract = strategy_review_readiness_contract(
        strategy_review=None,
        strategy_review_status="missing",
        strategy_review_approved=False,
        profit_margin=None,
        business_goal=None,
        budget_goal=None,
        target_roas=None,
        target_cpa_micros=None,
        missing_read_contracts=[
            "profit_margin",
            "business_goal",
            "human_budget_goal",
            "target_roas_or_cpa",
            "human_strategy_review",
        ],
        evidence_ids=["ev_google_ads_context"],
    )

    assert contract.status == "blocked"
    assert contract.action_ids == ["act_record_ads_strategy_review"]
    assert contract.evidence_ids == ["ev_google_ads_context"]
    assert contract.apply_allowed is False
    assert contract.destructive is False
