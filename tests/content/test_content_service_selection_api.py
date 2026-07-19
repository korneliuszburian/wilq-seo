from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from tests.content.dynamic_planning_test_support import (
    PlanningClient,
    configure_planning_harness,
)
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.workflow.api import _gate_candidate_on_service_binding
from wilq.content.workflow.catalog import inventory_work_item_id
from wilq.content.workflow.queue import ContentWorkItemQueueCandidate

BDO_WORK_ITEM_ID = inventory_work_item_id(
    "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
)


@pytest.fixture
def planning_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, PlanningClient]:
    return configure_planning_harness(monkeypatch, tmp_path)


def test_planning_scope_persists_only_allowed_service_override(
    planning_harness: tuple[TestClient, PlanningClient],
) -> None:
    client, _runtime = planning_harness
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


def test_unbound_service_candidate_cannot_look_plan_ready() -> None:
    candidate = ContentWorkItemQueueCandidate.model_construct(
        decision_id="decision_unbound",
        evidence_ids=["ev_page"],
        source_connectors=["google_search_console"],
        blockers=[],
        recommended_mode="refresh",
        preflight_status="plan_allowed",
    )
    context = ContentWorkItemServiceProfileContext.not_evaluated(
        reason="Brakuje karty usługi.",
        safe_next_step="Sprawdź kartę usługi.",
    ).model_copy(update={"binding_status": "unbound"})

    gated = _gate_candidate_on_service_binding(
        candidate,
        service_profile_context=context,
    )

    assert gated.recommended_mode == "block"
    assert gated.preflight_status == "blocked"
    assert gated.blockers[0].code == "missing_service_binding"


def _snapshot_with_service_override(
    client: TestClient,
) -> tuple[str, dict[str, Any]]:
    snapshot = _selected_snapshot(client, BDO_WORK_ITEM_ID)
    assert snapshot.get("response_type") == "workflow_snapshot"
    assert snapshot.get("planning_workspace") is not None
    assert len(snapshot["service_profile_context"]["service_candidates"]) > 1
    return BDO_WORK_ITEM_ID, snapshot


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
