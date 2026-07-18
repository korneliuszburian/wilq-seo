from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Literal

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningModelOutput
from wilq.content.workflow.planning import ContentPlanningInventoryMapping

SectionMappingStatus = Literal["mapped", "unmapped", "ambiguous"]


def canonicalize_model_inventory_headings(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
) -> ContentPlanningModelOutput:
    """Fill omitted inventory references using a conservative deterministic match."""
    inventory = [section.heading for section in planning_input.inventory.sections]
    if not inventory:
        return output
    used: set[str] = set()
    sections = []
    changed = False
    for section in output.sections:
        if section.inventory_disposition == "create" or section.inventory_heading:
            if section.inventory_heading:
                used.add(section.inventory_heading)
            sections.append(section)
            continue
        match = _best_inventory_heading(section.heading, inventory, used)
        if match is None:
            sections.append(section)
            continue
        sections.append(section.model_copy(update={"inventory_heading": match}))
        used.add(match)
        changed = True
    return output.model_copy(update={"sections": sections}) if changed else output


def build_inventory_mapping(
    planning_input: ContentPlanningInput,
    output: ContentPlanningModelOutput,
    section_ids: list[str],
) -> list[ContentPlanningInventoryMapping]:
    """Map all current inventory rows to the generated plan without guessing."""
    by_inventory_heading: dict[str, list[tuple[int, object]]] = {}
    for index, section in enumerate(output.sections):
        if section.inventory_heading:
            by_inventory_heading.setdefault(section.inventory_heading, []).append((index, section))
    used_plan_indices: set[int] = set()
    mappings: list[ContentPlanningInventoryMapping] = []
    for inventory_section in planning_input.inventory.sections:
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
            for index, section in enumerate(output.sections)
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
        mappings.append(
            ContentPlanningInventoryMapping(
                inventory_section_id=inventory_section.section_id,
                inventory_heading=inventory_section.heading,
                status=status,
                mapped_section_id=section_ids[chosen[1]] if chosen else None,
                mapped_section_heading=chosen[2].heading if chosen else None,
                disposition=chosen[2].inventory_disposition if chosen else None,
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
