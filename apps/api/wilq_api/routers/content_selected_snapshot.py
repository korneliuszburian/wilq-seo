from __future__ import annotations

from fastapi import HTTPException

from wilq.briefing.content_diagnostics import (
    build_content_diagnostics_cached,
    build_content_freshness_assessment_fast,
)
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.decisions.inventory_binding import (
    inventory_decision_for_work_item,
)
from wilq.content.workflow.decisions.planning import ContentPlanningDecision
from wilq.content.workflow.documents.revisions import ContentDraftRevisionState
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.content.workflow.workspace.api import (
    build_content_work_item_snapshot_response_from_selected_decision,
)
from wilq.content.workflow.workspace.document_workspace import (
    content_work_item_has_persisted_material,
)
from wilq.schemas import ContentDecisionItem, ContentFreshnessAssessment


def selected_workspace_snapshot_for_work_item_or_404(
    work_item_id: str,
    *,
    store: ContentWorkflowStore | None = None,
    revision_state: ContentDraftRevisionState | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Build a vendor-free selected projection without entering the planning cache."""

    workflow_store = store if store is not None else content_workflow_store()
    selected = _selected_decision_or_404(work_item_id)
    freshness = build_content_freshness_assessment_fast(
        relevant_connector_ids=selected.source_connectors,
    )
    current_revision = (
        revision_state
        if revision_state is not None
        else workflow_store.load_draft_revision_state(work_item_id)
    )
    planning_decisions = workflow_store.load_planning_decisions(work_item_id)
    snapshot = _build_selected_snapshot(
        selected,
        freshness=freshness,
        revision_state=current_revision,
        planning_decisions=planning_decisions,
    )
    review = workflow_store.latest_human_review(work_item_id)
    if review is None:
        return snapshot
    audit = workflow_store.latest_audit_for_review(review.id)
    return _with_recorded_human_review(
        _build_selected_snapshot(
            selected,
            freshness=freshness,
            revision_state=current_revision,
            planning_decisions=planning_decisions,
            human_review=review,
            audit=audit,
        )
    )


def _selected_decision_or_404(work_item_id: str) -> ContentDecisionItem:
    diagnostics = build_content_diagnostics_cached()
    decision_id = work_item_id.removeprefix("content_work_item_")
    persisted = next(
        (item for item in diagnostics.decision_queue if item.id == decision_id),
        None,
    )
    metadata = inventory_decision_for_work_item(
        work_item_id,
        read_material=False,
        include_all_metric_facts=True,
    )
    selected = persisted if persisted is not None else metadata
    if selected is None:
        raise HTTPException(
            status_code=404,
            detail="Wybrany element pracy nad treścią nie jest dostępny w tym obszarze roboczym.",
        )
    has_persisted_material = content_work_item_has_persisted_material(selected)
    selected = selected.model_copy(
        update={
            "wordpress_content_inventory_status": (
                "available" if has_persisted_material else "missing"
            ),
            "wordpress_content_inventory_note": (
                "Materiał pochodzi z zapisanego snapshotu; ten odczyt nie potwierdza, "
                "że odpowiada on aktualnej treści w WordPressie."
                if has_persisted_material
                else "Bieżący snapshot nie zawiera materiału strony; aktualna treść "
                "w WordPressie nie została w tym odczycie sprawdzona."
            ),
        }
    )
    return selected


def _build_selected_snapshot(
    selected: ContentDecisionItem,
    *,
    freshness: ContentFreshnessAssessment,
    revision_state: ContentDraftRevisionState,
    planning_decisions: list[ContentPlanningDecision],
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    return build_content_work_item_snapshot_response_from_selected_decision(
        selected,
        freshness_assessment=freshness,
        human_review=human_review,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=None,
    )


def _with_recorded_human_review(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentWorkItemWorkflowSnapshotResponse:
    return snapshot.model_copy(
        update={"human_review": snapshot.human_review.model_copy(update={"review_recorded": True})}
    )


__all__ = ["selected_workspace_snapshot_for_work_item_or_404"]
