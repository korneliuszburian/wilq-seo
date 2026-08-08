from __future__ import annotations

import re
from collections.abc import Iterable

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningModelOutput
from wilq.content.planning.section_mapping import build_inventory_mapping
from wilq.content.workflow.decisions.planning import (
    ContentPlanningInventoryMapping,
    ContentPlanningProposal,
)

_HEADING_NOISE_PATTERNS = (
    ("heading_navigation_noise", re.compile(r"^(?:zaufali nam|copyright|menu|więcej)\b", re.I)),
    ("heading_presentation_noise", re.compile(r"^poniżej przedstawiamy\b", re.I)),
    ("heading_promotional_noise", re.compile(r"^dowiedz się więcej .* podczas", re.I)),
    (
        "heading_related_content_noise",
        re.compile(r"^(?:powiązane materiały|zobacz także|materiały powiązane)\b", re.I),
    ),
    (
        "heading_dated_event_noise",
        re.compile(
            r"\b\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|"
            r"sierpnia|września|października|listopada|grudnia)\s+\d{4}\b",
            re.I,
        ),
    ),
)


def planning_output_quality_errors(
    output: ContentPlanningModelOutput,
    *,
    planning_input: ContentPlanningInput | None = None,
) -> list[str]:
    errors = planning_heading_quality_errors(section.heading for section in output.sections)
    if not output.cta_blocks:
        errors.append("missing_cta")
    errors.extend(
        orphaned_placement_quality_errors(
            sections=output.sections,
            placements=placement_values(output.cta_blocks)
            + placement_values(output.internal_links),
        )
    )
    if planning_input is not None and has_exact_query_rows(planning_input) and not any(
        section.query_terms for section in output.sections
    ):
        errors.append("missing_query_assignments")
    return list(dict.fromkeys(errors))


def proposal_quality_errors(proposal: ContentPlanningProposal) -> list[str]:
    errors = planning_heading_quality_errors(section.heading for section in proposal.sections)
    if not proposal.cta_blocks:
        errors.append("missing_cta")
    errors.extend(
        orphaned_placement_quality_errors(
            sections=proposal.sections,
            placements=placement_values(proposal.cta_blocks)
            + placement_values(proposal.internal_links),
        )
    )
    if has_exact_query_rows(proposal.search_demand) and not any(
        section.query_terms for section in proposal.sections
    ):
        errors.append("missing_query_assignments")
    return list(dict.fromkeys(errors))


def expected_inventory_mapping(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> list[ContentPlanningInventoryMapping]:
    return build_inventory_mapping(
        planning_input,
        proposal,
        [section.section_id for section in proposal.sections],
    )


def persisted_inventory_mapping_is_current(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> bool:
    return expected_inventory_mapping(planning_input, proposal) == proposal.inventory_mapping


def inventory_mapping_has_unresolved_rows(proposal: ContentPlanningProposal) -> bool:
    return any(
        mapping.status in {"unmapped", "ambiguous"} for mapping in proposal.inventory_mapping
    )


def remapped_proposal_projection(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> ContentPlanningProposal:
    return proposal.model_copy(
        update={"inventory_mapping": expected_inventory_mapping(planning_input, proposal)}
    )


def has_exact_query_rows(value: object) -> bool:
    if hasattr(value, "query_portfolio"):
        value = value.query_portfolio
    return any(
        bool(getattr(value, field, []))
        for field in ("gsc_query_rows", "ads_term_rows", "keyword_planner_rows")
    )


def orphaned_placement_quality_errors(
    *, sections: Iterable[object], placements: Iterable[str]
) -> list[str]:
    removed_targets = {
        target
        for section in sections
        if getattr(section, "inventory_disposition", None) == "remove_review_required"
        for target in (
            getattr(section, "heading", None),
            getattr(section, "section_id", None),
            getattr(section, "inventory_section_id", None),
        )
        if target
    }
    return ["orphaned_placement"] if removed_targets.intersection(placements) else []


def placement_values(items: Iterable[object]) -> list[str]:
    return [
        placement
        for item in items
        if isinstance(placement := getattr(item, "placement", None), str)
    ]


def planning_heading_quality_errors(headings: Iterable[str]) -> list[str]:
    errors: list[str] = []
    for raw_heading in headings:
        heading = str(raw_heading).strip()
        for code, pattern in _HEADING_NOISE_PATTERNS:
            if pattern.search(heading):
                errors.append(code)
    return list(dict.fromkeys(errors))
