from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx

from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_source, variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus

AHREFS_API_BASE = "https://api.ahrefs.com/v3"
AHREFS_ORGANIC_COMPETITOR_LIMIT_DEFAULT = 10
AHREFS_ORGANIC_COMPETITOR_LIMIT_MAX = 25


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
        metric_facts: list[VendorMetricFact] = []
        errors: list[str] = []
        try:
            competitor_summary, competitor_facts = _fetch_organic_competitors(
                client,
                token,
                target,
            )
            metric_summary.update(competitor_summary)
            metric_facts.extend(competitor_facts)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            metric_summary.update(
                {
                    "organic_competitor_read_status": f"http_{status_code}",
                    "organic_competitor_rows": 0,
                }
            )
            errors.append(f"Ahrefs Site Explorer organic-competitors HTTP {status_code}.")
        except httpx.HTTPError as exc:
            metric_summary.update(
                {
                    "organic_competitor_read_status": type(exc).__name__,
                    "organic_competitor_rows": 0,
                }
            )
            errors.append(
                f"Ahrefs Site Explorer organic-competitors {type(exc).__name__}."
            )
    finally:
        if owns_client:
            client.close()

    return VendorReadResult(
        status=ConnectorRefreshStatus.completed,
        summary=(
            "Ahrefs vendor read completed through Site Explorer domain-rating. "
            f"Domain rating: {metric_summary['domain_rating']}. "
            f"Organic competitor rows: {metric_summary['organic_competitor_rows']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
        metric_facts=metric_facts,
        errors=errors,
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


def _fetch_organic_competitors(
    client: httpx.Client,
    token: str,
    target: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    report_date = _report_date()
    country = _organic_competitor_country()
    limit = _organic_competitor_limit()
    response = client.get(
        f"{AHREFS_API_BASE}/site-explorer/organic-competitors",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={
            "target": target,
            "country": country,
            "date": report_date,
            "limit": limit,
            "output": "json",
            "select": ",".join(
                [
                    "competitor_domain",
                    "competitor_url",
                    "keywords_common",
                    "keywords_competitor",
                    "keywords_target",
                    "pages",
                    "share",
                ]
            ),
        },
    )
    response.raise_for_status()
    rows = _response_rows(response.json(), "organic_competitors")[:limit]
    facts = [
        fact
        for row in rows
        if (fact := _organic_competitor_fact(row, country=country)) is not None
    ]
    return (
        {
            "organic_competitor_read_status": "completed",
            "organic_competitor_rows": len(facts),
            "organic_competitor_country": country,
        },
        facts,
    )


def _report_date() -> str:
    return (datetime.now(UTC).date() - timedelta(days=1)).isoformat()


def _target_source_label() -> str:
    for name in ("AHREFS_TARGET", "WORDPRESS_EKOLOGUS_URL", "MIS_PRIMARY_SITE_URL"):
        if variable_value(name):
            return variable_source(name) or "configured"
    return "missing"


def _organic_competitor_country() -> str:
    country = variable_value("AHREFS_COUNTRY")
    if country and country.strip():
        return country.strip().lower()
    return "pl"


def _organic_competitor_limit() -> int:
    configured = variable_value("AHREFS_ORGANIC_COMPETITOR_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_ORGANIC_COMPETITOR_LIMIT_MAX))
    return AHREFS_ORGANIC_COMPETITOR_LIMIT_DEFAULT


def _response_rows(payload: Any, preferred_key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [_mapping(item) for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    preferred_value = payload.get(preferred_key)
    if isinstance(preferred_value, list):
        return [_mapping(item) for item in preferred_value if isinstance(item, dict)]
    for value in payload.values():
        if isinstance(value, list):
            return [_mapping(item) for item in value if isinstance(item, dict)]
    return []


def _mapping(value: dict[str, Any]) -> dict[str, Any]:
    return dict(value)


def _organic_competitor_fact(
    row: dict[str, Any],
    *,
    country: str,
) -> VendorMetricFact | None:
    competitor_domain = _competitor_domain(row)
    if competitor_domain is None:
        return None
    pages = max(
        1,
        _int_metric(
            _first_present(
                row,
                "pages",
                "competitor_pages",
                "pages_competitor",
            )
        ),
    )
    dimensions = _clean_dimensions(
        {
            "gap_type": "competitor_page",
            "competitor_domain": competitor_domain,
            "source_url": _first_text(row, "competitor_url", "url", "page_url"),
            "country": country,
            "keywords_common": _first_text(row, "keywords_common"),
            "keywords_competitor": _first_text(row, "keywords_competitor"),
            "keywords_target": _first_text(row, "keywords_target"),
            "share": _first_text(row, "share"),
        }
    )
    return VendorMetricFact(
        "ahrefs_competitor_page_count",
        pages,
        dimensions,
        period="ahrefs_organic_competitors",
    )


def _competitor_domain(row: dict[str, Any]) -> str | None:
    value = _first_text(
        row,
        "competitor_domain",
        "competitor",
        "domain",
        "target",
    )
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.hostname:
        return _clean_hostname(parsed.hostname)
    return _clean_hostname(value)


def _first_text(row: dict[str, Any], *keys: str) -> str | None:
    value = _first_present(row, *keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and value != "":
            return value
    return None


def _clean_dimensions(dimensions: dict[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in dimensions.items() if value}


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
