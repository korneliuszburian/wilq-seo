from __future__ import annotations

from fastapi import HTTPException

from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
from wilq.content.canonical.urls import content_normalized_path, content_normalized_url
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.planning.decisions import (
    content_decision_metric_tiles,
    content_decision_metrics,
    content_decision_summary,
    content_decision_title,
)
from wilq.content.planning.generated_proposal_store import (
    content_planning_proposal_store,
)
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.api import (
    build_content_work_item_blocked_snapshot_response_for_work_item,
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_diagnostics_snapshot_response_for_work_item,
)
from wilq.content.workflow.contracts import (
    ContentWorkItemSnapshotResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.demand_evidence import content_query_is_planning_signal
from wilq.content.workflow.planning import ContentPlanningDecision
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import ContentDiagnosticsResponse
from wilq.storage.metric_store import metric_store


def snapshot_for_work_item_or_404(
    work_item_id: str,
    *,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    planning_decisions_override: list[ContentPlanningDecision] | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    diagnostics = diagnostics_with_exact_gsc_demand(work_item_id)
    store = content_workflow_store()
    revision_state = store.load_draft_revision_state(work_item_id)
    planning_decisions = (
        store.load_planning_decisions(work_item_id)
        if planning_decisions_override is None
        else planning_decisions_override
    )
    generated_planning_proposal = content_planning_proposal_store().latest(work_item_id)
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
        human_review=human_review,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=generated_planning_proposal,
    )
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="Content work item is not available for the gated workflow.",
        )
    review = store.latest_human_review(work_item_id)
    if human_review is None and review is not None:
        audit_record = store.latest_audit_for_review(review.id)
        snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
            diagnostics,
            work_item_id,
            human_review=review,
            audit=audit_record,
            revision_state=revision_state,
            planning_decisions=planning_decisions,
            generated_planning_proposal=generated_planning_proposal,
        )
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail="Content work item is not available after review lookup.",
            )
    return snapshot


def snapshot_for_default_work_item_or_404() -> ContentWorkItemWorkflowSnapshotResponse:
    diagnostics = build_content_diagnostics_cached()
    default_snapshot = build_content_work_item_diagnostics_snapshot_response(diagnostics)
    return snapshot_for_work_item_or_404(default_snapshot.preflight.item.id)


def snapshot_for_work_item_or_blocked_or_404(
    work_item_id: str,
) -> ContentWorkItemSnapshotResponse:
    diagnostics = diagnostics_with_exact_gsc_demand(work_item_id)
    store = content_workflow_store()
    revision_state = store.load_draft_revision_state(work_item_id)
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
        revision_state=revision_state,
        planning_decisions=store.load_planning_decisions(work_item_id),
    )
    if snapshot is not None:
        review = store.latest_human_review(work_item_id)
        if review is None:
            return snapshot
        audit_record = store.latest_audit_for_review(review.id)
        reviewed_snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
            diagnostics,
            work_item_id,
            human_review=review,
            audit=audit_record,
            revision_state=revision_state,
            planning_decisions=store.load_planning_decisions(work_item_id),
        )
        return snapshot if reviewed_snapshot is None else reviewed_snapshot
    blocked_snapshot = build_content_work_item_blocked_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
    )
    if blocked_snapshot is not None:
        return blocked_snapshot
    raise HTTPException(
        status_code=404,
        detail="Content work item is not available for the gated workflow.",
    )


def diagnostics_with_exact_gsc_demand(
    work_item_id: str,
) -> ContentDiagnosticsResponse:
    diagnostics = build_content_diagnostics_cached()
    decision_id = work_item_id.removeprefix("content_work_item_")
    decision = next(
        (item for item in diagnostics.decision_queue if item.id == decision_id),
        None,
    )
    if decision is None or not decision.page:
        return diagnostics
    current_evidence_ids = set(decision.evidence_ids)
    exact_facts = [
        fact
        for fact in metric_store().list_metric_facts_for_content_url(
            ["google_search_console"],
            content_normalized_url(decision.page),
            content_path=content_normalized_path(decision.page),
        )
        if fact.evidence_id in current_evidence_ids
        and content_query_is_planning_signal(fact.dimensions.get("query", ""))
    ]
    if not exact_facts:
        return diagnostics
    queries = list(
        dict.fromkeys(fact.dimensions["query"] for fact in exact_facts)
    )
    metrics = content_decision_metrics(exact_facts, queries)
    wordpress_match = decision.wordpress_match or "missing"
    enriched_decision = decision.model_copy(
        update={
            "title": content_decision_title(
                decision.decision_type,
                decision.page,
                len(queries),
                metrics,
            ),
            "summary": content_decision_summary(
                decision.decision_type,
                metrics,
                wordpress_match,
                wordpress_title_or_h1=decision.wordpress_title_or_h1,
                wordpress_section_headings=decision.wordpress_section_headings,
            ),
            "metric_tiles": content_decision_metric_tiles(
                decision.decision_type,
                metrics,
                len(queries),
                wordpress_match,
                wordpress_section_count=decision.wordpress_section_count,
                wordpress_section_inventory_status=(
                    decision.wordpress_section_inventory_status
                ),
            ),
            "queries": queries,
            "query_count": len(queries),
            "primary_query": metrics.primary_query,
            "total_clicks": metrics.total_clicks,
            "total_impressions": metrics.total_impressions,
            "aggregate_ctr": metrics.aggregate_ctr,
            "best_average_position": metrics.best_average_position,
            "metric_facts": exact_facts,
        }
    )
    return diagnostics.model_copy(
        update={
            "decision_queue": [
                enriched_decision if item.id == decision_id else item
                for item in diagnostics.decision_queue
            ]
        }
    )
