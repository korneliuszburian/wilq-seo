from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_selected_workspace as selected_workspace_router
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


def test_selected_workspace_passes_current_revision_context_to_document_workspace(
    monkeypatch,
) -> None:
    expected = ContentDocumentWorkspace.model_construct(
        work_item_id="content_work_item_bdo",
        next_action=type("Action", (), {"label": "Przygotuj świeżą wersję"})(),
    )
    seen: dict[str, object] = {}

    def build(work_item_id: str, *, revision_context_current: bool):
        seen.update(
            work_item_id=work_item_id,
            revision_context_current=revision_context_current,
        )
        return expected

    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        build,
    )

    response = selected_workspace_module.build_content_selected_workspace_with_context(
        "content_work_item_bdo",
        revision_context_current=False,
    )

    assert response.workspace is expected
    assert seen == {
        "work_item_id": "content_work_item_bdo",
        "revision_context_current": False,
    }


def test_selected_workspace_route_returns_typed_missing_selection(monkeypatch) -> None:
    monkeypatch.setattr(
        selected_workspace_router,
        "snapshot_for_work_item_or_404",
        lambda _id: type(
            "Snapshot",
            (), {"revision_workspace": type("Revision", (), {"context_current": True})()},
        )(),
    )
    def build_selected(
        work_item_id: str,
        *,
        revision_context_current: bool,
    ):
        return selected_workspace_module.build_content_selected_workspace_with_context(
            work_item_id,
            revision_context_current=revision_context_current,
        )

    monkeypatch.setattr(
        selected_workspace_router,
        "build_content_selected_workspace_with_context",
        build_selected,
    )
    monkeypatch.setattr(
        selected_workspace_module, "build_content_document_workspace", lambda _id, **_kwargs: None
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
