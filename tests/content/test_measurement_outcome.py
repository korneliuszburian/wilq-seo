from __future__ import annotations

from datetime import date
from typing import cast

from wilq.content.measurement.outcome import (
    ContentMeasurementObservedMetric,
    interpret_content_measurement_outcome,
)
from wilq.content.measurement.window import (
    ContentDateRange,
    ContentMeasurementMetric,
    ContentMeasurementWindow,
)


def _window(**overrides: object) -> ContentMeasurementWindow:
    payload: dict[str, object] = {
        "id": "measurement_window_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "content_url": "https://ekologus.pl/bdo/",
        "baseline_period": ContentDateRange(
            start=date(2026, 5, 1),
            end=date(2026, 5, 31),
        ),
        "observation_period": ContentDateRange(
            start=date(2026, 7, 1),
            end=date(2026, 7, 31),
        ),
        "earliest_verdict_date": date(2026, 8, 1),
        "allowed_metrics": ["gsc_clicks", "gsc_impressions"],
        "source_connectors": ["google_search_console"],
        "evidence_ids": ["ev_gsc_bdo"],
        "status": "ready_for_review",
        "handoff_id": "wordpress_draft_handoff_content_work_item_bdo",
        "success_claim_allowed": True,
    }
    payload.update(overrides)
    return ContentMeasurementWindow.model_validate(payload)


def _metric(
    metric: str,
    baseline: float | None,
    observation: float | None,
    *,
    evidence_ids: list[str] | None = None,
    metric_fact_ids: list[str] | None = None,
    refresh_run_ids: list[str] | None = None,
    work_item_id: str = "content_work_item_bdo",
    measurement_window_id: str = "measurement_window_content_work_item_bdo",
    content_url: str = "https://ekologus.pl/bdo/",
) -> ContentMeasurementObservedMetric:
    return ContentMeasurementObservedMetric(
        metric=cast(ContentMeasurementMetric, metric),
        baseline_value=baseline,
        observation_value=observation,
        source_connector="google_search_console",
        evidence_ids=["ev_gsc_bdo"] if evidence_ids is None else evidence_ids,
        metric_fact_ids=(
            ["metric_fact_gsc_bdo_clicks"] if metric_fact_ids is None else metric_fact_ids
        ),
        refresh_run_ids=(
            ["refresh_google_search_console_bdo"]
            if refresh_run_ids is None
            else refresh_run_ids
        ),
        work_item_id=work_item_id,
        measurement_window_id=measurement_window_id,
        content_url=content_url,
    )


def test_measurement_outcome_blocks_before_window_is_ready() -> None:
    outcome = interpret_content_measurement_outcome(
        window=_window(status="planned", success_claim_allowed=False),
        observed_metrics=[_metric("gsc_clicks", 10, 20)],
        as_of=date(2026, 7, 20),
    )

    assert outcome.status == "not_ready"
    assert outcome.success_claim_allowed is False
    assert outcome.queue_feedback_allowed is False
    assert outcome.confidence == "none"


def test_measurement_outcome_requires_metric_values_and_evidence() -> None:
    outcome = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[_metric("gsc_clicks", 10, None, evidence_ids=[])],
        as_of=date(2026, 8, 1),
    )

    assert outcome.status == "insufficient_data"
    assert outcome.success_claim_allowed is False
    assert "Brakuje wartości po obserwacji" in outcome.limitations[0]
    assert "Brakuje evidence ID" in " ".join(outcome.limitations)


def test_measurement_outcome_requires_metric_store_and_window_provenance() -> None:
    missing_provenance = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[
            _metric(
                "gsc_clicks",
                100,
                130,
                metric_fact_ids=[],
                refresh_run_ids=[],
            )
        ],
        as_of=date(2026, 8, 1),
    )
    mismatched_window = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[
            _metric(
                "gsc_clicks",
                100,
                130,
                work_item_id="content_work_item_other",
                measurement_window_id="measurement_window_other",
                content_url="https://ekologus.pl/inny-url/",
            )
        ],
        as_of=date(2026, 8, 1),
    )

    assert missing_provenance.status == "insufficient_data"
    assert missing_provenance.success_claim_allowed is False
    assert "Brakuje metric_fact_ids" in " ".join(missing_provenance.limitations)
    assert "Brakuje refresh_run_ids" in " ".join(missing_provenance.limitations)
    assert mismatched_window.status == "insufficient_data"
    assert mismatched_window.success_claim_allowed is False
    assert "work_item_id" in " ".join(mismatched_window.limitations)
    assert "measurement_window_id" in " ".join(mismatched_window.limitations)
    assert "content_url" in " ".join(mismatched_window.limitations)


def test_measurement_outcome_classifies_noisy_directional_and_success_states() -> None:
    noisy = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[_metric("gsc_clicks", 100, 104)],
        as_of=date(2026, 8, 1),
    )
    directional = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[
            _metric("gsc_clicks", 100, 130),
            _metric("gsc_impressions", 1000, 990),
        ],
        as_of=date(2026, 8, 1),
    )
    success = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[
            _metric("gsc_clicks", 100, 130),
            _metric("gsc_impressions", 1000, 1200),
        ],
        as_of=date(2026, 8, 1),
    )

    assert noisy.status == "noisy_inconclusive"
    assert noisy.success_claim_allowed is False
    assert directional.status == "directional_improvement"
    assert directional.success_claim_allowed is False
    assert directional.queue_feedback_allowed is True
    assert success.status == "measured_success"
    assert success.success_claim_allowed is True
    assert success.queue_feedback_allowed is True
    assert success.metric_fact_ids == ["metric_fact_gsc_bdo_clicks"]
    assert success.refresh_run_ids == ["refresh_google_search_console_bdo"]
    assert "nie pełny dowód przyczyny" in " ".join(success.limitations)
