from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SourceFactType = Literal[
    "public_site",
    "connector_metric",
    "reviewed_internal",
    "private_candidate",
    "legal_update",
    "uat_feedback",
]
SourceFactPrivacyClass = Literal["commit_safe", "private_local", "redacted_only"]
SourceFactScope = Literal[
    "service",
    "buyer_problem",
    "cta",
    "claim_policy",
    "evidence_requirement",
    "metric_signal",
]
SourceFactReviewStatus = Literal[
    "unreviewed",
    "review_required",
    "approved",
    "rejected",
    "stale",
]
ContentKnowledgeLifecycleStatus = Literal[
    "seeded_contract_proof",
    "source_backed_review_required",
    "approved_current",
    "stale",
    "rejected",
]


class ContentSourceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_type: SourceFactType
    privacy_class: SourceFactPrivacyClass
    source_url_or_path: str
    extracted_fact: str
    scope: SourceFactScope
    freshness_date: str
    confidence: float = Field(ge=0, le=1)
    review_status: SourceFactReviewStatus
    reviewer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(default_factory=list)
    target_card_id: str
    target_card_type: str
    target_card_title: str
    service_fit_terms: list[str] = Field(default_factory=list)
    buyer_problem_terms: list[str] = Field(default_factory=list)
    buyer_triggers: list[str] = Field(default_factory=list)
    cta_patterns: list[str] = Field(default_factory=list)
    allowed_claims: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    usage_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_review_state(self) -> ContentSourceFact:
        if self.review_status == "approved" and not self.reviewer:
            raise ValueError("approved source facts require reviewer")
        if self.source_type == "public_site" and self.privacy_class != "commit_safe":
            raise ValueError("public site source facts must be commit_safe")
        if "ekologus_ai_private_source_catalog" in self.source_connectors:
            if self.source_type not in {"private_candidate", "reviewed_internal"}:
                raise ValueError("ekologus-ai source facts must use private source types")
            if self.privacy_class != "redacted_only":
                raise ValueError("ekologus-ai source facts must be redacted_only")
            if self.review_status != "review_required":
                raise ValueError("ekologus-ai source facts must start as review_required")
            if not self.blocked_claims:
                raise ValueError("ekologus-ai source facts require blocked_claims")
            if not self.evidence_requirements:
                raise ValueError("ekologus-ai source facts require evidence_requirements")
            if not self.usage_notes:
                raise ValueError("ekologus-ai source facts require usage_notes")
        return self


class ContentSourceFactRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: list[ContentSourceFact] = Field(default_factory=list)
    fact_count: int


@lru_cache(maxsize=1)
def ekologus_source_facts() -> tuple[ContentSourceFact, ...]:
    path = Path(__file__).with_name("source_facts.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    facts = [ContentSourceFact.model_validate(item) for item in payload["facts"]]
    return tuple(facts)


def ekologus_source_fact_registry() -> ContentSourceFactRegistry:
    facts = list(ekologus_source_facts())
    return ContentSourceFactRegistry(facts=facts, fact_count=len(facts))


def knowledge_lifecycle_from_review_status(
    review_status: SourceFactReviewStatus,
) -> ContentKnowledgeLifecycleStatus:
    if review_status == "approved":
        return "approved_current"
    if review_status == "stale":
        return "stale"
    if review_status == "rejected":
        return "rejected"
    return "source_backed_review_required"
