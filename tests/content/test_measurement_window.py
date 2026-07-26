from __future__ import annotations

from datetime import date

from wilq.content.measurement.window import (
    ContentDateRange,
    ContentMeasurementWindow,
    content_measurement_window_outcome_allowed,
    content_measurement_window_outcome_blockers,
    mark_content_measurement_window_ready,
)


def test_measurement_window_allows_outcome_claim_only_after_ready_date() -> None:
    window = ContentMeasurementWindow(
        id="measurement_window_bdo",
        work_item_id="content_work_item_bdo",
        content_url="https://ekologus.pl/bdo/",
        baseline_period=ContentDateRange(start=date(2026, 5, 1), end=date(2026, 5, 31)),
        observation_period=ContentDateRange(start=date(2026, 7, 1), end=date(2026, 7, 31)),
        earliest_verdict_date=date(2026, 8, 1),
        allowed_metrics=["gsc_clicks"],
        deployment_id="deployment_bdo",
        deployed_revision_id="revision_bdo",
        deployed_revision_digest="a" * 64,
    )

    too_early = mark_content_measurement_window_ready(window, as_of=date(2026, 7, 31))
    ready = mark_content_measurement_window_ready(window, as_of=date(2026, 8, 1))

    assert content_measurement_window_outcome_allowed(too_early, as_of=date(2026, 7, 31)) is False
    assert [blocker.code for blocker in content_measurement_window_outcome_blockers(too_early)] == [
        "measurement_window_not_ready"
    ]
    assert ready.status == "ready_for_review"
    assert ready.success_claim_allowed is True
    assert content_measurement_window_outcome_allowed(ready, as_of=date(2026, 8, 1))
