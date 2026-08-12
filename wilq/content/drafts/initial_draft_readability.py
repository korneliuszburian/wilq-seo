from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.initial_full_draft_turn import (
    _RegulatoryAssertionRepairOutput,
    _RegulatorySectionPatch,
    readability_repair_turn_request,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.reading_quality import revision_readability_issues
from wilq.content.quality.semantic_review_guards import repetition_quality_issues
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevisionSection
from wilq.storage.local_state import LocalStateStore

ReadabilityIssue = tuple[str, str, str]
_MAX_REPAIR_TURNS = 2


def readability_issues_for_output(
    output: ContentInitialDraftModelOutput,
) -> list[ReadabilityIssue]:
    revision_targets = [
        (
            section.section_id,
            ContentDraftRevisionSection(
                section_id=section.section_id,
                heading=section.heading,
                body_markdown=section.body_markdown,
            ),
        )
        for section in output.sections
    ]
    for index, faq_item in enumerate(output.faq, start=1):
        section_id = f"faq:{index}"
        revision_targets.append(
            (
                section_id,
                ContentDraftRevisionSection(
                    section_id=section_id,
                    heading=f"FAQ: {faq_item.question}",
                    body_markdown=faq_item.answer_markdown,
                ),
            )
        )
    for index, cta_item in enumerate(output.cta_blocks, start=1):
        section_id = f"cta:{index}"
        revision_targets.append(
            (
                section_id,
                ContentDraftRevisionSection(
                    section_id=section_id,
                    heading=f"CTA: {index}",
                    body_markdown=cta_item.body_markdown,
                ),
            )
        )
    issues = _mapped_revision_readability_issues(revision_targets)
    section_bodies = {section.section_id: section.body_markdown for section in output.sections}
    section_bodies.update(
        {f"faq:{index}": item.answer_markdown for index, item in enumerate(output.faq, start=1)}
    )
    section_bodies.update(
        {
            f"cta:{index}": item.body_markdown
            for index, item in enumerate(output.cta_blocks, start=1)
        }
    )
    issues.extend(_mapped_repetition_issues(section_bodies))
    return issues


def _mapped_revision_readability_issues(
    revision_targets: list[tuple[str, ContentDraftRevisionSection]],
) -> list[ReadabilityIssue]:
    section_ids_by_heading: dict[str, list[str]] = {}
    for section_id, section in revision_targets:
        section_ids_by_heading.setdefault(section.heading, []).append(section_id)
    combined_issues = revision_readability_issues([section for _, section in revision_targets])
    mapped: list[ReadabilityIssue] = [
        (issue.code, section_ids_by_heading[issue.affected_section][0], issue.reason)
        for issue in combined_issues
        if len(section_ids_by_heading[issue.affected_section]) == 1
        and _gate_applies_to_target(
            issue.code,
            section_ids_by_heading[issue.affected_section][0],
        )
    ]
    colliding_headings = {
        heading for heading, section_ids in section_ids_by_heading.items() if len(section_ids) > 1
    }
    for section_id, section in revision_targets:
        if section.heading not in colliding_headings:
            continue
        mapped.extend(
            issue
            for issue in _readability_issues_for_target(
                section_id=section_id,
                heading=section.heading,
                body_markdown=section.body_markdown,
            )
            if _gate_applies_to_target(issue[0], section_id)
        )
    return mapped


def _gate_applies_to_target(code: str, section_id: str) -> bool:
    if section_id.startswith(("faq:", "cta:")):
        return code != "thin_section"
    return True


def _readability_issues_for_target(
    *,
    section_id: str,
    heading: str,
    body_markdown: str,
) -> list[ReadabilityIssue]:
    return [
        (issue.code, section_id, issue.reason)
        for issue in revision_readability_issues(
            [
                ContentDraftRevisionSection(
                    section_id=section_id,
                    heading=heading,
                    body_markdown=body_markdown,
                )
            ]
        )
    ]


def assure_readability_and_repair(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    trace: ContentCodexRuntimeTrace,
    client: CodexAppServerClientProtocol,
    run_store: LocalStateStore,
    output_blocker: Callable[[ContentInitialDraftModelOutput], ContentInitialDraftBlocker | None],
) -> tuple[
    ContentInitialDraftModelOutput,
    ContentCodexRuntimeTrace,
    ContentInitialDraftBlocker | None,
]:
    issues = readability_issues_for_output(output)
    if not issues:
        return output, trace, None
    blocker = output_blocker(output)
    if blocker is not None:
        return output, trace, blocker
    repair_budget = min(
        len({section_id for _, section_id, _ in issues}),
        _MAX_REPAIR_TURNS,
    )
    for _ in range(repair_budget):
        output, trace = _repair_readability_candidate(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            issues=issues,
            client=client,
        )
        issues = readability_issues_for_output(output)
        blocker = output_blocker(output)
        if blocker is not None:
            return output, trace, blocker
        if not issues:
            return output, trace, None
    return output, trace, _readability_blocker(issues)


def _mapped_repetition_issues(
    section_bodies: dict[str, str],
) -> list[ReadabilityIssue]:
    mapped: list[ReadabilityIssue] = []
    for code, affected_section_id, reason in repetition_quality_issues(section_bodies):
        affected_section_ids = (
            [affected_section_id]
            if affected_section_id != "whole_document"
            else _whole_document_issue_sections(section_bodies, code, reason)
        )
        mapped.extend((code, section_id, reason) for section_id in affected_section_ids)
    return mapped


def _whole_document_issue_sections(
    section_bodies: dict[str, str],
    code: str,
    reason: str,
) -> list[str]:
    localized = [
        section_id
        for section_id, body in section_bodies.items()
        if (code, "whole_document", reason) in repetition_quality_issues({section_id: body})
    ]
    if localized:
        return localized
    body_counts = Counter(body for body in section_bodies.values() if body)
    return [section_id for section_id, body in section_bodies.items() if body_counts[body] > 1]


def _repair_readability_candidate(
    *,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    issues: list[ReadabilityIssue],
    client: CodexAppServerClientProtocol,
) -> tuple[ContentInitialDraftModelOutput, ContentCodexRuntimeTrace]:
    expected_section_ids = {section_id for _, section_id, _ in issues}
    try:
        result = client.run_structured_turn(
            readability_repair_turn_request(
                planning_input=planning_input,
                proposal=proposal,
                candidate=output,
                issues=issues,
            )
        )
    except Exception:
        return output, ContentCodexRuntimeTrace(status="failed")
    trace = _runtime_trace(result)
    if result.status != "completed" or result.output_text is None:
        return output, trace
    try:
        repair = _RegulatoryAssertionRepairOutput.model_validate_json(result.output_text)
    except ValueError:
        return output, trace
    patches = {patch.section_id: patch for patch in repair.sections}
    if (
        repair.publish_ready
        or len(patches) != len(repair.sections)
        or set(patches) != expected_section_ids
    ):
        return output, trace
    try:
        return _apply_readability_patches(output, patches), trace
    except ValueError:
        return output, trace


def _apply_readability_patches(
    output: ContentInitialDraftModelOutput,
    patches: dict[str, _RegulatorySectionPatch],
) -> ContentInitialDraftModelOutput:
    patched = output.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "body_markdown": _patched_section_body(
                            section.body_markdown,
                            patches.get(section.section_id),
                        )
                    }
                )
                for section in output.sections
            ],
            "faq": [
                item.model_copy(
                    update={
                        "answer_markdown": _patched_auxiliary_body(
                            item.answer_markdown,
                            patches.get(f"faq:{index}"),
                        )
                    }
                )
                for index, item in enumerate(output.faq, start=1)
            ],
            "cta_blocks": [
                item.model_copy(
                    update={
                        "body_markdown": _patched_auxiliary_body(
                            item.body_markdown,
                            patches.get(f"cta:{index}"),
                        )
                    }
                )
                for index, item in enumerate(output.cta_blocks, start=1)
            ],
        }
    )
    return ContentInitialDraftModelOutput.model_validate(patched.model_dump(mode="json"))


def _patched_section_body(
    existing: str,
    patch: _RegulatorySectionPatch | None,
) -> str:
    if patch is None:
        return existing
    if patch.mode == "replace":
        return patch.body_markdown
    return f"{existing}\n\n{patch.body_markdown}"


def _patched_auxiliary_body(
    existing: str,
    patch: _RegulatorySectionPatch | None,
) -> str:
    if patch is None:
        return existing
    if patch.mode != "replace":
        raise ValueError("FAQ and CTA readability patches must use replace mode.")
    return patch.body_markdown


def _readability_blocker(
    issues: list[ReadabilityIssue],
) -> ContentInitialDraftBlocker:
    return ContentInitialDraftBlocker(
        code="readability_gate_failed",
        label="Tekst zawiera notatki robocze lub błędy czytelności",
        reason="; ".join(f"{section_id}: {reason}" for _, section_id, reason in issues[:3]),
        next_step=(
            "Usuń wskazane notatki robocze i błędy czytelności, a następnie uruchom "
            "nową próbę generowania."
        ),
        source_codes=list(dict.fromkeys(code for code, _, _ in issues)),
    )


def _runtime_trace(result: CodexAppServerTurnResult) -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(
        status=result.status,
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        event_methods=list(result.event_methods),
        item_types=list(result.item_types),
        external_call_attempted=result.external_call_attempted,
    )


__all__ = ["assure_readability_and_repair", "readability_issues_for_output"]
