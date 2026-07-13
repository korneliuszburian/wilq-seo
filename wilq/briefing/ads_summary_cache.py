from __future__ import annotations

import os
from dataclasses import dataclass
from time import monotonic

from wilq.schemas import AdsDiagnosticsResponse

DEFAULT_ADS_SUMMARY_CACHE_SECONDS = 15.0


@dataclass(frozen=True)
class AdsSummaryCacheEntry:
    created_at: float
    diagnostics: AdsDiagnosticsResponse


_cached_ads_summary: AdsSummaryCacheEntry | None = None


def clear_ads_summary_cache() -> None:
    global _cached_ads_summary
    _cached_ads_summary = None


def read_ads_summary_cache() -> AdsDiagnosticsResponse | None:
    cache_seconds = ads_summary_cache_seconds()
    if cache_seconds <= 0 or _cached_ads_summary is None:
        return None
    if monotonic() - _cached_ads_summary.created_at > cache_seconds:
        return None
    return _cached_ads_summary.diagnostics


def write_ads_summary_cache(diagnostics: AdsDiagnosticsResponse) -> None:
    global _cached_ads_summary
    if ads_summary_cache_seconds() <= 0:
        return
    _cached_ads_summary = AdsSummaryCacheEntry(
        created_at=monotonic(),
        diagnostics=diagnostics,
    )


def ads_summary_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_ADS_SUMMARY_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_ADS_SUMMARY_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_ADS_SUMMARY_CACHE_SECONDS
