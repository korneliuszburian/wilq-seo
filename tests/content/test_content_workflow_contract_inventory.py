from __future__ import annotations

import json

from fastapi.routing import APIRoute

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_workflow import router
from apps.api.wilq_api.routers.content_workflow_http import _browser_item
from wilq.content.drafts.codex_section_proposal import (
    ContentCodexSectionProposalResponse,
)
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftResponse
from wilq.content.knowledge.cards import ContentKnowledgeCardsResponse
from wilq.content.knowledge.service_profile import ContentServiceProfileResponse
from wilq.content.planning.dynamic_input import ContentPlanningInputReadinessResponse
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalResponse,
)
from wilq.content.planning.new_page_proposal import ContentNewPagePlanningProposalWorkspace
from wilq.content.quality.semantic_review_contracts import ContentSemanticReviewResponse
from wilq.content.workflow.api import (
    ContentWorkItemMeasurementOutcomeResponse,
    ContentWorkItemMeasurementWindowResponse,
)
from wilq.content.workflow.contracts import (
    ContentDraftRevisionReviewResponse,
    ContentDraftRevisionSaveResponse,
    ContentEditorialIntegrityReport,
    ContentPublicDeploymentConfirmationResponse,
    ContentPublicDeploymentReadResponse,
    ContentRevisionHtmlPackageResponse,
    ContentWorkItemLearningProposalResponse,
)
from wilq.content.workflow.decision_context import ContentDecisionContext
from wilq.content.workflow.document_workspace import ContentDocumentWorkspace
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.new_page import (
    ContentNewPageBriefWorkspace,
    ContentNewPageFoundationResult,
)
from wilq.content.workflow.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
    ContentNewPageDeliveryReadiness,
)
from wilq.content.workflow.new_page_revision import ContentNewPageRevisionReviewResponse
from wilq.content.workflow.new_page_topics import ContentNewPageTopicRecommendations
from wilq.content.workflow.selected_workspace import ContentSelectedWorkspace
from wilq.content.workflow.target_discovery import ContentTargetDiscovery
from wilq.content.workflow.target_mapping import (
    ContentTargetDraftPreview,
    ContentTargetMappingConfirmationResult,
    ContentTargetMappingPreview,
)
from wilq.schemas import ActionObject, MetricFact

CONTENT_WORKFLOW_RESPONSE_MODELS = {
    ("GET", "/api/content/new-page-topics"): ContentNewPageTopicRecommendations,
    ("POST", "/api/content/new-page-briefs"): ContentNewPageBriefWorkspace,
    (
        "GET",
        "/api/content/new-page-briefs/{brief_id}",
    ): ContentNewPageBriefWorkspace,
    (
        "POST",
        "/api/content/new-page-briefs/{brief_id}/planning-foundation",
    ): ContentNewPageFoundationResult,
    (
        "GET",
        "/api/content/new-page-briefs/{brief_id}/planning-input",
    ): ContentPlanningInputReadinessResponse,
    (
        "GET",
        "/api/content/new-page-briefs/{brief_id}/planning-proposal",
    ): ContentNewPagePlanningProposalWorkspace,
    (
        "POST",
        "/api/content/new-page-briefs/{brief_id}/planning-proposal",
    ): ContentNewPagePlanningProposalWorkspace,
    (
        "GET",
        "/api/content/new-page-briefs/{brief_id}/canonical-document",
    ): ContentNewPageCanonicalDocumentWorkspace,
    (
        "POST",
        "/api/content/new-page-briefs/{brief_id}/draft-revisions/{revision_id}/review",
    ): ContentNewPageRevisionReviewResponse,
    (
        "GET",
        "/api/content/new-page-briefs/{brief_id}/delivery-readiness",
    ): ContentNewPageDeliveryReadiness,
    (
        "POST",
        "/api/content/new-page-briefs/{brief_id}/delivery-action",
    ): ActionObject,
    ("GET", "/api/content/knowledge-cards"): ContentKnowledgeCardsResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/document-workspace",
    ): ContentDocumentWorkspace,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/selected-workspace",
    ): ContentSelectedWorkspace,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/target-discovery",
    ): ContentTargetDiscovery,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping",
    ): ContentTargetMappingPreview,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping/confirmation",
    ): ContentTargetMappingConfirmationResult,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping/draft-preview",
    ): ContentTargetDraftPreview,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/target-mapping/draft-action",
    ): ActionObject,
    ("GET", "/api/content/service-profile"): ContentServiceProfileResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/decision-context",
    ): ContentDecisionContext,
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
        "GET",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/html-package",
    ): ContentRevisionHtmlPackageResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/editorial-integrity",
    ): ContentEditorialIntegrityReport,
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
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/public-deployments",
    ): ContentPublicDeploymentConfirmationResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/public-deployment",
    ): ContentPublicDeploymentReadResponse,
    (
        "POST",
        "/api/content/work-items/{work_item_id}/initial-draft",
    ): ContentInitialDraftResponse,
    (
        "POST",
        "/api/content/new-page-briefs/{brief_id}/initial-draft",
    ): ContentInitialDraftResponse,
    (
        "GET",
        "/api/content/work-items/{work_item_id}/initial-draft",
    ): ContentInitialDraftResponse,
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


def test_content_workflow_stateful_routes_include_active_selected_work_item_reads() -> None:
    routes = set(_content_workflow_routes())

    for suffix in [
        "selected-workspace",
        "target-discovery",
    ]:
        assert any(
            path == f"/api/content/work-items/{{work_item_id}}/{suffix}" for _method, path in routes
        )

    assert not any(
        path == "/api/content/work-items/{work_item_id}/snapshot" for _method, path in routes
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
                "planning-proposal",
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
        "/api/content/new-page-briefs/{brief_id}/planning-proposal",
        "/api/content/work-items/{work_item_id}/initial-draft",
        "/api/content/new-page-briefs/{brief_id}/initial-draft",
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/semantic-review",
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


def test_legacy_workflow_routes_are_not_public_content_routes() -> None:
    for method, path in (
        ("GET", "/api/content/work-items/queue"),
        ("GET", "/api/content/work-items/{work_item_id}/enrichment"),
        ("GET", "/api/content/work-items/snapshot"),
        ("GET", "/api/content/work-items/{work_item_id}/snapshot"),
        ("POST", "/api/content/work-items/snapshot/human-review"),
        ("POST", "/api/content/work-items/{work_item_id}/human-review"),
        ("POST", "/api/content/work-items/snapshot/audit"),
        ("POST", "/api/content/work-items/{work_item_id}/audit"),
        ("POST", "/api/content/work-items/wordpress-draft-execution"),
    ):
        assert (method, path) not in _content_workflow_routes()
        assert path not in app.openapi()["paths"]


def test_retired_global_authoring_profile_is_not_a_public_content_route() -> None:
    path = "/api/content/wordpress/authoring-profile"

    assert ("GET", path) not in _content_workflow_routes()
    assert path not in app.openapi()["paths"]


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
                "/api/content/new-page-briefs",
                "/api/content/new-page-topics",
                "/api/content/wordpress",
            )
        ):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[(method, route.path)] = route
    return routes
