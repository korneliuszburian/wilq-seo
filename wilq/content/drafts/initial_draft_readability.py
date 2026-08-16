from __future__ import annotations

import re
from collections import Counter

from wilq.codex.app_server import CodexAppServerClientProtocol
from wilq.content.codex_turn import runtime_trace
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
)
from wilq.content.drafts.initial_full_draft_turn import readability_repair_turn_request
from wilq.content.drafts.regulatory_patch import (
    RegulatoryAssertionRepairOutput,
    apply_readability_patches,
    validated_patches_by_section,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality.reading_quality import revision_readability_issues
from wilq.content.quality.semantic_review_guards import repetition_quality_issues
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevisionSection

ReadabilityIssue = tuple[str, str, str]


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
    issues.extend(_reader_visible_short_target_issues(output))
    return issues


def _reader_visible_short_target_issues(
    output: ContentInitialDraftModelOutput,
) -> list[ReadabilityIssue]:
    targets = {
        "page_assets:wordpress_title": output.page_assets.wordpress_title,
        "page_assets:meta_title": output.page_assets.meta_title,
        "page_assets:meta_description": output.page_assets.meta_description,
        "page_assets:h1": output.page_assets.h1,
        "page_assets:lead": output.page_assets.lead,
    }
    targets.update(
        {
            f"link:{index}": item.anchor_text
            for index, item in enumerate(output.internal_links, start=1)
        }
    )
    return [
        ("working_note", target_id, reason)
        for target_id, text in targets.items()
        if (reason := _working_note_reason(target_id, text)) is not None
    ]


def _working_note_reason(target_id: str, text: str) -> str | None:
    readability_issues = revision_readability_issues(
        [
            ContentDraftRevisionSection(
                section_id=target_id,
                heading=target_id,
                body_markdown=text,
            )
        ]
    )
    for issue in readability_issues:
        if issue.code == "working_note":
            return issue.reason
    for _, affected_section_id, reason in repetition_quality_issues({target_id: text.casefold()}):
        if affected_section_id == "whole_document":
            return reason
    return None


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
    if re.match(r"^(?:faq|cta):\d+$", section_id):
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
    trace = runtime_trace(result)
    if result.status != "completed" or result.output_text is None:
        return output, trace
    try:
        repair = RegulatoryAssertionRepairOutput.model_validate_json(result.output_text)
    except ValueError:
        return output, trace
    patches = validated_patches_by_section(
        repair,
        expected_section_ids=expected_section_ids,
    )
    if patches is None:
        return output, trace
    try:
        return apply_readability_patches(output, patches), trace
    except ValueError:
        return output, trace


__all__ = ["readability_issues_for_output"]
