from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from wilq.connectors.google_auth import GoogleCredentialError, google_access_token
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

GA4_READONLY_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
GA4_API_BASE = "https://analyticsdata.googleapis.com/v1beta"
GA4_BEHAVIOR_METRICS = (
    "activeUsers",
    "sessions",
    "screenPageViews",
    "eventCount",
    "engagementRate",
)
GA4_CONVERSION_METRICS = (
    "keyEvents",
    "ecommercePurchases",
    "purchaseRevenue",
    "totalRevenue",
    "transactions",
)
GA4_METRICS = (*GA4_BEHAVIOR_METRICS, *GA4_CONVERSION_METRICS)
GA4_DIMENSIONS = (
    "landingPagePlusQueryString",
    "sessionSourceMedium",
    "sessionCampaignName",
)
GA4_ITEM_DIMENSIONS = (
    "itemId",
    "itemName",
)
GA4_ITEM_METRICS = (
    "itemsViewed",
    "itemsAddedToCart",
    "itemsCheckedOut",
    "itemsPurchased",
    "itemRevenue",
)


def refresh_ga4_behavior_summary(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    property_id = variable_value("GA4_PROPERTY_ID")
    if not property_id:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="GA4 vendor read blocked by missing credential names: GA4_PROPERTY_ID.",
            errors=["GA4 property ID is missing."],
        )

    try:
        access_token = google_access_token([GA4_READONLY_SCOPE])
    except GoogleCredentialError as exc:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="GA4 vendor read blocked by Google credentials.",
            errors=[f"Google credentials blocked: {type(exc).__name__}."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        metric_summary, metric_facts = _fetch_behavior_summary(client, property_id, access_token)
    except httpx.HTTPStatusError as exc:
        return _http_failure_result(exc)
    except httpx.HTTPError as exc:
        return _transport_failure_result(exc)
    finally:
        if owns_client:
            client.close()

    return VendorReadResult(
        status=ConnectorRefreshStatus.completed,
        summary=(
            "Odczyt GA4 zakończony przez Analytics Data API runReport. "
            f"Wiersze stron wejścia: {metric_summary['row_count']}; "
            f"wiersze produktów: {metric_summary['ga4_item_product_row_count']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
        metric_facts=metric_facts,
    )


def _fetch_behavior_summary(
    client: httpx.Client,
    property_id: str,
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    date_start, date_end = _default_date_range()
    behavior_payload = _post_run_report(
        client,
        property_id,
        access_token,
        date_start=date_start,
        date_end=date_end,
        dimensions=GA4_DIMENSIONS,
        metrics=GA4_METRICS,
        limit=10,
    )
    behavior_summary, behavior_facts = _summarize_run_report_response(
        behavior_payload,
        date_start=date_start,
        date_end=date_end,
    )
    item_payload = _post_run_report(
        client,
        property_id,
        access_token,
        date_start=date_start,
        date_end=date_end,
        dimensions=GA4_ITEM_DIMENSIONS,
        metrics=GA4_ITEM_METRICS,
        limit=50,
    )
    item_summary, item_facts = _summarize_item_run_report_response(item_payload)
    return behavior_summary | item_summary, [*behavior_facts, *item_facts]


def _post_run_report(
    client: httpx.Client,
    property_id: str,
    access_token: str,
    *,
    date_start: str,
    date_end: str,
    dimensions: tuple[str, ...],
    metrics: tuple[str, ...],
    limit: int,
) -> Any:
    response = client.post(
        f"{GA4_API_BASE}/{_property_path(property_id)}:runReport",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "dateRanges": [{"startDate": date_start, "endDate": date_end}],
            "dimensions": [{"name": dimension} for dimension in dimensions],
            "metrics": [{"name": metric} for metric in metrics],
            "limit": str(limit),
        },
    )
    response.raise_for_status()
    return response.json()


def _property_path(property_id: str) -> str:
    normalized = property_id.strip()
    if normalized.startswith("properties/"):
        return normalized
    return f"properties/{normalized}"


def _default_date_range() -> tuple[str, str]:
    end = datetime.now(UTC).date() - timedelta(days=1)
    start = end - timedelta(days=27)
    return start.isoformat(), end.isoformat()


def _summarize_run_report_response(
    payload: Any,
    *,
    date_start: str,
    date_end: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    metric_names = _metric_names(payload)
    dimension_names = _dimension_names(payload)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    totals = {metric: 0.0 for metric in metric_names}
    row_count = 0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_count += 1
        values = row.get("metricValues", [])
        if not isinstance(values, list):
            continue
        for index, metric in enumerate(metric_names):
            if index >= len(values) or not isinstance(values[index], dict):
                continue
            totals[metric] += _float_metric(values[index].get("value"))
        dimensions = _ga4_dimensions(row, dimension_names)
        if dimensions:
            metric_facts.extend(
                _ga4_metric_facts(
                    values,
                    metric_names,
                    dimensions,
                    period=f"{date_start}/{date_end}",
                )
            )
    return (
        {
            "api": "analytics_data_run_report",
            "date_start": date_start,
            "date_end": date_end,
            "row_count": row_count,
            "active_users": int(totals.get("activeUsers", 0.0)),
            "sessions": int(totals.get("sessions", 0.0)),
            "screen_page_views": int(totals.get("screenPageViews", 0.0)),
            "event_count": int(totals.get("eventCount", 0.0)),
            "engagement_rate": round(totals.get("engagementRate", 0.0), 6),
            "key_events": int(totals.get("keyEvents", 0.0)),
            "ecommerce_purchases": int(totals.get("ecommercePurchases", 0.0)),
            "purchase_revenue": round(totals.get("purchaseRevenue", 0.0), 2),
            "total_revenue": round(totals.get("totalRevenue", 0.0), 2),
            "transactions": int(totals.get("transactions", 0.0)),
        },
        metric_facts,
    )


def _summarize_item_run_report_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    metric_names = _metric_names(payload, fallback=GA4_ITEM_METRICS)
    dimension_names = _dimension_names(payload, fallback=GA4_ITEM_DIMENSIONS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    totals = {metric: 0.0 for metric in metric_names}
    row_count = 0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_count += 1
        values = row.get("metricValues", [])
        if not isinstance(values, list):
            continue
        for index, metric in enumerate(metric_names):
            if index >= len(values) or not isinstance(values[index], dict):
                continue
            totals[metric] += _float_metric(values[index].get("value"))
        dimensions = _ga4_dimensions(row, dimension_names)
        if dimensions.get("item_id"):
            metric_facts.extend(_ga4_metric_facts(values, metric_names, dimensions))
    return (
        {
            "ga4_item_product_row_count": row_count,
            "ga4_items_viewed": int(totals.get("itemsViewed", 0.0)),
            "ga4_items_added_to_cart": int(totals.get("itemsAddedToCart", 0.0)),
            "ga4_items_checked_out": int(totals.get("itemsCheckedOut", 0.0)),
            "ga4_items_purchased": int(totals.get("itemsPurchased", 0.0)),
            "ga4_item_revenue": round(totals.get("itemRevenue", 0.0), 2),
        },
        metric_facts,
    )


def _metric_names(payload: Any, *, fallback: tuple[str, ...] = GA4_METRICS) -> list[str]:
    headers = payload.get("metricHeaders", []) if isinstance(payload, dict) else []
    if not isinstance(headers, list):
        return list(fallback)
    names = [item.get("name") for item in headers if isinstance(item, dict)]
    return [name for name in names if isinstance(name, str)] or list(fallback)


def _dimension_names(
    payload: Any,
    *,
    fallback: tuple[str, ...] = GA4_DIMENSIONS,
) -> list[str]:
    headers = payload.get("dimensionHeaders", []) if isinstance(payload, dict) else []
    if not isinstance(headers, list):
        return list(fallback)
    names = [item.get("name") for item in headers if isinstance(item, dict)]
    return [name for name in names if isinstance(name, str)] or list(fallback)


def _ga4_dimensions(row: dict[str, Any], dimension_names: list[str]) -> dict[str, str]:
    values = row.get("dimensionValues", [])
    if not isinstance(values, list):
        return {}
    dimensions: dict[str, str] = {}
    for index, dimension_name in enumerate(dimension_names):
        if index >= len(values) or not isinstance(values[index], dict):
            continue
        value = values[index].get("value")
        if isinstance(value, str) and value:
            dimensions[_snake_case_ga4_dimension(dimension_name)] = value
    return dimensions


def _ga4_metric_facts(
    values: Any,
    metric_names: list[str],
    dimensions: dict[str, str],
    *,
    period: str = "connector_refresh",
) -> list[VendorMetricFact]:
    if not isinstance(values, list):
        return []
    facts: list[VendorMetricFact] = []
    for index, metric_name in enumerate(metric_names):
        if index >= len(values) or not isinstance(values[index], dict):
            continue
        raw_value = values[index].get("value")
        value = _float_metric(raw_value)
        if metric_name != "engagementRate" and value.is_integer():
            metric_value: float | int = int(value)
        else:
            metric_value = round(value, 6)
        facts.append(
            VendorMetricFact(
                _snake_case_ga4_metric(metric_name),
                metric_value,
                dimensions,
                period=period,
            )
        )
    return facts


def _snake_case_ga4_metric(value: str) -> str:
    mapping = {
        "activeUsers": "active_users",
        "screenPageViews": "screen_page_views",
        "eventCount": "event_count",
        "engagementRate": "engagement_rate",
        "keyEvents": "key_events",
        "ecommercePurchases": "ecommerce_purchases",
        "purchaseRevenue": "purchase_revenue",
        "totalRevenue": "total_revenue",
        "itemsViewed": "item_views",
        "itemsAddedToCart": "item_adds_to_cart",
        "itemsCheckedOut": "item_checkouts",
        "itemsPurchased": "item_purchases",
        "itemRevenue": "item_revenue",
    }
    return mapping.get(value, value)


def _snake_case_ga4_dimension(value: str) -> str:
    mapping = {
        "landingPagePlusQueryString": "landing_page",
        "sessionSourceMedium": "source_medium",
        "sessionCampaignName": "campaign_name",
        "itemId": "item_id",
        "itemName": "item_name",
    }
    return mapping.get(value, value)


def _http_failure_result(exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"GA4 Analytics Data API runReport failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"GA4 Analytics Data API runReport HTTP {status_code}."],
    )


def _transport_failure_result(exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"GA4 Analytics Data API runReport failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"GA4 Analytics Data API runReport {type(exc).__name__}."],
    )


def _float_metric(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0
