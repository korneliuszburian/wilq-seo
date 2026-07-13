"""Focused proof for daily false-positive guards."""

import pytest

from wilq.briefing import daily_check
from wilq.briefing.daily_check import _daily_item
from wilq.briefing.false_positive_guards import (
    evaluate_content_measurement_baseline_guard,
    evaluate_conversion_readiness_guard,
    evaluate_gsc_date_window_guard,
    evaluate_multi_source_required_guard,
    evaluate_source_trace_guard,
)
from wilq.content.enrichment.opportunity import (
    ContentOpportunityMeasurementBaseline,
    build_content_opportunity_enrichment,
)
from wilq.content.workflow.queue import (
    ContentWorkItemQueueBlocker,
    ContentWorkItemQueueCandidate,
    ContentWorkItemQueueResponse,
)
from wilq.schemas import (
    ActionRisk,
    ContentDecisionItem,
    ContentDiagnosticsResponse,
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


def test_daily_item_blocks_recommendation_without_evidence() -> None:
    item = _daily_item(
        _content_queue_decision(
            source_connectors=["google_search_console"], metric_facts=[]
        ).model_copy(update={"evidence_ids": []})
    )

    assert item.status == "blocked"
    assert item.category == "blocked_recommendation"
    assert "missing_evidence" in item.false_positive_guards


def test_daily_item_blocks_recommendation_without_expert_rule() -> None:
    item = _daily_item(
        DailyDecision(
            id="decision_without_expert_rule",
            title="Decyzja bez reguły eksperckiej",
            domain="unknown_domain",
            route="/command-center",
            status="ready",
            priority=10,
            co_widzimy="Dane wymagają sprawdzenia.",
            dlaczego_to_ma_znaczenie="Bez reguły nie ma bezpiecznej interpretacji.",
            bezpieczny_next_step="Uzupełnij regułę i dowody.",
            why_it_matters="Brak reguły blokuje rekomendację.",
            operator_action="Nie rekomenduj działania.",
            source_connectors=["google_search_console"],
            evidence_ids=["ev_unknown_rule"],
            freshness=FreshnessState(state="fresh"),
        )
    )

    assert item.status == "blocked"
    assert item.category == "blocked_recommendation"
    assert "missing_expert_rule" in item.false_positive_guards


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


def test_measurement_baseline_guard_blocks_a_ready_label_without_metric_lineage() -> None:
    result = evaluate_content_measurement_baseline_guard(
        [
            _measurement_baseline(
                metrics_to_watch=[],
                source_connectors=[],
                evidence_ids=[],
            )
        ]
    )

    assert result.guard_id == "missing_measurement_baseline"
    assert result.status == "blocked"


def test_public_canonical_without_metrics_does_not_create_a_measurement_baseline() -> None:
    enrichment = build_content_opportunity_enrichment(
        ContentDecisionItem(
            id="content_decision_public_without_metrics",
            decision_type="refresh_or_merge",
            status="ready",
            title="Publiczna strona bez metryk",
            priority=1,
            source_public_url="https://www.ekologus.pl/nowa-strona/",
            final_canonical_url="https://www.ekologus.pl/nowa-strona/",
            source_connectors=["google_search_console", "wordpress_ekologus"],
            evidence_ids=["ev_gsc_public_without_metrics"],
            rationale="Publiczny canonical sam nie jest bazą metryk.",
            next_step="Uzupełnij metryki przed planem pomiaru.",
        )
    )

    result = evaluate_content_measurement_baseline_guard([enrichment.measurement_baseline])

    assert enrichment.measurement_baseline.status == "blocked"
    assert result.guard_id == "missing_measurement_baseline"


def test_measurement_baseline_guard_accepts_metric_source_and_evidence_lineage() -> None:
    result = evaluate_content_measurement_baseline_guard(
        [
            _measurement_baseline(
                metrics_to_watch=["gsc_clicks", "gsc_impressions"],
                source_connectors=["google_search_console"],
                evidence_ids=["ev_gsc_content"],
            )
        ]
    )

    assert result.guard_id == "measurement_baseline_ready"
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


def test_daily_content_queue_blocks_missing_measurement_baseline() -> None:
    measurement_guard = evaluate_content_measurement_baseline_guard([])

    item = _daily_item(
        _content_queue_decision(
            metric_facts=[
                _metric_fact("wordpress_ekologus", "ev_wordpress_public"),
                _metric_fact("wordpress_sklep", "ev_wordpress_store"),
            ]
        ),
        content_measurement_guard=daily_check._ContentMeasurementGuardContext(
            guard=measurement_guard,
            evidence_ids=[],
            source_connectors=[],
        ),
    )

    assert item.category == "blocked_recommendation"
    assert item.status == "blocked"
    assert "missing_measurement_baseline" in item.false_positive_guards
    assert item.next_step == measurement_guard.next_step


def test_individual_public_content_decision_does_not_inherit_queue_wide_store_requirement() -> None:
    measurement_guard = evaluate_content_measurement_baseline_guard([])
    item = _daily_item(
        _content_queue_decision(
            decision_id="decision_public_homepage",
            source_connectors=["google_search_console", "wordpress_ekologus"],
            metric_facts=[_metric_fact("wordpress_ekologus", "ev_wordpress_public")],
        ),
        content_measurement_guard=daily_check._ContentMeasurementGuardContext(
            guard=measurement_guard,
            evidence_ids=[],
            source_connectors=[],
            queue_density_summary="Pełna kolejka pozostaje zablokowana: 1 z 3 tematów.",
            queue_density_next_step="Nie dotyczy pojedynczego work orderu.",
        ),
    )

    assert item.status == "review_required"
    assert not any(guard.startswith("multi_source_") for guard in item.false_positive_guards)
    assert "missing_measurement_baseline" not in item.false_positive_guards
    assert "Pełna kolejka pozostaje zablokowana" not in item.summary


def test_content_measurement_guard_fails_closed_when_candidate_cannot_map_to_decision(
    monkeypatch,
) -> None:
    diagnostics = ContentDiagnosticsResponse.model_construct(decision_queue=[])
    queue = ContentWorkItemQueueResponse.model_construct(
        queue_status="blocked",
        actionable_candidate_count=1,
        minimum_actionable_candidate_count=3,
        candidates=[
            ContentWorkItemQueueCandidate.model_construct(
                decision_id="content_decision_missing",
                recommended_mode="refresh",
            )
        ],
        blockers=[
            ContentWorkItemQueueBlocker(
                code="not_enough_actionable_candidates",
                label="Za mało tematów gotowych do pracy",
                reason="Kolejka ma tylko jeden temat z pełnym dowodem.",
                next_step="Odśwież źródła, nie twórz sztucznych tematów.",
            )
        ],
    )
    monkeypatch.setattr(daily_check, "build_content_diagnostics_cached", lambda: diagnostics)
    monkeypatch.setattr(
        daily_check,
        "build_content_work_item_queue_response",
        lambda _diagnostics: queue,
    )

    result = daily_check._content_measurement_baseline_guard(
        [_content_queue_decision(metric_facts=[])]
    )

    assert result is not None
    assert result.guard.guard_id == "missing_measurement_baseline"
    assert result.guard.status == "blocked"
    assert result.queue_density_summary is not None


def test_content_measurement_guard_uses_ready_enrichment_and_keeps_density_blocker_visible(
    monkeypatch,
) -> None:
    ready_decision = _measurement_ready_content_decision()
    diagnostics = ContentDiagnosticsResponse.model_construct(decision_queue=[ready_decision])
    queue = ContentWorkItemQueueResponse.model_construct(
        queue_status="blocked",
        candidate_count=2,
        actionable_candidate_count=1,
        minimum_actionable_candidate_count=3,
        candidates=[
            ContentWorkItemQueueCandidate.model_construct(
                decision_id=ready_decision.id,
                recommended_mode="refresh",
                blockers=[],
                evidence_ids=ready_decision.evidence_ids,
                source_connectors=ready_decision.source_connectors,
            ),
            ContentWorkItemQueueCandidate.model_construct(
                decision_id="content_decision_blocked_ahrefs",
                recommended_mode="block",
                blockers=[],
                evidence_ids=["ev_ahrefs_blocked"],
                source_connectors=["ahrefs"],
            ),
        ],
        blockers=[
            ContentWorkItemQueueBlocker(
                code="not_enough_actionable_candidates",
                label="Za mało tematów gotowych do pracy",
                reason="Kolejka ma tylko jeden temat z pełnym dowodem.",
                next_step="Odśwież źródła, nie twórz sztucznych tematów.",
            )
        ],
    )
    monkeypatch.setattr(daily_check, "build_content_diagnostics_cached", lambda: diagnostics)
    monkeypatch.setattr(
        daily_check,
        "build_content_work_item_queue_response",
        lambda _diagnostics: queue,
    )

    result = daily_check._content_measurement_baseline_guard(
        [_content_queue_decision(metric_facts=[])]
    )

    assert result is not None
    assert result.guard.guard_id == "measurement_baseline_ready"
    assert result.guard.status == "pass"
    assert result.evidence_ids == ready_decision.evidence_ids
    assert result.source_connectors == ["google_search_console"]
    assert "ev_ahrefs_blocked" not in result.evidence_ids

    item = _daily_item(
        _content_queue_decision(
            metric_facts=[
                _metric_fact("wordpress_ekologus", "ev_wordpress_public"),
                _metric_fact("wordpress_sklep", "ev_wordpress_store"),
            ]
        ),
        content_measurement_guard=result,
    )

    assert item.status == "review_required"
    assert "measurement_baseline_ready" in item.false_positive_guards
    assert "Pełna kolejka pozostaje zablokowana" in item.summary
    assert "1 z 3 tematów gotowych do pracy" in item.summary
    assert "1 z 3 tematów gotowych do pracy" in item.next_step


def test_content_measurement_guard_keeps_density_visible_with_missing_baseline(
    monkeypatch,
) -> None:
    unready_decision = _measurement_ready_content_decision().model_copy(
        update={
            "id": "content_decision_homepage_without_measurement",
            "total_clicks": None,
            "total_impressions": None,
        }
    )
    diagnostics = ContentDiagnosticsResponse.model_construct(decision_queue=[unready_decision])
    queue = ContentWorkItemQueueResponse.model_construct(
        queue_status="blocked",
        candidate_count=1,
        actionable_candidate_count=1,
        minimum_actionable_candidate_count=3,
        candidates=[
            ContentWorkItemQueueCandidate.model_construct(
                decision_id=unready_decision.id,
                recommended_mode="refresh",
                blockers=[],
            )
        ],
        blockers=[
            ContentWorkItemQueueBlocker(
                code="not_enough_actionable_candidates",
                label="Za mało tematów gotowych do pracy",
                reason="Kolejka ma tylko jeden temat z pełnym dowodem.",
                next_step="Odśwież źródła, nie twórz sztucznych tematów.",
            )
        ],
    )
    monkeypatch.setattr(daily_check, "build_content_diagnostics_cached", lambda: diagnostics)
    monkeypatch.setattr(
        daily_check,
        "build_content_work_item_queue_response",
        lambda _diagnostics: queue,
    )

    result = daily_check._content_measurement_baseline_guard(
        [_content_queue_decision(metric_facts=[])]
    )
    assert result is not None
    item = _daily_item(
        _content_queue_decision(
            metric_facts=[
                _metric_fact("wordpress_ekologus", "ev_wordpress_public"),
                _metric_fact("wordpress_sklep", "ev_wordpress_store"),
            ]
        ),
        content_measurement_guard=result,
    )

    assert result.guard.guard_id == "missing_measurement_baseline"
    assert item.status == "blocked"
    assert "Żaden temat gotowy do pracy" in item.summary
    assert "Pełna kolejka pozostaje zablokowana" in item.summary
    assert "1 z 3 tematów gotowych do pracy" in item.next_step
    assert "Najpierw wybierz temat z metrykami" in item.next_step
    assert "Możesz ręcznie przejrzeć gotowy temat" not in item.next_step


def test_content_density_never_invites_review_when_source_trace_blocks() -> None:
    measurement_guard = evaluate_content_measurement_baseline_guard(
        [
            _measurement_baseline(
                metrics_to_watch=["gsc_clicks"],
                source_connectors=["google_search_console"],
                evidence_ids=["ev_gsc_content"],
            )
        ]
    )
    stale_decision = _content_queue_decision(
        metric_facts=[
            _metric_fact("wordpress_ekologus", "ev_wordpress_public"),
            _metric_fact("wordpress_sklep", "ev_wordpress_store"),
        ]
    ).model_copy(update={"freshness": FreshnessState(state="stale")})

    item = _daily_item(
        stale_decision,
        content_measurement_guard=daily_check._ContentMeasurementGuardContext(
            guard=measurement_guard,
            evidence_ids=["ev_gsc_content"],
            source_connectors=["google_search_console"],
            queue_density_summary="Pełna kolejka pozostaje zablokowana: 1 z 3 tematów.",
            queue_density_next_step="Uzupełnij kolejkę bez sztucznych tematów.",
        ),
    )

    assert item.status == "blocked"
    assert "stale_connector" in item.false_positive_guards
    assert "Pełna kolejka pozostaje zablokowana" in item.summary
    assert "Możesz ręcznie przejrzeć gotowy temat" not in item.next_step
    assert "Uzupełnij kolejkę bez sztucznych tematów" in item.next_step


@pytest.mark.parametrize("failed_builder", ["diagnostics", "queue", "enrichment"])
def test_content_measurement_guard_fails_closed_when_a_builder_raises(
    monkeypatch,
    failed_builder: str,
) -> None:
    ready_decision = _measurement_ready_content_decision()
    diagnostics = ContentDiagnosticsResponse.model_construct(decision_queue=[ready_decision])
    queue = ContentWorkItemQueueResponse.model_construct(
        queue_status="blocked",
        actionable_candidate_count=1,
        minimum_actionable_candidate_count=3,
        candidates=[
            ContentWorkItemQueueCandidate.model_construct(
                decision_id=ready_decision.id,
                recommended_mode="refresh",
                blockers=[],
            )
        ],
        blockers=[
            ContentWorkItemQueueBlocker(
                code="not_enough_actionable_candidates",
                label="Za mało tematów gotowych do pracy",
                reason="Kolejka ma tylko jeden temat z pełnym dowodem.",
                next_step="Odśwież źródła, nie twórz sztucznych tematów.",
            )
        ],
    )

    def raise_builder(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("synthetic content measurement failure")

    monkeypatch.setattr(
        daily_check,
        "build_content_diagnostics_cached",
        raise_builder if failed_builder == "diagnostics" else lambda: diagnostics,
    )
    monkeypatch.setattr(
        daily_check,
        "build_content_work_item_queue_response",
        raise_builder if failed_builder == "queue" else lambda _diagnostics: queue,
    )
    if failed_builder == "enrichment":
        monkeypatch.setattr(daily_check, "build_content_opportunity_enrichment", raise_builder)

    result = daily_check._content_measurement_baseline_guard(
        [_content_queue_decision(metric_facts=[])]
    )

    assert result is not None
    assert result.guard.guard_id == "missing_measurement_baseline"
    assert result.guard.status == "blocked"
    if failed_builder == "enrichment":
        assert result.queue_density_summary is not None


def _measurement_ready_content_decision() -> ContentDecisionItem:
    return ContentDecisionItem(
        id="content_decision_homepage_measurement",
        decision_type="refresh_or_merge",
        status="ready",
        title="Odśwież stronę główną BDO",
        primary_query="obsługa BDO",
        priority=1,
        source_public_url="https://www.ekologus.pl/",
        final_canonical_url="https://www.ekologus.pl/",
        total_clicks=12,
        total_impressions=120,
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_homepage", "ev_wordpress_homepage"],
        rationale="Publiczny adres i metryki są potwierdzone.",
        next_step="Przygotuj review odświeżenia strony.",
    )


def _measurement_baseline(
    *,
    metrics_to_watch: list[str],
    source_connectors: list[str],
    evidence_ids: list[str],
) -> ContentOpportunityMeasurementBaseline:
    return ContentOpportunityMeasurementBaseline(
        status="ready_to_plan",
        label="baza pomiaru do zaplanowania",
        reason="Fixture baseline.",
        metrics_to_watch=metrics_to_watch,
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
    )


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
