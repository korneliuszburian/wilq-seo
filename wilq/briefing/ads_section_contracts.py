from __future__ import annotations

from collections.abc import Callable

from wilq.briefing.ads_budget_pacing import build_budget_pacing_section
from wilq.briefing.ads_campaigns import (
    build_business_context_section,
    build_campaign_overview_section,
    build_derived_kpi_section,
)
from wilq.briefing.ads_change_history import build_change_history_section
from wilq.briefing.ads_custom_segments import build_custom_segments_section
from wilq.briefing.ads_impression_share import build_impression_share_section
from wilq.briefing.ads_keyword_planner import build_keyword_planner_section
from wilq.briefing.ads_negative_keywords import build_negative_keywords_section
from wilq.briefing.ads_recommendations import build_recommendations_section
from wilq.briefing.ads_search_terms import (
    build_keyword_match_context_section,
    build_search_term_ngram_section,
    build_search_term_safety_section,
    build_search_terms_section,
)
from wilq.schemas import (
    AdsBudgetPacingReadContract,
    AdsBusinessContextReadContract,
    AdsCampaignReadContract,
    AdsChangeHistoryReadContract,
    AdsCustomSegmentsReadContract,
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
    ConnectorRefreshRun,
    MetricFact,
)


def build_diagnostic_sections(
    *,
    action_ids: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    trusted_metric_facts: list[MetricFact],
    live_data_available: bool,
    campaign_read_contract: AdsCampaignReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    change_history_read_contract: AdsChangeHistoryReadContract,
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
    oauth_or_live: Callable[
        [ConnectorRefreshRun | None, list[MetricFact], list[str]], AdsDiagnosticSection
    ],
    fallback_evidence_ids: Callable[[ConnectorRefreshRun | None], list[str]],
    safe_action: Callable[
        [list[str], ConnectorRefreshRun | None, bool], AdsDiagnosticSection
    ],
    with_lineage: Callable[[AdsDiagnosticSection], AdsDiagnosticSection],
) -> list[AdsDiagnosticSection]:
    sections = [
        oauth_or_live(latest_refresh, trusted_metric_facts, action_ids),
        build_campaign_overview_section(
            action_ids,
            campaign_read_contract,
            fallback_evidence_ids=fallback_evidence_ids(latest_refresh),
        ),
        build_business_context_section(business_context_read_contract),
        build_derived_kpi_section(derived_kpi_read_contract),
        build_budget_pacing_section(budget_pacing_read_contract),
        build_recommendations_section(recommendations_read_contract),
        build_impression_share_section(impression_share_read_contract),
        build_change_history_section(change_history_read_contract),
        build_search_terms_section(search_terms_read_contract, action_ids),
        build_search_term_ngram_section(search_term_ngram_read_contract),
        build_search_term_safety_section(search_term_safety_read_contract),
        build_keyword_match_context_section(keyword_match_context_read_contract),
        build_keyword_planner_section(keyword_planner_read_contract, action_ids),
        build_custom_segments_section(custom_segments_read_contract),
        build_negative_keywords_section(negative_keywords_read_contract),
        safe_action(action_ids, latest_refresh, live_data_available),
    ]
    return [with_lineage(section) for section in sections]
