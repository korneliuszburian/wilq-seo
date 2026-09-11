from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

import pytest
from pydantic import ValidationError

from apps.api.wilq_api.routers import content_snapshot
from apps.api.wilq_api.routers.content_workflow_http import (
    project_content_work_item_browser_snapshot,
)
from wilq.content.workflow.contracts.contracts import (
    ContentWorkItemBrowserWorkflowSnapshotResponse,
)
from wilq.schemas import ContentDecisionItem

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
        snapshot = content_snapshot.snapshot_for_default_work_item_or_404()
    finally:
        monkeypatch.undo()

    payload: dict[str, Any] = project_content_work_item_browser_snapshot(snapshot).model_dump(
        mode="json"
    )
    assert payload["response_type"] == "workflow_snapshot"
    ContentWorkItemBrowserWorkflowSnapshotResponse.model_validate(payload)
    return payload


def test_internal_workflow_snapshot_projection_exposes_readiness_without_execution_contract(
    valid_workflow_snapshot_payload: dict[str, Any],
) -> None:
    _assert_browser_safe_generation_readiness(valid_workflow_snapshot_payload)


def test_public_readiness_cannot_be_ready_before_scope_or_generated_plan(
    valid_workflow_snapshot_payload: dict[str, Any],
) -> None:
    current_step_id = valid_workflow_snapshot_payload["current_step_id"]
    if current_step_id != "scope":
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


def test_selected_internal_workflow_snapshot_uses_same_safe_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    default_snapshot = content_snapshot.snapshot_for_default_work_item_or_404()
    work_item_id = default_snapshot.preflight.item.id
    payload: dict[str, Any] = project_content_work_item_browser_snapshot(
        content_snapshot.snapshot_for_work_item_or_404(work_item_id)
    ).model_dump(mode="json")
    ContentWorkItemBrowserWorkflowSnapshotResponse.model_validate(payload)
    _assert_browser_safe_generation_readiness(payload)


def test_selected_inventory_merge_preserves_acf_field_names() -> None:
    existing = ContentDecisionItem.model_construct(
        id="reach",
        decision_type="refresh_or_merge",
        title="REACH",
        rationale="test",
        next_step="test",
        wordpress_acf_field_names=[],
    )
    selected = ContentDecisionItem.model_construct(
        id="reach",
        decision_type="refresh_or_merge",
        title="REACH",
        rationale="test",
        next_step="test",
        wordpress_acf_field_names=["hero_component", "faq_items"],
    )

    merged = content_snapshot._merge_selected_inventory_fields(existing, selected)

    assert merged.wordpress_acf_field_names == ["hero_component", "faq_items"]


def test_snapshot_recovers_ready_inventory_work_item_when_diagnostics_alias_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_inventory_reach"
    selected = type(
        "SelectedDecision",
        (),
        {
            "id": "reach",
            "status": "ready",
            "source_connectors": ["wordpress_ekologus"],
            "final_canonical_url": "https://www.ekologus.pl/reach/",
            "evidence_ids": ["ev_reach_inventory"],
        },
    )()
    sentinel = type(
        "Snapshot",
        (),
        {
            "revision_workspace": type(
                "Workspace", (), {"latest_revision": None, "context_current": True}
            )(),
        },
    )()

    class Store:
        def load_draft_revision_state(self, _work_item_id):
            return SimpleNamespace(
                latest_revision=SimpleNamespace(planning_digest="b" * 64),
                latest_review=SimpleNamespace(),
            )

        def load_planning_decisions(self, _work_item_id):
            return []

        def latest_human_review(self, _work_item_id):
            return SimpleNamespace(id="human_review")

        def latest_audit_for_review(self, _review_id):
            return None

    class ProposalStore:
        def latest_for_planning_digest(self, _work_item_id, _digest):
            return SimpleNamespace()

    builder_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setattr(content_snapshot, "content_workflow_store", lambda: Store())
    monkeypatch.setattr(
        content_snapshot,
        "content_planning_proposal_store",
        lambda: ProposalStore(),
    )
    monkeypatch.setattr(
        content_snapshot,
        "inventory_decision_for_work_item",
        lambda *_args, **_kwargs: selected,
    )
    monkeypatch.setattr(
        content_snapshot,
        "build_content_freshness_assessment_fast",
        lambda **_kwargs: type("Freshness", (), {})(),
    )
    monkeypatch.setattr(
        content_snapshot,
        "diagnostics_with_exact_gsc_demand",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        content_snapshot,
        "build_content_work_item_diagnostics_snapshot_response_for_work_item",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        content_snapshot,
        "build_content_work_item_snapshot_response_from_selected_decision",
        lambda *args, **kwargs: builder_calls.append((args, kwargs)) or sentinel,
    )
    monkeypatch.setattr(content_snapshot, "_with_recorded_human_review", lambda value: value)

    result = content_snapshot.snapshot_for_work_item_or_404(
        work_item_id,
    )

    assert result is sentinel
    assert len(builder_calls) == 3
    assert builder_calls[-1][0][0] is selected
    assert builder_calls[-1][1]["freshness_assessment"] is not None


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
