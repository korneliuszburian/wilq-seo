"""Exact, append-only identity receipts for the content delivery pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    canonical_json_digest,
)

_HEX64 = r"^[0-9a-f]{64}$"
ContentDeliveryIdentitySeam = Literal[
    "canonical_identity",
    "classification_identity",
    "inventory_evidence",
    "retained_identity",
]
ContentDeliveryIdentityReason = Literal[
    "canonical_url_invalid",
    "canonical_path_mismatch",
    "classification_run_missing",
    "classification_run_mismatch",
    "classification_row_missing",
    "classification_row_ambiguous",
    "classification_row_mismatch",
    "inventory_evidence_digest_mismatch",
    "inventory_evidence_not_classified",
    "retained_identity_not_classified",
]
ContentDeliveryBlockerCode = Literal[
    "canonical_url_invalid",
    "canonical_path_mismatch",
    "classification_run_missing",
    "classification_run_mismatch",
    "classification_row_missing",
    "classification_row_ambiguous",
    "classification_row_mismatch",
    "inventory_evidence_digest_mismatch",
    "inventory_evidence_not_classified",
    "retained_identity_not_classified",
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentDeliveryIdentityCommand(_FrozenModel):
    """Caller-owned current identities; reconciliation policy stays inside this module."""

    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    current_work_item_id: str = Field(min_length=1, max_length=240)
    classification_run_id: str = Field(min_length=1, max_length=240)
    classification_run_digest: str = Field(pattern=_HEX64)
    classification_decision_set_digest: str = Field(pattern=_HEX64)
    classification_source_row_digest: str = Field(pattern=_HEX64)
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1)
    inventory_evidence_digest: str = Field(pattern=_HEX64)
    final_disposition: Literal["keep", "noindex", "redirect", "remove"]
    retained_work_item_id: str | None = Field(default=None, max_length=240)
    retained_usage: Literal["reuse", "history"] | None = None
    recorded_by: str = Field(min_length=1, max_length=160)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("inventory_evidence_ids")
    @classmethod
    def require_exact_evidence_set(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Inventory evidence IDs must be sorted, unique and non-blank.")
        return value

    @model_validator(mode="after")
    def require_explicit_retained_usage(self) -> Self:
        if (self.retained_work_item_id is None) != (self.retained_usage is None):
            raise ValueError("Retained identity requires an explicit reuse/history purpose.")
        if self.retained_work_item_id == self.current_work_item_id:
            raise ValueError("Retained identity must differ from the current work item.")
        return self


class ContentDeliveryIdentityBlocker(_FrozenModel):
    seam: ContentDeliveryIdentitySeam
    reason: ContentDeliveryIdentityReason
    evidence_ids: tuple[str, ...]
    next_step: str = Field(min_length=1)


class ContentDeliveryIdentityBinding(_FrozenModel):
    """One immutable result; it contains identities and digests, never source payloads."""

    schema_version: Literal["wilq_content_delivery_identity_v1"] = (
        "wilq_content_delivery_identity_v1"
    )
    binding_id: str = Field(min_length=1)
    binding_digest: str = Field(pattern=_HEX64)
    status: Literal["exact_current", "reconciled_retained", "blocked"]
    canonical_path: str = Field(min_length=1)
    public_url: str = Field(min_length=1)
    current_work_item_id: str = Field(min_length=1)
    retained_work_item_id: str | None = None
    retained_usage: Literal["reuse", "history"] | None = None
    classification_run_id: str = Field(min_length=1)
    classification_run_digest: str = Field(pattern=_HEX64)
    classification_decision_set_digest: str = Field(pattern=_HEX64)
    classification_source_row_digest: str = Field(pattern=_HEX64)
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1)
    inventory_evidence_digest: str = Field(pattern=_HEX64)
    final_disposition: Literal["keep", "noindex", "redirect", "remove"]
    blocker: ContentDeliveryIdentityBlocker | None = None
    recorded_by: str = Field(min_length=1)
    recorded_at: datetime

    @model_validator(mode="after")
    def require_self_authenticating_binding(self) -> Self:
        if (self.status == "blocked") != (self.blocker is not None):
            raise ValueError("Blocked identity state must carry exactly one typed blocker.")
        if self.status == "reconciled_retained" and self.retained_work_item_id is None:
            raise ValueError("Reconciled identity state requires an explicit retained owner.")
        if self.status == "exact_current" and self.retained_work_item_id is not None:
            raise ValueError("Exact-current identity cannot carry a retained owner.")
        expected = content_delivery_identity_digest(self)
        logical_id = content_delivery_identity_logical_id(self)
        if (
            self.binding_digest != expected
            or self.binding_id != f"content_delivery_identity_{logical_id[:24]}"
        ):
            raise ValueError("Content delivery identity ID/digest does not match its payload.")
        return self


class ContentDeliveryRecord(_FrozenModel):
    """Minimal runtime-owned state at the identity gate; later gates remain out of scope."""

    schema_version: Literal["wilq_content_delivery_record_v1"] = "wilq_content_delivery_record_v1"
    record_id: str = Field(min_length=1)
    record_digest: str = Field(pattern=_HEX64)
    binding_id: str = Field(min_length=1)
    binding_digest: str = Field(pattern=_HEX64)
    final_disposition: Literal["keep", "noindex", "redirect", "remove"]
    content_state: Literal["identity_bound", "identity_blocked"]
    delivery_status: Literal["not_started", "blocked"]
    robot_ready: Literal[False]
    gate_evidence_ids: tuple[str, ...]
    blocker_code: ContentDeliveryBlockerCode | None = None

    @model_validator(mode="after")
    def require_exact_gate_state(self) -> Self:
        blocked = self.content_state == "identity_blocked"
        if blocked != (self.delivery_status == "blocked") or blocked != (
            self.blocker_code is not None
        ):
            raise ValueError("Delivery record blocked state is inconsistent.")
        expected = canonical_json_digest(
            self.model_dump(mode="json", exclude={"record_id", "record_digest"})
        )
        if (
            self.record_digest != expected
            or self.record_id != f"content_delivery_record_{expected[:24]}"
        ):
            raise ValueError("Content delivery record ID/digest does not match its state.")
        return self


class ContentDeliveryClassificationLookup(_FrozenModel):
    run: ContentProductionClassificationProjection | None = None
    row_status: Literal["exact", "run_missing", "missing", "ambiguous"]

    @model_validator(mode="after")
    def require_lookup_shape(self) -> Self:
        if (self.row_status == "exact") != (self.run is not None):
            raise ValueError("Exact lookup state must carry exactly one row projection.")
        return self


class ContentDeliveryIdentityRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    binding: ContentDeliveryIdentityBinding
    delivery_record: ContentDeliveryRecord


def inventory_evidence_digest(evidence_ids: tuple[str, ...]) -> str:
    return canonical_json_digest({"inventory_evidence_ids": evidence_ids})


def content_delivery_identity_digest(
    value: ContentDeliveryIdentityBinding | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    for name in ("binding_id", "binding_digest", "recorded_by", "recorded_at"):
        payload.pop(name, None)
    return sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def content_delivery_identity_logical_id(
    value: ContentDeliveryIdentityBinding | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    return canonical_json_digest(
        {
            "canonical_path": payload["canonical_path"],
            "public_url": payload["public_url"],
            "current_work_item_id": payload["current_work_item_id"],
            "classification_run_id": payload["classification_run_id"],
        }
    )


def reconcile_content_delivery_identity(
    command: ContentDeliveryIdentityCommand,
    classification: ContentDeliveryClassificationLookup,
) -> ContentDeliveryIdentityBinding:
    """Resolve one exact identity without fuzzy, path-only, or implicit-latest fallback."""

    blocker = _identity_blocker(command, classification)
    status: Literal["exact_current", "reconciled_retained", "blocked"] = (
        "blocked"
        if blocker is not None
        else "reconciled_retained"
        if command.retained_work_item_id is not None
        else "exact_current"
    )
    command_payload = command.model_dump(mode="json")
    payload: dict[str, object] = {
        "schema_version": "wilq_content_delivery_identity_v1",
        "status": status,
        **{
            key: value
            for key, value in command_payload.items()
            if key not in {"recorded_by", "recorded_at"}
        },
        "blocker": None if blocker is None else blocker.model_dump(mode="json"),
        "recorded_by": command.recorded_by,
        "recorded_at": command_payload["recorded_at"],
    }
    digest = content_delivery_identity_digest(payload)
    logical_id = content_delivery_identity_logical_id(payload)
    return ContentDeliveryIdentityBinding.model_validate(
        {
            "binding_id": f"content_delivery_identity_{logical_id[:24]}",
            "binding_digest": digest,
            **payload,
        }
    )


def _identity_blocker(
    command: ContentDeliveryIdentityCommand,
    classification: ContentDeliveryClassificationLookup,
) -> ContentDeliveryIdentityBlocker | None:
    parsed = urlparse(command.public_url)
    evidence = command.inventory_evidence_ids
    if not content_is_safe_public_url(command.public_url) or parsed.query or parsed.fragment:
        return _blocker(
            "canonical_identity",
            "canonical_url_invalid",
            evidence,
            "Podaj exact bezpieczny publiczny URL bez query ani fragmentu.",
        )
    if content_normalized_path(command.public_url) != command.canonical_path:
        return _blocker(
            "canonical_identity",
            "canonical_path_mismatch",
            evidence,
            "Powiąż exact canonical path z tym samym publicznym URL-em.",
        )
    if classification.row_status != "exact":
        return _blocker(
            "classification_identity",
            (
                "classification_run_missing"
                if classification.row_status == "run_missing"
                else "classification_row_ambiguous"
                if classification.row_status == "ambiguous"
                else "classification_row_missing"
            ),
            (),
            "Wskaż klasyfikację zawierającą dokładnie jeden current work item.",
        )
    projection = classification.run
    if projection is None:
        raise ValueError("Exact classification lookup is missing its row projection.")
    if (
        projection.run_id != command.classification_run_id
        or projection.run_digest != command.classification_run_digest
        or projection.decision_set_digest != command.classification_decision_set_digest
    ):
        return _blocker(
            "classification_identity",
            "classification_run_mismatch",
            (),
            "Użyj exact run, run digest i decision-set digest z jednego persisted classification.",
        )
    row = projection.row
    if (
        row.current_work_item_id != command.current_work_item_id
        or row.canonical_path != command.canonical_path
        or row.public_url != command.public_url
        or row.source_packet_row_digest != command.classification_source_row_digest
    ):
        return _blocker(
            "classification_identity",
            "classification_row_mismatch",
            (*evidence, *row.primary_evidence_ids),
            "Ponownie zwiąż URL, work item i source-row digest z jednym exact classification row.",
        )
    if inventory_evidence_digest(evidence) != command.inventory_evidence_digest:
        return _blocker(
            "inventory_evidence",
            "inventory_evidence_digest_mismatch",
            evidence,
            "Przelicz digest uporządkowanego exact inventory evidence set.",
        )
    if not set(evidence).issubset(set(row.primary_evidence_ids) | set(row.lineage_evidence_ids)):
        return _blocker(
            "inventory_evidence",
            "inventory_evidence_not_classified",
            evidence,
            "Użyj inventory evidence jawnie zachowanego w classification row.",
        )
    if command.retained_work_item_id is not None and (
        row.decision != "reuse"
        or row.retained_binding is None
        or row.retained_work_item_id != command.retained_work_item_id
        or row.retained_binding.retained_work_item_id != command.retained_work_item_id
    ):
        return _blocker(
            "retained_identity",
            "retained_identity_not_classified",
            (*evidence, *row.lineage_evidence_ids),
            "Zachowaj retained ID tylko przez jawny reuse/history binding klasyfikacji.",
        )
    return None


def build_content_delivery_record(binding: ContentDeliveryIdentityBinding) -> ContentDeliveryRecord:
    blocked = binding.status == "blocked"
    evidence_ids = () if binding.blocker is None else binding.blocker.evidence_ids
    if not blocked:
        evidence_ids = binding.inventory_evidence_ids
    payload = {
        "schema_version": "wilq_content_delivery_record_v1",
        "binding_id": binding.binding_id,
        "binding_digest": binding.binding_digest,
        "final_disposition": binding.final_disposition,
        "content_state": "identity_blocked" if blocked else "identity_bound",
        "delivery_status": "blocked" if blocked else "not_started",
        "robot_ready": False,
        "gate_evidence_ids": tuple(sorted(set(evidence_ids))),
        "blocker_code": None if binding.blocker is None else binding.blocker.reason,
    }
    digest = canonical_json_digest(payload)
    return ContentDeliveryRecord.model_validate(
        {
            "record_id": f"content_delivery_record_{digest[:24]}",
            "record_digest": digest,
            **payload,
        }
    )


def _blocker(
    seam: ContentDeliveryIdentitySeam,
    reason: ContentDeliveryIdentityReason,
    evidence_ids: tuple[str, ...],
    next_step: str,
) -> ContentDeliveryIdentityBlocker:
    return ContentDeliveryIdentityBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step=next_step,
    )


__all__ = [
    "ContentDeliveryClassificationLookup",
    "ContentDeliveryIdentityBinding",
    "ContentDeliveryIdentityBlocker",
    "ContentDeliveryIdentityCommand",
    "ContentDeliveryIdentityRecordResult",
    "ContentDeliveryRecord",
    "build_content_delivery_record",
    "inventory_evidence_digest",
    "reconcile_content_delivery_identity",
]
