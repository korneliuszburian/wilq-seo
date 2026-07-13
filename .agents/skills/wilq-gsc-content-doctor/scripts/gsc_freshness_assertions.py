from __future__ import annotations

from typing import Any


def validate_freshness_and_gsc_contract(
    content_diagnostics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    freshness = content_diagnostics.get("freshness_assessment")
    if not isinstance(freshness, dict):
        raise SystemExit("Content diagnostics must expose freshness_assessment")
    if freshness.get("state") not in {"fresh", "stale", "missing", "blocked"}:
        raise SystemExit("Content diagnostics freshness_assessment has invalid state")
    for field in ("state_label", "summary", "next_step"):
        if not str(freshness.get(field) or "").strip():
            raise SystemExit(f"Content diagnostics freshness_assessment {field} is missing")
    if freshness.get("requires_refresh") is True and not (
        freshness.get("connector_labels_requiring_refresh") or []
    ):
        raise SystemExit(
            "Content diagnostics freshness_assessment requires refresh but lists no connectors"
        )
    contract = content_diagnostics.get("gsc_search_analytics_contract")
    if content_diagnostics.get("live_data_available") is not True:
        return freshness, contract if isinstance(contract, dict) else None
    if not isinstance(contract, dict):
        raise SystemExit("Content diagnostics must expose GSC Search Analytics contract")
    expected = {
        "data_availability_checked": True,
        "date_availability_status": "available",
        "search_type": "web",
        "detail_dimensions": "query,page",
        "detail_data_completeness": "partial_possible",
        "aggregate_dimensions": "country,device",
        "aggregate_aggregation_type": "byProperty",
        "aggregate_data_completeness": "aggregate_without_query_page_dimensions",
        "expected_data_delay_days_min": 2,
        "expected_data_delay_days_max": 3,
        "read_granularity": "single_day_latest_available",
        "api_recommended_page_size": 25000,
        "api_daily_row_cap_per_search_type": 50000,
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            raise SystemExit(f"Content diagnostics GSC contract must expose {field}={value}")
    for field in ("aggregate_summary_label", "summary_label"):
        if not str(contract.get(field) or "").strip():
            raise SystemExit(f"Content diagnostics GSC contract {field} is missing")
    if "nie pełną sumą całego ruchu" not in str(contract.get("partial_detail_warning_label") or ""):
        raise SystemExit("Content diagnostics GSC contract must warn about partial totals")
    if "25 000 wierszy" not in str(contract.get("official_limits_label") or ""):
        raise SystemExit("Content diagnostics GSC contract must explain official paging")
    if "rowLimit=" not in str(contract.get("wilq_internal_cap_label") or ""):
        raise SystemExit("Content diagnostics GSC contract must explain WILQ internal cap")
    return freshness, contract
