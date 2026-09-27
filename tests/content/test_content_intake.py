from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_intake import register_content_intake_routes
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
)

REQUEST_ID = "00000000-0000-4000-8000-000000000100"
_COLLECTED_AT = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
_FRESH_DEMAND = {
    "google_search_console": "fresh",
    "google_analytics_4": "fresh",
    "ahrefs": "fresh",
    "wordpress_ekologus": "fresh",
}
_STALE_DEMAND = {
    "google_search_console": "stale",
    "google_analytics_4": "stale",
    "ahrefs": "missing",
    "wordpress_ekologus": "fresh",
}


def _item(
    *,
    catalog_id: str,
    work_item_id: str,
    url: str,
    path: str,
    content_type: str,
) -> ContentInventoryCatalogItem:
    return ContentInventoryCatalogItem(
        catalog_id=catalog_id,
        work_item_id=work_item_id,
        url=url,
        path=path,
        content_type=content_type,
        material_status="ready",
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp_run",
        collected_at=_COLLECTED_AT,
    )


def _catalog(
    items: list[ContentInventoryCatalogItem],
    *,
    status: str = "ready",
    coverage_status: str = "complete",
) -> ContentInventoryCatalogResponse:
    return ContentInventoryCatalogResponse(
        status=status,
        total_count=len(items),
        ready_count=len(items),
        items=items,
        source_connectors=["wordpress_ekologus"],
        evidence_ids=["ev_wp_run"],
        coverage=ContentInventoryCoverage(
            status=coverage_status,
            source_count=1,
            returned_count=1,
            public_sitemap_source_count=1,
            public_sitemap_returned_count=1,
            public_sitemap_limit=1,
            public_sitemap_truncated=False,
            limit=1,
            truncated=False,
        ),
    )


def _ppwr_catalog() -> ContentInventoryCatalogResponse:
    return _catalog(
        [
            _item(
                catalog_id="catalog_ppwr_article",
                work_item_id="content_work_item_inventory_362aab5923e47a4b9181e8ea",
                url="https://www.ekologus.pl/ppwr-rozporzadzenie-o-opakowaniach/",
                path="/ppwr-rozporzadzenie-o-opakowaniach",
                content_type="post",
            ),
            _item(
                catalog_id="catalog_ppwr_offer",
                work_item_id="content_work_item_inventory_d4ca77db23a568b9a75b35e3",
                url="https://www.ekologus.pl/oferta/wsparcie-ppwr/",
                path="/oferta/wsparcie-ppwr",
                content_type="page",
            ),
        ]
    )


def _bdo_catalog(**overrides: str) -> ContentInventoryCatalogResponse:
    return _catalog(
        [
            _item(
                catalog_id="catalog_bdo",
                work_item_id="content_work_item_inventory_bdo",
                url="https://www.ekologus.pl/bdo-ipcc/",
                path="/bdo-ipcc",
                content_type="post",
            )
        ],
        **overrides,
    )


def _approved_bdo_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="fact_bdo",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov/bdo",
        extracted_fact="Synthetic approved BDO fact for the exact page.",
        scope="claim_policy",
        freshness_date="2026-09-24",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["ev_official_fact"],
        source_connectors=["official_regulatory_review"],
        target_card_id="synthetic_bdo_profile",
        target_card_type="regulatory_source",
        target_card_title="Synthetic BDO profile",
        official_source=True,
        regulatory_profile_id="synthetic_bdo_profile",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["requirement_bdo"],
        applicable_canonical_paths=["/bdo-ipcc"],
    )


def _client(
    store: ContentWorkflowStore,
    *,
    catalog: ContentInventoryCatalogResponse | None = None,
    facts: tuple[ContentSourceFact, ...] = (),
    freshness: dict[str, str] | None = None,
) -> TestClient:
    router = APIRouter()
    register_content_intake_routes(
        router,
        store_factory=lambda: store,
        catalog_loader=lambda: catalog if catalog is not None else _ppwr_catalog(),
        source_facts_loader=lambda: facts,
        freshness_loader=lambda: freshness if freshness is not None else _STALE_DEMAND,
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_intake_is_idempotent_by_request_id(tmp_path: Path) -> None:
    client = _client(ContentWorkflowStore(tmp_path / "intake.sqlite3"))
    body = {"request_id": REQUEST_ID, "ask": "artykuł o PPWR"}

    first = client.post("/api/content/intake-requests", json=body)
    second = client.post("/api/content/intake-requests", json=body)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert first.json()["queue_id"] == second.json()["queue_id"]
    readback = client.get(f"/api/content/intake-requests/{first.json()['queue_id']}")
    assert readback.status_code == 200
    assert readback.json() == first.json()


def test_intake_rejects_conflicting_payload_for_same_request_id(tmp_path: Path) -> None:
    client = _client(ContentWorkflowStore(tmp_path / "intake-conflict.sqlite3"))

    first = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o PPWR"},
    )
    conflict = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o BDO"},
    )

    assert first.status_code == 201, first.text
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["detail"] == "intake_request_id_conflict"


def test_intake_accepts_ppwr_ask_without_guessing_brief_or_demand(tmp_path: Path) -> None:
    client = _client(ContentWorkflowStore(tmp_path / "intake-ppwr.sqlite3"))

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o PPWR"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert {blocker["code"] for blocker in payload["blockers"]} == {
        "intake_target_ambiguous",
        "demand_evidence_not_fresh",
        "approved_source_facts_missing",
    }
    assert payload["generation_allowed"] is False
    assert payload["candidate_work_item_ids"]
    assert payload["safe_next_step"]
    assert not any(key in payload for key in ("brief", "plan", "draft", "action"))
    provenance = {entry["field"]: entry["provenance"] for entry in payload["provenance"]}
    assert provenance["ask"] == "user_input"
    assert provenance["target_path"] == "evidence"
    assert provenance["demand"] == "unknown"


def test_intake_blocks_a_generic_ask_without_candidates(tmp_path: Path) -> None:
    client = _client(ContentWorkflowStore(tmp_path / "intake-generic.sqlite3"))

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "zrób coś fajnego"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "intake_ask_too_generic" in {b["code"] for b in payload["blockers"]}
    assert payload["candidate_work_item_ids"] == []


def test_intake_blocks_an_ask_without_a_catalog_match(tmp_path: Path) -> None:
    client = _client(ContentWorkflowStore(tmp_path / "intake-target-missing.sqlite3"))

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o reaktorach jądrowych"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "intake_target_missing" in {b["code"] for b in payload["blockers"]}


def test_intake_queues_a_single_candidate_with_current_inventory(tmp_path: Path) -> None:
    client = _client(
        ContentWorkflowStore(tmp_path / "intake-queued.sqlite3"),
        catalog=_bdo_catalog(),
        facts=(_approved_bdo_fact(),),
        freshness=_FRESH_DEMAND,
    )

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o BDO"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["blockers"] == []
    assert payload["provenance"][1]["detail"] == "Dopasowanie z bieżącego katalogu WILQ."
    provenance = {entry["field"]: entry["provenance"] for entry in payload["provenance"]}
    assert provenance["target_path"] == "evidence"
    assert provenance["source_facts"] == "evidence"


def test_intake_blocks_a_stale_wordpress_inventory(tmp_path: Path) -> None:
    stale_wordpress = {**_FRESH_DEMAND, "wordpress_ekologus": "stale"}
    client = _client(
        ContentWorkflowStore(tmp_path / "intake-stale-wp.sqlite3"),
        catalog=_bdo_catalog(),
        facts=(_approved_bdo_fact(),),
        freshness=stale_wordpress,
    )

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o BDO"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "intake_inventory_not_current" in {b["code"] for b in payload["blockers"]}
    target = next(entry for entry in payload["provenance"] if entry["field"] == "target_path")
    assert "nie jest potwierdzony" in target["detail"]


def test_intake_blocks_an_incomplete_inventory_catalog(tmp_path: Path) -> None:
    client = _client(
        ContentWorkflowStore(tmp_path / "intake-incomplete.sqlite3"),
        catalog=_bdo_catalog(status="blocked", coverage_status="partial"),
        facts=(_approved_bdo_fact(),),
        freshness=_FRESH_DEMAND,
    )

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o BDO"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "intake_inventory_incomplete" in {b["code"] for b in payload["blockers"]}
    target = next(entry for entry in payload["provenance"] if entry["field"] == "target_path")
    assert "nie jest potwierdzony" in target["detail"]


def test_intake_blocks_combined_incomplete_and_stale_inventory(tmp_path: Path) -> None:
    stale_wordpress = {**_FRESH_DEMAND, "wordpress_ekologus": "stale"}
    client = _client(
        ContentWorkflowStore(tmp_path / "intake-incomplete-stale.sqlite3"),
        catalog=_bdo_catalog(status="blocked", coverage_status="partial"),
        facts=(_approved_bdo_fact(),),
        freshness=stale_wordpress,
    )

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o BDO"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    codes = {b["code"] for b in payload["blockers"]}
    assert {"intake_inventory_incomplete", "intake_inventory_not_current"} <= codes
    target = next(entry for entry in payload["provenance"] if entry["field"] == "target_path")
    assert "nie jest potwierdzony" in target["detail"]


def test_intake_matches_approved_facts_across_path_normalization(tmp_path: Path) -> None:
    client = _client(
        ContentWorkflowStore(tmp_path / "intake-normalized.sqlite3"),
        catalog=_catalog(
            [
                _item(
                    catalog_id="catalog_bdo",
                    work_item_id="content_work_item_inventory_bdo",
                    url="https://www.ekologus.pl/bdo-ipcc/",
                    path="/bdo-ipcc/",
                    content_type="post",
                )
            ]
        ),
        facts=(_approved_bdo_fact(),),
        freshness=_FRESH_DEMAND,
    )

    response = client.post(
        "/api/content/intake-requests",
        json={"request_id": REQUEST_ID, "ask": "artykuł o BDO"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["blockers"] == []


def test_intake_readback_returns_typed_missing_for_unknown_queue_id(tmp_path: Path) -> None:
    client = _client(ContentWorkflowStore(tmp_path / "intake-readback.sqlite3"))

    response = client.get("/api/content/intake-requests/content_intake_missing")

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "intake_queue_item_missing"
