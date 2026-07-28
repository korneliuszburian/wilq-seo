from __future__ import annotations

import wilq.content.workflow.selected_workspace as selected_workspace_module
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
