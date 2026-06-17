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
GA4_METRICS = ("activeUsers", "sessions", "screenPageViews", "eventCount", "engagementRate")
GA4_DIMENSIONS = (
    "landingPagePlusQueryString",
    "sessionSourceMedium",
    "sessionCampaignName",
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
            "GA4 vendor read completed through Analytics Data API runReport. "
            f"Rows: {metric_summary['row_count']}."
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
    response = client.post(
        f"{GA4_API_BASE}/{_property_path(property_id)}:runReport",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "dateRanges": [{"startDate": date_start, "endDate": date_end}],
            "dimensions": [{"name": dimension} for dimension in GA4_DIMENSIONS],
            "metrics": [{"name": metric} for metric in GA4_METRICS],
            "limit": "10",
        },
    )
    response.raise_for_status()
    return _summarize_run_report_response(
        response.json(),
        date_start=date_start,
        date_end=date_end,
    )


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
            metric_facts.extend(_ga4_metric_facts(values, metric_names, dimensions))
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
        },
        metric_facts,
    )


def _metric_names(payload: Any) -> list[str]:
    headers = payload.get("metricHeaders", []) if isinstance(payload, dict) else []
    if not isinstance(headers, list):
        return list(GA4_METRICS)
    names = [item.get("name") for item in headers if isinstance(item, dict)]
    return [name for name in names if isinstance(name, str)] or list(GA4_METRICS)


def _dimension_names(payload: Any) -> list[str]:
    headers = payload.get("dimensionHeaders", []) if isinstance(payload, dict) else []
    if not isinstance(headers, list):
        return list(GA4_DIMENSIONS)
    names = [item.get("name") for item in headers if isinstance(item, dict)]
    return [name for name in names if isinstance(name, str)] or list(GA4_DIMENSIONS)


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
            VendorMetricFact(_snake_case_ga4_metric(metric_name), metric_value, dimensions)
        )
    return facts


def _snake_case_ga4_metric(value: str) -> str:
    mapping = {
        "activeUsers": "active_users",
        "screenPageViews": "screen_page_views",
        "eventCount": "event_count",
        "engagementRate": "engagement_rate",
    }
    return mapping.get(value, value)


def _snake_case_ga4_dimension(value: str) -> str:
    mapping = {
        "landingPagePlusQueryString": "landing_page",
        "sessionSourceMedium": "source_medium",
        "sessionCampaignName": "campaign_name",
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
