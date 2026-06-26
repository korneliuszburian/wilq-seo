from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.schemas import MetricFact

RECOMMENDATION_REVIEW_ACTION_ID = "act_prepare_google_ads_recommendation_review_queue"
RECOMMENDATION_REVIEW_BLOCKED_CLAIMS = [
    "zapis rekomendacji",
    "automatic recommendation accept",
    "zmiana budżetu",
    "campaign mutation",
    "performance uplift",
]
RECOMMENDATION_REVIEW_REQUIRED_VALIDATION = [
    "review_recommendation_type",
    "review_impact_metrics",
    "review_change_history",
    "review_business_goal",
    "recommendation_apply_preview",
    "google_ads_rmf_compliance_review",
    "human_confirm_before_apply",
]


def validate_recommendation_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not payload.get("recommendations"):
        errors.append("Recommendation review payload requires recommendation rows.")
    if not payload.get("evidence_ids"):
        errors.append("Recommendation review payload requires evidence IDs.")
    if payload.get("apply_allowed") is not False:
        errors.append("Recommendation review payload must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("Recommendation review payload must be non-destructive.")
    required_validation = payload.get("required_validation")
    if not isinstance(required_validation, list):
        errors.append("Recommendation review payload requires required_validation list.")
    else:
        for required_check in RECOMMENDATION_REVIEW_REQUIRED_VALIDATION:
            if required_check not in required_validation:
                errors.append(f"Recommendation review payload requires {required_check}.")
    preview_items = payload.get("payload_preview")
    if not isinstance(preview_items, list) or not preview_items:
        errors.append("Recommendation review payload requires payload_preview.")
        return errors
    for index, item in enumerate(preview_items):
        if not isinstance(item, dict):
            errors.append(f"Recommendation podgląd zmian item {index} must be object.")
            continue
        if item.get("operation_type") != "ApplyRecommendationOperation":
            errors.append(
                f"Recommendation podgląd zmian item {index} must use "
                "ApplyRecommendationOperation."
            )
        if item.get("apply_allowed") is not False:
            errors.append(
                f"Recommendation podgląd zmian item {index} must keep apply_allowed=false."
            )
        if item.get("destructive") is not False:
            errors.append(
                f"Recommendation podgląd zmian item {index} must be non-destructive."
            )
        if item.get("api_mutation_ready") is not False:
            errors.append(
                f"Recommendation podgląd zmian item {index} must not be API-mutation ready."
            )
        if not item.get("evidence_ids"):
            errors.append(f"Recommendation podgląd zmian item {index} requires evidence IDs.")
    return errors


def recommendation_review_payload_from_metric_facts(
    facts: list[MetricFact],
) -> dict[str, Any] | None:
    groups = _recommendation_fact_groups(facts)
    if not groups:
        return None
    recommendations = [
        _recommendation_candidate(recommendation_id, recommendation_type, group_facts)
        for (recommendation_id, recommendation_type), group_facts in groups.items()
    ]
    recommendations = sorted(
        recommendations,
        key=lambda recommendation: (
            recommendation["recommendation_type"],
            recommendation.get("campaign_id") or "",
            recommendation.get("recommendation_id") or "",
        ),
    )[:12]
    evidence_ids = _unique(
        evidence_id
        for recommendation in recommendations
        for evidence_id in recommendation.get("evidence_ids", [])
    )
    if not evidence_ids:
        return None
    payload_preview = [
        recommendation["payload_preview"]
        for recommendation in recommendations
        if isinstance(recommendation.get("payload_preview"), dict)
    ]
    if not payload_preview:
        return None
    return {
        "action_type": "google_ads_recommendation_review",
        "connector": "google_ads",
        "mode": "prepare_only",
        "recommendations": recommendations,
        "preview_contract": "recommendation_apply_preview_v1",
        "payload_preview": payload_preview,
        "source_metric_names": _unique(
            metric_name
            for recommendation in recommendations
            for metric_name in recommendation.get("source_metric_names", [])
        ),
        "evidence_ids": evidence_ids,
        "required_validation": RECOMMENDATION_REVIEW_REQUIRED_VALIDATION,
        "blocked_claims": RECOMMENDATION_REVIEW_BLOCKED_CLAIMS,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _recommendation_fact_groups(
    facts: list[MetricFact],
) -> dict[tuple[str | None, str], list[MetricFact]]:
    grouped: dict[tuple[str | None, str], list[MetricFact]] = {}
    for fact in facts:
        if fact.source_connector != "google_ads" or not fact.name.startswith(
            "recommendation_"
        ):
            continue
        recommendation_type = fact.dimensions.get("recommendation_type")
        recommendation_id = fact.dimensions.get("recommendation_id")
        if not recommendation_type and not recommendation_id:
            continue
        grouped.setdefault(
            (recommendation_id, recommendation_type or f"recommendation {recommendation_id}"),
            [],
        ).append(fact)
    return grouped


def _recommendation_candidate(
    recommendation_id: str | None,
    recommendation_type: str,
    facts: list[MetricFact],
) -> dict[str, Any]:
    first_dimensions = facts[0].dimensions if facts else {}
    source_metric_names = _unique(fact.name for fact in facts)
    evidence_ids = _unique(fact.evidence_id for fact in facts)
    payload_preview = {
        "id": f"recommendation_apply_preview_{recommendation_id or recommendation_type}",
        "recommendation_id": recommendation_id,
        "recommendation_resource_name": first_dimensions.get(
            "recommendation_resource_name"
        ),
        "recommendation_type": recommendation_type,
        "campaign_id": first_dimensions.get("campaign_id"),
        "campaign_budget_id": first_dimensions.get("campaign_budget_id"),
        "operation_type": "ApplyRecommendationOperation",
        "reason": (
            "Podgląd zmian dla rekomendacji Google Ads jest do sprawdzenia w WILQ. "
            "WILQ nie może zapisać tej zmiany bez oceny strategii, sprawdzenia "
            "zgodności z RMF, potwierdzenia człowieka i audytu."
        ),
        "evidence_ids": evidence_ids,
        "source_metric_names": source_metric_names,
        "required_validation": RECOMMENDATION_REVIEW_REQUIRED_VALIDATION,
        "blocked_claims": RECOMMENDATION_REVIEW_BLOCKED_CLAIMS,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }
    return {
        "id": recommendation_id or recommendation_type,
        "recommendation_id": recommendation_id,
        "recommendation_resource_name": first_dimensions.get(
            "recommendation_resource_name"
        ),
        "recommendation_type": recommendation_type,
        "campaign_id": first_dimensions.get("campaign_id"),
        "campaign_budget_id": first_dimensions.get("campaign_budget_id"),
        "source_metric_names": source_metric_names,
        "evidence_ids": evidence_ids,
        "payload_preview": payload_preview,
        "blocked_claims": RECOMMENDATION_REVIEW_BLOCKED_CLAIMS,
        "required_validation": RECOMMENDATION_REVIEW_REQUIRED_VALIDATION,
    }


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
