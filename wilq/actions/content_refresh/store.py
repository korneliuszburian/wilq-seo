from __future__ import annotations

from wilq.schemas import MetricFact

from .shared import (
    CONTENT_SOURCE_SITE_HOSTS,
    _normalized_path,
    _normalized_url,
    _url_host,
)

__all__ = [
    "_wordpress_inventory_urls_by_path",
    "_wordpress_inventory_details_by_path",
    "_wordpress_inventory_details_by_url",
    "_inventory_detail_score",
]



def _wordpress_inventory_urls_by_path(metric_facts: list[MetricFact]) -> dict[str, str]:
    urls_by_path: dict[str, str] = {}
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        url = fact.dimensions.get("content_url")
        if not url:
            continue
        if _url_host(url) not in CONTENT_SOURCE_SITE_HOSTS:
            continue
        path = _normalized_path(url)
        if path:
            urls_by_path.setdefault(path, url)
    return urls_by_path


def _wordpress_inventory_details_by_path(
    metric_facts: list[MetricFact],
) -> dict[str, dict[str, str]]:
    details_by_path: dict[str, dict[str, str]] = {}
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        if fact.name != "content_object_seen":
            continue
        url = fact.dimensions.get("content_url")
        if not url:
            continue
        if _url_host(url) not in CONTENT_SOURCE_SITE_HOSTS:
            continue
        path = _normalized_path(url)
        if not path:
            continue
        candidate = {
            "content_type": fact.dimensions.get("content_type", ""),
            "status": fact.dimensions.get("status", ""),
            "inventory_source": fact.dimensions.get("inventory_source", ""),
            "modified_gmt": fact.dimensions.get("modified_gmt", ""),
            "title_or_h1": fact.dimensions.get("title_or_h1", ""),
            "canonical_url": fact.dimensions.get("canonical_url", ""),
        }
        current = details_by_path.get(path)
        if current is None or _inventory_detail_score(candidate) > _inventory_detail_score(current):
            details_by_path[path] = candidate
    return details_by_path


def _wordpress_inventory_details_by_url(
    metric_facts: list[MetricFact],
) -> dict[str, dict[str, str]]:
    details_by_url: dict[str, dict[str, str]] = {}
    for fact in metric_facts:
        if not fact.source_connector.startswith("wordpress_"):
            continue
        if fact.name != "content_object_seen":
            continue
        normalized_url = _normalized_url(fact.dimensions.get("content_url"))
        if not normalized_url:
            continue
        candidate = {
            "content_type": fact.dimensions.get("content_type", ""),
            "status": fact.dimensions.get("status", ""),
            "inventory_source": fact.dimensions.get("inventory_source", ""),
            "modified_gmt": fact.dimensions.get("modified_gmt", ""),
            "title_or_h1": fact.dimensions.get("title_or_h1", ""),
            "canonical_url": fact.dimensions.get("canonical_url", ""),
        }
        current = details_by_url.get(normalized_url)
        if current is None or _inventory_detail_score(candidate) > _inventory_detail_score(current):
            details_by_url[normalized_url] = candidate
    return details_by_url


def _inventory_detail_score(details: dict[str, str]) -> int:
    return sum(1 for value in details.values() if value)
