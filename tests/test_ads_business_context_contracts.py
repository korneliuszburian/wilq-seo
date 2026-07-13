"""Focused tests for the extracted Ads strategy-review contract owner."""

from __future__ import annotations

from wilq.briefing.ads_business_context_contracts import (
    business_context_contract_state,
    business_context_policy_ids,
    business_context_review_gates,
    business_context_summary_and_next_step,
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


def test_business_context_state_preserves_fail_closed_missing_contract_order() -> None:
    state = business_context_contract_state(
        profit_margin=None,
        business_goal=None,
        budget_goal=None,
        target_roas=None,
        target_cpa_micros=None,
        strategy_review_status="missing",
        strategy_review_approved=False,
    )

    assert state == (
        [
            "profit_margin",
            "business_goal",
            "human_budget_goal",
            "target_roas_or_cpa",
            "human_strategy_review",
        ],
        [],
        True,
        "blocked",
    )


def test_business_context_review_gates_remain_operator_readable() -> None:
    gates = business_context_review_gates(
        profit_margin=0.2,
        business_goal="pozyskanie zapytań",
        budget_goal=None,
        target_missing=True,
        strategy_review_approved=False,
    )

    assert gates == [
        "human_strategy_review",
        "review_profit_margin_model",
        "review_business_goal",
        "configure_human_budget_goal",
        "confirm_target_roas_or_cpa",
    ]


def test_business_context_policy_and_summary_keep_blockers_explicit() -> None:
    policy_ids = business_context_policy_ids(
        profit_margin=None,
        business_goal=None,
        budget_goal=None,
        target_missing=True,
        strategy_review_approved=False,
        status="blocked",
    )
    summary, next_step = business_context_summary_and_next_step(
        status="blocked",
        target_missing=True,
    )

    assert policy_ids == [
        "complete_business_context_before_ads_verdicts",
        "block_target_verdict_until_roas_or_cpa_confirmed",
        "block_target_verdict_until_strategy_review_approved",
    ]
    assert "nie ma kompletnego lokalnego kontekstu" in summary
    assert "WILQ_ADS_PROFIT_MARGIN" in next_step
