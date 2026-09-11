"""Durable, redacted editorial-kind receipts for classified refresh authority."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding

_HEX64 = r"^[0-9a-f]{64}$"


class ContentKindReceipt(BaseModel):
    """One exact editorial classification backed by current WordPress evidence only.

    This retains IDs, digests, URL identity, and typed inventory metadata.  It
    deliberately does not retain a WordPress packet, page body, or other raw
    external source data.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["wilq_content_kind_receipt_v1"] = (
        "wilq_content_kind_receipt_v1"
    )
    receipt_id: str = Field(min_length=1)
    receipt_digest: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1)
    classification_run_id: str = Field(min_length=1)
    classification_run_digest: str = Field(pattern=_HEX64)
    decision_set_digest: str = Field(pattern=_HEX64)
    source_packet_row_digest: str = Field(pattern=_HEX64)
    canonical_path: str = Field(min_length=1)
    public_url: str = Field(min_length=1)
    planning_input_digest: str = Field(pattern=_HEX64)
    content_kind: str = Field(pattern=r"^editorial$")
    wordpress_content_type: str = Field(min_length=1)
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1)
    inventory_evidence_digest: str = Field(pattern=_HEX64)

    @field_validator("inventory_evidence_ids")
    @classmethod
    def require_exact_inventory_evidence_set(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if (
            any(not item for item in normalized)
            or len(normalized) != len(set(normalized))
            or normalized != tuple(sorted(normalized))
        ):
            raise ValueError("Inventory evidence IDs must be a sorted unique non-blank set.")
        return normalized

    @model_validator(mode="after")
    def require_exact_receipt_identity(self) -> ContentKindReceipt:
        if content_normalized_path(self.public_url) != self.canonical_path:
            raise ValueError("Content-kind receipt canonical path does not match public URL.")
        if self.inventory_evidence_digest != _inventory_evidence_digest(
            self.inventory_evidence_ids
        ):
            raise ValueError("Content-kind receipt inventory evidence digest does not match IDs.")
        digest = content_kind_receipt_digest(
            work_item_id=self.work_item_id,
            classification_run_id=self.classification_run_id,
            classification_run_digest=self.classification_run_digest,
            decision_set_digest=self.decision_set_digest,
            source_packet_row_digest=self.source_packet_row_digest,
            canonical_path=self.canonical_path,
            public_url=self.public_url,
            planning_input_digest=self.planning_input_digest,
            wordpress_content_type=self.wordpress_content_type,
            inventory_evidence_ids=self.inventory_evidence_ids,
        )
        if self.receipt_digest != digest:
            raise ValueError("Content-kind receipt digest does not match its identity.")
        if self.receipt_id != f"content_kind_receipt_{digest[:24]}":
            raise ValueError("Content-kind receipt ID does not match its digest.")
        return self


class ContentKindReceiptRecordResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str = Field(pattern=r"^(created|idempotent|conflict)$")
    receipt: ContentKindReceipt


def build_editorial_content_kind_receipt(
    *,
    work_item_id: str,
    classification_run_id: str,
    classification_run_digest: str,
    decision_set_digest: str,
    source_packet_row_digest: str,
    canonical_path: str,
    public_url: str,
    planning_input_digest: str,
    inventory_binding: ContentKindInventoryBinding,
) -> ContentKindReceipt:
    """Build a receipt only when the exact inventory binding is current and editorial."""

    if (
        inventory_binding.content_kind != "editorial"
        or not inventory_binding.trusted
        or inventory_binding.work_item_id != work_item_id
        or inventory_binding.canonical_path != canonical_path
        or inventory_binding.public_url != public_url
    ):
        raise ValueError(
            "Editorial content-kind receipt requires one current trusted inventory binding."
        )
    evidence_ids = tuple(sorted(inventory_binding.inventory_evidence_ids))
    digest = content_kind_receipt_digest(
        work_item_id=work_item_id,
        classification_run_id=classification_run_id,
        classification_run_digest=classification_run_digest,
        decision_set_digest=decision_set_digest,
        source_packet_row_digest=source_packet_row_digest,
        canonical_path=canonical_path,
        public_url=public_url,
        planning_input_digest=planning_input_digest,
        wordpress_content_type=inventory_binding.wordpress_content_type,
        inventory_evidence_ids=evidence_ids,
    )
    return ContentKindReceipt(
        receipt_id=f"content_kind_receipt_{digest[:24]}",
        receipt_digest=digest,
        work_item_id=work_item_id,
        classification_run_id=classification_run_id,
        classification_run_digest=classification_run_digest,
        decision_set_digest=decision_set_digest,
        source_packet_row_digest=source_packet_row_digest,
        canonical_path=canonical_path,
        public_url=public_url,
        planning_input_digest=planning_input_digest,
        content_kind="editorial",
        wordpress_content_type=inventory_binding.wordpress_content_type,
        inventory_evidence_ids=evidence_ids,
        inventory_evidence_digest=_inventory_evidence_digest(evidence_ids),
    )


def content_kind_receipt_digest(
    *,
    work_item_id: str,
    classification_run_id: str,
    classification_run_digest: str,
    decision_set_digest: str,
    source_packet_row_digest: str,
    canonical_path: str,
    public_url: str,
    planning_input_digest: str,
    wordpress_content_type: str,
    inventory_evidence_ids: tuple[str, ...],
) -> str:
    payload = {
        "work_item_id": work_item_id,
        "classification_run_id": classification_run_id,
        "classification_run_digest": classification_run_digest,
        "decision_set_digest": decision_set_digest,
        "source_packet_row_digest": source_packet_row_digest,
        "canonical_path": canonical_path,
        "public_url": public_url,
        "planning_input_digest": planning_input_digest,
        "content_kind": "editorial",
        "wordpress_content_type": wordpress_content_type,
        "inventory_evidence_ids": list(inventory_evidence_ids),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def content_kind_receipt_matches_context(
    receipt: ContentKindReceipt,
    *,
    work_item_id: str,
    classification_run_id: str,
    classification_run_digest: str,
    decision_set_digest: str,
    source_packet_row_digest: str,
    canonical_path: str,
    public_url: str,
    planning_input_digest: str,
    inventory_binding: ContentKindInventoryBinding,
) -> bool:
    try:
        expected = build_editorial_content_kind_receipt(
            work_item_id=work_item_id,
            classification_run_id=classification_run_id,
            classification_run_digest=classification_run_digest,
            decision_set_digest=decision_set_digest,
            source_packet_row_digest=source_packet_row_digest,
            canonical_path=canonical_path,
            public_url=public_url,
            planning_input_digest=planning_input_digest,
            inventory_binding=inventory_binding,
        )
    except ValueError:
        return False
    return receipt == expected


def _inventory_evidence_digest(evidence_ids: tuple[str, ...]) -> str:
    return sha256(
        json.dumps(list(evidence_ids), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ContentKindReceipt",
    "ContentKindReceiptRecordResult",
    "build_editorial_content_kind_receipt",
    "content_kind_receipt_matches_context",
]
