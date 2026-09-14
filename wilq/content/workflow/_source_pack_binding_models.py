"""Private typed contracts for the source-pack seam."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.workflow._source_pack_binding_constants import (
    _HEX64,
    _SAFE_IDENTIFIER,
    _SECRET_LIKE_IDENTIFIER,
    ContentSourcePackBindingReason,
    ContentSourcePackBindingSeam,
)
from wilq.content.workflow._source_pack_binding_hashing import (
    content_source_pack_binding_digest,
    content_source_pack_binding_logical_id,
    evidence_ids_digest,
    source_fact_ids_digest,
    source_fact_provenance_digest,
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _require_nonzero_digest(value: str) -> str:
    if value == "0" * 64:
        raise ValueError("A zero digest is not an exact receipt.")
    return value


def _require_safe_identifier(value: str, label: str) -> str:
    if _SECRET_LIKE_IDENTIFIER.search(value):
        raise ValueError(f"{label} must not resemble a credential identifier.")
    return value


def _sorted_unique_ids(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(item.strip() for item in value)
    if (
        not normalized
        or any(not item for item in normalized)
        or any(
            not re.fullmatch(_SAFE_IDENTIFIER, item)
            or _SECRET_LIKE_IDENTIFIER.search(item) is not None
            for item in normalized
        )
        or len(normalized) != len(set(normalized))
        or normalized != tuple(sorted(normalized))
    ):
        raise ValueError(f"{label} must be sorted, unique and non-blank.")
    return normalized
class ContentSourcePackContextAttestation(_FrozenModel):
    """The exact persisted run receipt used as fresh source-pack context."""

    run_id: str = Field(
        min_length=1,
        max_length=240,
        pattern=_SAFE_IDENTIFIER,
        validation_alias=AliasChoices("run_id", "registry_id", "registry_or_run_id"),
    )
    context_digest: str = Field(pattern=_HEX64)
    checked_at: datetime
    source: Literal["content_delivery_identity_binding"]
    evidence_ids: tuple[str, ...] = Field(min_length=0, max_length=256)

    @field_validator("context_digest")
    @classmethod
    def require_nonzero_context_digest(cls, value: str) -> str:
        return _require_nonzero_digest(value)

    @field_validator("checked_at")
    @classmethod
    def require_aware_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checked_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            return value
        return _sorted_unique_ids(value, "Context evidence IDs")

    @field_validator("run_id", "source")
    @classmethod
    def require_non_blank_context_scalar(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Context attestation identifiers must be non-blank.")
        return _require_safe_identifier(value, "Context attestation identifier")


class ContentSourceFactRegistryReceipt(_FrozenModel):
    """Exact runtime receipt for the current redacted source-fact registry."""

    registry_id: str = Field(
        min_length=1,
        max_length=240,
        pattern=_SAFE_IDENTIFIER,
        validation_alias=AliasChoices(
            "registry_id",
            "source_fact_registry_id",
            "approved_manifest_id",
        ),
    )
    registry_digest: str = Field(
        pattern=_HEX64,
        validation_alias=AliasChoices(
            "registry_digest",
            "source_fact_registry_digest",
            "approved_manifest_digest",
        ),
    )
    checked_at: datetime
    evidence_ids: tuple[str, ...] = Field(min_length=0, max_length=256)

    @field_validator("registry_digest")
    @classmethod
    def require_nonzero_registry_digest(cls, value: str) -> str:
        return _require_nonzero_digest(value)

    @field_validator("checked_at")
    @classmethod
    def require_aware_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checked_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            return value
        return _sorted_unique_ids(value, "Source registry evidence IDs")

    @field_validator("registry_id")
    @classmethod
    def require_non_blank_registry_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source registry receipt identifier must be non-blank.")
        return _require_safe_identifier(value, "Source registry receipt identifier")


class ContentSourcePackFactProvenance(_FrozenModel):
    """Redacted provenance carried from the exact row-authority receipt."""

    source_fact_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_type: str = Field(min_length=1)
    privacy_class: str = Field(min_length=1)
    source_reference_digest: str = Field(pattern=_HEX64)
    fact_digest: str = Field(pattern=_HEX64)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    evidence_digest: str = Field(pattern=_HEX64)
    review_status: Literal["approved"] = "approved"

    @field_validator(
        "source_reference_digest", "fact_digest", "evidence_digest"
    )
    @classmethod
    def require_nonzero_provenance_digests(cls, value: str) -> str:
        return _require_nonzero_digest(value)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_provenance_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return value if not value else _sorted_unique_ids(value, "Source fact evidence IDs")


class ContentSourcePackRowAuthorityReceipt(_FrozenModel):
    """Metadata-only projection of the receipt that authorizes a row's facts."""

    receipt_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    authority_snapshot_digest: str = Field(pattern=_HEX64)
    source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    source_facts_digest: str = Field(pattern=_HEX64)
    source_fact_provenance: tuple[ContentSourcePackFactProvenance, ...] = Field(
        min_length=1, max_length=256
    )
    source_fact_provenance_digest: str = Field(pattern=_HEX64)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    evidence_ids_digest: str = Field(pattern=_HEX64)
    action_payload_digest: str = Field(pattern=_HEX64)
    preview_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    review_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    confirmation_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    impact_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    reviewed_by: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    confirmed_by: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    recorded_by: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    recorded_at: datetime

    @field_validator(
        "receipt_digest",
        "authority_snapshot_digest",
        "source_facts_digest",
        "source_fact_provenance_digest",
        "evidence_ids_digest",
        "action_payload_digest",
    )
    @classmethod
    def require_nonzero_row_authority_digests(cls, value: str) -> str:
        return _require_nonzero_digest(value)

    @field_validator("source_fact_ids")
    @classmethod
    def require_sorted_row_authority_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Row-authority source fact IDs")

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_row_authority_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Row-authority evidence IDs")

    @field_validator("recorded_at")
    @classmethod
    def require_aware_row_authority_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Row-authority recorded_at must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_self_authenticating_row_authority_projection(self) -> Self:
        provenance_ids = tuple(item.source_fact_id for item in self.source_fact_provenance)
        if provenance_ids != self.source_fact_ids:
            raise ValueError("Row-authority provenance does not match source fact IDs.")
        if self.source_fact_provenance_digest != source_fact_provenance_digest(
            self.source_fact_provenance
        ):
            raise ValueError("Row-authority provenance digest does not match its rows.")
        if self.source_facts_digest != source_fact_ids_digest(self.source_fact_ids):
            raise ValueError("Row-authority source facts digest does not match its IDs.")
        if self.evidence_ids_digest != evidence_ids_digest(self.evidence_ids):
            raise ValueError("Row-authority evidence digest does not match its IDs.")
        return self


class ContentSourcePackPrerequisites(_FrozenModel):
    """Read-only projection joining exact S1 identity and row-authority receipt."""

    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    row_authority_status: Literal["missing", "exact_current", "blocked"]
    row_authority_reason_pl: str = Field(min_length=1)
    safe_next_step_pl: str = Field(min_length=1)
    approved_source_fact_ids: tuple[str, ...] = Field(max_length=256)
    global_approved_source_fact_count: int = Field(ge=0)
    source_fact_registry_receipt: ContentSourceFactRegistryReceipt
    fresh_context_digest: str = Field(pattern=_HEX64)
    fresh_context_attestation: ContentSourcePackContextAttestation
    row_authority_receipt: ContentSourcePackRowAuthorityReceipt | None = None
    # Keep the authority wording discoverable for API consumers while retaining
    # the shorter row-authority field used by the content workflow UI.
    source_fact_authority_receipt: ContentSourcePackRowAuthorityReceipt | None = None
    row_authority_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    allowed_evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    row_authority_blocker_reason: str | None = None

    @model_validator(mode="after")
    def require_context_match(self) -> Self:
        if self.fresh_context_attestation.context_digest != self.fresh_context_digest:
            raise ValueError("Fresh context prerequisite digest does not match attestation.")
        if self.row_authority_status != "exact_current" and self.approved_source_fact_ids:
            raise ValueError("Non-current row authority cannot expose selectable source facts.")
        if self.row_authority_status == "exact_current":
            if self.row_authority_blocker_reason is not None:
                raise ValueError(
                    "Exact-current prerequisites cannot carry a row-authority blocker."
                )
            if self.row_authority_receipt is None:
                raise ValueError("Exact-current prerequisites require a row-authority receipt.")
            if self.source_fact_authority_receipt != self.row_authority_receipt:
                raise ValueError("Row-authority receipt aliases must match.")
            if self.approved_source_fact_ids != self.row_authority_receipt.source_fact_ids:
                raise ValueError("Prerequisite facts must match the row-authority receipt.")
            if self.row_authority_evidence_ids != self.row_authority_receipt.evidence_ids:
                raise ValueError("Prerequisite evidence must match the row-authority receipt.")
        elif (
            self.row_authority_receipt is not None
            or self.source_fact_authority_receipt is not None
        ):
            raise ValueError("Blocked or missing row authority cannot expose its receipt.")
        elif self.row_authority_blocker_reason is None:
            raise ValueError("Blocked or missing row authority requires a typed blocker.")
        if self.allowed_evidence_ids != self.row_authority_evidence_ids:
            raise ValueError("Allowed evidence must match row-authority evidence.")
        return self

    @field_validator("approved_source_fact_ids")
    @classmethod
    def require_safe_approved_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return value if not value else _sorted_unique_ids(value, "Approved source fact IDs")
class ContentSourcePackBindingCommand(_FrozenModel):
    """Caller-owned source-pack metadata; no source payload is accepted."""

    source_pack_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_pack_sha256: str = Field(
        pattern=_HEX64,
        validation_alias=AliasChoices("source_pack_sha256", "source_pack_hash"),
    )
    identity_binding_id: str = Field(
        min_length=1,
        max_length=240,
        pattern=_SAFE_IDENTIFIER,
        validation_alias=AliasChoices("identity_binding_id", "delivery_identity_binding_id"),
    )
    identity_binding_digest: str = Field(
        pattern=_HEX64,
        validation_alias=AliasChoices(
            "identity_binding_digest", "delivery_identity_binding_digest"
        ),
    )
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    fresh_context_digest: str = Field(pattern=_HEX64)
    source_fact_registry_receipt: ContentSourceFactRegistryReceipt
    fresh_context_attestation: ContentSourcePackContextAttestation
    source_fact_authority_receipt_id: str | None = Field(
        default=None, max_length=240, pattern=_SAFE_IDENTIFIER
    )
    source_fact_authority_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    source_fact_authority_snapshot_digest: str | None = Field(default=None, pattern=_HEX64)
    recorded_by: str = Field(min_length=1, max_length=160, pattern=_SAFE_IDENTIFIER)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("source_fact_ids")
    @classmethod
    def require_sorted_source_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Source fact IDs")

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Evidence IDs")

    @field_validator(
        "source_pack_sha256",
        "identity_binding_digest",
        "fresh_context_digest",
    )
    @classmethod
    def require_nonzero_hashes(cls, value: str) -> str:
        return _require_nonzero_digest(value)

    @field_validator(
        "source_fact_authority_receipt_digest", "source_fact_authority_snapshot_digest"
    )
    @classmethod
    def require_nonzero_optional_authority_digests(cls, value: str | None) -> str | None:
        return None if value is None else _require_nonzero_digest(value)

    @model_validator(mode="after")
    def require_matching_context_digest(self) -> Self:
        if self.fresh_context_attestation.context_digest != self.fresh_context_digest:
            raise ValueError("Fresh context digest does not match its attestation.")
        return self

    @field_validator("source_pack_id", "current_work_item_id", "identity_binding_id", "recorded_by")
    @classmethod
    def require_non_blank_scalar(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source-pack binding identifiers must be non-blank.")
        return _require_safe_identifier(value, "Source-pack binding identifier")


class ContentSourcePackBindingBlocker(_FrozenModel):
    """Typed fail-closed reason safe to show below the operator decision."""

    seam: ContentSourcePackBindingSeam
    reason: ContentSourcePackBindingReason
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    next_step: str = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_blocker_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value and value != tuple(sorted(set(value))):
            raise ValueError("Blocker evidence IDs must be sorted and unique.")
        if any(not item.strip() for item in value):
            raise ValueError("Blocker evidence IDs must be non-blank.")
        return value


class ContentSourcePackBinding(_FrozenModel):
    """One immutable source-pack receipt bound to one exact S1 identity."""

    schema_version: Literal["wilq_content_source_pack_binding_v1"] = (
        "wilq_content_source_pack_binding_v1"
    )
    binding_id: str = Field(min_length=1)
    binding_digest: str = Field(pattern=_HEX64)
    status: Literal["exact_current", "blocked"]
    source_pack_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_pack_sha256: str = Field(
        pattern=_HEX64,
        validation_alias=AliasChoices("source_pack_sha256", "source_pack_hash"),
    )
    identity_binding_id: str = Field(
        min_length=1,
        max_length=240,
        pattern=_SAFE_IDENTIFIER,
        validation_alias=AliasChoices("identity_binding_id", "delivery_identity_binding_id"),
    )
    identity_binding_digest: str = Field(
        pattern=_HEX64,
        validation_alias=AliasChoices(
            "identity_binding_digest", "delivery_identity_binding_digest"
        ),
    )
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    evidence_ids: tuple[str, ...] = Field(min_length=0, max_length=256)
    source_facts_digest: str = Field(pattern=_HEX64)
    evidence_ids_digest: str = Field(pattern=_HEX64)
    fresh_context_digest: str = Field(pattern=_HEX64)
    source_fact_registry_receipt: ContentSourceFactRegistryReceipt
    fresh_context_attestation: ContentSourcePackContextAttestation
    blocker: ContentSourcePackBindingBlocker | None = None
    source_fact_authority_receipt_id: str | None = Field(
        default=None, max_length=240, pattern=_SAFE_IDENTIFIER
    )
    source_fact_authority_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    source_fact_authority_snapshot_digest: str | None = Field(default=None, pattern=_HEX64)
    source_fact_authority_provenance_digest: str | None = Field(default=None, pattern=_HEX64)
    recorded_by: str = Field(min_length=1, max_length=160, pattern=_SAFE_IDENTIFIER)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("source_fact_ids")
    @classmethod
    def require_sorted_source_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Source fact IDs")

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            return value
        return _sorted_unique_ids(value, "Evidence IDs")

    @field_validator(
        "binding_digest",
        "source_pack_sha256",
        "identity_binding_digest",
        "source_facts_digest",
        "evidence_ids_digest",
        "fresh_context_digest",
    )
    @classmethod
    def require_nonzero_digests(cls, value: str) -> str:
        return _require_nonzero_digest(value)

    @field_validator(
        "source_fact_authority_receipt_digest",
        "source_fact_authority_snapshot_digest",
        "source_fact_authority_provenance_digest",
    )
    @classmethod
    def require_nonzero_optional_authority_digests(cls, value: str | None) -> str | None:
        return None if value is None else _require_nonzero_digest(value)

    @model_validator(mode="after")
    def require_self_authenticating_binding(self) -> Self:
        if (self.status == "blocked") != (self.blocker is not None):
            raise ValueError("Blocked source-pack state must carry exactly one typed blocker.")
        if self.source_facts_digest != source_fact_ids_digest(self.source_fact_ids):
            raise ValueError("Source fact digest does not match its allow-list.")
        if self.evidence_ids_digest != evidence_ids_digest(self.evidence_ids):
            raise ValueError("Evidence digest does not match its allow-list.")
        if self.fresh_context_attestation.context_digest != self.fresh_context_digest:
            raise ValueError("Fresh context digest does not match its attestation.")
        expected_digest = content_source_pack_binding_digest(self)
        expected_id = (
            f"content_source_pack_binding_{content_source_pack_binding_logical_id(self)[:24]}"
        )
        if self.binding_digest != expected_digest or self.binding_id != expected_id:
            raise ValueError("Source-pack binding ID/digest does not match its payload.")
        return self


class ContentSourcePackBindingRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    binding: ContentSourcePackBinding


class ContentSourcePackBindingReadResult(_FrozenModel):
    status: Literal["found"] = "found"
    binding: ContentSourcePackBinding
