from __future__ import annotations

from typing import Any


def validate_account_business_budget(
    pack: dict[str, Any],
    account_currency: dict[str, Any],
    business_context: dict[str, Any],
    budget_pacing: dict[str, Any],
    budget_decision: dict[str, Any],
    pack_budget_decision: dict[str, Any],
) -> dict[str, Any]:
    pack_ads = pack.get("ads_diagnostics", {})
    _currency(account_currency, pack_ads.get("account_currency_read_contract") or {})
    strategy = _business(business_context, pack_ads.get("business_context_read_contract") or {})
    _budget(
        budget_pacing,
        pack_ads.get("budget_pacing_read_contract") or {},
        budget_decision,
        pack_budget_decision,
    )
    return strategy


def _currency(contract: dict[str, Any], packed: dict[str, Any]) -> None:
    if contract.get("status") not in {"ready", "blocked"} or packed.get("summary") != contract.get(
        "summary"
    ):
        raise SystemExit("Ads account currency contract differs from context pack")
    if contract.get("status") == "ready":
        if (
            not isinstance(contract.get("currency_code"), str)
            or len(contract["currency_code"]) != 3
        ):
            raise SystemExit("Ready account currency contract must expose ISO currency code")
    elif "account_currency" not in contract.get("missing_read_contracts", []):
        raise SystemExit("Blocked account currency contract must list missing account_currency")


def _business(contract: dict[str, Any], packed: dict[str, Any]) -> dict[str, Any]:
    if contract.get("status") not in {"ready", "blocked"} or packed.get("summary") != contract.get(
        "summary"
    ):
        raise SystemExit("Ads business context contract differs from context pack")
    strategy = contract.get("strategy_review_readiness_contract") or {}
    packed_strategy = packed.get("strategy_review_readiness_contract") or {}
    if (
        strategy.get("id") != "ads_strategy_review_readiness_contract"
        or strategy.get("apply_allowed") is not False
    ):
        raise SystemExit("Strategy review readiness must keep apply blocked")
    if "ocena opłacalności" not in strategy.get("blocked_claims", []):
        raise SystemExit("Strategy review readiness must block opłacalność")
    if (
        packed_strategy.get("id") != strategy.get("id")
        or packed_strategy.get("status") != strategy.get("status")
        or packed_strategy.get("apply_allowed") is not False
    ):
        raise SystemExit("Context pack strategy readiness differs")
    if "human_strategy_review" not in packed_strategy.get("required_validation", []):
        raise SystemExit("Strategy readiness must require human review")
    if contract.get("status") == "blocked" and not contract.get("missing_read_contracts"):
        raise SystemExit("Blocked business context contract must list missing contracts")
    return strategy


def _budget(
    contract: dict[str, Any],
    packed: dict[str, Any],
    decision: dict[str, Any],
    packed_decision: dict[str, Any],
) -> None:
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose budget_pacing_read_contract")
    if contract.get("status") != "ready":
        return
    rows = contract.get("budget_rows") or []
    if (
        not rows
        or not packed.get("budget_rows")
        or contract.get("shared_budget_distribution_rows") is None
        or packed.get("shared_budget_distribution_rows") is None
    ):
        raise SystemExit(
            "Ready budget pacing contract must expose budget rows and shared distribution"
        )
    if all(row.get("budget_id") for row in rows) and "shared_budget_distribution" in contract.get(
        "missing_read_contracts", []
    ):
        raise SystemExit("Budget pacing contract must not miss shared distribution")
    if "zmiana budżetu" not in contract.get("blocked_claims", []):
        raise SystemExit("Budget pacing contract must keep zmiana budżetu blocked")
    if "card_google_ads_budget_review_playbook" not in decision.get("knowledge_card_ids", []):
        raise SystemExit("Budget decision must expose budget review knowledge card")
    if not {"ads_scaling_candidates_v1", "ads_recommendations_v1", "ads_principles_v1"} <= set(
        decision.get("expert_rule_ids", [])
    ):
        raise SystemExit("Budget decision must expose budget review expert rules")
    if packed_decision.get("knowledge_card_ids") != decision.get(
        "knowledge_card_ids"
    ) or packed_decision.get("expert_rule_ids") != decision.get("expert_rule_ids"):
        raise SystemExit("Context pack budget decision lineage differs")
