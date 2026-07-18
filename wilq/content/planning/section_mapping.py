from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Literal

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningModelOutput
from wilq.content.workflow.planning import ContentPlanningInventoryMapping

SectionMappingStatus = Literal["mapped", "unmapped", "ambiguous", "excluded"]


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
    output: object,
    section_ids: list[str],
) -> list[ContentPlanningInventoryMapping]:
    """Map all current inventory rows to the generated plan without guessing."""
    output_sections = getattr(output, "sections", [])
    by_inventory_id: dict[str, list[tuple[int, object]]] = {}
    by_inventory_heading: dict[str, list[tuple[int, object]]] = {}
    for index, section in enumerate(output_sections):
        if section.inventory_section_id:
            by_inventory_id.setdefault(section.inventory_section_id, []).append((index, section))
        if section.inventory_heading:
            by_inventory_heading.setdefault(section.inventory_heading, []).append((index, section))
    used_plan_indices: set[int] = set()
    mappings: list[ContentPlanningInventoryMapping] = []
    for inventory_section in planning_input.inventory.sections:
        explicit_id = by_inventory_id.get(inventory_section.section_id, [])
        if len(explicit_id) == 1 and explicit_id[0][0] not in used_plan_indices:
            index, section = explicit_id[0]
            used_plan_indices.add(index)
            mappings.append(
                ContentPlanningInventoryMapping(
                    inventory_section_id=inventory_section.section_id,
                    inventory_heading=inventory_section.heading,
                    status="mapped",
                    mapped_section_id=section_ids[index],
                    mapped_section_heading=section.heading,
                    disposition=section.inventory_disposition,
                    evidence_ids=inventory_section.evidence_ids,
                )
            )
            continue
        explicit = by_inventory_heading.get(inventory_section.heading, [])
        if len(explicit) == 1 and explicit[0][0] not in used_plan_indices:
            index, section = explicit[0]
            used_plan_indices.add(index)
            mappings.append(
                ContentPlanningInventoryMapping(
                    inventory_section_id=inventory_section.section_id,
                    inventory_heading=inventory_section.heading,
                    status="mapped",
                    mapped_section_id=section_ids[index],
                    mapped_section_heading=section.heading,
                    disposition=section.inventory_disposition,
                    evidence_ids=inventory_section.evidence_ids,
                )
            )
            continue
        candidates = [
            (score, index, section)
            for index, section in enumerate(output_sections)
            if section.inventory_disposition != "create" and index not in used_plan_indices
            for score in [_heading_similarity(inventory_section.heading, section.heading)]
            if score >= 0.72
        ]
        candidates.sort(reverse=True, key=lambda item: item[0])
        status: SectionMappingStatus = "unmapped"
        chosen: tuple[float, int, object] | None = None
        if candidates:
            chosen = candidates[0]
            if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.05:
                status = "ambiguous"
                chosen = None
            else:
                status = "mapped"
                used_plan_indices.add(chosen[1])
        reason = _excluded_reason(inventory_section.heading)
        if chosen is None and reason:
            status = "excluded"
        mappings.append(
            ContentPlanningInventoryMapping(
                inventory_section_id=inventory_section.section_id,
                inventory_heading=inventory_section.heading,
                status=status,
                mapped_section_id=section_ids[chosen[1]] if chosen else None,
                mapped_section_heading=chosen[2].heading if chosen else None,
                disposition=(
                    chosen[2].inventory_disposition
                    if chosen
                    else "remove_review_required"
                    if status == "excluded"
                    else None
                ),
                reason=reason,
                evidence_ids=inventory_section.evidence_ids,
            )
        )
    return mappings


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
