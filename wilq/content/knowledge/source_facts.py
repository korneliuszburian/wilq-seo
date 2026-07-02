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
        required_text_fields = {
            "source_id": self.source_id,
            "source_url_or_path": self.source_url_or_path,
            "extracted_fact": self.extracted_fact,
            "freshness_date": self.freshness_date,
            "target_card_id": self.target_card_id,
            "target_card_type": self.target_card_type,
            "target_card_title": self.target_card_title,
        }
        blank_text_fields = sorted(
            field_name
            for field_name, value in required_text_fields.items()
            if not value.strip()
        )
        if blank_text_fields:
            raise ValueError(
                "source facts require non-empty fields: "
                + ", ".join(blank_text_fields)
            )

        trace_list_fields = {
            "evidence_ids": self.evidence_ids,
            "source_connectors": self.source_connectors,
            "blocked_claims": self.blocked_claims,
            "service_fit_terms": self.service_fit_terms,
            "buyer_problem_terms": self.buyer_problem_terms,
            "buyer_triggers": self.buyer_triggers,
            "cta_patterns": self.cta_patterns,
            "allowed_claims": self.allowed_claims,
            "evidence_requirements": self.evidence_requirements,
            "usage_notes": self.usage_notes,
        }
        blank_list_fields = sorted(
            field_name
            for field_name, values in trace_list_fields.items()
            if any(not value.strip() for value in values)
        )
        if blank_list_fields:
            raise ValueError(
                "source facts require non-empty list entries: "
                + ", ".join(blank_list_fields)
            )

        if self.review_status == "approved":
            if not self.reviewer:
                raise ValueError("approved source facts require reviewer")
            if not self.evidence_ids:
                raise ValueError("approved source facts require evidence_ids")
            if not self.source_connectors:
                raise ValueError("approved source facts require source_connectors")
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

    @model_validator(mode="after")
    def validate_registry(self) -> ContentSourceFactRegistry:
        source_ids = [fact.source_id for fact in self.facts]
        duplicate_source_ids = sorted(
            source_id for source_id in set(source_ids) if source_ids.count(source_id) > 1
        )
        if duplicate_source_ids:
            raise ValueError(
                "source fact source_id values must be unique: "
                + ", ".join(duplicate_source_ids)
            )
        if self.fact_count != len(self.facts):
            raise ValueError("source fact registry fact_count must match facts length")
        return self


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
