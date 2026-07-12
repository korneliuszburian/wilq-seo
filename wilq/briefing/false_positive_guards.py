from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from wilq.operator_labels import source_connector_labels
from wilq.schemas import (
    ContentGscSearchAnalyticsContract,
    FreshnessState,
    Ga4ConversionReadinessContract,
)


class FalsePositiveGuardResult(BaseModel):
    guard_id: str
    status: Literal["pass", "blocked"]
    reason: str
    next_step: str


def evaluate_source_trace_guard(
    *,
    source_connectors: list[str],
    evidence_ids: list[str],
    expert_rule_ids: list[str],
    freshness: FreshnessState,
) -> FalsePositiveGuardResult:
    """Fail closed before a daily recommendation can look actionable."""
    if not source_connectors:
        return _blocked("missing_source_connector", "Brakuje źródła danych dla tej decyzji.")
    if not evidence_ids:
        return _blocked("missing_evidence", "Brakuje dowodu źródłowego dla tej decyzji.")
    if not expert_rule_ids:
        return _blocked("missing_expert_rule", "Brakuje reguły eksperckiej dla tej decyzji.")
    if freshness.state in {"stale", "missing", "unknown"}:
        return _blocked(
            "stale_connector" if freshness.state == "stale" else "missing_source_freshness",
            "Źródło nie ma świeżego, potwierdzonego odczytu.",
        )
    return FalsePositiveGuardResult(
        guard_id="source_trace_ready",
        status="pass",
        reason="Źródło, dowód, reguła i świeżość są potwierdzone.",
        next_step="Można przejść do ręcznego review wskazanej decyzji.",
    )


def evaluate_conversion_readiness_guard(
    contract: Ga4ConversionReadinessContract,
) -> FalsePositiveGuardResult:
    """Use the existing GA4 read contract instead of inferring conversion proof."""
    if contract.status == "ready" and contract.conversion_like_metric_count > 0:
        return FalsePositiveGuardResult(
            guard_id="conversion_readiness_ready",
            status="pass",
            reason="GA4 ma potwierdzone metryki konwersji albo zdarzeń kluczowych.",
            next_step="Można rozdzielić jakość ruchu od problemu pomiaru.",
        )
    return FalsePositiveGuardResult(
        guard_id="missing_conversion",
        status="blocked",
        reason="Brakuje potwierdzonych metryk konwersji albo zdarzeń kluczowych w GA4.",
        next_step=(
            contract.next_step
            or "Najpierw potwierdź mapowanie konwersji i zdarzeń kluczowych w GA4."
        ),
    )


def evaluate_gsc_date_window_guard(
    contract: ContentGscSearchAnalyticsContract | None,
) -> FalsePositiveGuardResult:
    """Require the existing GSC contract to expose a bounded available window."""
    if contract is not None and contract.data_availability_checked:
        has_window = bool(
            contract.aggregate_date_start
            and contract.aggregate_date_end
            and contract.latest_available_detail_date
        )
        if has_window and contract.detail_data_completeness:
            return FalsePositiveGuardResult(
                guard_id="date_window_ready",
                status="pass",
                reason="GSC ma potwierdzony zakres dat i opis kompletności odczytu.",
                next_step="Można porównać decyzję w ramach tego okna danych.",
            )
    return FalsePositiveGuardResult(
        guard_id="date_window",
        status="blocked",
        reason="GSC nie potwierdza kompletnego, ograniczonego zakresu dat dla tej decyzji.",
        next_step="Najpierw sprawdź dostępny zakres dat i kompletność odczytu GSC.",
    )


def evaluate_multi_source_required_guard(
    *,
    source_connectors: list[str],
    evidence_backed_connectors: list[str],
    required_connectors: list[str],
) -> FalsePositiveGuardResult:
    """Require typed fact-and-evidence coverage for every rule-required source."""
    required = list(dict.fromkeys(connector for connector in required_connectors if connector))
    declared = set(source_connectors)
    evidence_backed = set(evidence_backed_connectors)
    missing = [
        connector
        for connector in required
        if connector not in declared or connector not in evidence_backed
    ]
    if missing:
        labels = ", ".join(source_connector_labels(missing))
        return FalsePositiveGuardResult(
            guard_id="multi_source_required",
            status="blocked",
            reason=f"Brakuje potwierdzonego dowodu z wymaganego źródła: {labels}.",
            next_step=f"Odśwież {labels} w WILQ przed ręcznym review tej decyzji.",
        )
    return FalsePositiveGuardResult(
        guard_id="multi_source_ready",
        status="pass",
        reason="Każde źródło wymagane przez regułę ma własny potwierdzony dowód.",
        next_step="Można przejść do ręcznego review wskazanej decyzji.",
    )


def _blocked(guard_id: str, reason: str) -> FalsePositiveGuardResult:
    return FalsePositiveGuardResult(
        guard_id=guard_id,
        status="blocked",
        reason=reason,
        next_step="Najpierw potwierdź źródło, dowód i świeżość w WILQ.",
    )
