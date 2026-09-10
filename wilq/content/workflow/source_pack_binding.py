"""Exact, redacted source-pack bindings for content production.

This module is the S2.1 seam between the delivery-identity receipt and later
source registry/research-packet work.  It deliberately accepts only opaque
identities, digests and allow-listed IDs.  Source contents are owned by the
later source-pack modules and never cross this seam or enter SQLite.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal, Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.evidence.registry import (
    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
)

SOURCE_FACT_REGISTRY_ID = "ekologus_source_fact_registry"
SOURCE_PACK_BINDING_RECORDED_EVENT = "content_source_pack_binding_recorded"
SOURCE_PACK_BINDING_ADAPTER = "content_source_pack_binding_store"

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_SECRET_LIKE_IDENTIFIER = re.compile(
    r"(?:^|[^A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|gho_[A-Za-z0-9_]{20,}|ya29\.[A-Za-z0-9._-]{20,})",
    re.IGNORECASE,
)
_MAX_RECEIPT_AGE = timedelta(days=30)
_MAX_RECORDED_AT_AGE = timedelta(days=1)

ContentSourcePackBindingSeam = Literal[
    "source_pack_identity",
    "delivery_identity",
    "work_item_identity",
    "source_fact_whitelist",
    "evidence_whitelist",
    "fresh_context",
]
ContentSourcePackBindingReason = Literal[
    "source_pack_identity_missing",
    "source_pack_hash_mismatch",
    "delivery_identity_missing",
    "delivery_identity_digest_mismatch",
    "delivery_identity_blocked",
    "work_item_mismatch",
    "source_facts_missing",
    "evidence_missing",
    "evidence_not_bound",
    "evidence_set_mismatch",
    "fresh_context_missing",
    "fresh_context_mismatch",
    "fresh_context_stale",
    "source_fact_registry_mismatch",
    "source_fact_registry_stale",
    "source_fact_not_registered",
    "source_fact_not_approved",
    "source_facts_mismatch",
]


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


class ContentSourcePackPrerequisites(_FrozenModel):
    """Read-only projection for clients constructing an exact source command."""

    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    approved_source_fact_ids: tuple[str, ...] = Field(min_length=1, max_length=4096)
    source_fact_registry_receipt: ContentSourceFactRegistryReceipt
    fresh_context_digest: str = Field(pattern=_HEX64)
    fresh_context_attestation: ContentSourcePackContextAttestation

    @model_validator(mode="after")
    def require_context_match(self) -> Self:
        if self.fresh_context_attestation.context_digest != self.fresh_context_digest:
            raise ValueError("Fresh context prerequisite digest does not match attestation.")
        return self

    @field_validator("approved_source_fact_ids")
    @classmethod
    def require_safe_approved_facts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique_ids(value, "Approved source fact IDs")


def build_content_source_pack_prerequisites(
    identity: ContentDeliveryIdentityBinding,
    *,
    checked_at: datetime | None = None,
) -> ContentSourcePackPrerequisites:
    """Build current registry/context receipts from one exact S1 identity."""

    timestamp = checked_at or datetime.now(UTC)
    facts = ekologus_source_facts()
    registry_receipt = ContentSourceFactRegistryReceipt(
        registry_id=SOURCE_FACT_REGISTRY_ID,
        registry_digest=source_fact_registry_digest(facts),
        checked_at=timestamp,
        evidence_ids=tuple(
            sorted(
                {
                    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
                }
            )
        ),
    )
    attestation = ContentSourcePackContextAttestation(
        run_id=identity.classification_run_id,
        context_digest="1" * 64,
        checked_at=timestamp,
        source="content_delivery_identity_binding",
        evidence_ids=identity.inventory_evidence_ids,
    )
    context_digest = content_source_pack_context_digest(identity, attestation)
    attestation = attestation.model_copy(update={"context_digest": context_digest})
    return ContentSourcePackPrerequisites(
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        current_work_item_id=identity.current_work_item_id,
        approved_source_fact_ids=tuple(
            sorted(fact.source_id for fact in facts if fact.review_status == "approved")
        ),
        source_fact_registry_receipt=registry_receipt,
        fresh_context_digest=context_digest,
        fresh_context_attestation=attestation,
    )


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


def content_source_pack_binding_logical_id(
    value: ContentSourcePackBinding | ContentSourcePackBindingCommand | dict[str, object],
) -> str:
    if isinstance(value, (ContentSourcePackBinding, ContentSourcePackBindingCommand)):
        return _content_source_pack_binding_logical_id_from_model(value)
    payload = _payload(value)
    source_fact_values = payload.get("source_fact_ids")
    evidence_values = payload.get("evidence_ids")
    receipt_value = payload.get("source_fact_registry_receipt")
    blocker_value = payload.get("blocker")
    return canonical_json_digest(
        {
            "source_pack_id": payload["source_pack_id"],
            "source_pack_sha256": payload["source_pack_sha256"],
            "identity_binding_id": payload["identity_binding_id"],
            "identity_binding_digest": payload["identity_binding_digest"],
            "current_work_item_id": payload["current_work_item_id"],
            "source_facts_digest": source_fact_ids_digest(
                tuple(source_fact_values) if isinstance(source_fact_values, (list, tuple)) else ()
            ),
            "evidence_ids_digest": evidence_ids_digest(
                tuple(evidence_values) if isinstance(evidence_values, (list, tuple)) else ()
            ),
            "fresh_context_digest": payload["fresh_context_digest"],
            "source_fact_registry_digest": (
                receipt_value.get("registry_digest") if isinstance(receipt_value, dict) else None
            ),
            "status": payload.get("status"),
            "blocker_reason": (
                blocker_value.get("reason") if isinstance(blocker_value, dict) else None
            ),
        }
    )


def _content_source_pack_binding_logical_id_from_model(
    value: ContentSourcePackBinding | ContentSourcePackBindingCommand,
) -> str:
    receipt = value.source_fact_registry_receipt
    status = value.status if isinstance(value, ContentSourcePackBinding) else None
    blocker_reason = (
        value.blocker.reason
        if isinstance(value, ContentSourcePackBinding) and value.blocker is not None
        else None
    )
    return canonical_json_digest(
        {
            "source_pack_id": value.source_pack_id,
            "source_pack_sha256": value.source_pack_sha256,
            "identity_binding_id": value.identity_binding_id,
            "identity_binding_digest": value.identity_binding_digest,
            "current_work_item_id": value.current_work_item_id,
            "source_facts_digest": source_fact_ids_digest(value.source_fact_ids),
            "evidence_ids_digest": evidence_ids_digest(value.evidence_ids),
            "fresh_context_digest": value.fresh_context_digest,
            "source_fact_registry_digest": receipt.registry_digest,
            "status": status,
            "blocker_reason": blocker_reason,
        }
    )


def source_fact_ids_digest(source_fact_ids: tuple[str, ...]) -> str:
    """Digest the exact ordered, allow-listed source fact IDs."""

    return canonical_json_digest({"source_fact_ids": source_fact_ids})


def evidence_ids_digest(evidence_ids: tuple[str, ...]) -> str:
    """Digest the exact ordered, allow-listed evidence IDs."""

    return canonical_json_digest({"evidence_ids": evidence_ids})


def source_fact_registry_digest(
    facts: tuple[ContentSourceFact, ...] | None = None,
) -> str:
    """Digest the exact currently readable source-fact registry projection."""

    facts = ekologus_source_facts() if facts is None else facts
    return canonical_json_digest(
        {
            "registry_id": SOURCE_FACT_REGISTRY_ID,
            "fact_count": len(facts),
            "facts": [fact.model_dump(mode="json") for fact in facts],
        }
    )


def content_source_pack_context_digest(
    identity: ContentDeliveryIdentityBinding,
    attestation: ContentSourcePackContextAttestation,
) -> str:
    """Digest the exact current S1 identity and its context attestation."""

    return canonical_json_digest(
        {
            "identity_binding_id": identity.binding_id,
            "identity_binding_digest": identity.binding_digest,
            "current_work_item_id": identity.current_work_item_id,
            "classification_run_id": identity.classification_run_id,
            "classification_run_digest": identity.classification_run_digest,
            "classification_decision_set_digest": identity.classification_decision_set_digest,
            "classification_source_row_digest": identity.classification_source_row_digest,
            "inventory_evidence_ids": identity.inventory_evidence_ids,
            "inventory_evidence_digest": identity.inventory_evidence_digest,
            "attestation": {
                "run_id": attestation.run_id,
                "source": attestation.source,
                "checked_at": attestation.checked_at.isoformat(),
                "evidence_ids": attestation.evidence_ids,
            },
        }
    )


def content_source_pack_binding_digest(
    value: ContentSourcePackBinding | dict[str, object],
) -> str:
    payload = _payload(value)
    for name in ("binding_id", "binding_digest", "recorded_by", "recorded_at"):
        payload.pop(name, None)
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def reconcile_content_source_pack_binding(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding | None,
    *,
    prior_pack_hashes: tuple[str, ...] = (),
    prior_source_fact_sets: tuple[tuple[str, ...], ...] = (),
    prior_evidence_sets: tuple[tuple[str, ...], ...] = (),
    now: datetime | None = None,
) -> ContentSourcePackBinding:
    """Build one exact receipt; all joins are explicit and fail closed.

    Prior values are supplied by the store, not looked up by fuzzy path or
    implicit latest state.  They prevent a changed source pack/context/evidence
    set from silently replacing an earlier immutable receipt.
    """

    accepted = ContentSourcePackBindingCommand.model_validate_json(
        command.model_dump_json(), strict=True
    )
    blocker = _binding_blocker(
        accepted,
        identity,
        prior_pack_hashes=prior_pack_hashes,
        prior_source_fact_sets=prior_source_fact_sets,
        prior_evidence_sets=prior_evidence_sets,
        now=datetime.now(UTC) if now is None else now,
    )
    status: Literal["exact_current", "blocked"] = "blocked" if blocker else "exact_current"
    persisted_evidence_ids = _effective_evidence_ids(accepted, identity)
    persisted_registry_evidence_ids = _known_evidence_ids(
        accepted.source_fact_registry_receipt.evidence_ids, None
    )
    persisted_context_attestation = accepted.fresh_context_attestation.model_copy(
        update={
            "evidence_ids": _known_evidence_ids(
                accepted.fresh_context_attestation.evidence_ids, identity
            )
        }
    )
    persisted_context_digest = (
        content_source_pack_context_digest(identity, persisted_context_attestation)
        if identity is not None
        else accepted.fresh_context_digest
    )
    persisted_context_attestation = persisted_context_attestation.model_copy(
        update={"context_digest": persisted_context_digest}
    )
    payload: dict[str, object] = {
        "schema_version": "wilq_content_source_pack_binding_v1",
        "status": status,
        "source_pack_id": accepted.source_pack_id,
        "source_pack_sha256": accepted.source_pack_sha256,
        "identity_binding_id": accepted.identity_binding_id,
        "identity_binding_digest": accepted.identity_binding_digest,
        "current_work_item_id": accepted.current_work_item_id,
        "source_fact_ids": accepted.source_fact_ids,
        "evidence_ids": persisted_evidence_ids,
        "source_facts_digest": source_fact_ids_digest(accepted.source_fact_ids),
        "evidence_ids_digest": evidence_ids_digest(persisted_evidence_ids),
        "fresh_context_digest": persisted_context_digest,
        "source_fact_registry_receipt": accepted.source_fact_registry_receipt.model_copy(
            update={"evidence_ids": persisted_registry_evidence_ids}
        ).model_dump(mode="json"),
        "fresh_context_attestation": persisted_context_attestation.model_dump(mode="json"),
        "blocker": None if blocker is None else blocker.model_dump(mode="json"),
        "recorded_by": accepted.recorded_by,
        "recorded_at": accepted.recorded_at.isoformat(),
    }
    digest = content_source_pack_binding_digest(payload)
    logical_id = content_source_pack_binding_logical_id(payload)
    return ContentSourcePackBinding.model_validate(
        {
            "binding_id": f"content_source_pack_binding_{logical_id[:24]}",
            "binding_digest": digest,
            **payload,
        }
    )


def _binding_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding | None,
    *,
    prior_pack_hashes: tuple[str, ...],
    prior_source_fact_sets: tuple[tuple[str, ...], ...],
    prior_evidence_sets: tuple[tuple[str, ...], ...],
    now: datetime,
) -> ContentSourcePackBindingBlocker | None:
    input_evidence = command.evidence_ids
    evidence = _known_evidence_ids(input_evidence, identity)
    if command.recorded_at > now + timedelta(minutes=5):
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            evidence,
            "Użyj server-owned recorded_at z bieżącego okna czasu.",
        )
    if now - command.recorded_at > _MAX_RECORDED_AT_AGE:
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            evidence,
            "Użyj recorded_at z ostatnich 24 godzin albo pobierz nowe prerequisites.",
        )
    if not command.source_pack_id.strip() or not command.source_pack_sha256:
        return _blocker(
            "source_pack_identity",
            "source_pack_identity_missing",
            evidence,
            "Podaj jednocześnie exact source-pack ID i jego SHA-256.",
        )
    registry_blocker = _source_fact_blocker(command)
    if registry_blocker is not None:
        return registry_blocker
    if prior_pack_hashes and command.source_pack_sha256 not in set(prior_pack_hashes):
        return _blocker(
            "source_pack_identity",
            "source_pack_hash_mismatch",
            evidence,
            "Zweryfikuj hash tej samej wersji source packa; nie zastępuj istniejącego receiptu.",
        )
    if identity is None:
        return _blocker(
            "delivery_identity",
            "delivery_identity_missing",
            evidence,
            "Najpierw zapisz exact S1 identity binding dla tego source packa.",
        )
    if (
        identity.binding_id != command.identity_binding_id
        or identity.binding_digest != command.identity_binding_digest
    ):
        return _blocker(
            "delivery_identity",
            "delivery_identity_digest_mismatch",
            evidence,
            "Użyj ID i digestu z tego samego persisted S1 identity bindingu.",
        )
    if identity.status == "blocked":
        return _blocker(
            "delivery_identity",
            "delivery_identity_blocked",
            (*evidence, *identity.inventory_evidence_ids),
            "Usuń typed blocker S1 i dopiero potem wiąż source pack.",
        )
    if identity.current_work_item_id != command.current_work_item_id:
        return _blocker(
            "work_item_identity",
            "work_item_mismatch",
            (*evidence, *identity.inventory_evidence_ids),
            "Wskaż current work item zapisany w exact S1 identity bindingu.",
        )
    if not set(identity.inventory_evidence_ids).issubset(set(input_evidence)):
        return _blocker(
            "evidence_whitelist",
            "evidence_not_bound",
            (*evidence, *identity.inventory_evidence_ids),
            "Dodaj do whitelisty evidence dokładnie zakotwiczone w S1 inventory bindingu.",
        )
    allowed_evidence = (
        set(identity.inventory_evidence_ids)
        | set(command.source_fact_registry_receipt.evidence_ids)
        | set(command.fresh_context_attestation.evidence_ids)
    )
    if set(input_evidence) - allowed_evidence:
        return _blocker(
            "evidence_whitelist",
            "evidence_not_bound",
            evidence,
            "Usuń evidence spoza exact S1, registry i context attestation whitelisty.",
        )
    context_blocker = _context_blocker(command, identity, evidence)
    if context_blocker is not None:
        return context_blocker
    registry_receipt = command.source_fact_registry_receipt
    if prior_source_fact_sets and tuple(command.source_fact_ids) not in set(prior_source_fact_sets):
        return _blocker(
            "source_fact_whitelist",
            "source_facts_mismatch",
            _known_evidence_ids((*evidence, *registry_receipt.evidence_ids), identity),
            "Nie zmieniaj source-fact whitelisty istniejącego receipt; utwórz nowy exact pack.",
        )
    if prior_evidence_sets and tuple(command.evidence_ids) not in set(prior_evidence_sets):
        return _blocker(
            "evidence_whitelist",
            "evidence_set_mismatch",
            evidence,
            "Zachowaj exact evidence whitelistę z zatwierdzonego source-pack contextu.",
        )
    return None


def _effective_evidence_ids(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding | None,
) -> tuple[str, ...]:
    """Persist only evidence from known S1/registry owners, including blocked attempts."""

    allowed = {
        APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
        SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    }
    if identity is not None:
        allowed.update(identity.inventory_evidence_ids)
    selected = tuple(sorted(set(command.evidence_ids) & allowed))
    return selected


def _known_evidence_ids(
    evidence_ids: tuple[str, ...],
    identity: ContentDeliveryIdentityBinding | None,
) -> tuple[str, ...]:
    allowed = {
        APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
        SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
    }
    if identity is not None:
        allowed.update(identity.inventory_evidence_ids)
    return tuple(sorted(set(evidence_ids) & allowed))


def _source_fact_blocker(
    command: ContentSourcePackBindingCommand,
) -> ContentSourcePackBindingBlocker | None:
    receipt = command.source_fact_registry_receipt
    if receipt.checked_at > command.recorded_at:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_stale",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Registry receipt nie może pochodzić z przyszłości względem zapisu.",
        )
    if command.recorded_at - receipt.checked_at > _MAX_RECEIPT_AGE:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_stale",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Odśwież source-fact registry receipt w dozwolonym oknie 30 dni.",
        )
    if receipt.registry_id != SOURCE_FACT_REGISTRY_ID:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_mismatch",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Użyj receiptu aktualnego WILQ source-fact registry.",
        )
    facts = ekologus_source_facts()
    if receipt.registry_digest != source_fact_registry_digest(facts):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_mismatch",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Odśwież exact source-fact registry receipt przed związaniem source packa.",
        )
    expected_evidence_ids = tuple(
        sorted(
            {
                APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
            }
        )
    )
    if receipt.evidence_ids != expected_evidence_ids:
        return _blocker(
            "source_fact_whitelist",
            "source_fact_registry_mismatch",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Dołącz exact evidence registry i zatwierdzonego manifestu źródeł.",
        )
    facts_by_id = {fact.source_id: fact for fact in facts}
    if set(command.source_fact_ids) - set(facts_by_id):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_not_registered",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Usuń fakty spoza exact source-fact registry; nie twórz ich z listy caller-a.",
        )
    if any(facts_by_id[item].review_status != "approved" for item in command.source_fact_ids):
        return _blocker(
            "source_fact_whitelist",
            "source_fact_not_approved",
            _known_evidence_ids(receipt.evidence_ids, None),
            "Użyj wyłącznie source facts ze statusem approved w aktualnym registry.",
        )
    return None


def _context_blocker(
    command: ContentSourcePackBindingCommand,
    identity: ContentDeliveryIdentityBinding,
    evidence: tuple[str, ...],
) -> ContentSourcePackBindingBlocker | None:
    attestation = command.fresh_context_attestation
    if attestation.checked_at > command.recorded_at:
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            _known_evidence_ids((*evidence, *attestation.evidence_ids), identity),
            "Context attestation nie może pochodzić z przyszłości względem zapisu.",
        )
    if command.recorded_at - attestation.checked_at > _MAX_RECEIPT_AGE:
        return _blocker(
            "fresh_context",
            "fresh_context_stale",
            _known_evidence_ids((*evidence, *attestation.evidence_ids), identity),
            "Odśwież context attestation w dozwolonym oknie 30 dni.",
        )
    if (
        attestation.source == "content_delivery_identity_binding"
        and attestation.run_id == identity.classification_run_id
        and attestation.evidence_ids == identity.inventory_evidence_ids
        and command.fresh_context_digest
        == content_source_pack_context_digest(identity, attestation)
    ):
        return None
    return _blocker(
        "fresh_context",
        "fresh_context_mismatch",
        _known_evidence_ids((*evidence, *attestation.evidence_ids), identity),
        ("Zapisz świeży context attestation z exact S1 identity, digestem, checked_at i evidence."),
    )


def _blocker(
    seam: ContentSourcePackBindingSeam,
    reason: ContentSourcePackBindingReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentSourcePackBindingBlocker:
    return ContentSourcePackBindingBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids)))[:256],
        next_step=next_step,
    )


def _payload(
    value: ContentSourcePackBinding | ContentSourcePackBindingCommand | dict[str, object],
) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return dict(value)


# Short aliases make the seam discoverable to callers that use the wording in
# the production plan while retaining the canonical SHA-256 field name.
source_pack_binding_digest = content_source_pack_binding_digest
source_pack_binding_logical_id = content_source_pack_binding_logical_id


__all__ = [
    "ContentSourcePackBinding",
    "ContentSourcePackBindingBlocker",
    "ContentSourcePackBindingCommand",
    "ContentSourceFactRegistryReceipt",
    "ContentSourcePackContextAttestation",
    "ContentSourcePackBindingRecordResult",
    "ContentSourcePackBindingReadResult",
    "ContentSourcePackBindingReason",
    "ContentSourcePackBindingSeam",
    "content_source_pack_binding_digest",
    "content_source_pack_binding_logical_id",
    "content_source_pack_context_digest",
    "reconcile_content_source_pack_binding",
    "source_pack_binding_digest",
    "source_pack_binding_logical_id",
    "source_fact_ids_digest",
    "source_fact_registry_digest",
    "evidence_ids_digest",
]
