from __future__ import annotations

import os
from dataclasses import dataclass
from time import monotonic

from wilq.actions.service import list_actions
from wilq.briefing.command_center import build_command_center_response
from wilq.briefing.marketing_brief import build_marketing_brief, core_brief_actions
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import list_connector_statuses
from wilq.schemas import ActionObject, CommandCenterResponse, ConnectorStatus, MarketingBrief

DEFAULT_DAILY_RUNTIME_CACHE_SECONDS = 2.0
_cached_runtime: DailyRuntimeCacheEntry | None = None


@dataclass(frozen=True)
class DailyRuntime:
    connectors: list[ConnectorStatus]
    actions: list[ActionObject]
    core_actions: list[ActionObject]
    command_center: CommandCenterResponse
    marketing_brief: MarketingBrief


@dataclass(frozen=True)
class DailyRuntimeCacheEntry:
    created_at: float
    runtime: DailyRuntime


def build_daily_runtime(use_cache: bool = True) -> DailyRuntime:
    """Build the daily marketer view once for API and Codex surfaces."""
    if use_cache:
        cached_runtime = _read_daily_runtime_cache()
        if cached_runtime is not None:
            return cached_runtime
    connectors = list_connector_statuses()
    actions = list_actions()
    refresh_runs = list_connector_refresh_runs()
    tactical_queue = build_tactical_queue()
    command = build_command_center_response(
        connectors=connectors,
        tactical_queue=tactical_queue,
        actions=actions,
    )
    brief = build_marketing_brief(
        connectors=connectors,
        refresh_runs=refresh_runs,
        actions=actions,
    )
    runtime = DailyRuntime(
        connectors=connectors,
        actions=actions,
        core_actions=core_brief_actions(actions),
        command_center=command,
        marketing_brief=brief,
    )
    if use_cache:
        _write_daily_runtime_cache(runtime)
    return runtime


def clear_daily_runtime_cache() -> None:
    global _cached_runtime
    _cached_runtime = None


def _read_daily_runtime_cache() -> DailyRuntime | None:
    cache_seconds = _cache_seconds()
    if cache_seconds <= 0:
        return None
    if _cached_runtime is None:
        return None
    if monotonic() - _cached_runtime.created_at > cache_seconds:
        return None
    return _cached_runtime.runtime


def _write_daily_runtime_cache(runtime: DailyRuntime) -> None:
    global _cached_runtime
    if _cache_seconds() <= 0:
        return
    _cached_runtime = DailyRuntimeCacheEntry(created_at=monotonic(), runtime=runtime)


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
