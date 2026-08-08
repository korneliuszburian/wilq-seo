"""Google Ads budget and monetary impact helpers."""
from __future__ import annotations

from typing import Any

from wilq.connectors.vendor import VendorMetricFact

from .shared import (
    _optional_float_metric,
    _optional_int_metric,
)


def _budget_value(campaign_budget: Any, *keys: str) -> Any:
    if not isinstance(campaign_budget, dict):
        return None
    for key in keys:
        if key in campaign_budget:
            return campaign_budget[key]
    return None

def _recommendation_impact_metric_facts(
    recommendation: dict[str, Any],
    dimensions: dict[str, str],
) -> list[VendorMetricFact]:
    impact = recommendation.get("impact")
    if not isinstance(impact, dict):
        return []
    metric_facts: list[VendorMetricFact] = []
    for prefix, metrics in (
        ("base", impact.get("baseMetrics", impact.get("base_metrics"))),
        ("potential", impact.get("potentialMetrics", impact.get("potential_metrics"))),
    ):
        if not isinstance(metrics, dict):
            continue
        metric_facts.extend(_recommendation_impact_metrics_for_prefix(prefix, metrics, dimensions))
    return metric_facts

def _recommendation_impact_metrics_for_prefix(
    prefix: str,
    metrics: dict[str, Any],
    dimensions: dict[str, str],
) -> list[VendorMetricFact]:
    metric_facts: list[VendorMetricFact] = []
    int_metrics = {
        "clicks": _optional_int_metric(metrics.get("clicks")),
        "impressions": _optional_int_metric(metrics.get("impressions")),
        "cost_micros": _optional_int_metric(metrics.get("costMicros", metrics.get("cost_micros"))),
    }
    float_metrics = {
        "conversions": _optional_float_metric(metrics.get("conversions")),
        "conversion_value": _optional_float_metric(
            metrics.get("conversionsValue", metrics.get("conversions_value"))
        ),
    }
    for name, int_value in int_metrics.items():
        if int_value is not None:
            metric_facts.append(
                VendorMetricFact(
                    f"recommendation_impact_{prefix}_{name}",
                    int_value,
                    dimensions,
                    period="recommendation_impact",
                )
            )
    for name, float_value in float_metrics.items():
        if float_value is not None:
            metric_facts.append(
                VendorMetricFact(
                    f"recommendation_impact_{prefix}_{name}",
                    float_value,
                    dimensions,
                    period="recommendation_impact",
                )
            )
    return metric_facts

