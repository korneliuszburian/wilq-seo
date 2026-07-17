from __future__ import annotations

from fastapi import HTTPException

from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
from wilq.connectors.google_ads.ad_landing_pages import (
    ADS_DEMAND_INPUT_FACT_NAMES,
)
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.content.canonical.landing_identity import (
    LandingPageCandidate,
    landing_page_metric_lookup_path,
    landing_page_metric_lookup_urls,
    match_landing_page,
)
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.planning.generated_proposal_store import (
    content_planning_proposal_store,
)
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.ads_demand_source import (
    content_diagnostics_with_ads_refresh,
    latest_ads_refresh,
)
from wilq.content.workflow.api import (
    build_content_work_item_blocked_snapshot_response_for_work_item,
    build_content_work_item_diagnostics_snapshot_response,
    build_content_work_item_diagnostics_snapshot_response_for_work_item,
)
from wilq.content.workflow.contracts import (
    ContentWorkItemSnapshotResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.demand_evidence import (
    CONTENT_ADS_TERM_METRIC_NAMES,
    content_query_is_planning_signal,
)
from wilq.content.workflow.exact_demand_decision import (
    content_decision_with_exact_demand,
)
from wilq.content.workflow.planning import ContentPlanningDecision
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import (
    ContentDiagnosticsResponse,
    MetricFact,
    connector_refresh_has_live_data,
)
from wilq.storage.exact_metric_batch import list_exact_metric_batch
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
        snapshot = _with_recorded_human_review(snapshot)
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
        return (
            snapshot
            if reviewed_snapshot is None
            else _with_recorded_human_review(reviewed_snapshot)
        )
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


def _with_recorded_human_review(
    snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentWorkItemWorkflowSnapshotResponse:
    return snapshot.model_copy(
        update={
            "human_review": snapshot.human_review.model_copy(
                update={"review_recorded": True}
            )
        }
    )


def diagnostics_with_exact_gsc_demand(
    work_item_id: str,
) -> ContentDiagnosticsResponse:
    diagnostics = build_content_diagnostics_cached()
    diagnostics = content_diagnostics_with_ads_refresh(
        diagnostics,
        latest_ads_refresh(
            diagnostics,
            list_connector_refresh_runs(connector_id="google_ads"),
        ),
    )
    decision_id = work_item_id.removeprefix("content_work_item_")
    decision = next(
        (item for item in diagnostics.decision_queue if item.id == decision_id),
        None,
    )
    if decision is None or not decision.page:
        return diagnostics
    current_evidence_ids = set(decision.evidence_ids)
    candidate_facts = [
        fact
        for lookup_url in landing_page_metric_lookup_urls(decision.page)
        for fact in metric_store().list_metric_facts_for_content_url(
            ["google_search_console"],
            lookup_url,
            content_path=landing_page_metric_lookup_path(decision.page),
        )
    ]
    exact_facts = [
        fact
        for fact in {
            candidate.model_dump_json(): candidate for candidate in candidate_facts
        }.values()
        if fact.evidence_id in current_evidence_ids
        and match_landing_page(
            decision.page,
            LandingPageCandidate(
                candidate_id=fact.evidence_id,
                url=fact.dimensions.get("page"),
            ),
        ).matched
        and content_query_is_planning_signal(fact.dimensions.get("query", ""))
    ]
    if not exact_facts:
        return diagnostics
    ads_facts = _latest_ads_demand_facts(diagnostics)
    enriched_decision = content_decision_with_exact_demand(
        decision,
        gsc_facts=exact_facts,
        ads_facts=ads_facts,
    )
    return diagnostics.model_copy(
        update={
            "decision_queue": [
                enriched_decision if item.id == decision_id else item
                for item in diagnostics.decision_queue
            ]
        }
    )


def _latest_ads_demand_facts(
    diagnostics: ContentDiagnosticsResponse,
) -> list[MetricFact]:
    latest = next(
        (
            refresh
            for refresh in diagnostics.latest_refreshes
            if refresh.connector_id == "google_ads"
        ),
        None,
    )
    if latest is None or not connector_refresh_has_live_data(latest):
        return []
    evidence_id = latest.evidence_ids[-1] if latest.evidence_ids else None
    if evidence_id is None:
        return []
    allowed_names = CONTENT_ADS_TERM_METRIC_NAMES | ADS_DEMAND_INPUT_FACT_NAMES
    return list_exact_metric_batch(
        metric_store(),
        connector_id="google_ads",
        evidence_id=evidence_id,
        metric_names=allowed_names,
    )
