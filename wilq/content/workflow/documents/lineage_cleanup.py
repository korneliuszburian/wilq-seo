from __future__ import annotations

from wilq.content.workflow.documents.revision_children import build_child_draft_revision_command
from wilq.content.workflow.documents.revisions import ContentDraftRevision


def build_lineage_cleanup_command(
    *, base_revision: ContentDraftRevision, source_fact_id: str, requested_by: str
):
    removed = [item for item in base_revision.source_provenance if item.source_fact_id == source_fact_id]
    if len(removed) != 1:
        raise ValueError("Lineage cleanup requires one exact persisted source fact.")
    evidence_ids = set(removed[0].evidence_ids)
    without_evidence = lambda item: item.model_copy(
        update={"evidence_ids": [value for value in item.evidence_ids if value not in evidence_ids]}
    )
    return build_child_draft_revision_command(
        base_revision,
        sections=[without_evidence(item) for item in base_revision.sections],
        source_provenance=[item for item in base_revision.source_provenance if item.source_fact_id != source_fact_id],
        faq=[without_evidence(item) for item in base_revision.faq],
        cta_blocks=[without_evidence(item) for item in base_revision.cta_blocks],
        internal_links=[without_evidence(item) for item in base_revision.internal_links],
        official_source_references=[item for item in base_revision.official_source_references if item.source_fact_id != source_fact_id],
        proposal_metadata=base_revision.proposal_metadata,
        correction_reason="lineage_cleanup",
        created_by=requested_by,
    )
