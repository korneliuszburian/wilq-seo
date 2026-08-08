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
