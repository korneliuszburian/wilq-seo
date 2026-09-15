"""Server-owned immutable receipt for one research-packet preparation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal, Self

from pydantic import Field, model_validator

from wilq.content.workflow.research_packet_contracts import (
    ContentResearchPacketCommand,
    ContentResearchPacketContextReceipt,
    _FrozenModel,
)
from wilq.security.redaction import redact_mapping

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"


class ContentResearchPacketPreparationReceipt(_FrozenModel):
    """Immutable server-owned authority for one packet command."""

    schema_version: Literal["wilq_content_research_packet_preparation_v1"] = (
        "wilq_content_research_packet_preparation_v1"
    )
    receipt_id: str = Field(min_length=1, max_length=280, pattern=_SAFE_IDENTIFIER)
    receipt_digest: str = Field(pattern=_HEX64)
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    source_pack_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_pack_binding_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    input_digest: str = Field(pattern=_HEX64)
    context_receipt: ContentResearchPacketContextReceipt
    recorded_at: datetime

    @model_validator(mode="after")
    def require_exact_receipt_identity(self) -> Self:
        context = self.context_receipt
        if (
            context.identity_binding_id != self.identity_binding_id
            or context.identity_binding_digest != self.identity_binding_digest
            or not context.classification_source_row_digest
        ):
            raise ValueError("Preparation receipt context does not match its identity.")
        expected_digest = research_packet_preparation_receipt_digest(self)
        expected_id = f"content_research_packet_preparation_{expected_digest[:24]}"
        if self.receipt_digest != expected_digest or self.receipt_id != expected_id:
            raise ValueError("Preparation receipt ID/digest does not match its payload.")
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("Preparation receipt recorded_at must be timezone-aware.")
        return self


class ContentResearchPacketPreparationReceiptRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    receipt: ContentResearchPacketPreparationReceipt


def build_research_packet_preparation_receipt(
    command: ContentResearchPacketCommand,
    *,
    recorded_at: datetime,
) -> ContentResearchPacketPreparationReceipt:
    input_digest = research_packet_input_digest_for_receipt(command)
    provisional = ContentResearchPacketPreparationReceipt.model_construct(
        receipt_id="",
        receipt_digest="",
        identity_binding_id=command.identity_binding_id,
        identity_binding_digest=command.identity_binding_digest,
        source_pack_binding_id=command.source_pack_binding_id,
        source_pack_binding_digest=command.source_pack_binding_digest,
        current_work_item_id=command.current_work_item_id,
        input_digest=input_digest,
        context_receipt=command.context_receipt,
        recorded_at=recorded_at.astimezone(UTC),
    )
    digest = research_packet_preparation_receipt_digest(provisional)
    return ContentResearchPacketPreparationReceipt.model_validate(
        provisional.model_copy(
            update={
                "receipt_id": f"content_research_packet_preparation_{digest[:24]}",
                "receipt_digest": digest,
            }
        )
    )


def research_packet_input_digest_for_receipt(command: ContentResearchPacketCommand) -> str:
    return command_input_digest(command)


def command_input_digest(command: ContentResearchPacketCommand) -> str:
    payload = redact_mapping(
        command.model_dump(
            mode="json",
            exclude={
                "preparation_receipt_id",
                "preparation_receipt_digest",
                "recorded_by",
                "recorded_at",
            },
        )
    )
    return _canonical_digest(payload)


def research_packet_preparation_receipt_digest(
    receipt: ContentResearchPacketPreparationReceipt,
) -> str:
    payload = receipt.model_dump(
        mode="json", exclude={"receipt_id", "receipt_digest", "recorded_at"}
    )
    return _canonical_digest(payload)


def preparation_receipt_matches_command(
    receipt: ContentResearchPacketPreparationReceipt | None,
    command: ContentResearchPacketCommand,
) -> bool:
    return receipt is not None and (
        receipt.receipt_id == command.preparation_receipt_id
        and receipt.receipt_digest == command.preparation_receipt_digest
        and receipt.identity_binding_id == command.identity_binding_id
        and receipt.identity_binding_digest == command.identity_binding_digest
        and receipt.source_pack_binding_id == command.source_pack_binding_id
        and receipt.source_pack_binding_digest == command.source_pack_binding_digest
        and receipt.current_work_item_id == command.current_work_item_id
        and receipt.input_digest == research_packet_input_digest_for_receipt(command)
        and receipt.context_receipt == command.context_receipt
    )


def _canonical_digest(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ContentResearchPacketPreparationReceipt",
    "ContentResearchPacketPreparationReceiptRecordResult",
    "build_research_packet_preparation_receipt",
    "command_input_digest",
    "preparation_receipt_matches_command",
    "research_packet_input_digest_for_receipt",
    "research_packet_preparation_receipt_digest",
]
