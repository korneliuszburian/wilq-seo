from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from wilq.content.handoff.html_package import build_content_revision_html_package
from wilq.content.workflow.contracts import (
    ContentRevisionHtmlPackageResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)

ContentModelSnapshotLoader = Callable[[str], ContentWorkItemWorkflowSnapshotResponse]


def register_content_revision_html_package_route(
    router: APIRouter,
    *,
    snapshot_loader: ContentModelSnapshotLoader,
) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/html-package",
        response_model=ContentRevisionHtmlPackageResponse,
    )
    def content_work_item_revision_html_package(
        work_item_id: str,
        revision_id: str,
    ) -> ContentRevisionHtmlPackageResponse:
        snapshot = snapshot_loader(work_item_id)
        workspace = snapshot.revision_workspace
        revision = workspace.latest_revision
        review = workspace.latest_review
        if revision is None or revision.revision_id != revision_id:
            raise HTTPException(
                status_code=409,
                detail="Paczka HTML jest dostępna wyłącznie dla aktualnej rewizji.",
            )
        if revision.page_assets is None:
            raise HTTPException(
                status_code=409,
                detail="Paczka HTML wymaga kompletnej rewizji dokumentu.",
            )
        if (
            review is None
            or review.decision != "approved"
            or review.revision_id != revision.revision_id
            or review.revision_digest != revision.content_digest
        ):
            raise HTTPException(
                status_code=409,
                detail="Paczka HTML wymaga zatwierdzonego review tej dokładnej rewizji.",
            )
        return build_content_revision_html_package(revision, review)


__all__ = ["register_content_revision_html_package_route"]
