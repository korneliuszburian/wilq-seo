from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from wilq.content.planning.dynamic_input import ContentPlanningInputSummary
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.input_sources import ContentPlanningSourceAssessment


def _planning_summary() -> ContentPlanningInputSummary:
    return ContentPlanningInputSummary(
        final_canonical_url="https://www.ekologus.pl/bdo/",
        service_label="BDO",
        inventory_status="available",
        content_inventory_status="available",
        acf_section_inventory_status="missing",
        source_assessments=[
            ContentPlanningSourceAssessment(
                source=source,
                status="not_applicable",
                reason="Testowy stan źródła.",
            )
            for source in (
                "wordpress",
                "service_profile",
                "gsc",
                "ga4",
                "google_ads",
                "ahrefs",
                "keyword_planner",
                "merchant",
                "localo",
                "social",
            )
        ],
        source_fact_count=0,
        evidence_id_count=0,
        knowledge_card_count=0,
    )


def test_planning_status_ignores_a_historical_failed_job_for_another_exact_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = ContentPlanningProposalStore(tmp_path / "state.sqlite")
    historical = ContentPlanningProposalResponse(
        status="failed",
        work_item_id="work-item",
        service_card_id="service-a",
        planning_input_digest="a" * 64,
        input_summary=_planning_summary(),
        blockers=[
            ContentPlanningProposalBlocker(
                code="runtime_failed",
                label="Historyczny błąd",
                reason="Stary worker nie ukończył planu.",
                next_step="Odśwież wejście.",
            )
        ],
        safe_next_step="Odśwież wejście.",
    )
    store.save_terminal_response(historical)
    current = ContentPlanningProposalResponse(
        status="not_generated",
        work_item_id="work-item",
        service_card_id="service-b",
        planning_input_digest="b" * 64,
        input_summary=_planning_summary(),
        safe_next_step="Przygotuj plan dla bieżącego wejścia.",
    )
    app = FastAPI()
    snapshot = SimpleNamespace(work_item_id="work-item")
    monkeypatch.setattr(planning_router, "content_planning_proposal_store", lambda: store)
    monkeypatch.setattr(
        planning_router,
        "content_workflow_store",
        lambda: SimpleNamespace(load_planning_decisions=lambda _id: []),
    )
    monkeypatch.setattr(
        planning_router,
        "read_content_planning_proposal",
        lambda **kwargs: current if kwargs["snapshot"] is snapshot else None,
    )
    planning_router.register_content_planning_proposal_routes(
        app, snapshot_loader=lambda _id: snapshot
    )

    response = TestClient(app).get("/api/content/work-items/work-item/planning-proposals")

    assert response.status_code == 200
    assert response.json()["status"] == "not_generated"
    assert response.json()["service_card_id"] == "service-b"
    assert response.json()["planning_input_digest"] == "b" * 64
