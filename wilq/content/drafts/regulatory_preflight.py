from __future__ import annotations

from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory import turn_context as regulatory_turn_context
from wilq.content.regulatory.policy import (
    regulatory_assertion_matches,
    regulatory_requirement_assertion_errors,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


def regulatory_draft_preflight_errors(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> list[str]:
    requirements = planning_input.regulatory_coverage.requirements
    if not requirements:
        return []
    draftable_sections = draftable_planning_sections(proposal.sections)
    bound_requirement_ids = {
        requirement_id
        for section in draftable_sections
        for requirement_id in section.regulatory_requirement_ids
    }
    missing_bindings = {
        f"regulatory_preflight:missing_section_binding:{requirement.id}"
        for requirement in requirements
        if requirement.id not in bound_requirement_ids
    }
    ungroundable_assertions: set[str] = set()
    missing_plan_assertions: set[str] = set()
    for requirement in requirements:
        bound_sections = [
            section
            for section in draftable_sections
            if requirement.id in section.regulatory_requirement_ids
        ]
        official_facts = regulatory_turn_context.approved_regulatory_source_facts(
            planning_input,
            {requirement.id},
        )
        for assertion in requirement.document_assertions:
            if not any(
                regulatory_assertion_matches(
                    text=fact.extracted_fact,
                    assertion=assertion,
                )
                for fact in official_facts
            ):
                ungroundable_assertions.add(
                    "regulatory_preflight:ungroundable_assertion:"
                    f"{requirement.id}:{assertion.id}"
                )
        section_text = "\n".join(
            "\n".join((section.heading, section.purpose, section.reader_question))
            for section in bound_sections
        )
        for error in regulatory_requirement_assertion_errors(
            requirement=requirement,
            text=section_text,
        ):
            missing_plan_assertions.add(
                "regulatory_preflight:missing_plan_assertion:"
                + error.removeprefix("regulatory_document_assertion:")
            )
    return [
        *sorted(missing_bindings),
        *sorted(ungroundable_assertions),
        *sorted(missing_plan_assertions),
    ]


__all__ = ["regulatory_draft_preflight_errors"]
