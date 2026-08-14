from __future__ import annotations

from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import ContentRegulatoryRequirement


def regulatory_document_assertion_context(
    planning_input: ContentPlanningInput,
) -> list[dict[str, object]]:
    """Project profile-owned document assertions into trusted turn context."""

    return [
        assertion
        for requirement in planning_input.regulatory_coverage.requirements
        for assertion in _requirement_document_assertion_context(requirement)
    ]


def regulatory_facts_for_requirements(
    planning_input: ContentPlanningInput,
    requirement_ids: set[str] | None = None,
) -> list[ContentSourceFact]:
    """Return regulatory coverage facts bound to any requested requirement."""

    facts = planning_input.regulatory_coverage.source_facts
    if requirement_ids is None:
        return list(facts)
    return [
        fact
        for fact in facts
        if requirement_ids.intersection(fact.regulatory_requirement_ids)
    ]


def approved_regulatory_source_facts(
    planning_input: ContentPlanningInput,
    requirement_ids: set[str] | None = None,
) -> list[ContentSourceFact]:
    """Return only reviewed official facts for the requested requirements."""

    return [
        fact
        for fact in regulatory_facts_for_requirements(planning_input, requirement_ids)
        if fact.official_source and fact.review_status == "approved"
    ]


def _requirement_document_assertion_context(
    requirement: ContentRegulatoryRequirement,
) -> list[dict[str, object]]:
    return [
        {
            "requirement_id": requirement.id,
            "assertion_id": assertion.id,
            "label": assertion.label,
            "required_any_of": assertion.required_any_of,
        }
        for assertion in requirement.document_assertions
    ]


__all__ = [
    "approved_regulatory_source_facts",
    "regulatory_document_assertion_context",
    "regulatory_facts_for_requirements",
]
