from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

import httpx

from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

GOOGLE_ADS_API_VERSION = "v24"
OAUTH_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
SAFE_ERROR_LABEL = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
SAFE_FIELD_PATH = re.compile(r"^[A-Za-z0-9_.]{1,120}$")


def _google_ads_env_name(*parts: str) -> str:
    return "_".join(("GOOGLE_ADS", *parts))


GOOGLE_ADS_CREDENTIAL_NAMES = {
    "developer_token": _google_ads_env_name("DEVELOPER", "TOKEN"),
    "client_id": "GOOGLE_ADS_CLIENT_ID",
    "client_secret": _google_ads_env_name("CLIENT", "SECRET"),
    "refresh_token": _google_ads_env_name("REFRESH", "TOKEN"),
    "login_customer_id": "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
    "customer_id": "GOOGLE_ADS_CUSTOMER_ID",
}

CAMPAIGN_SUMMARY_QUERY = """
SELECT
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

SEARCH_TERM_SUMMARY_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  ad_group.id,
  ad_group.name,
  search_term_view.search_term,
  search_term_view.status,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
LIMIT 50
""".strip()

SEARCH_TERM_SAFETY_LOOKBACK_DAYS = 90
SEARCH_TERM_SAFETY_QUERY_TEMPLATE = """
SELECT
  campaign.id,
  campaign.name,
  ad_group.id,
  ad_group.name,
  search_term_view.search_term,
  search_term_view.status,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM search_term_view
WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
LIMIT 200
""".strip()

KEYWORD_MATCH_CONTEXT_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  ad_group.id,
  ad_group.name,
  ad_group_criterion.criterion_id,
  ad_group_criterion.status,
  ad_group_criterion.negative,
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type
FROM ad_group_criterion
WHERE ad_group_criterion.type = 'KEYWORD'
  AND campaign.status != 'REMOVED'
  AND ad_group_criterion.status != 'REMOVED'
LIMIT 500
""".strip()

RECOMMENDATION_SUMMARY_QUERY = """
SELECT
  recommendation.resource_name,
  recommendation.type,
  recommendation.dismissed,
  recommendation.campaign,
  recommendation.campaign_budget,
  recommendation.campaigns
FROM recommendation
WHERE recommendation.dismissed = false
LIMIT 50
""".strip()

CHANGE_EVENT_LOOKBACK_DAYS = 14
CHANGE_EVENT_SUMMARY_QUERY_TEMPLATE = """
SELECT
  change_event.resource_name,
  change_event.change_date_time,
  change_event.change_resource_name,
  change_event.client_type,
  change_event.change_resource_type,
  change_event.resource_change_operation,
  change_event.changed_fields,
  change_event.campaign
FROM change_event
WHERE change_event.change_date_time >= '{start_date}'
  AND change_event.change_date_time <= '{end_date}'
ORDER BY change_event.change_date_time DESC
LIMIT 50
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


def refresh_google_ads_campaign_summary(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    credentials = _google_ads_credentials()
    missing = [
        GOOGLE_ADS_CREDENTIAL_NAMES[name] for name, value in credentials.items() if not value
    ]
    if missing:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Google Ads vendor read blocked by missing credential names: "
                f"{', '.join(missing)}."
            ),
            errors=[
                "Google Ads vendor read blocked by missing credential names: "
                f"{', '.join(missing)}."
            ],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        try:
            access_token = _fetch_access_token(client, credentials)
        except httpx.HTTPStatusError as exc:
            return _http_failure_result("OAuth token refresh", exc)
        except httpx.HTTPError as exc:
            return _transport_failure_result("OAuth token refresh", exc)

        try:
            metric_summary, metric_facts = _fetch_campaign_summary(
                client,
                credentials,
                access_token,
            )
            search_term_summary, search_term_facts = _fetch_search_term_summary(
                client,
                credentials,
                access_token,
            )
            search_term_safety_summary, search_term_safety_facts = (
                _fetch_search_term_safety_summary(
                    client,
                    credentials,
                    access_token,
                )
            )
            keyword_context_summary, keyword_context_facts = (
                _fetch_keyword_match_context_summary(
                    client,
                    credentials,
                    access_token,
                )
            )
            recommendation_summary, recommendation_facts = _fetch_recommendation_summary(
                client,
                credentials,
                access_token,
            )
            change_event_summary, change_event_facts = _fetch_change_event_summary(
                client,
                credentials,
                access_token,
            )
            metric_summary.update(search_term_summary)
            metric_summary.update(search_term_safety_summary)
            metric_summary.update(keyword_context_summary)
            metric_summary.update(recommendation_summary)
            metric_summary.update(change_event_summary)
            metric_facts.extend(search_term_facts)
            metric_facts.extend(search_term_safety_facts)
            metric_facts.extend(keyword_context_facts)
            metric_facts.extend(recommendation_facts)
            metric_facts.extend(change_event_facts)
        except httpx.HTTPStatusError as exc:
            detail = _sanitized_http_error_detail(exc.response)
            if detail and "ads_error=queryError.REQUESTED_METRICS_FOR_MANAGER" in detail:
                try:
                    metric_summary, metric_facts = _fetch_customer_client_summary(
                        client,
                        credentials,
                        access_token,
                        blocked_detail=detail,
                    )
                except httpx.HTTPStatusError as fallback_exc:
                    return _http_failure_result("customerClient discovery", fallback_exc)
                except httpx.HTTPError as fallback_exc:
                    return _transport_failure_result("customerClient discovery", fallback_exc)
                return VendorReadResult(
                    status=ConnectorRefreshStatus.blocked,
                    summary=(
                        "Google Ads OAuth and manager access are working, but campaign metrics "
                        "were requested on a manager account. Set GOOGLE_ADS_CUSTOMER_ID to a "
                        "non-manager child account and keep GOOGLE_ADS_LOGIN_CUSTOMER_ID as the "
                        "manager account."
                    ),
                    external_call_attempted=True,
                    vendor_data_collected=True,
                    metric_summary=metric_summary,
                    metric_facts=metric_facts,
                    errors=[
                        "Google Ads manager account cannot return campaign metrics "
                        f"({detail})."
                    ],
                )
            return _http_failure_result("searchStream", exc)
        except httpx.HTTPError as exc:
            return _transport_failure_result("searchStream", exc)
    finally:
        if owns_client:
            client.close()

    return VendorReadResult(
        status=ConnectorRefreshStatus.completed,
        summary=(
            "Google Ads vendor read completed through googleAds:searchStream. "
            f"Campaign rows: {metric_summary['row_count']}; "
            f"search term rows: {metric_summary.get('search_term_row_count', 0)}; "
            "90-day search term safety rows: "
            f"{metric_summary.get('search_term_safety_row_count', 0)}; "
            "keyword match context rows: "
            f"{metric_summary.get('keyword_match_context_row_count', 0)}; "
            f"recommendation rows: {metric_summary.get('recommendation_row_count', 0)}; "
            f"change events: {metric_summary.get('change_event_row_count', 0)}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
        metric_facts=metric_facts,
    )


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


def _google_ads_credentials() -> dict[str, str | None]:
    login_customer_id = _normalize_customer_id(variable_value("GOOGLE_ADS_LOGIN_CUSTOMER_ID"))
    customer_id = (
        _normalize_customer_id(variable_value("GOOGLE_ADS_CUSTOMER_ID")) or login_customer_id
    )
    return {
        "developer_token": variable_value("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": variable_value("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": variable_value("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": variable_value("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": login_customer_id,
        "customer_id": customer_id,
    }


def _normalize_customer_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("-", "").strip()
    return normalized or None


def _fetch_access_token(client: httpx.Client, credentials: Mapping[str, str | None]) -> str:
    response = client.post(
        OAUTH_ENDPOINT,
        data={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "refresh_token": credentials["refresh_token"],
            "grant_type": "refresh_token",
            "scope": GOOGLE_ADS_SCOPE,
        },
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise httpx.HTTPError("OAuth response did not include access_token.")
    return token


def _fetch_campaign_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    customer_id = credentials["customer_id"]
    response = client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": CAMPAIGN_SUMMARY_QUERY},
    )
    response.raise_for_status()
    return _summarize_search_stream_response(response.json())


def _fetch_search_term_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    customer_id = credentials["customer_id"]
    response = client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": SEARCH_TERM_SUMMARY_QUERY},
    )
    response.raise_for_status()
    return _summarize_search_term_response(response.json())


def _fetch_search_term_safety_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    customer_id = credentials["customer_id"]
    response = client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": _search_term_safety_query()},
    )
    response.raise_for_status()
    return _summarize_search_term_safety_response(response.json())


def _fetch_keyword_match_context_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    customer_id = credentials["customer_id"]
    response = client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": KEYWORD_MATCH_CONTEXT_QUERY},
    )
    response.raise_for_status()
    return _summarize_keyword_match_context_response(response.json())


def _fetch_recommendation_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    customer_id = credentials["customer_id"]
    response = client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": RECOMMENDATION_SUMMARY_QUERY},
    )
    response.raise_for_status()
    return _summarize_recommendation_response(response.json())


def _fetch_change_event_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    customer_id = credentials["customer_id"]
    response = client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": _change_event_summary_query()},
    )
    response.raise_for_status()
    return _summarize_change_event_response(response.json())


def _change_event_summary_query(today: date | None = None) -> str:
    end_date = today or date.today()
    start_date = end_date - timedelta(days=CHANGE_EVENT_LOOKBACK_DAYS)
    return CHANGE_EVENT_SUMMARY_QUERY_TEMPLATE.format(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )


def _search_term_safety_query(today: date | None = None) -> str:
    end_date = today or date.today()
    start_date = end_date - timedelta(days=SEARCH_TERM_SAFETY_LOOKBACK_DAYS)
    return SEARCH_TERM_SAFETY_QUERY_TEMPLATE.format(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )


def _fetch_customer_client_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
    *,
    blocked_detail: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    customer_id = credentials["customer_id"]
    response = client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": CUSTOMER_CLIENT_QUERY},
    )
    response.raise_for_status()
    return _summarize_customer_client_response(response.json(), blocked_detail)


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
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
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
    return (
        {
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
        },
        metric_facts,
    )


def _summarize_recommendation_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    recommendation_types: set[str] = set()
    campaign_count = 0
    for row in rows:
        recommendation = row.get("recommendation", {})
        if not isinstance(recommendation, dict):
            continue
        dimensions = _recommendation_dimensions(recommendation)
        recommendation_type = dimensions.get("recommendation_type")
        if recommendation_type:
            recommendation_types.add(recommendation_type)
        row_campaign_count = _recommendation_campaign_count(recommendation)
        campaign_count += row_campaign_count
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "recommendation_available",
                        1,
                        dimensions,
                        period="recommendation",
                    ),
                    VendorMetricFact(
                        "recommendation_campaign_count",
                        row_campaign_count,
                        dimensions,
                        period="recommendation",
                    ),
                ]
            )
    return (
        {
            "recommendation_query": "active_recommendations",
            "recommendation_row_count": len(rows),
            "recommendation_campaign_count": campaign_count,
            "recommendation_types": ",".join(sorted(recommendation_types)),
        },
        metric_facts,
    )


def _summarize_change_event_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    resource_types: set[str] = set()
    operations: set[str] = set()
    client_types: set[str] = set()
    campaign_ids: set[str] = set()
    for row in rows:
        change_event = row.get("changeEvent", row.get("change_event", {}))
        if not isinstance(change_event, dict):
            continue
        dimensions = _change_event_dimensions(change_event)
        resource_type = dimensions.get("change_resource_type")
        operation = dimensions.get("resource_change_operation")
        client_type = dimensions.get("client_type")
        campaign_id = dimensions.get("campaign_id")
        if resource_type:
            resource_types.add(resource_type)
        if operation:
            operations.add(operation)
        if client_type:
            client_types.add(client_type)
        if campaign_id:
            campaign_ids.add(campaign_id)
        if dimensions:
            changed_field_count = _int_metric(dimensions.get("changed_field_count"))
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "change_event_available",
                        1,
                        dimensions,
                        period="change_history",
                    ),
                    VendorMetricFact(
                        "change_event_changed_field_count",
                        changed_field_count,
                        dimensions,
                        period="change_history",
                    ),
                ]
            )
    return (
        {
            "change_event_query": f"change_event_last_{CHANGE_EVENT_LOOKBACK_DAYS}_days",
            "change_event_row_count": len(rows),
            "change_event_campaign_count": len(campaign_ids),
            "change_event_resource_types": ",".join(sorted(resource_types)),
            "change_event_operations": ",".join(sorted(operations)),
            "change_event_client_types": ",".join(sorted(client_types)),
        },
        metric_facts,
    )


def _summarize_search_term_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
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
        dimensions = _search_term_dimensions(row)
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact("search_term_clicks", row_clicks, dimensions),
                    VendorMetricFact("search_term_impressions", row_impressions, dimensions),
                    VendorMetricFact("search_term_cost_micros", row_cost_micros, dimensions),
                    VendorMetricFact("search_term_conversions", row_conversions, dimensions),
                    VendorMetricFact(
                        "search_term_conversion_value",
                        row_conversion_value,
                        dimensions,
                    ),
                ]
            )
    return (
        {
            "search_term_query": "search_term_last_30_days",
            "search_term_row_count": len(rows),
            "search_term_clicks": clicks,
            "search_term_impressions": impressions,
            "search_term_cost_micros": cost_micros,
            "search_term_conversions": conversions,
            "search_term_conversion_value": conversion_value,
        },
        metric_facts,
    )


def _summarize_search_term_safety_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
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
        dimensions = _search_term_dimensions(row)
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "search_term_90d_clicks",
                        row_clicks,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_impressions",
                        row_impressions,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_cost_micros",
                        row_cost_micros,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_conversions",
                        row_conversions,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_conversion_value",
                        row_conversion_value,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                ]
            )
    return (
        {
            "search_term_safety_query": (
                f"search_term_last_{SEARCH_TERM_SAFETY_LOOKBACK_DAYS}_days"
            ),
            "search_term_safety_row_count": len(rows),
            "search_term_safety_clicks": clicks,
            "search_term_safety_impressions": impressions,
            "search_term_safety_cost_micros": cost_micros,
            "search_term_safety_conversions": conversions,
            "search_term_safety_conversion_value": conversion_value,
        },
        metric_facts,
    )


def _summarize_keyword_match_context_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    keyword_texts: set[str] = set()
    match_types: set[str] = set()
    negative_count = 0
    for row in rows:
        dimensions = _keyword_match_context_dimensions(row)
        keyword_text = dimensions.get("keyword_text")
        match_type = dimensions.get("keyword_match_type")
        if keyword_text:
            keyword_texts.add(keyword_text)
        if match_type:
            match_types.add(match_type)
        negative = dimensions.get("keyword_negative") == "true"
        if negative:
            negative_count += 1
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "keyword_match_context_available",
                        1,
                        dimensions,
                        period="keyword_match_context",
                    ),
                    VendorMetricFact(
                        "keyword_match_type",
                        match_type or "UNKNOWN",
                        dimensions,
                        period="keyword_match_context",
                    ),
                    VendorMetricFact(
                        "keyword_match_context_negative",
                        1 if negative else 0,
                        dimensions,
                        period="keyword_match_context",
                    ),
                ]
            )
    return (
        {
            "keyword_match_context_query": "ad_group_criterion_keyword_context",
            "keyword_match_context_row_count": len(rows),
            "keyword_match_context_keyword_count": len(keyword_texts),
            "keyword_match_context_negative_count": negative_count,
            "keyword_match_context_match_types": ",".join(sorted(match_types)),
        },
        metric_facts,
    )


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


def _customer_resource_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.rsplit("/", 1)[-1].strip() or None


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


def _budget_value(campaign_budget: Any, *keys: str) -> Any:
    if not isinstance(campaign_budget, dict):
        return None
    for key in keys:
        if key in campaign_budget:
            return campaign_budget[key]
    return None


def _search_term_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    ad_group = row.get("adGroup", row.get("ad_group", {}))
    if isinstance(ad_group, dict):
        ad_group_id = ad_group.get("id")
        if ad_group_id is not None:
            dimensions["ad_group_id"] = str(ad_group_id)
        ad_group_name = ad_group.get("name")
        if isinstance(ad_group_name, str) and ad_group_name:
            dimensions["ad_group_name"] = ad_group_name
    search_term_view = row.get("searchTermView", row.get("search_term_view", {}))
    if isinstance(search_term_view, dict):
        search_term = search_term_view.get("searchTerm", search_term_view.get("search_term"))
        if isinstance(search_term, str) and search_term:
            dimensions["search_term"] = search_term
        status = search_term_view.get("status")
        if isinstance(status, str) and status:
            dimensions["search_term_status"] = status
    return dimensions


def _keyword_match_context_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    ad_group = row.get("adGroup", row.get("ad_group", {}))
    if isinstance(ad_group, dict):
        ad_group_id = ad_group.get("id")
        if ad_group_id is not None:
            dimensions["ad_group_id"] = str(ad_group_id)
        ad_group_name = ad_group.get("name")
        if isinstance(ad_group_name, str) and ad_group_name:
            dimensions["ad_group_name"] = ad_group_name
    criterion = row.get("adGroupCriterion", row.get("ad_group_criterion", {}))
    if not isinstance(criterion, dict):
        return dimensions
    criterion_id = criterion.get("criterionId", criterion.get("criterion_id"))
    if criterion_id is not None:
        dimensions["criterion_id"] = str(criterion_id)
    status = criterion.get("status")
    if isinstance(status, str) and status:
        dimensions["criterion_status"] = status
    negative = _bool_metric(criterion.get("negative"))
    dimensions["keyword_negative"] = "true" if negative else "false"
    keyword = criterion.get("keyword", {})
    if isinstance(keyword, dict):
        keyword_text = keyword.get("text")
        if isinstance(keyword_text, str) and keyword_text:
            dimensions["keyword_text"] = keyword_text
        match_type = keyword.get("matchType", keyword.get("match_type"))
        if isinstance(match_type, str) and match_type:
            dimensions["keyword_match_type"] = match_type
    return dimensions


def _recommendation_dimensions(recommendation: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    resource_name = recommendation.get("resourceName", recommendation.get("resource_name"))
    recommendation_id = _customer_resource_id(resource_name)
    if recommendation_id:
        dimensions["recommendation_id"] = recommendation_id
    recommendation_type = recommendation.get("type")
    if isinstance(recommendation_type, str) and recommendation_type:
        dimensions["recommendation_type"] = recommendation_type
    dismissed = _bool_metric(recommendation.get("dismissed"))
    dimensions["dismissed"] = "true" if dismissed else "false"
    campaign_id = _customer_resource_id(recommendation.get("campaign"))
    if campaign_id:
        dimensions["campaign_id"] = campaign_id
    campaign_budget_id = _customer_resource_id(
        recommendation.get("campaignBudget", recommendation.get("campaign_budget"))
    )
    if campaign_budget_id:
        dimensions["campaign_budget_id"] = campaign_budget_id
    campaign_count = _recommendation_campaign_count(recommendation)
    dimensions["recommendation_campaign_count"] = str(campaign_count)
    return dimensions


def _recommendation_campaign_count(recommendation: dict[str, Any]) -> int:
    campaigns = recommendation.get("campaigns")
    if isinstance(campaigns, list):
        return len(campaigns)
    return 1 if _customer_resource_id(recommendation.get("campaign")) else 0


def _change_event_dimensions(change_event: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    resource_name = change_event.get("resourceName", change_event.get("resource_name"))
    change_event_id = _customer_resource_id(resource_name)
    if change_event_id:
        dimensions["change_event_id"] = change_event_id
    change_date_time = change_event.get(
        "changeDateTime",
        change_event.get("change_date_time"),
    )
    if isinstance(change_date_time, str) and change_date_time:
        dimensions["change_date_time"] = change_date_time[:32]
    change_resource_name = change_event.get(
        "changeResourceName",
        change_event.get("change_resource_name"),
    )
    change_resource_id = _customer_resource_id(change_resource_name)
    if change_resource_id:
        dimensions["change_resource_id"] = change_resource_id
    for source_key, target_key in (
        ("clientType", "client_type"),
        ("changeResourceType", "change_resource_type"),
        ("resourceChangeOperation", "resource_change_operation"),
    ):
        value = change_event.get(source_key, change_event.get(target_key))
        if isinstance(value, str) and SAFE_ERROR_LABEL.fullmatch(value):
            dimensions[target_key] = value
    campaign_id = _customer_resource_id(change_event.get("campaign"))
    if campaign_id:
        dimensions["campaign_id"] = campaign_id
    changed_fields = _field_mask_paths(
        change_event.get("changedFields", change_event.get("changed_fields"))
    )
    dimensions["changed_field_count"] = str(len(changed_fields))
    if changed_fields:
        dimensions["changed_fields"] = ",".join(changed_fields[:8])
    return dimensions


def _field_mask_paths(value: Any) -> list[str]:
    raw_paths: list[Any]
    if isinstance(value, dict):
        paths = value.get("paths")
        raw_paths = paths if isinstance(paths, list) else []
    elif isinstance(value, list):
        raw_paths = value
    elif isinstance(value, str):
        raw_paths = [path.strip() for path in value.split(",")]
    else:
        raw_paths = []
    return [
        path
        for path in (str(raw_path).strip() for raw_path in raw_paths)
        if path and SAFE_FIELD_PATH.fullmatch(path)
    ]
