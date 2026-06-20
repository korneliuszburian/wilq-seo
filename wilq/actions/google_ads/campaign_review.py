from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.actions.google_ads.campaign_triage import (
    campaign_review_gates,
    campaign_review_priority,
    campaign_review_reason,
    campaign_review_score,
)
from wilq.schemas import MetricFact

CAMPAIGN_REVIEW_ACTION_ID = "act_prepare_ads_campaign_review_queue"
CAMPAIGN_REVIEW_BLOCKED_CLAIMS = [
    "budget scaling",
    "budget apply",
    "campaign pause",
    "wasted budget",
    "profitability",
    "CPA verdict",
    "ROAS verdict",
    "recommendation apply",
]
CAMPAIGN_BUDGET_APPLY_PREVIEW_REQUIRED_VALIDATION = [
    "review_campaign_activity",
    "verify_account_currency",
    "budget_pacing",
    "impression_share",
    "change_history",
    "human_budget_goal",
    "campaign_budget_operation_preview",
    "human_confirm_before_apply",
]
CAMPAIGN_REVIEW_REQUIRED_VALIDATION = [
    "review_campaign_activity",
    "verify_account_currency",
    "budget_pacing",
    "budget_apply_preview",
    "impression_share",
    "change_history",
    "recommendations",
    "profit_margin_or_value_model",
    "human_confirm_before_apply",
]


def validate_campaign_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not payload.get("campaign_candidates"):
        errors.append("Campaign review payload requires evidence-backed campaign candidates.")
    for index, candidate in enumerate(payload.get("campaign_candidates", [])):
        if not isinstance(candidate, dict):
            errors.append(f"Campaign candidate {index} must be object.")
            continue
        for key in ("review_priority", "review_score", "review_reason", "human_review_gates"):
            if key not in candidate:
                errors.append(f"Campaign candidate {index} requires {key}.")
        if not isinstance(candidate.get("human_review_gates"), list):
            errors.append(f"Campaign candidate {index} requires human_review_gates list.")
    if not payload.get("evidence_ids"):
        errors.append("Campaign review payload requires evidence IDs.")
    if payload.get("apply_allowed") is not False:
        errors.append("Campaign review payload must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("Campaign review payload must be non-destructive.")
    required_validation = payload.get("required_validation")
    if not isinstance(required_validation, list):
        errors.append("Campaign review payload requires required_validation list.")
        return errors
    for required_check in CAMPAIGN_REVIEW_REQUIRED_VALIDATION:
        if required_check not in required_validation:
            errors.append(f"Campaign review payload requires {required_check}.")
    preview_items = payload.get("budget_payload_preview")
    if not isinstance(preview_items, list):
        errors.append("Campaign review payload requires budget_payload_preview list.")
        return errors
    candidates_with_budget = [
        candidate
        for candidate in payload.get("campaign_candidates", [])
        if isinstance(candidate, dict)
        and isinstance(candidate.get("budget_context"), dict)
        and candidate["budget_context"].get("budget_amount_micros") is not None
    ]
    if candidates_with_budget and not preview_items:
        errors.append("Campaign review payload requires budget preview for budget facts.")
    for index, item in enumerate(preview_items):
        if not isinstance(item, dict):
            errors.append(f"Budget payload preview item {index} must be object.")
            continue
        if item.get("operation_type") != "CampaignBudgetOperation":
            errors.append(
                f"Budget payload preview item {index} must use CampaignBudgetOperation."
            )
        if item.get("apply_allowed") is not False:
            errors.append(f"Budget payload preview item {index} must keep apply_allowed=false.")
        if item.get("destructive") is not False:
            errors.append(f"Budget payload preview item {index} must be non-destructive.")
        if item.get("api_mutation_ready") is not False:
            errors.append(
                f"Budget payload preview item {index} must not be API-mutation ready."
            )
        if not item.get("evidence_ids"):
            errors.append(f"Budget payload preview item {index} requires evidence IDs.")
    return errors


def campaign_review_payload_from_metric_facts(
    facts: list[MetricFact],
) -> dict[str, Any] | None:
    campaign_groups = _campaign_fact_groups(facts)
    if not campaign_groups:
        return None
    candidates = [
        _campaign_candidate(campaign_id, campaign_name, group_facts)
        for (campaign_id, campaign_name), group_facts in campaign_groups.items()
    ]
    candidates = sorted(
        candidates,
        key=lambda candidate: (
            -int(candidate.get("review_score") or 0),
            -int(candidate.get("cost_micros") or 0),
            -int(candidate.get("clicks") or 0),
            str(candidate["campaign_name"]),
        ),
    )[:8]
    evidence_ids = _unique(
        evidence_id
        for candidate in candidates
        for evidence_id in candidate.get("evidence_ids", [])
    )
    if not evidence_ids:
        return None
    source_metric_names = _unique(
        metric_name
        for candidate in candidates
        for metric_name in candidate.get("source_metric_names", [])
    )
    budget_payload_preview = [
        candidate["budget_payload_preview"]
        for candidate in candidates
        if isinstance(candidate.get("budget_payload_preview"), dict)
    ]
    return {
        "action_type": "campaign_change_review",
        "connector": "google_ads",
        "mode": "prepare_only",
        "campaign_candidates": candidates,
        "preview_contract": "budget_apply_preview_v1",
        "budget_payload_preview": budget_payload_preview,
        "source_metric_names": source_metric_names,
        "evidence_ids": evidence_ids,
        "required_validation": CAMPAIGN_REVIEW_REQUIRED_VALIDATION,
        "missing_read_contracts": [
            "profit_margin_or_value_model",
            "budget_target_or_seasonality",
            "human_budget_goal",
            "campaign_budget_apply_safety",
            "mutation_audit",
        ],
        "blocked_claims": CAMPAIGN_REVIEW_BLOCKED_CLAIMS,
        "apply_allowed": False,
        "destructive": False,
    }


def _campaign_fact_groups(
    facts: list[MetricFact],
) -> dict[tuple[str | None, str], list[MetricFact]]:
    grouped: dict[tuple[str | None, str], list[MetricFact]] = {}
    for fact in facts:
        if fact.source_connector != "google_ads" or fact.name not in {
            "clicks",
            "impressions",
            "cost_micros",
            "conversions",
            "conversion_value",
            "budget_amount_micros",
            "budget_has_recommended_budget",
            "budget_recommended_amount_micros",
        }:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name")
        if not campaign_id and not campaign_name:
            continue
        grouped.setdefault((campaign_id, campaign_name or f"campaign {campaign_id}"), []).append(
            fact
        )
    return grouped


def _campaign_candidate(
    campaign_id: str | None,
    campaign_name: str,
    facts: list[MetricFact],
) -> dict[str, Any]:
    facts_by_name = {fact.name: fact for fact in facts}
    clicks = _int_metric_value(facts_by_name.get("clicks"))
    impressions = _int_metric_value(facts_by_name.get("impressions"))
    cost_micros = _int_metric_value(facts_by_name.get("cost_micros"))
    conversions = _float_metric_value(facts_by_name.get("conversions"))
    conversion_value = _float_metric_value(facts_by_name.get("conversion_value"))
    dimensions = _campaign_dimensions(facts)
    advertising_channel_type = dimensions.get("advertising_channel_type")
    campaign_status = dimensions.get("campaign_status")
    budget_amount_micros = _int_metric_value(facts_by_name.get("budget_amount_micros"))
    has_recommended_budget = _bool_metric_value(
        facts_by_name.get("budget_has_recommended_budget")
    )
    recommended_budget_amount_micros = _int_metric_value(
        facts_by_name.get("budget_recommended_amount_micros")
    )
    source_metric_names = _unique(fact.name for fact in facts)
    evidence_ids = _unique(fact.evidence_id for fact in facts)
    expected_metrics = [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    missing_metrics = [name for name in expected_metrics if name not in facts_by_name]
    review_score = campaign_review_score(
        campaign_name=campaign_name,
        advertising_channel_type=advertising_channel_type,
        clicks=clicks,
        impressions=impressions,
        cost_micros=cost_micros,
        conversions=conversions,
        missing_metrics=missing_metrics,
    )
    budget_dimensions = _budget_dimensions(facts)
    budget_payload_preview = _budget_payload_preview(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        budget_id=budget_dimensions.get("budget_id"),
        budget_name=budget_dimensions.get("budget_name"),
        budget_amount_micros=budget_amount_micros,
        has_recommended_budget=has_recommended_budget,
        recommended_budget_amount_micros=recommended_budget_amount_micros,
        source_metric_names=source_metric_names,
        evidence_ids=evidence_ids,
    )
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "campaign_status": campaign_status,
        "advertising_channel_type": advertising_channel_type,
        "review_priority": campaign_review_priority(review_score),
        "review_score": review_score,
        "review_reason": campaign_review_reason(
            campaign_name=campaign_name,
            advertising_channel_type=advertising_channel_type,
            clicks=clicks,
            impressions=impressions,
            cost_micros=cost_micros,
            conversions=conversions,
            missing_metrics=missing_metrics,
        ),
        "human_review_gates": campaign_review_gates(
            campaign_name=campaign_name,
            advertising_channel_type=advertising_channel_type,
            cost_micros=cost_micros,
            conversions=conversions,
        ),
        "clicks": clicks,
        "impressions": impressions,
        "cost_micros": cost_micros,
        "conversions": conversions,
        "conversion_value": conversion_value,
        "derived_kpis": {
            "ctr": _ratio(clicks, impressions),
            "average_cpc_micros": _ratio(cost_micros, clicks),
            "conversion_rate": _ratio(conversions, clicks),
            "cost_per_conversion_micros": _ratio(cost_micros, conversions),
            "roas": _ratio(conversion_value, _micros_to_account_units(cost_micros)),
            "value_per_conversion": _ratio(conversion_value, conversions),
        },
        "budget_context": {
            "budget_amount_micros": budget_amount_micros,
            "cost_micros_7d": cost_micros,
            "seven_day_budget_micros": budget_amount_micros * 7
            if budget_amount_micros is not None
            else None,
            "spend_to_budget_ratio_7d": _ratio(
                cost_micros,
                budget_amount_micros * 7 if budget_amount_micros is not None else None,
            ),
            "has_recommended_budget": has_recommended_budget,
            "recommended_budget_amount_micros": recommended_budget_amount_micros,
        },
        "budget_payload_preview": budget_payload_preview,
        "source_metric_names": source_metric_names,
        "evidence_ids": evidence_ids,
        "missing_metrics": missing_metrics,
        "required_checks": CAMPAIGN_REVIEW_REQUIRED_VALIDATION,
        "blocked_claims": CAMPAIGN_REVIEW_BLOCKED_CLAIMS,
        "apply_allowed": False,
    }


def _budget_payload_preview(
    *,
    campaign_id: str | None,
    campaign_name: str,
    budget_id: str | None,
    budget_name: str | None,
    budget_amount_micros: int | None,
    has_recommended_budget: bool | None,
    recommended_budget_amount_micros: int | None,
    source_metric_names: list[str],
    evidence_ids: list[str],
) -> dict[str, Any]:
    proposed_budget_amount_micros = (
        recommended_budget_amount_micros
        if has_recommended_budget and recommended_budget_amount_micros is not None
        else None
    )
    proposed_budget_delta_micros = (
        proposed_budget_amount_micros - budget_amount_micros
        if proposed_budget_amount_micros is not None and budget_amount_micros is not None
        else None
    )
    reason = (
        "Review-only podgląd CampaignBudgetOperation z Google recommended budget. "
        "WILQ nie może zmienić budżetu bez celu budżetowego, review strategii, "
        "potwierdzenia człowieka i audytu."
        if proposed_budget_amount_micros is not None
        else (
            "Review-only podgląd CampaignBudgetOperation. Google Ads nie zwrócił "
            "recommended budget, więc WILQ pokazuje bieżący budżet i blokuje "
            "propozycję kwoty do czasu human_budget_goal."
        )
    )
    return {
        "id": (
            f"budget_apply_preview_{_slug(campaign_id or campaign_name)}_"
            f"{_slug(budget_id or budget_name or 'budget')}"
        ),
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "campaign_budget_id": budget_id,
        "campaign_budget_name": budget_name,
        "operation_type": "CampaignBudgetOperation",
        "current_budget_amount_micros": budget_amount_micros,
        "proposed_budget_amount_micros": proposed_budget_amount_micros,
        "proposed_budget_delta_micros": proposed_budget_delta_micros,
        "reason": reason,
        "evidence_ids": evidence_ids,
        "source_metric_names": source_metric_names,
        "required_validation": CAMPAIGN_BUDGET_APPLY_PREVIEW_REQUIRED_VALIDATION,
        "blocked_claims": CAMPAIGN_REVIEW_BLOCKED_CLAIMS,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _budget_dimensions(facts: list[MetricFact]) -> dict[str, str]:
    return next(
        (fact.dimensions for fact in facts if fact.dimensions.get("budget_id")),
        facts[0].dimensions if facts else {},
    )


def _campaign_dimensions(facts: list[MetricFact]) -> dict[str, str]:
    return next(
        (
            fact.dimensions
            for fact in facts
            if fact.dimensions.get("advertising_channel_type")
            or fact.dimensions.get("campaign_status")
        ),
        facts[0].dimensions if facts else {},
    )


def _int_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        try:
            return int(float(fact.value))
        except ValueError:
            return None
    return int(fact.value)


def _float_metric_value(fact: MetricFact | None) -> float | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        try:
            return float(fact.value)
        except ValueError:
            return None
    return float(fact.value)


def _bool_metric_value(fact: MetricFact | None) -> bool | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        return fact.value.lower() in {"1", "true", "yes"}
    return bool(fact.value)


def _ratio(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _micros_to_account_units(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value) / 1_000_000


def _unique(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def _slug(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_")[:80] or "unknown"
