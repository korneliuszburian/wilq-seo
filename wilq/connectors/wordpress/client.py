from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from wilq.connectors.vendor import VendorReadResult
from wilq.connectors.wordpress.inventory import (
    WORDPRESS_CONTENT_PER_PAGE,
    WORDPRESS_CONTENT_TYPES,
    WORDPRESS_READ_FIELDS,
    _HtmlMetadataParser,
    acf_inventory,
    content_inventory,
    fetch_content_inventory,
)
from wilq.connectors.wordpress.text import (
    clean_metadata_text,
    html_text,
    summary_text_limited,
    wordpress_title,
)
from wilq.content.canonical.urls import content_is_safe_public_url, content_url_host
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
WORDPRESS_DEV_HOSTS = {"ekologus.dev.proudsite.pl"}

WORDPRESS_AUTHORING_PAGE_FIELDS = (
    "id,slug,link,title,status,modified,modified_gmt,template,parent,acf"
)
WORDPRESS_AUTHORING_SECTION_LIMIT = 40
WORDPRESS_AUTHORING_TEXT_CANDIDATE_LIMIT = 40
WORDPRESS_AUTHORING_FIELD_NAME_LIMIT = 20
WORDPRESS_AUTHORING_SECTION_SUMMARY_MAX_CHARS = 280


@dataclass(frozen=True)
class WordPressCredentials:
    base_url: str | None
    public_url: str | None
    username: str | None
    application_auth: str | None
    site_kind: str


@dataclass(frozen=True)
class WordPressDraftPostReadback:
    post_id: str
    status: str
    title: str
    link: str
    modified_gmt: str
    content_summary: str
    content_word_count: int | None
    acf_field_count: int | None
    acf_field_names: list[str]


@dataclass(frozen=True)
class WordPressAuthoringSectionReadback:
    section_index: int
    acf_field_name: str
    layout_name: str
    layout_label: str
    title: str
    text_summary: str
    field_names: list[str]
    text_field_paths: list[str]


@dataclass(frozen=True)
class WordPressAuthoringPageReadback:
    post_id: str
    slug: str
    title: str
    link: str
    status: str
    modified: str
    modified_gmt: str
    template: str
    parent: str
    acf_field_name: str | None
    section_count: int
    sections: list[WordPressAuthoringSectionReadback]


@dataclass(frozen=True)
class WordPressContentMaterial:
    url: str
    source_kind: str
    title: str
    content_text: str
    content_summary: str
    content_word_count: int | None
    section_headings: list[str]
    acf_field_names: list[str]
    acf_section_headings: list[str]
    modified_gmt: str
    extraction_region: str
    material_confidence: str
    source_field_lineage: list[str]


@dataclass(frozen=True)
class _AcfTextCandidate:
    path: tuple[str, ...]
    value: str
    score: int


class WordPressDraftWriteError(RuntimeError):
    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message


class WordPressDraftReadError(RuntimeError):
    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message


class WordPressAuthoringReadError(RuntimeError):
    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message


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
                f"WordPress vendor read blocked by missing credential names: {', '.join(missing)}."
            ),
            errors=[
                f"WordPress vendor read blocked by missing credential names: {', '.join(missing)}."
            ],
        )

    target_urls = [value.strip() for value in request.target_urls if value.strip()]
    if any(not content_is_safe_public_url(value) for value in target_urls):
        return VendorReadResult(
            status=ConnectorRefreshStatus.blocked,
            summary="WordPress vendor read blocked by an unsafe target URL.",
            errors=["WordPress vendor read blocked by an unsafe target URL."],
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    try:
        try:
            metric_summary, metric_facts = fetch_content_inventory(
                client,
                connector_id,
                base_url=credentials.base_url or "",
                public_url=credentials.public_url,
                username=credentials.username or "",
                application_auth=credentials.application_auth or "",
                site_kind=credentials.site_kind,
                priority_urls=target_urls,
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


def create_wordpress_draft_post(
    payload: object,
    *,
    connector_id: str = "wordpress_ekologus",
    http_client: httpx.Client | None = None,
) -> str:
    credentials = _wordpress_credentials(connector_id)
    if credentials is None:
        raise WordPressDraftWriteError("WILQ nie zna tego connectora WordPress.")
    if (urlparse(credentials.base_url or "").hostname or "").lower() not in WORDPRESS_DEV_HOSTS:
        raise WordPressDraftWriteError(
            "Adapter szkicu WordPress działa wyłącznie na zatwierdzonym hoście dev."
        )
    missing = _missing_credentials(connector_id, credentials)
    if missing:
        raise WordPressDraftWriteError(
            "Brakuje konfiguracji WordPress wymaganej do utworzenia szkicu."
        )
    if getattr(payload, "connector", connector_id) != connector_id:
        raise WordPressDraftWriteError("Payload szkicu nie pasuje do connectora WordPress.")
    if getattr(payload, "post_status", None) != "draft":
        raise WordPressDraftWriteError("Adapter może utworzyć wyłącznie szkic WordPress.")
    if getattr(payload, "publish_allowed", True) or getattr(
        payload, "destructive_update_allowed", True
    ):
        raise WordPressDraftWriteError(
            "Adapter blokuje publikację i destrukcyjne aktualizacje."
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    auth = httpx.BasicAuth(credentials.username or "", credentials.application_auth or "")
    try:
        try:
            response = client.post(
                urljoin(credentials.base_url or "", "wp-json/wp/v2/posts"),
                auth=auth,
                params={"_fields": "id,status,link"},
                json={
                    "status": "draft",
                    "title": getattr(payload, "title", ""),
                    "content": getattr(payload, "content_markdown", ""),
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise WordPressDraftWriteError(
                f"WordPress odrzucił utworzenie szkicu HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise WordPressDraftWriteError(
                f"Połączenie WordPress przerwało tworzenie szkicu ({type(exc).__name__})."
            ) from exc
    finally:
        if owns_client:
            client.close()

    return _created_draft_post_id(response)


def read_wordpress_draft_post(
    post_id: str,
    *,
    connector_id: str = "wordpress_ekologus",
    http_client: httpx.Client | None = None,
) -> WordPressDraftPostReadback:
    credentials = _wordpress_credentials(connector_id)
    if credentials is None:
        raise WordPressDraftReadError("WILQ nie zna tego connectora WordPress.")
    missing = _missing_credentials(connector_id, credentials)
    if missing:
        raise WordPressDraftReadError(
            "Brakuje konfiguracji WordPress wymaganej do odczytu szkicu."
        )
    normalized_post_id = str(post_id).strip()
    if not normalized_post_id:
        raise WordPressDraftReadError("Brakuje ID szkicu WordPress do odczytu.")

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    auth = httpx.BasicAuth(credentials.username or "", credentials.application_auth or "")
    try:
        try:
            response = client.get(
                urljoin(credentials.base_url or "", f"wp-json/wp/v2/posts/{normalized_post_id}"),
                auth=auth,
                params={
                    "context": "edit",
                    "_fields": WORDPRESS_READ_FIELDS,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise WordPressDraftReadError(
                f"WordPress odrzucił odczyt szkicu HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise WordPressDraftReadError(
                f"Połączenie WordPress przerwało odczyt szkicu ({type(exc).__name__})."
            ) from exc
    finally:
        if owns_client:
            client.close()

    return _draft_post_readback(response, normalized_post_id)


def read_wordpress_authoring_pages(
    connector_id: str = "wordpress_ekologus",
    *,
    preferred_flexible_field_name: str | None = None,
    content_type: str = "pages",
    limit: int = WORDPRESS_CONTENT_PER_PAGE,
    http_client: httpx.Client | None = None,
) -> list[WordPressAuthoringPageReadback]:
    credentials = _wordpress_credentials(connector_id)
    if credentials is None:
        raise WordPressAuthoringReadError("WILQ nie zna tego connectora WordPress.")
    missing = _missing_credentials(connector_id, credentials)
    if missing:
        raise WordPressAuthoringReadError(
            "Brakuje konfiguracji WordPress wymaganej do odczytu stron authoringu."
        )
    normalized_type = content_type.strip().strip("/")
    if normalized_type not in WORDPRESS_CONTENT_TYPES:
        raise WordPressAuthoringReadError("Nieobsługiwany typ treści WordPress.")

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=30)
    auth = httpx.BasicAuth(credentials.username or "", credentials.application_auth or "")
    try:
        try:
            response = client.get(
                urljoin(credentials.base_url or "", f"wp-json/wp/v2/{normalized_type}"),
                auth=auth,
                params={
                    "context": "edit",
                    "per_page": max(1, min(limit, WORDPRESS_CONTENT_PER_PAGE)),
                    "orderby": "modified",
                    "order": "desc",
                    "_fields": WORDPRESS_AUTHORING_PAGE_FIELDS,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise WordPressAuthoringReadError(
                f"WordPress odrzucił odczyt stron authoringu HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise WordPressAuthoringReadError(
                f"Połączenie WordPress przerwało odczyt stron authoringu ({type(exc).__name__})."
            ) from exc
    finally:
        if owns_client:
            client.close()

    return _authoring_pages_from_response(
        response.json(),
        preferred_flexible_field_name=preferred_flexible_field_name,
    )


def read_wordpress_content_material(
    url: str,
    connector_id: str = "wordpress_ekologus",
    *,
    http_client: httpx.Client | None = None,
) -> WordPressContentMaterial:
    """Read one public content object dynamically from REST or rendered HTML.

    REST is preferred because it can expose authenticated ``the_content`` and
    ACF. Public HTML is the deliberate fallback for posts whose public REST
    surface is disabled; it still returns only normalized visible text and
    headings, never raw vendor payloads.
    """
    if not content_is_safe_public_url(url):
        raise WordPressDraftReadError("WILQ odrzucił adres spoza bezpiecznego inventory.")
    credentials = _wordpress_credentials(connector_id)
    if credentials is None or _missing_credentials(connector_id, credentials):
        raise WordPressDraftReadError("Brakuje konfiguracji WordPress do odczytu materiału.")
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=20)
    try:
        requested_path = urlparse(url).path.rstrip("/") or "/"
        slug = requested_path.rsplit("/", 1)[-1]
        configured_host = content_url_host(credentials.base_url)
        requested_host = content_url_host(url)
        read_base_url = credentials.base_url or ""
        auth: httpx.BasicAuth | None = httpx.BasicAuth(
            credentials.username or "", credentials.application_auth or ""
        )
        rest_context = "edit"
        if requested_host and requested_host != configured_host:
            # The configured dev host owns safe authoring, but the canonical
            # public host owns the source material.  Read its public REST
            # representation without sending dev credentials across hosts.
            read_base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
            auth = None
            rest_context = "view"
        for content_type in WORDPRESS_CONTENT_TYPES:
            try:
                response = client.get(
                    urljoin(read_base_url, f"wp-json/wp/v2/{content_type}"),
                    auth=auth,
                    params={
                        "slug": slug,
                        "context": rest_context,
                        "_fields": WORDPRESS_READ_FIELDS,
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError:
                continue
            for item in response.json() if isinstance(response.json(), list) else []:
                if not isinstance(item, dict):
                    continue
                link = str(item.get("link") or "")
                if urlparse(link).path.rstrip("/") != requested_path:
                    continue
                return _material_from_rest_item(item, requested_url=url)

        response = client.get(url, timeout=20)
        response.raise_for_status()
        parser = _HtmlMetadataParser()
        parser.feed(response.text[:200_000])
        text = clean_metadata_text(" ".join(parser.main_text_chunks))
        if not text:
            raise WordPressDraftReadError("WordPress nie wystawił widocznego materiału treści.")
        return WordPressContentMaterial(
            url=url,
            source_kind="rendered_html",
            title=clean_metadata_text(parser.title or parser.h1),
            content_text=text,
            content_summary=summary_text_limited(text, 240),
            content_word_count=len(text.split()),
            section_headings=[
                clean_metadata_text(value)
                for value in parser.section_headings
                if clean_metadata_text(value)
            ],
            acf_field_names=[],
            acf_section_headings=[],
            modified_gmt="",
            extraction_region="main_or_article_visible_text",
            material_confidence="review_required",
            source_field_lineage=["public_html.main_or_article"],
        )
    except httpx.HTTPError as exc:
        raise WordPressDraftReadError("Odczyt materiału WordPress nie powiódł się.") from exc
    finally:
        if owns_client:
            client.close()


def _material_from_rest_item(
    item: dict[str, Any], *, requested_url: str
) -> WordPressContentMaterial:
    content = item.get("content")
    raw = content.get("raw") if isinstance(content, dict) else None
    rendered = content.get("rendered") if isinstance(content, dict) else None
    source = (
        raw
        if isinstance(raw, str) and raw.strip()
        else rendered
        if isinstance(rendered, str)
        else ""
    )
    text = clean_metadata_text(html_text(source))
    content_parser = _HtmlMetadataParser()
    content_parser.feed(source)
    content_parser.close()
    content_dimensions = content_inventory(content)
    acf_dimensions = acf_inventory(item.get("acf"))
    return WordPressContentMaterial(
        url=requested_url,
        source_kind="wordpress_rest",
        title=wordpress_title(item.get("title")),
        content_text=text,
        content_summary=content_dimensions.get("content_summary", ""),
        content_word_count=_optional_int(content_dimensions.get("content_word_count")),
        section_headings=content_parser.section_headings,
        acf_field_names=_json_string_list(acf_dimensions.get("acf_field_names_json")),
        acf_section_headings=_json_string_list(acf_dimensions.get("acf_section_headings_json")),
        modified_gmt=str(item.get("modified_gmt") or ""),
        extraction_region="wordpress_rest.content",
        material_confidence="source_bound",
        source_field_lineage=["wordpress_rest.content", "wordpress_rest.acf"],
    )


def _created_draft_post_id(response: httpx.Response) -> str:
    body = response.json()
    if not isinstance(body, dict):
        raise WordPressDraftWriteError("WordPress zwrócił nieprawidłową odpowiedź szkicu.")
    post_id = body.get("id")
    if post_id is None:
        raise WordPressDraftWriteError("WordPress nie zwrócił ID utworzonego szkicu.")
    if body.get("status") != "draft":
        raise WordPressDraftWriteError(
            "WordPress nie potwierdził, że utworzony wpis jest szkicem."
        )
    return str(post_id)


def _draft_post_readback(
    response: httpx.Response,
    requested_post_id: str,
) -> WordPressDraftPostReadback:
    body = response.json()
    if not isinstance(body, dict):
        raise WordPressDraftReadError("WordPress zwrócił nieprawidłową odpowiedź szkicu.")
    post_id = body.get("id")
    content_dimensions = content_inventory(body.get("content"))
    acf_dimensions = acf_inventory(body.get("acf"))
    acf_names = _json_string_list(acf_dimensions.get("acf_field_names_json"))
    content_word_count = _optional_int(content_dimensions.get("content_word_count"))
    acf_field_count = _optional_int(acf_dimensions.get("acf_field_count"))
    return WordPressDraftPostReadback(
        post_id=str(post_id) if post_id is not None else requested_post_id,
        status=str(body.get("status") or ""),
        title=wordpress_title(body.get("title")),
        link=str(body.get("link") or ""),
        modified_gmt=str(body.get("modified_gmt") or ""),
        content_summary=content_dimensions.get("content_summary", ""),
        content_word_count=content_word_count,
        acf_field_count=acf_field_count,
        acf_field_names=acf_names,
    )


def _json_string_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def _optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


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


def _authoring_pages_from_response(
    payload: Any,
    *,
    preferred_flexible_field_name: str | None,
) -> list[WordPressAuthoringPageReadback]:
    if not isinstance(payload, list):
        return []
    pages: list[WordPressAuthoringPageReadback] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        sections = _authoring_sections_from_acf(
            item.get("acf"),
            preferred_flexible_field_name=preferred_flexible_field_name,
        )
        acf_field_name = sections[0].acf_field_name if sections else None
        post_id = item.get("id")
        parent = item.get("parent")
        slug_value = item.get("slug")
        pages.append(
            WordPressAuthoringPageReadback(
                post_id=str(post_id) if post_id is not None else "",
                slug=clean_metadata_text(slug_value if isinstance(slug_value, str) else ""),
                title=wordpress_title(item.get("title")),
                link=str(item.get("link") or ""),
                status=str(item.get("status") or ""),
                modified=str(item.get("modified") or ""),
                modified_gmt=str(item.get("modified_gmt") or ""),
                template=str(item.get("template") or ""),
                parent=str(parent) if parent not in (None, 0, "0") else "",
                acf_field_name=acf_field_name,
                section_count=len(sections),
                sections=sections,
            )
        )
    return pages


def _authoring_sections_from_acf(
    value: Any,
    *,
    preferred_flexible_field_name: str | None,
) -> list[WordPressAuthoringSectionReadback]:
    rows = _acf_flexible_rows(value, preferred_flexible_field_name=preferred_flexible_field_name)
    sections: list[WordPressAuthoringSectionReadback] = []
    for index, (field_name, row) in enumerate(rows[:WORDPRESS_AUTHORING_SECTION_LIMIT], start=1):
        layout_name = clean_metadata_text(str(row.get("acf_fc_layout") or f"section_{index}"))
        field_names = _acf_top_level_field_names(row)
        candidates = sorted(_acf_text_candidates(row), key=lambda item: item.score, reverse=True)
        title = _best_acf_title(candidates)
        text_summary = _best_acf_summary(candidates, title)
        text_paths = [".".join(candidate.path) for candidate in candidates[:6]]
        sections.append(
            WordPressAuthoringSectionReadback(
                section_index=index,
                acf_field_name=field_name,
                layout_name=layout_name,
                layout_label=_humanize_layout_name(layout_name),
                title=title,
                text_summary=text_summary,
                field_names=field_names,
                text_field_paths=text_paths,
            )
        )
    return sections


def _acf_flexible_rows(
    value: Any,
    *,
    preferred_flexible_field_name: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    if not isinstance(value, dict):
        return []
    preferred = (preferred_flexible_field_name or "").strip()
    ordered_keys = list(value)
    if preferred in value:
        ordered_keys = [preferred, *[key for key in ordered_keys if key != preferred]]
    rows: list[tuple[str, dict[str, Any]]] = []
    for key in ordered_keys:
        raw_rows = value.get(key)
        if not isinstance(raw_rows, list):
            continue
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            if not clean_metadata_text(str(row.get("acf_fc_layout") or "")):
                continue
            rows.append((str(key), row))
    return rows


def _acf_top_level_field_names(row: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key, value in row.items():
        if key == "acf_fc_layout" or value in (None, "", [], {}):
            continue
        names.append(str(key))
        if len(names) >= WORDPRESS_AUTHORING_FIELD_NAME_LIMIT:
            break
    return names


def _acf_text_candidates(value: Any, path: tuple[str, ...] = ()) -> list[_AcfTextCandidate]:
    if len(path) > 8:
        return []
    if isinstance(value, str):
        clean_value = _clean_acf_text_value(value)
        if not clean_value:
            return []
        score = _acf_text_score(path, clean_value)
        if score <= 0:
            return []
        return [_AcfTextCandidate(path=path, value=clean_value, score=score)]
    if isinstance(value, dict):
        candidates: list[_AcfTextCandidate] = []
        for key, child in value.items():
            if key == "acf_fc_layout":
                continue
            candidates.extend(_acf_text_candidates(child, (*path, str(key))))
            if len(candidates) >= WORDPRESS_AUTHORING_TEXT_CANDIDATE_LIMIT:
                break
        return candidates
    if isinstance(value, list):
        candidates = []
        for index, child in enumerate(value[:8]):
            candidates.extend(_acf_text_candidates(child, (*path, f"row_{index + 1}")))
            if len(candidates) >= WORDPRESS_AUTHORING_TEXT_CANDIDATE_LIMIT:
                break
        return candidates
    return []


def _clean_acf_text_value(value: str) -> str:
    source = html_text(value) if "<" in value and ">" in value else value
    cleaned = clean_metadata_text(source)
    if len(cleaned) < 3:
        return ""
    lowered = cleaned.lower()
    if lowered.startswith(("http://", "https://", "mailto:", "tel:")):
        return ""
    if "@" in cleaned and " " not in cleaned:
        return ""
    if cleaned.replace(".", "").replace(",", "").isdigit():
        return ""
    if cleaned.lower() in _acf_non_content_values():
        return ""
    return summary_text_limited(cleaned, WORDPRESS_AUTHORING_SECTION_SUMMARY_MAX_CHARS)


def _acf_text_score(path: tuple[str, ...], value: str) -> int:
    path_text = " ".join(part.lower() for part in path)
    if any(token in path_text for token in _acf_skip_path_tokens()):
        return 0
    score = min(len(value), 120) // 4
    if any(token in path_text for token in _acf_title_path_tokens()):
        score += 80
    if any(token in path_text for token in _acf_body_path_tokens()):
        score += 45
    word_count = len(value.split())
    if 2 <= word_count <= 14:
        score += 12
    elif word_count > 35:
        score -= 8
    return score


def _best_acf_title(candidates: list[_AcfTextCandidate]) -> str:
    title_candidates = [
        candidate
        for candidate in candidates
        if len(candidate.value.split()) <= 18
        and _acf_path_has_any(candidate.path, _acf_title_path_tokens())
        and not _acf_path_has_any(candidate.path, _acf_body_path_tokens())
    ]
    if title_candidates:
        title_selected = sorted(
            title_candidates,
            key=lambda candidate: (-candidate.score, len(candidate.value)),
        )[0]
        return title_selected.value
    short_candidates = [candidate for candidate in candidates if len(candidate.value.split()) <= 18]
    selected: _AcfTextCandidate | None = (
        short_candidates[0] if short_candidates else (candidates[0] if candidates else None)
    )
    return selected.value if selected else ""


def _best_acf_summary(candidates: list[_AcfTextCandidate], title: str) -> str:
    chunks: list[str] = []
    for candidate in candidates:
        if candidate.value == title and chunks:
            continue
        if candidate.value not in chunks:
            chunks.append(candidate.value)
        summary = " ".join(chunks)
        if len(summary) >= WORDPRESS_AUTHORING_SECTION_SUMMARY_MAX_CHARS:
            return summary_text_limited(summary, WORDPRESS_AUTHORING_SECTION_SUMMARY_MAX_CHARS)
    return summary_text_limited(" ".join(chunks), WORDPRESS_AUTHORING_SECTION_SUMMARY_MAX_CHARS)


def _humanize_layout_name(value: str) -> str:
    cleaned = value.replace("_", " ").replace("-", " ").strip()
    return cleaned.capitalize() if cleaned else value


def _acf_path_has_any(path: tuple[str, ...], tokens: set[str]) -> bool:
    path_text = " ".join(part.lower() for part in path)
    return any(token in path_text for token in tokens)


def _acf_skip_path_tokens() -> set[str]:
    return {
        "url",
        "link",
        "href",
        "image",
        "img",
        "icon",
        "ikona",
        "obraz",
        "zdjecie",
        "zdjęcie",
        "file",
        "plik",
        "key",
        "id",
        "color",
        "colour",
        "kolor",
        "type",
        "typ",
        "align",
        "alignment",
        "position",
        "pozycja",
        "style",
        "variant",
        "theme",
        "background",
        "bg",
        "size",
    }


def _acf_title_path_tokens() -> set[str]:
    return {
        "heading",
        "title",
        "tytul",
        "tytuł",
        "naglowek",
        "nagłówek",
        "nazwa",
        "label",
        "name",
    }


def _acf_body_path_tokens() -> set[str]:
    return {
        "desc",
        "opis",
        "description",
        "tekst",
        "text",
        "content",
        "body",
        "lead",
        "copy",
        "akapit",
        "paragraph",
        "glowny",
        "główny",
    }


def _acf_non_content_values() -> set[str]:
    return {
        "primary",
        "secondary",
        "tertiary",
        "primary-light",
        "secondary-light",
        "left",
        "right",
        "center",
        "centre",
        "top",
        "bottom",
        "background-img",
        "background-image",
        "default",
        "none",
        "true",
        "false",
    }
