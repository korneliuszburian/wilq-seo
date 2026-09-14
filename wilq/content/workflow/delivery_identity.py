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
    ContentProductionRegisteredInventoryReceipt,
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
    "classification_not_current",
    "classification_run_mismatch",
    "classification_row_missing",
    "classification_row_ambiguous",
    "classification_row_mismatch",
    "inventory_evidence_digest_mismatch",
    "inventory_evidence_not_classified",
    "retained_identity_not_classified",
    "identity_classification_drift",
]
ContentDeliveryBlockerCode = Literal[
    "canonical_url_invalid",
    "canonical_path_mismatch",
    "classification_run_missing",
    "classification_not_current",
    "classification_run_mismatch",
    "classification_row_missing",
    "classification_row_ambiguous",
    "classification_row_mismatch",
    "inventory_evidence_digest_mismatch",
    "inventory_evidence_not_classified",
    "retained_identity_not_classified",
    "identity_classification_drift",
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
    inventory_receipt_id: str | None = Field(default=None, max_length=240)
    inventory_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    inventory_catalog_id: str | None = Field(default=None, max_length=240)
    inventory_catalog_item_digest: str | None = Field(default=None, pattern=_HEX64)
    inventory_catalog_snapshot_digest: str | None = Field(default=None, pattern=_HEX64)
    inventory_catalog_snapshot_evidence_ids: tuple[str, ...] = ()
    inventory_receipt: ContentProductionRegisteredInventoryReceipt | None = None
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

    @field_validator("inventory_catalog_snapshot_evidence_ids")
    @classmethod
    def require_exact_receipt_evidence_set(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError(
                "Registered inventory receipt evidence IDs must be sorted, unique and non-blank."
            )
        return value

    @model_validator(mode="after")
    def require_explicit_retained_usage(self) -> Self:
        receipt_values = (
            self.inventory_receipt_id,
            self.inventory_receipt_digest,
            self.inventory_catalog_id,
            self.inventory_catalog_item_digest,
            self.inventory_catalog_snapshot_digest,
        )
        metadata_present = any(value is not None for value in receipt_values)
        if metadata_present and (
            not all(value is not None for value in receipt_values)
            or not self.inventory_catalog_snapshot_evidence_ids
        ):
            raise ValueError("Registered inventory receipt metadata must be complete.")
        if not metadata_present and self.inventory_catalog_snapshot_evidence_ids:
            raise ValueError("Registered inventory receipt metadata must be complete.")
        if metadata_present and (
            self.inventory_catalog_snapshot_evidence_ids != self.inventory_evidence_ids
        ):
            raise ValueError("Registered inventory receipt evidence must match identity evidence.")
        if self.inventory_receipt is not None and (
            not metadata_present
            or self.inventory_receipt_id != self.inventory_receipt.receipt_id
            or self.inventory_receipt_digest != self.inventory_receipt.receipt_digest
            or self.inventory_catalog_id != self.inventory_receipt.catalog_id
            or self.inventory_catalog_item_digest != self.inventory_receipt.catalog_item_digest
            or self.inventory_catalog_snapshot_digest
            != self.inventory_receipt.catalog_snapshot_digest
            or self.inventory_catalog_snapshot_evidence_ids
            != self.inventory_receipt.catalog_snapshot_evidence_ids
        ):
            raise ValueError("Registered inventory receipt does not match identity metadata.")
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
    inventory_receipt_id: str | None = Field(default=None, max_length=240)
    inventory_receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    inventory_catalog_id: str | None = Field(default=None, max_length=240)
    inventory_catalog_item_digest: str | None = Field(default=None, pattern=_HEX64)
    inventory_catalog_snapshot_digest: str | None = Field(default=None, pattern=_HEX64)
    inventory_catalog_snapshot_evidence_ids: tuple[str, ...] = ()
    inventory_receipt: ContentProductionRegisteredInventoryReceipt | None = None
    blocker: ContentDeliveryIdentityBlocker | None = None
    recorded_by: str = Field(min_length=1)
    recorded_at: datetime

    @field_validator("inventory_catalog_snapshot_evidence_ids")
    @classmethod
    def require_exact_receipt_evidence_set(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError(
                "Registered inventory receipt evidence IDs must be sorted, unique and non-blank."
            )
        return value

    @model_validator(mode="after")
    def require_self_authenticating_binding(self) -> Self:
        if (self.status == "blocked") != (self.blocker is not None):
            raise ValueError("Blocked identity state must carry exactly one typed blocker.")
        if self.status == "reconciled_retained" and self.retained_work_item_id is None:
            raise ValueError("Reconciled identity state requires an explicit retained owner.")
        if self.status == "exact_current" and self.retained_work_item_id is not None:
            raise ValueError("Exact-current identity cannot carry a retained owner.")
        receipt_values = (
            self.inventory_receipt_id,
            self.inventory_receipt_digest,
            self.inventory_catalog_id,
            self.inventory_catalog_item_digest,
            self.inventory_catalog_snapshot_digest,
        )
        metadata_present = any(value is not None for value in receipt_values)
        if metadata_present and (
            not all(value is not None for value in receipt_values)
            or not self.inventory_catalog_snapshot_evidence_ids
        ):
            raise ValueError("Registered inventory receipt metadata must be complete.")
        if not metadata_present and self.inventory_catalog_snapshot_evidence_ids:
            raise ValueError("Registered inventory receipt metadata must be complete.")
        if metadata_present and (
            self.inventory_catalog_snapshot_evidence_ids != self.inventory_evidence_ids
        ):
            raise ValueError("Registered inventory receipt evidence must match identity evidence.")
        if self.inventory_receipt is not None and (
            not metadata_present
            or self.inventory_receipt_id != self.inventory_receipt.receipt_id
            or self.inventory_receipt_digest != self.inventory_receipt.receipt_digest
            or self.inventory_catalog_id != self.inventory_receipt.catalog_id
            or self.inventory_catalog_item_digest != self.inventory_receipt.catalog_item_digest
            or self.inventory_catalog_snapshot_digest
            != self.inventory_receipt.catalog_snapshot_digest
            or self.inventory_catalog_snapshot_evidence_ids
            != self.inventory_receipt.catalog_snapshot_evidence_ids
        ):
            raise ValueError("Registered inventory receipt does not match identity metadata.")
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
    row_status: Literal["exact", "run_missing", "missing", "ambiguous", "not_current"]

    @model_validator(mode="after")
    def require_lookup_shape(self) -> Self:
        if (self.row_status == "exact") != (self.run is not None):
            raise ValueError("Exact lookup state must carry exactly one row projection.")
        return self


class ContentDeliveryIdentityRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    binding: ContentDeliveryIdentityBinding
    delivery_record: ContentDeliveryRecord
    current: ContentDeliveryIdentityCurrentProjection

    @model_validator(mode="after")
    def require_current_binding(self) -> Self:
        if self.current.recorded_binding != self.binding:
            raise ValueError("Current identity projection must reference its recorded binding.")
        return self


class ContentDeliveryIdentityCurrentProjection(_FrozenModel):
    """Current read assessment over one immutable delivery identity binding."""

    response_type: Literal["content_delivery_identity_current_projection"] = (
        "content_delivery_identity_current_projection"
    )
    contract_version: Literal["content_delivery_identity_current_projection_v1"] = (
        "content_delivery_identity_current_projection_v1"
    )
    recorded_binding: ContentDeliveryIdentityBinding
    recorded_status: Literal["exact_current", "reconciled_retained", "blocked"]
    assessed_at: datetime
    current_status: Literal["exact_current", "blocked"]
    current_blocker: ContentDeliveryIdentityBlocker | None = None
    current_safe_next_step: str = Field(min_length=1)

    @field_validator("assessed_at")
    @classmethod
    def require_aware_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Identity projection assessment time must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_current_state(self) -> Self:
        if self.recorded_status != self.recorded_binding.status:
            raise ValueError("Identity projection recorded status must match its binding.")
        if (self.current_status == "blocked") != (self.current_blocker is not None):
            raise ValueError("Blocked current identity requires exactly one typed blocker.")
        if self.current_status == "exact_current" and self.recorded_status != "exact_current":
            raise ValueError("Only exact-current recorded identity may be currently exact.")
        if self.current_blocker is not None and (
            self.current_safe_next_step != self.current_blocker.next_step
        ):
            raise ValueError("Current identity safe next step must match its blocker.")
        return self


def build_content_delivery_identity_current_projection(
    binding: ContentDeliveryIdentityBinding,
    classification: ContentDeliveryClassificationLookup,
    *,
    assessed_at: datetime,
) -> ContentDeliveryIdentityCurrentProjection:
    """Compare an immutable binding with the latest nonhistorical classification."""

    blocker: ContentDeliveryIdentityBlocker | None = None
    if binding.status != "exact_current":
        blocker = binding.blocker or _blocker(
            "classification_identity",
            "identity_classification_drift",
            binding.inventory_evidence_ids,
            "Zarejestruj nową exact current identity po potwierdzeniu klasyfikacji.",
        )
    elif classification.row_status != "exact":
        blocker = _current_classification_blocker(binding, classification)
    elif classification.run is None:
        raise ValueError("Exact classification lookup is missing its row projection.")
    elif not _binding_matches_current_classification(binding, classification.run):
        blocker = _blocker(
            "classification_identity",
            "identity_classification_drift",
            binding.inventory_evidence_ids,
            "Odśwież exact S1/classification context przed kolejnym krokiem.",
        )
    return ContentDeliveryIdentityCurrentProjection(
        recorded_binding=binding,
        recorded_status=binding.status,
        assessed_at=assessed_at,
        current_status="blocked" if blocker is not None else "exact_current",
        current_blocker=blocker,
        current_safe_next_step=(
            blocker.next_step
            if blocker is not None
            else "Exact current identity jest dostępna dla następnego kroku."
        ),
    )


def _current_classification_blocker(
    binding: ContentDeliveryIdentityBinding,
    classification: ContentDeliveryClassificationLookup,
) -> ContentDeliveryIdentityBlocker:
    if classification.row_status == "run_missing":
        reason: ContentDeliveryIdentityReason = "classification_run_missing"
    elif classification.row_status == "not_current":
        reason = "classification_not_current"
    elif classification.row_status == "missing":
        reason = "classification_row_missing"
    elif classification.row_status == "ambiguous":
        reason = "classification_row_ambiguous"
    else:
        reason = "identity_classification_drift"
    return _blocker(
        "classification_identity",
        reason,
        () if reason != "identity_classification_drift" else binding.inventory_evidence_ids,
        "Odśwież bieżącą exact classification przed kolejnym krokiem.",
    )


def _binding_matches_current_classification(
    binding: ContentDeliveryIdentityBinding,
    classification: ContentProductionClassificationProjection,
) -> bool:
    row = classification.row
    available_evidence = set(row.primary_evidence_ids) | set(row.lineage_evidence_ids)
    registered_receipt = row.source_receipt
    receipt_matches = (
        not isinstance(registered_receipt, ContentProductionRegisteredInventoryReceipt)
        or (
            binding.inventory_receipt == registered_receipt
            and binding.inventory_receipt_id == registered_receipt.receipt_id
            and binding.inventory_receipt_digest == registered_receipt.receipt_digest
            and binding.inventory_catalog_id == registered_receipt.catalog_id
            and binding.inventory_catalog_item_digest == registered_receipt.catalog_item_digest
            and binding.inventory_catalog_snapshot_digest
            == registered_receipt.catalog_snapshot_digest
            and binding.inventory_catalog_snapshot_evidence_ids
            == registered_receipt.catalog_snapshot_evidence_ids
        )
    )
    return all(
        (
            classification.run_id == binding.classification_run_id,
            classification.run_digest == binding.classification_run_digest,
            classification.decision_set_digest == binding.classification_decision_set_digest,
            classification.freshness.state == "fresh",
            classification.freshness.requires_refresh is False,
            row.current_work_item_id == binding.current_work_item_id,
            row.canonical_path == binding.canonical_path,
            row.public_url == binding.public_url,
            row.source_packet_row_digest == binding.classification_source_row_digest,
            inventory_evidence_digest(binding.inventory_evidence_ids)
            == binding.inventory_evidence_digest,
            set(binding.inventory_evidence_ids).issubset(available_evidence),
            receipt_matches,
        )
    )


def inventory_evidence_digest(evidence_ids: tuple[str, ...]) -> str:
    return canonical_json_digest({"inventory_evidence_ids": evidence_ids})


def content_delivery_identity_digest(
    value: ContentDeliveryIdentityBinding | dict[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    for name in ("binding_id", "binding_digest", "recorded_by", "recorded_at"):
        payload.pop(name, None)
    # Keep the pre-receipt binding digest stable for legacy rows that never
    # carried registered-inventory metadata.  New authority bindings retain
    # all metadata in their digest.
    receipt_metadata = (
        "inventory_receipt_id",
        "inventory_receipt_digest",
        "inventory_catalog_id",
        "inventory_catalog_item_digest",
        "inventory_catalog_snapshot_digest",
        "inventory_catalog_snapshot_evidence_ids",
        "inventory_receipt",
    )
    if not any(payload.get(name) not in (None, [], ()) for name in receipt_metadata):
        for name in receipt_metadata:
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
                else "classification_not_current"
                if classification.row_status == "not_current"
                else "classification_row_ambiguous"
                if classification.row_status == "ambiguous"
                else "classification_row_missing"
            ),
            (),
            (
                "Wskaż current-acceptance classification; historical reference nie może być "
                "źródłem identity."
                if classification.row_status == "not_current"
                else "Wskaż klasyfikację zawierającą dokładnie jeden current work item."
            ),
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
    receipt = row.source_receipt
    if isinstance(receipt, ContentProductionRegisteredInventoryReceipt) and (
        command.inventory_receipt_id is None
    ):
        return _blocker(
            "inventory_evidence",
            "inventory_evidence_not_classified",
            evidence,
            "Użyj exact registered inventory receipt z bieżącego classification row.",
        )
    if command.inventory_receipt_id is not None:
        if not isinstance(receipt, ContentProductionRegisteredInventoryReceipt):
            return _blocker(
                "inventory_evidence",
                "inventory_evidence_not_classified",
                evidence,
                "Użyj exact registered inventory receipt z bieżącego classification row.",
            )
        if (
            command.inventory_receipt_id != receipt.receipt_id
            or command.inventory_receipt_digest != receipt.receipt_digest
            or command.inventory_catalog_id != receipt.catalog_id
            or command.inventory_catalog_item_digest != receipt.catalog_item_digest
            or command.inventory_catalog_snapshot_digest != receipt.catalog_snapshot_digest
            or command.inventory_catalog_snapshot_evidence_ids
            != receipt.catalog_snapshot_evidence_ids
            or command.inventory_receipt != receipt
        ):
            return _blocker(
                "inventory_evidence",
                "inventory_evidence_not_classified",
                evidence,
                "Użyj exact registered inventory receipt z bieżącego classification row.",
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
    "ContentDeliveryIdentityCurrentProjection",
    "ContentDeliveryIdentityRecordResult",
    "build_content_delivery_identity_current_projection",
    "ContentDeliveryRecord",
    "build_content_delivery_record",
    "inventory_evidence_digest",
    "reconcile_content_delivery_identity",
]
