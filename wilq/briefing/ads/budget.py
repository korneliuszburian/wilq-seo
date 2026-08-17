from __future__ import annotations

from wilq.actions.google_ads.business_context import (
    ads_float_env,
    ads_int_env,
    ads_profit_margin_env,
    ads_text_env,
)
from wilq.briefing.ads_derived_kpis import derived_kpi_row, target_triage
from wilq.briefing.ads_metric_utils import (
    format_money_micros as _format_money_micros,
)
from wilq.content.operator_copy import unique
from wilq.operator_labels import (
    blocked_claim_count_label,
)
from wilq.schemas import (
    ActionPreviewCardViewModel,
    AdsAccountCurrencyReadContract,
    AdsBudgetApplyPreview,
    AdsBudgetPacingReadContract,
    AdsBusinessContextReadContract,
    AdsCampaignMetricRow,
    AdsCampaignReadContract,
    AdsDerivedKpiReadContract,
    AdsDerivedKpiRow,
    AdsImpressionShareReadContract,
)

from .campaigns import (
    _ads_budget_period_label,
    _ads_campaign_status_label,
    _ads_channel_type_label,
    _ads_google_operation_label,
)
from .labels import (
    _ads_missing_read_contract_labels,
    _ads_review_gate_labels,
    _ads_status_label,
)
from .shared import (
    GOOGLE_ADS_CONNECTOR_ID,
    AdsTargetStatus,
    _ads_preview_card_id,
    _ads_preview_row,
    _remove_missing_contract_names,
)


def _reconcile_ads_budget_and_business_context_contracts(
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    budget_pacing_read_contract: AdsBudgetPacingReadContract,
    impression_share_read_contract: AdsImpressionShareReadContract,
    business_context_read_contract: AdsBusinessContextReadContract,
) -> tuple[
    AdsDerivedKpiReadContract,
    AdsBudgetPacingReadContract,
    AdsImpressionShareReadContract,
]:
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
    return (
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        impression_share_read_contract,
    )


def _profit_margin_env() -> tuple[float | None, str | None]:
    return ads_profit_margin_env()


def _text_env(name: str) -> tuple[str | None, str | None]:
    return ads_text_env(name)


def _float_env(name: str) -> tuple[float | None, str | None]:
    return ads_float_env(name)


def _int_env(name: str) -> tuple[int | None, str | None]:
    return ads_int_env(name)


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
            allowed_metrics=unique(allowed_metrics),
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=unique(
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
    return derived_kpi_row(
        row,
        business_context_read_contract,
        ratio=_ratio,
        difference=_difference,
        micros_to_account_units=_micros_to_account_units,
        unique=unique,
    )


def _target_triage(
    *,
    row: AdsCampaignMetricRow,
    cost_per_conversion_micros: float | None,
    roas: float | None,
    target_cpa_micros: int | None,
    target_roas: float | None,
) -> tuple[AdsTargetStatus, str, int]:
    return target_triage(
        row=row,
        cost_per_conversion_micros=cost_per_conversion_micros,
        roas=roas,
        target_cpa_micros=target_cpa_micros,
        target_roas=target_roas,
    )


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
        row.blocked_claim_labels = unique(row.blocked_claims)
        row.blocked_claim_summary_label = blocked_claim_count_label(
            row.blocked_claim_labels or row.blocked_claims
        )
        if row.payload_preview is not None:
            _hydrate_budget_payload_preview_labels(row.payload_preview)
            row.preview_card = _budget_preview_card(row.payload_preview, currency_code)
    for shared_budget_row in contract.shared_budget_distribution_rows:
        shared_budget_row.blocked_claim_labels = unique(shared_budget_row.blocked_claims)
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
    preview.blocked_claim_labels = unique(preview.blocked_claims)
    safety_review = preview.safety_review
    safety_review.status_label = _ads_status_label(safety_review.status)
    safety_review.missing_requirement_labels = _ads_missing_read_contract_labels(
        safety_review.missing_requirements
    )
    safety_review.required_validation_labels = _ads_review_gate_labels(
        safety_review.required_validation
    )
    safety_review.blocked_claim_labels = unique(safety_review.blocked_claims)


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
        rows.append(_ads_preview_row("Braki bezpieczeństwa", ", ".join(missing_requirements[:4])))
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
