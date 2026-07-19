from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from threading import RLock
from time import monotonic
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.client import (
    WordPressDraftReadError,
    read_wordpress_content_material,
)
from wilq.content.canonical.landing_identity import (
    landing_page_metric_lookup_path,
    landing_page_metric_lookup_urls,
)
from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

_INVENTORY_CATALOG_CACHE_SECONDS = 30.0
_inventory_catalog_cache: tuple[float, ContentInventoryCatalogResponse] | None = None
_inventory_catalog_cache_lock = RLock()
_INVENTORY_MATERIAL_CACHE_SECONDS = 30.0
_inventory_material_cache: dict[
    tuple[str, str | None], tuple[float, ContentInventoryMaterialResponse]
] = {}
_inventory_material_cache_lock = RLock()


class ContentInventoryCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    path: str = Field(min_length=1)
    title: str | None = None
    content_type: str = Field(min_length=1)
    content_summary: str | None = None
    content_word_count: int | None = None
    section_count: int | None = None
    acf_section_count: int | None = None
    acf_field_names: list[str] = Field(default_factory=list)
    material_status: str = Field(min_length=1)
    acf_section_headings: list[str] = Field(default_factory=list)
    source_connector: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    collected_at: datetime
    metrics_status: str = "missing"
    metrics_evidence_ids: list[str] = Field(default_factory=list)
    metrics_query_count: int = 0
    metrics_clicks: int = 0
    metrics_impressions: int = 0


class ContentInventoryCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "unknown"
    source_count: int | None = None
    returned_count: int = 0
    public_sitemap_source_count: int | None = None
    public_sitemap_returned_count: int | None = None
    public_sitemap_limit: int | None = None
    public_sitemap_truncated: bool | None = None
    limit: int | None = None
    truncated: bool | None = None
    caveat: str = "Brak coverage z aktualnego odczytu WordPress."


class ContentInventoryCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ready"
    total_count: int
    ready_count: int = 0
    partial_count: int = 0
    blocked_count: int = 0
    items: list[ContentInventoryCatalogItem] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage: ContentInventoryCoverage = Field(default_factory=ContentInventoryCoverage)


class ContentInventoryMaterialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    url: str
    source_kind: str | None = None
    title: str | None = None
    content_text: str | None = None
    content_summary: str | None = None
    content_word_count: int | None = None
    section_headings: list[str] = Field(default_factory=list)
    acf_field_names: list[str] = Field(default_factory=list)
    acf_section_headings: list[str] = Field(default_factory=list)
    modified_gmt: str | None = None
    evidence_id: str | None = None
    blocker_code: str | None = None
    blocker: str | None = None
    extraction_region: str | None = None
    material_confidence: str | None = None
    source_field_lineage: list[str] = Field(default_factory=list)


class ContentInventoryBindingRequest(BaseModel):
    url: str = Field(min_length=1)


class ContentInventoryBindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    url: str
    work_item_id: str | None = None
    title: str | None = None
    evidence_id: str | None = None
    material_status: str | None = None
    material_source_kind: str | None = None
    material_confidence: str | None = None
    extraction_region: str | None = None
    source_field_lineage: list[str] = Field(default_factory=list)
    blocker_code: str | None = None
    blocker: str | None = None
    metrics_status: str = "not_evaluated"
    metrics_evidence_ids: list[str] = Field(default_factory=list)
    knowledge_status: str = "not_evaluated"
    generation_status: str = "blocked_until_service_and_metrics"


def build_content_inventory_catalog() -> ContentInventoryCatalogResponse:
    rows: dict[str, ContentInventoryCatalogItem] = {}
    metric_by_path = _catalog_metric_facts_by_path()
    for fact in _latest_wordpress_inventory_facts():
        if fact.name != "content_object_seen":
            continue
        dimensions: dict[str, Any] = fact.dimensions
        url = str(dimensions.get("content_url") or dimensions.get("canonical_url") or "").strip()
        if not content_is_safe_public_url(url) or url in rows:
            continue
        headings = _json_list(dimensions.get("acf_section_headings_json"))
        acf_fields = _json_list(dimensions.get("acf_field_names_json"))
        summary = _optional_text(dimensions.get("content_summary"))
        word_count = _optional_int(dimensions.get("content_word_count"))
        material_status = _material_status(summary, headings, acf_fields, word_count)
        metric_facts = metric_by_path.get(_path(url), [])
        metric_evidence_ids = sorted({fact.evidence_id for fact in metric_facts})
        metrics_clicks = sum(
            _metric_numeric_value(fact) for fact in metric_facts if fact.name == "clicks"
        )
        metrics_impressions = sum(
            _metric_numeric_value(fact)
            for fact in metric_facts
            if fact.name == "impressions"
        )
        metrics_query_count = len(
            {
                fact.dimensions.get("query")
                for fact in metric_facts
                if fact.dimensions.get("query")
            }
        )
        rows[url] = ContentInventoryCatalogItem(
            catalog_id=f"content_inventory_{sha256(url.encode()).hexdigest()[:20]}",
            work_item_id=inventory_work_item_id(url),
            url=url,
            path=_path(url),
            title=_optional_text(dimensions.get("title_or_h1")),
            content_type=str(dimensions.get("content_type") or "unknown"),
            content_summary=summary,
            content_word_count=word_count,
            section_count=_optional_int(dimensions.get("section_heading_count")),
            acf_section_count=_optional_int(dimensions.get("acf_section_count")),
            acf_field_names=acf_fields,
            material_status=material_status,
            acf_section_headings=headings,
            source_connector=fact.source_connector,
            evidence_id=fact.evidence_id,
            collected_at=fact.collected_at,
            metrics_status="available" if metric_facts else "missing",
            metrics_evidence_ids=metric_evidence_ids,
            metrics_query_count=metrics_query_count,
            metrics_clicks=metrics_clicks,
            metrics_impressions=metrics_impressions,
        )
    items = sorted(rows.values(), key=lambda item: (item.path.casefold(), item.url))
    return ContentInventoryCatalogResponse(
        total_count=len(items),
        ready_count=sum(
            item.material_status in {"content_summary", "content_and_structure"}
            for item in items
        ),
        partial_count=sum(item.material_status == "structure_only" for item in items),
        blocked_count=sum(item.material_status == "url_only" for item in items),
        items=items,
        source_connectors=sorted({item.source_connector for item in items}),
        evidence_ids=sorted({item.evidence_id for item in items}),
        coverage=_inventory_coverage(),
    )


def _latest_wordpress_inventory_facts() -> list[Any]:
    """Read one exact WordPress refresh batch, not an unbounded history union."""
    return _latest_connector_refresh_facts("wordpress_ekologus")


def _latest_connector_refresh_facts(connector_id: str) -> list[Any]:
    """Read one connector batch so catalog metrics never sum refresh history."""
    store = metric_store()
    runs = local_state_store().list_connector_refresh_runs(
        connector_id=connector_id
    )
    latest = next(
        (
            run
            for run in runs
            if run.mode.value == "vendor_read" and run.status.value == "completed"
        ),
        None,
    )
    evidence_ids = [] if latest is None else list(latest.evidence_ids)
    by_evidence = getattr(store, "list_metric_facts_by_evidence_ids", None)
    if evidence_ids and callable(by_evidence):
        return cast(list[Any], by_evidence(evidence_ids))
    # Keep lightweight test doubles and pre-migration local stores readable;
    # production DuckDB always has the evidence-scoped method above.
    return store.list_metric_facts(connector_id, limit=5000)


def _inventory_coverage() -> ContentInventoryCoverage:
    runs = local_state_store().list_connector_refresh_runs(
        connector_id="wordpress_ekologus"
    )
    latest = next(
        (
            run
            for run in runs
            if run.mode.value == "vendor_read" and run.status.value == "completed"
        ),
        None,
    )
    if latest is None:
        return ContentInventoryCoverage()
    summary = latest.metric_summary
    source_count = _coverage_int(summary.get("sitemap_url_source_count"))
    returned_count = _coverage_int(summary.get("sitemap_url_returned_count"))
    public_sitemap_returned_count = _coverage_int(summary.get("public_sitemap_url_count"))
    public_sitemap_source_count = _coverage_int(summary.get("public_sitemap_url_source_count"))
    public_sitemap_returned = _coverage_int(summary.get("public_sitemap_url_returned_count"))
    public_sitemap_limit = _coverage_int(summary.get("public_sitemap_url_limit"))
    public_sitemap_truncated = _coverage_bool(summary.get("public_sitemap_url_truncated"))
    limit = _coverage_int(summary.get("sitemap_url_limit"))
    truncated = _coverage_bool(summary.get("sitemap_url_truncated"))
    if not all(isinstance(value, int) for value in (source_count, returned_count, limit)):
        return ContentInventoryCoverage(
            status="unknown",
            returned_count=int(summary.get("sitemap_url_count", 0) or 0),
            public_sitemap_source_count=(
                int(public_sitemap_source_count)
                if isinstance(public_sitemap_source_count, (int, float))
                else None
            ),
            public_sitemap_returned_count=(
                int(public_sitemap_returned)
                if isinstance(public_sitemap_returned, (int, float))
                else (
                    int(public_sitemap_returned_count)
                    if isinstance(public_sitemap_returned_count, (int, float))
                    else None
                )
            ),
            public_sitemap_limit=(
                int(public_sitemap_limit)
                if isinstance(public_sitemap_limit, (int, float))
                else None
            ),
            public_sitemap_truncated=(
                bool(public_sitemap_truncated)
                if isinstance(public_sitemap_truncated, bool)
                else None
            ),
            caveat=(
                "Ostatni odczyt nie zapisał liczników coverage; nie traktuj inventory "
                "jako pełnego."
            ),
        )
    public_coverage_unknown = (
        public_sitemap_source_count is not None
        and public_sitemap_returned is not None
        and public_sitemap_limit is not None
        and public_sitemap_source_count >= public_sitemap_limit
        and public_sitemap_returned >= public_sitemap_limit
        and not isinstance(public_sitemap_truncated, bool)
    )
    return ContentInventoryCoverage(
        status=(
            "truncated"
            if truncated or public_sitemap_truncated is True
            else "unknown"
            if public_coverage_unknown
            else "complete"
        ),
        source_count=source_count,
        returned_count=returned_count or 0,
        public_sitemap_source_count=(
            int(public_sitemap_source_count)
            if isinstance(public_sitemap_source_count, (int, float))
            else None
        ),
        public_sitemap_returned_count=(
            int(public_sitemap_returned)
            if isinstance(public_sitemap_returned, (int, float))
            else (
                int(public_sitemap_returned_count)
                if isinstance(public_sitemap_returned_count, (int, float))
                else None
            )
        ),
        public_sitemap_limit=(
            int(public_sitemap_limit)
            if isinstance(public_sitemap_limit, (int, float))
            else None
        ),
        public_sitemap_truncated=(
            bool(public_sitemap_truncated)
            if isinstance(public_sitemap_truncated, bool)
            else None
        ),
        limit=limit,
        truncated=bool(truncated),
        caveat=(
            "Sitemap przekroczył limit; część adresów wymaga osobnego odczytu."
            if truncated or public_sitemap_truncated is True
            else (
                "Publiczna sitemap osiągnęła limit, ale starszy odczyt nie zapisał "
                "flagi ucięcia; kompletność wymaga ponownego odczytu."
                if public_coverage_unknown
                else "Liczba adresów mieści się w limicie tego odczytu; nie oznacza to "
                "kompletności danych ACF."
            )
        ),
    )


def _coverage_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _coverage_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def build_content_inventory_catalog_cached() -> ContentInventoryCatalogResponse:
    """Reuse one short-lived inventory read across the workflow request waterfall."""
    global _inventory_catalog_cache
    now = monotonic()
    with _inventory_catalog_cache_lock:
        if (
            _inventory_catalog_cache is not None
            and now - _inventory_catalog_cache[0] < _INVENTORY_CATALOG_CACHE_SECONDS
        ):
            return _inventory_catalog_cache[1]
    catalog = build_content_inventory_catalog()
    with _inventory_catalog_cache_lock:
        _inventory_catalog_cache = (now, catalog)
    return catalog


def read_content_inventory_material(
    url: str,
    *,
    catalog: ContentInventoryCatalogResponse | None = None,
) -> ContentInventoryMaterialResponse:
    """Read one live material while reusing a caller's current inventory snapshot."""
    catalog = catalog or build_content_inventory_catalog_cached()
    item = next(
        (
            candidate
            for candidate in catalog.items
            if candidate.url.rstrip("/") == url.rstrip("/")
        ),
        None,
    )
    evidence_id = item.evidence_id if item else None
    cache_key = (url.rstrip("/"), evidence_id)
    now = monotonic()
    with _inventory_material_cache_lock:
        cached = _inventory_material_cache.get(cache_key)
        if cached is not None and now - cached[0] < _INVENTORY_MATERIAL_CACHE_SECONDS:
            cached_material = cached[1]
            return cached_material.model_copy(update={"evidence_id": evidence_id})
        if cached is not None:
            _inventory_material_cache.pop(cache_key, None)
    try:
        wordpress_material = read_wordpress_content_material(url)
    except WordPressDraftReadError as exc:
        response = ContentInventoryMaterialResponse(
            status="blocked",
            url=url,
            evidence_id=evidence_id,
            blocker_code="material_unavailable",
            blocker=str(exc),
            extraction_region=None,
            material_confidence=None,
            source_field_lineage=[],
        )
    else:
        response = ContentInventoryMaterialResponse(
            status="ready",
            url=wordpress_material.url,
            source_kind=wordpress_material.source_kind,
            title=wordpress_material.title,
            content_text=wordpress_material.content_text,
            content_summary=wordpress_material.content_summary,
            content_word_count=wordpress_material.content_word_count,
            section_headings=wordpress_material.section_headings,
            acf_field_names=wordpress_material.acf_field_names,
            acf_section_headings=wordpress_material.acf_section_headings,
            modified_gmt=wordpress_material.modified_gmt,
            evidence_id=evidence_id,
            extraction_region=wordpress_material.extraction_region,
            material_confidence=wordpress_material.material_confidence,
            source_field_lineage=wordpress_material.source_field_lineage,
        )
    with _inventory_material_cache_lock:
        _inventory_material_cache[cache_key] = (now, response)
    return response


def bind_content_inventory_item(url: str) -> ContentInventoryBindingResponse:
    catalog = build_content_inventory_catalog_cached()
    item = next(
        (
            candidate
            for candidate in catalog.items
            if candidate.url.rstrip("/") == url.rstrip("/")
        ),
        None,
    )
    if item is None:
        return ContentInventoryBindingResponse(
            status="blocked",
            url=url,
            blocker_code="inventory_url_not_found",
            blocker="Ten adres nie występuje w aktualnym, evidence-bound inventory WordPress.",
        )
    metric_facts = inventory_metric_facts(item.url, item.path)
    # Catalog rows are intentionally cheap and may only contain a URL when
    # public REST/ACF did not expose the article. Resolve the selected URL once
    # at the binding seam so the marketer does not receive a false `url_only`
    # state when the public `the_content` fallback is readable. The selected
    # material is still read-only and remains review-required when it came from
    # rendered HTML.
    material_status = item.material_status
    title = item.title
    material_source_kind = (
        "wordpress_inventory_snapshot"
        if item.material_status != "url_only"
        else None
    )
    material_confidence = "source_bound" if item.material_status != "url_only" else None
    extraction_region = None
    source_field_lineage = (
        ["wordpress_inventory.content_object_seen"]
        if item.material_status != "url_only"
        else []
    )
    if item.material_status == "url_only":
        material = read_content_inventory_material(item.url, catalog=catalog)
        if material.status == "ready" and material.content_text:
            material_status = (
                "content_and_structure"
                if material.section_headings or material.acf_field_names
                else "content_summary"
            )
            title = title or material.title
            material_source_kind = material.source_kind
            material_confidence = material.material_confidence
            extraction_region = material.extraction_region
            source_field_lineage = material.source_field_lineage
    return ContentInventoryBindingResponse(
        status="ready",
        url=item.url,
        work_item_id=inventory_work_item_id(item.url),
        title=title,
        evidence_id=item.evidence_id,
        material_status=material_status,
        material_source_kind=material_source_kind,
        material_confidence=material_confidence,
        extraction_region=extraction_region,
        source_field_lineage=source_field_lineage,
        metrics_status="available" if metric_facts else "missing",
        metrics_evidence_ids=sorted({fact.evidence_id for fact in metric_facts}),
        # Binding only proves the URL/inventory seam. Service-card matching is
        # evaluated later, after the marketer chooses the page and current
        # source context; do not present it as a failed match here.
        knowledge_status="not_evaluated",
        generation_status="blocked_until_service_and_metrics",
    )


def inventory_work_item_id(url: str) -> str:
    return f"content_work_item_inventory_{sha256(url.rstrip('/').encode()).hexdigest()[:24]}"


def inventory_metric_facts(url: str, path: str) -> list[Any]:
    facts: list[Any] = []
    for lookup_url in landing_page_metric_lookup_urls(url):
        for connector_id in ("google_search_console", "google_analytics_4"):
            connector_facts = metric_store().list_metric_facts_for_content_url(
                [connector_id],
                lookup_url,
                content_path=landing_page_metric_lookup_path(url) or path,
            )
            facts.extend(_restrict_to_latest_refresh_batch(connector_id, connector_facts))
    return list({fact.model_dump_json(): fact for fact in facts}.values())


def _restrict_to_latest_refresh_batch(connector_id: str, facts: list[Any]) -> list[Any]:
    """Prevent demand rows from mixing evidence across connector refresh history."""
    runs = local_state_store().list_connector_refresh_runs(connector_id=connector_id)
    latest = next(
        (
            run
            for run in runs
            if run.mode.value == "vendor_read" and run.status.value == "completed"
        ),
        None,
    )
    if latest is None or not latest.evidence_ids:
        return facts
    allowed = set(latest.evidence_ids)
    return [fact for fact in facts if fact.evidence_id in allowed]


def _catalog_metric_facts_by_path() -> dict[str, list[Any]]:
    """Read the optional analytics snapshot once for the 601-row catalog."""
    try:
        facts = _latest_connector_refresh_facts("google_search_console")
    except AttributeError:
        return {}
    indexed: dict[str, list[Any]] = {}
    for fact in facts:
        page = str(fact.dimensions.get("page") or fact.dimensions.get("content_url") or "")
        path = _path(page) if page else ""
        if path:
            indexed.setdefault(path, []).append(fact)
    return indexed


def _path(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path or "/"


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _metric_numeric_value(fact: Any) -> int:
    try:
        return int(float(fact.value))
    except (TypeError, ValueError):
        return 0


def _json_list(value: Any) -> list[str]:
    import json

    if not value:
        return []
    try:
        decoded = json.loads(str(value))
    except (TypeError, ValueError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item).strip() for item in decoded if str(item).strip()]


def _material_status(
    summary: str | None,
    headings: list[str],
    acf_fields: list[str],
    word_count: int | None,
) -> str:
    if summary and word_count is not None and (headings or acf_fields):
        return "content_and_structure"
    if summary and word_count is not None:
        return "content_summary"
    if headings or acf_fields:
        return "structure_only"
    return "url_only"


__all__ = [
    "ContentInventoryCatalogResponse",
    "ContentInventoryMaterialResponse",
    "ContentInventoryBindingRequest",
    "ContentInventoryBindingResponse",
    "bind_content_inventory_item",
    "build_content_inventory_catalog",
    "read_content_inventory_material",
    "inventory_work_item_id",
    "inventory_metric_facts",
]
