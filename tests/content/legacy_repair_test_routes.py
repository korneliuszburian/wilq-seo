"""Historical repair adapter; remove after exact repair ActionObject tests supersede it."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import apps.api.wilq_api.routers.content_codex_proposal as repair_route
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentRevisionRepairProposalRequest,
    ContentRevisionRepairProposalResponse,
)


def register_legacy_repair_test_route(
    router: APIRouter,
    *,
    snapshot_loader: repair_route.ContentSnapshotLoader,
) -> None:
    @router.post(
        "/api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/repair-proposal",
        response_model=ContentRevisionRepairProposalResponse,
        responses={409: {"model": ContentRevisionRepairProposalResponse}},
    )
    def legacy_repair_test_post(
        work_item_id: str,
        base_revision_id: str,
        request: ContentRevisionRepairProposalRequest,
    ) -> ContentRevisionRepairProposalResponse | JSONResponse:
        return repair_route._run_private_revision_repair(
            work_item_id, base_revision_id, request, snapshot_loader
        )


__all__ = ["register_legacy_repair_test_route"]
