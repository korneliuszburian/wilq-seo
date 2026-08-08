from __future__ import annotations

from collections.abc import Iterable

from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexSectionProposalBlocker,
    ContentCodexSectionProposalBlockerCode,
)
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftOutput,
    StructuredDraftOutputSection,
    StructuredDraftSectionInput,
)
from wilq.content.workflow.documents.content_html import content_html_from_markdown
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionSection,
)


def contract_with_revision_lineage(
    contract: StructuredDraftGenerationContract,
    *,
    base_revision: ContentDraftRevision,
    selected_headings: list[str],
    selected_cta_ids: list[str] | None = None,
) -> StructuredDraftGenerationContract:
    """Merge exact persisted component evidence into the preview contract only."""

    selected_cta_ids = selected_cta_ids or []
    base_by_heading = {section.heading: section for section in base_revision.sections}
    sections = list(contract.model_input.sections)
    positions = {section.heading: index for index, section in enumerate(sections)}
    for heading in selected_headings:
        base_section = base_by_heading.get(heading)
        if base_section is None:
            continue
        index = positions.get(heading)
        if index is None:
            sections.append(
                StructuredDraftSectionInput(
                    heading=heading,
                    purpose="Selected persisted revision section.",
                    evidence_ids=list(base_section.evidence_ids),
                    section_id=str(base_section.section_id or ""),
                )
            )
            continue
        sections[index] = sections[index].model_copy(
            update={
                "evidence_ids": unique(
                    [*sections[index].evidence_ids, *base_section.evidence_ids]
                )
            }
        )
    if selected_cta_ids:
        cta = next(cta for cta in base_revision.cta_blocks if cta.cta_id == selected_cta_ids[0])
        sections.append(
            StructuredDraftSectionInput(
                heading=f"CTA · {cta.placement}",
                purpose="Selected persisted call to action.",
                evidence_ids=list(cta.evidence_ids),
                section_id=cta.cta_id,
            )
        )
    model_input = contract.model_input.model_copy(update={"sections": sections})
    return contract.model_copy(update={"model_input": model_input})


def item_with_revision_lineage(
    item: ContentWorkItem,
    *,
    base_revision: ContentDraftRevision,
    selected_headings: list[str],
    selected_cta_ids: list[str] | None = None,
) -> ContentWorkItem:
    selected_cta_ids = selected_cta_ids or []
    evidence_ids = [
        evidence_id
        for section in base_revision.sections
        if section.heading in selected_headings
        for evidence_id in section.evidence_ids
    ] + [
        evidence_id
        for cta in base_revision.cta_blocks
        if cta.cta_id in selected_cta_ids
        for evidence_id in cta.evidence_ids
    ]
    return item.model_copy(update={"evidence_ids": unique([*item.evidence_ids, *evidence_ids])})


def component_scope_blocker(
    output: StructuredDraftOutput,
    *,
    base_revision: ContentDraftRevision,
    selected_headings: list[str],
    selected_cta_ids: list[str],
) -> ContentCodexSectionProposalBlocker | None:
    if selected_cta_ids:
        selected_cta = next(
            (cta for cta in base_revision.cta_blocks if cta.cta_id == selected_cta_ids[0]),
            None,
        )
        if (
            selected_cta is not None
            and output.title == base_revision.title
            and not output.sections
            and output.cta.strip()
            and output.source_facts_used == selected_cta.evidence_ids
        ):
            return None
        return blocker(
            "section_scope_mismatch",
            "Codex wyszedł poza wybrane CTA",
            (
                "Wynik musi zmieniać tylko jedno wskazane wezwanie do działania "
                "i zachować jego dowody."
            ),
            "Odrzuć wynik i uruchom propozycję dla aktualnego wyboru.",
        )
    output_headings = [section.heading for section in output.sections]
    base_by_heading = {section.heading: section for section in base_revision.sections}
    evidence_mapping_matches = all(
        section.evidence_ids == base_by_heading[section.heading].evidence_ids
        for section in output.sections
        if section.heading in base_by_heading
    )
    if (
        output.title == base_revision.title
        and output_headings == selected_headings
        and evidence_mapping_matches
    ):
        return None
    return blocker(
        "section_scope_mismatch",
        "Codex wyszedł poza wybrane sekcje",
        "Wynik musi zachować tytuł, wybrane nagłówki, ich kolejność i mapę dowodów.",
        "Odrzuć wynik i uruchom propozycję dla aktualnego wyboru.",
    )


def output_for_contract_validation(
    output: StructuredDraftOutput,
    *,
    base_revision: ContentDraftRevision,
    selected_cta_ids: list[str],
) -> StructuredDraftOutput:
    """Validate a CTA body through the same claim-safety guard as section prose."""

    if not selected_cta_ids:
        return output
    cta = next(cta for cta in base_revision.cta_blocks if cta.cta_id == selected_cta_ids[0])
    return output.model_copy(
        update={
            "sections": [
                StructuredDraftOutputSection(
                    heading=f"CTA · {cta.placement}",
                    body_markdown=output.cta,
                    evidence_ids=cta.evidence_ids,
                    claims_used=[],
                )
            ]
        }
    )


def merge_selected_sections(
    base_revision: ContentDraftRevision,
    output: StructuredDraftOutput,
    selected_headings: list[str],
) -> list[ContentDraftRevisionSection]:
    selected = set(selected_headings)
    generated_by_heading = {section.heading: section for section in output.sections}
    return [
        base_section.model_copy(
            update={
                "body_markdown": generated_by_heading[base_section.heading].body_markdown,
                "content_html": content_html_from_markdown(
                    generated_by_heading[base_section.heading].body_markdown
                ),
            }
        )
        if base_section.heading in selected
        else base_section
        for base_section in base_revision.sections
    ]


def merge_selected_cta_blocks(
    base_revision: ContentDraftRevision,
    output: StructuredDraftOutput,
    selected_cta_ids: list[str],
) -> list[ContentDraftRevisionCtaBlock]:
    selected = set(selected_cta_ids)
    return [
        cta.model_copy(update={"body_markdown": output.cta}) if cta.cta_id in selected else cta
        for cta in base_revision.cta_blocks
    ]


def blocker(
    code: ContentCodexSectionProposalBlockerCode, label: str, reason: str, next_step: str
) -> ContentCodexSectionProposalBlocker:
    return ContentCodexSectionProposalBlocker(
        code=code, label=label, reason=reason, next_step=next_step
    )


def unique(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def proposal_evidence_ids(snapshot: ContentWorkItemWorkflowSnapshotResponse) -> list[str]:
    contract = snapshot.structured_generation.structured_generation_result.contract
    if contract is None:
        return unique(snapshot.preflight.item.evidence_ids)
    return unique(
        [
            *snapshot.preflight.item.evidence_ids,
            *(fact.evidence_id for fact in contract.model_input.source_facts),
            *(
                evidence_id
                for section in contract.model_input.sections
                for evidence_id in section.evidence_ids
            ),
            *(
                evidence_id
                for marker in [
                    *contract.model_input.claim_markers,
                    *contract.model_input.removed_or_blocked_claim_markers,
                ]
                for evidence_id in marker.evidence_ids
            ),
        ]
    )


def proposal_source_connectors(snapshot: ContentWorkItemWorkflowSnapshotResponse) -> list[str]:
    contract = snapshot.structured_generation.structured_generation_result.contract
    if contract is None:
        return unique(snapshot.preflight.item.source_connectors)
    return unique(
        [
            *snapshot.preflight.item.source_connectors,
            *(fact.source_connector for fact in contract.model_input.source_facts),
            *(
                connector
                for marker in [
                    *contract.model_input.claim_markers,
                    *contract.model_input.removed_or_blocked_claim_markers,
                ]
                for connector in marker.source_connectors
            ),
        ]
    )
