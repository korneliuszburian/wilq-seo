from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any, Literal, cast

from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
    ads_business_context_configured,
    ads_business_context_missing_read_contracts,
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
from wilq.briefing.ads_budget_pacing import build_budget_pacing_read_contract
from wilq.briefing.ads_change_history import build_change_history_read_contract
from wilq.briefing.ads_impression_share import build_impression_share_read_contract
from wilq.briefing.ads_recommendations import build_recommendations_read_contract
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
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
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    AdsAccountCurrencyReadContract,
    AdsBlockedHandoff,
    AdsBudgetApplyPreview,
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
    AdsRecommendationApplyPreview,
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
    MetricFact,
    connector_refresh_has_live_data,
    connector_refresh_run_status_label,
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
ADS_SUMMARY_METRIC_FACT_LIMIT = 500
ADS_SUMMARY_VIEW_ROW_LIMIT = 5
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
ADS_RECOMMENDATION_HUMAN_REVIEW_GATE = "human_strategy_review"
CUSTOM_SEGMENT_OPERATOR_REVIEW_GATES = [
    "review_source_terms",
    "reject_brand_or_low_intent_terms",
    "keyword_planner_enrichment",
    "forecast_or_audience_size",
    "human_confirm_before_apply",
]
ADS_REVIEW_GATE_LABELS = {
    "human_strategy_review": "ocena strategii przez człowieka",
    "review_recommendation_type": "sprawdzenie typu rekomendacji",
    "review_impact_metrics": "sprawdzenie wpływu rekomendacji",
    "review_change_history": "sprawdzenie historii zmian",
    "review_business_goal": "sprawdzenie celu biznesowego",
    "configure_business_goal": "uzupełnienie celu biznesowego",
    "review_profit_margin_model": "sprawdzenie modelu marży",
    "configure_profit_margin_or_value_model": "uzupełnienie marży albo modelu wartości",
    "review_human_budget_goal": "sprawdzenie celu budżetu",
    "configure_human_budget_goal": "uzupełnienie celu budżetu",
    "confirm_target_roas_or_cpa": (
        "potwierdzenie docelowego zwrotu z reklam albo kosztu pozyskania celu"
    ),
    "review_target_fit": "sprawdzenie dopasowania do celu",
    "review_campaign_goal": "sprawdzenie celu kampanii",
    "review_conversion_quality": "sprawdzenie jakości konwersji",
    "review_budget_context": "sprawdzenie kontekstu budżetu",
    "review_search_terms_before_budget_decision": ("wyszukiwane hasła przed decyzją budżetową"),
    "review_campaign_activity": "sprawdzenie aktywności kampanii",
    "verify_account_currency": "sprawdzenie waluty konta",
    "budget_pacing": "tempo wydawania budżetu",
    "impression_share": "udział w wyświetleniach",
    "change_history": "historia zmian",
    "human_budget_goal": "cel budżetu od człowieka",
    "budget_apply_preview": "podgląd zmiany budżetu",
    "campaign_budget_apply_safety": "bezpieczeństwo zmiany budżetu",
    "campaign_budget_operation_preview": "sprawdzenie zapisu budżetu w Google Ads",
    "review_conversion_tracking": "sprawdzenie trackingu konwersji",
    "review_pmax_asset_feed_context": "sprawdzenie PMax, pliku produktowego i materiałów",
    "review_draft_campaign_status": "sprawdzenie statusu draftu",
    "recommendation_apply_preview": "podgląd zapisu rekomendacji",
    "google_ads_rmf_compliance_review": "ocena zgodności Google Ads RMF",
    "human_confirm_before_apply": "potwierdzenie człowieka przed zapisem",
    "negative_keyword_action_validation": "sprawdzenie w WILQ dla wykluczeń",
    "human_intent_review": "ocena intencji przez człowieka",
    "review_source_terms": "sprawdzenie haseł źródłowych",
    "reject_brand_or_low_intent_terms": "odrzucenie brand i niskiej intencji",
    "keyword_planner_enrichment": "wzbogacenie przez Keyword Planner",
    "forecast_or_audience_size": "prognoza albo rozmiar odbiorców",
    "custom_segment_operation_preview": "sprawdzenie zapisu zmian w Google Ads",
    "google_ads_mutation_audit": "audyt zapisu zmian w Google Ads",
    "mutation_audit": "audyt zapisu zmian",
    "review_search_term_context": "sprawdzenie intencji zapytania",
    "check_existing_keywords_and_match_types": (
        "sprawdzenie istniejących słów kluczowych i typów dopasowania"
    ),
    "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
    "negative_keyword_change_preview": "podgląd zmian wykluczeń",
}
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


def build_ads_diagnostics(
    actions: list[ActionObject] | None = None,
    *,
    view: Literal["full", "summary"] = "full",
) -> AdsDiagnosticsResponse:
    connector = get_connector_status(GOOGLE_ADS_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Google Ads connector is not registered.")
    latest_refresh = _latest_google_ads_refresh()
    metric_facts = _ads_metric_facts_for_view(view, latest_refresh)
    latest_refresh_collected_data = (
        latest_refresh is not None
        and connector_refresh_has_live_data(latest_refresh)
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
        account_currency_read_contract.currency_code,
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
        account_currency_read_contract.currency_code,
    )
    search_term_safety_read_contract = _search_term_safety_read_contract(
        trusted_metric_facts,
        latest_refresh,
        account_currency_read_contract.currency_code,
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
        account_currency_read_contract.currency_code,
    )
    search_term_ngram_read_contract = _search_term_ngram_read_contract(
        search_terms_read_contract,
        latest_refresh,
        account_currency_read_contract.currency_code,
    )
    action_ids = _google_ads_action_ids(actions, live_data_available=live_data_available)
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
        account_currency_read_contract.currency_code,
    )
    response = AdsDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        connector_status_label=_ads_connector_status_label(str(connector.status)),
        latest_refresh=latest_refresh,
        latest_refresh_status_label=_ads_refresh_status_label(latest_refresh)
        if latest_refresh
        else None,
        live_data_status_label=_ads_live_data_status_label(live_data_available),
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
    _hydrate_ads_review_gate_labels(response)
    _hydrate_ads_marketer_labels(response)
    if view == "summary":
        return _compact_ads_diagnostics_summary(response)
    return response


def _compact_ads_diagnostics_summary(
    response: AdsDiagnosticsResponse,
) -> AdsDiagnosticsResponse:
    top_decision_ids = set(response.operator_summary.top_decision_ids)
    compact_decisions = [
        _compact_ads_decision(decision)
        for decision in response.decision_queue
        if decision.id in top_decision_ids
    ]
    if not compact_decisions:
        compact_decisions = [
            _compact_ads_decision(decision)
            for decision in response.decision_queue[:ADS_SUMMARY_VIEW_ROW_LIMIT]
        ]
    compact_custom_segments = response.custom_segments_read_contract.model_copy(
        update={
            "candidates": [
                _compact_custom_segment_candidate(candidate)
                for candidate in response.custom_segments_read_contract.candidates[
                    :ADS_SUMMARY_VIEW_ROW_LIMIT
                ]
            ],
            "payload_preview": response.custom_segments_read_contract.payload_preview[
                :ADS_SUMMARY_VIEW_ROW_LIMIT
            ],
            "audience_forecast_read_contract": (
                response.custom_segments_read_contract.audience_forecast_read_contract.model_copy(
                    update={
                        "forecast_rows": (
                            response.custom_segments_read_contract.audience_forecast_read_contract.forecast_rows[
                                :ADS_SUMMARY_VIEW_ROW_LIMIT
                            ]
                        )
                    }
                )
            ),
        }
    )
    compact_negative_keywords = response.negative_keywords_read_contract.model_copy(
        update={
            "candidates": [
                _compact_negative_keyword_candidate(candidate)
                for candidate in response.negative_keywords_read_contract.candidates[
                    :ADS_SUMMARY_VIEW_ROW_LIMIT
                ]
            ],
            "payload_preview": response.negative_keywords_read_contract.payload_preview[
                :ADS_SUMMARY_VIEW_ROW_LIMIT
            ],
        }
    )
    return response.model_copy(
        update={
            "campaign_read_contract": _copy_limited_model(
                response.campaign_read_contract,
                campaign_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "derived_kpi_read_contract": _copy_limited_model(
                response.derived_kpi_read_contract,
                kpi_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "budget_pacing_read_contract": _copy_limited_model(
                response.budget_pacing_read_contract,
                budget_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
                shared_budget_distribution_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
                payload_preview=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "recommendations_read_contract": _copy_limited_model(
                response.recommendations_read_contract,
                recommendation_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
                payload_preview=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "impression_share_read_contract": _copy_limited_model(
                response.impression_share_read_contract,
                impression_share_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "campaign_triage_read_contract": _copy_limited_model(
                response.campaign_triage_read_contract,
                triage_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "change_history_read_contract": _copy_limited_model(
                response.change_history_read_contract,
                change_history_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "change_impact_readiness_contract": _copy_limited_model(
                response.change_impact_readiness_contract,
                readiness_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "search_terms_read_contract": _copy_limited_model(
                response.search_terms_read_contract,
                search_term_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "search_term_ngram_read_contract": _copy_limited_model(
                response.search_term_ngram_read_contract,
                ngram_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "search_term_safety_read_contract": _copy_limited_model(
                response.search_term_safety_read_contract,
                safety_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "keyword_match_context_read_contract": _copy_limited_model(
                response.keyword_match_context_read_contract,
                context_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "keyword_planner_read_contract": _copy_limited_model(
                response.keyword_planner_read_contract,
                idea_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            ),
            "custom_segments_read_contract": compact_custom_segments,
            "negative_keywords_read_contract": compact_negative_keywords,
            "decision_queue": compact_decisions,
            "sections": [],
        }
    )


def _compact_ads_decision(decision: AdsDecisionItem) -> AdsDecisionItem:
    return cast(
        AdsDecisionItem,
        _copy_limited_model(
            decision,
            metric_facts=ADS_SUMMARY_VIEW_ROW_LIMIT,
            campaign_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            campaign_triage_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            derived_kpi_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            budget_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            shared_budget_distribution_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            budget_apply_preview=ADS_SUMMARY_VIEW_ROW_LIMIT,
            recommendation_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            recommendation_apply_preview=ADS_SUMMARY_VIEW_ROW_LIMIT,
            impression_share_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            change_history_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            search_term_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            search_term_ngram_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            search_term_safety_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            keyword_match_context_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            keyword_planner_idea_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            custom_segment_candidates=ADS_SUMMARY_VIEW_ROW_LIMIT,
            custom_segment_payload_preview=ADS_SUMMARY_VIEW_ROW_LIMIT,
            custom_segment_audience_forecast_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            negative_keyword_candidates=ADS_SUMMARY_VIEW_ROW_LIMIT,
            negative_keyword_payload_preview=ADS_SUMMARY_VIEW_ROW_LIMIT,
        ),
    )


def _compact_custom_segment_candidate(
    candidate: AdsCustomSegmentCandidate,
) -> AdsCustomSegmentCandidate:
    return cast(
        AdsCustomSegmentCandidate,
        _copy_limited_model(
            candidate,
            search_term_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
            keyword_planner_ideas=ADS_SUMMARY_VIEW_ROW_LIMIT,
            metric_facts=ADS_SUMMARY_VIEW_ROW_LIMIT,
        ),
    )


def _compact_negative_keyword_candidate(
    candidate: AdsNegativeKeywordCandidate,
) -> AdsNegativeKeywordCandidate:
    return cast(
        AdsNegativeKeywordCandidate,
        _copy_limited_model(
            candidate,
            metric_facts=ADS_SUMMARY_VIEW_ROW_LIMIT,
            safety_metric_facts=ADS_SUMMARY_VIEW_ROW_LIMIT,
            keyword_context_rows=ADS_SUMMARY_VIEW_ROW_LIMIT,
        ),
    )


def _copy_limited_model(model: Any, **field_limits: int) -> Any:
    updates = {}
    for field_name, limit in field_limits.items():
        if hasattr(model, field_name):
            updates[field_name] = getattr(model, field_name)[:limit]
    if not updates:
        return model
    return model.model_copy(update=updates)


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
        allowed_metrics=_unique(
            metric for decision in top_decisions for metric in decision.allowed_metrics
        ),
        missing_read_contracts=_unique(
            contract for decision in top_decisions for contract in decision.missing_read_contracts
        ),
        operator_review_gates=_unique(
            gate for decision in top_decisions for gate in decision.operator_review_gates
        ),
        source_connectors=_unique(
            connector for decision in top_decisions for connector in decision.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id for decision in top_decisions for evidence_id in decision.evidence_ids
        ),
        action_ids=_unique(
            action_id for decision in top_decisions for action_id in decision.action_ids
        ),
        blocked_claims=_unique(
            claim for decision in top_decisions for claim in decision.blocked_claims
        ),
        top_blocked_claim_labels=_unique(
            claim for decision in top_decisions for claim in decision.blocked_claims
        )[:5],
    )


def _ads_decision_status_rank(decision: AdsDecisionItem) -> int:
    return 0 if decision.status == "ready" else 1


def _latest_google_ads_refresh() -> ConnectorRefreshRun | None:
    runs = [
        run
        for run in list_connector_refresh_runs(connector_id=GOOGLE_ADS_CONNECTOR_ID)
        if run.mode == ConnectorRefreshMode.vendor_read
    ]
    if not runs:
        return None
    return max(runs, key=_connector_refresh_recency_key)


def _connector_refresh_recency_key(run: ConnectorRefreshRun) -> tuple[str, str]:
    timestamp = run.completed_at or run.started_at
    return (timestamp.isoformat(), run.id)


def _ads_metric_facts_for_view(
    view: Literal["full", "summary"],
    latest_refresh: ConnectorRefreshRun | None,
) -> list[MetricFact]:
    if view == "summary" and latest_refresh is not None and latest_refresh.evidence_ids:
        latest_evidence_facts = metric_store().list_metric_facts_by_evidence_ids(
            latest_refresh.evidence_ids
        )
        if not latest_refresh.metrics_persisted:
            return latest_evidence_facts
        if latest_evidence_facts:
            return latest_evidence_facts
        if (
            "row_count" in latest_refresh.metric_summary
            and not latest_refresh.vendor_data_collected
        ):
            return latest_evidence_facts

    metric_fact_limit = (
        ADS_SUMMARY_METRIC_FACT_LIMIT if view == "summary" else ADS_METRIC_FACT_LIMIT
    )
    return metric_store().list_metric_facts(
        connector_id=GOOGLE_ADS_CONNECTOR_ID,
        limit=metric_fact_limit,
    )


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
    has_completed_live_refresh = (
        connector_refresh_has_live_data(latest_refresh)
        and bool(metric_facts)
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
            "do diagnozy kosztu pozyskania celu, zwrotu z reklam, "
            "strat budżetu na zapytaniach ani wykluczeń."
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
        summary="Brak metryk kampanii z Google Ads.",
        diagnosis=(
            "Nie ma aktualnych wierszy kampanii, więc dashboard nie pokazuje kosztu ani trendów "
            "kampanii. To jest blokada, nie puste miejsce na estymację."
        ),
        next_step="Napraw OAuth i wykonaj odczyt danych Google Ads.",
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=[],
        blocked_claims=["wydatki reklamowe", "kliknięcia", "wyświetlenia", "trend kampanii"],
        risk=ActionRisk.medium,
    )


def _derived_kpi_section(
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
) -> AdsDiagnosticSection:
    return AdsDiagnosticSection(
        id="ads_derived_kpi",
        title="Wyliczone wskaźniki kampanii Google Ads",
        status=derived_kpi_read_contract.status,
        summary=derived_kpi_read_contract.summary,
        diagnosis=(
            "WILQ może pokazać współczynnik kliknięć, koszt kliknięcia, współczynnik konwersji, "
            "koszt pozyskania celu i zwrot z reklam jako obliczenia z bieżących danych kampanii. "
            "To nie jest jeszcze diagnoza rentowności, ocena zmarnowanego budżetu "
            "ani zgoda na zmianę budżetu."
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
            "WILQ oddziela wyliczone wskaźniki od decyzji biznesowej. Marża, cel biznesowy, "
            "cel budżetu, docelowy zwrot z reklam i docelowy koszt pozyskania celu "
            "są kontraktem operatora, nie danymi z Google Ads."
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
    currency_code: str | None,
) -> AdsCampaignReadContract:
    rows = _campaign_metric_rows(metric_facts, business_context_read_contract)
    missing_read_contracts = [
        "recommendations",
        "change_history",
        "impression_share",
    ]
    blocked_claims = [
        "koszt pozyskania celu",
        "zwrot z reklam",
        "marnowanie budżetu na zapytaniach",
        "zmarnowany budżet",
        "propozycje wykluczeń",
        "skalowanie budżetu",
        "spadek konwersji",
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
                f"WILQ ma {len(rows)} wierszy kampanii: {total_clicks} kliknięć, "
                f"{total_impressions} wyświetleń, "
                f"koszt {_format_money_micros(total_cost_micros, currency_code)}, "
                f"{_format_float(total_conversions)} konwersji, "
                f"wartość konwersji {_format_float(total_conversion_value)}."
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
            evidence_ids=_unique(
                evidence_id for row in rows for evidence_id in row.evidence_ids
            ),
            campaign_rows=rows,
            next_step=(
                "Użyj wierszy kampanii do sprawdzenia aktywności. "
                "Przed wnioskami o stracie budżetu, koszcie pozyskania celu, "
                "zwrocie z reklam albo wykluczeniach uzupełnij brakujące dane."
            ),
        )

    return AdsCampaignReadContract(
        status="blocked",
        title="Google Ads: brak aktywności kampanii",
        summary="WILQ nie ma wymiarowych danych kampanii z Google Ads.",
        allowed_metrics=[],
        missing_read_contracts=["aktywność kampanii", *missing_read_contracts],
        blocked_claims=["kliknięcia", "wyświetlenia", "wydatki reklamowe", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        campaign_rows=[],
        next_step="Uruchom odczyt danych Google Ads i zapisz metryki kampanii.",
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
                "opłacalność",
                "ocena marży",
                "zmiana budżetu",
            ],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(fact.evidence_id for fact in currency_facts),
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
    configured_sources = _unique(
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
    status: Literal["ready", "blocked"] = "ready" if not blocking_missing_contracts else "blocked"
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
            else "marża niepodana",
            "cel biznesowy": business_goal or "cel niepotwierdzony",
            "cel budżetu": budget_goal or "cel budżetu niepotwierdzony",
            "docelowy zwrot z reklam": target_roas,
            "docelowy koszt pozyskania celu": _format_micros(target_cpa_micros),
            "źródło celu": "potwierdzone" if target_confirmation is not None else None,
            "ocena strategii": _strategy_review_label(strategy_review_status),
        }
    )
    blocked_claims = [
        "opłacalność",
        "ocena marży",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "zmarnowany budżet",
    ]
    if status == "ready":
        if target_missing:
            summary = (
                "WILQ ma wstępny lokalny kontekst biznesowy Ads: marżę, cel "
                "biznesowy i cel budżetu. Docelowy zwrot z reklam albo koszt pozyskania "
                "celu jest celowo pusty, więc "
                "wskaźniki względem celu pozostają bez oceny i nie odblokowują skalowania "
                "ani zapisu zmian."
            )
            next_step = (
                "Użyj marży i celu budżetu jako kontekstu oceny kampanii. Jeśli "
                "operator potwierdzi docelowy zwrot z reklam albo koszt pozyskania celu "
                "przez sprawdzoną akcję, WILQ zapisze go w lokalnym stanie; do tego czasu "
                "ocena celu pozostaje zablokowana."
            )
        else:
            summary = (
                "WILQ ma lokalny kontekst biznesowy Ads: marżę, cel biznesowy, cel "
                "budżetu oraz docelowy zwrot z reklam albo koszt pozyskania celu. "
                "To pozwala "
                "interpretować wskaźniki ostrożniej, "
                "ale nadal nie odblokowuje automatycznych zmian."
            )
            next_step = (
                "Użyj potwierdzonego celu jako kontekstu oceny kampanii i "
                "budżetu. Zapis zmian nadal wymaga akcji do sprawdzenia w WILQ, podglądu zmian, "
                "potwierdzenia i audytu."
            )
    else:
        summary = (
            "WILQ ma aktualne metryki Google Ads, ale nie ma kompletnego lokalnego "
            "kontekstu biznesowego: marży, celu biznesowego, celu budżetu albo "
            "docelowego zwrotu z reklam lub kosztu pozyskania celu. Bez tego wskaźniki są "
            "tylko wstępnym przeglądem, nie oceną."
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
        strategy_reviewed_by=strategy_review.reviewed_by if strategy_review is not None else None,
        strategy_reviewed_at=strategy_review.created_at if strategy_review is not None else None,
        strategy_review_summary=strategy_review.notes if strategy_review is not None else None,
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
        "ocena opłacalności",
        "ocena wskaźników względem celu",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "automatyczna optymalizacja",
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
            "Ocena strategii Ads przez człowieka jest zatwierdzona do przygotowania. To pozwala "
            "używać potwierdzonego celu w ocenie, ale nie odblokowuje zapisu zmian "
            "ani automatycznej "
            "optymalizacji."
        )
        next_step = (
            "Użyj zatwierdzonej oceny jako kontekstu decyzji. Każda ścieżka zapisu "
            "nadal wymaga osobnego sprawdzenia w WILQ, podglądu, potwierdzenia i audytu."
        )
        status: Literal["ready", "blocked"] = "ready"
        contract_missing: list[str] = []
        action_ids: list[str] = []
    else:
        summary = (
            "Ocena strategii Ads przez człowieka nie jest zatwierdzona, więc WILQ może "
            "tylko przygotować kolejki do oceny. Ocena celu, ocena "
            "opłacalności, skalowanie i zapis zmian pozostają zablokowane."
        )
        next_step = (
            "Otwórz akcję strategii, sprawdź marżę, cel biznesowy, cel "
            "budżetu oraz docelowy zwrot z reklam albo koszt pozyskania celu, "
            "a potem zapisz wynik oceny."
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
    latest_outcome = strategy_review.outcome if strategy_review is not None else None
    return AdsStrategyReviewReadinessContract(
        status=status,
        title="Google Ads: gotowość oceny strategii przez człowieka",
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
                "WILQ nie interpretuje wskaźników biznesowo, dopóki brakuje marży, celu "
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
            "oceny, ale blokuje ocenę wskaźników względem celu, ocenę rentowności i zapis zmian "
            "do czasu potwierdzenia docelowego zwrotu z reklam albo kosztu pozyskania celu."
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
            "WILQ ma potwierdzony docelowy zwrot z reklam albo koszt pozyskania celu, "
            "ale blokuje ocenę wskaźników względem celu i zapis zmian, dopóki ocena strategii "
            "przez człowieka nie będzie zatwierdzona."
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
            "WILQ ma potwierdzony docelowy zwrot z reklam albo koszt pozyskania celu "
            "i może porównywać wskaźniki do celu po zatwierdzeniu przez człowieka. "
            "Zapis zmian nadal wymaga "
            "akcji do sprawdzenia w WILQ, podglądu, potwierdzenia i audytu."
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
    gates.append("review_human_budget_goal" if budget_goal else "configure_human_budget_goal")
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
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "marnowanie budżetu na zapytaniach",
            "zmarnowany budżet",
        ],
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
        "opłacalność",
        "skalowanie budżetu",
        "zmarnowany budżet",
        "zapis rekomendacji",
        "wpływ samej zmiany",
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
            f" Porównanie z celem dostępne dla {rows_with_target_context} kampanii."
            f" Wstępny przegląd celu: w celu {rows_within_target},"
            f" poza celem {rows_outside_target}, koszt bez konwersji"
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
            title="Google Ads: wyliczone wskaźniki kampanii",
            summary=(
                f"WILQ może policzyć wskaźniki dla {len(kpi_rows)} kampanii: "
                f"koszt pozyskania celu dostępny dla {rows_with_cpa}, "
                f"zwrot z reklam dostępny dla {rows_with_roas}. "
                "To są obliczenia z bieżących danych źródłowych, nie ocena opłacalności."
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
                "Użyj wskaźników i ewentualnego porównania z celem "
                "do ustalenia kolejności oceny kampanii. "
                "Przed decyzją budżetową sprawdź marżę, pacing budżetu, historię "
                "zmian i rekomendacje."
            ),
        )
    return AdsDerivedKpiReadContract(
        status="blocked",
        title="Google Ads: brak wyliczalnych wskaźników kampanii",
        summary="WILQ nie ma kompletnych danych kampanii do wyliczenia wskaźników.",
        allowed_metrics=[],
        missing_read_contracts=["aktywność kampanii", *missing_read_contracts],
        blocked_claims=[
            "współczynnik kliknięć",
            "koszt kliknięcia",
            "koszt pozyskania celu",
            "zwrot z reklam",
            *blocked_claims,
        ],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=campaign_read_contract.evidence_ids,
        kpi_rows=[],
        next_step="Najpierw zbierz dane kampanii z Google Ads.",
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
            "opłacalność",
            "skalowanie budżetu",
            "zmarnowany budżet",
            "zapis rekomendacji",
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
                return "within_target", "koszt pozyskania celu w granicy celu", 40
            return "outside_target", "koszt pozyskania celu powyżej celu", 20
        if (row.cost_micros or 0) > 0 and not row.conversions:
            return "spend_without_conversions", "koszt bez konwersji", 15
        return "insufficient_data", "brak kosztu pozyskania celu do porównania", 70

    if target_roas is not None:
        if roas is not None:
            if roas >= target_roas:
                return "within_target", "zwrot z reklam w granicy celu", 40
            return "outside_target", "zwrot z reklam poniżej celu", 20
        if (row.cost_micros or 0) > 0 and not row.conversion_value:
            return "spend_without_conversions", "koszt bez wartości konwersji", 15
        return "insufficient_data", "brak zwrotu z reklam do porównania", 70

    return "no_target", "brak celu", 90


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
            "skalowania ani zmiany budżetu."
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
        title="Rekomendacje Google Ads do sprawdzenia",
        status=recommendations_read_contract.status,
        summary=recommendations_read_contract.summary,
        diagnosis=(
            "WILQ może pokazać typy aktywnych rekomendacji Google Ads jako input "
            "do sprawdzenia. To nie jest zgoda na zapis zmian ani dowód, że rekomendacja jest "
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
        "zmarnowany budżet",
        "opłacalność",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "zapis zmian kampanii",
    ]
    if rows:
        urgent_rows = sum(1 for row in rows if row.review_priority == "pilne")
        high_rows = sum(1 for row in rows if row.review_priority == "wysokie")
        return AdsCampaignTriageReadContract(
            status="ready",
            title="Kolejność oceny kampanii Ads",
            summary=(
                f"WILQ połączył aktywność kampanii, wskaźniki, budżet, rekomendacje i "
                f"udział w wyświetleniach dla {len(rows)} kampanii. "
                f"{_urgent_ads_campaign_count_label(urgent_rows)} i "
                f"{_high_signal_ads_campaign_count_label(high_rows)}. "
                "To nie jest ocena zmarnowanego budżetu, "
                "opłacalności, kosztu pozyskania celu ani zwrotu z reklam; "
                "to kolejność ręcznej oceny."
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
                "jakość konwersji, budżet, wyszukiwane hasła i rekomendacje; zapis zmian i "
                "skalowanie zostają zablokowane."
            ),
        )
    return AdsCampaignTriageReadContract(
        status="blocked",
        title="Kolejność oceny kampanii Ads",
        summary="WILQ nie ma wierszy kampanii potrzebnych do kolejki oceny kampanii.",
        allowed_metrics=[],
        missing_read_contracts=["campaign activity"],
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=campaign_read_contract.evidence_ids,
        triage_rows=[],
        action_ids=[],
        next_step="Najpierw zbierz fakty kampanii Google Ads bez zapisu zmian.",
    )


def _urgent_ads_campaign_count_label(count: int) -> str:
    if count == 1:
        return "1 pilna kampania"
    if 2 <= count <= 4:
        return f"{count} pilne kampanie"
    return f"{count} pilnych kampanii"


def _high_signal_ads_campaign_count_label(count: int) -> str:
    if count == 1:
        return "1 kampania o wysokim sygnale"
    if 2 <= count <= 4:
        return f"{count} kampanie o wysokim sygnale"
    return f"{count} kampanii o wysokim sygnale"


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
        source_metric_values.extend(fact.name for fact in impression_share_row.metric_facts)
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
            f"{campaign_row.review_reason} Dodatkowy kontekst oceny: "
            f"wskaźniki {'dostępne' if kpi_row is not None else 'niedostępne'}, "
            f"budżet {'dostępny' if budget_row is not None else 'niedostępny'}, "
            f"rekomendacje do sprawdzenia: {len(recommendation_rows)}, "
            "udział w wyświetleniach "
            f"{'dostępny' if impression_share_row is not None else 'niedostępny'}."
        ),
        next_step=(
            "Otwórz kampanię w widoku Google Ads, sprawdź cel, konwersje, budżet, "
            "wyszukiwane hasła i rekomendacje. Nie zapisuj zmian bez akcji do sprawdzenia w WILQ "
            "i potwierdzenia człowieka."
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
            "zmarnowany budżet",
            "opłacalność",
            "skalowanie budżetu",
            "zmiana budżetu",
            "zapis rekomendacji",
            "zapis zmian kampanii",
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
            title="Kolejność oceny kampanii",
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
            title="Budżety, rekomendacje i udział w wyświetleniach",
            status=(
                "ready"
                if budget_pacing_read_contract.budget_rows
                or recommendations_read_contract.recommendation_rows
                or impression_share_read_contract.impression_share_rows
                else "blocked"
            ),
            summary=(
                "WILQ ma kontekst budżetu, rekomendacji albo udziału w wyświetleniach do "
                "ręcznej oceny. To nadal nie odblokowuje zmiany budżetu ani "
                "automatycznego przyjęcia rekomendacji."
            ),
            next_step=(
                "Porównaj tempo wydatków, rekomendacje i udział w wyświetleniach przy "
                "kampaniach z kolejki oceny; zapis zmian pozostaje zablokowany."
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
            title="Ocena wyszukiwanych haseł",
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
            title="Akcje do sprawdzenia wykluczeń",
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
            title="Segmenty niestandardowe z wyszukiwanych haseł",
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
            title="Wzbogacenie Keyword Planner",
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
            title="Ocena wpływu historii zmian",
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
            title="Zapis zmian Ads",
            status="blocked",
            summary=(
                "WILQ ma część podglądów do oceny, ale nie ma jeszcze bezpiecznej "
                "ścieżki zapisu zmian Ads. Każda mutacja pozostaje zablokowana."
            ),
            next_step=(
                "Zostań w trybie oceny: sprawdź propozycje w WILQ, nie zapisuj "
                "zmian budżetów, rekomendacji, wykluczeń ani segmentów bez "
                "osobnego kontraktu potwierdzenia i audytu."
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
                "zmiana budżetu",
                "zapis rekomendacji",
                "dodanie wykluczających słów kluczowych",
                "zapis kierowania reklam",
                "zapis zmian kampanii",
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
        title="Gotowość optymalizacji Ads",
        summary=(
            f"WILQ ma {ready_area_count} obszarów gotowych do oceny i "
            f"{blocked_area_count} obszarów zablokowanych. To jest tryb "
            "sprawdzenia bez zapisu zmian: porządkuje pracę marketera, ale nie "
            "odblokowuje zapisów zmian, obietnic wpływu ani decyzji o rentowności."
        ),
        ready_area_count=ready_area_count,
        blocked_area_count=blocked_area_count,
        readiness_items=items,
        allowed_metrics=_unique(metric for item in items for metric in item.allowed_metrics),
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
                "ocena kosztu pozyskania celu",
                "werdykt zwrotu z reklam",
                "opłacalność",
            ]
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        action_ids=_unique(action_id for item in items for action_id in item.action_ids),
        next_step=(
            "Pracuj od obszarów ready, ale każdy wniosek o zmianie budżetu, "
            "rekomendacji, wykluczeń, segmentów albo wpływie zmian traktuj jako "
            "zablokowany, dopóki odpowiedni odczyt, zapis zmian i audyt nie będą gotowe."
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
        "wpływ zmian",
        "obietnica poprawy wyniku",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis zmian kampanii",
    ]
    rows = [
        _change_impact_readiness_row(change_row, campaign_read_contract.campaign_rows)
        for change_row in change_history_read_contract.change_history_rows
    ]
    row_missing = _unique(missing for row in rows for missing in row.missing_read_contracts)
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
        campaign_context_count = sum(1 for row in rows if row.current_campaign_metrics_available)
        summary = (
            f"WILQ ma {len(rows)} zdarzeń zmian do oceny wpływu i "
            f"{campaign_context_count} powiązanych bieżących odczytów kampanii. To jest "
            "gotowość do ręcznego audytu, nie dowód wpływu zmian."
        )
    else:
        summary = (
            "WILQ nie ma zdarzeń historii zmian do oceny wpływu, więc nie może porównać "
            "wyników sprzed zmiany i po zmianie ani przypisać zmian do kampanii."
        )
    return AdsChangeImpactReadinessContract(
        status="blocked",
        title="Google Ads: gotowość oceny wpływu zmian",
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
            "Użyj tego jako checklisty gotowości: sprawdź, czy są zdarzenia historii zmian, "
            "aktualny odczyt kampanii i porównanie wyników sprzed zmiany i po zmianie. "
            "Nie oceniaj wpływu zmian bez takiego porównania i sprawdzenia przez człowieka."
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
            "wpływ zmian",
            "obietnica poprawy wyniku",
            "skalowanie budżetu",
            "zmiana budżetu",
            "zapis zmian kampanii",
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
    return change_history_read_contract.model_copy(update={"action_ids": change_history_action_ids})


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
        return "wartość niepotwierdzona"
    numeric_value = float(value)
    if numeric_value == 0:
        return "0"
    prefix = "+" if numeric_value > 0 else ""
    return f"{prefix}{_format_float(numeric_value)}"


def _search_terms_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> AdsSearchTermsReadContract:
    rows = _search_term_metric_rows(metric_facts)
    missing_read_contracts = [
        "keyword match context",
        "90_day_safety_check",
    ]
    operator_review_gates = ["negative_keyword_action_validation"]
    blocked_claims = [
        "marnowanie budżetu na zapytaniach",
        "propozycje wykluczeń",
        "dodanie wykluczających słów kluczowych",
        "koszt pozyskania celu",
        "zwrot z reklam",
        "utrata konwersji",
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
                f"WILQ ma {len(rows)} wierszy zapytań: {total_clicks} kliknięć, "
                f"{total_impressions} wyświetleń, "
                f"koszt {_format_money_micros(total_cost_micros, currency_code)}, "
                f"{_format_float(total_conversions)} konwersji, "
                f"wartość konwersji {_format_float(total_conversion_value)}."
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
                "wykluczeń ani obietnic o marnowaniu budżetu bez kontekstu dopasowania, 90-dniowej "
                "kontroli i akcji do sprawdzenia."
            ),
        )

    return AdsSearchTermsReadContract(
        status="blocked",
        title="Google Ads: brak zapytań użytkowników",
        summary="WILQ nie ma jeszcze wymiarowych faktów z `search_term_view`.",
        allowed_metrics=[],
        missing_read_contracts=["search_term_view", *missing_read_contracts],
        blocked_claims=["wyszukiwane hasła", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        search_term_rows=[],
        next_step=(
            "Uruchom odczyt danych Google Ads po dodaniu odczytu `search_term_view` "
            "i zapisz metryki search_term_*."
        ),
    )


def _search_term_review_summary_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> AdsSearchTermReviewSummaryContract:
    rows = search_terms_read_contract.search_term_rows
    blocked_claims = [
        "marnowanie budżetu na zapytaniach",
        "dodanie wykluczających słów kluczowych",
        "koszt pozyskania celu",
        "zwrot z reklam",
    ]
    if not rows:
        return AdsSearchTermReviewSummaryContract(
            status="blocked",
            title="Google Ads: brak kolejki oceny wyszukiwanych haseł",
            summary=(
                "WILQ nie ma wierszy wyszukiwanych haseł, więc nie może wskazać kolejności oceny."
            ),
            allowed_metrics=[],
            missing_read_contracts=["search_term_view"],
            operator_review_gates=[],
            blocked_claims=["wyszukiwane hasła", *blocked_claims],
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            top_cost_search_terms=[],
            campaign_review_rows=[],
            next_step="Uruchom odczyt danych Google Ads z odczytem `search_term_view`.",
        )

    total_clicks = sum(row.clicks or 0 for row in rows)
    total_impressions = sum(row.impressions or 0 for row in rows)
    total_cost_micros = sum(row.cost_micros or 0 for row in rows)
    total_conversions = sum(row.conversions or 0 for row in rows)
    zero_conversion_count = sum(1 for row in rows if row.conversions == 0)
    campaign_review_rows = _search_term_campaign_review_rows(rows)
    return AdsSearchTermReviewSummaryContract(
        status="ready",
        title="Google Ads: kolejność oceny wyszukiwanych haseł",
        summary=(
            f"WILQ ma {len(rows)} wierszy wyszukiwanych haseł do ręcznej oceny: "
            f"{total_clicks} kliknięć, {total_impressions} wyświetleń, "
            f"koszt {_format_money_micros(total_cost_micros, currency_code)}, "
            f"{_format_float(total_conversions)} konwersji, "
            f"{zero_conversion_count} wierszy bez konwersji."
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
        top_cost_search_terms=[_search_term_review_row(row) for row in rows[:5]],
        campaign_review_rows=campaign_review_rows,
        next_step=(
            "Najpierw przejrzyj kampanie i zapytania z największym kosztem. "
            "Nie nazywaj ich stratą budżetu i nie twórz wykluczeń bez oceny intencji, "
            "kontroli 90 dni, podglądu zmian i sprawdzenia w WILQ."
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
            "marnowanie budżetu na zapytaniach",
            "dodanie wykluczających słów kluczowych",
            "koszt pozyskania celu",
            "zwrot z reklam",
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
                    evidence_id for row in campaign_rows for evidence_id in row.evidence_ids
                ),
                blocked_claims=[
                    "marnowanie budżetu na zapytaniach",
                    "dodanie wykluczających słów kluczowych",
                    "koszt pozyskania celu",
                    "zwrot z reklam",
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
        conversion_value=_float_metric_value(facts_by_name.get("search_term_conversion_value")),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "dodanie wykluczających słów kluczowych",
            "zmarnowany budżet",
        ],
    )


def _search_term_row_sort_key(row: AdsSearchTermMetricRow) -> tuple[int, int, str]:
    return (-(row.cost_micros or 0), -(row.clicks or 0), row.search_term)


def _search_term_ngram_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    latest_refresh: ConnectorRefreshRun | None,
    currency_code: str | None,
) -> AdsSearchTermNgramReadContract:
    rows = _search_term_ngram_rows(search_terms_read_contract.search_term_rows)
    blocked_claims = [
        "marnowanie budżetu na zapytaniach",
        "propozycje wykluczeń",
        "dodanie wykluczających słów kluczowych",
        "koszt pozyskania celu",
        "zwrot z reklam",
        "utrata konwersji",
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
                f"wyszukiwanych haseł: {total_clicks} kliknięć, "
                f"koszt {_format_money_micros(total_cost_micros, currency_code)}."
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
                "ngram_to_negative_keyword_change_preview",
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
                "oceny intencji, 90-dniowego odczytu bezpieczeństwa i podglądu zmian."
            ),
        )

    return AdsSearchTermNgramReadContract(
        status="blocked",
        title="Google Ads: brak n-gramów zapytań",
        summary=("WILQ nie ma wierszy wyszukiwanych haseł, więc nie może zbudować n-gramów."),
        allowed_metrics=[],
        missing_read_contracts=["search_term_view"],
        operator_review_gates=[],
        blocked_claims=["wyszukiwane hasła", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        ngram_rows=[],
        next_step="Uruchom odczyt danych Google Ads z odczytem `search_term_view`.",
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
    return [token for token in tokens if len(token) > 1 and token not in ADS_NGRAM_STOPWORDS]


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
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "dodanie wykluczających słów kluczowych",
            "marnowanie budżetu na zapytaniach",
        ],
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
    currency_code: str | None,
) -> AdsSearchTermSafetyReadContract:
    rows = _search_term_safety_rows(metric_facts)
    read_attempted = _latest_refresh_has_summary_metric(
        latest_refresh,
        "search_term_safety_row_count",
    )
    blocked_claims = [
        "dodanie wykluczających słów kluczowych",
        "marnowanie budżetu na zapytaniach",
        "utrata konwersji",
        "koszt pozyskania celu",
        "zwrot z reklam",
    ]
    if rows or read_attempted:
        total_clicks = sum(row.clicks_90d or 0 for row in rows)
        total_impressions = sum(row.impressions_90d or 0 for row in rows)
        total_cost_micros = sum(row.cost_micros_90d or 0 for row in rows)
        total_conversions = sum(row.conversions_90d or 0 for row in rows)
        total_conversion_value = sum(row.conversion_value_90d or 0 for row in rows)
        return AdsSearchTermSafetyReadContract(
            status="ready",
            title="Google Ads: 90-dniowy odczyt bezpieczeństwa zapytań",
            summary=(
                f"WILQ ma 90-dniowy odczyt bezpieczeństwa dla {len(rows)} zapytań: "
                f"{total_clicks} kliknięć, {total_impressions} wyświetleń, "
                f"koszt {_format_money_micros(total_cost_micros, currency_code)}, "
                f"{_format_float(total_conversions)} konwersji, "
                f"wartość konwersji {_format_float(total_conversion_value)}."
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
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids)
            or _refresh_or_connector_evidence_ids(latest_refresh),
            safety_rows=rows,
            next_step=(
                "Użyj 90-dniowego odczytu jako hamulca bezpieczeństwa. Jeśli termin "
                "ma konwersje w 90 dniach, nie kwalifikuj go do wykluczenia; jeśli "
                "nie ma konwersji, nadal wymagaj oceny intencji, kontekstu dopasowań "
                "i podglądu zmian."
            ),
        )

    return AdsSearchTermSafetyReadContract(
        status="blocked",
        title="Google Ads: brak 90-dniowego odczytu bezpieczeństwa",
        summary="WILQ nie ma jeszcze 90-dniowego odczytu listy wyszukiwanych haseł.",
        allowed_metrics=[],
        missing_read_contracts=[
            "search_term_90d_read",
            "keyword match context",
            "negative_keyword_change_preview",
        ],
        blocked_claims=["90-dniowa kontrola bezpieczeństwa wykluczeń", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        safety_rows=[],
        next_step=(
            "Uruchom 90-dniowy odczyt wyszukiwanych haseł w Google Ads. Nie twórz "
            "wykluczeń bez tego hamulca bezpieczeństwa."
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
        impressions_90d=_int_metric_value(facts_by_name.get("search_term_90d_impressions")),
        cost_micros_90d=_int_metric_value(facts_by_name.get("search_term_90d_cost_micros")),
        conversions_90d=_float_metric_value(facts_by_name.get("search_term_90d_conversions")),
        conversion_value_90d=_float_metric_value(
            facts_by_name.get("search_term_90d_conversion_value")
        ),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=[
            "koszt pozyskania celu",
            "zwrot z reklam",
            "dodanie wykluczających słów kluczowych",
            "zmarnowany budżet",
        ],
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
        "dodanie wykluczających słów kluczowych",
        "marnowanie budżetu na zapytaniach",
        "utrata konwersji",
        "koszt pozyskania celu",
        "zwrot z reklam",
    ]
    if rows or read_attempted:
        match_type_labels = _unique(
            _ads_keyword_match_type_label(row.match_type) for row in rows if row.match_type
        )
        return AdsKeywordMatchContextReadContract(
            status="ready",
            title="Google Ads: kontekst dopasowań słów kluczowych",
            summary=(
                f"WILQ ma kontekst {len(rows)} istniejących słów kluczowych "
                "z typami dopasowania: "
                f"{', '.join(match_type_labels) if match_type_labels else 'brak wierszy'}."
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
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids)
            or _refresh_or_connector_evidence_ids(latest_refresh),
            context_rows=rows,
            next_step=(
                "Użyj tego jako kontekstu review: sprawdź, które istniejące "
                "słowa kluczowe i typy dopasowań mogły wywołać wyszukiwane hasło. Nie traktuj "
                "tego jako zgody na dodanie wykluczających słów kluczowych."
            ),
        )

    return AdsKeywordMatchContextReadContract(
        status="blocked",
        title="Google Ads: brak kontekstu dopasowań słów kluczowych",
        summary="WILQ nie ma jeszcze odczytu istniejących słów kluczowych i typów dopasowania.",
        allowed_metrics=[],
        missing_read_contracts=["keyword_match_context_read"],
        blocked_claims=["keyword match context", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        context_rows=[],
        next_step=(
            "Uruchom odczyt kontekstu słów kluczowych w Google Ads. Nie zapisuj "
            "wykluczeń bez sprawdzenia, które istniejące słowa i typy dopasowania "
            "mogły wywołać wyszukiwane hasło."
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
        blocked_claims=[
            "dodanie wykluczających słów kluczowych",
            "marnowanie budżetu na zapytaniach",
            "zmarnowany budżet",
        ],
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
        return f"Wyszukiwane hasła: {campaign_name}"
    return f"Segment z wyszukiwanych haseł {index}"


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
                "kontroli bezpieczeństwa i akcji do sprawdzenia."
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
            "Twarda ocena wymaga wyszukiwanych haseł, kosztu, konwersji i 90-dniowej kontroli "
            "ochronnej przed wykluczeniami. WILQ nie może z tego tworzyć propozycji "
            "wykluczających słów kluczowych bez kompletnych dowodów."
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
        fact for row in search_term_ngram_read_contract.ngram_rows for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_search_term_ngrams",
        title="N-gramy zapytań Google Ads",
        status=search_term_ngram_read_contract.status,
        summary=search_term_ngram_read_contract.summary,
        diagnosis=(
            "N-gramy kondensują powtarzające się tematy w wyszukiwanych hasłach. "
            "To pomaga szybciej znaleźć obszary do ręcznej oceny, ale nie jest "
            "oceną straty budżetu ani gotową zmianą wykluczeń."
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
        fact for row in search_term_safety_read_contract.safety_rows for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_search_term_safety",
        title="90-dniowy odczyt bezpieczeństwa zapytań",
        status=search_term_safety_read_contract.status,
        summary=search_term_safety_read_contract.summary,
        diagnosis=(
            "Ten kontrakt chroni przed pochopnym wykluczeniem zapytań. "
            "WILQ sprawdza dłuższe okno, ale nadal blokuje zapis zmian bez intencji, "
            "kontekstu dopasowania i podglądu zmian."
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
        title="Kontekst dopasowań słów kluczowych",
        status=keyword_match_context_read_contract.status,
        summary=keyword_match_context_read_contract.summary,
        diagnosis=(
            "Ten kontrakt pokazuje istniejące słowa kluczowe i typy dopasowań w Google Ads. "
            "Pomaga zrozumieć, skąd mogło przyjść wyszukiwane hasło, ale nie jest zgodą "
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
        "rozmiar odbiorców",
        "prognoza",
        "wzrost konwersji",
        "zwrot z reklam",
        "zapis kierowania reklam",
        "skuteczność kampanii",
    ]
    if rows:
        max_searches = max((row.avg_monthly_searches or 0 for row in rows), default=0)
        return AdsKeywordPlannerReadContract(
            status="ready",
            title="Keyword Planner: wzbogacenie segmentów",
            summary=(
                f"WILQ ma {len(rows)} pomysłów Keyword Planner dla haseł źródłowych z Ads. "
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
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            idea_rows=rows,
            next_step=(
                "Użyj wzbogacenia jako dodatkowego kontekstu przy segmentach. "
                "Nie traktuj go jako prognozy, rozmiaru odbiorców ani zgody na zapis zmian."
            ),
        )
    if read_attempted or latest_status == "blocked":
        return AdsKeywordPlannerReadContract(
            status="blocked",
            title="Keyword Planner: wzbogacenie zablokowane",
            summary=(
                "Odczyt Keyword Plannera został podjęty, ale dostęp do propozycji "
                "jest nadal zablokowany po stronie Google Ads."
            ),
            missing_read_contracts=["keyword_planner_enrichment"],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            idea_rows=[],
            next_step=(
                "Zostaw segmenty w trybie oceny haseł źródłowych. Nie dopowiadaj "
                "zasięgu ani prognozy bez faktów z Keyword Planner."
            ),
        )
    return AdsKeywordPlannerReadContract(
        status="blocked",
        title="Keyword Planner: brak wzbogacenia",
        summary="WILQ nie ma jeszcze danych wzbogacających z Keyword Plannera.",
        missing_read_contracts=["keyword_planner_enrichment"],
        blocked_claims=blocked_claims,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        idea_rows=[],
        next_step=(
            "Uruchom odczyt danych Google Ads z Keyword Planner albo zostaw "
            "segmenty jako przygotowanie do oceny haseł źródłowych."
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
        _keyword_planner_idea_row(idea_text, facts) for idea_text, facts in grouped_facts.items()
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
        competition_index=_int_metric_value(facts_by_name.get("keyword_planner_competition_index")),
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
            "rozmiar odbiorców",
            "prognoza",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
        ],
    )


def _keyword_planner_section(
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
) -> AdsDiagnosticSection:
    metric_facts = [
        fact for row in keyword_planner_read_contract.idea_rows for fact in row.metric_facts
    ]
    return AdsDiagnosticSection(
        id="ads_keyword_planner",
        title="Wzbogacenie Keyword Planner",
        status=keyword_planner_read_contract.status,
        summary=keyword_planner_read_contract.summary,
        diagnosis=(
            "Ten kontrakt wzbogaca hasła źródłowe o pomysły i historyczne metryki "
            "Keyword Planner. Nie jest prognozą, rozmiarem odbiorców ani zgodą na "
            "zapis kierowania reklam."
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
    return [action_id for action_id in action_ids if action_id == KEYWORD_PLANNER_ACCESS_ACTION_ID]


def _custom_segments_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
    action_ids: list[str],
) -> AdsCustomSegmentsReadContract:
    if not search_terms_read_contract.search_term_rows:
        return AdsCustomSegmentsReadContract(
            status="blocked",
            title="Segmenty z wyszukiwanych haseł",
            summary=("Brak wierszy wyszukiwanych haseł do zbudowania propozycji segmentów."),
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=search_terms_read_contract.evidence_ids,
            missing_read_contracts=[
                "search_term_view",
                "keyword_planner_enrichment",
                "custom_segment_change_preview",
            ],
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Najpierw zbierz fakty Google Ads o wyszukiwanych hasłach. Nie wymyślaj "
                "haseł odbiorców bez haseł źródłowych i identyfikatorów dowodów."
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
            title="Segmenty z wyszukiwanych haseł",
            summary=(
                "Wiersze wyszukiwanych haseł istnieją, ale wszystkie terminy zostały odrzucone "
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
                "custom_segment_change_preview",
            ],
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Zbierz więcej realnych haseł źródłowych albo użyj dowodów Keyword Planner; "
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
    audience_forecast_read_contract = _custom_segment_audience_forecast_read_contract(candidates)
    missing_read_contracts = ["forecast_or_audience_size"]
    if keyword_planner_read_contract.status != "ready":
        missing_read_contracts.insert(0, "keyword_planner_enrichment")
    return AdsCustomSegmentsReadContract(
        status="ready",
        title="Segmenty z realnych wyszukiwanych haseł",
        summary=(
            f"WILQ ma {_custom_segment_candidate_count_label(len(candidates))} i "
            f"{source_terms_count} haseł źródłowych z dowodów Google Ads, "
            f"{_custom_segment_keyword_planner_count_label(keyword_planner_idea_count)} i "
            f"{_custom_segment_preview_count_label(len(payload_preview))}."
        ),
        candidates=candidates,
        payload_preview=payload_preview,
        audience_forecast_read_contract=audience_forecast_read_contract,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
        missing_read_contracts=missing_read_contracts,
        operator_review_gates=CUSTOM_SEGMENT_OPERATOR_REVIEW_GATES,
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        action_ids=custom_segment_action_ids,
        next_step=(
            "Przejrzyj hasła źródłowe i podgląd zmian, odrzuć nietrafione frazy, "
            "użyj wzbogacenia Keyword Planner, jeśli jest dostępne, i sprawdź w WILQ "
            "akcję przed zapisem zmian."
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
                "Brak dowodów WILQ dla prognozy albo rozmiaru odbiorców tego "
                "segmentu. Propozycja zostaje tylko do przygotowania i oceny."
            ),
            evidence_ids=candidate.evidence_ids,
            blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        )
        for candidate in candidates
    ]
    return AdsCustomSegmentAudienceForecastReadContract(
        status="blocked",
        title="Prognoza i rozmiar odbiorców segmentów",
        summary=(
            f"WILQ sprawdził {_custom_segment_candidate_count_label(len(candidates))}, ale "
            "nie ma dowodów prognozy ani rozmiaru odbiorców. Segmenty można tylko "
            "przygotować do oceny."
        ),
        checked_candidate_count=len(candidates),
        forecast_row_count=len(forecast_rows),
        forecast_rows=forecast_rows,
        missing_read_contracts=["forecast_or_audience_size"],
        operator_review_gates=["forecast_or_audience_size", "human_confirm_before_apply"],
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
        next_step=(
            "Nie oceniaj zasięgu ani skuteczności segmentu. Najpierw dostarcz "
            "dowody prognozy albo rozmiaru odbiorców i dopiero potem wróć do "
            "kierowania reklam."
        ),
    )


def _custom_segment_candidate_count_label(count: int) -> str:
    if count == 1:
        return "1 segment do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} segmenty do sprawdzenia"
    return f"{count} segmentów do sprawdzenia"


def _custom_segment_preview_count_label(count: int) -> str:
    if count == 1:
        return "1 podgląd zmian do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} podglądy zmian do sprawdzenia"
    return f"{count} podglądów zmian do sprawdzenia"


def _custom_segment_keyword_planner_count_label(count: int) -> str:
    if count == 0:
        return "brak pomysłów Keyword Planner"
    if count == 1:
        return "1 pomysł Keyword Planner"
    if 2 <= count <= 4:
        return f"{count} pomysły Keyword Planner"
    return f"{count} pomysłów Keyword Planner"


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
            rejected_by_group.setdefault(group_key, []).append((row.search_term, rejection_reason))
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
        rejection_reasons = _unique(f"{term}: {reason}" for term, reason in rejected_pairs)
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
            *(fact for idea in matched_keyword_planner_ideas for fact in idea.metric_facts),
        ][:28]
        payload_preview = _custom_segment_change_preview(
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
                intent="zainteresowanie z wyszukiwanych haseł",
                review_priority=_custom_segment_review_priority(review_score),
                review_score=review_score,
                review_reason=_custom_segment_review_reason(
                    source_terms=source_terms,
                    rows=sorted_rows,
                    rejected_terms=rejected_terms,
                ),
                human_review_gates=[
                    "sprawdź intencję haseł źródłowych",
                    "odrzuć brand, konkurencję i frazy o niskiej intencji",
                    (
                        "sprawdź wzbogacenie Keyword Planner"
                        if has_keyword_planner
                        else "dodaj wzbogacenie Keyword Planner"
                    ),
                    "sprawdź prognozę albo rozmiar odbiorców",
                    "zatwierdź segment przed zapisem zmian",
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
                    "Użyj tych terminów jako materiału do przygotowania segmentu. Podgląd zmian "
                    "jest do sprawdzenia; przed zapisem zmian wymagaj prognozy, rozmiaru "
                    "odbiorców i sprawdzenia w WILQ."
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
        f"{len(source_terms)} haseł źródłowych, {total_clicks} kliknięć, "
        f"wyświetlenia {_search_term_impressions_review_value(rows)}, "
        f"koszt {_search_term_cost_review_value(rows)}, "
        f"{_format_float(float(total_conversions))} konwersji, "
        f"{len(_unique(rejected_terms))} odrzuconych terminów. "
        "To jest kolejność oceny segmentu, nie dowód rozmiaru odbiorców, kierowania "
        "reklam ani wpływu na kampanię."
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
        rejection_reasons=dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
    )


def _search_term_impressions_review_value(rows: list[AdsSearchTermMetricRow]) -> str:
    if not any(row.impressions is not None for row in rows):
        return "niepotwierdzone"
    return str(sum(row.impressions or 0 for row in rows))


def _search_term_cost_review_value(rows: list[AdsSearchTermMetricRow]) -> str:
    if not any(row.cost_micros is not None for row in rows):
        return "niepotwierdzony"
    return _format_micros(sum(row.cost_micros or 0 for row in rows)) or "0"


def _custom_segment_change_preview(
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
        member_type_label="słowa kluczowe",
        source_terms=[term for term in source_terms if term in row_terms],
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        reason=(
            "Podgląd zmian do sprawdzenia dla segmentu Google Ads opartego na hasłach "
            "z realnych wyszukiwanych haseł. To nie jest gotowy zapis zmian ani targetowanie."
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
                    "Do sprawdzenia: podgląd kampanii, do której można wrócić po "
                    "sprawdzenia segmentu. To nie jest targetowanie ani mutacja Ads."
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
        title="Segmenty z wyszukiwanych haseł",
        status=custom_segments_read_contract.status,
        summary=custom_segments_read_contract.summary,
        diagnosis=(
            "WILQ może przygotować akcji do sprawdzenia segmentów tylko z realnych "
            "haseł źródłowych. Wzbogacenie Keyword Planner jest dodatkowym kontekstem, "
            "ale rozmiar odbiorców i skuteczność pozostają zablokowane bez osobnych "
            "danych."
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
            title="Ocena wykluczeń z wyszukiwanych haseł",
            summary="Brak wierszy wyszukiwanych haseł do kolejki oceny wykluczeń.",
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
                "Najpierw zbierz fakty Google Ads z `search_term_view`. Nie twórz "
                "wykluczeń bez wyszukiwanych haseł, kontekstu dopasowania i kontroli "
                "bezpieczeństwa."
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
            title="Ocena wykluczeń z wyszukiwanych haseł",
            summary=(
                "Wiersze wyszukiwanych haseł istnieją, ale WILQ nie znalazł terminów z kosztem lub "
                "kliknięciami i zerową konwersją w bieżących dowodach."
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
                "Kontynuuj ocenę wyszukiwanych haseł bez zapisu zmian. Nie twórz "
                "propozycji wykluczeń, jeśli bieżące dowody nie pokazują zerowej "
                "konwersji."
            ),
        )

    missing_read_contracts = (
        [] if keyword_match_context_read_contract.status == "ready" else ["keyword match context"]
    )
    if any(candidate.safety_status != "read_ready_needs_human_review" for candidate in candidates):
        missing_read_contracts.insert(1, "90_day_safety_check")

    return AdsNegativeKeywordsReadContract(
        status="ready",
        title="Ocena wykluczeń z wyszukiwanych haseł",
        summary=(
            f"WILQ ma {len(candidates)} terminów do oceny: mają koszt lub kliknięcia, "
            "zero konwersji w bieżących dowodach i są sprawdzone przez dostępny "
            "90-dniowy odczyt, jeśli WILQ ma pasujący wiersz."
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
            "Przejrzyj propozycje do sprawdzenia. Przed jakimkolwiek zapisem "
            "zmian wymagaj kontekstu dopasowania, podglądu zmian i sprawdzenia "
            "w WILQ."
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
        payload_preview = _negative_keyword_change_preview(row, safety_row)
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
                    "porównaj z istniejącymi słowami kluczowymi i typami dopasowania",
                    "sprawdź 90-dniowy odczyt bezpieczeństwa",
                    "zatwierdź poziom wykluczenia przed zapisem zmian",
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
                conversion_value_90d=(safety_row.conversion_value_90d if safety_row else None),
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
                    "negative_keyword_change_preview",
                    "human_confirm_before_apply",
                ],
                safety_status=safety_status,
                validation_status="pending_validation",
                blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
                next_step=(
                    "Sprawdź intencję terminu, istniejące słowa kluczowe, typy dopasowań i "
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
    safety_conversions_value = safety_row.conversions_90d if safety_row is not None else 0
    safety_conversions = _format_float(float(safety_conversions_value or 0))
    safety_part = (
        f"90 dni: {safety_row.clicks_90d or 0} kliknięć, koszt {safety_cost or '0'}, "
        f"{safety_conversions} konwersji"
        if safety_row is not None
        else "brak dopasowanego 90-dniowego odczytu bezpieczeństwa"
    )
    context_part = (
        f"{len(keyword_context_rows)} wierszy kontekstu dopasowań słów kluczowych"
        if keyword_context_rows
        else "brak kontekstu dopasowań słów kluczowych dla tej grupy"
    )
    return (
        f"Bieżący odczyt: {row.clicks or 0} kliknięć, koszt {current_cost or '0'}, "
        f"{current_conversions} konwersji; {safety_part}; {context_part}. "
        "To jest kolejność oceny, nie ocena zmarnowanego budżetu."
    )


def _negative_keyword_change_preview(
    row: AdsSearchTermMetricRow,
    safety_row: AdsSearchTermSafetyRow | None,
) -> AdsNegativeKeywordPayloadPreview:
    safety_evidence_ids = safety_row.evidence_ids if safety_row else []
    evidence_ids = _unique([*row.evidence_ids, *safety_evidence_ids])
    safety_metric_names = [fact.name for fact in safety_row.metric_facts] if safety_row else []
    source_metric_names = _unique([*(fact.name for fact in row.metric_facts), *safety_metric_names])
    level: Literal["ad_group", "campaign_review_required"] = (
        "ad_group" if row.ad_group_id else "campaign_review_required"
    )
    reason = (
        "Podgląd oceny dokładnego wykluczenia zbudowany z 30-dniowych wyszukiwanych haseł "
        "i 90-dniowego odczytu bezpieczeństwa. To nie jest gotowa mutacja API."
    )
    if level == "campaign_review_required":
        reason = (
            "Brak ad_group_id w dowodach, więc WILQ pokazuje tylko podgląd oceny "
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
        title="Ocena wykluczeń z wyszukiwanych haseł",
        status=negative_keywords_read_contract.status,
        summary=negative_keywords_read_contract.summary,
        diagnosis=(
            "WILQ może przygotować tylko kolejkę oceny. Zero konwersji w bieżących "
            "dowodach nie jest jeszcze dowodem przepalonego budżetu ani zgodą na wykluczenie."
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
    if blocked_handoff is not None:
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
                    "Nie podejmuj decyzji budżetowych bez brakujących danych."
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
                title="Ustal kolejność oceny kampanii Ads",
                summary=campaign_triage_read_contract.summary,
                rationale=(
                    "Ta kolejka łączy kampanie, wskaźniki, tempo wydawania budżetu, rekomendacje "
                    "i udział w wyświetleniach w jeden widok decyzyjny. WILQ pokazuje, "
                    "co sprawdzić najpierw, ale nadal blokuje ocenę strat budżetu, "
                    "opłacalności, zapis zmian budżetu i zapis rekomendacji."
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
                "Użyj kontekstu biznesowego w ocenie Ads"
                if business_context_read_contract.status == "ready"
                else "Uzupełnij kontekst biznesowy przed decyzjami Ads"
            ),
            summary=business_context_read_contract.summary,
            rationale=(
                "Google Ads pokazuje koszt, kliknięcia, konwersje i część wskaźników. "
                "WILQ używa lokalnego kontraktu z marżą, celem biznesowym, "
                "celem budżetu oraz docelowym zwrotem z reklam albo kosztem "
                "pozyskania celu jako kontekstu oceny, ale "
                "nadal blokuje zapis zmian i twarde oceny bez pełnych danych "
                "tempa wydawania budżetu, historii zmian, rekomendacji i audytu."
                if business_context_read_contract.status == "ready"
                else (
                    "Google Ads pokazuje koszt, kliknięcia, konwersje i część wskaźników, ale "
                    "nie zna marży, celu sprzedażowego ani intencji budżetu Ekologus. "
                    "WILQ musi mieć ten kontekst jako zatwierdzony kontrakt, zanim nazwie coś "
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
                title="Sprawdź wyliczone wskaźniki kampanii bez decyzji budżetowych",
                summary=derived_kpi_read_contract.summary,
                rationale=(
                    "Koszt pozyskania celu i zwrot z reklam są tu wartościami "
                    "obliczonymi z kosztu, konwersji "
                    "i wartości konwersji w bieżących dowodach Google Ads. WILQ nadal "
                    "blokuje wniosek o rentowności, stracie budżetu, "
                    "skalowaniu budżetu i zapisie zmian."
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
                    "budżetowego i walidowanego podglądu zmian."
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
                title="Przejrzyj rekomendacje Google Ads bez zapisu zmian",
                summary=recommendations_read_contract.summary,
                rationale=(
                    "Rekomendacje Google Ads są sygnałem do kontroli, nie "
                    "automatyczną strategią. WILQ pokazuje typ rekomendacji i "
                    "powiązanie z kampanią/budżetem, ale blokuje akceptację i zapis zmian bez "
                    "strategii, oceny zgodności Google Ads, potwierdzenia i audytu."
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
                    "ale blokuje skalowanie budżetu i obietnice o marnowaniu budżetu bez "
                    "historii zmian, celu biznesowego i podglądu zmian."
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

    if change_history_read_contract.status == "ready" or change_history_read_contract.evidence_ids:
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
                status="ready",
                title=(
                    "Sprawdź historię zmian Google Ads"
                    if has_change_rows
                    else "Historia zmian: brak zdarzeń w ostatnich 14 dniach"
                ),
                summary=change_history_read_contract.summary,
                rationale=(
                    "Historia zmian mówi, co ostatnio zmieniano w koncie. Jeśli "
                    "Google Ads nie zwrócił żadnych zdarzeń, sam odczyt jest "
                    "poprawny, ale nie wolno przypisywać wyników kampanii do zmian. "
                    "Jeśli zdarzenia istnieją, WILQ nadal blokuje obietnice o wpływie "
                    "zmian na wynik bez porównania przed/po i sprawdzenia przez człowieka."
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
                    "wystarcza do obietnic o marnowaniu budżetu ani do zapisu wykluczeń."
                ),
                next_step=(
                    "Przejrzyj zapytania z najwyższym kosztem. Jeśli chcesz wykluczenia, "
                    "najpierw dodaj kontekst dopasowania, 90-dniową kontrolę bezpieczeństwa i "
                    "akcję tylko do przygotowania."
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
            fact for row in search_term_ngram_read_contract.ngram_rows for fact in row.metric_facts
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
                    "N-gramy pokazują, które słowa i frazy powtarzają się w wyszukiwanych "
                    "hasłach oraz jaki mają koszt, kliknięcia i konwersje w dowodach. "
                    "To skraca ocenę, ale nadal wymaga ręcznego sprawdzenia intencji "
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
                missing_read_contracts=(search_term_ngram_read_contract.missing_read_contracts),
                operator_review_gates=(search_term_ngram_read_contract.operator_review_gates),
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
                    "WILQ ma oddzielny 90-dniowy odczyt wyszukiwanych haseł jako hamulec "
                    "bezpieczeństwa. To nadal nie jest rekomendacja wykluczeń: "
                    "brakuje kontekstu dopasowania, intencji i podglądu zmian."
                ),
                next_step=search_term_safety_read_contract.next_step,
                allowed_metrics=search_term_safety_read_contract.allowed_metrics,
                missing_read_contracts=(search_term_safety_read_contract.missing_read_contracts),
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
                title="Przejrzyj akcji do sprawdzenia wykluczeń tylko w trybie bezpieczeństwa",
                summary=negative_keywords_read_contract.summary,
                rationale=(
                    "WILQ widzi terminy z kosztem lub kliknięciami i zerową konwersją "
                    "w bieżących dowodach oraz podgląd zmian do sprawdzenia. To jest "
                    "sygnał do oceny, nie dowód straty budżetu ani zgoda na automatyczne "
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
                negative_keyword_payload_preview=(negative_keywords_read_contract.payload_preview),
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
                title="Przygotuj segmenty z realnych wyszukiwanych haseł",
                summary=custom_segments_read_contract.summary,
                rationale=(
                    "WILQ ma hasła źródłowe z dowodów Google Ads, więc może przygotować "
                    "propozycje segmentów. To nie jest zapis zmian ani obietnica "
                    "skuteczności: podgląd zmian jest do sprawdzenia, a prognoza, "
                    "rozmiar odbiorców i zgoda człowieka nadal są wymagane."
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
                operator_review_gates=(custom_segments_read_contract.operator_review_gates),
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
                title="Zapis zmian Ads wymaga osobnego sprawdzenia akcji",
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

    return [_with_ads_decision_lineage(decision, currency_code) for decision in decisions]


def _campaign_review_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == CAMPAIGN_REVIEW_ACTION_ID]


def _business_context_action_ids(action_ids: list[str]) -> list[str]:
    allowed_ids = {
        ADS_BUSINESS_CONTEXT_ACTION_ID,
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    }
    return [action_id for action_id in action_ids if action_id in allowed_ids]


def _recommendation_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == RECOMMENDATION_REVIEW_ACTION_ID]


def _change_history_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == CHANGE_HISTORY_IMPACT_ACTION_ID]


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
    evidence_ids = _unique(
        evidence_id for section in sections for evidence_id in section.evidence_ids
    )
    blocked_claims = _unique(claim for section in sections for claim in section.blocked_claims)
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


def _with_ads_decision_lineage(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> AdsDecisionItem:
    knowledge_card_ids, expert_rule_ids = ADS_DECISION_LINEAGE.get(decision.id, ([], []))
    return decision.model_copy(
        update={
            "priority": _ads_decision_priority(decision),
            "metric_tiles": _ads_decision_metric_tiles(decision, currency_code),
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


def _ads_decision_metric_tiles(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> dict[str, int | float | str]:
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
            "koszt": _format_money_micros(
                _sum_attr(decision.campaign_rows, "cost_micros"),
                currency_code,
            ),
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
            1 for row in decision.campaign_triage_rows if row.has_budget_apply_preview
        ) + sum(1 for row in decision.campaign_triage_rows if row.has_recommendation_apply_preview)
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
                "warunki sprawdzenia": len(decision.operator_review_gates),
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
            "wiersze kosztu pozyskania celu": rows_with_cpa,
            "wiersze zwrotu z reklam": rows_with_roas,
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
            tiles["w celu"] = rows_within_target
        if rows_outside_target:
            tiles["poza celem"] = rows_outside_target
        if rows_with_spend_without_conversions:
            tiles["koszt bez konw."] = rows_with_spend_without_conversions
        return _clean_metric_tiles(tiles)
    if decision.decision_type == "review_budget_context":
        budget_tiles: dict[str, int | float | str | None] = {
            "budżety": len(decision.budget_rows),
            "podgląd budżetu": len(decision.budget_apply_preview),
            "koszt 7 dni": _format_money_micros(
                _sum_attr(decision.budget_rows, "cost_micros_7d"),
                currency_code,
            ),
        }
        if decision.shared_budget_distribution_rows:
            budget_tiles["wspólne budżety"] = len(decision.shared_budget_distribution_rows)
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
            ngram_tiles["top koszt"] = _format_money_micros(
                max_cost_micros,
                currency_code,
            )
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
                "koszt": _format_money_micros(
                    _sum_attr(decision.search_term_rows, "cost_micros"),
                    currency_code,
                ),
            }
        )
    if decision.decision_type == "review_search_term_safety":
        return _clean_metric_tiles(
            {
                "90 dni": len(decision.search_term_safety_rows),
                "kliknięcia": _sum_attr(decision.search_term_safety_rows, "clicks_90d"),
                "koszt": _format_money_micros(
                    _sum_attr(decision.search_term_safety_rows, "cost_micros_90d"),
                    currency_code,
                ),
            }
        )
    if decision.decision_type == "review_negative_keyword_safety":
        return _clean_metric_tiles(
            {
                "propozycje": len(decision.negative_keyword_candidates),
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
                "akcje do sprawdzenia": len(decision.action_ids),
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


def _format_money_micros(value: float | None, currency_code: str | None) -> str | None:
    formatted_value = _format_micros(value)
    if formatted_value is None:
        return None
    if formatted_value.endswith(".0"):
        formatted_value = formatted_value[:-2]
    if not currency_code:
        return formatted_value
    return f"{formatted_value} {currency_code}"


def _format_ratio_percent(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{_round_metric(value * 100)}%"


def _strategy_review_label(status: str) -> str:
    labels = {
        "missing": "ocena strategii nieprzeprowadzona",
        "approved_for_prepare": "zatwierdzone",
        "needs_changes": "wymaga poprawek",
        "rejected": "odrzucone",
        "deferred": "odłożone",
    }
    return labels.get(status, "status oceny strategii do sprawdzenia")


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
    return f"Fakty z danych: {samples}."


def _hydrate_ads_review_gate_labels(response: AdsDiagnosticsResponse) -> None:
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
        owner.operator_review_gate_labels = _ads_review_gate_labels(owner.operator_review_gates)
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
        owner.human_review_gate_labels = _ads_review_gate_labels(owner.human_review_gates)
        if hasattr(owner, "human_review_gate_summary_label"):
            owner.human_review_gate_summary_label = required_validation_count_label(
                owner.human_review_gate_labels or owner.human_review_gates
            )


def _hydrate_ads_marketer_labels(response: AdsDiagnosticsResponse) -> None:
    currency_code = response.account_currency_read_contract.currency_code
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
    response.operator_summary.missing_read_contract_labels = _ads_missing_read_contract_labels(
        response.operator_summary.missing_read_contracts
    )
    response.operator_summary.missing_read_contract_summary_label = missing_contract_count_label(
        response.operator_summary.missing_read_contracts
    )
    response.operator_summary.allowed_metric_labels = _ads_allowed_metric_labels(
        response.operator_summary.allowed_metrics
    )
    response.operator_summary.blocked_claim_labels = _unique(
        response.operator_summary.blocked_claims
    )
    response.operator_summary.blocked_claim_summary_label = blocked_claim_count_label(
        response.operator_summary.blocked_claim_labels or response.operator_summary.blocked_claims
    )
    response.operator_summary.top_blocked_claim_labels = _unique(
        response.operator_summary.top_blocked_claim_labels
        or response.operator_summary.blocked_claim_labels
    )[:5]
    response.operator_summary.top_blocked_claim_summary_label = blocked_claim_count_label(
        response.operator_summary.top_blocked_claim_labels
    )
    response.decision_queue = [
        decision.model_copy(
            update={
                "status_label": _ads_status_label(decision.status),
                "decision_type_label": _ads_decision_type_label(decision.decision_type),
                "priority_label": _ads_priority_label(decision.priority),
                "start_here_summary": _ads_decision_start_here_summary(
                    decision,
                    currency_code,
                ),
                "measurement_plan": _ads_decision_measurement_plan(decision),
                "risk_label": _ads_risk_label(decision.risk),
                "source_connector_labels": source_connector_labels(decision.source_connectors),
                "evidence_summary_label": evidence_count_label(decision.evidence_ids),
                "action_summary_label": action_count_label(decision.action_ids),
                "missing_read_contract_labels": _ads_missing_read_contract_labels(
                    decision.missing_read_contracts
                ),
                "missing_read_contract_summary_label": missing_contract_count_label(
                    decision.missing_read_contracts
                ),
                "blocked_claim_labels": _unique(decision.blocked_claims),
                "blocked_claim_summary_label": blocked_claim_count_label(
                    _unique(decision.blocked_claims)
                ),
                "operator_review_gate_summary_label": required_validation_count_label(
                    decision.operator_review_gate_labels or decision.operator_review_gates
                ),
            }
        )
        for decision in response.decision_queue
    ]
    response.sections = [
        section.model_copy(
            update={
                "status_label": _ads_status_label(section.status),
                "source_connector_labels": source_connector_labels(section.source_connectors),
                "evidence_summary_label": evidence_count_label(section.evidence_ids),
                "action_summary_label": action_count_label(section.action_ids),
                "blocked_claim_labels": _unique(section.blocked_claims),
            }
        )
        for section in response.sections
    ]
    if response.blocked_handoff is not None:
        response.blocked_handoff = response.blocked_handoff.model_copy(
            update={
                "status_label": _ads_status_label(response.blocked_handoff.status),
                "source_connector_labels": source_connector_labels(
                    response.blocked_handoff.source_connectors
                ),
                "evidence_summary_label": evidence_count_label(
                    response.blocked_handoff.evidence_ids
                ),
                "action_summary_label": action_count_label(response.blocked_handoff.action_ids),
                "blocked_claim_labels": _unique(response.blocked_handoff.blocked_claims),
            }
        )
    _hydrate_optimizer_readiness_marketer_labels(response.optimizer_readiness_contract)
    _hydrate_custom_segments_marketer_labels(response.custom_segments_read_contract)
    _hydrate_business_context_marketer_labels(response.business_context_read_contract)
    _hydrate_campaign_triage_marketer_labels(response.campaign_triage_read_contract)
    for row in response.derived_kpi_read_contract.kpi_rows:
        row.blocked_claim_labels = _unique(row.blocked_claims)
        row.blocked_claim_summary_label = blocked_claim_count_label(
            row.blocked_claim_labels or row.blocked_claims
        )
    _hydrate_budget_pacing_marketer_labels(
        response.budget_pacing_read_contract,
        currency_code,
    )
    _hydrate_recommendations_marketer_labels(response.recommendations_read_contract)
    _hydrate_impression_share_marketer_labels(response.impression_share_read_contract)
    _hydrate_change_history_marketer_labels(response.change_history_read_contract)
    _hydrate_change_impact_marketer_labels(response.change_impact_readiness_contract)
    response.search_term_review_summary_contract.blocked_claim_labels = _unique(
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


def _hydrate_campaign_triage_marketer_labels(
    contract: AdsCampaignTriageReadContract,
) -> None:
    contract.action_summary_label = action_count_label(contract.action_ids)
    for row in contract.triage_rows:
        row.campaign_status_label = _ads_campaign_status_label(row.campaign_status)
        row.advertising_channel_type_label = _ads_channel_type_label(row.advertising_channel_type)
        row.missing_read_contract_labels = _ads_missing_read_contract_labels(
            row.missing_read_contracts
        )
        row.blocked_claim_labels = _unique(row.blocked_claims)
        row.action_summary_label = action_count_label(row.action_ids)


def _hydrate_budget_pacing_marketer_labels(
    contract: AdsBudgetPacingReadContract,
    currency_code: str | None,
) -> None:
    for preview in contract.payload_preview:
        _hydrate_budget_payload_preview_labels(preview)
    for row in contract.budget_rows:
        row.campaign_status_label = _ads_campaign_status_label(row.campaign_status)
        row.advertising_channel_type_label = _ads_channel_type_label(row.advertising_channel_type)
        row.budget_period_label = _ads_budget_period_label(row.budget_period)
        row.budget_status_label = _ads_campaign_status_label(row.budget_status)
        row.blocked_claim_labels = _unique(row.blocked_claims)
        row.blocked_claim_summary_label = blocked_claim_count_label(
            row.blocked_claim_labels or row.blocked_claims
        )
        if row.payload_preview is not None:
            _hydrate_budget_payload_preview_labels(row.payload_preview)
            row.preview_card = _budget_preview_card(row.payload_preview, currency_code)
    for shared_budget_row in contract.shared_budget_distribution_rows:
        shared_budget_row.blocked_claim_labels = _unique(shared_budget_row.blocked_claims)
        shared_budget_row.blocked_claim_summary_label = blocked_claim_count_label(
            shared_budget_row.blocked_claim_labels or shared_budget_row.blocked_claims
        )
        for share in shared_budget_row.campaign_shares:
            share.campaign_status_label = _ads_campaign_status_label(share.campaign_status)
            share.advertising_channel_type_label = _ads_channel_type_label(
                share.advertising_channel_type
            )


def _hydrate_budget_payload_preview_labels(preview: AdsBudgetApplyPreview) -> None:
    preview.operation_type_label = _ads_google_operation_label(preview.operation_type)
    preview.required_validation_labels = _ads_review_gate_labels(preview.required_validation)
    preview.blocked_claim_labels = _unique(preview.blocked_claims)
    safety_review = preview.safety_review
    safety_review.status_label = _ads_status_label(safety_review.status)
    safety_review.missing_requirement_labels = _ads_missing_read_contract_labels(
        safety_review.missing_requirements
    )
    safety_review.required_validation_labels = _ads_review_gate_labels(
        safety_review.required_validation
    )
    safety_review.blocked_claim_labels = _unique(safety_review.blocked_claims)


def _ads_preview_card_id(kind: str, source_id: str) -> str:
    digest = hashlib.sha256(source_id.encode("utf-8")).digest()
    suffix = "".join(chr(ord("a") + byte % 26) for byte in digest[:8])
    return f"{kind}_card_{suffix}"


def _ads_preview_row(label: str, value: str) -> ActionPreviewRowViewModel:
    return ActionPreviewRowViewModel(label=label, value=value)


def _budget_preview_card(
    preview: AdsBudgetApplyPreview,
    currency_code: str | None,
) -> ActionPreviewCardViewModel:
    rows = [
        _ads_preview_row(
            "Budżet teraz",
            _format_money_micros(
                preview.current_budget_amount_micros,
                currency_code,
            )
            or "brak kwoty obecnego budżetu w odczycie Google Ads",
        ),
        _ads_preview_row(
            "Propozycja do sprawdzenia",
            _format_money_micros(
                preview.proposed_budget_amount_micros,
                currency_code,
            )
            or "brak proponowanej kwoty; WILQ blokuje zapis budżetu",
        ),
        _ads_preview_row(
            "Operacja",
            preview.operation_type_label or "zmiana budżetu do sprawdzenia",
        ),
    ]
    if preview.campaign_id or preview.campaign_budget_id:
        rows.append(
            _ads_preview_row(
                "Powiązanie",
                "kampania albo budżet do sprawdzenia w szczegółach technicznych",
            )
        )
    if preview.required_validation_labels:
        rows.append(
            _ads_preview_row(
                "Warunki sprawdzenia",
                ", ".join(preview.required_validation_labels[:4]),
            )
        )
    missing_requirements = preview.safety_review.missing_requirement_labels
    if missing_requirements:
        rows.append(
            _ads_preview_row("Braki bezpieczeństwa", ", ".join(missing_requirements[:4]))
        )
    if preview.blocked_claim_labels:
        rows.append(
            _ads_preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(preview.blocked_claim_labels[:4]),
            )
        )
    return ActionPreviewCardViewModel(
        id=_ads_preview_card_id("google_ads_budget_review", preview.id),
        kind="google_ads_budget_review",
        title_label="Budżet kampanii do sprawdzenia",
        subtitle_label="ocena budżetu bez zapisu zmian",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=(
            "możliwy zapis po sprawdzeniu" if preview.apply_allowed else "zapis zmian zablokowany"
        ),
        system_readiness_label=(
            "system gotowy do zapisu" if preview.api_mutation_ready else "wymaga kontroli"
        ),
    )


def _hydrate_recommendations_marketer_labels(
    contract: AdsRecommendationsReadContract,
) -> None:
    for row in contract.recommendation_rows:
        row.recommendation_type_label = _ads_recommendation_type_label(row.recommendation_type)
        row.blocked_claim_labels = _unique(row.blocked_claims)
        if row.payload_preview is not None:
            _hydrate_recommendation_payload_preview_labels(row.payload_preview)
            row.preview_card = _recommendation_preview_card(row.payload_preview)
    for preview in contract.payload_preview:
        _hydrate_recommendation_payload_preview_labels(preview)


def _hydrate_recommendation_payload_preview_labels(
    preview: AdsRecommendationApplyPreview,
) -> None:
    preview.recommendation_type_label = _ads_recommendation_type_label(preview.recommendation_type)
    preview.operation_type_label = _ads_google_operation_label(preview.operation_type)
    preview.required_validation_labels = _ads_review_gate_labels(preview.required_validation)
    preview.blocked_claim_labels = _unique(preview.blocked_claims)


def _recommendation_preview_card(
    preview: AdsRecommendationApplyPreview,
) -> ActionPreviewCardViewModel:
    rows = [
        _ads_preview_row(
            "Rekomendacja",
            preview.recommendation_type_label or "rekomendacja do sprawdzenia",
        ),
        _ads_preview_row(
            "Operacja",
            preview.operation_type_label or "operacja do sprawdzenia",
        ),
    ]
    if preview.campaign_id or preview.campaign_budget_id:
        rows.append(
            _ads_preview_row(
                "Powiązanie",
                "kampania albo budżet do sprawdzenia w szczegółach technicznych",
            )
        )
    if preview.required_validation_labels:
        rows.append(
            _ads_preview_row(
                "Warunki sprawdzenia",
                ", ".join(preview.required_validation_labels[:4]),
            )
        )
    if preview.blocked_claim_labels:
        rows.append(
            _ads_preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(preview.blocked_claim_labels[:4]),
            )
        )
    return ActionPreviewCardViewModel(
        id=_ads_preview_card_id("google_ads_recommendation_review", preview.id),
        kind="google_ads_recommendation_review",
        title_label="Rekomendacja Google Ads do sprawdzenia",
        subtitle_label="ocena rekomendacji bez zapisu zmian",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=(
            "możliwy zapis po sprawdzeniu" if preview.apply_allowed else "zapis zmian zablokowany"
        ),
        system_readiness_label=(
            "system gotowy do zapisu" if preview.api_mutation_ready else "wymaga kontroli"
        ),
    )


def _hydrate_impression_share_marketer_labels(
    contract: AdsImpressionShareReadContract,
) -> None:
    for row in contract.impression_share_rows:
        row.campaign_status_label = _ads_campaign_status_label(row.campaign_status)
        row.advertising_channel_type_label = _ads_channel_type_label(row.advertising_channel_type)
        row.blocked_claim_labels = _unique(row.blocked_claims)
        row.blocked_claim_summary_label = blocked_claim_count_label(
            row.blocked_claim_labels or row.blocked_claims
        )


def _hydrate_change_history_marketer_labels(
    contract: AdsChangeHistoryReadContract,
) -> None:
    contract.status_label = _ads_status_label(contract.status)
    contract.allowed_metric_labels = _ads_allowed_metric_labels(contract.allowed_metrics)
    contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        contract.missing_read_contracts
    )
    contract.blocked_claim_labels = _unique(contract.blocked_claims)
    for row in contract.change_history_rows:
        row.change_resource_type_label = _ads_change_resource_type_label(row.change_resource_type)
        row.resource_change_operation_label = _ads_resource_change_operation_label(
            row.resource_change_operation
        )
        row.client_type_label = _ads_client_type_label(row.client_type)
        row.changed_field_labels = _ads_changed_field_labels(row.changed_fields)
        row.changed_field_summary_label = (
            ", ".join(row.changed_field_labels[:4])
            if row.changed_field_labels
            else f"{row.changed_field_count or 0} pól"
        )
        row.blocked_claim_labels = _unique(row.blocked_claims)


def _hydrate_change_impact_marketer_labels(
    contract: AdsChangeImpactReadinessContract,
) -> None:
    contract.status_label = _ads_status_label(contract.status)
    contract.allowed_metric_labels = _ads_allowed_metric_labels(contract.allowed_metrics)
    contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        contract.missing_read_contracts
    )
    contract.blocked_claim_labels = _unique(contract.blocked_claims)
    contract.action_summary_label = action_count_label(contract.action_ids)
    for row in contract.readiness_rows:
        row.changed_field_labels = _ads_changed_field_labels(row.changed_fields)
        row.missing_read_contract_labels = _ads_missing_read_contract_labels(
            row.missing_read_contracts
        )
        row.blocked_claim_labels = _unique(row.blocked_claims)


def _hydrate_negative_keywords_marketer_labels(
    contract: AdsNegativeKeywordsReadContract,
) -> None:
    contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        contract.missing_read_contracts
    )
    contract.missing_read_contract_summary_label = missing_contract_count_label(
        contract.missing_read_contracts
    )
    contract.blocked_claim_labels = _unique(contract.blocked_claims)
    contract.blocked_claim_summary_label = blocked_claim_count_label(
        contract.blocked_claim_labels or contract.blocked_claims
    )
    for candidate in contract.candidates:
        candidate.required_check_labels = _ads_review_gate_labels(candidate.required_checks)
        candidate.safety_status_label = _ads_negative_keyword_safety_status_label(
            candidate.safety_status
        )
        candidate.validation_status_label = _ads_validation_status_label(
            candidate.validation_status
        )
        candidate.blocked_claim_labels = _unique(candidate.blocked_claims)
        for row in candidate.keyword_context_rows:
            _hydrate_keyword_match_context_row_labels(row)
        if candidate.payload_preview is not None:
            _hydrate_negative_keyword_payload_preview_labels(candidate.payload_preview)
            candidate.preview_card = _negative_keyword_preview_card(candidate.payload_preview)
    for preview in contract.payload_preview:
        _hydrate_negative_keyword_payload_preview_labels(preview)


def _hydrate_negative_keyword_payload_preview_labels(
    preview: AdsNegativeKeywordPayloadPreview,
) -> None:
    preview.match_type_label = _ads_keyword_match_type_label(preview.match_type)
    preview.level_label = _ads_negative_keyword_level_label(preview.level)
    preview.required_validation_labels = _ads_review_gate_labels(preview.required_validation)
    preview.blocked_claim_labels = _unique(preview.blocked_claims)


def _negative_keyword_preview_card(
    preview: AdsNegativeKeywordPayloadPreview,
) -> ActionPreviewCardViewModel:
    rows = [
        _ads_preview_row("Hasło", preview.search_term),
        _ads_preview_row("Wykluczenie", preview.negative_keyword_text),
        _ads_preview_row("Dopasowanie", preview.match_type_label or "dopasowanie do sprawdzenia"),
        _ads_preview_row("Poziom", preview.level_label or "poziom do sprawdzenia"),
        _ads_preview_row("Kampania", preview.campaign_label or "kampania do sprawdzenia"),
        _ads_preview_row("Grupa reklam", preview.ad_group_label or "grupa reklam do sprawdzenia"),
    ]
    if preview.required_validation_labels:
        rows.append(
            _ads_preview_row(
                "Warunki sprawdzenia",
                ", ".join(preview.required_validation_labels[:4]),
            )
        )
    if preview.blocked_claim_labels:
        rows.append(
            _ads_preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(preview.blocked_claim_labels[:4]),
            )
        )
    return ActionPreviewCardViewModel(
        id=_ads_preview_card_id("google_ads_negative_keyword_review", preview.id),
        kind="google_ads_negative_keyword_review",
        title_label="Wykluczenie słowa do sprawdzenia",
        subtitle_label="ocena intencji zapytania bez zapisu zmian",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=(
            "możliwy zapis po sprawdzeniu" if preview.apply_allowed else "zapis zmian zablokowany"
        ),
        system_readiness_label=(
            "system gotowy do zapisu" if preview.api_mutation_ready else "wymaga kontroli"
        ),
    )


def _hydrate_keyword_match_context_marketer_labels(
    contract: AdsKeywordMatchContextReadContract,
) -> None:
    for row in contract.context_rows:
        _hydrate_keyword_match_context_row_labels(row)


def _hydrate_keyword_match_context_row_labels(row: AdsKeywordMatchContextRow) -> None:
    row.match_type_label = _ads_keyword_match_type_label(row.match_type)
    row.criterion_status_label = _ads_keyword_criterion_status_label(row.criterion_status)
    row.negative_label = "wykluczające" if row.negative else "aktywne"


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
    readiness.blocked_claim_labels = _unique(readiness.blocked_claims)
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
    contract.blocked_claim_labels = _unique(contract.blocked_claims)
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
        item.blocked_claim_labels = _unique(item.blocked_claims)


def _hydrate_custom_segments_marketer_labels(
    contract: AdsCustomSegmentsReadContract,
) -> None:
    contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        contract.missing_read_contracts
    )
    contract.blocked_claim_labels = _unique(contract.blocked_claims)
    forecast_contract = contract.audience_forecast_read_contract
    forecast_contract.missing_read_contract_labels = _ads_missing_read_contract_labels(
        forecast_contract.missing_read_contracts
    )
    forecast_contract.blocked_claim_labels = _unique(forecast_contract.blocked_claims)

    for candidate in contract.candidates:
        candidate.confidence_label = _ads_confidence_label(candidate.confidence)
        candidate.validation_status_label = _ads_validation_status_label(
            candidate.validation_status
        )
        candidate.blocked_claim_labels = _unique(candidate.blocked_claims)
        candidate.source_quality.rejection_reason_labels = {
            _custom_segment_rejection_reason_label(reason): count
            for reason, count in candidate.source_quality.rejection_reasons.items()
        }
        if candidate.payload_preview is not None:
            _hydrate_custom_segment_payload_preview_labels(candidate.payload_preview)
            candidate.preview_card = _custom_segment_preview_card(candidate.payload_preview)

    for preview in contract.payload_preview:
        _hydrate_custom_segment_payload_preview_labels(preview)

    for row in forecast_contract.forecast_rows:
        row.blocked_claim_labels = _unique(row.blocked_claims)


def _custom_segment_preview_card(
    preview: AdsCustomSegmentPayloadPreview,
) -> ActionPreviewCardViewModel:
    targeting_preview = preview.targeting_preview[0] if preview.targeting_preview else None
    safety_review = preview.safety_review
    rows = [
        _ads_preview_row("Nazwa", preview.custom_segment_name),
        _ads_preview_row(
            "Typ odbiorców",
            preview.member_type_label or "typ odbiorców do sprawdzenia",
        ),
        _ads_preview_row(
            "Hasła źródłowe",
            ", ".join(preview.source_terms[:4]) if preview.source_terms else "brak haseł",
        ),
        _ads_preview_row(
            "Kampania do sprawdzenia",
            (
                targeting_preview.campaign_name
                if targeting_preview is not None and targeting_preview.campaign_name
                else "kampania do sprawdzenia"
            ),
        ),
        _ads_preview_row("Bezpieczeństwo", safety_review.status_label or "wymaga sprawdzenia"),
    ]
    if safety_review.missing_requirement_labels:
        rows.append(
            _ads_preview_row("Braki", ", ".join(safety_review.missing_requirement_labels[:4]))
        )
    if preview.required_validation_labels:
        rows.append(
            _ads_preview_row(
                "Warunki sprawdzenia",
                ", ".join(preview.required_validation_labels[:4]),
            )
        )
    if preview.blocked_claim_labels:
        rows.append(
            _ads_preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(preview.blocked_claim_labels[:4]),
            )
        )
    return ActionPreviewCardViewModel(
        id=_ads_preview_card_id("google_ads_custom_segment_review", preview.id),
        kind="google_ads_custom_segment_review",
        title_label="Segment odbiorców do sprawdzenia",
        subtitle_label="ocena segmentu bez zapisu zmian",
        status_label="zapis zmian zablokowany",
        rows=rows,
        apply_state_label=(
            "możliwy zapis po sprawdzeniu" if preview.apply_allowed else "zapis zmian zablokowany"
        ),
        system_readiness_label=(
            "system gotowy do zapisu" if preview.api_mutation_ready else "wymaga kontroli"
        ),
    )


def _hydrate_custom_segment_payload_preview_labels(
    preview: AdsCustomSegmentPayloadPreview,
) -> None:
    preview.required_validation_labels = _ads_review_gate_labels(preview.required_validation)
    preview.blocked_claim_labels = _unique(preview.blocked_claims)
    safety_review = preview.safety_review
    safety_review.status_label = _ads_status_label(safety_review.status)
    safety_review.missing_requirement_labels = _ads_missing_read_contract_labels(
        safety_review.missing_requirements
    )
    safety_review.required_validation_labels = _ads_review_gate_labels(
        safety_review.required_validation
    )
    safety_review.blocked_claim_labels = _unique(safety_review.blocked_claims)
    for target in preview.targeting_preview:
        target.required_validation_labels = _ads_review_gate_labels(target.required_validation)
        target.blocked_claim_labels = _unique(target.blocked_claims)


def _custom_segment_rejection_reason_label(reason: str) -> str:
    labels = {
        "brand_or_generic": "brand albo zbyt ogólna fraza",
        "short_or_low_signal": "za krótka fraza albo za słaby sygnał",
        "no_click_or_conversion_signal": "brak kliknięć albo sygnału celu",
    }
    return labels.get(reason, "odrzucona fraza do sprawdzenia")


def _ads_review_gate_labels(gates: Iterable[object]) -> list[str]:
    return [
        ADS_REVIEW_GATE_LABELS.get(str(gate), "sprawdzenie przez operatora")
        for gate in gates
        if str(gate)
    ]


def _ads_business_use_labels(values: Iterable[object]) -> list[str]:
    labels = {
        "campaign_review_context": "kontekst oceny kampanii",
        "budget_review_context": "kontekst oceny budżetu",
        "human_strategy_review_context": "kontekst strategii człowieka",
        "margin_context": "kontekst marży",
        "business_goal_alignment": "dopasowanie do celu biznesowego",
        "budget_goal_guardrail": "zasada bezpieczeństwa celu budżetu",
        "target_roas_review_context": "kontekst docelowego zwrotu z reklam",
        "target_cpa_review_context": "kontekst docelowego kosztu pozyskania celu",
        "target_roas_review": "ocena docelowego zwrotu z reklam",
        "target_cpa_review": "ocena docelowego kosztu pozyskania celu",
        "profitability_verdict": "ocena opłacalności",
        "target_kpi_verdict": "ocena wskaźników względem celu",
        "budget_scaling": "skalowanie budżetu",
        "budget_apply": "zmiana budżetu",
        "recommendation_apply": "zapis rekomendacji",
        "wasted_budget_claim": "wniosek o zmarnowanym budżecie",
        "automatic_scaling": "automatyczne skalowanie",
        "profitability_verdict_without_value_model_review": (
            "ocena opłacalności bez sprawdzenia modelu wartości"
        ),
    }
    return [
        labels.get(str(value), "zastosowanie biznesowe do sprawdzenia")
        for value in values
        if str(value)
    ]


def _ads_strategy_review_status_label(status: object) -> str:
    labels = {
        "missing": "ocena strategii niepotwierdzona",
        "approved_for_prepare": "zatwierdzone do przygotowania",
        "needs_changes": "wymaga zmian",
        "rejected": "odrzucone",
        "deferred": "odroczone",
    }
    value = str(status)
    return labels.get(value, "status oceny strategii do sprawdzenia")


def _ads_campaign_status_label(status: object | None) -> str:
    if status is None or str(status) == "":
        return "status kampanii niepotwierdzony"
    labels = {
        "ENABLED": "aktywna",
        "PAUSED": "wstrzymana",
        "REMOVED": "usunięta",
        "UNKNOWN": "status nieznany",
        "UNSPECIFIED": "status nieokreślony",
    }
    value = str(status)
    return labels.get(value, "status kampanii do sprawdzenia")


def _ads_channel_type_label(channel_type: object | None) -> str:
    if channel_type is None or str(channel_type) == "":
        return "typ kampanii niepotwierdzony"
    labels = {
        "SEARCH": "sieć wyszukiwania",
        "PERFORMANCE_MAX": "Performance Max",
        "SHOPPING": "Zakupy Google",
        "DISPLAY": "sieć reklamowa",
        "DEMAND_GEN": "Demand Gen",
        "VIDEO": "wideo",
        "LOCAL": "lokalna",
        "SMART": "Smart",
        "UNKNOWN": "kanał nieznany",
        "UNSPECIFIED": "kanał nieokreślony",
    }
    value = str(channel_type)
    return labels.get(value, "kanał kampanii do sprawdzenia")


def _ads_budget_period_label(period: object | None) -> str:
    if period is None or str(period) == "":
        return "okres budżetu niepotwierdzony"
    labels = {
        "DAILY": "dzienny",
        "CUSTOM_PERIOD": "niestandardowy okres",
        "FIXED_DAILY": "stały dzienny",
        "UNKNOWN": "okres nieznany",
        "UNSPECIFIED": "okres nieokreślony",
    }
    value = str(period)
    return labels.get(value, "okres budżetu do sprawdzenia")


def _ads_google_operation_label(operation_type: object) -> str:
    labels = {
        "CampaignBudgetOperation": "zmiana budżetu kampanii",
        "ApplyRecommendationOperation": "zastosowanie rekomendacji Google Ads",
    }
    value = str(operation_type)
    return labels.get(value, "operacja Google Ads do sprawdzenia")


def _ads_recommendation_type_label(recommendation_type: object) -> str:
    labels = {
        "CAMPAIGN_BUDGET": "budżet kampanii",
        "KEYWORD": "słowa kluczowe",
        "RESPONSIVE_SEARCH_AD": "elastyczna reklama w wyszukiwarce",
        "TARGET_CPA_OPT_IN": "strategia kosztu pozyskania celu",
        "TARGET_ROAS_OPT_IN": "strategia zwrotu z reklam",
        "MAXIMIZE_CONVERSIONS_OPT_IN": "maksymalizacja konwersji",
        "MAXIMIZE_CONVERSION_VALUE_OPT_IN": "maksymalizacja wartości konwersji",
        "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH": "jakość zasobów Performance Max",
        "DISPLAY_EXPANSION_OPT_IN": "rozszerzenie kampanii na sieć reklamową",
        "DYNAMIC_IMAGE_EXTENSION_OPT_IN": "dynamiczne rozszerzenia graficzne",
        "SEARCH_PARTNERS_OPT_IN": "rozszerzenie kampanii na partnerów wyszukiwania",
        "UNKNOWN": "typ rekomendacji nieznany",
        "UNSPECIFIED": "typ rekomendacji nieokreślony",
    }
    value = str(recommendation_type)
    return labels.get(value, "typ rekomendacji do sprawdzenia")


def _ads_change_resource_type_label(value: object | None) -> str:
    if value is None or str(value) == "":
        return "typ zasobu zmiany niepotwierdzony"
    labels = {
        "CAMPAIGN": "kampania",
        "CAMPAIGN_BUDGET": "budżet kampanii",
        "AD_GROUP": "grupa reklam",
        "AD_GROUP_AD": "reklama w grupie reklam",
        "AD_GROUP_CRITERION": "kryterium grupy reklam",
        "CAMPAIGN_CRITERION": "kryterium kampanii",
        "ASSET": "zasób reklamy",
        "CUSTOMER": "konto Google Ads",
        "UNKNOWN": "typ zasobu nieznany",
        "UNSPECIFIED": "typ zasobu nieokreślony",
    }
    text = str(value)
    return labels.get(text, "typ zasobu Google Ads do sprawdzenia")


def _ads_resource_change_operation_label(value: object | None) -> str:
    if value is None or str(value) == "":
        return "operacja zmiany niepotwierdzona"
    labels = {
        "CREATE": "utworzenie",
        "UPDATE": "zmiana",
        "REMOVE": "usunięcie",
        "UNKNOWN": "operacja nieznana",
        "UNSPECIFIED": "operacja nieokreślona",
    }
    text = str(value)
    return labels.get(text, "typ zmiany Google Ads do sprawdzenia")


def _ads_client_type_label(value: object | None) -> str:
    if value is None or str(value) == "":
        return "źródło zmiany niepotwierdzone"
    labels = {
        "GOOGLE_ADS_WEB_CLIENT": "panel Google Ads",
        "GOOGLE_ADS_API": "Google Ads API",
        "GOOGLE_ADS_EDITOR": "Google Ads Editor",
        "GOOGLE_ADS_MOBILE_APP": "aplikacja Google Ads",
        "UNKNOWN": "źródło zmiany nieznane",
        "UNSPECIFIED": "źródło zmiany nieokreślone",
    }
    text = str(value)
    return labels.get(text, "źródło zmiany Google Ads do sprawdzenia")


def _ads_changed_field_labels(fields: Iterable[object]) -> list[str]:
    labels = {
        "campaign.status": "status kampanii",
        "campaign.name": "nazwa kampanii",
        "campaign_budget.amount_micros": "kwota budżetu kampanii",
        "campaign_budget.delivery_method": "sposób wydawania budżetu",
        "campaign.target_roas.target_roas": "docelowy zwrot z reklam",
        "campaign.target_cpa.target_cpa_micros": "docelowy koszt pozyskania celu",
        "ad_group.status": "status grupy reklam",
        "ad_group_ad.status": "status reklamy",
        "ad_group_criterion.status": "status słowa kluczowego",
        "ad_group_criterion.keyword.match_type": "typ dopasowania słowa kluczowego",
        "ad_group_criterion.negative": "wykluczenie słowa kluczowego",
    }
    result: list[str] = []
    for field in fields:
        text = str(field)
        if not text:
            continue
        result.append(labels.get(text, "pole zmiany Google Ads do sprawdzenia"))
    return result


def _ads_allowed_metric_labels(metrics: Iterable[object]) -> list[str]:
    labels = {
        "change_event_available": "historia zmian dostępna",
        "change_event_changed_field_count": "liczba zmienionych pól",
        "current_campaign_clicks": "bieżące kliknięcia kampanii",
        "current_campaign_impressions": "bieżące wyświetlenia kampanii",
        "current_campaign_cost_micros": "bieżący koszt kampanii",
        "current_campaign_conversions": "bieżące konwersje kampanii",
        "current_campaign_conversion_value": "bieżąca wartość konwersji kampanii",
    }
    return [
        labels.get(str(metric), "metryka Google Ads do sprawdzenia")
        for metric in metrics
        if str(metric)
    ]


def _ads_confidence_label(confidence: object) -> str:
    labels = {
        "low": "niska",
        "medium": "średnia",
        "high": "wysoka",
    }
    value = str(confidence)
    return labels.get(value, "pewność do sprawdzenia")


def _ads_validation_status_label(status: object) -> str:
    labels = {
        "pending_validation": "do sprawdzenia",
        "blocked": "zablokowane",
    }
    value = str(status)
    return labels.get(value, "status sprawdzenia do sprawdzenia")


def _ads_negative_keyword_safety_status_label(status: object) -> str:
    labels = {
        "needs_90_day_review": "wymaga 90-dniowej kontroli",
        "read_ready_needs_human_review": "90-dniowy odczyt gotowy",
        "blocked": "zablokowane",
    }
    value = str(status)
    return labels.get(value, "status bezpieczeństwa wykluczenia do sprawdzenia")


def _ads_negative_keyword_level_label(level: object) -> str:
    labels = {
        "ad_group": "grupa reklam",
        "campaign_review_required": "poziom do decyzji człowieka",
    }
    value = str(level)
    return labels.get(value, "poziom wykluczenia do sprawdzenia")


def _ads_keyword_match_type_label(match_type: object) -> str:
    labels = {
        "EXACT": "dopasowanie ścisłe",
        "PHRASE": "dopasowanie do wyrażenia",
        "BROAD": "dopasowanie przybliżone",
        "UNKNOWN": "typ dopasowania nieznany",
        "UNSPECIFIED": "typ dopasowania nieokreślony",
    }
    value = str(match_type)
    return labels.get(value, "typ dopasowania słowa do sprawdzenia")


def _ads_keyword_criterion_status_label(status: object | None) -> str:
    labels = {
        "ENABLED": "aktywne",
        "PAUSED": "wstrzymane",
        "REMOVED": "usunięte",
        "UNKNOWN": "status nieznany",
        "UNSPECIFIED": "status nieokreślony",
    }
    if status is None or str(status) == "":
        return "status słowa niepotwierdzony"
    value = str(status)
    return labels.get(value, "status słowa do sprawdzenia")


def _ads_optimizer_mode_label(mode: object) -> str:
    labels = {
        "review_only": "ocena bez zapisu",
    }
    value = str(mode)
    return labels.get(value, "tryb pracy Google Ads do sprawdzenia")


def _ads_optimizer_status_label(status: object) -> str:
    labels = {
        "review_ready": "gotowe do oceny",
        "blocked": "zablokowane",
    }
    value = str(status)
    return labels.get(value, "status optymalizacji do sprawdzenia")


def _ads_optimizer_readiness_item_label(item_id: object) -> str:
    labels = {
        "campaign_review_queue": "kampanie do oceny",
        "budget_and_recommendation_review": "budżety i rekomendacje",
        "search_terms_review_queue": "wyszukiwane hasła",
        "negative_keyword_review_queue": "wykluczenia do oceny",
        "custom_segments_review_queue": "segmenty niestandardowe",
        "keyword_planner_enrichment": "Keyword Planner",
        "change_history_impact_review": "historia zmian",
        "ads_apply_safety_gate": "bramka zapisu zmian",
    }
    value = str(item_id)
    return labels.get(value, "element gotowości Google Ads do sprawdzenia")


def _ads_missing_read_contract_labels(contracts: Iterable[object]) -> list[str]:
    labels = {
        "recommendations": "rekomendacje Google Ads",
        "recommendation_impact_preview": "podgląd wpływu rekomendacji",
        "recommendation_apply_preview": "podgląd zapisu rekomendacji",
        "human_strategy_review": "ocena strategii przez człowieka",
        "approved_human_strategy_review": "zatwierdzona ocena strategii",
        "change_history": "historia zmian",
        "budget_pacing": "tempo wydawania budżetu",
        "campaign_budget": "budżet kampanii",
        "recommended_budget_missing": "brak rekomendowanego budżetu z Google Ads",
        "shared_budget_distribution": "podział wspólnego budżetu",
        "budget_target_or_seasonality": "cel budżetowy albo sezonowość",
        "business_goal": "cel biznesowy",
        "target_roas_or_cpa": "docelowy zwrot z reklam albo koszt pozyskania celu",
        "profit_margin": "marża albo model rentowności",
        "human_budget_goal": "cel budżetu od człowieka",
        "account_currency": "waluta konta",
        "pre_change_performance_window": "wyniki sprzed zmiany",
        "post_change_performance_window": "wyniki po zmianie",
        "human_change_impact_review": "ręczna ocena wpływu zmian",
        "apply_preview": "podgląd zmian",
        "change_event_rows": "zdarzenia historii zmian",
        "current_campaign_snapshot": "bieżący odczyt kampanii",
        "impression_share": "udział w wyświetleniach",
        "keyword match context": "kontekst dopasowania słów kluczowych",
        "keyword_match_context_read": "odczyt słów kluczowych i typów dopasowania",
        "90_day_safety_check": "90-dniowa kontrola bezpieczeństwa",
        "search_term_90d_read": "90-dniowy odczyt zapytań",
        "human_intent_review": "ręczna ocena intencji",
        "negative_keyword_change_preview": "podgląd zmian wykluczeń",
        "ngram_to_negative_keyword_change_preview": ("podgląd zmian wykluczeń z tematów zapytań"),
        "review_search_term_context": "sprawdzenie intencji zapytania",
        "check_existing_keywords_and_match_types": ("sprawdzenie słów i typów dopasowania"),
        "human_confirm_before_apply": "potwierdzenie człowieka przed zapisem",
        "google_ads_mutation_audit": "sprawdzenie zapisu zmian w Google Ads",
        "mutation_audit": "audyt zapisu zmian",
        "keyword_planner_enrichment": "wzbogacenie przez Keyword Planner",
        "forecast_or_audience_size": "prognoza albo rozmiar odbiorców",
        "campaign activity": "aktywność kampanii",
        "search_term_view": "widok zapytań użytkowników",
        "zero_conversion_search_terms": "zapytania z zerową konwersją",
    }
    return [
        labels.get(str(contract), "brakujący odczyt Ads do sprawdzenia")
        for contract in contracts
        if str(contract)
    ]


def _ads_status_label(status: object) -> str:
    value = str(status)
    labels = {
        "ready": "gotowe",
        "preliminary": "wstępne",
        "blocked": "zablokowane",
        "missing": "zakres danych Ads niepotwierdzony",
    }
    return labels.get(value, "status Google Ads do sprawdzenia")


def _ads_decision_type_label(decision_type: object) -> str:
    labels = {
        "review_campaign_activity": "aktywność kampanii",
        "review_business_context": "kontekst biznesowy",
        "review_derived_kpi": "wyliczone wskaźniki",
        "review_budget_context": "kontekst budżetu",
        "review_recommendations": "rekomendacje",
        "review_impression_share": "udział w wyświetleniach",
        "review_change_history": "historia zmian",
        "review_search_term_safety": "bezpieczeństwo zapytań",
        "review_search_terms": "wyszukiwane hasła",
        "review_search_term_ngrams": "tematy zapytań",
        "review_negative_keyword_safety": "bezpieczeństwo wykluczeń",
        "prepare_custom_segments": "segmenty odbiorców",
        "block_write_actions": "blokada zapisu zmian",
        "fix_ads_access": "naprawa dostępu",
        "review_campaign_triage": "kolejność kampanii",
    }
    value = str(decision_type)
    return labels.get(value, "typ decyzji Google Ads do sprawdzenia")


def _ads_decision_start_here_summary(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> str:
    if decision.decision_type == "review_campaign_triage":
        campaign_count = len(decision.campaign_triage_rows) or len(decision.campaign_rows)
        return (
            f"{campaign_count} kampanii w kolejce oceny. Zacznij od celu, kosztu, "
            "konwersji, budżetu i haseł."
        )
    if decision.decision_type == "review_campaign_activity":
        cost = _format_money_micros(
            sum(row.cost_micros or 0 for row in decision.campaign_rows),
            currency_code,
        )
        return (
            f"{len(decision.campaign_rows)} kampanii z odczytem aktywności. "
            f"Koszt w tej karcie: {cost or 'brak'}."
        )
    if decision.decision_type == "review_business_context":
        return (
            "Najpierw potwierdź marżę, cel biznesowy, docelowy koszt pozyskania "
            "celu i docelowy zwrot z reklam, zanim ktokolwiek nazwie wynik opłacalnym."
        )
    if decision.decision_type == "review_derived_kpi":
        return (
            f"{len(decision.derived_kpi_rows)} wierszy wskaźników do oceny. "
            "To nadal sygnał do sprawdzenia, nie ocena kosztu pozyskania celu "
            "ani zwrotu z reklam."
        )
    if decision.decision_type == "review_budget_context":
        return (
            f"{len(decision.budget_rows)} budżetów do sprawdzenia. Nie skaluj "
            "ani nie tnij budżetu bez sprawdzenia w WILQ."
        )
    if decision.decision_type == "review_search_terms":
        return (
            f"{len(decision.search_term_rows)} haseł do oceny. Zacznij od kosztu "
            "i intencji, nie od automatycznego wykluczenia."
        )
    return decision.summary


def _ads_decision_measurement_plan(decision: AdsDecisionItem) -> str:
    if decision.decision_type == "review_campaign_activity":
        return (
            "Po sprawdzeniu kampanii zapisz baseline kosztu, kliknięć, konwersji "
            "i wartości konwersji. Dopiero osobne okno pre/post oraz historia zmian "
            "pozwolą mówić o efekcie."
        )
    if decision.decision_type == "review_campaign_triage":
        return (
            "Po przejściu kolejki kampanii zapisz, które kampanie wymagają ręcznej "
            "decyzji. Efekt sprawdzimy dopiero przez porównanie przed i po, historię "
            "zmian i ponowny odczyt Ads."
        )
    if decision.decision_type == "review_search_terms":
        return (
            "Po sprawdzeniu wyszukiwanych haseł zapisz akcje do sprawdzenia i blokady. "
            "Dopiero po potwierdzonej zmianie oraz porównaniu przed i po można oceniać "
            "wpływ na koszt, konwersje lub utratę ruchu."
        )
    if decision.decision_type in {
        "review_negative_keyword_safety",
        "review_search_term_ngrams",
    }:
        return (
            "Po sprawdzeniu wykluczeń sprawdź zapytania, koszt i konwersje przed "
            "i po zmianie. Bez sprawdzenia efektu WILQ nie twierdzi, że oszczędzono "
            "budżet albo uniknięto utraty konwersji."
        )
    if decision.decision_type == "review_recommendations":
        return (
            "Po sprawdzeniu rekomendacji zapisz, które rekomendacje odrzucono albo "
            "skierowano do sprawdzenia. Efekt można ocenić dopiero po audycie zmiany "
            "i porównaniu metryk w kolejnym oknie."
        )
    return (
        "Po decyzji zapisz przegląd akcji, punkt odniesienia i sprawdzenie efektu. "
        "Brak okna pomiarowego oznacza brak twierdzenia o poprawie wyniku."
    )


def _ads_business_context_status_label(contract: AdsBusinessContextReadContract) -> str:
    if contract.status == "blocked":
        return "blokada"
    if "target_roas_or_cpa" in contract.missing_read_contracts:
        return "wstępny"
    return "gotowe"


def _ads_priority_label(priority: int) -> str:
    if priority <= 12:
        return "najpierw"
    if priority <= 25:
        return "wysoki priorytet"
    if priority <= 45:
        return "do sprawdzenia"
    return "niżej w kolejce"


def _ads_risk_label(risk: object) -> str:
    value = str(risk.value if isinstance(risk, ActionRisk) else risk)
    labels = {
        "critical": "krytyczne",
        "high": "wysokie",
        "medium": "średnie",
        "low": "niskie",
    }
    return labels.get(value, "ryzyko Google Ads do sprawdzenia")


def _ads_connector_status_label(status: str) -> str:
    labels = {
        "configured": "dostęp skonfigurowany",
        "missing_credentials": "brakuje dostępu",
        "disabled": "źródło wyłączone",
    }
    return labels.get(status, "status dostępu Google Ads do sprawdzenia")


def _ads_refresh_status_label(run: ConnectorRefreshRun | object) -> str:
    if not isinstance(run, ConnectorRefreshRun):
        return "status odczytu Google Ads do sprawdzenia"
    return connector_refresh_run_status_label(run)


def _ads_live_data_status_label(live_data_available: bool) -> str:
    return "metryki Google Ads dostępne" if live_data_available else "brak metryk Google Ads"


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
