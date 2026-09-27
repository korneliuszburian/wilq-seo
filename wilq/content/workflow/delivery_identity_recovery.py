"""Typed read-only operator recovery for a drifted delivery identity binding."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    ContentDeliveryIdentityBinding,
    build_content_delivery_identity_current_projection,
)
from wilq.schemas.core import utc_now

_HEX64 = r"^[0-9a-f]{64}$"
CURRENT_SAFE_NEXT_STEP = "Exact current identity jest dostępna dla następnego kroku."
DRIFT_SAFE_NEXT_STEP = (
    "Zarejestruj nową exact current identity dla tego bieżącego wiersza klasyfikacji."
)
CLASSIFICATION_MISSING_SAFE_NEXT_STEP = (
    "Odśwież bieżącą exact klasyfikację, a potem zarejestruj nową identity."
)


class ContentDeliveryIdentityDriftRecovery(BaseModel):
    """What the binding packed versus the exact current classification row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_delivery_identity_drift_recovery"] = (
        "content_delivery_identity_drift_recovery"
    )
    contract_version: Literal["content_delivery_identity_drift_recovery_v1"] = (
        "content_delivery_identity_drift_recovery_v1"
    )
    binding_id: str = Field(min_length=1, max_length=240)
    status: Literal["current", "drift", "classification_missing"]
    binding_classification_run_id: str | None = Field(default=None, max_length=240)
    binding_classification_run_digest: str | None = Field(default=None, pattern=_HEX64)
    binding_classification_source_row_digest: str | None = Field(default=None, pattern=_HEX64)
    current_work_item_id: str | None = Field(default=None, max_length=240)
    current_classification_run_id: str | None = Field(default=None, max_length=240)
    current_classification_run_digest: str | None = Field(default=None, pattern=_HEX64)
    current_classification_source_row_digest: str | None = Field(
        default=None, pattern=_HEX64
    )
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_typed_recovery(self) -> ContentDeliveryIdentityDriftRecovery:
        current_fields = (
            self.current_work_item_id,
            self.current_classification_run_id,
            self.current_classification_run_digest,
            self.current_classification_source_row_digest,
        )
        if self.status == "drift":
            if any(value is None for value in current_fields):
                raise ValueError("Drifted recovery needs the exact current row identity.")
        elif any(value is not None for value in current_fields):
            raise ValueError("Only a drifted identity exposes a current row identity.")
        return self


def build_content_delivery_identity_drift_recovery(
    binding: ContentDeliveryIdentityBinding,
    classification: ContentDeliveryClassificationLookup,
) -> ContentDeliveryIdentityDriftRecovery:
    """Never reports a drifted binding as usable; always names the current row."""

    projection = build_content_delivery_identity_current_projection(
        binding, classification, assessed_at=utc_now()
    )
    if projection.current_status == "exact_current":
        return ContentDeliveryIdentityDriftRecovery(
            binding_id=binding.binding_id,
            status="current",
            binding_classification_run_id=binding.classification_run_id,
            binding_classification_run_digest=binding.classification_run_digest,
            binding_classification_source_row_digest=binding.classification_source_row_digest,
            safe_next_step=CURRENT_SAFE_NEXT_STEP,
        )
    blocker = projection.current_blocker
    run = classification.run
    if classification.row_status != "exact" or run is None:
        return ContentDeliveryIdentityDriftRecovery(
            binding_id=binding.binding_id,
            status="classification_missing",
            binding_classification_run_id=binding.classification_run_id,
            binding_classification_run_digest=binding.classification_run_digest,
            binding_classification_source_row_digest=binding.classification_source_row_digest,
            safe_next_step=CLASSIFICATION_MISSING_SAFE_NEXT_STEP,
        )
    return ContentDeliveryIdentityDriftRecovery(
        binding_id=binding.binding_id,
        status="drift",
        binding_classification_run_id=binding.classification_run_id,
        binding_classification_run_digest=binding.classification_run_digest,
        binding_classification_source_row_digest=binding.classification_source_row_digest,
        current_work_item_id=run.row.current_work_item_id,
        current_classification_run_id=run.run_id,
        current_classification_run_digest=run.run_digest,
        current_classification_source_row_digest=run.row.source_packet_row_digest,
        safe_next_step=(
            DRIFT_SAFE_NEXT_STEP
            if blocker is not None and blocker.reason == "identity_classification_drift"
            else blocker.next_step
            if blocker is not None
            else DRIFT_SAFE_NEXT_STEP
        ),
    )


__all__ = [
    "CLASSIFICATION_MISSING_SAFE_NEXT_STEP",
    "CURRENT_SAFE_NEXT_STEP",
    "DRIFT_SAFE_NEXT_STEP",
    "ContentDeliveryIdentityDriftRecovery",
    "build_content_delivery_identity_drift_recovery",
]
