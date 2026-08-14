"""Source-fact grounding gates and deterministic draft repair."""

from __future__ import annotations

import re

from wilq.content.drafts.fact_selection import approved_planning_source_facts
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import _source_facts_by_section
from wilq.content.knowledge.text_matching import (
    normalize_search_text,
    normalized_term_matches,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.reading_quality import _WORKING_NOTE
from wilq.content.workflow.decisions.planning import ContentPlanningProposal

_MISSING_SOURCE_FACT_SIGNAL_PREFIX = "missing_source_fact_signal:"
_MAX_GROUNDING_FACT_PARAGRAPHS = 3
_SOURCE_ATTRIBUTION_PREFIX = re.compile(
    r"^\s*(?:źródło\s+podaje,\s+że\s+|zgodnie\s+z\s+treścią\s+źródła\s+|"
    r"według\s+dostarczonej\s+instrukcji\s+\w+\s*,?\s+|"
    r"zgodnie\s+z\s+oficjalnym\s+źródłem\s+\w+\s*,?\s+|"
    r"oficjalne\s+źródło\s+\w+\s+(?:wskazuje|wyjaśnia),\s+że\s+|"
    r"źródło\s+wskazuje,\s+że\s+|źródło\s+\w+\s+rozróżnia\s+)",
    re.IGNORECASE,
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])")
_TRAILING_VERIFICATION_CLAUSE = re.compile(
    r"\s*(?:,?\s*i\s+)?wymagają?\s+weryfikacj[^.]*\.?\s*$",
    re.IGNORECASE,
)


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


def document_ready_fact_text(
    fact_text: str,
    *,
    protected_terms: list[str] | None,
) -> str:
    """Project one approved review fact into reader-facing document text."""

    stripped = _SOURCE_ATTRIBUTION_PREFIX.sub("", fact_text).strip()
    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY.split(stripped)
        if sentence.strip()
    ]
    normalized_terms = [
        term.casefold().strip() for term in (protected_terms or []) if term.strip()
    ]
    kept = [
        sentence
        for sentence in sentences
        if not (
            _WORKING_NOTE.search(sentence)
            and not any(term in sentence.casefold() for term in normalized_terms)
        )
    ]
    result = " ".join(kept) if kept else stripped
    qualifier = _TRAILING_VERIFICATION_CLAUSE.search(result)
    if qualifier and not any(
        term in qualifier.group(0).casefold() for term in normalized_terms
    ):
        result = result[: qualifier.start()].rstrip(" ,;")
    if not result:
        return result
    return result[0].upper() + result[1:]


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
) -> ContentInitialDraftModelOutput:
    """Append exact approved planning facts to shallow targeted sections."""

    missing_section_ids = {
        code.removeprefix(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
        for code in missing_codes
        if code.startswith(_MISSING_SOURCE_FACT_SIGNAL_PREFIX)
    }
    facts_by_section = _source_fact_summaries_by_section(planning_input, proposal)
    source_fact_corpus = [
        fact.extracted_fact
        for fact in approved_planning_source_facts(
            planning_input,
            include_official=True,
        )
    ]
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
                    fact_text := document_ready_fact_text(
                        summary,
                        protected_terms=None,
                    ).strip()
                )
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


def _source_fact_summaries_by_section(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> dict[str, list[str]]:
    projection: dict[str, list[str]] = {}
    for row in _source_facts_by_section(planning_input, proposal):
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


__all__ = [
    "body_has_source_fact_signal",
    "distinctive_fact_tokens",
    "document_ready_fact_text",
    "repair_missing_source_fact_signals",
    "source_fact_signal_errors",
]
