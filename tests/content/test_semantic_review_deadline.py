from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from types import SimpleNamespace

import pytest

from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality import semantic_review_service
from wilq.content.quality.semantic_review_contracts import (
    CONTENT_SEMANTIC_DIMENSIONS,
    ContentSemanticDimensionAssessment,
    ContentSemanticReview,
    ContentSemanticReviewBlocker,
)
from wilq.content.quality.semantic_review_service import _SemanticInputs
from wilq.content.quality.semantic_review_store import (
    ContentSemanticReviewStore,
    SemanticReviewDeadlineExpired,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.runtime.codex_run_lifecycle import (
    finish_codex_run,
    save_terminal_codex_run,
    transition_codex_run_if_status,
)
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


@pytest.mark.parametrize("status", ["completed", "failed", "blocked"])
def test_finish_codex_run_persists_terminal_state(tmp_path, status: str) -> None:
    store = LocalStateStore(tmp_path / f"{status}.sqlite3")
    started = CodexRun(id=f"codex_finish_{status}", status="started")
    store.save_codex_run(started)

    finished = finish_codex_run(store, started, status=status, error=f"err_{status}")

    assert finished.status == status
    assert finished.completed_at is not None
    assert finished.error == f"err_{status}"
    assert store.list_codex_runs() == [finished]


def test_save_terminal_codex_run_overwrites_existing_terminal_state(tmp_path) -> None:
    store = LocalStateStore(tmp_path / "unconditional.sqlite3")
    started = CodexRun(id="codex_unconditional", status="started")
    store.save_codex_run(started)
    first = save_terminal_codex_run(store, started, status="completed")

    overwritten = save_terminal_codex_run(
        store,
        first,
        status="blocked",
        error="retry_blocked",
    )

    assert overwritten.status == "blocked"
    assert overwritten.error == "retry_blocked"
    assert store.list_codex_runs() == [overwritten]


def test_expired_started_run_cannot_commit_review(tmp_path) -> None:
    now = datetime.now(UTC)
    db = tmp_path / "state.sqlite3"
    run_store = LocalStateStore(db)
    review_store = ContentSemanticReviewStore(db)
    started = CodexRun(
        id="codex_content_semantic_review_expired_commit",
        hook="content_semantic_review",
        source="wilq_api",
        status="started",
        started_at=now - timedelta(seconds=2),
        deadline_at=now - timedelta(seconds=1),
        planning_input_digest="b" * 64,
        used_endpoints=[
            "/api/content/work-items/work/draft-revisions/"
            "revision/semantic-review"
        ],
    )
    run_store.save_codex_run(started)
    dimensions = [
        ContentSemanticDimensionAssessment(
            dimension=dimension,
            status="strong",
            reason="OK",
            affected_targets=["whole_document"],
        )
        for dimension in CONTENT_SEMANTIC_DIMENSIONS
    ]
    review = ContentSemanticReview(
        review_id="content_semantic_review_expired_commit",
        work_item_id="work",
        revision_id="revision",
        revision_digest="a" * 64,
        codex_run_id=started.id,
        status="reviewable",
        dimensions=dimensions,
        findings=[],
        requested_by="reviewer",
        created_at=now,
        safe_next_step="Przekaż do review człowieka.",
    )
    completed = started.model_copy(
        update={"status": "completed", "completed_at": now, "error": None}
    )

    with pytest.raises(SemanticReviewDeadlineExpired):
        review_store.save_generated(review, completed)
    assert review_store.for_revision("work", "revision", "a" * 64) is None


def test_parallel_claims_share_one_semantic_run(tmp_path) -> None:
    store = ContentSemanticReviewStore(tmp_path / "state.sqlite3")
    barrier = Barrier(2)
    endpoint = "/api/content/work-items/work/draft-revisions/revision/semantic-review"

    def claim():
        barrier.wait()
        return store.claim_run(
            work_item_id="work",
            revision_id="revision",
            revision_digest="a" * 64,
            endpoint=endpoint,
            evidence_ids=["ev"],
            planning_input_digest="b" * 64,
            timeout_seconds=30,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _item: claim(), range(2)))

    assert len({claim.run.id for claim in claims if claim.run is not None}) == 1
    assert sum(claim.newly_claimed for claim in claims) == 1
    assert len(
        [
            run
            for run in LocalStateStore(store.path).list_codex_runs()
            if run.status == "started"
        ]
    ) == 1


def test_claim_terminalizes_legacy_started_run_without_deadline(tmp_path) -> None:
    db = tmp_path / "state.sqlite3"
    run_store = LocalStateStore(db)
    review_store = ContentSemanticReviewStore(db)
    endpoint = "/api/content/work-items/work/draft-revisions/revision/semantic-review"
    legacy = CodexRun(
        id="codex_content_semantic_review_legacy",
        hook="content_semantic_review",
        source="wilq_api",
        status="started",
        started_at=datetime.now(UTC) - timedelta(seconds=301),
        planning_input_digest="b" * 64,
        used_endpoints=[endpoint],
        evidence_ids=["ev"],
    )
    run_store.save_codex_run(legacy)

    claim = review_store.claim_run(
        work_item_id="work",
        revision_id="revision",
        revision_digest="a" * 64,
        endpoint=endpoint,
        evidence_ids=["ev"],
        planning_input_digest="b" * 64,
        timeout_seconds=180,
    )

    assert claim.newly_claimed is True
    assert claim.run is not None
    assert claim.run.id != legacy.id
    persisted = next(
        run for run in run_store.list_codex_runs() if run.id == legacy.id
    )
    assert persisted.status == "failed"
    assert persisted.error == "semantic_review_timeout"


def test_legacy_deadline_uses_one_conservative_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WILQ_SEMANTIC_REVIEW_CODEX_TIMEOUT_SECONDS", "211")
    db = tmp_path / "state.sqlite3"
    run_store = LocalStateStore(db)
    review_store = ContentSemanticReviewStore(db)
    endpoint = "/api/content/work-items/work/draft-revisions/revision/semantic-review"
    legacy = CodexRun(
        id="codex_content_semantic_review_legacy_211",
        hook="content_semantic_review",
        source="wilq_api",
        status="started",
        started_at=datetime.now(UTC) - timedelta(seconds=190),
        planning_input_digest="b" * 64,
        used_endpoints=[endpoint],
    )
    run_store.save_codex_run(legacy)

    claim = review_store.claim_run(
        work_item_id="work",
        revision_id="revision",
        revision_digest="a" * 64,
        endpoint=endpoint,
        evidence_ids=["ev"],
        planning_input_digest="b" * 64,
        timeout_seconds=211,
    )

    assert claim.newly_claimed is True
    persisted = next(
        run for run in run_store.list_codex_runs() if run.id == legacy.id
    )
    assert persisted.status == "failed"
    assert persisted.error == "semantic_review_timeout"


def test_commit_timeout_preserves_source_code_in_run_error() -> None:
    saved = []

    class Store:
        def save_codex_run(self, run):
            saved.append(run)
            return run

    now = datetime.now(UTC)
    run = CodexRun(
        id="codex_content_semantic_review_timeout_source",
        hook="content_semantic_review",
        status="started",
        started_at=now,
    )
    revision = ContentDraftRevision.model_construct(
        work_item_id="work",
        revision_id="revision",
        content_digest="a" * 64,
    )
    snapshot = SimpleNamespace(preflight=SimpleNamespace(item=SimpleNamespace(id="work")))
    blocker = ContentSemanticReviewBlocker(
        code="runtime_failed",
        label="Timeout",
        reason="Timeout.",
        next_step="Retry.",
        source_codes=["semantic_review_timeout"],
    )

    semantic_review_service._finish_with_blocker(
        snapshot,
        revision,
        run,
        ContentCodexRuntimeTrace(status="failed"),
        blocker,
        Store(),
        response_status="failed",
        run_status="failed",
    )

    assert saved[0].error == "runtime_failed:semantic_review_timeout"
