from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.schemas import (
    DemandGenAdGroupAdRow,
    DemandGenCreativeAssetRow,
    DemandGenLandingQualityRow,
    DemandGenMigrationConstraintRow,
    MetricFact,
)

DEMAND_GEN_READINESS_REVIEW_ACTION_ID = "act_review_demand_gen_readiness"
DEMAND_GEN_READINESS_REVIEW_ACTION_TYPE = "google_ads_demand_gen_readiness_review"
DEMAND_GEN_READINESS_REVIEW_PREVIEW_CONTRACT = "demand_gen_readiness_review_preview_v1"
DEMAND_GEN_READINESS_REVIEW_OPERATION_TYPE = "DemandGenReadinessReview"
DEMAND_GEN_READINESS_AVAILABLE_CONTRACT = "demand_gen_readiness_review_action_object"
DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT = "demand_gen_campaign_rows"
DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT = "demand_gen_ad_group_ad_rows"
DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT = "demand_gen_creative_asset_rows"
DEMAND_GEN_LANDING_QUALITY_CONTRACT = "demand_gen_landing_quality_by_campaign"
DEMAND_GEN_MIGRATION_CONSTRAINTS_CONTRACT = "demand_gen_migration_constraints"
DEMAND_GEN_AD_READ_STATUS_FACT = "demand_gen_ad_group_ad_status"
DEMAND_GEN_AD_READ_ROW_COUNT_FACT = "demand_gen_ad_group_ad_row_count"
DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT = "demand_gen_creative_asset_status"
DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT = "demand_gen_creative_asset_row_count"
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
    demand_gen_ad_group_ad_rows: list[dict[str, Any]],
    demand_gen_creative_asset_rows: list[dict[str, Any]],
    demand_gen_landing_quality_rows: list[dict[str, Any]],
    demand_gen_migration_constraint_rows: list[dict[str, Any]],
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
        "demand_gen_ad_group_ad_row_count": len(demand_gen_ad_group_ad_rows),
        "demand_gen_ad_group_ad_rows": demand_gen_ad_group_ad_rows[:4],
        "demand_gen_creative_asset_row_count": len(demand_gen_creative_asset_rows),
        "demand_gen_creative_asset_rows": demand_gen_creative_asset_rows[:4],
        "demand_gen_landing_quality_row_count": len(demand_gen_landing_quality_rows),
        "demand_gen_landing_quality_rows": demand_gen_landing_quality_rows[:4],
        "demand_gen_migration_constraint_row_count": len(
            demand_gen_migration_constraint_rows
        ),
        "demand_gen_migration_constraint_rows": demand_gen_migration_constraint_rows[:4],
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
        if not isinstance(preview.get("demand_gen_ad_group_ad_rows"), list):
            errors.append(f"Demand Gen readiness preview item {index} requires ad rows.")
        if not isinstance(preview.get("demand_gen_creative_asset_rows"), list):
            errors.append(f"Demand Gen readiness preview item {index} requires asset rows.")
        if not isinstance(preview.get("demand_gen_landing_quality_rows"), list):
            errors.append(
                f"Demand Gen readiness preview item {index} requires landing rows."
            )
        if not isinstance(preview.get("demand_gen_migration_constraint_rows"), list):
            errors.append(
                f"Demand Gen readiness preview item {index} requires migration rows."
            )
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


def demand_gen_ad_group_ad_rows_from_facts(
    facts: Iterable[MetricFact],
) -> list[DemandGenAdGroupAdRow]:
    grouped: dict[tuple[str | None, str | None, str | None], list[MetricFact]] = {}
    for fact in facts:
        if fact.name not in {
            "demand_gen_ad_available",
            "demand_gen_ad_final_url_count",
            "demand_gen_ad_asset_reference_count",
        }:
            continue
        ad_id = fact.dimensions.get("ad_id")
        if not ad_id:
            continue
        ad_type = fact.dimensions.get("ad_type")
        campaign_id = fact.dimensions.get("campaign_id")
        grouped.setdefault((campaign_id, ad_id, ad_type), []).append(fact)
    rows = [_demand_gen_ad_group_ad_row(group_facts) for group_facts in grouped.values()]
    return sorted(
        rows,
        key=lambda row: (
            row.campaign_name or "",
            row.ad_group_name or "",
            row.ad_id or "",
            row.ad_type or "",
        ),
    )


def demand_gen_creative_asset_rows_from_facts(
    facts: Iterable[MetricFact],
) -> list[DemandGenCreativeAssetRow]:
    grouped: dict[tuple[str | None, str | None, str | None], list[MetricFact]] = {}
    for fact in facts:
        if fact.name != "demand_gen_creative_asset_impressions":
            continue
        asset_id = fact.dimensions.get("asset_id")
        if not asset_id:
            continue
        asset_type = fact.dimensions.get("asset_type")
        field_type = fact.dimensions.get("field_type")
        grouped.setdefault((asset_id, asset_type, field_type), []).append(fact)
    rows = [_demand_gen_creative_asset_row(group_facts) for group_facts in grouped.values()]
    return sorted(
        rows,
        key=lambda row: (row.asset_type or "", row.asset_id or "", row.field_type or ""),
    )


def demand_gen_landing_quality_rows_from_facts(
    facts: Iterable[MetricFact],
    demand_gen_campaign_rows: Iterable[dict[str, Any]],
) -> list[DemandGenLandingQualityRow]:
    demand_gen_campaigns = _campaigns_by_name(demand_gen_campaign_rows)
    if not demand_gen_campaigns:
        return []
    grouped: dict[tuple[str, str, str], list[MetricFact]] = {}
    for fact in facts:
        if fact.source_connector != "google_analytics_4":
            continue
        if fact.name not in {"active_users", "sessions", "engagement_rate"}:
            continue
        campaign_name = fact.dimensions.get("campaign_name")
        landing_page = fact.dimensions.get("landing_page")
        source_medium = fact.dimensions.get("source_medium", "")
        if not campaign_name or not landing_page:
            continue
        if _normalize_name(campaign_name) not in demand_gen_campaigns:
            continue
        grouped.setdefault((campaign_name, landing_page, source_medium), []).append(fact)
    rows = [
        _demand_gen_landing_quality_row(group_facts, demand_gen_campaigns)
        for group_facts in grouped.values()
    ]
    return sorted(
        rows,
        key=lambda row: (
            row.campaign_name,
            row.landing_page,
            row.source_medium or "",
        ),
    )


def demand_gen_migration_constraint_rows_from_campaigns(
    demand_gen_campaign_rows: Iterable[dict[str, Any]],
) -> list[DemandGenMigrationConstraintRow]:
    rows: list[DemandGenMigrationConstraintRow] = []
    for campaign in demand_gen_campaign_rows:
        campaign_name = str(campaign.get("campaign_name") or "campaign").strip()
        channel = str(campaign.get("advertising_channel_type") or "").strip().upper()
        if channel == "DISCOVERY":
            migration_candidate = True
            reason = "discovery_to_demand_gen_requires_human_review"
        else:
            migration_candidate = False
            reason = "already_demand_gen_review_only"
        rows.append(
            DemandGenMigrationConstraintRow(
                campaign_id=campaign.get("campaign_id"),
                campaign_name=campaign_name,
                campaign_status=campaign.get("campaign_status"),
                advertising_channel_type=campaign.get("advertising_channel_type"),
                migration_candidate=migration_candidate,
                reason=reason,
                evidence_ids=unique_items(campaign.get("evidence_ids") or []),
            )
        )
    return sorted(
        rows,
        key=lambda row: (row.migration_candidate, row.campaign_name),
        reverse=True,
    )


def demand_gen_contract_has_ready_fact(
    facts: Iterable[MetricFact],
    *,
    status_fact_name: str,
    row_count_fact_name: str,
) -> bool:
    status_ready = False
    row_count_seen = False
    for fact in facts:
        if fact.name == status_fact_name and str(fact.value) == "ready":
            status_ready = True
        elif fact.name == row_count_fact_name:
            row_count_seen = True
    return status_ready or row_count_seen


def unique_items(items: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique


def _demand_gen_ad_group_ad_row(facts: list[MetricFact]) -> DemandGenAdGroupAdRow:
    first = facts[0]
    return DemandGenAdGroupAdRow(
        campaign_id=first.dimensions.get("campaign_id"),
        campaign_name=first.dimensions.get("campaign_name"),
        campaign_status=first.dimensions.get("campaign_status"),
        advertising_channel_type=first.dimensions.get("advertising_channel_type"),
        ad_group_id=first.dimensions.get("ad_group_id"),
        ad_group_name=first.dimensions.get("ad_group_name"),
        ad_id=first.dimensions.get("ad_id"),
        ad_type=first.dimensions.get("ad_type"),
        ad_status=first.dimensions.get("ad_status"),
        final_url_count=_int_fact_value(facts, "demand_gen_ad_final_url_count"),
        asset_reference_count=_int_fact_value(
            facts,
            "demand_gen_ad_asset_reference_count",
        ),
        evidence_ids=sorted({fact.evidence_id for fact in facts if fact.evidence_id}),
    )


def _demand_gen_creative_asset_row(facts: list[MetricFact]) -> DemandGenCreativeAssetRow:
    first = facts[0]
    impressions_fact = next(
        (fact for fact in facts if fact.name == "demand_gen_creative_asset_impressions"),
        None,
    )
    return DemandGenCreativeAssetRow(
        asset_id=first.dimensions.get("asset_id"),
        asset_type=first.dimensions.get("asset_type"),
        field_type=first.dimensions.get("field_type"),
        impressions=_int_value(impressions_fact.value) if impressions_fact else None,
        evidence_ids=sorted({fact.evidence_id for fact in facts if fact.evidence_id}),
    )


def _demand_gen_landing_quality_row(
    facts: list[MetricFact],
    demand_gen_campaigns: dict[str, dict[str, Any]],
) -> DemandGenLandingQualityRow:
    first = facts[0]
    campaign_name = first.dimensions.get("campaign_name", "campaign")
    campaign = demand_gen_campaigns.get(_normalize_name(campaign_name), {})
    engagement_rate = _float_fact_value(facts, "engagement_rate")
    return DemandGenLandingQualityRow(
        campaign_id=campaign.get("campaign_id"),
        campaign_name=campaign_name,
        landing_page=first.dimensions.get("landing_page", ""),
        source_medium=first.dimensions.get("source_medium"),
        active_users=_int_fact_value(facts, "active_users"),
        sessions=_int_fact_value(facts, "sessions"),
        engagement_rate=engagement_rate,
        evidence_ids=unique_items(fact.evidence_id for fact in facts if fact.evidence_id),
    )


def _campaigns_by_name(
    demand_gen_campaign_rows: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    campaigns: dict[str, dict[str, Any]] = {}
    for campaign in demand_gen_campaign_rows:
        campaign_name = str(campaign.get("campaign_name") or "").strip()
        if campaign_name:
            campaigns[_normalize_name(campaign_name)] = campaign
    return campaigns


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _int_fact_value(facts: list[MetricFact], name: str) -> int:
    fact = next((candidate for candidate in facts if candidate.name == name), None)
    if fact is None:
        return 0
    return _int_value(fact.value)


def _float_fact_value(facts: list[MetricFact], name: str) -> float | None:
    fact = next((candidate for candidate in facts if candidate.name == name), None)
    if fact is None:
        return None
    return _float_value(fact.value)


def _int_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _float_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
