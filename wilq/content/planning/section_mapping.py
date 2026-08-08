from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Literal, cast

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
    ContentPlanningModelSection,
)
from wilq.content.planning.input_sources import ContentPlanningInventorySection
from wilq.content.workflow.decisions.planning import (
    ContentPlanningInventoryMapping,
    ContentPlanningProposal,
    ContentPlanningSection,
)

SectionMappingStatus = Literal["mapped", "unmapped", "ambiguous", "excluded"]
PlanSection = ContentPlanningModelSection | ContentPlanningSection
PlanSectionReference = tuple[int, PlanSection]


def canonicalize_model_inventory_headings(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> ContentPlanningModelOutput:
    """Fill omitted inventory references using a conservative deterministic match."""
    inventory = [section.heading for section in planning_input.inventory.sections]
    inventory_by_id = {
        section.section_id: section.heading for section in planning_input.inventory.sections
    }
    inventory_ids_by_heading: dict[str, list[str]] = {}
    for inventory_section in planning_input.inventory.sections:
        inventory_ids_by_heading.setdefault(inventory_section.heading, []).append(
            inventory_section.section_id
        )
    if not inventory:
        return output
    used: set[str] = set()
    sections = []
    changed = False
    for section in output.sections:
        if section.inventory_disposition == "create":
            if section.inventory_heading is not None or section.inventory_section_id is not None:
                sections.append(
                    section.model_copy(
                        update={"inventory_heading": None, "inventory_section_id": None}
                    )
                )
                changed = True
            else:
                sections.append(section)
            continue
        if section.inventory_section_id in inventory_by_id:
            heading = inventory_by_id[section.inventory_section_id]
            if section.inventory_heading != heading:
                sections.append(
                    section.model_copy(update={"inventory_heading": heading})
                )
                changed = True
            else:
                sections.append(section)
            used.add(heading)
            continue
        if section.inventory_heading:
            used.add(section.inventory_heading)
            matching_ids = inventory_ids_by_heading.get(section.inventory_heading, [])
            if len(matching_ids) == 1 and section.inventory_section_id != matching_ids[0]:
                sections.append(
                    section.model_copy(
                        update={"inventory_section_id": matching_ids[0]}
                    )
                )
                changed = True
            else:
                sections.append(section)
            continue
        match = _best_inventory_heading(section.heading, inventory, used)
        if match is None:
            sections.append(section)
            continue
        matching_ids = inventory_ids_by_heading.get(match, [])
        update = {"inventory_heading": match}
        if len(matching_ids) == 1:
            update["inventory_section_id"] = matching_ids[0]
        sections.append(section.model_copy(update=update))
        used.add(match)
        changed = True
    return output.model_copy(update={"sections": sections}) if changed else output


def build_inventory_mapping(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput | ContentPlanningProposal,
    section_ids: list[str],
) -> list[ContentPlanningInventoryMapping]:
    """Map all current inventory rows to the generated plan without guessing."""
    output_sections = cast(
        list[PlanSection],
        output.sections,
    )
    by_inventory_id, by_inventory_heading = _index_inventory_references(output_sections)
    used_plan_indices: set[int] = set()
    inventory_reasons = _inventory_exclusion_reasons(planning_input)
    return [
        _inventory_mapping_row(
            inventory_section=inventory_section,
            output_sections=output_sections,
            section_ids=section_ids,
            by_inventory_id=by_inventory_id,
            by_inventory_heading=by_inventory_heading,
            used_plan_indices=used_plan_indices,
            exclusion_reason=inventory_reasons[inventory_section.section_id],
        )
        for inventory_section in planning_input.inventory.sections
    ]


def _index_inventory_references(
    output_sections: list[PlanSection],
) -> tuple[
    dict[str, list[PlanSectionReference]],
    dict[str, list[PlanSectionReference]],
]:
    by_inventory_id: dict[str, list[PlanSectionReference]] = {}
    by_inventory_heading: dict[str, list[PlanSectionReference]] = {}
    for index, section in enumerate(output_sections):
        if section.inventory_section_id:
            by_inventory_id.setdefault(section.inventory_section_id, []).append((index, section))
        if section.inventory_heading:
            by_inventory_heading.setdefault(section.inventory_heading, []).append((index, section))
    return by_inventory_id, by_inventory_heading


def _inventory_mapping_row(
    *,
    inventory_section: ContentPlanningInventorySection,
    output_sections: list[PlanSection],
    section_ids: list[str],
    by_inventory_id: dict[str, list[PlanSectionReference]],
    by_inventory_heading: dict[str, list[PlanSectionReference]],
    used_plan_indices: set[int],
    exclusion_reason: str,
) -> ContentPlanningInventoryMapping:
    if exclusion_reason == "navigation_or_promotional_inventory":
        return _unmapped_inventory_row(inventory_section, "excluded", exclusion_reason)
    direct = _one_unused(
        by_inventory_id.get(inventory_section.section_id, []), used_plan_indices
    ) or _one_unused(by_inventory_heading.get(inventory_section.heading, []), used_plan_indices)
    if direct is not None:
        index, section = direct
        used_plan_indices.add(index)
        status, reason = _mapped_status(section, inventory_section.heading)
        return _mapped_inventory_row(inventory_section, section_ids[index], section, status, reason)
    return _similar_inventory_row(
        inventory_section,
        output_sections=output_sections,
        section_ids=section_ids,
        used_plan_indices=used_plan_indices,
        exclusion_reason=exclusion_reason,
    )


def _one_unused(
    candidates: list[PlanSectionReference],
    used_plan_indices: set[int],
) -> PlanSectionReference | None:
    if len(candidates) == 1 and candidates[0][0] not in used_plan_indices:
        return candidates[0]
    return None


def _mapped_inventory_row(
    inventory_section: ContentPlanningInventorySection,
    section_id: str,
    section: PlanSection,
    status: SectionMappingStatus,
    reason: str,
) -> ContentPlanningInventoryMapping:
    return ContentPlanningInventoryMapping(
        inventory_section_id=inventory_section.section_id,
        inventory_heading=inventory_section.heading,
        status=status,
        mapped_section_id=section_id,
        mapped_section_heading=section.heading,
        disposition=section.inventory_disposition,
        reason=reason,
        evidence_ids=inventory_section.evidence_ids,
    )


def _unmapped_inventory_row(
    inventory_section: ContentPlanningInventorySection,
    status: SectionMappingStatus,
    reason: str,
) -> ContentPlanningInventoryMapping:
    return ContentPlanningInventoryMapping(
        inventory_section_id=inventory_section.section_id,
        inventory_heading=inventory_section.heading,
        status=status,
        mapped_section_id=None,
        mapped_section_heading=None,
        disposition="remove_review_required" if status == "excluded" else None,
        reason=reason,
        evidence_ids=inventory_section.evidence_ids,
    )


def _similar_inventory_row(
    inventory_section: ContentPlanningInventorySection,
    *,
    output_sections: list[PlanSection],
    section_ids: list[str],
    used_plan_indices: set[int],
    exclusion_reason: str,
) -> ContentPlanningInventoryMapping:
    candidates = sorted(
        (
            (score, index, section)
            for index, section in enumerate(output_sections)
            if section.inventory_disposition != "create" and index not in used_plan_indices
            for score in [_heading_similarity(inventory_section.heading, section.heading)]
            if score >= 0.72
        ),
        reverse=True,
        key=lambda item: item[0],
    )
    ambiguous = len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.05
    chosen = None if not candidates or ambiguous else candidates[0]
    if chosen is None:
        return _unmapped_inventory_row(
            inventory_section,
            "excluded" if exclusion_reason else "ambiguous" if ambiguous else "unmapped",
            exclusion_reason,
        )
    _, index, section = chosen
    used_plan_indices.add(index)
    status, model_reason = _mapped_status(section, inventory_section.heading)
    reason = exclusion_reason
    if status == "excluded" and not reason:
        reason = model_reason
    return _mapped_inventory_row(
        inventory_section,
        section_ids[index],
        section,
        status,
        reason,
    )


def _inventory_exclusion_reasons(
    planning_input: ContentPlanningInput,
) -> dict[str, str]:
    """Treat a detected related/testimonial tail as page chrome as a unit."""

    reasons: dict[str, str] = {}
    footer_tail = False
    for section in planning_input.inventory.sections:
        direct_reason = _excluded_reason(section.heading)
        if _starts_footer_tail(section.heading):
            footer_tail = True
        reason = direct_reason
        if footer_tail and not reason:
            reason = "navigation_or_promotional_inventory"
        reasons[section.section_id] = reason
    return reasons


def _starts_footer_tail(heading: str) -> bool:
    normalized = _normalize_heading(heading)
    return normalized.startswith(
        (
            "zaufali nam",
            "moze cie rowniez zainteresowac",
            "oferta ",
        )
    )


def _mapped_status(
    section: ContentPlanningModelSection | ContentPlanningSection,
    inventory_heading: str,
) -> tuple[SectionMappingStatus, str]:
    if section.inventory_disposition == "remove_review_required":
        return "excluded", _excluded_reason(inventory_heading) or "model_remove_review_required"
    return "mapped", ""


def _best_inventory_heading(
    heading: str,
    inventory: list[str],
    used: set[str],
) -> str | None:
    candidates = [
        (score, candidate)
        for candidate in inventory
        if candidate not in used
        for score in [_heading_similarity(heading, candidate)]
        if score >= 0.72
    ]
    candidates.sort(reverse=True, key=lambda item: item[0])
    if not candidates or (len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.05):
        return None
    return candidates[0][1]


def _heading_similarity(left: str, right: str) -> float:
    left_tokens = set(_heading_tokens(left))
    right_tokens = set(_heading_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    sequence = SequenceMatcher(None, _normalize_heading(left), _normalize_heading(right)).ratio()
    return max(overlap, sequence)


def _heading_tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", _normalize_heading(value)) if len(token) > 2]


def _excluded_reason(heading: str) -> str:
    normalized = _normalize_heading(heading)
    if re.search(r"\b(?:19|20)\d{2}\b", normalized) or re.search(
        r"\b\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|"
        r"sierpnia|wrzesnia|pazdziernika|listopada|grudnia)\b",
        normalized,
    ):
        return "dated_or_event_inventory"
    if normalized.startswith(
        (
            "ponizej przedstawiamy",
            "zaufali nam",
            "moze cie rowniez zainteresowac",
            "dowiedz sie wiecej",
            "sprawdz co ci grozi",
        )
    ):
        return "navigation_or_promotional_inventory"
    return ""


def _normalize_heading(value: str) -> str:
    ascii_value = "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", ascii_value)).strip()


__all__ = [
    "ContentPlanningInventoryMapping",
    "build_inventory_mapping",
    "canonicalize_model_inventory_headings",
]
