"""Immutable evidence-scoped receipt for one current authoring inventory item."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    build_content_inventory_catalog_cached,
)

_HEX64 = r"^[0-9a-f]{64}$"
_MATERIAL_STATUSES = {"content_summary", "content_and_structure", "structure_only"}


def _require_json_false(value: object) -> object:
    if type(value) is not bool or value:
        raise ValueError("Exact JSON false required.")
    return value


_ExactFalse = Annotated[Literal[False], BeforeValidator(_require_json_false)]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentAuthoringInventoryReceipt(_FrozenModel):
    """A material receipt, deliberately weaker than a delivery identity binding."""

    schema_version: Literal["wilq_content_authoring_inventory_receipt_v1"] = (
        "wilq_content_authoring_inventory_receipt_v1"
    )
    receipt_id: str = Field(min_length=1)
    receipt_digest: str = Field(pattern=_HEX64)
    status: Literal["registered_current_inventory"]
    catalog_id: str = Field(min_length=1)
    current_work_item_id: str = Field(min_length=1)
    public_url: str = Field(min_length=1)
    canonical_path: str = Field(min_length=1)
    source_connector: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    collected_at: datetime
    catalog_item_digest: str = Field(pattern=_HEX64)
    catalog_snapshot_digest: str = Field(pattern=_HEX64)
    catalog_snapshot_evidence_ids: tuple[str, ...] = Field(min_length=1)
    inventory_complete: _ExactFalse = False
    generation_allowed: _ExactFalse = False
    delivery_identity_available: _ExactFalse = False
    source_pack_available: _ExactFalse = False
    recorded_by: str = Field(min_length=1, max_length=160)
    recorded_at: datetime

    @field_validator("collected_at", "recorded_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Inventory receipt timestamp must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("catalog_snapshot_evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Snapshot evidence IDs must be sorted, unique and non-blank.")
        return value

    @model_validator(mode="after")
    def require_self_authenticating_receipt(self) -> Self:
        if not content_is_safe_public_url(self.public_url):
            raise ValueError("Inventory receipt requires a safe public URL.")
        if content_normalized_path(self.public_url) != self.canonical_path:
            raise ValueError("Inventory receipt URL/path mismatch.")
        if self.evidence_id not in self.catalog_snapshot_evidence_ids:
            raise ValueError("Inventory receipt evidence is outside its catalog snapshot.")
        payload = self.model_dump(mode="json")
        for field in ("receipt_id", "receipt_digest", "recorded_by", "recorded_at"):
            payload.pop(field)
        digest = canonical_json_digest(payload)
        if self.receipt_digest != digest or self.receipt_id != (
            f"content_authoring_inventory_{digest[:24]}"
        ):
            raise ValueError("Inventory receipt ID/digest does not match its payload.")
        return self


class ContentAuthoringInventoryReceiptRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    receipt: ContentAuthoringInventoryReceipt


def content_inventory_catalog_item_digest(item: ContentInventoryCatalogItem) -> str:
    """Digest every retained item field; URL identity alone is intentionally insufficient."""

    return canonical_json_digest(item.model_dump(mode="json"))


def content_inventory_catalog_snapshot_digest(catalog: object) -> str:
    """Digest source inventory scope, excluding derived journal projections.

    Journal reconciliation/readiness are derived from this catalog and external
    journal/store state, so including them would make the receipt snapshot
    digest recursive and would change it merely by attaching the projection.
    """

    model_dump = getattr(catalog, "model_dump", None)
    if not callable(model_dump):
        raise ValueError("Catalog snapshot requires a typed catalog model.")
    return canonical_json_digest(
        model_dump(
            mode="json",
            exclude={"journal_reconciliation", "journal_readiness"},
        )
    )


def build_current_content_authoring_inventory_receipt(
    *,
    canonical_path: str,
    recorded_by: str,
    recorded_at: datetime,
) -> ContentAuthoringInventoryReceipt:
    """Register one exact item from the authoritative current typed catalog."""

    normalized_path = content_normalized_path(canonical_path)
    supplied_canonical_path = canonical_path.rstrip("/") or "/"
    if (
        not canonical_path.startswith("/")
        or normalized_path != supplied_canonical_path
        or not normalized_path
    ):
        raise ValueError("Inventory receipt requires a canonical public path.")
    catalog = build_content_inventory_catalog_cached()
    matches = [
        item for item in catalog.items if content_normalized_path(item.path) == normalized_path
    ]
    if len(matches) != 1:
        raise ValueError("Inventory receipt requires one exact current catalog item.")
    return _build_content_authoring_inventory_receipt_from_catalog(
        item=matches[0],
        catalog=catalog,
        recorded_by=recorded_by,
        recorded_at=recorded_at,
    )


def _build_content_authoring_inventory_receipt_from_catalog(
    *,
    item: ContentInventoryCatalogItem,
    catalog: ContentInventoryCatalogResponse,
    recorded_by: str,
    recorded_at: datetime,
) -> ContentAuthoringInventoryReceipt:
    """Build a non-generative receipt from one material-bearing current catalog item."""

    matching_items = [
        candidate
        for candidate in catalog.items
        if candidate.catalog_id == item.catalog_id
        and content_inventory_catalog_item_digest(candidate)
        == content_inventory_catalog_item_digest(item)
    ]
    if len(matching_items) != 1:
        raise ValueError("Inventory item is not an exact member of the current catalog snapshot.")
    catalog_snapshot_evidence_ids = tuple(
        sorted({evidence_id.strip() for evidence_id in catalog.evidence_ids if evidence_id.strip()})
    )
    catalog_snapshot_digest = content_inventory_catalog_snapshot_digest(catalog)
    if item.material_status not in _MATERIAL_STATUSES:
        raise ValueError("Inventory item has no material sufficient for registration.")
    if not content_is_safe_public_url(item.url):
        raise ValueError("Inventory item has no safe public URL.")
    canonical_path = content_normalized_path(item.url)
    if canonical_path != content_normalized_path(item.path):
        raise ValueError("Inventory item URL/path mismatch.")
    if not item.evidence_id.strip() or item.evidence_id not in catalog_snapshot_evidence_ids:
        raise ValueError("Inventory item evidence is outside its current catalog snapshot.")
    values = {
        "schema_version": "wilq_content_authoring_inventory_receipt_v1",
        "status": "registered_current_inventory",
        "catalog_id": item.catalog_id,
        "current_work_item_id": item.work_item_id,
        "public_url": item.url,
        "canonical_path": canonical_path,
        "source_connector": item.source_connector,
        "evidence_id": item.evidence_id,
        "collected_at": item.model_dump(mode="json")["collected_at"],
        "catalog_item_digest": content_inventory_catalog_item_digest(item),
        "catalog_snapshot_digest": catalog_snapshot_digest,
        "catalog_snapshot_evidence_ids": list(catalog_snapshot_evidence_ids),
        "inventory_complete": False,
        "generation_allowed": False,
        "delivery_identity_available": False,
        "source_pack_available": False,
    }
    digest = canonical_json_digest(values)
    return ContentAuthoringInventoryReceipt(
        receipt_id=f"content_authoring_inventory_{digest[:24]}",
        receipt_digest=digest,
        recorded_by=recorded_by,
        recorded_at=recorded_at,
        **values,
    )


__all__ = [
    "ContentAuthoringInventoryReceipt",
    "ContentAuthoringInventoryReceiptRecordResult",
    "build_current_content_authoring_inventory_receipt",
    "content_inventory_catalog_item_digest",
    "content_inventory_catalog_snapshot_digest",
]
