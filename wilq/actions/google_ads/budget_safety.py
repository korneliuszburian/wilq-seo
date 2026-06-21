from __future__ import annotations

from typing import Any

CAMPAIGN_BUDGET_APPLY_SAFETY_CONTRACT = "campaign_budget_apply_safety_v1"
MAX_BUDGET_APPLY_DELTA_PERCENT = 0.3
CAMPAIGN_BUDGET_APPLY_SAFETY_REQUIRED_VALIDATION = [
    "review_campaign_activity",
    "verify_account_currency",
    "budget_pacing",
    "change_history",
    "human_budget_goal",
    "budget_delta_limit_30_percent",
    "campaign_budget_operation_preview",
    "mutation_audit",
    "human_confirm_before_apply",
]
CAMPAIGN_BUDGET_APPLY_SAFETY_BLOCKED_CLAIMS = [
    "budget apply",
    "budget scaling",
    "campaign pause",
    "profitability",
    "wasted budget",
    "automatic budget mutation",
]


def budget_apply_safety_review(
    *,
    preview_id: str,
    current_budget_amount_micros: int | None,
    proposed_budget_amount_micros: int | None,
    proposed_budget_delta_micros: int | None,
    evidence_ids: list[str],
) -> dict[str, Any]:
    proposed_delta_percent = _proposed_delta_percent(
        current_budget_amount_micros,
        proposed_budget_delta_micros,
    )
    missing_requirements = _missing_requirements(
        current_budget_amount_micros=current_budget_amount_micros,
        proposed_budget_amount_micros=proposed_budget_amount_micros,
        proposed_delta_percent=proposed_delta_percent,
    )
    return {
        "id": f"{preview_id}_safety",
        "budget_preview_id": preview_id,
        "safety_contract": CAMPAIGN_BUDGET_APPLY_SAFETY_CONTRACT,
        "status": "blocked",
        "reason": _safety_reason(proposed_budget_amount_micros, proposed_delta_percent),
        "max_allowed_delta_percent": MAX_BUDGET_APPLY_DELTA_PERCENT,
        "current_budget_amount_micros": current_budget_amount_micros,
        "proposed_budget_amount_micros": proposed_budget_amount_micros,
        "proposed_delta_percent": proposed_delta_percent,
        "missing_requirements": missing_requirements,
        "required_validation": CAMPAIGN_BUDGET_APPLY_SAFETY_REQUIRED_VALIDATION,
        "blocked_claims": CAMPAIGN_BUDGET_APPLY_SAFETY_BLOCKED_CLAIMS,
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _proposed_delta_percent(
    current_budget_amount_micros: int | None,
    proposed_budget_delta_micros: int | None,
) -> float | None:
    if (
        current_budget_amount_micros is None
        or current_budget_amount_micros <= 0
        or proposed_budget_delta_micros is None
    ):
        return None
    return round(proposed_budget_delta_micros / current_budget_amount_micros, 6)


def _missing_requirements(
    *,
    current_budget_amount_micros: int | None,
    proposed_budget_amount_micros: int | None,
    proposed_delta_percent: float | None,
) -> list[str]:
    requirements = [
        "change_history",
        "human_budget_goal",
        "mutation_audit",
        "human_confirm_before_apply",
    ]
    if current_budget_amount_micros is None:
        requirements.append("current_budget_amount_micros")
    if proposed_budget_amount_micros is None:
        requirements.append("recommended_budget_missing")
    if proposed_delta_percent is None:
        requirements.append("budget_delta_percent")
    elif abs(proposed_delta_percent) > MAX_BUDGET_APPLY_DELTA_PERCENT:
        requirements.append("budget_delta_within_30_percent")
    return requirements


def _safety_reason(
    proposed_budget_amount_micros: int | None,
    proposed_delta_percent: float | None,
) -> str:
    if proposed_budget_amount_micros is None:
        return (
            "Budget apply zablokowany: brak proponowanej kwoty. WILQ może pokazać "
            "bieżący budżet, ale nie może przygotować mutacji bez celu operatora."
        )
    if (
        proposed_delta_percent is not None
        and abs(proposed_delta_percent) > MAX_BUDGET_APPLY_DELTA_PERCENT
    ):
        return (
            "Budget apply zablokowany: proponowana zmiana przekracza limit 30%. "
            "Wymagane są change history, cel budżetowy, audyt i potwierdzenie człowieka."
        )
    return (
        "Budget apply zablokowany: preview jest gotowe tylko do review. Apply wymaga "
        "change history, celu budżetowego, audytu mutacji i potwierdzenia człowieka."
    )
