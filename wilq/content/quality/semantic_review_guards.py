from __future__ import annotations

import re
from collections.abc import Mapping

from wilq.content.drafts.initial_full_draft_scope import (
    bind_draftable_planning_sections,
    draftable_planning_sections,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.reading_quality import revision_readability_issues
from wilq.content.quality.section_heading_index import build_section_heading_index
from wilq.content.quality.semantic_review_contracts import ContentSemanticDimension
from wilq.content.quality.working_note import contains_working_note
from wilq.content.regulatory.policy import ContentRegulatoryRequirementCoverage
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionSection,
)

_SEMANTIC_STOPWORDS = frozenset(
    {
        "albo",
        "który",
        "która",
        "które",
        "przez",
        "może",
        "jest",
        "się",
        "dla",
        "jego",
    }
)


def regulatory_quality_issues(
    *,
    revision: ContentDraftRevision,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> list[tuple[ContentSemanticDimension, str, str, list[str]]]:
    coverage = planning_input.regulatory_coverage
    if coverage is None:
        return []
    fact_by_id = {fact.source_id: fact for fact in coverage.source_facts}
    coverage_by_requirement = {item.requirement_id: item for item in coverage.requirement_coverage}
    proposal_by_id = bind_draftable_planning_sections(
        proposal.sections,
        revision.sections,
        allow_revision_subset=True,
    )
    issues: list[tuple[ContentSemanticDimension, str, str, list[str]]] = []
    for revision_section in revision.sections:
        section_id = revision_section.section_id
        if section_id is None:
            raise ValueError("Semantic review requires exact revision section IDs.")
        proposal_section = proposal_by_id[section_id]
        requirement_ids = getattr(proposal_section, "regulatory_requirement_ids", [])
        if not requirement_ids:
            continue
        body_tokens = _semantic_tokens(revision_section.body_markdown)
        fact_tokens: set[str] = set()
        requirement_evidence_ids: list[str] = []
        for requirement_id in requirement_ids:
            binding = coverage_by_requirement.get(requirement_id)
            if binding is None:
                continue
            requirement_evidence_ids.extend(binding.evidence_ids)
            for fact_id in binding.source_fact_ids:
                fact = fact_by_id.get(fact_id)
                if fact is not None:
                    fact_tokens.update(_semantic_tokens(fact.extracted_fact))
        if not _has_required_fact_overlap(body_tokens, fact_tokens):
            issues.append(
                (
                    "credibility",
                    str(revision_section.section_id),
                    (
                        "Sekcja regulacyjna nie zachowuje wystarczającego "
                        "pokrycia zatwierdzonych source facts."
                    ),
                    [
                        evidence_id
                        for evidence_id in dict.fromkeys(requirement_evidence_ids)
                        if evidence_id in _revision_evidence_ids(revision)
                    ],
                )
            )
        query_tokens = {
            token for term in proposal_section.query_terms for token in _semantic_tokens(str(term))
        }
        if query_tokens and len(body_tokens) < 15 and not body_tokens.intersection(query_tokens):
            issues.append(
                (
                    "search_intent_fit",
                    str(revision_section.section_id),
                    "Sekcja nie odpowiada zatwierdzonej mapie zapytań.",
                    list(revision_section.evidence_ids),
                )
            )
    issues.extend(
        _merged_section_regulatory_issues(
            revision=revision,
            proposal=proposal,
            fact_by_id=fact_by_id,
            coverage_by_requirement=coverage_by_requirement,
        )
    )
    return issues


def _merged_section_regulatory_issues(
    *,
    revision: ContentDraftRevision,
    proposal: ContentPlanningProposal,
    fact_by_id: Mapping[str, ContentSourceFact],
    coverage_by_requirement: Mapping[str, ContentRegulatoryRequirementCoverage],
) -> list[tuple[ContentSemanticDimension, str, str, list[str]]]:
    revision_ids = {section.section_id for section in revision.sections}
    revision_evidence_ids = _revision_evidence_ids(revision)
    document_tokens = _whole_document_tokens(revision)
    issues: list[tuple[ContentSemanticDimension, str, str, list[str]]] = []
    for proposal_section in draftable_planning_sections(proposal.sections):
        if proposal_section.section_id in revision_ids:
            continue
        missing_requirements: list[str] = []
        missing_evidence_ids: list[str] = []
        for requirement_id in proposal_section.regulatory_requirement_ids:
            binding = coverage_by_requirement.get(requirement_id)
            if binding is None:
                continue
            requirement_fact_tokens: set[str] = set()
            for fact_id in binding.source_fact_ids:
                fact = fact_by_id.get(fact_id)
                if fact is not None:
                    requirement_fact_tokens.update(_semantic_tokens(fact.extracted_fact))
            if not _has_required_fact_overlap(
                document_tokens,
                requirement_fact_tokens,
            ):
                missing_requirements.append(requirement_id)
                missing_evidence_ids.extend(
                    evidence_id
                    for evidence_id in binding.evidence_ids
                    if evidence_id in revision_evidence_ids
                )
        if missing_requirements:
            issues.append(
                (
                    "credibility",
                    "whole_document",
                    "Scalony dokument nie zachowuje wymagań: "
                    + ", ".join(missing_requirements)
                    + ".",
                    list(dict.fromkeys(missing_evidence_ids)),
                )
            )
        merged_query_tokens = {
            token for term in proposal_section.query_terms for token in _semantic_tokens(str(term))
        }
        if (
            merged_query_tokens
            and len(document_tokens) < 15
            and not document_tokens.intersection(merged_query_tokens)
        ):
            issues.append(
                (
                    "search_intent_fit",
                    "whole_document",
                    "Scalony dokument nie odpowiada mapie zapytań usuniętej sekcji planu.",
                    [
                        evidence_id
                        for evidence_id in proposal_section.evidence_ids
                        if evidence_id in revision_evidence_ids
                    ],
                )
            )
    return issues


def _whole_document_tokens(revision: ContentDraftRevision) -> set[str]:
    page_assets = revision.page_assets
    values = [
        *(section.heading for section in revision.sections),
        *(section.body_markdown for section in revision.sections),
        *(item.question for item in revision.faq),
        *(item.answer_markdown for item in revision.faq),
        *(item.body_markdown for item in revision.cta_blocks),
    ]
    if page_assets is not None:
        values.extend(
            [
                page_assets.wordpress_title,
                page_assets.meta_title,
                page_assets.meta_description,
                page_assets.h1,
                page_assets.lead,
            ]
        )
    return _semantic_tokens("\n".join(values))


def _revision_evidence_ids(revision: ContentDraftRevision) -> set[str]:
    return {
        evidence_id
        for values in (
            *(section.evidence_ids for section in revision.sections),
            *(item.evidence_ids for item in revision.faq),
            *(item.evidence_ids for item in revision.cta_blocks),
            *(item.evidence_ids for item in revision.internal_links),
            *(item.evidence_ids for item in revision.official_source_references),
        )
        for evidence_id in values
    }


def _has_required_fact_overlap(document_tokens: set[str], fact_tokens: set[str]) -> bool:
    if not fact_tokens:
        return True
    return len(document_tokens & fact_tokens) >= min(3, len(fact_tokens))


def _semantic_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-ząćęłńóśźż0-9]+", value.casefold())
        if len(token) >= 4 and token not in _SEMANTIC_STOPWORDS
    }


def readability_quality_issues(
    revision: ContentDraftRevision,
) -> list[tuple[ContentSemanticDimension, str, str]]:
    """Map deterministic reading-quality gates into semantic review findings.

    Keeps working notes, duplicated paragraphs, thin sections, long sentences,
    unanswered question headings and text walls from passing a semantic review
    as strong when the text still fails the deterministic reading gates. Findings
    feed the next Codex proposal turn, so a repair run cannot repeat the same
    drafting defects.
    """

    dimension_by_code: dict[str, ContentSemanticDimension] = {
        "thin_section": "answer_directness",
        "wall_of_text": "logical_flow",
        "long_sentence": "logical_flow",
        "heading_answer_mismatch": "answer_directness",
        "vague_answer_phrase": "answer_directness",
        "working_note": "credibility",
        "duplicate_paragraph": "repetition",
    }
    return [
        (
            dimension_by_code[issue.code],
            str(section.section_id)
            if (section := _section_by_heading(revision, issue.affected_section)) is not None
            else "whole_document",
            issue.reason,
        )
        for issue in revision_readability_issues(revision.sections)
    ]


def _section_by_heading(
    revision: ContentDraftRevision,
    heading: str,
) -> ContentDraftRevisionSection | None:
    index = build_section_heading_index(
        (str(section.section_id), section.heading) for section in revision.sections
    )
    section_id = index.resolve(heading)
    return next(
        (section for section in revision.sections if str(section.section_id) == section_id),
        None,
    )


def repetition_quality_issues(
    section_bodies: dict[str, str],
) -> list[tuple[ContentSemanticDimension, str, str]]:
    """Return deterministic repetition and drafting-note findings."""
    issues: list[tuple[ContentSemanticDimension, str, str]] = []
    normalized_bodies = [body for body in section_bodies.values() if body]
    if len(normalized_bodies) != len(set(normalized_bodies)):
        issues.append(("repetition", "whole_document", "Dokument zawiera powtórzone całe sekcje."))
    for section_id, body in section_bodies.items():
        paragraphs = [part.strip() for part in re.split(r"\n+", body) if part.strip()]
        if len(paragraphs) > 1 and len(paragraphs) != len(set(paragraphs)):
            issues.append(
                (
                    "repetition",
                    section_id,
                    "Sekcja zawiera powtórzony akapit lub odpowiedź.",
                )
            )
    all_text = "\n".join(section_bodies.values())
    if contains_working_note(all_text):
        issues.append(
            (
                "repetition",
                "whole_document",
                "Dokument zawiera meta-komentarz źródłowy albo notatkę roboczą.",
            )
        )
    return issues


__all__ = [
    "regulatory_quality_issues",
    "repetition_quality_issues",
    "readability_quality_issues",
]
