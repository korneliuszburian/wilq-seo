from __future__ import annotations

from typing import Any

import httpx

from wilq.connectors.google_auth import GoogleCredentialError, google_access_token
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

MERCHANT_API_SCOPE = "https://www.googleapis.com/auth/content"
MERCHANT_ISSUE_RESOLUTION_BASE = "https://merchantapi.googleapis.com/issueresolution/v1"


def refresh_merchant_product_status_summary(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    account_id = _normalize_account_id(variable_value("GOOGLE_MERCHANT_CENTER_ACCOUNT_ID"))
    if not account_id:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Merchant Center vendor read blocked by missing credential names: "
                "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID."
            ),
            errors=["Merchant Center account ID is missing."],
        )

    try:
        access_token = google_access_token([MERCHANT_API_SCOPE])
    except GoogleCredentialError as exc:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="Merchant Center vendor read blocked by Google credentials.",
            errors=[f"Google credentials blocked: {type(exc).__name__}."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        metric_summary, metric_facts = _fetch_product_status_summary(
            client,
            account_id,
            access_token,
        )
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
            "Merchant Center vendor read completed through aggregateProductStatuses. "
            f"Products: {metric_summary['total_products']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
        metric_facts=metric_facts,
    )


def _normalize_account_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.removeprefix("accounts/").strip()
    return normalized or None


def _fetch_product_status_summary(
    client: httpx.Client,
    account_id: str,
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    response = client.get(
        f"{MERCHANT_ISSUE_RESOLUTION_BASE}/accounts/{account_id}/aggregateProductStatuses",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"pageSize": 100},
    )
    response.raise_for_status()
    return _summarize_aggregate_product_statuses(response.json())


def _summarize_aggregate_product_statuses(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    statuses = payload.get("aggregateProductStatuses", []) if isinstance(payload, dict) else []
    if not isinstance(statuses, list):
        statuses = []
    active_count = 0
    pending_count = 0
    disapproved_count = 0
    expiring_count = 0
    issue_count = 0
    merchant_action_issue_count = 0
    merchant_action_product_count = 0
    disapproved_issue_count = 0
    demoted_issue_count = 0
    warning_issue_count = 0
    countries: set[str] = set()
    reporting_contexts: set[str] = set()
    metric_facts: list[VendorMetricFact] = []
    for status in statuses:
        if not isinstance(status, dict):
            continue
        country = status.get("country")
        if isinstance(country, str) and country:
            countries.add(country)
        reporting_context = status.get("reportingContext")
        if isinstance(reporting_context, str) and reporting_context:
            reporting_contexts.add(reporting_context)
        stats = status.get("stats") or status.get("statistics") or {}
        if not isinstance(stats, dict):
            stats = {}
        status_active_count = _int_metric(stats.get("activeCount") or stats.get("approvedCount"))
        status_pending_count = _int_metric(stats.get("pendingCount"))
        status_disapproved_count = _int_metric(stats.get("disapprovedCount"))
        status_expiring_count = _int_metric(stats.get("expiringCount"))
        active_count += status_active_count
        pending_count += status_pending_count
        disapproved_count += status_disapproved_count
        expiring_count += status_expiring_count
        status_dimensions = _status_dimensions(status)
        if status_dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact("active_products", status_active_count, status_dimensions),
                    VendorMetricFact("pending_products", status_pending_count, status_dimensions),
                    VendorMetricFact(
                        "disapproved_products",
                        status_disapproved_count,
                        status_dimensions,
                    ),
                    VendorMetricFact("expiring_products", status_expiring_count, status_dimensions),
                ]
            )
        issues = status.get("itemLevelIssues") or status.get("issues") or []
        if not isinstance(issues, list):
            continue
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            issue_count += 1
            product_count = _int_metric(issue.get("productCount") or issue.get("numProducts"))
            issue_dimensions = status_dimensions | _issue_dimensions(issue)
            if issue_dimensions:
                metric_facts.append(
                    VendorMetricFact(
                        "issue_product_count",
                        product_count,
                        issue_dimensions,
                    )
                )
            if issue.get("resolution") == "MERCHANT_ACTION":
                merchant_action_issue_count += 1
                merchant_action_product_count += product_count
            severity = issue.get("severity")
            if severity == "DISAPPROVED":
                disapproved_issue_count += 1
            elif severity == "DEMOTED":
                demoted_issue_count += 1
            elif severity == "NOT_IMPACTED":
                warning_issue_count += 1
    total_products = active_count + pending_count + disapproved_count + expiring_count
    return (
        {
            "api": "merchant_aggregate_product_statuses",
            "status_group_count": len([status for status in statuses if isinstance(status, dict)]),
            "country_count": len(countries),
            "reporting_context_count": len(reporting_contexts),
            "active_products": active_count,
            "pending_products": pending_count,
            "disapproved_products": disapproved_count,
            "expiring_products": expiring_count,
            "total_products": total_products,
            "item_level_issue_count": issue_count,
            "merchant_action_issue_count": merchant_action_issue_count,
            "merchant_action_product_count": merchant_action_product_count,
            "disapproved_issue_count": disapproved_issue_count,
            "demoted_issue_count": demoted_issue_count,
            "warning_issue_count": warning_issue_count,
            "next_page_present": 1 if _next_page_present(payload) else 0,
        },
        metric_facts,
    )


def _next_page_present(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    token = payload.get("nextPageToken")
    return isinstance(token, str) and bool(token)


def _http_failure_result(exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Merchant Center aggregateProductStatuses failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"Merchant Center aggregateProductStatuses HTTP {status_code}."],
    )


def _transport_failure_result(exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Merchant Center aggregateProductStatuses failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"Merchant Center aggregateProductStatuses {type(exc).__name__}."],
    )


def _int_metric(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _status_dimensions(status: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    country = status.get("country") or status.get("countryCode")
    if isinstance(country, str) and country:
        dimensions["country"] = country
    reporting_context = status.get("reportingContext")
    if isinstance(reporting_context, str) and reporting_context:
        dimensions["reporting_context"] = reporting_context
    return dimensions


def _issue_dimensions(issue: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    severity = issue.get("severity")
    if isinstance(severity, str) and severity:
        dimensions["severity"] = severity
    resolution = issue.get("resolution")
    if isinstance(resolution, str) and resolution:
        dimensions["resolution"] = resolution
    issue_type = issue.get("issueType") or issue.get("type") or issue.get("code")
    if isinstance(issue_type, str) and issue_type:
        dimensions["issue_type"] = _safe_dimension_text(issue_type)
    title = issue.get("title")
    if isinstance(title, str) and title:
        dimensions["issue_title"] = _safe_dimension_text(title)
    category = issue.get("category")
    if isinstance(category, str) and category:
        dimensions["issue_category"] = _safe_dimension_text(category)
    attribute = issue.get("attribute")
    if isinstance(attribute, str) and attribute:
        dimensions["affected_attribute"] = _safe_dimension_text(attribute)
    destination = issue.get("destination")
    if isinstance(destination, str) and destination:
        dimensions["destination"] = _safe_dimension_text(destination)
    return dimensions


def _safe_dimension_text(value: str) -> str:
    normalized = " ".join(value.split())
    return normalized[:120]
