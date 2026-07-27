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
