from __future__ import annotations

from collections.abc import Sequence

from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.knowledge.text_matching import (
    normalize_search_text,
    normalized_term_matches,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)

_MAX_SOURCE_FACTS_PER_SECTION = 4


def approved_planning_source_facts(
    planning_input: ContentPlanningInput,
    *,
    include_official: bool,
) -> list[ContentSourceFact]:
    allowed_ids = list(
        dict.fromkeys(
            source_fact_id
            for fact in planning_input.source_facts
            for source_fact_id in fact.source_fact_ids
        )
    )
    if not allowed_ids:
        return []
    approved_by_id = {
        fact.source_id: fact
        for fact in ekologus_source_facts()
        if fact.review_status == "approved" and (include_official or not fact.official_source)
    }
    return [approved_by_id[source_id] for source_id in allowed_ids if source_id in approved_by_id]


def select_source_fact_contexts_for_section(
    approved_facts: Sequence[ContentSourceFact],
    *,
    section: ContentPlanningSection,
    service_card_id: str | None,
) -> list[dict[str, object]]:
    fallback_facts = [
        fact
        for fact in approved_facts
        if service_card_id is not None
        and fact.target_card_type == "service"
        and fact.target_card_id == service_card_id
    ]
    matched_facts = [fact for fact in approved_facts if _source_fact_matches_section(fact, section)]
    selected_facts = matched_facts or fallback_facts
    ranked_facts = sorted(
        selected_facts,
        key=lambda fact: _source_fact_section_overlap_score(fact, section),
        reverse=True,
    )[:_MAX_SOURCE_FACTS_PER_SECTION]
    return [_source_fact_for_writer(fact) for fact in ranked_facts]


def approved_source_facts_by_section(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> list[dict[str, object]]:
    """Project approved planning facts onto their concrete draft targets."""

    approved_facts = approved_planning_source_facts(
        planning_input,
        include_official=True,
    )
    rows: list[dict[str, object]] = []
    for section in draftable_planning_sections(proposal.sections):
        source_facts = (
            []
            if section.regulatory_requirement_ids
            else select_source_fact_contexts_for_section(
                approved_facts,
                section=section,
                service_card_id=proposal.service_card_id,
            )
        )
        rows.append(
            {
                "section_id": section.section_id,
                "source_facts": source_facts,
            }
        )
    return rows


def _source_fact_matches_section(
    fact: ContentSourceFact,
    section: ContentPlanningSection,
) -> bool:
    section_text = _source_fact_section_text(section)
    return any(
        normalized_term_matches(term, section_text)
        for term in [*fact.service_fit_terms, *fact.buyer_problem_terms]
    )


def _source_fact_section_overlap_score(
    fact: ContentSourceFact,
    section: ContentPlanningSection,
) -> int:
    section_tokens = set(_source_fact_section_text(section).split())
    fact_tokens = {
        token
        for term in [*fact.service_fit_terms, *fact.buyer_problem_terms]
        for token in normalize_search_text(term).split()
    }
    return len(section_tokens.intersection(fact_tokens))


def _source_fact_section_text(section: ContentPlanningSection) -> str:
    return normalize_search_text(
        " ".join(
            [
                *section.query_terms,
                section.heading,
                section.reader_question,
                section.purpose,
            ]
        )
    )


def _source_fact_for_writer(fact: ContentSourceFact) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_fact_id": fact.source_id,
        "summary": fact.extracted_fact,
        "evidence_ids": fact.evidence_ids,
    }
    if fact.target_card_type == "service":
        payload["service_label"] = fact.target_card_title
    return payload


__all__ = [
    "approved_planning_source_facts",
    "approved_source_facts_by_section",
    "select_source_fact_contexts_for_section",
]
