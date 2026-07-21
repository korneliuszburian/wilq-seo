from __future__ import annotations

from threading import RLock
from time import monotonic

from fastapi import HTTPException

from wilq.briefing.content_diagnostics import (
    build_content_diagnostics_cached,
    build_content_freshness_assessment_fast,
)
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
from wilq.content.planning.generated_proposal import read_content_planning_proposal
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
from wilq.content.workflow.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.planning import ContentPlanningDecision
from wilq.content.workflow.revisions import ContentDraftRevisionState
from wilq.content.workflow.store import content_workflow_store
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    MetricFact,
    connector_refresh_has_live_data,
)
from wilq.storage.exact_metric_batch import list_exact_metric_batch
from wilq.storage.metric_store import metric_store

# Exact demand enrichment is a read-only projection of the already cached
# diagnostics.  Keep it briefly per work item so dashboard polling does not
# repeat the same GSC/Ads scans, while a refreshed base diagnostics object
# naturally invalidates the entry.
_EXACT_DIAGNOSTICS_CACHE_SECONDS = 15.0
_exact_diagnostics_cache: dict[
    str, tuple[float, int, str | None, ContentDiagnosticsResponse]
] = {}
_exact_diagnostics_cache_lock = RLock()

_SELECTED_INVENTORY_FIELDS = (
    "title",
    "summary",
    "wordpress_title_or_h1",
    "wordpress_section_headings",
    "wordpress_section_count",
    "wordpress_section_inventory_status",
    "wordpress_content_summary",
    "wordpress_content_text",
    "wordpress_content_source_kind",
    "wordpress_content_extraction_region",
    "wordpress_content_material_confidence",
    "wordpress_content_source_field_lineage",
    "wordpress_content_word_count",
    "wordpress_content_inventory_status",
    "wordpress_content_inventory_note",
    "wordpress_acf_section_inventory_status",
    "wordpress_acf_section_inventory_note",
    "wordpress_acf_section_headings",
    "wordpress_acf_section_count",
)


def _merge_selected_inventory_fields(
    existing: ContentDecisionItem,
    selected: ContentDecisionItem,
) -> ContentDecisionItem:
    """Enrich a diagnostics row without replacing its freshness authority."""

    updates = {
        field: getattr(selected, field)
        for field in _SELECTED_INVENTORY_FIELDS
        if getattr(selected, field) is not None
    }
    if selected.metric_facts:
        facts_by_key = {
            fact.model_dump_json(): fact
            for fact in [*existing.metric_facts, *selected.metric_facts]
        }
        updates["metric_facts"] = list(facts_by_key.values())
    updates["source_connectors"] = list(
        dict.fromkeys([*existing.source_connectors, *selected.source_connectors])
    )
    updates["evidence_ids"] = list(dict.fromkeys([*existing.evidence_ids, *selected.evidence_ids]))
    return existing.model_copy(update=updates)


def snapshot_for_work_item_or_404(
    work_item_id: str,
    *,
    human_review: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
    planning_decisions_override: list[ContentPlanningDecision] | None = None,
    diagnostics_override: ContentDiagnosticsResponse | None = None,
    revision_state_override: ContentDraftRevisionState | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    diagnostics = diagnostics_override or diagnostics_with_exact_gsc_demand(work_item_id)
    store = content_workflow_store()
    revision_state = (
        revision_state_override
        if revision_state_override is not None
        else store.load_draft_revision_state(work_item_id)
    )
    planning_decisions = (
        store.load_planning_decisions(work_item_id)
        if planning_decisions_override is None
        else planning_decisions_override
    )
    proposal_store = content_planning_proposal_store()
    snapshot = build_content_work_item_diagnostics_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
        human_review=human_review,
        audit=audit,
        revision_state=revision_state,
        planning_decisions=planning_decisions,
        generated_planning_proposal=None,
    )
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="Content work item is not available for the gated workflow.",
        )
    generated_response = read_content_planning_proposal(
        snapshot=snapshot,
        store=proposal_store,
    )
    generated_planning_proposal = (
        generated_response.proposal
        if generated_response.status in {"ready", "idempotent", "created"}
        else None
    )
    if generated_planning_proposal is not None:
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
                detail="Content work item is not available after planning lookup.",
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
    planning_decisions = store.load_planning_decisions(work_item_id)
    blocked_snapshot = build_content_work_item_blocked_snapshot_response_for_work_item(
        diagnostics,
        work_item_id,
    )
    if blocked_snapshot is not None:
        return blocked_snapshot
    return snapshot_for_work_item_or_404(
        work_item_id,
        diagnostics_override=diagnostics,
        revision_state_override=revision_state,
        planning_decisions_override=planning_decisions,
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
    base_cache_key = id(diagnostics)
    latest_ads_run = next(
        iter(list_connector_refresh_runs(connector_id="google_ads")), None
    )
    latest_ads_run_key = latest_ads_run.id if latest_ads_run is not None else None
    now = monotonic()
    with _exact_diagnostics_cache_lock:
        expired = [
            key
            for key, value in _exact_diagnostics_cache.items()
            if now - value[0] >= _EXACT_DIAGNOSTICS_CACHE_SECONDS
        ]
        for key in expired:
            _exact_diagnostics_cache.pop(key, None)
        cached = _exact_diagnostics_cache.get(work_item_id)
        if (
            cached is not None
            and cached[1] == base_cache_key
            and cached[2] == latest_ads_run_key
            and now - cached[0] < _EXACT_DIAGNOSTICS_CACHE_SECONDS
        ):
            return cached[3]
    inventory_decision = inventory_decision_for_work_item(work_item_id)
    if inventory_decision is not None:
        # The broad diagnostics queue may already contain a cheap URL-only
        # decision with the same id. For an explicitly selected page, replace
        # that row with the exact inventory-bound decision so rendered
        # provenance (ACF/the_content), source lineage and material confidence
        # cannot be lost before the snapshot is assembled.
        decision_queue = [
            _merge_selected_inventory_fields(item, inventory_decision)
            if item.id == inventory_decision.id
            else item
            for item in diagnostics.decision_queue
        ]
        if not any(item.id == inventory_decision.id for item in diagnostics.decision_queue):
            decision_queue.append(inventory_decision)
        diagnostics = diagnostics.model_copy(
            update={
                "decision_queue": decision_queue,
                # A selected workflow must not inherit connector quality
                # caveats from unrelated content consumers (for example the
                # shop WordPress source on an ordinary ekologus.pl page).
                "freshness_assessment": build_content_freshness_assessment_fast(
                    relevant_connector_ids=inventory_decision.source_connectors,
                ),
            }
        )
    diagnostics = content_diagnostics_with_ads_refresh(
        diagnostics,
        latest_ads_refresh(
            diagnostics,
            [] if latest_ads_run is None else [latest_ads_run],
        ),
    )
    decision_id = work_item_id.removeprefix("content_work_item_")
    decision = next(
        (item for item in diagnostics.decision_queue if item.id == decision_id),
        None,
    )
    if decision is None or not decision.page:
        result = diagnostics
        with _exact_diagnostics_cache_lock:
            _exact_diagnostics_cache[work_item_id] = (
                now,
                base_cache_key,
                latest_ads_run_key,
                result,
            )
        return result
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
        result = diagnostics
        with _exact_diagnostics_cache_lock:
            _exact_diagnostics_cache[work_item_id] = (
                now,
                base_cache_key,
                latest_ads_run_key,
                result,
            )
        return result
    ads_facts = _latest_ads_demand_facts(diagnostics)
    enriched_decision = content_decision_with_exact_demand(
        decision,
        gsc_facts=exact_facts,
        ads_facts=ads_facts,
    )
    result = diagnostics.model_copy(
        update={
            "decision_queue": [
                enriched_decision if item.id == decision_id else item
                for item in diagnostics.decision_queue
            ]
        }
    )
    with _exact_diagnostics_cache_lock:
        _exact_diagnostics_cache[work_item_id] = (
            now,
            base_cache_key,
            latest_ads_run_key,
            result,
        )
    return result


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
