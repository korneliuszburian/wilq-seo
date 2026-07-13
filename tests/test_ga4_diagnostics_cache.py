"""Focused tests for the GA4 diagnostics cache boundary."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from time import sleep
from types import SimpleNamespace

from wilq.briefing import ga4_diagnostics


def test_ga4_cached_builder_hits_and_expires(monkeypatch) -> None:
    calls: list[str] = []
    now = [0.0]
    response = SimpleNamespace(id="ga4-response")

    monkeypatch.setattr(ga4_diagnostics, "_ga4_diagnostics_cache_seconds", lambda: 1.0)
    monkeypatch.setattr(ga4_diagnostics, "monotonic", lambda: now[0])
    monkeypatch.setattr(
        ga4_diagnostics,
        "build_ga4_diagnostics",
        lambda: calls.append("build") or response,
    )
    ga4_diagnostics.clear_ga4_diagnostics_cache()

    assert ga4_diagnostics.build_ga4_diagnostics_cached() is response
    assert ga4_diagnostics.build_ga4_diagnostics_cached() is response
    assert calls == ["build"]

    now[0] = 2.0
    assert ga4_diagnostics.build_ga4_diagnostics_cached() is response
    assert calls == ["build", "build"]


def test_ga4_cache_clear_forces_next_build(monkeypatch) -> None:
    calls: list[str] = []
    response = SimpleNamespace(id="ga4-response")

    monkeypatch.setattr(ga4_diagnostics, "_ga4_diagnostics_cache_seconds", lambda: 60.0)
    monkeypatch.setattr(ga4_diagnostics, "monotonic", lambda: 0.0)
    monkeypatch.setattr(
        ga4_diagnostics,
        "build_ga4_diagnostics",
        lambda: calls.append("build") or response,
    )
    ga4_diagnostics.clear_ga4_diagnostics_cache()

    ga4_diagnostics.build_ga4_diagnostics_cached()
    ga4_diagnostics.clear_ga4_diagnostics_cache()
    ga4_diagnostics.build_ga4_diagnostics_cached()

    assert calls == ["build", "build"]


def test_ga4_cached_builder_serializes_concurrent_cold_build(monkeypatch) -> None:
    calls: list[str] = []
    response = SimpleNamespace(id="ga4-response")

    monkeypatch.setattr(ga4_diagnostics, "_ga4_diagnostics_cache_seconds", lambda: 60.0)
    monkeypatch.setattr(ga4_diagnostics, "monotonic", lambda: 0.0)

    def build() -> SimpleNamespace:
        calls.append("build")
        sleep(0.05)
        return response

    monkeypatch.setattr(ga4_diagnostics, "build_ga4_diagnostics", build)
    ga4_diagnostics.clear_ga4_diagnostics_cache()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: ga4_diagnostics.build_ga4_diagnostics_cached(), [1, 2])
        )

    assert results == [response, response]
    assert calls == ["build"]
