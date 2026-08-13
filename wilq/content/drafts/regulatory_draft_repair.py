"""Bounded repair of unmet profile-owned regulatory assertions.

This owner may change a transient draft candidate only.  It never approves,
persists, publishes, or writes to a vendor.  A deterministic fallback uses
only already approved official facts exact for the missing profile requirement.
"""

from __future__ import annotations

import re

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
from wilq.content.drafts.regulatory_repair_policy import regulatory_section_repair_modes
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.reading_quality import _WORKING_NOTE
from wilq.content.regulatory.policy import (
    ContentRegulatoryRequirement,
    regulatory_assertion_matches,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


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
        if code.startswith(("regulatory_document_assertion:", "requirement:"))
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
        patch = _RegulatoryAssertionRepairOutput.model_validate_json(result.output_text)
    except ValueError:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    patches = {item.section_id: item for item in patch.sections}
    if len(patches) != len(patch.sections):
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    if {section_id: item.mode for section_id, item in patches.items()} != expected_modes:
        return _grounded_repair_fallback(
            planning_input,
            proposal,
            output,
            missing,
            replace_semantic_requirements=fallback_requires_replacement,
        )
    patched = output.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": _apply_patch(
                            section.body_markdown,
                            patches.get(section.section_id),
                        )
                    }
                )
                for section in output.sections
            ]
        }
    )
    try:
        validated_patch = ContentInitialDraftModelOutput.model_validate(
            patched.model_dump(mode="json")
        )
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
    return grounded, _runtime_trace(result)


def _apply_patch(existing: str, patch: object | None) -> str:
    """Apply the server-authorized append or replacement for one targeted section."""

    if patch is None:
        return existing
    mode = getattr(patch, "mode", None)
    body_markdown = getattr(patch, "body_markdown", None)
    if not isinstance(body_markdown, str):
        return existing
    if mode == "replace":
        return body_markdown
    if mode != "append" or body_markdown in existing:
        return existing
    return f"{existing}\n\n{body_markdown}"


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
            _document_ready_fact_text(item, protected_terms=protected_terms)
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
                    _document_ready_fact_text(
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


_SOURCE_ATTRIBUTION_PREFIX = re.compile(
    r"^\s*(?:źródło\s+podaje,\s+że\s+|zgodnie\s+z\s+treścią\s+źródła\s+|"
    r"według\s+dostarczonej\s+instrukcji\s+\w+\s*,?\s+|"
    r"zgodnie\s+z\s+oficjalnym\s+źródłem\s+\w+\s*,?\s+|"
    r"oficjalne\s+źródło\s+\w+\s+(?:wskazuje|wyjaśnia),\s+że\s+|"
    r"źródło\s+wskazuje,\s+że\s+|źródło\s+\w+\s+rozróżnia\s+)",
    re.IGNORECASE,
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])")
_TRAILING_VERIFICATION_CLAUSE = re.compile(
    r"\s*(?:,?\s*i\s+)?wymagają?\s+weryfikacj[^.]*\.?\s*$",
    re.IGNORECASE,
)


def _document_ready_fact_text(fact_text: str, *, protected_terms: list[str] | None) -> str:
    """Project one approved review fact into reader-facing document text.

    Strip source-attribution prefixes, drop editorial qualifier sentences
    (e.g. "Wymaga weryfikacji przez człowieka") and trailing verification
    clauses that belong to the review packet, not to the public document.
    Text carrying a required assertion term is never dropped, so grounding
    stays verifiable.
    """

    stripped = _SOURCE_ATTRIBUTION_PREFIX.sub("", fact_text).strip()
    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY.split(stripped)
        if sentence.strip()
    ]
    normalized_terms = [
        term.casefold().strip() for term in (protected_terms or []) if term.strip()
    ]
    kept = [
        sentence
        for sentence in sentences
        if not (
            _WORKING_NOTE.search(sentence)
            and not any(term in sentence.casefold() for term in normalized_terms)
        )
    ]
    result = " ".join(kept) if kept else stripped
    qualifier = _TRAILING_VERIFICATION_CLAUSE.search(result)
    if qualifier and not any(
        term in qualifier.group(0).casefold() for term in normalized_terms
    ):
        result = result[: qualifier.start()].rstrip(" ,;")
    if not result:
        return result
    return result[0].upper() + result[1:]


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
        if code.startswith("regulatory_document_assertion:"):
            _, requirement_id, assertion_id = code.split(":", 2)
            assertion_codes.append((requirement_id, assertion_id))
        elif code.startswith("requirement:"):
            requirement = requirement_by_id.get(code.removeprefix("requirement:"))
            if requirement is not None:
                assertion_codes.extend(
                    (requirement.id, assertion.id) for assertion in requirement.document_assertions
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
