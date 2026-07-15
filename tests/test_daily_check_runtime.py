"""Focused tests for the narrow daily-check runtime seam."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock, RLock, local
from types import SimpleNamespace

from wilq.briefing import daily_runtime


def test_daily_check_runtime_uses_only_the_lightweight_command_center(monkeypatch) -> None:
    command_center = SimpleNamespace(connector_health=["connector"])

    monkeypatch.setattr(
        daily_runtime,
        "build_daily_runtime_base",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("full daily runtime base is out of scope")
        ),
    )
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
    assert runtime.command_center is command_center


def test_daily_check_expired_dependencies_rebuild_concurrently(monkeypatch) -> None:
    from wilq.briefing import daily_check

    all_builds_started = Barrier(3)
    calls: list[str] = []
    runtime = SimpleNamespace(connectors=[], command_center=SimpleNamespace(daily_decisions=[]))
    ga4 = SimpleNamespace()
    content = SimpleNamespace()

    def build(name: str, value: object) -> object:
        calls.append(name)
        all_builds_started.wait(timeout=2)
        return value

    monkeypatch.setattr(
        daily_check,
        "build_daily_check_runtime",
        lambda **_: build("runtime", runtime),
    )
    monkeypatch.setattr(
        daily_check,
        "build_ga4_diagnostics_cached",
        lambda: build("ga4", ga4),
    )
    monkeypatch.setattr(
        daily_check,
        "build_content_diagnostics_cached",
        lambda: build("content", content),
    )

    dependencies = daily_check._build_daily_check_dependencies(use_cache=True)

    assert set(calls) == {"runtime", "ga4", "content"}
    assert dependencies.runtime is runtime
    assert dependencies.ga4 is ga4
    assert dependencies.content is content


def test_daily_check_expiry_returns_blocker_and_starts_one_background_rebuild(
    monkeypatch,
) -> None:
    from wilq.briefing import daily_check

    daily_runtime.finish_daily_check_prewarm()
    targets: list[object] = []
    builds: list[str] = []

    class DeferredThread:
        def __init__(self, *, target, **_kwargs) -> None:
            targets.append(target)

        def start(self) -> None:
            return None

    monkeypatch.setattr(daily_check, "Thread", DeferredThread)
    monkeypatch.setattr(daily_check, "_daily_check_dependencies_cached", lambda: False)
    monkeypatch.setattr(
        daily_check,
        "_build_daily_check_dependencies",
        lambda **_: builds.append("build"),
    )

    first = daily_check.build_daily_check()
    second = daily_check.build_daily_check()

    assert first.blocked_recommendations[0].id == "daily_check_runtime_prewarm"
    assert second.blocked_recommendations[0].id == "daily_check_runtime_prewarm"
    assert len(targets) == 1
    assert builds == []

    target = targets[0]
    assert callable(target)
    target()

    assert builds == ["build"]
    assert daily_runtime.daily_check_prewarm_in_progress() is False


def test_daily_check_runtime_deduplicates_concurrent_cold_builds(monkeypatch) -> None:
    daily_runtime.clear_daily_runtime_cache()
    original_cache_read = daily_runtime._read_daily_command_center_cache
    initial_reads = Barrier(2)
    read_lock = Lock()
    read_count = 0
    build_count = 0

    def synchronized_initial_cache_read():
        nonlocal read_count
        with read_lock:
            read_count += 1
            current_read = read_count
        if current_read <= 2:
            initial_reads.wait(timeout=2)
            return None
        return original_cache_read()

    def build_command_center_response(**_):
        nonlocal build_count
        with read_lock:
            build_count += 1
        return SimpleNamespace(connector_health=[])

    monkeypatch.setattr(daily_runtime, "_cache_seconds", lambda: 30.0)
    monkeypatch.setattr(
        daily_runtime,
        "_read_daily_command_center_cache",
        synchronized_initial_cache_read,
    )
    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [])
    monkeypatch.setattr(daily_runtime, "list_actions_cached", lambda: [])
    monkeypatch.setattr(daily_runtime, "list_connector_refresh_runs", lambda: [])
    monkeypatch.setattr(
        daily_runtime,
        "metric_store",
        lambda: SimpleNamespace(
            list_latest_metric_facts_by_connector_limits=lambda _: {}
        ),
    )
    monkeypatch.setattr(daily_runtime, "build_tactical_queue", lambda **_: SimpleNamespace())
    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        build_command_center_response,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        runtimes = list(executor.map(lambda _: daily_runtime.build_daily_check_runtime(), range(2)))

    assert build_count == 1
    assert runtimes[0].command_center is runtimes[1].command_center
    daily_runtime.clear_daily_runtime_cache()


def test_daily_check_invalidation_wins_over_an_inflight_build(
    monkeypatch,
) -> None:
    daily_runtime.clear_daily_runtime_cache()
    first_build_started = Event()
    release_first_build = Event()
    clear_lock_attempted = Event()
    thread_role = local()
    old_command = SimpleNamespace(connector_health=["old"])
    new_command = SimpleNamespace(connector_health=["new"])
    current_command = old_command
    build_count = 0

    class ObservedRLock:
        def __init__(self) -> None:
            self._lock = RLock()

        def __enter__(self):
            if getattr(thread_role, "name", None) == "clear":
                clear_lock_attempted.set()
            self._lock.acquire()
            return self

        def __exit__(self, *_args) -> None:
            self._lock.release()

    def build_command_center_response(**_):
        nonlocal build_count
        build_count += 1
        captured_command = current_command
        if build_count == 1:
            first_build_started.set()
            assert release_first_build.wait(timeout=2)
        return captured_command

    monkeypatch.setattr(daily_runtime, "_cache_seconds", lambda: 30.0)
    monkeypatch.setattr(daily_runtime, "_daily_runtime_build_lock", ObservedRLock())
    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [])
    monkeypatch.setattr(daily_runtime, "list_actions_cached", lambda: [])
    monkeypatch.setattr(daily_runtime, "list_connector_refresh_runs", lambda: [])
    monkeypatch.setattr(
        daily_runtime,
        "metric_store",
        lambda: SimpleNamespace(
            list_latest_metric_facts_by_connector_limits=lambda _: {}
        ),
    )
    monkeypatch.setattr(daily_runtime, "build_tactical_queue", lambda **_: SimpleNamespace())
    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        build_command_center_response,
    )

    def build_first_runtime():
        thread_role.name = "build"
        return daily_runtime.build_daily_check_runtime()

    def clear_runtime_cache() -> None:
        thread_role.name = "clear"
        daily_runtime.clear_daily_runtime_cache()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_runtime = executor.submit(build_first_runtime)
        assert first_build_started.wait(timeout=2)
        current_command = new_command
        clear_runtime = executor.submit(clear_runtime_cache)
        assert clear_lock_attempted.wait(timeout=2)
        release_first_build.set()
        assert first_runtime.result(timeout=2).command_center is old_command
        clear_runtime.result(timeout=2)

    second_runtime = daily_runtime.build_daily_check_runtime()

    assert second_runtime.command_center is new_command
    assert build_count == 2
    daily_runtime.clear_daily_runtime_cache()


def test_daily_check_prewarm_preserves_full_runtime_action_semantics(monkeypatch) -> None:
    daily_runtime.clear_daily_runtime_cache()
    actions = [SimpleNamespace(id="act_real_registry_action")]

    monkeypatch.setattr(daily_runtime, "_cache_seconds", lambda: 30.0)
    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [])
    monkeypatch.setattr(daily_runtime, "list_actions_cached", lambda: actions)
    monkeypatch.setattr(daily_runtime, "list_actions", lambda: actions)
    monkeypatch.setattr(daily_runtime, "list_connector_refresh_runs", lambda: [])
    monkeypatch.setattr(
        daily_runtime,
        "metric_store",
        lambda: SimpleNamespace(
            list_latest_metric_facts_by_connector_limits=lambda _: {}
        ),
    )
    monkeypatch.setattr(daily_runtime, "build_tactical_queue", lambda **_: "queue")

    def build_command_center_response(*, connectors, actions, **_):
        action_ids = (
            tuple(action.id for action in actions)
            if actions is not None
            else ("act_synthetic_stub",)
        )
        return SimpleNamespace(
            connector_health=connectors,
            action_ids=action_ids,
        )

    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        build_command_center_response,
    )
    base = daily_runtime.DailyRuntimeBase(
        connectors=[],
        actions=actions,
        refresh_runs=[],
        tactical_queue="queue",
        command_center_facts_by_connector={},
    )

    prewarmed = daily_runtime.build_daily_command_center(use_cache=True)
    full_after_prewarm = daily_runtime.build_daily_command_center(
        use_cache=True,
        base=base,
    )
    full_without_cache = daily_runtime.build_daily_command_center(
        use_cache=False,
        base=base,
    )

    assert prewarmed.action_ids == ("act_real_registry_action",)
    assert full_after_prewarm.action_ids == full_without_cache.action_ids
    daily_runtime.clear_daily_runtime_cache()


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
