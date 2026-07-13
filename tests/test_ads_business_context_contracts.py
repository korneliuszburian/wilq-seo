"""Focused tests for the extracted Ads strategy-review contract owner."""

from __future__ import annotations

from wilq.briefing.ads_business_context_contracts import (
    business_context_contract_state,
    business_context_policy_ids,
    business_context_read_metric_tiles,
    business_context_review_gates,
    business_context_summary_and_next_step,
    business_target_interpretation,
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


def test_business_target_interpretation_blocks_verdicts_without_context() -> None:
    result = business_target_interpretation(
        status="blocked",
        profit_margin=None,
        business_goal=None,
        budget_goal=None,
        target_roas=None,
        target_cpa_micros=None,
        target_missing=True,
        strategy_review_status="missing",
        strategy_review_approved=False,
        business_policy_ids=["complete_business_context_before_ads_verdicts"],
        evidence_ids=["ev_ads_context"],
    )

    assert result.status == "blocked"
    assert "profitability_verdict" in result.blocked_uses
    assert result.missing_requirements == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]


def test_business_target_interpretation_keeps_confirmed_target_review_only() -> None:
    result = business_target_interpretation(
        status="ready",
        profit_margin=0.2,
        business_goal="pozyskanie zapytań",
        budget_goal="utrzymać obecny budżet",
        target_roas=3.0,
        target_cpa_micros=None,
        target_missing=False,
        strategy_review_status="approved_for_prepare",
        strategy_review_approved=True,
        business_policy_ids=["compare_kpis_to_confirmed_target_in_review"],
        evidence_ids=["ev_ads_context"],
    )

    assert result.status == "ready"
    assert "target_roas_review" in result.allowed_uses
    assert "automatic_scaling" in result.blocked_uses


def test_business_context_read_metric_tiles_preserve_existing_operator_shape() -> None:
    tiles = business_context_read_metric_tiles(
        profit_margin=0.2,
        business_goal="pozyskanie zapytań",
        budget_goal="utrzymać obecny budżet",
        target_roas=3.0,
        target_cpa_micros=1_250_000,
        target_confirmation=object(),
        strategy_review_status="approved_for_prepare",
    )

    assert tiles == {
        "marża": "20%",
        "cel biznesowy": "pozyskanie zapytań",
        "cel budżetu": "utrzymać obecny budżet",
        "docelowy zwrot z reklam": 3.0,
        "docelowy koszt pozyskania celu": "1.25",
        "źródło celu": "potwierdzone",
        "ocena strategii": "zatwierdzone",
    }
