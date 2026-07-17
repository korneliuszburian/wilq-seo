from __future__ import annotations

from datetime import timedelta

from wilq.schemas import (
    ConnectorRefreshRun,
    ContentDiagnosticsResponse,
    connector_refresh_has_live_data,
)


def content_diagnostics_with_ads_refresh(
    diagnostics: ContentDiagnosticsResponse,
    refresh: ConnectorRefreshRun | None,
) -> ContentDiagnosticsResponse:
    if refresh is None:
        return diagnostics
    freshness = diagnostics.freshness_assessment
    blocked = [
        connector_id
        for connector_id in freshness.blocked_connector_ids
        if connector_id != "google_ads"
    ]
    stale = [
        connector_id
        for connector_id in freshness.stale_connector_ids
        if connector_id != "google_ads"
    ]
    if not connector_refresh_has_live_data(refresh):
        blocked = _with_value(blocked, "google_ads")
    else:
        collected_at = refresh.completed_at or refresh.started_at
        stale_after = freshness.checked_at - timedelta(hours=freshness.stale_after_hours)
        if collected_at < stale_after:
            stale = _with_value(stale, "google_ads")
    return diagnostics.model_copy(
        update={
            "latest_refreshes": [
                *(
                    item
                    for item in diagnostics.latest_refreshes
                    if item.connector_id != "google_ads"
                ),
                refresh,
            ],
            "freshness_assessment": freshness.model_copy(
                update={
                    "blocked_connector_ids": blocked,
                    "stale_connector_ids": stale,
                }
            ),
        }
    )


def latest_ads_refresh(
    diagnostics: ContentDiagnosticsResponse,
    refreshes: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    return next(iter(refreshes), None) or next(
        (
            refresh
            for refresh in diagnostics.latest_refreshes
            if refresh.connector_id == "google_ads"
        ),
        None,
    )


def _with_value(values: list[str], value: str) -> list[str]:
    return list(dict.fromkeys([*values, value]))
