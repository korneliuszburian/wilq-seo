from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from apps.api.wilq_api.routers.content_codex_proposal import (
    register_content_codex_proposal_route,
)
from apps.api.wilq_api.routers.content_decision_context import (
    register_content_decision_context_route,
)
from apps.api.wilq_api.routers.content_document_workspace import (
    register_content_document_workspace_route,
)
from apps.api.wilq_api.routers.content_editorial_integrity import (
    register_content_editorial_integrity_route,
)
from apps.api.wilq_api.routers.content_initial_draft import (
    register_content_initial_draft_route,
)
from apps.api.wilq_api.routers.content_new_page_brief import (
    register_content_new_page_brief_routes,
)
from apps.api.wilq_api.routers.content_planning_proposals import (
    register_content_planning_proposal_routes,
)
from apps.api.wilq_api.routers.content_revision_html_package import (
    register_content_revision_html_package_route,
)
from apps.api.wilq_api.routers.content_semantic_review import (
    register_content_semantic_review_routes,
)
from apps.api.wilq_api.routers.content_target_discovery import (
    register_content_target_discovery_route,
)
from apps.api.wilq_api.routers.content_target_mapping import (
    register_content_target_mapping_route,
)
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse

ContentModelSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_model_routes(
    router: APIRouter,
    *,
    snapshot_loader: ContentModelSnapshotLoader,
) -> None:
    register_content_decision_context_route(router)
    register_content_document_workspace_route(router)
    register_content_editorial_integrity_route(router)
    register_content_codex_proposal_route(router, snapshot_loader=snapshot_loader)
    register_content_initial_draft_route(router, snapshot_loader=snapshot_loader)
    register_content_new_page_brief_routes(router)
    register_content_revision_html_package_route(router, snapshot_loader=snapshot_loader)
    register_content_planning_proposal_routes(router, snapshot_loader=snapshot_loader)
    register_content_semantic_review_routes(router, snapshot_loader=snapshot_loader)
    register_content_target_discovery_route(router)
    register_content_target_mapping_route(router)


__all__ = ["register_content_model_routes"]
