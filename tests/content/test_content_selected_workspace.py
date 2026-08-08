from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_selected_workspace as selected_workspace_router
import wilq.content.workflow.workspace.selected_workspace as selected_workspace_module
from apps.api.wilq_api.routers.content_selected_workspace import (
    register_content_selected_workspace_route,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.pipeline_steps.operator_steps import (
    ContentDraftRevisionWorkspaceStatus,
    ContentWorkflowOperatorFacts,
    ContentWorkflowOperatorJourney,
    build_content_workflow_operator_journey,
)
from wilq.content.workflow.workspace.document_workspace import ContentDocumentWorkspace


def test_selected_workspace_keeps_exact_missing_state_out_of_catalogue_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        selected_workspace_module, "build_content_document_workspace", lambda _id: None
    )

    response = selected_workspace_module.build_content_selected_workspace(
        "content_work_item_missing",
        operator_journey=_operator_journey(),
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

    response = selected_workspace_module.build_content_selected_workspace(
        "content_work_item_bdo",
        operator_journey=_operator_journey(),
    )

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
    item = ContentWorkItem(id="content_work_item_bdo", topic="BDO")

    def build(
        work_item_id: str,
        *,
        revision_context_current: bool,
        item: ContentWorkItem,
    ):
        seen.update(
            work_item_id=work_item_id,
            revision_context_current=revision_context_current,
            item=item,
        )
        return expected

    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        build,
    )

    response = selected_workspace_module.build_content_selected_workspace_with_context(
        "content_work_item_bdo",
        operator_journey=_operator_journey(),
        revision_context_current=False,
        item=item,
    )

    assert response.workspace is expected
    assert seen == {
        "work_item_id": "content_work_item_bdo",
        "revision_context_current": False,
        "item": item,
    }


def test_selected_workspace_route_returns_typed_missing_selection(monkeypatch) -> None:
    journey = _operator_journey()
    item = ContentWorkItem(id="content_work_item_missing", topic="Brakujący temat")
    monkeypatch.setattr(
        selected_workspace_router,
        "snapshot_for_work_item_or_404",
        lambda _id: type(
            "Snapshot",
            (),
            {
                "revision_workspace": type("Revision", (), {"context_current": True})(),
                "preflight": type("Preflight", (), {"item": item})(),
                "current_step_id": journey.current_step_id,
                "operator_steps": journey.steps,
            },
        )(),
    )
    def build_selected(
        work_item_id: str,
        *,
        operator_journey: ContentWorkflowOperatorJourney,
        revision_context_current: bool,
        item: ContentWorkItem,
    ):
        return selected_workspace_module.build_content_selected_workspace_with_context(
            work_item_id,
            operator_journey=operator_journey,
            revision_context_current=revision_context_current,
            item=item,
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
        "operator_journey": journey.model_dump(mode="json"),
        "workspace": None,
        "reason": "Nie znaleziono istniejącej strony do odświeżenia pod tym dokładnym adresem.",
        "safe_next_step": (
            "Wróć do wyboru pracy i wybierz istniejącą stronę albo rozpocznij brief "
            "nowej strony."
        ),
    }


def test_selected_workspace_exposes_blocked_dev_draft_for_approved_revision_without_seam(
    monkeypatch,
) -> None:
    workspace = ContentDocumentWorkspace.model_construct(
        work_item_id="content_work_item_bdo",
        canonical_document=type("Document", (), {"status": "approved"})(),
        next_action=type("Action", (), {"label": "Zachowaj zatwierdzenie"})(),
    )
    journey = _operator_journey(revision_status="approved")
    monkeypatch.setattr(
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _id: workspace,
    )

    response = selected_workspace_module.build_content_selected_workspace(
        "content_work_item_bdo",
        operator_journey=journey,
    )

    dev_draft = next(step for step in response.operator_journey.steps if step.id == "dev_draft")
    assert response.workspace is workspace
    assert response.workspace.canonical_document.status == "approved"
    assert response.operator_journey.current_step_id == "dev_draft"
    assert dev_draft.readiness == "blocked"
    assert dev_draft.blocker is not None
    assert dev_draft.blocker.code == "missing_revision_bound_wordpress_seam"
    assert dev_draft.safe_next_step


def _operator_journey(
    *,
    revision_status: ContentDraftRevisionWorkspaceStatus = "empty",
    revision_bound_wordpress_handoff_ready: bool = False,
) -> ContentWorkflowOperatorJourney:
    return build_content_workflow_operator_journey(
        ContentWorkflowOperatorFacts(
            sales_brief_present=True,
            sales_brief_signal_status="strong",
            sales_brief_signal_reason="Zakres ma wystarczające źródła.",
            sales_brief_safe_next_step="Przejdź do planu sekcji.",
            sales_brief_blocker=None,
            section_map_present=True,
            section_map_blocker=None,
            section_map_safe_next_step="Przejdź do szkicu.",
            structured_contract_present=True,
            structured_contract_blocker=None,
            structured_contract_safe_next_step="Przygotuj kontrakt szkicu.",
            revision_workspace_status=revision_status,
            revision_bound_wordpress_handoff_ready=(
                revision_bound_wordpress_handoff_ready
            ),
        )
    )
