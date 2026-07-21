from __future__ import annotations

import json
from hashlib import sha256

from pydantic import BaseModel

from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.content_html import content_html_from_markdown
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionFaqItem,
    ContentDraftRevisionInternalLink,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionSection,
    content_draft_package_digest,
)
from wilq.schemas import CodexRun


def build_initial_draft_revision_command(
    *,
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
    request: ContentInitialDraftRequest,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    output: ContentInitialDraftModelOutput,
    run: CodexRun,
    base_revision_id: str | None = None,
) -> ContentDraftRevisionAppendCommand:
    package = snapshot.draft_package.draft_package_result.draft_package
    if package is None:
        raise ValueError("Initial draft preflight passed without a draft package.")
    sections = [
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
        for plan, generated in zip(
            draftable_planning_sections(proposal.sections), output.sections, strict=True
        )
    ]
    return ContentDraftRevisionAppendCommand(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id=planning_input.work_item_id,
        base_revision_id=base_revision_id,
        draft_package_id=package.id,
        draft_package_digest=content_draft_package_digest(package),
        planning_digest=proposal.planning_digest,
        planning_input_digest=planning_input.planning_input_digest,
        service_card_id=planning_input.confirmed_service_card_id,
        service_digest=_service_digest(planning_input),
        inventory_digest=_digest(planning_input.inventory),
        source_material_ids=sorted(
            {
                source_material_id
                for fact in planning_input.source_facts
                for source_material_id in fact.source_material_ids
            }
        ),
        knowledge_card_ids=sorted(set(planning_input.knowledge_card_ids)),
        final_canonical_url=planning_input.final_canonical_url,
        title=output.page_assets.wordpress_title,
        page_assets=output.page_assets,
        sections=sections,
        faq=_revision_faq(proposal, output),
        cta_blocks=_revision_ctas(proposal, output),
        internal_links=_revision_links(proposal, output),
        proposal_metadata=ContentDraftRevisionProposalMetadata(
            codex_run_id=run.id,
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
        created_by=request.requested_by,
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
        for index, (plan, generated) in enumerate(
            zip(proposal.faq, output.faq, strict=True), start=1
        )
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
            zip(proposal.cta_blocks, output.cta_blocks, strict=True), start=1
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
            zip(proposal.internal_links, output.internal_links, strict=True), start=1
        )
    ]


def _revision_placement(value: str, proposal: ContentPlanningProposal) -> str:
    allowed = {"after_lead", "after_content", *(item.section_id for item in proposal.sections)}
    if value in allowed:
        return value
    for section in proposal.sections:
        if value == section.heading:
            return section.section_id
    raise ValueError("Approved plan contains an unknown document placement.")


def _service_digest(planning_input: ContentPlanningInput) -> str:
    selected = next(
        item
        for item in planning_input.service_candidates
        if item.service_card_id == planning_input.confirmed_service_card_id
    )
    return _digest(
        {
            "service": selected,
            "service_label": planning_input.service_label,
            "knowledge_card_ids": planning_input.knowledge_card_ids,
            "claim_ledger": planning_input.claim_ledger,
        }
    )


def _digest(value: object) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=lambda item: item.model_dump(mode="json"),
        ).encode("utf-8")
    ).hexdigest()


__all__ = ["build_initial_draft_revision_command"]
