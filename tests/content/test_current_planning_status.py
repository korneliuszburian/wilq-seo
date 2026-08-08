from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from wilq.content.planning.dynamic_input import ContentPlanningInputSummary
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalBlocker,
    ContentPlanningProposalRequest,
    ContentPlanningProposalResponse,
)
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.input_sources import ContentPlanningSourceAssessment
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.schemas import CodexRun


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


def _proposal(*, digest: str, service_card_id: str) -> ContentPlanningProposal:
    return ContentPlanningProposal(
        work_item_id="work-item",
        planning_digest="c" * 64,
        proposal_id=f"proposal-{digest[0]}",
        planning_input_digest=digest,
        service_card_id=service_card_id,
        final_canonical_url="https://www.ekologus.pl/bdo/",
        target_reader="Firma",
        buyer_problem="Brak porządku.",
        buyer_trigger="Zmiana wymagań.",
        search_intent="informacyjny",
        cta_direction="Skonsultuj sytuację.",
        sections=[ContentPlanningSection(heading="Zakres", purpose="Wyjaśnia zakres.")],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak dokładnych danych.",
        ),
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


@pytest.mark.parametrize(
    ("current", "expected_status", "expected_digest"),
    [
        (
            ContentPlanningProposalResponse(
                status="stale",
                work_item_id="work-item",
                service_card_id="service-a",
                planning_input_digest="b" * 64,
                input_summary=_planning_summary(),
                blockers=[
                    ContentPlanningProposalBlocker(
                        code="stale_input",
                        label="Wejście planu jest nieaktualne",
                        reason="Źródła zmieniły exact wejście.",
                        next_step="Odśwież wejście.",
                    )
                ],
                safe_next_step="Odśwież wejście.",
            ),
            "stale",
            "b" * 64,
        ),
        (
            ContentPlanningProposalResponse(
                status="blocked",
                work_item_id="work-item",
                service_card_id="service-a",
                planning_input_digest="a" * 64,
                input_summary=_planning_summary(),
                proposal=_proposal(digest="a" * 64, service_card_id="service-a"),
                blockers=[
                    ContentPlanningProposalBlocker(
                        code="quality_gate_failed",
                        label="Plan wymaga poprawy",
                        reason="Plan nie przeszedł bramki jakości.",
                        next_step="Uruchom plan ponownie.",
                    )
                ],
                safe_next_step="Uruchom plan ponownie.",
            ),
            "blocked",
            "a" * 64,
        ),
    ],
)
def test_planning_post_preserves_current_stale_or_quality_blocked_state(
    monkeypatch: pytest.MonkeyPatch,
    current: ContentPlanningProposalResponse,
    expected_status: str,
    expected_digest: str,
) -> None:
    existing = _proposal(digest="a" * 64, service_card_id="service-a")
    snapshot = SimpleNamespace(work_item_id="work-item")
    app = FastAPI()
    monkeypatch.setattr(
        planning_router,
        "content_planning_proposal_store",
        lambda: SimpleNamespace(
            for_input=lambda *_args: existing,
        ),
    )
    monkeypatch.setattr(
        planning_router,
        "ekologus_content_knowledge_cards",
        lambda: (SimpleNamespace(id="service-a", card_type="service"),),
    )
    monkeypatch.setattr(
        planning_router,
        "read_content_planning_proposal",
        lambda **_kwargs: current,
    )
    planning_router.register_content_planning_proposal_routes(
        app, snapshot_loader=lambda _id: snapshot
    )

    response = TestClient(app).post(
        "/api/content/work-items/work-item/planning-proposals",
        json={
            "service_card_id": "service-a",
            "expected_planning_input_digest": "a" * 64,
            "requested_by": "Wilku",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == expected_status
    assert response.json()["planning_input_digest"] == expected_digest
    if expected_status == "stale":
        assert response.json()["proposal"] is None
    else:
        assert response.json()["blockers"][0]["code"] == "quality_gate_failed"


def test_planning_post_regenerates_an_exact_stale_inventory_mapping_without_client_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _proposal(digest="a" * 64, service_card_id="service-a")
    current = ContentPlanningProposalResponse(
        status="stale",
        work_item_id="work-item",
        service_card_id="service-a",
        planning_input_digest="a" * 64,
        input_summary=_planning_summary(),
        proposal=existing,
        blockers=[
            ContentPlanningProposalBlocker(
                code="stale_input",
                label="Mapa istniejącej strony wymaga odświeżenia",
                reason="Mapa inventory przestała być bieżąca.",
                next_step="Wygeneruj nową mapę.",
            )
        ],
        safe_next_step="Wygeneruj nową mapę.",
    )
    snapshot = SimpleNamespace(work_item_id="work-item")
    app = FastAPI()
    preparation_flags: list[bool] = []
    generating = ContentPlanningProposalResponse(
        status="generating",
        work_item_id="work-item",
        service_card_id="service-a",
        planning_input_digest="a" * 64,
        input_summary=_planning_summary(),
        safe_next_step="Plan jest przygotowywany.",
    )
    monkeypatch.setattr(
        planning_router,
        "content_planning_proposal_store",
        lambda: SimpleNamespace(for_input=lambda *_args: existing),
    )
    monkeypatch.setattr(
        planning_router,
        "ekologus_content_knowledge_cards",
        lambda: (SimpleNamespace(id="service-a", card_type="service"),),
    )
    monkeypatch.setattr(
        planning_router,
        "read_content_planning_proposal",
        lambda **_kwargs: current,
    )

    def prepare(**kwargs):
        preparation_flags.append(kwargs["request"].regenerate_stale_mapping)
        return None, generating

    monkeypatch.setattr(planning_router, "_prepare_generation", prepare)
    planning_router.register_content_planning_proposal_routes(
        app, snapshot_loader=lambda _id: snapshot
    )

    response = TestClient(app).post(
        "/api/content/work-items/work-item/planning-proposals",
        json={
            "service_card_id": "service-a",
            "expected_planning_input_digest": "a" * 64,
            "requested_by": "Wilku",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "generating"
    assert preparation_flags == [True]


def test_planning_post_regenerates_exact_plan_after_review_with_visible_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _proposal(digest="a" * 64, service_card_id="service-a")
    current = ContentPlanningProposalResponse(
        status="ready",
        work_item_id="work-item",
        service_card_id="service-a",
        planning_input_digest="a" * 64,
        input_summary=_planning_summary(),
        proposal=existing,
        safe_next_step="Przygotuj tekst z tego planu.",
    )
    snapshot = SimpleNamespace(work_item_id="work-item")
    app = FastAPI()
    replacement_flags: list[bool] = []
    generating = ContentPlanningProposalResponse(
        status="generating",
        work_item_id="work-item",
        service_card_id="service-a",
        planning_input_digest="a" * 64,
        input_summary=_planning_summary(),
        safe_next_step="Plan jest przygotowywany.",
    )
    monkeypatch.setattr(
        planning_router,
        "content_planning_proposal_store",
        lambda: SimpleNamespace(for_input=lambda *_args: existing),
    )
    monkeypatch.setattr(
        planning_router,
        "ekologus_content_knowledge_cards",
        lambda: (SimpleNamespace(id="service-a", card_type="service"),),
    )
    monkeypatch.setattr(
        planning_router,
        "read_content_planning_proposal",
        lambda **_kwargs: current,
    )

    def prepare(**kwargs):
        replacement_flags.append(kwargs["request"].regenerate_after_review)
        return None, generating

    monkeypatch.setattr(planning_router, "_prepare_generation", prepare)
    planning_router.register_content_planning_proposal_routes(
        app, snapshot_loader=lambda _id: snapshot
    )

    response = TestClient(app).post(
        "/api/content/work-items/work-item/planning-proposals",
        json={
            "service_card_id": "service-a",
            "expected_planning_input_digest": "a" * 64,
            "operator_hint": "Usuń niepotwierdzoną lokalną frazę z planu.",
            "requested_by": "Wilku",
            "regenerate_after_review": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "generating"
    assert replacement_flags == [True]


def test_planning_review_regeneration_requires_visible_instruction() -> None:
    with pytest.raises(ValueError, match="visible repair instruction"):
        ContentPlanningProposalRequest(
            service_card_id="service-a",
            expected_planning_input_digest="a" * 64,
            requested_by="Wilku",
            regenerate_after_review=True,
        )


def test_planning_store_replaces_current_exact_input_without_mutating_history(
    tmp_path: Path,
) -> None:
    store = ContentPlanningProposalStore(tmp_path / "state.sqlite")
    completed_at = datetime.now(UTC)
    proposal_a = _proposal(digest="a" * 64, service_card_id="service-a").model_copy(
        update={
            "proposal_id": "proposal-a",
            "codex_run_id": "run-a",
            "generation_status": "codex_generated",
            "created_at": completed_at,
        }
    )
    run_a = CodexRun(
        id="run-a",
        status="completed",
        started_at=completed_at,
        completed_at=completed_at,
    )
    proposal_b = proposal_a.model_copy(
        update={"proposal_id": "proposal-b", "codex_run_id": "run-b"}
    )
    run_b = run_a.model_copy(update={"id": "run-b"})

    assert store.save_generated(proposal_a, run_a)[0] == "created"
    outcome, stored_b = store.save_generated(
        proposal_b,
        run_b,
        replace_existing_exact_input=True,
    )

    assert outcome == "replaced"
    assert stored_b.proposal_id == "proposal-b"
    assert store.for_input("work-item", "service-a", "a" * 64).proposal_id == "proposal-b"
    assert store.latest("work-item", "service-a").proposal_id == "proposal-b"
    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT proposal_id FROM content_planning_proposals"
        ).fetchall() == [("proposal-a",)]
        assert connection.execute(
            "SELECT proposal_id, supersedes_proposal_id FROM content_planning_proposal_repairs"
        ).fetchall() == [("proposal-b", "proposal-a")]
