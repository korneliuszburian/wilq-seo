from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_codex_proposal as section_proposal_router
from apps.api.wilq_api.routers import content_initial_draft as initial_draft_router
from apps.api.wilq_api.routers import content_planning_proposals as planning_router
from apps.api.wilq_api.routers import content_semantic_review as semantic_review_router
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
        self.planning_placement = "after_content"
        self.semantic_external_call_attempted = False

    def run_structured_turn(self, request: Any) -> CodexAppServerTurnResult:
        self.calls += 1
        if self.fail:
            return CodexAppServerTurnResult(
                status="failed",
                blockers=(),
            )
        application = json.loads(request.application_context)
        if application["operation"] == "generate_initial_full_content_draft":
            return self._initial_draft_result(request)
        if application["operation"] == "review_full_content_revision_semantics":
            return self._semantic_review_result(request)
        if application["operation"] == "propose_section_revision":
            return self._section_revision_result(request)
        context = json.loads(request.untrusted_context)
        planning_input = context["planning_input"]
        _assert_planning_input_contract(planning_input)
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
                    "placement": self.planning_placement,
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

    def _initial_draft_result(self, request: Any) -> CodexAppServerTurnResult:
        context = json.loads(request.untrusted_context)
        proposal = context["approved_planning_proposal"]
        planning_input = context["planning_input"]
        assert len(planning_input["source_assessments"]) == 10
        assert planning_input["inventory"]["sections"]
        assert "query_portfolio" in planning_input
        assert "measurement_metrics" in planning_input
        assert "generation_constraints" in context
        schema = request.output_schema
        section_schema = schema["$defs"]["ContentInitialDraftSectionOutput"]
        assert schema["properties"]["sections"]["minItems"] == len(proposal["sections"])
        assert section_schema["properties"]["section_id"]["enum"] == [
            item["section_id"] for item in proposal["sections"]
        ]
        service_label = proposal["service_label"]
        output = {
            "language": "pl-PL",
            "page_assets": {
                "wordpress_title": f"Pełny tekst: {service_label}",
                "meta_title": f"{service_label} — Ekologus",
                "meta_description": "Sprawdź sytuację firmy i możliwy następny krok.",
                "h1": f"{service_label} dla firm",
                "lead": f"Wyjaśniamy, kiedy {service_label} może pomóc w uporządkowaniu działań.",
            },
            "sections": [
                {
                    "section_id": section["section_id"],
                    "heading": section["heading"],
                    "body_markdown": (
                        f"{section['reader_question']} Odpowiedź wynika z dokładnego planu "
                        f"dla usługi {service_label}."
                    ),
                }
                for section in proposal["sections"]
            ],
            "faq": [
                {
                    "question": item["question"],
                    "answer_markdown": (
                        f"Najpierw opisz sytuację firmy w kontekście usługi {service_label}."
                    ),
                }
                for item in proposal["faq"]
            ],
            "cta_blocks": [
                {"body_markdown": f"Opisz potrzeby firmy dotyczące: {service_label}."}
                for _ in proposal["cta_blocks"]
            ],
            "internal_links": [
                {
                    "target_url": item["target_url"],
                    "anchor_text": item["anchor_direction"],
                }
                for item in proposal["internal_links"]
            ],
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

    def _semantic_review_result(self, request: Any) -> CodexAppServerTurnResult:
        context = json.loads(request.untrusted_context)
        revision = context["revision"]
        proposal = context["approved_planning_proposal"]
        planning_input = context["planning_input"]
        assert revision["content_digest"] == json.loads(request.application_context)[
            "revision_digest"
        ]
        assert proposal["planning_input_digest"] == planning_input["planning_input_digest"]
        target = revision["sections"][0]["section_id"]
        evidence_id = revision["sections"][0]["evidence_ids"][0]
        dimensions = [
            "answer_directness",
            "completeness",
            "logical_flow",
            "specificity",
            "repetition",
            "search_intent_fit",
            "buyer_fit",
            "credibility",
            "conversion_clarity",
        ]
        output = {
            "language": "pl-PL",
            "dimensions": [
                {
                    "dimension": dimension,
                    "status": "needs_changes" if dimension == "answer_directness" else "strong",
                    "reason": (
                        "Pierwsza odpowiedź powinna szybciej przejść do decyzji czytelnika."
                        if dimension == "answer_directness"
                        else "Wymiar nie ma konkretnego problemu w tej syntetycznej wersji."
                    ),
                    "affected_targets": [target],
                }
                for dimension in dimensions
            ],
            "findings": [
                {
                    "dimension": "answer_directness",
                    "severity": "medium",
                    "label": "Odpowiedź zaczyna się zbyt ogólnie",
                    "reason": "Czytelnik zbyt późno widzi bezpośredni następny krok.",
                    "instruction": "Przenieś konkretną odpowiedź na początek wybranej sekcji.",
                    "affected_targets": [target],
                    "evidence_ids": [evidence_id],
                }
            ],
            "publish_ready": False,
            "human_review_required": True,
        }
        schema = request.output_schema
        finding_schema = schema["$defs"]["ContentSemanticFindingOutput"]
        assert target in finding_schema["properties"]["affected_targets"]["items"]["enum"]
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(output, ensure_ascii=False),
            thread_id=f"thread_{self.calls}",
            turn_id=f"turn_{self.calls}",
            event_methods=("turn/completed",),
            item_types=("agentMessage",),
            external_call_attempted=self.semantic_external_call_attempted,
        )

    def _section_revision_result(self, request: Any) -> CodexAppServerTurnResult:
        context = json.loads(request.untrusted_context)
        generation_input = context["generation_input"]
        base_revision = context["base_revision"]
        selected_headings = context["editable_section_headings"]
        base_by_heading = {
            section["heading"]: section for section in base_revision["sections"]
        }
        selected_sections = [base_by_heading[heading] for heading in selected_headings]
        evidence_ids = list(
            dict.fromkeys(
                evidence_id
                for section in selected_sections
                for evidence_id in section["evidence_ids"]
            )
        )
        output = {
            "draft_kind": "section_draft",
            "language": "pl-PL",
            "title": base_revision["title"],
            "meta_title": generation_input["title"],
            "meta_description": "Sprawdź zakres przed kontaktem z Ekologus.",
            "h1": generation_input["title"],
            "sections": [
                {
                    "heading": section["heading"],
                    "body_markdown": (
                        "Konkretna odpowiedź poprawiona po decyzji człowieka i advisory review."
                    ),
                    "evidence_ids": section["evidence_ids"],
                    "claims_used": generation_input["claims_allowed"],
                }
                for section in selected_sections
            ],
            "faq": ["Co warto sprawdzić przed kontaktem z Ekologus?"],
            "cta": "Skontaktuj się z Ekologus, żeby sprawdzić sytuację firmy.",
            "internal_links": ["https://ekologus.pl/kontakt/"],
            "source_facts_used": evidence_ids,
            "claims_needing_review": [],
            "forbidden_claims_avoided": generation_input["claims_removed_or_blocked"],
            "human_review_checklist": generation_input["human_review_questions"],
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


def _assert_planning_input_contract(planning_input: dict[str, Any]) -> None:
    assert planning_input["schema_name"] == "wilq_content_planning_input_v2"
    excluded_connectors = {
        "google_search_console",
        "google_ads",
        "google_analytics_4",
        "ahrefs",
        "google_merchant_center",
        "localo",
    }
    assert not {
        fact["source_connector"] for fact in planning_input["source_facts"]
    }.intersection(excluded_connectors)
    assert "baseline_proposal" not in planning_input


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
    monkeypatch.setattr(
        initial_draft_router,
        "content_codex_app_server_client",
        lambda: runtime,
    )
    monkeypatch.setattr(
        semantic_review_router,
        "content_codex_app_server_client",
        lambda: runtime,
    )
    monkeypatch.setattr(
        section_proposal_router,
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


def test_dynamic_planning_rejects_an_unknown_document_placement(
    planning_harness: tuple[TestClient, _PlanningClient],
) -> None:
    client, runtime = planning_harness
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    service_card_id = snapshot["service_profile_context"]["service_card_id"]
    planning_digest = snapshot["planning_workspace"]["proposal"]["planning_digest"]
    approved = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-review",
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
    planning_input = client.get(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals"
    ).json()
    runtime.planning_placement = "gdzieś obok formularza"

    result = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/planning-proposals",
        json=_generation_request(service_card_id, planning_input["planning_input_digest"]),
    )

    assert result.status_code == 200
    assert result.json()["status"] == "blocked"
    assert result.json()["blockers"][0]["code"] == "invalid_structured_output"
    assert content_planning_proposal_store().latest(BDO_WORK_ITEM_ID) is None


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


def test_initial_full_draft_uses_the_same_atomic_contract_for_both_services(
    planning_harness: tuple[TestClient, _PlanningClient],
) -> None:
    client, runtime = planning_harness
    revisions: dict[str, dict[str, Any]] = {}
    expected_calls = 0
    for work_item_id in (BDO_WORK_ITEM_ID, OUTSOURCING_WORK_ITEM_ID):
        proposal = _approve_and_generate(
            client,
            runtime,
            work_item_id,
            expected_calls=expected_calls,
        )
        expected_calls += 1
        _approve_generated_plan(client, work_item_id, proposal)
        stale_request = _initial_draft_request(proposal)
        stale_request["expected_planning_digest"] = "0" * 64
        stale = client.post(
            f"/api/content/work-items/{work_item_id}/initial-draft",
            json=stale_request,
        )
        assert stale.status_code == 409
        assert stale.json()["blockers"][0]["code"] == "proposal_mismatch"
        assert runtime.calls == expected_calls
        created = client.post(
            f"/api/content/work-items/{work_item_id}/initial-draft",
            json=_initial_draft_request(proposal),
        )
        assert created.status_code == 200, created.json()
        payload = cast(dict[str, Any], created.json())
        assert payload["status"] == "created", payload["blockers"][0]["source_codes"]
        revision = cast(dict[str, Any], payload["revision"])
        assert revision["schema_version"] == "wilq_content_draft_revision_v2"
        assert revision["publish_ready"] is False
        assert revision["proposal_metadata"]["review_scope"] == (
            "persisted_full_document_and_declared_lineage"
        )
        assert revision["planning_input_digest"] == proposal["planning_input_digest"]
        assert revision["service_card_id"] == proposal["service_card_id"]
        assert all(section["evidence_ids"] for section in revision["sections"])
        assert runtime.calls == expected_calls + 1
        expected_calls += 1
        repeated = client.post(
            f"/api/content/work-items/{work_item_id}/initial-draft",
            json=_initial_draft_request(proposal),
        )
        assert repeated.status_code == 409
        assert repeated.json()["blockers"][0]["code"] == "revision_already_exists"
        assert runtime.calls == expected_calls
        revisions[work_item_id] = revision

    assert revisions[BDO_WORK_ITEM_ID]["page_assets"]["h1"] != (
        revisions[OUTSOURCING_WORK_ITEM_ID]["page_assets"]["h1"]
    )


def test_initial_full_draft_runtime_failure_writes_no_partial_revision_and_get_is_model_free(
    planning_harness: tuple[TestClient, _PlanningClient],
) -> None:
    client, runtime = planning_harness
    proposal = _approve_and_generate(client, runtime, BDO_WORK_ITEM_ID, expected_calls=0)
    _approve_generated_plan(client, BDO_WORK_ITEM_ID, proposal)
    runtime.fail = True
    failed = client.post(
        f"/api/content/work-items/{BDO_WORK_ITEM_ID}/initial-draft",
        json=_initial_draft_request(proposal),
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed", failed.json()
    calls_after_failure = runtime.calls
    snapshot = _snapshot(client, BDO_WORK_ITEM_ID)
    assert snapshot["revision_workspace"]["latest_revision"] is None
    assert runtime.calls == calls_after_failure


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
    input_summary = before.json()["input_summary"]
    assert len(input_summary["source_assessments"]) == 10
    gsc_assessment = next(
        item for item in input_summary["source_assessments"] if item["source"] == "gsc"
    )
    assert gsc_assessment["status"] == "used"
    assert gsc_assessment["landing_match_tiers"]
    assert input_summary["evidence_id_count"] > 0
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
    assert created.json()["proposal"]["input_schema_version"] == (
        "wilq_content_planning_input_v2"
    )
    repeated = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json=_generation_request(service_card_id, input_digest),
    )
    assert repeated.json()["status"] == "idempotent"
    assert repeated.json()["proposal"]["proposal_id"] == created.json()["proposal"]["proposal_id"]
    ready = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert ready.json()["status"] == "ready"
    assert ready.json()["proposal"] == created.json()["proposal"]
    assert ready.json()["input_summary"] == input_summary
    return cast(dict[str, Any], created.json()["proposal"])


def _snapshot(client: TestClient, work_item_id: str) -> dict[str, Any]:
    response = client.get(f"/api/content/work-items/{work_item_id}/snapshot")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def _approve_generated_plan(
    client: TestClient,
    work_item_id: str,
    proposal: dict[str, Any],
) -> None:
    for stage in ("scope", "section_map"):
        response = client.post(
            f"/api/content/work-items/{work_item_id}/planning-review",
            json={
                "stage": stage,
                "service_card_id": proposal["service_card_id"] if stage == "scope" else None,
                "expected_planning_digest": proposal["planning_digest"],
                "decision": "approved",
                "reviewed_by": "wilku",
                "checked_items": ["strona", "usługa", "intencja", "sekcje", "CTA"],
                "notes": "Syntetyczne zatwierdzenie aktualnego planu.",
            },
        )
        assert response.status_code == 200, response.json()


def _initial_draft_request(proposal: dict[str, Any]) -> dict[str, str]:
    return {
        "expected_proposal_id": proposal["proposal_id"],
        "expected_planning_digest": proposal["planning_digest"],
        "expected_planning_input_digest": proposal["planning_input_digest"],
        "requested_by": "wilku",
    }


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
