from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import wilq.content.planning.dynamic_input as planning_input_module
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.new_page_proposal import (
    ContentNewPagePlanningProposalRequest,
    ContentNewPagePlanningProposalWorkspace,
    build_new_page_planning_proposal_workspace,
    generate_new_page_planning_proposal,
    queue_new_page_planning_proposal,
)
from wilq.content.workflow.target.new_page import (
    ContentNewPageBrief,
    ContentNewPageBriefInput,
    ContentNewPageFoundationCommand,
    ContentNewPageOverlapGuard,
    ContentNewPagePlanningFoundation,
    build_new_page_brief,
    build_new_page_planning_foundation,
    new_page_overlap_digest,
)
from wilq.storage.local_state import LocalStateStore


class _PlanningClient:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    def run_structured_turn(self, request) -> CodexAppServerTurnResult:
        self.calls += 1
        if self.fail:
            return CodexAppServerTurnResult(status="failed")
        planning_input = json.loads(request.untrusted_context)["planning_input"]
        evidence_id = planning_input["evidence_ids"][0]
        output = {
            "language": "pl-PL",
            "service_card_id": planning_input["confirmed_service_card_id"],
            "target_reader": planning_input["target_reader"],
            "buyer_problem": planning_input["buyer_problem"],
            "buyer_trigger": planning_input["buyer_trigger"],
            "search_intent": planning_input["search_intent"],
            "angle": "Bezpieczna odpowiedź na intencję nowej strony.",
            "value_proposition": "Porządkuje pierwszy krok inwestora.",
            "page_assets": {
                "title": "Dokumentacja środowiskowa — Ekologus",
                "h1": "Dokumentacja środowiskowa dla inwestycji",
                "lead": "Sprawdź wymagania przed rozpoczęciem inwestycji.",
                "meta_title": "Dokumentacja środowiskowa | Ekologus",
                "meta_description": "Pomagamy przygotować dokumentację środowiskową.",
            },
            "sections": [
                {
                    "heading": "Jak przygotować dokumentację środowiskową",
                    "purpose": "Wyjaśnia pierwszy bezpieczny krok.",
                    "reader_question": "Od czego zacząć przygotowanie dokumentacji?",
                    "inventory_disposition": "create",
                    "inventory_section_id": None,
                    "inventory_heading": None,
                    "query_terms": [],
                    "evidence_ids": [evidence_id],
                    "claim_ids": [],
                }
            ],
            "faq": [],
            "cta_blocks": [
                {
                    "placement": "after_content",
                    "purpose": "Zaproś do konsultacji zakresu dokumentacji.",
                    "copy_direction": "Opisz inwestycję i poproś o weryfikację.",
                    "evidence_ids": [evidence_id],
                    "claim_ids": [],
                }
            ],
            "internal_links": [],
            "conditional_hypotheses": [],
            "measurement_plan": {
                "metrics_to_watch": [],
                "baseline_evidence_ids": [],
                "observation_rule": planning_input["measurement_observation_rule"],
                "success_claim_rule": planning_input["measurement_success_claim_rule"],
            },
            "publish_ready": False,
        }
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(output, ensure_ascii=False),
            thread_id="thread_new_page",
            turn_id=f"turn_{self.calls}",
            event_methods=("turn/completed",),
            item_types=("agentMessage",),
        )


def _ready_context(
    monkeypatch,
) -> tuple[
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
    ContentNewPageOverlapGuard,
    ContentKnowledgeCard,
]:
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Dokumentacja środowiskowa inwestycji",
            purpose="Pomóc inwestorowi przygotować dokumentację środowiskową.",
            service="Dokumentacja środowiskowa",
            audience="Inwestor przygotowujący przedsięwzięcie",
            search_intent="dokumentacja środowiskowa inwestycji",
            proposed_ia_location="Usługi → Dokumentacja środowiskowa",
        )
    )
    guard = ContentNewPageOverlapGuard(
        disposition="no_conflict",
        label="Brak bezpośredniego pokrycia",
        reason="Katalog nie pokazuje bezpośredniego pokrycia.",
        caveat="To nie jest dowód braku wszystkich duplikatów.",
        evidence_ids=["ev_inventory_new_page"],
    )
    service_card = next(
        card for card in ekologus_content_knowledge_cards() if card.card_type == "service"
    ).model_copy(
        update={
            "id": "knowledge_service_new_page_proposal",
            "lifecycle_status": "approved_current",
            "evidence_ids": ["ev_service_new_page"],
            "source_connectors": ["public_site"],
            "cta_patterns": ["Opisz sytuację i poproś o kontakt."],
        }
    )
    foundation = build_new_page_planning_foundation(
        brief=brief,
        guard=guard,
        command=ContentNewPageFoundationCommand(
            expected_brief_digest=brief.brief_digest,
            expected_overlap_digest=new_page_overlap_digest(guard),
            service_card_id=service_card.id,
            confirmed_by="Wilku",
        ),
        service_card=service_card,
    )
    source_fact = ContentSourceFact(
        source_id="fact_service_new_page_proposal",
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path="https://www.ekologus.pl/oferta/",
        extracted_fact="Ekologus pomaga inwestorom w dokumentacji środowiskowej.",
        scope="service",
        freshness_date="2026-07-28",
        confidence=0.9,
        review_status="approved",
        reviewer="Wilku",
        evidence_ids=["ev_service_new_page"],
        source_connectors=["public_site"],
        target_card_id=service_card.id,
        target_card_type="service",
        target_card_title=service_card.title,
    )
    monkeypatch.setattr(planning_input_module, "ekologus_source_facts", lambda: (source_fact,))
    return brief, foundation, guard, service_card


def test_new_page_plan_uses_exact_input_without_refresh_snapshot_or_public_url(
    monkeypatch,
    tmp_path: Path,
) -> None:
    brief, foundation, guard, service_card = _ready_context(monkeypatch)
    store = ContentPlanningProposalStore(tmp_path / "new-page-plans.sqlite3")
    workspace = build_new_page_planning_proposal_workspace(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
        store=store,
    )
    assert workspace.readiness.status == "ready"
    assert workspace.proposal_status is not None
    assert workspace.proposal_status.status == "not_generated"
    assert workspace.proposal_status.proposal is None

    input_result = planning_input_module.build_new_page_planning_input(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
    )
    runtime = _PlanningClient()
    generated = generate_new_page_planning_proposal(
        workspace=workspace,
        build_result=input_result,
        request=ContentNewPagePlanningProposalRequest(
            expected_planning_input_digest=workspace.readiness.planning_input_digest or "",
            requested_by="Wilku",
        ),
        client=runtime,
        store=store,
        run_store=LocalStateStore(tmp_path / "new-page-runs.sqlite3"),
        endpoint_path=f"/api/content/new-page-briefs/{brief.brief_id}/planning-proposal",
    )

    assert runtime.calls == 1
    assert generated.proposal_status is not None
    assert generated.proposal_status.status == "created"
    assert generated.proposal_status.proposal is not None
    proposal = generated.proposal_status.proposal
    assert proposal.goal == "new_page"
    assert proposal.final_canonical_url is None
    assert proposal.inventory_mapping == []
    assert proposal.new_page_document_identity is not None
    assert proposal.new_page_document_identity.foundation_id == foundation.foundation_id

    response_payload = generated.proposal_status.model_dump(mode="python")
    for mismatch in (
        {"work_item_id": "another-work-item"},
        {"service_card_id": "another-service"},
        {"planning_input_digest": "f" * 64},
    ):
        with pytest.raises(ValidationError, match="nested exact proposal"):
            type(generated.proposal_status).model_validate(response_payload | mismatch)
    with pytest.raises(ValidationError, match="one exact ready input"):
        ContentNewPagePlanningProposalWorkspace.model_validate(
            generated.model_dump(mode="python") | {"brief_id": "another-brief"}
        )

    replay = generate_new_page_planning_proposal(
        workspace=workspace,
        build_result=input_result,
        request=ContentNewPagePlanningProposalRequest(
            expected_planning_input_digest=workspace.readiness.planning_input_digest or "",
            requested_by="Wilku",
        ),
        client=runtime,
        store=store,
        run_store=LocalStateStore(tmp_path / "new-page-runs.sqlite3"),
        endpoint_path=f"/api/content/new-page-briefs/{brief.brief_id}/planning-proposal",
    )
    assert replay.proposal_status is not None
    assert replay.proposal_status.status == "idempotent"
    assert runtime.calls == 1


def test_new_page_plan_rejects_stale_input_and_runtime_failure(monkeypatch, tmp_path: Path) -> None:
    brief, foundation, guard, service_card = _ready_context(monkeypatch)
    store = ContentPlanningProposalStore(tmp_path / "new-page-plans.sqlite3")
    workspace = build_new_page_planning_proposal_workspace(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
        store=store,
    )
    input_result = planning_input_module.build_new_page_planning_input(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
    )
    runtime = _PlanningClient()
    stale = generate_new_page_planning_proposal(
        workspace=workspace,
        build_result=input_result,
        request=ContentNewPagePlanningProposalRequest(
            expected_planning_input_digest="0" * 64,
            requested_by="Wilku",
        ),
        client=runtime,
        store=store,
        run_store=LocalStateStore(tmp_path / "new-page-runs.sqlite3"),
        endpoint_path="/api/content/new-page-briefs/test/planning-proposal",
    )
    assert stale.proposal_status is not None
    assert stale.proposal_status.status == "stale"
    assert runtime.calls == 0

    runtime.fail = True
    failed = generate_new_page_planning_proposal(
        workspace=workspace,
        build_result=input_result,
        request=ContentNewPagePlanningProposalRequest(
            expected_planning_input_digest=workspace.readiness.planning_input_digest or "",
            requested_by="Wilku",
        ),
        client=runtime,
        store=store,
        run_store=LocalStateStore(tmp_path / "new-page-runs.sqlite3"),
        endpoint_path="/api/content/new-page-briefs/test/planning-proposal",
    )
    assert failed.proposal_status is not None
    assert failed.proposal_status.status == "failed"
    assert failed.proposal_status.proposal is None


def test_new_page_plan_queue_claims_one_exact_run_before_the_worker_starts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    brief, foundation, guard, service_card = _ready_context(monkeypatch)
    store = ContentPlanningProposalStore(tmp_path / "new-page-plans.sqlite3")
    workspace = build_new_page_planning_proposal_workspace(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
        store=store,
    )
    input_result = planning_input_module.build_new_page_planning_input(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
    )
    request = ContentNewPagePlanningProposalRequest(
        expected_planning_input_digest=workspace.readiness.planning_input_digest or "",
        requested_by="Wilku",
    )

    first, first_claim = queue_new_page_planning_proposal(
        workspace=workspace,
        build_result=input_result,
        request=request,
        store=store,
    )
    second, second_claim = queue_new_page_planning_proposal(
        workspace=workspace,
        build_result=input_result,
        request=request,
        store=store,
    )

    assert first.proposal_status is not None
    assert first.proposal_status.status == "generating"
    assert second.proposal_status is not None
    assert second.proposal_status.status == "generating"
    assert first_claim is True
    assert second_claim is False

    completed = generate_new_page_planning_proposal(
        workspace=workspace,
        build_result=input_result,
        request=request,
        client=_PlanningClient(),
        store=store,
        run_store=LocalStateStore(tmp_path / "new-page-runs.sqlite3"),
        endpoint_path="/api/content/new-page-briefs/test/planning-proposal",
    )
    assert completed.proposal_status is not None
    assert completed.proposal_status.status == "created"
    store.save_terminal_response(completed.proposal_status)

    reread = build_new_page_planning_proposal_workspace(
        brief=brief,
        foundation=foundation,
        overlap_guard=guard,
        service_card=service_card,
        store=store,
    )
    assert reread.proposal_status is not None
    assert reread.proposal_status.status == "ready"


def test_new_page_plan_rejects_a_build_result_for_another_ready_workspace(
    monkeypatch,
    tmp_path: Path,
) -> None:
    brief_a, foundation_a, guard_a, service_card_a = _ready_context(monkeypatch)
    store = ContentPlanningProposalStore(tmp_path / "new-page-plans.sqlite3")
    workspace_a = build_new_page_planning_proposal_workspace(
        brief=brief_a,
        foundation=foundation_a,
        overlap_guard=guard_a,
        service_card=service_card_a,
        store=store,
    )
    brief_b, foundation_b, guard_b, service_card_b = _ready_context(monkeypatch)
    input_b = planning_input_module.build_new_page_planning_input(
        brief=brief_b,
        foundation=foundation_b,
        overlap_guard=guard_b,
        service_card=service_card_b,
    )
    request_b = ContentNewPagePlanningProposalRequest(
        expected_planning_input_digest=input_b.planning_input.planning_input_digest,
        requested_by="Wilku",
    )
    runtime = _PlanningClient()

    with pytest.raises(ValueError, match="exact workspace readiness"):
        queue_new_page_planning_proposal(
            workspace=workspace_a,
            build_result=input_b,
            request=request_b,
            store=store,
        )
    with pytest.raises(ValueError, match="exact workspace readiness"):
        generate_new_page_planning_proposal(
            workspace=workspace_a,
            build_result=input_b,
            request=request_b,
            client=runtime,
            store=store,
            run_store=LocalStateStore(tmp_path / "new-page-runs.sqlite3"),
            endpoint_path="/api/content/new-page-briefs/test/planning-proposal",
        )

    assert runtime.calls == 0
    assert (
        store.for_input(
            foundation_b.work_item_id,
            foundation_b.service_card_id,
            input_b.planning_input.planning_input_digest,
        )
        is None
    )
