"""One bounded deadline contract for the initial-draft Codex run.

Evidence: a live Operat 12-section initial draft with six assurance turns
exceeded the previous 3600-second deadline (``initial_draft_timeout`` /
``assurance_turn_timeouterror``). The effective deadline must keep real margin
above that observed need and stay env-configurable, for both the queue claim
default and the run-status check.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
