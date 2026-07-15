from __future__ import annotations

import json

from fastapi.routing import APIRoute

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_workflow import router
from wilq.connectors.wordpress.authoring import WordPressAuthoringProfile
from wilq.content.drafts.codex_section_proposal import (
    ContentCodexSectionProposalResponse,
)
from wilq.content.enrichment.opportunity import ContentOpportunityEnrichmentResponse
from wilq.content.knowledge.cards import ContentKnowledgeCardsResponse
from wilq.content.knowledge.service_profile import ContentServiceProfileResponse
from wilq.content.workflow.api import (
    ContentWordPressDraftActivationPacketResponse,
    ContentWordPressDraftWriteReadinessResponse,
    ContentWordPressExistingDraftUpdateReadinessResponse,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightResponse,
    ContentWorkItemQualityReviewResponse,
    ContentWorkItemRevisionApplyResponse,
    ContentWorkItemRevisionPlanResponse,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
    ContentWorkItemWordPressDraftExecutionResponse,
    ContentWorkItemWordPressDraftHandoffResponse,
)
from wilq.content.workflow.contracts import (
    ContentDraftRevisionReviewResponse,
    ContentDraftRevisionSaveResponse,
    ContentWorkItemBrowserSnapshotResponse,
    ContentWorkItemBrowserWorkflowSnapshotResponse,
)
from wilq.content.workflow.queue import ContentWorkItemQueueResponse

CONTENT_WORKFLOW_RESPONSE_MODELS = {
    ("GET", "/api/content/knowledge-cards"): ContentKnowledgeCardsResponse,
    ("GET", "/api/content/service-profile"): ContentServiceProfileResponse,
    ("GET", "/api/content/wordpress/authoring-profile"): WordPressAuthoringProfile,
    (
        "GET",
        "/api/content/wordpress/draft-activation-packet",
    ): ContentWordPressDraftActivationPacketResponse,
    (
        "GET",
        "/api/content/wordpress/draft-write-readiness",
    ): ContentWordPressDraftWriteReadinessResponse,
    (
        "GET",
        "/api/content/wordpress/existing-draft-update-readiness",
    ): ContentWordPressExistingDraftUpdateReadinessResponse,
    ("GET", "/api/content/work-items/queue"): ContentWorkItemQueueResponse,
    (
        "GET",
        "/api/content/work-items/snapshot",
    ): ContentWorkItemBrowserWorkflowSnapshotResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/snapshot",
    ): ContentWorkItemBrowserSnapshotResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/enrichment",
    ): ContentOpportunityEnrichmentResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions",
    ): ContentDraftRevisionSaveResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal",
    ): ContentCodexSectionProposalResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/review",
    ): ContentDraftRevisionReviewResponse,
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
        "/api/content/work-items/wordpress-authoring-payload-preview",
    ): ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
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
        "quality-review",
        "revision-plan",
        "revision-apply",
    ]:
        assert any(
            path == f"/api/content/work-items/{{work_item_id}}/{suffix}"
            for _method, path in routes
        )


def test_public_content_openapi_has_one_model_entrypoint_and_no_execution_contract() -> None:
    content_paths = {
        path: operation
        for path, operation in app.openapi()["paths"].items()
        if path.startswith("/api/content/")
    }
    model_paths = [path for path in content_paths if "codex-proposal" in path]
    forbidden_paths = {
        "/api/content/work-items/structured-draft-generation",
        "/api/content/work-items/structured-draft-runtime",
        "/api/content/work-items/structured-draft-preview",
        "/api/content/work-items/{work_item_id}/structured-draft-preview",
        "/api/content/work-items/draft-variants",
    }

    assert model_paths == [
        "/api/content/work-items/{work_item_id}/draft-revisions/"
        "{base_revision_id}/codex-proposal"
    ]
    assert forbidden_paths.isdisjoint(content_paths)
    serialized_contract = json.dumps(content_paths, sort_keys=True)
    for forbidden_field in (
        "model_input",
        "system_instruction",
        "user_instruction",
        "output_schema",
    ):
        assert forbidden_field not in serialized_contract


def _content_workflow_routes() -> dict[tuple[str, str], APIRoute]:
    routes: dict[tuple[str, str], APIRoute] = {}
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(
            (
                "/api/content/work-items",
                "/api/content/knowledge-cards",
                "/api/content/service-profile",
                "/api/content/wordpress",
            )
        ):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[(method, route.path)] = route
    return routes
