from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from wilq.content.workflow.catalog import build_content_inventory_catalog_cached
from wilq.content.workflow.new_page import (
    ContentNewPageBriefInput,
    ContentNewPageBriefWorkspace,
    ContentNewPageFoundationCommand,
    ContentNewPageFoundationResult,
    build_new_page_brief_workspace,
    build_new_page_overlap_guard,
    build_new_page_planning_foundation,
    new_page_service_card,
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
        return build_new_page_brief_workspace(
            brief,
            foundation=new_page_brief_store().load_new_page_foundation(brief_id),
        )

    @router.post(
        "/api/content/new-page-briefs/{brief_id}/planning-foundation",
        response_model=ContentNewPageFoundationResult,
        responses={409: {"model": ContentNewPageFoundationResult}},
    )
    def create_content_new_page_planning_foundation(
        brief_id: str,
        request: ContentNewPageFoundationCommand,
    ) -> ContentNewPageFoundationResult | JSONResponse:
        store = new_page_brief_store()
        brief = store.load_new_page_brief(brief_id)
        if brief is None:
            raise HTTPException(status_code=404, detail="Nie znaleziono briefu nowej strony.")
        guard = build_new_page_overlap_guard(
            brief,
            catalog=build_content_inventory_catalog_cached(),
        )
        service_card = new_page_service_card(request.service_card_id)
        if service_card is None:
            result = ContentNewPageFoundationResult(
                status="blocked",
                reason="Wybrana karta usługi nie jest zatwierdzona do użycia w planowaniu.",
                safe_next_step="Wybierz zatwierdzoną kartę usługi zwróconą przez WILQ.",
            )
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        try:
            foundation = build_new_page_planning_foundation(
                brief=brief,
                guard=guard,
                command=request,
                service_card=service_card,
            )
        except ValueError as error:
            result = ContentNewPageFoundationResult(
                status="conflict",
                reason=str(error),
                safe_next_step="Odśwież brief i ponownie sprawdź pokrycie przed zapisem.",
            )
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        try:
            status, stored = store.save_new_page_foundation(foundation)
        except ValueError as error:
            result = ContentNewPageFoundationResult(
                status="conflict",
                reason=str(error),
                safe_next_step=(
                    "Odczytaj zapisaną podstawę planowania zamiast zastępować jej wiązanie."
                ),
            )
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return ContentNewPageFoundationResult(
            status=status,
            foundation=stored,
            reason=(
                "Podstawa planowania jest związana z dokładnym briefem, "
                "kontrolą pokrycia i kartą usługi."
            ),
            safe_next_step="Przygotuj plan dokumentu w kolejnym etapie workflow.",
        )
