from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.quality.editorial_integrity import build_content_editorial_integrity_report
from wilq.content.workflow.contracts import ContentEditorialIntegrityReport
from wilq.content.workflow.store import content_workflow_store


def register_content_editorial_integrity_route(router: APIRouter) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/editorial-integrity",
        response_model=ContentEditorialIntegrityReport,
    )
    def content_work_item_editorial_integrity(
        work_item_id: str,
        revision_id: str,
    ) -> ContentEditorialIntegrityReport:
        try:
            store = content_workflow_store()
            return build_content_editorial_integrity_report(
                work_item_id=work_item_id,
                revision_id=revision_id,
                revisions=store.list_draft_revisions(work_item_id),
                human_review=store.load_draft_revision_state(work_item_id).latest_review,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error


__all__ = ["register_content_editorial_integrity_route"]
