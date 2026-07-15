from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from wilq.content.workflow.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store import ContentWorkflowStore
from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore


def test_same_content_from_a_different_codex_run_conflicts(tmp_path: Path) -> None:
    path = tmp_path / "wilq.sqlite3"
    workflow_store = ContentWorkflowStore(path)
    run_store = LocalStateStore(path)
    base = workflow_store.append_draft_revision(_append_command(body="Wersja bazowa."))
    assert base.revision is not None

    first_run = _started_run("codex_run_first")
    run_store.save_codex_run(first_run)
    first = workflow_store.append_draft_revision(
        _append_command(base_id=base.revision.revision_id, run_id=first_run.id),
        completed_codex_run=_completed_run(first_run),
    )
    assert first.status == "created"
    assert first.revision is not None

    second_run = _started_run("codex_run_second")
    run_store.save_codex_run(second_run)
    second = workflow_store.append_draft_revision(
        _append_command(base_id=base.revision.revision_id, run_id=second_run.id),
        completed_codex_run=_completed_run(second_run),
    )

    assert second.status == "conflict"
    assert second.conflict is not None
    assert second.conflict.code == "stale_base"
    state = workflow_store.load_draft_revision_state("content_work_item_atomic")
    assert state.latest_revision == first.revision
    runs = {run.id: run for run in run_store.list_codex_runs()}
    assert runs[first_run.id].status == "completed"
    assert runs[second_run.id].status == "started"


def test_codex_completion_failure_rolls_back_child_revision(tmp_path: Path) -> None:
    path = tmp_path / "wilq.sqlite3"
    workflow_store = ContentWorkflowStore(path)
    run_store = LocalStateStore(path)
    base = workflow_store.append_draft_revision(_append_command(body="Wersja bazowa."))
    assert base.revision is not None
    started_run = _started_run("codex_run_atomic_failure")
    run_store.save_codex_run(started_run)
    _reject_codex_completion(path)

    with pytest.raises(sqlite3.IntegrityError, match="synthetic completion failure"):
        workflow_store.append_draft_revision(
            _append_command(base_id=base.revision.revision_id, run_id=started_run.id),
            completed_codex_run=_completed_run(started_run),
        )

    state = workflow_store.load_draft_revision_state("content_work_item_atomic")
    assert state.latest_revision == base.revision
    stored_run = next(run for run in run_store.list_codex_runs() if run.id == started_run.id)
    assert stored_run.status == "started"


def _append_command(
    *,
    body: str = "Propozycja Codexa.",
    base_id: str | None = None,
    run_id: str | None = None,
) -> ContentDraftRevisionAppendCommand:
    metadata = None if run_id is None else _proposal_metadata(run_id)
    return ContentDraftRevisionAppendCommand(
        work_item_id="content_work_item_atomic",
        base_revision_id=base_id,
        draft_package_id="draft_package_atomic",
        draft_package_digest="d" * 64,
        final_canonical_url="https://ekologus.pl/test-atomiczny/",
        title="Test atomowego szkicu",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown=body,
                evidence_ids=["evidence_atomic"],
            )
        ],
        proposal_metadata=metadata,
        created_by="wilku",
    )


def _proposal_metadata(run_id: str) -> ContentDraftRevisionProposalMetadata:
    return ContentDraftRevisionProposalMetadata(
        codex_run_id=run_id,
        selected_section_headings=["Zakres"],
        section_lineage=[
            ContentDraftRevisionProposalSectionLineage(
                heading="Zakres",
                evidence_ids=["evidence_atomic"],
            )
        ],
        quality_verdict="needs_changes",
        quality_finding_codes=["semantic_review_required"],
    )


def _started_run(run_id: str) -> CodexRun:
    return CodexRun(
        id=run_id,
        skill="wilq-content-operator",
        hook="content_revision_proposal",
        source="wilq_api",
        status="started",
        used_endpoints=["/api/content/work-items/test/codex-proposal"],
        evidence_ids=["evidence_atomic"],
    )


def _completed_run(started_run: CodexRun) -> CodexRun:
    return started_run.model_copy(update={"status": "completed", "completed_at": utc_now()})


def _reject_codex_completion(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_codex_completion
            BEFORE UPDATE OF payload_json ON codex_runs
            WHEN OLD.id = 'codex_run_atomic_failure'
            BEGIN
              SELECT RAISE(ABORT, 'synthetic completion failure');
            END
            """
        )
