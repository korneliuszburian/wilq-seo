from __future__ import annotations

from typing import Any

from scripts.skill_smoke_harness import request_json


def read_latest_gsc_refresh_contract(api_base: str) -> tuple[dict[str, Any], str | None]:
    runs = request_json(api_base, "GET", "/api/connectors/google_search_console/refresh-runs")
    summary = _latest_summary(runs)
    evidence_id = _latest_evidence_id(runs)
    if not summary:
        return {}, evidence_id
    required = {
        "data_availability_checked",
        "date_availability_status",
        "availability_date_start",
        "availability_date_end",
        "date_start",
        "date_end",
        "query_page_row_limit",
        "query_page_max_rows",
        "query_page_rows_truncated",
        "search_type",
        "detail_dimensions",
        "detail_data_completeness",
        "aggregate_dimensions",
        "aggregate_aggregation_type",
        "aggregate_data_completeness",
        "aggregate_clicks",
        "aggregate_impressions",
    }
    missing = sorted(required - set(summary))
    if missing:
        raise SystemExit(
            "Latest GSC vendor_read metric_summary missing Search Analytics "
            f"contract fields: {', '.join(missing)}"
        )
    expected = {
        "data_availability_checked": "true",
        "date_availability_status": "available",
        "search_type": "web",
        "detail_dimensions": "query,page",
        "detail_data_completeness": "partial_possible",
        "aggregate_dimensions": "country,device",
        "aggregate_aggregation_type": "byProperty",
        "aggregate_data_completeness": "aggregate_without_query_page_dimensions",
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            raise SystemExit(f"Latest GSC vendor_read must record {field}={value}")
    return summary, evidence_id


def _latest_summary(runs: Any) -> dict[str, Any]:
    if not isinstance(runs, list):
        return {}
    for run in runs:
        if (
            isinstance(run, dict)
            and run.get("status") == "completed"
            and run.get("mode") == "vendor_read"
            and run.get("connector_id") == "google_search_console"
            and isinstance(run.get("metric_summary"), dict)
        ):
            return run["metric_summary"]
    return {}


def _latest_evidence_id(runs: Any) -> str | None:
    if not isinstance(runs, list):
        return None
    for run in runs:
        if (
            not isinstance(run, dict)
            or run.get("status") != "completed"
            or run.get("mode") != "vendor_read"
            or run.get("connector_id") != "google_search_console"
        ):
            continue
        evidence_ids = run.get("evidence_ids")
        if isinstance(evidence_ids, list):
            for evidence_id in evidence_ids:
                if str(evidence_id).startswith("ev_refresh_refresh_google_search_console_"):
                    return str(evidence_id)
    return None
