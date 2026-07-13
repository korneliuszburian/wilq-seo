"""Contract tests for the non-blocking daily runtime prewarm."""

from __future__ import annotations

import asyncio

from apps.api.wilq_api import main


def test_daily_runtime_prewarm_builds_the_daily_check_runtime(
    monkeypatch,
) -> None:
    calls: list[bool] = []

    monkeypatch.setattr(main, "build_daily_check_runtime", lambda: calls.append(True))

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


def test_api_cache_invalidation_clears_daily_runtime(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main, "clear_tactical_queue_cache", lambda: None)
    monkeypatch.setattr(main, "clear_content_diagnostics_cache", lambda: None)
    monkeypatch.setattr(main, "clear_merchant_diagnostics_cache", lambda: None)
    monkeypatch.setattr(main, "clear_action_list_cache", lambda: None)
    monkeypatch.setattr(main, "clear_ads_summary_cache", lambda: None)
    monkeypatch.setattr(main, "clear_knowledge_operating_map_cache", lambda: None)
    monkeypatch.setattr(main, "clear_daily_runtime_cache", lambda: calls.append("daily"))
    monkeypatch.setattr(main, "clear_skill_context_cache", lambda: None)

    main.clear_api_view_model_caches()

    assert calls == ["daily"]
