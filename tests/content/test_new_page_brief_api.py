from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_new_page_brief as new_page_router_module
import wilq.content.workflow.new_page as new_page_module
from apps.api.wilq_api.routers.content_workflow import router
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)
from wilq.content.workflow.new_page import (
    ContentNewPageBriefInput,
    build_new_page_brief,
    build_new_page_overlap_guard,
)
from wilq.content.workflow.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevisionConflict,
    ContentDraftRevisionReviewResult,
)


def _review_workspace() -> ContentNewPageCanonicalDocumentWorkspace:
    return ContentNewPageCanonicalDocumentWorkspace(
        status="review_required",
        work_item_id="content_work_item_new_page_review",
        brief_id="content_new_page_brief_review",
        brief_digest="a" * 64,
        foundation_id="content_new_page_foundation_review",
        service_card_id="knowledge_service_environment",
        service_card_digest="b" * 64,
        proposal_id="content_planning_proposal_review",
        planning_digest="c" * 64,
        planning_input_digest="d" * 64,
        title="Dokumentacja środowiskowa inwestycji",
        proposed_ia_location="Usługi → Dokumentacja środowiskowa",
        safe_next_step="Sprawdź plan nowej strony przed zapisem decyzji.",
    )


def test_new_page_plan_review_returns_the_current_typed_workspace_on_conflict(
    monkeypatch,
) -> None:
    workspace = _review_workspace()
    monkeypatch.setattr(
        new_page_router_module,
        "_new_page_canonical_document_workspace",
        lambda brief_id: workspace,
    )
    monkeypatch.setattr(
        new_page_router_module,
        "content_workflow_store",
        lambda: (_ for _ in ()).throw(AssertionError("Conflict must not record review state.")),
    )
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post(
        f"/api/content/new-page-briefs/{workspace.brief_id}/planning-review",
        json={
            "expected_proposal_id": workspace.proposal_id,
            "expected_planning_digest": "e" * 64,
            "expected_planning_input_digest": workspace.planning_input_digest,
            "decision": "approved",
            "reviewed_by": "Wilku",
            "checked_items": ["Zakres planu"],
        },
    )

    assert response.status_code == 409
    assert "detail" not in response.json()
    parsed = ContentNewPageCanonicalDocumentWorkspace.model_validate(response.json())
    assert parsed.proposal_id == workspace.proposal_id
    assert parsed.planning_digest == workspace.planning_digest
    assert parsed.planning_input_digest == workspace.planning_input_digest
    assert app.openapi()["paths"][
        "/api/content/new-page-briefs/{brief_id}/planning-review"
    ]["post"]["responses"]["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ContentNewPageCanonicalDocumentWorkspace"
    }


def test_new_page_plan_review_records_only_an_exact_current_decision(monkeypatch) -> None:
    workspace = _review_workspace()
    recorded: list[tuple[object, object, object]] = []

    class PlanningStore:
        def record_planning_review(self, work_item_id, request, **kwargs):
            recorded.append((work_item_id, request, kwargs))
            return "created", None

    monkeypatch.setattr(
        new_page_router_module,
        "_new_page_canonical_document_workspace",
        lambda brief_id: workspace,
    )
    monkeypatch.setattr(new_page_router_module, "content_workflow_store", PlanningStore)
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post(
        f"/api/content/new-page-briefs/{workspace.brief_id}/planning-review",
        json={
            "expected_proposal_id": workspace.proposal_id,
            "expected_planning_digest": workspace.planning_digest,
            "expected_planning_input_digest": workspace.planning_input_digest,
            "decision": "approved",
            "reviewed_by": "Wilku",
            "checked_items": ["Zakres planu"],
        },
    )

    assert response.status_code == 200
    assert response.json()["proposal_id"] == workspace.proposal_id
    assert len(recorded) == 1
    work_item_id, recorded_request, record_kwargs = recorded[0]
    assert work_item_id == workspace.work_item_id
    assert recorded_request.expected_planning_digest == workspace.planning_digest
    assert record_kwargs == {
        "planning_digest": workspace.planning_digest,
        "service_card_id": workspace.service_card_id,
        "human_override_review_required": False,
    }


def test_new_page_revision_review_preserves_typed_current_revision_conflict(
    monkeypatch,
) -> None:
    workspace = _review_workspace()
    monkeypatch.setattr(
        new_page_router_module,
        "_new_page_canonical_document_workspace",
        lambda brief_id: workspace,
    )
    monkeypatch.setattr(
        new_page_router_module,
        "review_new_page_revision",
        lambda **_: ContentDraftRevisionReviewResult(
            status="conflict",
            conflict=ContentDraftRevisionConflict(
                code="stale_revision",
                current_revision_id="content_revision_current",
                current_revision_digest="f" * 64,
            ),
        ),
    )
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post(
        f"/api/content/new-page-briefs/{workspace.brief_id}/draft-revisions/content_revision_old/review",
        json={
            "expected_revision_digest": "e" * 64,
            "reviewed_by": "Wilku",
            "decision": "approved",
            "checked_items": ["Dokument"],
            "evidence_ids": ["ev_service"],
        },
    )

    assert response.status_code == 409
    assert "detail" not in response.json()
    assert response.json() == {
        "status": "conflict",
        "code": "stale_revision",
        "current_revision_id": "content_revision_current",
        "current_digest": "f" * 64,
        "safe_next_step": (
            "Ta wersja nie jest już najnowsza. Odśwież snapshot i sprawdź aktualną "
            "wersję bez przenoszenia starej decyzji."
        ),
    }
    assert app.openapi()["paths"][
        "/api/content/new-page-briefs/{brief_id}/draft-revisions/{revision_id}/review"
    ]["post"]["responses"]["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ContentDraftRevisionConflictResponse"
    }


def test_new_page_brief_persists_without_a_public_url_and_requires_human_overlap_decision(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "new-page.sqlite3"))
    monkeypatch.setattr(
        new_page_module,
        "build_content_inventory_catalog_cached",
        lambda: ContentInventoryCatalogResponse(
            total_count=1,
            items=[
                ContentInventoryCatalogItem(
                    catalog_id="inventory_audit",
                    work_item_id="content_work_item_audit",
                    url="https://www.ekologus.pl/audyt-srodowiskowy/",
                    path="/audyt-srodowiskowy/",
                    title="Audyt środowiskowy dla inwestycji",
                    content_type="page",
                    material_status="content_and_structure",
                    source_connector="wordpress_ekologus",
                    evidence_id="ev_wp_audit",
                    collected_at=new_page_module.utc_now(),
                )
            ],
            evidence_ids=["ev_wp_audit"],
            source_connectors=["wordpress_ekologus"],
        ),
    )
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    payload = {
        "title": "Nowa strona o audycie",
        "purpose": "Pomóc inwestorowi przygotować audyt środowiskowy.",
        "service": "Audyt środowiskowy",
        "audience": "Inwestor przygotowujący przedsięwzięcie",
        "search_intent": "audyt środowiskowy dla inwestycji",
        "proposed_ia_location": "Usługi → Dokumentacja środowiskowa",
    }

    created = client.post("/api/content/new-page-briefs", json=payload)

    assert created.status_code == 200
    saved = created.json()
    assert saved["brief"]["work_kind"] == "new_page"
    assert "url" not in saved["brief"]
    assert saved["overlap_guard"]["disposition"] == "human_decision_required"
    assert saved["overlap_guard"]["candidates"] == [
        {
            "title": "Audyt środowiskowy dla inwestycji",
            "url": "https://www.ekologus.pl/audyt-srodowiskowy/",
            "match_kind": "shared_intent",
            "evidence_ids": ["ev_wp_audit"],
        }
    ]
    assert saved["review_status"] == "blocked"

    reloaded = client.get(f"/api/content/new-page-briefs/{saved['brief']['brief_id']}")

    assert reloaded.status_code == 200
    assert reloaded.json()["brief"] == saved["brief"]
    assert reloaded.json()["overlap_guard"]["evidence_ids"] == ["ev_wp_audit"]


def test_new_page_overlap_guard_does_not_infer_a_match_from_an_inventory_slug() -> None:
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Audyt inwestycji liniowej",
            purpose="Wyjaśnić przygotowanie audytu dla inwestycji liniowej.",
            service="Dokumentacja inwestycji",
            audience="Inwestor",
            search_intent="audyt inwestycji liniowej",
            proposed_ia_location="Usługi → Dokumentacja",
        )
    )
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="inventory_slug_only",
                work_item_id="content_work_item_other",
                url="https://www.ekologus.pl/audyt-inwestycji-liniowej/",
                path="/audyt-inwestycji-liniowej/",
                title="Pozwolenie wodnoprawne",
                content_type="page",
                material_status="content_and_structure",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_other",
                collected_at=new_page_module.utc_now(),
            )
        ],
    )

    guard = build_new_page_overlap_guard(brief, catalog=catalog)

    assert guard.disposition == "no_conflict"
    assert guard.candidates == []
    assert guard.evidence_ids == ["ev_wp_other"]


def test_new_page_overlap_guard_does_not_claim_no_conflict_without_catalog_evidence() -> None:
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Audyt inwestycji liniowej",
            purpose="Wyjaśnić przygotowanie audytu dla inwestycji liniowej.",
            service="Dokumentacja inwestycji",
            audience="Inwestor",
            search_intent="audyt inwestycji liniowej",
            proposed_ia_location="Usługi → Dokumentacja",
        )
    )
    catalog = ContentInventoryCatalogResponse(total_count=0)

    guard = build_new_page_overlap_guard(brief, catalog=catalog)

    assert guard.disposition == "human_decision_required"
    assert guard.evidence_ids == []


def test_new_page_foundation_requires_exact_no_conflict_guard_and_explicit_approved_service(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "new-page-foundation.sqlite3"))
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="inventory_other",
                work_item_id="content_work_item_other",
                url="https://www.ekologus.pl/pozwolenie-wodne/",
                path="/pozwolenie-wodne/",
                title="Pozwolenie wodnoprawne",
                content_type="page",
                material_status="content_and_structure",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_other",
                collected_at=new_page_module.utc_now(),
            )
        ],
        evidence_ids=["ev_wp_other"],
        source_connectors=["wordpress_ekologus"],
    )
    approved_service = next(
        card for card in ekologus_content_knowledge_cards() if card.card_type == "service"
    ).model_copy(update={"lifecycle_status": "approved_current"})
    monkeypatch.setattr(new_page_module, "build_content_inventory_catalog_cached", lambda: catalog)
    monkeypatch.setattr(
        new_page_router_module, "build_content_inventory_catalog_cached", lambda: catalog
    )
    monkeypatch.setattr(new_page_router_module, "new_page_service_card", lambda _: approved_service)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    created = client.post(
        "/api/content/new-page-briefs",
        json={
            "title": "Audyt inwestycji liniowej",
            "purpose": "Wyjaśnić przygotowanie audytu dla inwestycji liniowej.",
            "service": "Dokumentacja inwestycji",
            "audience": "Inwestor",
            "search_intent": "audyt inwestycji liniowej",
            "proposed_ia_location": "Usługi → Dokumentacja",
        },
    ).json()
    brief_id = created["brief"]["brief_id"]
    command = {
        "expected_brief_digest": created["brief"]["brief_digest"],
        "expected_overlap_digest": created["overlap_digest"],
        "service_card_id": approved_service.id,
        "confirmed_by": "Wilku",
    }

    stale = client.post(
        f"/api/content/new-page-briefs/{brief_id}/planning-foundation",
        json={**command, "expected_overlap_digest": "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["status"] == "conflict"

    saved = client.post(
        f"/api/content/new-page-briefs/{brief_id}/planning-foundation", json=command
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "created"
    assert saved.json()["foundation"]["brief_digest"] == command["expected_brief_digest"]
    assert saved.json()["foundation"]["overlap_digest"] == command["expected_overlap_digest"]
    assert saved.json()["foundation"]["service_card_id"] == approved_service.id

    reloaded = client.get(f"/api/content/new-page-briefs/{brief_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["foundation"] == saved.json()["foundation"]

    replay = client.post(
        f"/api/content/new-page-briefs/{brief_id}/planning-foundation", json=command
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "idempotent"

    alternate_service = approved_service.model_copy(update={"id": "knowledge_service_other"})
    monkeypatch.setattr(
        new_page_router_module,
        "new_page_service_card",
        lambda service_card_id: (
            alternate_service if service_card_id == alternate_service.id else approved_service
        ),
    )
    conflicting = client.post(
        f"/api/content/new-page-briefs/{brief_id}/planning-foundation",
        json={**command, "service_card_id": alternate_service.id},
    )

    assert conflicting.status_code == 409
    assert conflicting.json()["status"] == "conflict"
