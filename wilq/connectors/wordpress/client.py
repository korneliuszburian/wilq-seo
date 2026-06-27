from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import httpx
from defusedxml import ElementTree

from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus


def _wp_env(*parts: str) -> str:
    return "_".join(parts)


WORDPRESS_CONNECTORS = {
    "wordpress_ekologus": {
        "url": _wp_env("WORDPRESS", "EKOLOGUS", "URL"),
        "public_url": _wp_env("WORDPRESS", "EKOLOGUS", "PUBLIC", "URL"),
        "fallback_public_url": "https://www.ekologus.pl/",
        "username": _wp_env("WORDPRESS", "EKOLOGUS", "USERNAME"),
        "application_auth": _wp_env("WORDPRESS", "EKOLOGUS", "APP", "PASSWORD"),
        "site_kind": "primary",
    },
    "wordpress_sklep": {
        "url": _wp_env("WORDPRESS", "SKLEP", "URL"),
        "public_url": _wp_env("WORDPRESS", "SKLEP", "PUBLIC", "URL"),
        "fallback_public_url": "",
        "username": _wp_env("WORDPRESS", "SKLEP", "USERNAME"),
        "application_auth": _wp_env("WORDPRESS", "SKLEP", "APP", "PASSWORD"),
        "site_kind": "shop",
    },
}

WORDPRESS_CONTENT_TYPES = ("posts", "pages")
WORDPRESS_CONTENT_PER_PAGE = 100
WORDPRESS_READ_FIELDS = "id,status,modified_gmt,date_gmt,link,slug,title"
WORDPRESS_SITEMAP_PATHS = ("wp-sitemap.xml", "sitemap_index.xml", "sitemap.xml")
WORDPRESS_SITEMAP_CHILD_LIMIT = 20
WORDPRESS_SITEMAP_URL_LIMIT = 500
WORDPRESS_METADATA_FETCH_LIMIT = 50
WORDPRESS_METADATA_MAX_BYTES = 200_000
WORDPRESS_METADATA_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class WordPressCredentials:
    base_url: str | None
    public_url: str | None
    username: str | None
    application_auth: str | None
    site_kind: str


def refresh_wordpress_content_inventory(
    connector_id: str,
    request: ConnectorRefreshRequest,
    *,
    http_client: httpx.Client | None = None,
) -> VendorReadResult:
    credentials = _wordpress_credentials(connector_id)
    if credentials is None:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=f"WordPress vendor read blocked by unknown connector: {connector_id}.",
            errors=[f"WordPress vendor read blocked by unknown connector: {connector_id}."],
        )
    missing = _missing_credentials(connector_id, credentials)
    if missing:
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary=(
                "WordPress vendor read blocked by missing credential names: "
                f"{', '.join(missing)}."
            ),
            errors=[
                "WordPress vendor read blocked by missing credential names: "
                f"{', '.join(missing)}."
            ],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        try:
            metric_summary, metric_facts = _fetch_content_inventory(
                client,
                connector_id,
                credentials,
            )
        except httpx.HTTPStatusError as exc:
            return _http_failure_result(connector_id, exc)
        except httpx.HTTPError as exc:
            return _transport_failure_result(connector_id, exc)
    finally:
        if owns_client:
            client.close()

    return VendorReadResult(
        status=ConnectorRefreshStatus.completed,
        summary=(
            "Odczyt WordPress zakończony przez REST i spis z mapy strony. "
            f"Obiekty treści: {metric_summary['content_object_count']}."
        ),
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary=metric_summary,
        metric_facts=metric_facts,
    )


def _wordpress_credentials(connector_id: str) -> WordPressCredentials | None:
    names = WORDPRESS_CONNECTORS.get(connector_id)
    if names is None:
        return None
    return WordPressCredentials(
        base_url=_normalize_base_url(variable_value(names["url"])),
        public_url=_normalize_base_url(
            variable_value(names["public_url"]) or names["fallback_public_url"]
        ),
        username=variable_value(names["username"]),
        application_auth=variable_value(names["application_auth"]),
        site_kind=names["site_kind"],
    )


def _missing_credentials(
    connector_id: str,
    credentials: WordPressCredentials,
) -> list[str]:
    names = WORDPRESS_CONNECTORS[connector_id]
    missing: list[str] = []
    if not credentials.base_url:
        missing.append(names["url"])
    if not credentials.username:
        missing.append(names["username"])
    if not credentials.application_auth:
        missing.append(names["application_auth"])
    return missing


def _normalize_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped.rstrip("/") + "/"


def _fetch_content_inventory(
    client: httpx.Client,
    connector_id: str,
    credentials: WordPressCredentials,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    auth = httpx.BasicAuth(credentials.username or "", credentials.application_auth or "")
    summaries: dict[str, dict[str, int | str | list[dict[str, str]]]] = {}
    content_object_count = 0
    latest_modified_values: list[str] = []
    for content_type in WORDPRESS_CONTENT_TYPES:
        summary = _fetch_content_type_summary(
            client,
            credentials.base_url or "",
            content_type,
            auth,
        )
        summaries[content_type] = summary
        content_object_count += _summary_total(summary)
        latest = summary["latest_modified_gmt"]
        if isinstance(latest, str) and latest:
            latest_modified_values.append(latest)
    sitemap_objects = _fetch_sitemap_objects(client, credentials.base_url or "")
    public_sitemap_objects = _fetch_public_sitemap_objects(
        client,
        credentials.base_url,
        credentials.public_url,
    )
    metric_summary: dict[str, float | int | str] = {
        "api": "wordpress_rest_and_sitemap_content_inventory",
        "connector_id": connector_id,
        "site_kind": credentials.site_kind,
        "content_object_count": content_object_count,
        "posts_total": _summary_total(summaries["posts"]),
        "pages_total": _summary_total(summaries["pages"]),
        "sitemap_url_count": len(sitemap_objects),
        "public_sitemap_url_count": len(public_sitemap_objects),
        "latest_modified_gmt": max(latest_modified_values) if latest_modified_values else "",
        "latest_post_modified_gmt": str(summaries["posts"]["latest_modified_gmt"]),
        "latest_page_modified_gmt": str(summaries["pages"]["latest_modified_gmt"]),
    }
    metric_facts = [
        VendorMetricFact(
            name="content_object_count",
            value=_summary_total(summary),
            dimensions={
                "connector_id": connector_id,
                "site_kind": credentials.site_kind,
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
            metric_facts.append(
                VendorMetricFact(
                    name="content_object_seen",
                    value=1,
                    dimensions={
                        "connector_id": connector_id,
                        "site_kind": credentials.site_kind,
                        "content_type": content_type,
                        "object_id": item.get("object_id", ""),
                        "content_url": item.get("content_url", ""),
                        "status": item.get("status", ""),
                        "modified_gmt": item.get("modified_gmt", ""),
                        "title_or_h1": item.get("title_or_h1", ""),
                        "canonical_url": item.get("canonical_url", ""),
                        "inventory_source": "wordpress_rest",
                    },
                )
            )
    for item in sitemap_objects:
        metric_facts.append(
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": connector_id,
                    "site_kind": credentials.site_kind,
                    "content_type": item.get("content_type", "sitemap"),
                    "object_id": "",
                    "content_url": item.get("content_url", ""),
                    "status": "indexed",
                    "modified_gmt": item.get("modified_gmt", ""),
                    "title_or_h1": item.get("title_or_h1", ""),
                    "canonical_url": item.get("canonical_url", ""),
                    "inventory_source": "sitemap",
                },
            )
        )
    for item in public_sitemap_objects:
        metric_facts.append(
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": connector_id,
                    "site_kind": credentials.site_kind,
                    "content_type": item.get("content_type", "sitemap"),
                    "object_id": "",
                    "content_url": item.get("content_url", ""),
                    "status": "indexed",
                    "modified_gmt": item.get("modified_gmt", ""),
                    "title_or_h1": item.get("title_or_h1", ""),
                    "canonical_url": item.get("canonical_url", ""),
                    "inventory_source": "public_sitemap",
                },
            )
        )
    if sitemap_objects:
        metric_facts.append(
            VendorMetricFact(
                name="sitemap_url_count",
                value=len(sitemap_objects),
                dimensions={
                    "connector_id": connector_id,
                    "site_kind": credentials.site_kind,
                    "inventory_source": "sitemap",
                },
            )
        )
    if public_sitemap_objects:
        metric_facts.append(
            VendorMetricFact(
                name="public_sitemap_url_count",
                value=len(public_sitemap_objects),
                dimensions={
                    "connector_id": connector_id,
                    "site_kind": credentials.site_kind,
                    "inventory_source": "public_sitemap",
                },
            )
        )
    return metric_summary, metric_facts


def _fetch_public_sitemap_objects(
    client: httpx.Client,
    base_url: str | None,
    public_url: str | None,
) -> list[dict[str, str]]:
    if not public_url or _normalize_base_url(public_url) == _normalize_base_url(base_url):
        return []
    base_hosts = {_host(base_url or "")}
    public_objects = _fetch_sitemap_objects(client, public_url, enrich_metadata=False)
    filtered_objects = [
        item
        for item in public_objects
        if _host(item.get("content_url", "")) not in base_hosts
    ]
    return _enrich_sitemap_objects_with_page_metadata(client, filtered_objects)


def _fetch_sitemap_objects(
    client: httpx.Client,
    base_url: str,
    *,
    enrich_metadata: bool = True,
) -> list[dict[str, str]]:
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
            limited_objects = sitemap_objects[:WORDPRESS_SITEMAP_URL_LIMIT]
            if not enrich_metadata:
                return limited_objects
            return _enrich_sitemap_objects_with_page_metadata(client, limited_objects)
    return []


def _enrich_sitemap_objects_with_page_metadata(
    client: httpx.Client,
    objects: list[dict[str, str]],
) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []
    for index, item in enumerate(objects):
        if index >= WORDPRESS_METADATA_FETCH_LIMIT:
            enriched.append(item)
            continue
        metadata = _fetch_public_page_metadata(client, item.get("content_url", ""))
        enriched.append({**item, **metadata} if metadata else item)
    return enriched


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
    title_or_h1 = _clean_metadata_text(parser.title or parser.h1)
    canonical_url = _clean_metadata_text(parser.canonical_url)
    return {
        key: value
        for key, value in {
            "title_or_h1": title_or_h1,
            "canonical_url": canonical_url,
        }.items()
        if value
    }


def _sitemap_objects_from_xml(client: httpx.Client, xml_text: str) -> list[dict[str, str]]:
    entries = _parse_sitemap_xml(xml_text)
    child_sitemaps = [entry for entry in entries if entry["kind"] == "sitemap"]
    if not child_sitemaps:
        return [
            _sitemap_url_object(entry)
            for entry in entries
            if entry["kind"] == "url"
        ][:WORDPRESS_SITEMAP_URL_LIMIT]

    objects: list[dict[str, str]] = []
    for sitemap in child_sitemaps[:WORDPRESS_SITEMAP_CHILD_LIMIT]:
        try:
            response = client.get(sitemap["loc"])
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        child_entries = _parse_sitemap_xml(response.text)
        objects.extend(
            _sitemap_url_object(entry)
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
        loc = ""
        lastmod = ""
        for child in element:
            child_tag = _local_name(child.tag)
            text = (child.text or "").strip()
            if child_tag == "loc":
                loc = text
            elif child_tag == "lastmod":
                lastmod = text
        if loc:
            entries.append({"kind": tag, "loc": loc, "lastmod": lastmod})
    return entries


def _sitemap_url_object(entry: dict[str, str]) -> dict[str, str]:
    return {
        "content_type": "sitemap",
        "content_url": entry["loc"],
        "modified_gmt": entry.get("lastmod", ""),
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _host(value: str) -> str:
    return httpx.URL(value).host or ""


def _fetch_content_type_summary(
    client: httpx.Client,
    base_url: str,
    content_type: str,
    auth: httpx.BasicAuth,
) -> dict[str, int | str | list[dict[str, str]]]:
    response = client.get(
        urljoin(base_url, f"wp-json/wp/v2/{content_type}"),
        auth=auth,
        params={
            "per_page": WORDPRESS_CONTENT_PER_PAGE,
            "orderby": "modified",
            "order": "desc",
            "_fields": WORDPRESS_READ_FIELDS,
        },
    )
    response.raise_for_status()
    return {
        "total": _header_int(response.headers.get("X-WP-Total")),
        "latest_modified_gmt": _latest_modified(response.json()),
        "objects": _content_objects(response.json()),
    }


def _http_failure_result(connector_id: str, exc: httpx.HTTPStatusError) -> VendorReadResult:
    status_code = exc.response.status_code
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"WordPress content inventory failed with HTTP {status_code}.",
        external_call_attempted=True,
        errors=[f"WordPress {connector_id} content inventory HTTP {status_code}."],
    )


def _transport_failure_result(connector_id: str, exc: httpx.HTTPError) -> VendorReadResult:
    return VendorReadResult(
        status=ConnectorRefreshStatus.failed,
        summary=f"WordPress content inventory failed: {type(exc).__name__}.",
        external_call_attempted=True,
        errors=[f"WordPress {connector_id} content inventory {type(exc).__name__}."],
    )


def _header_int(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _summary_total(summary: dict[str, int | str | list[dict[str, str]]]) -> int:
    total = summary["total"]
    return total if isinstance(total, int) else 0


def _latest_modified(payload: Any) -> str:
    if not isinstance(payload, list):
        return ""
    for item in payload:
        if not isinstance(item, dict):
            continue
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
                "title_or_h1": _wordpress_title(item.get("title")),
                "canonical_url": "",
            }
        )
    return objects


def _wordpress_title(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    rendered = value.get("rendered")
    if not isinstance(rendered, str):
        return ""
    return _clean_metadata_text(rendered)


def _clean_metadata_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(unescape(value).split())


class _HtmlMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.h1 = ""
        self.canonical_url = ""
        self._capture: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        normalized_tag = tag.lower()
        if normalized_tag == "link" and not self.canonical_url:
            rel_values = attr_map.get("rel", "").lower().split()
            href = attr_map.get("href", "")
            if "canonical" in rel_values and href:
                self.canonical_url = href
        if normalized_tag == "title" and not self.title:
            self._capture = "title"
            self._chunks = []
        elif normalized_tag == "h1" and not self.h1:
            self._capture = "h1"
            self._chunks = []

    def handle_endtag(self, tag: str) -> None:
        if self._capture != tag.lower():
            return
        text = _clean_metadata_text("".join(self._chunks))
        if self._capture == "title" and text:
            self.title = text
        elif self._capture == "h1" and text:
            self.h1 = text
        self._capture = None
        self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._chunks.append(data)
