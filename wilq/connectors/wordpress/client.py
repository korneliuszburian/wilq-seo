from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from wilq.connectors.vendor import VendorMetricFact, VendorReadResult
from wilq.credentials.runtime import variable_value
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshStatus


def _wp_env(*parts: str) -> str:
    return "_".join(parts)


WORDPRESS_CONNECTORS = {
    "wordpress_ekologus": {
        "url": _wp_env("WORDPRESS", "EKOLOGUS", "URL"),
        "username": _wp_env("WORDPRESS", "EKOLOGUS", "USERNAME"),
        "application_auth": _wp_env("WORDPRESS", "EKOLOGUS", "APP", "PASSWORD"),
        "site_kind": "primary",
    },
    "wordpress_sklep": {
        "url": _wp_env("WORDPRESS", "SKLEP", "URL"),
        "username": _wp_env("WORDPRESS", "SKLEP", "USERNAME"),
        "application_auth": _wp_env("WORDPRESS", "SKLEP", "APP", "PASSWORD"),
        "site_kind": "shop",
    },
}

WORDPRESS_CONTENT_TYPES = ("posts", "pages")
WORDPRESS_CONTENT_PER_PAGE = 100
WORDPRESS_READ_FIELDS = "id,status,modified_gmt,date_gmt,link,slug"


@dataclass(frozen=True)
class WordPressCredentials:
    base_url: str | None
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
            "WordPress vendor read completed through REST content inventory. "
            f"Objects: {metric_summary['content_object_count']}."
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
    metric_summary: dict[str, float | int | str] = {
        "api": "wordpress_rest_content_inventory",
        "connector_id": connector_id,
        "site_kind": credentials.site_kind,
        "content_object_count": content_object_count,
        "posts_total": _summary_total(summaries["posts"]),
        "pages_total": _summary_total(summaries["pages"]),
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
                    },
                )
            )
    return metric_summary, metric_facts


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
            }
        )
    return objects
