from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_snapshot import (
    snapshot_for_work_item_or_blocked_or_404,
)


def test_blocked_queue_item_returns_typed_blocked_snapshot_without_fake_workflow(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    queue = client.get("/api/content/work-items/queue").json()
    blocked = next(
        candidate for candidate in queue["candidates"] if candidate["recommended_mode"] == "block"
    )

    payload = _get_selected_snapshot(client, blocked["work_item_id"])
    assert payload["response_type"] == "blocked_snapshot"
    assert payload["work_item_id"] == blocked["work_item_id"]
    assert payload["recommended_mode"] == "block"
    assert payload["freshness_assessment"]["next_step"]
    assert payload["blockers"]
    assert payload["candidate"]["work_item_id"] == blocked["work_item_id"]
    assert "preflight" not in payload
    assert "sales_brief" not in payload
    assert payload["service_profile_context"]["binding_status"] == "not_evaluated"
    assert payload["service_profile_context"]["decision_status"] == "not_evaluated"
    assert payload["service_profile_context"]["service_card_id"] is None
    assert payload["service_profile_context"]["safe_next_step"] == blocked["safe_next_step"]


def _get_selected_snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    del client
    return cast(
        dict[str, Any],
        snapshot_for_work_item_or_blocked_or_404(work_item_id).model_dump(mode="json"),
    )
