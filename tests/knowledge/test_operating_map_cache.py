from __future__ import annotations

import pytest

import wilq.knowledge.operating_map as operating_map


def test_knowledge_operating_map_cache_reuses_one_build_outside_test_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_KNOWLEDGE_MAP_CACHE_SECONDS", "60")
    operating_map.clear_knowledge_operating_map_cache()
    calls = 0
    sentinel = object()

    def fake_build():
        nonlocal calls
        calls += 1
        return sentinel

    monkeypatch.setattr(operating_map, "build_knowledge_operating_map", fake_build)
    assert operating_map.build_knowledge_operating_map_cached() is sentinel
    assert operating_map.build_knowledge_operating_map_cached() is sentinel
    assert calls == 1
    operating_map.clear_knowledge_operating_map_cache()
    assert operating_map.build_knowledge_operating_map_cached() is sentinel
    assert calls == 2
