"""Deterministic pre-persist validation for initial draft candidates."""

from __future__ import annotations

from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.knowledge.text_matching import (
    normalize_search_text,
    normalized_term_matches,
)
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
    source_facts_by_section: dict[str, list[str]] | None = None,
    source_fact_corpus: list[str] | None = None,
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
    if source_facts_by_section is not None:
        output_by_section_id = {section.section_id: section for section in output.sections}
        corpus = (
            source_fact_corpus
            if source_fact_corpus is not None
            else list(
                dict.fromkeys(
                    summary
                    for summaries in source_facts_by_section.values()
                    for summary in summaries
                )
            )
        )
        distinctive_tokens = _distinctive_fact_tokens(corpus)
        for section in draftable_sections:
            fact_summaries = source_facts_by_section.get(section.section_id, [])
            if section.regulatory_requirement_ids or not fact_summaries:
                continue
            generated = output_by_section_id.get(section.section_id)
            body_markdown = generated.body_markdown if generated is not None else ""
            if not _body_has_source_fact_signal(
                body_markdown,
                fact_summaries,
                distinctive_tokens=distinctive_tokens,
            ):
                errors.append(f"missing_source_fact_signal:{section.section_id}")
    return errors


def _distinctive_fact_tokens(source_fact_corpus: list[str]) -> frozenset[str]:
    """Return fact tokens that are specific rather than shared boilerplate.

    A token that appears in only one or two of the card's fact summaries is a
    reliable concrete signal (e.g. "respirabilny", "grawimetryczna", "FID"),
    while shared words such as "obejmować", "pomiary" or "emisji" appear across
    every summary and would let a generic section pass the gate. The corpus
    must be the full card fact set, not the per-section selection, so that
    words shared by several facts never look distinctive.
    """

    counts: dict[str, int] = {}
    for summary in source_fact_corpus:
        for token in set(normalize_search_text(summary).split()):
            if len(token) >= 5:
                counts[token] = counts.get(token, 0) + 1
    return frozenset(token for token, count in counts.items() if count <= 2)


def _body_has_source_fact_signal(
    body_markdown: str,
    fact_summaries: list[str],
    *,
    distinctive_tokens: frozenset[str],
) -> bool:
    normalized_body = normalize_search_text(body_markdown)
    return any(
        normalized_term_matches(token, normalized_body)
        for summary in fact_summaries
        for token in normalize_search_text(summary).split()
        if token in distinctive_tokens
    )


__all__ = ["document_scope_errors"]
