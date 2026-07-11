from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from wilq.schemas import FreshnessState, Ga4ConversionReadinessContract


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


def _blocked(guard_id: str, reason: str) -> FalsePositiveGuardResult:
    return FalsePositiveGuardResult(
        guard_id=guard_id,
        status="blocked",
        reason=reason,
        next_step="Najpierw potwierdź źródło, dowód i świeżość w WILQ.",
    )
