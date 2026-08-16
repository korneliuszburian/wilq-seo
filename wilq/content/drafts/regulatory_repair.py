"""Bounded repair of unmet profile-owned regulatory assertions.

This owner may change a transient draft candidate only.  It never approves,
persists, publishes, or writes to a vendor.  A deterministic fallback uses
only already approved official facts exact for the missing profile requirement.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.codex_turn import mapping, require_all_object_properties, runtime_trace
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.grounding import document_ready_fact_text
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory import turn_context as regulatory_turn_context
from wilq.content.regulatory.policy import (
    ContentRegulatoryRequirement,
    regulatory_assertion_matches,
    regulatory_requirement_assertion_errors,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import validate_no_inline_link

RegulatoryPatchMode = Literal["append", "replace"]


class RegulatorySectionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", title="_RegulatorySectionPatch")

    section_id: str = Field(min_length=1)
    mode: RegulatoryPatchMode
    body_markdown: str = Field(min_length=1)

    @field_validator("body_markdown")
    @classmethod
    def require_visible_text_without_inline_links(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Regulatory repair body cannot be blank.")
        return validate_no_inline_link(value)


class RegulatoryAssertionRepairOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", title="_RegulatoryAssertionRepairOutput")

    sections: list[RegulatorySectionPatch] = Field(min_length=1)
    publish_ready: Literal[False] = False


def regulatory_assertion_code(code: str) -> tuple[str, str] | None:
    """Parse one profile-owned assertion code, or return ``None``."""

    prefix = "regulatory_document_assertion:"
    if not code.startswith(prefix):
        return None
    parts = code.removeprefix(prefix).split(":", 1)
    if len(parts) != 2 or not all(parts):
        return None
    return parts[0], parts[1]


def regulatory_assertion_repair_output_schema(
    section_ids: list[str],
) -> dict[str, object]:
    """Build the bounded turn schema without changing its legacy wire shape."""

    schema = deepcopy(RegulatoryAssertionRepairOutput.model_json_schema())
    require_all_object_properties(schema)
    definitions = mapping(schema, "$defs")
    public_definition_name = RegulatorySectionPatch.__name__
    schema_definition = mapping(definitions, public_definition_name)
    del definitions[public_definition_name]
    legacy_definition_name = "_RegulatorySectionPatch"
    definitions[legacy_definition_name] = schema_definition
    sections = mapping(mapping(schema, "properties"), "sections")
    section_items = mapping(sections, "items")
    section_items["$ref"] = f"#/$defs/{legacy_definition_name}"
    section_properties = mapping(schema_definition, "properties")
    section_id = mapping(section_properties, "section_id")
    section_id["enum"] = section_ids
    sections["minItems"] = len(section_ids)
    sections["maxItems"] = len(section_ids)
    return schema


def validated_patches_by_section(
    output: RegulatoryAssertionRepairOutput,
    *,
    expected_section_ids: Collection[str] | None = None,
    expected_modes: Mapping[str, RegulatoryPatchMode] | None = None,
) -> dict[str, RegulatorySectionPatch] | None:
    """Return one patch per exact target, or reject the complete patch set."""

    patches = {patch.section_id: patch for patch in output.sections}
    if output.publish_ready or len(patches) != len(output.sections):
        return None
    if expected_section_ids is not None and set(patches) != set(expected_section_ids):
        return None
    if expected_modes is not None and {
        section_id: patch.mode for section_id, patch in patches.items()
    } != dict(expected_modes):
        return None
    return patches


def apply_regulatory_patches(
    output: ContentInitialDraftModelOutput,
    patches: Mapping[str, RegulatorySectionPatch],
) -> ContentInitialDraftModelOutput:
    """Apply validated regulatory patches to document sections and revalidate."""

    patched = output.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": _patched_regulatory_section_body(
                            section.body_markdown,
                            patches.get(section.section_id),
                        )
                    }
                )
                for section in output.sections
            ]
        }
    )
    return ContentInitialDraftModelOutput.model_validate(patched.model_dump(mode="json"))


def _patched_regulatory_section_body(
    existing: str,
    patch: RegulatorySectionPatch | None,
) -> str:
    if patch is None:
        return existing
    if patch.mode == "replace":
        return patch.body_markdown
    if patch.mode != "append" or patch.body_markdown in existing:
        return existing
    return f"{existing}\n\n{patch.body_markdown}"


def regulatory_section_repair_modes(
    proposal: ContentPlanningProposal,
    missing_codes: list[str],
    repair_reasons: dict[str, str],
) -> dict[str, RegulatoryPatchMode]:
    """Choose a safe repair mode from server-owned assurance evidence."""

    failed_requirement_ids = {
        constraint_id.removeprefix("requirement:")
        for constraint_id, reason_code in repair_reasons.items()
        if constraint_id.startswith("requirement:") and reason_code != "supported"
    }
    missing_requirement_ids = {
        code.removeprefix("requirement:")
        for code in missing_codes
        if code.startswith("requirement:")
    }
    assertion_requirement_ids = {
        parsed[0]
        for code in missing_codes
        if (parsed := regulatory_assertion_code(code)) is not None
    }
    return {
        section.section_id: (
            "replace"
            if failed_requirement_ids.intersection(section.regulatory_requirement_ids)
            else "append"
        )
        for section in proposal.sections
        if missing_requirement_ids.intersection(section.regulatory_requirement_ids)
        or assertion_requirement_ids.intersection(section.regulatory_requirement_ids)
    }


def regulatory_draft_preflight_errors(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
) -> list[str]:
    requirements = planning_input.regulatory_coverage.requirements
    if not requirements:
        return []
    draftable_sections = draftable_planning_sections(proposal.sections)
    bound_requirement_ids = {
        requirement_id
        for section in draftable_sections
        for requirement_id in section.regulatory_requirement_ids
    }
    missing_bindings = {
        f"regulatory_preflight:missing_section_binding:{requirement.id}"
        for requirement in requirements
        if requirement.id not in bound_requirement_ids
    }
    ungroundable_assertions: set[str] = set()
    missing_plan_assertions: set[str] = set()
    for requirement in requirements:
        bound_sections = [
            section
            for section in draftable_sections
            if requirement.id in section.regulatory_requirement_ids
        ]
        official_facts = regulatory_turn_context.approved_regulatory_source_facts(
            planning_input,
            {requirement.id},
        )
        for assertion in requirement.document_assertions:
            if not any(
                regulatory_assertion_matches(text=fact.extracted_fact, assertion=assertion)
                for fact in official_facts
            ):
                ungroundable_assertions.add(
                    "regulatory_preflight:ungroundable_assertion:"
                    f"{requirement.id}:{assertion.id}"
                )
        section_text = "\n".join(
            "\n".join((section.heading, section.purpose, section.reader_question))
            for section in bound_sections
        )
        for error in regulatory_requirement_assertion_errors(
            requirement=requirement,
            text=section_text,
        ):
            parsed = regulatory_assertion_code(error)
            if parsed is None:
                continue
            missing_plan_assertions.add(
                "regulatory_preflight:missing_plan_assertion:" + ":".join(parsed)
            )
    return [
        *sorted(missing_bindings),
        *sorted(ungroundable_assertions),
        *sorted(missing_plan_assertions),
    ]


def repair_regulatory_assertions(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    blocker: ContentInitialDraftBlocker,
    client: CodexAppServerClientProtocol,
    repair_reasons: dict[str, str] | None = None,
    force_deterministic_replace: bool = False,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | None:
    """Repair only profile-owned failures, falling back to exact approved facts."""

    missing = [
        code
        for code in blocker.source_codes
        if regulatory_assertion_code(code) is not None or code.startswith("requirement:")
    ]
    if blocker.code not in {"document_scope_mismatch", "draft_assurance_failed"} or not missing:
        return None
    expected_modes = regulatory_section_repair_modes(proposal, missing, repair_reasons or {})
    fallback_requires_replacement = "replace" in expected_modes.values()
    if blocker.code == "document_scope_mismatch" or force_deterministic_replace:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=force_deterministic_replace,
        )
    try:
        from wilq.content.drafts.initial_full_draft_turn import (
            regulatory_assertion_repair_turn_request,
        )

        result = client.run_structured_turn(
            regulatory_assertion_repair_turn_request(
                planning_input=planning_input,
                proposal=proposal,
                candidate=output,
                missing_assertion_codes=missing,
                repair_reasons=repair_reasons,
            )
        )
    except Exception:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    if result.status != "completed" or result.output_text is None:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    try:
        patch = RegulatoryAssertionRepairOutput.model_validate_json(result.output_text)
    except ValueError:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    patches = validated_patches_by_section(patch, expected_modes=expected_modes)
    if patches is None:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    try:
        validated_patch = apply_regulatory_patches(output, patches)
        grounded = ground_unmet_regulatory_assertions(
            validated_patch,
            planning_input=planning_input,
            proposal=proposal,
            missing_codes=missing,
        )
    except ValueError:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    return grounded, runtime_trace(result)


def _grounded_repair_fallback(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    missing: list[str],
    *,
    replace_semantic_requirements: bool = False,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | None:
    try:
        grounded = ground_unmet_regulatory_assertions(
            output,
            planning_input=planning_input,
            proposal=proposal,
            missing_codes=missing,
            replace_semantic_requirements=replace_semantic_requirements,
        )
    except ValueError:
        return None
    if grounded == output:
        return None
    return grounded, ContentCodexRuntimeTrace(status="completed")


def ground_unmet_regulatory_assertions(
    output: ContentInitialDraftModelOutput,
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    missing_codes: list[str],
    replace_semantic_requirements: bool = False,
) -> ContentInitialDraftModelOutput:
    """Ground unmet assertions with source facts, replacing only failed semantics.

    Approved regulatory facts are written for human review and may carry
    source-attribution prefixes and editorial qualifiers ("Wymaga weryfikacji
    przez człowieka"). The grounded document is reader-facing, so each fact is
    projected to document-ready text before it can reach a section body.
    """

    requirement_by_id = {item.id: item for item in planning_input.regulatory_coverage.requirements}
    sections = {item.section_id: item for item in proposal.sections}
    additions: dict[str, list[str]] = {}
    replacements: dict[str, list[str]] = {}
    semantic_requirement_ids = {
        code.removeprefix("requirement:")
        for code in missing_codes
        if code.startswith("requirement:")
    }
    for requirement_id, assertion_id in _assertion_codes_for_missing_requirements(
        missing_codes, requirement_by_id
    ):
        requirement = requirement_by_id.get(requirement_id)
        if requirement is None:
            continue
        assertion = next(
            (item for item in requirement.document_assertions if item.id == assertion_id),
            None,
        )
        if assertion is None:
            continue
        target = next(
            (
                section_id
                for section_id, section in sections.items()
                if requirement_id in section.regulatory_requirement_ids
            ),
            None,
        )
        if target is None:
            continue
        current_body = next(
            (
                section.body_markdown
                for section in output.sections
                if section.section_id == target
            ),
            "",
        )
        if not replace_semantic_requirements and regulatory_assertion_matches(
            text=current_body,
            assertion=assertion,
        ):
            # A repair turn between the blocker and grounding already restored
            # the exact concept; appending the fact again would duplicate it.
            continue
        semantic_requirement = requirement_id in semantic_requirement_ids
        protected_terms = (
            sorted(
                {
                    term
                    for item in requirement.document_assertions
                    for term in item.required_any_of
                }
            )
            if semantic_requirement
            else assertion.required_any_of
        )
        facts = [
            document_ready_fact_text(item, protected_terms=protected_terms)
            for item in _approved_facts_for_requirement(
                planning_input,
                requirement_id=requirement_id,
                assertion_terms=(
                    None if semantic_requirement else assertion.required_any_of
                ),
            )
        ]
        facts = list(dict.fromkeys(fact for fact in facts if fact.strip()))
        if not facts:
            continue
        if replace_semantic_requirements and requirement_id in semantic_requirement_ids:
            replacement_facts: list[str] = []
            for covered_requirement_id in sections[target].regulatory_requirement_ids:
                covered_requirement = requirement_by_id.get(covered_requirement_id)
                replacement_facts.extend(
                    document_ready_fact_text(
                        fact,
                        protected_terms=(
                            sorted(
                                {
                                    term
                                    for item in covered_requirement.document_assertions
                                    for term in item.required_any_of
                                }
                            )
                            if covered_requirement is not None
                            else None
                        ),
                    )
                    for fact in _approved_facts_for_requirement(
                        planning_input,
                        requirement_id=covered_requirement_id,
                        assertion_terms=None,
                    )
                )
            replacement_facts = list(
                dict.fromkeys(fact for fact in replacement_facts if fact.strip())
            )
            replacements.setdefault(target, []).extend(replacement_facts)
            continue
        additions.setdefault(target, []).extend(facts)
    if not additions and not replacements:
        return output
    patched = output.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": _grounded_section_body(
                            section.body_markdown,
                            additions.get(section.section_id, []),
                            replacements.get(section.section_id, []),
                        )
                    }
                )
                for section in output.sections
            ]
        }
    )
    return ContentInitialDraftModelOutput.model_validate(patched.model_dump(mode="json"))


def _grounded_section_body(
    existing: str,
    additions: list[str],
    replacements: list[str],
) -> str:
    """Keep literal repairs additive; remove failed semantic prose before fallback."""

    if replacements:
        return "\n\n".join(dict.fromkeys(replacements))
    if additions:
        return existing + "\n\n" + "\n\n".join(dict.fromkeys(additions))
    return existing


def _approved_facts_for_requirement(
    planning_input: ContentPlanningInput,
    *,
    requirement_id: str,
    assertion_terms: list[str] | None,
) -> list[str]:
    """Return only exact approved facts, optionally narrowed to one assertion."""

    return [
        item.extracted_fact
        for item in regulatory_turn_context.approved_regulatory_source_facts(
            planning_input,
            {requirement_id},
        )
        if (
            assertion_terms is None
            or any(term.lower() in item.extracted_fact.lower() for term in assertion_terms)
        )
    ]


def _assertion_codes_for_missing_requirements(
    missing_codes: list[str],
    requirement_by_id: dict[str, ContentRegulatoryRequirement],
) -> list[tuple[str, str]]:
    """Expand a semantic requirement failure into profile-owned assertions."""

    assertion_codes: list[tuple[str, str]] = []
    for code in missing_codes:
        parsed = regulatory_assertion_code(code)
        if parsed is not None:
            assertion_codes.append(parsed)
        elif code.startswith("requirement:"):
            requirement = requirement_by_id.get(code.removeprefix("requirement:"))
            if requirement is not None:
                assertion_codes.extend(
                    (requirement.id, assertion.id) for assertion in requirement.document_assertions
                )
    return assertion_codes


__all__ = [
    "RegulatoryAssertionRepairOutput",
    "RegulatoryPatchMode",
    "RegulatorySectionPatch",
    "apply_regulatory_patches",
    "ground_unmet_regulatory_assertions",
    "regulatory_assertion_code",
    "regulatory_assertion_repair_output_schema",
    "regulatory_draft_preflight_errors",
    "regulatory_section_repair_modes",
    "repair_regulatory_assertions",
    "validated_patches_by_section",
]
