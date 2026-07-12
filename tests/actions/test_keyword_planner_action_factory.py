from __future__ import annotations

from datetime import UTC, datetime

import pytest

from wilq.actions.google_ads.keyword_planner import (
    keyword_planner_access_action_from_vendor_read,
)
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
)


def _keyword_planner_run(
    *,
    mode: ConnectorRefreshMode = ConnectorRefreshMode.vendor_read,
    status: ConnectorRefreshStatus = ConnectorRefreshStatus.completed,
    vendor_data_collected: bool = True,
    metric_summary: dict[str, str | int] | None = None,
) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id="refresh_google_ads_keyword_planner",
        connector_id="google_ads",
        mode=mode,
        status=status,
        completed_at=datetime.now(UTC),
        evidence_ids=["ev_keyword_planner"],
        external_call_attempted=True,
        vendor_data_collected=vendor_data_collected,
        metric_summary=metric_summary or {},
        summary="Keyword Planner test run.",
    )


def test_keyword_planner_factory_sanitizes_recognized_live_blocker() -> None:
    action = keyword_planner_access_action_from_vendor_read(
        _keyword_planner_run(
            metric_summary={
                "keyword_planner_status": "blocked",
                "keyword_planner_http_status": 403,
                "keyword_planner_blocker": (
                    "api_status=PERMISSION_DENIED "
                    "ads_error=authorizationError.DEVELOPER_TOKEN_NOT_APPROVED"
                ),
            }
        )
    )

    assert action is not None
    assert action.mode == ActionMode.prepare
    assert action.evidence_ids == [connector_evidence_id("google_ads"), "ev_keyword_planner"]
    assert action.payload["blocked_reason"] == (
        "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera"
    )
    assert action.payload["apply_allowed"] is False
    assert action.payload["destructive"] is False
    serialized = action.model_dump_json()
    assert "PERMISSION_DENIED" not in serialized
    assert "DEVELOPER_TOKEN_NOT_APPROVED" not in serialized


@pytest.mark.parametrize(
    ("mode", "status", "vendor_data_collected", "metric_summary"),
    [
        (ConnectorRefreshMode.status_probe, ConnectorRefreshStatus.completed, True, {}),
        (ConnectorRefreshMode.vendor_read, ConnectorRefreshStatus.queued, True, {}),
        (ConnectorRefreshMode.vendor_read, ConnectorRefreshStatus.completed, False, {}),
        (
            ConnectorRefreshMode.vendor_read,
            ConnectorRefreshStatus.completed,
            True,
            {"keyword_planner_status": "ready"},
        ),
        (
            ConnectorRefreshMode.vendor_read,
            ConnectorRefreshStatus.completed,
            True,
            {
                "keyword_planner_status": "blocked",
                "keyword_planner_blocker": "unrelated transient error",
            },
        ),
    ],
)
def test_keyword_planner_factory_rejects_unqualified_runs(
    mode: ConnectorRefreshMode,
    status: ConnectorRefreshStatus,
    vendor_data_collected: bool,
    metric_summary: dict[str, str | int],
) -> None:
    assert (
        keyword_planner_access_action_from_vendor_read(
            _keyword_planner_run(
                mode=mode,
                status=status,
                vendor_data_collected=vendor_data_collected,
                metric_summary=metric_summary,
            )
        )
        is None
    )
