from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app


def _get_mutation_readiness(action_id: str) -> dict[str, Any]:
    response = TestClient(app).get(
        f"/api/actions/{action_id}/mutation-readiness",
    )
    assert response.status_code == 200
    data = cast(dict[str, Any], response.json())
    assert data["response_type"] == "action_mutation_readiness"
    return data


def test_action_mutation_readiness_blocks_prepare_only_action(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "actions.sqlite3"))

    data = _get_mutation_readiness("act_prepare_wordpress_draft_handoff")

    assert data["ready_to_request_apply"] is False
    assert data["vendor_write_possible"] is False
    assert data["would_attempt_vendor_write"] is False
    assert data["mutation_adapter"] is None
    assert data["mode"] == "prepare"
    assert data["source_connectors"] == ["wordpress_ekologus"]
    assert data["evidence_ids"]
    blocker_codes = [blocker["code"] for blocker in data["blockers"]]
    assert "missing_apply_mode" in blocker_codes
    assert "missing_mutation_adapter" in blocker_codes
    assert any(
        requirement["code"] == "mutation_adapter" and requirement["satisfied"] is False
        for requirement in data["requirements"]
    )
    assert "validate" in data["operator_next_step"]


def test_action_mutation_readiness_returns_404_for_unknown_action() -> None:
    response = TestClient(app).get(
        "/api/actions/no-such-action/mutation-readiness",
    )

    assert response.status_code == 404
