from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.workflow.new_page import (
    ContentNewPageBriefInput,
    ContentNewPageBriefWorkspace,
    build_new_page_brief_workspace,
)
from wilq.content.workflow.store_new_page import new_page_brief_store


def register_content_new_page_brief_routes(router: APIRouter) -> None:
    @router.post(
        "/api/content/new-page-briefs",
        response_model=ContentNewPageBriefWorkspace,
    )
    def create_content_new_page_brief(
        request: ContentNewPageBriefInput,
    ) -> ContentNewPageBriefWorkspace:
        brief = new_page_brief_store().create_new_page_brief(request)
        return build_new_page_brief_workspace(brief)

    @router.get(
        "/api/content/new-page-briefs/{brief_id}",
        response_model=ContentNewPageBriefWorkspace,
    )
    def content_new_page_brief_workspace(brief_id: str) -> ContentNewPageBriefWorkspace:
        brief = new_page_brief_store().load_new_page_brief(brief_id)
        if brief is None:
            raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
        return build_new_page_brief_workspace(brief)
