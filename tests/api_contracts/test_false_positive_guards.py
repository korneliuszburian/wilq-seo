"""Focused proof for the first daily false-positive guard slice."""

from wilq.briefing.false_positive_guards import (
    evaluate_conversion_readiness_guard,
    evaluate_source_trace_guard,
)
from wilq.schemas import FreshnessState, Ga4ConversionReadinessContract


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


def test_conversion_guard_uses_ga4_read_contract() -> None:
    contract = Ga4ConversionReadinessContract(
        status="blocked",
        title="GA4",
        summary="Brak mapowania",
        next_step="Sprawdź zdarzenia kluczowe.",
        missing_read_contracts=["conversion_or_key_event_mapping"],
    )

    result = evaluate_conversion_readiness_guard(contract)

    assert result.guard_id == "missing_conversion"
    assert result.status == "blocked"
    assert result.next_step == "Sprawdź zdarzenia kluczowe."
