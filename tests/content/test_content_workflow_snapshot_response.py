from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.wilq_api.main import app
from wilq.content.workflow.contracts import (
    ContentWorkItemBrowserWorkflowSnapshotResponse,
)

InvalidJourneyCase = Literal[
    "reordered",
    "duplicate",
    "multiple_current",
    "current_mismatch",
]


@pytest.fixture(scope="module")
def valid_workflow_snapshot_payload(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path_factory.mktemp("workflow-snapshot") / "wilq.sqlite3"),
    )
    try:
        response = TestClient(app).get("/api/content/work-items/snapshot")
    finally:
        monkeypatch.undo()

    assert response.status_code == 200
    payload: dict[str, Any] = response.json()
    assert payload["response_type"] == "workflow_snapshot"
    ContentWorkItemBrowserWorkflowSnapshotResponse.model_validate(payload)
    return payload


def test_public_workflow_snapshot_exposes_readiness_without_execution_contract(
    valid_workflow_snapshot_payload: dict[str, Any],
) -> None:
    _assert_browser_safe_generation_readiness(valid_workflow_snapshot_payload)


def test_public_readiness_cannot_be_ready_before_scope_or_section_map(
    valid_workflow_snapshot_payload: dict[str, Any],
) -> None:
    current_step_id = valid_workflow_snapshot_payload["current_step_id"]
    if current_step_id not in {"scope", "section_map"}:
        pytest.skip("fixture is already beyond planning gates")

    readiness = valid_workflow_snapshot_payload["structured_generation_readiness"]
    current_step = next(
        step
        for step in valid_workflow_snapshot_payload["operator_steps"]
        if step["phase"] == "current"
    )
    assert readiness["status"] == "blocked"
    assert readiness["blockers"]
    if current_step["blocker"] is not None:
        assert readiness["blockers"][0]["code"] == current_step["blocker"]["code"]


def test_selected_public_workflow_snapshot_uses_same_safe_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    default_response = client.get("/api/content/work-items/snapshot")
    assert default_response.status_code == 200
    work_item_id = default_response.json()["preflight"]["item"]["id"]

    selected_response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")

    assert selected_response.status_code == 200
    payload: dict[str, Any] = selected_response.json()
    ContentWorkItemBrowserWorkflowSnapshotResponse.model_validate(payload)
    _assert_browser_safe_generation_readiness(payload)


@pytest.mark.parametrize(
    ("case", "expected_error"),
    [
        ("reordered", "canonical order"),
        ("duplicate", "must be unique"),
        ("multiple_current", "exactly one current step"),
        ("current_mismatch", "must match the current step"),
    ],
)
def test_workflow_snapshot_response_rejects_invalid_operator_journey(
    case: InvalidJourneyCase,
    expected_error: str,
    valid_workflow_snapshot_payload: dict[str, Any],
) -> None:
    invalid_payload = deepcopy(valid_workflow_snapshot_payload)
    steps: list[dict[str, Any]] = invalid_payload["operator_steps"]
    if case == "reordered":
        steps[0], steps[1] = steps[1], steps[0]
    elif case == "duplicate":
        steps[1]["id"] = steps[0]["id"]
    elif case == "multiple_current":
        next(step for step in steps if step["phase"] != "current")["phase"] = "current"
    else:
        invalid_payload["current_step_id"] = next(
            step["id"] for step in steps if step["id"] != invalid_payload["current_step_id"]
        )

    with pytest.raises(ValidationError, match=expected_error):
        ContentWorkItemBrowserWorkflowSnapshotResponse.model_validate(invalid_payload)


def _assert_browser_safe_generation_readiness(payload: dict[str, Any]) -> None:
    forbidden_keys = {
        "structured_generation",
        "model_input",
        "system_instruction",
        "user_instruction",
        "output_schema",
    }
    assert forbidden_keys.isdisjoint(_nested_keys(payload))

    readiness = payload["structured_generation_readiness"]
    assert readiness["publish_ready"] is False
    if readiness["status"] == "ready":
        assert readiness["editable_section_headings"]
        assert readiness["blockers"] == []
    else:
        assert readiness["editable_section_headings"] == []
        assert readiness["blockers"]


def _nested_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        for item in value.values():
            keys.update(_nested_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_nested_keys(item))
    return keys
