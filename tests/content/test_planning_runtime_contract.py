"""Focused contract for the bounded planning Codex deadline.

Evidence for the floor below: a live BDO editorial planning turn on
``gpt-5.6-terra`` at ``max`` effort completed in 613.4 seconds and returned a
valid 9-section plan (12 KB). A default deadline of 300 seconds therefore
guaranteed a typed ``codex_timeout`` for real inventory instead of a plan. The
durable stale window must stay aligned to the same deadline so a slow worker is
never replaced while a legitimate turn is still running.
"""

from __future__ import annotations

from wilq.content.planning.runtime_contract import (
    DEFAULT_PLANNING_CODEX_TIMEOUT_SECONDS,
    PLANNING_JOB_STALE_GRACE_SECONDS,
    planning_codex_timeout_seconds,
    planning_job_stale_after_seconds,
)

_OBSERVED_FULL_TURN_SECONDS = 613.4


def test_default_deadline_covers_observed_full_planning_turn() -> None:
    assert (
        DEFAULT_PLANNING_CODEX_TIMEOUT_SECONDS >= _OBSERVED_FULL_TURN_SECONDS * 1.3
    ), "the default planning deadline must keep real margin above a full turn"


def test_configured_deadline_and_stale_window_share_one_contract(monkeypatch) -> None:
    monkeypatch.setenv("WILQ_PLANNING_CODEX_TIMEOUT_SECONDS", "123")
    assert planning_codex_timeout_seconds() == 123.0
    assert planning_job_stale_after_seconds() == 123.0 + PLANNING_JOB_STALE_GRACE_SECONDS


def test_invalid_configured_deadline_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.setenv("WILQ_PLANNING_CODEX_TIMEOUT_SECONDS", "not-a-number")
    assert planning_codex_timeout_seconds() == DEFAULT_PLANNING_CODEX_TIMEOUT_SECONDS
