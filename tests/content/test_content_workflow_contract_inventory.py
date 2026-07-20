from __future__ import annotations

import json

from fastapi.routing import APIRoute

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_workflow as content_workflow_module
from apps.api.wilq_api.routers.content_workflow import router
from apps.api.wilq_api.routers.content_workflow_http import _browser_item
from wilq.connectors.wordpress.authoring import WordPressAuthoringProfile
from wilq.content.drafts.codex_section_proposal import (
    ContentCodexSectionProposalResponse,
)
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftResponse
from wilq.content.enrichment.opportunity import ContentOpportunityEnrichmentResponse
from wilq.content.knowledge.cards import ContentKnowledgeCardsResponse
from wilq.content.knowledge.service_profile import ContentServiceProfileResponse
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalResponse,
)
from wilq.content.quality.semantic_review_contracts import ContentSemanticReviewResponse
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
    ContentWorkItemLearningProposalResponse,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.planning import ContentPlanningReviewResponse
from wilq.content.workflow.queue import ContentWorkItemQueueResponse
from wilq.schemas import MetricFact

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
        "/api/content/work-items/{work_item_id}/planning-review",
    ): ContentPlanningReviewResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/planning-proposals",
    ): ContentPlanningProposalResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/planning-proposals",
    ): ContentPlanningProposalResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions",
    ): ContentDraftRevisionSaveResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal",
    ): ContentCodexSectionProposalResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/semantic-review",
    ): ContentSemanticReviewResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/semantic-review",
    ): ContentSemanticReviewResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/review",
    ): ContentDraftRevisionReviewResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/initial-draft",
    ): ContentInitialDraftResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/initial-draft",
    ): ContentInitialDraftResponse,
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
    (
        "POST",
        "/api/content/work-items/learning-proposal",
    ): ContentWorkItemLearningProposalResponse,
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
    ]:
        assert any(
            path == f"/api/content/work-items/{{work_item_id}}/{suffix}"
            for _method, path in routes
        )


def test_public_content_openapi_has_only_review_gated_model_entrypoints() -> None:
    content_paths = {
        path: operation
        for path, operation in app.openapi()["paths"].items()
        if path.startswith("/api/content/")
    }
    model_paths = {
        path
        for path in content_paths
        if any(
            marker in path
            for marker in (
                "codex-proposal",
                "initial-draft",
                "planning-proposals",
                "semantic-review",
            )
        )
    }
    forbidden_paths = {
        "/api/content/work-items/structured-draft-generation",
        "/api/content/work-items/structured-draft-runtime",
        "/api/content/work-items/structured-draft-preview",
        "/api/content/work-items/{work_item_id}/structured-draft-preview",
        "/api/content/work-items/draft-variants",
    }

    assert model_paths == {
        "/api/content/work-items/{work_item_id}/planning-proposals",
        "/api/content/work-items/{work_item_id}/initial-draft",
        "/api/content/work-items/{work_item_id}/draft-revisions/"
        "{base_revision_id}/codex-proposal",
        "/api/content/work-items/{work_item_id}/draft-revisions/"
        "{revision_id}/semantic-review",
    }
    assert forbidden_paths.isdisjoint(content_paths)
    serialized_contract = json.dumps(content_paths, sort_keys=True)
    for forbidden_field in (
        "model_input",
        "system_instruction",
        "user_instruction",
        "output_schema",
    ):
        assert forbidden_field not in serialized_contract


def test_browser_item_does_not_duplicate_full_wordpress_material() -> None:
    item = ContentWorkItem(
        id="content_work_item_test",
        topic="Test",
        wordpress_content_text="pełny materiał strony",
        wordpress_content_summary="krótkie podsumowanie",
        metric_facts=[
            MetricFact(
                name=f"metric_{index}",
                value=index,
                period="2026-07-20",
                source_connector="google_analytics_4",
                evidence_id=f"ev_{index}",
            )
            for index in range(13)
        ],
    )

    projected = _browser_item(item)

    assert projected.wordpress_content_text is None
    assert projected.wordpress_content_summary == "krótkie podsumowanie"
    assert len(projected.metric_facts) == 12
    assert projected.metric_facts == item.metric_facts[:12]


def test_selected_snapshot_handler_uses_browser_projection(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr(
        content_workflow_module,
        "_snapshot_for_work_item_or_blocked_or_404",
        lambda _work_item_id: "internal-snapshot",
    )
    monkeypatch.setattr(
        content_workflow_module,
        "project_content_work_item_browser_snapshot",
        lambda snapshot: (snapshot, sentinel),
    )

    result = content_workflow_module.content_work_item_snapshot_for_selected_item(
        "content_work_item_test"
    )

    assert result == ("internal-snapshot", sentinel)


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
