"""Google Ads transport, authentication, API fetches, and refresh entrypoint."""
from __future__ import annotations

import sys
from collections.abc import Mapping
from datetime import date, timedelta
from types import ModuleType

import httpx

from wilq.connectors.google_ads.ad_landing_pages import (
    AdsLandingInventory,
)
from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.content.canonical.redacted_landing import build_redacted_landing_reference
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

from . import budget as _budget
from . import campaigns as _campaigns
from . import reports as _reports
from . import search_terms as _search_terms
from . import shared as _shared
from .campaigns import (
    AD_FINAL_URL_INVENTORY_QUERY,
    CAMPAIGN_SUMMARY_QUERY,
    CUSTOMER_CLIENT_QUERY,
    _summarize_customer_client_response,
    _summarize_search_stream_response,
)
from .reports import (
    CHANGE_EVENT_LOOKBACK_DAYS,
    CHANGE_EVENT_SUMMARY_QUERY_TEMPLATE,
    DEMAND_GEN_AD_GROUP_AD_QUERY,
    DEMAND_GEN_CREATIVE_ASSET_QUERY,
    RECOMMENDATION_SUMMARY_QUERY,
    SHOPPING_PRODUCT_PERFORMANCE_LOOKBACK_DAYS,
    SHOPPING_PRODUCT_PERFORMANCE_QUERY_TEMPLATE,
    SHOPPING_PRODUCT_STATE_QUERY,
    _summarize_change_event_response,
    _summarize_demand_gen_ad_group_ad_response,
    _summarize_demand_gen_creative_asset_response,
    _summarize_recommendation_response,
    _summarize_shopping_product_performance_response,
    _summarize_shopping_product_state_response,
)
from .search_terms import (
    KEYWORD_MATCH_CONTEXT_QUERY,
    KEYWORD_PLANNER_IDEA_RESULT_LIMIT,
    KEYWORD_PLANNER_NETWORK,
    SEARCH_TERM_SAFETY_LOOKBACK_DAYS,
    SEARCH_TERM_SAFETY_QUERY_TEMPLATE,
    SEARCH_TERM_SUMMARY_QUERY,
    _keyword_planner_geo_target_resource,
    _keyword_planner_language_resource,
    _keyword_planner_seed_terms,
    _summarize_keyword_match_context_response,
    _summarize_keyword_planner_response,
    _summarize_search_term_response,
    _summarize_search_term_safety_response,
)
from .shared import (
    GOOGLE_ADS_API_VERSION,
    _demand_gen_http_failure_summary,
    _http_failure_result,
    _int_metric,
    _keyword_planner_http_failure_summary,
    _sanitized_http_error_detail,
    _search_stream_rows,
    _shopping_product_performance_http_failure_summary,
    _shopping_product_state_http_failure_summary,
    _transport_failure_result,
)

OAUTH_ENDPOINT = "https://oauth2.googleapis.com/token"

GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"

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
            landing_inventory, landing_inventory_status = _fetch_ad_final_url_inventory(
                client,
                credentials,
                access_token,
            )
            search_term_summary, search_term_facts = _fetch_search_term_summary(
                client,
                credentials,
                access_token,
                landing_inventory=landing_inventory,
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
            metric_summary["search_term_landing_inventory_status"] = landing_inventory_status
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

def _fetch_ad_final_url_inventory(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
) -> tuple[AdsLandingInventory, str]:
    """Read ad final URLs separately because search-term GAQL may reject them."""
    customer_id = credentials["customer_id"]
    try:
        response = client.post(
            f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/"
            f"{customer_id}/googleAds:searchStream",
            headers={
                "Authorization": f"Bearer {access_token}",
                "developer-token": str(credentials["developer_token"]),
                "login-customer-id": str(credentials["login_customer_id"]),
                "Content-Type": "application/json",
            },
            json={"query": AD_FINAL_URL_INVENTORY_QUERY},
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return {}, "blocked"
    rows = _search_stream_rows(response.json())
    inventory: AdsLandingInventory = {}
    for row in rows:
        campaign = row.get("campaign", {})
        ad_group = row.get("adGroup", row.get("ad_group", {}))
        ad_group_ad = row.get("adGroupAd", row.get("ad_group_ad", {}))
        ad = ad_group_ad.get("ad", {}) if isinstance(ad_group_ad, dict) else {}
        if not isinstance(campaign, dict) or not isinstance(ad_group, dict) or not isinstance(
            ad, dict
        ):
            continue
        campaign_id = campaign.get("id")
        ad_group_id = ad_group.get("id")
        final_urls = ad.get("finalUrls", ad.get("final_urls", []))
        if campaign_id is None or ad_group_id is None or not isinstance(final_urls, list):
            continue
        references = inventory.setdefault((str(campaign_id), str(ad_group_id)), set())
        for url in final_urls:
            reference = build_redacted_landing_reference(url if isinstance(url, str) else None)
            references.add(
                (
                    reference.status,
                    reference.identity_sha256,
                    reference.tracking_parameters_removed,
                    reference.has_functional_query,
                )
            )
    return inventory, "ready"

def _fetch_search_term_summary(
    client: httpx.Client,
    credentials: Mapping[str, str | None],
    access_token: str,
    *,
    landing_inventory: AdsLandingInventory | None = None,
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
    return _summarize_search_term_response(response.json(), landing_inventory=landing_inventory)

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

__all__ = [
    "GOOGLE_ADS_API_VERSION",
    "GOOGLE_ADS_SCOPE",
    "OAUTH_ENDPOINT",
    "refresh_google_ads_campaign_summary",
]

_FORWARD_TARGETS = (
    _budget,
    _campaigns,
    _reports,
    _search_terms,
    _shared,
)


class _Facade(ModuleType):
    """Forward legacy monkeypatch targets to their decomposed owners."""

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        for target in _FORWARD_TARGETS:
            if hasattr(target, name):
                setattr(target, name, value)


sys.modules[__name__].__class__ = _Facade
