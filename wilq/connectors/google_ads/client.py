from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

import httpx

from wilq.connectors.google_ads.ad_landing_pages import (
    ADS_DEMAND_PERIOD,
    ADS_LANDING_MAPPING_STATUS,
    ADS_LANDING_RESOLVED,
    ADS_SEARCH_TERM_PAYLOAD_STATUS,
    search_term_landing_dimensions,
    strict_search_stream_rows,
)
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

# Google Ads minor releases such as v24.2 automatically update the existing
# major REST endpoint. Keep the connector on the major endpoint and add new
# fields/features through explicit WILQ read contracts.
GOOGLE_ADS_API_VERSION = "v24"
OAUTH_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
SAFE_ERROR_LABEL = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
SAFE_FIELD_PATH = re.compile(r"^[A-Za-z0-9_.]{1,120}$")
KEYWORD_PLANNER_IDEA_SOURCE_TERM_LIMIT = 10
KEYWORD_PLANNER_IDEA_RESULT_LIMIT = 20
KEYWORD_PLANNER_DEFAULT_LANGUAGE_RESOURCE = "languageConstants/1045"
KEYWORD_PLANNER_DEFAULT_GEO_TARGET_RESOURCE = "geoTargetConstants/2616"
KEYWORD_PLANNER_NETWORK = "GOOGLE_SEARCH_AND_PARTNERS"


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
  AND metrics.clicks > 0
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

SHOPPING_PRODUCT_PERFORMANCE_LOOKBACK_DAYS = (30, 90)
SHOPPING_PRODUCT_PERFORMANCE_QUERY_TEMPLATE = """
SELECT
  campaign.id,
  campaign.name,
  campaign.advertising_channel_type,
  segments.product_item_id,
  segments.product_title,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM shopping_performance_view
WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
  AND metrics.impressions > 0
ORDER BY
  metrics.conversions DESC,
  metrics.clicks DESC,
  metrics.cost_micros DESC,
  metrics.impressions DESC
LIMIT 200
""".strip()

SHOPPING_PRODUCT_STATE_QUERY = """
SELECT
  shopping_product.resource_name,
  shopping_product.merchant_center_id,
  shopping_product.channel,
  shopping_product.language_code,
  shopping_product.feed_label,
  shopping_product.item_id,
  shopping_product.title,
  shopping_product.status,
  shopping_product.availability,
  shopping_product.currency_code,
  shopping_product.price_micros,
  shopping_product.target_countries
FROM shopping_product
ORDER BY shopping_product.item_id ASC
LIMIT 500
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
  recommendation.campaigns,
  recommendation.impact
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

DEMAND_GEN_AD_GROUP_AD_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type,
  ad_group.id,
  ad_group.name,
  ad_group_ad.status,
  ad_group_ad.ad.id,
  ad_group_ad.ad.type,
  ad_group_ad.ad.final_urls,
  ad_group_ad.ad.demand_gen_multi_asset_ad.marketing_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.square_marketing_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.portrait_marketing_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.classic_display_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.logo_images,
  ad_group_ad.ad.demand_gen_carousel_ad.logo_image,
  ad_group_ad.ad.demand_gen_carousel_ad.carousel_cards,
  ad_group_ad.ad.demand_gen_video_responsive_ad.logo_images,
  ad_group_ad.ad.demand_gen_video_responsive_ad.call_to_actions,
  ad_group_ad.ad.demand_gen_video_responsive_ad.videos
FROM ad_group_ad
WHERE campaign.advertising_channel_type = DEMAND_GEN
  AND ad_group_ad.status != 'REMOVED'
LIMIT 100
""".strip()

DEMAND_GEN_CREATIVE_ASSET_QUERY = """
SELECT
  asset.id,
  asset.type,
  ad_group_ad_asset_view.field_type,
  metrics.impressions
FROM ad_group_ad_asset_view
WHERE ad_group_ad_asset_view.field_type = DEMAND_GEN_CAROUSEL_CARD
LIMIT 100
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
                f"Google Ads vendor read blocked by missing credential names: {', '.join(missing)}."
            ),
            errors=[
                f"Google Ads vendor read blocked by missing credential names: {', '.join(missing)}."
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
            shopping_product_summary, shopping_product_facts = (
                _fetch_optional_shopping_product_performance(
                    client,
                    credentials,
                    access_token,
                )
            )
            shopping_product_state_summary, shopping_product_state_facts = (
                _fetch_optional_shopping_product_state(
                    client,
                    credentials,
                    access_token,
                )
            )
            keyword_context_summary, keyword_context_facts = _fetch_keyword_match_context_summary(
                client,
                credentials,
                access_token,
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
            demand_gen_ad_summary, demand_gen_ad_facts = _fetch_optional_demand_gen_ad_group_ads(
                client,
                credentials,
                access_token,
            )
            demand_gen_asset_summary, demand_gen_asset_facts = (
                _fetch_optional_demand_gen_creative_assets(
                    client,
                    credentials,
                    access_token,
                )
            )
            keyword_planner_summary, keyword_planner_facts = _fetch_optional_keyword_planner_ideas(
                client,
                credentials,
                access_token,
                search_term_facts,
            )
            metric_summary.update(search_term_summary)
            metric_summary.update(search_term_safety_summary)
            metric_summary.update(shopping_product_summary)
            metric_summary.update(shopping_product_state_summary)
            metric_summary.update(keyword_context_summary)
            metric_summary.update(recommendation_summary)
            metric_summary.update(change_event_summary)
            metric_summary.update(demand_gen_ad_summary)
            metric_summary.update(demand_gen_asset_summary)
            metric_summary.update(keyword_planner_summary)
            metric_facts.extend(search_term_facts)
            metric_facts.extend(search_term_safety_facts)
            metric_facts.extend(shopping_product_facts)
            metric_facts.extend(shopping_product_state_facts)
            metric_facts.extend(keyword_context_facts)
            metric_facts.extend(recommendation_facts)
            metric_facts.extend(change_event_facts)
            metric_facts.extend(demand_gen_ad_facts)
            metric_facts.extend(demand_gen_asset_facts)
            metric_facts.extend(keyword_planner_facts)
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
                        f"Google Ads manager account cannot return campaign metrics ({detail})."
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
            "Odczyt Google Ads zakończony przez googleAds:searchStream. "
            f"Wiersze kampanii: {metric_summary['row_count']}; "
            f"wiersze zapytań: {metric_summary.get('search_term_row_count', 0)}; "
            "90-dniowe wiersze bezpieczeństwa zapytań: "
            f"{metric_summary.get('search_term_safety_row_count', 0)}; "
            "wiersze produktów Shopping: "
            f"{metric_summary.get('shopping_product_performance_row_count', 0)}; "
            "wiersze stanu produktów Shopping: "
            f"{metric_summary.get('shopping_product_state_row_count', 0)}; "
            "wiersze kontekstu dopasowań słów kluczowych: "
            f"{metric_summary.get('keyword_match_context_row_count', 0)}; "
            f"wiersze rekomendacji: {metric_summary.get('recommendation_row_count', 0)}; "
            f"zdarzenia zmian: {metric_summary.get('change_event_row_count', 0)}; "
            "reklamy Demand Gen: "
            f"{metric_summary.get('demand_gen_ad_group_ad_row_count', 0)}; "
            "zasoby kreacji Demand Gen: "
            f"{metric_summary.get('demand_gen_creative_asset_row_count', 0)}; "
            f"keyword planner ideas: {metric_summary.get('keyword_planner_idea_count', 0)}."
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


def _fetch_optional_shopping_product_performance(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    zero_row_lookbacks: list[int] = []
    latest_summary: dict[str, float | int | str] | None = None
    for lookback_days in SHOPPING_PRODUCT_PERFORMANCE_LOOKBACK_DAYS:
        try:
            response = _post_google_ads_search_stream(
                client,
                credentials,
                access_token,
                _shopping_product_performance_query(lookback_days),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return _shopping_product_performance_http_failure_summary(exc, lookback_days)
        except httpx.HTTPError as exc:
            return (
                {
                    "shopping_product_performance_status": "blocked",
                    "shopping_product_performance_blocker": type(exc).__name__,
                    "shopping_product_performance_lookback_days": lookback_days,
                    "shopping_product_performance_row_count": 0,
                },
                [],
            )
        summary, facts = _summarize_shopping_product_performance_response(
            response.json(),
            lookback_days,
        )
        row_count = _int_metric(summary["shopping_product_performance_row_count"])
        if row_count > 0:
            if zero_row_lookbacks:
                summary["shopping_product_performance_zero_row_lookbacks"] = ",".join(
                    str(days) for days in zero_row_lookbacks
                )
            return summary, facts
        zero_row_lookbacks.append(lookback_days)
        latest_summary = summary

    if latest_summary is None:
        return (
            {
                "shopping_product_performance_status": "ready",
                "shopping_product_performance_row_count": 0,
            },
            [],
        )
    latest_summary["shopping_product_performance_zero_row_lookbacks"] = ",".join(
        str(days) for days in zero_row_lookbacks
    )
    return latest_summary, []


def _fetch_optional_shopping_product_state(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    try:
        response = _post_google_ads_search_stream(
            client,
            credentials,
            access_token,
            SHOPPING_PRODUCT_STATE_QUERY,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return _shopping_product_state_http_failure_summary(exc)
    except httpx.HTTPError as exc:
        return (
            {
                "shopping_product_state_status": "blocked",
                "shopping_product_state_blocker": type(exc).__name__,
                "shopping_product_state_row_count": 0,
            },
            [],
        )
    return _summarize_shopping_product_state_response(response.json())


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


def _fetch_optional_demand_gen_ad_group_ads(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    try:
        response = _post_google_ads_search_stream(
            client,
            credentials,
            access_token,
            DEMAND_GEN_AD_GROUP_AD_QUERY,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return _demand_gen_http_failure_summary("ad_group_ad", exc)
    except httpx.HTTPError as exc:
        return (
            {
                "demand_gen_ad_group_ad_status": "blocked",
                "demand_gen_ad_group_ad_blocker": type(exc).__name__,
                "demand_gen_ad_group_ad_row_count": 0,
            },
            [],
        )
    return _summarize_demand_gen_ad_group_ad_response(response.json())


def _fetch_optional_demand_gen_creative_assets(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    try:
        response = _post_google_ads_search_stream(
            client,
            credentials,
            access_token,
            DEMAND_GEN_CREATIVE_ASSET_QUERY,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return _demand_gen_http_failure_summary("creative_asset", exc)
    except httpx.HTTPError as exc:
        return (
            {
                "demand_gen_creative_asset_status": "blocked",
                "demand_gen_creative_asset_blocker": type(exc).__name__,
                "demand_gen_creative_asset_row_count": 0,
            },
            [],
        )
    return _summarize_demand_gen_creative_asset_response(response.json())


def _fetch_optional_keyword_planner_ideas(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
    search_term_facts: list[VendorMetricFact],
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    seed_terms = _keyword_planner_seed_terms(search_term_facts)
    if not seed_terms:
        return (
            {
                "keyword_planner_status": "blocked",
                "keyword_planner_blocker": "missing_seed_terms",
                "keyword_planner_seed_term_count": 0,
                "keyword_planner_idea_count": 0,
            },
            [],
        )

    customer_id = credentials["customer_id"]
    language_resource = _keyword_planner_language_resource()
    geo_target_resource = _keyword_planner_geo_target_resource()
    try:
        response = client.post(
            f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
            f"{customer_id}:generateKeywordIdeas",
            headers={
                "Authorization": f"Bearer {access_token}",
                "developer-token": str(credentials["developer_token"]),
                "login-customer-id": str(credentials["login_customer_id"]),
                "Content-Type": "application/json",
            },
            json={
                "keywordSeed": {"keywords": seed_terms},
                "language": language_resource,
                "geoTargetConstants": [geo_target_resource],
                "keywordPlanNetwork": KEYWORD_PLANNER_NETWORK,
                "includeAdultKeywords": False,
                "pageSize": KEYWORD_PLANNER_IDEA_RESULT_LIMIT,
            },
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return _keyword_planner_http_failure_summary(exc)
    except httpx.HTTPError as exc:
        return (
            {
                "keyword_planner_status": "blocked",
                "keyword_planner_blocker": type(exc).__name__,
                "keyword_planner_seed_term_count": len(seed_terms),
                "keyword_planner_idea_count": 0,
            },
            [],
        )
    return _summarize_keyword_planner_response(
        response.json(),
        seed_terms=seed_terms,
        language_resource=language_resource,
        geo_target_resource=geo_target_resource,
    )


def _post_google_ads_search_stream(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
    query: str,
) -> httpx.Response:
    customer_id = credentials["customer_id"]
    return client.post(
        f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
        f"{customer_id}/googleAds:searchStream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": str(credentials["developer_token"]),
            "login-customer-id": str(credentials["login_customer_id"]),
            "Content-Type": "application/json",
        },
        json={"query": query},
    )


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


def _keyword_planner_seed_terms(search_term_facts: list[VendorMetricFact]) -> list[str]:
    grouped: dict[str, dict[str, int]] = {}
    for fact in search_term_facts:
        if fact.name not in {
            "search_term_clicks",
            "search_term_impressions",
            "search_term_cost_micros",
        }:
            continue
        search_term = fact.dimensions.get("search_term")
        if not search_term:
            continue
        normalized = " ".join(search_term.split())
        if len(normalized) < 3:
            continue
        row = grouped.setdefault(
            normalized,
            {"clicks": 0, "impressions": 0, "cost_micros": 0},
        )
        if fact.name == "search_term_clicks":
            row["clicks"] = _int_metric(fact.value)
        elif fact.name == "search_term_impressions":
            row["impressions"] = _int_metric(fact.value)
        elif fact.name == "search_term_cost_micros":
            row["cost_micros"] = _int_metric(fact.value)
    return [
        term
        for term, _metrics in sorted(
            grouped.items(),
            key=lambda item: (
                -item[1]["cost_micros"],
                -item[1]["clicks"],
                -item[1]["impressions"],
                item[0],
            ),
        )[:KEYWORD_PLANNER_IDEA_SOURCE_TERM_LIMIT]
    ]


def _keyword_planner_language_resource() -> str:
    configured = variable_value("GOOGLE_ADS_KEYWORD_PLANNER_LANGUAGE_RESOURCE")
    return configured or KEYWORD_PLANNER_DEFAULT_LANGUAGE_RESOURCE


def _keyword_planner_geo_target_resource() -> str:
    configured = variable_value("GOOGLE_ADS_KEYWORD_PLANNER_GEO_TARGET_RESOURCE")
    return configured or KEYWORD_PLANNER_DEFAULT_GEO_TARGET_RESOURCE


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


def _shopping_product_performance_query(
    lookback_days: int,
    today: date | None = None,
) -> str:
    end_date = today or date.today()
    start_date = end_date - timedelta(days=lookback_days)
    return SHOPPING_PRODUCT_PERFORMANCE_QUERY_TEMPLATE.format(
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


def _summarize_recommendation_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    recommendation_types: set[str] = set()
    campaign_count = 0
    impact_row_count = 0
    impact_metric_count = 0
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
            impact_facts = _recommendation_impact_metric_facts(recommendation, dimensions)
            if impact_facts:
                impact_row_count += 1
                impact_metric_count += len(impact_facts)
                metric_facts.extend(impact_facts)
    return (
        {
            "recommendation_query": "active_recommendations",
            "recommendation_row_count": len(rows),
            "recommendation_campaign_count": campaign_count,
            "recommendation_impact_row_count": impact_row_count,
            "recommendation_impact_metric_count": impact_metric_count,
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


def _summarize_keyword_planner_response(
    payload: Any,
    *,
    seed_terms: list[str],
    language_resource: str,
    geo_target_resource: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        results = []
    metric_facts: list[VendorMetricFact] = []
    max_avg_monthly_searches = 0
    competition_values: set[str] = set()
    seed_terms_label = _keyword_planner_seed_terms_label(seed_terms)
    for result in results:
        if not isinstance(result, dict):
            continue
        idea_text = result.get("text")
        if not isinstance(idea_text, str) or not idea_text.strip():
            continue
        metrics = result.get("keywordIdeaMetrics", result.get("keyword_idea_metrics", {}))
        if not isinstance(metrics, dict):
            metrics = {}
        avg_monthly_searches = _int_metric(
            metrics.get(
                "avgMonthlySearches",
                metrics.get("avg_monthly_searches"),
            )
        )
        competition = metrics.get("competition")
        if not isinstance(competition, str):
            competition = None
        competition_index = _optional_int_metric(
            metrics.get("competitionIndex", metrics.get("competition_index"))
        )
        low_bid_micros = _optional_int_metric(
            metrics.get(
                "lowTopOfPageBidMicros",
                metrics.get("low_top_of_page_bid_micros"),
            )
        )
        high_bid_micros = _optional_int_metric(
            metrics.get(
                "highTopOfPageBidMicros",
                metrics.get("high_top_of_page_bid_micros"),
            )
        )
        dimensions = {
            "keyword_idea_text": _clip_dimension(idea_text),
            "seed_terms": seed_terms_label,
            "seed_terms_count": str(len(seed_terms)),
            "language_resource": language_resource,
            "geo_target_resource": geo_target_resource,
        }
        if competition:
            dimensions["competition"] = competition
            competition_values.add(competition)
        max_avg_monthly_searches = max(max_avg_monthly_searches, avg_monthly_searches)
        metric_facts.extend(
            [
                VendorMetricFact(
                    "keyword_planner_idea_available",
                    1,
                    dimensions,
                    period="keyword_planner",
                ),
                VendorMetricFact(
                    "keyword_planner_avg_monthly_searches",
                    avg_monthly_searches,
                    dimensions,
                    period="keyword_planner",
                ),
            ]
        )
        if competition_index is not None:
            metric_facts.append(
                VendorMetricFact(
                    "keyword_planner_competition_index",
                    competition_index,
                    dimensions,
                    period="keyword_planner",
                )
            )
        if low_bid_micros is not None:
            metric_facts.append(
                VendorMetricFact(
                    "keyword_planner_low_top_of_page_bid_micros",
                    low_bid_micros,
                    dimensions,
                    period="keyword_planner",
                )
            )
        if high_bid_micros is not None:
            metric_facts.append(
                VendorMetricFact(
                    "keyword_planner_high_top_of_page_bid_micros",
                    high_bid_micros,
                    dimensions,
                    period="keyword_planner",
                )
            )
    return (
        {
            "keyword_planner_status": "ready",
            "keyword_planner_seed_term_count": len(seed_terms),
            "keyword_planner_idea_count": sum(
                1 for fact in metric_facts if fact.name == "keyword_planner_idea_available"
            ),
            "keyword_planner_avg_monthly_searches_max": max_avg_monthly_searches,
            "keyword_planner_competition_values": ",".join(sorted(competition_values)),
            "keyword_planner_language_resource": language_resource,
            "keyword_planner_geo_target_resource": geo_target_resource,
            "keyword_planner_network": KEYWORD_PLANNER_NETWORK,
        },
        metric_facts,
    )


def _keyword_planner_seed_terms_label(seed_terms: list[str]) -> str:
    return _clip_dimension(", ".join(seed_terms[:5]))


def _clip_dimension(value: str, limit: int = 240) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _summarize_search_term_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows, payload_valid = strict_search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    metric_facts: list[VendorMetricFact] = []
    mapped_landing_rows = 0
    blocked_landing_rows = 0
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
        dimensions.update(search_term_landing_dimensions(row))
        if dimensions.get(ADS_LANDING_MAPPING_STATUS) == ADS_LANDING_RESOLVED:
            mapped_landing_rows += 1
        else:
            blocked_landing_rows += 1
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "search_term_clicks", row_clicks, dimensions, ADS_DEMAND_PERIOD
                    ),
                    VendorMetricFact(
                        "search_term_impressions",
                        row_impressions,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                    VendorMetricFact(
                        "search_term_cost_micros",
                        row_cost_micros,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                    VendorMetricFact(
                        "search_term_conversions",
                        row_conversions,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                    VendorMetricFact(
                        "search_term_conversion_value",
                        row_conversion_value,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                ]
            )
    metric_facts.append(
        VendorMetricFact(
            ADS_SEARCH_TERM_PAYLOAD_STATUS,
            "ready" if payload_valid else "blocked",
            period=ADS_DEMAND_PERIOD,
        )
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
            ADS_SEARCH_TERM_PAYLOAD_STATUS: "ready" if payload_valid else "blocked",
            "search_term_landing_mapped_row_count": mapped_landing_rows,
            "search_term_landing_blocked_row_count": blocked_landing_rows,
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


def _summarize_shopping_product_performance_response(
    payload: Any,
    lookback_days: int,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    product_ids: set[str] = set()
    metric_facts: list[VendorMetricFact] = []
    fact_period = f"shopping_product_performance_{lookback_days}d"
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
        dimensions = _shopping_product_dimensions(row)
        product_id = dimensions.get("product_id")
        if product_id:
            product_ids.add(product_id)
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "shopping_product_clicks",
                        row_clicks,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_impressions",
                        row_impressions,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_cost_micros",
                        row_cost_micros,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_conversions",
                        row_conversions,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_conversion_value",
                        row_conversion_value,
                        dimensions,
                        period=fact_period,
                    ),
                ]
            )
    return (
        {
            "shopping_product_performance_status": "ready",
            "shopping_product_performance_query": (
                f"shopping_performance_view_last_{lookback_days}_days"
            ),
            "shopping_product_performance_lookback_days": lookback_days,
            "shopping_product_performance_row_count": len(rows),
            "shopping_product_performance_product_count": len(product_ids),
            "shopping_product_clicks": clicks,
            "shopping_product_impressions": impressions,
            "shopping_product_cost_micros": cost_micros,
            "shopping_product_conversions": conversions,
            "shopping_product_conversion_value": conversion_value,
        },
        metric_facts,
    )


def _summarize_shopping_product_state_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    product_ids: set[str] = set()
    statuses: Counter[str] = Counter()
    availability: Counter[str] = Counter()
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        shopping_product = row.get("shoppingProduct", row.get("shopping_product", {}))
        if not isinstance(shopping_product, dict):
            continue
        dimensions = _shopping_product_state_dimensions(shopping_product)
        product_id = dimensions.get("product_id")
        if product_id:
            product_ids.add(product_id)
        status = _string_metric(shopping_product.get("status"))
        if status:
            statuses[status] += 1
        product_availability = _string_metric(shopping_product.get("availability"))
        if product_availability:
            availability[product_availability] += 1
        if not dimensions:
            continue
        metric_facts.append(
            VendorMetricFact(
                "shopping_product_state_available",
                1,
                dimensions,
                period="shopping_product_state",
            )
        )
        if status:
            metric_facts.append(
                VendorMetricFact(
                    "shopping_product_status",
                    status,
                    dimensions,
                    period="shopping_product_state",
                )
            )
        if product_availability:
            metric_facts.append(
                VendorMetricFact(
                    "shopping_product_availability",
                    product_availability,
                    dimensions,
                    period="shopping_product_state",
                )
            )
        price_micros = _int_metric(shopping_product.get("priceMicros"))
        if price_micros:
            metric_facts.append(
                VendorMetricFact(
                    "shopping_product_price_micros",
                    price_micros,
                    dimensions,
                    period="shopping_product_state",
                )
            )
    return (
        {
            "shopping_product_state_status": "ready",
            "shopping_product_state_query": "shopping_product_current_state",
            "shopping_product_state_row_count": len(rows),
            "shopping_product_state_product_count": len(product_ids),
            "shopping_product_state_eligible_count": statuses.get("ELIGIBLE", 0),
            "shopping_product_state_limited_count": statuses.get("ELIGIBLE_LIMITED", 0),
            "shopping_product_state_not_eligible_count": statuses.get("NOT_ELIGIBLE", 0),
            "shopping_product_state_status_values": ",".join(sorted(statuses)),
            "shopping_product_state_availability_values": ",".join(sorted(availability)),
        },
        metric_facts,
    )


def _summarize_demand_gen_ad_group_ad_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    ad_type_counts: Counter[str] = Counter()
    final_url_count = 0
    asset_reference_count = 0
    for row in rows:
        dimensions = _demand_gen_ad_dimensions(row)
        if not dimensions:
            continue
        ad_type = dimensions.get("ad_type", "UNKNOWN")
        ad_type_counts[ad_type] += 1
        ad_group_ad = row.get("adGroupAd", row.get("ad_group_ad", {}))
        ad = ad_group_ad.get("ad", {}) if isinstance(ad_group_ad, dict) else {}
        row_final_url_count = _list_count(ad, "finalUrls", "final_urls")
        row_asset_reference_count = _demand_gen_ad_asset_reference_count(ad)
        final_url_count += row_final_url_count
        asset_reference_count += row_asset_reference_count
        metric_facts.extend(
            [
                VendorMetricFact(
                    "demand_gen_ad_available",
                    1,
                    dimensions,
                    period="demand_gen_ad_inventory",
                ),
                VendorMetricFact(
                    "demand_gen_ad_final_url_count",
                    row_final_url_count,
                    dimensions,
                    period="demand_gen_ad_inventory",
                ),
                VendorMetricFact(
                    "demand_gen_ad_asset_reference_count",
                    row_asset_reference_count,
                    dimensions,
                    period="demand_gen_ad_inventory",
                ),
            ]
        )
    return (
        {
            "demand_gen_ad_group_ad_status": "ready",
            "demand_gen_ad_group_ad_query": "demand_gen_ad_group_ad_inventory",
            "demand_gen_ad_group_ad_row_count": len(rows),
            "demand_gen_multi_asset_ad_count": ad_type_counts["DEMAND_GEN_MULTI_ASSET_AD"],
            "demand_gen_carousel_ad_count": ad_type_counts["DEMAND_GEN_CAROUSEL_AD"],
            "demand_gen_video_responsive_ad_count": ad_type_counts[
                "DEMAND_GEN_VIDEO_RESPONSIVE_AD"
            ],
            "demand_gen_final_url_count": final_url_count,
            "demand_gen_asset_reference_count": asset_reference_count,
        },
        metric_facts,
    )


def _summarize_demand_gen_creative_asset_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    impressions = 0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        dimensions = _demand_gen_creative_asset_dimensions(row)
        if not dimensions:
            continue
        metrics = row.get("metrics", {})
        row_impressions = _int_metric(metrics.get("impressions"))
        impressions += row_impressions
        metric_facts.append(
            VendorMetricFact(
                "demand_gen_creative_asset_impressions",
                row_impressions,
                dimensions,
                period="demand_gen_creative_asset",
            )
        )
    return (
        {
            "demand_gen_creative_asset_status": "ready",
            "demand_gen_creative_asset_query": "demand_gen_carousel_asset_performance",
            "demand_gen_creative_asset_row_count": len(rows),
            "demand_gen_creative_asset_impressions": impressions,
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


def _demand_gen_ad_asset_reference_count(ad: Any) -> int:
    if not isinstance(ad, dict):
        return 0
    return (
        _demand_gen_multi_asset_reference_count(ad)
        + _demand_gen_carousel_asset_reference_count(ad)
        + _demand_gen_video_responsive_asset_reference_count(ad)
    )


def _demand_gen_multi_asset_reference_count(ad: dict[str, Any]) -> int:
    info = ad.get("demandGenMultiAssetAd", ad.get("demand_gen_multi_asset_ad", {}))
    if not isinstance(info, dict):
        return 0
    return sum(
        _list_count(info, camel_key, snake_key)
        for camel_key, snake_key in (
            ("marketingImages", "marketing_images"),
            ("squareMarketingImages", "square_marketing_images"),
            ("portraitMarketingImages", "portrait_marketing_images"),
            ("classicDisplayImages", "classic_display_images"),
            ("logoImages", "logo_images"),
        )
    )


def _demand_gen_carousel_asset_reference_count(ad: dict[str, Any]) -> int:
    info = ad.get("demandGenCarouselAd", ad.get("demand_gen_carousel_ad", {}))
    if not isinstance(info, dict):
        return 0
    return _list_count(info, "logoImage", "logo_image") + _list_count(
        info,
        "carouselCards",
        "carousel_cards",
    )


def _demand_gen_video_responsive_asset_reference_count(ad: dict[str, Any]) -> int:
    info = ad.get(
        "demandGenVideoResponsiveAd",
        ad.get("demand_gen_video_responsive_ad", {}),
    )
    if not isinstance(info, dict):
        return 0
    return sum(
        _list_count(info, camel_key, snake_key)
        for camel_key, snake_key in (
            ("logoImages", "logo_images"),
            ("callToActions", "call_to_actions"),
            ("videos", "videos"),
        )
    )


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


def _shopping_product_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    segments = row.get("segments", {})
    if not isinstance(segments, dict):
        return dimensions
    product_item_id = segments.get("productItemId", segments.get("product_item_id"))
    if isinstance(product_item_id, str) and product_item_id.strip():
        normalized_product_id = product_item_id.strip()
        dimensions["product_id"] = normalized_product_id
        dimensions["item_id"] = normalized_product_id
        dimensions["product_item_id"] = normalized_product_id
    product_title = segments.get("productTitle", segments.get("product_title"))
    if isinstance(product_title, str) and product_title.strip():
        dimensions["product_title"] = _clip_dimension(product_title)
    return dimensions


def _shopping_product_state_dimensions(shopping_product: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    resource_name = _string_metric(
        shopping_product.get("resourceName", shopping_product.get("resource_name"))
    )
    if resource_name:
        dimensions["shopping_product_resource_name"] = _clip_dimension(resource_name)
    item_id = _string_metric(shopping_product.get("itemId", shopping_product.get("item_id")))
    if item_id:
        dimensions["product_id"] = item_id
        dimensions["item_id"] = item_id
        dimensions["product_item_id"] = item_id
    merchant_center_id = shopping_product.get(
        "merchantCenterId",
        shopping_product.get("merchant_center_id"),
    )
    if merchant_center_id is not None:
        dimensions["merchant_center_id"] = str(merchant_center_id)
    for api_key, fallback_key, dimension_key in (
        ("channel", "channel", "product_channel"),
        ("languageCode", "language_code", "language_code"),
        ("feedLabel", "feed_label", "feed_label"),
        ("currencyCode", "currency_code", "currency_code"),
        ("status", "status", "product_status"),
        ("availability", "availability", "product_availability"),
    ):
        value = _string_metric(shopping_product.get(api_key, shopping_product.get(fallback_key)))
        if value:
            dimensions[dimension_key] = value
    title = _string_metric(shopping_product.get("title"))
    if title:
        dimensions["product_title"] = _clip_dimension(title)
    target_countries = shopping_product.get(
        "targetCountries",
        shopping_product.get("target_countries"),
    )
    if isinstance(target_countries, list):
        countries = sorted(str(country) for country in target_countries if country)
        if countries:
            dimensions["target_countries"] = ",".join(countries)
    return dimensions


def _demand_gen_ad_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    ad_group = row.get("adGroup", row.get("ad_group", {}))
    if isinstance(ad_group, dict):
        ad_group_id = ad_group.get("id")
        if ad_group_id is not None:
            dimensions["ad_group_id"] = str(ad_group_id)
        ad_group_name = ad_group.get("name")
        if isinstance(ad_group_name, str) and ad_group_name:
            dimensions["ad_group_name"] = ad_group_name
    ad_group_ad = row.get("adGroupAd", row.get("ad_group_ad", {}))
    if not isinstance(ad_group_ad, dict):
        return dimensions
    ad_status = ad_group_ad.get("status")
    if isinstance(ad_status, str) and ad_status:
        dimensions["ad_status"] = ad_status
    ad = ad_group_ad.get("ad", {})
    if not isinstance(ad, dict):
        return dimensions
    ad_id = ad.get("id")
    if ad_id is not None:
        dimensions["ad_id"] = str(ad_id)
    ad_type = ad.get("type")
    if isinstance(ad_type, str) and ad_type:
        dimensions["ad_type"] = ad_type
    return dimensions


def _demand_gen_creative_asset_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    asset = row.get("asset", {})
    if isinstance(asset, dict):
        asset_id = asset.get("id")
        if asset_id is not None:
            dimensions["asset_id"] = str(asset_id)
        asset_type = asset.get("type")
        if isinstance(asset_type, str) and asset_type:
            dimensions["asset_type"] = asset_type
    asset_view = row.get("adGroupAdAssetView", row.get("ad_group_ad_asset_view", {}))
    if isinstance(asset_view, dict):
        field_type = asset_view.get("fieldType", asset_view.get("field_type"))
        if isinstance(field_type, str) and field_type:
            dimensions["field_type"] = field_type
    return dimensions


def _recommendation_dimensions(recommendation: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    resource_name = recommendation.get("resourceName", recommendation.get("resource_name"))
    if isinstance(resource_name, str) and resource_name:
        dimensions["recommendation_resource_name"] = resource_name
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


def _recommendation_impact_metric_facts(
    recommendation: dict[str, Any],
    dimensions: dict[str, str],
) -> list[VendorMetricFact]:
    impact = recommendation.get("impact")
    if not isinstance(impact, dict):
        return []
    metric_facts: list[VendorMetricFact] = []
    for prefix, metrics in (
        ("base", impact.get("baseMetrics", impact.get("base_metrics"))),
        ("potential", impact.get("potentialMetrics", impact.get("potential_metrics"))),
    ):
        if not isinstance(metrics, dict):
            continue
        metric_facts.extend(_recommendation_impact_metrics_for_prefix(prefix, metrics, dimensions))
    return metric_facts


def _recommendation_impact_metrics_for_prefix(
    prefix: str,
    metrics: dict[str, Any],
    dimensions: dict[str, str],
) -> list[VendorMetricFact]:
    metric_facts: list[VendorMetricFact] = []
    int_metrics = {
        "clicks": _optional_int_metric(metrics.get("clicks")),
        "impressions": _optional_int_metric(metrics.get("impressions")),
        "cost_micros": _optional_int_metric(metrics.get("costMicros", metrics.get("cost_micros"))),
    }
    float_metrics = {
        "conversions": _optional_float_metric(metrics.get("conversions")),
        "conversion_value": _optional_float_metric(
            metrics.get("conversionsValue", metrics.get("conversions_value"))
        ),
    }
    for name, int_value in int_metrics.items():
        if int_value is not None:
            metric_facts.append(
                VendorMetricFact(
                    f"recommendation_impact_{prefix}_{name}",
                    int_value,
                    dimensions,
                    period="recommendation_impact",
                )
            )
    for name, float_value in float_metrics.items():
        if float_value is not None:
            metric_facts.append(
                VendorMetricFact(
                    f"recommendation_impact_{prefix}_{name}",
                    float_value,
                    dimensions,
                    period="recommendation_impact",
                )
            )
    return metric_facts


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
