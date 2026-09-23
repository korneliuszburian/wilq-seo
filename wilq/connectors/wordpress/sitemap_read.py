"""Bounded, same-origin reads of WordPress sitemap XML."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from defusedxml import ElementTree

from wilq.connectors.wordpress.sitemap_policy import (
    sitemap_group_for_url,
    sitemap_url_object,
)
from wilq.content.canonical.urls import (
    content_is_safe_authoring_url,
    content_is_safe_public_url,
)

WORDPRESS_SITEMAP_CHILD_LIMIT = 20
WORDPRESS_SITEMAP_URL_LIMIT = 2000


def _is_safe_configured_sitemap_alias(
    location: str | None,
    sitemap_url: str,
    remaining_candidates: list[str],
) -> bool:
    """Accept only a same-origin HTTPS redirect to one remaining configured path."""

    if not location:
        return False
    try:
        target = httpx.URL(urljoin(sitemap_url, location))
        origin = httpx.URL(sitemap_url)
        if (
            not (
                content_is_safe_public_url(str(target))
                or content_is_safe_authoring_url(str(target))
            )
            or target.scheme != "https"
            or target.scheme != origin.scheme
            or target.host != origin.host
            or target.port != origin.port
            or target.query
            or target.fragment
        ):
            return False
        return sum(target == httpx.URL(candidate) for candidate in remaining_candidates) == 1
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class _SitemapParseResult:
    objects: list[dict[str, str]]
    source_count: int
    uncovered_count: int
    truncated: bool
    partial: bool


def _sitemap_objects_from_xml(
    client: httpx.Client,
    xml_text: str,
    *,
    sitemap_url: str,
) -> _SitemapParseResult:
    entries = _parse_sitemap_xml(xml_text)
    safe_entries = [
        entry for entry in entries if _same_origin_sitemap_url(entry["loc"], sitemap_url)
    ]
    invalid_locations = len(safe_entries) != len(entries)
    child_sitemaps = [entry for entry in safe_entries if entry["kind"] == "sitemap"]
    if not child_sitemaps:
        urls = [
            sitemap_url_object(entry)
            for entry in safe_entries
            if entry["kind"] == "url"
        ]
        return _SitemapParseResult(
            objects=urls[:WORDPRESS_SITEMAP_URL_LIMIT],
            source_count=len(urls),
            uncovered_count=(
                len(entries)
                - len(safe_entries)
                + max(0, len(urls) - WORDPRESS_SITEMAP_URL_LIMIT)
            ),
            truncated=len(urls) > WORDPRESS_SITEMAP_URL_LIMIT,
            partial=invalid_locations or len(urls) > WORDPRESS_SITEMAP_URL_LIMIT,
        )
    objects: list[dict[str, str]] = []
    direct_urls = [entry for entry in safe_entries if entry["kind"] == "url"]
    partial = (
        invalid_locations
        or bool(direct_urls)
        or len(child_sitemaps) > WORDPRESS_SITEMAP_CHILD_LIMIT
    )
    source_count = 0
    # An omitted child map counts as one uncovered location because its page
    # count is unknown unless that map is fetched.
    uncovered_count = len(entries) - len(safe_entries) + len(direct_urls)
    uncovered_count += max(0, len(child_sitemaps) - WORDPRESS_SITEMAP_CHILD_LIMIT)
    bounded_child_sitemaps = child_sitemaps[:WORDPRESS_SITEMAP_CHILD_LIMIT]
    for child_index, sitemap in enumerate(bounded_child_sitemaps):
        metadata_group = sitemap_group_for_url(sitemap["loc"])
        try:
            response = client.get(sitemap["loc"], follow_redirects=False)
            response.raise_for_status()
        except httpx.HTTPError:
            partial = True
            uncovered_count += 1
            continue
        try:
            child_entries = _parse_sitemap_xml(response.text)
        except ElementTree.ParseError:
            partial = True
            uncovered_count += 1
            continue
        nested_sitemaps = [entry for entry in child_entries if entry["kind"] == "sitemap"]
        if nested_sitemaps:
            partial = True
            uncovered_count += len(nested_sitemaps)
        child_urls = [entry for entry in child_entries if entry["kind"] == "url"]
        safe_child_urls = [
            entry
            for entry in child_urls
            if _same_origin_sitemap_url(entry["loc"], sitemap_url)
        ]
        if len(safe_child_urls) != len(child_urls):
            partial = True
            uncovered_count += len(child_urls) - len(safe_child_urls)
        child_objects = [
            sitemap_url_object(entry, metadata_group=metadata_group)
            for entry in safe_child_urls
        ]
        source_count += len(child_objects)
        remaining = WORDPRESS_SITEMAP_URL_LIMIT - len(objects)
        objects.extend(child_objects[:remaining])
        omitted_urls = max(0, len(child_objects) - remaining)
        if omitted_urls:
            partial = True
            uncovered_count += omitted_urls
            # Remaining allowed maps are skipped because the URL cap is full.
            uncovered_count += len(bounded_child_sitemaps) - child_index - 1
            return _SitemapParseResult(
                objects=objects,
                source_count=source_count,
                uncovered_count=uncovered_count,
                truncated=True,
                partial=partial,
            )
    return _SitemapParseResult(
        objects=objects,
        source_count=source_count,
        uncovered_count=uncovered_count,
        truncated=len(child_sitemaps) > WORDPRESS_SITEMAP_CHILD_LIMIT,
        partial=partial,
    )


def _parse_sitemap_xml(xml_text: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(xml_text)
    if _local_name(root.tag) not in {"urlset", "sitemapindex"}:
        raise ElementTree.ParseError("Unexpected sitemap root element.")
    entries: list[dict[str, str]] = []
    for element in root:
        tag = _local_name(element.tag)
        if tag not in {"url", "sitemap"}:
            continue
        values = {_local_name(child.tag): (child.text or "").strip() for child in element}
        entries.append(
            {
                "kind": tag,
                "loc": values.get("loc", ""),
                "lastmod": values.get("lastmod", ""),
            }
        )
    return entries


def _same_origin_sitemap_url(value: str, sitemap_url: str) -> bool:
    """Use canonical URL policy and require the requested sitemap's exact host."""

    try:
        safe_candidate = content_is_safe_public_url(value) or content_is_safe_authoring_url(
            value
        )
        safe_origin = content_is_safe_public_url(sitemap_url) or content_is_safe_authoring_url(
            sitemap_url
        )
        return (
            safe_candidate
            and safe_origin
            and httpx.URL(value).host == httpx.URL(sitemap_url).host
        )
    except (TypeError, ValueError):
        return False


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
