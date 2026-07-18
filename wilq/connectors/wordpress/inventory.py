from __future__ import annotations

import json
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from defusedxml import ElementTree

from wilq.connectors.vendor import VendorMetricFact
from wilq.connectors.wordpress.text import (
    clean_metadata_text,
    html_text,
    wordpress_title,
)

WORDPRESS_CONTENT_TYPES = ("posts", "pages")
WORDPRESS_CONTENT_PER_PAGE = 100
WORDPRESS_READ_FIELDS = (
    "id,status,modified_gmt,date_gmt,link,slug,title,content,acf,template"
)
WORDPRESS_SITEMAP_PATHS = ("wp-sitemap.xml", "sitemap_index.xml", "sitemap.xml")
WORDPRESS_SITEMAP_CHILD_LIMIT = 20
WORDPRESS_SITEMAP_URL_LIMIT = 500
WORDPRESS_METADATA_FETCH_LIMIT = 50
WORDPRESS_METADATA_MAX_BYTES = 200_000
WORDPRESS_METADATA_TIMEOUT_SECONDS = 3.0
WORDPRESS_SECTION_HEADING_LIMIT = 12
WORDPRESS_CONTENT_SUMMARY_MAX_CHARS = 240
WORDPRESS_BLOCK_NAME_LIMIT = 16


@dataclass(frozen=True)
class _SitemapFetchResult:
    objects: list[dict[str, str]]
    source_count: int
    returned_count: int
    truncated: bool


def fetch_content_inventory(
    client: httpx.Client,
    connector_id: str,
    *,
    base_url: str,
    public_url: str | None,
    username: str,
    application_auth: str,
    site_kind: str,
    priority_urls: list[str] | None = None,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    auth = httpx.BasicAuth(username, application_auth)
    summaries = {
        content_type: _fetch_content_type_summary(client, base_url, content_type, auth)
        for content_type in WORDPRESS_CONTENT_TYPES
    }
    sitemap_result = _fetch_sitemap_objects_with_coverage(client, base_url)
    sitemap_objects = sitemap_result.objects
    public_sitemap_result = _fetch_public_sitemap_objects(
        client,
        base_url,
        public_url,
        priority_urls=priority_urls or [],
    )
    public_sitemap_objects = public_sitemap_result.objects
    public_sitemap_objects = _merge_public_rest_acf_inventory(
        client,
        public_url,
        public_sitemap_objects,
        priority_urls=priority_urls or [],
    )
    latest_values = [
        str(summary["latest_modified_gmt"])
        for summary in summaries.values()
        if summary["latest_modified_gmt"]
    ]
    metric_summary: dict[str, float | int | str] = {
        "api": "wordpress_rest_and_sitemap_content_inventory",
        "connector_id": connector_id,
        "site_kind": site_kind,
        "content_object_count": sum(_summary_total(item) for item in summaries.values()),
        "posts_total": _summary_total(summaries["posts"]),
        "pages_total": _summary_total(summaries["pages"]),
        "sitemap_url_count": len(sitemap_objects),
        "sitemap_url_source_count": sitemap_result.source_count,
        "sitemap_url_returned_count": sitemap_result.returned_count,
        "sitemap_url_truncated": sitemap_result.truncated,
        "sitemap_url_limit": WORDPRESS_SITEMAP_URL_LIMIT,
        "public_sitemap_url_count": len(public_sitemap_objects),
        "public_sitemap_url_source_count": public_sitemap_result.source_count,
        "public_sitemap_url_returned_count": public_sitemap_result.returned_count,
        "public_sitemap_url_truncated": public_sitemap_result.truncated,
        "public_sitemap_url_limit": WORDPRESS_SITEMAP_URL_LIMIT,
        "latest_modified_gmt": max(latest_values) if latest_values else "",
        "latest_post_modified_gmt": str(summaries["posts"]["latest_modified_gmt"]),
        "latest_page_modified_gmt": str(summaries["pages"]["latest_modified_gmt"]),
        "target_url_count": len(priority_urls or []),
    }
    metric_facts = _rest_metric_facts(connector_id, site_kind, summaries)
    metric_facts.extend(
        _sitemap_metric_facts(connector_id, site_kind, sitemap_objects, source="sitemap")
    )
    metric_facts.extend(
        _sitemap_metric_facts(
            connector_id,
            site_kind,
            public_sitemap_objects,
            source="public_sitemap",
        )
    )
    metric_facts.extend(
        _sitemap_count_facts(
            connector_id,
            site_kind,
            sitemap_objects=sitemap_objects,
            public_sitemap_objects=public_sitemap_objects,
        )
    )
    return metric_summary, metric_facts


def _rest_metric_facts(
    connector_id: str,
    site_kind: str,
    summaries: dict[str, dict[str, int | str | list[dict[str, str]]]],
) -> list[VendorMetricFact]:
    facts = [
        VendorMetricFact(
            name="content_object_count",
            value=_summary_total(summary),
            dimensions={
                "connector_id": connector_id,
                "site_kind": site_kind,
                "content_type": content_type,
            },
        )
        for content_type, summary in summaries.items()
    ]
    for content_type, summary in summaries.items():
        objects = summary["objects"]
        if not isinstance(objects, list):
            continue
        for item in objects:
            facts.append(
                VendorMetricFact(
                    name="content_object_seen",
                    value=1,
                    dimensions={
                        "connector_id": connector_id,
                        "site_kind": site_kind,
                        "content_type": content_type,
                        "object_id": item.get("object_id", ""),
                        "content_url": item.get("content_url", ""),
                        "status": item.get("status", ""),
                        "modified_gmt": item.get("modified_gmt", ""),
                        "title_or_h1": item.get("title_or_h1", ""),
                        "canonical_url": item.get("canonical_url", ""),
                        "section_headings_json": item.get("section_headings_json", ""),
                        "section_heading_count": item.get("section_heading_count", ""),
                        "content_summary": item.get("content_summary", ""),
                        "content_word_count": item.get("content_word_count", ""),
                        "block_names_json": item.get("block_names_json", ""),
                        "block_name_count": item.get("block_name_count", ""),
                        "acf_field_count": item.get("acf_field_count", ""),
                        "acf_section_headings_json": item.get(
                            "acf_section_headings_json", ""
                        ),
                        "acf_field_names_json": item.get("acf_field_names_json", ""),
                        "acf_section_count": item.get("acf_section_count", ""),
                        "inventory_source": "wordpress_rest",
                    },
                )
            )
    return facts


def _sitemap_metric_facts(
    connector_id: str,
    site_kind: str,
    objects: list[dict[str, str]],
    *,
    source: str,
) -> list[VendorMetricFact]:
    return [
        VendorMetricFact(
            name="content_object_seen",
            value=1,
            dimensions={
                "connector_id": connector_id,
                "site_kind": site_kind,
                "content_type": item.get("content_type", "sitemap"),
                "object_id": "",
                "content_url": item.get("content_url", ""),
                "status": "indexed",
                "modified_gmt": item.get("modified_gmt", ""),
                "title_or_h1": item.get("title_or_h1", ""),
                "canonical_url": item.get("canonical_url", ""),
                "section_headings_json": item.get("section_headings_json", ""),
                "section_heading_count": item.get("section_heading_count", ""),
                "content_summary": item.get("content_summary", ""),
                "content_word_count": item.get("content_word_count", ""),
                "acf_section_headings_json": item.get(
                    "acf_section_headings_json", ""
                ),
                "acf_field_names_json": item.get("acf_field_names_json", ""),
                "acf_section_count": item.get("acf_section_count", ""),
                "inventory_source": source,
            },
        )
        for item in objects
    ]


def _sitemap_count_facts(
    connector_id: str,
    site_kind: str,
    *,
    sitemap_objects: list[dict[str, str]],
    public_sitemap_objects: list[dict[str, str]],
) -> list[VendorMetricFact]:
    facts: list[VendorMetricFact] = []
    for name, source, objects in (
        ("sitemap_url_count", "sitemap", sitemap_objects),
        ("public_sitemap_url_count", "public_sitemap", public_sitemap_objects),
    ):
        if objects:
            facts.append(
                VendorMetricFact(
                    name=name,
                    value=len(objects),
                    dimensions={
                        "connector_id": connector_id,
                        "site_kind": site_kind,
                        "inventory_source": source,
                    },
                )
            )
    return facts


def _fetch_public_sitemap_objects(
    client: httpx.Client,
    base_url: str,
    public_url: str | None,
    *,
    priority_urls: list[str],
) -> _SitemapFetchResult:
    if not public_url or _normalize_base_url(public_url) == _normalize_base_url(base_url):
        return _SitemapFetchResult(objects=[], source_count=0, returned_count=0, truncated=False)
    base_hosts = {_host(base_url)}
    sitemap_result = _fetch_sitemap_objects_with_coverage(
        client, public_url, enrich_metadata=False
    )
    public_objects = sitemap_result.objects
    filtered_objects = [
        item for item in public_objects if _host(item.get("content_url", "")) not in base_hosts
    ]
    filtered_count = len(filtered_objects)
    if priority_urls:
        priority_keys = {
            _normalize_base_url(url)
            for url in priority_urls
            if _normalize_base_url(url) is not None
        }
        targeted_objects = [
            item
            for item in filtered_objects
            if _normalize_base_url(item.get("content_url", "")) in priority_keys
        ]
        enriched_targets = _enrich_sitemap_objects_with_page_metadata(
            client,
            targeted_objects,
            distribute_content_groups=False,
        )
        enriched_by_url = {
            _normalize_base_url(item.get("content_url", "")): item
            for item in enriched_targets
        }
        objects = [
            enriched_by_url.get(_normalize_base_url(item.get("content_url", "")), item)
            for item in filtered_objects
        ]
    else:
        objects = _enrich_sitemap_objects_with_page_metadata(
            client,
            _prioritize_sitemap_objects(filtered_objects, [*priority_urls, public_url]),
            distribute_content_groups=True,
        )
    return _SitemapFetchResult(
        objects=objects,
        source_count=(
            filtered_count
            if not sitemap_result.truncated
            else sitemap_result.source_count
        ),
        returned_count=len(objects),
        truncated=sitemap_result.truncated,
    )


def _merge_public_rest_acf_inventory(
    client: httpx.Client,
    public_url: str | None,
    sitemap_objects: list[dict[str, str]],
    *,
    priority_urls: list[str],
) -> list[dict[str, str]]:
    """Supplement requested public pages with sanitized ACF section labels.

    This intentionally uses the public WordPress REST surface without credentials.
    A disabled ACF REST field or an unavailable endpoint is ordinary missing source
    data, not a reason to fail the rest of the WordPress inventory refresh.
    """

    if not public_url or not priority_urls or not sitemap_objects:
        return sitemap_objects
    requested = {
        _normalize_base_url(url)
        for url in priority_urls
        if _normalize_base_url(url) is not None
    }
    public_rest_objects = _fetch_public_rest_objects(
        client, public_url, requested_urls=requested
    )
    if not public_rest_objects:
        return sitemap_objects
    by_url = {
        _normalize_base_url(item.get("content_url", "")): item
        for item in public_rest_objects
    }
    return [
        {**item, **by_url[key]}
        if (key := _normalize_base_url(item.get("content_url", ""))) in by_url
        else item
        for item in sitemap_objects
    ]


def _fetch_public_rest_objects(
    client: httpx.Client,
    public_url: str,
    *,
    requested_urls: set[str | None],
) -> list[dict[str, str]]:
    objects: list[dict[str, str]] = []
    for requested_url in requested_urls:
        if not requested_url:
            continue
        slug = urlparse(requested_url).path.rstrip("/").rsplit("/", 1)[-1]
        if not slug:
            continue
        for content_type in WORDPRESS_CONTENT_TYPES:
            try:
                response = client.get(
                    urljoin(public_url, f"wp-json/wp/v2/{content_type}"),
                    params={"slug": slug, "_fields": WORDPRESS_READ_FIELDS},
                    timeout=WORDPRESS_METADATA_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
            except httpx.HTTPError:
                continue
            payload = response.json()
            for item in payload if isinstance(payload, list) else []:
                if not isinstance(item, dict):
                    continue
                content_url = item.get("link")
                if _normalize_base_url(content_url) != requested_url:
                    continue
                acf_dimensions = acf_inventory(item.get("acf"))
                if not (
                    acf_dimensions.get("acf_field_names_json")
                    or acf_dimensions.get("acf_section_headings_json")
                ):
                    continue
                enriched = {
                    "content_url": content_url,
                    "acf_field_names_json": acf_dimensions.get("acf_field_names_json", ""),
                }
                for key in ("acf_section_headings_json", "acf_section_count"):
                    if key in acf_dimensions:
                        enriched[key] = acf_dimensions[key]
                objects.append(enriched)
    return objects


def _fetch_sitemap_objects(
    client: httpx.Client,
    base_url: str,
    *,
    enrich_metadata: bool = True,
) -> list[dict[str, str]]:
    return _fetch_sitemap_objects_with_coverage(
        client,
        base_url,
        enrich_metadata=enrich_metadata,
    ).objects


def _fetch_sitemap_objects_with_coverage(
    client: httpx.Client,
    base_url: str,
    *,
    enrich_metadata: bool = True,
) -> _SitemapFetchResult:
    for sitemap_path in WORDPRESS_SITEMAP_PATHS:
        try:
            response = client.get(urljoin(base_url, sitemap_path))
            if response.status_code == 404:
                continue
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        sitemap_objects = _sitemap_objects_from_xml(client, response.text)
        if sitemap_objects:
            limited = sitemap_objects[:WORDPRESS_SITEMAP_URL_LIMIT]
            objects = (
                _enrich_sitemap_objects_with_page_metadata(client, limited)
                if enrich_metadata
                else limited
            )
            return _SitemapFetchResult(
                objects=objects,
                source_count=len(sitemap_objects),
                returned_count=len(objects),
                truncated=len(sitemap_objects) > len(objects),
            )
    return _SitemapFetchResult(objects=[], source_count=0, returned_count=0, truncated=False)


def _enrich_sitemap_objects_with_page_metadata(
    client: httpx.Client,
    objects: list[dict[str, str]],
    *,
    distribute_content_groups: bool = False,
) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []
    group_counts: dict[str, int] = {}
    for index, item in enumerate(objects):
        group = _metadata_budget_group(item) if distribute_content_groups else "all"
        group_count = group_counts.get(group, 0)
        limit_reached = (
            index >= WORDPRESS_METADATA_FETCH_LIMIT
            if not distribute_content_groups
            else group_count >= WORDPRESS_METADATA_FETCH_LIMIT
        )
        if limit_reached:
            enriched.append(item)
            continue
        group_counts[group] = group_count + 1
        metadata = _fetch_public_page_metadata(client, item.get("content_url", ""))
        enriched.append({**item, **metadata} if metadata else item)
    return enriched


def _metadata_budget_group(item: dict[str, str]) -> str:
    group = item.get("_metadata_group", "")
    return group if group in {"posts", "pages"} else "other"


def _prioritize_sitemap_objects(
    objects: list[dict[str, str]],
    priority_urls: list[str | None],
) -> list[dict[str, str]]:
    priority_keys = {_normalize_base_url(url) for url in priority_urls if url}
    return sorted(
        objects,
        key=lambda item: (
            0 if _normalize_base_url(item.get("content_url", "")) in priority_keys else 1
        ),
    )


def _fetch_public_page_metadata(client: httpx.Client, url: str) -> dict[str, str]:
    if not url:
        return {}
    try:
        response = client.get(url, timeout=WORDPRESS_METADATA_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError:
        return {}
    content_type = response.headers.get("content-type", "")
    if content_type and "html" not in content_type.lower():
        return {}
    parser = _HtmlMetadataParser()
    parser.feed(response.text[:WORDPRESS_METADATA_MAX_BYTES])
    title_or_h1 = clean_metadata_text(parser.title or parser.h1)
    canonical_url = clean_metadata_text(parser.canonical_url)
    section_headings = [
        heading
        for heading in (clean_metadata_text(value) for value in parser.section_headings)
        if heading
    ][:WORDPRESS_SECTION_HEADING_LIMIT]
    content_text = clean_metadata_text(" ".join(parser.main_text_chunks))
    content_summary = _summary_text(content_text)
    return {
        key: value
        for key, value in {
            "title_or_h1": title_or_h1,
            "canonical_url": canonical_url,
            "section_headings_json": json.dumps(section_headings, ensure_ascii=False),
            "section_heading_count": str(len(section_headings)),
            "content_summary": content_summary,
            "content_word_count": str(len(content_text.split())) if content_text else "",
        }.items()
        if value
    }


def _sitemap_objects_from_xml(client: httpx.Client, xml_text: str) -> list[dict[str, str]]:
    entries = _parse_sitemap_xml(xml_text)
    child_sitemaps = [entry for entry in entries if entry["kind"] == "sitemap"]
    if not child_sitemaps:
        return [_sitemap_url_object(entry) for entry in entries if entry["kind"] == "url"][
            :WORDPRESS_SITEMAP_URL_LIMIT
        ]
    objects: list[dict[str, str]] = []
    for sitemap in child_sitemaps[:WORDPRESS_SITEMAP_CHILD_LIMIT]:
        metadata_group = _sitemap_metadata_group(sitemap["loc"])
        try:
            response = client.get(sitemap["loc"])
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        child_entries = _parse_sitemap_xml(response.text)
        objects.extend(
            _sitemap_url_object(entry, metadata_group=metadata_group)
            for entry in child_entries
            if entry["kind"] == "url"
        )
        if len(objects) >= WORDPRESS_SITEMAP_URL_LIMIT:
            return objects[:WORDPRESS_SITEMAP_URL_LIMIT]
    return objects


def _parse_sitemap_xml(xml_text: str) -> list[dict[str, str]]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []
    entries: list[dict[str, str]] = []
    for element in root:
        tag = _local_name(element.tag)
        if tag not in {"url", "sitemap"}:
            continue
        values = {_local_name(child.tag): (child.text or "").strip() for child in element}
        if values.get("loc"):
            entries.append(
                {
                    "kind": tag,
                    "loc": values["loc"],
                    "lastmod": values.get("lastmod", ""),
                }
            )
    return entries


def _sitemap_url_object(
    entry: dict[str, str], *, metadata_group: str = "other"
) -> dict[str, str]:
    return {
        "content_type": "sitemap",
        "content_url": entry["loc"],
        "modified_gmt": entry.get("lastmod", ""),
        "_metadata_group": metadata_group,
    }


def _sitemap_metadata_group(sitemap_url: str) -> str:
    filename = urlparse(sitemap_url).path.rsplit("/", 1)[-1].lower()
    if filename.startswith("post-sitemap"):
        return "posts"
    if filename.startswith("page-sitemap"):
        return "pages"
    return "other"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _host(value: str) -> str:
    return httpx.URL(value).host or ""


def _normalize_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped.rstrip("/") + "/" if stripped else None


def _fetch_content_type_summary(
    client: httpx.Client,
    base_url: str,
    content_type: str,
    auth: httpx.BasicAuth,
) -> dict[str, int | str | list[dict[str, str]]]:
    endpoint = urljoin(base_url, f"wp-json/wp/v2/{content_type}")
    params = {
        "per_page": WORDPRESS_CONTENT_PER_PAGE,
        "orderby": "modified",
        "order": "desc",
        "_fields": WORDPRESS_READ_FIELDS,
    }
    response = client.get(endpoint, auth=auth, params={**params, "page": 1})
    response.raise_for_status()
    payload = response.json()
    objects = _content_objects(payload)
    total_pages = _header_int(response.headers.get("X-WP-TotalPages"))
    # WordPress REST is paginated even when the total count is available. Fetch
    # every page so sitemap-only URLs do not masquerade as complete inventory.
    for page in range(2, total_pages + 1):
        page_response = client.get(endpoint, auth=auth, params={**params, "page": page})
        page_response.raise_for_status()
        page_payload = page_response.json()
        page_objects = _content_objects(page_payload)
        if not page_objects:
            break
        objects.extend(page_objects)
    return {
        "total": _header_int(response.headers.get("X-WP-Total")),
        "latest_modified_gmt": _latest_modified(objects),
        "objects": objects,
    }


def _header_int(value: str | None) -> int:
    try:
        return int(value) if value is not None else 0
    except ValueError:
        return 0


def _summary_total(summary: dict[str, int | str | list[dict[str, str]]]) -> int:
    total = summary["total"]
    return total if isinstance(total, int) else 0


def _latest_modified(payload: Any) -> str:
    if not isinstance(payload, list):
        return ""
    for item in payload:
        if isinstance(item, dict):
            modified = item.get("modified_gmt") or item.get("date_gmt")
            if isinstance(modified, str):
                return modified
    return ""


def _content_objects(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, list):
        return []
    objects: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        content_url = item.get("link")
        if not isinstance(content_url, str) or not content_url:
            continue
        object_id = item.get("id")
        modified = item.get("modified_gmt") or item.get("date_gmt")
        status = item.get("status")
        objects.append(
            {
                "object_id": str(object_id) if object_id is not None else "",
                "content_url": content_url,
                "status": status if isinstance(status, str) else "",
                "modified_gmt": modified if isinstance(modified, str) else "",
                "title_or_h1": wordpress_title(item.get("title")),
                "canonical_url": "",
                **content_inventory(item.get("content")),
                **acf_inventory(item.get("acf")),
            }
        )
    return objects


def content_inventory(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    raw = value.get("raw")
    rendered = value.get("rendered")
    source = raw if isinstance(raw, str) and raw.strip() else rendered
    if not isinstance(source, str) or not source.strip():
        return {}
    block_names = _block_names(source)
    text = html_text(source)
    summary = _summary_text(text)
    dimensions: dict[str, str] = {}
    if summary:
        dimensions["content_summary"] = summary
        dimensions["content_word_count"] = str(len(text.split()))
    if block_names:
        dimensions["block_names_json"] = json.dumps(block_names, ensure_ascii=False)
        dimensions["block_name_count"] = str(len(block_names))
    return dimensions


def acf_inventory(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        field_names = [
            str(key) for key, item in value.items() if key and item not in (None, "", [], {})
        ]
        sections = _acf_section_headings(value)
        dimensions = {
            "acf_field_count": str(len(field_names)),
            "acf_field_names_json": json.dumps(
                field_names[:WORDPRESS_BLOCK_NAME_LIMIT], ensure_ascii=False
            ),
        }
        if sections:
            dimensions["acf_section_headings_json"] = json.dumps(
                sections, ensure_ascii=False
            )
            dimensions["acf_section_count"] = str(len(sections))
        return dimensions
    if isinstance(value, list):
        return {"acf_field_count": str(len(value))}
    return {}


def _acf_section_headings(value: dict[str, Any]) -> list[str]:
    """Return only concise, public-safe ACF section labels; never raw field data."""

    headings: list[str] = []
    for row in _acf_flexible_rows(value):
        heading = _acf_row_heading(row)
        if heading and heading not in headings:
            headings.append(heading)
        if len(headings) >= WORDPRESS_SECTION_HEADING_LIMIT:
            return headings
    return headings


def _acf_flexible_rows(value: Any) -> list[dict[str, Any]]:
    """Find flexible-content rows under ACF groups without retaining their values."""

    if isinstance(value, dict):
        if isinstance(value.get("acf_fc_layout"), str):
            return [value]
        return [row for child in value.values() for row in _acf_flexible_rows(child)]
    if isinstance(value, list):
        return [row for child in value for row in _acf_flexible_rows(child)]
    return []


def _acf_row_heading(row: dict[str, Any]) -> str:
    preferred = ("tytul", "title", "naglowek", "heading", "nazwa", "name")
    for key in preferred:
        value = row.get(key)
        if isinstance(value, str):
            heading = clean_metadata_text(html_text(value))
            if heading:
                return heading[:180]
    layout = row.get("acf_fc_layout")
    if isinstance(layout, str):
        return clean_metadata_text(layout.replace("_", " ").replace("-", " "))[:180]
    return ""


def _block_names(value: str) -> list[str]:
    names: list[str] = []
    marker = "<!-- wp:"
    start = 0
    while len(names) < WORDPRESS_BLOCK_NAME_LIMIT:
        index = value.find(marker, start)
        if index < 0:
            break
        name_start = index + len(marker)
        candidates = [
            position
            for position in (value.find(" ", name_start), value.find("-->", name_start))
            if position >= 0
        ]
        if not candidates:
            break
        end = min(candidates)
        name = value[name_start:end].strip().strip("/")
        if name and name not in names:
            names.append(name)
        start = end + 1
    return names


def _summary_text(value: str) -> str:
    if len(value) <= WORDPRESS_CONTENT_SUMMARY_MAX_CHARS:
        return value
    shortened = value[:WORDPRESS_CONTENT_SUMMARY_MAX_CHARS].rsplit(" ", 1)[0].strip()
    return shortened + "..."


class _HtmlMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.h1 = ""
        self.canonical_url = ""
        self.section_headings: list[str] = []
        self._capture: str | None = None
        self._capture_tag: str | None = None
        self._chunks: list[str] = []
        self.main_text_chunks: list[str] = []
        self._body_depth = 0
        self._main_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        normalized_tag = tag.lower()
        if normalized_tag == "body":
            self._body_depth += 1
        if normalized_tag in {"main", "article"}:
            self._main_depth += 1
        if normalized_tag in {"script", "style", "nav", "header", "footer", "aside"}:
            self._ignored_depth += 1
        if (
            normalized_tag == "link"
            and not self.canonical_url
            and "canonical" in attr_map.get("rel", "").lower().split()
        ):
            self.canonical_url = attr_map.get("href", "")
        if normalized_tag == "title" and not self.title:
            self._start_capture("title", normalized_tag)
        elif normalized_tag == "h1" and not self.h1:
            self._start_capture("h1", normalized_tag)
        elif normalized_tag in {"h2", "h3"} and len(
            self.section_headings
        ) < WORDPRESS_SECTION_HEADING_LIMIT:
            self._start_capture("section_heading", normalized_tag)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if self._capture_tag != tag.lower():
            pass
        else:
            text = clean_metadata_text(" ".join(self._chunks))
            if self._capture == "title" and text:
                self.title = text
            elif self._capture == "h1" and text:
                self.h1 = text
            elif self._capture == "section_heading" and text:
                self.section_headings.append(text)
            self._capture = None
            self._capture_tag = None
            self._chunks = []
        if normalized_tag in {"script", "style", "nav", "header", "footer", "aside"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        if normalized_tag in {"main", "article"}:
            self._main_depth = max(0, self._main_depth - 1)
        if normalized_tag == "body":
            self._body_depth = max(0, self._body_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._chunks.append(data)
        if self._ignored_depth == 0 and (self._main_depth > 0 or self._body_depth > 0):
            self.main_text_chunks.append(data)

    def _start_capture(self, capture: str, tag: str) -> None:
        self._capture = capture
        self._capture_tag = tag
        self._chunks = []
