from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_codex_proposal, content_workflow
from wilq.content.drafts import codex_section_proposal
from wilq.content.drafts.codex_section_proposal import propose_content_section_revision
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexRuntimeTrace,
    ContentCodexSectionProposalBlocker,
    ContentCodexSectionProposalRequest,
    ContentCodexSectionProposalResponse,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
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
