"""One exact, append-only verification receipt for current content inputs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    canonical_json_digest,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.source_pack_binding import ContentSourcePackBinding

_HEX64 = r"^[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentCurrentVerificationCommand(_FrozenModel):
    identity_binding_id: str = Field(min_length=1)
    identity_binding_digest: str = Field(pattern=_HEX64)
    source_pack_binding_id: str = Field(min_length=1)
    source_pack_binding_digest: str = Field(pattern=_HEX64)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=_HEX64)
    review_decision_id: str = Field(min_length=1)
    wordpress_draft_binding: ContentDraftRevisionBinding
    action_id: str = Field(min_length=1)
    mutation_audit_id: str = Field(min_length=1)
    recorded_by: str = Field(min_length=1, max_length=160)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware.")
        return value.astimezone(UTC)


class ContentCurrentVerificationBlocker(_FrozenModel):
    seam: Literal[
        "classification",
        "delivery_identity",
        "source_pack",
        "revision_review",
        "wordpress_readback",
    ]
    reason: str = Field(min_length=1)


class ContentCurrentVerification(_FrozenModel):
    verification_id: str = Field(min_length=1)
    verification_digest: str = Field(pattern=_HEX64)
    status: Literal["verified", "blocked"]
    identity_binding_id: str = Field(min_length=1)
    identity_binding_digest: str = Field(pattern=_HEX64)
    source_pack_binding_id: str = Field(min_length=1)
    source_pack_binding_digest: str = Field(pattern=_HEX64)
    classification_run_id: str = Field(min_length=1)
    classification_run_digest: str = Field(pattern=_HEX64)
    classification_source_row_digest: str = Field(pattern=_HEX64)
    canonical_path: str = Field(min_length=1)
    public_url: str = Field(min_length=1)
    current_work_item_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    revision_digest: str = Field(pattern=_HEX64)
    review_decision_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    mutation_audit_id: str = Field(min_length=1)
    handoff_id: str = Field(min_length=1)
    approval_decision_id: str = Field(min_length=1)
    blocker: ContentCurrentVerificationBlocker | None = None
    recorded_by: str = Field(min_length=1)
    recorded_at: datetime

    @model_validator(mode="after")
    def require_self_authenticating_state(self) -> Self:
        if (self.status == "blocked") != (self.blocker is not None):
            raise ValueError("Blocked verification requires exactly one typed blocker.")
        payload = self.model_dump(mode="json")
        for name in ("verification_id", "verification_digest", "recorded_by", "recorded_at"):
            payload.pop(name)
        expected = canonical_json_digest(payload)
        if (
            self.verification_digest != expected
            or self.verification_id != f"content_current_verification_{expected[:24]}"
        ):
            raise ValueError("Verification ID/digest does not match its payload.")
        return self


class ContentCurrentVerificationRecordResult(_FrozenModel):
    status: Literal["created", "idempotent", "conflict"]
    verification: ContentCurrentVerification


def reconcile_current_verification(
    command: ContentCurrentVerificationCommand,
    *,
    classification: ContentProductionClassificationProjection | None,
    identity: ContentDeliveryIdentityBinding | None,
    source_pack: ContentSourcePackBinding | None,
    review_matches: bool,
    exact_readback_matches: bool,
) -> ContentCurrentVerification:
    """Reconcile exact supplied IDs only; callers own all lookups and no fallback exists."""

    blocker = _blocker(
        command,
        classification,
        identity,
        source_pack,
        review_matches,
        exact_readback_matches,
    )
    values = {
        "identity_binding_id": command.identity_binding_id,
        "identity_binding_digest": command.identity_binding_digest,
        "source_pack_binding_id": command.source_pack_binding_id,
        "source_pack_binding_digest": command.source_pack_binding_digest,
        "classification_run_id": "missing" if classification is None else classification.run_id,
        "classification_run_digest": (
            "0" * 64 if classification is None else classification.run_digest
        ),
        "classification_source_row_digest": (
            "0" * 64 if classification is None else classification.row.source_packet_row_digest
        ),
        "canonical_path": (
            "missing" if classification is None else classification.row.canonical_path
        ),
        "public_url": "missing" if classification is None else classification.row.public_url,
        "current_work_item_id": (
            "missing"
            if classification is None
            else classification.row.current_work_item_id or "missing"
        ),
        "revision_id": command.revision_id,
        "revision_digest": command.revision_digest,
        "review_decision_id": command.review_decision_id,
        "action_id": command.action_id,
        "mutation_audit_id": command.mutation_audit_id,
        "handoff_id": command.wordpress_draft_binding.handoff_id,
        "approval_decision_id": command.wordpress_draft_binding.approval_decision_id,
        "status": "blocked" if blocker else "verified",
        "blocker": None if blocker is None else blocker.model_dump(mode="json"),
    }
    digest = canonical_json_digest(values)
    return ContentCurrentVerification.model_validate(
        {
            "verification_id": f"content_current_verification_{digest[:24]}",
            "verification_digest": digest,
            "recorded_by": command.recorded_by,
            "recorded_at": command.recorded_at,
            **values,
        }
    )


def _blocker(
    command: ContentCurrentVerificationCommand,
    classification: ContentProductionClassificationProjection | None,
    identity: ContentDeliveryIdentityBinding | None,
    source_pack: ContentSourcePackBinding | None,
    review_matches: bool,
    exact_readback_matches: bool,
) -> ContentCurrentVerificationBlocker | None:
    if classification is None or classification.row.current_work_item_id is None:
        return ContentCurrentVerificationBlocker(
            seam="classification", reason="current_row_missing"
        )
    if identity is None or (
        identity.binding_id != command.identity_binding_id
        or identity.binding_digest != command.identity_binding_digest
        or identity.status != "exact_current"
        or identity.classification_run_id != classification.run_id
        or identity.classification_run_digest != classification.run_digest
        or identity.classification_source_row_digest != classification.row.source_packet_row_digest
        or identity.canonical_path != classification.row.canonical_path
        or identity.public_url != classification.row.public_url
        or identity.current_work_item_id != classification.row.current_work_item_id
    ):
        return ContentCurrentVerificationBlocker(
            seam="delivery_identity", reason="identity_mismatch"
        )
    if (
        command.wordpress_draft_binding.work_item_id != identity.current_work_item_id
        or command.wordpress_draft_binding.revision_id != command.revision_id
        or command.wordpress_draft_binding.content_digest != command.revision_digest
    ):
        return ContentCurrentVerificationBlocker(
            seam="revision_review", reason="revision_binding_mismatch"
        )
    if source_pack is None or (
        source_pack.binding_id != command.source_pack_binding_id
        or source_pack.binding_digest != command.source_pack_binding_digest
        or source_pack.status != "exact_current"
        or source_pack.identity_binding_id != identity.binding_id
        or source_pack.identity_binding_digest != identity.binding_digest
        or source_pack.current_work_item_id != identity.current_work_item_id
        or not set(classification.row.primary_evidence_ids).issubset(source_pack.evidence_ids)
        or not set(classification.row.source_connectors).issubset(
            classification.freshness.connector_ids
        )
    ):
        return ContentCurrentVerificationBlocker(seam="source_pack", reason="source_pack_mismatch")
    if not review_matches:
        return ContentCurrentVerificationBlocker(seam="revision_review", reason="review_mismatch")
    if not exact_readback_matches:
        return ContentCurrentVerificationBlocker(
            seam="wordpress_readback", reason="readback_mismatch"
        )
    return None


__all__ = [
    "ContentCurrentVerification",
    "ContentCurrentVerificationBlocker",
    "ContentCurrentVerificationCommand",
    "ContentCurrentVerificationRecordResult",
    "reconcile_current_verification",
]
