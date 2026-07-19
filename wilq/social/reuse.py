from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.social.history import SocialHistoryInventory

SocialReusePlatform = Literal["linkedin", "facebook"]
SocialReuseStatus = Literal["review_required", "approved", "rejected", "stale", "blocked"]
SocialReuseReviewDecision = Literal["approved", "needs_changes", "rejected"]


class SocialReuseProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    expected_revision_id: str = Field(min_length=1)
    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform: SocialReusePlatform
    audience: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    body: str = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    measurement_hypothesis: str = Field(min_length=1)

    @field_validator("audience", "angle", "body", "measurement_hypothesis")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Social reuse fields cannot be blank.")
        return value.strip()


class SocialReuseRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    audience: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    body: str = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    measurement_hypothesis: str = Field(min_length=1)

    @field_validator("audience", "angle", "body", "measurement_hypothesis")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Social reuse revision fields cannot be blank.")
        return value.strip()


class SocialReuseProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["social_reuse_proposal_v1"] = "social_reuse_proposal_v1"
    proposal_id: str = Field(min_length=1)
    parent_proposal_id: str | None = None
    proposal_number: int = Field(default=1, ge=1)
    work_item_id: str = Field(min_length=1)
    platform: SocialReusePlatform
    source_revision_id: str = Field(min_length=1)
    source_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_evidence_ids: list[str] = Field(min_length=1)
    source_claim_ids: list[str] = Field(default_factory=list)
    audience: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    body: str = Field(min_length=1)
    constraints: list[str] = Field(min_length=1)
    duplicate_risk_inventory_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    duplicate_risk_evidence_ids: list[str] = Field(default_factory=list)
    duplicate_risk_status: Literal["review_ready"] = "review_ready"
    measurement_hypothesis: str = Field(min_length=1)
    status: SocialReuseStatus = "review_required"
    publish_allowed: Literal[False] = False
    created_at: datetime
    proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class SocialReuseProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["created", "blocked", "stale"]
    proposal: SocialReuseProposal | None = None
    review: SocialReuseReview | None = None
    blocker: str | None = None
    next_step: str


class SocialReuseProposalListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[SocialReuseProposalResponse]
    next_step: str


class SocialReuseReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_by: str = Field(min_length=1)
    decision: SocialReuseReviewDecision
    notes: str = ""
    checked_items: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)

    @field_validator("reviewed_by", "notes")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("checked_items", "evidence_ids")
    @classmethod
    def normalize_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if not normalized:
            raise ValueError("Review requires checked items and evidence IDs.")
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def require_change_reason(self) -> SocialReuseReviewRequest:
        if self.decision != "approved" and not self.notes:
            raise ValueError("Review requiring changes or rejection needs notes.")
        return self


class SocialReuseReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["social_reuse_review_v1"] = "social_reuse_review_v1"
    review_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_number: int = Field(ge=1)
    decision: SocialReuseReviewDecision
    reviewed_by: str = Field(min_length=1)
    notes: str = ""
    checked_items: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    created_at: datetime


SocialReuseProposalResponse.model_rebuild()


class SocialReuseReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["recorded", "idempotent", "blocked", "stale"]
    proposal: SocialReuseProposal | None = None
    review: SocialReuseReview | None = None
    blocker: str | None = None
    next_step: str


def social_history_inventory_digest(inventory: SocialHistoryInventory) -> str:
    payload = inventory.model_dump(mode="json")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def build_social_reuse_proposal(
    request: SocialReuseProposalRequest,
    revision: ContentDraftRevision,
    inventory: SocialHistoryInventory,
    *,
    now: datetime,
    parent_proposal_id: str | None = None,
    proposal_number: int = 1,
) -> SocialReuseProposal:
    source_evidence_ids = sorted(
        {
            evidence_id
            for section in revision.sections
            for evidence_id in section.evidence_ids
        }
        | {
            evidence_id
            for item in revision.faq
            for evidence_id in item.evidence_ids
        }
        | {
            evidence_id
            for item in revision.cta_blocks
            for evidence_id in item.evidence_ids
        }
        | {
            evidence_id
            for item in revision.internal_links
            for evidence_id in item.evidence_ids
        }
    )
    if not source_evidence_ids:
        raise ValueError("Social reuse requires source evidence from the revision.")
    allowed_claim_ids = {
        claim_id
        for section in revision.sections
        for claim_id in section.claim_ids
    } | {
        claim_id
        for item in revision.faq
        for claim_id in item.claim_ids
    } | {
        claim_id
        for item in revision.cta_blocks
        for claim_id in item.claim_ids
    }
    if any(claim_id not in allowed_claim_ids for claim_id in request.claim_ids):
        raise ValueError("Social reuse claim_ids must belong to the source revision.")
    if not inventory.source_evidence_ids:
        raise ValueError("Social reuse requires reviewed social history evidence.")
    proposal_id = f"social_reuse_{request.platform}_{request.expected_revision_id}"
    if parent_proposal_id is not None:
        proposal_id += f"_child_{proposal_number}"
    constraints = [
        "review_only",
        "no_vendor_publish",
        "use_only_declared_revision_lineage",
        "human_review_before_apply",
    ]
    payload = {
        "contract": "social_reuse_proposal_v1",
        "proposal_id": proposal_id,
        "parent_proposal_id": parent_proposal_id,
        "proposal_number": proposal_number,
        "work_item_id": request.work_item_id,
        "platform": request.platform,
        "source_revision_id": revision.revision_id,
        "source_revision_digest": revision.content_digest,
        "source_evidence_ids": source_evidence_ids,
        "source_claim_ids": sorted(set(request.claim_ids)),
        "audience": request.audience,
        "angle": request.angle,
        "body": request.body,
        "constraints": constraints,
        "duplicate_risk_inventory_digest": social_history_inventory_digest(inventory),
        "duplicate_risk_evidence_ids": sorted(set(inventory.source_evidence_ids)),
        "duplicate_risk_status": "review_ready",
        "measurement_hypothesis": request.measurement_hypothesis,
        "status": "review_required",
        "publish_allowed": False,
        "created_at": now.isoformat(),
    }
    proposal_digest = sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return SocialReuseProposal.model_validate({**payload, "proposal_digest": proposal_digest})
