from __future__ import annotations

from apps.api.wilq_api import context_cache


def test_skill_context_cache_default_is_session_warm_and_env_overridable(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WILQ_SKILL_CONTEXT_CACHE_SECONDS", raising=False)
    assert context_cache._skill_context_cache_seconds() == 300.0

    monkeypatch.setenv("WILQ_SKILL_CONTEXT_CACHE_SECONDS", "7.5")
    assert context_cache._skill_context_cache_seconds() == 7.5

    monkeypatch.setenv("WILQ_SKILL_CONTEXT_CACHE_SECONDS", "-1")
    assert context_cache._skill_context_cache_seconds() == 0.0
