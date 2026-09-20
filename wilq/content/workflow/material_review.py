"""Exact, append-only review of one current WordPress material snapshot."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.workflow.authoring_inventory_receipt import (
    content_inventory_catalog_item_digest,
    content_inventory_catalog_snapshot_digest,
)
from wilq.content.workflow.decisions.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.evidence_acquisition_contracts import EvidenceObservationReceipt
from wilq.content.workflow.evidence_acquisition_snapshot import (
    MaterialReader,
    WordPressCurrentPageSnapshotAdapter,
    current_page_receipt_is_fresh,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
)
from wilq.schemas import ContentDecisionItem
from wilq.schemas.core import utc_now

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"

ContentMaterialReviewDecision = Literal["approved", "rejected"]
ContentMaterialReviewStatus = Literal[
    "missing",
    "review_required",
    "approved_current",
    "stale",
    "rejected",
]


def _sorted_unique(values: Sequence[str], *, label: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if (
        any(not value for value in normalized)
        or len(normalized) != len(set(normalized))
        or normalized != tuple(sorted(normalized))
    ):
        raise ValueError(f"{label} must be sorted, unique and non-blank.")
    return normalized


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentMaterialReviewPreview(_FrozenModel):
    """Immutable, raw-free preview of the material that may be reviewed."""

    schema_version: Literal["wilq_content_material_review_preview_v1"] = (
        "wilq_content_material_review_preview_v1"
    )
    preview_id: str = Field(min_length=1, max_length=280, pattern=_SAFE_IDENTIFIER)
    preview_digest: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1, max_length=240)
    catalog_id: str = Field(min_length=1, max_length=240)
    public_url: str = Field(min_length=1, max_length=2048)
    canonical_path: str = Field(min_length=1, max_length=2048)
    catalog_item_digest: str = Field(pattern=_HEX64)
    catalog_snapshot_digest: str = Field(pattern=_HEX64)
    catalog_item_evidence_id: str = Field(min_length=1, max_length=240)
    catalog_snapshot_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    observation: EvidenceObservationReceipt
    source_field_lineage_digest: str = Field(pattern=_HEX64)
    prepared_at: datetime

    @field_validator("catalog_snapshot_evidence_ids", "evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique(value, label="Material review evidence IDs")

    @field_validator("prepared_at")
    @classmethod
    def require_aware_prepared_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Material review preview time must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_self_authenticating_preview(self) -> ContentMaterialReviewPreview:
        if not content_is_safe_public_url(self.public_url):
            raise ValueError("Material review preview requires a safe public URL.")
        if content_normalized_path(self.public_url) != self.canonical_path:
            raise ValueError("Material review preview URL/path mismatch.")
        if self.catalog_item_evidence_id not in self.catalog_snapshot_evidence_ids:
            raise ValueError("Catalog item evidence is outside its catalog snapshot.")
        expected_evidence = tuple(
            sorted(set((*self.catalog_snapshot_evidence_ids, *self.observation.evidence_ids)))
        )
        if self.evidence_ids != expected_evidence:
            raise ValueError("Material review evidence does not match its sources.")
        if (
            self.observation.source_url != self.public_url
            or self.observation.canonical_path != self.canonical_path
        ):
            raise ValueError("Material review observation is not bound to the selected URL/path.")
        expected_digest = material_review_preview_digest(self)
        if self.preview_digest != expected_digest or self.preview_id != (
            f"content_material_review_preview_{expected_digest[:24]}"
        ):
            raise ValueError("Material review preview ID/digest does not match its payload.")
        return self


class ContentMaterialReviewCommand(_FrozenModel):
    """The exact human decision submitted for one immutable preview."""

    preview_id: str = Field(min_length=1, max_length=280, pattern=_SAFE_IDENTIFIER)
    preview_digest: str = Field(pattern=_HEX64)
    decision: ContentMaterialReviewDecision
    reviewer: str = Field(min_length=1, max_length=200)
    reviewed_full_material: Literal[True] = True

    @field_validator("reviewer")
    @classmethod
    def require_reviewer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Material review reviewer cannot be blank.")
        return value


class ContentMaterialReviewReceipt(_FrozenModel):
    """Immutable decision receipt; it intentionally carries no raw body."""

    schema_version: Literal["wilq_content_material_review_receipt_v1"] = (
        "wilq_content_material_review_receipt_v1"
    )
    review_id: str = Field(min_length=1, max_length=280, pattern=_SAFE_IDENTIFIER)
    review_digest: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1, max_length=240)
    preview_id: str = Field(min_length=1, max_length=280, pattern=_SAFE_IDENTIFIER)
    preview_digest: str = Field(pattern=_HEX64)
    decision: ContentMaterialReviewDecision
    reviewer: str = Field(min_length=1, max_length=200)
    reviewed_full_material: Literal[True] = True
    reviewed_at: datetime

    @field_validator("reviewer")
    @classmethod
    def require_receipt_reviewer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Material review reviewer cannot be blank.")
        return value

    @field_validator("reviewed_at")
    @classmethod
    def require_aware_reviewed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Material review time must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_self_authenticating_receipt(self) -> ContentMaterialReviewReceipt:
        expected_digest = material_review_receipt_digest(self)
        if self.review_digest != expected_digest or self.review_id != (
            f"content_material_review_{expected_digest[:24]}"
        ):
            raise ValueError("Material review receipt ID/digest does not match its payload.")
        return self


class ContentMaterialReviewPreviewRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    preview: ContentMaterialReviewPreview


class ContentMaterialReviewRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    review: ContentMaterialReviewReceipt


class ContentMaterialReviewReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_material_review_read"] = "content_material_review_read"
    status: ContentMaterialReviewStatus
    work_item_id: str
    preview: ContentMaterialReviewPreview | None = None
    review: ContentMaterialReviewReceipt | None = None
    current_observation: EvidenceObservationReceipt | None = None
    blockers: list[str] = Field(default_factory=list, max_length=8)
    safe_next_step: str = Field(min_length=1, max_length=600)


class ContentMaterialReviewPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_material_review_preview"] = (
        "content_material_review_preview"
    )
    status: Literal["preview_ready"] = "preview_ready"
    preview: ContentMaterialReviewPreview


class ContentMaterialReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_material_review"] = "content_material_review"
    status: Literal["created", "idempotent", "conflict"]
    review: ContentMaterialReviewReceipt
    current: ContentMaterialReviewReadResponse


class MaterialReviewStore(Protocol):
    def record_content_material_review_preview(
        self, preview: ContentMaterialReviewPreview
    ) -> ContentMaterialReviewPreviewRecordResult: ...

    def load_content_material_review_preview(
        self, preview_id: str
    ) -> ContentMaterialReviewPreview | None: ...

    def record_content_material_review(
        self, receipt: ContentMaterialReviewReceipt
    ) -> ContentMaterialReviewRecordResult: ...

    def load_content_material_review(
        self, review_id: str
    ) -> ContentMaterialReviewReceipt | None: ...

    def latest_content_material_review(
        self, work_item_id: str
    ) -> ContentMaterialReviewReceipt | None: ...


CatalogLoader = Callable[[], ContentInventoryCatalogResponse]
SelectedItemLoader = Callable[[str], ContentDecisionItem | None]
MaterialReaderFactory = Callable[[], MaterialReader]
Clock = Callable[[], datetime]


class MaterialReviewNotFoundError(LookupError):
    pass


class MaterialReviewConflictError(ValueError):
    pass


def material_review_source_field_lineage_digest(lineage: Sequence[str]) -> str:
    return _digest_payload(tuple(_canonical_material_source(value) for value in lineage))


def _canonical_material_source(value: str) -> str:
    return {
        "public_html.article_content": "wordpress.article_content",
        "wordpress_rest.content": "wordpress.article_content",
    }.get(value, value)


def material_review_preview_digest(preview: ContentMaterialReviewPreview) -> str:
    return _digest_payload(
        preview.model_dump(mode="json", exclude={"preview_id", "preview_digest"})
    )


def material_review_receipt_digest(receipt: ContentMaterialReviewReceipt) -> str:
    return _digest_payload(
        receipt.model_dump(
            mode="json",
            exclude={"review_id", "review_digest", "reviewed_at"},
        )
    )


def _digest_payload(payload: object) -> str:
    from wilq.content.workflow.decisions.production import canonical_json_digest

    return canonical_json_digest(payload)


def build_content_material_review_preview(
    *,
    work_item_id: str,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    selected_item_loader: SelectedItemLoader | None = None,
    adapter: WordPressCurrentPageSnapshotAdapter | None = None,
    material_reader_factory: MaterialReaderFactory | None = None,
    clock: Clock = utc_now,
) -> ContentMaterialReviewPreview:
    catalog = catalog_loader()
    item = (selected_item_loader or _canonical_selected_item)(work_item_id)
    if item is None:
        raise MaterialReviewNotFoundError("content_material_review_work_item_not_found")
    catalog_item = _catalog_item_for_selected(catalog, item)
    public_url, canonical_path = _selected_identity(item)
    current_adapter = adapter or _adapter(
        material_reader_factory=material_reader_factory,
        clock=clock,
    )
    observation = current_adapter.read(source_url=public_url, canonical_path=canonical_path)
    now = _aware_now(clock)
    if not current_page_receipt_is_fresh(observation, now=now):
        raise MaterialReviewConflictError("content_material_review_observation_stale")
    lineage = (observation.extraction_region,)
    snapshot_evidence_ids = _sorted_unique(
        tuple(catalog.evidence_ids) or (catalog_item.evidence_id,),
        label="Catalog snapshot evidence IDs",
    )
    catalog_item_digest = content_inventory_catalog_item_digest(catalog_item)
    catalog_snapshot_digest = content_inventory_catalog_snapshot_digest(catalog)
    evidence_ids = tuple(sorted(set((*snapshot_evidence_ids, *observation.evidence_ids))))
    source_field_lineage_digest = material_review_source_field_lineage_digest(lineage)
    digest = material_review_preview_digest(
        ContentMaterialReviewPreview.model_construct(
            schema_version="wilq_content_material_review_preview_v1",
            preview_id="material_review_preview_digest_input",
            preview_digest="0" * 64,
            work_item_id=work_item_id,
            catalog_id=catalog_item.catalog_id,
            public_url=public_url,
            canonical_path=canonical_path,
            catalog_item_digest=catalog_item_digest,
            catalog_snapshot_digest=catalog_snapshot_digest,
            catalog_item_evidence_id=catalog_item.evidence_id,
            catalog_snapshot_evidence_ids=snapshot_evidence_ids,
            evidence_ids=evidence_ids,
            observation=observation,
            source_field_lineage_digest=source_field_lineage_digest,
            prepared_at=now,
        )
    )
    return ContentMaterialReviewPreview(
        preview_id=f"content_material_review_preview_{digest[:24]}",
        preview_digest=digest,
        schema_version="wilq_content_material_review_preview_v1",
        work_item_id=work_item_id,
        catalog_id=catalog_item.catalog_id,
        public_url=public_url,
        canonical_path=canonical_path,
        catalog_item_digest=catalog_item_digest,
        catalog_snapshot_digest=catalog_snapshot_digest,
        catalog_item_evidence_id=catalog_item.evidence_id,
        catalog_snapshot_evidence_ids=snapshot_evidence_ids,
        evidence_ids=evidence_ids,
        observation=observation,
        source_field_lineage_digest=source_field_lineage_digest,
        prepared_at=now,
    )


def build_content_material_review_receipt(
    *,
    work_item_id: str,
    command: ContentMaterialReviewCommand,
    reviewed_at: datetime,
) -> ContentMaterialReviewReceipt:
    digest = material_review_receipt_digest(
        ContentMaterialReviewReceipt.model_construct(
            schema_version="wilq_content_material_review_receipt_v1",
            review_id="material_review_digest_input",
            review_digest="0" * 64,
            work_item_id=work_item_id,
            preview_id=command.preview_id,
            preview_digest=command.preview_digest,
            decision=command.decision,
            reviewer=command.reviewer,
            reviewed_full_material=command.reviewed_full_material,
            reviewed_at=reviewed_at,
        )
    )
    return ContentMaterialReviewReceipt(
        review_id=f"content_material_review_{digest[:24]}",
        review_digest=digest,
        schema_version="wilq_content_material_review_receipt_v1",
        work_item_id=work_item_id,
        preview_id=command.preview_id,
        preview_digest=command.preview_digest,
        decision=command.decision,
        reviewer=command.reviewer,
        reviewed_full_material=command.reviewed_full_material,
        reviewed_at=reviewed_at,
    )


def read_content_material_review(
    *,
    work_item_id: str,
    store: MaterialReviewStore,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    selected_item_loader: SelectedItemLoader | None = None,
    adapter: WordPressCurrentPageSnapshotAdapter | None = None,
    material_reader_factory: MaterialReaderFactory | None = None,
    clock: Clock = utc_now,
) -> ContentMaterialReviewReadResponse:
    review = store.latest_content_material_review(work_item_id)
    if review is None:
        return ContentMaterialReviewReadResponse(
            status="missing",
            work_item_id=work_item_id,
            safe_next_step="Utwórz preview aktualnego materiału WordPress przed review.",
        )
    preview = store.load_content_material_review_preview(review.preview_id)
    if preview is None or preview.preview_digest != review.preview_digest:
        return _read_response(
            work_item_id=work_item_id,
            status="stale",
            preview=preview,
            review=review,
            blockers=["content_material_review_preview_missing_or_changed"],
            safe_next_step="Utwórz nowe preview materiału WordPress.",
        )
    if review.decision == "rejected":
        return _read_response(
            work_item_id=work_item_id,
            status="rejected",
            preview=preview,
            review=review,
            blockers=["content_material_review_rejected"],
            safe_next_step="Utwórz nowe preview i przeprowadź ponowne review materiału.",
        )
    try:
        current_observation = revalidate_content_material_review_preview(
            work_item_id=work_item_id,
            preview=preview,
            catalog_loader=catalog_loader,
            selected_item_loader=selected_item_loader,
            adapter=adapter,
            material_reader_factory=material_reader_factory,
            clock=clock,
        )
    except (MaterialReviewConflictError, ValueError, RuntimeError) as exc:
        blockers = [str(exc)]
        current_observation = None
    else:
        blockers = []
    if blockers:
        return _read_response(
            work_item_id=work_item_id,
            status="stale",
            preview=preview,
            review=review,
            blockers=blockers,
            safe_next_step="Utwórz nowe preview po potwierdzeniu aktualnego materiału WordPress.",
        )
    return _read_response(
        work_item_id=work_item_id,
        status="approved_current",
        preview=preview,
        review=review,
        current_observation=current_observation,
        safe_next_step="Materiał jest zatwierdzony i aktualny dla bieżącego katalogu.",
    )


def revalidate_content_material_review_preview(
    *,
    work_item_id: str,
    preview: ContentMaterialReviewPreview,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    selected_item_loader: SelectedItemLoader | None = None,
    adapter: WordPressCurrentPageSnapshotAdapter | None = None,
    material_reader_factory: MaterialReaderFactory | None = None,
    clock: Clock = utc_now,
) -> EvidenceObservationReceipt:
    """Rebuild current evidence before accepting a human material decision."""

    catalog = catalog_loader()
    item = (selected_item_loader or _canonical_selected_item)(work_item_id)
    if item is None:
        raise MaterialReviewConflictError("content_material_review_work_item_missing")
    catalog_item = _catalog_item_for_selected(catalog, item)
    public_url, canonical_path = _selected_identity(item)
    current_adapter = adapter or _adapter(
        material_reader_factory=material_reader_factory,
        clock=clock,
    )
    current_observation = current_adapter.read(
        source_url=public_url,
        canonical_path=canonical_path,
    )
    now = _aware_now(clock)
    if not current_page_receipt_is_fresh(preview.observation, now=now):
        raise MaterialReviewConflictError("content_material_review_observation_stale")
    if not current_page_receipt_is_fresh(current_observation, now=now):
        raise MaterialReviewConflictError("content_material_review_current_observation_stale")
    lineage = (current_observation.extraction_region,)
    blockers = _current_mismatch_blockers(
        preview,
        catalog=catalog,
        catalog_item=catalog_item,
        current_observation=current_observation,
        current_lineage_digest=material_review_source_field_lineage_digest(lineage),
    )
    if blockers:
        raise MaterialReviewConflictError(blockers[0])
    return current_observation


def _current_mismatch_blockers(
    preview: ContentMaterialReviewPreview,
    *,
    catalog: ContentInventoryCatalogResponse,
    catalog_item: ContentInventoryCatalogItem,
    current_observation: EvidenceObservationReceipt,
    current_lineage_digest: str,
) -> list[str]:
    blockers: list[str] = []
    if content_inventory_catalog_item_digest(catalog_item) != preview.catalog_item_digest:
        blockers.append("content_material_review_catalog_item_changed")
    if content_inventory_catalog_snapshot_digest(catalog) != preview.catalog_snapshot_digest:
        blockers.append("content_material_review_catalog_snapshot_changed")
    snapshot_evidence_ids = _catalog_snapshot_evidence_ids(catalog, catalog_item)
    if snapshot_evidence_ids != preview.catalog_snapshot_evidence_ids:
        blockers.append("content_material_review_catalog_evidence_changed")
    if catalog_item.evidence_id != preview.catalog_item_evidence_id:
        blockers.append("content_material_review_catalog_item_evidence_changed")
    original = preview.observation
    if current_observation.body_digest != original.body_digest:
        blockers.append("content_material_review_body_changed")
    if (
        current_observation.excerpt_digest != original.excerpt_digest
        or current_observation.sanitized_excerpt != original.sanitized_excerpt
    ):
        blockers.append("content_material_review_excerpt_changed")
    if (
        current_observation.source_url != original.source_url
        or current_observation.canonical_path != original.canonical_path
    ):
        blockers.append("content_material_review_url_or_path_changed")
    if _canonical_material_source(
        current_observation.extraction_region
    ) != _canonical_material_source(original.extraction_region):
        blockers.append("content_material_review_extraction_changed")
    if current_observation.source_connectors != original.source_connectors:
        blockers.append("content_material_review_source_connector_changed")
    if current_lineage_digest != preview.source_field_lineage_digest:
        blockers.append("content_material_review_lineage_changed")
    return blockers


def _catalog_snapshot_evidence_ids(
    catalog: ContentInventoryCatalogResponse,
    catalog_item: ContentInventoryCatalogItem,
) -> tuple[str, ...]:
    return _sorted_unique(
        tuple(catalog.evidence_ids) or (catalog_item.evidence_id,),
        label="Catalog snapshot evidence IDs",
    )


def _read_response(
    *,
    work_item_id: str,
    status: ContentMaterialReviewStatus,
    preview: ContentMaterialReviewPreview | None,
    review: ContentMaterialReviewReceipt,
    safe_next_step: str,
    blockers: list[str] | None = None,
    current_observation: EvidenceObservationReceipt | None = None,
) -> ContentMaterialReviewReadResponse:
    return ContentMaterialReviewReadResponse(
        status=status,
        work_item_id=work_item_id,
        preview=preview,
        review=review,
        current_observation=current_observation,
        blockers=blockers or [],
        safe_next_step=safe_next_step,
    )


def _canonical_selected_item(work_item_id: str) -> ContentDecisionItem | None:
    return inventory_decision_for_work_item(
        work_item_id,
        read_material=True,
        include_all_metric_facts=True,
    )


def _catalog_item_for_selected(
    catalog: ContentInventoryCatalogResponse,
    item: ContentDecisionItem,
) -> ContentInventoryCatalogItem:
    public_url, canonical_path = _selected_identity(item)
    matches = [
        candidate
        for candidate in catalog.items
        if candidate.url.rstrip("/") == public_url.rstrip("/")
        and content_normalized_path(candidate.path) == canonical_path
    ]
    if len(matches) != 1:
        raise MaterialReviewConflictError("content_material_review_catalog_item_not_exact")
    return matches[0]


def _selected_identity(item: ContentDecisionItem) -> tuple[str, str]:
    public_url = str(
        getattr(item, "final_canonical_url", None)
        or getattr(item, "source_public_url", None)
        or getattr(item, "page", "")
    ).strip()
    supplied_path = str(
        getattr(item, "normalized_page_path", None) or content_normalized_path(public_url)
    ).strip()
    canonical_path = content_normalized_path(supplied_path)
    if (
        not content_is_safe_public_url(public_url)
        or content_normalized_path(public_url) != canonical_path
    ):
        raise MaterialReviewConflictError("content_material_review_selected_identity_invalid")
    return public_url, canonical_path


def _adapter(
    *,
    material_reader_factory: MaterialReaderFactory | None,
    clock: Clock,
) -> WordPressCurrentPageSnapshotAdapter:
    if material_reader_factory is None:
        return WordPressCurrentPageSnapshotAdapter(clock=clock)
    return WordPressCurrentPageSnapshotAdapter(
        material_reader=material_reader_factory(),
        clock=clock,
    )


def _aware_now(clock: Clock) -> datetime:
    now = clock()
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Material review clock must be timezone-aware.")
    return now.astimezone(UTC)


__all__ = [
    "ContentMaterialReviewCommand",
    "ContentMaterialReviewDecision",
    "ContentMaterialReviewPreview",
    "ContentMaterialReviewPreviewRecordResult",
    "ContentMaterialReviewPreviewResponse",
    "ContentMaterialReviewReadResponse",
    "ContentMaterialReviewReceipt",
    "ContentMaterialReviewRecordResult",
    "ContentMaterialReviewResponse",
    "ContentMaterialReviewStatus",
    "MaterialReviewConflictError",
    "MaterialReviewNotFoundError",
    "MaterialReviewStore",
    "build_content_material_review_preview",
    "build_content_material_review_receipt",
    "material_review_preview_digest",
    "material_review_receipt_digest",
    "material_review_source_field_lineage_digest",
    "revalidate_content_material_review_preview",
    "read_content_material_review",
]
