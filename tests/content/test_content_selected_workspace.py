from __future__ import annotations

from types import SimpleNamespace

from fastapi import APIRouter

import apps.api.wilq_api.routers.content_selected_snapshot as selected_snapshot_router
import apps.api.wilq_api.routers.content_selected_workspace as selected_workspace_router
import wilq.content.workflow.workspace.selected_workspace as selected_workspace_module
from apps.api.wilq_api.routers.content_selected_workspace import (
    register_content_selected_workspace_route,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.documents.revisions import ContentDraftRevisionState
from wilq.content.workflow.pipeline_steps.operator_steps import (
    ContentDraftRevisionWorkspaceStatus,
    ContentWorkflowOperatorFacts,
    ContentWorkflowOperatorJourney,
    build_content_workflow_operator_journey,
)
from wilq.content.workflow.workspace.document_workspace import ContentDocumentWorkspace
from wilq.schemas import ContentDecisionItem


class _CopyableProjection(SimpleNamespace):
    def model_copy(self, *, update: dict[str, object]) -> _CopyableProjection:
        return type(self)(**(vars(self) | update))


def _block_selected_snapshot_side_effects(monkeypatch) -> None:
    def unexpected_side_effect(*_args, **_kwargs):
        raise AssertionError("selected snapshot entered a default or planning side-effect seam")

    for name in (
        "content_workflow_store",
        "content_planning_proposal_store",
        "read_content_planning_proposal",
        "snapshot_for_work_item_or_404",
    ):
        monkeypatch.setattr(
            selected_snapshot_router,
            name,
            unexpected_side_effect,
            raising=False,
        )


def test_selected_workspace_keeps_exact_missing_state_out_of_catalogue_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        selected_workspace_module, "build_content_document_workspace", lambda _id, **_kwargs: None
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
        selected_workspace_module,
        "build_content_document_workspace",
        lambda _id, **_kwargs: expected,
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
        revision_state: ContentDraftRevisionState | None,
        item: ContentWorkItem,
        read_material: bool,
    ):
        seen.update(
            work_item_id=work_item_id,
            revision_context_current=revision_context_current,
            revision_state=revision_state,
            item=item,
            read_material=read_material,
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
        "revision_state": None,
        "item": item,
        "read_material": False,
    }


def test_selected_workspace_route_returns_typed_missing_selection(monkeypatch) -> None:
    journey = _operator_journey()
    item = ContentWorkItem(id="content_work_item_missing", topic="Brakujący temat")
    snapshot_calls: list[dict[str, object]] = []
    revision_state = ContentDraftRevisionState(status="empty", revision_count=0)
    store = type(
        "Store",
        (),
        {
            "load_production_classification_for_work_item": lambda _self, _id: None,
            "load_draft_revision_state": lambda _self, _id: revision_state,
        },
    )()
    factory_calls: list[object] = []

    def store_factory() -> object:
        factory_calls.append(store)
        return store

    monkeypatch.setattr(selected_workspace_router, "content_workflow_store", store_factory)

    def load_snapshot(
        work_item_id: str,
        *,
        store: object,
        revision_state: ContentDraftRevisionState,
    ):
        snapshot_calls.append(
            {
                "work_item_id": work_item_id,
                "store": store,
                "revision_state": revision_state,
            }
        )
        return type(
            "Snapshot",
            (),
            {
                "revision_workspace": type("Revision", (), {"context_current": True})(),
                "preflight": type("Preflight", (), {"item": item})(),
                "current_step_id": journey.current_step_id,
                "operator_steps": journey.steps,
            },
        )()

    monkeypatch.setattr(
        selected_workspace_router,
        "selected_workspace_snapshot_for_work_item_or_404",
        load_snapshot,
    )

    monkeypatch.setattr(
        selected_workspace_module, "build_content_document_workspace", lambda _id, **_kwargs: None
    )
    router = APIRouter()
    register_content_selected_workspace_route(router)
    endpoint = next(
        route.endpoint
        for route in router.routes
        if getattr(route, "path", "").endswith("/selected-workspace")
    )
    response = endpoint("content_work_item_missing")

    assert snapshot_calls == [
        {
            "work_item_id": "content_work_item_missing",
            "store": store,
            "revision_state": revision_state,
        }
    ]
    assert factory_calls == [store]
    assert response.model_dump(mode="json") == {
        "response_type": "content_selected_workspace",
        "contract_version": "content_selected_workspace_v2",
        "status": "missing",
        "work_item_id": "content_work_item_missing",
        "requested_work_item_id": "content_work_item_missing",
        "production_decision": {"status": "missing"},
        "operator_journey": journey.model_dump(mode="json"),
        "workspace": None,
        "reason": "Nie znaleziono istniejącej strony do odświeżenia pod tym dokładnym adresem.",
        "safe_next_step": (
            "Wróć do wyboru pracy i wybierz istniejącą stronę albo rozpocznij brief nowej strony."
        ),
    }


def test_selected_workspace_snapshot_uses_explicit_store_without_factory(monkeypatch) -> None:
    revision_state = ContentDraftRevisionState(status="empty", revision_count=0)
    planning_decisions = [SimpleNamespace(id="planning-decision")]
    review = SimpleNamespace(id="human-review")
    audit = SimpleNamespace(id="review-audit")
    freshness = SimpleNamespace(status="fresh")
    selected = ContentDecisionItem.model_construct(
        id="bdo",
        source_connectors=["google_search_console"],
    )
    store_calls: list[tuple[str, str]] = []
    build_calls: list[dict[str, object]] = []

    class ExplicitStore:
        def load_draft_revision_state(self, work_item_id: str) -> ContentDraftRevisionState:
            store_calls.append(("revision", work_item_id))
            return revision_state

        def load_planning_decisions(self, work_item_id: str) -> list[object]:
            store_calls.append(("planning", work_item_id))
            return planning_decisions

        def latest_human_review(self, work_item_id: str) -> object:
            store_calls.append(("review", work_item_id))
            return review

        def latest_audit_for_review(self, review_id: str) -> object:
            store_calls.append(("audit", review_id))
            return audit

    store = ExplicitStore()

    _block_selected_snapshot_side_effects(monkeypatch)
    monkeypatch.setattr(
        selected_snapshot_router,
        "build_content_diagnostics_cached",
        lambda: SimpleNamespace(decision_queue=[selected]),
    )
    monkeypatch.setattr(
        selected_snapshot_router,
        "inventory_decision_for_work_item",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        selected_snapshot_router,
        "content_work_item_has_persisted_material",
        lambda _selected: False,
    )
    monkeypatch.setattr(
        selected_snapshot_router,
        "build_content_freshness_assessment_fast",
        lambda *, relevant_connector_ids: freshness,
    )

    def build_snapshot(decision, **kwargs):
        build_calls.append({"decision": decision, **kwargs})
        return _CopyableProjection(human_review=_CopyableProjection(review_recorded=False))

    monkeypatch.setattr(
        selected_snapshot_router,
        "build_content_work_item_snapshot_response_from_selected_decision",
        build_snapshot,
    )

    result = selected_snapshot_router.selected_workspace_snapshot_for_work_item_or_404(
        "content_work_item_bdo",
        store=store,
    )

    assert store_calls == [
        ("revision", "content_work_item_bdo"),
        ("planning", "content_work_item_bdo"),
        ("review", "content_work_item_bdo"),
        ("audit", "human-review"),
    ]
    assert len(build_calls) == 2
    assert build_calls[0]["decision"] is build_calls[1]["decision"]
    assert [call["freshness_assessment"] for call in build_calls] == [freshness, freshness]
    assert build_calls[0]["revision_state"] is revision_state
    assert build_calls[0]["planning_decisions"] is planning_decisions
    assert build_calls[0]["human_review"] is None
    assert build_calls[0]["audit"] is None
    assert build_calls[1]["human_review"] is review
    assert build_calls[1]["audit"] is audit
    assert [call["generated_planning_proposal"] for call in build_calls] == [None, None]
    assert result.human_review.review_recorded is True


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
        lambda _id, **_kwargs: workspace,
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
            revision_bound_wordpress_handoff_ready=(revision_bound_wordpress_handoff_ready),
        )
    )
