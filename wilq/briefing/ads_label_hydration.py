from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
    evidence_count_label,
    missing_contract_count_label,
    required_validation_count_label,
    source_connector_labels,
)
from wilq.schemas import AdsDiagnosticsResponse


def hydrate_review_gate_labels(
    response: AdsDiagnosticsResponse,
    *,
    review_gate_labels: Callable[[list[str]], list[str]],
) -> None:
    operator_gate_owners: list[Any] = [
        response.business_context_read_contract,
        response.recommendations_read_contract,
        response.optimizer_readiness_contract,
        *response.optimizer_readiness_contract.readiness_items,
        response.search_terms_read_contract,
        response.search_term_review_summary_contract,
        response.search_term_ngram_read_contract,
        response.search_term_safety_read_contract,
        response.keyword_match_context_read_contract,
        response.keyword_planner_read_contract,
        response.custom_segments_read_contract,
        response.custom_segments_read_contract.audience_forecast_read_contract,
        response.operator_summary,
        *response.decision_queue,
    ]
    for owner in operator_gate_owners:
        owner.operator_review_gate_labels = review_gate_labels(owner.operator_review_gates)
        if hasattr(owner, "operator_review_gate_summary_label"):
            owner.operator_review_gate_summary_label = required_validation_count_label(
                owner.operator_review_gate_labels or owner.operator_review_gates
            )

    human_gate_owners: list[Any] = [
        *response.campaign_read_contract.campaign_rows,
        *response.recommendations_read_contract.recommendation_rows,
        *response.campaign_triage_read_contract.triage_rows,
        *response.custom_segments_read_contract.candidates,
        *response.negative_keywords_read_contract.candidates,
    ]
    for owner in human_gate_owners:
        owner.human_review_gate_labels = review_gate_labels(owner.human_review_gates)
        if hasattr(owner, "human_review_gate_summary_label"):
            owner.human_review_gate_summary_label = required_validation_count_label(
                owner.human_review_gate_labels or owner.human_review_gates
            )


def hydrate_summary_labels(
    response: AdsDiagnosticsResponse,
    *,
    missing_contract_labels: Callable[[list[str]], list[str]],
    allowed_metric_labels: Callable[[list[str]], list[str]],
    unique: Callable[[Iterable[str]], list[str]],
) -> None:
    response.evidence_summary_label = evidence_count_label(response.evidence_ids)
    response.source_connector_labels = source_connector_labels(
        response.operator_summary.source_connectors
    )
    response.action_summary_label = action_count_label(response.action_ids)
    response.operator_summary.source_connector_labels = source_connector_labels(
        response.operator_summary.source_connectors
    )
    response.operator_summary.evidence_summary_label = evidence_count_label(
        response.operator_summary.evidence_ids
    )
    response.operator_summary.action_summary_label = action_count_label(
        response.operator_summary.action_ids
    )
    response.operator_summary.missing_read_contract_labels = missing_contract_labels(
        response.operator_summary.missing_read_contracts
    )
    response.operator_summary.missing_read_contract_summary_label = missing_contract_count_label(
        response.operator_summary.missing_read_contracts
    )
    response.operator_summary.allowed_metric_labels = allowed_metric_labels(
        response.operator_summary.allowed_metrics
    )
    response.operator_summary.blocked_claim_labels = unique(
        response.operator_summary.blocked_claims
    )
    response.operator_summary.blocked_claim_summary_label = blocked_claim_count_label(
        response.operator_summary.blocked_claim_labels or response.operator_summary.blocked_claims
    )
    response.operator_summary.top_blocked_claim_labels = unique(
        response.operator_summary.top_blocked_claim_labels
        or response.operator_summary.blocked_claim_labels
    )[:5]
    response.operator_summary.top_blocked_claim_summary_label = blocked_claim_count_label(
        response.operator_summary.top_blocked_claim_labels
    )


def hydrate_decision_labels(
    response: AdsDiagnosticsResponse,
    currency_code: str | None,
    *,
    status_label: Callable[[str], str],
    decision_type_label: Callable[[str], str],
    priority_label: Callable[[int], str],
    start_here_summary: Callable[[Any, str | None], str],
    measurement_plan: Callable[[Any], str],
    risk_label: Callable[[str], str],
    missing_contract_labels: Callable[[list[str]], list[str]],
    unique: Callable[[Iterable[str]], list[str]],
) -> None:
    response.decision_queue = [
        decision.model_copy(
            update={
                "status_label": status_label(decision.status),
                "decision_type_label": decision_type_label(decision.decision_type),
                "priority_label": priority_label(decision.priority),
                "start_here_summary": start_here_summary(decision, currency_code),
                "measurement_plan": measurement_plan(decision),
                "risk_label": risk_label(decision.risk),
                "source_connector_labels": source_connector_labels(decision.source_connectors),
                "evidence_summary_label": evidence_count_label(decision.evidence_ids),
                "action_summary_label": action_count_label(decision.action_ids),
                "missing_read_contract_labels": missing_contract_labels(
                    decision.missing_read_contracts
                ),
                "missing_read_contract_summary_label": missing_contract_count_label(
                    decision.missing_read_contracts
                ),
                "blocked_claim_labels": unique(decision.blocked_claims),
                "blocked_claim_summary_label": blocked_claim_count_label(
                    unique(decision.blocked_claims)
                ),
                "operator_review_gate_summary_label": required_validation_count_label(
                    decision.operator_review_gate_labels or decision.operator_review_gates
                ),
            }
        )
        for decision in response.decision_queue
    ]


def hydrate_surface_labels(
    response: AdsDiagnosticsResponse,
    *,
    status_label: Callable[[str], str],
    unique: Callable[[Iterable[str]], list[str]],
) -> None:
    response.sections = [
        section.model_copy(
            update={
                "status_label": status_label(section.status),
                "source_connector_labels": source_connector_labels(section.source_connectors),
                "evidence_summary_label": evidence_count_label(section.evidence_ids),
                "action_summary_label": action_count_label(section.action_ids),
                "blocked_claim_labels": unique(section.blocked_claims),
            }
        )
        for section in response.sections
    ]
    if response.blocked_handoff is not None:
        response.blocked_handoff = response.blocked_handoff.model_copy(
            update={
                "status_label": status_label(response.blocked_handoff.status),
                "source_connector_labels": source_connector_labels(
                    response.blocked_handoff.source_connectors
                ),
                "evidence_summary_label": evidence_count_label(
                    response.blocked_handoff.evidence_ids
                ),
                "action_summary_label": action_count_label(response.blocked_handoff.action_ids),
                "blocked_claim_labels": unique(response.blocked_handoff.blocked_claims),
            }
        )
