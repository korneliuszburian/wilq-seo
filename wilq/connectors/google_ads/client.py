from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import httpx

from wilq.connectors.vendor import VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

GOOGLE_ADS_API_VERSION = "v24"
OAUTH_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
SAFE_ERROR_LABEL = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


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
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros
FROM campaign
WHERE segments.date DURING LAST_7_DAYS
  AND campaign.status != 'REMOVED'
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
            metric_summary = _fetch_campaign_summary(client, credentials, access_token)
        except httpx.HTTPStatusError as exc:
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
            f"Rows: {metric_summary['row_count']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
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
    if not isinstance(payload, dict):
        return None

    error = payload.get("error")
    details: list[str] = []
    if isinstance(error, str):
        _append_safe_detail(details, "oauth_error", error)
    elif isinstance(error, dict):
        code = error.get("code")
        status = error.get("status")
        if isinstance(code, int):
            details.append(f"api_code={code}")
        if isinstance(status, str):
            _append_safe_detail(details, "api_status", status)

    if not details:
        return None
    return ", ".join(details)


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
) -> dict[str, float | int | str]:
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


def _summarize_search_stream_response(payload: Any) -> dict[str, float | int | str]:
    rows = _search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    for row in rows:
        metrics = row.get("metrics", {})
        clicks += _int_metric(metrics.get("clicks"))
        impressions += _int_metric(metrics.get("impressions"))
        cost_micros += _int_metric(metrics.get("costMicros", metrics.get("cost_micros")))
    return {
        "api_version": GOOGLE_ADS_API_VERSION,
        "query": "campaign_last_7_days",
        "row_count": len(rows),
        "clicks": clicks,
        "impressions": impressions,
        "cost_micros": cost_micros,
    }


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
