from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from wilq.briefing.content_diagnostics import build_content_diagnostics_cached
from wilq.briefing.daily_runtime import build_daily_runtime
from wilq.briefing.false_positive_guards import (
    FalsePositiveGuardResult,
    evaluate_content_measurement_baseline_guard,
    evaluate_conversion_readiness_guard,
    evaluate_gsc_date_window_guard,
    evaluate_low_volume_guard,
    evaluate_multi_source_required_guard,
    evaluate_source_conflict_guard,
    evaluate_source_trace_guard,
)
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.recommendation_log import list_recommendation_logs
from wilq.content.enrichment.opportunity import build_content_opportunity_enrichment
from wilq.content.workflow.queue import (
    ContentWorkItemQueueResponse,
    build_content_work_item_queue_response,
)
from wilq.expert.rules import get_expert_rule
from wilq.knowledge.workspace_dossier import build_workspace_dossier
from wilq.schemas import (
    ActionRisk,
    ConnectorStatus,
    DailyCheckConnectorRef,
    DailyCheckItem,
    DailyCheckResult,
    DailyDecision,
    FreshnessState,
)

WORKSPACE_ID = "ekologus"
_CONTENT_QUEUE_DECISION_ID = "decision_prepare_content_refresh_queue"

_RULE_IDS_BY_DOMAIN: dict[str, tuple[str, ...]] = {
    "google_ads": ("ads_diagnostics_v1", "ads_platform_traps_v1"),
    "ga4": ("ga4_diagnostics_v1", "ga4_platform_traps_v1"),
    "merchant": ("merchant_feed_rules_v1", "merchant_platform_traps_v1"),
    "content": ("gsc_platform_traps_v1", "wordpress_platform_traps_v1"),
    "localo": ("local_visibility_v1",),
}


@dataclass(frozen=True)
class _ContentMeasurementGuardContext:
    """Keep aggregate content measurement proof distinct from queue-wide density."""

    guard: FalsePositiveGuardResult
    evidence_ids: list[str]
    source_connectors: list[str]
    queue_density_summary: str | None = None
    queue_density_next_step: str | None = None


def build_daily_check(*, use_cache: bool = True) -> DailyCheckResult:
    """Compile the existing daily decision queue into a traceable operator result."""
    runtime = build_daily_runtime(use_cache=use_cache)
    connector_refs = _connector_refs(runtime.connectors)
    ga4_guard = _ga4_conversion_guard(runtime.command_center.daily_decisions)
    content_guard = _content_date_window_guard(runtime.command_center.daily_decisions)
    content_measurement_guard = _content_measurement_baseline_guard(
        runtime.command_center.daily_decisions
    )
    items = [
        _daily_item(
            decision,
            ga4_guard=ga4_guard,
            content_guard=content_guard,
            content_measurement_guard=content_measurement_guard,
        )
        for decision in runtime.command_center.daily_decisions
    ]
    safe_next_actions = [
        item for item in items if item.category == "safe_next_action" and item.status != "blocked"
    ]
    blocked = [
        item
        for item in items
        if item.category == "blocked_recommendation" or item.status == "blocked"
    ]
    do_not_touch = [_do_not_touch_item(items)] if any(item.blocked_claims for item in items) else []
    return DailyCheckResult(
        workspace_id=WORKSPACE_ID,
        date=date.today(),
        status=_result_status(safe_next_actions, blocked),
        checked_connectors=[ref for ref in connector_refs if ref.status == "checked"],
        skipped_connectors=[ref for ref in connector_refs if ref.status == "skipped"],
        opportunities=safe_next_actions,
        blocked_recommendations=blocked,
        safe_next_actions=safe_next_actions,
        do_not_touch=do_not_touch,
        freshness=_aggregate_freshness(connector_refs),
        workspace_dossier=build_workspace_dossier(),
        recommendation_history=list_recommendation_logs(WORKSPACE_ID)[:20],
    )


def _connector_refs(connectors: list[ConnectorStatus]) -> list[DailyCheckConnectorRef]:
    return [
        DailyCheckConnectorRef(
            connector_id=connector.id,
            status=(
                "checked"
                if connector.configured and connector.status != "disabled"
                else "skipped"
            ),
            freshness=connector.freshness,
            reason=(
                "źródło sprawdzone w bieżącym przebiegu"
                if connector.configured and connector.status != "disabled"
                else "brak dostępu albo źródło wyłączone"
            ),
        )
        for connector in connectors
    ]


def _daily_item(
    decision: DailyDecision,
    *,
    ga4_guard: FalsePositiveGuardResult | None = None,
    content_guard: FalsePositiveGuardResult | None = None,
    content_measurement_guard: _ContentMeasurementGuardContext | None = None,
) -> DailyCheckItem:
    rule_ids = list(_RULE_IDS_BY_DOMAIN.get(decision.domain, ()))
    source_trace_guard = evaluate_source_trace_guard(
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        expert_rule_ids=rule_ids,
        freshness=decision.freshness,
    )
    guards = [source_trace_guard]
    evidence_ids = list(decision.evidence_ids)
    source_connectors = list(decision.source_connectors)
    multi_source_guard = _multi_source_required_guard(decision, rule_ids)
    if multi_source_guard is not None:
        multi_source_result, required_evidence_ids = multi_source_guard
        guards.append(multi_source_result)
        evidence_ids = list(dict.fromkeys([*evidence_ids, *required_evidence_ids]))
    if decision.domain == "ga4" and ga4_guard is not None:
        guards.append(ga4_guard)
    if decision.domain == "content" and content_guard is not None:
        guards.append(content_guard)
    measurement_guards, measurement_evidence, measurement_sources = _measurement_guards(decision)
    guards.extend(measurement_guards)
    evidence_ids = list(dict.fromkeys([*evidence_ids, *measurement_evidence]))
    source_connectors = list(dict.fromkeys([*source_connectors, *measurement_sources]))
    if decision.id == _CONTENT_QUEUE_DECISION_ID and content_measurement_guard is not None:
        guards.append(content_measurement_guard.guard)
        evidence_ids = list(
            dict.fromkeys([*evidence_ids, *content_measurement_guard.evidence_ids])
        )
        source_connectors = list(
            dict.fromkeys(
                [*source_connectors, *content_measurement_guard.source_connectors]
            )
        )
    blocked_guard = next(
        (item for item in guards if item.status == "blocked"),
        source_trace_guard,
    )
    is_blocked = decision.status == "blocked" or blocked_guard.status == "blocked"
    category: Literal["blocked_recommendation", "safe_next_action"] = (
        "blocked_recommendation" if is_blocked else "safe_next_action"
    )
    status: Literal["blocked", "review_required"] = "blocked" if is_blocked else "review_required"
    summary = decision.co_widzimy
    next_step = decision.bezpieczny_next_step
    if blocked_guard.status == "blocked":
        summary = blocked_guard.reason
        next_step = blocked_guard.next_step
    if (
        decision.id == _CONTENT_QUEUE_DECISION_ID
        and content_measurement_guard is not None
    ):
        if content_measurement_guard.queue_density_summary:
            summary = f"{content_measurement_guard.queue_density_summary} {summary}"
        if content_measurement_guard.queue_density_next_step:
            if blocked_guard.status == "blocked":
                next_step = f"{next_step} {content_measurement_guard.queue_density_next_step}"
            else:
                next_step = (
                    f"{next_step} Możesz ręcznie przejrzeć gotowy temat, ale pełna kolejka "
                    f"nie jest jeszcze gotowa. {content_measurement_guard.queue_density_next_step}"
                )
    return DailyCheckItem(
        id=f"daily_check_{decision.id}",
        category=category,
        title=decision.title,
        status=status,
        priority=decision.priority,
        summary=summary,
        next_step=next_step,
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
        expert_rule_ids=rule_ids,
        freshness=decision.freshness,
        action_ids=decision.action_ids,
        blocked_claims=decision.blocked_claims,
        false_positive_guards=[item.guard_id for item in guards],
        risk=decision.risk,
    )


def _measurement_guards(
    decision: DailyDecision,
) -> tuple[list[FalsePositiveGuardResult], list[str], list[str]]:
    guards: list[FalsePositiveGuardResult] = []
    evidence_ids: list[str] = []
    source_connectors: list[str] = []
    if decision.sample_evidence is not None:
        sample = decision.sample_evidence
        guards.append(evaluate_low_volume_guard(sample))
        evidence_ids.extend(sample.evidence_ids)
        source_connectors.append(sample.source_connector)
    if decision.source_comparison_evidence is not None:
        comparison = decision.source_comparison_evidence
        guards.append(evaluate_source_conflict_guard(comparison))
        for value in comparison.values:
            evidence_ids.extend(value.evidence_ids)
            source_connectors.append(value.source_connector)
    return guards, evidence_ids, source_connectors


def _multi_source_required_guard(
    decision: DailyDecision,
    rule_ids: list[str],
) -> tuple[FalsePositiveGuardResult, list[str]] | None:
    if decision.id != _CONTENT_QUEUE_DECISION_ID:
        return None
    multi_source_rules = [
        rule
        for rule_id in rule_ids
        if (rule := get_expert_rule(rule_id)) is not None
        and len(set(rule.required_connectors)) >= 2
    ]
    if len(multi_source_rules) != 1:
        return None
    required_connectors = multi_source_rules[0].required_connectors
    evidence_backed_connectors = [
        fact.source_connector for fact in decision.metric_facts if fact.evidence_id
    ]
    required_evidence_ids = list(
        dict.fromkeys(
            fact.evidence_id
            for fact in decision.metric_facts
            if fact.source_connector in required_connectors and fact.evidence_id
        )
    )
    return (
        evaluate_multi_source_required_guard(
            source_connectors=decision.source_connectors,
            evidence_backed_connectors=evidence_backed_connectors,
            required_connectors=required_connectors,
        ),
        required_evidence_ids,
    )


def _content_measurement_baseline_guard(
    decisions: list[DailyDecision],
) -> _ContentMeasurementGuardContext | None:
    if not any(decision.id == _CONTENT_QUEUE_DECISION_ID for decision in decisions):
        return None
    queue: ContentWorkItemQueueResponse | None = None
    try:
        diagnostics = build_content_diagnostics_cached()
        queue = build_content_work_item_queue_response(diagnostics)
        decisions_by_id = {decision.id: decision for decision in diagnostics.decision_queue}
        baselines = []
        for candidate in queue.candidates:
            if candidate.recommended_mode == "block":
                continue
            decision = decisions_by_id.get(candidate.decision_id)
            if decision is None:
                return _missing_content_measurement_baseline_guard(queue)
            baseline = build_content_opportunity_enrichment(
                decision,
                candidate=candidate,
            ).measurement_baseline
            baselines.append(baseline)
    except Exception:
        return _missing_content_measurement_baseline_guard(queue)
    guard = evaluate_content_measurement_baseline_guard(baselines)
    qualifying_baselines = [
        baseline
        for baseline in baselines
        if baseline.status == "ready_to_plan"
        and baseline.metrics_to_watch
        and baseline.source_connectors
        and baseline.evidence_ids
    ]
    density_note = _content_queue_density_note(queue)
    return _ContentMeasurementGuardContext(
        guard=guard,
        evidence_ids=list(
            dict.fromkeys(
                evidence_id
                for baseline in qualifying_baselines
                for evidence_id in baseline.evidence_ids
            )
        ),
        source_connectors=list(
            dict.fromkeys(
                connector
                for baseline in qualifying_baselines
                for connector in baseline.source_connectors
            )
        ),
        queue_density_summary=None if density_note is None else density_note[0],
        queue_density_next_step=None if density_note is None else density_note[1],
    )


def _missing_content_measurement_baseline_guard(
    queue: ContentWorkItemQueueResponse | None = None,
) -> _ContentMeasurementGuardContext:
    density_note = _content_queue_density_note(queue) if queue is not None else None
    return _ContentMeasurementGuardContext(
        guard=evaluate_content_measurement_baseline_guard([]),
        evidence_ids=[],
        source_connectors=[],
        queue_density_summary=None if density_note is None else density_note[0],
        queue_density_next_step=None if density_note is None else density_note[1],
    )


def _content_queue_density_note(
    queue: ContentWorkItemQueueResponse,
) -> tuple[str, str] | None:
    if not any(
        blocker.code == "not_enough_actionable_candidates" for blocker in queue.blockers
    ):
        return None
    progress = (
        f"{queue.actionable_candidate_count} z "
        f"{queue.minimum_actionable_candidate_count} tematów gotowych do pracy"
    )
    return (
        f"Pełna kolejka pozostaje zablokowana: {progress}.",
        (
            f"Uzupełnij kolejkę do wymaganego minimum ({progress}); odśwież źródła, "
            "zamiast tworzyć sztuczne tematy."
        ),
    )


def _ga4_conversion_guard(
    decisions: list[DailyDecision],
) -> FalsePositiveGuardResult | None:
    if not any(decision.domain == "ga4" for decision in decisions):
        return None
    try:
        contract = build_ga4_diagnostics().conversion_readiness_contract
    except Exception:
        return FalsePositiveGuardResult(
            guard_id="missing_conversion",
            status="blocked",
            reason="Nie udało się potwierdzić kontraktu konwersji GA4.",
            next_step="Najpierw sprawdź dostęp i odczyt GA4.",
        )
    return evaluate_conversion_readiness_guard(contract)


def _content_date_window_guard(
    decisions: list[DailyDecision],
) -> FalsePositiveGuardResult | None:
    if not any(decision.domain == "content" for decision in decisions):
        return None
    try:
        contract = build_content_diagnostics_cached().gsc_search_analytics_contract
    except Exception:
        contract = None
    return evaluate_gsc_date_window_guard(contract)


def _do_not_touch_item(items: list[DailyCheckItem]) -> DailyCheckItem:
    claims = sorted({claim for item in items for claim in item.blocked_claims})
    return DailyCheckItem(
        id="daily_check_do_not_touch_writes",
        category="do_not_touch",
        title="Nie zapisuj zmian bez potwierdzenia w WILQ",
        status="blocked",
        priority=1,
        summary="Brak dowodu i audytu nie jest zgodą na zapis ani publikację.",
        next_step=(
            "Pozostaw write/publish zablokowane i przejdź przez preview, review, "
            "confirm oraz audit."
        ),
        blocked_claims=claims,
        risk=ActionRisk.high,
    )


def _result_status(
    safe_next_actions: list[DailyCheckItem],
    blocked: list[DailyCheckItem],
) -> Literal["ready", "review_ready", "blocked", "degraded"]:
    if blocked:
        return "blocked"
    if safe_next_actions:
        return "review_ready"
    return "degraded"


def _aggregate_freshness(refs: list[DailyCheckConnectorRef]) -> FreshnessState:
    checked_refs = [ref for ref in refs if ref.status == "checked"]
    states = {ref.freshness.state for ref in checked_refs}
    last_success_values = [
        ref.freshness.last_success_at
        for ref in checked_refs
        if ref.freshness.last_success_at is not None
    ]
    aggregate_last_success_at = min(last_success_values) if last_success_values else None
    if "stale" in states:
        return FreshnessState(
            state="stale",
            last_success_at=aggregate_last_success_at,
            notes="co najmniej jedno sprawdzone źródło wymaga odświeżenia",
        )
    if "fresh" in states:
        return FreshnessState(state="fresh", last_success_at=aggregate_last_success_at)
    if "missing" in states:
        return FreshnessState(state="missing", last_success_at=aggregate_last_success_at)
    return FreshnessState(state="unknown", notes="brak potwierdzonego odczytu")
