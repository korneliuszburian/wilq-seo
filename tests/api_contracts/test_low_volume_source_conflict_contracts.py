import pytest

from wilq.briefing.false_positive_guards import (
    evaluate_low_volume_guard,
    evaluate_source_conflict_guard,
)
from wilq.schemas.measurement import (
    MetricSampleEvidence,
    SourceComparisonEvidence,
    SourceComparisonValue,
)


def test_low_volume_guard_requires_explicit_contract_and_blocks_small_sample() -> None:
    assert evaluate_low_volume_guard(None).guard_id == "low_volume_contract_missing"

    result = evaluate_low_volume_guard(
        MetricSampleEvidence(
            metric_name="sessions",
            period="2026-07-01/2026-07-07",
            sample_size=8,
            minimum_sample_size=30,
            source_connector="google_analytics",
            evidence_ids=["ev_ga4_sample"],
        )
    )
    assert result.status == "blocked"
    assert result.guard_id == "low_volume"
    assert "30" in result.reason


def test_low_volume_guard_passes_only_when_explicit_threshold_is_met() -> None:
    result = evaluate_low_volume_guard(
        MetricSampleEvidence(
            metric_name="sessions",
            period="2026-07-01/2026-07-07",
            sample_size=30,
            minimum_sample_size=30,
            source_connector="google_analytics",
            evidence_ids=["ev_ga4_sample"],
        )
    )
    assert result.guard_id == "low_volume_ready"
    assert result.status == "pass"


def test_source_conflict_guard_blocks_disagreement_and_requires_distinct_sources() -> None:
    with pytest.raises(ValueError, match="distinct source"):
        SourceComparisonEvidence(
            metric_name="clicks",
            period="2026-07-01/2026-07-07",
            values=[
                SourceComparisonValue(
                    source_connector="google_search_console", value=10, evidence_ids=["a"]
                ),
                SourceComparisonValue(
                    source_connector="google_search_console", value=11, evidence_ids=["b"]
                ),
            ],
        )

    result = evaluate_source_conflict_guard(
        SourceComparisonEvidence(
            metric_name="clicks",
            period="2026-07-01/2026-07-07",
            values=[
                SourceComparisonValue(
                    source_connector="google_search_console", value=10, evidence_ids=["a"]
                ),
                SourceComparisonValue(
                    source_connector="google_analytics", value=11, evidence_ids=["b"]
                ),
            ],
        )
    )
    assert result.status == "blocked"
    assert result.guard_id == "source_conflict"
