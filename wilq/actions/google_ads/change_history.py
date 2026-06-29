from __future__ import annotations

from collections.abc import Iterable
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
from wilq.schemas import MetricFact

CHANGE_HISTORY_IMPACT_ACTION_ID = "act_review_ads_change_history_impact"
CHANGE_HISTORY_IMPACT_ACTION_TYPE = "google_ads_change_history_impact_review"
CHANGE_HISTORY_IMPACT_PREVIEW_CONTRACT = "change_history_impact_review_v1"
CHANGE_HISTORY_IMPACT_OPERATION_TYPE = "ChangeHistoryImpactReview"
CHANGE_HISTORY_IMPACT_REQUIRED_VALIDATION = [
    "review_change_history",
    "pre_change_performance_window",
    "post_change_performance_window",
    "human_change_impact_review",
    "business_goal_review",
    "block_apply_until_mutation_audit",
]
CHANGE_HISTORY_IMPACT_BLOCKED_CLAIMS = [
    "wpływ zmian",
    "obietnica poprawy wyniku",
    "skalowanie budżetu",
    "zmiana budżetu",
    "zapis zmian kampanii",
]


def change_history_impact_payload_from_metric_facts(
    facts: list[MetricFact],
) -> dict[str, Any] | None:
    groups = _change_history_fact_groups(facts)
    if not groups:
        return None
    previews = [
        _change_history_impact_preview(change_event_id, group_facts)
        for change_event_id, group_facts in groups.items()
    ]
    previews = sorted(
        previews,
        key=lambda preview: (
            str(preview.get("change_date_time") or ""),
            str(preview.get("change_event_id") or ""),
        ),
        reverse=True,
    )[:8]
    evidence_ids = _unique(
        evidence_id for preview in previews for evidence_id in preview.get("evidence_ids", [])
    )
    if not evidence_ids:
        return None
    return {
        "action_type": CHANGE_HISTORY_IMPACT_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "preview_contract": CHANGE_HISTORY_IMPACT_PREVIEW_CONTRACT,
        "operation_type": CHANGE_HISTORY_IMPACT_OPERATION_TYPE,
        "change_history_preview": previews,
        "source_metric_names": _unique(
            metric_name
            for preview in previews
            for metric_name in preview.get("source_metric_names", [])
        ),
        "evidence_ids": evidence_ids,
        "missing_read_contracts": [
            "pre_change_performance_window",
            "post_change_performance_window",
            "human_change_impact_review",
            "apply_preview",
        ],
        "required_validation": CHANGE_HISTORY_IMPACT_REQUIRED_VALIDATION,
        "blocked_claims": CHANGE_HISTORY_IMPACT_BLOCKED_CLAIMS,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def validate_change_history_impact_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Przegląd wpływu zmian w Google Ads"
    if not payload.get("evidence_ids"):
        errors.append(missing_evidence(subject))
    if payload.get("preview_contract") != CHANGE_HISTORY_IMPACT_PREVIEW_CONTRACT:
        errors.append(missing(subject, "poprawnego kontraktu podglądu"))
    if payload.get("operation_type") != CHANGE_HISTORY_IMPACT_OPERATION_TYPE:
        errors.append(missing(subject, "poprawnego typu operacji"))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    if payload.get("api_mutation_ready") is not False:
        errors.append(no_api_write(subject))
    required_validation = payload.get("required_validation")
    if not isinstance(required_validation, list):
        errors.append(missing(subject, "listy wymaganych sprawdzeń"))
    else:
        for required_check in CHANGE_HISTORY_IMPACT_REQUIRED_VALIDATION:
            if required_check not in required_validation:
                errors.append(missing_review_check(subject))
    previews = payload.get("change_history_preview")
    if not isinstance(previews, list) or not previews:
        errors.append(missing(subject, "podglądu historii zmian"))
        return errors
    for index, preview in enumerate(previews):
        preview_subject = row("Podgląd historii zmian", index)
        if not isinstance(preview, dict):
            errors.append(wrong(preview_subject, "ma nieprawidłową strukturę"))
            continue
        if preview.get("operation_type") != CHANGE_HISTORY_IMPACT_OPERATION_TYPE:
            errors.append(missing(preview_subject, "poprawnego typu operacji"))
        if not preview.get("change_event_id"):
            errors.append(missing(preview_subject, "identyfikatora zmiany"))
        if not preview.get("evidence_ids"):
            errors.append(missing_evidence(preview_subject))
        if preview.get("api_mutation_ready") is not False:
            errors.append(no_api_write(preview_subject))
        if preview.get("apply_allowed") is not False:
            errors.append(no_write(preview_subject))
        if preview.get("destructive") is not False:
            errors.append(no_destructive_change(preview_subject))
    return errors


def _change_history_fact_groups(facts: list[MetricFact]) -> dict[str, list[MetricFact]]:
    grouped: dict[str, list[MetricFact]] = {}
    for fact in facts:
        if fact.source_connector != "google_ads" or fact.name not in {
            "change_event_available",
            "change_event_changed_field_count",
        }:
            continue
        change_event_id = fact.dimensions.get("change_event_id")
        if not change_event_id:
            continue
        grouped.setdefault(change_event_id, []).append(fact)
    return grouped


def _change_history_impact_preview(
    change_event_id: str,
    facts: list[MetricFact],
) -> dict[str, Any]:
    dimensions = facts[0].dimensions if facts else {}
    changed_fields = [
        field.strip() for field in dimensions.get("changed_fields", "").split(",") if field.strip()
    ]
    return {
        "id": f"change_history_impact_preview_{_slug(change_event_id)}",
        "change_event_id": change_event_id,
        "change_date_time": dimensions.get("change_date_time"),
        "change_resource_id": dimensions.get("change_resource_id"),
        "change_resource_type": dimensions.get("change_resource_type"),
        "resource_change_operation": dimensions.get("resource_change_operation"),
        "client_type": dimensions.get("client_type"),
        "campaign_id": dimensions.get("campaign_id"),
        "changed_fields": changed_fields,
        "operation_type": CHANGE_HISTORY_IMPACT_OPERATION_TYPE,
        "reason": (
            "Do sprawdzenia: podgląd wpływu historii zmian. WILQ nie może "
            "twierdzić wpływu zmiany bez okna wyników przed/po i ręcznej oceny."
        ),
        "missing_read_contracts": [
            "pre_change_performance_window",
            "post_change_performance_window",
            "human_change_impact_review",
        ],
        "required_validation": CHANGE_HISTORY_IMPACT_REQUIRED_VALIDATION,
        "blocked_claims": CHANGE_HISTORY_IMPACT_BLOCKED_CLAIMS,
        "source_metric_names": _unique(fact.name for fact in facts),
        "evidence_ids": _unique(fact.evidence_id for fact in facts),
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")


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
