"""Optimizer-readiness contract assembly for Google Ads diagnostics."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.schemas import (
    ActionRisk,
    AdsBudgetPacingReadContract,
    AdsCampaignTriageReadContract,
    AdsChangeHistoryReadContract,
    AdsChangeImpactReadinessContract,
    AdsCustomSegmentsReadContract,
    AdsImpressionShareReadContract,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordsReadContract,
    AdsOptimizerReadinessContract,
    AdsOptimizerReadinessItem,
    AdsRecommendationsReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _campaign_review_item(
    campaign_triage_read_contract: AdsCampaignTriageReadContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def _budget_and_recommendation_item(
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def _search_terms_item(
    search_term_review_summary_contract: AdsSearchTermReviewSummaryContract,
    search_term_ngram_read_contract: AdsSearchTermNgramReadContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def _negative_keywords_item(
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
    search_term_safety_read_contract: AdsSearchTermSafetyReadContract,
    keyword_match_context_read_contract: AdsKeywordMatchContextReadContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def _custom_segments_item(
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def _keyword_planner_item(
    keyword_planner_read_contract: AdsKeywordPlannerReadContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def _change_history_item(
    change_history_read_contract: AdsChangeHistoryReadContract,
    change_impact_readiness_contract: AdsChangeImpactReadinessContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def _apply_safety_item(
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    recommendations_read_contract: AdsRecommendationsReadContract,
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
) -> AdsOptimizerReadinessItem:
    return _optimizer_readiness_item(
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
    )

def build_optimizer_readiness_contract(
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
        _campaign_review_item(
            campaign_triage_read_contract,
        ),
        _budget_and_recommendation_item(
            budget_pacing_read_contract,
            recommendations_read_contract,
            impression_share_read_contract,
        ),
        _search_terms_item(
            search_term_review_summary_contract,
            search_term_ngram_read_contract,
        ),
        _negative_keywords_item(
            negative_keywords_read_contract,
            search_term_safety_read_contract,
            keyword_match_context_read_contract,
        ),
        _custom_segments_item(
            custom_segments_read_contract,
        ),
        _keyword_planner_item(
            keyword_planner_read_contract,
        ),
        _change_history_item(
            change_history_read_contract,
            change_impact_readiness_contract,
        ),
        _apply_safety_item(
            budget_pacing_read_contract,
            recommendations_read_contract,
            custom_segments_read_contract,
            negative_keywords_read_contract,
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
        allowed_metrics=_unique([metric for item in items for metric in item.allowed_metrics]),
        missing_read_contracts=_unique(
            [contract for item in items for contract in item.missing_read_contracts]
        ),
        operator_review_gates=_unique(
            [gate for item in items for gate in item.operator_review_gates]
        ),
        blocked_claims=_unique(
            [
                claim
                for item in items
                for claim in [
                    *item.blocked_claims,
                    "ocena kosztu pozyskania celu",
                    "werdykt zwrotu z reklam",
                    "opłacalność",
                ]
            ]
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique([evidence_id for item in items for evidence_id in item.evidence_ids]),
        action_ids=_unique([action_id for item in items for action_id in item.action_ids]),
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
