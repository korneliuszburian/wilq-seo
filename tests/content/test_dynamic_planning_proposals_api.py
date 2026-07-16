from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from apps.api.wilq_api.routers import content_snapshot as content_snapshot_router
from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.knowledge import cards as knowledge_cards
from wilq.content.planning.dynamic_input import build_content_planning_input
from wilq.content.planning.generated_proposal import (
    generate_content_planning_proposal,
    read_content_planning_proposal,
)
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalRequest,
)
from wilq.content.planning.generated_proposal_store import (
    ContentPlanningProposalStore,
    content_planning_proposal_store,
)
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.schemas import CodexRun
from wilq.storage.local_state import local_state_store

BDO_WORK_ITEM_ID = (
    "content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca"
)
OUTSOURCING_WORK_ITEM_ID = (
    "content_work_item_content_decision_https___www_ekologus_pl_"
    "oferta_doradztwo_i_outsourcing_ekologiczny"
)


class _PlanningClient:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    def run_structured_turn(self, request: Any) -> CodexAppServerTurnResult:
        self.calls += 1
        if self.fail:
            return CodexAppServerTurnResult(
                status="failed",
                blockers=(),
            )
        context = json.loads(request.untrusted_context)
        planning_input = context["planning_input"]
        inventory_heading = planning_input["inventory"]["sections"][0]["heading"]
        evidence_id = planning_input["evidence_ids"][0]
        query_rows = planning_input["query_portfolio"]["gsc_query_rows"]
        query_terms = [query_rows[0]["term"]] if query_rows else []
        allowed_claims = [
            entry["id"]
            for entry in planning_input["claim_ledger"]
            if entry["status"] in {"allowed_with_evidence", "allowed_general"}
        ]
        output = {
            "language": "pl-PL",
            "service_card_id": planning_input["confirmed_service_card_id"],
            "target_reader": planning_input["target_reader"],
            "buyer_problem": planning_input["buyer_problem"],
            "buyer_trigger": planning_input["buyer_trigger"],
            "search_intent": planning_input["search_intent"],
            "angle": f"Plan dla {planning_input['service_label']}",
            "value_proposition": "Bezpieczna odpowiedź na pytanie czytelnika.",
            "page_assets": {
                "title": f"Plan: {planning_input['service_label']}",
                "h1": planning_input["inventory"]["title_or_h1"] or inventory_heading,
                "lead": "Najpierw odpowiedz na główny problem czytelnika.",
                "meta_title": f"{planning_input['service_label']} — Ekologus",
                "meta_description": "Sprawdź zakres, dokumenty i bezpieczny następny krok.",
            },
            "sections": [
                {
                    "heading": inventory_heading,
                    "purpose": "Zachowaj użyteczną sekcję i doprecyzuj odpowiedź.",
                    "reader_question": "Co trzeba sprawdzić przed działaniem?",
                    "inventory_disposition": "rewrite",
                    "inventory_heading": inventory_heading,
                    "query_terms": query_terms,
                    "evidence_ids": [evidence_id],
                    "claim_ids": allowed_claims[:1],
                }
            ],
            "faq": [
                {
                    "question": "Od czego zacząć?",
                    "purpose": "Wyjaśnić bezpieczny pierwszy krok.",
                    "query_terms": query_terms,
                    "evidence_ids": [evidence_id],
                    "claim_ids": allowed_claims[:1],
                }
            ],
            "cta_blocks": [
                {
                    "placement": "po sekcjach",
                    "purpose": "Przejście do konsultacji bez gwarancji wyniku.",
                    "copy_direction": "Opisz sytuację firmy i poproś o weryfikację.",
                    "evidence_ids": [evidence_id],
                    "claim_ids": allowed_claims[:1],
                }
            ],
            "internal_links": [],
            "conditional_hypotheses": [],
            "measurement_plan": {
                "metrics_to_watch": planning_input["measurement_metrics"],
                "baseline_evidence_ids": planning_input["measurement_baseline_evidence_ids"],
                "observation_rule": planning_input["measurement_observation_rule"],
                "success_claim_rule": planning_input["measurement_success_claim_rule"],
            },
            "publish_ready": False,
        }
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(output, ensure_ascii=False),
            thread_id=f"thread_{self.calls}",
            turn_id=f"turn_{self.calls}",
            event_methods=("turn/completed",),
            item_types=("agentMessage",),
        )


class _FailingPlanningStore(ContentPlanningProposalStore):
    def save_generated(
        self,
        proposal: ContentPlanningProposal,
        completed_run: CodexRun,
    ) -> tuple[Literal["created", "idempotent"], ContentPlanningProposal]:
        raise RuntimeError("synthetic persistence failure")


@pytest.fixture
def planning_harness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[TestClient, _PlanningClient]:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    original_cards = knowledge_cards.ekologus_content_knowledge_cards()
    approved_service_ids = {
        "ekologus_service_bdo_reporting",
        "ekologus_service_environmental_consulting_outsourcing",
    }
    approved_cards = tuple(
        card.model_copy(update={"lifecycle_status": "approved_current"})
        if card.id in approved_service_ids
        else card
        for card in original_cards
    )
    monkeypatch.setattr(
        knowledge_cards,
        "ekologus_content_knowledge_cards",
        lambda: approved_cards,
    )
    original_diagnostics = content_snapshot_router.diagnostics_with_exact_gsc_demand

    def fresh_diagnostics(work_item_id: str) -> Any:
        diagnostics = original_diagnostics(work_item_id)
        decisions = [
            decision.model_copy(
                update={
                    "wordpress_section_headings": (
                        decision.wordpress_section_headings
                        or [f"Istniejąca sekcja: {decision.primary_query or decision.title}"]
                    ),
                    "wordpress_section_count": (decision.wordpress_section_count or 1),
                    "wordpress_section_inventory_status": "available",
                    "wordpress_content_summary": (
                        decision.wordpress_content_summary
                        or "Syntetyczne podsumowanie publicznej treści."
                    ),
                    "wordpress_content_word_count": (decision.wordpress_content_word_count or 500),
                    "wordpress_content_inventory_status": "available",
                }
            )
            if f"content_work_item_{decision.id}" == work_item_id
            else decision
            for decision in diagnostics.decision_queue
        ]
        return diagnostics.model_copy(
            update={
                "decision_queue": decisions,
                "freshness_assessment": diagnostics.freshness_assessment.model_copy(
                    update={
                        "state": "fresh",
                        "requires_refresh": False,
                        "missing_connector_ids": [],
                        "blocked_connector_ids": [],
                        "stale_connector_ids": [],
                        "connector_labels_requiring_refresh": [],
                        "summary": "Syntetyczny świeży proof planowania.",
                        "next_step": "Można zbudować wejście planu do testu.",
                    }
                ),
            }
        )

    monkeypatch.setattr(
        content_snapshot_router,
        "diagnostics_with_exact_gsc_demand",
        fresh_diagnostics,
    )
    runtime = _PlanningClient()
    monkeypatch.setattr(
        planning_router,
        "content_codex_app_server_client",
        lambda: runtime,
    )
    return TestClient(app), runtime


def test_dynamic_planning_proposals_are_two_case_and_idempotent(
    planning_harness: tuple[TestClient, _PlanningClient],
) -> None:
    client, runtime = planning_harness
    generated = {
        work_item_id: _approve_and_generate(
            client,
            runtime,
            work_item_id,
            expected_calls=index,
        )
        for index, work_item_id in enumerate((BDO_WORK_ITEM_ID, OUTSOURCING_WORK_ITEM_ID))
    }
    assert runtime.calls == 2
    assert generated[BDO_WORK_ITEM_ID]["service_card_id"] == ("ekologus_service_bdo_reporting")
    assert generated[OUTSOURCING_WORK_ITEM_ID]["service_card_id"] == (
        "ekologus_service_environmental_consulting_outsourcing"
    )
    assert generated[BDO_WORK_ITEM_ID]["angle"] != generated[OUTSOURCING_WORK_ITEM_ID]["angle"]


def test_dynamic_planning_input_change_is_stale_and_runtime_fails_closed(
    planning_harness: tuple[TestClient, _PlanningClient],
) -> None:
    client, runtime = planning_harness
    generated = _approve_and_generate(
        client,
        runtime,
        BDO_WORK_ITEM_ID,
        expected_calls=0,
    )
    latest_snapshot = snapshot_for_work_item_or_404(BDO_WORK_ITEM_ID)
    changed_item = latest_snapshot.preflight.item.model_copy(
        update={"wordpress_content_summary": "Zmienione exact inventory."}
    )
    changed_snapshot = latest_snapshot.model_copy(
        update={"preflight": latest_snapshot.preflight.model_copy(update={"item": changed_item})}
    )
    changed_input = build_content_planning_input(
        changed_snapshot,
        service_card_id="ekologus_service_bdo_reporting",
    ).planning_input
    assert changed_input is not None
    stale_read = read_content_planning_proposal(
        snapshot=changed_snapshot,
        store=content_planning_proposal_store(),
    )
    assert stale_read.status == "stale"

    runtime.fail = True
    failed = generate_content_planning_proposal(
        snapshot=changed_snapshot,
        request=ContentPlanningProposalRequest(
            service_card_id="ekologus_service_bdo_reporting",
            expected_planning_input_digest=changed_input.planning_input_digest,
            requested_by="wilku",
        ),
        client=runtime,
        store=content_planning_proposal_store(),
        run_store=local_state_store(),
    )
    assert failed.status == "failed"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) == (
        generated_proposal_from(generated)
    )
    runtime.fail = False
    persistence_failed = generate_content_planning_proposal(
        snapshot=changed_snapshot,
        request=ContentPlanningProposalRequest(
            service_card_id="ekologus_service_bdo_reporting",
            expected_planning_input_digest=changed_input.planning_input_digest,
            requested_by="wilku",
        ),
        client=runtime,
        store=_FailingPlanningStore(content_planning_proposal_store().path),
        run_store=local_state_store(),
    )
    assert persistence_failed.status == "failed"
    assert persistence_failed.blockers[0].code == "persistence_failed"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) == (
        generated_proposal_from(generated)
    )


def _approve_and_generate(
    client: TestClient,
    runtime: _PlanningClient,
    work_item_id: str,
    *,
    expected_calls: int,
) -> dict[str, Any]:
    snapshot = _snapshot(client, work_item_id)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    planning_digest = snapshot["planning_workspace"]["proposal"]["planning_digest"]
    approved = client.post(
        f"/api/content/work-items/{work_item_id}/planning-review",
        json={
            "stage": "scope",
            "service_card_id": service_card_id,
            "expected_planning_digest": planning_digest,
            "decision": "approved",
            "reviewed_by": "wilku",
            "checked_items": ["strona", "usługa", "intencja", "CTA"],
            "notes": "Syntetyczny proof zatwierdzonej karty.",
        },
    )
    assert approved.status_code == 200
    before = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert before.status_code == 200
    assert before.json()["status"] == "not_generated", before.json()["blockers"]
    assert runtime.calls == expected_calls
    if expected_calls == 0:
        assert not _planning_table_exists()
    input_digest = before.json()["planning_input_digest"]
    unknown = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request("ekologus_service_unknown", input_digest),
    )
    assert unknown.status_code == 422
    assert unknown.json()["blockers"][0]["code"] == "unknown_service_card"
    stale = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request(service_card_id, "0" * 64),
    )
    assert stale.status_code == 409
    assert stale.json()["status"] == "stale"
    assert stale.json()["planning_input_digest"] == input_digest
    created = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request(service_card_id, input_digest),
    )
    assert created.status_code == 200
    assert created.json()["status"] == "created"
    repeated = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request(service_card_id, input_digest),
    )
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["proposal"]["proposal_id"] == created.json()["proposal"]["proposal_id"]
    ready = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert ready.json()["status"] == "ready"
    assert ready.json()["proposal"] == created.json()["proposal"]
    return cast(dict[str, Any], created.json()["proposal"])


def _snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _generation_request(service_card_id: str, digest: str) -> dict[str, str]:
    return {
        "service_card_id": service_card_id,
        "expected_planning_input_digest": digest,
        "operator_hint": "Odpowiedz najpierw na najważniejsze pytanie czytelnika.",
        "requested_by": "wilku",
    }


def generated_proposal_from(payload: dict[str, Any]) -> ContentPlanningProposal:
    return ContentPlanningProposal.model_validate(payload)


def _planning_table_exists() -> bool:
    path = content_planning_proposal_store().path
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("content_planning_proposals",),
        ).fetchone()
    return row is not None
