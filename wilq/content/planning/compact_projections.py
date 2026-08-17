from __future__ import annotations

from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal

PROPOSAL_EDITORIAL_KEYS = frozenset(
    {
        "work_item_id",
        "planning_digest",
        "proposal_id",
        "planning_input_digest",
        "final_canonical_url",
        "service_card_id",
        "service_label",
        "target_reader",
        "buyer_problem",
        "buyer_trigger",
        "search_intent",
        "angle",
        "value_proposition",
        "cta_direction",
        "sections",
        "faq",
        "cta_blocks",
        "internal_links",
        "evidence_ids",
        "source_connectors",
        "source_material_ids",
        "knowledge_card_ids",
    }
)

_DRAFTABLE_SECTION_KEYS = (
    "section_id",
    "heading",
    "purpose",
    "reader_question",
    "query_terms",
    "evidence_ids",
    "regulatory_requirement_ids",
)


def compact_proposal(
    proposal: ContentPlanningProposal,
    *,
    draftable_sections_only: bool,
) -> dict[str, object]:
    """Keep the approved editorial contract without replaying inventory telemetry."""

    payload = proposal.model_dump(mode="json", exclude_none=True)
    projected = {key: value for key, value in payload.items() if key in PROPOSAL_EDITORIAL_KEYS}
    if not draftable_sections_only:
        return projected

    proposal_sections = getattr(proposal, "sections", [])
    draftable_ids = {
        section.get("section_id") if isinstance(section, dict) else section.section_id
        for section in draftable_planning_sections(proposal_sections)
    }
    projected["sections"] = [
        {
            key: section[key]
            for key in _DRAFTABLE_SECTION_KEYS
            if key in section
        }
        for section in payload.get("sections", [])
        if section.get("section_id") in draftable_ids
    ]
    return projected


def compact_initial_draft_planning_input(
    planning_input: ContentPlanningInput,
) -> dict[str, object]:
    """Keep draft transport useful without replaying connector bookkeeping."""

    payload = planning_input.model_dump(mode="json", exclude_none=True)
    assessments = payload.get("source_assessments")
    if isinstance(assessments, list):
        compact_assessments: list[object] = []
        assessment_keys = {
            "source",
            "status",
            "reason",
            "landing_match_tiers",
            "evidence_ids",
            "knowledge_card_ids",
            "refresh_run_id",
            "settlement_state",
            "quality_state",
            "interpretation_caveats",
        }
        for assessment in assessments:
            if isinstance(assessment, dict):
                compact_assessments.append(
                    {key: value for key, value in assessment.items() if key in assessment_keys}
                )
            else:
                compact_assessments.append(assessment)
        payload["source_assessments"] = compact_assessments

    comparisons = payload.get("metric_comparisons")
    if isinstance(comparisons, list):
        compact_comparisons: list[object] = []
        comparison_keys = {
            "source_connector",
            "status",
            "baseline_period",
            "comparison_period",
            "metric_names",
            "evidence_ids",
            "reason",
        }
        for comparison in comparisons:
            if isinstance(comparison, dict):
                compact_comparisons.append(
                    {key: value for key, value in comparison.items() if key in comparison_keys}
                )
            else:
                compact_comparisons.append(comparison)
        payload["metric_comparisons"] = compact_comparisons

    return payload


def compact_semantic_review_planning_input(
    planning_input: ContentPlanningInput,
) -> dict[str, object]:
    """Project only the plan facts needed to assess one immutable document."""

    payload = planning_input.model_dump(mode="json", exclude_none=True)
    allowed = {
        "planning_input_digest",
        "work_item_id",
        "final_canonical_url",
        "service_label",
        "target_reader",
        "buyer_problem",
        "buyer_trigger",
        "search_intent",
        "source_facts",
        "regulatory_coverage",
        "query_portfolio",
        "claim_ledger",
        "baseline_cta_direction",
        "evidence_ids",
        "source_connectors",
    }
    projected = {key: value for key, value in payload.items() if key in allowed}
    coverage = projected.get("regulatory_coverage")
    if isinstance(coverage, dict):
        projected["regulatory_coverage"] = _compact_regulatory_coverage(coverage)
    return projected


def _compact_regulatory_coverage(coverage: dict[str, object]) -> dict[str, object]:
    """Keep legal assertions and lineage while dropping duplicate model fields."""

    allowed = {
        "profile_id",
        "profile_version",
        "requirements",
        "requirement_coverage",
        "source_fact_ids",
        "evidence_ids",
    }
    projected = {key: coverage[key] for key in allowed if key in coverage}
    source_facts = coverage.get("source_facts", [])
    if not isinstance(source_facts, list):
        raise RuntimeError("Semantic review regulatory coverage source facts must be a list.")
    projected["source_facts"] = [
        {
            key: fact[key]
            for key in (
                "source_id",
                "source_url_or_path",
                "extracted_fact",
                "scope",
                "freshness_date",
                "review_status",
                "evidence_ids",
                "regulatory_requirement_ids",
                "official_source",
            )
            if key in fact
        }
        for fact in source_facts
        if isinstance(fact, dict)
    ]
    return projected


__all__ = [
    "PROPOSAL_EDITORIAL_KEYS",
    "compact_initial_draft_planning_input",
    "compact_proposal",
    "compact_semantic_review_planning_input",
]
