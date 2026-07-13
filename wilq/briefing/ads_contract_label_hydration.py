from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from wilq.operator_labels import (
    blocked_claim_count_label,
    missing_contract_count_label,
    required_validation_count_label,
)
from wilq.schemas import AdsDiagnosticsResponse


def hydrate_contract_labels(
    response: AdsDiagnosticsResponse,
    currency_code: str | None,
    *,
    custom_segments: Callable[[Any], None],
    business_context: Callable[[Any], None],
    campaign_triage: Callable[[Any], None],
    optimizer_readiness: Callable[[Any], None],
    change_impact: Callable[[Any], None],
    budget_pacing: Callable[[Any, str | None], None],
    recommendations: Callable[[Any], None],
    impression_share: Callable[[Any], None],
    change_history: Callable[[Any], None],
    negative_keywords: Callable[[Any], None],
    keyword_match_context: Callable[[Any], None],
    unique: Callable[[Iterable[str]], list[str]],
) -> None:
    optimizer_readiness(response.optimizer_readiness_contract)
    change_impact(response.change_impact_readiness_contract)
    custom_segments(response.custom_segments_read_contract)
    business_context(response.business_context_read_contract)
    campaign_triage(response.campaign_triage_read_contract)
    for row in response.derived_kpi_read_contract.kpi_rows:
        row.blocked_claim_labels = unique(row.blocked_claims)
        row.blocked_claim_summary_label = blocked_claim_count_label(
            row.blocked_claim_labels or row.blocked_claims
        )
    budget_pacing(response.budget_pacing_read_contract, currency_code)
    recommendations(response.recommendations_read_contract)
    impression_share(response.impression_share_read_contract)
    change_history(response.change_history_read_contract)
    response.search_term_review_summary_contract.blocked_claim_labels = unique(
        response.search_term_review_summary_contract.blocked_claims
    )
    response.search_term_review_summary_contract.blocked_claim_summary_label = (
        blocked_claim_count_label(
            response.search_term_review_summary_contract.blocked_claim_labels
            or response.search_term_review_summary_contract.blocked_claims
        )
    )
    response.search_term_review_summary_contract.missing_read_contract_summary_label = (
        missing_contract_count_label(
            response.search_term_review_summary_contract.missing_read_contracts
        )
    )
    response.search_term_review_summary_contract.operator_review_gate_summary_label = (
        required_validation_count_label(
            response.search_term_review_summary_contract.operator_review_gate_labels
            or response.search_term_review_summary_contract.operator_review_gates
        )
    )
    negative_keywords(response.negative_keywords_read_contract)
    keyword_match_context(response.keyword_match_context_read_contract)
