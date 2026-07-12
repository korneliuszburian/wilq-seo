"""Focused proof for daily false-positive guards."""

from wilq.briefing.daily_check import _daily_item
from wilq.briefing.false_positive_guards import (
    evaluate_conversion_readiness_guard,
    evaluate_gsc_date_window_guard,
    evaluate_multi_source_required_guard,
    evaluate_source_trace_guard,
)
from wilq.schemas import (
    ActionRisk,
    ContentGscSearchAnalyticsContract,
    DailyDecision,
    FreshnessState,
    Ga4ConversionReadinessContract,
    MetricFact,
)


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


def test_gsc_date_window_guard_requires_bounded_contract() -> None:
    contract = ContentGscSearchAnalyticsContract(
        data_availability_checked=True,
        aggregate_date_start="2026-06-01",
        aggregate_date_end="2026-06-30",
        latest_available_detail_date="2026-06-30",
        detail_data_completeness="partial",
    )

    result = evaluate_gsc_date_window_guard(contract)

    assert result.guard_id == "date_window_ready"
    assert result.status == "pass"


def test_multi_source_guard_requires_evidence_for_every_required_connector() -> None:
    result = evaluate_multi_source_required_guard(
        source_connectors=["wordpress_ekologus", "wordpress_sklep"],
        evidence_backed_connectors=["wordpress_ekologus"],
        required_connectors=["wordpress_ekologus", "wordpress_sklep"],
    )

    assert result.guard_id == "multi_source_required"
    assert result.status == "blocked"
    assert "WordPress" in result.reason


def test_multi_source_guard_accepts_typed_evidence_for_every_required_connector() -> None:
    result = evaluate_multi_source_required_guard(
        source_connectors=["wordpress_ekologus", "wordpress_sklep"],
        evidence_backed_connectors=["wordpress_ekologus", "wordpress_sklep"],
        required_connectors=["wordpress_ekologus", "wordpress_sklep"],
    )

    assert result.guard_id == "multi_source_ready"
    assert result.status == "pass"


def test_daily_content_queue_requires_typed_evidence_for_both_wordpress_sources() -> None:
    missing_evidence_item = _daily_item(
        _content_queue_decision(
            metric_facts=[_metric_fact("wordpress_ekologus", "ev_wordpress_public")]
        )
    )
    complete_evidence_item = _daily_item(
        _content_queue_decision(
            metric_facts=[
                _metric_fact("wordpress_ekologus", "ev_wordpress_public"),
                _metric_fact("wordpress_sklep", "ev_wordpress_store"),
            ]
        )
    )

    assert missing_evidence_item.category == "blocked_recommendation"
    assert missing_evidence_item.status == "blocked"
    assert "multi_source_required" in missing_evidence_item.false_positive_guards
    assert complete_evidence_item.category == "safe_next_action"
    assert complete_evidence_item.status == "review_required"
    assert "multi_source_ready" in complete_evidence_item.false_positive_guards
    assert "ev_wordpress_store" in complete_evidence_item.evidence_ids


def test_individual_public_content_decision_does_not_inherit_queue_wide_store_requirement() -> None:
    item = _daily_item(
        _content_queue_decision(
            decision_id="decision_public_homepage",
            source_connectors=["google_search_console", "wordpress_ekologus"],
            metric_facts=[_metric_fact("wordpress_ekologus", "ev_wordpress_public")],
        )
    )

    assert item.status == "review_required"
    assert not any(guard.startswith("multi_source_") for guard in item.false_positive_guards)


def _content_queue_decision(
    *,
    decision_id: str = "decision_prepare_content_refresh_queue",
    source_connectors: list[str] | None = None,
    metric_facts: list[MetricFact],
) -> DailyDecision:
    return DailyDecision(
        id=decision_id,
        title="Przejrzyj kolejkę SEO z GSC i WordPress",
        domain="content",
        freshness=FreshnessState(state="fresh"),
        route="/content-workflow",
        status="ready",
        priority=1,
        co_widzimy="Kolejka ma sygnały do sprawdzenia.",
        dlaczego_to_ma_znaczenie="Decyzja wymaga potwierdzenia inventory WordPress.",
        bezpieczny_next_step="Przejdź do ręcznego review.",
        why_it_matters="Decyzja nie może pominąć wymaganych źródeł.",
        operator_action="Sprawdź decyzję.",
        source_connectors=source_connectors
        or ["google_search_console", "wordpress_ekologus", "wordpress_sklep"],
        evidence_ids=["ev_content_refresh"],
        metric_facts=metric_facts,
        risk=ActionRisk.medium,
    )


def _metric_fact(source_connector: str, evidence_id: str) -> MetricFact:
    return MetricFact(
        name="inventory_count",
        value=1,
        period="latest_refresh",
        source_connector=source_connector,
        evidence_id=evidence_id,
    )
