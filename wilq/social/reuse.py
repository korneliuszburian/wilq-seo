from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.social.history import SocialHistoryInventory

SocialReusePlatform = Literal["linkedin", "facebook"]
SocialReuseStatus = Literal["review_required", "approved", "rejected", "stale", "blocked"]


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


class SocialReuseProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: Literal["social_reuse_proposal_v1"] = "social_reuse_proposal_v1"
    proposal_id: str = Field(min_length=1)
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
    proposal_id = (
        f"social_reuse_{request.platform}_{request.expected_revision_id}"
    )
    constraints = [
        "review_only",
        "no_vendor_publish",
        "use_only_declared_revision_lineage",
        "human_review_before_apply",
    ]
    payload = {
        "contract": "social_reuse_proposal_v1",
        "proposal_id": proposal_id,
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
