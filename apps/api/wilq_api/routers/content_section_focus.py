from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wilq.content.workflow.contracts.section_focus import (
    ContentSectionFocusRecord,
    ContentSectionFocusResponse,
    ContentSectionFocusStatus,
    ContentSectionFocusUpdateRequest,
    content_section_focus_status,
)
from wilq.content.workflow.decisions.planning import ContentPlanningWorkspace
from wilq.storage.local_state import local_state_store

ContentSectionFocusPlanningWorkspaceLoader = Callable[
    [str], ContentPlanningWorkspace | None
]

_SAFE_NEXT_STEPS: dict[ContentSectionFocusStatus, str] = {
    "current": "Kontynuuj pracę nad wybraną sekcją bieżącego planu.",
    "stale": (
        "Plan lub mapa sekcji zmieniły się. Wybierz sekcję ponownie "
        "w aktualnym planie."
    ),
    "missing": "Wybierz sekcję w aktualnym planie, aby zapisać fokus pracy.",
}


def register_content_section_focus_routes(
    router: APIRouter,
    *,
    planning_workspace_loader: ContentSectionFocusPlanningWorkspaceLoader,
) -> None:
    @router.get(
        "/api/content/work-items/{work_item_id}/section-focus",
        response_model=ContentSectionFocusResponse,
    )
    def content_work_item_section_focus(
        work_item_id: str,
    ) -> ContentSectionFocusResponse:
        workspace = planning_workspace_loader(work_item_id)
        planning_digest, section_ids = _current_plan_identity(work_item_id, workspace)
        record = local_state_store().get_content_section_focus(work_item_id)
        return _focus_response(record, planning_digest, section_ids)

    @router.put(
        "/api/content/work-items/{work_item_id}/section-focus",
        response_model=ContentSectionFocusResponse,
        responses={409: {"model": ContentSectionFocusResponse}},
    )
    def content_work_item_section_focus_save(
        work_item_id: str,
        request: ContentSectionFocusUpdateRequest,
    ) -> ContentSectionFocusResponse | JSONResponse:
        workspace = planning_workspace_loader(work_item_id)
        planning_digest, section_ids = _current_plan_identity(work_item_id, workspace)
        if (
            planning_digest is None
            or request.planning_digest != planning_digest
            or request.section_id not in section_ids
        ):
            return _stale_focus_conflict()
        record = ContentSectionFocusRecord(
            work_item_id=work_item_id,
            section_id=request.section_id,
            planning_digest=planning_digest,
            updated_by=request.updated_by,
            updated_at=datetime.now(UTC),
        )
        saved = local_state_store().save_content_section_focus(record)
        return _focus_response(saved, planning_digest, section_ids)

    @router.delete(
        "/api/content/work-items/{work_item_id}/section-focus",
        response_model=ContentSectionFocusResponse,
    )
    def content_work_item_section_focus_clear(
        work_item_id: str,
    ) -> ContentSectionFocusResponse:
        planning_workspace_loader(work_item_id)
        local_state_store().clear_content_section_focus(work_item_id)
        return ContentSectionFocusResponse(
            status="missing",
            safe_next_step=_SAFE_NEXT_STEPS["missing"],
        )


def _current_plan_identity(
    work_item_id: str,
    workspace: ContentPlanningWorkspace | None,
) -> tuple[str | None, set[str]]:
    if workspace is None or workspace.proposal.work_item_id != work_item_id:
        return None, set()
    return (
        workspace.proposal.planning_digest,
        {section.section_id for section in workspace.proposal.sections if section.section_id},
    )


def _focus_response(
    record: ContentSectionFocusRecord | None,
    current_planning_digest: str | None,
    section_ids_in_plan: set[str],
) -> ContentSectionFocusResponse:
    status = content_section_focus_status(
        record,
        current_planning_digest,
        section_ids_in_plan,
    )
    return ContentSectionFocusResponse(
        status=status,
        record=record if status == "current" else None,
        safe_next_step=_SAFE_NEXT_STEPS[status],
    )


def _stale_focus_conflict() -> JSONResponse:
    response = ContentSectionFocusResponse(
        status="stale",
        safe_next_step=_SAFE_NEXT_STEPS["stale"],
    )
    return JSONResponse(status_code=409, content=response.model_dump(mode="json"))


__all__ = ["register_content_section_focus_routes"]
