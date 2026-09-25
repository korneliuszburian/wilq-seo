"""Immutable local records for exact v3 research packet review."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_preview import ResearchPacketV3Preview

_HEX64 = r"^[0-9a-f]{64}$"


class ResearchPacketV3PreviewRecord(BaseModel):
    """A ready preview captured as its complete, validated immutable snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["wilq_research_packet_v3_preview_record_v1"] = (
        "wilq_research_packet_v3_preview_record_v1"
    )
    preview_hash: str = Field(pattern=_HEX64)
    work_item_id: str = Field(min_length=1, max_length=240)
    snapshot: ResearchPacketV3Preview

    @model_validator(mode="after")
    def validate_exact_preview(self) -> Self:
        if (
            self.snapshot.status != "ready"
            or self.snapshot.preview_hash != self.preview_hash
            or self.snapshot.work_item_id != self.work_item_id
        ):
            raise ValueError("Research packet v3 preview record identity does not match.")
        return self

    @classmethod
    def from_preview(cls, preview: ResearchPacketV3Preview) -> Self:
        accepted = ResearchPacketV3Preview.model_validate_json(
            preview.model_dump_json(), strict=True
        )
        if accepted.status != "ready" or accepted.preview_hash is None:
            raise ValueError("Only a ready research packet v3 preview can be recorded.")
        if not accepted.has_exact_page_identity():
            raise ValueError("research_packet_v3_page_identity_missing")
        if not accepted.has_current_per_url_identity():
            raise ValueError("per_url_delivery_identity_required")
        return cls(
            preview_hash=accepted.preview_hash,
            work_item_id=accepted.work_item_id,
            snapshot=accepted,
        )

    def has_exact_page_identity(self) -> bool:
        return self.snapshot.has_exact_page_identity()


class ResearchPacketV3ApprovalReceipt(BaseModel):
    """Self-authenticating server receipt bound to an exact reviewed ActionObject."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["wilq_research_packet_v3_approval_receipt_v1"] = (
        "wilq_research_packet_v3_approval_receipt_v1"
    )
    packet_id: str = Field(min_length=1, max_length=240)
    packet_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    preview_audit_event_id: str = Field(min_length=1, max_length=240)
    review_audit_event_id: str = Field(min_length=1, max_length=240)
    confirmation_audit_event_id: str = Field(min_length=1, max_length=240)
    impact_audit_event_id: str = Field(min_length=1, max_length=240)
    review_actor: str = Field(min_length=1, max_length=240)
    verification_evidence_ids: tuple[str, ...] = Field(min_length=1)
    verification_evidence_digest: str = Field(pattern=_HEX64)
    approved_at: datetime
    receipt_digest: str = Field(pattern=_HEX64)

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        if self.packet_id != f"content_research_packet_v3_{self.packet_digest[:24]}":
            raise ValueError("Research packet v3 approval packet identity does not match.")
        if self.action_id != f"act_content_research_packet_v3_{self.packet_digest}":
            raise ValueError("Research packet v3 approval action identity does not match.")
        if self.approved_at.tzinfo is None or self.approved_at.utcoffset() is None:
            raise ValueError("Research packet v3 approval timestamp must be timezone-aware.")
        if self.receipt_digest != research_packet_v3_receipt_digest(self):
            raise ValueError("Research packet v3 approval receipt digest does not match.")
        return self

    @classmethod
    def from_action_chain(
        cls,
        *,
        preview_hash: str,
        action_id: str,
        action_payload_digest: str,
        preview_audit_event_id: str,
        review_audit_event_id: str,
        confirmation_audit_event_id: str,
        impact_audit_event_id: str,
        review_actor: str,
        verification_evidence_ids: tuple[str, ...],
        verification_evidence_digest: str,
        approved_at: datetime,
    ) -> Self:
        payload: dict[str, Any] = {
            "packet_id": f"content_research_packet_v3_{preview_hash[:24]}",
            "packet_digest": preview_hash,
            "action_id": action_id,
            "action_payload_digest": action_payload_digest,
            "preview_audit_event_id": preview_audit_event_id,
            "review_audit_event_id": review_audit_event_id,
            "confirmation_audit_event_id": confirmation_audit_event_id,
            "impact_audit_event_id": impact_audit_event_id,
            "review_actor": review_actor,
            "verification_evidence_ids": verification_evidence_ids,
            "verification_evidence_digest": verification_evidence_digest,
            "approved_at": approved_at,
        }
        provisional = cls.model_construct(**payload, receipt_digest="0" * 64)
        return cls.model_validate(
            provisional.model_dump(mode="python")
            | {"receipt_digest": research_packet_v3_receipt_digest(provisional)}
        )


def research_packet_v3_receipt_digest(
    value: ResearchPacketV3ApprovalReceipt | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("receipt_digest", None)
    return canonical_json_digest(payload)


__all__ = [
    "ResearchPacketV3ApprovalReceipt",
    "ResearchPacketV3PreviewRecord",
    "research_packet_v3_receipt_digest",
]
