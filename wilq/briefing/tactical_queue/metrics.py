"""Decomposed tactical_queue metrics implementation."""

from __future__ import annotations

from collections.abc import Iterable

from wilq.briefing.metric_fact_identity import latest_metric_facts_by_identity
from wilq.briefing.tactical_queue.shared import (
    GA4_LANDING_FACT_LIMIT,
    GSC_QUERY_PAGE_FACT_LIMIT,
    TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT,
    TACTICAL_QUEUE_SOURCE_CONNECTORS,
    WORDPRESS_CANONICAL_HOST_ALIASES,
    WORDPRESS_INVENTORY_FACT_LIMIT,
    WORDPRESS_PUBLIC_CONTENT_HOSTS,
    WordPressContentIndex,
    WordPressMatch,
    _normalize_path_key,
    _normalize_url_key,
    _url_host,
)
from wilq.schemas import MetricFact
from wilq.storage.metric_store import metric_store as metric_store


def _sum_metric_facts(facts: list[MetricFact], name: str) -> float | int | None:
    values = [
        float(fact.value)
        for fact in facts
        if fact.name == name and isinstance(fact.value, int | float)
    ]
    if not values:
        return None
    total = sum(values)
    return int(total) if total.is_integer() else total


def _tactical_metric_facts(
    facts_by_connector: dict[str, list[MetricFact]] | None = None,
) -> list[MetricFact]:
    if facts_by_connector is None:
        facts_by_connector = metric_store().list_latest_metric_facts_by_connector_limits(
            {
                connector_id: _tactical_connector_fact_limit(connector_id)
                for connector_id in TACTICAL_QUEUE_SOURCE_CONNECTORS
            }
        )
    facts: list[MetricFact] = []
    for connector_id in TACTICAL_QUEUE_SOURCE_CONNECTORS:
        facts.extend(facts_by_connector.get(connector_id, []))
    return latest_metric_facts_by_identity(facts)


def _tactical_connector_fact_limit(connector_id: str) -> int:
    if connector_id == "google_search_console":
        return GSC_QUERY_PAGE_FACT_LIMIT
    if connector_id == "google_analytics_4":
        return GA4_LANDING_FACT_LIMIT
    if connector_id.startswith("wordpress"):
        return WORDPRESS_INVENTORY_FACT_LIMIT
    return TACTICAL_QUEUE_CONNECTOR_FACT_LIMIT


def _group_facts(facts: Iterable[MetricFact]) -> dict[tuple[str, ...], list[MetricFact]]:
    grouped: dict[tuple[str, ...], list[MetricFact]] = {}
    for fact in facts:
        key = _fact_group_key(fact)
        if not key:
            continue
        grouped.setdefault(key, []).append(fact)
    return grouped


def _fact_group_key(fact: MetricFact) -> tuple[str, ...] | None:
    if fact.source_connector == "google_search_console":
        return (fact.dimensions.get("query", ""), fact.dimensions.get("page", ""))
    if fact.source_connector == "google_analytics_4":
        return (
            fact.dimensions.get("landing_page", ""),
            fact.dimensions.get("source_medium", ""),
            fact.dimensions.get("campaign_name", ""),
        )
    if fact.source_connector == "google_merchant_center" and fact.name == "issue_product_count":
        return (
            fact.dimensions.get("severity", ""),
            fact.dimensions.get("resolution", "unknown_resolution"),
            fact.dimensions.get("issue_type", "unknown_issue"),
            fact.dimensions.get("country", ""),
        )
    if fact.source_connector == "google_merchant_center":
        return (
            fact.dimensions.get("country", ""),
            fact.dimensions.get("reporting_context", ""),
        )
    return None


def _numeric_fact(facts: list[MetricFact], name: str) -> float | int | None:
    fact = next((item for item in facts if item.name == name), None)
    if fact is None or not isinstance(fact.value, int | float):
        return None
    return fact.value


def _dimension_value(facts: list[MetricFact], name: str) -> str | None:
    for fact in facts:
        value = fact.dimensions.get(name)
        if value:
            return value
    return None


def _wordpress_content_index(facts: list[MetricFact]) -> WordPressContentIndex:
    exact_urls: dict[str, MetricFact] = {}
    paths: dict[str, list[MetricFact]] = {}
    for fact in facts:
        if not fact.source_connector.startswith("wordpress"):
            continue
        if fact.name != "content_object_seen":
            continue
        content_url = fact.dimensions.get("content_url")
        if not content_url:
            continue
        _set_wordpress_index(exact_urls, _normalize_url_key(content_url), fact)
        path_key = _normalize_path_key(content_url)
        paths.setdefault(path_key, []).append(fact)
    return WordPressContentIndex(exact_urls=exact_urls, paths=paths)


def _find_wordpress_match(index: WordPressContentIndex, page_or_path: str) -> WordPressMatch:
    requested_url_key = _normalize_url_key(page_or_path)
    path_key = _normalize_path_key(page_or_path)
    full_match = index.exact_urls.get(requested_url_key)
    if full_match:
        return WordPressMatch(
            fact=full_match,
            confidence="exact_url",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    requested_host = _url_host(page_or_path)
    path_candidates = [
        candidate
        for candidate in index.paths.get(path_key, [])
        if _wordpress_path_candidate_allowed_for_request(requested_host, candidate)
    ]
    if path_key == "/" and not _url_host(page_or_path):
        path_match = _preferred_wordpress_path_match(path_candidates)
        if path_match:
            return WordPressMatch(
                fact=path_match,
                confidence="path_fallback",
                requested_url_key=requested_url_key,
                requested_path_key=path_key,
            )
        return WordPressMatch(
            fact=None,
            confidence="missing",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    alias_match = _host_alias_sitemap_match(page_or_path, path_candidates)
    if alias_match:
        return WordPressMatch(
            fact=alias_match,
            confidence="host_alias_sitemap",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    path_match = _preferred_wordpress_path_match(path_candidates)
    if path_match:
        return WordPressMatch(
            fact=path_match,
            confidence="path_fallback",
            requested_url_key=requested_url_key,
            requested_path_key=path_key,
        )
    return WordPressMatch(
        fact=None,
        confidence="missing",
        requested_url_key=requested_url_key,
        requested_path_key=path_key,
    )


def _set_wordpress_index(
    index: dict[str, MetricFact],
    key: str,
    fact: MetricFact,
) -> None:
    current = index.get(key)
    if current is None or _wordpress_index_fact_score(fact) > _wordpress_index_fact_score(current):
        index[key] = fact


def _preferred_wordpress_path_match(candidates: list[MetricFact]) -> MetricFact | None:
    return max(candidates, key=_wordpress_path_match_score, default=None)


def _wordpress_path_candidate_allowed_for_request(
    requested_host: str | None,
    fact: MetricFact,
) -> bool:
    if not requested_host:
        return True
    content_host = _url_host(fact.dimensions.get("content_url", ""))
    return not (content_host and content_host not in WORDPRESS_PUBLIC_CONTENT_HOSTS)


def _wordpress_path_match_score(fact: MetricFact) -> tuple[int, int, int, int, int, str, str]:
    return _wordpress_index_fact_score(fact)


def _wordpress_index_fact_score(fact: MetricFact) -> tuple[int, int, int, int, int, str, str]:
    dimensions = fact.dimensions
    inventory_source = dimensions.get("inventory_source")
    host = _url_host(dimensions.get("content_url", ""))
    collected_at = fact.collected_at.isoformat() if fact.collected_at is not None else ""
    return (
        1 if fact.source_connector == "wordpress_ekologus" else 0,
        1 if inventory_source in {"public_sitemap", "sitemap"} else 0,
        1 if host in {"www.ekologus.pl", "ekologus.pl"} else 0,
        1 if dimensions.get("title_or_h1") else 0,
        1 if dimensions.get("canonical_url") else 0,
        collected_at,
        fact.evidence_id,
    )


def _host_alias_sitemap_match(
    requested_url_or_path: str,
    candidates: list[MetricFact],
) -> MetricFact | None:
    requested_host = _url_host(requested_url_or_path)
    if not requested_host:
        return None
    for fact in candidates:
        dimensions = fact.dimensions
        if dimensions.get("inventory_source") not in {"sitemap", "public_sitemap"}:
            continue
        content_url = dimensions.get("content_url", "")
        content_host = _url_host(content_url)
        if _is_allowed_wordpress_host_alias(requested_host, content_host):
            return fact
    return None


def _is_allowed_wordpress_host_alias(requested_host: str, content_host: str) -> bool:
    if not requested_host or not content_host:
        return False
    normalized_requested = requested_host.lower()
    normalized_content = content_host.lower()
    return normalized_content in WORDPRESS_CANONICAL_HOST_ALIASES.get(
        normalized_requested,
        set(),
    )


def _gsc_page_counts(facts: list[MetricFact]) -> dict[str, int]:
    queries_by_page: dict[str, set[str]] = {}
    for fact in facts:
        if fact.source_connector != "google_search_console":
            continue
        page = fact.dimensions.get("page")
        query = fact.dimensions.get("query")
        if not page or not query:
            continue
        queries_by_page.setdefault(_normalize_url_key(page), set()).add(query)
    return {page: len(queries) for page, queries in queries_by_page.items()}


def _is_probe_only_fact(fact: MetricFact) -> bool:
    return fact.source_connector == "localo" and fact.name in {
        "api",
        "access_token_present",
        "authorization_code_supported",
        "pkce_s256_supported",
        "mcp_initialize_status",
    }
