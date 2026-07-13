from datetime import UTC, datetime

from wilq.briefing.daily_check import _aggregate_freshness
from wilq.schemas import DailyCheckConnectorRef, FreshnessState


def test_aggregate_freshness_preserves_oldest_checked_success() -> None:
    oldest = datetime(2026, 7, 12, 0, 31, tzinfo=UTC)
    newest = datetime(2026, 7, 13, 16, 10, tzinfo=UTC)
    result = _aggregate_freshness(
        [
            DailyCheckConnectorRef(
                connector_id="google_analytics_4",
                status="checked",
                freshness=FreshnessState(state="fresh", last_success_at=oldest),
            ),
            DailyCheckConnectorRef(
                connector_id="google_search_console",
                status="checked",
                freshness=FreshnessState(state="fresh", last_success_at=newest),
            ),
            DailyCheckConnectorRef(
                connector_id="linkedin",
                status="skipped",
                freshness=FreshnessState(state="unknown"),
            ),
        ]
    )

    assert result.state == "fresh"
    assert result.last_success_at == oldest
