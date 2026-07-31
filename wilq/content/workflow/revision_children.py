from __future__ import annotations

from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionCorrectionReason,
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionOfficialSourceReference,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionSection,
)


def build_child_draft_revision_command(
    base_revision: ContentDraftRevision,
    *,
    sections: list[ContentDraftRevisionSection],
    cta_blocks: list[ContentDraftRevisionCtaBlock] | None = None,
    official_source_references: list[ContentDraftRevisionOfficialSourceReference] | None = None,
    proposal_metadata: ContentDraftRevisionProposalMetadata | None,
    correction_reason: ContentDraftRevisionCorrectionReason | None = None,
    created_by: str,
) -> ContentDraftRevisionAppendCommand:
    if base_revision.planning_digest is None:
        raise ValueError("A child revision requires an exact planning binding.")
    return ContentDraftRevisionAppendCommand(
        schema_version=base_revision.schema_version,
        work_item_id=base_revision.work_item_id,
        base_revision_id=base_revision.revision_id,
        draft_package_id=base_revision.draft_package_id,
        draft_package_digest=base_revision.draft_package_digest,
        planning_digest=base_revision.planning_digest,
        planning_input_digest=base_revision.planning_input_digest,
        service_card_id=base_revision.service_card_id,
        service_digest=base_revision.service_digest,
        inventory_digest=base_revision.inventory_digest,
        source_material_ids=base_revision.source_material_ids,
        knowledge_card_ids=base_revision.knowledge_card_ids,
        document_kind=base_revision.document_kind,
        final_canonical_url=base_revision.final_canonical_url,
        new_page_document_identity=base_revision.new_page_document_identity,
        title=base_revision.title,
        page_assets=base_revision.page_assets,
        sections=sections,
        faq=base_revision.faq,
        cta_blocks=base_revision.cta_blocks if cta_blocks is None else cta_blocks,
        internal_links=base_revision.internal_links,
        official_source_references=(
            base_revision.official_source_references
            if official_source_references is None
            else official_source_references
        ),
        proposal_metadata=proposal_metadata,
        correction_reason=correction_reason,
        created_by=created_by,
    )
