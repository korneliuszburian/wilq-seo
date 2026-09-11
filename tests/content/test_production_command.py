from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_production_command as command_route
from apps.api.wilq_api.main import app
from tests.content.initial_draft_authority_fakes import draft_review, draft_revision
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexSectionProposalResponse,
)
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftResponse
from wilq.content.workflow.documents.revisions import ContentDraftRevisionState
from wilq.content.workflow.production_command import (
    ContentProductionCommand,
    ContentProductionInitialCommand,
    ContentProductionRepairCommand,
)

WORK_ITEM_ID = "content_work_item_command"
REVISION_DIGEST = "a" * 64


@dataclass
class _Journal:
    state: ContentDraftRevisionState

    def load_draft_revision_state(self, _work_item_id: str) -> ContentDraftRevisionState:
        return self.state


def _initial_request() -> ContentProductionInitialCommand:
    return ContentProductionInitialCommand(
        expected_proposal_id="content_planning_proposal_command",
        expected_planning_digest="b" * 64,
        expected_planning_input_digest="c" * 64,
        requested_by="wilku",
    )


def test_approved_revision_is_reused_without_initial_executor() -> None:
    revision = draft_revision(
        WORK_ITEM_ID,
        "revision-approved",
        REVISION_DIGEST,
    ).model_copy(
        update={
            "planning_digest": "b" * 64,
            "planning_input_digest": "c" * 64,
        }
    )
    journal = _Journal(
        ContentDraftRevisionState(
            status="approved",
            latest_revision=revision,
            latest_review=draft_review(revision),
            revision_count=1,
        )
    )
    calls = 0

    def initial_executor(_work_item_id: str, _request: object) -> ContentInitialDraftResponse:
        nonlocal calls
        calls += 1
        raise AssertionError("approved revision must not reach generation")

    command = ContentProductionCommand(
        journal=journal,
        initial_executor=initial_executor,
        repair_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("repair must not run")
        ),
    )

    result = command.run(WORK_ITEM_ID, _initial_request())

    assert result.status == "reused"
    assert result.revision == revision
    assert calls == 0


def test_needs_changes_creates_exact_child_and_second_call_does_not_generate() -> None:
    base = draft_revision(WORK_ITEM_ID, "revision-needs-changes", REVISION_DIGEST)
    journal = _Journal(
        ContentDraftRevisionState(
            status="needs_changes",
            latest_revision=base,
            latest_review=draft_review(base, decision="needs_changes"),
            revision_count=1,
        )
    )
    calls = 0
    child = base.model_copy(
        update={
            "revision_id": "revision-child",
            "revision_number": 2,
            "base_revision_id": base.revision_id,
            "content_digest": "d" * 64,
        }
    )

    def repair_executor(
        _work_item_id: str,
        _request: object,
    ) -> ContentCodexSectionProposalResponse:
        nonlocal calls
        calls += 1
        journal.state = ContentDraftRevisionState(
            status="unreviewed",
            latest_revision=child,
            latest_review=None,
            revision_count=2,
        )
        return ContentCodexSectionProposalResponse.model_construct(
            status="created",
            run_id="codex-repair-run",
            work_item_id=WORK_ITEM_ID,
            base_revision_id=base.revision_id,
            selected_section_headings=["Zakres"],
            revision=child,
            runtime={"status": "completed"},
            safe_next_step="Przeczytaj child revision.",
        )

    command = ContentProductionCommand(
        journal=journal,
        initial_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("initial must not run in repair mode")
        ),
        repair_executor=repair_executor,
    )
    request = ContentProductionRepairCommand(
        expected_base_digest=base.content_digest,
        selected_section_ids=["section_scope"],
        requested_by="wilku",
    )

    created = command.run(WORK_ITEM_ID, request)
    repeated = command.run(WORK_ITEM_ID, request)

    assert created.status == "created"
    assert created.revision is not None
    assert created.revision.base_revision_id == base.revision_id
    assert repeated.status == "blocked"
    assert repeated.blockers[0].code == "repair_requires_needs_changes"
    assert calls == 1


def test_missing_revision_blocks_repair_before_executor() -> None:
    journal = _Journal(
        ContentDraftRevisionState(
            status="empty",
            latest_revision=None,
            latest_review=None,
            revision_count=0,
        )
    )
    command = ContentProductionCommand(
        journal=journal,
        initial_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("repair preflight must stop before initial executor")
        ),
        repair_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("repair preflight must stop before model")
        ),
    )

    result = command.run(
        WORK_ITEM_ID,
        ContentProductionRepairCommand(
            expected_base_digest=REVISION_DIGEST,
            selected_section_ids=["section_scope"],
            requested_by="wilku",
        ),
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "repair_requires_revision"


def test_repair_claim_prevents_a_second_model_turn() -> None:
    base = draft_revision(WORK_ITEM_ID, "revision-claim", REVISION_DIGEST)
    journal = _Journal(
        ContentDraftRevisionState(
            status="needs_changes",
            latest_revision=base,
            latest_review=draft_review(base, decision="needs_changes"),
            revision_count=1,
        )
    )
    command = ContentProductionCommand(
        journal=journal,
        initial_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("initial must not run")
        ),
        repair_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("claim must stop repair before model")
        ),
        repair_claim_acquire=lambda *_args: False,
        repair_claim_release=lambda *_args: None,
    )

    result = command.run(
        WORK_ITEM_ID,
        ContentProductionRepairCommand(
            expected_base_digest=REVISION_DIGEST,
            selected_section_ids=["section_scope"],
            requested_by="wilku",
        ),
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "repair_claim_unavailable"


def test_rejected_review_can_start_exact_repair() -> None:
    base = draft_revision(WORK_ITEM_ID, "revision-rejected", REVISION_DIGEST)
    journal = _Journal(
        ContentDraftRevisionState(
            status="rejected",
            latest_revision=base,
            latest_review=draft_review(base, decision="rejected"),
            revision_count=1,
        )
    )
    child = base.model_copy(
        update={
            "revision_id": "revision-rejected-child",
            "revision_number": 2,
            "base_revision_id": base.revision_id,
            "content_digest": "e" * 64,
        }
    )
    command = ContentProductionCommand(
        journal=journal,
        initial_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("initial must not run")
        ),
        repair_executor=lambda *_args: ContentCodexSectionProposalResponse.model_construct(
            status="created",
            run_id="rejected-repair-run",
            work_item_id=WORK_ITEM_ID,
            base_revision_id=base.revision_id,
            selected_section_headings=["Zakres"],
            revision=child,
            runtime={"status": "completed"},
            safe_next_step="Przeczytaj child revision.",
        ),
    )

    result = command.run(
        WORK_ITEM_ID,
        ContentProductionRepairCommand(
            expected_base_digest=REVISION_DIGEST,
            selected_section_ids=["section_scope"],
            requested_by="wilku",
        ),
    )

    assert result.status == "created"
    assert result.revision is not None
    assert result.revision.base_revision_id == base.revision_id


def test_repair_digest_mismatch_blocks_before_model() -> None:
    base = draft_revision(WORK_ITEM_ID, "revision-digest", REVISION_DIGEST)
    journal = _Journal(
        ContentDraftRevisionState(
            status="needs_changes",
            latest_revision=base,
            latest_review=draft_review(base, decision="needs_changes"),
            revision_count=1,
        )
    )
    command = ContentProductionCommand(
        journal=journal,
        initial_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("initial must not run")
        ),
        repair_executor=lambda *_args: (_ for _ in ()).throw(
            AssertionError("digest mismatch must stop before model")
        ),
    )

    result = command.run(
        WORK_ITEM_ID,
        ContentProductionRepairCommand(
            expected_base_digest="f" * 64,
            selected_section_ids=["section_scope"],
            requested_by="wilku",
        ),
    )

    assert result.status == "blocked"
    assert result.blockers[0].code == "repair_base_digest_mismatch"


def test_production_command_rejects_invalid_path_without_echo() -> None:
    response = TestClient(app).post(
        "/api/content/work-items/INVALID/production-command",
        json={"operation": "initial"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "production_command_request_invalid"}


def test_production_command_route_reuses_approved_revision_without_model(
    monkeypatch,
) -> None:
    revision = draft_revision(
        WORK_ITEM_ID,
        "route-approved",
        REVISION_DIGEST,
    ).model_copy(
        update={
            "planning_digest": "b" * 64,
            "planning_input_digest": "c" * 64,
        }
    )
    journal = _Journal(
        ContentDraftRevisionState(
            status="approved",
            latest_revision=revision,
            latest_review=draft_review(revision),
            revision_count=1,
        )
    )
    monkeypatch.setattr(command_route, "content_workflow_store", lambda: journal)
    monkeypatch.setattr(
        command_route,
        "_submit_initial_draft",
        lambda *_args: (_ for _ in ()).throw(AssertionError("reuse reached model")),
    )

    response = TestClient(app).post(
        f"/api/content/work-items/{WORK_ITEM_ID}/production-command",
        json=_initial_request().model_dump(mode="json"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "reused"
    assert response.json()["revision"]["revision_id"] == revision.revision_id


def test_production_command_route_repair_is_single_child_attempt(monkeypatch) -> None:
    base = draft_revision(WORK_ITEM_ID, "route-needs-changes", REVISION_DIGEST)
    child = base.model_copy(
        update={
            "revision_id": "route-child",
            "revision_number": 2,
            "base_revision_id": base.revision_id,
            "content_digest": "f" * 64,
        }
    )
    journal = _Journal(
        ContentDraftRevisionState(
            status="needs_changes",
            latest_revision=base,
            latest_review=draft_review(base, decision="needs_changes"),
            revision_count=1,
        )
    )
    calls = 0

    def fake_repair_executor(*_args):
        nonlocal calls
        calls += 1
        journal.state = ContentDraftRevisionState(
            status="unreviewed",
            latest_revision=child,
            latest_review=None,
            revision_count=2,
        )
        return ContentCodexSectionProposalResponse.model_construct(
            status="created",
            run_id="route-repair-run",
            work_item_id=WORK_ITEM_ID,
            base_revision_id=base.revision_id,
            selected_section_headings=["Zakres"],
            revision=child,
            runtime={"status": "completed"},
            safe_next_step="Przeczytaj child revision.",
        )

    monkeypatch.setattr(command_route, "content_workflow_store", lambda: journal)
    monkeypatch.setattr(command_route, "_repair_executor", fake_repair_executor)
    payload = {
        "operation": "repair",
        "expected_base_digest": base.content_digest,
        "selected_section_ids": ["section_scope"],
        "requested_by": "wilku",
    }

    client = TestClient(app)
    created = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/production-command",
        json=payload,
    )
    repeated = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/production-command",
        json=payload,
    )

    assert created.status_code == 201
    assert created.json()["revision"]["base_revision_id"] == base.revision_id
    assert repeated.status_code == 409
    assert repeated.json()["blockers"][0]["code"] == "repair_requires_needs_changes"
    assert calls == 1
