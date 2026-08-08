"""Google Ads campaign and customer response summaries."""
from __future__ import annotations

from typing import Any

from wilq.connectors.vendor import VendorMetricFact

from .budget import (
    _budget_value,
)
from .shared import (
    GOOGLE_ADS_API_VERSION,
    _bool_metric,
    _float_metric,
    _int_metric,
    _optional_float_metric,
    _optional_int_metric,
    _search_stream_rows,
)

CAMPAIGN_SUMMARY_QUERY = """
SELECT
  customer.currency_code,
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type,
  campaign_budget.id,
  campaign_budget.name,
  campaign_budget.amount_micros,
  campaign_budget.period,
  campaign_budget.status,
  campaign_budget.has_recommended_budget,
  campaign_budget.recommended_budget_amount_micros,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value,
  metrics.search_impression_share,
  metrics.search_budget_lost_impression_share,
  metrics.search_rank_lost_impression_share
FROM campaign
WHERE segments.date DURING LAST_7_DAYS
  AND campaign.status != 'REMOVED'
""".strip()

AD_FINAL_URL_INVENTORY_QUERY = """
SELECT
  campaign.id,
  ad_group.id,
  ad_group_ad.status,
  ad_group_ad.ad.final_urls
FROM ad_group_ad
WHERE campaign.status != 'REMOVED'
  AND ad_group_ad.status != 'REMOVED'
LIMIT 500
""".strip()

CUSTOMER_CLIENT_QUERY = """
SELECT
  customer_client.client_customer,
  customer_client.manager,
  customer_client.level,
  customer_client.status
FROM customer_client
WHERE customer_client.level <= 1
LIMIT 50
""".strip()

def _summarize_customer_client_response(
    payload: Any,
    blocked_detail: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    child_count = 0
    manager_child_count = 0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        customer_client = row.get("customerClient", row.get("customer_client", {}))
        if not isinstance(customer_client, dict):
            continue
        child_count += 1
        manager = _bool_metric(customer_client.get("manager"))
        if manager:
            manager_child_count += 1
        child_customer_id = _customer_resource_id(customer_client.get("clientCustomer"))
        dimensions = {
            key: value
            for key, value in {
                "child_customer_id": child_customer_id,
                "manager": "true" if manager else "false",
                "level": str(customer_client.get("level", "")),
                "status": str(customer_client.get("status", "")),
            }.items()
            if value
        }
        if dimensions:
            metric_facts.append(
                VendorMetricFact(
                    "customer_client_available",
                    1,
                    dimensions,
                    period="account_inventory",
                )
            )
    return (
        {
            "api_version": GOOGLE_ADS_API_VERSION,
            "query": "customer_client_level_1",
            "manager_metrics_blocker": blocked_detail,
            "customer_client_count": child_count,
            "manager_customer_client_count": manager_child_count,
            "non_manager_customer_client_count": max(0, child_count - manager_child_count),
        },
        metric_facts,
    )

def _summarize_search_stream_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    budgeted_campaign_count = 0
    recommended_budget_count = 0
    impression_share_row_count = 0
    currency_codes: set[str] = set()
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        currency_code = _customer_currency_code(row)
        if currency_code:
            currency_codes.add(currency_code)
        metrics = row.get("metrics", {})
        row_clicks = _int_metric(metrics.get("clicks"))
        row_impressions = _int_metric(metrics.get("impressions"))
        row_cost_micros = _int_metric(metrics.get("costMicros", metrics.get("cost_micros")))
        row_conversions = _float_metric(metrics.get("conversions"))
        row_conversion_value = _float_metric(
            metrics.get("conversionsValue", metrics.get("conversions_value"))
        )
        clicks += row_clicks
        impressions += row_impressions
        cost_micros += row_cost_micros
        conversions += row_conversions
        conversion_value += row_conversion_value
        campaign = row.get("campaign", {})
        campaign_budget = row.get("campaignBudget", row.get("campaign_budget", {}))
        dimensions = _campaign_dimensions(campaign, campaign_budget)
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact("clicks", row_clicks, dimensions),
                    VendorMetricFact("impressions", row_impressions, dimensions),
                    VendorMetricFact("cost_micros", row_cost_micros, dimensions),
                    VendorMetricFact("conversions", row_conversions, dimensions),
                    VendorMetricFact("conversion_value", row_conversion_value, dimensions),
                ]
            )
            budget_amount_micros = _optional_int_metric(
                _budget_value(campaign_budget, "amountMicros", "amount_micros")
            )
            if budget_amount_micros is not None:
                budgeted_campaign_count += 1
                metric_facts.append(
                    VendorMetricFact(
                        "budget_amount_micros",
                        budget_amount_micros,
                        dimensions,
                    )
                )
            has_recommended_budget = _bool_metric(
                _budget_value(
                    campaign_budget,
                    "hasRecommendedBudget",
                    "has_recommended_budget",
                )
            )
            if has_recommended_budget:
                recommended_budget_count += 1
            metric_facts.append(
                VendorMetricFact(
                    "budget_has_recommended_budget",
                    1 if has_recommended_budget else 0,
                    dimensions,
                )
            )
            recommended_budget_amount_micros = _optional_int_metric(
                _budget_value(
                    campaign_budget,
                    "recommendedBudgetAmountMicros",
                    "recommended_budget_amount_micros",
                )
            )
            if recommended_budget_amount_micros is not None:
                metric_facts.append(
                    VendorMetricFact(
                        "budget_recommended_amount_micros",
                        recommended_budget_amount_micros,
                        dimensions,
                    )
                )
            impression_share_values = {
                "search_impression_share": _optional_float_metric(
                    metrics.get("searchImpressionShare", metrics.get("search_impression_share"))
                ),
                "search_budget_lost_impression_share": _optional_float_metric(
                    metrics.get(
                        "searchBudgetLostImpressionShare",
                        metrics.get("search_budget_lost_impression_share"),
                    )
                ),
                "search_rank_lost_impression_share": _optional_float_metric(
                    metrics.get(
                        "searchRankLostImpressionShare",
                        metrics.get("search_rank_lost_impression_share"),
                    )
                ),
            }
            if any(value is not None for value in impression_share_values.values()):
                impression_share_row_count += 1
            for name, value in impression_share_values.items():
                if value is not None:
                    metric_facts.append(VendorMetricFact(name, value, dimensions))
    for currency_code in sorted(currency_codes):
        metric_facts.append(
            VendorMetricFact(
                "account_currency_code",
                currency_code,
                period="account_context",
            )
        )
    summary: dict[str, float | int | str] = {
        "api_version": GOOGLE_ADS_API_VERSION,
        "query": "campaign_last_7_days",
        "row_count": len(rows),
        "clicks": clicks,
        "impressions": impressions,
        "cost_micros": cost_micros,
        "conversions": conversions,
        "conversion_value": conversion_value,
        "budgeted_campaign_count": budgeted_campaign_count,
        "recommended_budget_count": recommended_budget_count,
        "impression_share_row_count": impression_share_row_count,
    }
    if currency_codes:
        summary["customer_currency_code"] = ",".join(sorted(currency_codes))
    return summary, metric_facts

def _customer_currency_code(row: dict[str, Any]) -> str | None:
    customer = row.get("customer", {})
    if not isinstance(customer, dict):
        return None
    currency_code = customer.get("currencyCode", customer.get("currency_code"))
    if not isinstance(currency_code, str):
        return None
    normalized = currency_code.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        return None
    return normalized

def _customer_resource_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.rsplit("/", 1)[-1].strip() or None

def _campaign_dimensions(
    campaign: Any,
    campaign_budget: Any | None = None,
) -> dict[str, str]:
    if not isinstance(campaign, dict):
        return {}
    dimensions: dict[str, str] = {}
    campaign_id = campaign.get("id")
    if campaign_id is not None:
        dimensions["campaign_id"] = str(campaign_id)
    campaign_name = campaign.get("name")
    if isinstance(campaign_name, str) and campaign_name:
        dimensions["campaign_name"] = campaign_name
    campaign_status = campaign.get("status")
    if isinstance(campaign_status, str) and campaign_status:
        dimensions["campaign_status"] = campaign_status
    advertising_channel_type = campaign.get(
        "advertisingChannelType",
        campaign.get("advertising_channel_type"),
    )
    if isinstance(advertising_channel_type, str) and advertising_channel_type:
        dimensions["advertising_channel_type"] = advertising_channel_type
    if isinstance(campaign_budget, dict):
        budget_id = campaign_budget.get("id")
        if budget_id is not None:
            dimensions["budget_id"] = str(budget_id)
        budget_name = campaign_budget.get("name")
        if isinstance(budget_name, str) and budget_name:
            dimensions["budget_name"] = budget_name
        budget_period = campaign_budget.get("period")
        if isinstance(budget_period, str) and budget_period:
            dimensions["budget_period"] = budget_period
        budget_status = campaign_budget.get("status")
        if isinstance(budget_status, str) and budget_status:
            dimensions["budget_status"] = budget_status
    return dimensions

