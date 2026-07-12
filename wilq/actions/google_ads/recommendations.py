from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

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
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    MetricFact,
    OpportunityDomain,
)

RECOMMENDATION_REVIEW_ACTION_ID = "act_prepare_google_ads_recommendation_review_queue"
RECOMMENDATION_REVIEW_BLOCKED_CLAIMS = [
    "zapis rekomendacji",
    "automatyczne przyjęcie rekomendacji",
    "zmiana budżetu",
    "zapis zmian kampanii",
    "obietnica poprawy wyniku",
]

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
StateLabel = Callable[[Any], str]


def recommendation_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render recommendation review cards while hiding vendor identifiers."""
    preview_items = [item for item in payload.get("payload_preview", []) if isinstance(item, dict)]
    cards: list[ActionPreviewCardViewModel] = []
    for index, item in enumerate(preview_items[:4]):
        rows = [
            preview_row(
                "Typ rekomendacji",
                str(item.get("recommendation_type_label") or "rekomendacja do sprawdzenia"),
            ),
            preview_row(
                "Kampania",
                "powiązana kampania do sprawdzenia"
                if item.get("campaign_id")
                else "brak powiązanej kampanii",
            ),
            preview_row(
                "Budżet kampanii",
                "powiązany budżet do sprawdzenia"
                if item.get("campaign_budget_id")
                else "brak powiązanego budżetu",
            ),
        ]
        requirement_labels = string_list(item.get("required_validation_labels"))
        if requirement_labels:
            rows.append(preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
        blocked_claim_labels = string_list(item.get("blocked_claim_labels"))
        if blocked_claim_labels:
            rows.append(
                preview_row(
                    "Czego nie wolno twierdzić",
                    ", ".join(blocked_claim_labels[:4]),
                )
            )
        cards.append(
            ActionPreviewCardViewModel(
                id=str(item.get("id") or f"ads_recommendation_preview_{index}"),
                kind="google_ads_recommendation_review",
                title_label="Rekomendacja Google Ads do sprawdzenia",
                subtitle_label=str(
                    item.get("operation_type_label") or "ocena rekomendacji bez zapisu zmian"
                ),
                status_label="zapis zmian zablokowany",
                rows=rows,
                apply_state_label=apply_state_label(item.get("apply_allowed")),
                system_readiness_label=system_readiness_label(item.get("api_mutation_ready")),
            )
        )
    return cards


def seed_recommendation_review_action() -> ActionObject:
    evidence_id = connector_evidence_id("google_ads")
    return ActionObject(
        id=RECOMMENDATION_REVIEW_ACTION_ID,
        title="Przygotuj sprawdzenie rekomendacji Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=[evidence_id],
        human_diagnosis=(
            "Rekomendacje Google Ads są core workflow WILQ. WILQ utrzymuje "
            "kontrakt sprawdzenia, ale nie może akceptować ani odrzucać "
            "rekomendacji bez danych rekomendacji w WILQ."
        ),
        recommended_reason=(
            "Zbierz odczyt rekomendacji Google Ads, potem sprawdź typ "
            "rekomendacji, wpływ, powiązane kampanie i strategię przed "
            "jakimkolwiek zapisem zmian."
        ),
        payload={
            "action_type": "google_ads_recommendation_review",
            "connector": "google_ads",
            "mode": "prepare_only",
            "preview_contract": "recommendation_apply_preview_v1",
            "source_metric_names": ["connector_status"],
            "recommendations": [
                {
                    "recommendation_id": "google_ads_recommendations_read_required",
                    "recommendation_type": "read_required",
                    "campaign_id": None,
                    "review_reason": (
                        "Najpierw odśwież dane rekomendacji Google Ads; bez nich "
                        "WILQ nie ocenia wpływu ani nie przygotowuje zapisu zmian."
                    ),
                    "evidence_ids": [evidence_id],
                    "source_metric_names": ["connector_status"],
                }
            ],
            "recommendations_total": 1,
            "recommendations_included": 1,
            "payload_preview": [
                {
                    "operation_type": "ApplyRecommendationOperation",
                    "recommendation_id": "google_ads_recommendations_read_required",
                    "recommendation_type": "read_required",
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                    "destructive": False,
                    "evidence_ids": [evidence_id],
                }
            ],
            "payload_preview_total": 1,
            "payload_preview_included": 1,
            "evidence_ids": [evidence_id],
            "required_validation": RECOMMENDATION_REVIEW_REQUIRED_VALIDATION,
            "blocked_claims": RECOMMENDATION_REVIEW_BLOCKED_CLAIMS,
            "apply_allowed": False,
            "api_mutation_ready": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_seed",
    )


def recommendation_review_action(
    *,
    google_ads_facts: list[MetricFact],
    recommendation_review_payload: dict[str, Any],
) -> ActionObject:
    metric_names = set(recommendation_review_payload["source_metric_names"])
    evidence_ids = set(recommendation_review_payload["evidence_ids"])
    recommendation_ids = {
        recommendation.get("recommendation_id")
        for recommendation in recommendation_review_payload["recommendations"][:6]
        if isinstance(recommendation, dict)
    }
    metrics = [
        fact
        for fact in google_ads_facts
        if fact.name in metric_names
        and fact.evidence_id in evidence_ids
        and fact.dimensions.get("recommendation_id") in recommendation_ids
    ][:12]
    return ActionObject(
        id=RECOMMENDATION_REVIEW_ACTION_ID,
        title="Przygotuj ocenę rekomendacji Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=recommendation_review_payload["evidence_ids"],
        metrics=metrics,
        human_diagnosis=(
            "Google Ads ma aktywne fakty rekomendacji. WILQ może pokazać "
            "podgląd zmian do sprawdzenia, ale nie może akceptować "
            "rekomendacji bez strategii, oceny RMF/compliance, potwierdzenia "
            "i audytu."
        ),
        recommended_reason=(
            "W widoku Google Ads przejrzyj typ rekomendacji, podgląd wpływu i "
            "powiązane kampanie. Traktuj podgląd jako materiał do decyzji, "
            "nie zgodę na zapis zmian."
        ),
        payload=recommendation_review_payload,
        validation_status="not_validated",
        created_by="system_metric_seed",
    )


def recommendation_review_action_from_metric_facts(
    google_ads_facts: list[MetricFact],
) -> ActionObject | None:
    payload = recommendation_review_payload_from_metric_facts(google_ads_facts)
    if payload is None:
        return None
    return recommendation_review_action(
        google_ads_facts=google_ads_facts,
        recommendation_review_payload=payload,
    )
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
    subject = "Przegląd rekomendacji Google Ads"
    if not payload.get("recommendations"):
        errors.append(missing(subject, "wierszy rekomendacji"))
    if not payload.get("evidence_ids"):
        errors.append(missing_evidence(subject))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    required_validation = payload.get("required_validation")
    if not isinstance(required_validation, list):
        errors.append(missing(subject, "listy wymaganych sprawdzeń"))
    else:
        for required_check in RECOMMENDATION_REVIEW_REQUIRED_VALIDATION:
            if required_check not in required_validation:
                errors.append(missing_review_check(subject))
    preview_items = payload.get("payload_preview")
    if not isinstance(preview_items, list) or not preview_items:
        errors.append(missing(subject, "podglądu zmian"))
        return errors
    for index, item in enumerate(preview_items):
        item_subject = row("Podgląd rekomendacji Google Ads", index)
        if not isinstance(item, dict):
            errors.append(wrong(item_subject, "ma nieprawidłową strukturę"))
            continue
        if item.get("operation_type") != "ApplyRecommendationOperation":
            errors.append(wrong(item_subject, "ma nieprawidłowy typ operacji"))
        if item.get("apply_allowed") is not False:
            errors.append(no_write(item_subject))
        if item.get("destructive") is not False:
            errors.append(no_destructive_change(item_subject))
        if item.get("api_mutation_ready") is not False:
            errors.append(no_api_write(item_subject))
        if not item.get("evidence_ids"):
            errors.append(missing_evidence(item_subject))
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
        if fact.source_connector != "google_ads" or not fact.name.startswith("recommendation_"):
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
        "recommendation_resource_name": first_dimensions.get("recommendation_resource_name"),
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
        "recommendation_resource_name": first_dimensions.get("recommendation_resource_name"),
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
