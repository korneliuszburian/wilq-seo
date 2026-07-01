from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from wilq.connectors.google_auth import GoogleCredentialError, google_access_token
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

GSC_READONLY_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GSC_API_BASE = "https://searchconsole.googleapis.com/webmasters/v3"
GSC_AVAILABILITY_LOOKBACK_DAYS = 10
GSC_QUERY_PAGE_ROW_LIMIT = 250
GSC_QUERY_PAGE_MAX_ROWS = 1000


def refresh_search_console_site_summary(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    site_url = variable_value("GOOGLE_SEARCH_CONSOLE_SITE_URL") or variable_value("GSC_SITE_URL")
    if not site_url:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Google Search Console vendor read blocked by missing credential names: "
                "GOOGLE_SEARCH_CONSOLE_SITE_URL."
            ),
            errors=["Google Search Console site URL is missing."],
        )

    try:
        access_token = google_access_token([GSC_READONLY_SCOPE])
    except GoogleCredentialError as exc:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="Google Search Console vendor read blocked by Google credentials.",
            errors=[f"Google credentials blocked: {type(exc).__name__}."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        metric_summary, metric_facts = _fetch_site_summary(client, site_url, access_token)
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
            "Odczyt Google Search Console zakończony przez Search Analytics. "
            f"Wiersze: {metric_summary['row_count']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
        metric_facts=metric_facts,
    )


def _fetch_site_summary(
    client: httpx.Client,
    site_url: str,
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    availability_start, availability_end = _default_availability_range()
    endpoint = f"{GSC_API_BASE}/sites/{quote(site_url, safe='')}/searchAnalytics/query"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    availability_response = client.post(
        endpoint,
        headers=headers,
        json={
            "startDate": availability_start,
            "endDate": availability_end,
            "dimensions": ["date"],
            "rowLimit": GSC_AVAILABILITY_LOOKBACK_DAYS,
        },
    )
    availability_response.raise_for_status()
    available_date = _latest_available_date(availability_response.json())
    if available_date is None:
        return (
            {
                "api": "search_console_search_analytics",
                "date_start": availability_start,
                "date_end": availability_end,
                "row_count": 0,
                "clicks": 0,
                "impressions": 0,
                "ctr": 0.0,
                "average_position": 0.0,
                "data_availability_checked": "true",
                "date_availability_status": "no_available_date",
                "availability_date_start": availability_start,
                "availability_date_end": availability_end,
                "query_page_row_limit": GSC_QUERY_PAGE_ROW_LIMIT,
                "query_page_max_rows": GSC_QUERY_PAGE_MAX_ROWS,
                "query_page_rows_truncated": "false",
            },
            [],
        )
    rows: list[dict[str, Any]] = []
    start_row = 0
    while start_row < GSC_QUERY_PAGE_MAX_ROWS:
        response = client.post(
            endpoint,
            headers=headers,
            json={
                "startDate": available_date,
                "endDate": available_date,
                "dimensions": ["query", "page"],
                "rowLimit": GSC_QUERY_PAGE_ROW_LIMIT,
                "startRow": start_row,
            },
        )
        response.raise_for_status()
        page_rows = _payload_rows(response.json())
        rows.extend(page_rows)
        if len(page_rows) < GSC_QUERY_PAGE_ROW_LIMIT:
            break
        start_row += GSC_QUERY_PAGE_ROW_LIMIT
    return _summarize_search_analytics_response(
        {"rows": rows[:GSC_QUERY_PAGE_MAX_ROWS]},
        date_start=available_date,
        date_end=available_date,
        availability_date_start=availability_start,
        availability_date_end=availability_end,
        rows_truncated=len(rows) >= GSC_QUERY_PAGE_MAX_ROWS,
    )


def _default_availability_range() -> tuple[str, str]:
    end = datetime.now(UTC).date() - timedelta(days=1)
    start = end - timedelta(days=GSC_AVAILABILITY_LOOKBACK_DAYS - 1)
    return start.isoformat(), end.isoformat()


def _summarize_search_analytics_response(
    payload: Any,
    *,
    date_start: str,
    date_end: str,
    availability_date_start: str | None = None,
    availability_date_end: str | None = None,
    rows_truncated: bool = False,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _payload_rows(payload)
    clicks = 0
    impressions = 0
    weighted_position = 0.0
    ctr_values: list[float] = []
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_clicks = _int_metric(row.get("clicks"))
        row_impressions = _int_metric(row.get("impressions"))
        row_ctr = _float_metric(row.get("ctr"))
        row_position = _float_metric(row.get("position"))
        clicks += row_clicks
        impressions += row_impressions
        weighted_position += row_position * row_impressions
        ctr_values.append(row_ctr)
        dimensions = _search_dimensions(row)
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact("clicks", row_clicks, dimensions),
                    VendorMetricFact("impressions", row_impressions, dimensions),
                    VendorMetricFact("ctr", row_ctr, dimensions),
                    VendorMetricFact("average_position", row_position, dimensions),
                ]
            )
    return (
        {
            "api": "search_console_search_analytics",
            "date_start": date_start,
            "date_end": date_end,
            "row_count": len([row for row in rows if isinstance(row, dict)]),
            "clicks": clicks,
            "impressions": impressions,
            "ctr": round(clicks / impressions, 6) if impressions else _average(ctr_values),
            "average_position": round(weighted_position / impressions, 4) if impressions else 0.0,
            "data_availability_checked": "true",
            "date_availability_status": "available",
            "availability_date_start": availability_date_start or date_start,
            "availability_date_end": availability_date_end or date_end,
            "query_page_row_limit": GSC_QUERY_PAGE_ROW_LIMIT,
            "query_page_max_rows": GSC_QUERY_PAGE_MAX_ROWS,
            "query_page_rows_truncated": str(rows_truncated).lower(),
        },
        metric_facts,
    )


def _payload_rows(payload: Any) -> list[dict[str, Any]]:
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _latest_available_date(payload: Any) -> str | None:
    available_dates: list[str] = []
    for row in _payload_rows(payload):
        keys = row.get("keys", [])
        if isinstance(keys, list) and keys and isinstance(keys[0], str) and keys[0]:
            available_dates.append(keys[0])
    if not available_dates:
        return None
    return max(available_dates)


def _http_failure_result(exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Google Search Console Search Analytics failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"Google Search Console Search Analytics HTTP {status_code}."],
    )


def _transport_failure_result(exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Google Search Console Search Analytics failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"Google Search Console Search Analytics {type(exc).__name__}."],
    )


def _int_metric(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _float_metric(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _search_dimensions(row: dict[str, Any]) -> dict[str, str]:
    keys = row.get("keys", [])
    if not isinstance(keys, list):
        return {}
    dimensions: dict[str, str] = {}
    if len(keys) > 0 and isinstance(keys[0], str) and keys[0]:
        dimensions["query"] = keys[0]
    if len(keys) > 1 and isinstance(keys[1], str) and keys[1]:
        dimensions["page"] = keys[1]
    return dimensions
