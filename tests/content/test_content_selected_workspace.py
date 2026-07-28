from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.workflow.selected_workspace as selected_workspace_module
from apps.api.wilq_api.routers.content_selected_workspace import (
    register_content_selected_workspace_route,
)
from wilq.content.workflow.document_workspace import ContentDocumentWorkspace


def test_selected_workspace_keeps_exact_missing_state_out_of_catalogue_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        selected_workspace_module, "build_content_document_workspace", lambda _id: None
    )

    response = selected_workspace_module.build_content_selected_workspace(
        "content_work_item_missing"
    )

    assert response.status == "missing"
    assert response.workspace is None
    assert response.work_item_id == "content_work_item_missing"


def test_selected_workspace_wraps_only_the_exact_workspace(monkeypatch) -> None:
    expected = ContentDocumentWorkspace.model_construct(
        work_item_id="content_work_item_bdo",
        next_action=type("Action", (), {"label": "Otwórz dokument"})(),
    )
    monkeypatch.setattr(
        selected_workspace_module, "build_content_document_workspace", lambda _id: expected
    )

    response = selected_workspace_module.build_content_selected_workspace("content_work_item_bdo")

    assert response.status == "ready"
    assert response.workspace is expected


def test_selected_workspace_route_returns_typed_missing_selection(monkeypatch) -> None:
    monkeypatch.setattr(
        selected_workspace_module, "build_content_document_workspace", lambda _id: None
    )
    app = FastAPI()
    router = APIRouter()
    register_content_selected_workspace_route(router)
    app.include_router(router)

    response = TestClient(app).get(
        "/api/content/work-items/content_work_item_missing/selected-workspace"
    )

    assert response.status_code == 200
    assert response.json() == {
        "response_type": "content_selected_workspace",
        "contract_version": "content_selected_workspace_v1",
        "status": "missing",
        "work_item_id": "content_work_item_missing",
        "workspace": None,
        "reason": "Nie znaleziono istniejącej strony do odświeżenia pod tym dokładnym adresem.",
        "safe_next_step": (
            "Wróć do wyboru pracy i wybierz istniejącą stronę albo rozpocznij brief "
            "nowej strony."
        ),
    }
