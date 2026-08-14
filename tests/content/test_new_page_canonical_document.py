from __future__ import annotations

import json
from pathlib import Path

import pytest

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftSectionOutput,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.contracts.contracts import ContentDraftRevisionReviewRequest
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.target.new_page import (
    ContentNewPageBrief,
    ContentNewPageBriefInput,
    ContentNewPagePlanningFoundation,
    build_new_page_brief,
    build_new_page_document_identity,
)
from wilq.content.workflow.target.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
    ContentNewPageDeliveryReadiness,
    build_new_page_canonical_document_workspace,
    build_new_page_delivery_readiness,
)
from wilq.content.workflow.target.new_page_initial_draft import generate_new_page_initial_draft
from wilq.content.workflow.target.new_page_revision import (
    append_new_page_initial_revision,
    review_new_page_revision,
)
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
            ContentPlanningSection(
                section_id="new_page_section_01",
                heading="Jak przygotować dokumentację",
                purpose="Wyjaśnia pierwszy krok.",
                inventory_disposition="create",
                evidence_ids=["ev_service"],
            )
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


def _planning_input_for_new_page(
    foundation: ContentNewPagePlanningFoundation,
    proposal: ContentPlanningProposal,
) -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        planning_input_digest=proposal.planning_input_digest,
        work_item_id=foundation.work_item_id,
        goal="new_page",
        confirmed_service_card_id=foundation.service_card_id,
        regulatory_coverage=ContentRegulatoryCoverage(),
        source_facts=[],
        evidence_ids=proposal.evidence_ids,
    )


def test_new_page_canonical_document_uses_exact_generated_plan() -> None:
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
        brief=brief, foundation=foundation, proposal=proposal
    )
    assert pending is not None
    assert pending.status == "ready_for_document"
    assert pending.document_status == "not_created"
    assert pending.public_source_status == "not_applicable"
    assert pending.public_deployment_status == "not_confirmed"


def test_new_page_delivery_readiness_fails_closed_before_exact_approval() -> None:
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
    workspace = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal
    )
    assert workspace is not None

    blocked = build_new_page_delivery_readiness(
        workspace,
        allowed_content_types=["page", "post"],
        authoring_profile_digest="a" * 64,
        evidence_ids=["ev_wordpress_profile"],
    )

    assert blocked.status == "blocked"
    assert blocked.revision_id is None
    with pytest.raises(ValueError, match="Ready new-page delivery"):
        ContentNewPageDeliveryReadiness(
            status="ready_for_action",
            work_item_id=foundation.work_item_id,
            brief_id=foundation.brief_id,
            brief_digest=foundation.brief_digest,
            foundation_id=foundation.foundation_id,
            service_card_id=foundation.service_card_id,
            service_card_digest=foundation.service_card_digest,
            safe_next_step="Nie powinno przejść.",
        )
    ready = ContentNewPageDeliveryReadiness(
        status="ready_for_action",
        work_item_id=foundation.work_item_id,
        brief_id=foundation.brief_id,
        brief_digest=foundation.brief_digest,
        foundation_id=foundation.foundation_id,
        service_card_id=foundation.service_card_id,
        service_card_digest=foundation.service_card_digest,
        revision_id="revision_new_page_exact",
        revision_digest="b" * 64,
        allowed_content_types=["page"],
        authoring_profile_digest="c" * 64,
        evidence_ids=["ev_wordpress_profile"],
        safe_next_step="Wybierz typ nowego draftu.",
    )
    assert ready.status == "ready_for_action"

    document_workspace = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal
    )
    assert document_workspace is not None
    assert document_workspace.status == "ready_for_document"
    assert document_workspace.proposal_id == proposal.proposal_id
    assert document_workspace.outline[0].section_id == "new_page_section_01"


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
    assert proposal.new_page_document_identity is not None
    mismatched_identity = proposal.new_page_document_identity.model_copy(
        update={"brief_digest": "e" * 64}
    )
    mismatched = proposal.model_copy(
        update={"new_page_document_identity": mismatched_identity}
    )
    blocked = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=mismatched
    )
    assert blocked is not None
    assert blocked.status == "blocked"
    assert blocked.outline == []

def test_new_page_workspace_requires_exact_generated_plan_and_truthful_top_level_state() -> None:
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
        brief=brief, foundation=foundation, proposal=proposal
    )
    assert pending is not None
    assert ContentNewPageCanonicalDocumentWorkspace.model_validate(
        pending.model_dump(mode="python")
    ) == pending
    for blank_proposal_id in ("", "   "):
        with pytest.raises(ValueError):
            ContentNewPageCanonicalDocumentWorkspace.model_validate(
                pending.model_dump(mode="python") | {"proposal_id": blank_proposal_id}
            )
    with pytest.raises(ValueError, match="requires a canonical revision"):
        ContentNewPageCanonicalDocumentWorkspace.model_validate(
            pending.model_dump(mode="python") | {"status": "document_approved"}
        )
    with pytest.raises(ValueError):
        ContentNewPageCanonicalDocumentWorkspace.model_validate(
            pending.model_dump(mode="python") | {"status": "review_required"}
        )
    blocked = pending.model_dump(mode="python") | {
        "status": "blocked",
        "proposal_id": None,
        "planning_digest": None,
        "planning_input_digest": None,
    }
    assert ContentNewPageCanonicalDocumentWorkspace.model_validate(blocked).status == "blocked"
    for partial_identity in (
        {"proposal_id": "content_planning_proposal_partial"},
        {"planning_digest": "e" * 64},
        {"proposal_id": "content_planning_proposal_partial", "planning_input_digest": "f" * 64},
    ):
        with pytest.raises(ValueError, match="Blocked new-page workspace"):
            ContentNewPageCanonicalDocumentWorkspace.model_validate(blocked | partial_identity)

    ready = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal
    )
    assert ready is not None
    assert ContentNewPageCanonicalDocumentWorkspace.model_validate(
        ready.model_dump(mode="python")
    ) == ready
    for blank_proposal_id in ("", "   "):
        with pytest.raises(ValueError):
            ContentNewPageCanonicalDocumentWorkspace.model_validate(
                ready.model_dump(mode="python") | {"proposal_id": blank_proposal_id}
            )
    with pytest.raises(ValueError):
        ContentNewPageCanonicalDocumentWorkspace.model_validate(
            ready.model_dump(mode="python") | {"status": "review_required"}
        )
    with pytest.raises(ValueError):
        ContentNewPageCanonicalDocumentWorkspace.model_validate(
            ready.model_dump(mode="python")
            | {"plan_review": {"decision_id": "legacy_plan_review"}}
        )


def _new_page_append_context(
    tmp_path: Path,
) -> tuple[
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
    ContentPlanningProposal,
    ContentInitialDraftModelOutput,
    ContentWorkflowStore,
    CodexRun,
]:
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
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title=brief.title,
            meta_title="Dokumentacja środowiskowa | Ekologus",
            meta_description="Przygotuj dokumentację środowiskową inwestycji.",
            h1=brief.title,
            lead="Sprawdź pierwszy krok przed rozpoczęciem inwestycji.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="new_page_section_01",
                heading="Jak przygotować dokumentację",
                body_markdown=(
                    "Zacznij od sprawdzenia zakresu inwestycji i uporządkowania danych. "
                    "Następnie zaplanuj dokumenty potrzebne do dalszych prac."
                ),
            )
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
    return brief, foundation, proposal, output, store, completed_run


def test_new_page_append_rejects_stale_plan_before_persisting(tmp_path: Path) -> None:
    brief, foundation, proposal, output, store, completed_run = _new_page_append_context(
        tmp_path
    )
    with pytest.raises(ValueError, match="stale or unavailable"):
        append_new_page_initial_revision(
            brief=brief, foundation=foundation, proposal=proposal,
            expected_proposal_id=proposal.proposal_id or "",
            expected_planning_digest="e" * 64,
            expected_planning_input_digest=proposal.planning_input_digest or "",
            output=output, completed_run=completed_run, requested_by="Wilku", store=store,
        )
    assert store.load_draft_revision_state(foundation.work_item_id).revision_count == 0


def test_new_page_revision_review_is_exact_bound(tmp_path: Path) -> None:
    brief, foundation, proposal, output, store, completed_run = _new_page_append_context(
        tmp_path
    )
    result = append_new_page_initial_revision(
        brief=brief, foundation=foundation, proposal=proposal,
        expected_proposal_id=proposal.proposal_id or "",
        expected_planning_digest=proposal.planning_digest,
        expected_planning_input_digest=proposal.planning_input_digest or "",
        output=output, completed_run=completed_run, requested_by="Wilku", store=store,
    )
    assert result.status == "created", repr(result)
    assert result.revision is not None
    assert result.revision.document_kind == "new_page"
    assert result.revision.final_canonical_url is None

    workspace = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal
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
    assert store.load_draft_revision_state(foundation.work_item_id).latest_review is None
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
        revision_state=store.load_draft_revision_state(foundation.work_item_id),
    )
    assert projected is not None
    assert projected.status == "document_approved"
    assert projected.document_status == "approved"
    assert projected.canonical_revision == result.revision
    assert projected.revision_review == review.review
    assert projected.public_source_status == "not_applicable"
    assert projected.public_source_url is None
    assert projected.document_lineage.source_material_ids == result.revision.source_material_ids
    assert {
        *[card.id for card in projected.document_lineage.knowledge_cards],
        *projected.document_lineage.unresolved_knowledge_card_ids,
    } == set(result.revision.knowledge_card_ids)
    assert ContentNewPageCanonicalDocumentWorkspace.model_validate(
        projected.model_dump(mode="python")
    ) == projected
    mismatched_lineage = projected.model_dump(mode="python")
    mismatched_lineage["document_lineage"]["source_material_ids"] = ["foreign_material"]
    with pytest.raises(ValueError, match="Document lineage must match"):
        ContentNewPageCanonicalDocumentWorkspace.model_validate(mismatched_lineage)
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


def test_new_page_generator_appends_only_the_exact_generated_plan(tmp_path: Path) -> None:
    brief, foundation, proposal, output, _, _ = _new_page_append_context(tmp_path)
    store = ContentWorkflowStore(tmp_path / "generator.sqlite3")
    workspace = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal
    )
    assert workspace is not None

    class FakeClient:
        def run_structured_turn(
            self, request: CodexAppServerStructuredTurnRequest
        ) -> CodexAppServerTurnResult:
            assert "do_not_write_vendor" in request.application_context
            return CodexAppServerTurnResult(
                status="completed", output_text=json.dumps(output.model_dump(mode="json"))
            )

    result = generate_new_page_initial_draft(
        brief=brief,
        foundation=foundation,
        planning_input=_planning_input_for_new_page(foundation, proposal),
        proposal=proposal,
        workspace=workspace,
        request=ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id or "",
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=proposal.planning_input_digest or "",
            requested_by="Wilku",
        ),
        client=FakeClient(),
        workflow_store=store,
        run_store=LocalStateStore(tmp_path / "generator.sqlite3"),
        endpoint_path="/api/content/new-page-briefs/content_new_page_brief_test/initial-draft",
    )
    assert result.status == "created"
    assert result.revision is not None
    assert result.revision.document_kind == "new_page"
    assert result.revision.final_canonical_url is None
    assert result.runtime.status == "completed"


def test_new_page_generator_rejects_stale_plan_before_starting_codex(
    tmp_path: Path,
) -> None:
    brief, foundation, proposal, _, _, _ = _new_page_append_context(tmp_path)
    workspace = build_new_page_canonical_document_workspace(
        brief=brief, foundation=foundation, proposal=proposal
    )
    assert workspace is not None

    class NoCallClient:
        def run_structured_turn(
            self, request: CodexAppServerStructuredTurnRequest
        ) -> CodexAppServerTurnResult:
            raise AssertionError("stale planning binding must not call Codex")

    store = ContentWorkflowStore(tmp_path / "stale-generator.sqlite3")
    result = generate_new_page_initial_draft(
        brief=brief,
        foundation=foundation,
        planning_input=_planning_input_for_new_page(foundation, proposal),
        proposal=proposal,
        workspace=workspace,
        request=ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id or "",
            expected_planning_digest="e" * 64,
            expected_planning_input_digest=proposal.planning_input_digest or "",
            requested_by="Wilku",
        ),
        client=NoCallClient(),
        workflow_store=store,
        run_store=LocalStateStore(tmp_path / "stale-generator.sqlite3"),
        endpoint_path="/api/content/new-page-briefs/content_new_page_brief_test/initial-draft",
    )
    assert result.status == "blocked"
    assert result.blockers[0].code == "proposal_mismatch"
    assert store.load_draft_revision_state(foundation.work_item_id).revision_count == 0
