from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.actions.google_ads.campaign_review import (
    CAMPAIGN_REVIEW_ACTION_ID,
)
from wilq.actions.google_ads.change_history import CHANGE_HISTORY_IMPACT_ACTION_ID
from wilq.briefing.ads_campaign_metrics import campaign_metric_rows
from wilq.briefing.ads_campaign_optimizer_contracts import (
    build_campaign_optimizer_contracts,
)
from wilq.briefing.ads_metric_utils import (
    format_money_micros as _format_money_micros,
)
from wilq.operator_labels import (
    action_count_label,
    blocked_claim_count_label,
)
from wilq.schemas import (
    ActionPreviewCardViewModel,
    AdsBudgetPacingReadContract,
    AdsBudgetPacingRow,
    AdsBusinessContextReadContract,
    AdsCampaignMetricRow,
    AdsCampaignReadContract,
    AdsCampaignTriageReadContract,
    AdsCampaignTriageRow,
    AdsChangeHistoryReadContract,
    AdsChangeHistoryRow,
    AdsChangeImpactReadinessContract,
    AdsChangeImpactReadinessRow,
    AdsCustomSegmentsReadContract,
    AdsDerivedKpiReadContract,
    AdsDerivedKpiRow,
    AdsImpressionShareReadContract,
    AdsImpressionShareRow,
    AdsKeywordMatchContextReadContract,
    AdsKeywordPlannerReadContract,
    AdsNegativeKeywordsReadContract,
    AdsOptimizerReadinessContract,
    AdsRecommendationApplyPreview,
    AdsRecommendationRow,
    AdsRecommendationsReadContract,
    AdsSearchTermNgramReadContract,
    AdsSearchTermReviewSummaryContract,
    AdsSearchTermSafetyReadContract,
    ConnectorRefreshRun,
    MetricFact,
)

from .labels import (
    _ads_allowed_metric_labels,
    _ads_missing_read_contract_labels,
    _ads_review_gate_labels,
    _ads_status_label,
)
from .shared import (
    GOOGLE_ADS_CONNECTOR_ID,
    _ads_preview_card_id,
    _ads_preview_row,
    _float_metric_value,
    _format_float,
    _int_metric_value,
    _refresh_or_connector_evidence_ids,
    _unique,
)

ADS_RECOMMENDATION_HUMAN_REVIEW_GATE = "human_strategy_review"


def _build_ads_campaign_optimizer_contracts(
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
) -> tuple[AdsCampaignTriageReadContract, AdsOptimizerReadinessContract]:
    return build_campaign_optimizer_contracts(
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
        campaign_triage=_campaign_triage_read_contract,
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
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
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


def _campaign_metric_rows(
    metric_facts: list[MetricFact],
    business_context_read_contract: AdsBusinessContextReadContract,
) -> list[AdsCampaignMetricRow]:
    return campaign_metric_rows(
        metric_facts,
        business_context_read_contract,
        unique=_unique,
        int_metric_value=_int_metric_value,
        float_metric_value=_float_metric_value,
        row_sort_key=_campaign_row_sort_key,
    )


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


def _format_signed_number(value: int | float | None) -> str:
    if value is None:
        return "wartość niepotwierdzona"
    numeric_value = float(value)
    if numeric_value == 0:
        return "0"
    prefix = "+" if numeric_value > 0 else ""
    return f"{prefix}{_format_float(numeric_value)}"


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
    (
        source_metric_names,
        evidence_ids,
        has_budget_apply_preview,
        has_recommendation_apply_preview,
    ) = _campaign_triage_source_context(
        campaign_row=campaign_row,
        kpi_row=kpi_row,
        budget_row=budget_row,
        recommendation_rows=recommendation_rows,
        impression_share_row=impression_share_row,
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


def _campaign_triage_source_context(
    *,
    campaign_row: AdsCampaignMetricRow,
    kpi_row: AdsDerivedKpiRow | None,
    budget_row: AdsBudgetPacingRow | None,
    recommendation_rows: list[AdsRecommendationRow],
    impression_share_row: AdsImpressionShareRow | None,
) -> tuple[list[str], list[str], bool, bool]:
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
    return (
        source_metric_names,
        evidence_ids,
        bool(budget_row is not None and budget_row.payload_preview is not None),
        any(row.payload_preview is not None for row in recommendation_rows),
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


def _campaign_row_sort_key(row: AdsCampaignMetricRow) -> tuple[int, int, int, str]:
    return (
        -row.review_score,
        -(row.cost_micros or 0),
        -(row.clicks or 0),
        row.campaign_name,
    )


def _campaign_review_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == CAMPAIGN_REVIEW_ACTION_ID]


def _change_history_action_ids(action_ids: list[str]) -> list[str]:
    return [action_id for action_id in action_ids if action_id == CHANGE_HISTORY_IMPACT_ACTION_ID]


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
