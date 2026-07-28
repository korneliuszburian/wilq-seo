from __future__ import annotations

import json
from hashlib import sha256

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.workflow.content_html import content_html_from_markdown
from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
)
from wilq.content.workflow.new_page_document import (
    build_new_page_canonical_document_workspace,
)
from wilq.content.workflow.planning import ContentPlanningDecision, ContentPlanningProposal
from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionFaqItem,
    ContentDraftRevisionInternalLink,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionSection,
    ContentDraftRevisionWriteResult,
)
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.schemas import CodexRun


def append_new_page_initial_revision(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    proposal: ContentPlanningProposal,
    decisions: list[ContentPlanningDecision],
    expected_proposal_id: str,
    expected_planning_digest: str,
    expected_planning_input_digest: str,
    output: ContentInitialDraftModelOutput,
    completed_run: CodexRun,
    requested_by: str,
    store: ContentWorkflowStore,
) -> ContentDraftRevisionWriteResult:
    """Append only from the current approved new-page plan; never invent a URL."""

    workspace = build_new_page_canonical_document_workspace(
        brief=brief,
        foundation=foundation,
        proposal=proposal,
        decisions=decisions,
    )
    if (
        workspace is None
        or workspace.status != "ready_for_document"
        or workspace.proposal_id != expected_proposal_id
        or workspace.planning_digest != expected_planning_digest
        or workspace.planning_input_digest != expected_planning_input_digest
    ):
        raise ValueError("New-page plan identity is stale or not approved.")
    if completed_run.status != "completed" or completed_run.completed_at is None:
        raise ValueError("New-page revision requires a completed Codex run.")
    command = _revision_command(
        brief=brief,
        foundation=foundation,
        proposal=proposal,
        output=output,
        codex_run_id=completed_run.id,
        requested_by=requested_by,
    )
    return store.append_draft_revision(command, completed_codex_run=completed_run)


def _revision_command(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    codex_run_id: str,
    requested_by: str,
) -> ContentDraftRevisionAppendCommand:
    plan_sections = draftable_planning_sections(proposal.sections)
    _validate_output_matches_plan(plan_sections, proposal, output)
    sections = _revision_sections(plan_sections, output)
    proposal_id = proposal.proposal_id
    if proposal_id is None or proposal.planning_input_digest is None:
        raise ValueError("New-page revision requires an exact generated proposal.")
    return ContentDraftRevisionAppendCommand(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id=foundation.work_item_id,
        draft_package_id=f"content_new_page_plan_{proposal_id}",
        draft_package_digest=_digest(
            {
                "brief_digest": brief.brief_digest,
                "foundation_id": foundation.foundation_id,
                "planning_digest": proposal.planning_digest,
                "planning_input_digest": proposal.planning_input_digest,
            }
        ),
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
        service_card_id=foundation.service_card_id,
        service_digest=foundation.service_card_digest,
        inventory_digest=_digest({"work_kind": "new_page", "status": "not_applicable"}),
        source_material_ids=_lineage_ids(
            proposal.source_material_ids, sections, "source_material_ids"
        ),
        knowledge_card_ids=_lineage_ids(
            proposal.knowledge_card_ids, sections, "knowledge_card_ids"
        ),
        document_kind="new_page",
        final_canonical_url=None,
        new_page_document_identity=proposal.new_page_document_identity,
        title=output.page_assets.wordpress_title,
        page_assets=output.page_assets,
        sections=sections,
        faq=_revision_faq(proposal, output),
        cta_blocks=_revision_ctas(proposal, output),
        internal_links=_revision_links(proposal, output),
        proposal_metadata=ContentDraftRevisionProposalMetadata(
            codex_run_id=codex_run_id,
            selected_section_headings=[item.heading for item in sections],
            section_lineage=[
                ContentDraftRevisionProposalSectionLineage(
                    heading=item.heading,
                    evidence_ids=item.evidence_ids,
                    claim_ids=item.claim_ids,
                    source_material_ids=item.source_material_ids,
                    knowledge_card_ids=item.knowledge_card_ids,
                )
                for item in sections
            ],
            quality_verdict="ready_for_human_review",
            quality_finding_codes=["semantic_review_required"],
            review_scope="persisted_full_document_and_declared_lineage",
        ),
        created_by=requested_by,
    )


def _validate_output_matches_plan(
    plan_sections: list,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
) -> None:
    if [(section.section_id, section.heading) for section in output.sections] != [
        (section.section_id, section.heading) for section in plan_sections
    ]:
        raise ValueError("New-page output sections do not match the exact approved plan.")
    if [item.question for item in output.faq] != [item.question for item in proposal.faq]:
        raise ValueError("New-page output FAQ does not match the exact approved plan.")
    if len(output.cta_blocks) != len(proposal.cta_blocks):
        raise ValueError("New-page output CTA blocks do not match the exact approved plan.")
    if [item.target_url for item in output.internal_links] != [
        item.target_url for item in proposal.internal_links
    ]:
        raise ValueError("New-page output links do not match the exact approved plan.")


def _revision_sections(
    plan_sections: list,
    output: ContentInitialDraftModelOutput,
) -> list[ContentDraftRevisionSection]:
    return [
        ContentDraftRevisionSection(
            section_id=plan.section_id,
            heading=plan.heading,
            body_markdown=generated.body_markdown,
            content_html=content_html_from_markdown(generated.body_markdown),
            query_terms=plan.query_terms,
            evidence_ids=plan.evidence_ids,
            claim_ids=plan.claim_ids,
            source_material_ids=sorted(set(plan.source_material_ids)),
            knowledge_card_ids=sorted(set(plan.knowledge_card_ids)),
        )
        for plan, generated in zip(plan_sections, output.sections, strict=True)
    ]


def _lineage_ids(
    proposal_ids: list[str],
    sections: list[ContentDraftRevisionSection],
    field: str,
) -> list[str]:
    return sorted(
        {
            *proposal_ids,
            *(item_id for section in sections for item_id in getattr(section, field)),
        }
    )


def _revision_faq(
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
) -> list[ContentDraftRevisionFaqItem]:
    proposal_id = str(proposal.proposal_id)
    return [
        ContentDraftRevisionFaqItem(
            faq_id=f"{proposal_id}_faq_{index:02d}",
            question=plan.question,
            answer_markdown=generated.answer_markdown,
            query_terms=plan.query_terms,
            evidence_ids=plan.evidence_ids,
            claim_ids=plan.claim_ids,
        )
        for index, (plan, generated) in enumerate(zip(proposal.faq, output.faq, strict=True), 1)
    ]


def _revision_ctas(
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
) -> list[ContentDraftRevisionCtaBlock]:
    proposal_id = str(proposal.proposal_id)
    return [
        ContentDraftRevisionCtaBlock(
            cta_id=f"{proposal_id}_cta_{index:02d}",
            placement=_revision_placement(plan.placement, proposal),
            body_markdown=generated.body_markdown,
            evidence_ids=plan.evidence_ids,
            claim_ids=plan.claim_ids,
        )
        for index, (plan, generated) in enumerate(
            zip(proposal.cta_blocks, output.cta_blocks, strict=True), 1
        )
    ]


def _revision_links(
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
) -> list[ContentDraftRevisionInternalLink]:
    proposal_id = str(proposal.proposal_id)
    return [
        ContentDraftRevisionInternalLink(
            link_id=f"{proposal_id}_link_{index:02d}",
            placement=_revision_placement(plan.placement, proposal),
            target_url=plan.target_url,
            anchor_text=generated.anchor_text,
            evidence_ids=plan.evidence_ids,
            claim_ids=plan.claim_ids,
        )
        for index, (plan, generated) in enumerate(
            zip(proposal.internal_links, output.internal_links, strict=True), 1
        )
    ]


def _digest(value: object) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _revision_placement(value: str, proposal: ContentPlanningProposal) -> str:
    allowed = {"after_lead", "after_content", *(item.section_id for item in proposal.sections)}
    if value in allowed:
        return value
    for section in proposal.sections:
        if value == section.heading:
            return section.section_id
    raise ValueError("Approved plan contains an unknown document placement.")


__all__ = ["append_new_page_initial_revision"]
