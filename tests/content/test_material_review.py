from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_material_review import (
    register_content_material_review_routes,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)

WORK_ITEM_ID = "content_work_item_material_review"
PAGE_URL = "https://www.ekologus.pl/oferta/material-review/"
PAGE_PATH = "/oferta/material-review/"
READ_AT = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)


def test_public_material_review_routes_are_immutable_idempotent_and_drift_aware(
    tmp_path,
) -> None:
    original_body = "Treść strony " + ("stabilna " * 300)
    body = {"value": original_body}
    store = ContentWorkflowStore(tmp_path / "material-review.sqlite3")
    catalog_item = ContentInventoryCatalogItem(
        catalog_id="catalog_material_review",
        work_item_id=WORK_ITEM_ID,
        url=PAGE_URL,
        path=PAGE_PATH,
        title="Materiał review",
        content_type="page",
        content_summary="Treść strony",
        content_word_count=302,
        section_count=1,
        section_headings=["Materiał"],
        material_status="url_only",
        source_connector="wordpress_ekologus",
        evidence_id="ev_inventory_material_review",
        collected_at=READ_AT,
    )
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        ready_count=1,
        items=[catalog_item],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=[catalog_item.evidence_id],
    )
    selected = SimpleNamespace(
        id=WORK_ITEM_ID.removeprefix("content_work_item_"),
        final_canonical_url=PAGE_URL,
        source_public_url=PAGE_URL,
        normalized_page_path=PAGE_PATH,
        wordpress_content_material_confidence="review_required",
        wordpress_content_source_field_lineage=["public_html.main_or_article"],
    )

    def read_material(_url: str) -> SimpleNamespace:
        return SimpleNamespace(
            url=PAGE_URL,
            content_text=body["value"],
            extraction_region="public_html.main_or_article",
        )

    clock_now = READ_AT

    def clock() -> datetime:
        nonlocal clock_now
        current = clock_now
        clock_now += timedelta(microseconds=1)
        return current

    app = FastAPI()
    register_content_material_review_routes(
        app.router,
        store_factory=lambda: store,
        catalog_loader=lambda: catalog,
        selected_item_loader=lambda _work_item_id: selected,
        material_reader_factory=lambda: read_material,
        clock=clock,
    )
    client = TestClient(app)

    preview_response = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review/preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()["preview"]
    assert preview["work_item_id"] == WORK_ITEM_ID
    assert preview["catalog_item_digest"]
    assert preview["catalog_snapshot_digest"]
    assert preview["observation"]["body_digest"]
    assert preview["observation"]["sanitized_excerpt"]
    assert "stabilna stabilna" in preview["observation"]["sanitized_excerpt"]
    assert "content_text" not in preview["observation"]

    review_payload = {
        "preview_id": preview["preview_id"],
        "preview_digest": preview["preview_digest"],
        "decision": "approved",
        "reviewer": "wilku",
        "reviewed_full_material": True,
    }
    body["value"] = original_body + " drift before receipt"
    drifted_review = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review",
        json=review_payload,
    )
    assert drifted_review.status_code == 409
    assert store.latest_content_material_review(WORK_ITEM_ID) is None
    assert client.get(f"/api/content/work-items/{WORK_ITEM_ID}/material-review").json()[
        "status"
    ] == "missing"

    body["value"] = original_body
    reviewed = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review",
        json=review_payload,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "created"

    retry = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review",
        json=review_payload,
    )
    assert retry.status_code == 200
    assert retry.json()["status"] == "idempotent"

    current = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/material-review")
    assert current.status_code == 200
    assert current.json()["status"] == "approved_current"
    original_preview = current.json()["preview"]
    original_review = current.json()["review"]
    original_observation_id = current.json()["current_observation"]["observation_id"]

    # Catalog metrics/evidence can refresh without changing the reviewed page material.
    refreshed_catalog_item = catalog_item.model_copy(
        update={
            "evidence_id": "ev_inventory_material_review_refresh",
            "metrics_status": "available",
            "metrics_evidence_ids": ["ev_metrics_material_review_refresh"],
            "metrics_query_count": 4,
            "metrics_clicks": 12,
            "metrics_impressions": 180,
            "collected_at": READ_AT + timedelta(hours=25),
        }
    )
    catalog = catalog.model_copy(
        update={
            "items": [refreshed_catalog_item],
            "evidence_ids": [
                "ev_catalog_material_review_refresh",
                refreshed_catalog_item.evidence_id,
            ],
        }
    )
    clock_now = READ_AT + timedelta(hours=25)
    refreshed = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/material-review")
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "approved_current"
    assert refreshed.json()["preview"] == original_preview
    assert refreshed.json()["review"] == original_review
    assert (
        refreshed.json()["current_observation"]["observation_id"]
        != original_observation_id
    )

    # Keep the bounded excerpt stable while changing the body outside it.
    body["value"] = body["value"][:2400] + " drift after excerpt"
    drifted = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/material-review")
    assert drifted.status_code == 200
    assert drifted.json()["status"] == "stale"
    assert selected.wordpress_content_material_confidence == "review_required"
