from __future__ import annotations

from wilq.content.drafts.initial_full_draft_document import (
    official_source_references_for_planning_input,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revision_children import build_child_draft_revision_command
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
)


def build_official_source_lineage_rebase_command(
    *,
    base_revision: ContentDraftRevision,
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    requested_by: str,
) -> ContentDraftRevisionAppendCommand:
    """Append the same document with current, server-derived official lineage.

    This narrow workflow is for an unreviewed v2 document created before the
    official-source projection existed. It never accepts source links from the
    caller and it does not rewrite the immutable base revision.
    """

    if base_revision.schema_version != "wilq_content_draft_revision_v2":
        raise ValueError("Official-source lineage rebase requires a v2 revision.")
    if base_revision.official_source_references:
        raise ValueError("Revision already records official-source lineage.")
    if (
        base_revision.planning_input_digest is None
        or base_revision.service_card_id is None
        or base_revision.planning_digest is None
        or planning_input.planning_input_digest != base_revision.planning_input_digest
        or planning_input.confirmed_service_card_id != base_revision.service_card_id
        or proposal.planning_digest != base_revision.planning_digest
        or proposal.planning_input_digest != base_revision.planning_input_digest
        or proposal.service_card_id != base_revision.service_card_id
    ):
        raise ValueError("Current planning identity does not match the base revision.")
    references = official_source_references_for_planning_input(planning_input)
    if not references:
        raise ValueError("Current planning input does not require official-source lineage.")
    return build_child_draft_revision_command(
        base_revision,
        sections=base_revision.sections,
        cta_blocks=base_revision.cta_blocks,
        official_source_references=references,
        proposal_metadata=base_revision.proposal_metadata,
        correction_reason="official_source_lineage_rebase",
        created_by=requested_by,
    )


__all__ = ["build_official_source_lineage_rebase_command"]
