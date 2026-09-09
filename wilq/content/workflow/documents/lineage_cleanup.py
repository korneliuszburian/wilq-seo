from __future__ import annotations

from typing import Literal

from wilq.content.workflow.documents.revision_children import build_child_draft_revision_command
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionCtaBlock,
    ContentDraftRevisionFaqItem,
    ContentDraftRevisionInternalLink,
    ContentDraftRevisionOfficialSourceReference,
    ContentDraftRevisionProposalCtaLineage,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionSection,
    ContentDraftRevisionSourceProvenance,
)

LineageCleanupFailureCode = Literal[
    "lineage_cleanup_unavailable",
    "source_fact_not_found",
    "source_fact_ambiguous",
]


class LineageCleanupBuildError(ValueError):
    def __init__(self, code: LineageCleanupFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def build_lineage_cleanup_command(
    *, base_revision: ContentDraftRevision, source_fact_id: str, requested_by: str
):
    """Create an immutable child without one obsolete source fact's unique lineage."""

    source_fact_id = _visible_identifier(source_fact_id, "source fact")
    requested_by = _visible_identifier(requested_by, "requester")
    if base_revision.schema_version != "wilq_content_draft_revision_v2":
        raise LineageCleanupBuildError(
            "lineage_cleanup_unavailable",
            "Lineage cleanup requires a v2 revision.",
        )

    matching_provenance = [
        item
        for item in base_revision.source_provenance
        if item.source_fact_id == source_fact_id
    ]
    if not matching_provenance:
        raise LineageCleanupBuildError(
            "source_fact_not_found",
            "Lineage cleanup requires one exact persisted source fact.",
        )
    if len(matching_provenance) != 1:
        raise LineageCleanupBuildError(
            "source_fact_ambiguous",
            "More than one provenance record owns the requested source fact.",
        )

    target_provenance = matching_provenance[0]
    target_evidence_ids = _owned_evidence_ids(
        target_provenance.evidence_ids,
        owner="source provenance",
    )
    matching_references = [
        item
        for item in base_revision.official_source_references
        if item.source_fact_id == source_fact_id
    ]
    if len(matching_references) > 1:
        raise LineageCleanupBuildError(
            "source_fact_ambiguous",
            "More than one official reference projects the requested source fact.",
        )
    if matching_references and _owned_evidence_ids(
        matching_references[0].evidence_ids,
        owner="official reference",
    ) != target_evidence_ids:
        raise LineageCleanupBuildError(
            "source_fact_ambiguous",
            "Source provenance and official reference disagree about owned evidence.",
        )

    retained_provenance = [
        item
        for item in base_revision.source_provenance
        if item.source_fact_id != source_fact_id
    ]
    retained_references = [
        item
        for item in base_revision.official_source_references
        if item.source_fact_id != source_fact_id
    ]
    retained_evidence_ids = _retained_evidence_ids(
        provenance=retained_provenance,
        references=retained_references,
    )
    removable_evidence_ids = target_evidence_ids.difference(retained_evidence_ids)

    return build_child_draft_revision_command(
        base_revision,
        sections=_clean_sections(base_revision.sections, removable_evidence_ids),
        source_provenance=retained_provenance,
        faq=_clean_required_evidence(
            base_revision.faq,
            removable_evidence_ids,
            component_name="FAQ",
        ),
        cta_blocks=_clean_required_evidence(
            base_revision.cta_blocks,
            removable_evidence_ids,
            component_name="CTA",
        ),
        internal_links=_clean_required_evidence(
            base_revision.internal_links,
            removable_evidence_ids,
            component_name="link wewnętrzny",
        ),
        official_source_references=retained_references,
        proposal_metadata=_clean_proposal_metadata(
            base_revision.proposal_metadata,
            removable_evidence_ids,
        ),
        correction_reason="lineage_cleanup",
        created_by=requested_by,
    )


def _visible_identifier(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise LineageCleanupBuildError(
            "lineage_cleanup_unavailable",
            f"Lineage cleanup requires a visible {label} identifier.",
        )
    return normalized


def _owned_evidence_ids(evidence_ids: list[str], *, owner: str) -> frozenset[str]:
    if any(not evidence_id.strip() for evidence_id in evidence_ids) or len(
        evidence_ids
    ) != len(set(evidence_ids)):
        raise LineageCleanupBuildError(
            "source_fact_ambiguous",
            f"The {owner} does not declare one unambiguous evidence set.",
        )
    return frozenset(evidence_ids)


def _retained_evidence_ids(
    *,
    provenance: list[ContentDraftRevisionSourceProvenance],
    references: list[ContentDraftRevisionOfficialSourceReference],
) -> frozenset[str]:
    evidence_ids: set[str] = set()
    for item in [*provenance, *references]:
        evidence_ids.update(
            _owned_evidence_ids(item.evidence_ids, owner="retained source lineage")
        )
    return frozenset(evidence_ids)


def _filtered_evidence_ids(
    evidence_ids: list[str], removable_evidence_ids: frozenset[str]
) -> list[str]:
    return [
        evidence_id
        for evidence_id in evidence_ids
        if evidence_id not in removable_evidence_ids
    ]


def _clean_sections(
    sections: list[ContentDraftRevisionSection],
    removable_evidence_ids: frozenset[str],
) -> list[ContentDraftRevisionSection]:
    return [
        section.model_copy(
            update={
                "evidence_ids": _filtered_evidence_ids(
                    section.evidence_ids,
                    removable_evidence_ids,
                )
            }
        )
        for section in sections
    ]


def _clean_required_evidence[
    RequiredEvidenceComponent: (
        ContentDraftRevisionFaqItem
        | ContentDraftRevisionCtaBlock
        | ContentDraftRevisionInternalLink
    )
](
    components: list[RequiredEvidenceComponent],
    removable_evidence_ids: frozenset[str],
    *,
    component_name: str,
) -> list[RequiredEvidenceComponent]:
    cleaned: list[RequiredEvidenceComponent] = []
    for component in components:
        evidence_ids = _filtered_evidence_ids(
            component.evidence_ids,
            removable_evidence_ids,
        )
        if not evidence_ids:
            raise LineageCleanupBuildError(
                "lineage_cleanup_unavailable",
                f"Cleanup would leave {component_name} without required evidence.",
            )
        cleaned.append(component.model_copy(update={"evidence_ids": evidence_ids}))
    return cleaned


def _clean_proposal_metadata(
    metadata: ContentDraftRevisionProposalMetadata | None,
    removable_evidence_ids: frozenset[str],
) -> ContentDraftRevisionProposalMetadata | None:
    if metadata is None:
        return None
    section_lineage = [
        lineage.model_copy(
            update={
                "evidence_ids": _filtered_evidence_ids(
                    lineage.evidence_ids,
                    removable_evidence_ids,
                )
            }
        )
        for lineage in metadata.section_lineage
    ]
    cta_lineage = _clean_cta_lineage(
        metadata.cta_lineage,
        removable_evidence_ids,
    )
    return metadata.model_copy(
        update={"section_lineage": section_lineage, "cta_lineage": cta_lineage}
    )


def _clean_cta_lineage(
    lineage_items: list[ContentDraftRevisionProposalCtaLineage],
    removable_evidence_ids: frozenset[str],
) -> list[ContentDraftRevisionProposalCtaLineage]:
    cleaned = []
    for lineage in lineage_items:
        evidence_ids = _filtered_evidence_ids(
            lineage.evidence_ids,
            removable_evidence_ids,
        )
        if not evidence_ids:
            raise LineageCleanupBuildError(
                "lineage_cleanup_unavailable",
                "Cleanup would leave CTA lineage without required evidence.",
            )
        cleaned.append(lineage.model_copy(update={"evidence_ids": evidence_ids}))
    return cleaned


__all__ = ["LineageCleanupBuildError", "build_lineage_cleanup_command"]
