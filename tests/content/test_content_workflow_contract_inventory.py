from __future__ import annotations

from fastapi.routing import APIRoute

from apps.api.wilq_api.routers.content_workflow import router
from wilq.content.enrichment.opportunity import ContentOpportunityEnrichmentResponse
from wilq.content.knowledge.cards import ContentKnowledgeCardsResponse
from wilq.content.workflow.api import (
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemDraftVariantsResponse,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightResponse,
    ContentWorkItemQualityReviewResponse,
    ContentWorkItemRevisionApplyResponse,
    ContentWorkItemRevisionPlanResponse,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemStructuredDraftGenerationResponse,
    ContentWorkItemStructuredDraftPreviewResponse,
    ContentWorkItemStructuredDraftRuntimeResponse,
    ContentWorkItemWordPressDraftExecutionResponse,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.queue import ContentWorkItemQueueResponse

CONTENT_WORKFLOW_RESPONSE_MODELS = {
    ("GET", "/api/content/knowledge-cards"): ContentKnowledgeCardsResponse,
    ("GET", "/api/content/work-items/queue"): ContentWorkItemQueueResponse,
    ("GET", "/api/content/work-items/snapshot"): ContentWorkItemWorkflowSnapshotResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/snapshot",
    ): ContentWorkItemWorkflowSnapshotResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/enrichment",
    ): ContentOpportunityEnrichmentResponse,
    (
        "POST",
        "/api/content/work-items/snapshot/human-review",
    ): ContentWorkItemHumanReviewResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/human-review",
    ): ContentWorkItemHumanReviewResponse,
    (
        "POST",
        "/api/content/work-items/snapshot/audit",
    ): ContentWorkItemWordPressDraftHandoffResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/audit",
    ): ContentWorkItemWordPressDraftHandoffResponse,
    ("POST", "/api/content/work-items/preflight"): ContentWorkItemPreflightResponse,
    ("POST", "/api/content/work-items/sales-brief"): ContentWorkItemSalesBriefResponse,
    ("POST", "/api/content/work-items/draft-package"): ContentWorkItemDraftPackageResponse,
    (
        "POST",
        "/api/content/work-items/structured-draft-generation",
    ): ContentWorkItemStructuredDraftGenerationResponse,
    ("POST", "/api/content/work-items/draft-variants"): ContentWorkItemDraftVariantsResponse,
    (
        "POST",
        "/api/content/work-items/structured-draft-runtime",
    ): ContentWorkItemStructuredDraftRuntimeResponse,
    (
        "POST",
        "/api/content/work-items/structured-draft-preview",
    ): ContentWorkItemStructuredDraftPreviewResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/structured-draft-preview",
    ): ContentWorkItemStructuredDraftPreviewResponse,
    ("POST", "/api/content/work-items/quality-review"): ContentWorkItemQualityReviewResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/quality-review",
    ): ContentWorkItemQualityReviewResponse,
    ("POST", "/api/content/work-items/revision-plan"): ContentWorkItemRevisionPlanResponse,
    (
        "POST",
        "/api/content/work-items/revision-apply",
    ): ContentWorkItemRevisionApplyResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/revision-plan",
    ): ContentWorkItemRevisionPlanResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/revision-apply",
    ): ContentWorkItemRevisionApplyResponse,
    ("POST", "/api/content/work-items/human-review"): ContentWorkItemHumanReviewResponse,
    (
        "POST",
        "/api/content/work-items/wordpress-draft-handoff",
    ): ContentWorkItemWordPressDraftHandoffResponse,
    (
        "POST",
        "/api/content/work-items/wordpress-draft-execution",
    ): ContentWorkItemWordPressDraftExecutionResponse,
    (
        "POST",
        "/api/content/work-items/measurement-window",
    ): ContentWorkItemMeasurementWindowResponse,
    (
        "POST",
        "/api/content/work-items/measurement-outcome",
    ): ContentWorkItemMeasurementOutcomeResponse,
}


def test_content_workflow_routes_have_frozen_response_models() -> None:
    routes = _content_workflow_routes()

    assert set(routes) == set(CONTENT_WORKFLOW_RESPONSE_MODELS)
    for key, expected_response_model in CONTENT_WORKFLOW_RESPONSE_MODELS.items():
        assert routes[key].response_model is expected_response_model


def test_content_workflow_stateful_routes_have_selected_work_item_variants() -> None:
    routes = set(_content_workflow_routes())

    for suffix in [
        "snapshot",
        "human-review",
        "audit",
        "structured-draft-preview",
        "quality-review",
        "revision-plan",
        "revision-apply",
    ]:
        assert any(
            path == f"/api/content/work-items/{{work_item_id}}/{suffix}"
            for _method, path in routes
        )


def _content_workflow_routes() -> dict[tuple[str, str], APIRoute]:
    routes: dict[tuple[str, str], APIRoute] = {}
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(("/api/content/work-items", "/api/content/knowledge-cards")):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[(method, route.path)] = route
    return routes
