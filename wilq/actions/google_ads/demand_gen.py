from __future__ import annotations

from collections.abc import Iterable
from typing import Any

DEMAND_GEN_READINESS_REVIEW_ACTION_ID = "act_review_demand_gen_readiness"
DEMAND_GEN_READINESS_REVIEW_ACTION_TYPE = "google_ads_demand_gen_readiness_review"
DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT = "demand_gen_readiness_review_preview_v1"
DEMAND_GEN_READINESS_REVIEW_OPERATION_TYPE = "DemandGenReadinessReview"
DEMAND_GEN_READINESS_AVAILABLE_CONTRACT = "demand_gen_readiness_review_action_object"
DEMAND_GEN_READINESS_REQUIRED_VALIDATION = [
    "review_ads_campaign_channel_context",
    "review_ga4_landing_source_campaign_context",
    "review_demand_gen_missing_contracts",
    "human_strategy_review",
    "human_confirm_before_apply",
]
DEMAND_GEN_READINESS_BLOCKED_CLAIMS = [
    "Demand Gen launch recommendation",
    "Demand Gen migration ready",
    "creative quality verdict",
    "asset performance verdict",
    "campaign apply",
    "performance uplift",
]


def demand_gen_readiness_review_payload(
    *,
    campaign_rows_evaluated: int,
    campaign_channel_counts: dict[str, int],
    demand_gen_campaign_rows: list[dict[str, Any]],
    available_read_contracts: list[str],
    missing_read_contracts: list[str],
    source_connectors: list[str],
    evidence_ids: list[str],
) -> dict[str, Any] | None:
    if not evidence_ids:
        return None
    preview = {
        "id": "demand_gen_readiness_review",
        "preview_contract": DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT,
        "operation_type": DEMAND_GEN_READINESS_REVIEW_OPERATION_TYPE,
        "campaign_rows_evaluated": campaign_rows_evaluated,
        "campaign_channel_counts": campaign_channel_counts,
        "demand_gen_campaign_row_count": len(demand_gen_campaign_rows),
        "demand_gen_campaign_rows": demand_gen_campaign_rows[:4],
        "available_read_contracts": available_read_contracts,
        "missing_read_contracts": missing_read_contracts,
        "reason": (
            "Review-only podgląd gotowości Demand Gen. WILQ może pokazać kontekst "
            "kanałów kampanii Ads i GA4, ale nadal blokuje launch, migrację, "
            "werdykty kreatywne i apply bez osobnych kontraktów assetów, kreacji, "
            "landing quality i migration constraints."
        ),
        "required_validation": DEMAND_GEN_READINESS_REQUIRED_VALIDATION,
        "blocked_claims": DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
        "evidence_ids": evidence_ids,
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }
    return {
        "action_type": DEMAND_GEN_READINESS_REVIEW_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "source_connectors": source_connectors,
        "evidence_ids": evidence_ids,
        "available_read_contracts": available_read_contracts,
        "missing_read_contracts": missing_read_contracts,
        "required_validation": DEMAND_GEN_READINESS_REQUIRED_VALIDATION,
        "blocked_claims": DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
        "preview_contract": DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT,
        "payload_preview": [preview],
        "api_mutation_ready": False,
        "apply_allowed": False,
        "destructive": False,
    }


def validate_demand_gen_readiness_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("connector") != "google_ads":
        errors.append("Demand Gen readiness review requires connector=google_ads.")
    if payload.get("mode") != "prepare_only":
        errors.append("Demand Gen readiness review requires mode=prepare_only.")
    if payload.get("preview_contract") != DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT:
        errors.append("Demand Gen readiness review requires preview contract.")
    if payload.get("api_mutation_ready") is not False:
        errors.append("Demand Gen readiness review must not be API-mutation ready.")
    if payload.get("apply_allowed") is not False:
        errors.append("Demand Gen readiness review must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("Demand Gen readiness review must be non-destructive.")
    if not isinstance(payload.get("source_connectors"), list):
        errors.append("Demand Gen readiness review requires source_connectors list.")
    if not isinstance(payload.get("evidence_ids"), list) or not payload.get("evidence_ids"):
        errors.append("Demand Gen readiness review requires evidence IDs.")
    if not isinstance(payload.get("available_read_contracts"), list):
        errors.append("Demand Gen readiness review requires available_read_contracts list.")
    if not isinstance(payload.get("missing_read_contracts"), list):
        errors.append("Demand Gen readiness review requires missing_read_contracts list.")
    required_validation = payload.get("required_validation")
    if not isinstance(required_validation, list):
        errors.append("Demand Gen readiness review requires required_validation list.")
    else:
        for required_check in DEMAND_GEN_READINESS_REQUIRED_VALIDATION:
            if required_check not in required_validation:
                errors.append(f"Demand Gen readiness review requires {required_check}.")
    blocked_claims = payload.get("blocked_claims")
    if not isinstance(blocked_claims, list):
        errors.append("Demand Gen readiness review requires blocked_claims list.")
    else:
        for claim in DEMAND_GEN_READINESS_BLOCKED_CLAIMS:
            if claim not in blocked_claims:
                errors.append(f"Demand Gen readiness review must block {claim}.")
    previews = payload.get("payload_preview")
    if not isinstance(previews, list) or not previews:
        errors.append("Demand Gen readiness review requires payload_preview list.")
        return errors
    for index, preview in enumerate(previews):
        if not isinstance(preview, dict):
            errors.append(f"Demand Gen readiness preview item {index} must be object.")
            continue
        if preview.get("preview_contract") != DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT:
            errors.append(f"Demand Gen readiness preview item {index} requires contract.")
        if preview.get("operation_type") != DEMAND_GEN_READINESS_REVIEW_OPERATION_TYPE:
            errors.append(f"Demand Gen readiness preview item {index} requires operation type.")
        if not isinstance(preview.get("campaign_channel_counts"), dict):
            errors.append(f"Demand Gen readiness preview item {index} requires channel counts.")
        if not isinstance(preview.get("missing_read_contracts"), list):
            errors.append(
                f"Demand Gen readiness preview item {index} requires missing contracts."
            )
        if not isinstance(preview.get("required_validation"), list):
            errors.append(
                f"Demand Gen readiness preview item {index} requires required validation."
            )
        if not isinstance(preview.get("evidence_ids"), list) or not preview.get(
            "evidence_ids"
        ):
            errors.append(f"Demand Gen readiness preview item {index} requires evidence IDs.")
        if preview.get("api_mutation_ready") is not False:
            errors.append(
                f"Demand Gen readiness preview item {index} must not be API-mutation ready."
            )
        if preview.get("apply_allowed") is not False:
            errors.append(
                f"Demand Gen readiness preview item {index} must keep apply_allowed=false."
            )
        if preview.get("destructive") is not False:
            errors.append(f"Demand Gen readiness preview item {index} must be non-destructive.")
    return errors


def unique_items(items: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique
