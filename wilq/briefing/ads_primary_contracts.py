from __future__ import annotations

from collections.abc import Callable

from wilq.briefing.ads_budget_pacing import build_budget_pacing_read_contract
from wilq.briefing.ads_change_history import build_change_history_read_contract
from wilq.briefing.ads_impression_share import build_impression_share_read_contract
from wilq.briefing.ads_recommendations import build_recommendations_read_contract
from wilq.schemas import (
    AdsAccountCurrencyReadContract,
    AdsBudgetPacingReadContract,
    AdsBusinessContextReadContract,
    AdsCampaignReadContract,
    AdsChangeHistoryReadContract,
    AdsDerivedKpiReadContract,
    AdsImpressionShareReadContract,
    AdsRecommendationsReadContract,
    ConnectorRefreshRun,
    MetricFact,
)


def build_primary_read_contracts(
    trusted_metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
    *,
    account_currency: Callable[
        [list[MetricFact], ConnectorRefreshRun | None], AdsAccountCurrencyReadContract
    ],
    business_context: Callable[
        [ConnectorRefreshRun | None], AdsBusinessContextReadContract
    ],
    campaign: Callable[
        [
            list[MetricFact],
            ConnectorRefreshRun | None,
            AdsBusinessContextReadContract,
            str | None,
        ],
        AdsCampaignReadContract,
    ],
    derived_kpi: Callable[
        [
            AdsCampaignReadContract,
            AdsAccountCurrencyReadContract,
            AdsBusinessContextReadContract,
        ],
        AdsDerivedKpiReadContract,
    ],
    fallback_evidence_ids: Callable[[ConnectorRefreshRun | None], list[str]],
    latest_refresh_has_summary_metric: Callable[
        [ConnectorRefreshRun | None, str], bool
    ],
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
    account_currency_read_contract = account_currency(trusted_metric_facts, latest_refresh)
    business_context_read_contract = business_context(latest_refresh)
    campaign_read_contract = campaign(
        trusted_metric_facts,
        latest_refresh,
        business_context_read_contract,
        account_currency_read_contract.currency_code,
    )
    derived_kpi_read_contract = derived_kpi(
        campaign_read_contract,
        account_currency_read_contract,
        business_context_read_contract,
    )
    evidence_ids = fallback_evidence_ids(latest_refresh)
    budget_pacing_read_contract = build_budget_pacing_read_contract(
        trusted_metric_facts,
        campaign_read_contract,
        fallback_evidence_ids=evidence_ids,
    )
    recommendations_read_contract = build_recommendations_read_contract(
        trusted_metric_facts,
        read_attempted=latest_refresh_has_summary_metric(
            latest_refresh, "recommendation_row_count"
        ),
        fallback_evidence_ids=evidence_ids,
    )
    impression_share_read_contract = build_impression_share_read_contract(
        trusted_metric_facts,
        read_attempted=latest_refresh_has_summary_metric(
            latest_refresh, "impression_share_row_count"
        ),
        fallback_evidence_ids=evidence_ids,
    )
    change_history_read_contract = build_change_history_read_contract(
        trusted_metric_facts,
        read_attempted=latest_refresh_has_summary_metric(
            latest_refresh, "change_event_row_count"
        ),
        fallback_evidence_ids=evidence_ids,
    )
    return (
        account_currency_read_contract,
        business_context_read_contract,
        campaign_read_contract,
        derived_kpi_read_contract,
        budget_pacing_read_contract,
        recommendations_read_contract,
        impression_share_read_contract,
        change_history_read_contract,
    )
