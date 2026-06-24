from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import monotonic

from wilq.actions.service import list_actions
from wilq.briefing.command_center import (
    build_command_center_response,
    command_center_metric_fact_limits,
)
from wilq.briefing.marketing_brief import build_marketing_brief, core_brief_actions
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import list_connector_statuses
from wilq.schemas import (
    ActionObject,
    CommandCenterResponse,
    ConnectorRefreshRun,
    ConnectorStatus,
    MarketingBrief,
    MetricFact,
    TacticalQueueResponse,
)
from wilq.storage.metric_store import metric_store

DEFAULT_DAILY_RUNTIME_CACHE_SECONDS = 30.0
_cached_base: DailyRuntimeBaseCacheEntry | None = None
_cached_command_center: DailyCommandCenterCacheEntry | None = None
_cached_marketing_brief: DailyMarketingBriefCacheEntry | None = None


@dataclass(frozen=True)
class DailyRuntimeBase:
    connectors: list[ConnectorStatus]
    actions: list[ActionObject]
    refresh_runs: list[ConnectorRefreshRun]
    tactical_queue: TacticalQueueResponse
    command_center_facts_by_connector: dict[str, list[MetricFact]] | None = None


@dataclass(frozen=True)
class DailyRuntime:
    connectors: list[ConnectorStatus]
    actions: list[ActionObject]
    refresh_runs: list[ConnectorRefreshRun]
    core_actions: list[ActionObject]
    command_center: CommandCenterResponse
    marketing_brief: MarketingBrief


@dataclass(frozen=True)
class DailyRuntimeBaseCacheEntry:
    created_at: float
    base: DailyRuntimeBase


@dataclass(frozen=True)
class DailyCommandCenterCacheEntry:
    created_at: float
    command_center: CommandCenterResponse


@dataclass(frozen=True)
class DailyMarketingBriefCacheEntry:
    created_at: float
    marketing_brief: MarketingBrief


def build_daily_runtime(use_cache: bool = True) -> DailyRuntime:
    """Build both daily marketer views for API and Codex surfaces."""
    base = build_daily_runtime_base(use_cache=use_cache)
    command = build_daily_command_center(use_cache=use_cache, base=base)
    brief = build_daily_marketing_brief(
        use_cache=use_cache,
        base=base,
        command_center=command,
    )
    return DailyRuntime(
        connectors=base.connectors,
        actions=base.actions,
        refresh_runs=base.refresh_runs,
        core_actions=core_brief_actions(base.actions),
        command_center=command,
        marketing_brief=brief,
    )


def build_daily_runtime_base(use_cache: bool = True) -> DailyRuntimeBase:
    if use_cache:
        cached_base = _read_daily_runtime_base_cache()
        if cached_base is not None:
            return cached_base
    with ThreadPoolExecutor(max_workers=4) as executor:
        connectors_future = executor.submit(list_connector_statuses)
        actions_future = executor.submit(list_actions)
        refresh_runs_future = executor.submit(list_connector_refresh_runs)
        command_facts_future = executor.submit(
            metric_store().list_latest_metric_facts_by_connector_limits,
            command_center_metric_fact_limits(),
        )

        connectors = connectors_future.result()
        actions = actions_future.result()
        refresh_runs = refresh_runs_future.result()
        command_center_facts_by_connector = command_facts_future.result()
        tactical_queue = build_tactical_queue(
            facts_by_connector=command_center_facts_by_connector
        )
    base = DailyRuntimeBase(
        connectors=connectors,
        actions=actions,
        refresh_runs=refresh_runs,
        tactical_queue=tactical_queue,
        command_center_facts_by_connector=command_center_facts_by_connector,
    )
    if use_cache:
        _write_daily_runtime_base_cache(base)
    return base


def build_daily_command_center(
    use_cache: bool = True,
    base: DailyRuntimeBase | None = None,
) -> CommandCenterResponse:
    if use_cache:
        cached_command = _read_daily_command_center_cache()
        if cached_command is not None:
            return cached_command
    if base is None:
        with ThreadPoolExecutor(max_workers=3) as executor:
            connectors_future = executor.submit(list_connector_statuses)
            refresh_runs_future = executor.submit(list_connector_refresh_runs)
            command_facts_future = executor.submit(
                metric_store().list_latest_metric_facts_by_connector_limits,
                command_center_metric_fact_limits(),
            )
            connectors = connectors_future.result()
            refresh_runs = refresh_runs_future.result()
            command_center_facts_by_connector = command_facts_future.result()
            tactical_queue = build_tactical_queue(
                facts_by_connector=command_center_facts_by_connector
            )
        command = build_command_center_response(
            connectors=connectors,
            tactical_queue=tactical_queue,
            actions=None,
            facts_by_connector=command_center_facts_by_connector,
            refresh_runs=refresh_runs,
        )
        if use_cache:
            _write_daily_command_center_cache(command)
        return command
    command = build_command_center_response(
        connectors=base.connectors,
        tactical_queue=base.tactical_queue,
        actions=base.actions,
        facts_by_connector=base.command_center_facts_by_connector,
        refresh_runs=base.refresh_runs,
    )
    if use_cache:
        _write_daily_command_center_cache(command)
    return command


def build_daily_marketing_brief(
    use_cache: bool = True,
    base: DailyRuntimeBase | None = None,
    command_center: CommandCenterResponse | None = None,
) -> MarketingBrief:
    if use_cache:
        cached_brief = _read_daily_marketing_brief_cache()
        if cached_brief is not None:
            return cached_brief
    base = base if base is not None else build_daily_runtime_base(use_cache=use_cache)
    command_center = command_center if command_center is not None else build_daily_command_center(
        use_cache=use_cache,
        base=base,
    )
    brief = build_marketing_brief(
        connectors=base.connectors,
        refresh_runs=base.refresh_runs,
        actions=base.actions,
        command_center=command_center,
        metric_facts_by_connector=base.command_center_facts_by_connector,
    )
    if use_cache:
        _write_daily_marketing_brief_cache(brief)
    return brief


def clear_daily_runtime_cache() -> None:
    global _cached_base, _cached_command_center, _cached_marketing_brief
    _cached_base = None
    _cached_command_center = None
    _cached_marketing_brief = None


def _read_daily_runtime_base_cache() -> DailyRuntimeBase | None:
    cache_seconds = _cache_seconds()
    if cache_seconds <= 0:
        return None
    if _cached_base is None:
        return None
    if monotonic() - _cached_base.created_at > cache_seconds:
        return None
    return _cached_base.base


def _write_daily_runtime_base_cache(base: DailyRuntimeBase) -> None:
    global _cached_base
    if _cache_seconds() <= 0:
        return
    _cached_base = DailyRuntimeBaseCacheEntry(created_at=monotonic(), base=base)


def _read_daily_command_center_cache() -> CommandCenterResponse | None:
    cache_seconds = _cache_seconds()
    if cache_seconds <= 0:
        return None
    if _cached_command_center is None:
        return None
    if monotonic() - _cached_command_center.created_at > cache_seconds:
        return None
    return _cached_command_center.command_center


def _write_daily_command_center_cache(command_center: CommandCenterResponse) -> None:
    global _cached_command_center
    if _cache_seconds() <= 0:
        return
    _cached_command_center = DailyCommandCenterCacheEntry(
        created_at=monotonic(),
        command_center=command_center,
    )


def _read_daily_marketing_brief_cache() -> MarketingBrief | None:
    cache_seconds = _cache_seconds()
    if cache_seconds <= 0:
        return None
    if _cached_marketing_brief is None:
        return None
    if monotonic() - _cached_marketing_brief.created_at > cache_seconds:
        return None
    return _cached_marketing_brief.marketing_brief


def _write_daily_marketing_brief_cache(marketing_brief: MarketingBrief) -> None:
    global _cached_marketing_brief
    if _cache_seconds() <= 0:
        return
    _cached_marketing_brief = DailyMarketingBriefCacheEntry(
        created_at=monotonic(),
        marketing_brief=marketing_brief,
    )


def _cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_DAILY_RUNTIME_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_DAILY_RUNTIME_CACHE_SECONDS
