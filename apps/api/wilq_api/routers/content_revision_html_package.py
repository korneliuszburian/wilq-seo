from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.handoff.html_package import build_content_revision_html_package
from wilq.content.workflow.contracts.contracts import ContentRevisionHtmlPackageResponse
from wilq.content.workflow.store.store import content_workflow_store


def register_content_revision_html_package_route(
    router: APIRouter,
) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/html-package",
        response_model=ContentRevisionHtmlPackageResponse,
    )
    def content_work_item_revision_html_package(
        work_item_id: str,
        revision_id: str,
    ) -> ContentRevisionHtmlPackageResponse:
        store = content_workflow_store()
        revision = next(
            (
                item
                for item in store.list_draft_revisions(work_item_id)
                if item.revision_id == revision_id
            ),
            None,
        )
        if revision is None:
            raise HTTPException(
                status_code=404,
                detail="Nie znaleziono wskazanej rewizji dokumentu.",
            )
        if revision.page_assets is None:
            raise HTTPException(
                status_code=409,
                detail="Paczka HTML wymaga kompletnej rewizji dokumentu.",
            )
        review = store.load_draft_revision_review(
            work_item_id=work_item_id,
            revision_id=revision_id,
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
