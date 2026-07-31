from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.source_facts import ContentSourceFact


class ContentRegulatoryRequirement(BaseModel):
    """One topic that must be grounded before WILQ plans regulated content."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ContentRegulatoryProfile(BaseModel):
    """Versioned, data-owned policy for one exact service context."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    service_card_ids: list[str] = Field(min_length=1)
    official_source_hosts: list[str] = Field(min_length=1)
    max_source_age_days: int = Field(ge=1, le=3650)
    requirements: list[ContentRegulatoryRequirement] = Field(min_length=1)


class ContentRegulatoryRequirementCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)
    source_fact_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentRegulatoryCoverage(BaseModel):
    """Exact official sources available for the selected profile and service."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str | None = None
    profile_version: str | None = None
    requirements: list[ContentRegulatoryRequirement] = Field(default_factory=list)
    requirement_coverage: list[ContentRegulatoryRequirementCoverage] = Field(
        default_factory=list
    )
    source_fact_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_facts: list[ContentSourceFact] = Field(default_factory=list)

    @property
    def covered_requirement_ids(self) -> list[str]:
        return [item.requirement_id for item in self.requirement_coverage if item.evidence_ids]

    @property
    def missing_requirements(self) -> list[ContentRegulatoryRequirement]:
        covered = set(self.covered_requirement_ids)
        return [requirement for requirement in self.requirements if requirement.id not in covered]

    @property
    def complete(self) -> bool:
        return not self.missing_requirements


class ContentRegulatoryCoverageGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


@lru_cache(maxsize=1)
def regulatory_content_profiles() -> tuple[ContentRegulatoryProfile, ...]:
    raw_profiles = json.loads(
        Path(__file__).with_name("profiles.json").read_text(encoding="utf-8")
    )["profiles"]
    profiles = tuple(ContentRegulatoryProfile.model_validate(profile) for profile in raw_profiles)
    service_card_ids = [
        service_card_id for profile in profiles for service_card_id in profile.service_card_ids
    ]
    if len(service_card_ids) != len(set(service_card_ids)):
        raise ValueError("Regulatory profiles must not share service_card_ids.")
    return profiles


def regulatory_content_profile(
    *,
    service_card_id: str,
    profiles: tuple[ContentRegulatoryProfile, ...] | None = None,
) -> ContentRegulatoryProfile | None:
    """Resolve the one profile explicitly assigned to the selected service."""

    return next(
        (
            profile
            for profile in (profiles if profiles is not None else regulatory_content_profiles())
            if service_card_id in profile.service_card_ids
        ),
        None,
    )


def regulatory_content_coverage(
    *,
    service_card_id: str,
    source_facts: tuple[ContentSourceFact, ...],
    profiles: tuple[ContentRegulatoryProfile, ...] | None = None,
    as_of: date | None = None,
) -> ContentRegulatoryCoverage:
    """Resolve profile/version/service-bound official source coverage."""

    profile = regulatory_content_profile(service_card_id=service_card_id, profiles=profiles)
    if profile is None:
        return ContentRegulatoryCoverage()
    today = as_of or date.today()
    required_ids = {requirement.id for requirement in profile.requirements}
    approved_facts = [
        fact
        for fact in source_facts
        if _fact_covers_profile(
            fact,
            profile=profile,
            service_card_id=service_card_id,
            required_ids=required_ids,
            as_of=today,
        )
    ]
    return ContentRegulatoryCoverage(
        profile_id=profile.id,
        profile_version=profile.version,
        requirements=profile.requirements,
        requirement_coverage=[
            ContentRegulatoryRequirementCoverage(
                requirement_id=requirement.id,
                source_fact_ids=sorted(
                    fact.source_id
                    for fact in approved_facts
                    if requirement.id in fact.regulatory_requirement_ids
                ),
                evidence_ids=sorted(
                    {
                        evidence_id
                        for fact in approved_facts
                        if requirement.id in fact.regulatory_requirement_ids
                        for evidence_id in fact.evidence_ids
                    }
                ),
            )
            for requirement in profile.requirements
        ],
        source_fact_ids=sorted({fact.source_id for fact in approved_facts}),
        evidence_ids=sorted(
            {evidence_id for fact in approved_facts for evidence_id in fact.evidence_ids}
        ),
        source_facts=approved_facts,
    )


def _fact_covers_profile(
    fact: ContentSourceFact,
    *,
    profile: ContentRegulatoryProfile,
    service_card_id: str,
    required_ids: set[str],
    as_of: date,
) -> bool:
    try:
        age_days = (as_of - date.fromisoformat(fact.freshness_date)).days
    except ValueError:
        return False
    return (
        fact.review_status == "approved"
        and fact.source_type == "legal_update"
        and fact.official_source
        and fact.regulatory_profile_id == profile.id
        and fact.regulatory_profile_version == profile.version
        and service_card_id in fact.applicable_service_card_ids
        and bool(required_ids.intersection(fact.regulatory_requirement_ids))
        and urlsplit(fact.source_url_or_path).hostname in profile.official_source_hosts
        and 0 <= age_days <= profile.max_source_age_days
    )


def regulatory_coverage_gap(
    coverage: ContentRegulatoryCoverage,
) -> ContentRegulatoryCoverageGap | None:
    if coverage.complete:
        return None
    missing = ", ".join(requirement.label for requirement in coverage.missing_requirements)
    return ContentRegulatoryCoverageGap(
        label="Brakuje zatwierdzonych źródeł urzędowych",
        reason=(
            "Temat regulacyjny nie ma jeszcze zatwierdzonych, oficjalnych źródeł dla: "
            f"{missing}."
        ),
        next_step=(
            "Dodaj i zatwierdź aktualne źródła urzędowe dla wskazanych zagadnień; "
            "nie zastępuj ich materiałem Ekologus ani promptem."
        ),
    )
