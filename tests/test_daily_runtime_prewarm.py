"""Contract tests for lazy API read-model startup."""

from __future__ import annotations

import asyncio

from apps.api.wilq_api import main


def test_lifespan_does_not_preheat_unrelated_read_models(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    async def exercise_lifespan() -> None:
        async with main.wilq_lifespan(None):
            pass

    asyncio.run(exercise_lifespan())


def test_api_cache_invalidation_clears_daily_runtime(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main, "clear_tactical_queue_cache", lambda: None)
    monkeypatch.setattr(main, "clear_content_diagnostics_cache", lambda: None)
    monkeypatch.setattr(main, "clear_merchant_diagnostics_cache", lambda: None)
    monkeypatch.setattr(main, "clear_action_list_cache", lambda: None)
    monkeypatch.setattr(main, "clear_ads_summary_cache", lambda: None)
    monkeypatch.setattr(main, "clear_knowledge_operating_map_cache", lambda: None)
    monkeypatch.setattr(main, "clear_daily_runtime_cache", lambda: calls.append("daily"))
    monkeypatch.setattr(main, "clear_ga4_diagnostics_cache", lambda: calls.append("ga4"))
    monkeypatch.setattr(main, "clear_skill_context_cache", lambda: None)

    main.clear_api_view_model_caches()

    assert calls == ["daily", "ga4"]
