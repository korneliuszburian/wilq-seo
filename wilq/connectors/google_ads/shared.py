"""Shared Google Ads parsing, formatting, and validation helpers."""
from __future__ import annotations

import re
from typing import Any

import httpx

from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.schemas import ConnectorRefreshStatus

GOOGLE_ADS_API_VERSION = "v24"

SAFE_ERROR_LABEL = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")

SAFE_FIELD_PATH = re.compile(r"^[A-Za-z0-9_.]{1,120}$")

def _http_failure_result(operation: str, exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    detail = _sanitized_http_error_detail(exc.response)
    detail_suffix = f" ({detail})" if detail else ""
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Google Ads {operation} failed with HTTP {status_code}{detail_suffix}.",
        external_call_attempted=True,
        errors=[f"Google Ads {operation} HTTP {status_code}{detail_suffix}."],
    )

def _transport_failure_result(operation: str, exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Google Ads {operation} failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"Google Ads {operation} {type(exc).__name__}."],
    )

def _sanitized_http_error_detail(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    details: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                _append_error_payload_details(details, item.get("error"))
            if details:
                break
    elif isinstance(payload, dict):
        error = payload.get("error")
        _append_error_payload_details(details, error)

    if not details:
        return None
    return ", ".join(details)

def _append_error_payload_details(details: list[str], error: Any) -> None:
    if isinstance(error, str):
        _append_safe_detail(details, "oauth_error", error)
    elif isinstance(error, dict):
        code = error.get("code")
        status = error.get("status")
        if isinstance(code, int):
            details.append(f"api_code={code}")
        if isinstance(status, str):
            _append_safe_detail(details, "api_status", status)
        nested_details = error.get("details")
        if isinstance(nested_details, list):
            for nested_detail in nested_details:
                if not isinstance(nested_detail, dict):
                    continue
                for key in ("requestId", "request_id"):
                    value = nested_detail.get(key)
                    if isinstance(value, str):
                        _append_safe_detail(details, "request_id", value)
                        break
                errors = nested_detail.get("errors")
                if isinstance(errors, list):
                    _append_google_ads_error_details(details, errors)
                if details:
                    break

def _append_google_ads_error_details(
    details: list[str],
    errors: list[Any],
) -> None:
    for google_ads_error in errors:
        if not isinstance(google_ads_error, dict):
            continue
        error_code = google_ads_error.get("errorCode")
        if isinstance(error_code, dict):
            for category, code in error_code.items():
                if isinstance(category, str) and isinstance(code, str):
                    _append_safe_detail(details, "ads_error", f"{category}.{code}")
                    return
        message = google_ads_error.get("message")
        if isinstance(message, str):
            _append_safe_detail(details, "ads_message", message)

def _append_safe_detail(details: list[str], name: str, value: str) -> None:
    if SAFE_ERROR_LABEL.fullmatch(value):
        details.append(f"{name}={value}")

def _demand_gen_http_failure_summary(
    contract: str,
    exc: httpx.HTTPStatusError,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    detail = _sanitized_http_error_detail(exc.response)
    if contract == "creative_asset":
        summary: dict[str, float | int | str] = {
            "demand_gen_creative_asset_status": "blocked",
            "demand_gen_creative_asset_http_status": exc.response.status_code,
            "demand_gen_creative_asset_row_count": 0,
        }
        if detail:
            summary["demand_gen_creative_asset_blocker"] = detail
        return summary, []
    summary = {
        "demand_gen_ad_group_ad_status": "blocked",
        "demand_gen_ad_group_ad_http_status": exc.response.status_code,
        "demand_gen_ad_group_ad_row_count": 0,
    }
    if detail:
        summary["demand_gen_ad_group_ad_blocker"] = detail
    return summary, []

def _keyword_planner_http_failure_summary(
    exc: httpx.HTTPStatusError,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    detail = _sanitized_http_error_detail(exc.response)
    summary: dict[str, float | int | str] = {
        "keyword_planner_status": "blocked",
        "keyword_planner_http_status": exc.response.status_code,
        "keyword_planner_idea_count": 0,
    }
    if detail:
        summary["keyword_planner_blocker"] = detail
    return summary, []

def _shopping_product_performance_http_failure_summary(
    exc: httpx.HTTPStatusError,
    lookback_days: int,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    detail = _sanitized_http_error_detail(exc.response)
    summary: dict[str, float | int | str] = {
        "shopping_product_performance_status": "blocked",
        "shopping_product_performance_http_status": exc.response.status_code,
        "shopping_product_performance_lookback_days": lookback_days,
        "shopping_product_performance_row_count": 0,
    }
    if detail:
        summary["shopping_product_performance_blocker"] = detail
    return summary, []

def _shopping_product_state_http_failure_summary(
    exc: httpx.HTTPStatusError,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    detail = _sanitized_http_error_detail(exc.response)
    summary: dict[str, float | int | str] = {
        "shopping_product_state_status": "blocked",
        "shopping_product_state_http_status": exc.response.status_code,
        "shopping_product_state_row_count": 0,
    }
    if detail:
        summary["shopping_product_state_blocker"] = detail
    return summary, []

def _clip_dimension(value: str, limit: int = 240) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."

def _search_stream_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, Any]] = []
    for chunk in payload:
        if not isinstance(chunk, dict):
            continue
        results = chunk.get("results", [])
        if not isinstance(results, list):
            continue
        rows.extend(row for row in results if isinstance(row, dict))
    return rows

def _bool_metric(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False

def _int_metric(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0

def _string_metric(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _optional_int_metric(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None

def _float_metric(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0

def _list_count(mapping: Any, *keys: str) -> int:
    if not isinstance(mapping, dict):
        return 0
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, str) and value:
            return 1
    return 0

def _optional_float_metric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None

