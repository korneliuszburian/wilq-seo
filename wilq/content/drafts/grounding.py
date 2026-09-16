"""Source-fact grounding gates and deterministic draft repair."""

from __future__ import annotations

from wilq.content.drafts.document_facts import (
    document_ready_fact_text,
    safe_document_ready_fact_text,
)
from wilq.content.drafts.draft_plan_preparation import PreparedDraftPlan
from wilq.content.drafts.fact_selection import (
    approved_planning_source_facts,
    approved_source_facts_by_section,
)
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.knowledge.text_matching import (
    normalize_search_text,
    normalized_term_matches,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal

_MISSING_SOURCE_FACT_SIGNAL_PREFIX = "missing_source_fact_signal:"
_MAX_GROUNDING_FACT_PARAGRAPHS = 3


def distinctive_fact_tokens(source_fact_corpus: list[str]) -> frozenset[str]:
    """Return concrete fact tokens that are not shared card boilerplate."""

    counts: dict[str, int] = {}
    for summary in source_fact_corpus:
        for token in set(normalize_search_text(summary).split()):
            if len(token) >= 5:
                counts[token] = counts.get(token, 0) + 1
    return frozenset(token for token, count in counts.items() if count <= 2)


def body_has_source_fact_signal(
    body_markdown: str,
    fact_summaries: list[str],
    *,
    distinctive_tokens: frozenset[str],
) -> bool:
    """Return whether a body contains a concrete token from its selected facts."""

    normalized_body = normalize_search_text(body_markdown)
    return any(
        normalized_term_matches(token, normalized_body)
        for summary in fact_summaries
        for token in normalize_search_text(summary).split()
        if token in distinctive_tokens
    )


def source_fact_signal_errors(
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    *,
    source_facts_by_section: dict[str, list[str]],
    source_fact_corpus: list[str],
) -> list[str]:
    """Return missing-signal codes for non-regulatory sections with facts."""

    output_by_section_id = {section.section_id: section for section in output.sections}
    distinctive_tokens = distinctive_fact_tokens(source_fact_corpus)
    errors: list[str] = []
    for section in draftable_planning_sections(proposal.sections):
        fact_summaries = source_facts_by_section.get(section.section_id, [])
        if section.regulatory_requirement_ids or not fact_summaries:
            continue
        generated = output_by_section_id.get(section.section_id)
        body_markdown = generated.body_markdown if generated is not None else ""
        if not body_has_source_fact_signal(
            body_markdown,
            fact_summaries,
            distinctive_tokens=distinctive_tokens,
        ):
            errors.append(f"{_MISSING_SOURCE_FACT_SIGNAL_PREFIX}{section.section_id}")
    return errors


def repair_missing_source_fact_signals(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    missing_codes: list[str],
    prepared_plan: PreparedDraftPlan | None = None,
) -> ContentInitialDraftModelOutput:
    """Append exact approved planning facts to shallow targeted sections."""

    missing_section_ids = {
        code.removeprefix(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
        for code in missing_codes
        if code.startswith(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
    }
    facts_by_section = source_fact_summaries_by_section(
        planning_input,
        proposal,
        prepared_plan=prepared_plan,
    )
    source_fact_corpus = (
        prepared_source_fact_corpus(prepared_plan)
        if prepared_plan is not None
        else [
            fact.extracted_fact
            for fact in approved_planning_source_facts(
                planning_input,
                include_official=True,
            )
        ]
    )
    distinctive_tokens = distinctive_fact_tokens(source_fact_corpus)
    sections = []
    for section in output.sections:
        fact_summaries = facts_by_section.get(section.section_id, [])
        if (
            section.section_id not in missing_section_ids
            or not fact_summaries
            or body_has_source_fact_signal(
                section.body_markdown,
                fact_summaries,
                distinctive_tokens=distinctive_tokens,
            )
        ):
            sections.append(section)
            continue
        document_ready_facts = list(
            dict.fromkeys(
                fact_text
                for summary in fact_summaries
                if (
                    fact_text := safe_document_ready_fact_text(
                        summary,
                        protected_terms=None,
                    )
                )
                is not None
            )
        )[:_MAX_GROUNDING_FACT_PARAGRAPHS]
        patch_text = "\n\n".join(document_ready_facts)
        if not patch_text or patch_text in section.body_markdown:
            sections.append(section)
            continue
        sections.append(
            section.model_copy(
                update={
                    "body_markdown": f"{section.body_markdown}\n\n{patch_text}",
                }
            )
        )
    return ContentInitialDraftModelOutput.model_validate(
        {
            **output.model_dump(mode="python"),
            "sections": [section.model_dump(mode="python") for section in sections],
        }
    )


def source_fact_summaries_by_section(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    *,
    prepared_plan: PreparedDraftPlan | None = None,
) -> dict[str, list[str]]:
    if prepared_plan is not None:
        return {
            target.section.section_id: [fact.summary for fact in target.source_facts]
            for target in prepared_plan.target_supports
            if not target.section.regulatory_requirement_ids
        }
    projection: dict[str, list[str]] = {}
    for row in approved_source_facts_by_section(planning_input, proposal):
        section_id = row.get("section_id")
        source_facts = row.get("source_facts")
        if not isinstance(section_id, str) or not isinstance(source_facts, list):
            raise ValueError("Invalid source-fact section projection.")
        summaries: list[str] = []
        for source_fact in source_facts:
            if not isinstance(source_fact, dict):
                raise ValueError("Invalid source-fact section projection.")
            summary = source_fact.get("summary")
            if not isinstance(summary, str):
                raise ValueError("Invalid source-fact section projection.")
            summaries.append(summary)
        projection[section_id] = summaries
    return projection


def prepared_source_fact_corpus(prepared_plan: PreparedDraftPlan) -> list[str]:
    """Deduplicate exact assigned facts before deriving distinctive tokens."""

    seen: set[tuple[tuple[str, ...], str]] = set()
    corpus: list[str] = []
    for target in prepared_plan.target_supports:
        for fact in target.source_facts:
            key = (tuple(sorted(fact.source_fact_ids)), fact.summary)
            if key in seen:
                continue
            seen.add(key)
            corpus.append(fact.summary)
    return corpus


__all__ = [
    "body_has_source_fact_signal",
    "distinctive_fact_tokens",
    "document_ready_fact_text",
    "prepared_source_fact_corpus",
    "repair_missing_source_fact_signals",
    "safe_document_ready_fact_text",
    "source_fact_summaries_by_section",
    "source_fact_signal_errors",
]
