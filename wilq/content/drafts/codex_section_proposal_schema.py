from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy

from wilq.content.codex_turn import mapping
from wilq.content.drafts.structured_generation import StructuredDraftGenerationContract
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionSection,
)


def proposal_output_schema(
    contract: StructuredDraftGenerationContract,
    *,
    base_revision: ContentDraftRevision,
    selected_headings: list[str],
    selected_cta_ids: list[str] | None = None,
) -> dict[str, object]:
    """Constrain free-form lineage fields to API-owned literal values."""

    schema = deepcopy(contract.output_schema)
    properties = mapping(schema, "properties")
    definitions = mapping(schema, "$defs")
    section_schema = mapping(definitions, "StructuredDraftOutputSection")
    section_properties = mapping(section_schema, "properties")
    sections_schema = mapping(properties, "sections")
    selected_cta_ids = selected_cta_ids or []
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
    # Bind a section's lineage to its heading before the structured turn runs.
    # A shared enum is insufficient for a multi-section proposal: it lets the
    # model place an otherwise allowed evidence id on the wrong section, which
    # the exact-revision guard must then reject after generation completes.
    sections_schema["items"] = (
        section_schema
        if not selected_headings
        else {
            "anyOf": [
                _section_schema_for_heading(
                    section_schema,
                    base_by_heading[heading],
                    claim_marker_by_id={
                        marker.claim_id: (marker.claim_text, marker.evidence_ids)
                        for marker in contract.model_input.claim_markers
                    },
                )
                for heading in selected_headings
            ]
        }
    )
    _set_literals(section_properties, "claims_used", contract.model_input.claims_allowed)
    _set_literals(properties, "source_facts_used", evidence_ids)
    _set_literals(properties, "claims_needing_review", [])
    _set_literals(
        properties,
        "forbidden_claims_avoided",
        contract.model_input.claims_removed_or_blocked,
    )
    if selected_cta_ids:
        _bind_selected_cta(
            properties,
            selected_cta=next(
                cta
                for cta in getattr(base_revision, "cta_blocks", [])
                if cta.cta_id == selected_cta_ids[0]
            ),
        )
    return schema


def _set_const(properties: dict[str, object], key: str, value: str) -> None:
    mapping(properties, key)["const"] = value


def _set_literals(
    properties: dict[str, object],
    key: str,
    values: list[str],
    *,
    scalar: bool = False,
) -> None:
    field_schema = mapping(properties, key)
    if scalar:
        field_schema["enum"] = _unique(values)
        return
    field_schema["items"] = {
        "enum": _unique(values) or ["__WILQ_EMPTY_ARRAY_ONLY__"],
        "type": "string",
    }


def _section_schema_for_heading(
    section_schema: dict[str, object],
    section: ContentDraftRevisionSection,
    *,
    claim_marker_by_id: dict[str, tuple[str, list[str]]],
) -> dict[str, object]:
    schema = deepcopy(section_schema)
    properties = mapping(schema, "properties")
    heading = section.heading
    evidence_ids = _unique(section.evidence_ids)
    _set_const(properties, "heading", heading)
    _set_literals(properties, "evidence_ids", evidence_ids)
    evidence_schema = mapping(properties, "evidence_ids")
    evidence_schema["minItems"] = len(evidence_ids)
    evidence_schema["maxItems"] = len(evidence_ids)
    allowed_claims = _unique(
        claim_marker_by_id[claim_id][0]
        for claim_id in section.claim_ids
        if claim_id in claim_marker_by_id
        and set(claim_marker_by_id[claim_id][1]).issubset(evidence_ids)
    )
    claims_schema = mapping(properties, "claims_used")
    claims_schema["items"] = {
        "enum": allowed_claims or ["__WILQ_EMPTY_ARRAY_ONLY__"],
        "type": "string",
    }
    claims_schema["minItems"] = 0
    claims_schema["maxItems"] = len(allowed_claims)
    return schema


def _bind_selected_cta(
    properties: dict[str, object],
    *,
    selected_cta: ContentDraftRevisionCtaBlock,
) -> None:
    """Keep the generic structured output safely scoped to one persisted CTA."""

    mapping(properties, "cta")["minLength"] = 1
    _set_literals(properties, "source_facts_used", _unique(selected_cta.evidence_ids))
    mapping(properties, "source_facts_used")["minItems"] = len(selected_cta.evidence_ids)
    mapping(properties, "source_facts_used")["maxItems"] = len(selected_cta.evidence_ids)
    for key in ("faq", "internal_links"):
        field_schema = mapping(properties, key)
        field_schema["minItems"] = 0
        field_schema["maxItems"] = 0


def _unique(values: Iterable[object]) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique:
            unique.append(text)
    return unique


__all__ = ["proposal_output_schema"]
