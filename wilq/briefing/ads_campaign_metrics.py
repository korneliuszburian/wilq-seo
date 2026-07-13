from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from wilq.actions.google_ads.campaign_triage import (
    campaign_review_gates,
    campaign_review_priority,
    campaign_review_reason,
    campaign_review_score,
    campaign_target_context,
)
from wilq.schemas import (
    AdsBusinessContextReadContract,
    AdsCampaignMetricRow,
    MetricFact,
)


def campaign_metric_rows(
    metric_facts: list[MetricFact],
    business_context_read_contract: AdsBusinessContextReadContract,
    *,
    unique: Callable[[Iterable[object]], list[str]],
    int_metric_value: Callable[[MetricFact | None], int | None],
    float_metric_value: Callable[[MetricFact | None], float | None],
    row_sort_key: Callable[[AdsCampaignMetricRow], Any],
) -> list[AdsCampaignMetricRow]:
    grouped_facts: dict[tuple[str | None, str], list[MetricFact]] = {}
    row_metadata: dict[tuple[str | None, str], dict[str, str]] = {}
    seen_metric_keys: set[tuple[str | None, str, str]] = set()
    for fact in metric_facts:
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name")
        if not campaign_id and not campaign_name:
            continue
        row_key = (campaign_id, campaign_name or f"campaign {campaign_id}")
        metadata = row_metadata.setdefault(row_key, {})
        for key in ("campaign_status", "advertising_channel_type"):
            value = fact.dimensions.get(key)
            if value:
                metadata[key] = value
        if fact.name not in {
            "clicks",
            "impressions",
            "cost_micros",
            "conversions",
            "conversion_value",
        }:
            continue
        metric_key = (campaign_id, row_key[1], fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _campaign_metric_row(
            campaign_id,
            campaign_name,
            facts,
            row_metadata.get((campaign_id, campaign_name), {}),
            business_context_read_contract,
            unique=unique,
            int_metric_value=int_metric_value,
            float_metric_value=float_metric_value,
        )
        for (campaign_id, campaign_name), facts in grouped_facts.items()
    ]
    return sorted(rows, key=row_sort_key)


def _campaign_metric_row(
    campaign_id: str | None,
    campaign_name: str,
    facts: list[MetricFact],
    metadata: dict[str, str] | None,
    business_context_read_contract: AdsBusinessContextReadContract,
    *,
    unique: Callable[[Iterable[object]], list[str]],
    int_metric_value: Callable[[MetricFact | None], int | None],
    float_metric_value: Callable[[MetricFact | None], float | None],
) -> AdsCampaignMetricRow:
    facts_by_name = {fact.name: fact for fact in facts}
    metadata_dimensions = metadata or {}
    first_dimensions = next(
        (
            fact.dimensions
            for fact in facts
            if fact.dimensions.get("advertising_channel_type")
            or fact.dimensions.get("campaign_status")
        ),
        metadata_dimensions or (facts[0].dimensions if facts else {}),
    )
    expected_metrics = [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    clicks = int_metric_value(facts_by_name.get("clicks"))
    impressions = int_metric_value(facts_by_name.get("impressions"))
    cost_micros = int_metric_value(facts_by_name.get("cost_micros"))
    conversions = float_metric_value(facts_by_name.get("conversions"))
    conversion_value = float_metric_value(facts_by_name.get("conversion_value"))
    advertising_channel_type = first_dimensions.get("advertising_channel_type")
    campaign_status = first_dimensions.get("campaign_status")
    missing_metrics = [name for name in expected_metrics if name not in facts_by_name]
    target_context = campaign_target_context(
        cost_micros=cost_micros,
        conversions=conversions,
        conversion_value=conversion_value,
        target_roas=business_context_read_contract.target_roas,
        target_cpa_micros=business_context_read_contract.target_cpa_micros,
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
    return AdsCampaignMetricRow(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        campaign_status=campaign_status,
        advertising_channel_type=advertising_channel_type,
        clicks=clicks,
        impressions=impressions,
        cost_micros=cost_micros,
        conversions=conversions,
        conversion_value=conversion_value,
        evidence_ids=unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=missing_metrics,
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "marnowanie budżetu na zapytaniach",
            "zmarnowany budżet",
        ],
        target_status=target_context["target_status"],
        target_status_label=target_context["target_status_label"],
        review_priority=campaign_review_priority(review_score),
        review_score=review_score,
        review_reason=campaign_review_reason(
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
        human_review_gates=campaign_review_gates(
            campaign_name=campaign_name,
            advertising_channel_type=advertising_channel_type,
            cost_micros=cost_micros,
            conversions=conversions,
            target_status=target_context["target_status"],
        ),
    )
