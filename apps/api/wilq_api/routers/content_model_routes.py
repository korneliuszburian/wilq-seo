from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers.content_codex_proposal import (
    register_content_codex_proposal_route,
)
from apps.api.wilq_api.routers.content_decision_context import (
    register_content_decision_context_route,
)
from apps.api.wilq_api.routers.content_initial_draft import (
    register_content_initial_draft_route,
)
from apps.api.wilq_api.routers.content_revision_html_package import (
    register_content_revision_html_package_route,
)
from apps.api.wilq_api.routers.content_planning_proposals import (
    register_content_planning_proposal_routes,
)
from apps.api.wilq_api.routers.content_semantic_review import (
    register_content_semantic_review_routes,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse

ContentModelSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_model_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentModelSnapshotLoader,
) -> None:
    register_content_decision_context_route(router)
    register_content_codex_proposal_route(router, snapshot_loader=snapshot_loader)
    register_content_initial_draft_route(router, snapshot_loader=snapshot_loader)
    register_content_revision_html_package_route(router, snapshot_loader=snapshot_loader)
    register_content_planning_proposal_routes(router, snapshot_loader=snapshot_loader)
    register_content_semantic_review_routes(router, snapshot_loader=snapshot_loader)


__all__ = ["register_content_model_routes"]
