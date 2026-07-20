from __future__ import annotations

from apps.api.wilq_api import context_cache, main
from apps.api.wilq_api.context_models import ContextPackRequest


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


def test_full_context_cache_uses_shorter_metric_freshness_ttl(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WILQ_FULL_CONTEXT_CACHE_SECONDS", raising=False)
    assert context_cache._full_context_cache_seconds() == 30.0
    monkeypatch.setenv("WILQ_FULL_CONTEXT_CACHE_SECONDS", "4.5")
    assert context_cache._full_context_cache_seconds() == 4.5


def test_full_context_cache_is_bounded_and_invalidated(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WILQ_SKILL_CONTEXT_CACHE_SECONDS", raising=False)
    context_cache.clear_skill_context_cache()
    calls: list[int] = []

    def fake_full_context_pack(**_kwargs):
        calls.append(1)
        return {"generated": len(calls)}

    monkeypatch.setattr(main.context_full, "full_context_pack", fake_full_context_pack)
    request = ContextPackRequest()

    assert main.context_pack(request) == {"generated": 1}
    assert main.context_pack(request) == {"generated": 1}
    assert len(calls) == 1

    context_cache.clear_skill_context_cache()
    assert main.context_pack(request) == {"generated": 2}
    assert len(calls) == 2
