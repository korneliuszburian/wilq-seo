"""Bounded repair of unmet profile-owned regulatory assertions.

This owner may change a transient draft candidate only.  It never approves,
persists, publishes, or writes to a vendor.  A deterministic fallback appends
only an already approved official fact that is exact for the missing profile
requirement.
"""

from __future__ import annotations

from wilq.codex.app_server import CodexAppServerClientProtocol, CodexAppServerTurnResult
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.initial_full_draft_turn import (
    _RegulatoryAssertionRepairOutput,
    regulatory_assertion_repair_turn_request,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import ContentRegulatoryRequirement
from wilq.content.workflow.planning import ContentPlanningProposal


def repair_regulatory_assertions(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    blocker: ContentInitialDraftBlocker,
    client: CodexAppServerClientProtocol,
    repair_reasons: dict[str, str] | None = None,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | None:
    """Repair only profile-owned failures, falling back to exact approved facts."""

    missing = [
        code
        for code in blocker.source_codes
        if code.startswith(("regulatory_document_assertion:", "requirement:"))
    ]
    if blocker.code not in {"document_scope_mismatch", "draft_assurance_failed"} or not missing:
        return None
    try:
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
        return _grounded_repair_fallback(planning_input, proposal, output, missing)
    if result.status != "completed" or result.output_text is None:
        return _grounded_repair_fallback(planning_input, proposal, output, missing)
    try:
        patch = _RegulatoryAssertionRepairOutput.model_validate_json(result.output_text)
    except ValueError:
        return _grounded_repair_fallback(planning_input, proposal, output, missing)
    replacements = {item.section_id: item.body_markdown for item in patch.sections}
    if len(replacements) != len(patch.sections):
        return _grounded_repair_fallback(planning_input, proposal, output, missing)
    patched = output.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": replacements.get(
                            section.section_id, section.body_markdown
                        )
                    }
                )
                for section in output.sections
            ]
        }
    )
    return (
        ground_unmet_regulatory_assertions(
            patched,
            planning_input=planning_input,
            proposal=proposal,
            missing_codes=missing,
        ),
        _runtime_trace(result),
    )


def _grounded_repair_fallback(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    missing: list[str],
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace] | None:
    grounded = ground_unmet_regulatory_assertions(
        output,
        planning_input=planning_input,
        proposal=proposal,
        missing_codes=missing,
    )
    if grounded == output:
        return None
    return grounded, ContentCodexRuntimeTrace(status="completed")


def ground_unmet_regulatory_assertions(
    output: ContentInitialDraftModelOutput,
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    missing_codes: list[str],
) -> ContentInitialDraftModelOutput:
    """Append one exact approved fact only where an assertion remains unmet."""

    requirement_by_id = {
        item.id: item for item in planning_input.regulatory_coverage.requirements
    }
    sections = {item.section_id: item for item in proposal.sections}
    additions: dict[str, list[str]] = {}
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
        facts = _approved_facts_for_requirement(
            planning_input,
            requirement_id=requirement_id,
            assertion_terms=(
                None
                if requirement_id in semantic_requirement_ids
                else assertion.required_any_of
            ),
        )
        if not facts:
            continue
        target = next(
            (
                section_id
                for section_id, section in sections.items()
                if requirement_id in section.regulatory_requirement_ids
            ),
            None,
        )
        if target is not None:
            additions.setdefault(target, []).extend(facts)
    if not additions:
        return output
    return output.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": section.body_markdown
                        + "\n\n"
                        + "\n\n".join(
                            dict.fromkeys(additions.get(section.section_id, []))
                        )
                    }
                )
                for section in output.sections
            ]
        }
    )


def _approved_facts_for_requirement(
    planning_input: ContentPlanningInput,
    *,
    requirement_id: str,
    assertion_terms: list[str] | None,
) -> list[str]:
    """Return only exact approved facts, optionally narrowed to one assertion."""

    return [
        item.extracted_fact
        for item in planning_input.regulatory_coverage.source_facts
        if item.official_source
        and item.review_status == "approved"
        and requirement_id in item.regulatory_requirement_ids
        and (
            assertion_terms is None
            or any(
                term.lower() in item.extracted_fact.lower()
                for term in assertion_terms
            )
        )
    ]


def _assertion_codes_for_missing_requirements(
    missing_codes: list[str],
    requirement_by_id: dict[str, ContentRegulatoryRequirement],
) -> list[tuple[str, str]]:
    """Expand a semantic requirement failure into profile-owned assertions."""

    assertion_codes: list[tuple[str, str]] = []
    for code in missing_codes:
        if code.startswith("regulatory_document_assertion:"):
            _, requirement_id, assertion_id = code.split(":", 2)
            assertion_codes.append((requirement_id, assertion_id))
        elif code.startswith("requirement:"):
            requirement = requirement_by_id.get(code.removeprefix("requirement:"))
            if requirement is not None:
                assertion_codes.extend(
                    (requirement.id, assertion.id)
                    for assertion in requirement.document_assertions
                )
    return assertion_codes


def _runtime_trace(result: CodexAppServerTurnResult) -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(
        status=result.status,
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        event_methods=list(result.event_methods),
        item_types=list(result.item_types),
        external_call_attempted=result.external_call_attempted,
    )


__all__ = ["ground_unmet_regulatory_assertions", "repair_regulatory_assertions"]
