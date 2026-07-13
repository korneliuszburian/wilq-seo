"""Focused tests for the narrow daily-check runtime seam."""

from __future__ import annotations

from types import SimpleNamespace

from wilq.briefing import daily_runtime


def test_daily_check_runtime_does_not_build_the_marketing_brief(monkeypatch) -> None:
    base = SimpleNamespace(connectors=["connector"], tactical_queue="queue", actions=["action"])
    command_center = "command-center"

    monkeypatch.setattr(daily_runtime, "build_daily_runtime_base", lambda **_: base)
    monkeypatch.setattr(
        daily_runtime,
        "build_daily_command_center",
        lambda **_: command_center,
    )
    monkeypatch.setattr(
        daily_runtime,
        "build_daily_marketing_brief",
        lambda **_: (_ for _ in ()).throw(AssertionError("marketing brief is out of scope")),
    )

    runtime = daily_runtime.build_daily_check_runtime(use_cache=False)

    assert runtime.connectors == ["connector"]
    assert runtime.command_center == "command-center"


def test_daily_check_prewarm_state_is_explicit_and_resettable() -> None:
    daily_runtime.finish_daily_check_prewarm()
    assert daily_runtime.daily_check_prewarm_in_progress() is False


def test_daily_check_returns_typed_blocker_during_prewarm(monkeypatch) -> None:
    from wilq.briefing import daily_check
    from wilq.briefing.daily_check import build_daily_check

    monkeypatch.setattr(daily_check, "daily_check_prewarm_in_progress", lambda: True)

    result = build_daily_check()

    assert result.status == "blocked"
    assert result.blocked_recommendations[0].id == "daily_check_runtime_prewarm"
    assert result.blocked_recommendations[0].evidence_ids == []

    daily_runtime.start_daily_check_prewarm()
    assert daily_runtime.daily_check_prewarm_in_progress() is True

    daily_runtime.finish_daily_check_prewarm()
    assert daily_runtime.daily_check_prewarm_in_progress() is False
