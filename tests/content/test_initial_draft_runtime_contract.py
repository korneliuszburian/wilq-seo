"""One bounded deadline contract for the initial-draft Codex run.

Evidence: a live Operat 12-section initial draft with six assurance turns
exceeded the previous 3600-second deadline (``initial_draft_timeout`` /
``assurance_turn_timeouterror``). The effective deadline must keep real margin
above that observed need and stay env-configurable, for both the queue claim
default and the run-status check.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnBlocker,
    CodexAppServerTurnResult,
)
from wilq.content.drafts import initial_draft_queue
from wilq.content.drafts.initial_draft_queue import _DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS
from wilq.content.drafts.initial_draft_run import effective_initial_draft_deadline
from wilq.schemas import CodexRun

_OBSERVED_TIMEOUT_SECONDS = 3600.0


def _started() -> datetime:
    return datetime(2026, 9, 19, 23, 0, tzinfo=UTC)


def test_queue_deadline_covers_observed_full_draft() -> None:
    assert (
        _DEFAULT_INITIAL_DRAFT_TIMEOUT_SECONDS >= _OBSERVED_TIMEOUT_SECONDS * 1.4
    ), "the default draft deadline must keep real margin above the observed need"


def test_effective_deadline_uses_the_shared_default() -> None:
    started = _started()
    run = CodexRun.model_construct(id="run_contract", started_at=started, deadline_at=None)

    deadline = effective_initial_draft_deadline(run)

    assert (deadline - started).total_seconds() >= _OBSERVED_TIMEOUT_SECONDS * 1.4


def test_effective_deadline_is_env_overridable(monkeypatch) -> None:
    started = _started()
    run = CodexRun.model_construct(id="run_contract", started_at=started, deadline_at=None)
    monkeypatch.setenv("WILQ_INITIAL_DRAFT_TIMEOUT_SECONDS", "4000")

    deadline = effective_initial_draft_deadline(run)

    assert (deadline - started).total_seconds() == 4000.0


def test_initial_draft_assurance_turn_uses_bounded_remaining_deadline(monkeypatch) -> None:
    now = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
    snapshot = SimpleNamespace(
        planning_workspace=SimpleNamespace(
            proposal=SimpleNamespace(
                proposal_id="proposal-1",
                planning_digest="a" * 64,
                planning_input_digest="b" * 64,
            )
        ),
        revision_workspace=SimpleNamespace(latest_revision=None),
    )
    context_digest = initial_draft_queue.snapshot_initial_draft_context_digest(
        snapshot, snapshot.planning_workspace.proposal
    )
    run = CodexRun.model_construct(
        id="run-1",
        status="started",
        started_at=now,
        deadline_at=now.replace(hour=13),
        initial_draft_context_digest=context_digest,
    )
    runs = [run]
    captured_timeouts: list[float] = []

    class _CapturingClient:
        def __init__(self, *, timeout_seconds: float) -> None:
            captured_timeouts.append(timeout_seconds)

        def run_structured_turn(
            self, _request: CodexAppServerStructuredTurnRequest
        ) -> CodexAppServerTurnResult:
            return CodexAppServerTurnResult(
                status="failed",
                blockers=(
                    CodexAppServerTurnBlocker(
                        code="codex_timeout",
                        message="The bounded turn deadline expired.",
                    ),
                ),
            )

    monkeypatch.setenv("WILQ_SECTION_REPAIR_TIMEOUT_SECONDS", "17")
    monkeypatch.setattr(initial_draft_queue, "utc_now", lambda: now)
    monkeypatch.setattr(
        initial_draft_queue,
        "local_state_store",
        lambda: SimpleNamespace(list_codex_runs=lambda: runs),
    )
    monkeypatch.setattr(initial_draft_queue, "StdioCodexAppServerClient", _CapturingClient)
    request = CodexAppServerStructuredTurnRequest(
        instruction="Run one assurance turn.",
        application_context=json.dumps({"operation": "assure_regulatory_content_draft"}),
        untrusted_context="{}",
        output_schema={"type": "object"},
    )
    client = initial_draft_queue._InitialDraftDeadlineClient(
        object(), "run-1", lambda _work_item_id: snapshot, "work-item-1"
    )

    result = client.run_structured_turn(request)
    runs[0] = run.model_copy(update={"deadline_at": now.replace(hour=12, minute=0, second=3)})
    client.run_structured_turn(request)

    assert result.status == "failed"
    assert result.blockers[0].code == "codex_timeout"
    assert captured_timeouts == [17.0, 3.0]
