"""Deterministic pre-persist validation for initial draft candidates."""

from __future__ import annotations

from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.regulatory.policy import (
    ContentRegulatoryRequirement,
    regulatory_requirement_assertion_errors,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


def document_scope_errors(
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    *,
    regulatory_requirements: list[ContentRegulatoryRequirement] | None = None,
) -> list[str]:
    errors: list[str] = []
    draftable_sections = draftable_planning_sections(proposal.sections)
    expected_sections = [(item.section_id, item.heading) for item in draftable_sections]
    actual_sections = [(item.section_id, item.heading) for item in output.sections]
    if actual_sections != expected_sections:
        errors.append("sections")
    if [item.question for item in output.faq] != [item.question for item in proposal.faq]:
        errors.append("faq")
    if len(output.cta_blocks) != len(proposal.cta_blocks):
        errors.append("cta_blocks")
    if [item.target_url for item in output.internal_links] != [
        item.target_url for item in proposal.internal_links
    ]:
        errors.append("internal_links")
    lineage_groups = [
        *(item.evidence_ids for item in draftable_sections),
        *(item.evidence_ids for item in proposal.faq),
        *(item.evidence_ids for item in proposal.cta_blocks),
        *(item.evidence_ids for item in proposal.internal_links),
    ]
    if any(not values for values in lineage_groups):
        errors.append("missing_evidence_lineage")
    lineage_atoms = [
        *(value for item in draftable_sections for value in (*item.query_terms, *item.claim_ids)),
        *(value for item in proposal.faq for value in (*item.query_terms, *item.claim_ids)),
        *(value for item in proposal.cta_blocks for value in item.claim_ids),
        *(value for item in proposal.internal_links for value in item.claim_ids),
    ]
    if any(not value.strip() for value in lineage_atoms):
        errors.append("blank_lineage_atom")
    if any(not content_is_safe_public_url(item.target_url) for item in proposal.internal_links):
        errors.append("invalid_internal_link_target")
    if regulatory_requirements:
        output_by_section_id = {section.section_id: section for section in output.sections}
        for requirement in regulatory_requirements:
            generated_sections = [
                output_by_section_id[section.section_id]
                for section in draftable_sections
                if requirement.id in section.regulatory_requirement_ids
                and section.section_id in output_by_section_id
            ]
            if generated_sections:
                errors.extend(
                    regulatory_requirement_assertion_errors(
                        requirement=requirement,
                        text="\n".join(section.body_markdown for section in generated_sections),
                    )
                )
    return errors


__all__ = ["document_scope_errors"]
