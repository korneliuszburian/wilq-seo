from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.evidence.registry import list_evidence_by_ids


class ContentRegulatoryDocumentAssertion(BaseModel):
    """One observable concept a regulated plan and draft must cover.

    The profile owns these assertions.  They are deliberately small, typed
    concept checks rather than a hidden prompt rubric, so a future regulated
    service can declare its own obligations without adding service-specific
    code.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    required_any_of: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def require_visible_terms(self) -> ContentRegulatoryDocumentAssertion:
        fields = {"id": self.id, "label": self.label}
        blanks = [name for name, value in fields.items() if not value.strip()]
        terms = [term.strip() for term in self.required_any_of]
        if not terms or any(not term for term in terms):
            blanks.append("required_any_of")
        if len(terms) != len(set(terms)):
            raise ValueError("Regulatory document assertions cannot repeat terms.")
        if blanks:
            raise ValueError(
                "Regulatory document assertions require visible fields: "
                + ", ".join(blanks)
            )
        self.id = self.id.strip()
        self.label = self.label.strip()
        self.required_any_of = terms
        return self


def regulatory_assertion_matches(
    *, text: str, assertion: ContentRegulatoryDocumentAssertion
) -> bool:
    """Return whether one profile-owned observable concept occurs in text.

    Case-folding and whitespace normalization keep the policy robust to
    ordinary Polish capitalization and layout, while profiles explicitly own
    permitted variants for inflection or wording.
    """

    normalized = re.sub(r"\s+", " ", text).casefold()
    return any(
        re.sub(r"\s+", " ", term).casefold() in normalized
        for term in assertion.required_any_of
    )


def regulatory_requirement_assertion_errors(
    *,
    requirement: ContentRegulatoryRequirement,
    text: str,
) -> list[str]:
    """Return exact missing profile-owned concepts for one content target."""

    return [
        f"regulatory_document_assertion:{requirement.id}:{assertion.id}"
        for assertion in requirement.document_assertions
        if not regulatory_assertion_matches(text=text, assertion=assertion)
    ]


class ContentRegulatoryRequirement(BaseModel):
    """One topic that must be grounded before WILQ plans regulated content."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    document_assertions: list[ContentRegulatoryDocumentAssertion] = Field(
        default_factory=list
    )


class ContentRegulatoryClaimConstraint(BaseModel):
    """One profile-owned semantic constraint for a regulated document.

    Phrase assertions prove that a visible concept is present.  They cannot
    distinguish a qualified legal statement from an overbroad one, so the
    assurance critic receives these versioned constraints together with the
    exact approved source facts.  The constraint is data, not a BDO branch in
    a prompt: every regulated service can declare its own checks.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    requirement_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def require_visible_fields(self) -> ContentRegulatoryClaimConstraint:
        text_fields = {
            "id": self.id,
            "label": self.label,
            "instruction": self.instruction,
        }
        blank_fields = sorted(
            name for name, value in text_fields.items() if not value.strip()
        )
        requirement_ids = [value.strip() for value in self.requirement_ids]
        if not requirement_ids or any(not value for value in requirement_ids):
            blank_fields.append("requirement_ids")
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("Regulatory claim constraints cannot repeat requirement IDs.")
        if blank_fields:
            raise ValueError(
                "Regulatory claim constraints require visible fields: "
                + ", ".join(blank_fields)
            )
        self.id = self.id.strip()
        self.label = self.label.strip()
        self.instruction = self.instruction.strip()
        self.requirement_ids = requirement_ids
        return self


class ContentRegulatoryProfile(BaseModel):
    """Versioned, data-owned policy for one exact service context."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    service_card_ids: list[str] = Field(min_length=1)
    official_source_hosts: list[str] = Field(min_length=1)
    max_source_age_days: int = Field(ge=1, le=3650)
    requirements: list[ContentRegulatoryRequirement] = Field(min_length=1)
    claim_constraints: list[ContentRegulatoryClaimConstraint] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def require_constraint_requirement_bindings(self) -> ContentRegulatoryProfile:
        requirement_ids = [requirement.id for requirement in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("Regulatory profiles must have unique requirement IDs.")
        known_ids = set(requirement_ids)
        constraint_ids = [constraint.id for constraint in self.claim_constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("Regulatory profiles must have unique claim constraint IDs.")
        reserved_constraint_ids = sorted(
            constraint_id
            for constraint_id in constraint_ids
            if constraint_id.startswith("requirement:")
        )
        if reserved_constraint_ids:
            raise ValueError(
                "Regulatory claim constraints cannot use the reserved requirement: namespace: "
                + ", ".join(reserved_constraint_ids)
            )
        unknown = sorted(
            {
                requirement_id
                for constraint in self.claim_constraints
                for requirement_id in constraint.requirement_ids
                if requirement_id not in known_ids
            }
        )
        if unknown:
            raise ValueError(
                "Regulatory claim constraints reference unknown requirements: "
                + ", ".join(unknown)
            )
        return self


def regulatory_draft_assurance_constraints(
    profile: ContentRegulatoryProfile,
) -> list[ContentRegulatoryClaimConstraint]:
    """Compile universal critic checks from the profile's approved requirements.

    This is deliberately requirement-driven rather than service-driven: every
    regulated service gets the same baseline check for scope, conditions,
    exceptions, deadlines and quantified consequences present in its exact
    official facts. Profiles may add narrow, exceptional constraints, but do
    not need a hand-authored rubric merely to receive the safety baseline.
    """

    baseline = [
        ContentRegulatoryClaimConstraint(
            id=f"requirement:{requirement.id}",
            label=requirement.label,
            instruction=(
                "Oceń ten wymóg wyłącznie względem przypisanych oficjalnych faktów. "
                "Jeżeli kandydat opisuje obowiązek, uprawnienie, wyjątek, termin, "
                "sankcję albo procedurę, musi zachować podmiot, warunek, zakres, "
                "wyjątki oraz wartości i terminy z tych faktów. Nie wolno zaakceptować "
                "uogólnienia, które rozszerza obowiązek na wszystkich, przypisuje termin "
                "innemu obowiązkowi, usuwa wyjątek albo obiecuje wynik kontroli."
            ),
            requirement_ids=[requirement.id],
        )
        for requirement in profile.requirements
    ]
    constraints = [*baseline, *profile.claim_constraints]
    ids = [constraint.id for constraint in constraints]
    if len(ids) != len(set(ids)):
        raise ValueError("Regulatory draft assurance constraints must have unique IDs.")
    return constraints


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


class ContentRegulatorySourceCandidate(BaseModel):
    """Read-only official source awaiting human promotion into a SourceFact."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    service_card_ids: list[str] = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    observed_on: str = Field(min_length=1)
    requirement_ids: list[str] = Field(min_length=1)
    review_status: Literal["review_required"] = "review_required"
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_reviewable_identity(self) -> ContentRegulatorySourceCandidate:
        text_fields = {
            "candidate_id": self.candidate_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "observed_on": self.observed_on,
            "safe_next_step": self.safe_next_step,
        }
        blank_fields = sorted(
            name for name, value in text_fields.items() if not value.strip()
        )
        list_fields = {
            "service_card_ids": self.service_card_ids,
            "requirement_ids": self.requirement_ids,
        }
        blank_lists = sorted(
            name
            for name, values in list_fields.items()
            if any(not value.strip() for value in values)
        )
        if blank_fields or blank_lists:
            fields = ", ".join([*blank_fields, *blank_lists])
            raise ValueError(f"Regulatory source candidates require non-empty fields: {fields}")
        try:
            date.fromisoformat(self.observed_on)
        except ValueError as exc:
            raise ValueError("Regulatory source candidates require ISO observed_on.") from exc
        return self


class ContentRegulatoryReviewCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    observed_on: str = Field(min_length=1)
    requirement_ids: list[str] = Field(min_length=1)
    requirement_labels: list[str] = Field(min_length=1)
    review_status: Literal["review_required"] = "review_required"
    safe_next_step: str = Field(min_length=1)


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


@lru_cache(maxsize=1)
def regulatory_source_candidates() -> tuple[ContentRegulatorySourceCandidate, ...]:
    raw_candidates = json.loads(
        Path(__file__).with_name("candidates.json").read_text(encoding="utf-8")
    )["candidates"]
    candidates = tuple(
        ContentRegulatorySourceCandidate.model_validate(candidate)
        for candidate in raw_candidates
    )
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Regulatory source candidates must have unique candidate_id values.")
    return candidates


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


def regulatory_review_candidates(
    *,
    service_card_id: str,
    coverage: ContentRegulatoryCoverage,
    candidates: tuple[ContentRegulatorySourceCandidate, ...] | None = None,
    profiles: tuple[ContentRegulatoryProfile, ...] | None = None,
    as_of: date | None = None,
) -> list[ContentRegulatoryReviewCandidate]:
    """Expose only current official candidates for requirements still blocked."""

    profile = regulatory_content_profile(service_card_id=service_card_id, profiles=profiles)
    if profile is None or coverage.complete:
        return []
    today = as_of or date.today()
    missing_ids = {requirement.id for requirement in coverage.missing_requirements}
    labels = {requirement.id: requirement.label for requirement in profile.requirements}
    return [
        ContentRegulatoryReviewCandidate(
            candidate_id=candidate.candidate_id,
            source_url=candidate.source_url,
            source_title=candidate.source_title,
            observed_on=candidate.observed_on,
            requirement_ids=sorted(set(candidate.requirement_ids).intersection(missing_ids)),
            requirement_labels=[
                labels[requirement_id]
                for requirement_id in candidate.requirement_ids
                if requirement_id in missing_ids
            ],
            safe_next_step=candidate.safe_next_step,
        )
        for candidate in (candidates if candidates is not None else regulatory_source_candidates())
        if _candidate_matches_profile(
            candidate,
            profile=profile,
            service_card_id=service_card_id,
            missing_ids=missing_ids,
            as_of=today,
        )
    ]


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
    evidence_by_id = {
        evidence.id: evidence for evidence in list_evidence_by_ids(fact.evidence_ids)
    }
    evidence_is_exact = bool(fact.evidence_ids) and all(
        evidence_id in evidence_by_id
        and evidence_by_id[evidence_id].source_id == fact.source_id
        and evidence_by_id[evidence_id].raw_ref == fact.source_url_or_path
        for evidence_id in fact.evidence_ids
    )
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
        and evidence_is_exact
    )


def _candidate_matches_profile(
    candidate: ContentRegulatorySourceCandidate,
    *,
    profile: ContentRegulatoryProfile,
    service_card_id: str,
    missing_ids: set[str],
    as_of: date,
) -> bool:
    try:
        age_days = (as_of - date.fromisoformat(candidate.observed_on)).days
    except ValueError:
        return False
    return (
        candidate.profile_id == profile.id
        and candidate.profile_version == profile.version
        and service_card_id in candidate.service_card_ids
        and bool(missing_ids.intersection(candidate.requirement_ids))
        and urlsplit(candidate.source_url).hostname in profile.official_source_hosts
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
