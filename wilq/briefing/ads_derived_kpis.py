from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Literal

from wilq.schemas import AdsBusinessContextReadContract, AdsCampaignMetricRow, AdsDerivedKpiRow

AdsTargetStatus = Literal[
    "within_target",
    "outside_target",
    "spend_without_conversions",
    "insufficient_data",
    "no_target",
]


def target_triage(
    *,
    row: AdsCampaignMetricRow,
    cost_per_conversion_micros: float | None,
    roas: float | None,
    target_cpa_micros: int | None,
    target_roas: float | None,
) -> tuple[AdsTargetStatus, str, int]:
    if target_cpa_micros is not None:
        if cost_per_conversion_micros is not None:
            if cost_per_conversion_micros <= target_cpa_micros:
                return "within_target", "koszt pozyskania celu w granicy celu", 40
            return "outside_target", "koszt pozyskania celu powyżej celu", 20
        if (row.cost_micros or 0) > 0 and not row.conversions:
            return "spend_without_conversions", "koszt bez konwersji", 15
        return "insufficient_data", "brak kosztu pozyskania celu do porównania", 70

    if target_roas is not None:
        if roas is not None:
            if roas >= target_roas:
                return "within_target", "zwrot z reklam w granicy celu", 40
            return "outside_target", "zwrot z reklam poniżej celu", 20
        if (row.cost_micros or 0) > 0 and not row.conversion_value:
            return "spend_without_conversions", "koszt bez wartości konwersji", 15
        return "insufficient_data", "brak zwrotu z reklam do porównania", 70

    return "no_target", "brak celu", 90


def derived_kpi_row(
    row: AdsCampaignMetricRow,
    business_context_read_contract: AdsBusinessContextReadContract,
    *,
    ratio: Callable[[float | int | None, float | int | None], float | None],
    difference: Callable[[float | int | None, float | int | None], float | None],
    micros_to_account_units: Callable[[float | int | None], float | None],
    unique: Callable[[Iterable[object]], list[str]],
) -> AdsDerivedKpiRow:
    source_metric_names = [fact.name for fact in row.metric_facts]
    missing_metrics = list(row.missing_metrics)
    if not row.impressions:
        missing_metrics.append("nonzero_impressions")
    if not row.clicks:
        missing_metrics.extend(["nonzero_clicks_for_cpc", "nonzero_clicks_for_conversion_rate"])
    if not row.conversions:
        missing_metrics.extend(
            ["nonzero_conversions_for_cpa", "nonzero_conversions_for_value_per_conversion"]
        )
    if not row.cost_micros:
        missing_metrics.append("nonzero_cost_for_roas")
    cost_per_conversion_micros = ratio(row.cost_micros, row.conversions)
    roas = ratio(row.conversion_value, micros_to_account_units(row.cost_micros))
    target_roas = business_context_read_contract.target_roas
    target_cpa_micros = business_context_read_contract.target_cpa_micros
    target_status, target_status_label, target_review_priority = target_triage(
        row=row,
        cost_per_conversion_micros=cost_per_conversion_micros,
        roas=roas,
        target_cpa_micros=target_cpa_micros,
        target_roas=target_roas,
    )
    return AdsDerivedKpiRow(
        campaign_id=row.campaign_id,
        campaign_name=row.campaign_name,
        ctr=ratio(row.clicks, row.impressions),
        average_cpc_micros=ratio(row.cost_micros, row.clicks),
        conversion_rate=ratio(row.conversions, row.clicks),
        cost_per_conversion_micros=cost_per_conversion_micros,
        roas=roas,
        value_per_conversion=ratio(row.conversion_value, row.conversions),
        target_roas=target_roas,
        roas_vs_target=difference(roas, target_roas),
        target_cpa_micros=target_cpa_micros,
        cpa_vs_target_micros=difference(cost_per_conversion_micros, target_cpa_micros),
        target_status=target_status,
        target_status_label=target_status_label,
        target_review_priority=target_review_priority,
        evidence_ids=row.evidence_ids,
        source_metric_names=unique(source_metric_names),
        missing_metrics=unique(missing_metrics),
        blocked_claims=[
            "opłacalność",
            "skalowanie budżetu",
            "zmarnowany budżet",
            "zapis rekomendacji",
        ],
    )
