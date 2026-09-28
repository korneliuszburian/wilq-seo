from __future__ import annotations

import json

from fastapi.routing import APIRoute

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_workflow import router
from apps.api.wilq_api.routers.content_workflow_http import _browser_item
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.schemas import MetricFact


def test_content_workflow_routes_declare_response_models() -> None:
    routes = _content_workflow_routes()

    assert routes
    assert all(route.response_model is not None for route in routes.values())


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
                "repair-proposal",
                "initial-draft",
                "planning-proposals",
                "planning-proposal",
                "semantic-review",
                "fact-proposal",
                "independent-reviews",
            )
        )
    }
    forbidden_paths = {
        "/api/content/work-items/structured-draft-generation",
        "/api/content/work-items/structured-draft-runtime",
        "/api/content/work-items/structured-draft-preview",
        "/api/content/work-items/{work_item_id}/structured-draft-preview",
        "/api/content/work-items/draft-variants",
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal",
    }

    assert model_paths == {
        "/api/content/work-items/{work_item_id}/planning-proposals",
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/repair-proposal",
        "/api/content/new-page-briefs/{brief_id}/planning-proposal",
        "/api/content/work-items/{work_item_id}/initial-draft",
        "/api/content/new-page-briefs/{brief_id}/initial-draft",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/semantic-review",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/independent-reviews",
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/independent-reviews/{run_id}/findings/{finding_id}/disposition",
        "/api/content/regulatory-source-candidates/{candidate_id}/fact-proposal",
        "/api/content/regulatory-source-fact-proposals/{proposal_id}/review",
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
        ("GET", "/api/content/work-items/{work_item_id}/document-workspace"),
        ("GET", "/api/content/work-items/{work_item_id}/decision-context"),
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


def test_retired_inventory_mutation_and_material_reads_are_not_public_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/api/content/inventory/bind" not in paths
    assert "/api/content/inventory/material" not in paths


def _content_workflow_routes() -> dict[tuple[str, str], APIRoute]:
    routes: dict[tuple[str, str], APIRoute] = {}
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(
            (
                "/api/content/work-items",
                "/api/content/production-classifications",
                "/api/content/knowledge-cards",
                "/api/content/service-profile",
                "/api/content/new-page-briefs",
                "/api/content/new-page-topics",
                "/api/content/regulatory-source-candidates",
                "/api/content/regulatory-source-fact-proposals",
                "/api/content/regulatory-source-reviews",
                "/api/content/wordpress",
            )
        ):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[(method, route.path)] = route
    return routes
