from __future__ import annotations

import math
from typing import Any

from wilq.content.canonical.redacted_landing import build_redacted_landing_reference

ADS_DEMAND_PERIOD = "last_30_days"
ADS_SEARCH_TERM_PAYLOAD_STATUS = "search_term_payload_status"
ADS_LANDING_MAPPING_STATUS = "landing_mapping_status"
ADS_LANDING_IDENTITY = "landing_identity_sha256"
ADS_LANDING_ACTUAL_CLICKED = "actual_clicked_in_window"
ADS_LANDING_RESOLVED = "resolved"
ADS_DEMAND_INPUT_FACT_NAMES = {ADS_SEARCH_TERM_PAYLOAD_STATUS}


def search_term_landing_dimensions(row: dict[str, Any]) -> dict[str, str]:
    landing = row.get(
        "expandedLandingPageView",
        row.get("expanded_landing_page_view", {}),
    )
    raw_url = (
        landing.get("expandedFinalUrl", landing.get("expanded_final_url"))
        if isinstance(landing, dict)
        else None
    )
    reference = build_redacted_landing_reference(
        raw_url if isinstance(raw_url, str) else None
    )
    dimensions = {ADS_LANDING_MAPPING_STATUS: reference.status}
    if reference.status != ADS_LANDING_RESOLVED or not reference.identity_sha256:
        return dimensions
    dimensions.update(
        {
            ADS_LANDING_IDENTITY: reference.identity_sha256,
            ADS_LANDING_ACTUAL_CLICKED: "true",
        }
    )
    if reference.tracking_parameters_removed:
        dimensions["tracking_parameters_removed"] = "true"
    if reference.has_functional_query:
        dimensions["functional_query_present"] = "true"
    return dimensions


def strict_search_stream_rows(payload: Any) -> tuple[list[dict[str, Any]], bool]:
    if not isinstance(payload, list):
        return [], False
    rows: list[dict[str, Any]] = []
    for chunk in payload:
        if not isinstance(chunk, dict) or "results" not in chunk:
            return [], False
        results = chunk["results"]
        if not isinstance(results, list) or any(
            not isinstance(row, dict) or not _search_term_row_is_complete(row)
            for row in results
        ):
            return [], False
        rows.extend(results)
    return rows, True


def _search_term_row_is_complete(row: dict[str, Any]) -> bool:
    campaign = _nested_object(row, "campaign")
    ad_group = _nested_object(row, "adGroup", "ad_group")
    search_term = _nested_object(row, "searchTermView", "search_term_view")
    landing = _nested_object(
        row,
        "expandedLandingPageView",
        "expanded_landing_page_view",
    )
    metrics = _nested_object(row, "metrics")
    if not all((campaign, ad_group, search_term, metrics)):
        return False
    clicks = _metric_number(metrics, "clicks")
    required_metrics = (
        clicks,
        _metric_number(metrics, "impressions"),
        _metric_number(metrics, "costMicros", "cost_micros"),
        _metric_number(metrics, "conversions"),
        _metric_number(metrics, "conversionsValue", "conversions_value"),
    )
    landing_is_valid = landing is None or bool(
        _nonempty_text(landing, "expandedFinalUrl", "expanded_final_url")
    )
    return bool(
        _nonempty_scalar(campaign, "id")
        and _nonempty_scalar(ad_group, "id")
        and _nonempty_text(search_term, "searchTerm", "search_term")
        and landing_is_valid
        and all(value is not None and value >= 0 for value in required_metrics)
        and clicks is not None
        and clicks > 0
    )


def _nested_object(row: dict[str, Any], *names: str) -> dict[str, Any] | None:
    value = next((row[name] for name in names if name in row), None)
    return value if isinstance(value, dict) else None


def _nonempty_scalar(value: dict[str, Any], *names: str) -> bool:
    raw = next((value[name] for name in names if name in value), None)
    return (
        isinstance(raw, int)
        and not isinstance(raw, bool)
        or isinstance(raw, str)
        and bool(raw.strip())
    )


def _nonempty_text(value: dict[str, Any], *names: str) -> bool:
    raw = next((value[name] for name in names if name in value), None)
    return isinstance(raw, str) and bool(raw.strip())


def _metric_number(value: dict[str, Any], *names: str) -> float | None:
    raw = next((value[name] for name in names if name in value), None)
    if isinstance(raw, bool):
        return None
    if not isinstance(raw, int | float | str) or isinstance(raw, str) and not raw.strip():
        return None
    try:
        number = float(raw)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None
