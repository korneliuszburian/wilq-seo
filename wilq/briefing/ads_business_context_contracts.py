"""Typed Google Ads business-context readiness projections."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from wilq.actions.google_ads.business_context import ADS_STRATEGY_REVIEW_ACTION_ID
from wilq.schemas import AdsBusinessTargetInterpretation, AdsStrategyReviewReadinessContract

GOOGLE_ADS_CONNECTOR_ID = "google_ads"
StrategyReviewStatus = Literal[
    "missing",
    "approved_for_prepare",
    "needs_changes",
    "rejected",
    "deferred",
]


def strategy_review_operator_state(
    *,
    strategy_review_approved: bool,
    missing_read_contracts: list[str],
) -> tuple[Literal["ready", "blocked"], str, str, list[str], list[str]]:
    if strategy_review_approved:
        return (
            "ready",
            "Ocena strategii Ads przez człowieka jest zatwierdzona do przygotowania. To pozwala "
            "używać potwierdzonego celu w ocenie, ale nie odblokowuje zapisu zmian "
            "ani automatycznej optymalizacji.",
            "Użyj zatwierdzonej oceny jako kontekstu decyzji. Każda ścieżka zapisu "
            "nadal wymaga osobnego sprawdzenia w WILQ, podglądu, potwierdzenia i audytu.",
            [],
            [],
        )
    return (
        "blocked",
        "Ocena strategii Ads przez człowieka nie jest zatwierdzona, więc WILQ może "
        "tylko przygotować kolejki do oceny. Ocena celu, ocena "
        "opłacalności, skalowanie i zapis zmian pozostają zablokowane.",
        "Otwórz akcję strategii, sprawdź marżę, cel biznesowy, cel budżetu oraz "
        "docelowy zwrot z reklam albo koszt pozyskania celu, a potem zapisz wynik oceny.",
        _unique(
            missing
            for missing in missing_read_contracts
            if missing
            in {
                "profit_margin",
                "business_goal",
                "human_budget_goal",
                "target_roas_or_cpa",
                "human_strategy_review",
                "approved_human_strategy_review",
            }
        ),
        [ADS_STRATEGY_REVIEW_ACTION_ID],
    )


def strategy_review_readiness_contract(
    *,
    strategy_review: Any | None,
    strategy_review_status: StrategyReviewStatus,
    strategy_review_approved: bool,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_roas: float | None,
    target_cpa_micros: int | None,
    missing_read_contracts: list[str],
    evidence_ids: list[str],
) -> AdsStrategyReviewReadinessContract:
    required_validation = [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review",
    ]
    blocked_claims = [
        "ocena opłacalności",
        "ocena wskaźników względem celu",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "automatyczna optymalizacja",
    ]
    current_context = {
        "profit_margin": profit_margin,
        "business_goal": business_goal,
        "budget_goal": budget_goal,
        "target_roas": target_roas,
        "target_cpa_micros": target_cpa_micros,
    }
    status, summary, next_step, contract_missing, action_ids = strategy_review_operator_state(
        strategy_review_approved=strategy_review_approved,
        missing_read_contracts=missing_read_contracts,
    )
    latest_outcome = strategy_review.outcome if strategy_review is not None else None
    return AdsStrategyReviewReadinessContract(
        status=status,
        title="Google Ads: gotowość oceny strategii przez człowieka",
        summary=summary,
        latest_review_status=strategy_review_status,
        latest_review_outcome=latest_outcome,
        reviewed_by=strategy_review.reviewed_by if strategy_review is not None else None,
        reviewed_at=strategy_review.created_at if strategy_review is not None else None,
        current_context=current_context,
        required_validation=required_validation,
        missing_read_contracts=contract_missing,
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        apply_allowed=False,
        destructive=False,
        next_step=next_step,
    )


def business_context_contract_state(
    *,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_roas: float | None,
    target_cpa_micros: int | None,
    strategy_review_status: str,
    strategy_review_approved: bool,
) -> tuple[list[str], list[str], bool, Literal["ready", "blocked"]]:
    """Return missing contracts, allowed metrics and fail-closed readiness."""
    missing_read_contracts: list[str] = []
    if profit_margin is None:
        missing_read_contracts.append("profit_margin")
    if not business_goal:
        missing_read_contracts.append("business_goal")
    if not budget_goal:
        missing_read_contracts.append("human_budget_goal")
    if target_roas is None and target_cpa_micros is None:
        missing_read_contracts.append("target_roas_or_cpa")
    if strategy_review_status == "missing":
        missing_read_contracts.append("human_strategy_review")
    elif not strategy_review_approved:
        missing_read_contracts.append("approved_human_strategy_review")
    allowed_metrics = [
        name
        for name, value in [
            ("profit_margin", profit_margin),
            ("business_goal", business_goal),
            ("human_budget_goal", budget_goal),
            ("target_roas", target_roas),
            ("target_cpa_micros", target_cpa_micros),
        ]
        if value is not None and value != ""
    ]
    blocking_missing_contracts = [
        contract
        for contract in missing_read_contracts
        if contract not in {"target_roas_or_cpa", "human_strategy_review"}
    ]
    target_missing = "target_roas_or_cpa" in missing_read_contracts
    status: Literal["ready", "blocked"] = "ready" if not blocking_missing_contracts else "blocked"
    return missing_read_contracts, allowed_metrics, target_missing, status


def business_context_review_gates(
    *,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_missing: bool,
    strategy_review_approved: bool,
) -> list[str]:
    """Describe the human/configuration gates required before Ads verdicts."""
    gates = ["strategy_review_approved" if strategy_review_approved else "human_strategy_review"]
    gates.append(
        "review_profit_margin_model"
        if profit_margin is not None
        else "configure_profit_margin_or_value_model"
    )
    gates.append("review_business_goal" if business_goal else "configure_business_goal")
    gates.append("review_human_budget_goal" if budget_goal else "configure_human_budget_goal")
    gates.append("confirm_target_roas_or_cpa" if target_missing else "review_target_fit")
    return _unique(gates)


def business_context_policy_ids(
    *,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_missing: bool,
    strategy_review_approved: bool,
    status: Literal["ready", "blocked"],
) -> list[str]:
    """Return the policy lineage that explains the Ads context verdict."""
    policy_ids: list[str] = []
    if status == "blocked":
        policy_ids.append("complete_business_context_before_ads_verdicts")
    if profit_margin is not None:
        policy_ids.append("use_margin_as_context_not_profitability_verdict")
    if business_goal:
        policy_ids.append("align_campaign_review_to_business_goal")
    if budget_goal:
        policy_ids.append("honor_human_budget_goal_before_budget_changes")
    if target_missing:
        policy_ids.append("block_target_verdict_until_roas_or_cpa_confirmed")
    else:
        policy_ids.append("compare_kpis_to_confirmed_target_in_review")
    if strategy_review_approved:
        policy_ids.append("use_approved_strategy_review_before_target_verdict")
    else:
        policy_ids.append("block_target_verdict_until_strategy_review_approved")
    return _unique(policy_ids)


def business_context_summary_and_next_step(
    *,
    status: Literal["ready", "blocked"],
    target_missing: bool,
) -> tuple[str, str]:
    """Keep operator-facing context rationale and next step API-owned."""
    if status == "ready" and target_missing:
        return (
            "WILQ ma wstępny lokalny kontekst biznesowy Ads: marżę, cel "
            "biznesowy i cel budżetu. Docelowy zwrot z reklam albo koszt pozyskania "
            "celu jest celowo pusty, więc wskaźniki względem celu pozostają bez oceny "
            "i nie odblokowują skalowania ani zapisu zmian.",
            "Użyj marży i celu budżetu jako kontekstu oceny kampanii. Jeśli operator "
            "potwierdzi docelowy zwrot z reklam albo koszt pozyskania celu przez "
            "sprawdzoną akcję, WILQ zapisze go w lokalnym stanie; do tego czasu ocena "
            "celu pozostaje zablokowana.",
        )
    if status == "ready":
        return (
            "WILQ ma lokalny kontekst biznesowy Ads: marżę, cel biznesowy, cel "
            "budżetu oraz docelowy zwrot z reklam albo koszt pozyskania celu. To "
            "pozwala interpretować wskaźniki ostrożniej, ale nadal nie odblokowuje "
            "automatycznych zmian.",
            "Użyj potwierdzonego celu jako kontekstu oceny kampanii i budżetu. Zapis "
            "zmian nadal wymaga akcji do sprawdzenia w WILQ, podglądu zmian, "
            "potwierdzenia i audytu.",
        )
    return (
        "WILQ ma aktualne metryki Google Ads, ale nie ma kompletnego lokalnego "
        "kontekstu biznesowego: marży, celu biznesowego, celu budżetu albo "
        "docelowego zwrotu z reklam lub kosztu pozyskania celu. Bez tego wskaźniki "
        "są tylko wstępnym przeglądem, nie oceną.",
        "Uzupełnij nie-sekretne wartości w repo-local .env: "
        "WILQ_ADS_PROFIT_MARGIN, WILQ_ADS_BUSINESS_GOAL, WILQ_ADS_BUDGET_GOAL "
        "oraz WILQ_ADS_TARGET_ROAS albo WILQ_ADS_TARGET_CPA_MICROS.",
    )


def business_target_missing_requirements(
    *,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_missing: bool,
    strategy_review_status: str,
    strategy_review_approved: bool,
) -> list[str]:
    missing: list[str] = []
    if profit_margin is None:
        missing.append("profit_margin")
    if not business_goal:
        missing.append("business_goal")
    if not budget_goal:
        missing.append("human_budget_goal")
    if target_missing:
        missing.append("target_roas_or_cpa")
    if strategy_review_status == "missing":
        missing.append("human_strategy_review")
    elif not strategy_review_approved:
        missing.append("approved_human_strategy_review")
    return missing


def business_target_interpretation(
    *,
    status: Literal["ready", "blocked"],
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_roas: float | None,
    target_cpa_micros: int | None,
    target_missing: bool,
    strategy_review_status: str,
    strategy_review_approved: bool,
    business_policy_ids: list[str],
    evidence_ids: list[str],
) -> AdsBusinessTargetInterpretation:
    required_validation = [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review",
    ]
    missing_requirements = business_target_missing_requirements(
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_missing=target_missing,
        strategy_review_status=strategy_review_status,
        strategy_review_approved=strategy_review_approved,
    )
    if status == "blocked":
        return AdsBusinessTargetInterpretation(
            status="blocked",
            summary=(
                "WILQ nie interpretuje wskaźników biznesowo, dopóki brakuje marży, "
                "celu biznesowego albo celu budżetu."
            ),
            allowed_uses=[],
            blocked_uses=[
                "profitability_verdict",
                "target_kpi_verdict",
                "budget_scaling",
                "budget_apply",
                "wasted_budget_claim",
            ],
            missing_requirements=missing_requirements,
            required_validation=required_validation,
            policy_ids=business_policy_ids,
            evidence_ids=evidence_ids,
        )
    allowed_uses = [
        "campaign_review_context",
        "budget_review_context",
        "human_strategy_review_context",
    ]
    if profit_margin is not None:
        allowed_uses.append("margin_context")
    if business_goal:
        allowed_uses.append("business_goal_alignment")
    if budget_goal:
        allowed_uses.append("budget_goal_guardrail")
    if target_missing or not strategy_review_approved:
        return _preliminary_target_interpretation(
            allowed_uses=allowed_uses,
            target_roas=target_roas,
            target_cpa_micros=target_cpa_micros,
            target_missing=target_missing,
            missing_requirements=missing_requirements,
            required_validation=required_validation,
            business_policy_ids=business_policy_ids,
            evidence_ids=evidence_ids,
        )
    return _ready_target_interpretation(
        allowed_uses=allowed_uses,
        target_roas=target_roas,
        target_cpa_micros=target_cpa_micros,
        missing_requirements=missing_requirements,
        required_validation=required_validation,
        business_policy_ids=business_policy_ids,
        evidence_ids=evidence_ids,
    )


def _preliminary_target_interpretation(
    *,
    allowed_uses: list[str],
    target_roas: float | None,
    target_cpa_micros: int | None,
    target_missing: bool,
    missing_requirements: list[str],
    required_validation: list[str],
    business_policy_ids: list[str],
    evidence_ids: list[str],
) -> AdsBusinessTargetInterpretation:
    if target_missing:
        summary = (
            "WILQ może używać marży, celu biznesowego i celu budżetu jako kontekstu "
            "oceny, ale blokuje ocenę wskaźników względem celu, ocenę rentowności i "
            "zapis zmian do czasu potwierdzenia docelowego zwrotu z reklam albo kosztu "
            "pozyskania celu."
        )
    else:
        summary = (
            "WILQ ma potwierdzony docelowy zwrot z reklam albo koszt pozyskania celu, "
            "ale blokuje ocenę wskaźników względem celu i zapis zmian, dopóki ocena "
            "strategii przez człowieka nie będzie zatwierdzona."
        )
        if target_roas is not None:
            allowed_uses.append("target_roas_review_context")
        if target_cpa_micros is not None:
            allowed_uses.append("target_cpa_review_context")
    return AdsBusinessTargetInterpretation(
        status="preliminary",
        summary=summary,
        allowed_uses=allowed_uses,
        blocked_uses=[
            "target_kpi_verdict",
            "profitability_verdict",
            "budget_scaling",
            "budget_apply",
            "recommendation_apply",
        ],
        missing_requirements=missing_requirements,
        required_validation=required_validation,
        policy_ids=business_policy_ids,
        evidence_ids=evidence_ids,
    )


def _ready_target_interpretation(
    *,
    allowed_uses: list[str],
    target_roas: float | None,
    target_cpa_micros: int | None,
    missing_requirements: list[str],
    required_validation: list[str],
    business_policy_ids: list[str],
    evidence_ids: list[str],
) -> AdsBusinessTargetInterpretation:
    if target_roas is not None:
        allowed_uses.append("target_roas_review")
    if target_cpa_micros is not None:
        allowed_uses.append("target_cpa_review")
    return AdsBusinessTargetInterpretation(
        status="ready",
        summary=(
            "WILQ ma potwierdzony docelowy zwrot z reklam albo koszt pozyskania celu "
            "i może porównywać wskaźniki do celu po zatwierdzeniu przez człowieka. "
            "Zapis zmian nadal wymaga akcji do sprawdzenia w WILQ, podglądu zmian, "
            "potwierdzenia i audytu."
        ),
        allowed_uses=allowed_uses,
        blocked_uses=[
            "budget_apply",
            "recommendation_apply",
            "automatic_scaling",
            "profitability_verdict_without_value_model_review",
        ],
        missing_requirements=missing_requirements,
        required_validation=required_validation,
        policy_ids=business_policy_ids,
        evidence_ids=evidence_ids,
    )


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
