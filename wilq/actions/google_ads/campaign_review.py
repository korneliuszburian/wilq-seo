from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.actions.google_ads.budget_safety import budget_apply_safety_review
from wilq.actions.google_ads.business_context import (
    ADS_TARGET_CPA_MICROS_ENV,
    ADS_TARGET_ROAS_ENV,
    ads_float_env,
    ads_int_env,
)
from wilq.actions.google_ads.campaign_triage import (
    campaign_review_gates,
    campaign_review_priority,
    campaign_review_reason,
    campaign_review_score,
    campaign_target_context,
)
from wilq.actions.validation_copy import (
    missing,
    missing_evidence,
    missing_review_check,
    no_api_write,
    no_destructive_change,
    no_write,
    row,
    wrong,
)
from wilq.schemas import MetricFact

CAMPAIGN_REVIEW_ACTION_ID = "act_prepare_ads_campaign_review_queue"
CAMPAIGN_REVIEW_BLOCKED_CLAIMS = [
    "skalowanie budżetu",
    "zmiana budżetu",
    "wstrzymanie kampanii",
    "zmarnowany budżet",
    "opłacalność",
    "werdykt kosztu pozyskania celu",
    "werdykt zwrotu z reklam",
    "zapis rekomendacji",
]
CAMPAIGN_BUDGET_APPLY_PREVIEW_REQUIRED_VALIDATION = [
    "review_campaign_activity",
    "verify_account_currency",
    "budget_pacing",
    "impression_share",
    "change_history",
    "human_budget_goal",
    "campaign_budget_apply_safety",
    "campaign_budget_operation_preview",
    "human_confirm_before_apply",
]
CAMPAIGN_REVIEW_REQUIRED_VALIDATION = [
    "review_campaign_activity",
    "verify_account_currency",
    "budget_pacing",
    "budget_apply_preview",
    "campaign_budget_apply_safety",
    "impression_share",
    "change_history",
    "recommendations",
    "profit_margin_or_value_model",
    "human_confirm_before_apply",
]


def validate_campaign_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Przegląd kampanii Google Ads"
    if not payload.get("campaign_candidates"):
        errors.append(missing(subject, "kampanii do sprawdzenia opartych na dowodach"))
    for index, candidate in enumerate(payload.get("campaign_candidates", [])):
        candidate_subject = row("Kampania do sprawdzenia", index)
        if not isinstance(candidate, dict):
            errors.append(wrong(candidate_subject, "ma nieprawidłową strukturę"))
            continue
        for key in (
            "review_priority",
            "review_score",
            "review_reason",
            "human_review_gates",
            "target_context",
        ):
            if key not in candidate:
                errors.append(missing(candidate_subject, "kompletu informacji do decyzji"))
        if not isinstance(candidate.get("human_review_gates"), list):
            errors.append(missing(candidate_subject, "listy sprawdzeń człowieka"))
        if not isinstance(candidate.get("target_context"), dict):
            errors.append(missing(candidate_subject, "kontekstu celu kampanii"))
    if not payload.get("evidence_ids"):
        errors.append(missing_evidence(subject))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    required_validation = payload.get("required_validation")
    if not isinstance(required_validation, list):
        errors.append(missing(subject, "listy wymaganych sprawdzeń"))
        return errors
    for required_check in CAMPAIGN_REVIEW_REQUIRED_VALIDATION:
        if required_check not in required_validation:
            errors.append(missing_review_check(subject))
    preview_items = payload.get("budget_payload_preview")
    if not isinstance(preview_items, list):
        errors.append(missing(subject, "podglądu zmian budżetu"))
        return errors
    candidates_with_budget = [
        candidate
        for candidate in payload.get("campaign_candidates", [])
        if isinstance(candidate, dict)
        and isinstance(candidate.get("budget_context"), dict)
        and candidate["budget_context"].get("budget_amount_micros") is not None
    ]
    if candidates_with_budget and not preview_items:
        errors.append(missing(subject, "podglądu budżetu dla kampanii z danymi budżetowymi"))
    for index, item in enumerate(preview_items):
        item_subject = row("Podgląd zmiany budżetu", index)
        if not isinstance(item, dict):
            errors.append(wrong(item_subject, "ma nieprawidłową strukturę"))
            continue
        if item.get("operation_type") != "CampaignBudgetOperation":
            errors.append(wrong(item_subject, "ma nieprawidłowy typ operacji"))
        if item.get("apply_allowed") is not False:
            errors.append(no_write(item_subject))
        if item.get("destructive") is not False:
            errors.append(no_destructive_change(item_subject))
        if item.get("api_mutation_ready") is not False:
            errors.append(no_api_write(item_subject))
        if not item.get("evidence_ids"):
            errors.append(missing_evidence(item_subject))
        safety_review = item.get("safety_review")
        if not isinstance(safety_review, dict):
            errors.append(missing(item_subject, "sprawdzenia bezpieczeństwa budżetu"))
            continue
        if safety_review.get("safety_contract") != "campaign_budget_apply_safety_v1":
            errors.append(missing(item_subject, "poprawnego sprawdzenia bezpieczeństwa budżetu"))
        if safety_review.get("apply_allowed") is not False:
            errors.append(no_write(f"{item_subject}, sprawdzenie bezpieczeństwa"))
        if safety_review.get("api_mutation_ready") is not False:
            errors.append(no_api_write(f"{item_subject}, sprawdzenie bezpieczeństwa"))
        if safety_review.get("destructive") is not False:
            errors.append(no_destructive_change(f"{item_subject}, sprawdzenie bezpieczeństwa"))
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
        evidence_id for candidate in candidates for evidence_id in candidate.get("evidence_ids", [])
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
    has_recommended_budget = _bool_metric_value(facts_by_name.get("budget_has_recommended_budget"))
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
    target_roas, _target_roas_source = ads_float_env(ADS_TARGET_ROAS_ENV)
    target_cpa_micros, _target_cpa_source = ads_int_env(ADS_TARGET_CPA_MICROS_ENV)
    target_context = campaign_target_context(
        cost_micros=cost_micros,
        conversions=conversions,
        conversion_value=conversion_value,
        target_roas=target_roas,
        target_cpa_micros=target_cpa_micros,
    )
    review_score = campaign_review_score(
        campaign_name=campaign_name,
        advertising_channel_type=advertising_channel_type,
        clicks=clicks,
        impressions=impressions,
        cost_micros=cost_micros,
        conversions=conversions,
        missing_metrics=missing_metrics,
        target_status=target_context["target_status"],
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
            target_status=target_context["target_status"],
            target_status_label=target_context["target_status_label"],
        ),
        "human_review_gates": campaign_review_gates(
            campaign_name=campaign_name,
            advertising_channel_type=advertising_channel_type,
            cost_micros=cost_micros,
            conversions=conversions,
            target_status=target_context["target_status"],
        ),
        "target_context": target_context,
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
        "Podgląd budżetu z rekomendacji Google do sprawdzenia. "
        "WILQ nie może zmienić budżetu bez celu budżetowego, przeglądu strategii, "
        "potwierdzenia człowieka i audytu."
        if proposed_budget_amount_micros is not None
        else (
            "Podgląd budżetu do sprawdzenia. Google Ads nie zwrócił "
            "recommended budget, więc WILQ pokazuje bieżący budżet i blokuje "
            "propozycję kwoty do czasu human_budget_goal."
        )
    )
    preview_id = (
        f"budget_apply_preview_{_slug(campaign_id or campaign_name)}_"
        f"{_slug(budget_id or budget_name or 'budget')}"
    )
    return {
        "id": preview_id,
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
        "safety_review": budget_apply_safety_review(
            preview_id=preview_id,
            current_budget_amount_micros=budget_amount_micros,
            proposed_budget_amount_micros=proposed_budget_amount_micros,
            proposed_budget_delta_micros=proposed_budget_delta_micros,
            evidence_ids=evidence_ids,
        ),
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
