from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Literal

from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
    ads_float_env,
    ads_int_env,
    ads_profit_margin_env,
    ads_strategy_review_state,
    ads_target_guardrail_values,
    ads_text_env,
)
from wilq.actions.google_ads.campaign_review import (
    CAMPAIGN_REVIEW_ACTION_ID,
)
from wilq.actions.google_ads.campaign_triage import (
    campaign_review_gates,
    campaign_review_priority,
    campaign_review_reason,
    campaign_review_score,
    campaign_target_context,
)
from wilq.actions.google_ads.change_history import CHANGE_HISTORY_IMPACT_ACTION_ID
from wilq.actions.google_ads.custom_segments import (
    CUSTOM_SEGMENT_ACTION_ID,
    CUSTOM_SEGMENT_BLOCKED_CLAIMS,
    custom_segment_apply_safety_review,
)
from wilq.actions.google_ads.demand_gen import DEMAND_GEN_READINESS_REVIEW_ACTION_ID
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.negative_keywords import (
    NEGATIVE_KEYWORD_ACTION_ID,
    NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
)
from wilq.actions.google_ads.recommendations import (
    RECOMMENDATION_REVIEW_ACTION_ID,
)
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID
from wilq.actions.service import list_actions
from wilq.briefing.ads_budget_pacing import build_budget_pacing_read_contract
from wilq.briefing.ads_change_history import build_change_history_read_contract
from wilq.briefing.ads_impression_share import build_impression_share_read_contract
from wilq.briefing.ads_recommendations import build_recommendations_read_contract
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    AdsAccountCurrencyReadContract,
    AdsBlockedHandoff,
    AdsBudgetPacingReadContract,
    AdsBudgetPacingRow,
    AdsBusinessContextReadContract,
    AdsBusinessTargetInterpretation,
    AdsCampaignMetricRow,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsCampaignTriageRow,
    AdsChangeHistoryReadContract,
    AdsChangeHistoryRow,
    AdsChangeImpactReadinessContract,
    AdsChangeImpactReadinessRow,
    AdsCustomSegmentApplySafetyReview,
    AdsCustomSegmentAudienceForecastReadContract,
    AdsCustomSegmentAudienceForecastRow,
    AdsCustomSegmentCandidate,
    AdsCustomSegmentPayloadPreview,
    AdsCustomSegmentSourceQuality,
    AdsCustomSegmentsReadContract,
    AdsCustomSegmentTargetingPreview,
    AdsDecisionItem,
    AdsDerivedKpiReadContract,
    AdsDerivedKpiRow,
    AdsDiagnosticSection,
    AdsDiagnosticsResponse,
    AdsImpressionShareReadContract,
    AdsImpressionShareRow,
    AdsKeywordMatchContextReadContract,
    AdsKeywordMatchContextRow,
    AdsKeywordPlannerIdeaRow,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordCandidate,
    AdsNegativeKeywordPayloadPreview,
    AdsNegativeKeywordsReadContract,
    AdsOperatorSummary,
    AdsOptimizerReadinessContract,
    AdsOptimizerReadinessItem,
    AdsRecommendationRow,
    AdsRecommendationsReadContract,
    AdsSearchTermCampaignReviewRow,
    AdsSearchTermMetricRow,
    AdsSearchTermNgramReadContract,
    AdsSearchTermNgramRow,
    AdsSearchTermReviewRow,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
    AdsSearchTermSafetyRow,
    AdsSearchTermsReadContract,
    AdsStrategyReviewReadinessContract,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.metric_store import metric_store

GOOGLE_ADS_CONNECTOR_ID = "google_ads"
AdsTargetStatus = Literal[
    "within_target",
    "outside_target",
    "spend_without_conversions",
    "insufficient_data",
    "no_target",
]
ADS_METRIC_FACT_LIMIT = 2500
CARD_GOAL_001_RULES = "card_goal_001_rules"
CARD_ADS_SEARCH = "card_google_ads_search_playbook"
CARD_ADS_BUDGET_REVIEW = "card_google_ads_budget_review_playbook"
CARD_ADS_NEGATIVE_KEYWORDS = "card_google_ads_negative_keywords_playbook"
CARD_ADS_CUSTOM_SEGMENTS = "card_google_ads_custom_segments_playbook"
ADS_RECOMMENDATION_HUMAN_REVIEW_GATE = "human_strategy_review"
CUSTOM_SEGMENT_OPERATOR_REVIEW_GATES = [
    "review_source_terms",
    "reject_brand_or_low_intent_terms",
    "keyword_planner_enrichment",
    "forecast_or_audience_size",
    "human_confirm_before_apply",
]
ADS_NGRAM_STOPWORDS = {
    "a",
    "albo",
    "bez",
    "dla",
    "do",
    "i",
    "lub",
    "na",
    "od",
    "oraz",
    "po",
    "s",
    "sa",
    "sp",
    "w",
    "we",
    "z",
    "za",
}

ADS_SECTION_LINEAGE: dict[str, tuple[list[str], list[str]]] = {
    "ads_live_data_status": (
        [CARD_ADS_SEARCH, CARD_GOAL_001_RULES],
        ["ads_diagnostics_v1", "ads_principles_v1"],
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


def build_ads_diagnostics(actions: list[ActionObject] | None = None) -> AdsDiagnosticsResponse:
    connector = get_connector_status(GOOGLE_ADS_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Google Ads connector is not registered.")
    latest_refresh = _latest_google_ads_refresh()
    metric_facts = metric_store().list_metric_facts(
        connector_id=GOOGLE_ADS_CONNECTOR_ID,
        limit=ADS_METRIC_FACT_LIMIT,
    )
    latest_refresh_collected_data = (
        latest_refresh is not None
        and latest_refresh.status == ConnectorRefreshStatus.completed
        and latest_refresh.vendor_data_collected
    )
    trusted_metric_facts = metric_facts if latest_refresh_collected_data else []
    live_data_available = bool(trusted_metric_facts)
    account_currency_read_contract = _account_currency_read_contract(
        trusted_metric_facts,
        latest_refresh,
    )
    business_context_read_contract = _business_context_read_contract(latest_refresh)
    campaign_read_contract = _campaign_read_contract(
        trusted_metric_facts,
        latest_refresh,
        business_context_read_contract,
    )
    derived_kpi_read_contract = _derived_kpi_read_contract(
        campaign_read_contract,
        account_currency_read_contract,
        business_context_read_contract,
    )
    budget_pacing_read_contract = build_budget_pacing_read_contract(
        trusted_metric_facts,
        campaign_read_contract,
        fallback_evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
    )
    recommendations_read_contract = build_recommendations_read_contract(
        trusted_metric_facts,
        read_attempted=_latest_refresh_has_summary_metric(
            latest_refresh,
            "recommendation_row_count",
        ),
        fallback_evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
    )
    impression_share_read_contract = build_impression_share_read_contract(
        trusted_metric_facts,
        read_attempted=_latest_refresh_has_summary_metric(
            latest_refresh,
            "impression_share_row_count",
        ),
        fallback_evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
    )
    change_history_read_contract = build_change_history_read_contract(
        trusted_metric_facts,
        read_attempted=_latest_refresh_has_summary_metric(
            latest_refresh,
            "change_event_row_count",
        ),
        fallback_evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
    )
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
    if budget_pacing_read_contract.payload_preview:
        impression_share_read_contract = impression_share_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    impression_share_read_contract.missing_read_contracts,
                    "budget_apply_preview",
                )
            }
        )
    if business_context_read_contract.profit_margin is not None:
        derived_kpi_read_contract = derived_kpi_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    derived_kpi_read_contract.missing_read_contracts,
                    "profit_margin",
                )
            }
        )
    if business_context_read_contract.budget_goal:
        budget_pacing_read_contract = budget_pacing_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    budget_pacing_read_contract.missing_read_contracts,
                    "human_budget_goal",
                    "budget_target_or_seasonality",
                )
            }
        )
        impression_share_read_contract = impression_share_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    impression_share_read_contract.missing_read_contracts,
                    "human_budget_goal",
                )
            }
        )
    search_terms_read_contract = _search_terms_read_contract(
        trusted_metric_facts,
        latest_refresh,
    )
    search_term_safety_read_contract = _search_term_safety_read_contract(
        trusted_metric_facts,
        latest_refresh,
    )
    keyword_match_context_read_contract = _keyword_match_context_read_contract(
        trusted_metric_facts,
        latest_refresh,
    )
    keyword_planner_read_contract = _keyword_planner_read_contract(
        trusted_metric_facts,
        latest_refresh,
    )
    if search_term_safety_read_contract.status == "ready":
        search_terms_read_contract = search_terms_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    search_terms_read_contract.missing_read_contracts,
                    "90_day_safety_check",
                )
            }
        )
    if keyword_match_context_read_contract.status == "ready":
        search_terms_read_contract = search_terms_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    search_terms_read_contract.missing_read_contracts,
                    "keyword match context",
                )
            }
        )
        search_term_safety_read_contract = search_term_safety_read_contract.model_copy(
            update={
                "missing_read_contracts": _remove_missing_contract_names(
                    search_term_safety_read_contract.missing_read_contracts,
                    "keyword match context",
                )
            }
        )
    search_term_review_summary_contract = _search_term_review_summary_contract(
        search_terms_read_contract,
        latest_refresh,
    )
    search_term_ngram_read_contract = _search_term_ngram_read_contract(
        search_terms_read_contract,
        latest_refresh,
    )
    action_ids = _google_ads_action_ids(
        actions if actions is not None else list_actions(),
        live_data_available=live_data_available,
    )
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
    custom_segments_read_contract = _custom_segments_read_contract(
        search_terms_read_contract,
        keyword_planner_read_contract,
        action_ids,
    )
    negative_keywords_read_contract = _negative_keywords_read_contract(
        search_terms_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
        action_ids,
    )
    campaign_triage_read_contract = _campaign_triage_read_contract(
        campaign_read_contract,
        business_context_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        action_ids,
    )
    optimizer_readiness_contract = _optimizer_readiness_contract(
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
    sections = [
        _oauth_or_live_section(latest_refresh, trusted_metric_facts, action_ids),
        _campaign_overview_section(
            trusted_metric_facts,
            latest_refresh,
            action_ids,
            campaign_read_contract,
        ),
        _business_context_section(business_context_read_contract),
        _derived_kpi_section(derived_kpi_read_contract),
        _budget_pacing_section(budget_pacing_read_contract),
        _recommendations_section(recommendations_read_contract),
        _impression_share_section(impression_share_read_contract),
        _change_history_section(change_history_read_contract),
        _search_terms_section(search_terms_read_contract, action_ids),
        _search_term_ngram_section(search_term_ngram_read_contract),
        _search_term_safety_section(search_term_safety_read_contract),
        _keyword_match_context_section(keyword_match_context_read_contract),
        _keyword_planner_section(keyword_planner_read_contract, action_ids),
        _custom_segments_section(custom_segments_read_contract),
        _negative_keywords_section(negative_keywords_read_contract),
        _safe_action_section(
            action_ids,
            latest_refresh,
            live_data_available=live_data_available,
        ),
    ]
    sections = [_with_ads_section_lineage(section) for section in sections]
    blocked_handoff = _blocked_handoff(live_data_available, latest_refresh, sections, action_ids)
    decision_queue = _ads_decision_queue(
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
    )
    return AdsDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        campaign_read_contract=campaign_read_contract,
        account_currency_read_contract=account_currency_read_contract,
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
        operator_summary=_operator_summary(
            decision_queue,
            campaign_read_contract,
            search_terms_read_contract,
            optimizer_readiness_contract,
        ),
        decision_queue=decision_queue,
        sections=sections,
        blocked_handoff=blocked_handoff,
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
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
            "zapytania, KPI i rekomendacje można przeglądać jako evidence-backed review, "
            "ale apply, waste, CPA/ROAS verdict i skalowanie budżetu pozostają za "
            "bramkami ActionObject oraz brakującymi kontraktami."
        ),
        next_step=(
            "Przejrzyj top decyzje w tej kolejności. Nie wdrażaj wykluczeń, budżetów "
            "ani rekomendacji bez payload preview, walidacji ActionObject i review "
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
        allowed_metrics=_unique(
            metric for decision in top_decisions for metric in decision.allowed_metrics
        ),
        missing_read_contracts=_unique(
            contract
            for decision in top_decisions
            for contract in decision.missing_read_contracts
        ),
        operator_review_gates=_unique(
            gate for decision in top_decisions for gate in decision.operator_review_gates
        ),
        source_connectors=_unique(
            connector
            for decision in top_decisions
            for connector in decision.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id
            for decision in top_decisions
            for evidence_id in decision.evidence_ids
        ),
        action_ids=_unique(
            action_id for decision in top_decisions for action_id in decision.action_ids
        ),
        blocked_claims=_unique(
            claim for decision in top_decisions for claim in decision.blocked_claims
        ),
    )


def _ads_decision_status_rank(decision: AdsDecisionItem) -> int:
    return 0 if decision.status == "ready" else 1


def _latest_google_ads_refresh() -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=GOOGLE_ADS_CONNECTOR_ID)
    for run in runs:
        if run.mode == ConnectorRefreshMode.vendor_read:
            return run
    return None


def _google_ads_action_ids(
    actions: list[ActionObject],
    *,
    live_data_available: bool,
) -> list[str]:
    return [
        action.id
        for action in actions
        if action.connector == GOOGLE_ADS_CONNECTOR_ID
        and not (live_data_available and action.id == "act_configure_google_ads_env")
        and action.id != DEMAND_GEN_READINESS_REVIEW_ACTION_ID
    ]


def _oauth_or_live_section(
    latest_refresh: ConnectorRefreshRun | None,
    metric_facts: list[MetricFact],
    action_ids: list[str],
) -> AdsDiagnosticSection:
    evidence_ids = _refresh_or_connector_evidence_ids(latest_refresh)
    has_completed_live_refresh = (
        latest_refresh is not None
        and latest_refresh.status == ConnectorRefreshStatus.completed
        and bool(metric_facts)
    )
    if has_completed_live_refresh:
        return AdsDiagnosticSection(
            id="ads_live_data_status",
            title="Google Ads: live data dostępne",
            status="ready",
            summary="WILQ ma zapisane metric facts z odczytu Google Ads vendor_read.",
            diagnosis=(
                "Można przejść do diagnozy kampanii, ale nadal każda rekomendacja musi "
                "wskazać evidence ID, metric facts i bezpieczny ActionObject."
            ),
            next_step=(
                "Użyj wierszy kampanii i zapytań do przeglądu. Następnie dodaj "
                "rekomendacje, historię zmian, safety checks i ActionObjecty przed "
                "rekomendacjami wdrożenia."
            ),
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=evidence_ids,
            metric_facts=metric_facts[:8],
            action_ids=[],
            blocked_claims=["negative keyword apply", "budget mutation", "campaign mutation"],
            risk=ActionRisk.medium,
        )

    reason = _ads_blocker_reason(latest_refresh)
    return AdsDiagnosticSection(
        id="ads_oauth_blocker",
        title="Google Ads: OAuth blokuje live metryki",
        status="blocked",
        summary=reason,
        diagnosis=(
            "WILQ widzi konfigurację Google Ads, ale ostatni read-only vendor_read nie "
            "zebrał danych. Ads Doctor nie może uczciwie pokazać spendu, CPA, ROAS, "
            "search terms ani rekomendacji Google bez poprawnego OAuth."
        ),
        next_step=(
            "Użyj ActionObject `act_configure_google_ads_env`, odśwież token z zakresem "
            "`adwords`, potem uruchom `google_ads vendor_read`."
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=[
            "wasted spend",
            "CPA",
            "ROAS",
            "search terms",
            "negative keyword candidates",
            "campaign scaling",
        ],
        risk=ActionRisk.medium,
    )


def _campaign_overview_section(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    action_ids: list[str],
    campaign_read_contract: AdsCampaignReadContract,
) -> AdsDiagnosticSection:
    campaign_facts = [
        fact for row in campaign_read_contract.campaign_rows for fact in row.metric_facts
    ]
    if campaign_facts:
        return AdsDiagnosticSection(
            id="ads_campaign_overview",
            title="Aktywność kampanii Google Ads",
            status="ready",
            summary=campaign_read_contract.summary,
            diagnosis=(
                "WILQ ma wymiarowe wiersze aktywności kampanii z Google Ads. To wystarcza "
                "do pierwszego przeglądu aktywności kampanii, ale nadal nie wystarcza "
                "do diagnozy CPA, ROAS, waste na zapytaniach ani wykluczeń."
            ),
            next_step=campaign_read_contract.next_step,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=campaign_read_contract.evidence_ids,
            metric_facts=campaign_facts[:12],
            action_ids=_campaign_review_action_ids(action_ids),
            blocked_claims=campaign_read_contract.blocked_claims,
            risk=ActionRisk.low,
        )

    evidence_ids = _refresh_or_connector_evidence_ids(latest_refresh)
    return AdsDiagnosticSection(
        id="ads_campaign_overview",
        title="Aktywność kampanii Google Ads",
        status="blocked",
        summary="Brak campaign metric facts z Google Ads.",
        diagnosis=(
            "Nie ma live campaign rows, więc dashboard nie pokazuje spendu ani trendów "
            "kampanii. To jest blocker, nie puste miejsce na estymację."
        ),
        next_step="Napraw OAuth i wykonaj read-only Google Ads vendor_read.",
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=[],
        blocked_claims=["spend", "clicks", "impressions", "campaign trend"],
        risk=ActionRisk.medium,
    )


def _derived_kpi_section(
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
) -> AdsDiagnosticSection:
    return AdsDiagnosticSection(
        id="ads_derived_kpi",
        title="Wyliczone KPI kampanii Google Ads",
        status=derived_kpi_read_contract.status,
        summary=derived_kpi_read_contract.summary,
        diagnosis=(
            "WILQ może pokazać CTR, CPC, conversion rate, CPA i ROAS jako obliczenia "
            "z bieżących campaign facts. To nie jest jeszcze diagnoza rentowności, "
            "waste ani zgoda na zmianę budżetu."
        ),
        next_step=derived_kpi_read_contract.next_step,
        source_connectors=derived_kpi_read_contract.source_connectors,
        evidence_ids=derived_kpi_read_contract.evidence_ids,
        action_ids=[],
        blocked_claims=derived_kpi_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _business_context_section(
    business_context_read_contract: AdsBusinessContextReadContract,
) -> AdsDiagnosticSection:
    return AdsDiagnosticSection(
        id="ads_business_context",
        title="Kontekst biznesowy Google Ads",
        status=business_context_read_contract.status,
        summary=business_context_read_contract.summary,
        diagnosis=(
            "WILQ oddziela wyliczone KPI od decyzji biznesowej. Marża, cel biznesowy, "
            "cel budżetu i target ROAS/CPA są kontraktem operatora, nie danymi z "
            "Google Ads."
        ),
        next_step=business_context_read_contract.next_step,
        source_connectors=business_context_read_contract.source_connectors,
        evidence_ids=business_context_read_contract.evidence_ids,
        action_ids=business_context_read_contract.target_interpretation.action_ids,
        blocked_claims=business_context_read_contract.blocked_claims,
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


def _campaign_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    business_context_read_contract: AdsBusinessContextReadContract,
) -> AdsCampaignReadContract:
    rows = _campaign_metric_rows(metric_facts, business_context_read_contract)
    missing_read_contracts = [
        "recommendations",
        "change_history",
        "impression_share",
    ]
    blocked_claims = [
        "CPA",
        "ROAS",
        "search-term waste",
        "wasted budget",
        "negative keyword candidates",
        "budget scaling",
        "conversion drop",
    ]
    if rows:
        total_clicks = sum(row.clicks or 0 for row in rows)
        total_impressions = sum(row.impressions or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros or 0 for row in rows)
        total_conversions = sum(row.conversions or 0 for row in rows)
        total_conversion_value = sum(row.conversion_value or 0 for row in rows)
        return AdsCampaignReadContract(
            status="ready",
            title="Google Ads: aktywność kampanii",
            summary=(
                f"WILQ ma {len(rows)} wierszy kampanii: kliknięcia={total_clicks}, "
                f"wyświetlenia={total_impressions}, koszt_micros={total_cost_micros}, "
                f"konwersje={_format_float(total_conversions)}, "
                f"wartość_konwersji={_format_float(total_conversion_value)}."
            ),
            allowed_metrics=[
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
            ],
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            campaign_rows=rows,
            next_step=(
                "Użyj wierszy kampanii do przeglądu aktywności. Przed wnioskami o waste, "
                "CPA, ROAS albo wykluczenia dodaj brakujące kontrakty odczytu."
            ),
        )

    return AdsCampaignReadContract(
        status="blocked",
        title="Google Ads: brak aktywności kampanii",
        summary="WILQ nie ma wymiarowych campaign facts z Google Ads.",
        allowed_metrics=[],
        missing_read_contracts=["campaign activity", *missing_read_contracts],
        blocked_claims=["clicks", "impressions", "spend", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        campaign_rows=[],
        next_step="Uruchom read-only Google Ads vendor_read i zapisz campaign metric facts.",
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
    currency_codes = _unique(currency_codes)
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
                "profitability",
                "margin verdict",
                "budget apply",
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(fact.evidence_id for fact in currency_facts),
            next_step=(
                "Pokazuj koszt, CPC i CPA w walucie konta. Nadal nie oceniaj "
                "rentowności bez marży, celu biznesowego i walidowanego preview."
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
            "currency-formatted cost",
            "profitability",
            "CPA verdict",
            "ROAS verdict",
        ],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        next_step=(
            "Uruchom read-only Google Ads vendor_read z polem `customer.currency_code`."
        ),
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
    strategy_review_status = (
        strategy_review.outcome if strategy_review is not None else "missing"
    )
    strategy_review_approved = strategy_review_status == "approved_for_prepare"
    configured_sources = _unique(
        source
        for source in [
            profit_margin_source,
            business_goal_source,
            budget_goal_source,
            target_roas_source,
            target_cpa_source,
            f"local_state:{ADS_STRATEGY_REVIEW_ACTION_ID}"
            if strategy_review is not None
            else None,
        ]
        if source
    )
    missing_read_contracts: list[str] = []
    if profit_margin is None:
        missing_read_contracts.append("profit_margin")
    if not business_goal:
        missing_read_contracts.append("business_goal")
    if not budget_goal:
        missing_read_contracts.append("human_budget_goal")
    if target_roas is None and target_cpa_micros is None:
        missing_read_contracts.append("target_roas_or_cpa")
    if strategy_review is None:
        missing_read_contracts.append("human_strategy_review")
    elif not strategy_review_approved:
        missing_read_contracts.append("approved_human_strategy_review")

    allowed_metrics = [
        name
        for name, value in [
            ("profit_margin", profit_margin),
            ("business_goal", business_goal),
            ("human_budget_goal", budget_goal),
            ("target_roas", target_roas),
            ("target_cpa_micros", target_cpa_micros),
        ]
        if value is not None and value != ""
    ]
    blocking_missing_contracts = [
        contract
        for contract in missing_read_contracts
        if contract not in {"target_roas_or_cpa", "human_strategy_review"}
    ]
    target_missing = "target_roas_or_cpa" in missing_read_contracts
    status: Literal["ready", "blocked"] = (
        "ready" if not blocking_missing_contracts else "blocked"
    )
    business_policy_ids = _business_policy_ids(
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_missing=target_missing,
        strategy_review_approved=strategy_review_approved,
        status=status,
    )
    operator_review_gates = _business_context_review_gates(
        profit_margin=profit_margin,
        business_goal=business_goal,
        budget_goal=budget_goal,
        target_missing=target_missing,
        strategy_review_approved=strategy_review_approved,
    )
    metric_tiles = _clean_metric_tiles(
        {
            "marża": _format_ratio_percent(profit_margin)
            if profit_margin is not None
            else "brak",
            "cel biznesowy": business_goal or "brak",
            "cel budżetu": budget_goal or "brak",
            "target ROAS": target_roas,
            "target CPA": _format_micros(target_cpa_micros),
            "target source": "potwierdzony"
            if target_confirmation is not None
            else None,
            "strategy review": _strategy_review_label(strategy_review_status),
        }
    )
    blocked_claims = [
        "profitability",
        "margin verdict",
        "budget scaling",
        "budget apply",
        "recommendation apply",
        "wasted budget",
    ]
    if status == "ready":
        if target_missing:
            summary = (
                "WILQ ma wstępny lokalny kontekst biznesowy Ads: marżę, cel "
                "biznesowy i cel budżetu. Target ROAS/CPA jest celowo pusty, więc "
                "KPI targetowe pozostają bez werdyktu i nie odblokowują skalowania "
                "ani apply."
            )
            next_step = (
                "Użyj marży i celu budżetu jako kontekstu review kampanii. Jeśli "
                "operator potwierdzi target ROAS albo CPA przez ActionObject, WILQ "
                "zapisze go w lokalnym state; do tego czasu target verdict zostaje "
                "zablokowany."
            )
        else:
            summary = (
                "WILQ ma lokalny kontekst biznesowy Ads: marżę, cel biznesowy, cel "
                "budżetu oraz target ROAS albo CPA. To pozwala interpretować KPI "
                "ostrożniej, ale nadal nie odblokowuje automatycznych zmian."
            )
            next_step = (
                "Użyj potwierdzonego targetu jako kontekstu review kampanii i "
                "budżetu. Apply nadal wymaga ActionObject, payload preview, "
                "potwierdzenia i audytu."
            )
    else:
        summary = (
            "WILQ ma live metryki Google Ads, ale nie ma kompletnego lokalnego "
            "kontekstu biznesowego: marży, celu biznesowego, celu budżetu albo "
            "targetu ROAS/CPA. Bez tego KPI są tylko triage, nie werdyktem."
        )
        next_step = (
            "Uzupełnij nie-sekretne wartości w repo-local .env: "
            "WILQ_ADS_PROFIT_MARGIN, WILQ_ADS_BUSINESS_GOAL, "
            "WILQ_ADS_BUDGET_GOAL oraz WILQ_ADS_TARGET_ROAS albo "
            "WILQ_ADS_TARGET_CPA_MICROS."
        )
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
        strategy_reviewed_by=strategy_review.reviewed_by
        if strategy_review is not None
        else None,
        strategy_reviewed_at=strategy_review.created_at
        if strategy_review is not None
        else None,
        strategy_review_summary=strategy_review.notes
        if strategy_review is not None
        else None,
        configured_sources=configured_sources,
        business_policy_ids=business_policy_ids,
        operator_review_gates=operator_review_gates,
        target_interpretation=_business_target_interpretation(
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
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        ),
        strategy_review_readiness_contract=_strategy_review_readiness_contract(
            strategy_review=strategy_review,
            strategy_review_status=strategy_review_status,
            strategy_review_approved=strategy_review_approved,
            profit_margin=profit_margin,
            business_goal=business_goal,
            budget_goal=budget_goal,
            target_roas=target_roas,
            target_cpa_micros=target_cpa_micros,
            missing_read_contracts=missing_read_contracts,
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        ),
        allowed_metrics=allowed_metrics,
        missing_read_contracts=missing_read_contracts,
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        metric_tiles=metric_tiles,
        next_step=next_step,
    )


def _strategy_review_readiness_contract(
    *,
    strategy_review: Any | None,
    strategy_review_status: Literal[
        "missing",
        "approved_for_prepare",
        "needs_changes",
        "rejected",
        "deferred",
    ],
    strategy_review_approved: bool,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_roas: float | None,
    target_cpa_micros: int | None,
    missing_read_contracts: list[str],
    evidence_ids: list[str],
) -> AdsStrategyReviewReadinessContract:
    required_validation = [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review",
    ]
    blocked_claims = [
        "profitability verdict",
        "target KPI verdict",
        "budget scaling",
        "budget apply",
        "recommendation apply",
        "automatic optimization",
    ]
    current_context = {
        "profit_margin": profit_margin,
        "business_goal": business_goal,
        "budget_goal": budget_goal,
        "target_roas": target_roas,
        "target_cpa_micros": target_cpa_micros,
    }
    if strategy_review_approved:
        summary = (
            "Human strategy review Ads jest zatwierdzone do prepare. To pozwala "
            "używać targetu w review, ale nie odblokowuje apply ani automatycznej "
            "optymalizacji."
        )
        next_step = (
            "Użyj zatwierdzonego review jako kontekstu decyzji. Każdy write path "
            "nadal wymaga osobnego ActionObject, preview, confirm i audytu."
        )
        status: Literal["ready", "blocked"] = "ready"
        contract_missing: list[str] = []
        action_ids: list[str] = []
    else:
        summary = (
            "Human strategy review Ads nie jest zatwierdzone, więc WILQ może "
            "tylko przygotować kolejki review. Target verdict, profitability "
            "verdict, skalowanie i apply pozostają zablokowane."
        )
        next_step = (
            "Otwórz ActionObject strategii, sprawdź marżę, cel biznesowy, cel "
            "budżetu i target ROAS/CPA, a potem zapisz outcome review."
        )
        status = "blocked"
        contract_missing = _unique(
            [
                missing
                for missing in missing_read_contracts
                if missing
                in {
                    "profit_margin",
                    "business_goal",
                    "human_budget_goal",
                    "target_roas_or_cpa",
                    "human_strategy_review",
                    "approved_human_strategy_review",
                }
            ]
        )
        action_ids = [ADS_STRATEGY_REVIEW_ACTION_ID]
    latest_outcome = (
        strategy_review.outcome if strategy_review is not None else None
    )
    return AdsStrategyReviewReadinessContract(
        status=status,
        title="Google Ads: gotowość human strategy review",
        summary=summary,
        latest_review_status=strategy_review_status,
        latest_review_outcome=latest_outcome,
        reviewed_by=strategy_review.reviewed_by if strategy_review is not None else None,
        reviewed_at=strategy_review.created_at if strategy_review is not None else None,
        current_context=current_context,
        required_validation=required_validation,
        missing_read_contracts=contract_missing,
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        apply_allowed=False,
        destructive=False,
        next_step=next_step,
    )


def _business_target_interpretation(
    *,
    status: Literal["ready", "blocked"],
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_roas: float | None,
    target_cpa_micros: int | None,
    target_missing: bool,
    strategy_review_status: str,
    strategy_review_approved: bool,
    business_policy_ids: list[str],
    evidence_ids: list[str],
) -> AdsBusinessTargetInterpretation:
    required_validation = [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review",
    ]
    if status == "blocked":
        return AdsBusinessTargetInterpretation(
            status="blocked",
            summary=(
                "WILQ nie interpretuje KPI biznesowo, dopóki brakuje marży, celu "
                "biznesowego albo celu budżetu."
            ),
            allowed_uses=[],
            blocked_uses=[
                "profitability_verdict",
                "target_kpi_verdict",
                "budget_scaling",
                "budget_apply",
                "wasted_budget_claim",
            ],
            missing_requirements=_business_target_missing_requirements(
                profit_margin=profit_margin,
                business_goal=business_goal,
                budget_goal=budget_goal,
                target_missing=target_missing,
                strategy_review_status=strategy_review_status,
                strategy_review_approved=strategy_review_approved,
            ),
            required_validation=required_validation,
            policy_ids=business_policy_ids,
            evidence_ids=evidence_ids,
        )
    allowed_uses = [
        "campaign_review_context",
        "budget_review_context",
        "human_strategy_review_context",
    ]
    if profit_margin is not None:
        allowed_uses.append("margin_context")
    if business_goal:
        allowed_uses.append("business_goal_alignment")
    if budget_goal:
        allowed_uses.append("budget_goal_guardrail")
    if target_missing:
        summary = (
            "WILQ może używać marży, celu biznesowego i celu budżetu jako kontekstu "
            "review, ale blokuje target KPI verdict, profitability verdict i apply "
            "do czasu potwierdzenia target ROAS albo CPA."
        )
        blocked_uses = [
            "target_kpi_verdict",
            "profitability_verdict",
            "budget_scaling",
            "budget_apply",
            "recommendation_apply",
        ]
        interpretation_status: Literal["ready", "preliminary", "blocked"] = "preliminary"
    elif not strategy_review_approved:
        summary = (
            "WILQ ma potwierdzony target ROAS albo CPA, ale blokuje target KPI "
            "verdict i apply, dopóki human strategy review nie będzie zatwierdzone."
        )
        blocked_uses = [
            "target_kpi_verdict",
            "profitability_verdict",
            "budget_scaling",
            "budget_apply",
            "recommendation_apply",
        ]
        interpretation_status = "preliminary"
        if target_roas is not None:
            allowed_uses.append("target_roas_review_context")
        if target_cpa_micros is not None:
            allowed_uses.append("target_cpa_review_context")
    else:
        summary = (
            "WILQ ma potwierdzony target ROAS albo CPA i może porównywać KPI do "
            "targetu w zatwierdzonym review. Apply nadal wymaga ActionObject, "
            "preview, confirm i audit."
        )
        blocked_uses = [
            "budget_apply",
            "recommendation_apply",
            "automatic_scaling",
            "profitability_verdict_without_value_model_review",
        ]
        interpretation_status = "ready"
        if target_roas is not None:
            allowed_uses.append("target_roas_review")
        if target_cpa_micros is not None:
            allowed_uses.append("target_cpa_review")
    return AdsBusinessTargetInterpretation(
        status=interpretation_status,
        summary=summary,
        allowed_uses=allowed_uses,
        blocked_uses=blocked_uses,
        missing_requirements=_business_target_missing_requirements(
            profit_margin=profit_margin,
            business_goal=business_goal,
            budget_goal=budget_goal,
            target_missing=target_missing,
            strategy_review_status=strategy_review_status,
            strategy_review_approved=strategy_review_approved,
        ),
        required_validation=required_validation,
        policy_ids=business_policy_ids,
        evidence_ids=evidence_ids,
    )


def _business_target_missing_requirements(
    *,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_missing: bool,
    strategy_review_status: str,
    strategy_review_approved: bool,
) -> list[str]:
    missing: list[str] = []
    if profit_margin is None:
        missing.append("profit_margin")
    if not business_goal:
        missing.append("business_goal")
    if not budget_goal:
        missing.append("human_budget_goal")
    if target_missing:
        missing.append("target_roas_or_cpa")
    if strategy_review_status == "missing":
        missing.append("human_strategy_review")
    elif not strategy_review_approved:
        missing.append("approved_human_strategy_review")
    return missing


def _business_policy_ids(
    *,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_missing: bool,
    strategy_review_approved: bool,
    status: Literal["ready", "blocked"],
) -> list[str]:
    policy_ids: list[str] = []
    if status == "blocked":
        policy_ids.append("complete_business_context_before_ads_verdicts")
    if profit_margin is not None:
        policy_ids.append("use_margin_as_context_not_profitability_verdict")
    if business_goal:
        policy_ids.append("align_campaign_review_to_business_goal")
    if budget_goal:
        policy_ids.append("honor_human_budget_goal_before_budget_changes")
    if target_missing:
        policy_ids.append("block_target_verdict_until_roas_or_cpa_confirmed")
    else:
        policy_ids.append("compare_kpis_to_confirmed_target_in_review")
    if strategy_review_approved:
        policy_ids.append("use_approved_strategy_review_before_target_verdict")
    else:
        policy_ids.append("block_target_verdict_until_strategy_review_approved")
    return _unique(policy_ids)


def _business_context_review_gates(
    *,
    profit_margin: float | None,
    business_goal: str | None,
    budget_goal: str | None,
    target_missing: bool,
    strategy_review_approved: bool,
) -> list[str]:
    gates = ["strategy_review_approved" if strategy_review_approved else "human_strategy_review"]
    gates.append(
        "review_profit_margin_model"
        if profit_margin is not None
        else "configure_profit_margin_or_value_model"
    )
    gates.append("review_business_goal" if business_goal else "configure_business_goal")
    gates.append(
        "review_human_budget_goal" if budget_goal else "configure_human_budget_goal"
    )
    gates.append("confirm_target_roas_or_cpa" if target_missing else "review_target_fit")
    return _unique(gates)


def _profit_margin_env() -> tuple[float | None, str | None]:
    return ads_profit_margin_env()


def _text_env(name: str) -> tuple[str | None, str | None]:
    return ads_text_env(name)


def _float_env(name: str) -> tuple[float | None, str | None]:
    return ads_float_env(name)


def _int_env(name: str) -> tuple[int | None, str | None]:
    return ads_int_env(name)


def _campaign_metric_rows(
    metric_facts: list[MetricFact],
    business_context_read_contract: AdsBusinessContextReadContract,
) -> list[AdsCampaignMetricRow]:
    grouped_facts: dict[tuple[str | None, str], list[MetricFact]] = {}
    row_metadata: dict[tuple[str | None, str], dict[str, str]] = {}
    seen_metric_keys: set[tuple[str | None, str, str]] = set()
    for fact in metric_facts:
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name")
        if not campaign_id and not campaign_name:
            continue
        row_key = (campaign_id, campaign_name or f"campaign {campaign_id}")
        metadata = row_metadata.setdefault(row_key, {})
        for key in ("campaign_status", "advertising_channel_type"):
            value = fact.dimensions.get(key)
            if value:
                metadata[key] = value
        if fact.name not in {
            "clicks",
            "impressions",
            "cost_micros",
            "conversions",
            "conversion_value",
        }:
            continue
        metric_key = (campaign_id, row_key[1], fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _campaign_metric_row(
            campaign_id,
            campaign_name,
            facts,
            row_metadata.get((campaign_id, campaign_name), {}),
            business_context_read_contract,
        )
        for (campaign_id, campaign_name), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_campaign_row_sort_key)


def _campaign_metric_row(
    campaign_id: str | None,
    campaign_name: str,
    facts: list[MetricFact],
    metadata: dict[str, str] | None = None,
    business_context_read_contract: AdsBusinessContextReadContract | None = None,
) -> AdsCampaignMetricRow:
    facts_by_name = {fact.name: fact for fact in facts}
    metadata_dimensions = metadata or {}
    first_dimensions = next(
        (
            fact.dimensions
            for fact in facts
            if fact.dimensions.get("advertising_channel_type")
            or fact.dimensions.get("campaign_status")
        ),
        metadata_dimensions or (facts[0].dimensions if facts else {}),
    )
    expected_metrics = [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    clicks = _int_metric_value(facts_by_name.get("clicks"))
    impressions = _int_metric_value(facts_by_name.get("impressions"))
    cost_micros = _int_metric_value(facts_by_name.get("cost_micros"))
    conversions = _float_metric_value(facts_by_name.get("conversions"))
    conversion_value = _float_metric_value(facts_by_name.get("conversion_value"))
    advertising_channel_type = first_dimensions.get("advertising_channel_type")
    campaign_status = first_dimensions.get("campaign_status")
    missing_metrics = [name for name in expected_metrics if name not in facts_by_name]
    target_context = campaign_target_context(
        cost_micros=cost_micros,
        conversions=conversions,
        conversion_value=conversion_value,
        target_roas=business_context_read_contract.target_roas
        if business_context_read_contract is not None
        else None,
        target_cpa_micros=business_context_read_contract.target_cpa_micros
        if business_context_read_contract is not None
        else None,
    )
    review_score = campaign_review_score(
        campaign_name=campaign_name,
        advertising_channel_type=advertising_channel_type,
        clicks=clicks,
        impressions=impressions,
        cost_micros=cost_micros,
        conversions=conversions,
        missing_metrics=missing_metrics,
        target_status=target_context["target_status"],
    )
    return AdsCampaignMetricRow(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        campaign_status=campaign_status,
        advertising_channel_type=advertising_channel_type,
        clicks=clicks,
        impressions=impressions,
        cost_micros=cost_micros,
        conversions=conversions,
        conversion_value=conversion_value,
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=missing_metrics,
        blocked_claims=["CPA", "ROAS", "search-term waste", "wasted budget"],
        target_status=target_context["target_status"],
        target_status_label=target_context["target_status_label"],
        review_priority=campaign_review_priority(review_score),
        review_score=review_score,
        review_reason=campaign_review_reason(
            campaign_name=campaign_name,
            advertising_channel_type=advertising_channel_type,
            clicks=clicks,
            impressions=impressions,
            cost_micros=cost_micros,
            conversions=conversions,
            missing_metrics=missing_metrics,
            target_status=target_context["target_status"],
            target_status_label=target_context["target_status_label"],
        ),
        human_review_gates=campaign_review_gates(
            campaign_name=campaign_name,
            advertising_channel_type=advertising_channel_type,
            cost_micros=cost_micros,
            conversions=conversions,
            target_status=target_context["target_status"],
        ),
    )


def _derived_kpi_read_contract(
    campaign_read_contract: AdsCampaignReadContract,
    account_currency_read_contract: AdsAccountCurrencyReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
) -> AdsDerivedKpiReadContract:
    missing_read_contracts = ["profit_margin", "change_history", "recommendations"]
    if account_currency_read_contract.status != "ready":
        missing_read_contracts.insert(0, "account_currency")
    blocked_claims = [
        "profitability",
        "budget scaling",
        "wasted budget",
        "recommendation apply",
        "incrementality",
    ]
    kpi_rows = [
        _derived_kpi_row(row, business_context_read_contract)
        for row in campaign_read_contract.campaign_rows
    ]
    kpi_rows.sort(key=lambda row: (row.target_review_priority, row.campaign_name))
    if kpi_rows:
        rows_with_cpa = sum(1 for row in kpi_rows if row.cost_per_conversion_micros is not None)
        rows_with_roas = sum(1 for row in kpi_rows if row.roas is not None)
        rows_with_target_context = sum(
            1
            for row in kpi_rows
            if row.roas_vs_target is not None or row.cpa_vs_target_micros is not None
        )
        rows_within_target = sum(1 for row in kpi_rows if row.target_status == "within_target")
        rows_outside_target = sum(1 for row in kpi_rows if row.target_status == "outside_target")
        rows_with_spend_without_conversions = sum(
            1 for row in kpi_rows if row.target_status == "spend_without_conversions"
        )
        target_summary = (
            f" Porównanie z targetem dostępne dla {rows_with_target_context} kampanii."
            f" Triage targetu: w targetcie {rows_within_target},"
            f" poza targetem {rows_outside_target}, koszt bez konwersji"
            f" {rows_with_spend_without_conversions}."
            if rows_with_target_context
            else ""
        )
        allowed_metrics = [
            "ctr",
            "average_cpc_micros",
            "conversion_rate",
            "cost_per_conversion_micros",
            "roas",
            "value_per_conversion",
        ]
        if business_context_read_contract.target_roas is not None:
            allowed_metrics.extend(["target_roas", "roas_vs_target", "target_status"])
        if business_context_read_contract.target_cpa_micros is not None:
            allowed_metrics.extend(["target_cpa_micros", "cpa_vs_target_micros", "target_status"])
        return AdsDerivedKpiReadContract(
            status="ready",
            title="Google Ads: wyliczone KPI kampanii",
            summary=(
                f"WILQ może policzyć KPI dla {len(kpi_rows)} kampanii: "
                f"CPA dostępne dla {rows_with_cpa}, ROAS dostępny dla {rows_with_roas}. "
                "To są obliczenia z bieżących metric facts, nie werdykt opłacalności."
                f"{target_summary}"
            ),
            allowed_metrics=_unique(allowed_metrics),
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                evidence_id for row in kpi_rows for evidence_id in row.evidence_ids
            ),
            kpi_rows=kpi_rows,
            next_step=(
                "Użyj KPI i ewentualnego porównania z targetem do triage kampanii. "
                "Przed decyzją budżetową sprawdź marżę, pacing budżetu, historię "
                "zmian i rekomendacje."
            ),
        )
    return AdsDerivedKpiReadContract(
        status="blocked",
        title="Google Ads: brak wyliczalnych KPI kampanii",
        summary="WILQ nie ma kompletnych campaign facts do wyliczenia KPI.",
        allowed_metrics=[],
        missing_read_contracts=["campaign activity", *missing_read_contracts],
        blocked_claims=["CTR", "CPC", "CPA", "ROAS", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=campaign_read_contract.evidence_ids,
        kpi_rows=[],
        next_step="Najpierw zbierz read-only campaign facts z Google Ads.",
    )


def _derived_kpi_row(
    row: AdsCampaignMetricRow,
    business_context_read_contract: AdsBusinessContextReadContract,
) -> AdsDerivedKpiRow:
    source_metric_names = [fact.name for fact in row.metric_facts]
    missing_metrics = list(row.missing_metrics)
    if not row.impressions:
        missing_metrics.append("nonzero_impressions")
    if not row.clicks:
        missing_metrics.extend(["nonzero_clicks_for_cpc", "nonzero_clicks_for_conversion_rate"])
    if not row.conversions:
        missing_metrics.extend(
            ["nonzero_conversions_for_cpa", "nonzero_conversions_for_value_per_conversion"]
        )
    if not row.cost_micros:
        missing_metrics.append("nonzero_cost_for_roas")
    cost_per_conversion_micros = _ratio(row.cost_micros, row.conversions)
    roas = _ratio(row.conversion_value, _micros_to_account_units(row.cost_micros))
    target_roas = business_context_read_contract.target_roas
    target_cpa_micros = business_context_read_contract.target_cpa_micros
    target_status, target_status_label, target_review_priority = _target_triage(
        row=row,
        cost_per_conversion_micros=cost_per_conversion_micros,
        roas=roas,
        target_cpa_micros=target_cpa_micros,
        target_roas=target_roas,
    )
    return AdsDerivedKpiRow(
        campaign_id=row.campaign_id,
        campaign_name=row.campaign_name,
        ctr=_ratio(row.clicks, row.impressions),
        average_cpc_micros=_ratio(row.cost_micros, row.clicks),
        conversion_rate=_ratio(row.conversions, row.clicks),
        cost_per_conversion_micros=cost_per_conversion_micros,
        roas=roas,
        value_per_conversion=_ratio(row.conversion_value, row.conversions),
        target_roas=target_roas,
        roas_vs_target=_difference(roas, target_roas),
        target_cpa_micros=target_cpa_micros,
        cpa_vs_target_micros=_difference(cost_per_conversion_micros, target_cpa_micros),
        target_status=target_status,
        target_status_label=target_status_label,
        target_review_priority=target_review_priority,
        evidence_ids=row.evidence_ids,
        source_metric_names=_unique(source_metric_names),
        missing_metrics=_unique(missing_metrics),
        blocked_claims=[
            "profitability",
            "budget scaling",
            "wasted budget",
            "recommendation apply",
        ],
    )


def _target_triage(
    *,
    row: AdsCampaignMetricRow,
    cost_per_conversion_micros: float | None,
    roas: float | None,
    target_cpa_micros: int | None,
    target_roas: float | None,
) -> tuple[AdsTargetStatus, str, int]:
    if target_cpa_micros is not None:
        if cost_per_conversion_micros is not None:
            if cost_per_conversion_micros <= target_cpa_micros:
                return "within_target", "CPA w targetcie", 40
            return "outside_target", "CPA powyżej targetu", 20
        if (row.cost_micros or 0) > 0 and not row.conversions:
            return "spend_without_conversions", "koszt bez konwersji", 15
        return "insufficient_data", "brak CPA do porównania", 70

    if target_roas is not None:
        if roas is not None:
            if roas >= target_roas:
                return "within_target", "ROAS w targetcie", 40
            return "outside_target", "ROAS poniżej targetu", 20
        if (row.cost_micros or 0) > 0 and not row.conversion_value:
            return "spend_without_conversions", "koszt bez wartości konwersji", 15
        return "insufficient_data", "brak ROAS do porównania", 70

    return "no_target", "brak targetu", 90


def _budget_pacing_section(
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact for row in budget_pacing_read_contract.budget_rows for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_budget_pacing",
        title="Kontekst budżetu Google Ads",
        status=budget_pacing_read_contract.status,
        summary=budget_pacing_read_contract.summary,
        diagnosis=(
            "WILQ może pokazać koszt z 7 dni względem budżetu dziennego, jeśli "
            "campaign_budget facts istnieją. To nadal nie jest rekomendacja "
            "skalowania ani apply budżetu."
        ),
        next_step=budget_pacing_read_contract.next_step,
        source_connectors=budget_pacing_read_contract.source_connectors,
        evidence_ids=budget_pacing_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=budget_pacing_read_contract.action_ids,
        blocked_claims=budget_pacing_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _latest_refresh_has_summary_metric(
    latest_refresh: ConnectorRefreshRun | None,
    metric_name: str,
) -> bool:
    if latest_refresh is None:
        return False
    return metric_name in latest_refresh.metric_summary


def _remove_missing_contract_names(
    missing_read_contracts: list[str],
    *contract_names: str,
) -> list[str]:
    removals = set(contract_names)
    return [contract for contract in missing_read_contracts if contract not in removals]



def _recommendations_section(
    recommendations_read_contract: AdsRecommendationsReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in recommendations_read_contract.recommendation_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_recommendations",
        title="Rekomendacje Google Ads do review",
        status=recommendations_read_contract.status,
        summary=recommendations_read_contract.summary,
        diagnosis=(
            "WILQ może pokazać typy aktywnych rekomendacji Google Ads jako input "
            "do review. To nie jest zgoda na apply ani dowód, że rekomendacja jest "
            "biznesowo dobra dla Ekologus."
        ),
        next_step=recommendations_read_contract.next_step,
        source_connectors=recommendations_read_contract.source_connectors,
        evidence_ids=recommendations_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=recommendations_read_contract.action_ids,
        blocked_claims=recommendations_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )



def _impression_share_section(
    impression_share_read_contract: AdsImpressionShareReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in impression_share_read_contract.impression_share_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_impression_share",
        title="Udział w wyświetleniach Google Ads",
        status=impression_share_read_contract.status,
        summary=impression_share_read_contract.summary,
        diagnosis=(
            "WILQ może pokazać search impression share oraz utracony udział przez "
            "budżet albo ranking. To jest kontekst ograniczeń, nie automatyczna "
            "rekomendacja budżetowa."
        ),
        next_step=impression_share_read_contract.next_step,
        source_connectors=impression_share_read_contract.source_connectors,
        evidence_ids=impression_share_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=[],
        blocked_claims=impression_share_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _campaign_triage_read_contract(
    campaign_read_contract: AdsCampaignReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    action_ids: list[str],
) -> AdsCampaignTriageReadContract:
    campaign_review_action_ids = _campaign_review_action_ids(action_ids)
    rows = [
        _campaign_triage_row(
            campaign_row,
            business_context_read_contract,
            _row_by_campaign_id(derived_kpi_read_contract.kpi_rows, campaign_row.campaign_id),
            _row_by_campaign_id(budget_pacing_read_contract.budget_rows, campaign_row.campaign_id),
            _rows_by_campaign_id(
                recommendations_read_contract.recommendation_rows,
                campaign_row.campaign_id,
            ),
            _row_by_campaign_id(
                impression_share_read_contract.impression_share_rows,
                campaign_row.campaign_id,
            ),
            campaign_review_action_ids,
        )
        for campaign_row in campaign_read_contract.campaign_rows
    ]
    rows.sort(key=lambda row: (-row.review_score, row.campaign_name))
    blocked_claims = [
        "wasted budget",
        "profitability",
        "budget scaling",
        "budget apply",
        "recommendation apply",
        "campaign mutation",
    ]
    if rows:
        urgent_rows = sum(1 for row in rows if row.review_priority == "pilne")
        high_rows = sum(1 for row in rows if row.review_priority == "wysokie")
        return AdsCampaignTriageReadContract(
            status="ready",
            title="Kolejność review kampanii Ads",
            summary=(
                f"WILQ połączył campaign activity, KPI, budżet, rekomendacje i "
                f"impression share dla {len(rows)} kampanii. Pilne={urgent_rows}, "
                f"wysokie={high_rows}. To nie jest werdyktem wasted budget, "
                "profitability, CPA ani ROAS; to kolejność ręcznego review."
            ),
            allowed_metrics=[
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
                "ctr",
                "average_cpc_micros",
                "conversion_rate",
                "cost_per_conversion_micros",
                "roas",
                "spend_to_budget_ratio_7d",
                "search_budget_lost_impression_share",
                "recommendation_count",
            ],
            missing_read_contracts=business_context_read_contract.missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            triage_rows=rows,
            action_ids=campaign_review_action_ids,
            next_step=(
                "Przejrzyj kampanie od góry kolejki. Najpierw sprawdź cel kampanii, "
                "jakość konwersji, budżet, search terms i rekomendacje; apply i "
                "skalowanie zostają zablokowane."
            ),
        )
    return AdsCampaignTriageReadContract(
        status="blocked",
        title="Kolejność review kampanii Ads",
        summary="WILQ nie ma campaign rows potrzebnych do kolejki review kampanii.",
        allowed_metrics=[],
        missing_read_contracts=["campaign activity"],
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=campaign_read_contract.evidence_ids,
        triage_rows=[],
        action_ids=[],
        next_step="Najpierw zbierz read-only Google Ads campaign facts.",
    )


def _campaign_triage_row(
    campaign_row: AdsCampaignMetricRow,
    business_context_read_contract: AdsBusinessContextReadContract,
    kpi_row: AdsDerivedKpiRow | None,
    budget_row: AdsBudgetPacingRow | None,
    recommendation_rows: list[AdsRecommendationRow],
    impression_share_row: AdsImpressionShareRow | None,
    action_ids: list[str],
) -> AdsCampaignTriageRow:
    source_metric_values: list[str] = [fact.name for fact in campaign_row.metric_facts]
    if kpi_row is not None:
        source_metric_values.extend(kpi_row.source_metric_names)
    if budget_row is not None:
        source_metric_values.extend(fact.name for fact in budget_row.metric_facts)
    for recommendation_row in recommendation_rows:
        source_metric_values.extend(fact.name for fact in recommendation_row.metric_facts)
    if impression_share_row is not None:
        source_metric_values.extend(
            fact.name for fact in impression_share_row.metric_facts
        )
    source_metric_names = _unique(source_metric_values)
    evidence_ids = _unique(
        [
            *campaign_row.evidence_ids,
            *(kpi_row.evidence_ids if kpi_row is not None else []),
            *(budget_row.evidence_ids if budget_row is not None else []),
            *(
                evidence_id
                for recommendation_row in recommendation_rows
                for evidence_id in recommendation_row.evidence_ids
            ),
            *(impression_share_row.evidence_ids if impression_share_row is not None else []),
        ]
    )
    has_budget_apply_preview = bool(
        budget_row is not None and budget_row.payload_preview is not None
    )
    has_recommendation_apply_preview = any(
        row.payload_preview is not None for row in recommendation_rows
    )
    return AdsCampaignTriageRow(
        campaign_id=campaign_row.campaign_id,
        campaign_name=campaign_row.campaign_name,
        campaign_status=campaign_row.campaign_status,
        advertising_channel_type=campaign_row.advertising_channel_type,
        review_priority=campaign_row.review_priority,
        review_score=campaign_row.review_score,
        review_reason=(
            f"{campaign_row.review_reason} Dodatkowy kontekst review: "
            f"KPI={'tak' if kpi_row is not None else 'brak'}, "
            f"budżet={'tak' if budget_row is not None else 'brak'}, "
            f"rekomendacje={len(recommendation_rows)}, "
            f"impression_share={'tak' if impression_share_row is not None else 'brak'}."
        ),
        next_step=(
            "Otwórz kampanię w Ads Doctor, sprawdź cel, konwersje, budżet, "
            "search terms i rekomendacje. Nie wykonuj apply bez ActionObject "
            "validation i human confirm."
        ),
        target_status=campaign_row.target_status,
        target_status_label=campaign_row.target_status_label,
        clicks=campaign_row.clicks,
        impressions=campaign_row.impressions,
        cost_micros=campaign_row.cost_micros,
        conversions=campaign_row.conversions,
        conversion_value=campaign_row.conversion_value,
        ctr=kpi_row.ctr if kpi_row is not None else None,
        average_cpc_micros=kpi_row.average_cpc_micros if kpi_row is not None else None,
        conversion_rate=kpi_row.conversion_rate if kpi_row is not None else None,
        cost_per_conversion_micros=(
            kpi_row.cost_per_conversion_micros if kpi_row is not None else None
        ),
        roas=kpi_row.roas if kpi_row is not None else None,
        spend_to_budget_ratio_7d=(
            budget_row.spend_to_budget_ratio_7d if budget_row is not None else None
        ),
        search_budget_lost_impression_share=(
            impression_share_row.search_budget_lost_impression_share
            if impression_share_row is not None
            else None
        ),
        recommendation_count=len(recommendation_rows),
        recommendation_types=_unique(row.recommendation_type for row in recommendation_rows),
        has_budget_apply_preview=has_budget_apply_preview,
        has_recommendation_apply_preview=has_recommendation_apply_preview,
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        source_metric_names=source_metric_names,
        missing_read_contracts=business_context_read_contract.missing_read_contracts,
        blocked_claims=[
            "wasted budget",
            "profitability",
            "budget scaling",
            "budget apply",
            "recommendation apply",
            "campaign mutation",
        ],
        human_review_gates=_unique(
            [
                *campaign_row.human_review_gates,
                *(
                    [
                        "review_recommendation_type",
                        "review_impact_metrics",
                        "review_change_history",
                        "review_business_goal",
                    ]
                    if recommendation_rows
                    else []
                ),
                *(["campaign_budget_apply_safety"] if has_budget_apply_preview else []),
            ]
        ),
    )


def _optimizer_readiness_contract(
    campaign_triage_read_contract: AdsCampaignTriageReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    change_history_read_contract: AdsChangeHistoryReadContract,
    change_impact_readiness_contract: AdsChangeImpactReadinessContract,
    search_term_review_summary_contract: AdsSearchTermReviewSummaryContract,
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
) -> AdsOptimizerReadinessContract:
    items = [
        _optimizer_readiness_item(
            item_id="campaign_review_queue",
            title="Kolejność review kampanii",
            status="ready" if campaign_triage_read_contract.triage_rows else "blocked",
            summary=campaign_triage_read_contract.summary,
            next_step=campaign_triage_read_contract.next_step,
            source_contract_ids=[campaign_triage_read_contract.id],
            allowed_metrics=campaign_triage_read_contract.allowed_metrics,
            missing_read_contracts=campaign_triage_read_contract.missing_read_contracts,
            blocked_claims=campaign_triage_read_contract.blocked_claims,
            source_connectors=campaign_triage_read_contract.source_connectors,
            evidence_ids=campaign_triage_read_contract.evidence_ids,
            action_ids=campaign_triage_read_contract.action_ids,
            risk=ActionRisk.medium,
        ),
        _optimizer_readiness_item(
            item_id="budget_and_recommendation_review",
            title="Budżety, rekomendacje i impression share",
            status=(
                "ready"
                if budget_pacing_read_contract.budget_rows
                or recommendations_read_contract.recommendation_rows
                or impression_share_read_contract.impression_share_rows
                else "blocked"
            ),
            summary=(
                "WILQ ma kontekst budżetu, rekomendacji albo impression share do "
                "ręcznego review. To nadal nie odblokowuje zmiany budżetu ani "
                "automatycznego przyjęcia rekomendacji."
            ),
            next_step=(
                "Porównaj pacing, rekomendacje i impression share przy kampaniach "
                "z kolejki triage; apply pozostaje zablokowany."
            ),
            source_contract_ids=[
                budget_pacing_read_contract.id,
                recommendations_read_contract.id,
                impression_share_read_contract.id,
            ],
            allowed_metrics=[
                *budget_pacing_read_contract.allowed_metrics,
                *recommendations_read_contract.allowed_metrics,
                *impression_share_read_contract.allowed_metrics,
            ],
            missing_read_contracts=[
                *budget_pacing_read_contract.missing_read_contracts,
                *recommendations_read_contract.missing_read_contracts,
                *impression_share_read_contract.missing_read_contracts,
            ],
            operator_review_gates=recommendations_read_contract.operator_review_gates,
            blocked_claims=[
                *budget_pacing_read_contract.blocked_claims,
                *recommendations_read_contract.blocked_claims,
                *impression_share_read_contract.blocked_claims,
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=[
                *budget_pacing_read_contract.evidence_ids,
                *recommendations_read_contract.evidence_ids,
                *impression_share_read_contract.evidence_ids,
            ],
            action_ids=[
                *budget_pacing_read_contract.action_ids,
                *recommendations_read_contract.action_ids,
            ],
            risk=ActionRisk.medium,
        ),
        _optimizer_readiness_item(
            item_id="search_terms_review_queue",
            title="Review search terms",
            status=(
                "ready"
                if search_term_review_summary_contract.total_search_term_count > 0
                else "blocked"
            ),
            summary=search_term_review_summary_contract.summary,
            next_step=search_term_review_summary_contract.next_step,
            source_contract_ids=[
                search_term_review_summary_contract.id,
                search_term_ngram_read_contract.id,
            ],
            allowed_metrics=[
                *search_term_review_summary_contract.allowed_metrics,
                *search_term_ngram_read_contract.allowed_metrics,
            ],
            missing_read_contracts=[
                *search_term_review_summary_contract.missing_read_contracts,
                *search_term_ngram_read_contract.missing_read_contracts,
            ],
            operator_review_gates=[
                *search_term_review_summary_contract.operator_review_gates,
                *search_term_ngram_read_contract.operator_review_gates,
            ],
            blocked_claims=[
                *search_term_review_summary_contract.blocked_claims,
                *search_term_ngram_read_contract.blocked_claims,
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=[
                *search_term_review_summary_contract.evidence_ids,
                *search_term_ngram_read_contract.evidence_ids,
            ],
            action_ids=search_term_ngram_read_contract.action_ids,
            risk=ActionRisk.medium,
        ),
        _optimizer_readiness_item(
            item_id="negative_keyword_review_queue",
            title="Kandydaci negative keywords",
            status=(
                "ready"
                if negative_keywords_read_contract.candidates
                and search_term_safety_read_contract.status == "ready"
                and keyword_match_context_read_contract.status == "ready"
                else "blocked"
            ),
            summary=negative_keywords_read_contract.summary,
            next_step=negative_keywords_read_contract.next_step,
            source_contract_ids=[
                negative_keywords_read_contract.id,
                search_term_safety_read_contract.id,
                keyword_match_context_read_contract.id,
            ],
            allowed_metrics=[
                *search_term_safety_read_contract.allowed_metrics,
                *keyword_match_context_read_contract.allowed_metrics,
            ],
            missing_read_contracts=[
                *negative_keywords_read_contract.missing_read_contracts,
                *search_term_safety_read_contract.missing_read_contracts,
                *keyword_match_context_read_contract.missing_read_contracts,
            ],
            operator_review_gates=[
                *search_term_safety_read_contract.operator_review_gates,
                *keyword_match_context_read_contract.operator_review_gates,
            ],
            blocked_claims=[
                *negative_keywords_read_contract.blocked_claims,
                *search_term_safety_read_contract.blocked_claims,
                *keyword_match_context_read_contract.blocked_claims,
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=[
                *negative_keywords_read_contract.evidence_ids,
                *search_term_safety_read_contract.evidence_ids,
                *keyword_match_context_read_contract.evidence_ids,
            ],
            action_ids=negative_keywords_read_contract.action_ids,
            risk=ActionRisk.high,
        ),
        _optimizer_readiness_item(
            item_id="custom_segments_review_queue",
            title="Custom segments z search terms",
            status="ready" if custom_segments_read_contract.candidates else "blocked",
            summary=custom_segments_read_contract.summary,
            next_step=custom_segments_read_contract.next_step,
            source_contract_ids=[
                custom_segments_read_contract.id,
                custom_segments_read_contract.audience_forecast_read_contract.id,
            ],
            missing_read_contracts=[
                *custom_segments_read_contract.missing_read_contracts,
                *custom_segments_read_contract.audience_forecast_read_contract.missing_read_contracts,
            ],
            operator_review_gates=[
                *custom_segments_read_contract.operator_review_gates,
                *custom_segments_read_contract.audience_forecast_read_contract.operator_review_gates,
            ],
            blocked_claims=[
                *custom_segments_read_contract.blocked_claims,
                *custom_segments_read_contract.audience_forecast_read_contract.blocked_claims,
            ],
            source_connectors=custom_segments_read_contract.source_connectors,
            evidence_ids=[
                *custom_segments_read_contract.evidence_ids,
                *custom_segments_read_contract.audience_forecast_read_contract.evidence_ids,
            ],
            action_ids=custom_segments_read_contract.action_ids,
            risk=ActionRisk.medium,
        ),
        _optimizer_readiness_item(
            item_id="keyword_planner_enrichment",
            title="Keyword Planner enrichment",
            status=keyword_planner_read_contract.status,
            summary=keyword_planner_read_contract.summary,
            next_step=keyword_planner_read_contract.next_step,
            source_contract_ids=[keyword_planner_read_contract.id],
            allowed_metrics=keyword_planner_read_contract.allowed_metrics,
            missing_read_contracts=keyword_planner_read_contract.missing_read_contracts,
            operator_review_gates=keyword_planner_read_contract.operator_review_gates,
            blocked_claims=keyword_planner_read_contract.blocked_claims,
            source_connectors=keyword_planner_read_contract.source_connectors,
            evidence_ids=keyword_planner_read_contract.evidence_ids,
            action_ids=[],
            risk=ActionRisk.medium,
        ),
        _optimizer_readiness_item(
            item_id="change_history_impact_review",
            title="Impact review historii zmian",
            status=change_impact_readiness_contract.status,
            summary=change_impact_readiness_contract.summary,
            next_step=change_impact_readiness_contract.next_step,
            source_contract_ids=[
                change_history_read_contract.id,
                change_impact_readiness_contract.id,
            ],
            allowed_metrics=change_impact_readiness_contract.allowed_metrics,
            missing_read_contracts=change_impact_readiness_contract.missing_read_contracts,
            blocked_claims=change_impact_readiness_contract.blocked_claims,
            source_connectors=change_impact_readiness_contract.source_connectors,
            evidence_ids=change_impact_readiness_contract.evidence_ids,
            action_ids=change_impact_readiness_contract.action_ids,
            risk=ActionRisk.high,
        ),
        _optimizer_readiness_item(
            item_id="ads_apply_safety_gate",
            title="Apply i mutacje Ads",
            status="blocked",
            summary=(
                "WILQ ma część podglądów review, ale nie ma jeszcze bezpiecznej "
                "ścieżki wykonania zmian Ads. Każda mutacja pozostaje zablokowana."
            ),
            next_step=(
                "Zostań w trybie review-only: waliduj ActionObjecty, nie wykonuj "
                "budżetów, rekomendacji, wykluczeń ani segmentów bez osobnego "
                "confirm/audit contract."
            ),
            source_contract_ids=[
                budget_pacing_read_contract.id,
                recommendations_read_contract.id,
                custom_segments_read_contract.id,
                negative_keywords_read_contract.id,
            ],
            missing_read_contracts=[
                "google_ads_mutation_audit",
                "human_confirm_before_apply",
            ],
            operator_review_gates=["human_confirm_before_apply"],
            blocked_claims=[
                "budget apply",
                "recommendation apply",
                "negative keyword apply",
                "targeting applied",
                "campaign mutation",
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=[
                *budget_pacing_read_contract.evidence_ids,
                *recommendations_read_contract.evidence_ids,
                *custom_segments_read_contract.evidence_ids,
                *negative_keywords_read_contract.evidence_ids,
            ],
            action_ids=[
                *budget_pacing_read_contract.action_ids,
                *recommendations_read_contract.action_ids,
                *custom_segments_read_contract.action_ids,
                *negative_keywords_read_contract.action_ids,
            ],
            risk=ActionRisk.high,
        ),
    ]
    ready_area_count = sum(1 for item in items if item.status == "ready")
    blocked_area_count = sum(1 for item in items if item.status == "blocked")
    status: Literal["review_ready", "blocked"] = (
        "review_ready" if ready_area_count > 0 else "blocked"
    )
    return AdsOptimizerReadinessContract(
        status=status,
        title="Ads Optimizer readiness",
        summary=(
            f"WILQ ma {ready_area_count} obszarów gotowych do review i "
            f"{blocked_area_count} obszarów zablokowanych. To jest tryb "
            "review-only: kontrakt porządkuje pracę marketera, ale nie "
            "odblokowuje apply, impact claimów ani decyzji o rentowności."
        ),
        ready_area_count=ready_area_count,
        blocked_area_count=blocked_area_count,
        readiness_items=items,
        allowed_metrics=_unique(
            metric for item in items for metric in item.allowed_metrics
        ),
        missing_read_contracts=_unique(
            contract for item in items for contract in item.missing_read_contracts
        ),
        operator_review_gates=_unique(
            gate for item in items for gate in item.operator_review_gates
        ),
        blocked_claims=_unique(
            claim
            for item in items
            for claim in [
                *item.blocked_claims,
                "CPA verdict",
                "ROAS verdict",
                "profitability",
            ]
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id for item in items for evidence_id in item.evidence_ids
        ),
        action_ids=_unique(action_id for item in items for action_id in item.action_ids),
        next_step=(
            "Pracuj od obszarów ready, ale każdy wniosek o zmianie budżetu, "
            "rekomendacji, wykluczeń, segmentów albo wpływie zmian traktuj jako "
            "blocked, dopóki odpowiedni read/apply/audit contract nie będzie gotowy."
        ),
    )


def _optimizer_readiness_item(
    *,
    item_id: str,
    title: str,
    status: Literal["ready", "blocked"],
    summary: str,
    next_step: str,
    source_contract_ids: list[str],
    allowed_metrics: list[str] | None = None,
    missing_read_contracts: list[str] | None = None,
    operator_review_gates: list[str] | None = None,
    blocked_claims: list[str] | None = None,
    source_connectors: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    action_ids: list[str] | None = None,
    risk: ActionRisk = ActionRisk.medium,
) -> AdsOptimizerReadinessItem:
    return AdsOptimizerReadinessItem(
        id=item_id,
        title=title,
        status=status,
        summary=summary,
        next_step=next_step,
        source_contract_ids=_unique(source_contract_ids),
        allowed_metrics=_unique(allowed_metrics or []),
        missing_read_contracts=_unique(missing_read_contracts or []),
        operator_review_gates=_unique(operator_review_gates or []),
        blocked_claims=_unique(blocked_claims or []),
        source_connectors=_unique(source_connectors or []),
        evidence_ids=_unique(evidence_ids or []),
        action_ids=_unique(action_ids or []),
        risk=risk,
    )


def _row_by_campaign_id(rows: list[Any], campaign_id: str | None) -> Any | None:
    for row in rows:
        if getattr(row, "campaign_id", None) == campaign_id:
            return row
    return None


def _rows_by_campaign_id(rows: list[Any], campaign_id: str | None) -> list[Any]:
    return [row for row in rows if getattr(row, "campaign_id", None) == campaign_id]


def _change_impact_readiness_contract(
    change_history_read_contract: AdsChangeHistoryReadContract,
    campaign_read_contract: AdsCampaignReadContract,
) -> AdsChangeImpactReadinessContract:
    base_missing = [
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_change_impact_review",
        "apply_preview",
    ]
    blocked_claims = [
        "change impact",
        "performance uplift",
        "budget scaling",
        "budget apply",
        "campaign mutation",
    ]
    rows = [
        _change_impact_readiness_row(change_row, campaign_read_contract.campaign_rows)
        for change_row in change_history_read_contract.change_history_rows
    ]
    row_missing = _unique(
        missing for row in rows for missing in row.missing_read_contracts
    )
    missing_read_contracts = _unique(
        [
            *(
                ["change_event_rows"]
                if not change_history_read_contract.change_history_rows
                else []
            ),
            *row_missing,
            *base_missing,
        ]
    )
    allowed_metrics = [
        "change_event_available",
        "change_event_changed_field_count",
    ]
    if any(row.current_campaign_metrics_available for row in rows):
        allowed_metrics.extend(
            [
                "current_campaign_clicks",
                "current_campaign_impressions",
                "current_campaign_cost_micros",
                "current_campaign_conversions",
                "current_campaign_conversion_value",
            ]
        )
    if rows:
        campaign_context_count = sum(
            1 for row in rows if row.current_campaign_metrics_available
        )
        summary = (
            f"WILQ ma {len(rows)} zdarzeń zmian do impact review i "
            f"{campaign_context_count} powiązanych snapshotów kampanii. To jest "
            "readiness do ręcznego audytu, nie dowód wpływu zmian."
        )
    else:
        summary = (
            "WILQ nie ma change_event rows do impact review, więc nie może zbudować "
            "okien wyników przed/po ani przypisać zmian do kampanii."
        )
    return AdsChangeImpactReadinessContract(
        status="blocked",
        title="Google Ads: gotowość impact review zmian",
        summary=summary,
        allowed_metrics=allowed_metrics,
        missing_read_contracts=missing_read_contracts,
        blocked_claims=blocked_claims,
        source_connectors=change_history_read_contract.source_connectors,
        evidence_ids=_unique(
            [
                *change_history_read_contract.evidence_ids,
                *(evidence_id for row in rows for evidence_id in row.evidence_ids),
            ]
        ),
        readiness_rows=rows,
        action_ids=change_history_read_contract.action_ids,
        api_mutation_ready=False,
        apply_allowed=False,
        next_step=(
            "Użyj tego jako checklisty readiness: sprawdź, czy są change rows, "
            "aktualny odczyt kampanii i okna wyników przed/po. Nie claimuj "
            "wpływu zmian bez pre/post windows i human review."
        ),
    )


def _change_impact_readiness_row(
    change_row: AdsChangeHistoryRow,
    campaign_rows: list[AdsCampaignMetricRow],
) -> AdsChangeImpactReadinessRow:
    campaign_row = _row_by_campaign_id(campaign_rows, change_row.campaign_id)
    missing_read_contracts = [
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_change_impact_review",
        "apply_preview",
    ]
    if campaign_row is None:
        missing_read_contracts.insert(0, "current_campaign_snapshot")
    return AdsChangeImpactReadinessRow(
        change_event_id=change_row.change_event_id,
        campaign_id=change_row.campaign_id,
        campaign_name=getattr(campaign_row, "campaign_name", None),
        change_date_time=change_row.change_date_time,
        changed_fields=change_row.changed_fields,
        current_campaign_metrics_available=campaign_row is not None,
        pre_window_available=False,
        post_window_available=False,
        current_clicks=getattr(campaign_row, "clicks", None),
        current_impressions=getattr(campaign_row, "impressions", None),
        current_cost_micros=getattr(campaign_row, "cost_micros", None),
        current_conversions=getattr(campaign_row, "conversions", None),
        current_conversion_value=getattr(campaign_row, "conversion_value", None),
        missing_read_contracts=missing_read_contracts,
        evidence_ids=_unique(
            [
                *change_row.evidence_ids,
                *(getattr(campaign_row, "evidence_ids", []) if campaign_row else []),
            ]
        ),
        blocked_claims=[
            "change impact",
            "performance uplift",
            "budget scaling",
            "budget apply",
            "campaign mutation",
        ],
    )



def _change_history_section(
    change_history_read_contract: AdsChangeHistoryReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in change_history_read_contract.change_history_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_change_history",
        title="Historia zmian Google Ads",
        status=change_history_read_contract.status,
        summary=change_history_read_contract.summary,
        diagnosis=(
            "WILQ pokazuje ostatnie zmiany jako kontekst audytu kampanii. To nie "
            "jest jeszcze dowód wpływu zmiany na wynik ani zgoda na kolejną mutację."
        ),
        next_step=change_history_read_contract.next_step,
        source_connectors=change_history_read_contract.source_connectors,
        evidence_ids=change_history_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=change_history_read_contract.action_ids,
        blocked_claims=change_history_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _change_history_with_action_ids(
    change_history_read_contract: AdsChangeHistoryReadContract,
    action_ids: list[str],
) -> AdsChangeHistoryReadContract:
    if not change_history_read_contract.change_history_rows:
        return change_history_read_contract
    change_history_action_ids = _change_history_action_ids(action_ids)
    return change_history_read_contract.model_copy(
        update={"action_ids": change_history_action_ids}
    )


def _change_history_row_sort_key(row: AdsChangeHistoryRow) -> tuple[str, str]:
    return (row.change_date_time or "", row.change_event_id or "")


def _ratio(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _difference(
    left: float | int | None,
    right: float | int | None,
) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 6)


def _micros_to_account_units(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value) / 1_000_000


def _campaign_row_sort_key(row: AdsCampaignMetricRow) -> tuple[int, int, int, str]:
    return (
        -row.review_score,
        -(row.cost_micros or 0),
        -(row.clicks or 0),
        row.campaign_name,
    )


def _int_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        try:
            return int(float(fact.value))
        except ValueError:
            return None
    return int(fact.value)


def _float_metric_value(fact: MetricFact | None) -> float | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        try:
            return float(fact.value)
        except ValueError:
            return None
    return float(fact.value)


def _int_metric_delta(base: int | None, potential: int | None) -> int | None:
    if base is None or potential is None:
        return None
    return potential - base


def _float_metric_delta(base: float | None, potential: float | None) -> float | None:
    if base is None or potential is None:
        return None
    return round(potential - base, 6)


def _bool_metric_value(fact: MetricFact | None) -> bool | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        return fact.value.lower() in {"1", "true", "yes"}
    return bool(fact.value)


def _format_float(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _format_signed_number(value: int | float | None) -> str:
    if value is None:
        return "brak"
    numeric_value = float(value)
    if numeric_value == 0:
        return "0"
    prefix = "+" if numeric_value > 0 else ""
    return f"{prefix}{_format_float(numeric_value)}"


def _search_terms_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsSearchTermsReadContract:
    rows = _search_term_metric_rows(metric_facts)
    missing_read_contracts = [
        "keyword match context",
        "90_day_safety_check",
    ]
    operator_review_gates = ["negative_keyword_action_validation"]
    blocked_claims = [
        "search-term waste",
        "negative keyword candidates",
        "negative keyword apply",
        "CPA",
        "ROAS",
        "conversion loss",
    ]
    if rows:
        total_clicks = sum(row.clicks or 0 for row in rows)
        total_impressions = sum(row.impressions or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros or 0 for row in rows)
        total_conversions = sum(row.conversions or 0 for row in rows)
        total_conversion_value = sum(row.conversion_value or 0 for row in rows)
        return AdsSearchTermsReadContract(
            status="ready",
            title="Google Ads: zapytania użytkowników",
            summary=(
                f"WILQ ma {len(rows)} wierszy zapytań: kliknięcia={total_clicks}, "
                f"wyświetlenia={total_impressions}, koszt_micros={total_cost_micros}, "
                f"konwersje={_format_float(total_conversions)}, "
                f"wartość_konwersji={_format_float(total_conversion_value)}."
            ),
            allowed_metrics=[
                "search_term",
                "campaign",
                "ad_group",
                "status",
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
            ],
            missing_read_contracts=missing_read_contracts,
            operator_review_gates=operator_review_gates,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            search_term_rows=rows,
            next_step=(
                "Użyj wierszy zapytań jako przeglądu danych z reklam. Nie twórz "
                "wykluczeń ani claimów o waste bez kontekstu dopasowania, 90-dniowego "
                "checku i zwalidowanego ActionObject."
            ),
        )

    return AdsSearchTermsReadContract(
        status="blocked",
        title="Google Ads: brak zapytań użytkowników",
        summary="WILQ nie ma jeszcze wymiarowych facts z search_term_view.",
        allowed_metrics=[],
        missing_read_contracts=["search_term_view", *missing_read_contracts],
        blocked_claims=["search terms", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        search_term_rows=[],
        next_step=(
            "Uruchom read-only Google Ads vendor_read po wdrożeniu search_term_view "
            "i zapisz search_term_* metric facts."
        ),
        )


def _search_term_review_summary_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsSearchTermReviewSummaryContract:
    rows = search_terms_read_contract.search_term_rows
    blocked_claims = [
        "search-term waste",
        "negative keyword apply",
        "CPA",
        "ROAS",
    ]
    if not rows:
        return AdsSearchTermReviewSummaryContract(
            status="blocked",
            title="Google Ads: brak kolejki review zapytań",
            summary="WILQ nie ma search-term rows, więc nie może wskazać kolejności review.",
            allowed_metrics=[],
            missing_read_contracts=["search_term_view"],
            operator_review_gates=[],
            blocked_claims=["search terms", *blocked_claims],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            top_cost_search_terms=[],
            campaign_review_rows=[],
            next_step="Uruchom read-only Google Ads vendor_read z search_term_view.",
        )

    total_clicks = sum(row.clicks or 0 for row in rows)
    total_impressions = sum(row.impressions or 0 for row in rows)
    total_cost_micros = sum(row.cost_micros or 0 for row in rows)
    total_conversions = sum(row.conversions or 0 for row in rows)
    zero_conversion_count = sum(1 for row in rows if row.conversions == 0)
    campaign_review_rows = _search_term_campaign_review_rows(rows)
    return AdsSearchTermReviewSummaryContract(
        status="ready",
        title="Google Ads: kolejność review zapytań",
        summary=(
            f"WILQ ma {len(rows)} search-term rows do ręcznego review: "
            f"kliknięcia={total_clicks}, wyświetlenia={total_impressions}, "
            f"koszt_micros={total_cost_micros}, "
            f"konwersje={_format_float(total_conversions)}, "
            f"wiersze_bez_konwersji={zero_conversion_count}."
        ),
        allowed_metrics=search_terms_read_contract.allowed_metrics,
        missing_read_contracts=search_terms_read_contract.missing_read_contracts,
        operator_review_gates=_unique(
            ["human_intent_review", *search_terms_read_contract.operator_review_gates]
        ),
        blocked_claims=blocked_claims,
        source_connectors=search_terms_read_contract.source_connectors,
        evidence_ids=search_terms_read_contract.evidence_ids,
        total_search_term_count=len(rows),
        zero_conversion_search_term_count=zero_conversion_count,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        total_cost_micros=total_cost_micros,
        total_conversions=round(total_conversions, 6),
        top_cost_search_terms=[
            _search_term_review_row(row) for row in rows[:5]
        ],
        campaign_review_rows=campaign_review_rows,
        next_step=(
            "Najpierw przejrzyj kampanie i zapytania z największym kosztem. "
            "Nie nazywaj ich waste i nie twórz wykluczeń bez review intencji, "
            "safety checku, payload preview i walidacji ActionObject."
        ),
    )


def _search_term_review_row(row: AdsSearchTermMetricRow) -> AdsSearchTermReviewRow:
    return AdsSearchTermReviewRow(
        search_term=row.search_term,
        campaign_id=row.campaign_id,
        campaign_name=row.campaign_name,
        ad_group_id=row.ad_group_id,
        ad_group_name=row.ad_group_name,
        search_term_status=row.search_term_status,
        clicks=row.clicks,
        impressions=row.impressions,
        cost_micros=row.cost_micros,
        conversions=row.conversions,
        evidence_ids=row.evidence_ids,
        blocked_claims=[
            "search-term waste",
            "negative keyword apply",
            "CPA",
            "ROAS",
        ],
    )


def _search_term_campaign_review_rows(
    rows: list[AdsSearchTermMetricRow],
) -> list[AdsSearchTermCampaignReviewRow]:
    grouped: dict[tuple[str | None, str | None], list[AdsSearchTermMetricRow]] = {}
    for row in rows:
        grouped.setdefault((row.campaign_id, row.campaign_name), []).append(row)

    review_rows = []
    for (campaign_id, campaign_name), campaign_rows in grouped.items():
        review_rows.append(
            AdsSearchTermCampaignReviewRow(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                search_term_count=len(campaign_rows),
                zero_conversion_search_term_count=sum(
                    1 for row in campaign_rows if row.conversions == 0
                ),
                clicks=sum(row.clicks or 0 for row in campaign_rows),
                impressions=sum(row.impressions or 0 for row in campaign_rows),
                cost_micros=sum(row.cost_micros or 0 for row in campaign_rows),
                conversions=round(
                    sum(row.conversions or 0 for row in campaign_rows),
                    6,
                ),
                evidence_ids=_unique(
                    evidence_id
                    for row in campaign_rows
                    for evidence_id in row.evidence_ids
                ),
                blocked_claims=[
                    "search-term waste",
                    "negative keyword apply",
                    "CPA",
                    "ROAS",
                ],
            )
        )
    return sorted(
        review_rows,
        key=lambda row: (-row.cost_micros, -row.clicks, row.campaign_name or ""),
    )


def _search_term_metric_rows(metric_facts: list[MetricFact]) -> list[AdsSearchTermMetricRow]:
    grouped_facts: dict[tuple[str, str | None, str | None], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str, str | None, str | None, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "search_term_clicks",
            "search_term_impressions",
            "search_term_cost_micros",
            "search_term_conversions",
            "search_term_conversion_value",
        }:
            continue
        search_term = fact.dimensions.get("search_term")
        if not search_term:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        ad_group_id = fact.dimensions.get("ad_group_id")
        row_key = (search_term, campaign_id, ad_group_id)
        metric_key = (*row_key, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _search_term_metric_row(search_term, campaign_id, ad_group_id, facts)
        for (search_term, campaign_id, ad_group_id), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_search_term_row_sort_key)


def _search_term_metric_row(
    search_term: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    facts: list[MetricFact],
) -> AdsSearchTermMetricRow:
    facts_by_name = {fact.name: fact for fact in facts}
    expected_metrics = [
        "search_term_clicks",
        "search_term_impressions",
        "search_term_cost_micros",
        "search_term_conversions",
        "search_term_conversion_value",
    ]
    first_dimensions = facts[0].dimensions if facts else {}
    return AdsSearchTermMetricRow(
        search_term=search_term,
        campaign_id=campaign_id,
        campaign_name=first_dimensions.get("campaign_name"),
        ad_group_id=ad_group_id,
        ad_group_name=first_dimensions.get("ad_group_name"),
        search_term_status=first_dimensions.get("search_term_status"),
        clicks=_int_metric_value(facts_by_name.get("search_term_clicks")),
        impressions=_int_metric_value(facts_by_name.get("search_term_impressions")),
        cost_micros=_int_metric_value(facts_by_name.get("search_term_cost_micros")),
        conversions=_float_metric_value(facts_by_name.get("search_term_conversions")),
        conversion_value=_float_metric_value(
            facts_by_name.get("search_term_conversion_value")
        ),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=["CPA", "ROAS", "negative keyword apply", "wasted budget"],
    )


def _search_term_row_sort_key(row: AdsSearchTermMetricRow) -> tuple[int, int, str]:
    return (-(row.cost_micros or 0), -(row.clicks or 0), row.search_term)


def _search_term_ngram_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsSearchTermNgramReadContract:
    rows = _search_term_ngram_rows(search_terms_read_contract.search_term_rows)
    blocked_claims = [
        "search-term waste",
        "negative keyword candidates",
        "negative keyword apply",
        "CPA",
        "ROAS",
        "conversion loss",
    ]
    if rows:
        total_terms = sum(row.source_search_term_count for row in rows)
        total_clicks = sum(row.clicks or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros or 0 for row in rows)
        return AdsSearchTermNgramReadContract(
            status="ready",
            title="Google Ads: n-gramy zapytań",
            summary=(
                f"WILQ zgrupował {len(rows)} n-gramów z {total_terms} wystąpień "
                f"search terms: kliknięcia={total_clicks}, "
                f"koszt_micros={total_cost_micros}."
            ),
            allowed_metrics=[
                "ngram",
                "ngram_size",
                "source_search_term_count",
                "sample_search_terms",
                "clicks",
                "impressions",
                "cost_micros",
                "conversions",
                "conversion_value",
            ],
            missing_read_contracts=[
                "human_intent_review",
                "ngram_to_negative_keyword_payload_preview",
            ],
            operator_review_gates=[
                "human_intent_review",
                "negative_keyword_action_validation",
            ],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            ngram_rows=rows,
            next_step=(
                "Użyj n-gramów do znalezienia powtarzających się tematów w "
                "zapytaniach. Nie traktuj ich jako gotowej listy wykluczeń bez "
                "review intencji, 90-dniowego safety read i payload preview."
            ),
        )

    return AdsSearchTermNgramReadContract(
        status="blocked",
        title="Google Ads: brak n-gramów zapytań",
        summary="WILQ nie ma search-term rows, więc nie może zbudować n-gramów.",
        allowed_metrics=[],
        missing_read_contracts=["search_term_view"],
        operator_review_gates=[],
        blocked_claims=["search terms", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        ngram_rows=[],
        next_step="Uruchom read-only Google Ads vendor_read z search_term_view.",
    )


def _search_term_ngram_rows(
    rows: list[AdsSearchTermMetricRow],
) -> list[AdsSearchTermNgramRow]:
    grouped_rows: dict[tuple[str, int], list[AdsSearchTermMetricRow]] = {}
    for row in rows:
        tokens = _search_term_tokens(row.search_term)
        for ngram_size in (1, 2, 3):
            if len(tokens) < ngram_size:
                continue
            seen_for_row: set[tuple[str, int]] = set()
            for index in range(0, len(tokens) - ngram_size + 1):
                ngram = " ".join(tokens[index : index + ngram_size])
                key = (ngram, ngram_size)
                if key in seen_for_row:
                    continue
                seen_for_row.add(key)
                grouped_rows.setdefault(key, []).append(row)

    ngram_rows = [
        _search_term_ngram_row(ngram, ngram_size, source_rows)
        for (ngram, ngram_size), source_rows in grouped_rows.items()
    ]
    return sorted(ngram_rows, key=_search_term_ngram_sort_key)[:30]


def _search_term_tokens(search_term: str) -> list[str]:
    tokens = re.findall(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", search_term.lower())
    return [
        token
        for token in tokens
        if len(token) > 1 and token not in ADS_NGRAM_STOPWORDS
    ]


def _search_term_ngram_row(
    ngram: str,
    ngram_size: int,
    rows: list[AdsSearchTermMetricRow],
) -> AdsSearchTermNgramRow:
    metric_facts = _dedupe_metric_facts(fact for row in rows for fact in row.metric_facts)
    missing_metrics = _unique(metric for row in rows for metric in row.missing_metrics)
    sample_search_terms = _unique(row.search_term for row in rows)[:3]
    return AdsSearchTermNgramRow(
        ngram=ngram,
        ngram_size=ngram_size,
        source_search_term_count=len({row.search_term for row in rows}),
        sample_search_terms=sample_search_terms,
        clicks=sum(row.clicks or 0 for row in rows),
        impressions=sum(row.impressions or 0 for row in rows),
        cost_micros=sum(row.cost_micros or 0 for row in rows),
        conversions=round(sum(row.conversions or 0 for row in rows), 6),
        conversion_value=round(sum(row.conversion_value or 0 for row in rows), 6),
        evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
        metric_facts=metric_facts[:12],
        missing_metrics=missing_metrics,
        blocked_claims=["CPA", "ROAS", "negative keyword apply", "search-term waste"],
    )


def _dedupe_metric_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    deduped: list[MetricFact] = []
    seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
    for fact in facts:
        key = (fact.name, fact.evidence_id, tuple(sorted(fact.dimensions.items())))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)
    return sorted(deduped, key=lambda fact: (fact.name, fact.evidence_id))


def _search_term_ngram_sort_key(
    row: AdsSearchTermNgramRow,
) -> tuple[int, int, int, int, str]:
    return (
        -(row.cost_micros or 0),
        -(row.clicks or 0),
        -row.source_search_term_count,
        row.ngram_size,
        row.ngram,
    )


def _search_term_safety_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsSearchTermSafetyReadContract:
    rows = _search_term_safety_rows(metric_facts)
    read_attempted = _latest_refresh_has_summary_metric(
        latest_refresh,
        "search_term_safety_row_count",
    )
    blocked_claims = [
        "negative keyword apply",
        "search-term waste",
        "conversion loss",
        "CPA",
        "ROAS",
    ]
    if rows or read_attempted:
        total_clicks = sum(row.clicks_90d or 0 for row in rows)
        total_impressions = sum(row.impressions_90d or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros_90d or 0 for row in rows)
        total_conversions = sum(row.conversions_90d or 0 for row in rows)
        total_conversion_value = sum(row.conversion_value_90d or 0 for row in rows)
        return AdsSearchTermSafetyReadContract(
            status="ready",
            title="Google Ads: 90-dniowy safety read zapytań",
            summary=(
                f"WILQ ma 90-dniowy read safety dla {len(rows)} zapytań: "
                f"kliknięcia={total_clicks}, wyświetlenia={total_impressions}, "
                f"koszt_micros={total_cost_micros}, "
                f"konwersje={_format_float(total_conversions)}, "
                f"wartość_konwersji={_format_float(total_conversion_value)}."
            ),
            allowed_metrics=[
                "search_term",
                "campaign",
                "ad_group",
                "status",
                "search_term_90d_clicks",
                "search_term_90d_impressions",
                "search_term_90d_cost_micros",
                "search_term_90d_conversions",
                "search_term_90d_conversion_value",
            ],
            missing_read_contracts=[
                "keyword match context",
            ],
            operator_review_gates=["human_intent_review"],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                evidence_id for row in rows for evidence_id in row.evidence_ids
            )
            or _refresh_or_connector_evidence_ids(latest_refresh),
            safety_rows=rows,
            next_step=(
                "Użyj 90-dniowego odczytu jako hamulca bezpieczeństwa. Jeśli termin "
                "ma konwersje w 90 dniach, nie kwalifikuj go do wykluczenia; jeśli "
                "nie ma konwersji, nadal wymagaj review intencji, match context i "
                "review payload preview."
            ),
        )

    return AdsSearchTermSafetyReadContract(
        status="blocked",
        title="Google Ads: brak 90-dniowego safety read",
        summary="WILQ nie ma jeszcze 90-dniowych facts dla search_term_view.",
        allowed_metrics=[],
        missing_read_contracts=[
            "search_term_90d_read",
            "keyword match context",
            "negative_keyword_payload_preview",
        ],
        blocked_claims=["90-day negative keyword safety", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        safety_rows=[],
        next_step=(
            "Uruchom read-only Google Ads vendor_read po wdrożeniu "
            "search_term_90d_* metric facts. Nie twórz wykluczeń bez tego "
            "kontraktu."
        ),
    )


def _search_term_safety_rows(metric_facts: list[MetricFact]) -> list[AdsSearchTermSafetyRow]:
    grouped_facts: dict[tuple[str, str | None, str | None], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str, str | None, str | None, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "search_term_90d_clicks",
            "search_term_90d_impressions",
            "search_term_90d_cost_micros",
            "search_term_90d_conversions",
            "search_term_90d_conversion_value",
        }:
            continue
        search_term = fact.dimensions.get("search_term")
        if not search_term:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        ad_group_id = fact.dimensions.get("ad_group_id")
        row_key = (search_term, campaign_id, ad_group_id)
        metric_key = (*row_key, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _search_term_safety_row(search_term, campaign_id, ad_group_id, facts)
        for (search_term, campaign_id, ad_group_id), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_search_term_safety_row_sort_key)


def _search_term_safety_row(
    search_term: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    facts: list[MetricFact],
) -> AdsSearchTermSafetyRow:
    facts_by_name = {fact.name: fact for fact in facts}
    expected_metrics = [
        "search_term_90d_clicks",
        "search_term_90d_impressions",
        "search_term_90d_cost_micros",
        "search_term_90d_conversions",
        "search_term_90d_conversion_value",
    ]
    first_dimensions = facts[0].dimensions if facts else {}
    return AdsSearchTermSafetyRow(
        search_term=search_term,
        campaign_id=campaign_id,
        campaign_name=first_dimensions.get("campaign_name"),
        ad_group_id=ad_group_id,
        ad_group_name=first_dimensions.get("ad_group_name"),
        search_term_status=first_dimensions.get("search_term_status"),
        clicks_90d=_int_metric_value(facts_by_name.get("search_term_90d_clicks")),
        impressions_90d=_int_metric_value(
            facts_by_name.get("search_term_90d_impressions")
        ),
        cost_micros_90d=_int_metric_value(
            facts_by_name.get("search_term_90d_cost_micros")
        ),
        conversions_90d=_float_metric_value(
            facts_by_name.get("search_term_90d_conversions")
        ),
        conversion_value_90d=_float_metric_value(
            facts_by_name.get("search_term_90d_conversion_value")
        ),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=["CPA", "ROAS", "negative keyword apply", "wasted budget"],
    )


def _search_term_safety_row_sort_key(
    row: AdsSearchTermSafetyRow,
) -> tuple[int, int, str]:
    return (-(row.cost_micros_90d or 0), -(row.clicks_90d or 0), row.search_term)


def _search_term_safety_key(
    row: AdsSearchTermMetricRow | AdsSearchTermSafetyRow,
) -> tuple[str, str | None, str | None]:
    return (row.search_term, row.campaign_id, row.ad_group_id)


def _safety_row_has_conversion_signal(row: AdsSearchTermSafetyRow) -> bool:
    return bool((row.conversions_90d or 0) > 0 or (row.conversion_value_90d or 0) > 0)


def _keyword_match_context_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsKeywordMatchContextReadContract:
    rows = _keyword_match_context_rows(metric_facts)
    read_attempted = _latest_refresh_has_summary_metric(
        latest_refresh,
        "keyword_match_context_row_count",
    )
    blocked_claims = [
        "negative keyword apply",
        "search-term waste",
        "conversion loss",
        "CPA",
        "ROAS",
    ]
    if rows or read_attempted:
        match_types = _unique(row.match_type for row in rows if row.match_type)
        return AdsKeywordMatchContextReadContract(
            status="ready",
            title="Google Ads: kontekst dopasowań keywords",
            summary=(
                f"WILQ ma read-only kontekst {len(rows)} istniejących keywordów "
                f"z match types: {', '.join(match_types) if match_types else 'brak rows'}."
            ),
            allowed_metrics=[
                "keyword_text",
                "keyword_match_type",
                "criterion_status",
                "keyword_negative",
                "campaign",
                "ad_group",
            ],
            missing_read_contracts=[],
            operator_review_gates=["human_intent_review"],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                evidence_id for row in rows for evidence_id in row.evidence_ids
            )
            or _refresh_or_connector_evidence_ids(latest_refresh),
            context_rows=rows,
            next_step=(
                "Użyj tego jako kontekstu review: sprawdź, które istniejące "
                "keywords i match types mogły wywołać search term. Nie traktuj "
                "tego jako zgody na apply negative keywords."
            ),
        )

    return AdsKeywordMatchContextReadContract(
        status="blocked",
        title="Google Ads: brak kontekstu dopasowań keywords",
        summary="WILQ nie ma jeszcze read-only facts z ad_group_criterion keyword.",
        allowed_metrics=[],
        missing_read_contracts=["keyword_match_context_read"],
        blocked_claims=["keyword match context", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        context_rows=[],
        next_step=(
            "Uruchom read-only Google Ads vendor_read po wdrożeniu "
            "ad_group_criterion keyword facts. Nie wdrażaj wykluczeń bez tego "
            "kontekstu."
        ),
    )


def _keyword_match_context_rows(
    metric_facts: list[MetricFact],
) -> list[AdsKeywordMatchContextRow]:
    grouped_facts: dict[
        tuple[str, str | None, str | None, str | None],
        list[MetricFact],
    ] = {}
    seen_metric_keys: set[tuple[str, str | None, str | None, str | None, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "keyword_match_context_available",
            "keyword_match_type",
            "keyword_match_context_negative",
        }:
            continue
        keyword_text = fact.dimensions.get("keyword_text")
        if not keyword_text:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        ad_group_id = fact.dimensions.get("ad_group_id")
        criterion_id = fact.dimensions.get("criterion_id")
        row_key = (keyword_text, campaign_id, ad_group_id, criterion_id)
        metric_key = (*row_key, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _keyword_match_context_row(keyword_text, campaign_id, ad_group_id, facts)
        for (
            keyword_text,
            campaign_id,
            ad_group_id,
            _criterion_id,
        ), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_keyword_match_context_row_sort_key)


def _keyword_match_context_row(
    keyword_text: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    facts: list[MetricFact],
) -> AdsKeywordMatchContextRow:
    facts_by_name = {fact.name: fact for fact in facts}
    first_dimensions = facts[0].dimensions if facts else {}
    negative_value = _int_metric_value(facts_by_name.get("keyword_match_context_negative"))
    match_type_fact = facts_by_name.get("keyword_match_type")
    match_type = match_type_fact.value if match_type_fact is not None else None
    return AdsKeywordMatchContextRow(
        keyword_text=keyword_text,
        match_type=str(match_type or first_dimensions.get("keyword_match_type") or "UNKNOWN"),
        criterion_id=first_dimensions.get("criterion_id"),
        criterion_status=first_dimensions.get("criterion_status"),
        negative=bool(negative_value) if negative_value is not None else None,
        campaign_id=campaign_id,
        campaign_name=first_dimensions.get("campaign_name"),
        ad_group_id=ad_group_id,
        ad_group_name=first_dimensions.get("ad_group_name"),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        blocked_claims=["negative keyword apply", "search-term waste", "wasted budget"],
    )


def _keyword_match_context_row_sort_key(
    row: AdsKeywordMatchContextRow,
) -> tuple[str, str, str]:
    return (
        row.campaign_name or row.campaign_id or "",
        row.ad_group_name or "",
        row.keyword_text,
    )


def _keyword_match_context_key(row: AdsKeywordMatchContextRow) -> tuple[str | None, str | None]:
    return (row.campaign_id, row.ad_group_id)


def _custom_segment_rejection_reason(row: AdsSearchTermMetricRow) -> str | None:
    term = row.search_term.strip()
    normalized = term.lower()
    if len(normalized) < 3:
        return "termin jest zbyt krótki"
    if not any(character.isalpha() for character in normalized):
        return "termin nie ma czytelnego intentu tekstowego"
    if "ekologus" in normalized:
        return "termin wygląda na własny brand albo zapytanie nawigacyjne"
    if not any((row.clicks or 0, row.impressions or 0, row.cost_micros or 0)):
        return "termin nie ma aktywności w dostępnych metrykach"
    return None


def _custom_segment_group_sort_key(rows: list[AdsSearchTermMetricRow]) -> tuple[int, int, str]:
    total_cost = sum(row.cost_micros or 0 for row in rows)
    total_clicks = sum(row.clicks or 0 for row in rows)
    first_campaign = next((row.campaign_name for row in rows if row.campaign_name), "")
    return (-total_cost, -total_clicks, first_campaign)


def _custom_segment_name(campaign_name: str | None, index: int) -> str:
    if campaign_name:
        return f"Search terms: {campaign_name}"
    return f"Search terms: kandydat {index}"


def _custom_segment_confidence(
    rows: list[AdsSearchTermMetricRow],
) -> Literal["low", "medium", "high"]:
    total_clicks = sum(row.clicks or 0 for row in rows)
    source_term_count = len({row.search_term for row in rows})
    if source_term_count >= 8 and total_clicks >= 10:
        return "high"
    if source_term_count >= 3 and total_clicks >= 3:
        return "medium"
    return "low"


def _slug(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in normalized.split("_") if part)[:80] or "unknown"


def _search_terms_section(
    search_terms_read_contract: AdsSearchTermsReadContract,
    action_ids: list[str],
) -> AdsDiagnosticSection:
    if search_terms_read_contract.search_term_rows:
        metric_facts = [
            fact for row in search_terms_read_contract.search_term_rows for fact in row.metric_facts
        ]
        return AdsDiagnosticSection(
            id="ads_search_terms",
            title="Zapytania użytkowników Google Ads",
            status="ready",
            summary=search_terms_read_contract.summary,
            diagnosis=(
                "WILQ ma wiersze zapytań z Google Ads. To jeszcze nie "
                "odblokowuje wykluczeń: brakuje kontekstu dopasowania, 90-dniowego "
                "safety checku i zwalidowanego ActionObject."
            ),
            next_step=search_terms_read_contract.next_step,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=search_terms_read_contract.evidence_ids,
            metric_facts=metric_facts[:12],
            action_ids=_search_term_action_ids(action_ids),
            blocked_claims=search_terms_read_contract.blocked_claims,
            risk=ActionRisk.medium,
        )

    return AdsDiagnosticSection(
        id="ads_search_terms",
        title="Zapytania użytkowników Google Ads",
        status="blocked",
        summary=search_terms_read_contract.summary,
        diagnosis=(
            "BDOS-klasa wymaga search terms, kosztu, konwersji i 90-dniowego checku "
            "ochronnego przed wykluczeniami. WILQ nie może z tego tworzyć negative "
            "keyword candidates bez kompletnego evidence."
        ),
        next_step=search_terms_read_contract.next_step,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=search_terms_read_contract.evidence_ids,
        action_ids=_search_term_action_ids(action_ids),
        blocked_claims=search_terms_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _search_term_ngram_section(
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in search_term_ngram_read_contract.ngram_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_search_term_ngrams",
        title="N-gramy zapytań Google Ads",
        status=search_term_ngram_read_contract.status,
        summary=search_term_ngram_read_contract.summary,
        diagnosis=(
            "N-gramy kondensują powtarzające się tematy w search terms. To pomaga "
            "szybciej znaleźć obszary do ręcznego review, ale nie jest werdyktem "
            "o waste ani gotowym negative keyword payloadem."
        ),
        next_step=search_term_ngram_read_contract.next_step,
        source_connectors=search_term_ngram_read_contract.source_connectors,
        evidence_ids=search_term_ngram_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=search_term_ngram_read_contract.action_ids,
        blocked_claims=search_term_ngram_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _search_term_safety_section(
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in search_term_safety_read_contract.safety_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_search_term_safety",
        title="90-dniowy safety read zapytań",
        status=search_term_safety_read_contract.status,
        summary=search_term_safety_read_contract.summary,
        diagnosis=(
            "Ten kontrakt chroni przed pochopnym wykluczeniem zapytań. "
            "WILQ sprawdza dłuższe okno, ale nadal blokuje apply bez intencji, "
            "kontekstu dopasowania i payload preview."
        ),
        next_step=search_term_safety_read_contract.next_step,
        source_connectors=search_term_safety_read_contract.source_connectors,
        evidence_ids=search_term_safety_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=[],
        blocked_claims=search_term_safety_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _keyword_match_context_section(
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in keyword_match_context_read_contract.context_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_keyword_match_context",
        title="Kontekst dopasowań keywords",
        status=keyword_match_context_read_contract.status,
        summary=keyword_match_context_read_contract.summary,
        diagnosis=(
            "Ten kontrakt pokazuje istniejące keywords i match types w Google Ads. "
            "Pomaga zrozumieć, skąd mógł przyjść search term, ale nie jest zgodą "
            "na dodanie wykluczenia."
        ),
        next_step=keyword_match_context_read_contract.next_step,
        source_connectors=keyword_match_context_read_contract.source_connectors,
        evidence_ids=keyword_match_context_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=[],
        blocked_claims=keyword_match_context_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _keyword_planner_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsKeywordPlannerReadContract:
    rows = _keyword_planner_idea_rows(metric_facts)
    read_attempted = _latest_refresh_has_summary_metric(
        latest_refresh,
        "keyword_planner_idea_count",
    )
    latest_status = (
        str(latest_refresh.metric_summary.get("keyword_planner_status"))
        if latest_refresh is not None
        else ""
    )
    blocked_claims = [
        "audience size",
        "forecast",
        "conversion uplift",
        "ROAS",
        "targeting applied",
        "campaign performance",
    ]
    if rows:
        max_searches = max((row.avg_monthly_searches or 0 for row in rows), default=0)
        return AdsKeywordPlannerReadContract(
            status="ready",
            title="Keyword Planner: enrichment segmentów",
            summary=(
                f"WILQ ma {len(rows)} pomysłów Keyword Planner dla source terms z Ads. "
                f"Najwyższe avg_monthly_searches={max_searches}."
            ),
            allowed_metrics=[
                "keyword_idea_text",
                "keyword_planner_avg_monthly_searches",
                "keyword_planner_competition_index",
                "keyword_planner_low_top_of_page_bid_micros",
                "keyword_planner_high_top_of_page_bid_micros",
            ],
            missing_read_contracts=["forecast_or_audience_size"],
            operator_review_gates=[
                "review_keyword_planner_ideas",
                "reject_off-topic_or_brand_terms",
                "human_confirm_before_apply",
            ],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                evidence_id for row in rows for evidence_id in row.evidence_ids
            ),
            idea_rows=rows,
            next_step=(
                "Użyj enrichmentu jako dodatkowego kontekstu przy custom segments. "
                "Nie traktuj go jako forecastu, audience size ani zgody na apply."
            ),
        )
    if read_attempted or latest_status == "blocked":
        blocker = (
            str(latest_refresh.metric_summary.get("keyword_planner_blocker"))
            if latest_refresh is not None
            else "unknown"
        )
        return AdsKeywordPlannerReadContract(
            status="blocked",
            title="Keyword Planner: enrichment zablokowany",
            summary=f"Keyword Planner read został podjęty, ale nie zwrócił idei ({blocker}).",
            missing_read_contracts=["keyword_planner_enrichment"],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            idea_rows=[],
            next_step=(
                "Zostaw custom segments w trybie source-term review. Nie dopowiadaj "
                "zasięgu ani forecastu bez Keyword Planner facts."
            ),
        )
    return AdsKeywordPlannerReadContract(
        status="blocked",
        title="Keyword Planner: brak enrichmentu",
        summary="WILQ nie ma jeszcze keyword_planner_* metric facts.",
        missing_read_contracts=["keyword_planner_enrichment"],
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        idea_rows=[],
        next_step=(
            "Uruchom read-only Google Ads vendor_read z Keyword Planner albo zostaw "
            "segmenty jako prepare-only source-term review."
        ),
    )


def _keyword_planner_idea_rows(metric_facts: list[MetricFact]) -> list[AdsKeywordPlannerIdeaRow]:
    grouped_facts: dict[str, list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "keyword_planner_idea_available",
            "keyword_planner_avg_monthly_searches",
            "keyword_planner_competition_index",
            "keyword_planner_low_top_of_page_bid_micros",
            "keyword_planner_high_top_of_page_bid_micros",
        }:
            continue
        idea_text = fact.dimensions.get("keyword_idea_text")
        if not idea_text:
            continue
        metric_key = (idea_text, fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(idea_text, []).append(fact)

    rows = [
        _keyword_planner_idea_row(idea_text, facts)
        for idea_text, facts in grouped_facts.items()
    ]
    return sorted(
        rows,
        key=lambda row: (-(row.avg_monthly_searches or 0), row.idea_text),
    )


def _keyword_planner_idea_row(
    idea_text: str,
    facts: list[MetricFact],
) -> AdsKeywordPlannerIdeaRow:
    facts_by_name = {fact.name: fact for fact in facts}
    expected_metrics = [
        "keyword_planner_avg_monthly_searches",
        "keyword_planner_competition_index",
    ]
    first_dimensions = facts[0].dimensions if facts else {}
    source_terms = [
        term.strip()
        for term in (first_dimensions.get("seed_terms") or "").split(",")
        if term.strip()
    ]
    return AdsKeywordPlannerIdeaRow(
        idea_text=idea_text,
        avg_monthly_searches=_int_metric_value(
            facts_by_name.get("keyword_planner_avg_monthly_searches")
        ),
        competition=first_dimensions.get("competition"),
        competition_index=_int_metric_value(
            facts_by_name.get("keyword_planner_competition_index")
        ),
        low_top_of_page_bid_micros=_int_metric_value(
            facts_by_name.get("keyword_planner_low_top_of_page_bid_micros")
        ),
        high_top_of_page_bid_micros=_int_metric_value(
            facts_by_name.get("keyword_planner_high_top_of_page_bid_micros")
        ),
        source_terms=source_terms,
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "audience size",
            "forecast",
            "conversion uplift",
            "ROAS",
            "targeting applied",
        ],
    )


def _keyword_planner_section(
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for row in keyword_planner_read_contract.idea_rows
        for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_keyword_planner",
        title="Keyword Planner enrichment",
        status=keyword_planner_read_contract.status,
        summary=keyword_planner_read_contract.summary,
        diagnosis=(
            "Ten kontrakt wzbogaca source terms o pomysły i historyczne metryki "
            "Keyword Planner. Nie jest forecastem, audience size ani zgodą na "
            "targeting apply."
        ),
        next_step=keyword_planner_read_contract.next_step,
        source_connectors=keyword_planner_read_contract.source_connectors,
        evidence_ids=keyword_planner_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=_keyword_planner_access_action_ids(action_ids),
        blocked_claims=keyword_planner_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _keyword_planner_access_action_ids(action_ids: list[str]) -> list[str]:
    return [
        action_id
        for action_id in action_ids
        if action_id == KEYWORD_PLANNER_ACCESS_ACTION_ID
    ]


def _custom_segments_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
) -> AdsCustomSegmentsReadContract:
    if not search_terms_read_contract.search_term_rows:
        return AdsCustomSegmentsReadContract(
            status="blocked",
            title="Custom segments z search terms",
            summary="Brak search-term rows do zbudowania kandydatów custom segments.",
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=search_terms_read_contract.evidence_ids,
            missing_read_contracts=[
                "search_term_view",
                "keyword_planner_enrichment",
                "custom_segment_payload_preview",
            ],
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Najpierw zbierz Google Ads search_term_view metric facts. Nie wymyślaj "
                "audience terms bez source terms i evidence IDs."
            ),
        )

    candidates = _custom_segment_candidates(
        search_terms_read_contract.search_term_rows,
        keyword_planner_read_contract.idea_rows,
    )
    custom_segment_action_ids = [
        action_id for action_id in action_ids if action_id == CUSTOM_SEGMENT_ACTION_ID
    ]
    if not candidates:
        return AdsCustomSegmentsReadContract(
            status="blocked",
            title="Custom segments z search terms",
            summary=(
                "Search-term rows istnieją, ale wszystkie terminy zostały odrzucone "
                "jako brand, zbyt krótkie albo bez wystarczającego sygnału."
            ),
            source_connectors=search_terms_read_contract.source_connectors,
            evidence_ids=search_terms_read_contract.evidence_ids,
            missing_read_contracts=[
                "eligible_source_terms",
                *(
                    []
                    if keyword_planner_read_contract.status == "ready"
                    else ["keyword_planner_enrichment"]
                ),
                "custom_segment_payload_preview",
            ],
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Zbierz więcej realnych source terms albo użyj Keyword Planner evidence; "
                "nie twórz segmentu z pustych lub brandowych terminów."
            ),
        )

    source_terms_count = sum(len(candidate.source_terms) for candidate in candidates)
    keyword_planner_idea_count = sum(
        len(candidate.keyword_planner_ideas) for candidate in candidates
    )
    payload_preview = [
        candidate.payload_preview
        for candidate in candidates
        if candidate.payload_preview is not None
    ]
    audience_forecast_read_contract = _custom_segment_audience_forecast_read_contract(
        candidates
    )
    missing_read_contracts = ["forecast_or_audience_size"]
    if keyword_planner_read_contract.status != "ready":
        missing_read_contracts.insert(0, "keyword_planner_enrichment")
    return AdsCustomSegmentsReadContract(
        status="ready",
        title="Custom segments z realnych search terms",
        summary=(
            f"WILQ ma {len(candidates)} kandydatów custom segments i "
            f"{source_terms_count} source terms z Google Ads evidence oraz "
            f"{keyword_planner_idea_count} Keyword Planner ideas oraz "
            f"{len(payload_preview)} review-only payload preview."
        ),
        candidates=candidates,
        payload_preview=payload_preview,
        audience_forecast_read_contract=audience_forecast_read_contract,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id
            for candidate in candidates
            for evidence_id in candidate.evidence_ids
        ),
        missing_read_contracts=missing_read_contracts,
        operator_review_gates=CUSTOM_SEGMENT_OPERATOR_REVIEW_GATES,
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        action_ids=custom_segment_action_ids,
        next_step=(
            "Przejrzyj source terms i payload preview, odrzuć nietrafione frazy, "
            "użyj Keyword Planner enrichment, jeśli jest dostępny, i waliduj "
            "ActionObject przed apply."
        ),
    )


def _custom_segment_audience_forecast_read_contract(
    candidates: list[AdsCustomSegmentCandidate],
) -> AdsCustomSegmentAudienceForecastReadContract:
    forecast_rows = [
        AdsCustomSegmentAudienceForecastRow(
            id=f"forecast_{_slug(candidate.id)}",
            candidate_id=candidate.id,
            custom_segment_name=candidate.name,
            status="missing_forecast",
            forecast_available=False,
            audience_size=None,
            source_terms=candidate.source_terms,
            reason=(
                "Brak WILQ evidence dla forecast albo audience size tego custom "
                "segmentu. Kandydat zostaje prepare-only do review."
            ),
            evidence_ids=candidate.evidence_ids,
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        )
        for candidate in candidates
    ]
    return AdsCustomSegmentAudienceForecastReadContract(
        status="blocked",
        title="Forecast i audience size custom segments",
        summary=(
            f"WILQ sprawdził {len(candidates)} kandydatów custom segments, ale "
            "nie ma evidence forecastu ani audience size. Segmenty można tylko "
            "przygotować do review."
        ),
        checked_candidate_count=len(candidates),
        forecast_row_count=len(forecast_rows),
        forecast_rows=forecast_rows,
        missing_read_contracts=["forecast_or_audience_size"],
        operator_review_gates=["forecast_or_audience_size", "human_confirm_before_apply"],
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id
            for candidate in candidates
            for evidence_id in candidate.evidence_ids
        ),
        next_step=(
            "Nie oceniaj zasięgu ani skuteczności segmentu. Najpierw dostarcz "
            "forecast/audience-size evidence i dopiero potem wróć do targetowania."
        ),
    )


def _custom_segment_candidates(
    rows: list[AdsSearchTermMetricRow],
    keyword_planner_ideas: list[AdsKeywordPlannerIdeaRow],
) -> list[AdsCustomSegmentCandidate]:
    grouped: dict[tuple[str | None, str | None], list[AdsSearchTermMetricRow]] = {}
    rejected_by_group: dict[tuple[str | None, str | None], list[tuple[str, str]]] = {}
    for row in rows:
        group_key = (row.campaign_id, row.campaign_name)
        rejection_reason = _custom_segment_rejection_reason(row)
        if rejection_reason is not None:
            rejected_by_group.setdefault(group_key, []).append(
                (row.search_term, rejection_reason)
            )
            continue
        grouped.setdefault(group_key, []).append(row)

    candidates: list[AdsCustomSegmentCandidate] = []
    for index, ((campaign_id, campaign_name), group_rows) in enumerate(
        sorted(grouped.items(), key=lambda item: _custom_segment_group_sort_key(item[1])),
        start=1,
    ):
        sorted_rows = sorted(group_rows, key=_search_term_row_sort_key)[:12]
        source_terms = _unique(row.search_term for row in sorted_rows)[:10]
        if not source_terms:
            continue
        name = _custom_segment_name(campaign_name, index)
        rejected_pairs = rejected_by_group.get((campaign_id, campaign_name), [])
        rejected_terms = _unique(term for term, _reason in rejected_pairs)
        rejection_reasons = _unique(
            f"{term}: {reason}" for term, reason in rejected_pairs
        )
        matched_keyword_planner_ideas = _matching_keyword_planner_ideas(
            source_terms,
            keyword_planner_ideas,
        )
        evidence_ids = _unique(
            [
                *(evidence_id for row in sorted_rows for evidence_id in row.evidence_ids),
                *(
                    evidence_id
                    for idea in matched_keyword_planner_ideas
                    for evidence_id in idea.evidence_ids
                ),
            ]
        )
        metric_facts = [
            *(fact for row in sorted_rows for fact in row.metric_facts),
            *(
                fact
                for idea in matched_keyword_planner_ideas
                for fact in idea.metric_facts
            ),
        ][:28]
        payload_preview = _custom_segment_payload_preview(
            candidate_id=f"ads_custom_segment_{_slug(campaign_id or campaign_name or str(index))}",
            name=name,
            source_terms=source_terms,
            rows=sorted_rows,
            evidence_ids=evidence_ids,
            metric_facts=metric_facts,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            keyword_planner_enriched=bool(matched_keyword_planner_ideas),
        )
        review_score = _custom_segment_review_score(
            source_terms=source_terms,
            rows=sorted_rows,
            payload_preview=payload_preview,
            keyword_planner_ideas=matched_keyword_planner_ideas,
        )
        has_keyword_planner = bool(matched_keyword_planner_ideas)
        candidates.append(
            AdsCustomSegmentCandidate(
                id=payload_preview.id.removeprefix("preview_"),
                name=name,
                intent="search_term_interest",
                review_priority=_custom_segment_review_priority(review_score),
                review_score=review_score,
                review_reason=_custom_segment_review_reason(
                    source_terms=source_terms,
                    rows=sorted_rows,
                    rejected_terms=rejected_terms,
                ),
                human_review_gates=[
                    "sprawdź intencję source terms",
                    "odrzuć brand, konkurencję i low-intent frazy",
                    (
                        "sprawdź Keyword Planner enrichment"
                        if has_keyword_planner
                        else "dodaj Keyword Planner enrichment"
                    ),
                    "sprawdź forecast albo audience size",
                    "zatwierdź segment przed apply",
                ],
                source_terms=source_terms,
                rejected_terms=_unique(rejected_terms)[:12],
                rejection_reasons=_unique(rejection_reasons)[:12],
                source_quality=_custom_segment_source_quality(
                    source_terms=source_terms,
                    rows=sorted_rows,
                    rejected_pairs=rejected_pairs,
                ),
                search_term_rows=sorted_rows,
                keyword_planner_ideas=matched_keyword_planner_ideas,
                source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
                evidence_ids=evidence_ids,
                metric_facts=metric_facts,
                confidence=_custom_segment_confidence(sorted_rows),
                validation_status="pending_validation",
                payload_preview=payload_preview,
                blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
                next_step=(
                    "Użyj tych terminów jako prepare-only candidate. Payload preview "
                    "jest tylko do review; przed apply wymagaj forecastu, audience "
                    "size i walidacji ActionObject."
                ),
            )
        )
    return candidates[:4]


def _matching_keyword_planner_ideas(
    source_terms: list[str],
    ideas: list[AdsKeywordPlannerIdeaRow],
) -> list[AdsKeywordPlannerIdeaRow]:
    source_terms_lower = {term.lower() for term in source_terms}
    matched = [
        idea
        for idea in ideas
        if not idea.source_terms
        or any(term.lower() in source_terms_lower for term in idea.source_terms)
    ]
    return matched[:8]


def _custom_segment_review_score(
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    payload_preview: AdsCustomSegmentPayloadPreview | None,
    keyword_planner_ideas: list[AdsKeywordPlannerIdeaRow],
) -> int:
    total_clicks = sum(row.clicks or 0 for row in rows)
    total_impressions = sum(row.impressions or 0 for row in rows)
    total_cost = sum(row.cost_micros or 0 for row in rows) / 1_000_000
    total_conversions = sum(row.conversions or 0 for row in rows)
    score = float(min(len(source_terms) * 8, 25))
    score += min(total_clicks * 4, 25)
    score += min(total_impressions / 50, 15)
    score += min(total_cost, 15)
    if total_conversions > 0:
        score += 10
    if payload_preview is not None:
        score += 10
    if keyword_planner_ideas:
        score += 10
    return min(100, int(round(score)))


def _custom_segment_review_priority(
    review_score: int,
) -> Literal["pilne", "wysokie", "normalne", "niski sygnał"]:
    if review_score >= 70:
        return "pilne"
    if review_score >= 45:
        return "wysokie"
    if review_score >= 15:
        return "normalne"
    return "niski sygnał"


def _custom_segment_review_reason(
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    rejected_terms: list[str],
) -> str:
    total_clicks = sum(row.clicks or 0 for row in rows)
    total_conversions = sum(row.conversions or 0 for row in rows)
    return (
        f"Source terms={len(source_terms)}, kliknięcia={total_clicks}, "
        f"wyświetlenia={_search_term_impressions_review_value(rows)}, "
        f"koszt={_search_term_cost_review_value(rows)}, "
        f"konwersje={_format_float(float(total_conversions))}, "
        f"odrzucone terminy={len(_unique(rejected_terms))}. "
        "To jest kolejność review segmentu, nie dowód audience size, targetowania "
        "ani wpływu na kampanię."
    )


def _custom_segment_source_quality(
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    rejected_pairs: list[tuple[str, str]],
) -> AdsCustomSegmentSourceQuality:
    accepted_terms = len(_unique(source_terms))
    rejected_terms = len(_unique(term for term, _reason in rejected_pairs))
    reason_counts: dict[str, int] = {}
    for _term, reason in rejected_pairs:
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    missing_metric_terms = sum(1 for row in rows if row.missing_metrics)
    return AdsCustomSegmentSourceQuality(
        total_terms=accepted_terms + rejected_terms,
        accepted_terms=accepted_terms,
        rejected_terms=rejected_terms,
        missing_metric_terms=missing_metric_terms,
        rejection_reasons=dict(
            sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
    )


def _search_term_impressions_review_value(rows: list[AdsSearchTermMetricRow]) -> str:
    if not any(row.impressions is not None for row in rows):
        return "brak danych"
    return str(sum(row.impressions or 0 for row in rows))


def _search_term_cost_review_value(rows: list[AdsSearchTermMetricRow]) -> str:
    if not any(row.cost_micros is not None for row in rows):
        return "brak danych"
    return _format_micros(sum(row.cost_micros or 0 for row in rows)) or "0"


def _custom_segment_payload_preview(
    candidate_id: str,
    name: str,
    source_terms: list[str],
    rows: list[AdsSearchTermMetricRow],
    evidence_ids: list[str],
    metric_facts: list[MetricFact],
    campaign_id: str | None,
    campaign_name: str | None,
    keyword_planner_enriched: bool,
) -> AdsCustomSegmentPayloadPreview:
    source_metric_names = _unique(
        fact.name for fact in metric_facts if fact.name.startswith("search_term_")
    )
    row_terms = _unique(row.search_term for row in rows)
    preview_id = f"preview_{candidate_id}"
    return AdsCustomSegmentPayloadPreview(
        id=preview_id,
        custom_segment_name=name,
        member_type="KEYWORD",
        source_terms=[term for term in source_terms if term in row_terms],
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        reason=(
            "Podgląd review-only dla Google Ads custom audience keyword members "
            "z realnych search terms. To nie jest gotowa mutacja ani targetowanie."
        ),
        evidence_ids=evidence_ids,
        source_metric_names=source_metric_names,
        required_validation=[
            "review_source_terms",
            "reject_brand_or_low_intent_terms",
            "keyword_planner_enrichment",
            "forecast_or_audience_size",
            "human_confirm_before_apply",
        ],
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        targeting_preview=[
            AdsCustomSegmentTargetingPreview(
                id=f"targeting_{preview_id}",
                custom_segment_preview_id=preview_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                reason=(
                    "Review-only podgląd kampanii, do której można wrócić po "
                    "walidacji segmentu. To nie jest targetowanie ani mutacja Ads."
                ),
                required_validation=[
                    "keyword_planner_enrichment",
                    "forecast_or_audience_size",
                    "human_confirm_before_apply",
                    "mutation_audit_required",
                ],
                blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
                api_mutation_ready=False,
                apply_allowed=False,
                destructive=False,
            )
        ],
        safety_review=AdsCustomSegmentApplySafetyReview.model_validate(
            custom_segment_apply_safety_review(
                preview_id=preview_id,
                evidence_ids=evidence_ids,
                keyword_planner_enriched=keyword_planner_enriched,
                forecast_available=False,
            )
        ),
        api_mutation_ready=False,
        apply_allowed=False,
        destructive=False,
    )


def _custom_segments_section(
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for candidate in custom_segments_read_contract.candidates
        for fact in candidate.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_custom_segments",
        title="Custom segments z search terms",
        status=custom_segments_read_contract.status,
        summary=custom_segments_read_contract.summary,
        diagnosis=(
            "WILQ może przygotować kandydatów custom segments tylko z realnych "
            "source terms. Keyword Planner enrichment jest dodatkowym kontekstem, "
            "ale audience size i performance pozostają zablokowane bez osobnych "
            "kontraktów."
        ),
        next_step=custom_segments_read_contract.next_step,
        source_connectors=custom_segments_read_contract.source_connectors,
        evidence_ids=custom_segments_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=custom_segments_read_contract.action_ids,
        blocked_claims=custom_segments_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _negative_keywords_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
    action_ids: list[str],
) -> AdsNegativeKeywordsReadContract:
    if not search_terms_read_contract.search_term_rows:
        return AdsNegativeKeywordsReadContract(
            status="blocked",
            title="Review wykluczeń z search terms",
            summary="Brak search-term rows do kolejki review wykluczeń.",
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=search_terms_read_contract.evidence_ids,
            missing_read_contracts=[
                "search_term_view",
                *(
                    []
                    if keyword_match_context_read_contract.status == "ready"
                    else ["keyword match context"]
                ),
                "90_day_safety_check",
            ],
            blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Najpierw zbierz Google Ads search_term_view metric facts. Nie twórz "
                "wykluczeń bez search terms, kontekstu dopasowania i safety checku."
            ),
        )

    candidates = _negative_keyword_candidates(
        search_terms_read_contract.search_term_rows,
        search_term_safety_read_contract.safety_rows,
        keyword_match_context_read_contract.context_rows,
    )
    negative_keyword_action_ids = [
        action_id for action_id in action_ids if action_id == NEGATIVE_KEYWORD_ACTION_ID
    ]
    if not candidates:
        return AdsNegativeKeywordsReadContract(
            status="blocked",
            title="Review wykluczeń z search terms",
            summary=(
                "Search-term rows istnieją, ale WILQ nie znalazł terminów z kosztem lub "
                "kliknięciami i zerową konwersją w bieżącym evidence."
            ),
            source_connectors=search_terms_read_contract.source_connectors,
            evidence_ids=search_terms_read_contract.evidence_ids,
            missing_read_contracts=[
                "zero_conversion_search_terms",
                *(
                    []
                    if keyword_match_context_read_contract.status == "ready"
                    else ["keyword match context"]
                ),
                *(
                    []
                    if search_term_safety_read_contract.status == "ready"
                    else ["90_day_safety_check"]
                ),
            ],
            blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Kontynuuj read-only review search terms. Nie twórz negative keyword "
                "candidates, jeśli bieżące evidence nie pokazuje zerowej konwersji."
            ),
        )

    missing_read_contracts = (
        []
        if keyword_match_context_read_contract.status == "ready"
        else ["keyword match context"]
    )
    if any(
        candidate.safety_status != "read_ready_needs_human_review"
        for candidate in candidates
    ):
        missing_read_contracts.insert(1, "90_day_safety_check")

    return AdsNegativeKeywordsReadContract(
        status="ready",
        title="Review wykluczeń z search terms",
        summary=(
            f"WILQ ma {len(candidates)} terminów do review: mają koszt lub kliknięcia, "
            "zero konwersji w bieżącym evidence i są sprawdzone przez dostępny "
            "90-dniowy read, jeśli WILQ ma matching row."
        ),
        candidates=candidates,
        payload_preview=[
            candidate.payload_preview
            for candidate in candidates
            if candidate.payload_preview is not None
        ],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id
            for candidate in candidates
            for evidence_id in [
                *candidate.evidence_ids,
                *candidate.safety_evidence_ids,
                *candidate.keyword_context_evidence_ids,
            ]
        ),
        missing_read_contracts=missing_read_contracts,
        blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
        action_ids=negative_keyword_action_ids,
        next_step=(
            "Przejrzyj kandydatów jako review-only. Przed jakimkolwiek apply wymagaj "
            "kontekstu dopasowania, sprawdzenia payload preview i walidacji "
            "ActionObject."
        ),
    )


def _negative_keyword_candidates(
    rows: list[AdsSearchTermMetricRow],
    safety_rows: list[AdsSearchTermSafetyRow],
    keyword_context_rows: list[AdsKeywordMatchContextRow],
) -> list[AdsNegativeKeywordCandidate]:
    candidates: list[AdsNegativeKeywordCandidate] = []
    safety_by_key = {_search_term_safety_key(row): row for row in safety_rows}
    keyword_context_by_key: dict[
        tuple[str | None, str | None],
        list[AdsKeywordMatchContextRow],
    ] = {}
    for context_row in keyword_context_rows:
        keyword_context_by_key.setdefault(
            _keyword_match_context_key(context_row),
            [],
        ).append(context_row)
    for row in sorted(rows, key=_search_term_row_sort_key):
        if not _is_negative_keyword_review_candidate(row):
            continue
        safety_row = safety_by_key.get(_search_term_safety_key(row))
        if safety_row is not None and _safety_row_has_conversion_signal(safety_row):
            continue
        metric_facts = row.metric_facts[:12]
        safety_metric_facts = safety_row.metric_facts[:12] if safety_row else []
        safety_status: Literal["needs_90_day_review", "read_ready_needs_human_review"]
        if safety_row is None:
            safety_status = "needs_90_day_review"
        else:
            safety_status = "read_ready_needs_human_review"
        row_keyword_context = keyword_context_by_key.get(
            (row.campaign_id, row.ad_group_id),
            [],
        )[:8]
        payload_preview = _negative_keyword_payload_preview(row, safety_row)
        review_score = _negative_keyword_review_score(
            row,
            safety_row,
            row_keyword_context,
        )
        candidates.append(
            AdsNegativeKeywordCandidate(
                id=(
                    "ads_negative_keyword_review_"
                    f"{_slug(row.campaign_id or row.campaign_name or 'campaign')}_"
                    f"{_slug(row.ad_group_id or row.ad_group_name or 'ad_group')}_"
                    f"{_slug(row.search_term)}"
                ),
                search_term=row.search_term,
                review_priority=_negative_keyword_review_priority(review_score),
                review_score=review_score,
                review_reason=_negative_keyword_review_reason(
                    row,
                    safety_row,
                    row_keyword_context,
                ),
                human_review_gates=[
                    "sprawdź intencję zapytania",
                    "porównaj z istniejącymi keywords i match types",
                    "sprawdź 90-dniowy safety read",
                    "zatwierdź poziom wykluczenia przed apply",
                ],
                campaign_id=row.campaign_id,
                campaign_name=row.campaign_name,
                ad_group_id=row.ad_group_id,
                ad_group_name=row.ad_group_name,
                clicks=row.clicks,
                impressions=row.impressions,
                cost_micros=row.cost_micros,
                conversions=row.conversions,
                conversion_value=row.conversion_value,
                clicks_90d=safety_row.clicks_90d if safety_row else None,
                impressions_90d=safety_row.impressions_90d if safety_row else None,
                cost_micros_90d=safety_row.cost_micros_90d if safety_row else None,
                conversions_90d=safety_row.conversions_90d if safety_row else None,
                conversion_value_90d=(
                    safety_row.conversion_value_90d if safety_row else None
                ),
                evidence_ids=row.evidence_ids,
                safety_evidence_ids=safety_row.evidence_ids if safety_row else [],
                keyword_context_evidence_ids=_unique(
                    evidence_id
                    for context_row in row_keyword_context
                    for evidence_id in context_row.evidence_ids
                ),
                metric_facts=metric_facts,
                safety_metric_facts=safety_metric_facts,
                keyword_context_rows=row_keyword_context,
                payload_preview=payload_preview,
                required_checks=[
                    "review_search_term_context",
                    "check_existing_keywords_and_match_types",
                    "90_day_safety_check",
                    "negative_keyword_payload_preview",
                    "human_confirm_before_apply",
                ],
                safety_status=safety_status,
                validation_status="pending_validation",
                blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
                next_step=(
                    "Sprawdź intencję terminu, istniejące keywords/match types i "
                    "90-dniową historię przed jakimkolwiek wykluczeniem."
                ),
            )
        )
    return candidates[:12]


def _negative_keyword_review_score(
    row: AdsSearchTermMetricRow,
    safety_row: AdsSearchTermSafetyRow | None,
    keyword_context_rows: list[AdsKeywordMatchContextRow],
) -> int:
    current_cost = (row.cost_micros or 0) / 1_000_000
    safety_cost = ((safety_row.cost_micros_90d if safety_row else 0) or 0) / 1_000_000
    current_clicks = row.clicks or 0
    safety_clicks = (safety_row.clicks_90d if safety_row else 0) or 0
    score = min(current_cost * 2, 40)
    score += min(safety_cost, 25)
    score += min(max(current_clicks, safety_clicks) * 5, 20)
    if safety_row is not None:
        score += 10
    if keyword_context_rows:
        score += 5
    return min(100, int(round(score)))


def _negative_keyword_review_priority(
    review_score: int,
) -> Literal["pilne", "wysokie", "normalne", "niski sygnał"]:
    if review_score >= 70:
        return "pilne"
    if review_score >= 45:
        return "wysokie"
    if review_score >= 15:
        return "normalne"
    return "niski sygnał"


def _negative_keyword_review_reason(
    row: AdsSearchTermMetricRow,
    safety_row: AdsSearchTermSafetyRow | None,
    keyword_context_rows: list[AdsKeywordMatchContextRow],
) -> str:
    current_cost = _format_micros(row.cost_micros)
    safety_cost = _format_micros(safety_row.cost_micros_90d if safety_row else None)
    current_conversions = _format_float(float(row.conversions or 0))
    safety_conversions_value = (
        safety_row.conversions_90d if safety_row is not None else 0
    )
    safety_conversions = _format_float(float(safety_conversions_value or 0))
    safety_part = (
        f"90 dni: kliknięcia={safety_row.clicks_90d or 0}, koszt={safety_cost or '0'}, "
        f"konwersje={safety_conversions}"
        if safety_row is not None
        else "brak dopasowanego 90-dniowego safety row"
    )
    context_part = (
        f"kontekst keywords={len(keyword_context_rows)} rows"
        if keyword_context_rows
        else "brak keyword match context dla tej grupy"
    )
    return (
        f"Bieżący read: kliknięcia={row.clicks or 0}, koszt={current_cost or '0'}, "
        f"konwersje={current_conversions}; {safety_part}; {context_part}. "
        "To jest kolejność review, nie werdykt zmarnowanego budżetu."
    )


def _negative_keyword_payload_preview(
    row: AdsSearchTermMetricRow,
    safety_row: AdsSearchTermSafetyRow | None,
) -> AdsNegativeKeywordPayloadPreview:
    safety_evidence_ids = safety_row.evidence_ids if safety_row else []
    evidence_ids = _unique([*row.evidence_ids, *safety_evidence_ids])
    safety_metric_names = (
        [fact.name for fact in safety_row.metric_facts] if safety_row else []
    )
    source_metric_names = _unique(
        [*(fact.name for fact in row.metric_facts), *safety_metric_names]
    )
    level: Literal["ad_group", "campaign_review_required"] = (
        "ad_group" if row.ad_group_id else "campaign_review_required"
    )
    reason = (
        "Exact negative keyword review preview zbudowany z 30-dniowych search terms "
        "i 90-dniowego safety read. To nie jest gotowa mutacja API."
    )
    if level == "campaign_review_required":
        reason = (
            "Brak ad_group_id w evidence, więc WILQ pokazuje tylko review preview "
            "i wymaga decyzji człowieka o poziomie kampanii lub grupy reklam."
        )
    return AdsNegativeKeywordPayloadPreview(
        id=(
            "negative_keyword_preview_"
            f"{_slug(row.campaign_id or row.campaign_name or 'campaign')}_"
            f"{_slug(row.ad_group_id or row.ad_group_name or 'ad_group')}_"
            f"{_slug(row.search_term)}"
        ),
        search_term=row.search_term,
        negative_keyword_text=row.search_term,
        match_type="EXACT",
        level=level,
        campaign_id=row.campaign_id,
        campaign_name=row.campaign_name,
        ad_group_id=row.ad_group_id,
        ad_group_name=row.ad_group_name,
        reason=reason,
        evidence_ids=evidence_ids,
        source_metric_names=source_metric_names,
        required_validation=[
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "human_confirm_before_apply",
        ],
        blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
    )


def _is_negative_keyword_review_candidate(row: AdsSearchTermMetricRow) -> bool:
    if not _eligible_negative_keyword_term(row.search_term):
        return False
    has_activity = bool((row.clicks or 0) > 0 or (row.cost_micros or 0) > 0)
    has_conversions = bool((row.conversions or 0) > 0 or (row.conversion_value or 0) > 0)
    return has_activity and not has_conversions


def _eligible_negative_keyword_term(term: str) -> bool:
    normalized = term.strip().lower()
    if len(normalized) < 3:
        return False
    if "ekologus" in normalized:
        return False
    return any(character.isalpha() for character in normalized)


def _negative_keywords_section(
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
) -> AdsDiagnosticSection:
    metric_facts = [
        fact
        for candidate in negative_keywords_read_contract.candidates
        for fact in candidate.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_negative_keyword_safety",
        title="Review wykluczeń z search terms",
        status=negative_keywords_read_contract.status,
        summary=negative_keywords_read_contract.summary,
        diagnosis=(
            "WILQ może przygotować tylko kolejkę review. Zero konwersji w bieżącym "
            "evidence nie jest jeszcze dowodem waste ani zgodą na wykluczenie."
        ),
        next_step=negative_keywords_read_contract.next_step,
        source_connectors=negative_keywords_read_contract.source_connectors,
        evidence_ids=negative_keywords_read_contract.evidence_ids,
        metric_facts=metric_facts[:12],
        action_ids=negative_keywords_read_contract.action_ids,
        blocked_claims=negative_keywords_read_contract.blocked_claims,
        risk=ActionRisk.medium,
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
            "WILQ ma dowody z odczytu Google Ads; ścieżka apply nadal wymaga "
            "osobnej walidacji, preview, potwierdzenia i audytu."
        )
        diagnosis = (
            "Odczyt kampanii i zapytań może wspierać analizę, ale zmiany budżetów, "
            "kampanii, wykluczeń i segmentów wymagają osobnych podglądów akcji, "
            "walidacji, jawnego potwierdzenia i audytu."
        )
        next_step = (
            "Rozszerz Ads workflow o prepare-only ActionObject dopiero po osobnym evidence "
            "dla konkretnej zmiany."
        )
    else:
        summary = "WILQ ma tylko prepare-only repair action dla Google Ads access."
        diagnosis = (
            "Żadna zmiana Google Ads nie może przejść do wdrożenia bez podglądu akcji, "
            "walidacji, jawnego potwierdzenia i audytu. Obecnie jedyny sensowny "
            "ActionObject to naprawa dostępu."
        )
        next_step = (
            "Zweryfikuj `act_configure_google_ads_env`; apply pozostaje zablokowany "
            "bez explicit support."
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
        blocked_claims=["budget apply", "campaign creation", "negative keyword apply"],
        risk=ActionRisk.medium,
    )


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
) -> list[AdsDecisionItem]:
    if blocked_handoff is not None:
        return [
            _with_ads_decision_lineage(AdsDecisionItem(
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
            ))
        ]

    decisions: list[AdsDecisionItem] = []
    if campaign_read_contract.campaign_rows:
        campaign_review_action_ids = _campaign_review_action_ids(action_ids)
        metric_facts = [
            fact for row in campaign_read_contract.campaign_rows for fact in row.metric_facts
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_campaign_activity",
                decision_type="review_campaign_activity",
                status="ready",
                title="Przejrzyj aktywność kampanii Google Ads",
                summary=campaign_read_contract.summary,
                rationale=(
                    "To jest uczciwy pierwszy przegląd kampanii: WILQ widzi kliknięcia, "
                    "wyświetlenia, koszt, konwersje i wartość konwersji po kampaniach. "
                    "Nie ma jeszcze pełnego kontraktu rekomendacji, impression share "
                    "ani historii zmian."
                ),
                next_step=(
                    "Sprawdź kampanie z największym kosztem i ruchem w tabeli dowodów. "
                    "Nie podejmuj decyzji budżetowych bez brakujących kontraktów odczytu."
                ),
                allowed_metrics=campaign_read_contract.allowed_metrics,
                missing_read_contracts=_remove_available_contracts(
                    campaign_read_contract.missing_read_contracts,
                    budget_pacing_read_contract,
                    recommendations_read_contract,
                    impression_share_read_contract,
                    change_history_read_contract,
                ),
                source_connectors=campaign_read_contract.source_connectors,
                evidence_ids=campaign_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                campaign_rows=campaign_read_contract.campaign_rows,
                operator_review_gates=_unique(
                    gate
                    for row in campaign_read_contract.campaign_rows
                    for gate in row.human_review_gates
                ),
                action_ids=campaign_review_action_ids,
                blocked_claims=campaign_read_contract.blocked_claims,
                risk=ActionRisk.low,
            )
        )

    if campaign_triage_read_contract.triage_rows:
        decisions.append(
            AdsDecisionItem(
                id="ads_review_campaign_triage",
                decision_type="review_campaign_triage",
                status="ready",
                title="Ustal kolejność review kampanii Ads",
                summary=campaign_triage_read_contract.summary,
                rationale=(
                    "Ta kolejka łączy kampanie, KPI, pacing budżetu, rekomendacje "
                    "i impression share w jeden widok decyzyjny. WILQ pokazuje, "
                    "co sprawdzić najpierw, ale nadal blokuje waste/profitability/"
                    "budget apply/recommendation apply."
                ),
                next_step=campaign_triage_read_contract.next_step,
                allowed_metrics=campaign_triage_read_contract.allowed_metrics,
                missing_read_contracts=campaign_triage_read_contract.missing_read_contracts,
                source_connectors=campaign_triage_read_contract.source_connectors,
                evidence_ids=campaign_triage_read_contract.evidence_ids,
                campaign_triage_rows=campaign_triage_read_contract.triage_rows,
                operator_review_gates=_unique(
                    gate
                    for row in campaign_triage_read_contract.triage_rows
                    for gate in row.human_review_gates
                ),
                action_ids=campaign_triage_read_contract.action_ids,
                blocked_claims=campaign_triage_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    decisions.append(
        AdsDecisionItem(
            id="ads_review_business_context",
            decision_type="review_business_context",
            status=business_context_read_contract.status,
            title=(
                "Użyj kontekstu biznesowego w review Ads"
                if business_context_read_contract.status == "ready"
                else "Uzupełnij kontekst biznesowy przed decyzjami Ads"
            ),
            summary=business_context_read_contract.summary,
            rationale=(
                "Google Ads pokazuje koszt, kliknięcia, konwersje i część KPI. "
                "WILQ używa lokalnego typed contractu z marżą, celem biznesowym, "
                "celem budżetu oraz targetem ROAS/CPA jako kontekstu review, ale "
                "nadal blokuje apply i twarde werdykty bez pełnych kontraktów "
                "pacingu, historii zmian, rekomendacji i audytu."
                if business_context_read_contract.status == "ready"
                else (
                    "Google Ads pokazuje koszt, kliknięcia, konwersje i część KPI, ale "
                    "nie zna marży, celu sprzedażowego ani intencji budżetu Ekologus. "
                    "WILQ musi mieć ten kontekst jako typed contract, zanim nazwie coś "
                    "rentowne, nierentowne albo gotowe do skalowania."
                )
            ),
            next_step=business_context_read_contract.next_step,
            metric_tiles={"polityki": len(business_context_read_contract.business_policy_ids)},
            allowed_metrics=business_context_read_contract.allowed_metrics,
            missing_read_contracts=business_context_read_contract.missing_read_contracts,
            operator_review_gates=business_context_read_contract.operator_review_gates,
            source_connectors=business_context_read_contract.source_connectors,
            evidence_ids=business_context_read_contract.evidence_ids,
            action_ids=business_context_read_contract.target_interpretation.action_ids,
            blocked_claims=business_context_read_contract.blocked_claims,
            risk=ActionRisk.medium,
        )
    )

    if derived_kpi_read_contract.kpi_rows:
        campaign_review_action_ids = _campaign_review_action_ids(action_ids)
        decisions.append(
            AdsDecisionItem(
                id="ads_review_derived_kpis",
                decision_type="review_derived_kpi",
                status="ready",
                title="Sprawdź wyliczone KPI kampanii bez decyzji budżetowych",
                summary=derived_kpi_read_contract.summary,
                rationale=(
                    "CPA i ROAS są tu wartościami obliczonymi z kosztu, konwersji "
                    "i wartości konwersji w bieżącym Google Ads evidence. WILQ nadal "
                    "blokuje wniosek o rentowności, waste, skalowaniu budżetu i apply."
                ),
                next_step=derived_kpi_read_contract.next_step,
                allowed_metrics=derived_kpi_read_contract.allowed_metrics,
                missing_read_contracts=_remove_available_contracts(
                    derived_kpi_read_contract.missing_read_contracts,
                    budget_pacing_read_contract,
                    recommendations_read_contract,
                    impression_share_read_contract,
                    change_history_read_contract,
                ),
                source_connectors=derived_kpi_read_contract.source_connectors,
                evidence_ids=derived_kpi_read_contract.evidence_ids,
                derived_kpi_rows=derived_kpi_read_contract.kpi_rows,
                action_ids=campaign_review_action_ids,
                blocked_claims=derived_kpi_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if budget_pacing_read_contract.budget_rows:
        campaign_review_action_ids = _campaign_review_action_ids(action_ids)
        metric_facts = [
            fact for row in budget_pacing_read_contract.budget_rows for fact in row.metric_facts
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_budget_context",
                decision_type="review_budget_context",
                status="ready",
                title="Sprawdź koszt kampanii względem budżetu dziennego",
                summary=budget_pacing_read_contract.summary,
                rationale=(
                    "WILQ widzi campaign_budget amount i koszt z ostatnich 7 dni, więc "
                    "może pokazać kontekst tempa wydawania. To nadal nie jest decyzja "
                    "o skalowaniu: brakuje historii zmian, impression share, celu "
                    "budżetowego i walidowanego preview apply."
                ),
                next_step=budget_pacing_read_contract.next_step,
                allowed_metrics=budget_pacing_read_contract.allowed_metrics,
                missing_read_contracts=budget_pacing_read_contract.missing_read_contracts,
                source_connectors=budget_pacing_read_contract.source_connectors,
                evidence_ids=budget_pacing_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                budget_rows=budget_pacing_read_contract.budget_rows,
                shared_budget_distribution_rows=(
                    budget_pacing_read_contract.shared_budget_distribution_rows
                ),
                budget_apply_preview=budget_pacing_read_contract.payload_preview,
                action_ids=campaign_review_action_ids,
                blocked_claims=budget_pacing_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if recommendations_read_contract.status == "ready":
        recommendation_action_ids = _recommendation_action_ids(action_ids)
        metric_facts = [
            fact
            for row in recommendations_read_contract.recommendation_rows
            for fact in row.metric_facts
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_recommendations",
                decision_type="review_recommendations",
                status="ready",
                title="Przejrzyj rekomendacje Google Ads bez apply",
                summary=recommendations_read_contract.summary,
                rationale=(
                    "Google Ads recommendations są sygnałem do kontroli, nie "
                    "automatyczną strategią. WILQ pokazuje typ rekomendacji i "
                    "powiązanie z kampanią/budżetem, ale blokuje accept/apply bez "
                    "strategii, RMF/compliance review, potwierdzenia i audytu."
                ),
                next_step=recommendations_read_contract.next_step,
                allowed_metrics=recommendations_read_contract.allowed_metrics,
                missing_read_contracts=recommendations_read_contract.missing_read_contracts,
                operator_review_gates=recommendations_read_contract.operator_review_gates,
                source_connectors=recommendations_read_contract.source_connectors,
                evidence_ids=recommendations_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                recommendation_rows=recommendations_read_contract.recommendation_rows,
                recommendation_apply_preview=recommendations_read_contract.payload_preview,
                action_ids=recommendation_action_ids,
                blocked_claims=recommendations_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if impression_share_read_contract.status == "ready":
        metric_facts = [
            fact
            for row in impression_share_read_contract.impression_share_rows
            for fact in row.metric_facts
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_impression_share",
                decision_type="review_impression_share",
                status="ready",
                title="Sprawdź utracony udział w wyświetleniach",
                summary=impression_share_read_contract.summary,
                rationale=(
                    "Impression share pokazuje, czy kampania traci ekspozycję przez "
                    "budżet albo ranking. WILQ może to pokazać jako kontekst review, "
                    "ale blokuje skalowanie budżetu i claimy o wasted budget bez "
                    "historii zmian, celu biznesowego i preview apply."
                ),
                next_step=impression_share_read_contract.next_step,
                allowed_metrics=impression_share_read_contract.allowed_metrics,
                missing_read_contracts=impression_share_read_contract.missing_read_contracts,
                source_connectors=impression_share_read_contract.source_connectors,
                evidence_ids=impression_share_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                impression_share_rows=impression_share_read_contract.impression_share_rows,
                action_ids=[],
                blocked_claims=impression_share_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if (
        change_history_read_contract.status == "ready"
        or change_history_read_contract.evidence_ids
    ):
        metric_facts = [
            fact
            for row in change_history_read_contract.change_history_rows
            for fact in row.metric_facts
        ]
        has_change_rows = bool(change_history_read_contract.change_history_rows)
        decisions.append(
            AdsDecisionItem(
                id="ads_review_change_history",
                decision_type="review_change_history",
                status="ready" if has_change_rows else "blocked",
                title=(
                    "Sprawdź historię zmian Google Ads"
                    if has_change_rows
                    else "Historia zmian: brak zdarzeń do impact review"
                ),
                summary=change_history_read_contract.summary,
                rationale=(
                    "Historia zmian mówi, co ostatnio zmieniano w koncie. Jeśli "
                    "Google Ads nie zwrócił żadnych zdarzeń, WILQ blokuje impact "
                    "review zamiast pokazywać pusty task. Jeśli zdarzenia istnieją, "
                    "WILQ nadal blokuje claimy o wpływie zmian na wynik bez "
                    "porównania przed/po i ręcznego review."
                ),
                next_step=change_history_read_contract.next_step,
                allowed_metrics=change_history_read_contract.allowed_metrics,
                missing_read_contracts=change_history_read_contract.missing_read_contracts,
                source_connectors=change_history_read_contract.source_connectors,
                evidence_ids=change_history_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                change_history_rows=change_history_read_contract.change_history_rows,
                action_ids=change_history_read_contract.action_ids,
                blocked_claims=change_history_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if search_terms_read_contract.search_term_rows:
        search_term_action_ids = _search_term_action_ids(action_ids)
        metric_facts = [
            fact for row in search_terms_read_contract.search_term_rows for fact in row.metric_facts
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_search_terms",
                decision_type="review_search_terms",
                status="ready",
                title="Przejrzyj zapytania z reklam bez automatycznych wykluczeń",
                summary=search_terms_read_contract.summary,
                rationale=(
                    "WILQ widzi zapytania, kampanie, grupy reklam, koszt, kliknięcia "
                    "i konwersje. To pozwala zrobić kontrolę jakości zapytań, ale nie "
                    "wystarcza do claimów o waste ani do wdrożenia negative keywords."
                ),
                next_step=(
                    "Przejrzyj zapytania z najwyższym kosztem. Jeśli chcesz wykluczenia, "
                    "najpierw dodaj kontekst dopasowania, 90-dniowy safety check i "
                    "prepare-only ActionObject."
                ),
                allowed_metrics=search_terms_read_contract.allowed_metrics,
                missing_read_contracts=search_terms_read_contract.missing_read_contracts,
                operator_review_gates=search_terms_read_contract.operator_review_gates,
                source_connectors=search_terms_read_contract.source_connectors,
                evidence_ids=search_terms_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                search_term_rows=search_terms_read_contract.search_term_rows,
                action_ids=search_term_action_ids,
                blocked_claims=search_terms_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if search_term_ngram_read_contract.ngram_rows:
        metric_facts = [
            fact
            for row in search_term_ngram_read_contract.ngram_rows
            for fact in row.metric_facts
        ]
        top_rows = search_term_ngram_read_contract.ngram_rows[:8]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_search_term_ngrams",
                decision_type="review_search_term_ngrams",
                status="ready",
                title="Sprawdź powtarzające się tematy w zapytaniach",
                summary=search_term_ngram_read_contract.summary,
                rationale=(
                    "N-gramy pokazują, które słowa i frazy powtarzają się w search "
                    "terms oraz jaki mają koszt, kliknięcia i konwersje w evidence. "
                    "To skraca review, ale nadal wymaga ręcznego sprawdzenia intencji "
                    "i nie odblokowuje wykluczeń."
                ),
                next_step=search_term_ngram_read_contract.next_step,
                priority=42,
                metric_tiles={
                    "n-gramy": len(search_term_ngram_read_contract.ngram_rows),
                    "top koszt": sum(row.cost_micros or 0 for row in top_rows),
                    "top kliknięcia": sum(row.clicks or 0 for row in top_rows),
                },
                allowed_metrics=search_term_ngram_read_contract.allowed_metrics,
                missing_read_contracts=(
                    search_term_ngram_read_contract.missing_read_contracts
                ),
                operator_review_gates=(
                    search_term_ngram_read_contract.operator_review_gates
                ),
                source_connectors=search_term_ngram_read_contract.source_connectors,
                evidence_ids=search_term_ngram_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                search_term_ngram_rows=top_rows,
                action_ids=search_term_ngram_read_contract.action_ids,
                blocked_claims=search_term_ngram_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if search_term_safety_read_contract.status == "ready":
        metric_facts = [
            fact
            for row in search_term_safety_read_contract.safety_rows
            for fact in row.metric_facts
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_search_term_safety",
                decision_type="review_search_term_safety",
                status="ready",
                title="Sprawdź 90-dniową historię zapytań przed wykluczeniami",
                summary=search_term_safety_read_contract.summary,
                rationale=(
                    "WILQ ma oddzielny 90-dniowy odczyt search terms jako hamulec "
                    "bezpieczeństwa. To nadal nie jest rekomendacja wykluczeń: "
                    "brakuje kontekstu dopasowania, intencji i payload preview."
                ),
                next_step=search_term_safety_read_contract.next_step,
                allowed_metrics=search_term_safety_read_contract.allowed_metrics,
                missing_read_contracts=(
                    search_term_safety_read_contract.missing_read_contracts
                ),
                operator_review_gates=search_term_safety_read_contract.operator_review_gates,
                source_connectors=search_term_safety_read_contract.source_connectors,
                evidence_ids=search_term_safety_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                search_term_safety_rows=search_term_safety_read_contract.safety_rows,
                action_ids=[],
                blocked_claims=search_term_safety_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if negative_keywords_read_contract.candidates:
        metric_facts = [
            fact
            for candidate in negative_keywords_read_contract.candidates
            for fact in candidate.metric_facts
        ]
        safety_metric_facts = [
            fact
            for candidate in negative_keywords_read_contract.candidates
            for fact in candidate.safety_metric_facts
        ]
        keyword_context_metric_facts = [
            fact
            for candidate in negative_keywords_read_contract.candidates
            for context_row in candidate.keyword_context_rows
            for fact in context_row.metric_facts
        ]
        keyword_match_context_rows = [
            context_row
            for candidate in negative_keywords_read_contract.candidates
            for context_row in candidate.keyword_context_rows
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_review_negative_keyword_safety",
                decision_type="review_negative_keyword_safety",
                status="ready",
                title="Przejrzyj kandydatów wykluczeń tylko w trybie safety review",
                summary=negative_keywords_read_contract.summary,
                rationale=(
                    "WILQ widzi terminy z kosztem lub kliknięciami i zerową konwersją "
                    "w bieżącym evidence oraz review-only payload preview. To jest "
                    "sygnał do review, nie dowód waste ani zgoda na automatyczne "
                    "wykluczenie."
                ),
                next_step=negative_keywords_read_contract.next_step,
                allowed_metrics=[
                    "search_term",
                    "search_term_clicks",
                    "search_term_cost_micros",
                    "search_term_conversions",
                    "search_term_conversion_value",
                    "search_term_90d_clicks",
                    "search_term_90d_cost_micros",
                    "search_term_90d_conversions",
                    "search_term_90d_conversion_value",
                    "keyword_text",
                    "keyword_match_type",
                ],
                missing_read_contracts=negative_keywords_read_contract.missing_read_contracts,
                operator_review_gates=["human_intent_review"],
                source_connectors=negative_keywords_read_contract.source_connectors,
                evidence_ids=negative_keywords_read_contract.evidence_ids,
                metric_facts=[
                    *metric_facts,
                    *safety_metric_facts,
                    *keyword_context_metric_facts,
                ][:12],
                search_term_safety_rows=search_term_safety_read_contract.safety_rows[:12],
                keyword_match_context_rows=keyword_match_context_rows[:12],
                negative_keyword_candidates=negative_keywords_read_contract.candidates,
                negative_keyword_payload_preview=(
                    negative_keywords_read_contract.payload_preview
                ),
                action_ids=negative_keywords_read_contract.action_ids,
                blocked_claims=negative_keywords_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if custom_segments_read_contract.candidates:
        metric_facts = [
            fact
            for candidate in custom_segments_read_contract.candidates
            for fact in candidate.metric_facts
        ]
        search_term_rows = [
            row
            for candidate in custom_segments_read_contract.candidates
            for row in candidate.search_term_rows
        ]
        keyword_planner_idea_rows = [
            idea
            for candidate in custom_segments_read_contract.candidates
            for idea in candidate.keyword_planner_ideas
        ]
        decisions.append(
            AdsDecisionItem(
                id="ads_prepare_custom_segments_from_search_terms",
                decision_type="prepare_custom_segments",
                status="ready",
                title="Przygotuj custom segments z realnych search terms",
                summary=custom_segments_read_contract.summary,
                rationale=(
                    "WILQ ma source terms z Google Ads evidence, więc może przygotować "
                    "kandydatów segmentów. To nie jest apply ani obietnica skuteczności: "
                    "payload preview jest review-only, a forecast, audience size i zgoda "
                    "człowieka nadal są wymagane."
                ),
                next_step=custom_segments_read_contract.next_step,
                allowed_metrics=[
                    "search_term",
                    "search_term_clicks",
                    "search_term_impressions",
                    "search_term_cost_micros",
                    "search_term_conversions",
                    "search_term_conversion_value",
                    "keyword_planner_idea_text",
                    "keyword_planner_avg_monthly_searches",
                    "keyword_planner_competition_index",
                ],
                missing_read_contracts=custom_segments_read_contract.missing_read_contracts,
                operator_review_gates=(
                    custom_segments_read_contract.operator_review_gates
                ),
                source_connectors=custom_segments_read_contract.source_connectors,
                evidence_ids=custom_segments_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                search_term_rows=search_term_rows[:12],
                keyword_planner_idea_rows=keyword_planner_idea_rows[:12],
                custom_segment_candidates=custom_segments_read_contract.candidates,
                custom_segment_payload_preview=custom_segments_read_contract.payload_preview,
                custom_segment_audience_forecast_rows=(
                    custom_segments_read_contract.audience_forecast_read_contract.forecast_rows
                ),
                action_ids=custom_segments_read_contract.action_ids,
                blocked_claims=custom_segments_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    safety_section = next(
        (section for section in sections if section.id == "ads_action_safety"),
        None,
    )
    if safety_section is not None:
        decisions.append(
            AdsDecisionItem(
                id="ads_block_write_actions_without_actionobject",
                decision_type="block_write_actions",
                status="blocked",
                title="Nie wdrażaj zmian Ads bez osobnego ActionObject",
                summary=safety_section.summary,
                rationale=safety_section.diagnosis,
                next_step=safety_section.next_step,
                source_connectors=safety_section.source_connectors,
                evidence_ids=safety_section.evidence_ids,
                action_ids=safety_section.action_ids,
                blocked_claims=safety_section.blocked_claims,
                risk=safety_section.risk,
            )
        )

    return [_with_ads_decision_lineage(decision) for decision in decisions]


def _campaign_review_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == CAMPAIGN_REVIEW_ACTION_ID]


def _business_context_action_ids(action_ids: list[str]) -> list[str]:
    allowed_ids = {
        ADS_BUSINESS_CONTEXT_ACTION_ID,
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    }
    return [
        action_id for action_id in action_ids if action_id in allowed_ids
    ]


def _recommendation_action_ids(action_ids: list[str]) -> list[str]:
    return [
        action_id
        for action_id in action_ids
        if action_id == RECOMMENDATION_REVIEW_ACTION_ID
    ]


def _change_history_action_ids(action_ids: list[str]) -> list[str]:
    return [
        action_id for action_id in action_ids if action_id == CHANGE_HISTORY_IMPACT_ACTION_ID
    ]


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
        unavailable = [
            contract for contract in unavailable if contract != "budget_pacing"
        ]
    if (
        recommendations_read_contract is not None
        and recommendations_read_contract.status == "ready"
    ):
        unavailable = [
            contract for contract in unavailable if contract != "recommendations"
        ]
    if (
        impression_share_read_contract is not None
        and impression_share_read_contract.status == "ready"
    ):
        unavailable = [
            contract for contract in unavailable if contract != "impression_share"
        ]
    if (
        change_history_read_contract is not None
        and "change_history" not in change_history_read_contract.missing_read_contracts
    ):
        unavailable = [
            contract for contract in unavailable if contract != "change_history"
        ]
    return unavailable


def _blocked_handoff(
    live_data_available: bool,
    latest_refresh: ConnectorRefreshRun | None,
    sections: list[AdsDiagnosticSection],
    action_ids: list[str],
) -> AdsBlockedHandoff | None:
    evidence_ids = _unique(
        evidence_id for section in sections for evidence_id in section.evidence_ids
    )
    blocked_claims = _unique(claim for section in sections for claim in section.blocked_claims)
    if live_data_available:
        return None
    return AdsBlockedHandoff(
        status="blocked",
        title="Google Ads: finalny handoff blockera OAuth",
        summary=_ads_blocker_reason(latest_refresh),
        marketer_message=(
            "W demo pokaż, że WILQ widzi problem z dostępem i blokuje wszystkie wnioski o "
            "spendzie, CPA, ROAS, search terms i negative keywords. To jest kontrola jakości, "
            "nie brak wiedzy."
        ),
        repair_steps=[
            "Otwórz /ads-doctor i pokaż redacted OAuth blocker.",
            "Zweryfikuj ActionObject `act_configure_google_ads_env`.",
            "Uzyskaj świeży Google Ads OAuth token z zakresem `adwords`.",
            "Uruchom read-only `google_ads vendor_read`.",
            "Dopiero po świeżym evidence pokazuj spend, CPA, ROAS lub search terms.",
        ],
        allowed_demo_claims=[
            "Google Ads jest zablokowany przez OAuth/API access.",
            "WILQ nie zmyśla Ads metryk bez vendor evidence.",
            "Naprawa dostępu ma ActionObject i validation gate.",
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
    return "Brak wykonanego Google Ads vendor_read."


def _refresh_or_connector_evidence_ids(latest_refresh: ConnectorRefreshRun | None) -> list[str]:
    if latest_refresh:
        return latest_refresh.evidence_ids
    return [connector_evidence_id(GOOGLE_ADS_CONNECTOR_ID)]


def _with_ads_section_lineage(section: AdsDiagnosticSection) -> AdsDiagnosticSection:
    knowledge_card_ids, expert_rule_ids = ADS_SECTION_LINEAGE.get(section.id, ([], []))
    return section.model_copy(
        update={
            "knowledge_card_ids": _unique([*section.knowledge_card_ids, *knowledge_card_ids]),
            "expert_rule_ids": _unique([*section.expert_rule_ids, *expert_rule_ids]),
        }
    )


def _with_ads_decision_lineage(decision: AdsDecisionItem) -> AdsDecisionItem:
    knowledge_card_ids, expert_rule_ids = ADS_DECISION_LINEAGE.get(decision.id, ([], []))
    return decision.model_copy(
        update={
            "priority": _ads_decision_priority(decision),
            "metric_tiles": _ads_decision_metric_tiles(decision),
            "knowledge_card_ids": _unique([*decision.knowledge_card_ids, *knowledge_card_ids]),
            "expert_rule_ids": _unique([*decision.expert_rule_ids, *expert_rule_ids]),
        }
    )


def _ads_decision_priority(decision: AdsDecisionItem) -> int:
    type_priority: dict[str, int] = {
        "fix_ads_access": 5,
        "block_write_actions": 10,
        "review_campaign_triage": 18,
        "review_campaign_activity": 20,
        "review_business_context": 22,
        "review_derived_kpi": 25,
        "review_budget_context": 30,
        "review_recommendations": 35,
        "review_search_terms": 40,
        "review_search_term_ngrams": 42,
        "review_negative_keyword_safety": 45,
        "review_search_term_safety": 50,
        "prepare_custom_segments": 55,
        "review_impression_share": 60,
        "review_change_history": 65,
    }
    return type_priority.get(decision.decision_type, 90)


def _ads_decision_metric_tiles(decision: AdsDecisionItem) -> dict[str, int | float | str]:
    if decision.decision_type == "review_campaign_activity":
        urgent_rows = sum(1 for row in decision.campaign_rows if row.review_priority == "pilne")
        high_rows = sum(1 for row in decision.campaign_rows if row.review_priority == "wysokie")
        target_context_rows = sum(
            1 for row in decision.campaign_rows if row.target_status != "no_target"
        )
        campaign_tiles: dict[str, int | float | str | None] = {
            "kampanie": len(decision.campaign_rows),
            "pilne": urgent_rows,
            "wysokie": high_rows,
            "kliknięcia": _sum_attr(decision.campaign_rows, "clicks"),
            "wyświetlenia": _sum_attr(decision.campaign_rows, "impressions"),
            "koszt": _format_micros(_sum_attr(decision.campaign_rows, "cost_micros")),
            "konwersje": _round_metric(_sum_attr(decision.campaign_rows, "conversions")),
        }
        if target_context_rows:
            campaign_tiles["targety"] = target_context_rows
        return _clean_metric_tiles(campaign_tiles)
    if decision.decision_type == "review_campaign_triage":
        urgent_rows = sum(
            1 for row in decision.campaign_triage_rows if row.review_priority == "pilne"
        )
        high_rows = sum(
            1 for row in decision.campaign_triage_rows if row.review_priority == "wysokie"
        )
        recommendation_count = sum(
            row.recommendation_count for row in decision.campaign_triage_rows
        )
        preview_count = sum(
            1
            for row in decision.campaign_triage_rows
            if row.has_budget_apply_preview
        ) + sum(
            1
            for row in decision.campaign_triage_rows
            if row.has_recommendation_apply_preview
        )
        return _clean_metric_tiles(
            {
                "kampanie": len(decision.campaign_triage_rows),
                "pilne": urgent_rows,
                "wysokie": high_rows,
                "rekomendacje": recommendation_count,
                "podglądy": preview_count,
            }
        )
    if decision.decision_type == "review_business_context":
        return _clean_metric_tiles(
            {
                "braki": len(decision.missing_read_contracts),
                "blokady": len(decision.blocked_claims),
                "ustawione pola": len(decision.allowed_metrics),
                "review gates": len(decision.operator_review_gates),
                "polityki": decision.metric_tiles.get("polityki", 0),
            }
        )
    if decision.decision_type == "review_derived_kpi":
        rows_with_cpa = sum(
            1 for row in decision.derived_kpi_rows if row.cost_per_conversion_micros is not None
        )
        rows_with_roas = sum(1 for row in decision.derived_kpi_rows if row.roas is not None)
        rows_with_target_context = sum(
            1
            for row in decision.derived_kpi_rows
            if row.roas_vs_target is not None or row.cpa_vs_target_micros is not None
        )
        tiles: dict[str, int | float | str | None] = {
            "kampanie": len(decision.derived_kpi_rows),
            "wiersze CPA": rows_with_cpa,
            "wiersze ROAS": rows_with_roas,
        }
        if rows_with_target_context:
            tiles["targety"] = rows_with_target_context
        rows_within_target = sum(
            1 for row in decision.derived_kpi_rows if row.target_status == "within_target"
        )
        rows_outside_target = sum(
            1 for row in decision.derived_kpi_rows if row.target_status == "outside_target"
        )
        rows_with_spend_without_conversions = sum(
            1
            for row in decision.derived_kpi_rows
            if row.target_status == "spend_without_conversions"
        )
        if rows_within_target:
            tiles["w targetcie"] = rows_within_target
        if rows_outside_target:
            tiles["poza targetem"] = rows_outside_target
        if rows_with_spend_without_conversions:
            tiles["koszt bez konw."] = rows_with_spend_without_conversions
        return _clean_metric_tiles(tiles)
    if decision.decision_type == "review_budget_context":
        budget_tiles: dict[str, int | float | str | None] = {
            "budżety": len(decision.budget_rows),
            "podgląd budżetu": len(decision.budget_apply_preview),
            "koszt 7 dni": _format_micros(
                _sum_attr(decision.budget_rows, "cost_micros_7d")
            ),
        }
        if decision.shared_budget_distribution_rows:
            budget_tiles["wspólne budżety"] = len(
                decision.shared_budget_distribution_rows
            )
        return _clean_metric_tiles(budget_tiles)
    if decision.decision_type == "review_recommendations":
        rows_with_impact = sum(1 for row in decision.recommendation_rows if row.impact_available)
        urgent_rows = sum(
            1 for row in decision.recommendation_rows if row.review_priority == "pilne"
        )
        high_rows = sum(
            1 for row in decision.recommendation_rows if row.review_priority == "wysokie"
        )
        return _clean_metric_tiles(
            {
                "rekomendacje": len(decision.recommendation_rows),
                "pilne": urgent_rows,
                "wysokie": high_rows,
                "podgląd wpływu": rows_with_impact,
                "podgląd akcji": len(decision.recommendation_apply_preview),
            }
        )
    if decision.decision_type == "review_search_term_ngrams":
        rows = decision.search_term_ngram_rows
        rows_with_clicks = sum(1 for row in rows if (row.clicks or 0) > 0)
        max_source_terms = max((row.source_search_term_count for row in rows), default=0)
        max_clicks = max((row.clicks or 0 for row in rows), default=0)
        max_cost_micros = max((row.cost_micros or 0 for row in rows), default=0)
        ngram_tiles: dict[str, int | float | str | None] = {
            "n-gramy": decision.metric_tiles.get("n-gramy", len(rows)),
            "pokazane": len(rows),
            "z kliknięciami": rows_with_clicks,
            "max query/temat": max_source_terms,
            "top kliknięcia": max_clicks,
        }
        if max_cost_micros:
            ngram_tiles["top koszt"] = _format_micros(max_cost_micros)
        return _clean_metric_tiles(ngram_tiles)
    if decision.decision_type == "review_impression_share":
        return _clean_metric_tiles(
            {
                "kampanie": len(decision.impression_share_rows),
                "utrata przez budżet": sum(
                    1
                    for row in decision.impression_share_rows
                    if row.search_budget_lost_impression_share is not None
                ),
            }
        )
    if decision.decision_type == "review_change_history":
        return _clean_metric_tiles(
            {
                "zmiany": len(decision.change_history_rows),
                "kampanie": sum(
                    1 for row in decision.change_history_rows if row.campaign_id is not None
                ),
            }
        )
    if decision.decision_type == "review_search_terms":
        return _clean_metric_tiles(
            {
                "zapytania": len(decision.search_term_rows),
                "kliknięcia": _sum_attr(decision.search_term_rows, "clicks"),
                "koszt": _format_micros(_sum_attr(decision.search_term_rows, "cost_micros")),
            }
        )
    if decision.decision_type == "review_search_term_safety":
        return _clean_metric_tiles(
            {
                "90 dni": len(decision.search_term_safety_rows),
                "kliknięcia": _sum_attr(decision.search_term_safety_rows, "clicks_90d"),
                "koszt": _format_micros(
                    _sum_attr(decision.search_term_safety_rows, "cost_micros_90d")
                ),
            }
        )
    if decision.decision_type == "review_negative_keyword_safety":
        return _clean_metric_tiles(
            {
                "kandydaci": len(decision.negative_keyword_candidates),
                "pilne": sum(
                    1
                    for candidate in decision.negative_keyword_candidates
                    if candidate.review_priority == "pilne"
                ),
                "wysokie": sum(
                    1
                    for candidate in decision.negative_keyword_candidates
                    if candidate.review_priority == "wysokie"
                ),
                "podgląd akcji": len(decision.negative_keyword_payload_preview),
                "kontekst słów": len(decision.keyword_match_context_rows),
            }
        )
    if decision.decision_type == "prepare_custom_segments":
        return _clean_metric_tiles(
            {
                "segmenty": len(decision.custom_segment_candidates),
                "pilne": sum(
                    1
                    for candidate in decision.custom_segment_candidates
                    if candidate.review_priority == "pilne"
                ),
                "wysokie": sum(
                    1
                    for candidate in decision.custom_segment_candidates
                    if candidate.review_priority == "wysokie"
                ),
                "podgląd akcji": len(decision.custom_segment_payload_preview),
                "źródłowe zapytania": len(decision.search_term_rows),
                "KP ideas": len(decision.keyword_planner_idea_rows),
            }
        )
    if decision.decision_type in {"block_write_actions", "fix_ads_access"}:
        return _clean_metric_tiles(
            {
                "ActionObjecty": len(decision.action_ids),
                "blokady": len(decision.blocked_claims),
            }
        )
    return {}


def _sum_attr(rows: Iterable[object], attr: str) -> float | None:
    total: float | None = None
    for row in rows:
        value = getattr(row, attr, None)
        if isinstance(value, int | float):
            total = (total or 0.0) + float(value)
    return total


def _round_metric(value: float | None) -> int | float | None:
    if value is None:
        return None
    if value.is_integer():
        return int(value)
    return round(value, 3)


def _format_micros(value: float | None) -> str | None:
    if value is None:
        return None
    account_units = value / 1_000_000
    if account_units >= 100:
        return f"{account_units:.0f}"
    if account_units >= 10:
        return f"{account_units:.1f}"
    return f"{account_units:.2f}"


def _format_ratio_percent(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{_round_metric(value * 100)}%"


def _strategy_review_label(status: str) -> str:
    labels = {
        "missing": "brak",
        "approved_for_prepare": "zatwierdzone",
        "needs_changes": "wymaga poprawek",
        "rejected": "odrzucone",
        "deferred": "odłożone",
    }
    return labels.get(status, status)


def _clean_metric_tiles(
    tiles: dict[str, int | float | str | None],
) -> dict[str, int | float | str]:
    clean_tiles: dict[str, int | float | str] = {}
    for label, value in tiles.items():
        if value is None:
            continue
        if isinstance(value, float):
            rounded_value = _round_metric(value)
            if rounded_value is not None:
                clean_tiles[label] = rounded_value
        else:
            clean_tiles[label] = value
    return clean_tiles


def _metric_sentence(facts: list[MetricFact]) -> str:
    samples = ", ".join(f"{fact.name}={fact.value}" for fact in facts[:6])
    return f"Metric facts: {samples}."


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
