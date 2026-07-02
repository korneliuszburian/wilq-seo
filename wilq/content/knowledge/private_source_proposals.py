from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts

PrivateSourceProposalType = Literal["private_candidate", "reviewed_internal"]
PrivateSourceProposalPrivacyClass = Literal["private_local", "redacted_only"]
PrivateSourceProposalReviewStatus = Literal["review_required", "approved", "rejected", "stale"]
PrivateSourceProposalFreshnessStatus = Literal["current", "historical", "stale", "unknown"]
PrivateSourceProposalRetentionDecision = Literal[
    "pending_owner_decision",
    "retain_while_source_approved",
    "short_window_only",
    "do_not_retain",
]
PrivateSourceProposalScope = Literal[
    "service",
    "buyer_problem",
    "cta",
    "claim_policy",
    "evidence_requirement",
    "metric_signal",
]
PrivateSourceProposalAudience = Literal[
    "company_wide",
    "department_only",
    "role_restricted",
    "owner_only",
    "unknown",
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
    freshness_status: PrivateSourceProposalFreshnessStatus
    confidence: float = Field(ge=0, le=1)
    review_status: PrivateSourceProposalReviewStatus
    reviewer: str | None = None
    owner_role: str
    audience: PrivateSourceProposalAudience
    risk_tier: Literal["low", "medium", "high", "unknown"]
    data_classes: list[str] = Field(default_factory=list)
    source_block_refs: list[str] = Field(default_factory=list)
    retention_decision: PrivateSourceProposalRetentionDecision
    deletion_path: list[str] = Field(default_factory=list)
    eval_case_ids: list[str] = Field(default_factory=list)
    source_class_label: str
    target_card_id: str
    target_card_title: str
    support_level: Literal["direct", "partial", "background", "conflicting"]
    blocked_claims: list[str] = Field(default_factory=list)
    safe_next_step: str

    @model_validator(mode="after")
    def validate_governance_fields(self) -> PrivateSourceProposal:
        required_text_fields = {
            "proposal_id": self.proposal_id,
            "source_id": self.source_id,
            "source_locator_label": self.source_locator_label,
            "owner_role": self.owner_role,
            "source_class_label": self.source_class_label,
            "target_card_id": self.target_card_id,
            "target_card_title": self.target_card_title,
            "safe_next_step": self.safe_next_step,
        }
        missing_text_fields = sorted(
            field_name
            for field_name, value in required_text_fields.items()
            if not value.strip()
        )
        if missing_text_fields:
            raise ValueError(
                "private source proposals require non-empty fields: "
                + ", ".join(missing_text_fields)
            )

        required_list_fields = {
            "data_classes": self.data_classes,
            "source_block_refs": self.source_block_refs,
            "deletion_path": self.deletion_path,
            "eval_case_ids": self.eval_case_ids,
            "blocked_claims": self.blocked_claims,
        }
        missing_list_fields = sorted(
            field_name
            for field_name, values in required_list_fields.items()
            if not values or any(not value.strip() for value in values)
        )
        if missing_list_fields:
            raise ValueError(
                "private source proposals require non-empty governance lists: "
                + ", ".join(missing_list_fields)
            )
        if self.review_status == "approved" and not (self.reviewer or "").strip():
            raise ValueError("approved private source proposals require reviewer")

        return self


class PrivateSourceProposalRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[PrivateSourceProposal] = Field(default_factory=list)
    proposal_count: int

    @model_validator(mode="after")
    def validate_registry(self) -> PrivateSourceProposalRegistry:
        proposal_ids = [proposal.proposal_id for proposal in self.proposals]
        duplicate_proposal_ids = sorted(
            proposal_id
            for proposal_id in set(proposal_ids)
            if proposal_ids.count(proposal_id) > 1
        )
        if duplicate_proposal_ids:
            raise ValueError(
                "private source proposal_id values must be unique: "
                + ", ".join(duplicate_proposal_ids)
            )
        if self.proposal_count != len(self.proposals):
            raise ValueError(
                "private source proposal registry proposal_count must match proposals length"
            )
        return self


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
        data_classes=_data_classes(fact),
        source_block_refs=_source_block_refs(fact),
        retention_decision="pending_owner_decision",
        deletion_path=[
            "Usuń albo odrzuć redacted proposal w Service Profile review.",
            "Nie promuj source fact i nie kompiluj knowledge card.",
            "Usuń lokalny derived artifact, jeżeli owner nie zatwierdzi źródła.",
        ],
        eval_case_ids=_eval_case_ids(fact),
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


def _audience(fact: ContentSourceFact) -> PrivateSourceProposalAudience:
    if fact.scope in {"claim_policy", "evidence_requirement"}:
        return "role_restricted"
    return "company_wide"


def _risk_tier(fact: ContentSourceFact) -> Literal["low", "medium", "high", "unknown"]:
    if fact.scope == "claim_policy":
        return "high"
    if fact.scope == "evidence_requirement":
        return "medium"
    return "medium"


def _data_classes(fact: ContentSourceFact) -> list[str]:
    if fact.scope == "claim_policy":
        return ["brand_policy", "legal_or_claim_policy", "internal_operational"]
    if fact.scope == "evidence_requirement":
        return ["evidence_policy", "internal_operational"]
    if fact.scope == "service":
        return ["service_strategy", "internal_operational"]
    return ["internal_operational"]


def _source_block_refs(fact: ContentSourceFact) -> list[str]:
    if "KB_001_EKO_OPIEKA" in fact.source_url_or_path:
        return ["KB_001_EKO_OPIEKA"]
    if "KB_003_AUDYT_ZGODNOSCI" in fact.source_url_or_path:
        return ["KB_003_AUDYT_ZGODNOSCI"]
    if "KB_014_STYL_MARKI" in fact.source_url_or_path:
        return ["KB_014_STYL_MARKI"]
    if "KB_021_BEZPIECZENSTWO_PRAWNE" in fact.source_url_or_path:
        return ["KB_021_BEZPIECZENSTWO_PRAWNE"]
    return [fact.source_id]


def _eval_case_ids(fact: ContentSourceFact) -> list[str]:
    if fact.scope == "claim_policy":
        return ["goal_005_private_claim_policy_review", "goal_006_claim_ledger_gate"]
    if fact.scope == "evidence_requirement":
        return ["goal_005_private_evidence_policy_review"]
    if fact.scope == "service":
        return ["goal_005_private_service_review", "goal_005_service_profile_uat"]
    return ["goal_005_private_source_review"]


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
