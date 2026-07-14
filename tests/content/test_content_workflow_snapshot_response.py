from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.wilq_api.main import app
from wilq.content.workflow.contracts import ContentWorkItemWorkflowSnapshotResponse

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
    ContentWorkItemWorkflowSnapshotResponse.model_validate(payload)
    return payload


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
        ContentWorkItemWorkflowSnapshotResponse.model_validate(invalid_payload)
