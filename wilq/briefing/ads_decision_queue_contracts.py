from __future__ import annotations

from collections.abc import Callable

from wilq.briefing.ads_decision_queue import (
    build_budget_context_decision,
    build_change_history_decision,
    build_custom_segments_decision,
    build_impression_share_decision,
    build_negative_keyword_safety_decision,
    build_recommendations_decision,
    build_search_term_ngram_decision,
    build_search_term_safety_decision,
    build_search_terms_decision,
)
from wilq.schemas import (
    AdsBlockedHandoff,
    AdsBudgetPacingReadContract,
    AdsBusinessContextReadContract,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsChangeHistoryReadContract,
    AdsCustomSegmentsReadContract,
    AdsDecisionItem,
    AdsDerivedKpiReadContract,
    AdsDiagnosticSection,
    AdsImpressionShareReadContract,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordsReadContract,
    AdsRecommendationsReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermsReadContract,
)


def build_decision_queue(
    campaign_read_contract: AdsCampaignReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    campaign_triage_read_contract: AdsCampaignTriageReadContract,
    change_history_read_contract: AdsChangeHistoryReadContract,
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
    sections: list[AdsDiagnosticSection],
    blocked_handoff: AdsBlockedHandoff | None,
    action_ids: list[str],
    currency_code: str | None,
    *,
    campaign_context: Callable[..., list[AdsDecisionItem]],
    blocked_queue: Callable[[AdsBlockedHandoff, str | None], list[AdsDecisionItem]],
    safety_decisions: Callable[[list[AdsDiagnosticSection]], list[AdsDecisionItem]],
    remove_available: Callable[..., list[str]],
    with_lineage: Callable[[AdsDecisionItem, str | None], AdsDecisionItem],
) -> list[AdsDecisionItem]:
    if blocked_handoff is not None:
        return blocked_queue(blocked_handoff, currency_code)

    decisions = campaign_context(
        campaign_read_contract,
        business_context_read_contract,
        derived_kpi_read_contract,
        campaign_triage_read_contract,
        action_ids=action_ids,
        campaign_missing_read_contracts=remove_available(
            campaign_read_contract.missing_read_contracts,
            budget_pacing_read_contract,
            recommendations_read_contract,
            impression_share_read_contract,
            change_history_read_contract,
        ),
        derived_missing_read_contracts=remove_available(
            derived_kpi_read_contract.missing_read_contracts,
            budget_pacing_read_contract,
            recommendations_read_contract,
            impression_share_read_contract,
            change_history_read_contract,
        ),
    )
    if budget_pacing_read_contract.budget_rows:
        decisions.append(
            build_budget_context_decision(
                budget_pacing_read_contract,
                action_ids=action_ids,
            )
        )
    if recommendations_read_contract.status == "ready":
        decisions.append(
            build_recommendations_decision(
                recommendations_read_contract,
                action_ids=action_ids,
            )
        )
    if impression_share_read_contract.status == "ready":
        decisions.append(build_impression_share_decision(impression_share_read_contract))
    if change_history_read_contract.status == "ready" or change_history_read_contract.evidence_ids:
        decisions.append(build_change_history_decision(change_history_read_contract))
    if search_terms_read_contract.search_term_rows:
        decisions.append(
            build_search_terms_decision(
                search_terms_read_contract,
                action_ids=action_ids,
            )
        )
    if search_term_ngram_read_contract.ngram_rows:
        decisions.append(build_search_term_ngram_decision(search_term_ngram_read_contract))
    if search_term_safety_read_contract.status == "ready":
        decisions.append(build_search_term_safety_decision(search_term_safety_read_contract))
    if negative_keywords_read_contract.candidates:
        decisions.append(
            build_negative_keyword_safety_decision(
                negative_keywords_read_contract,
                search_term_safety_read_contract,
            )
        )
    if custom_segments_read_contract.candidates:
        decisions.append(build_custom_segments_decision(custom_segments_read_contract))
    decisions.extend(safety_decisions(sections))
    return [with_lineage(decision, currency_code) for decision in decisions]
