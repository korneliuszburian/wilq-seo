from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import wilq.content.workflow.new_page as new_page_module
from apps.api.wilq_api.routers.content_workflow import router
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
