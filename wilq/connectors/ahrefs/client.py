from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx

from wilq.connectors.vendor import VendorReadResult
from wilq.credentials.runtime import variable_source, variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

AHREFS_API_BASE = "https://api.ahrefs.com/v3"


def refresh_ahrefs_domain_rating(
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    token = variable_value("AHREFS_API_TOKEN")
    if not token:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="Ahrefs vendor read blocked by missing credential names: AHREFS_API_TOKEN.",
            errors=["Ahrefs API token is missing."],
        )
    target = _target()
    if target is None:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "Ahrefs vendor read blocked by missing config names: "
                "AHREFS_TARGET or WORDPRESS_EKOLOGUS_URL."
            ),
            errors=["Ahrefs target URL/domain is missing."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        try:
            metric_summary = _fetch_domain_rating(client, token, target)
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
            "Ahrefs vendor read completed through Site Explorer domain-rating. "
            f"Domain rating: {metric_summary['domain_rating']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
    )


def _target() -> str | None:
    for name in ("AHREFS_TARGET", "WORDPRESS_EKOLOGUS_URL", "MIS_PRIMARY_SITE_URL"):
        value = variable_value(name)
        normalized = _normalize_target(value)
        if normalized:
            return normalized
    return None


def _normalize_target(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    parsed = urlparse(stripped)
    if parsed.hostname:
        return _clean_hostname(parsed.hostname)
    return _clean_hostname(stripped.split("/", 1)[0])


def _clean_hostname(value: str) -> str | None:
    return value.strip().lower().removeprefix("www.").strip(".") or None


def _fetch_domain_rating(
    client: httpx.Client,
    token: str,
    target: str,
) -> dict[str, float | int | str]:
    report_date = _report_date()
    response = client.get(
        f"{AHREFS_API_BASE}/site-explorer/domain-rating",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={"target": target, "date": report_date, "output": "json"},
    )
    response.raise_for_status()
    payload = response.json()
    domain_rating = payload.get("domain_rating", {}) if isinstance(payload, dict) else {}
    if not isinstance(domain_rating, dict):
        domain_rating = {}
    return {
        "api": "ahrefs_site_explorer_domain_rating",
        "date": report_date,
        "target_source": _target_source_label(),
        "domain_rating": _float_metric(domain_rating.get("domain_rating")),
        "ahrefs_rank": _int_metric(domain_rating.get("ahrefs_rank")),
    }


def _report_date() -> str:
    return (datetime.now(UTC).date() - timedelta(days=1)).isoformat()


def _target_source_label() -> str:
    for name in ("AHREFS_TARGET", "WORDPRESS_EKOLOGUS_URL", "MIS_PRIMARY_SITE_URL"):
        if variable_value(name):
            return variable_source(name) or "configured"
    return "missing"


def _http_failure_result(exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Ahrefs Site Explorer domain-rating failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"Ahrefs Site Explorer domain-rating HTTP {status_code}."],
    )


def _transport_failure_result(exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"Ahrefs Site Explorer domain-rating failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"Ahrefs Site Explorer domain-rating {type(exc).__name__}."],
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
