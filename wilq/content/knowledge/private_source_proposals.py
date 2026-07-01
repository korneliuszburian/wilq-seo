from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts

PrivateSourceProposalType = Literal["private_candidate", "reviewed_internal"]
PrivateSourceProposalPrivacyClass = Literal["private_local", "redacted_only"]
PrivateSourceProposalReviewStatus = Literal["review_required", "approved", "rejected", "stale"]
PrivateSourceProposalScope = Literal[
    "service",
    "buyer_problem",
    "cta",
    "claim_policy",
    "evidence_requirement",
    "metric_signal",
]


class PrivateSourceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    source_id: str
    source_type: PrivateSourceProposalType
    privacy_class: PrivateSourceProposalPrivacyClass
    source_locator_label: str
    scope: PrivateSourceProposalScope
    freshness_date: str
    freshness_status: Literal["current", "historical", "stale", "unknown"]
    confidence: float = Field(ge=0, le=1)
    review_status: PrivateSourceProposalReviewStatus
    reviewer: str | None = None
    owner_role: str
    audience: Literal[
        "company_wide",
        "department_only",
        "role_restricted",
        "owner_only",
        "unknown",
    ]
    risk_tier: Literal["low", "medium", "high", "unknown"]
    source_class_label: str
    target_card_id: str
    target_card_title: str
    support_level: Literal["direct", "partial", "background", "conflicting"]
    blocked_claims: list[str] = Field(default_factory=list)
    safe_next_step: str


class PrivateSourceProposalRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[PrivateSourceProposal] = Field(default_factory=list)
    proposal_count: int


@lru_cache(maxsize=1)
def ekologus_private_source_proposals() -> tuple[PrivateSourceProposal, ...]:
    return tuple(
        _proposal_from_source_fact(fact)
        for fact in ekologus_source_facts()
        if _is_private_service_proposal_fact(fact)
    )


def ekologus_private_source_proposal_registry() -> PrivateSourceProposalRegistry:
    proposals = list(ekologus_private_source_proposals())
    return PrivateSourceProposalRegistry(
        proposals=proposals,
        proposal_count=len(proposals),
    )


def _is_private_service_proposal_fact(fact: ContentSourceFact) -> bool:
    return (
        fact.source_type == "reviewed_internal"
        and fact.privacy_class == "redacted_only"
        and fact.review_status == "review_required"
        and fact.scope == "service"
        and "ekologus_ai_private_source_catalog" in fact.source_connectors
    )


def _proposal_from_source_fact(fact: ContentSourceFact) -> PrivateSourceProposal:
    return PrivateSourceProposal(
        proposal_id=f"private_proposal_{fact.source_id}",
        source_id=fact.source_id,
        source_type="reviewed_internal",
        privacy_class="redacted_only",
        source_locator_label=_source_locator_label(fact),
        scope=fact.scope,
        freshness_date=fact.freshness_date,
        freshness_status="current",
        confidence=fact.confidence,
        review_status="review_required",
        reviewer=fact.reviewer,
        owner_role="Wilku albo owner oferty Ekologus",
        audience="company_wide",
        risk_tier="medium",
        source_class_label="review-required internal service source fact",
        target_card_id=fact.target_card_id,
        target_card_title=fact.target_card_title,
        support_level="partial",
        blocked_claims=fact.blocked_claims,
        safe_next_step=(
            "Pokaż Wilkowi zwykły handoff i zdecyduj, czy ten redacted source "
            "fact może przejść review; nie odblokowuj production-depth bez decyzji człowieka."
        ),
    )


def _source_locator_label(fact: ContentSourceFact) -> str:
    if "KB_001_EKO_OPIEKA" in fact.source_url_or_path:
        return "ekologus-ai reviewed handoff: Eko-Opieka"
    if "KB_003_AUDYT_ZGODNOSCI" in fact.source_url_or_path:
        return "ekologus-ai reviewed handoff: Audyt zgodności"
    return f"ekologus-ai reviewed handoff: {fact.target_card_title}"
