from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, cast
from urllib.parse import urljoin, urlparse

import httpx
from defusedxml import ElementTree

from wilq.connectors.vendor import VendorMetricFact
from wilq.connectors.wordpress.inventory_metadata import (
    WORDPRESS_METADATA_TIMEOUT_SECONDS,
    WORDPRESS_SECTION_HEADING_LIMIT,
    _enrich_sitemap_objects_with_page_metadata,
    _HtmlMetadataParser,  # noqa: F401 - compatibility export for WordPress material reads
    _summary_text,
)
from wilq.connectors.wordpress.sitemap_policy import is_commerce_only_url
from wilq.connectors.wordpress.sitemap_read import (
    WORDPRESS_SITEMAP_URL_LIMIT,
    _is_safe_configured_sitemap_alias,
    _sitemap_objects_from_xml,
)
from wilq.connectors.wordpress.text import (
    clean_metadata_text,
    html_text,
    wordpress_title,
)

WORDPRESS_CONTENT_TYPES = ("posts", "pages", "uslugi")
WORDPRESS_CONTENT_PER_PAGE = 100
WORDPRESS_READ_FIELDS = (
    "id,status,modified_gmt,date_gmt,link,slug,title,content,acf,template"
)
WORDPRESS_SITEMAP_PATHS = ("wp-sitemap.xml", "sitemap_index.xml", "sitemap.xml")
# Keep the sitemap inventory broad enough to cover the whole Ekologus site
# while remaining explicitly bounded for a single vendor read.
WORDPRESS_BLOCK_NAME_LIMIT = 16


@dataclass(frozen=True)
class _SitemapFetchResult:
    objects: list[dict[str, str]]
    source_count: int
    returned_count: int
    uncovered_count: int
    truncated: bool
    coverage_status: Literal["complete", "partial", "unavailable", "not_applicable"]


class WordPressInventoryPayloadError(ValueError):
    """A successful WordPress response did not satisfy the read contract."""


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
    inventory_coverage_status = _inventory_coverage_status(
        sitemap_result,
        public_sitemap_result,
    )
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
        "sitemap_url_uncovered_count": sitemap_result.uncovered_count,
        "sitemap_url_truncated": sitemap_result.truncated,
        "sitemap_url_limit": WORDPRESS_SITEMAP_URL_LIMIT,
        "sitemap_coverage_status": sitemap_result.coverage_status,
        "public_sitemap_url_count": len(public_sitemap_objects),
        "public_sitemap_url_source_count": public_sitemap_result.source_count,
        "public_sitemap_url_returned_count": public_sitemap_result.returned_count,
        "public_sitemap_url_uncovered_count": public_sitemap_result.uncovered_count,
        "public_sitemap_url_truncated": public_sitemap_result.truncated,
        "public_sitemap_url_limit": WORDPRESS_SITEMAP_URL_LIMIT,
        "public_sitemap_coverage_status": public_sitemap_result.coverage_status,
        "inventory_coverage_status": inventory_coverage_status,
        "aggregate_data_completeness": (
            "complete" if inventory_coverage_status == "complete" else "partial_possible"
        ),
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
                        "editorial_eligible": (
                            "false" if is_commerce_only_url(item.get("content_url", "")) else "true"
                        ),
                        "inventory_scope": (
                            "commerce_catalog"
                            if is_commerce_only_url(item.get("content_url", ""))
                            else "editorial"
                        ),
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
                "sitemap_group": item.get("sitemap_group", "other"),
                "editorial_eligible": item.get("editorial_eligible", "false"),
                "inventory_scope": item.get("inventory_scope", "other"),
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
        return _SitemapFetchResult(
            objects=[],
            source_count=0,
            returned_count=0,
            uncovered_count=0,
            truncated=False,
            coverage_status="not_applicable",
        )
    base_hosts = {_host(base_url)}
    sitemap_result = _fetch_sitemap_objects_with_coverage(
        client, public_url, enrich_metadata=False
    )
    public_objects = sitemap_result.objects
    filtered_objects = [
        item for item in public_objects if _host(item.get("content_url", "")) not in base_hosts
    ]
    filtered_count = len(filtered_objects)
    baseline_objects = _enrich_sitemap_objects_with_page_metadata(
        client,
        _prioritize_sitemap_objects(filtered_objects, [*priority_urls, public_url]),
        sitemap_origin=public_url,
        distribute_content_groups=True,
    )
    if priority_urls:
        priority_keys = {
            _normalize_base_url(url)
            for url in priority_urls
            if _normalize_base_url(url) is not None
        }
        targets_needing_metadata = [
            item
            for item in baseline_objects
            if (
                _normalize_base_url(item.get("content_url", "")) in priority_keys
                and not (item.get("content_summary") or item.get("title_or_h1"))
            )
        ]
        enriched_by_url = {
            _normalize_base_url(item.get("content_url", "")): item
            for item in baseline_objects
        }
        if targets_needing_metadata:
            enriched_targets = _enrich_sitemap_objects_with_page_metadata(
                client,
                targets_needing_metadata,
                sitemap_origin=public_url,
                distribute_content_groups=False,
            )
            enriched_by_url.update(
                {
                    _normalize_base_url(item.get("content_url", "")): item
                    for item in enriched_targets
                }
            )
        objects = [
            enriched_by_url.get(_normalize_base_url(item.get("content_url", "")), item)
            for item in filtered_objects
        ]
    else:
        objects = baseline_objects
    return _SitemapFetchResult(
        objects=objects,
        source_count=(
            filtered_count
            if not sitemap_result.truncated
            else sitemap_result.source_count
        ),
        returned_count=len(objects),
        uncovered_count=sitemap_result.uncovered_count,
        truncated=sitemap_result.truncated,
        coverage_status=sitemap_result.coverage_status,
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
                payload = _json_object_list(response)
            except (httpx.HTTPError, WordPressInventoryPayloadError):
                continue
            for item in payload:
                content_url = item.get("link")
                if (
                    not isinstance(content_url, str)
                    or _normalize_base_url(content_url) != requested_url
                ):
                    continue
                acf_dimensions = acf_inventory(item.get("acf"))
                if not (
                    acf_dimensions.get("acf_field_names_json")
                    or acf_dimensions.get("acf_section_headings_json")
                ):
                    continue
                enriched: dict[str, str] = {
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
    suppressed_failure = False
    for sitemap_index, sitemap_path in enumerate(WORDPRESS_SITEMAP_PATHS):
        try:
            sitemap_url = urljoin(base_url, sitemap_path)
            response = client.get(sitemap_url, follow_redirects=False)
            if response.status_code == 404:
                continue
            if 300 <= response.status_code < 400:
                remaining_candidates = [
                    urljoin(base_url, candidate_path)
                    for candidate_path in WORDPRESS_SITEMAP_PATHS[sitemap_index + 1 :]
                ]
                if not _is_safe_configured_sitemap_alias(
                    response.headers.get("location"),
                    sitemap_url,
                    remaining_candidates,
                ):
                    suppressed_failure = True
                continue
            response.raise_for_status()
        except httpx.HTTPError:
            suppressed_failure = True
            continue
        try:
            parsed = _sitemap_objects_from_xml(
                client,
                response.text,
                sitemap_url=sitemap_url,
            )
        except ElementTree.ParseError:
            suppressed_failure = True
            continue
        objects = (
            _enrich_sitemap_objects_with_page_metadata(
                client,
                parsed.objects,
                sitemap_origin=sitemap_url,
            )
            if enrich_metadata
            else parsed.objects
        )
        partial = suppressed_failure or parsed.partial
        return _SitemapFetchResult(
            objects=objects,
            source_count=parsed.source_count,
            returned_count=len(objects),
            uncovered_count=parsed.uncovered_count,
            truncated=parsed.truncated,
            coverage_status="partial" if partial else "complete",
        )
    return _SitemapFetchResult(
        objects=[],
        source_count=0,
        returned_count=0,
        uncovered_count=0,
        truncated=False,
        coverage_status="unavailable",
    )


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
    response = client.get(
        endpoint,
        auth=auth,
        params=cast(httpx.QueryParams, {**params, "page": 1}),
    )
    if response.status_code == 404:
        return {
            "total": 0,
            "latest_modified_gmt": "",
            "objects": [],
        }
    response.raise_for_status()
    payload = _json_object_list(response)
    objects = _content_objects(payload)
    total_pages = _header_int(response.headers.get("X-WP-TotalPages"))
    # WordPress REST is paginated even when the total count is available. Fetch
    # every page so sitemap-only URLs do not masquerade as complete inventory.
    for page in range(2, total_pages + 1):
        page_response = client.get(
            endpoint,
            auth=auth,
            params=cast(httpx.QueryParams, {**params, "page": page}),
        )
        page_response.raise_for_status()
        page_payload = _json_object_list(page_response)
        page_objects = _content_objects(page_payload)
        if not page_objects:
            break
        objects.extend(page_objects)
    return {
        "total": _header_int(response.headers.get("X-WP-Total")),
        "latest_modified_gmt": _latest_modified(objects),
        "objects": objects,
    }


def _json_object_list(response: httpx.Response) -> list[dict[str, Any]]:
    content_type = response.headers.get("content-type", "").casefold()
    if "json" not in content_type:
        raise WordPressInventoryPayloadError(
            "WordPress inventory response has a non-JSON content type."
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise WordPressInventoryPayloadError(
            "WordPress inventory response contains malformed JSON."
        ) from exc
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise WordPressInventoryPayloadError(
            "WordPress inventory response must be a list of objects."
        )
    return payload


def _inventory_coverage_status(
    sitemap: _SitemapFetchResult,
    public_sitemap: _SitemapFetchResult,
) -> Literal["complete", "partial", "unavailable"]:
    relevant = [
        result
        for result in (sitemap, public_sitemap)
        if result.coverage_status != "not_applicable"
    ]
    if not relevant or all(result.coverage_status == "unavailable" for result in relevant):
        return "unavailable"
    if any(
        result.coverage_status in {"partial", "unavailable"} or result.truncated
        for result in relevant
    ):
        return "partial"
    return "complete"


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
