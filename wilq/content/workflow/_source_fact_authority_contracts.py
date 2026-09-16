"""Exact, ActionObject-owned authority for selecting source facts per S1 row.

The source-fact registry and source review ledgers answer whether a fact is
approved.  This module answers the separate question of whether that exact
fact set is approved for one exact current content row.  Proposals are safe to
persist; only the canonical ActionObject apply adapter may create a receipt.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.knowledge.source_facts import (
    ContentSourceFact,
)
from wilq.content.workflow.decisions.production import (
    canonical_json_digest,
)
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityBlocker,
    ContentSourceFactAuthorityCandidate,
    ContentSourceFactAuthorityCandidateProjection,
    ContentSourceFactAuthorityRegistryReceipt,
    ContentSourceFactAuthorityServiceBinding,
)
from wilq.schemas import (
    ActionObject,
    AuditEvent,
)

SOURCE_FACT_AUTHORITY_ACTION_TYPE = "content_source_fact_authority_receipt"
SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT = "content_source_fact_authority_preview_v1"
SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER = "content_source_fact_authority_store"
SOURCE_FACT_AUTHORITY_RECORDED_EVENT = "content_source_fact_authority_recorded"
SOURCE_FACT_AUTHORITY_PROPOSAL_SCHEMA: Literal["wilq_content_source_fact_authority_proposal_v1"] = (
    "wilq_content_source_fact_authority_proposal_v1"
)
SOURCE_FACT_AUTHORITY_RECEIPT_SCHEMA: Literal["wilq_content_source_fact_authority_receipt_v1"] = (
    "wilq_content_source_fact_authority_receipt_v1"
)

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _nonzero_digest(value: str) -> str:
    if value == "0" * 64:
        raise ValueError("Authority digest cannot be zero.")
    return value


def _sorted_unique_ids(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(item.strip() for item in value)
    if (
        not normalized
        or any(not item for item in normalized)
        or any(not re.fullmatch(_SAFE_IDENTIFIER, item) for item in normalized)
        or len(normalized) != len(set(normalized))
        or normalized != tuple(sorted(normalized))
    ):
        raise ValueError(f"{label} must be sorted, unique and non-blank.")
    return normalized


def _sorted_optional_ids(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    if not value:
        return value
    return _sorted_unique_ids(value, label)


class ContentSourceFactAuthorityPreviewCommand(_FrozenModel):
    """The only public input to a source-fact authority preview."""

    identity_binding_id: str = Field(
        min_length=1,
        max_length=240,
        pattern=_SAFE_IDENTIFIER,
    )
    proposed_source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    # A retry must be a new append-only ActionObject identity.  Keep attempt
    # optional so proposals written before this field existed remain readable
    # as attempt zero.
    attempt: int = Field(default=0, ge=0, le=1000, strict=True)

    @field_validator("proposed_source_fact_ids")
    @classmethod
    def require_sorted_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Proposed source fact IDs")


class ContentSourceFactProvenance(_FrozenModel):
    """Redacted, typed provenance for one approved source fact."""

    source_fact_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_type: str = Field(min_length=1)
    privacy_class: str = Field(min_length=1)
    source_reference_digest: str = Field(pattern=_HEX64)
    fact_digest: str = Field(pattern=_HEX64)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    evidence_digest: str = Field(pattern=_HEX64)
    review_status: Literal["approved"] = "approved"

    @field_validator("source_reference_digest", "fact_digest", "evidence_digest")
    @classmethod
    def require_nonzero_digests(cls, value: str) -> str:
        return _nonzero_digest(value)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_optional_ids(value, "Source fact evidence IDs")


class ContentSourceFactAuthoritySnapshot(_FrozenModel):
    """The exact S1/classification/registry/fact selection being reviewed."""

    schema_version: Literal["wilq_content_source_fact_authority_snapshot_v1"] = (
        "wilq_content_source_fact_authority_snapshot_v1"
    )
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    classification_run_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    classification_run_digest: str = Field(pattern=_HEX64)
    classification_decision_set_digest: str = Field(pattern=_HEX64)
    classification_source_row_digest: str = Field(pattern=_HEX64)
    source_fact_registry_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_fact_registry_digest: str = Field(pattern=_HEX64)
    source_fact_registry_evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    source_facts_digest: str = Field(pattern=_HEX64)
    source_fact_provenance: tuple[ContentSourceFactProvenance, ...] = Field(
        min_length=1,
        max_length=256,
    )
    source_fact_provenance_digest: str = Field(pattern=_HEX64)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    evidence_ids_digest: str = Field(pattern=_HEX64)
    context_digest: str = Field(pattern=_HEX64)
    # The exact service-card binding is part of the row context.  It is
    # optional only for legacy snapshots; newly built snapshots always carry
    # it so card evidence/freshness drift invalidates the receipt.
    service_binding: ContentSourceFactAuthorityServiceBinding | None = None

    @field_validator(
        "identity_binding_digest",
        "classification_run_digest",
        "classification_decision_set_digest",
        "classification_source_row_digest",
        "source_fact_registry_digest",
        "source_facts_digest",
        "source_fact_provenance_digest",
        "evidence_ids_digest",
        "context_digest",
    )
    @classmethod
    def require_nonzero_context_digests(cls, value: str) -> str:
        return _nonzero_digest(value)

    @field_validator("source_fact_registry_evidence_ids", "evidence_ids")
    @classmethod
    def require_sorted_context_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_optional_ids(value, "Authority evidence IDs")

    @field_validator("source_fact_ids")
    @classmethod
    def require_sorted_context_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Authority source fact IDs")

    @model_validator(mode="after")
    def require_self_authenticating_snapshot(self) -> Self:
        provenance_ids = tuple(item.source_fact_id for item in self.source_fact_provenance)
        if self.source_facts_digest != authority_source_fact_ids_digest(self.source_fact_ids):
            raise ValueError("source facts digest does not match the selected source facts.")
        if provenance_ids != self.source_fact_ids:
            raise ValueError("Source fact provenance does not match source fact IDs.")
        if self.source_fact_provenance_digest != authority_source_fact_provenance_digest(
            self.source_fact_provenance
        ):
            raise ValueError("Source fact provenance digest does not match its rows.")
        if self.evidence_ids_digest != authority_evidence_ids_digest(self.evidence_ids):
            raise ValueError("Authority evidence digest does not match its evidence IDs.")
        if self.context_digest != source_fact_authority_snapshot_digest(self):
            raise ValueError("source row digest or authority context digest does not match.")
        return self


class ContentSourceFactAuthorityProposal(_FrozenModel):
    schema_version: Literal["wilq_content_source_fact_authority_proposal_v1"] = (
        SOURCE_FACT_AUTHORITY_PROPOSAL_SCHEMA
    )
    action_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    proposal_digest: str = Field(pattern=_HEX64)
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    proposed_source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    # Legacy proposal JSON omitted this field; Pydantic's default keeps those
    # rows valid while non-zero attempts receive a distinct identity.
    attempt: int = Field(default=0, ge=0, le=1000, strict=True)
    prepared_snapshot_digest: str | None = Field(default=None, pattern=_HEX64)
    prepared_at: datetime

    @field_validator("proposal_digest")
    @classmethod
    def require_nonzero_proposal_digest(cls, value: str) -> str:
        return _nonzero_digest(value)

    @field_validator("proposed_source_fact_ids")
    @classmethod
    def require_sorted_proposal_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Proposed source fact IDs")

    @field_validator("prepared_at")
    @classmethod
    def require_aware_prepared_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("prepared_at must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_exact_proposal_identity(self) -> Self:
        expected = source_fact_authority_proposal_digest(
            self.identity_binding_id,
            self.proposed_source_fact_ids,
            self.attempt,
        )
        if self.proposal_digest != expected or self.action_id != source_fact_authority_action_id(
            self.identity_binding_id,
            self.proposed_source_fact_ids,
            self.attempt,
        ):
            raise ValueError("Source fact authority proposal ID/digest does not match.")
        return self


class ContentSourceFactAuthorityReceipt(_FrozenModel):
    """One exact receipt created only by the ActionObject executor."""

    schema_version: Literal["wilq_content_source_fact_authority_receipt_v1"] = (
        SOURCE_FACT_AUTHORITY_RECEIPT_SCHEMA
    )
    receipt_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    action_payload_digest: str = Field(pattern=_HEX64)
    authority_snapshot: ContentSourceFactAuthoritySnapshot
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
        "action_payload_digest",
    )
    @classmethod
    def require_nonzero_receipt_digests(cls, value: str) -> str:
        return _nonzero_digest(value)

    @field_validator("recorded_at")
    @classmethod
    def require_aware_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_self_authenticating_receipt(self) -> Self:
        expected_digest = source_fact_authority_receipt_digest(self)
        expected_id = f"content_source_fact_authority_{expected_digest[:24]}"
        if self.receipt_digest != expected_digest or self.receipt_id != expected_id:
            raise ValueError("Source fact authority receipt ID/digest does not match.")
        return self


class ContentSourceFactAuthorityPreviewResponse(_FrozenModel):
    response_type: Literal["content_source_fact_authority_preview"] = (
        "content_source_fact_authority_preview"
    )
    status: Literal["preview_ready", "blocked"]
    action: ActionObject
    identity_binding_id: str = Field(min_length=1)
    proposed_source_fact_ids: tuple[str, ...] = Field(min_length=1)
    blockers: tuple[ContentSourceFactAuthorityBlocker, ...] = ()
    preview_audit_id: str | None = None

    @model_validator(mode="after")
    def require_preview_status(self) -> Self:
        expected_blocked = bool(self.blockers) or bool(self.action.payload.get("runtime_blockers"))
        if (self.status == "blocked") != expected_blocked:
            raise ValueError("Authority preview status does not match its blockers.")
        return self


class ContentSourceFactAuthorityReadProjection(_FrozenModel):
    response_type: Literal["content_source_fact_authority_read"] = (
        "content_source_fact_authority_read"
    )
    status: Literal["current", "blocked", "missing"]
    identity_binding_id: str = Field(min_length=1)
    current_work_item_id: str | None = None
    canonical_path: str | None = None
    public_url: str | None = None
    current_snapshot: ContentSourceFactAuthoritySnapshot | None = None
    receipt: ContentSourceFactAuthorityReceipt | None = None
    blockers: tuple[ContentSourceFactAuthorityBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_read_state(self) -> Self:
        if self.status == "current" and self.receipt is None:
            raise ValueError("Current source fact authority read requires a receipt.")
        if self.status == "missing" and self.receipt is not None:
            raise ValueError("Missing source fact authority read cannot carry a receipt.")
        return self


class ContentSourceFactAuthorityApplyResult(_FrozenModel):
    status: Literal["created", "idempotent", "blocked", "conflict"]
    receipt: ContentSourceFactAuthorityReceipt | None = None
    audit_event: AuditEvent | None = None
    blockers: tuple[ContentSourceFactAuthorityBlocker, ...] = ()


def authority_source_fact_ids_digest(source_fact_ids: tuple[str, ...]) -> str:
    return canonical_json_digest({"source_fact_ids": source_fact_ids})


def authority_evidence_ids_digest(evidence_ids: tuple[str, ...]) -> str:
    return canonical_json_digest({"evidence_ids": evidence_ids})


def authority_source_fact_reference_digest(fact: ContentSourceFact) -> str:
    return canonical_json_digest(
        {
            "source_type": fact.source_type,
            "privacy_class": fact.privacy_class,
            "source_url_or_path": fact.source_url_or_path,
        }
    )


def authority_source_fact_digest(fact: ContentSourceFact) -> str:
    return canonical_json_digest(fact.model_dump(mode="json"))


def authority_source_fact_evidence_digest(fact: ContentSourceFact) -> str:
    evidence_ids = tuple(sorted(set(fact.evidence_ids)))
    return canonical_json_digest({"source_fact_id": fact.source_id, "evidence_ids": evidence_ids})


def authority_source_fact_provenance(fact: ContentSourceFact) -> ContentSourceFactProvenance:
    evidence_ids = tuple(sorted(set(fact.evidence_ids)))
    return ContentSourceFactProvenance(
        source_fact_id=fact.source_id,
        source_type=fact.source_type,
        privacy_class=fact.privacy_class,
        source_reference_digest=authority_source_fact_reference_digest(fact),
        fact_digest=authority_source_fact_digest(fact),
        evidence_ids=evidence_ids,
        evidence_digest=authority_source_fact_evidence_digest(fact),
    )


def authority_source_fact_provenance_digest(
    provenance: tuple[ContentSourceFactProvenance, ...],
) -> str:
    return canonical_json_digest(
        {"source_fact_provenance": [item.model_dump(mode="json") for item in provenance]}
    )


def source_fact_authority_snapshot_digest(
    value: ContentSourceFactAuthoritySnapshot | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    # Legacy receipts predate the service-card binding.  Preserve their
    # original digest while making the field part of every newly built
    # snapshot's digest.
    if isinstance(value, ContentSourceFactAuthoritySnapshot) and (
        "service_binding" not in value.__pydantic_fields_set__
    ):
        payload.pop("service_binding", None)
    payload.pop("context_digest", None)
    return canonical_json_digest(payload)


def parse_source_fact_authority_snapshot_json(
    value: ContentSourceFactAuthoritySnapshot | dict[str, Any],
) -> ContentSourceFactAuthoritySnapshot:
    """Parse a persisted snapshot through Pydantic's strict JSON boundary.

    SQLite and ActionObject payloads are untrusted serialized data.  Reusing
    ``model_validate`` here would allow Python-side coercions (for example an
    integer becoming a string), so the executor always serializes the exact
    payload and validates the resulting JSON strictly.
    """

    serialized = json.dumps(
        value.model_dump(mode="json") if isinstance(value, BaseModel) else value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return ContentSourceFactAuthoritySnapshot.model_validate_json(serialized, strict=True)


def source_fact_authority_proposal_digest(
    identity_binding_id: str,
    source_fact_ids: tuple[str, ...],
    attempt: int = 0,
) -> str:
    _validate_attempt(attempt)
    payload: dict[str, Any] = {
        "identity_binding_id": identity_binding_id,
        "proposed_source_fact_ids": source_fact_ids,
    }
    # Do not change the digest of historical/legacy attempt-zero proposals.
    if attempt:
        payload["attempt"] = attempt
    return canonical_json_digest(payload)


def source_fact_authority_action_id(
    identity_binding_id: str,
    source_fact_ids: tuple[str, ...],
    attempt: int = 0,
) -> str:
    _validate_attempt(attempt)
    # Keep the historical action ID stable, while making retries explicit and
    # easy to distinguish in the action/audit ledgers.
    digest = source_fact_authority_proposal_digest(identity_binding_id, source_fact_ids)
    base_id = f"act_source_fact_authority_{digest[:24]}"
    return base_id if attempt == 0 else f"{base_id}_attempt_{attempt}"


def source_fact_authority_action_payload_digest(action: ActionObject) -> str:
    authority_payload = action.payload.get("source_fact_authority")
    if not isinstance(authority_payload, dict):
        return "0" * 64
    attempt = action.payload.get("attempt", 0)
    _validate_attempt(attempt)
    payload: dict[str, Any] = {
        "action_type": action.payload.get("action_type"),
        "proposal_digest": action.payload.get("proposal_digest"),
        "source_fact_authority": authority_payload,
    }
    # Legacy attempt-zero ActionObjects did not carry this field.  Keep their
    # payload/audit/receipt digest stable, while binding every retry's exact
    # attempt into the digest so a 1 -> 2 rewrite cannot pass apply checks.
    if attempt:
        payload["attempt"] = attempt
    return canonical_json_digest(payload)


def source_fact_authority_receipt_digest(
    value: ContentSourceFactAuthorityReceipt | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    for key in ("receipt_id", "receipt_digest", "recorded_by", "recorded_at"):
        payload.pop(key, None)
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _validate_attempt(attempt: int) -> None:
    if isinstance(attempt, bool) or not isinstance(attempt, int) or not 0 <= attempt <= 1000:
        raise ValueError("Source fact authority attempt must be an integer from 0 to 1000.")


__all__ = [
    "SOURCE_FACT_AUTHORITY_ACTION_TYPE",
    "SOURCE_FACT_AUTHORITY_MUTATION_ADAPTER",
    "SOURCE_FACT_AUTHORITY_PREVIEW_CONTRACT",
    "SOURCE_FACT_AUTHORITY_PROPOSAL_SCHEMA",
    "SOURCE_FACT_AUTHORITY_RECEIPT_SCHEMA",
    "SOURCE_FACT_AUTHORITY_RECORDED_EVENT",
    "ContentSourceFactAuthorityApplyResult",
    "ContentSourceFactAuthorityBlocker",
    "ContentSourceFactAuthorityCandidate",
    "ContentSourceFactAuthorityCandidateProjection",
    "ContentSourceFactAuthorityPreviewCommand",
    "ContentSourceFactAuthorityPreviewResponse",
    "ContentSourceFactAuthorityProposal",
    "ContentSourceFactAuthorityReadProjection",
    "ContentSourceFactAuthorityReceipt",
    "ContentSourceFactAuthorityRegistryReceipt",
    "ContentSourceFactAuthorityServiceBinding",
    "ContentSourceFactAuthoritySnapshot",
    "ContentSourceFactProvenance",
    "authority_evidence_ids_digest",
    "authority_source_fact_digest",
    "authority_source_fact_evidence_digest",
    "authority_source_fact_ids_digest",
    "authority_source_fact_provenance",
    "authority_source_fact_provenance_digest",
    "authority_source_fact_reference_digest",
    "parse_source_fact_authority_snapshot_json",
    "source_fact_authority_action_id",
    "source_fact_authority_action_payload_digest",
    "source_fact_authority_proposal_digest",
    "source_fact_authority_receipt_digest",
    "source_fact_authority_snapshot_digest",
]
