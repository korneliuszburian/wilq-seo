"""Focused proof for the first daily false-positive guard slice."""

from wilq.briefing.false_positive_guards import evaluate_source_trace_guard
from wilq.schemas import FreshnessState


def test_stale_source_guard_blocks_daily_recommendation() -> None:
    result = evaluate_source_trace_guard(
        source_connectors=["google_merchant_center"],
        evidence_ids=["ev_merchant"],
        expert_rule_ids=["merchant_platform_traps_v1"],
        freshness=FreshnessState(state="stale"),
    )

    assert result.guard_id == "stale_connector"
    assert result.status == "blocked"
    assert result.next_step


def test_source_trace_guard_requires_all_trace_fields() -> None:
    result = evaluate_source_trace_guard(
        source_connectors=[],
        evidence_ids=[],
        expert_rule_ids=[],
        freshness=FreshnessState(state="fresh"),
    )

    assert result.guard_id == "missing_source_connector"
    assert result.status == "blocked"
