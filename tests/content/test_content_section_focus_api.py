from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError

from apps.api.wilq_api.routers.content_section_focus import (
    register_content_section_focus_routes,
)
from wilq.content.workflow.contracts.section_focus import (
    ContentSectionFocusResponse,
    ContentSectionFocusUpdateRequest,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
    ContentPlanningWorkspace,
)
from wilq.storage.local_state import local_state_store

WORK_ITEM_ID = "work_1"


@pytest.fixture
def focus_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[APIRouter, dict[str, ContentPlanningWorkspace | None]]:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    plan_state: dict[str, ContentPlanningWorkspace | None] = {
        "workspace": _planning_workspace("a" * 64, ["section_1", "section_2"]),
    }
    router = APIRouter()
    register_content_section_focus_routes(
        router,
        planning_workspace_loader=lambda work_item_id: (
            plan_state["workspace"] if work_item_id == WORK_ITEM_ID else None
        ),
    )
    return router, plan_state


def test_focus_put_is_current_after_api_reload_without_planning_approval(
    focus_api: tuple[APIRouter, dict[str, ContentPlanningWorkspace | None]],
) -> None:
    router, _ = focus_api
    save_focus = _route_endpoint(router, "PUT")
    read_focus = _route_endpoint(router, "GET")

    saved = save_focus(
        WORK_ITEM_ID,
        ContentSectionFocusUpdateRequest(
            section_id="section_1",
            planning_digest="a" * 64,
            updated_by="wilku",
        ),
    )
    reloaded = read_focus(WORK_ITEM_ID)

    assert isinstance(saved, ContentSectionFocusResponse)
    assert isinstance(reloaded, ContentSectionFocusResponse)
    assert reloaded == saved
    assert reloaded.status == "current"
    assert reloaded.record is not None
    assert reloaded.record.section_id == "section_1"
    assert set(reloaded.record.model_dump(mode="json")) == {
        "work_item_id",
        "section_id",
        "planning_digest",
        "updated_by",
        "updated_at",
    }


def test_focus_becomes_stale_after_plan_regeneration_without_losing_record(
    focus_api: tuple[APIRouter, dict[str, ContentPlanningWorkspace | None]],
) -> None:
    router, plan_state = focus_api
    _save_current_focus(router)

    plan_state["workspace"] = _planning_workspace("b" * 64, ["section_1"])
    response = _route_endpoint(router, "GET")(WORK_ITEM_ID)

    assert isinstance(response, ContentSectionFocusResponse)
    assert response.status == "stale"
    assert response.record is None
    persisted = local_state_store().get_content_section_focus(WORK_ITEM_ID)
    assert persisted is not None
    assert persisted.planning_digest == "a" * 64


def test_focus_becomes_stale_when_section_leaves_same_plan_digest(
    focus_api: tuple[APIRouter, dict[str, ContentPlanningWorkspace | None]],
) -> None:
    router, plan_state = focus_api
    _save_current_focus(router)

    plan_state["workspace"] = _planning_workspace("a" * 64, ["section_2"])
    response = _route_endpoint(router, "GET")(WORK_ITEM_ID)

    assert isinstance(response, ContentSectionFocusResponse)
    assert response.status == "stale"
    assert response.record is None


def test_focus_read_is_typed_missing_without_persisted_selection(
    focus_api: tuple[APIRouter, dict[str, ContentPlanningWorkspace | None]],
) -> None:
    router, _ = focus_api

    response = _route_endpoint(router, "GET")(WORK_ITEM_ID)

    assert isinstance(response, ContentSectionFocusResponse)
    assert response.status == "missing"
    assert response.record is None


@pytest.mark.parametrize(
    ("section_id", "planning_digest"),
    [
        ("section_1", "b" * 64),
        ("section_missing", "a" * 64),
    ],
)
def test_focus_put_rejects_noncurrent_plan_identity_without_replacing_focus(
    focus_api: tuple[APIRouter, dict[str, ContentPlanningWorkspace | None]],
    section_id: str,
    planning_digest: str,
) -> None:
    router, _ = focus_api
    existing = _save_current_focus(router)

    response = _route_endpoint(router, "PUT")(
        WORK_ITEM_ID,
        ContentSectionFocusUpdateRequest(
            section_id=section_id,
            planning_digest=planning_digest,
            updated_by="wilku",
        ),
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "status": "stale",
        "record": None,
        "safe_next_step": (
            "Plan lub mapa sekcji zmieniły się. Wybierz sekcję ponownie "
            "w aktualnym planie."
        ),
    }
    assert local_state_store().get_content_section_focus(WORK_ITEM_ID) == existing.record


def test_focus_delete_clears_selection_idempotently(
    focus_api: tuple[APIRouter, dict[str, ContentPlanningWorkspace | None]],
) -> None:
    router, _ = focus_api
    _save_current_focus(router)
    clear_focus = _route_endpoint(router, "DELETE")

    cleared = clear_focus(WORK_ITEM_ID)
    cleared_again = clear_focus(WORK_ITEM_ID)

    assert cleared == ContentSectionFocusResponse(
        status="missing",
        safe_next_step="Wybierz sekcję w aktualnym planie, aby zapisać fokus pracy.",
    )
    assert cleared_again == cleared
    assert local_state_store().get_content_section_focus(WORK_ITEM_ID) is None


def test_focus_request_rejects_browser_content_and_unsaved_edits() -> None:
    with pytest.raises(ValidationError):
        ContentSectionFocusUpdateRequest.model_validate(
            {
                "section_id": "section_1",
                "planning_digest": "a" * 64,
                "updated_by": "wilku",
                "content_text": "Niezapisana treść przeglądarki",
                "browser_edits": {"lead": "lokalna zmiana"},
            }
        )


def _save_current_focus(router: APIRouter) -> ContentSectionFocusResponse:
    response = _route_endpoint(router, "PUT")(
        WORK_ITEM_ID,
        ContentSectionFocusUpdateRequest(
            section_id="section_1",
            planning_digest="a" * 64,
            updated_by="wilku",
        ),
    )
    assert isinstance(response, ContentSectionFocusResponse)
    return response


def _route_endpoint(router: APIRouter, method: str) -> Any:
    route = next(
        route
        for route in router.routes
        if isinstance(route, APIRoute) and method in route.methods
    )
    return cast(Any, route.endpoint)


def _planning_workspace(
    planning_digest: str,
    section_ids: list[str],
) -> ContentPlanningWorkspace:
    proposal = ContentPlanningProposal(
        work_item_id=WORK_ITEM_ID,
        planning_digest=planning_digest,
        proposal_id=f"proposal_{planning_digest[0]}",
        generation_status="codex_generated",
        final_canonical_url="https://www.ekologus.pl/usluga/",
        target_reader="firma",
        buyer_problem="brak uporządkowanego procesu",
        buyer_trigger="potrzeba aktualizacji treści",
        search_intent="informational",
        cta_direction="Skontaktuj się z Ekologusem.",
        sections=[
            ContentPlanningSection(
                section_id=section_id,
                heading=f"Sekcja {index}",
                purpose="Wyjaśnia zakres usługi.",
            )
            for index, section_id in enumerate(section_ids, start=1)
        ],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak dokładnych danych popytowych.",
        ),
    )
    return ContentPlanningWorkspace(
        proposal=proposal,
        scope_current=False,
        section_map_current=True,
    )
