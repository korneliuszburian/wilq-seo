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
AHREFS_ORGANIC_COMPETITOR_MODE_DEFAULT = "subdomains"
AHREFS_ORGANIC_COMPETITOR_MODES = {"exact", "prefix", "domain", "subdomains"}
AHREFS_TOP_PAGES_COMPETITOR_LIMIT_DEFAULT = 3
AHREFS_TOP_PAGES_COMPETITOR_LIMIT_MAX = 5
AHREFS_TOP_PAGES_PER_COMPETITOR_DEFAULT = 3
AHREFS_TOP_PAGES_PER_COMPETITOR_MAX = 10
AHREFS_TOP_PAGES_MODE_DEFAULT = "subdomains"
AHREFS_ORGANIC_KEYWORDS_TOP_PAGE_LIMIT_DEFAULT = 4
AHREFS_ORGANIC_KEYWORDS_TOP_PAGE_LIMIT_MAX = 8
AHREFS_ORGANIC_KEYWORDS_PER_URL_DEFAULT = 3
AHREFS_ORGANIC_KEYWORDS_PER_URL_MAX = 10
AHREFS_ORGANIC_KEYWORDS_MODE_DEFAULT = "exact"
AHREFS_BACKLINK_GAP_COMPETITOR_LIMIT_DEFAULT = 2
AHREFS_BACKLINK_GAP_COMPETITOR_LIMIT_MAX = 5
AHREFS_BACKLINK_GAP_TARGET_REFDOMAIN_LIMIT_DEFAULT = 1000
AHREFS_BACKLINK_GAP_TARGET_REFDOMAIN_LIMIT_MAX = 5000
AHREFS_BACKLINK_GAP_REFDOMAIN_LIMIT_DEFAULT = 10
AHREFS_BACKLINK_GAP_REFDOMAIN_LIMIT_MAX = 50
AHREFS_BACKLINK_GAP_MODE_DEFAULT = "subdomains"
AHREFS_BACKLINK_GAP_HISTORY_DEFAULT = "live"
AHREFS_CONTENT_GAP_TARGET_KEYWORD_LIMIT_DEFAULT = 1000
AHREFS_CONTENT_GAP_TARGET_KEYWORD_LIMIT_MAX = 5000
AHREFS_CONTENT_GAP_RECORD_LIMIT_DEFAULT = 24
AHREFS_CONTENT_GAP_RECORD_LIMIT_MAX = 100
AHREFS_CONTENT_GAP_MODE_DEFAULT = "subdomains"


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
                "AHREFS_TARGET, MIS_PRIMARY_SITE_URL or WORDPRESS_EKOLOGUS_URL."
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
            try:
                top_pages_summary, top_page_facts = _fetch_top_pages_by_competitors(
                    client,
                    token,
                    competitor_facts,
                )
                metric_summary.update(top_pages_summary)
                metric_facts.extend(top_page_facts)
                keyword_facts: list[VendorMetricFact] = []
                try:
                    keyword_summary, keyword_facts = _fetch_organic_keywords_by_top_pages(
                        client,
                        token,
                        top_page_facts,
                    )
                    metric_summary.update(keyword_summary)
                    metric_facts.extend(keyword_facts)
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    metric_summary.update(
                        {
                            "organic_keywords_by_url_read_status": f"http_{status_code}",
                            "organic_keywords_by_url_rows": 0,
                        }
                    )
                    errors.append(f"Ahrefs Site Explorer organic-keywords HTTP {status_code}.")
                except httpx.HTTPError as exc:
                    metric_summary.update(
                        {
                            "organic_keywords_by_url_read_status": type(exc).__name__,
                            "organic_keywords_by_url_rows": 0,
                        }
                    )
                    errors.append(f"Ahrefs Site Explorer organic-keywords {type(exc).__name__}.")
                try:
                    content_summary, content_facts = _fetch_content_gaps(
                        client,
                        token,
                        target,
                        keyword_facts,
                    )
                    metric_summary.update(content_summary)
                    metric_facts.extend(content_facts)
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    metric_summary.update(
                        {
                            "content_gap_read_status": f"http_{status_code}",
                            "content_gap_rows": 0,
                        }
                    )
                    errors.append(
                        f"Ahrefs Site Explorer content-gap organic-keywords HTTP {status_code}."
                    )
                except httpx.HTTPError as exc:
                    metric_summary.update(
                        {
                            "content_gap_read_status": type(exc).__name__,
                            "content_gap_rows": 0,
                        }
                    )
                    errors.append(
                        f"Ahrefs Site Explorer content-gap organic-keywords {type(exc).__name__}."
                    )
                try:
                    backlink_summary, backlink_facts = _fetch_backlink_gaps(
                        client,
                        token,
                        target,
                        competitor_facts,
                    )
                    metric_summary.update(backlink_summary)
                    metric_facts.extend(backlink_facts)
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    metric_summary.update(
                        {
                            "backlink_gap_read_status": f"http_{status_code}",
                            "backlink_gap_rows": 0,
                        }
                    )
                    errors.append(f"Ahrefs Site Explorer refdomains HTTP {status_code}.")
                except httpx.HTTPError as exc:
                    metric_summary.update(
                        {
                            "backlink_gap_read_status": type(exc).__name__,
                            "backlink_gap_rows": 0,
                        }
                    )
                    errors.append(f"Ahrefs Site Explorer refdomains {type(exc).__name__}.")
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                metric_summary.update(
                    {
                        "top_pages_by_competitor_read_status": f"http_{status_code}",
                        "top_pages_by_competitor_rows": 0,
                    }
                )
                errors.append(f"Ahrefs Site Explorer top-pages HTTP {status_code}.")
            except httpx.HTTPError as exc:
                metric_summary.update(
                    {
                        "top_pages_by_competitor_read_status": type(exc).__name__,
                        "top_pages_by_competitor_rows": 0,
                    }
                )
                errors.append(f"Ahrefs Site Explorer top-pages {type(exc).__name__}.")
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
            errors.append(f"Ahrefs Site Explorer organic-competitors {type(exc).__name__}.")
    finally:
        if owns_client:
            client.close()

    return VendorReadResult(
        status=ConnectorRefreshStatus.completed,
        summary=(
            "Odczyt Ahrefs zakończony przez Site Explorer domain-rating. "
            f"Domain rating: {metric_summary['domain_rating']}. "
            f"Wiersze konkurentów organicznych: {metric_summary['organic_competitor_rows']}. "
            f"Wiersze top pages: {metric_summary.get('top_pages_by_competitor_rows', 0)}. "
            "Wiersze organic keywords dla top pages: "
            f"{metric_summary.get('organic_keywords_by_url_rows', 0)}. "
            f"Wiersze luk treści: {metric_summary.get('content_gap_rows', 0)}. "
            f"Wiersze luk linków: {metric_summary.get('backlink_gap_rows', 0)}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
        metric_facts=metric_facts,
        errors=errors,
    )


def _target() -> str | None:
    for name in ("AHREFS_TARGET", "MIS_PRIMARY_SITE_URL", "WORDPRESS_EKOLOGUS_URL"):
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
    mode = _organic_competitor_mode()
    limit = _organic_competitor_limit()
    response = client.get(
        f"{AHREFS_API_BASE}/site-explorer/organic-competitors",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={
            "target": target,
            "mode": mode,
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
    rows = _response_rows(response.json(), "competitors")[:limit]
    facts = [
        fact
        for row in rows
        if (fact := _organic_competitor_fact(row, country=country, mode=mode)) is not None
    ]
    return (
        {
            "organic_competitor_read_status": "completed",
            "organic_competitor_rows": len(facts),
            "organic_competitor_country": country,
            "organic_competitor_mode": mode,
        },
        facts,
    )


def _fetch_top_pages_by_competitors(
    client: httpx.Client,
    token: str,
    competitor_facts: list[VendorMetricFact],
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    report_date = _report_date()
    country = _organic_competitor_country()
    mode = _top_pages_mode()
    competitor_domains = _top_page_competitor_domains(competitor_facts)
    if not competitor_domains:
        return (
            {
                "top_pages_by_competitor_read_status": "skipped_no_competitors",
                "top_pages_by_competitor_rows": 0,
                "top_pages_by_competitor_competitors": 0,
                "top_pages_by_competitor_country": country,
                "top_pages_by_competitor_mode": mode,
            },
            [],
        )

    page_limit = _top_pages_per_competitor_limit()
    facts: list[VendorMetricFact] = []
    for competitor_domain in competitor_domains:
        response = client.get(
            f"{AHREFS_API_BASE}/site-explorer/top-pages",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={
                "target": competitor_domain,
                "mode": mode,
                "country": country,
                "date": report_date,
                "limit": page_limit,
                "output": "json",
                "order_by": "sum_traffic:desc",
                "select": ",".join(
                    [
                        "raw_url",
                        "top_keyword",
                        "sum_traffic",
                        "keywords",
                        "referring_domains",
                        "top_keyword_best_position",
                        "top_keyword_country",
                    ]
                ),
            },
        )
        response.raise_for_status()
        rows = _response_rows(response.json(), "pages")[:page_limit]
        facts.extend(
            fact
            for row in rows
            if (
                fact := _top_page_gap_fact(
                    row,
                    competitor_domain=competitor_domain,
                    country=country,
                    mode=mode,
                )
            )
            is not None
        )
    return (
        {
            "top_pages_by_competitor_read_status": "completed",
            "top_pages_by_competitor_rows": len(facts),
            "top_pages_by_competitor_competitors": len(competitor_domains),
            "top_pages_by_competitor_country": country,
            "top_pages_by_competitor_mode": mode,
        },
        facts,
    )


def _fetch_organic_keywords_by_top_pages(
    client: httpx.Client,
    token: str,
    top_page_facts: list[VendorMetricFact],
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    report_date = _report_date()
    country = _organic_competitor_country()
    mode = _organic_keywords_mode()
    top_pages = _organic_keyword_top_pages(top_page_facts)
    if not top_pages:
        return (
            {
                "organic_keywords_by_url_read_status": "skipped_no_top_pages",
                "organic_keywords_by_url_rows": 0,
                "organic_keywords_by_url_urls": 0,
                "organic_keywords_by_url_country": country,
                "organic_keywords_by_url_mode": mode,
            },
            [],
        )

    keyword_limit = _organic_keywords_per_url_limit()
    facts: list[VendorMetricFact] = []
    for top_page in top_pages:
        response = client.get(
            f"{AHREFS_API_BASE}/site-explorer/organic-keywords",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={
                "target": top_page["source_url"],
                "mode": mode,
                "country": country,
                "date": report_date,
                "limit": keyword_limit,
                "output": "json",
                "order_by": "sum_traffic:desc",
                "select": ",".join(
                    [
                        "keyword",
                        "best_position",
                        "best_position_url",
                        "volume",
                        "sum_traffic",
                        "keyword_difficulty",
                        "cpc",
                        "is_branded",
                        "is_commercial",
                        "is_informational",
                        "is_local",
                        "is_transactional",
                    ]
                ),
            },
        )
        response.raise_for_status()
        rows = _response_rows(response.json(), "keywords")[:keyword_limit]
        facts.extend(
            fact
            for row in rows
            if (
                fact := _organic_keyword_gap_fact(
                    row,
                    competitor_domain=top_page["competitor_domain"],
                    source_url=top_page["source_url"],
                    country=country,
                    mode=mode,
                    target_keyword_sample_size=len(rows),
                    target_keyword_limit=keyword_limit,
                )
            )
            is not None
        )
    return (
        {
            "organic_keywords_by_url_read_status": "completed",
            "organic_keywords_by_url_rows": len(facts),
            "organic_keywords_by_url_urls": len(top_pages),
            "organic_keywords_by_url_country": country,
            "organic_keywords_by_url_mode": mode,
            "organic_keywords_by_url_keyword_limit": keyword_limit,
        },
        facts,
    )


def _fetch_backlink_gaps(
    client: httpx.Client,
    token: str,
    target: str,
    competitor_facts: list[VendorMetricFact],
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    mode = _backlink_gap_mode()
    history = _backlink_gap_history()
    competitor_domains = _backlink_gap_competitor_domains(competitor_facts)
    if not competitor_domains:
        return (
            {
                "backlink_gap_read_status": "skipped_no_competitors",
                "backlink_gap_rows": 0,
                "backlink_gap_competitors": 0,
                "backlink_gap_mode": mode,
                "backlink_gap_history": history,
            },
            [],
        )

    target_limit = _backlink_gap_target_refdomain_limit()
    target_refdomains = _fetch_refdomains(
        client,
        token,
        target=target,
        mode=mode,
        history=history,
        limit=target_limit,
    )
    target_domain_names = {
        domain for row in target_refdomains if (domain := _refdomain(row)) is not None
    }
    competitor_limit = _backlink_gap_refdomain_limit()
    facts: list[VendorMetricFact] = []
    for competitor_domain in competitor_domains:
        competitor_rows = _fetch_refdomains(
            client,
            token,
            target=competitor_domain,
            mode=mode,
            history=history,
            limit=competitor_limit,
        )
        for row in competitor_rows:
            if (
                fact := _backlink_gap_fact(
                    row,
                    competitor_domain=competitor_domain,
                    target=target,
                    target_refdomains=target_domain_names,
                    target_refdomain_sample_size=len(target_domain_names),
                    target_refdomain_limit=target_limit,
                    mode=mode,
                    history=history,
                )
            ) is not None:
                facts.append(fact)
    return (
        {
            "backlink_gap_read_status": "completed",
            "backlink_gap_rows": len(facts),
            "backlink_gap_competitors": len(competitor_domains),
            "backlink_gap_target_refdomains": len(target_domain_names),
            "backlink_gap_target_refdomain_limit": target_limit,
            "backlink_gap_competitor_refdomain_limit": competitor_limit,
            "backlink_gap_mode": mode,
            "backlink_gap_history": history,
        },
        facts,
    )


def _fetch_content_gaps(
    client: httpx.Client,
    token: str,
    target: str,
    competitor_keyword_facts: list[VendorMetricFact],
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    if not competitor_keyword_facts:
        return (
            {
                "content_gap_read_status": "skipped_no_competitor_keywords",
                "content_gap_rows": 0,
                "content_gap_target_keywords": 0,
                "content_gap_competitor_keywords": 0,
                "content_gap_mode": _content_gap_mode(),
            },
            [],
        )

    report_date = _report_date()
    country = _organic_competitor_country()
    mode = _content_gap_mode()
    target_limit = _content_gap_target_keyword_limit()
    target_rows = _fetch_organic_keywords(
        client,
        token,
        target=target,
        mode=mode,
        country=country,
        date=report_date,
        limit=target_limit,
    )
    target_keywords = {
        normalized
        for row in target_rows
        if (normalized := _normalized_keyword(_first_text(row, "keyword"))) is not None
    }
    facts = [
        fact
        for competitor_fact in competitor_keyword_facts[: _content_gap_record_limit()]
        if (
            fact := _content_gap_fact(
                competitor_fact,
                target=target,
                target_keywords=target_keywords,
                target_keyword_sample_size=len(target_keywords),
                target_keyword_limit=target_limit,
                mode=mode,
            )
        )
        is not None
    ]
    return (
        {
            "content_gap_read_status": "completed",
            "content_gap_rows": len(facts),
            "content_gap_target_keywords": len(target_keywords),
            "content_gap_target_keyword_limit": target_limit,
            "content_gap_competitor_keywords": len(competitor_keyword_facts),
            "content_gap_mode": mode,
        },
        facts,
    )


def _fetch_organic_keywords(
    client: httpx.Client,
    token: str,
    *,
    target: str,
    mode: str,
    country: str,
    date: str,
    limit: int,
) -> list[dict[str, Any]]:
    response = client.get(
        f"{AHREFS_API_BASE}/site-explorer/organic-keywords",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={
            "target": target,
            "mode": mode,
            "country": country,
            "date": date,
            "limit": limit,
            "output": "json",
            "order_by": "sum_traffic:desc",
            "select": ",".join(
                [
                    "keyword",
                    "best_position",
                    "best_position_url",
                    "volume",
                    "sum_traffic",
                    "keyword_difficulty",
                    "cpc",
                    "is_branded",
                    "is_commercial",
                    "is_informational",
                    "is_local",
                    "is_transactional",
                ]
            ),
        },
    )
    response.raise_for_status()
    return _response_rows(response.json(), "keywords")[:limit]


def _fetch_refdomains(
    client: httpx.Client,
    token: str,
    *,
    target: str,
    mode: str,
    history: str,
    limit: int,
) -> list[dict[str, Any]]:
    response = client.get(
        f"{AHREFS_API_BASE}/site-explorer/refdomains",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={
            "target": target,
            "mode": mode,
            "history": history,
            "limit": limit,
            "output": "json",
            "order_by": "domain_rating:desc",
            "select": ",".join(
                [
                    "domain",
                    "domain_rating",
                    "links_to_target",
                    "dofollow_links",
                    "dofollow_refdomains",
                    "traffic_domain",
                    "positions_source_domain",
                    "first_seen",
                    "last_seen",
                    "is_spam",
                    "is_root_domain",
                ]
            ),
        },
    )
    response.raise_for_status()
    return _response_rows(response.json(), "refdomains")[:limit]


def _report_date() -> str:
    return (datetime.now(UTC).date() - timedelta(days=1)).isoformat()


def _target_source_label() -> str:
    for name in ("AHREFS_TARGET", "MIS_PRIMARY_SITE_URL", "WORDPRESS_EKOLOGUS_URL"):
        if variable_value(name):
            return variable_source(name) or "configured"
    return "missing"


def _organic_competitor_country() -> str:
    country = variable_value("AHREFS_COUNTRY")
    if country and country.strip():
        return country.strip().lower()
    return "pl"


def _organic_competitor_mode() -> str:
    mode = variable_value("AHREFS_ORGANIC_COMPETITOR_MODE")
    if mode and mode.strip().lower() in AHREFS_ORGANIC_COMPETITOR_MODES:
        return mode.strip().lower()
    return AHREFS_ORGANIC_COMPETITOR_MODE_DEFAULT


def _organic_competitor_limit() -> int:
    configured = variable_value("AHREFS_ORGANIC_COMPETITOR_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_ORGANIC_COMPETITOR_LIMIT_MAX))
    return AHREFS_ORGANIC_COMPETITOR_LIMIT_DEFAULT


def _top_pages_mode() -> str:
    mode = variable_value("AHREFS_TOP_PAGES_MODE")
    if mode and mode.strip().lower() in AHREFS_ORGANIC_COMPETITOR_MODES:
        return mode.strip().lower()
    return AHREFS_TOP_PAGES_MODE_DEFAULT


def _top_pages_competitor_limit() -> int:
    configured = variable_value("AHREFS_TOP_PAGES_COMPETITOR_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_TOP_PAGES_COMPETITOR_LIMIT_MAX))
    return AHREFS_TOP_PAGES_COMPETITOR_LIMIT_DEFAULT


def _top_pages_per_competitor_limit() -> int:
    configured = variable_value("AHREFS_TOP_PAGES_PER_COMPETITOR")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_TOP_PAGES_PER_COMPETITOR_MAX))
    return AHREFS_TOP_PAGES_PER_COMPETITOR_DEFAULT


def _organic_keywords_mode() -> str:
    mode = variable_value("AHREFS_ORGANIC_KEYWORDS_MODE")
    if mode and mode.strip().lower() in AHREFS_ORGANIC_COMPETITOR_MODES:
        return mode.strip().lower()
    return AHREFS_ORGANIC_KEYWORDS_MODE_DEFAULT


def _organic_keywords_top_page_limit() -> int:
    configured = variable_value("AHREFS_ORGANIC_KEYWORDS_TOP_PAGE_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_ORGANIC_KEYWORDS_TOP_PAGE_LIMIT_MAX))
    return AHREFS_ORGANIC_KEYWORDS_TOP_PAGE_LIMIT_DEFAULT


def _organic_keywords_per_url_limit() -> int:
    configured = variable_value("AHREFS_ORGANIC_KEYWORDS_PER_URL")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_ORGANIC_KEYWORDS_PER_URL_MAX))
    return AHREFS_ORGANIC_KEYWORDS_PER_URL_DEFAULT


def _backlink_gap_mode() -> str:
    mode = variable_value("AHREFS_BACKLINK_GAP_MODE")
    if mode and mode.strip().lower() in AHREFS_ORGANIC_COMPETITOR_MODES:
        return mode.strip().lower()
    return AHREFS_BACKLINK_GAP_MODE_DEFAULT


def _backlink_gap_history() -> str:
    history = variable_value("AHREFS_BACKLINK_GAP_HISTORY")
    if history and history.strip():
        return history.strip().lower()
    return AHREFS_BACKLINK_GAP_HISTORY_DEFAULT


def _backlink_gap_competitor_limit() -> int:
    configured = variable_value("AHREFS_BACKLINK_GAP_COMPETITOR_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_BACKLINK_GAP_COMPETITOR_LIMIT_MAX))
    return AHREFS_BACKLINK_GAP_COMPETITOR_LIMIT_DEFAULT


def _backlink_gap_target_refdomain_limit() -> int:
    configured = variable_value("AHREFS_BACKLINK_GAP_TARGET_REFDOMAIN_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_BACKLINK_GAP_TARGET_REFDOMAIN_LIMIT_MAX))
    return AHREFS_BACKLINK_GAP_TARGET_REFDOMAIN_LIMIT_DEFAULT


def _backlink_gap_refdomain_limit() -> int:
    configured = variable_value("AHREFS_BACKLINK_GAP_REFDOMAIN_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_BACKLINK_GAP_REFDOMAIN_LIMIT_MAX))
    return AHREFS_BACKLINK_GAP_REFDOMAIN_LIMIT_DEFAULT


def _content_gap_mode() -> str:
    mode = variable_value("AHREFS_CONTENT_GAP_MODE")
    if mode and mode.strip().lower() in AHREFS_ORGANIC_COMPETITOR_MODES:
        return mode.strip().lower()
    return AHREFS_CONTENT_GAP_MODE_DEFAULT


def _content_gap_target_keyword_limit() -> int:
    configured = variable_value("AHREFS_CONTENT_GAP_TARGET_KEYWORD_LIMIT")
    if configured and configured.isdigit():
        return max(
            1,
            min(int(configured), AHREFS_CONTENT_GAP_TARGET_KEYWORD_LIMIT_MAX),
        )
    return AHREFS_CONTENT_GAP_TARGET_KEYWORD_LIMIT_DEFAULT


def _content_gap_record_limit() -> int:
    configured = variable_value("AHREFS_CONTENT_GAP_RECORD_LIMIT")
    if configured and configured.isdigit():
        return max(1, min(int(configured), AHREFS_CONTENT_GAP_RECORD_LIMIT_MAX))
    return AHREFS_CONTENT_GAP_RECORD_LIMIT_DEFAULT


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
    mode: str,
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
            "target_mode": mode,
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


def _top_page_competitor_domains(competitor_facts: list[VendorMetricFact]) -> list[str]:
    domains: list[str] = []
    for fact in competitor_facts:
        competitor_domain = fact.dimensions.get("competitor_domain")
        if competitor_domain and competitor_domain not in domains:
            domains.append(competitor_domain)
    return domains[: _top_pages_competitor_limit()]


def _backlink_gap_competitor_domains(
    competitor_facts: list[VendorMetricFact],
) -> list[str]:
    domains: list[str] = []
    for fact in competitor_facts:
        competitor_domain = fact.dimensions.get("competitor_domain")
        if competitor_domain and competitor_domain not in domains:
            domains.append(competitor_domain)
    return domains[: _backlink_gap_competitor_limit()]


def _organic_keyword_top_pages(
    top_page_facts: list[VendorMetricFact],
) -> list[dict[str, str]]:
    top_pages: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for fact in top_page_facts:
        source_url = fact.dimensions.get("source_url")
        competitor_domain = fact.dimensions.get("competitor_domain")
        if not source_url or not competitor_domain or source_url in seen_urls:
            continue
        seen_urls.add(source_url)
        top_pages.append(
            {
                "source_url": source_url,
                "competitor_domain": competitor_domain,
            }
        )
    return top_pages[: _organic_keywords_top_page_limit()]


def _top_page_gap_fact(
    row: dict[str, Any],
    *,
    competitor_domain: str,
    country: str,
    mode: str,
) -> VendorMetricFact | None:
    source_url = _first_text(row, "raw_url", "url", "page_url")
    if source_url is None:
        return None
    dimensions = _clean_dimensions(
        {
            "gap_type": "top_page_gap",
            "competitor_domain": competitor_domain,
            "source_url": source_url,
            "keyword": _first_text(row, "top_keyword", "keyword"),
            "country": country,
            "target_mode": mode,
            "sum_traffic": _first_text(row, "sum_traffic"),
            "keywords": _first_text(row, "keywords"),
            "referring_domains": _first_text(row, "referring_domains"),
            "top_keyword_best_position": _first_text(row, "top_keyword_best_position"),
            "top_keyword_country": _first_text(row, "top_keyword_country"),
        }
    )
    return VendorMetricFact(
        "ahrefs_top_page_gap_count",
        1,
        dimensions,
        period="ahrefs_top_pages",
    )


def _organic_keyword_gap_fact(
    row: dict[str, Any],
    *,
    competitor_domain: str,
    source_url: str,
    country: str,
    mode: str,
    target_keyword_sample_size: int,
    target_keyword_limit: int,
) -> VendorMetricFact | None:
    keyword = _first_text(row, "keyword", "keyword_merged", "organic_keyword")
    if keyword is None:
        return None
    dimensions = _clean_dimensions(
        {
            "gap_type": "organic_keyword_gap",
            "competitor_domain": competitor_domain,
            "source_url": source_url,
            "keyword": keyword,
            "country": country,
            "target_mode": mode,
            "best_position": _first_text(row, "best_position"),
            "best_position_url": _first_text(row, "best_position_url"),
            "volume": _first_text(row, "volume"),
            "sum_traffic": _first_text(row, "sum_traffic"),
            "keyword_difficulty": _first_text(row, "keyword_difficulty"),
            "cpc": _first_text(row, "cpc"),
            "is_branded": _first_text(row, "is_branded"),
            "is_commercial": _first_text(row, "is_commercial"),
            "is_informational": _first_text(row, "is_informational"),
            "is_local": _first_text(row, "is_local"),
            "is_transactional": _first_text(row, "is_transactional"),
            "target_keyword_sample_size": str(target_keyword_sample_size),
            "target_keyword_limit": str(target_keyword_limit),
        }
    )
    return VendorMetricFact(
        "ahrefs_organic_keyword_gap_count",
        1,
        dimensions,
        period="ahrefs_organic_keywords",
    )


def _backlink_gap_fact(
    row: dict[str, Any],
    *,
    competitor_domain: str,
    target: str,
    target_refdomains: set[str],
    target_refdomain_sample_size: int,
    target_refdomain_limit: int,
    mode: str,
    history: str,
) -> VendorMetricFact | None:
    referring_domain = _refdomain(row)
    if referring_domain is None or referring_domain in target_refdomains:
        return None
    dimensions = _clean_dimensions(
        {
            "gap_type": "backlink_gap",
            "competitor_domain": competitor_domain,
            "source_url": referring_domain,
            "referring_domain": referring_domain,
            "target_domain": target,
            "target_mode": mode,
            "history": history,
            "domain_rating": _first_text(row, "domain_rating"),
            "links_to_target": _first_text(row, "links_to_target"),
            "dofollow_links": _first_text(row, "dofollow_links"),
            "dofollow_refdomains": _first_text(row, "dofollow_refdomains"),
            "traffic_domain": _first_text(row, "traffic_domain"),
            "positions_source_domain": _first_text(row, "positions_source_domain"),
            "first_seen": _first_text(row, "first_seen"),
            "last_seen": _first_text(row, "last_seen"),
            "is_spam": _first_text(row, "is_spam"),
            "is_root_domain": _first_text(row, "is_root_domain"),
            "target_refdomain_sample_size": str(target_refdomain_sample_size),
            "target_refdomain_limit": str(target_refdomain_limit),
        }
    )
    return VendorMetricFact(
        "ahrefs_referring_domain_gap_count",
        1,
        dimensions,
        period="ahrefs_refdomains_gap",
    )


def _content_gap_fact(
    competitor_fact: VendorMetricFact,
    *,
    target: str,
    target_keywords: set[str],
    target_keyword_sample_size: int,
    target_keyword_limit: int,
    mode: str,
) -> VendorMetricFact | None:
    keyword = competitor_fact.dimensions.get("keyword")
    normalized = _normalized_keyword(keyword)
    if normalized is None or normalized in target_keywords:
        return None
    dimensions = _clean_dimensions(
        {
            "gap_type": "content_gap",
            "competitor_domain": competitor_fact.dimensions.get("competitor_domain"),
            "source_url": competitor_fact.dimensions.get("source_url"),
            "target_domain": target,
            "keyword": keyword,
            "country": competitor_fact.dimensions.get("country"),
            "target_mode": mode,
            "competitor_target_mode": competitor_fact.dimensions.get("target_mode"),
            "best_position": competitor_fact.dimensions.get("best_position"),
            "best_position_url": competitor_fact.dimensions.get("best_position_url"),
            "volume": competitor_fact.dimensions.get("volume"),
            "sum_traffic": competitor_fact.dimensions.get("sum_traffic"),
            "keyword_difficulty": competitor_fact.dimensions.get("keyword_difficulty"),
            "cpc": competitor_fact.dimensions.get("cpc"),
            "is_branded": competitor_fact.dimensions.get("is_branded"),
            "is_commercial": competitor_fact.dimensions.get("is_commercial"),
            "is_informational": competitor_fact.dimensions.get("is_informational"),
            "is_local": competitor_fact.dimensions.get("is_local"),
            "is_transactional": competitor_fact.dimensions.get("is_transactional"),
            "target_keyword_sample_size": str(target_keyword_sample_size),
            "target_keyword_limit": str(target_keyword_limit),
        }
    )
    return VendorMetricFact(
        "ahrefs_content_gap_count",
        1,
        dimensions,
        period="ahrefs_content_gap",
    )


def _competitor_domain(row: dict[str, Any]) -> str | None:
    value = _first_text(
        row,
        "competitor_domain",
        "competitor_url",
        "url",
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


def _refdomain(row: dict[str, Any]) -> str | None:
    value = _first_text(row, "domain", "refdomain", "referring_domain")
    if value is None:
        return None
    return _clean_hostname(value)


def _normalized_keyword(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.casefold().split())
    return normalized or None


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
