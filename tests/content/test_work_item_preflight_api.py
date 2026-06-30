from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def _item(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
    }
    payload.update(overrides)
    return payload


def _inventory_record(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "inventory_bdo",
        "url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "content_status": "published",
        "source_connectors": ["wordpress_ekologus"],
        "evidence_ids": ["ev_wp_bdo"],
        "title": "BDO dla firm",
        "h1": "BDO dla firm",
        "topic_tags": ["bdo"],
    }
    payload.update(overrides)
    return payload


def _post_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    response = TestClient(app).post("/api/content/work-items/preflight", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert sorted(data) == ["inventory_resolution", "item", "preflight_verdict"]
    return data


def test_content_work_item_preflight_api_blocks_dev_preview_canonical() -> None:
    data = _post_preflight(
        {
            "item": _item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"),
            "inventory_records": [
                _inventory_record(
                    final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"
                )
            ],
            "duplicate_risk": "clear",
        }
    )

    assert data["inventory_resolution"]["status"] == "blocked"
    assert data["inventory_resolution"]["recommended_mode"] == "block"
    assert data["preflight_verdict"]["status"] == "blocked"
    assert data["preflight_verdict"]["wordpress_draft_allowed"] is False
    assert [blocker["code"] for blocker in data["preflight_verdict"]["blockers"]] == [
        "invalid_final_canonical"
    ]


def test_content_work_item_preflight_api_preserves_evidence_for_valid_item() -> None:
    data = _post_preflight(
        {
            "item": _item(),
            "inventory_records": [_inventory_record()],
            "duplicate_risk": "clear",
        }
    )

    assert data["inventory_resolution"]["status"] == "resolved"
    assert data["inventory_resolution"]["recommended_mode"] == "preserve"
    assert data["preflight_verdict"]["status"] == "plan_allowed"
    assert data["preflight_verdict"]["sales_brief_allowed"] is False
    assert data["preflight_verdict"]["evidence_ids"] == ["ev_gsc_bdo", "ev_wp_bdo"]
    assert data["preflight_verdict"]["source_connectors"] == [
        "google_search_console",
        "wordpress_ekologus",
    ]
    assert "https://ekologus.pl/bdo/" in data["preflight_verdict"]["similar_existing_urls"]


def test_existing_content_preflight_endpoint_shape_stays_unchanged() -> None:
    response = TestClient(app).get("/api/content/preflight")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "primary_item" in data
    assert data["items"]
    first_plan = data["primary_item"]
    assert "recommended_mode" in first_plan
    assert "inventory_gate_status" in first_plan
    assert "canonical_gate_status" in first_plan
    assert "draft_allowed" in first_plan
    assert "preflight_verdict" not in data
