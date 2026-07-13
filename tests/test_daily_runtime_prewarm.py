"""Contract tests for the non-blocking daily runtime prewarm."""

from __future__ import annotations

import asyncio

from apps.api.wilq_api import main


def test_daily_runtime_prewarm_builds_the_existing_cached_runtime(
    monkeypatch,
) -> None:
    calls: list[bool] = []

    monkeypatch.setattr(main, "build_daily_runtime", lambda: calls.append(True))

    asyncio.run(main._prewarm_daily_runtime())

    assert calls == [True]


def test_lifespan_schedules_daily_runtime_prewarm_after_readiness(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(main, "build_content_diagnostics_cached", lambda: None)
    monkeypatch.setattr(main, "build_merchant_diagnostics_cached", lambda: None)
    monkeypatch.setattr(main, "list_actions_cached", lambda: [])

    async def fake_knowledge_prewarm() -> None:
        calls.append("knowledge")

    async def fake_daily_prewarm() -> None:
        calls.append("daily")

    monkeypatch.setattr(main, "_prewarm_knowledge_map", fake_knowledge_prewarm)
    monkeypatch.setattr(main, "_prewarm_daily_runtime", fake_daily_prewarm)

    async def exercise_lifespan() -> None:
        async with main.wilq_lifespan(None):
            assert calls == []

    asyncio.run(exercise_lifespan())

    assert calls == ["knowledge", "daily"]
