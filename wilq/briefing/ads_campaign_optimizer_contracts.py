from __future__ import annotations

from collections.abc import Callable

from wilq.briefing.ads_optimizer import build_optimizer_readiness_contract
from wilq.schemas import (
    AdsBudgetPacingReadContract,
    AdsBusinessContextReadContract,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsChangeHistoryReadContract,
    AdsChangeImpactReadinessContract,
    AdsCustomSegmentsReadContract,
    AdsDerivedKpiReadContract,
    AdsImpressionShareReadContract,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordsReadContract,
    AdsOptimizerReadinessContract,
    AdsRecommendationsReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
)


def build_campaign_optimizer_contracts(
    campaign_read_contract: AdsCampaignReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    action_ids: list[str],
    change_history_read_contract: AdsChangeHistoryReadContract,
    change_impact_readiness_contract: AdsChangeImpactReadinessContract,
    search_term_review_summary_contract: AdsSearchTermReviewSummaryContract,
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
    *,
    campaign_triage: Callable[..., AdsCampaignTriageReadContract],
) -> tuple[AdsCampaignTriageReadContract, AdsOptimizerReadinessContract]:
    campaign_triage_read_contract = campaign_triage(
        campaign_read_contract,
        business_context_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        action_ids,
    )
    optimizer_readiness_contract = build_optimizer_readiness_contract(
        campaign_triage_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        change_history_read_contract,
        change_impact_readiness_contract,
        search_term_review_summary_contract,
        search_term_ngram_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
        keyword_planner_read_contract,
        custom_segments_read_contract,
        negative_keywords_read_contract,
    )
    return campaign_triage_read_contract, optimizer_readiness_contract
