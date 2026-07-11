from __future__ import annotations

import pytest

import wilq.actions.service as action_service


def test_action_list_cache_reuses_one_registry_build_outside_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_ACTION_LIST_CACHE_SECONDS", "60")
    action_service.clear_action_list_cache()
    calls = 0
    sentinel: list[object] = []

    def fake_list_actions() -> list[object]:
        nonlocal calls
        calls += 1
        return sentinel

    monkeypatch.setattr(action_service, "list_actions", fake_list_actions)
    assert action_service.list_actions_cached() is sentinel
    assert action_service.list_actions_cached() is sentinel
    assert calls == 1
    action_service.clear_action_list_cache()
    assert action_service.list_actions_cached() is sentinel
    assert calls == 2
