from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    return (
        PrivateSourceProposal(
            proposal_id="private_proposal_ekologus_ai_eko_opieka_2026_07_01",
            source_id="ekologus_ai_review_eko_opieka",
            source_type="private_candidate",
            privacy_class="redacted_only",
            source_locator_label="ekologus-ai reviewed handoff: Eko-Opieka",
            scope="service",
            freshness_date="2026-07-01",
            freshness_status="current",
            confidence=0.66,
            review_status="review_required",
            owner_role="Wilku albo owner oferty Ekologus",
            audience="company_wide",
            risk_tier="medium",
            source_class_label="review-required internal service context",
            target_card_id="ekologus_service_eko_opieka",
            target_card_title="Eko-Opieka / Eko Kalendarz",
            support_level="partial",
            blocked_claims=[
                "obietnica stałej zgodności",
                "gwarancja wykonania obowiązków bez danych klienta",
            ],
            safe_next_step=(
                "Pokazać Wilkowi zwykły handoff i zdecydować, czy tworzyć "
                "reviewed internal source fact."
            ),
        ),
        PrivateSourceProposal(
            proposal_id="private_proposal_ekologus_ai_audyt_zgodnosci_2026_07_01",
            source_id="ekologus_ai_review_audyt_zgodnosci",
            source_type="private_candidate",
            privacy_class="redacted_only",
            source_locator_label="ekologus-ai reviewed handoff: Audyt zgodności",
            scope="service",
            freshness_date="2026-07-01",
            freshness_status="current",
            confidence=0.64,
            review_status="review_required",
            owner_role="Wilku albo owner oferty Ekologus",
            audience="company_wide",
            risk_tier="medium",
            source_class_label="review-required internal service context",
            target_card_id="ekologus_service_audyt_zgodnosci",
            target_card_title="Audyt zgodności środowiskowej",
            support_level="partial",
            blocked_claims=[
                "gwarancja braku kar",
                "wiążąca ocena zgodności bez review eksperta",
            ],
            safe_next_step=(
                "Użyć jako pytania do review oferty; nie tworzyć production-depth "
                "karty bez decyzji człowieka."
            ),
        ),
    )


def ekologus_private_source_proposal_registry() -> PrivateSourceProposalRegistry:
    proposals = list(ekologus_private_source_proposals())
    return PrivateSourceProposalRegistry(
        proposals=proposals,
        proposal_count=len(proposals),
    )
