from __future__ import annotations

import pytest

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftModelOutput
from wilq.content.workflow.contracts import ContentDraftRevisionReviewRequest
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.new_page import (
    ContentNewPageBriefInput,
    ContentNewPagePlanningFoundation,
    build_new_page_brief,
    build_new_page_document_identity,
)
from wilq.content.workflow.new_page_document import (
    ContentNewPagePlanningReviewCommand,
    build_new_page_canonical_document_workspace,
)
from wilq.content.workflow.new_page_revision import (
    append_new_page_initial_revision,
    review_new_page_revision,
)
from wilq.content.workflow.planning import ContentPlanningDecision, ContentPlanningProposal
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


def _exact_inputs() -> tuple[ContentNewPagePlanningFoundation, ContentPlanningProposal]:
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
    foundation = ContentNewPagePlanningFoundation(
        foundation_id="content_new_page_foundation_test",
        work_item_id="content_work_item_new_page_test",
        brief_id=brief.brief_id,
        brief_digest=brief.brief_digest,
        overlap_digest="a" * 64,
        service_card_id="service_environment",
        service_card_digest="b" * 64,
        service_label="Dokumentacja środowiskowa",
        confirmed_by="Wilku",
        created_at=utc_now(),
    )
    proposal = ContentPlanningProposal(
        work_item_id=foundation.work_item_id,
        planning_digest="c" * 64,
        proposal_id="content_planning_proposal_test",
        proposal_version=1,
        codex_run_id="codex_new_page_plan_test",
        generation_status="codex_generated",
        planning_input_digest="d" * 64,
        goal="new_page",
        final_canonical_url=None,
        proposed_ia_location=brief.proposed_ia_location,
        new_page_document_identity=build_new_page_document_identity(
            foundation=foundation,
            proposed_ia_location=brief.proposed_ia_location,
        ),
        service_card_id=foundation.service_card_id,
        service_label=foundation.service_label,
        service_selection_confirmed=True,
        target_reader=brief.audience,
        buyer_problem=brief.purpose,
        buyer_trigger="Przed rozpoczęciem inwestycji.",
        search_intent=brief.search_intent,
        cta_direction="Poproś o konsultację.",
        sections=[
            {
                "section_id": "new_page_section_01",
                "heading": "Jak przygotować dokumentację",
                "purpose": "Wyjaśnia pierwszy krok.",
                "inventory_disposition": "create",
                "evidence_ids": ["ev_service"],
            }
        ],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Zapisz plan do review.",
        ),
        evidence_ids=["ev_service"],
        source_connectors=["public_site"],
    )
    return foundation, proposal


def test_new_page_canonical_document_requires_exact_approved_plan() -> None:
    foundation, proposal = _exact_inputs()
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Dokumentacja środowiskowa inwestycji",
            purpose="Pomóc inwestorowi przygotować dokumentację środowiskową.",
            service="Dokumentacja środowiskowa",
            audience="Inwestor przygotowujący przedsięwzięcie",
            search_intent="dokumentacja środowiskowa inwestycji",
            proposed_ia_location="Usługi → Dokumentacja środowiskowa",
        )
    ).model_copy(update={"brief_id": foundation.brief_id, "brief_digest": foundation.brief_digest})
    pending = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal, decisions=[]
    )
    assert pending is not None
    assert pending.status == "review_required"
    assert pending.document_status == "not_created"
    assert pending.public_source_status == "not_applicable"
    assert pending.public_deployment_status == "not_confirmed"

    decision = ContentPlanningDecision(
        decision_id="content_planning_review_test",
        decision_number=1,
        work_item_id=foundation.work_item_id,
        stage="scope",
        planning_digest=proposal.planning_digest,
        service_card_id=foundation.service_card_id,
        decision="approved",
        reviewed_by="Wilku",
        checked_items=["zakres"],
        created_at=utc_now(),
    )
    ready = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal, decisions=[decision]
    )
    assert ready is not None
    assert ready.status == "ready_for_document"
    assert ready.proposal_id == proposal.proposal_id
    assert ready.outline[0].section_id == "new_page_section_01"


def test_new_page_canonical_document_rejects_mismatched_lineage_and_blank_approval() -> None:
    foundation, proposal = _exact_inputs()
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Dokumentacja środowiskowa inwestycji",
            purpose="Pomóc inwestorowi przygotować dokumentację środowiskową.",
            service="Dokumentacja środowiskowa",
            audience="Inwestor przygotowujący przedsięwzięcie",
            search_intent="dokumentacja środowiskowa inwestycji",
            proposed_ia_location="Usługi → Dokumentacja środowiskowa",
        )
    ).model_copy(update={"brief_id": foundation.brief_id, "brief_digest": foundation.brief_digest})
    mismatched_identity = proposal.new_page_document_identity.model_copy(
        update={"brief_digest": "e" * 64}
    )
    mismatched = proposal.model_copy(
        update={"new_page_document_identity": mismatched_identity}
    )
    blocked = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=mismatched, decisions=[]
    )
    assert blocked is not None
    assert blocked.status == "blocked"
    assert blocked.outline == []

    try:
        ContentNewPagePlanningReviewCommand(
            expected_proposal_id=proposal.proposal_id or "",
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=proposal.planning_input_digest or "",
            decision="approved",
            reviewed_by="Wilku",
            checked_items=[],
        )
    except ValueError as error:
        assert "checked items" in str(error)
    else:
        raise AssertionError("Blank planning approval must fail closed.")


def _new_page_append_context(tmp_path):
    foundation, proposal = _exact_inputs()
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Dokumentacja środowiskowa inwestycji",
            purpose="Pomóc inwestorowi przygotować dokumentację środowiskową.",
            service="Dokumentacja środowiskowa",
            audience="Inwestor przygotowujący przedsięwzięcie",
            search_intent="dokumentacja środowiskowa inwestycji",
            proposed_ia_location="Usługi → Dokumentacja środowiskowa",
        )
    ).model_copy(update={"brief_id": foundation.brief_id, "brief_digest": foundation.brief_digest})
    approved = ContentPlanningDecision(
        decision_id="content_planning_review_test",
        decision_number=1,
        work_item_id=foundation.work_item_id,
        stage="scope",
        planning_digest=proposal.planning_digest,
        service_card_id=foundation.service_card_id,
        decision="approved",
        reviewed_by="Wilku",
        checked_items=["zakres"],
        created_at=utc_now(),
    )
    output = ContentInitialDraftModelOutput(
        page_assets={
            "wordpress_title": brief.title,
            "meta_title": "Dokumentacja środowiskowa | Ekologus",
            "meta_description": "Przygotuj dokumentację środowiskową inwestycji.",
            "h1": brief.title,
            "lead": "Sprawdź pierwszy krok przed rozpoczęciem inwestycji.",
        },
        sections=[
            {
                "section_id": "new_page_section_01",
                "heading": "Jak przygotować dokumentację",
                "body_markdown": "Zacznij od sprawdzenia zakresu inwestycji.",
            }
        ],
    )
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    started_run = CodexRun(
        id="codex_new_page_document",
        skill="wilq-content-operator",
        hook="content_new_page_initial_draft",
        source="wilq_api",
        status="started",
        proposal_id=proposal.proposal_id,
        planning_input_digest=proposal.planning_input_digest,
    )
    LocalStateStore(tmp_path / "wilq.sqlite3").save_codex_run(started_run)
    completed_run = started_run.model_copy(
        update={"status": "completed", "completed_at": utc_now()}
    )
    return brief, foundation, proposal, approved, output, store, completed_run


def test_new_page_append_rejects_stale_plan_before_persisting(tmp_path) -> None:
    brief, foundation, proposal, approved, output, store, completed_run = _new_page_append_context(
        tmp_path
    )
    with pytest.raises(ValueError, match="stale or not approved"):
        append_new_page_initial_revision(
            brief=brief, foundation=foundation, proposal=proposal, decisions=[approved],
            expected_proposal_id=proposal.proposal_id or "",
            expected_planning_digest="e" * 64,
            expected_planning_input_digest=proposal.planning_input_digest or "",
            output=output, completed_run=completed_run, requested_by="Wilku", store=store,
        )
    assert store.load_draft_revision_state(foundation.work_item_id).revision_count == 0


def test_new_page_revision_review_is_exact_bound(tmp_path) -> None:
    brief, foundation, proposal, approved, output, store, completed_run = _new_page_append_context(
        tmp_path
    )
    result = append_new_page_initial_revision(
        brief=brief, foundation=foundation, proposal=proposal, decisions=[approved],
        expected_proposal_id=proposal.proposal_id or "",
        expected_planning_digest=proposal.planning_digest,
        expected_planning_input_digest=proposal.planning_input_digest or "",
        output=output, completed_run=completed_run, requested_by="Wilku", store=store,
    )
    assert result.status == "created"
    assert result.revision is not None
    assert result.revision.document_kind == "new_page"
    assert result.revision.final_canonical_url is None

    workspace = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal, decisions=[approved]
    )
    assert workspace is not None
    stale_review = review_new_page_revision(
        workspace=workspace,
        revision_id=result.revision.revision_id,
        request=ContentDraftRevisionReviewRequest(
            expected_revision_digest="f" * 64,
            reviewed_by="Wilku",
            decision="approved",
            checked_items=["dokument", "dowody"],
            evidence_ids=["ev_service"],
        ),
        store=store,
    )
    assert stale_review.status == "conflict"
    assert stale_review.conflict is not None
    assert stale_review.conflict.code == "digest_mismatch"
    review = review_new_page_revision(
        workspace=workspace,
        revision_id=result.revision.revision_id,
        request=ContentDraftRevisionReviewRequest(
            expected_revision_digest=result.revision.content_digest,
            reviewed_by="Wilku",
            decision="approved",
            checked_items=["dokument", "dowody"],
            evidence_ids=["ev_service"],
        ),
        store=store,
    )
    assert review.status == "created"
    assert review.review is not None
    assert review.review.revision_id == result.revision.revision_id
    projected = build_new_page_canonical_document_workspace(
        brief=brief,
        foundation=foundation,
        proposal=proposal,
        decisions=[approved],
        revision_state=store.load_draft_revision_state(foundation.work_item_id),
    )
    assert projected is not None
    assert projected.status == "document_approved"
    assert projected.document_status == "approved"
    assert projected.canonical_revision == result.revision
    assert projected.revision_review == review.review
    assert projected.public_source_status == "not_applicable"
    assert projected.public_source_url is None
    with pytest.raises(ValueError, match="outside the exact"):
        review_new_page_revision(
            workspace=workspace,
            revision_id=result.revision.revision_id,
            request=ContentDraftRevisionReviewRequest(
                expected_revision_digest=result.revision.content_digest,
                reviewed_by="Wilku",
                decision="needs_changes",
                notes="Brakuje uzasadnienia.",
                evidence_ids=["ev_foreign"],
            ),
            store=store,
        )
