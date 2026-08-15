from __future__ import annotations

from typing import Literal, cast

from wilq.briefing.ads_summary_cache import (
    clear_ads_summary_cache as _clear_ads_summary_cache,
)
from wilq.briefing.ads_summary_cache import (
    read_ads_summary_cache,
    write_ads_summary_cache,
)
from wilq.briefing.diagnostic_readiness import build_diagnostic_data_readiness
from wilq.connectors.registry import get_connector_status
from wilq.schemas import (
    ActionObject,
    AdsCustomSegmentsReadContract,
    AdsDecisionItem,
    AdsDiagnosticsResponse,
    AdsNegativeKeywordsReadContract,
    connector_refresh_has_live_data,
)

from .budget import (
    _hydrate_budget_pacing_marketer_labels,
    _reconcile_ads_budget_and_business_context_contracts,
)
from .campaigns import (
    _ads_campaign_status_label,
    _ads_change_resource_type_label,
    _ads_changed_field_labels,
    _ads_channel_type_label,
    _ads_client_type_label,
    _ads_google_operation_label,
    _ads_recommendation_type_label,
    _ads_resource_change_operation_label,
    _build_ads_campaign_optimizer_contracts,
    _hydrate_recommendations_marketer_labels,
)
from .custom_segments import (
    _compact_custom_segment_candidate,
    _custom_segment_rejection_reason_label,
    _custom_segment_review_reason,
    _custom_segment_source_quality,
)
from .labels import (
    _ads_allowed_metric_labels,
    _ads_missing_read_contract_labels,
    _ads_review_gate_labels,
    _ads_status_label,
)
from .negative_keywords import (
    _ads_keyword_criterion_status_label,
    _ads_keyword_match_type_label,
    _compact_negative_keyword_candidate,
    _hydrate_negative_keywords_marketer_labels,
)
from .operator_summary import (
    _account_currency_read_contract,
    _ads_aggregation_contract,
    _build_ads_action_enriched_contracts,
    _build_ads_decision_queue_response,
    _build_ads_diagnostics_response,
    _build_ads_primary_read_contracts,
    _build_ads_sections_and_blocked_handoff,
    _google_ads_action_ids,
    _hydrate_ads_response_labels,
    _reconcile_ads_change_history_contracts,
    _reconcile_ads_recommendation_and_impression_contracts,
)
from .operator_summary import (
    _latest_google_ads_refresh as _latest_google_ads_refresh,
)
from .search_terms import (
    _ads_metric_facts_for_view,
    _build_ads_search_term_read_contracts,
    _build_ads_search_term_review_contracts,
    _reconcile_search_term_read_contracts,
    _search_term_metric_rows,
)
from .shared import (
    ADS_METRIC_FACT_LIMIT,
    ADS_SUMMARY_VIEW_ROW_LIMIT,
    GOOGLE_ADS_CONNECTOR_ID,
    _copy_limited_model,
)


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
    latest_refresh_collected_data = latest_refresh is not None and connector_refresh_has_live_data(
        latest_refresh
    )
    trusted_metric_facts = metric_facts if latest_refresh_collected_data else []
    live_data_available = bool(trusted_metric_facts)
    data_readiness = build_diagnostic_data_readiness(
        connector=connector,
        latest_refresh=latest_refresh,
        factual_metrics=trusted_metric_facts[:12],
        factual_metric_count=len(trusted_metric_facts),
        partial=bool(
            latest_refresh and latest_refresh.quality_state.value == "partial"
        ),
        stale=connector.freshness.state == "stale",
        partial_coverage_label=(
            "Pokazane metryki obejmują tylko potwierdzony zakres odczytu Google Ads."
        ),
    )
    (
        account_currency_read_contract,
        business_context_read_contract,
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        change_history_read_contract,
    ) = _build_ads_primary_read_contracts(trusted_metric_facts, latest_refresh)
    (
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
    ) = _reconcile_ads_recommendation_and_impression_contracts(
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
    )
    (
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
    ) = _reconcile_ads_change_history_contracts(
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        change_history_read_contract,
    )
    (
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        impression_share_read_contract,
    ) = _reconcile_ads_budget_and_business_context_contracts(
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        impression_share_read_contract,
        business_context_read_contract,
    )
    (
        search_terms_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
        keyword_planner_read_contract,
    ) = _build_ads_search_term_read_contracts(
        trusted_metric_facts,
        latest_refresh,
        account_currency_read_contract.currency_code,
    )
    (
        search_terms_read_contract,
        search_term_safety_read_contract,
    ) = _reconcile_search_term_read_contracts(
        search_terms_read_contract,
        search_term_safety_read_contract,
        keyword_match_context_read_contract,
    )
    (
        search_term_review_summary_contract,
        search_term_ngram_read_contract,
    ) = _build_ads_search_term_review_contracts(
        search_terms_read_contract,
        latest_refresh,
        account_currency_read_contract.currency_code,
    )
    action_ids = _google_ads_action_ids(actions, live_data_available=live_data_available)
    (
        business_context_read_contract,
        change_history_read_contract,
        change_impact_readiness_contract,
        search_term_ngram_read_contract,
        custom_segments_read_contract,
        negative_keywords_read_contract,
    ) = _build_ads_action_enriched_contracts(
        action_ids=action_ids,
        business_context_read_contract=business_context_read_contract,
        change_history_read_contract=change_history_read_contract,
        campaign_read_contract=campaign_read_contract,
        search_term_ngram_read_contract=search_term_ngram_read_contract,
        search_terms_read_contract=search_terms_read_contract,
        search_term_safety_read_contract=search_term_safety_read_contract,
        keyword_match_context_read_contract=keyword_match_context_read_contract,
        keyword_planner_read_contract=keyword_planner_read_contract,
    )
    (
        campaign_triage_read_contract,
        optimizer_readiness_contract,
    ) = _build_ads_campaign_optimizer_contracts(
        campaign_read_contract,
        business_context_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        action_ids,
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
    sections, blocked_handoff = _build_ads_sections_and_blocked_handoff(
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
    decision_queue = _build_ads_decision_queue_response(
        campaign_read_contract=campaign_read_contract,
        business_context_read_contract=business_context_read_contract,
        derived_kpi_read_contract=derived_kpi_read_contract,
        budget_pacing_read_contract=budget_pacing_read_contract,
        recommendations_read_contract=recommendations_read_contract,
        impression_share_read_contract=impression_share_read_contract,
        campaign_triage_read_contract=campaign_triage_read_contract,
        change_history_read_contract=change_history_read_contract,
        search_terms_read_contract=search_terms_read_contract,
        search_term_ngram_read_contract=search_term_ngram_read_contract,
        search_term_safety_read_contract=search_term_safety_read_contract,
        keyword_match_context_read_contract=keyword_match_context_read_contract,
        keyword_planner_read_contract=keyword_planner_read_contract,
        custom_segments_read_contract=custom_segments_read_contract,
        negative_keywords_read_contract=negative_keywords_read_contract,
        sections=sections,
        blocked_handoff=blocked_handoff,
        action_ids=action_ids,
        currency_code=account_currency_read_contract.currency_code,
    )
    response = _build_ads_diagnostics_response(
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
    )
    response.aggregation_contract = _ads_aggregation_contract(
        view=view,
        campaign_rows_available=len(campaign_read_contract.campaign_rows),
        search_term_rows_available=len(search_terms_read_contract.search_term_rows),
        account_currency_read_contract=account_currency_read_contract,
    )
    _hydrate_ads_response_labels(response)
    if view == "summary":
        return _compact_ads_diagnostics_summary(response)
    return response


def build_ads_diagnostics_summary_cached() -> AdsDiagnosticsResponse:
    """Reuse one summary build across the initial Ads dashboard reads."""
    cached = read_ads_summary_cache()
    if cached is not None:
        return cached
    diagnostics = build_ads_diagnostics(view="summary")
    write_ads_summary_cache(diagnostics)
    return diagnostics


def clear_ads_summary_cache() -> None:
    """Compatibility facade for callers that reset the Ads summary cache."""
    _clear_ads_summary_cache()


def _prepare_ads_summary_compaction(
    response: AdsDiagnosticsResponse,
) -> tuple[list[AdsDecisionItem], AdsCustomSegmentsReadContract, AdsNegativeKeywordsReadContract]:
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
    compact_custom_segments, compact_negative_keywords = _compact_ads_candidate_contracts(response)
    return compact_decisions, compact_custom_segments, compact_negative_keywords


def _compact_ads_summary_response_fields(
    response: AdsDiagnosticsResponse,
    compact_decisions: list[AdsDecisionItem],
    compact_custom_segments: AdsCustomSegmentsReadContract,
    compact_negative_keywords: AdsNegativeKeywordsReadContract,
) -> AdsDiagnosticsResponse:
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


def _compact_ads_diagnostics_summary(
    response: AdsDiagnosticsResponse,
) -> AdsDiagnosticsResponse:
    (
        compact_decisions,
        compact_custom_segments,
        compact_negative_keywords,
    ) = _prepare_ads_summary_compaction(response)
    return _compact_ads_summary_response_fields(
        response,
        compact_decisions,
        compact_custom_segments,
        compact_negative_keywords,
    )


def _compact_ads_candidate_contracts(
    response: AdsDiagnosticsResponse,
) -> tuple[AdsCustomSegmentsReadContract, AdsNegativeKeywordsReadContract]:
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
    return compact_custom_segments, compact_negative_keywords


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


__all__ = [
    "ADS_METRIC_FACT_LIMIT",
    "_account_currency_read_contract",
    "_ads_aggregation_contract",
    "_ads_allowed_metric_labels",
    "_ads_campaign_status_label",
    "_ads_change_resource_type_label",
    "_ads_changed_field_labels",
    "_ads_channel_type_label",
    "_ads_client_type_label",
    "_ads_google_operation_label",
    "_ads_keyword_criterion_status_label",
    "_ads_keyword_match_type_label",
    "_ads_missing_read_contract_labels",
    "_ads_recommendation_type_label",
    "_ads_resource_change_operation_label",
    "_ads_review_gate_labels",
    "_ads_status_label",
    "_custom_segment_rejection_reason_label",
    "_custom_segment_review_reason",
    "_custom_segment_source_quality",
    "_hydrate_budget_pacing_marketer_labels",
    "_hydrate_negative_keywords_marketer_labels",
    "_hydrate_recommendations_marketer_labels",
    "_search_term_metric_rows",
    "build_ads_diagnostics",
    "build_ads_diagnostics_summary_cached",
    "clear_ads_summary_cache",
]
