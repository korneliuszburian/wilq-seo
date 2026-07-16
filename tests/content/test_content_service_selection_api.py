from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def test_planning_scope_persists_only_allowed_service_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    work_item_id, snapshot = _snapshot_with_service_override(client)
    proposal = snapshot["planning_workspace"]["proposal"]
    candidates = snapshot["service_profile_context"]["service_candidates"]
    recommended = next(candidate for candidate in candidates if candidate["recommended"])
    override = next(candidate for candidate in candidates if not candidate["recommended"])

    unknown_payload = _planning_review_payload(proposal["planning_digest"])
    unknown_payload["service_card_id"] = "ekologus_service_unknown"
    unknown = client.post(_planning_review_path(work_item_id), json=unknown_payload)
    assert unknown.status_code == 422
    assert unknown.json()["detail"] == (
        "Wybrana karta usługi nie jest dozwolona dla tego work itemu."
    )

    override_payload = _planning_review_payload(proposal["planning_digest"])
    override_payload["service_card_id"] = override["service_card_id"]
    recorded = client.post(_planning_review_path(work_item_id), json=override_payload)

    assert recorded.status_code == 200
    body = recorded.json()
    assert body["status"] == "recorded"
    assert body["decision"]["service_card_id"] == override["service_card_id"]
    assert body["decision"]["human_override_review_required"] is True
    selected = body["planning_workspace"]["proposal"]
    assert selected["service_card_id"] == override["service_card_id"]
    assert selected["service_card_id"] != recommended["service_card_id"]
    assert selected["service_selection_confirmed"] is True
    assert selected["human_override_review_required"] is True
    assert selected["planning_digest"] != proposal["planning_digest"]
    assert body["planning_workspace"]["scope_current"] is True

    reloaded = _selected_snapshot(client, work_item_id)
    assert reloaded["planning_workspace"]["proposal"] == selected
    assert reloaded["service_profile_context"]["service_card_id"] == override[
        "service_card_id"
    ]

    repeated_payload = {**override_payload}
    repeated_payload["expected_planning_digest"] = selected["planning_digest"]
    repeated = client.post(_planning_review_path(work_item_id), json=repeated_payload)
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["decision"]["decision_id"] == body["decision"][
        "decision_id"
    ]


def _snapshot_with_service_override(
    client: TestClient,
) -> tuple[str, dict[str, Any]]:
    queue = client.get("/api/content/work-items/queue").json()
    for candidate in queue["candidates"]:
        snapshot = _selected_snapshot(client, candidate["work_item_id"])
        if (
            snapshot.get("response_type") == "workflow_snapshot"
            and snapshot.get("planning_workspace") is not None
            and len(snapshot["service_profile_context"]["service_candidates"]) > 1
        ):
            return candidate["work_item_id"], snapshot
    pytest.fail("Planning override proof requires two allowed service candidates.")


def _selected_snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _planning_review_payload(digest: str) -> dict[str, Any]:
    return {
        "stage": "scope",
        "expected_planning_digest": digest,
        "decision": "approved",
        "reviewed_by": "wilku",
        "checked_items": ["zakres", "dowody", "CTA"],
        "notes": "Sprawdzono aktualną wersję planu.",
    }


def _planning_review_path(work_item_id: str) -> str:
    return f"/api/content/work-items/{work_item_id}/planning-review"
