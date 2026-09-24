from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_codex_proposal, content_workflow
from tests.content.legacy_repair_test_routes import register_legacy_repair_test_route
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts import codex_section_proposal
from wilq.content.drafts.codex_section_proposal import propose_content_section_revision
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexRuntimeTrace,
    ContentCodexSectionProposalBlocker,
    ContentCodexSectionProposalRequest,
    ContentCodexSectionProposalResponse,
    ContentRevisionRepairProposalRequest,
    ContentRevisionRepairProposalResponse,
)
from wilq.content.workflow.documents.revision_children import build_child_draft_revision_command
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionSection,
)
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


@pytest.mark.parametrize("review_status", ["unreviewed", "approved"])
def test_repair_owner_requires_recorded_human_needs_changes(review_status: str) -> None:
    revision = ContentDraftRevision.model_construct(
        revision_id="content_revision_bdo_1",
        work_item_id="content_work_item_bdo",
        content_digest="a" * 64,
        sections=[
            ContentDraftRevisionSection.model_construct(
                section_id="section_bdo_1",
                heading="Zakres obowiązku",
            )
        ],
        cta_blocks=[],
    )
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(
                id=revision.work_item_id,
                evidence_ids=[],
                source_connectors=[],
            )
        ),
        structured_generation=SimpleNamespace(
            structured_generation_result=SimpleNamespace(contract=None)
        ),
        revision_workspace=SimpleNamespace(
            latest_revision=revision,
            context_current=True,
            status=review_status,
            can_save=False,
        )
    )
    request = ContentCodexSectionProposalRequest(
        expected_base_digest=revision.content_digest,
        selected_section_ids=["section_bdo_1"],
        requested_by="wilku",
    )

    response = propose_content_section_revision(
        snapshot=cast(object, snapshot),
        base_revision_id=revision.revision_id,
        request=request,
        client=cast(object, None),
        workflow_store=cast(object, None),
        run_store=cast(object, None),
    )

    assert response.status == "blocked"
    assert response.revision is None
    assert response.blockers[0].code == "revision_not_ready_for_proposal"


def test_revision_repair_route_adapts_one_stable_component_without_prompt_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = APIRouter()
    app_for_test = FastAPI()
    observed: dict[str, object] = {}

    def snapshot_loader(work_item_id: str) -> SimpleNamespace:
        assert work_item_id == "content_work_item_bdo"
        return SimpleNamespace(revision_workspace=SimpleNamespace(latest_revision=None))

    def proposal(**kwargs: object) -> ContentCodexSectionProposalResponse:
        request = cast(ContentCodexSectionProposalRequest, kwargs["request"])
        observed["request"] = request
        return ContentCodexSectionProposalResponse(
            status="blocked",
            work_item_id="content_work_item_bdo",
            base_revision_id="content_revision_bdo_1",
            selected_section_headings=[],
            selected_cta_ids=request.selected_cta_ids,
            runtime=ContentCodexRuntimeTrace(status="not_started"),
            blockers=[
                ContentCodexSectionProposalBlocker(
                    code="revision_not_ready_for_proposal",
                    label="Ta wersja nie czeka na poprawki",
                    reason="Brakuje zapisanej decyzji człowieka.",
                    next_step="Zapisz decyzję review.",
                )
            ],
            safe_next_step="Zapisz decyzję review.",
        )

    monkeypatch.setattr(content_codex_proposal, "propose_content_section_revision", proposal)
    register_legacy_repair_test_route(router, snapshot_loader=snapshot_loader)
    content_codex_proposal.register_content_revision_repair_route(
        router,
        snapshot_loader=snapshot_loader,
    )
    app_for_test.include_router(router)

    response = TestClient(app_for_test).post(
        "/api/content/work-items/content_work_item_bdo/draft-revisions/"
        "content_revision_bdo_1/repair-proposal",
        json={
            "expected_base_digest": "a" * 64,
            "selected_section_ids": ["section_bdo_1"],
            "requested_by": "wilku",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    request = cast(ContentCodexSectionProposalRequest, observed["request"])
    assert request.selected_section_ids == ["section_bdo_1"]
    assert request.selected_section_headings == []
    assert "model_input" not in response.text
    assert "system_instruction" not in response.text


def test_revision_repair_route_uses_bounded_codex_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = APIRouter()
    timeouts: list[float] = []
    turn_results: list[CodexAppServerTurnResult] = []
    persisted_revision = ContentDraftRevision.model_construct(
        revision_id="content_revision_deadline",
        work_item_id="content_work_item_deadline",
        content_digest="d" * 64,
    )

    class _FakeClient:
        def __init__(self, *, timeout_seconds: float) -> None:
            timeouts.append(timeout_seconds)

        def run_structured_turn(self, _request: object) -> CodexAppServerTurnResult:
            result = CodexAppServerTurnResult(status="failed")
            turn_results.append(result)
            return result

    def proposal(**kwargs: object) -> ContentCodexSectionProposalResponse:
        client = cast(_FakeClient, kwargs["client"])
        result = client.run_structured_turn(object())
        assert isinstance(result, CodexAppServerTurnResult)
        assert result.status == "failed"
        return ContentCodexSectionProposalResponse(
            status="failed",
            work_item_id=persisted_revision.work_item_id,
            base_revision_id=persisted_revision.revision_id,
            selected_section_headings=["Sekcja naprawy"],
            runtime=ContentCodexRuntimeTrace(status="failed"),
            blockers=[
                ContentCodexSectionProposalBlocker(
                    code="runtime_failed",
                    label="Codex nie zakończył propozycji",
                    reason="Testowy failed turn.",
                    next_step="Uruchom nową propozycję.",
                )
            ],
            safe_next_step="Uruchom nową propozycję.",
        )

    monkeypatch.setattr(content_codex_proposal, "StdioCodexAppServerClient", _FakeClient)
    monkeypatch.setattr(content_codex_proposal, "propose_content_section_revision", proposal)
    monkeypatch.setattr(
        content_codex_proposal,
        "content_semantic_review_store",
        lambda: SimpleNamespace(for_revision=lambda *_args: None),
    )
    monkeypatch.setattr(content_codex_proposal, "content_workflow_store", lambda: object())
    monkeypatch.setattr(content_codex_proposal, "local_state_store", lambda: object())
    def snapshot_loader(_work_item_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            revision_workspace=SimpleNamespace(
                latest_revision=persisted_revision,
                status="needs_changes",
                context_current=True,
                can_save=True,
            ),
            planning_workspace=None,
        )
    register_legacy_repair_test_route(router, snapshot_loader=snapshot_loader)
    content_codex_proposal.register_content_revision_repair_route(
        router, snapshot_loader=snapshot_loader
    )

    request = ContentRevisionRepairProposalRequest(
        expected_base_digest="d" * 64,
        selected_section_ids=["section_deadline"],
        requested_by="wilku",
    )
    endpoint = router.routes[0].endpoint
    response = endpoint(
        work_item_id="content_work_item_deadline",
        base_revision_id="content_revision_deadline",
        request=request,
    )

    from wilq.content.drafts.section_repair_runtime_contract import (
        section_repair_timeout_seconds,
    )

    assert isinstance(response, ContentRevisionRepairProposalResponse)
    assert response.status == "failed"
    assert turn_results
    assert timeouts == [section_repair_timeout_seconds()]
    assert timeouts[0] > 120.0


def test_refresh_bound_repair_uses_binding_aware_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = APIRouter()
    app_for_test = FastAPI()
    revision = ContentDraftRevision.model_construct(
        revision_id="content_revision_editorial_1",
        work_item_id="content_work_item_editorial",
        content_digest="b" * 64,
        refresh_preparation_binding=SimpleNamespace(),
    )
    fallback = SimpleNamespace(revision_workspace=SimpleNamespace(latest_revision=revision))
    bound = SimpleNamespace(
        revision_workspace=SimpleNamespace(latest_revision=revision),
        planning_workspace=SimpleNamespace(
            proposal=SimpleNamespace(content_kind="editorial", service_card_id=None)
        ),
    )
    seen: dict[str, object] = {}

    def bound_snapshot(work_item_id: str) -> object:
        seen["bound_id"] = work_item_id
        return bound

    def planning_input(snapshot: object) -> None:
        seen["planning_snapshot"] = snapshot
        return None

    monkeypatch.setattr(
        content_workflow,
        "semantic_review_snapshot_for_work_item_or_404",
        bound_snapshot,
    )
    monkeypatch.setattr(content_codex_proposal, "_current_planning_input", planning_input)

    def proposal(**kwargs: object) -> ContentCodexSectionProposalResponse:
        seen["snapshot"] = kwargs["snapshot"]
        return ContentCodexSectionProposalResponse(
            status="blocked",
            work_item_id=revision.work_item_id,
            base_revision_id=revision.revision_id,
            selected_section_headings=[],
            runtime=ContentCodexRuntimeTrace(status="not_started"),
            blockers=[
                ContentCodexSectionProposalBlocker(
                    code="revision_not_ready_for_proposal",
                    label="Brak review",
                    reason="Testowa blokada.",
                    next_step="Zapisz review.",
                )
            ],
            safe_next_step="Zapisz review.",
        )

    monkeypatch.setattr(content_codex_proposal, "propose_content_section_revision", proposal)
    register_legacy_repair_test_route(router, snapshot_loader=lambda _work_item_id: fallback)
    content_codex_proposal.register_content_revision_repair_route(
        router,
        snapshot_loader=lambda _work_item_id: fallback,
    )
    app_for_test.include_router(router)

    response = TestClient(app_for_test).post(
        "/api/content/work-items/content_work_item_editorial/draft-revisions/"
        "content_revision_editorial_1/repair-proposal",
        json={
            "expected_base_digest": "b" * 64,
            "selected_section_ids": ["section_editorial_1"],
            "requested_by": "wilku",
        },
    )

    assert response.status_code == 200
    assert seen["bound_id"] == revision.work_item_id
    assert seen["snapshot"] is bound
    assert seen["planning_snapshot"] is bound


def test_editorial_null_service_builds_planning_input_but_service_does_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[object] = []

    monkeypatch.setattr(
        content_codex_proposal,
        "build_content_planning_input",
        lambda snapshot, *, service_card_id: seen.append((snapshot, service_card_id))
        or SimpleNamespace(blockers=[], planning_input="editorial-input"),
    )
    editorial = SimpleNamespace(
        planning_workspace=SimpleNamespace(
            proposal=SimpleNamespace(content_kind="editorial", service_card_id=None)
        )
    )
    service = SimpleNamespace(
        planning_workspace=SimpleNamespace(
            proposal=SimpleNamespace(content_kind="service", service_card_id=None)
        )
    )

    assert content_codex_proposal._current_planning_input(editorial) == "editorial-input"
    assert seen == [(editorial, None)]
    assert content_codex_proposal._current_planning_input(service) is None


def test_legacy_section_proposal_route_remains_retired() -> None:
    response = TestClient(app).post(
        "/api/content/work-items/content_work_item_retired/draft-revisions/"
        "content_revision_retired/codex-proposal",
        json={},
    )

    assert response.status_code == 404


def test_section_proposal_conflict_finishes_started_run_as_blocked_without_revision(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_store = LocalStateStore(tmp_path / "state.sqlite3")
    started = CodexRun(id="codex_section_conflict", status="started")
    run_store.save_codex_run(started)
    appended: list[object] = []

    class WorkflowStore:
        def append_draft_revision(self, command: object, *, completed_codex_run: CodexRun):
            appended.append(completed_codex_run)
            return SimpleNamespace(status="conflict", revision=None)

    monkeypatch.setattr(
        codex_section_proposal,
        "merge_selected_sections",
        lambda *_args: [],
    )
    monkeypatch.setattr(
        codex_section_proposal,
        "merge_selected_cta_blocks",
        lambda *_args: [],
    )
    monkeypatch.setattr(
        codex_section_proposal,
        "build_child_draft_revision_command",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        codex_section_proposal,
        "_proposal_metadata",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        codex_section_proposal,
        "build_blocker",
        lambda _model, **kwargs: SimpleNamespace(code=kwargs["code"]),
    )
    monkeypatch.setattr(
        codex_section_proposal,
        "_blocked_response",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    base_revision = SimpleNamespace(
        planning_digest="planning", revision_id="base", work_item_id="work"
    )
    inputs = SimpleNamespace(
        base_revision=base_revision,
        selected_headings=["Zakres"],
        selected_cta_ids=[],
        contract=SimpleNamespace(),
    )
    runtime = SimpleNamespace(
        run=started,
        output=SimpleNamespace(),
        trace=SimpleNamespace(),
    )
    response = codex_section_proposal._persist_proposal(
        snapshot=SimpleNamespace(),
        request=SimpleNamespace(requested_by="wilku"),
        inputs=inputs,
        runtime=runtime,
        quality_review=SimpleNamespace(),
        workflow_store=WorkflowStore(),
        run_store=run_store,
    )

    assert response.status == "conflict"
    assert response.run.status == "blocked"
    assert len(appended) == 1
    assert appended[0].status == "completed"
    assert run_store.list_codex_runs()[0].status == "blocked"


def test_child_section_proposal_preserves_research_packet_binding() -> None:
    base_revision = ContentDraftRevision.model_construct(
        revision_id="content_revision_packet_parent",
        work_item_id="content_work_item_packet",
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id="draft_package_packet",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        research_packet_id="content_research_packet_parent",
        research_packet_digest="d" * 64,
        title="Tytuł wersji bazowej",
        final_canonical_url="https://ekologus.pl/test-packet-binding/",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown="Treść wersji bazowej.",
                evidence_ids=["evidence_packet"],
            )
        ],
        cta_blocks=[],
    )
    metadata = ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_run_packet_binding",
        selected_section_headings=["Zakres"],
        section_lineage=[
            ContentDraftRevisionProposalSectionLineage(
                heading="Zakres",
                evidence_ids=["evidence_packet"],
            )
        ],
        quality_verdict="reviewable",
        research_packet_id=base_revision.research_packet_id,
        research_packet_digest=base_revision.research_packet_digest,
    )

    child_command = build_child_draft_revision_command(
        base_revision,
        sections=base_revision.sections,
        proposal_metadata=metadata,
        created_by="wilku",
    )

    assert isinstance(child_command, ContentDraftRevisionAppendCommand)
    assert child_command.research_packet_id == base_revision.research_packet_id
    assert child_command.research_packet_digest == base_revision.research_packet_digest

    mismatched_metadata = metadata.model_copy(update={"research_packet_digest": "e" * 64})
    with pytest.raises(
        ValueError,
        match="Draft revision packet binding must match its proposal metadata\\.",
    ):
        build_child_draft_revision_command(
            base_revision,
            sections=base_revision.sections,
            proposal_metadata=mismatched_metadata,
            created_by="wilku",
        )
