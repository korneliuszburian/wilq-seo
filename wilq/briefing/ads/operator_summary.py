from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
    ads_business_context_configured,
    ads_business_context_missing_read_contracts,
    ads_strategy_review_state,
    ads_target_guardrail_values,
)
from wilq.actions.google_ads.campaign_review import (
    CAMPAIGN_REVIEW_ACTION_ID,
)
from wilq.actions.google_ads.change_history import CHANGE_HISTORY_IMPACT_ACTION_ID
from wilq.actions.google_ads.custom_segments import (
    CUSTOM_SEGMENT_ACTION_ID,
)
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.negative_keywords import (
    NEGATIVE_KEYWORD_ACTION_ID,
)
from wilq.actions.google_ads.recommendations import (
    RECOMMENDATION_REVIEW_ACTION_ID,
)
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID
from wilq.briefing.ads_business_context_contracts import (
    business_context_contract_state,
    business_context_policy_ids,
    business_context_read_metric_tiles,
    business_context_review_gates,
    business_context_summary_and_next_step,
    business_target_interpretation,
    strategy_review_readiness_contract,
)
from wilq.briefing.ads_contract_label_hydration import hydrate_contract_labels
from wilq.briefing.ads_decision_queue import (
    build_block_write_actions_decision,
    build_business_context_decision,
    build_campaign_activity_decision,
    build_campaign_triage_decision,
    build_derived_kpi_decision,
    decision_priority,
)
from wilq.briefing.ads_decision_queue_contracts import build_decision_queue
from wilq.briefing.ads_freshness import (
    ads_freshness_assessment,
    as_utc,
    connector_refresh_recency_key,
    latest_google_ads_refresh,
)
from wilq.briefing.ads_label_hydration import (
    hydrate_decision_labels,
    hydrate_review_gate_labels,
    hydrate_summary_labels,
    hydrate_surface_labels,
)
from wilq.briefing.ads_metric_tiles import (
    budget_context_metric_tiles,
    business_context_metric_tiles,
    campaign_activity_metric_tiles,
    campaign_triage_metric_tiles,
    change_history_metric_tiles,
    custom_segments_metric_tiles,
    derived_kpi_metric_tiles,
    impression_share_metric_tiles,
    negative_keyword_safety_metric_tiles,
    recommendations_metric_tiles,
    safety_blocker_metric_tiles,
    search_term_ngram_metric_tiles,
    search_term_safety_metric_tiles,
    search_terms_metric_tiles,
)
from wilq.briefing.ads_primary_contracts import build_primary_read_contracts
from wilq.briefing.ads_response_assembly import build_diagnostics_response
from wilq.briefing.ads_section_contracts import build_diagnostic_sections
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.content.operator_copy import unique
from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
    evidence_count_label,
    missing_contract_count_label,
    required_validation_count_label,
    source_connector_labels,
)
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    AdsAccountCurrencyReadContract,
    AdsAggregationContract,
    AdsBlockedHandoff,
    AdsBudgetPacingReadContract,
    AdsBusinessContextReadContract,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsChangeHistoryReadContract,
    AdsChangeImpactReadinessContract,
    AdsCustomSegmentsReadContract,
    AdsDecisionItem,
    AdsDerivedKpiReadContract,
    AdsDiagnosticSection,
    AdsDiagnosticsResponse,
    AdsFreshnessAssessment,
    AdsImpressionShareReadContract,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordsReadContract,
    AdsOperatorSummary,
    AdsOptimizerReadinessContract,
    AdsRecommendationsReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermsReadContract,
    ConnectorRefreshRun,
    ConnectorStatus,
    DiagnosticDataReadiness,
    MetricFact,
    connector_refresh_has_live_data,
)

from .budget import (
    _derived_kpi_read_contract,
    _hydrate_budget_pacing_marketer_labels,
    _profit_margin_env,
    _text_env,
)
from .campaigns import (
    _ads_optimizer_mode_label,
    _ads_optimizer_readiness_item_label,
    _ads_optimizer_status_label,
    _campaign_read_contract,
    _change_history_with_action_ids,
    _change_impact_readiness_contract,
    _hydrate_campaign_triage_marketer_labels,
    _hydrate_change_history_marketer_labels,
    _hydrate_change_impact_marketer_labels,
    _hydrate_impression_share_marketer_labels,
    _hydrate_recommendations_marketer_labels,
)
from .custom_segments import (
    _build_ads_candidate_read_contracts,
    _hydrate_custom_segments_marketer_labels,
)
from .demand_gen import DEMAND_GEN_READINESS_REVIEW_ACTION_ID
from .labels import (
    _ads_allowed_metric_labels,
    _ads_business_context_status_label,
    _ads_business_use_labels,
    _ads_connector_status_label,
    _ads_decision_measurement_plan,
    _ads_decision_start_here_summary,
    _ads_decision_type_label,
    _ads_live_data_status_label,
    _ads_missing_read_contract_labels,
    _ads_priority_label,
    _ads_refresh_status_label,
    _ads_review_gate_labels,
    _ads_risk_label,
    _ads_status_label,
    _ads_strategy_review_status_label,
)
from .negative_keywords import (
    _hydrate_keyword_match_context_marketer_labels,
    _hydrate_negative_keywords_marketer_labels,
)
from .shared import (
    ADS_SUMMARY_VIEW_ROW_LIMIT,
    GOOGLE_ADS_CONNECTOR_ID,
    _latest_refresh_has_summary_metric,
    _refresh_or_connector_evidence_ids,
    _remove_missing_contract_names,
)

GOOGLE_ADS_OAUTH_REPAIR_ACTION_ID = "act_configure_google_ads_env"


GOOGLE_ADS_DIAGNOSTIC_ACTION_IDS = [
    GOOGLE_ADS_OAUTH_REPAIR_ACTION_ID,
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    KEYWORD_PLANNER_ACCESS_ACTION_ID,
    CAMPAIGN_REVIEW_ACTION_ID,
    RECOMMENDATION_REVIEW_ACTION_ID,
    CHANGE_HISTORY_IMPACT_ACTION_ID,
    SEARCH_TERM_NGRAM_ACTION_ID,
    CUSTOM_SEGMENT_ACTION_ID,
    NEGATIVE_KEYWORD_ACTION_ID,
]


CARD_GOAL_001_RULES = "card_goal_001_rules"


CARD_ADS_SEARCH = "card_google_ads_search_playbook"


CARD_ADS_BUDGET_REVIEW = "card_google_ads_budget_review_playbook"


CARD_ADS_NEGATIVE_KEYWORDS = "card_google_ads_negative_keywords_playbook"


CARD_ADS_CUSTOM_SEGMENTS = "card_google_ads_custom_segments_playbook"


ADS_SECTION_LINEAGE: dict[str, tuple[list[str], list[str]]] = {
    "ads_live_data_status": (
        [CARD_ADS_SEARCH, CARD_GOAL_001_RULES],
        ["ads_diagnostics_v1", "ads_principles_v1", "ads_platform_traps_v1"],
    ),
    "ads_oauth_blocker": (
        [CARD_GOAL_001_RULES],
        ["ads_principles_v1"],
    ),
    "ads_campaign_overview": (
        [CARD_ADS_SEARCH, CARD_ADS_BUDGET_REVIEW],
        ["ads_diagnostics_v1", "ads_scaling_candidates_v1", "ads_recommendations_v1"],
    ),
    "ads_business_context": (
        [CARD_ADS_BUDGET_REVIEW, CARD_GOAL_001_RULES],
        ["ads_scaling_candidates_v1", "ads_principles_v1"],
    ),
    "ads_derived_kpi": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_diagnostics_v1", "ads_scaling_candidates_v1", "ads_recommendations_v1"],
    ),
    "ads_budget_pacing": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_scaling_candidates_v1", "ads_recommendations_v1", "ads_principles_v1"],
    ),
    "ads_recommendations": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_recommendations_v1", "ads_principles_v1"],
    ),
    "ads_impression_share": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_scaling_candidates_v1", "ads_principles_v1"],
    ),
    "ads_change_history": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_diagnostics_v1", "ads_principles_v1"],
    ),
    "ads_search_terms": (
        [CARD_ADS_SEARCH, CARD_ADS_NEGATIVE_KEYWORDS, CARD_ADS_CUSTOM_SEGMENTS],
        ["ads_search_terms_v1", "ads_negative_keywords_v1", "ads_custom_segments_v1"],
    ),
    "ads_search_term_ngrams": (
        [CARD_ADS_SEARCH, CARD_ADS_NEGATIVE_KEYWORDS],
        ["ads_search_terms_v1", "ads_negative_keywords_v1"],
    ),
    "ads_search_term_safety": (
        [CARD_ADS_NEGATIVE_KEYWORDS, CARD_ADS_SEARCH],
        ["ads_negative_keywords_v1", "ads_search_terms_v1", "ads_principles_v1"],
    ),
    "ads_keyword_match_context": (
        [CARD_ADS_NEGATIVE_KEYWORDS, CARD_ADS_SEARCH],
        ["ads_negative_keywords_v1", "ads_search_terms_v1", "ads_principles_v1"],
    ),
    "ads_keyword_planner": (
        [CARD_ADS_CUSTOM_SEGMENTS],
        ["ads_custom_segments_v1", "ads_keyword_planner_v1"],
    ),
    "ads_custom_segments": (
        [CARD_ADS_CUSTOM_SEGMENTS],
        ["ads_custom_segments_v1", "ads_keyword_planner_v1"],
    ),
    "ads_negative_keyword_safety": (
        [CARD_ADS_NEGATIVE_KEYWORDS, CARD_ADS_SEARCH],
        ["ads_negative_keywords_v1", "ads_search_terms_v1"],
    ),
    "ads_action_safety": (
        [CARD_GOAL_001_RULES],
        ["ads_principles_v1"],
    ),
}


ADS_DECISION_LINEAGE: dict[str, tuple[list[str], list[str]]] = {
    "ads_fix_access_before_analysis": (
        [CARD_GOAL_001_RULES],
        ["ads_principles_v1"],
    ),
    "ads_review_campaign_activity": (
        [CARD_ADS_SEARCH, CARD_ADS_BUDGET_REVIEW],
        ["ads_diagnostics_v1", "ads_scaling_candidates_v1", "ads_recommendations_v1"],
    ),
    "ads_review_campaign_triage": (
        [CARD_ADS_SEARCH, CARD_ADS_BUDGET_REVIEW],
        ["ads_diagnostics_v1", "ads_scaling_candidates_v1", "ads_recommendations_v1"],
    ),
    "ads_review_business_context": (
        [CARD_ADS_BUDGET_REVIEW, CARD_GOAL_001_RULES],
        ["ads_scaling_candidates_v1", "ads_principles_v1"],
    ),
    "ads_review_derived_kpis": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_diagnostics_v1", "ads_scaling_candidates_v1", "ads_recommendations_v1"],
    ),
    "ads_review_budget_context": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_scaling_candidates_v1", "ads_recommendations_v1", "ads_principles_v1"],
    ),
    "ads_review_recommendations": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_recommendations_v1", "ads_principles_v1"],
    ),
    "ads_review_impression_share": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_scaling_candidates_v1", "ads_principles_v1"],
    ),
    "ads_review_change_history": (
        [CARD_ADS_BUDGET_REVIEW],
        ["ads_diagnostics_v1", "ads_principles_v1"],
    ),
    "ads_review_search_terms": (
        [CARD_ADS_SEARCH, CARD_ADS_NEGATIVE_KEYWORDS, CARD_ADS_CUSTOM_SEGMENTS],
        ["ads_search_terms_v1", "ads_negative_keywords_v1", "ads_custom_segments_v1"],
    ),
    "ads_review_search_term_ngrams": (
        [CARD_ADS_SEARCH, CARD_ADS_NEGATIVE_KEYWORDS],
        ["ads_search_terms_v1", "ads_negative_keywords_v1"],
    ),
    "ads_review_search_term_safety": (
        [CARD_ADS_NEGATIVE_KEYWORDS, CARD_ADS_SEARCH],
        ["ads_negative_keywords_v1", "ads_search_terms_v1", "ads_principles_v1"],
    ),
    "ads_review_negative_keyword_safety": (
        [CARD_ADS_NEGATIVE_KEYWORDS, CARD_ADS_SEARCH],
        ["ads_negative_keywords_v1", "ads_search_terms_v1"],
    ),
    "ads_prepare_custom_segments_from_search_terms": (
        [CARD_ADS_CUSTOM_SEGMENTS],
        ["ads_custom_segments_v1", "ads_keyword_planner_v1"],
    ),
    "ads_block_write_actions_without_actionobject": (
        [CARD_GOAL_001_RULES],
        ["ads_principles_v1"],
    ),
}


def _build_ads_diagnostic_sections(
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
) -> list[AdsDiagnosticSection]:
    return build_diagnostic_sections(
        action_ids=action_ids,
        latest_refresh=latest_refresh,
        trusted_metric_facts=trusted_metric_facts,
        live_data_available=live_data_available,
        campaign_read_contract=campaign_read_contract,
        business_context_read_contract=business_context_read_contract,
        derived_kpi_read_contract=derived_kpi_read_contract,
        budget_pacing_read_contract=budget_pacing_read_contract,
        recommendations_read_contract=recommendations_read_contract,
        impression_share_read_contract=impression_share_read_contract,
        change_history_read_contract=change_history_read_contract,
        search_terms_read_contract=search_terms_read_contract,
        search_term_ngram_read_contract=search_term_ngram_read_contract,
        search_term_safety_read_contract=search_term_safety_read_contract,
        keyword_match_context_read_contract=keyword_match_context_read_contract,
        keyword_planner_read_contract=keyword_planner_read_contract,
        custom_segments_read_contract=custom_segments_read_contract,
        negative_keywords_read_contract=negative_keywords_read_contract,
        oauth_or_live=_oauth_or_live_section,
        fallback_evidence_ids=_refresh_or_connector_evidence_ids,
        safe_action=lambda ids, refresh, live: _safe_action_section(
            ids, refresh, live_data_available=live
        ),
        with_lineage=_with_ads_section_lineage,
    )


def _build_ads_sections_and_blocked_handoff(
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
) -> tuple[list[AdsDiagnosticSection], AdsBlockedHandoff | None]:
    sections = _build_ads_diagnostic_sections(
        action_ids=action_ids,
        latest_refresh=latest_refresh,
        trusted_metric_facts=trusted_metric_facts,
        live_data_available=live_data_available,
        campaign_read_contract=campaign_read_contract,
        business_context_read_contract=business_context_read_contract,
        derived_kpi_read_contract=derived_kpi_read_contract,
        budget_pacing_read_contract=budget_pacing_read_contract,
        recommendations_read_contract=recommendations_read_contract,
        impression_share_read_contract=impression_share_read_contract,
        change_history_read_contract=change_history_read_contract,
        search_terms_read_contract=search_terms_read_contract,
        search_term_ngram_read_contract=search_term_ngram_read_contract,
        search_term_safety_read_contract=search_term_safety_read_contract,
        keyword_match_context_read_contract=keyword_match_context_read_contract,
        keyword_planner_read_contract=keyword_planner_read_contract,
        custom_segments_read_contract=custom_segments_read_contract,
        negative_keywords_read_contract=negative_keywords_read_contract,
    )
    blocked_handoff = _blocked_handoff(live_data_available, latest_refresh, sections, action_ids)
    return sections, blocked_handoff


def _build_ads_decision_queue_response(
    *,
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
) -> list[AdsDecisionItem]:
    return _ads_decision_queue(
        campaign_read_contract,
        business_context_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        campaign_triage_read_contract,
        change_history_read_contract,
        search_terms_read_contract,
        search_term_ngram_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
        keyword_planner_read_contract,
        custom_segments_read_contract,
        negative_keywords_read_contract,
        sections,
        blocked_handoff,
        action_ids,
        currency_code,
    )


def _build_ads_diagnostics_response(
    *,
    connector: ConnectorStatus,
    latest_refresh: ConnectorRefreshRun | None,
    live_data_available: bool,
    data_readiness: DiagnosticDataReadiness,
    account_currency_read_contract: AdsAccountCurrencyReadContract,
    campaign_read_contract: AdsCampaignReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    campaign_triage_read_contract: AdsCampaignTriageReadContract,
    optimizer_readiness_contract: AdsOptimizerReadinessContract,
    change_history_read_contract: AdsChangeHistoryReadContract,
    change_impact_readiness_contract: AdsChangeImpactReadinessContract,
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_review_summary_contract: AdsSearchTermReviewSummaryContract,
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
    decision_queue: list[AdsDecisionItem],
    sections: list[AdsDiagnosticSection],
    blocked_handoff: AdsBlockedHandoff | None,
) -> AdsDiagnosticsResponse:
    return build_diagnostics_response(
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        data_readiness=data_readiness,
        account_currency_read_contract=account_currency_read_contract,
        campaign_read_contract=campaign_read_contract,
        business_context_read_contract=business_context_read_contract,
        derived_kpi_read_contract=derived_kpi_read_contract,
        budget_pacing_read_contract=budget_pacing_read_contract,
        recommendations_read_contract=recommendations_read_contract,
        impression_share_read_contract=impression_share_read_contract,
        campaign_triage_read_contract=campaign_triage_read_contract,
        optimizer_readiness_contract=optimizer_readiness_contract,
        change_history_read_contract=change_history_read_contract,
        change_impact_readiness_contract=change_impact_readiness_contract,
        search_terms_read_contract=search_terms_read_contract,
        search_term_review_summary_contract=search_term_review_summary_contract,
        search_term_ngram_read_contract=search_term_ngram_read_contract,
        search_term_safety_read_contract=search_term_safety_read_contract,
        keyword_match_context_read_contract=keyword_match_context_read_contract,
        keyword_planner_read_contract=keyword_planner_read_contract,
        custom_segments_read_contract=custom_segments_read_contract,
        negative_keywords_read_contract=negative_keywords_read_contract,
        decision_queue=decision_queue,
        sections=sections,
        blocked_handoff=blocked_handoff,
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector_status_label=_ads_connector_status_label,
        refresh_status_label=_ads_refresh_status_label,
        live_data_status_label=_ads_live_data_status_label,
        freshness_assessment=_ads_freshness_assessment,
        operator_summary=_operator_summary,
        unique=unique,
    )


def _build_ads_primary_read_contracts(
    trusted_metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> tuple[
    AdsAccountCurrencyReadContract,
    AdsBusinessContextReadContract,
    AdsCampaignReadContract,
    AdsDerivedKpiReadContract,
    AdsBudgetPacingReadContract,
    AdsRecommendationsReadContract,
    AdsImpressionShareReadContract,
    AdsChangeHistoryReadContract,
]:
    return build_primary_read_contracts(
        trusted_metric_facts,
        latest_refresh,
        account_currency=_account_currency_read_contract,
        business_context=_business_context_read_contract,
        campaign=_campaign_read_contract,
        derived_kpi=_derived_kpi_read_contract,
        fallback_evidence_ids=_refresh_or_connector_evidence_ids,
        latest_refresh_has_summary_metric=_latest_refresh_has_summary_metric,
    )


def _build_ads_action_enriched_contracts(
    *,
    action_ids: list[str],
    business_context_read_contract: AdsBusinessContextReadContract,
    change_history_read_contract: AdsChangeHistoryReadContract,
    campaign_read_contract: AdsCampaignReadContract,
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
) -> tuple[
    AdsBusinessContextReadContract,
    AdsChangeHistoryReadContract,
    AdsChangeImpactReadinessContract,
    AdsSearchTermNgramReadContract,
    AdsCustomSegmentsReadContract,
    AdsNegativeKeywordsReadContract,
]:
    business_context_read_contract = _business_context_with_action_ids(
        business_context_read_contract,
        action_ids,
    )
    change_history_read_contract = _change_history_with_action_ids(
        change_history_read_contract,
        action_ids,
    )
    change_impact_readiness_contract = _change_impact_readiness_contract(
        change_history_read_contract,
        campaign_read_contract,
    )
    search_term_ngram_read_contract = _search_term_ngram_with_action_ids(
        search_term_ngram_read_contract,
        action_ids,
    )
    (
        custom_segments_read_contract,
        negative_keywords_read_contract,
    ) = _build_ads_candidate_read_contracts(
        search_terms_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
        keyword_planner_read_contract,
        action_ids,
    )
    return (
        business_context_read_contract,
        change_history_read_contract,
        change_impact_readiness_contract,
        search_term_ngram_read_contract,
        custom_segments_read_contract,
        negative_keywords_read_contract,
    )


def _hydrate_ads_response_labels(response: AdsDiagnosticsResponse) -> None:
    """Apply review-gate and marketer labels after response construction."""
    _hydrate_ads_review_gate_labels(response)
    _hydrate_ads_marketer_labels(response)


def _reconcile_ads_recommendation_and_impression_contracts(
    campaign_read_contract: AdsCampaignReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
) -> tuple[
    AdsCampaignReadContract,
    AdsDerivedKpiReadContract,
    AdsBudgetPacingReadContract,
    AdsRecommendationsReadContract,
    AdsImpressionShareReadContract,
]:
    if recommendations_read_contract.status == "ready":
        campaign_read_contract = campaign_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    campaign_read_contract.missing_read_contracts,
                    "recommendations",
                )
            }
        )
        derived_kpi_read_contract = derived_kpi_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    derived_kpi_read_contract.missing_read_contracts,
                    "recommendations",
                )
            }
        )
        budget_pacing_read_contract = budget_pacing_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    budget_pacing_read_contract.missing_read_contracts,
                    "recommendations",
                )
            }
        )
    if impression_share_read_contract.status == "ready":
        campaign_read_contract = campaign_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    campaign_read_contract.missing_read_contracts,
                    "impression_share",
                )
            }
        )
        derived_kpi_read_contract = derived_kpi_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    derived_kpi_read_contract.missing_read_contracts,
                    "impression_share",
                )
            }
        )
        budget_pacing_read_contract = budget_pacing_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    budget_pacing_read_contract.missing_read_contracts,
                    "impression_share",
                )
            }
        )
        recommendations_read_contract = recommendations_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    recommendations_read_contract.missing_read_contracts,
                    "impression_share",
                )
            }
        )
    return (
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
    )


def _reconcile_ads_change_history_contracts(
    campaign_read_contract: AdsCampaignReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    change_history_read_contract: AdsChangeHistoryReadContract,
) -> tuple[
    AdsCampaignReadContract,
    AdsDerivedKpiReadContract,
    AdsBudgetPacingReadContract,
    AdsRecommendationsReadContract,
    AdsImpressionShareReadContract,
]:
    if "change_history" not in change_history_read_contract.missing_read_contracts:
        campaign_read_contract = campaign_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    campaign_read_contract.missing_read_contracts,
                    "change_history",
                )
            }
        )
        derived_kpi_read_contract = derived_kpi_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    derived_kpi_read_contract.missing_read_contracts,
                    "change_history",
                )
            }
        )
        budget_pacing_read_contract = budget_pacing_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    budget_pacing_read_contract.missing_read_contracts,
                    "change_history",
                )
            }
        )
        recommendations_read_contract = recommendations_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    recommendations_read_contract.missing_read_contracts,
                    "change_history",
                )
            }
        )
        impression_share_read_contract = impression_share_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    impression_share_read_contract.missing_read_contracts,
                    "change_history",
                )
            }
        )
    return (
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
    )


def _ads_aggregation_contract(
    *,
    view: Literal["full", "summary"],
    campaign_rows_available: int,
    search_term_rows_available: int,
    account_currency_read_contract: AdsAccountCurrencyReadContract,
) -> AdsAggregationContract:
    summary = view == "summary"
    currency_status: Literal["ready", "blocked", "missing"] = (
        "ready"
        if account_currency_read_contract.status == "ready"
        else "blocked"
        if account_currency_read_contract.missing_read_contracts
        else "missing"
    )
    return AdsAggregationContract(
        view=view,
        search_term_windows=["last_30_days", "search_term_safety_90d"],
        summary_row_limit=ADS_SUMMARY_VIEW_ROW_LIMIT,
        campaign_rows_returned=min(campaign_rows_available, ADS_SUMMARY_VIEW_ROW_LIMIT)
        if summary
        else campaign_rows_available,
        campaign_rows_available=campaign_rows_available,
        search_term_rows_returned=min(search_term_rows_available, ADS_SUMMARY_VIEW_ROW_LIMIT)
        if summary
        else search_term_rows_available,
        search_term_rows_available=search_term_rows_available,
        # Even the full API view is bounded by connector limits/privacy
        # omission; only the row compaction differs between views.
        is_exhaustive=False,
        summary_scope=(
            "top_decisions_and_first_rows" if summary else "all_rows_from_bounded_source_reads"
        ),
        currency_code=account_currency_read_contract.currency_code,
        currency_status=currency_status,
        money_aggregation_allowed=currency_status == "ready",
        caveats=[
            "Podsumowanie nie jest pełną kolejką; pokazuje ograniczoną liczbę wierszy.",
            "Okno kampanii to LAST_7_DAYS; pacing nie jest miesięcznym planem budżetu.",
            (
                "Wyszukiwane hasła podlegają limitom odczytu i pomijaniu niskiego "
                "wolumenu przez Google."
            ),
            "Kosztów nie wolno sumować ani etykietować bez potwierdzonej jednej waluty konta.",
        ],
    )


def _operator_summary(
    decisions: list[AdsDecisionItem],
    campaign_read_contract: AdsCampaignReadContract,
    search_terms_read_contract: AdsSearchTermsReadContract,
    optimizer_readiness_contract: AdsOptimizerReadinessContract,
) -> AdsOperatorSummary:
    top_decisions = sorted(
        decisions,
        key=lambda item: (_ads_decision_status_rank(item), item.priority),
    )[:5]
    campaign_rows = campaign_read_contract.campaign_rows
    return AdsOperatorSummary(
        title="Co marketer ma sprawdzić teraz w Google Ads",
        summary=(
            "WILQ pokazuje tylko decyzje wynikające z odczytu Google Ads. Kampanie, "
            "zapytania, wskaźniki i rekomendacje można przeglądać jako ocenę opartą na dowodach, "
            "ale zapis zmian, ocena zmarnowanego budżetu, koszt pozyskania celu, zwrot z reklam "
            "i skalowanie budżetu pozostają za "
            "sprawdzeniem w WILQ oraz brakującymi danymi."
        ),
        next_step=(
            "Przejrzyj top decyzje w tej kolejności. Nie zapisuj wykluczeń, budżetów "
            "ani rekomendacji bez podglądu zmian, sprawdzenia w WILQ i oceny "
            "kontekstu biznesowego."
        ),
        top_decision_ids=[decision.id for decision in top_decisions],
        campaign_count=len(campaign_rows),
        search_term_count=len(search_terms_read_contract.search_term_rows),
        total_clicks=sum(row.clicks or 0 for row in campaign_rows),
        total_impressions=sum(row.impressions or 0 for row in campaign_rows),
        total_cost_micros=sum(row.cost_micros or 0 for row in campaign_rows),
        total_conversions=sum(row.conversions or 0.0 for row in campaign_rows),
        total_conversion_value=sum(row.conversion_value or 0.0 for row in campaign_rows),
        ready_area_count=optimizer_readiness_contract.ready_area_count,
        blocked_area_count=optimizer_readiness_contract.blocked_area_count,
        allowed_metrics=unique(
            metric for decision in top_decisions for metric in decision.allowed_metrics
        ),
        missing_read_contracts=unique(
            contract for decision in top_decisions for contract in decision.missing_read_contracts
        ),
        operator_review_gates=unique(
            gate for decision in top_decisions for gate in decision.operator_review_gates
        ),
        source_connectors=unique(
            connector for decision in top_decisions for connector in decision.source_connectors
        ),
        evidence_ids=unique(
            evidence_id for decision in top_decisions for evidence_id in decision.evidence_ids
        ),
        action_ids=unique(
            action_id for decision in top_decisions for action_id in decision.action_ids
        ),
        blocked_claims=unique(
            claim for decision in top_decisions for claim in decision.blocked_claims
        ),
        top_blocked_claim_labels=unique(
            claim for decision in top_decisions for claim in decision.blocked_claims
        )[:5],
    )


def _ads_decision_status_rank(decision: AdsDecisionItem) -> int:
    return 0 if decision.status == "ready" else 1


def _latest_google_ads_refresh() -> ConnectorRefreshRun | None:
    return latest_google_ads_refresh()


def _ads_freshness_assessment(
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsFreshnessAssessment:
    return ads_freshness_assessment(
        latest_refresh,
        refresh_status_label=_ads_refresh_status_label,
    )


def _as_utc(value: datetime) -> datetime:
    return as_utc(value)


def _connector_refresh_recency_key(run: ConnectorRefreshRun) -> tuple[str, str]:
    return connector_refresh_recency_key(run)


def _google_ads_action_ids(
    actions: list[ActionObject] | None,
    *,
    live_data_available: bool,
) -> list[str]:
    if actions is None:
        if not live_data_available:
            return [GOOGLE_ADS_OAUTH_REPAIR_ACTION_ID]
        missing_read_contracts = ads_business_context_missing_read_contracts()
        business_context_configured = ads_business_context_configured()
        strategy_review = ads_strategy_review_state()
        return [
            action_id
            for action_id in GOOGLE_ADS_DIAGNOSTIC_ACTION_IDS
            if not (live_data_available and action_id == GOOGLE_ADS_OAUTH_REPAIR_ACTION_ID)
            and not (business_context_configured and action_id == ADS_BUSINESS_CONTEXT_ACTION_ID)
            and not (
                action_id == ADS_TARGET_CONFIRMATION_ACTION_ID
                and (
                    business_context_configured
                    and "target_roas_or_cpa" not in missing_read_contracts
                )
            )
            and not (
                action_id == ADS_STRATEGY_REVIEW_ACTION_ID
                and (
                    business_context_configured
                    and (
                        strategy_review is not None
                        and strategy_review.outcome == "approved_for_prepare"
                    )
                )
            )
        ]
    return [
        action.id
        for action in actions
        if action.connector == GOOGLE_ADS_CONNECTOR_ID
        and not (live_data_available and action.id == GOOGLE_ADS_OAUTH_REPAIR_ACTION_ID)
        and action.id != DEMAND_GEN_READINESS_REVIEW_ACTION_ID
    ]


def _oauth_or_live_section(
    latest_refresh: ConnectorRefreshRun | None,
    metric_facts: list[MetricFact],
    action_ids: list[str],
) -> AdsDiagnosticSection:
    evidence_ids = _refresh_or_connector_evidence_ids(latest_refresh)
    has_completed_live_refresh = connector_refresh_has_live_data(latest_refresh) and bool(
        metric_facts
    )
    if has_completed_live_refresh:
        return AdsDiagnosticSection(
            id="ads_live_data_status",
            title="Google Ads: live data dostępne",
            status="ready",
            summary="WILQ ma zapisane metryki z odczytu danych Google Ads.",
            diagnosis=(
                "Można przejść do diagnozy kampanii, ale nadal każda rekomendacja musi "
                "wskazać dowód w WILQ, metryki źródłowe i bezpieczną akcję."
            ),
            next_step=(
                "Użyj wierszy kampanii i zapytań do sprawdzenia. Następnie dodaj "
                "rekomendacje, historię zmian, kontrole bezpieczeństwa "
                "i akcje do sprawdzenia przed "
                "rekomendacjami zapisu zmian."
            ),
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=evidence_ids,
            metric_facts=metric_facts[:8],
            action_ids=[],
            blocked_claims=[
                "dodanie wykluczających słów kluczowych",
                "zapis zmian budżetu",
                "zapis zmian kampanii",
            ],
            risk=ActionRisk.medium,
        )

    reason = _ads_blocker_reason(latest_refresh)
    return AdsDiagnosticSection(
        id="ads_oauth_blocker",
        title="Google Ads: OAuth blokuje aktualne metryki",
        status="blocked",
        summary=reason,
        diagnosis=(
            "WILQ widzi konfigurację Google Ads, ale ostatni odczyt danych nie "
            "zebrał danych. WILQ nie może uczciwie pokazać wydatków, "
            "kosztu pozyskania celu, zwrotu z reklam, "
            "wyszukiwanych haseł ani rekomendacji Google bez poprawnego OAuth."
        ),
        next_step=(
            "Użyj akcji `act_configure_google_ads_env`, odśwież token z zakresem "
            "`adwords`, potem uruchom odczyt danych Google Ads."
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=[
            "zmarnowany koszt",
            "koszt pozyskania celu",
            "zwrot z reklam",
            "wyszukiwane hasła",
            "propozycje wykluczeń",
            "skalowanie kampanii",
        ],
        risk=ActionRisk.medium,
    )


def _business_context_with_action_ids(
    business_context_read_contract: AdsBusinessContextReadContract,
    action_ids: list[str],
) -> AdsBusinessContextReadContract:
    business_context_action_ids = _business_context_action_ids(action_ids)
    target_interpretation = business_context_read_contract.target_interpretation.model_copy(
        update={"action_ids": business_context_action_ids}
    )
    return business_context_read_contract.model_copy(
        update={"target_interpretation": target_interpretation}
    )


def _account_currency_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsAccountCurrencyReadContract:
    currency_facts: list[MetricFact] = []
    currency_codes: list[str] = []
    for fact in metric_facts:
        if fact.name != "account_currency_code" or not isinstance(fact.value, str):
            continue
        currency_code = fact.value.strip().upper()
        if len(currency_code) != 3:
            continue
        currency_facts.append(fact)
        currency_codes.append(currency_code)
    currency_codes = unique(currency_codes)
    if len(currency_codes) > 1:
        return AdsAccountCurrencyReadContract(
            status="blocked",
            title="Google Ads: niespójna waluta odczytu",
            summary=(
                "WILQ znalazł więcej niż jedną walutę konta w aktualnym zbiorze "
                "dowodów; nie sumuje ani nie etykietuje kosztów jedną walutą."
            ),
            currency_code=None,
            allowed_metrics=["account_currency_code"],
            missing_read_contracts=["account_currency_consistency"],
            blocked_claims=[
                "koszt w walucie konta",
                "opłacalność",
                "ocena kosztu pozyskania celu",
                "werdykt zwrotu z reklam",
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=unique(fact.evidence_id for fact in currency_facts),
            next_step=(
                "Rozdziel odczyt na jedno konto i jedną walutę albo potwierdź "
                "spójność customer.currency_code przed interpretacją kosztów."
            ),
        )
    if currency_codes:
        currency_code = currency_codes[0]
        return AdsAccountCurrencyReadContract(
            status="ready",
            title="Google Ads: waluta konta",
            summary=f"WILQ ma walutę konta Google Ads z evidence: {currency_code}.",
            currency_code=currency_code,
            allowed_metrics=["account_currency_code"],
            missing_read_contracts=[],
            blocked_claims=[
                "opłacalność",
                "ocena marży",
                "zmiana budżetu",
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=unique(fact.evidence_id for fact in currency_facts),
            next_step=(
                "Pokazuj koszt, koszt kliknięcia i koszt pozyskania celu "
                "w walucie konta. Nadal nie oceniaj "
                "rentowności bez marży, celu biznesowego i podglądu zmian po kontroli WILQ."
            ),
        )
    return AdsAccountCurrencyReadContract(
        status="blocked",
        title="Google Ads: brak waluty konta",
        summary="WILQ nie ma `customer.currency_code` w ostatnim Google Ads evidence.",
        currency_code=None,
        allowed_metrics=[],
        missing_read_contracts=["account_currency"],
        blocked_claims=[
            "koszt w walucie konta",
            "opłacalność",
            "ocena kosztu pozyskania celu",
            "werdykt zwrotu z reklam",
        ],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        next_step=("Uruchom odczyt danych Google Ads z polem `customer.currency_code`."),
    )


def _build_business_context_read_contract(
    *,
    strategy_review: Any | None,
    status: Literal["ready", "blocked"],
    summary: str,
    next_step: str,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_roas: float | None,
    target_cpa_micros: int | None,
    strategy_review_status: Literal[
        "missing",
        "approved_for_prepare",
        "needs_changes",
        "rejected",
        "deferred",
    ],
    strategy_review_approved: bool,
    configured_sources: list[str],
    business_policy_ids: list[str],
    operator_review_gates: list[str],
    target_missing: bool,
    allowed_metrics: list[str],
    missing_read_contracts: list[str],
    metric_tiles: dict[str, int | float | str],
    evidence_ids: list[str],
) -> AdsBusinessContextReadContract:
    blocked_claims = [
        "opłacalność",
        "ocena marży",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "zmarnowany budżet",
    ]
    return AdsBusinessContextReadContract(
        status=status,
        title="Google Ads: kontekst biznesowy decyzji",
        summary=summary,
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_roas=target_roas,
        target_cpa_micros=target_cpa_micros,
        strategy_review_status=strategy_review_status,
        strategy_reviewed_by=strategy_review.reviewed_by if strategy_review is not None else None,
        strategy_reviewed_at=strategy_review.created_at if strategy_review is not None else None,
        strategy_review_summary=strategy_review.notes if strategy_review is not None else None,
        configured_sources=configured_sources,
        business_policy_ids=business_policy_ids,
        operator_review_gates=operator_review_gates,
        target_interpretation=business_target_interpretation(
            status=status,
            profit_margin=profit_margin,
            business_goal=business_goal,
            budget_goal=budget_goal,
            target_roas=target_roas,
            target_cpa_micros=target_cpa_micros,
            target_missing=target_missing,
            strategy_review_status=strategy_review_status,
            strategy_review_approved=strategy_review_approved,
            business_policy_ids=business_policy_ids,
            evidence_ids=evidence_ids,
        ),
        strategy_review_readiness_contract=strategy_review_readiness_contract(
            strategy_review=strategy_review,
            strategy_review_status=strategy_review_status,
            strategy_review_approved=strategy_review_approved,
            profit_margin=profit_margin,
            business_goal=business_goal,
            budget_goal=budget_goal,
            target_roas=target_roas,
            target_cpa_micros=target_cpa_micros,
            missing_read_contracts=missing_read_contracts,
            evidence_ids=evidence_ids,
        ),
        allowed_metrics=allowed_metrics,
        missing_read_contracts=missing_read_contracts,
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        metric_tiles=metric_tiles,
        next_step=next_step,
    )


def _business_context_read_contract(
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsBusinessContextReadContract:
    profit_margin, profit_margin_source = _profit_margin_env()
    business_goal, business_goal_source = _text_env("WILQ_ADS_BUSINESS_GOAL")
    budget_goal, budget_goal_source = _text_env("WILQ_ADS_BUDGET_GOAL")
    (
        target_roas,
        target_roas_source,
        target_cpa_micros,
        target_cpa_source,
        target_confirmation,
    ) = ads_target_guardrail_values()
    strategy_review = ads_strategy_review_state()
    strategy_review_status = strategy_review.outcome if strategy_review is not None else "missing"
    strategy_review_approved = strategy_review_status == "approved_for_prepare"
    configured_sources = unique(
        source
        for source in [
            profit_margin_source,
            business_goal_source,
            budget_goal_source,
            target_roas_source,
            target_cpa_source,
            f"local_state:{ADS_STRATEGY_REVIEW_ACTION_ID}" if strategy_review is not None else None,
        ]
        if source
    )
    (
        missing_read_contracts,
        allowed_metrics,
        target_missing,
        status,
    ) = business_context_contract_state(
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_roas=target_roas,
        target_cpa_micros=target_cpa_micros,
        strategy_review_status=strategy_review_status,
        strategy_review_approved=strategy_review_approved,
    )
    business_policy_ids = business_context_policy_ids(
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_missing=target_missing,
        strategy_review_approved=strategy_review_approved,
        status=status,
    )
    operator_review_gates = business_context_review_gates(
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_missing=target_missing,
        strategy_review_approved=strategy_review_approved,
    )
    metric_tiles = business_context_read_metric_tiles(
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_roas=target_roas,
        target_cpa_micros=target_cpa_micros,
        target_confirmation=target_confirmation,
        strategy_review_status=strategy_review_status,
    )
    summary, next_step = business_context_summary_and_next_step(
        status=status,
        target_missing=target_missing,
    )
    return _build_business_context_read_contract(
        strategy_review=strategy_review,
        status=status,
        summary=summary,
        next_step=next_step,
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_roas=target_roas,
        target_cpa_micros=target_cpa_micros,
        strategy_review_status=strategy_review_status,
        strategy_review_approved=strategy_review_approved,
        configured_sources=configured_sources,
        business_policy_ids=business_policy_ids,
        operator_review_gates=operator_review_gates,
        target_missing=target_missing,
        allowed_metrics=allowed_metrics,
        missing_read_contracts=missing_read_contracts,
        metric_tiles=metric_tiles,
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
    )


def _safe_action_section(
    action_ids: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    *,
    live_data_available: bool,
) -> AdsDiagnosticSection:
    evidence_ids = _refresh_or_connector_evidence_ids(latest_refresh)
    if live_data_available:
        summary = (
            "WILQ ma dowody z odczytu Google Ads; ścieżka zapisu zmian nadal wymaga "
            "osobnego sprawdzenia, podglądu, potwierdzenia i audytu."
        )
        diagnosis = (
            "Odczyt kampanii i zapytań może wspierać analizę, ale zmiany budżetów, "
            "kampanii, wykluczeń i segmentów wymagają osobnych podglądów akcji, "
            "sprawdzenia, jawnego potwierdzenia i audytu."
        )
        next_step = (
            "Rozszerz proces Ads o akcję tylko do przygotowania dopiero po "
            "osobnym dowodzie dla konkretnej zmiany."
        )
    else:
        summary = "WILQ ma tylko akcję naprawy dostępu Google Ads bez zapisu zmian."
        diagnosis = (
            "Żadna zmiana Google Ads nie może przejść do zapisu bez podglądu akcji, "
            "sprawdzenia, jawnego potwierdzenia i audytu. Obecnie jedyny sensowny "
            "następny krok to naprawa dostępu."
        )
        next_step = (
            "Zweryfikuj `act_configure_google_ads_env`; zapis zmian pozostaje zablokowany "
            "bez jawnego wsparcia w kontrakcie."
        )
    return AdsDiagnosticSection(
        id="ads_action_safety",
        title="Bezpieczne akcje Ads",
        status="blocked",
        summary=summary,
        diagnosis=diagnosis,
        next_step=next_step,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=[
            "zmiana budżetu",
            "campaign creation",
            "dodanie wykluczających słów kluczowych",
        ],
        risk=ActionRisk.medium,
    )


def _blocked_ads_decision_queue(
    blocked_handoff: AdsBlockedHandoff,
    currency_code: str | None,
) -> list[AdsDecisionItem]:
    return [
        _with_ads_decision_lineage(
            AdsDecisionItem(
                id="ads_fix_access_before_analysis",
                decision_type="fix_ads_access",
                status="blocked",
                title="Napraw dostęp Google Ads przed analizą",
                summary=blocked_handoff.summary,
                rationale=blocked_handoff.marketer_message,
                next_step="Wykonaj ścieżkę naprawy OAuth i dopiero potem odczyt Google Ads.",
                source_connectors=blocked_handoff.source_connectors,
                evidence_ids=blocked_handoff.evidence_ids,
                action_ids=blocked_handoff.action_ids,
                blocked_claims=blocked_handoff.blocked_claims,
                risk=ActionRisk.medium,
            ),
            currency_code,
        )
    ]


def _build_campaign_context_decisions(
    campaign_read_contract: AdsCampaignReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    campaign_triage_read_contract: AdsCampaignTriageReadContract,
    *,
    action_ids: list[str],
    campaign_missing_read_contracts: list[str],
    derived_missing_read_contracts: list[str],
) -> list[AdsDecisionItem]:
    decisions: list[AdsDecisionItem] = []
    if campaign_read_contract.campaign_rows:
        decisions.append(
            build_campaign_activity_decision(
                campaign_read_contract,
                action_ids=action_ids,
                missing_read_contracts=campaign_missing_read_contracts,
            )
        )
    if campaign_triage_read_contract.triage_rows:
        decisions.append(build_campaign_triage_decision(campaign_triage_read_contract))
    decisions.append(build_business_context_decision(business_context_read_contract))
    if derived_kpi_read_contract.kpi_rows:
        decisions.append(
            build_derived_kpi_decision(
                derived_kpi_read_contract,
                action_ids=action_ids,
                missing_read_contracts=derived_missing_read_contracts,
            )
        )
    return decisions


def _build_ads_safety_decisions(
    sections: list[AdsDiagnosticSection],
) -> list[AdsDecisionItem]:
    safety_section = next(
        (section for section in sections if section.id == "ads_action_safety"),
        None,
    )
    if safety_section is None:
        return []
    return [build_block_write_actions_decision(safety_section)]


def _ads_decision_queue(
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
) -> list[AdsDecisionItem]:
    return build_decision_queue(
        campaign_read_contract,
        business_context_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        campaign_triage_read_contract,
        change_history_read_contract,
        search_terms_read_contract,
        search_term_ngram_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
        keyword_planner_read_contract,
        custom_segments_read_contract,
        negative_keywords_read_contract,
        sections,
        blocked_handoff,
        action_ids,
        currency_code,
        campaign_context=_build_campaign_context_decisions,
        blocked_queue=_blocked_ads_decision_queue,
        safety_decisions=_build_ads_safety_decisions,
        remove_available=_remove_available_contracts,
        with_lineage=_with_ads_decision_lineage,
    )


def _business_context_action_ids(action_ids: list[str]) -> list[str]:
    allowed_ids = {
        ADS_BUSINESS_CONTEXT_ACTION_ID,
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    }
    return [action_id for action_id in action_ids if action_id in allowed_ids]


def _recommendation_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == RECOMMENDATION_REVIEW_ACTION_ID]


def _search_term_ngram_with_action_ids(
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
    action_ids: list[str],
) -> AdsSearchTermNgramReadContract:
    if not search_term_ngram_read_contract.ngram_rows:
        return search_term_ngram_read_contract
    return search_term_ngram_read_contract.model_copy(
        update={"action_ids": _search_term_ngram_action_ids(action_ids)}
    )


def _search_term_ngram_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == SEARCH_TERM_NGRAM_ACTION_ID]


def _search_term_action_ids(action_ids: list[str]) -> list[str]:
    allowed_ids = {CUSTOM_SEGMENT_ACTION_ID, NEGATIVE_KEYWORD_ACTION_ID}
    return [action_id for action_id in action_ids if action_id in allowed_ids]


def _remove_available_contracts(
    missing_read_contracts: list[str],
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract | None = None,
    impression_share_read_contract: AdsImpressionShareReadContract | None = None,
    change_history_read_contract: AdsChangeHistoryReadContract | None = None,
) -> list[str]:
    unavailable = list(missing_read_contracts)
    if budget_pacing_read_contract.status == "ready":
        unavailable = [contract for contract in unavailable if contract != "budget_pacing"]
    if (
        recommendations_read_contract is not None
        and recommendations_read_contract.status == "ready"
    ):
        unavailable = [contract for contract in unavailable if contract != "recommendations"]
    if (
        impression_share_read_contract is not None
        and impression_share_read_contract.status == "ready"
    ):
        unavailable = [contract for contract in unavailable if contract != "impression_share"]
    if (
        change_history_read_contract is not None
        and "change_history" not in change_history_read_contract.missing_read_contracts
    ):
        unavailable = [contract for contract in unavailable if contract != "change_history"]
    return unavailable


def _blocked_handoff(
    live_data_available: bool,
    latest_refresh: ConnectorRefreshRun | None,
    sections: list[AdsDiagnosticSection],
    action_ids: list[str],
) -> AdsBlockedHandoff | None:
    evidence_ids = unique(
        evidence_id for section in sections for evidence_id in section.evidence_ids
    )
    blocked_claims = unique(claim for section in sections for claim in section.blocked_claims)
    if live_data_available:
        return None
    return AdsBlockedHandoff(
        status="blocked",
        title="Google Ads: końcowe przekazanie blokady OAuth",
        summary=_ads_blocker_reason(latest_refresh),
        marketer_message=(
            "W demo pokaż, że WILQ widzi problem z dostępem i blokuje wszystkie wnioski o "
            "wydatkach, koszcie pozyskania celu, zwrocie z reklam, "
            "wyszukiwanych hasłach i wykluczających słowach kluczowych. "
            "To jest kontrola jakości, "
            "nie brak wiedzy."
        ),
        repair_steps=[
            "Otwórz /ads-doctor i pokaż zanonimizowaną blokadę OAuth.",
            "Zweryfikuj akcję `act_configure_google_ads_env`.",
            "Uzyskaj świeży Google Ads OAuth token z zakresem `adwords`.",
            "Uruchom odczyt danych Google Ads.",
            "Dopiero po świeżych dowodach pokazuj wydatki, koszt pozyskania celu, "
            "zwrot z reklam lub wyszukiwane hasła.",
        ],
        allowed_demo_claims=[
            "Google Ads jest zablokowany przez dostęp OAuth/API.",
            "WILQ nie zmyśla metryk Ads bez dowodów z Google Ads.",
            "Naprawa dostępu ma akcję i bramkę sprawdzenia.",
        ],
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
    )


def _ads_blocker_reason(latest_refresh: ConnectorRefreshRun | None) -> str:
    if latest_refresh and latest_refresh.errors:
        return latest_refresh.errors[0]
    if latest_refresh and latest_refresh.summary:
        return latest_refresh.summary
    return "Brak wykonanego odczytu danych Google Ads."


def _with_ads_section_lineage(section: AdsDiagnosticSection) -> AdsDiagnosticSection:
    knowledge_card_ids, expert_rule_ids = ADS_SECTION_LINEAGE.get(section.id, ([], []))
    return section.model_copy(
        update={
            "knowledge_card_ids": unique([*section.knowledge_card_ids, *knowledge_card_ids]),
            "expert_rule_ids": unique([*section.expert_rule_ids, *expert_rule_ids]),
        }
    )


def _with_ads_decision_lineage(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> AdsDecisionItem:
    knowledge_card_ids, expert_rule_ids = ADS_DECISION_LINEAGE.get(decision.id, ([], []))
    return decision.model_copy(
        update={
            "priority": decision_priority(decision),
            "metric_tiles": _ads_decision_metric_tiles(decision, currency_code),
            "knowledge_card_ids": unique([*decision.knowledge_card_ids, *knowledge_card_ids]),
            "expert_rule_ids": unique([*decision.expert_rule_ids, *expert_rule_ids]),
        }
    )


def _ads_decision_metric_tiles(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> dict[str, int | float | str]:
    if decision.decision_type == "review_campaign_activity":
        return campaign_activity_metric_tiles(decision, currency_code)
    if decision.decision_type == "review_campaign_triage":
        return campaign_triage_metric_tiles(decision)
    if decision.decision_type == "review_business_context":
        return business_context_metric_tiles(decision)
    if decision.decision_type == "review_derived_kpi":
        return derived_kpi_metric_tiles(decision)
    if decision.decision_type == "review_budget_context":
        return budget_context_metric_tiles(decision, currency_code)
    if decision.decision_type == "review_recommendations":
        return recommendations_metric_tiles(decision)
    if decision.decision_type == "review_search_term_ngrams":
        return search_term_ngram_metric_tiles(decision, currency_code)
    if decision.decision_type == "review_impression_share":
        return impression_share_metric_tiles(decision)
    if decision.decision_type == "review_change_history":
        return change_history_metric_tiles(decision)
    if decision.decision_type == "review_search_terms":
        return search_terms_metric_tiles(decision, currency_code)
    if decision.decision_type == "review_search_term_safety":
        return search_term_safety_metric_tiles(decision, currency_code)
    if decision.decision_type == "review_negative_keyword_safety":
        return negative_keyword_safety_metric_tiles(decision)
    if decision.decision_type == "prepare_custom_segments":
        return custom_segments_metric_tiles(decision)
    if decision.decision_type in {"block_write_actions", "fix_ads_access"}:
        return safety_blocker_metric_tiles(decision)
    return {}


def _metric_sentence(facts: list[MetricFact]) -> str:
    samples = ", ".join(f"{fact.name}={fact.value}" for fact in facts[:6])
    return f"Fakty z danych: {samples}."


def _hydrate_ads_review_gate_labels(response: AdsDiagnosticsResponse) -> None:
    hydrate_review_gate_labels(response, review_gate_labels=_ads_review_gate_labels)


def _hydrate_ads_summary_labels(response: AdsDiagnosticsResponse) -> None:
    hydrate_summary_labels(
        response,
        missing_contract_labels=_ads_missing_read_contract_labels,
        allowed_metric_labels=_ads_allowed_metric_labels,
        unique=unique,
    )


def _hydrate_ads_decision_labels(
    response: AdsDiagnosticsResponse,
    currency_code: str | None,
) -> None:
    hydrate_decision_labels(
        response,
        currency_code,
        status_label=_ads_status_label,
        decision_type_label=_ads_decision_type_label,
        priority_label=_ads_priority_label,
        start_here_summary=_ads_decision_start_here_summary,
        measurement_plan=_ads_decision_measurement_plan,
        risk_label=_ads_risk_label,
        missing_contract_labels=_ads_missing_read_contract_labels,
        unique=unique,
    )


def _hydrate_ads_surface_labels(response: AdsDiagnosticsResponse) -> None:
    hydrate_surface_labels(
        response,
        status_label=_ads_status_label,
        unique=unique,
    )


def _hydrate_ads_contract_labels(
    response: AdsDiagnosticsResponse,
    currency_code: str | None,
) -> None:
    hydrate_contract_labels(
        response,
        currency_code,
        custom_segments=_hydrate_custom_segments_marketer_labels,
        business_context=_hydrate_business_context_marketer_labels,
        campaign_triage=_hydrate_campaign_triage_marketer_labels,
        optimizer_readiness=_hydrate_optimizer_readiness_marketer_labels,
        change_impact=_hydrate_change_impact_marketer_labels,
        budget_pacing=_hydrate_budget_pacing_marketer_labels,
        recommendations=_hydrate_recommendations_marketer_labels,
        impression_share=_hydrate_impression_share_marketer_labels,
        change_history=_hydrate_change_history_marketer_labels,
        negative_keywords=_hydrate_negative_keywords_marketer_labels,
        keyword_match_context=_hydrate_keyword_match_context_marketer_labels,
        unique=unique,
    )


def _hydrate_ads_core_contract_labels(response: AdsDiagnosticsResponse) -> None:
    _hydrate_custom_segments_marketer_labels(response.custom_segments_read_contract)
    _hydrate_business_context_marketer_labels(response.business_context_read_contract)
    _hydrate_campaign_triage_marketer_labels(response.campaign_triage_read_contract)
    for row in response.derived_kpi_read_contract.kpi_rows:
        row.blocked_claim_labels = unique(row.blocked_claims)
        row.blocked_claim_summary_label = blocked_claim_count_label(
            row.blocked_claim_labels or row.blocked_claims
        )


def _hydrate_ads_optimization_contract_labels(response: AdsDiagnosticsResponse) -> None:
    _hydrate_optimizer_readiness_marketer_labels(response.optimizer_readiness_contract)
    _hydrate_change_impact_marketer_labels(response.change_impact_readiness_contract)


def _hydrate_ads_budget_performance_contract_labels(
    response: AdsDiagnosticsResponse,
    currency_code: str | None,
) -> None:
    _hydrate_budget_pacing_marketer_labels(
        response.budget_pacing_read_contract,
        currency_code,
    )
    _hydrate_recommendations_marketer_labels(response.recommendations_read_contract)
    _hydrate_impression_share_marketer_labels(response.impression_share_read_contract)
    _hydrate_change_history_marketer_labels(response.change_history_read_contract)


def _hydrate_ads_search_contract_labels(response: AdsDiagnosticsResponse) -> None:
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
    _hydrate_negative_keywords_marketer_labels(response.negative_keywords_read_contract)
    _hydrate_keyword_match_context_marketer_labels(response.keyword_match_context_read_contract)


def _hydrate_ads_marketer_labels(response: AdsDiagnosticsResponse) -> None:
    currency_code = response.account_currency_read_contract.currency_code
    _hydrate_ads_summary_labels(response)
    _hydrate_ads_decision_labels(response, currency_code)
    _hydrate_ads_surface_labels(response)
    _hydrate_ads_contract_labels(response, currency_code)


def _hydrate_business_context_marketer_labels(
    contract: AdsBusinessContextReadContract,
) -> None:
    contract.status_label = _ads_business_context_status_label(contract)
    interpretation = contract.target_interpretation
    interpretation.status_label = _ads_status_label(interpretation.status)
    interpretation.allowed_use_labels = _ads_business_use_labels(interpretation.allowed_uses)
    interpretation.blocked_use_labels = _ads_business_use_labels(interpretation.blocked_uses)
    interpretation.missing_requirement_labels = _ads_missing_read_contract_labels(
        interpretation.missing_requirements
    )
    interpretation.required_validation_labels = _ads_review_gate_labels(
        interpretation.required_validation
    )
    interpretation.action_summary_label = action_count_label(interpretation.action_ids)

    readiness = contract.strategy_review_readiness_contract
    readiness.status_label = _ads_status_label(readiness.status)
    readiness.latest_review_status_label = _ads_strategy_review_status_label(
        readiness.latest_review_status
    )
    readiness.required_validation_labels = _ads_review_gate_labels(readiness.required_validation)
    readiness.missing_read_contract_labels = _ads_missing_read_contract_labels(
        readiness.missing_read_contracts
    )
    readiness.blocked_claim_labels = unique(readiness.blocked_claims)
    readiness.action_summary_label = action_count_label(readiness.action_ids)


def _hydrate_optimizer_readiness_marketer_labels(
    contract: AdsOptimizerReadinessContract,
) -> None:
    contract.status_label = _ads_optimizer_status_label(contract.status)
    contract.mode_label = _ads_optimizer_mode_label(contract.mode)
    contract.source_connector_labels = source_connector_labels(contract.source_connectors)
    contract.evidence_summary_label = evidence_count_label(contract.evidence_ids)
    contract.action_summary_label = action_count_label(contract.action_ids)
    contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        contract.missing_read_contracts
    )
    contract.blocked_claim_labels = unique(contract.blocked_claims)
    for item in contract.readiness_items:
        item.label = _ads_optimizer_readiness_item_label(item.id)
        item.status_label = _ads_status_label(item.status)
        item.risk_label = _ads_risk_label(item.risk)
        item.source_connector_labels = source_connector_labels(item.source_connectors)
        item.evidence_summary_label = evidence_count_label(item.evidence_ids)
        item.action_summary_label = action_count_label(item.action_ids)
        item.missing_read_contract_labels = _ads_missing_read_contract_labels(
            item.missing_read_contracts
        )
        item.blocked_claim_labels = unique(item.blocked_claims)
