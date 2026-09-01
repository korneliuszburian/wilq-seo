from __future__ import annotations

from dataclasses import dataclass

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision


@dataclass(frozen=True, slots=True)
class SemanticInputs:
    revision: ContentDraftRevision
    planning_input: ContentPlanningInput
    proposal: ContentPlanningProposal


def revision_evidence_ids(revision: ContentDraftRevision) -> list[str]:
    return list(
        dict.fromkeys(
            evidence_id
            for values in (
                *(item.evidence_ids for item in revision.sections),
                *(item.evidence_ids for item in revision.faq),
                *(item.evidence_ids for item in revision.cta_blocks),
                *(item.evidence_ids for item in revision.internal_links),
            )
            for evidence_id in values
        )
    )
