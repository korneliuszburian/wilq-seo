"""Exact local authority for one initial full draft from an approved v3 plan."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.decisions.production import canonical_json_digest


class FullDraftGenerationV3Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_item_id: str = Field(min_length=1)
    subject_key: str = Field(min_length=1)
    content_kind: Literal["service", "editorial"]
    service_card_id: str | None
    page_url: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    proposal_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    packet_id: str = Field(min_length=1)
    packet_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    packet_receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_action_id: str = Field(min_length=1)
    identity_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_pack_id: str = Field(min_length=1)
    source_pack_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    base_revision_id: None = None
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @property
    def context_digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))

    @property
    def action_id(self) -> str:
        return f"act_content_full_draft_generation_v3_{self.context_digest}"


class FullDraftGenerationV3Receipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot: FullDraftGenerationV3Snapshot
    action_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    preview_audit_id: str = Field(min_length=1)
    review_audit_id: str = Field(min_length=1)
    confirmation_audit_id: str = Field(min_length=1)
    impact_audit_id: str = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    confirmed_by: str = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def aware_timestamp(self) -> Self:
        if self.created_at.tzinfo is None:
            raise ValueError("Full draft authorization requires an aware audit timestamp.")
        return self

    @property
    def receipt_digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


class FullDraftGenerationV3Binding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1)
    authorization_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_id: str = Field(min_length=1)

    @classmethod
    def from_receipt(cls, receipt: FullDraftGenerationV3Receipt) -> Self:
        return cls(
            action_id=receipt.snapshot.action_id,
            authorization_digest=receipt.receipt_digest,
            payload_digest=receipt.action_payload_digest,
            context_digest=receipt.snapshot.context_digest,
            run_id=f"codex_full_draft_v3_{receipt.receipt_digest}",
        )


class FullDraftGenerationV3WorkerStart(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    binding: FullDraftGenerationV3Binding
    started_at: datetime

    @property
    def action_id(self) -> str:
        return self.binding.action_id
