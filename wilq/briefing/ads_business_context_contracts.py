"""Typed Google Ads business-context readiness projections."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from wilq.actions.google_ads.business_context import ADS_STRATEGY_REVIEW_ACTION_ID
from wilq.schemas import AdsStrategyReviewReadinessContract

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


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
