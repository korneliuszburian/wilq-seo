"""Build an exact, read-only scope from the latest complete WordPress sitemap."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal, NoReturn, Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.connectors.registry import get_connector_status
from wilq.content.canonical.urls import (
    content_is_safe_public_url,
    content_normalized_path,
    content_normalized_url,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog,
    inventory_work_item_id,
    latest_wordpress_vendor_read_evidence_ids,
)
from wilq.evidence.registry import refresh_run_evidence_id
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store

InventoryScopeDisposition = Literal["eligible", "excluded", "blocked"]


class CurrentInventoryReconciliationBlocked(ValueError):
    """Typed blocker raised before current inventory can be reconciled."""

    def __init__(self, detail: str, coverage_status: str, evidence_ids: list[str]) -> None:
        super().__init__(detail)
        self.detail = detail
        self.coverage_status = coverage_status
        self.evidence_ids = evidence_ids


class CurrentInventoryScopeRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    disposition: InventoryScopeDisposition
    current_work_item_id: str | None = Field(default=None, max_length=240)
    source_evidence_ids: tuple[str, ...] = Field(min_length=1)
    catalog_evidence_ids: tuple[str, ...] = ()
    reason_code: str | None = Field(default=None, max_length=120)
    blocker_code: str | None = Field(default=None, max_length=120)
    blocker_owner: str | None = Field(default=None, max_length=160)
    safe_next_step: str = Field(min_length=1)
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_exact_disposition_shape(self) -> Self:
        if self.source_evidence_ids != tuple(sorted(set(self.source_evidence_ids))):
            raise ValueError("Inventory scope source evidence IDs must be sorted and unique.")
        if self.catalog_evidence_ids != tuple(sorted(set(self.catalog_evidence_ids))):
            raise ValueError("Inventory scope catalog evidence IDs must be sorted and unique.")
        if self.disposition == "eligible":
            if (
                not self.current_work_item_id
                or not self.catalog_evidence_ids
                or self.reason_code is not None
                or self.blocker_code is not None
                or self.blocker_owner is not None
            ):
                raise ValueError("Eligible scope rows require one exact catalog binding.")
        elif self.disposition == "excluded":
            if (
                self.current_work_item_id is not None
                or self.reason_code is None
                or self.blocker_code is not None
                or self.blocker_owner is not None
            ):
                raise ValueError("Excluded scope rows require one typed exclusion reason.")
        elif (
            self.reason_code is not None
            or self.blocker_code is None
            or self.blocker_owner is None
        ):
            raise ValueError("Blocked scope rows require one typed blocker.")
        return self


class CurrentInventoryScopeCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rows: int = Field(ge=0)
    eligible: int = Field(ge=0)
    excluded: int = Field(ge=0)
    blocked: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_cover_rows(self) -> Self:
        if self.rows != self.eligible + self.excluded + self.blocked:
            raise ValueError("Current inventory scope counts do not cover every row.")
        return self


class CurrentInventoryScopeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["current_inventory_scope"] = "current_inventory_scope"
    status: Literal["complete"] = "complete"
    coverage_status: Literal["complete"] = "complete"
    checked_at: datetime
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1)
    counts: CurrentInventoryScopeCounts
    rows: tuple[CurrentInventoryScopeRow, ...]
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_complete_unique_scope(self) -> Self:
        paths = tuple(row.canonical_path for row in self.rows)
        if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError("Current inventory scope rows must have unique canonical order.")
        if self.counts.rows != len(self.rows):
            raise ValueError("Current inventory scope count does not match its rows.")
        if self.inventory_evidence_ids != tuple(sorted(set(self.inventory_evidence_ids))):
            raise ValueError("Current inventory evidence IDs must be sorted and unique.")
        if self.checked_at.tzinfo is None or self.checked_at.utcoffset() is None:
            raise ValueError("Current inventory check time must be timezone-aware.")
        return self


def build_current_inventory_scope() -> CurrentInventoryScopeResponse:
    """Partition every current public sitemap URL once, without writing decisions."""

    catalog = build_content_inventory_catalog()
    coverage = catalog.coverage
    source_evidence_ids = tuple(sorted(set(latest_wordpress_vendor_read_evidence_ids())))
    if not source_evidence_ids:
        _blocked("inventory_source_evidence_missing", coverage.status, [])
    if not set(catalog.evidence_ids).issubset(source_evidence_ids):
        _blocked("inventory_catalog_binding_invalid", coverage.status, list(source_evidence_ids))
    evidence_ids = tuple(sorted(set(catalog.evidence_ids) | set(source_evidence_ids)))
    if coverage.status != "complete" or _coverage_is_incomplete(catalog):
        _blocked("inventory_coverage_incomplete", coverage.status, list(evidence_ids))

    source_run = _source_run_for_evidence(
        source_evidence_ids,
        coverage.status,
        list(evidence_ids),
    )
    connector_status = get_connector_status("wordpress_ekologus")
    freshness = None if connector_status is None else connector_status.freshness
    if freshness is None or freshness.state != "fresh":
        _blocked("inventory_source_freshness_blocked", coverage.status, list(evidence_ids))
    if freshness.last_success_at != source_run.completed_at:
        _blocked("inventory_source_freshness_batch_mismatch", coverage.status, list(evidence_ids))

    facts = metric_store().list_metric_facts_by_evidence_ids(list(source_evidence_ids))
    sitemap_facts = [
        fact
        for fact in facts
        if fact.name == "content_object_seen"
        and fact.dimensions.get("inventory_source") == "public_sitemap"
    ]
    expected_count = coverage.public_sitemap_source_count
    if (
        expected_count is None
        or expected_count <= 0
        or coverage.public_sitemap_returned_count != expected_count
        or len(sitemap_facts) != expected_count
    ):
        _blocked("inventory_sitemap_count_mismatch", coverage.status, list(evidence_ids))

    catalog_by_url = _catalog_by_exact_url(catalog, source_evidence_ids, evidence_ids)
    rows: list[CurrentInventoryScopeRow] = []
    seen_paths: set[str] = set()
    sitemap_urls: set[str] = set()
    for fact in sitemap_facts:
        row = _scope_row(
            fact,
            catalog_by_url=catalog_by_url,
            source_evidence_ids=source_evidence_ids,
        )
        if row.canonical_path in seen_paths:
            _blocked("inventory_sitemap_duplicate_url", coverage.status, list(evidence_ids))
        seen_paths.add(row.canonical_path)
        sitemap_urls.add(content_normalized_url(row.public_url))
        rows.append(row)

    if set(catalog_by_url) - sitemap_urls:
        _blocked("inventory_catalog_outside_sitemap", coverage.status, list(evidence_ids))

    rows.sort(key=lambda row: row.canonical_path)
    return CurrentInventoryScopeResponse(
        checked_at=datetime.now(UTC),
        inventory_evidence_ids=evidence_ids,
        counts=CurrentInventoryScopeCounts(
            rows=len(rows),
            eligible=sum(row.disposition == "eligible" for row in rows),
            excluded=sum(row.disposition == "excluded" for row in rows),
            blocked=sum(row.disposition == "blocked" for row in rows),
        ),
        rows=tuple(rows),
    )


def _source_run_for_evidence(
    source_evidence_ids: tuple[str, ...],
    coverage_status: str,
    evidence_ids: list[str],
) -> ConnectorRefreshRun:
    allowed = set(source_evidence_ids)
    matches = [
        run
        for run in local_state_store().list_connector_refresh_runs(
            connector_id="wordpress_ekologus"
        )
        if refresh_run_evidence_id(run.id) in allowed
    ]
    if len(matches) != 1:
        _blocked("inventory_source_run_evidence_mismatch", coverage_status, evidence_ids)
    run = matches[0]
    if (
        run.mode != ConnectorRefreshMode.vendor_read
        or run.status != ConnectorRefreshStatus.completed
        or not run.metrics_persisted
        or not run.vendor_data_collected
        or run.completed_at is None
    ):
        _blocked("inventory_source_run_incomplete", coverage_status, evidence_ids)
    return run


def _coverage_is_incomplete(catalog: ContentInventoryCatalogResponse) -> bool:
    coverage = catalog.coverage
    source_count = coverage.public_sitemap_source_count
    returned_count = coverage.public_sitemap_returned_count
    limit = coverage.public_sitemap_limit
    return (
        source_count is None
        or returned_count is None
        or source_count != returned_count
        or coverage.public_sitemap_truncated is True
        or coverage.truncated is True
        or (
            limit is not None
            and source_count >= limit
            and coverage.public_sitemap_truncated is not False
        )
    )


def _catalog_by_exact_url(
    catalog: ContentInventoryCatalogResponse,
    source_evidence_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
) -> dict[str, ContentInventoryCatalogItem]:
    by_url: dict[str, ContentInventoryCatalogItem] = {}
    by_path: set[str] = set()
    allowed_evidence = set(source_evidence_ids)
    for item in catalog.items:
        if not content_is_safe_public_url(item.url):
            _blocked(
                "inventory_catalog_binding_invalid",
                catalog.coverage.status,
                list(evidence_ids),
            )
        normalized_url = content_normalized_url(item.url)
        canonical_path = content_normalized_path(item.url)
        if (
            not normalized_url
            or not canonical_path
            or item.path != (urlparse(item.url).path or "/")
            or item.source_connector != "wordpress_ekologus"
            or item.evidence_id not in allowed_evidence
            or item.work_item_id != inventory_work_item_id(item.url)
            or normalized_url in by_url
            or canonical_path in by_path
        ):
            _blocked(
                "inventory_catalog_binding_invalid",
                catalog.coverage.status,
                list(evidence_ids),
            )
        by_url[normalized_url] = item
        by_path.add(canonical_path)
    return by_url


def _scope_row(
    fact: MetricFact,
    *,
    catalog_by_url: Mapping[str, ContentInventoryCatalogItem],
    source_evidence_ids: tuple[str, ...],
) -> CurrentInventoryScopeRow:
    dimensions = fact.dimensions
    source_url = str(dimensions.get("content_url") or "").strip()
    if (
        fact.source_connector != "wordpress_ekologus"
        or fact.evidence_id not in source_evidence_ids
        or not content_is_safe_public_url(source_url)
    ):
        _blocked("inventory_sitemap_fact_invalid", "complete", list(source_evidence_ids))
    canonical_path = content_normalized_path(source_url)
    normalized_url = content_normalized_url(source_url)
    if not canonical_path or not normalized_url:
        _blocked("inventory_sitemap_fact_invalid", "complete", list(source_evidence_ids))

    item = catalog_by_url.get(normalized_url)
    fact_evidence_ids = (fact.evidence_id,)
    canonical_url = str(dimensions.get("canonical_url") or "").strip()
    if canonical_url and (
        not content_is_safe_public_url(canonical_url)
        or content_normalized_url(canonical_url) != normalized_url
    ):
        return _blocked_scope_row(
            canonical_path=canonical_path,
            public_url=source_url,
            evidence_ids=fact_evidence_ids,
            code="inventory_canonical_url_mismatch",
            next_step="Zweryfikuj canonical strony w bieżącym odczycie WordPress.",
        )

    scope = dimensions.get("inventory_scope")
    editorial_eligible = dimensions.get("editorial_eligible")
    if scope == "editorial" and editorial_eligible == "true":
        if item is None:
            return _blocked_scope_row(
                canonical_path=canonical_path,
                public_url=source_url,
                evidence_ids=fact_evidence_ids,
                code="editorial_catalog_binding_missing",
                next_step="Uzupełnij dokładne powiązanie URL-a z bieżącym katalogiem WordPress.",
            )
        if item.path.rstrip("/") != canonical_path.rstrip("/"):
            return _blocked_scope_row(
                canonical_path=canonical_path,
                public_url=source_url,
                evidence_ids=fact_evidence_ids,
                catalog_evidence_ids=(item.evidence_id,),
                code="editorial_catalog_binding_missing",
                next_step="Uzupełnij dokładne powiązanie URL-a z bieżącym katalogiem WordPress.",
            )
        return CurrentInventoryScopeRow(
            canonical_path=canonical_path,
            public_url=item.url,
            disposition="eligible",
            current_work_item_id=item.work_item_id,
            source_evidence_ids=fact_evidence_ids,
            catalog_evidence_ids=(item.evidence_id,),
            safe_next_step="Sprawdź bieżące materiały i źródła tego dokładnego URL-a.",
        )

    if editorial_eligible == "false" and scope in {"commerce_catalog", "taxonomy"}:
        if item is not None:
            return _blocked_scope_row(
                canonical_path=canonical_path,
                public_url=source_url,
                evidence_ids=fact_evidence_ids,
                catalog_evidence_ids=(item.evidence_id,),
                code="inventory_scope_catalog_conflict",
                next_step="Zweryfikuj konflikt między kwalifikacją sitemap a katalogiem editorial.",
            )
        return CurrentInventoryScopeRow(
            canonical_path=canonical_path,
            public_url=source_url,
            disposition="excluded",
            source_evidence_ids=fact_evidence_ids,
            reason_code=(
                "commerce_catalog_excluded" if scope == "commerce_catalog" else "taxonomy_excluded"
            ),
            safe_next_step="Adres pozostaje poza kolejką treści editorial.",
        )

    return _blocked_scope_row(
        canonical_path=canonical_path,
        public_url=source_url,
        evidence_ids=fact_evidence_ids,
        code="inventory_scope_metadata_invalid",
        next_step="Zweryfikuj typ i kwalifikację URL-a w bieżącym źródle WordPress.",
    )


def _blocked_scope_row(
    *,
    canonical_path: str,
    public_url: str,
    evidence_ids: tuple[str, ...],
    code: str,
    next_step: str,
    catalog_evidence_ids: tuple[str, ...] = (),
) -> CurrentInventoryScopeRow:
    return CurrentInventoryScopeRow(
        canonical_path=canonical_path,
        public_url=public_url,
        disposition="blocked",
        source_evidence_ids=tuple(sorted(set(evidence_ids))),
        catalog_evidence_ids=tuple(sorted(set(catalog_evidence_ids))),
        blocker_code=code,
        blocker_owner="WILQ content workflow",
        safe_next_step=next_step,
    )


def _blocked(detail: str, coverage_status: str, evidence_ids: list[str]) -> NoReturn:
    raise CurrentInventoryReconciliationBlocked(detail, coverage_status, evidence_ids)


__all__ = [
    "CurrentInventoryReconciliationBlocked",
    "CurrentInventoryScopeCounts",
    "CurrentInventoryScopeResponse",
    "CurrentInventoryScopeRow",
    "build_current_inventory_scope",
]
