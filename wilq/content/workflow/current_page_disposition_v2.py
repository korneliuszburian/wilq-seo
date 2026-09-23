"""Versioned local proposal and receipt contracts for a reviewed current page."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import (
    content_is_safe_public_url,
    content_normalized_path,
    content_normalized_url,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.schemas import ActionObject

_HEX64 = r"^[0-9a-f]{64}$"
CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE = "content_current_page_disposition_v2"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CurrentPageDispositionV2Snapshot(_FrozenModel):
    """Immutable evidence context attached to one semantic KEEP proposal."""

    schema_version: Literal["wilq_current_page_disposition_snapshot_v2"] = (
        "wilq_current_page_disposition_snapshot_v2"
    )
    work_item_id: str = Field(min_length=1, max_length=240)
    page_url: str = Field(min_length=1, max_length=2048)
    normalized_page_url: str = Field(min_length=1, max_length=2048)
    canonical_path: str = Field(min_length=1, max_length=2048)
    disposition: Literal["keep"] = "keep"
    generation_allowed: Literal[False] = False
    material_meaning_digest: str = Field(pattern=_HEX64)
    current_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    catalog_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    context_digest: str = Field(pattern=_HEX64)

    @field_validator("current_evidence_ids", "catalog_evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Current page disposition evidence IDs must be sorted and unique.")
        return value

    @model_validator(mode="after")
    def require_self_authenticating_context(self) -> Self:
        if (
            not content_is_safe_public_url(self.page_url)
            or self.normalized_page_url != content_normalized_url(self.page_url)
            or self.canonical_path != content_normalized_path(self.page_url)
        ):
            raise ValueError("Current page disposition v2 URL identity does not match.")
        if self.context_digest != current_page_disposition_v2_context_digest(self):
            raise ValueError("Current page disposition v2 context digest does not match.")
        return self


class CurrentPageDispositionV2Proposal(_FrozenModel):
    """Semantic identity plus the exact original evidence snapshot for a KEEP proposal."""

    schema_version: Literal["wilq_current_page_disposition_proposal_v2"] = (
        "wilq_current_page_disposition_proposal_v2"
    )
    proposal_id: str = Field(min_length=1, max_length=240)
    proposal_digest: str = Field(pattern=_HEX64)
    snapshot: CurrentPageDispositionV2Snapshot

    @model_validator(mode="after")
    def require_semantic_identity(self) -> Self:
        expected_digest = current_page_disposition_v2_proposal_digest(self.snapshot)
        if self.proposal_digest != expected_digest or self.proposal_id != (
            f"content_current_page_disposition_v2_{expected_digest}"
        ):
            raise ValueError("Current page disposition v2 proposal identity does not match.")
        return self


class CurrentPageDispositionV2Receipt(_FrozenModel):
    """Local lifecycle receipt fields; execution remains owned by the later lifecycle seam."""

    schema_version: Literal["wilq_current_page_disposition_receipt_v2"] = (
        "wilq_current_page_disposition_receipt_v2"
    )
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    generation_allowed: Literal[False] = False
    snapshot: CurrentPageDispositionV2Snapshot
    verification_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    verified_at: datetime
    preview_audit_id: str = Field(min_length=1, max_length=240)
    review_audit_id: str = Field(min_length=1, max_length=240)
    confirmation_audit_id: str = Field(min_length=1, max_length=240)
    impact_audit_id: str = Field(min_length=1, max_length=240)
    reviewed_by: str = Field(min_length=1, max_length=240)
    confirmed_by: str = Field(min_length=1, max_length=240)

    @field_validator("verification_evidence_ids")
    @classmethod
    def require_sorted_verification_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Verification evidence IDs must be sorted, unique and non-blank.")
        return value

    @model_validator(mode="after")
    def require_self_authenticating_receipt(self) -> Self:
        if self.verified_at.tzinfo is None or self.verified_at.utcoffset() is None:
            raise ValueError("verified_at must be timezone-aware.")
        expected = current_page_disposition_v2_receipt_digest(self)
        if self.receipt_digest != expected or self.receipt_id != (
            f"content_current_page_disposition_receipt_v2_{expected}"
        ):
            raise ValueError("Current page disposition v2 receipt digest does not match.")
        return self


def current_page_disposition_v2_context_digest(
    value: CurrentPageDispositionV2Snapshot | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("context_digest", None)
    return canonical_json_digest(payload)


def current_page_disposition_v2_proposal_digest(
    snapshot: CurrentPageDispositionV2Snapshot,
) -> str:
    """Hash semantic identity only; evidence rotation and timestamps do not affect it."""

    return canonical_json_digest(
        {
            "schema_version": "wilq_current_page_disposition_proposal_v2",
            "work_item_id": snapshot.work_item_id,
            "page_url": snapshot.page_url,
            "normalized_page_url": snapshot.normalized_page_url,
            "canonical_path": snapshot.canonical_path,
            "disposition": "keep",
            "material_meaning_digest": snapshot.material_meaning_digest,
        }
    )


def current_page_disposition_v2_receipt_digest(
    value: CurrentPageDispositionV2Receipt | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("receipt_id", None)
    payload.pop("receipt_digest", None)
    return canonical_json_digest(payload)


def build_current_page_disposition_v2_proposal(
    evidence: CurrentPageEvidenceResponse,
) -> CurrentPageDispositionV2Proposal:
    """Build a local KEEP proposal only from reviewed current material evidence."""

    accepted = CurrentPageEvidenceResponse.model_validate_json(
        evidence.model_dump_json(), strict=True
    )
    if accepted.status != "reviewed_material_current" or accepted.page_url is None:
        raise ValueError("A current page disposition requires reviewed current page material.")
    assert accepted.material_meaning_digest is not None
    provisional = {
        "schema_version": "wilq_current_page_disposition_snapshot_v2",
        "work_item_id": accepted.work_item_id,
        "page_url": accepted.page_url,
        "normalized_page_url": content_normalized_url(accepted.page_url),
        "canonical_path": content_normalized_path(accepted.page_url),
        "disposition": "keep",
        "generation_allowed": False,
        "material_meaning_digest": accepted.material_meaning_digest,
        "current_evidence_ids": tuple(sorted(set(accepted.current_evidence_ids))),
        "catalog_evidence_ids": tuple(sorted(set(accepted.catalog_evidence_ids))),
        "context_digest": "0" * 64,
    }
    snapshot = CurrentPageDispositionV2Snapshot.model_validate(
        provisional | {"context_digest": current_page_disposition_v2_context_digest(provisional)}
    )
    digest = current_page_disposition_v2_proposal_digest(snapshot)
    return CurrentPageDispositionV2Proposal(
        proposal_id=f"content_current_page_disposition_v2_{digest}",
        proposal_digest=digest,
        snapshot=snapshot,
    )


def build_current_page_disposition_v2_receipt(
    *,
    action: ActionObject,
    proposal: CurrentPageDispositionV2Proposal,
    preview_audit_id: str,
    review_audit_id: str,
    confirmation_audit_id: str,
    impact_audit_id: str,
    reviewed_by: str,
    confirmed_by: str,
    verification_evidence_ids: tuple[str, ...] | None = None,
    verified_at: datetime | None = None,
) -> CurrentPageDispositionV2Receipt:
    """Bind exact ActionObject identity and lifecycle audit references to the snapshot."""

    if action.id != proposal.proposal_id:
        raise ValueError(
            "Current page disposition v2 receipt must use its proposal ActionObject ID."
        )
    provisional = {
        "schema_version": "wilq_current_page_disposition_receipt_v2",
        "receipt_id": "",
        "receipt_digest": "0" * 64,
        "action_id": action.id,
        "action_payload_digest": canonical_json_digest(action.payload),
        "generation_allowed": False,
        "snapshot": proposal.snapshot.model_dump(mode="json"),
        "verification_evidence_ids": tuple(
            sorted(
                set(
                    verification_evidence_ids
                    if verification_evidence_ids is not None
                    else proposal.snapshot.current_evidence_ids
                    + proposal.snapshot.catalog_evidence_ids
                )
            )
        ),
        "verified_at": (verified_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        "preview_audit_id": preview_audit_id,
        "review_audit_id": review_audit_id,
        "confirmation_audit_id": confirmation_audit_id,
        "impact_audit_id": impact_audit_id,
        "reviewed_by": reviewed_by,
        "confirmed_by": confirmed_by,
    }
    digest = current_page_disposition_v2_receipt_digest(provisional)
    return CurrentPageDispositionV2Receipt.model_validate(
        provisional
        | {
            "receipt_id": f"content_current_page_disposition_receipt_v2_{digest}",
            "receipt_digest": digest,
        }
    )


__all__ = [
    "CURRENT_PAGE_DISPOSITION_V2_ACTION_TYPE",
    "CurrentPageDispositionV2Proposal",
    "CurrentPageDispositionV2Receipt",
    "CurrentPageDispositionV2Snapshot",
    "build_current_page_disposition_v2_proposal",
    "build_current_page_disposition_v2_receipt",
]
