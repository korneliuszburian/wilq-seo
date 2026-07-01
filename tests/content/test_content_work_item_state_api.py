from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def test_selected_content_work_item_state_is_isolated(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    first, second = _first_two_actionable_queue_items(client)

    first_snapshot = _get_selected_snapshot(client, first["work_item_id"])

    first_item = first_snapshot["preflight"]["item"]
    first_draft = first_snapshot["draft_package"]["draft_package_result"]["draft_package"]
    review = _human_review(first_item, first_draft)

    review_response = client.post(
        f"/api/content/work-items/{first['work_item_id']}/human-review",
        json={"review": review},
    )
    assert review_response.status_code == 200
    assert review_response.json()["wordpress_handoff_allowed"] is True

    wrong_item_response = client.post(
        f"/api/content/work-items/{second['work_item_id']}/human-review",
        json={"review": review},
    )
    assert wrong_item_response.status_code == 200
    assert wrong_item_response.json()["wordpress_handoff_allowed"] is False
    assert "wrong_work_item" in [
        blocker["code"] for blocker in wrong_item_response.json()["blockers"]
    ]

    first_after_review = _get_selected_snapshot(client, first["work_item_id"])
    second_after_review = _get_selected_snapshot(client, second["work_item_id"])
    assert first_after_review["human_review"]["review"]["id"] == review["id"]
    assert first_after_review["human_review"]["reviewed_item"]["human_review_status"] == "approved"
    assert second_after_review["human_review"]["review"] is None
    assert second_after_review["human_review"]["reviewed_item"]["human_review_status"] == "missing"

    audit = _audit(first_item, review)
    audit_response = client.post(
        f"/api/content/work-items/{first['work_item_id']}/audit",
        json={"audit": audit},
    )
    assert audit_response.status_code == 200
    assert audit_response.json()["handoff_result"]["handoff"]["post_status"] == "draft"
    assert audit_response.json()["handoff_result"]["handoff"]["publish_allowed"] is False

    first_after_audit = _get_selected_snapshot(client, first["work_item_id"])
    second_after_audit = _get_selected_snapshot(client, second["work_item_id"])
    assert first_after_audit["wordpress_handoff"]["handoff_result"]["handoff"]["audit_id"] == audit[
        "audit_id"
    ]
    assert second_after_audit["wordpress_handoff"]["handoff_result"]["handoff"] is None
    assert "missing_human_review" in [
        blocker["code"]
        for blocker in second_after_audit["wordpress_handoff"]["handoff_result"]["blockers"]
    ]


def test_blocked_queue_item_does_not_get_fake_workflow_snapshot(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    queue = client.get("/api/content/work-items/queue").json()
    blocked = next(
        candidate for candidate in queue["candidates"] if candidate["recommended_mode"] == "block"
    )

    response = client.get(f"/api/content/work-items/{blocked['work_item_id']}/snapshot")

    assert response.status_code == 404
    assert response.json()["detail"] == "Content work item is not available for the gated workflow."


def _first_two_actionable_queue_items(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    queue = client.get("/api/content/work-items/queue").json()
    actionable = [
        candidate for candidate in queue["candidates"] if candidate["recommended_mode"] != "block"
    ]
    assert len(actionable) >= 2
    return actionable[0], actionable[1]


def _get_selected_snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _human_review(item: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"human_review_{item['id']}",
        "work_item_id": item["id"],
        "stage": "draft_package",
        "reviewed_by": "wilku",
        "decision": "approved",
        "notes": "Szkic może iść dalej jako WordPress draft.",
        "checked_items": [
            "brief zgodny z dowodami",
            "claimy bez gwarancji efektu",
            "CTA bez obietnicy wyniku",
        ],
        "evidence_ids": item["evidence_ids"],
        "blocked_claims_handled": [],
        "draft_package_id": draft["id"],
    }


def _audit(item: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_id": f"audit_{item['id']}",
        "actor": "wilku",
        "reason": "Zatwierdzony szkic może trafić do WordPress jako draft.",
        "evidence_ids": item["evidence_ids"],
        "human_review_id": review["id"],
    }
