from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality import semantic_review_service
from wilq.content.quality.semantic_review_service import _SemanticInputs
from wilq.content.quality.semantic_run_state import transition_codex_run_if_status
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import ContentDraftRevision
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


def test_terminal_queued_run_cannot_be_resurrected(tmp_path) -> None:
    now = datetime.now(UTC)
    terminal = CodexRun(
        id="codex_content_semantic_review_expired",
        hook="content_semantic_review",
        source="wilq_api",
        status="failed",
        started_at=now - timedelta(seconds=10),
        deadline_at=now - timedelta(seconds=1),
        completed_at=now,
        error="semantic_review_timeout",
        planning_input_digest="b" * 64,
        used_endpoints=[
            "/api/content/work-items/work/draft-revisions/"
            "revision/semantic-review"
        ],
        evidence_ids=["ev"],
    )
    store = LocalStateStore(tmp_path / "state.sqlite3")
    store.save_codex_run(terminal)
    revision = ContentDraftRevision.model_construct(
        work_item_id="work",
        revision_id="revision",
        planning_input_digest="b" * 64,
    )

    with pytest.raises(ValueError, match="no longer executable"):
        semantic_review_service._start_run(
            _SemanticInputs(
                revision=revision,
                planning_input=ContentPlanningInput.model_construct(),
                proposal=ContentPlanningProposal.model_construct(),
            ),
            store,
            run_id=terminal.id,
        )

    persisted = next(run for run in store.list_codex_runs() if run.id == terminal.id)
    assert persisted == terminal


def test_terminal_transition_cannot_overwrite_completed_run(tmp_path) -> None:
    now = datetime.now(UTC)
    active = CodexRun(
        id="codex_content_semantic_review_cas",
        hook="content_semantic_review",
        status="started",
        started_at=now,
        deadline_at=now + timedelta(seconds=30),
    )
    store = LocalStateStore(tmp_path / "state.sqlite3")
    store.save_codex_run(active)
    completed = active.model_copy(update={"status": "completed", "completed_at": now})

    assert transition_codex_run_if_status(store, completed) == completed
    failed = completed.model_copy(
        update={"status": "failed", "error": "semantic_review_timeout"}
    )
    assert transition_codex_run_if_status(store, failed) is None
    assert store.list_codex_runs()[0] == completed
