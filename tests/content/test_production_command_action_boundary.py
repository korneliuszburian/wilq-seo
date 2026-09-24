"""Both public production operations require a reviewed ActionObject."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_production_command as production_route
from apps.api.wilq_api.main import app
from wilq.content.workflow.production_command import (
    ContentProductionCommandBlocker,
    ContentProductionCommandResponse,
)


@pytest.mark.parametrize(
    "command_payload",
    [
        {
            "operation": "initial",
            "expected_proposal_id": "proposal_exact",
            "expected_planning_digest": "a" * 64,
            "expected_planning_input_digest": "b" * 64,
            "requested_by": "synthetic-operator",
        },
        {
            "operation": "repair",
            "expected_base_digest": "c" * 64,
            "selected_section_ids": ["section_exact"],
            "requested_by": "synthetic-operator",
        },
    ],
)
def test_public_production_command_blocks_before_private_writer(
    command_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    entered_writer = False

    class FakeProductionCommand:
        def __init__(self, **_kwargs: object) -> None:
            nonlocal entered_writer
            entered_writer = True

        def run(self, work_item_id: str, _request: object) -> ContentProductionCommandResponse:
            blocker = ContentProductionCommandBlocker(
                code="unsafe_writer_reached",
                label="Test",
                reason="Test",
                next_step="Test",
            )
            return ContentProductionCommandResponse(
                status="blocked",
                operation=command_payload["operation"],  # type: ignore[arg-type]
                work_item_id=work_item_id,
                blockers=[blocker],
                safe_next_step=blocker.next_step,
            )

    monkeypatch.setattr(production_route, "ContentProductionCommand", FakeProductionCommand)
    response = TestClient(app).post(
        "/api/content/work-items/wi_exact/production-command", json=command_payload
    )

    assert entered_writer is False
    assert response.status_code == 409
    assert response.json()["blockers"][0]["code"] == "production_action_required"
    assert response.json()["blockers"][0]["owner"] == "WILQ content workflow"
