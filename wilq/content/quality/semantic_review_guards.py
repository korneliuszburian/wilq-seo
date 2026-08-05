from __future__ import annotations

import re

from wilq.content.drafts.initial_full_draft_scope import (
    bind_draftable_planning_sections,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.semantic_review_contracts import ContentSemanticDimension
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import ContentDraftRevision

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
) -> list[tuple[ContentSemanticDimension, str, str]]:
    coverage = planning_input.regulatory_coverage
    if coverage is None:
        return []
    fact_by_id = {fact.source_id: fact for fact in coverage.source_facts}
    coverage_by_requirement = {
        item.requirement_id: item for item in coverage.requirement_coverage
    }
    proposal_by_id = bind_draftable_planning_sections(
        proposal.sections,
        revision.sections,
    )
    issues: list[tuple[ContentSemanticDimension, str, str]] = []
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
        for requirement_id in requirement_ids:
            binding = coverage_by_requirement.get(requirement_id)
            if binding is None:
                continue
            for fact_id in binding.source_fact_ids:
                fact = fact_by_id.get(fact_id)
                if fact is not None:
                    fact_tokens.update(_semantic_tokens(fact.extracted_fact))
        if fact_tokens and len(body_tokens & fact_tokens) < 3:
            issues.append(
                (
                    "credibility",
                    str(revision_section.section_id),
                    (
                        "Sekcja regulacyjna nie zachowuje wystarczającego "
                        "pokrycia zatwierdzonych source facts."
                    ),
                )
            )
        query_tokens = {
            token
            for term in proposal_section.query_terms
            for token in _semantic_tokens(str(term))
        }
        if query_tokens and len(body_tokens) < 15 and not body_tokens.intersection(query_tokens):
            issues.append(
                (
                    "search_intent_fit",
                    str(revision_section.section_id),
                    "Sekcja nie odpowiada zatwierdzonej mapie zapytań.",
                )
            )
    return issues


def _semantic_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-ząćęłńóśźż0-9]+", value.casefold())
        if len(token) >= 4 and token not in _SEMANTIC_STOPWORDS
    }


def repetition_quality_issues(
    section_bodies: dict[str, str],
) -> list[tuple[ContentSemanticDimension, str, str]]:
    """Return deterministic repetition and drafting-note findings."""
    issues: list[tuple[ContentSemanticDimension, str, str]] = []
    normalized_bodies = [body for body in section_bodies.values() if body]
    if len(normalized_bodies) != len(set(normalized_bodies)):
        issues.append(
            ("repetition", "whole_document", "Dokument zawiera powtórzone całe sekcje.")
        )
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
    if any(
        marker in all_text
        for marker in (
            "źródło wskazuje",
            "informacja wymaga weryfikacji",
            "[do uzupełnienia]",
        )
    ):
        issues.append(
            (
                "repetition",
                "whole_document",
                "Dokument zawiera meta-komentarz źródłowy albo notatkę roboczą.",
            )
        )
    return issues


__all__ = ["regulatory_quality_issues", "repetition_quality_issues"]
