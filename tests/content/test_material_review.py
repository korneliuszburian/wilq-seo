from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.wilq_api.routers.content_material_review import (
    register_content_material_review_routes,
)
from wilq.content.workflow.material_review import ContentMaterialReviewReadResponse
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)

WORK_ITEM_ID = "content_work_item_material_review"
PAGE_URL = "https://www.ekologus.pl/oferta/material-review/"
PAGE_PATH = "/oferta/material-review/"
READ_AT = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)


@pytest.fixture
def material_review_routes(tmp_path):
    body = {"value": "Treść strony " + ("stabilna " * 300)}
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
    clock_state = SimpleNamespace(now=READ_AT)

    def read_material(_url: str) -> SimpleNamespace:
        return SimpleNamespace(
            url=PAGE_URL,
            content_text=body["value"],
            extraction_region="public_html.main_or_article",
        )

    def clock() -> datetime:
        current = clock_state.now
        clock_state.now += timedelta(microseconds=1)
        return current

    def refresh_catalog() -> None:
        nonlocal catalog
        refreshed_item = catalog_item.model_copy(
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
                "items": [refreshed_item],
                "evidence_ids": [
                    "ev_catalog_material_review_refresh",
                    refreshed_item.evidence_id,
                ],
            }
        )
        clock_state.now = READ_AT + timedelta(hours=25)

    app = FastAPI()
    register_content_material_review_routes(
        app.router,
        store_factory=lambda: store,
        catalog_loader=lambda: catalog,
        selected_item_loader=lambda _work_item_id: selected,
        material_reader_factory=lambda: read_material,
        clock=clock,
    )
    return SimpleNamespace(
        body=body,
        client=TestClient(app),
        refresh_catalog=refresh_catalog,
        selected=selected,
        store=store,
    )


def _preview_and_approve(routes) -> dict[str, object]:
    preview_response = routes.client.post(
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
    reviewed = routes.client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review",
        json={
            "preview_id": preview["preview_id"],
            "preview_digest": preview["preview_digest"],
            "decision": "approved",
            "reviewer": "wilku",
            "reviewed_full_material": True,
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    return preview


def test_public_material_review_routes_are_immutable_idempotent_and_drift_aware(
    material_review_routes,
) -> None:
    routes = material_review_routes
    _preview_and_approve(routes)
    current = routes.client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review"
    ).json()
    assert current["status"] == "approved_current"
    original_digest = current.get("material_meaning_digest")
    assert original_digest is not None
    original_preview = current["preview"]
    original_review = current["review"]
    original_observation_id = current["current_observation"]["observation_id"]

    routes.refresh_catalog()
    refreshed = routes.client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review"
    ).json()
    assert refreshed["status"] == "approved_current"
    assert refreshed["preview"] == original_preview
    assert refreshed["review"] == original_review
    assert refreshed["material_meaning_digest"] == original_digest
    assert refreshed["current_observation"]["observation_id"] != original_observation_id


def test_material_review_routes_revalidate_before_recording_and_allow_idempotent_retry(
    material_review_routes,
) -> None:
    routes = material_review_routes
    preview_response = routes.client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review/preview"
    )
    preview = preview_response.json()["preview"]
    payload = {
        "preview_id": preview["preview_id"],
        "preview_digest": preview["preview_digest"],
        "decision": "approved",
        "reviewer": "wilku",
        "reviewed_full_material": True,
    }
    routes.body["value"] += " drift before receipt"
    drifted = routes.client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review", json=payload
    )
    assert drifted.status_code == 409
    assert routes.store.latest_content_material_review(WORK_ITEM_ID) is None
    missing = routes.client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review"
    ).json()
    assert missing["status"] == "missing"
    assert missing["material_meaning_digest"] is None

    routes.body["value"] = "Treść strony " + ("stabilna " * 300)
    first = routes.client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review", json=payload
    )
    retry = routes.client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review", json=payload
    )
    assert first.status_code == 200
    assert first.json()["status"] == "created"
    assert retry.status_code == 200
    assert retry.json()["status"] == "idempotent"


def test_changed_material_requires_new_review_and_gets_new_meaning_digest(
    material_review_routes,
) -> None:
    routes = material_review_routes
    _preview_and_approve(routes)
    original_digest = routes.client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review"
    ).json()["material_meaning_digest"]
    routes.body["value"] = routes.body["value"][:2400] + " drift after excerpt"

    stale = routes.client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review"
    ).json()
    assert stale["status"] == "stale"
    assert stale["material_meaning_digest"] is None
    assert routes.selected.wordpress_content_material_confidence == "review_required"

    _preview_and_approve(routes)
    changed = routes.client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review"
    ).json()
    assert changed["status"] == "approved_current"
    assert changed["material_meaning_digest"] != original_digest


def test_approved_current_read_response_rejects_forged_material_bindings(
    material_review_routes,
) -> None:
    routes = material_review_routes
    _preview_and_approve(routes)
    response = routes.client.get(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review"
    ).json()
    _assert_material_review_response_rejects_forgery(response)


def _assert_material_review_response_rejects_forgery(
    response: dict[str, object],
) -> None:
    for change in (
        {"material_meaning_digest": "0" * 64},
        {"preview": None},
        {"review": None},
        {"current_observation": None},
    ):
        with pytest.raises(ValidationError):
            ContentMaterialReviewReadResponse.model_validate({**response, **change})
