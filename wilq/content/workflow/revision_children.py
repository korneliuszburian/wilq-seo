from __future__ import annotations

from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionSection,
)


def build_child_draft_revision_command(
    base_revision: ContentDraftRevision,
    *,
    sections: list[ContentDraftRevisionSection],
    proposal_metadata: ContentDraftRevisionProposalMetadata,
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
        final_canonical_url=base_revision.final_canonical_url,
        title=base_revision.title,
        page_assets=base_revision.page_assets,
        sections=sections,
        faq=base_revision.faq,
        cta_blocks=base_revision.cta_blocks,
        internal_links=base_revision.internal_links,
        proposal_metadata=proposal_metadata,
        created_by=created_by,
    )
