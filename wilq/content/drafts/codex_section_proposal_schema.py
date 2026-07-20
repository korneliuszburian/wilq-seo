from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import cast

from wilq.content.drafts.structured_generation import StructuredDraftGenerationContract
from wilq.content.workflow.revisions import ContentDraftRevision


def proposal_output_schema(
    contract: StructuredDraftGenerationContract,
    *,
    base_revision: ContentDraftRevision,
    selected_headings: list[str],
) -> dict[str, object]:
    """Constrain free-form lineage fields to API-owned literal values."""

    schema = deepcopy(contract.output_schema)
    properties = _mapping(schema, "properties")
    definitions = _mapping(schema, "$defs")
    section_schema = _mapping(definitions, "StructuredDraftOutputSection")
    section_properties = _mapping(section_schema, "properties")
    sections_schema = _mapping(properties, "sections")
    base_by_heading = {section.heading: section for section in base_revision.sections}
    evidence_ids = _unique(
        evidence_id
        for heading in selected_headings
        for evidence_id in base_by_heading[heading].evidence_ids
    )

    _set_const(properties, "title", base_revision.title)
    _set_const(properties, "h1", base_revision.title)
    # The proposal is a selected-section child revision, not a second full
    # draft.  Bound the array itself so the model cannot return duplicate or
    # unselected section objects that only fail after the turn completes.
    sections_schema["minItems"] = len(selected_headings)
    sections_schema["maxItems"] = len(selected_headings)
    _set_literals(section_properties, "heading", selected_headings, scalar=True)
    _set_literals(section_properties, "evidence_ids", evidence_ids)
    _set_literals(section_properties, "claims_used", contract.model_input.claims_allowed)
    _set_literals(properties, "source_facts_used", evidence_ids)
    _set_literals(properties, "claims_needing_review", [])
    _set_literals(
        properties,
        "forbidden_claims_avoided",
        contract.model_input.claims_removed_or_blocked,
    )
    return schema


def _mapping(value: dict[str, object], key: str) -> dict[str, object]:
    nested = value.get(key)
    if not isinstance(nested, dict):
        raise RuntimeError(f"Structured output schema is missing {key}.")
    return cast(dict[str, object], nested)


def _set_const(properties: dict[str, object], key: str, value: str) -> None:
    _mapping(properties, key)["const"] = value


def _set_literals(
    properties: dict[str, object],
    key: str,
    values: list[str],
    *,
    scalar: bool = False,
) -> None:
    field_schema = _mapping(properties, key)
    if scalar:
        field_schema["enum"] = _unique(values)
        return
    field_schema["items"] = {
        "enum": _unique(values) or ["__WILQ_EMPTY_ARRAY_ONLY__"],
        "type": "string",
    }


def _unique(values: Iterable[object]) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique:
            unique.append(text)
    return unique


__all__ = ["proposal_output_schema"]
