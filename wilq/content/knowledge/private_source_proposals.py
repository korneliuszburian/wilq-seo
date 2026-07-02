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
        if _is_private_proposal_fact(fact)
    )


def ekologus_private_source_proposal_registry() -> PrivateSourceProposalRegistry:
    proposals = list(ekologus_private_source_proposals())
    return PrivateSourceProposalRegistry(
        proposals=proposals,
        proposal_count=len(proposals),
    )


def _is_private_proposal_fact(fact: ContentSourceFact) -> bool:
    return (
        fact.source_type == "reviewed_internal"
        and fact.privacy_class == "redacted_only"
        and fact.review_status == "review_required"
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
        owner_role=_owner_role(fact),
        audience=_audience(fact),
        risk_tier=_risk_tier(fact),
        source_class_label=_source_class_label(fact),
        target_card_id=fact.target_card_id,
        target_card_title=fact.target_card_title,
        support_level=_support_level(fact),
        blocked_claims=fact.blocked_claims,
        safe_next_step=_safe_next_step(fact),
    )


def _source_locator_label(fact: ContentSourceFact) -> str:
    if "KB_001_EKO_OPIEKA" in fact.source_url_or_path:
        return "ekologus-ai reviewed handoff: Eko-Opieka"
    if "KB_003_AUDYT_ZGODNOSCI" in fact.source_url_or_path:
        return "ekologus-ai reviewed handoff: Audyt zgodności"
    if "KB_014_STYL_MARKI" in fact.source_url_or_path:
        return "ekologus-ai reviewed handoff: Styl marki"
    if "KB_021_BEZPIECZENSTWO_PRAWNE" in fact.source_url_or_path:
        return "ekologus-ai reviewed handoff: Bezpieczeństwo prawne"
    return f"ekologus-ai reviewed handoff: {fact.target_card_title}"


def _owner_role(fact: ContentSourceFact) -> str:
    if fact.scope == "service":
        return "Wilku albo owner oferty Ekologus"
    if fact.scope in {"claim_policy", "evidence_requirement"}:
        return "Wilku, owner marki albo reviewer prawny Ekologus"
    return "Wilku albo owner wiedzy Ekologus"


def _audience(fact: ContentSourceFact) -> Literal[
    "company_wide",
    "department_only",
    "role_restricted",
    "owner_only",
    "unknown",
]:
    if fact.scope in {"claim_policy", "evidence_requirement"}:
        return "role_restricted"
    return "company_wide"


def _risk_tier(fact: ContentSourceFact) -> Literal["low", "medium", "high", "unknown"]:
    if fact.scope == "claim_policy":
        return "high"
    if fact.scope == "evidence_requirement":
        return "medium"
    return "medium"


def _support_level(
    fact: ContentSourceFact,
) -> Literal["direct", "partial", "background", "conflicting"]:
    if fact.scope == "claim_policy":
        return "direct"
    if fact.scope == "evidence_requirement":
        return "direct"
    return "partial"


def _source_class_label(fact: ContentSourceFact) -> str:
    if fact.scope == "service":
        return "review-required internal service source fact"
    if fact.scope == "claim_policy":
        return "review-required internal claim-policy source fact"
    if fact.scope == "evidence_requirement":
        return "review-required internal evidence-policy source fact"
    return "review-required internal source fact"


def _safe_next_step(fact: ContentSourceFact) -> str:
    if fact.scope == "claim_policy":
        return (
            "Pokaż Wilkowi/reviewerowi zasady claimów i zdecyduj, czy mają stać "
            "się reviewed policy fact; nie używaj jako automatycznej bramki bez review."
        )
    if fact.scope == "evidence_requirement":
        return (
            "Pokaż wymaganie dowodowe reviewerowi i zdecyduj, czy ma wejść do "
            "WILQ jako reviewed evidence policy; nie odblokowuj rekomendacji bez decyzji."
        )
    return (
        "Pokaż Wilkowi zwykły handoff i zdecyduj, czy ten redacted source "
        "fact może przejść review; nie odblokowuj production-depth bez decyzji człowieka."
    )
