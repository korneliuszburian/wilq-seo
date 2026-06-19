from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.actions.google_ads.custom_segments import (
    CUSTOM_SEGMENT_ACTION_ID,
    CUSTOM_SEGMENT_BLOCKED_CLAIMS,
)
from wilq.actions.google_ads.negative_keywords import (
    NEGATIVE_KEYWORD_ACTION_ID,
    NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
)
from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    AdsBlockedHandoff,
    AdsCampaignMetricRow,
    AdsCampaignReadContract,
    AdsCustomSegmentCandidate,
    AdsCustomSegmentsReadContract,
    AdsDecisionItem,
    AdsDerivedKpiReadContract,
    AdsDerivedKpiRow,
    AdsDiagnosticSection,
    AdsDiagnosticsResponse,
    AdsNegativeKeywordCandidate,
    AdsNegativeKeywordsReadContract,
    AdsSearchTermMetricRow,
    AdsSearchTermsReadContract,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.metric_store import metric_store

GOOGLE_ADS_CONNECTOR_ID = "google_ads"
ADS_METRIC_FACT_LIMIT = 500


def build_ads_diagnostics() -> AdsDiagnosticsResponse:
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
    campaign_read_contract = _campaign_read_contract(trusted_metric_facts, latest_refresh)
    derived_kpi_read_contract = _derived_kpi_read_contract(campaign_read_contract)
    search_terms_read_contract = _search_terms_read_contract(
        trusted_metric_facts,
        latest_refresh,
    )
    action_ids = _google_ads_action_ids(
        list_actions(),
        live_data_available=live_data_available,
    )
    custom_segments_read_contract = _custom_segments_read_contract(
        search_terms_read_contract,
        action_ids,
    )
    negative_keywords_read_contract = _negative_keywords_read_contract(
        search_terms_read_contract,
        action_ids,
    )
    sections = [
        _oauth_or_live_section(latest_refresh, trusted_metric_facts, action_ids),
        _campaign_overview_section(
            trusted_metric_facts,
            latest_refresh,
            action_ids,
            campaign_read_contract,
        ),
        _derived_kpi_section(derived_kpi_read_contract),
        _search_terms_section(search_terms_read_contract, action_ids),
        _custom_segments_section(custom_segments_read_contract),
        _negative_keywords_section(negative_keywords_read_contract),
        _safe_action_section(
            action_ids,
            latest_refresh,
            live_data_available=live_data_available,
        ),
    ]
    blocked_handoff = _blocked_handoff(live_data_available, latest_refresh, sections, action_ids)
    decision_queue = _ads_decision_queue(
        campaign_read_contract,
        derived_kpi_read_contract,
        search_terms_read_contract,
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
        derived_kpi_read_contract=derived_kpi_read_contract,
        search_terms_read_contract=search_terms_read_contract,
        custom_segments_read_contract=custom_segments_read_contract,
        negative_keywords_read_contract=negative_keywords_read_contract,
        decision_queue=decision_queue,
        sections=sections,
        blocked_handoff=blocked_handoff,
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
    )


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
            action_ids=action_ids,
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
            action_ids=action_ids,
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
        action_ids=action_ids,
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


def _campaign_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsCampaignReadContract:
    rows = _campaign_metric_rows(metric_facts)
    missing_read_contracts = [
        "recommendations",
        "change_history",
        "budget_pacing",
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


def _campaign_metric_rows(metric_facts: list[MetricFact]) -> list[AdsCampaignMetricRow]:
    grouped_facts: dict[tuple[str | None, str], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str | None, str, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "clicks",
            "impressions",
            "cost_micros",
            "conversions",
            "conversion_value",
        }:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name")
        if not campaign_id and not campaign_name:
            continue
        row_key = (campaign_id, campaign_name or f"campaign {campaign_id}")
        metric_key = (campaign_id, row_key[1], fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _campaign_metric_row(campaign_id, campaign_name, facts)
        for (campaign_id, campaign_name), facts in grouped_facts.items()
    ]
    return sorted(rows, key=_campaign_row_sort_key)


def _campaign_metric_row(
    campaign_id: str | None,
    campaign_name: str,
    facts: list[MetricFact],
) -> AdsCampaignMetricRow:
    facts_by_name = {fact.name: fact for fact in facts}
    expected_metrics = [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
    ]
    return AdsCampaignMetricRow(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        clicks=_int_metric_value(facts_by_name.get("clicks")),
        impressions=_int_metric_value(facts_by_name.get("impressions")),
        cost_micros=_int_metric_value(facts_by_name.get("cost_micros")),
        conversions=_float_metric_value(facts_by_name.get("conversions")),
        conversion_value=_float_metric_value(facts_by_name.get("conversion_value")),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        missing_metrics=[name for name in expected_metrics if name not in facts_by_name],
        blocked_claims=["CPA", "ROAS", "search-term waste", "wasted budget"],
    )


def _derived_kpi_read_contract(
    campaign_read_contract: AdsCampaignReadContract,
) -> AdsDerivedKpiReadContract:
    missing_read_contracts = [
        "account_currency",
        "profit_margin",
        "budget_pacing",
        "change_history",
        "recommendations",
    ]
    blocked_claims = [
        "profitability",
        "budget scaling",
        "wasted budget",
        "recommendation apply",
        "incrementality",
    ]
    kpi_rows = [_derived_kpi_row(row) for row in campaign_read_contract.campaign_rows]
    if kpi_rows:
        rows_with_cpa = sum(1 for row in kpi_rows if row.cost_per_conversion_micros is not None)
        rows_with_roas = sum(1 for row in kpi_rows if row.roas is not None)
        return AdsDerivedKpiReadContract(
            status="ready",
            title="Google Ads: wyliczone KPI kampanii",
            summary=(
                f"WILQ może policzyć KPI dla {len(kpi_rows)} kampanii: "
                f"CPA dostępne dla {rows_with_cpa}, ROAS dostępny dla {rows_with_roas}. "
                "To są obliczenia z bieżących metric facts, nie werdykt opłacalności."
            ),
            allowed_metrics=[
                "ctr",
                "average_cpc_micros",
                "conversion_rate",
                "cost_per_conversion_micros",
                "roas",
                "value_per_conversion",
            ],
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(
                evidence_id for row in kpi_rows for evidence_id in row.evidence_ids
            ),
            kpi_rows=kpi_rows,
            next_step=(
                "Użyj KPI do triage kampanii. Przed decyzją budżetową sprawdź walutę konta, "
                "marżę, pacing budżetu, historię zmian i rekomendacje."
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


def _derived_kpi_row(row: AdsCampaignMetricRow) -> AdsDerivedKpiRow:
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
    return AdsDerivedKpiRow(
        campaign_id=row.campaign_id,
        campaign_name=row.campaign_name,
        ctr=_ratio(row.clicks, row.impressions),
        average_cpc_micros=_ratio(row.cost_micros, row.clicks),
        conversion_rate=_ratio(row.conversions, row.clicks),
        cost_per_conversion_micros=_ratio(row.cost_micros, row.conversions),
        roas=_ratio(row.conversion_value, _micros_to_account_units(row.cost_micros)),
        value_per_conversion=_ratio(row.conversion_value, row.conversions),
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


def _ratio(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _micros_to_account_units(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value) / 1_000_000


def _campaign_row_sort_key(row: AdsCampaignMetricRow) -> tuple[int, int, str]:
    return (-(row.cost_micros or 0), -(row.clicks or 0), row.campaign_name)


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


def _format_float(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _search_terms_read_contract(
    metric_facts: list[MetricFact],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsSearchTermsReadContract:
    rows = _search_term_metric_rows(metric_facts)
    missing_read_contracts = [
        "keyword match context",
        "90_day_safety_check",
        "negative_keyword_action_validation",
    ]
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
            action_ids=action_ids,
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
        action_ids=action_ids,
        blocked_claims=search_terms_read_contract.blocked_claims,
        risk=ActionRisk.medium,
    )


def _custom_segments_read_contract(
    search_terms_read_contract: AdsSearchTermsReadContract,
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

    candidates = _custom_segment_candidates(search_terms_read_contract.search_term_rows)
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
                "keyword_planner_enrichment",
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
    return AdsCustomSegmentsReadContract(
        status="ready",
        title="Custom segments z realnych search terms",
        summary=(
            f"WILQ ma {len(candidates)} kandydatów custom segments i "
            f"{source_terms_count} source terms z Google Ads evidence."
        ),
        candidates=candidates,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id
            for candidate in candidates
            for evidence_id in candidate.evidence_ids
        ),
        missing_read_contracts=[
            "keyword_planner_enrichment",
            "forecast_or_audience_size",
            "custom_segment_payload_preview",
        ],
        blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
        action_ids=custom_segment_action_ids,
        next_step=(
            "Przejrzyj source terms, odrzuć nietrafione frazy, dodaj Keyword Planner "
            "enrichment i waliduj ActionObject przed jakimkolwiek apply."
        ),
    )


def _custom_segment_candidates(
    rows: list[AdsSearchTermMetricRow],
) -> list[AdsCustomSegmentCandidate]:
    grouped: dict[tuple[str | None, str | None], list[AdsSearchTermMetricRow]] = {}
    rejected_terms: list[str] = []
    rejection_reasons: list[str] = []
    for row in rows:
        rejection_reason = _custom_segment_rejection_reason(row)
        if rejection_reason is not None:
            rejected_terms.append(row.search_term)
            rejection_reasons.append(f"{row.search_term}: {rejection_reason}")
            continue
        grouped.setdefault((row.campaign_id, row.campaign_name), []).append(row)

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
        evidence_ids = _unique(
            evidence_id for row in sorted_rows for evidence_id in row.evidence_ids
        )
        metric_facts = [fact for row in sorted_rows for fact in row.metric_facts][:20]
        candidates.append(
            AdsCustomSegmentCandidate(
                id=f"ads_custom_segment_{_slug(campaign_id or campaign_name or str(index))}",
                name=name,
                intent="search_term_interest",
                source_terms=source_terms,
                rejected_terms=_unique(rejected_terms)[:12],
                rejection_reasons=_unique(rejection_reasons)[:12],
                search_term_rows=sorted_rows,
                source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
                evidence_ids=evidence_ids,
                metric_facts=metric_facts,
                confidence=_custom_segment_confidence(sorted_rows),
                validation_status="pending_validation",
                blocked_claims=CUSTOM_SEGMENT_BLOCKED_CLAIMS,
                next_step=(
                    "Użyj tych terminów jako prepare-only candidate. Przed apply wymagaj "
                    "Keyword Planner enrichment, payload preview i walidacji ActionObject."
                ),
            )
        )
    return candidates[:4]


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
            "source terms. Keyword Planner enrichment, audience size i performance "
            "pozostają brakującymi kontraktami."
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
                "keyword match context",
                "90_day_safety_check",
                "negative_keyword_payload_preview",
            ],
            blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Najpierw zbierz Google Ads search_term_view metric facts. Nie twórz "
                "wykluczeń bez search terms, kontekstu dopasowania i safety checku."
            ),
        )

    candidates = _negative_keyword_candidates(search_terms_read_contract.search_term_rows)
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
                "keyword match context",
                "90_day_safety_check",
                "negative_keyword_payload_preview",
            ],
            blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
            action_ids=[],
            next_step=(
                "Kontynuuj read-only review search terms. Nie twórz negative keyword "
                "candidates, jeśli bieżące evidence nie pokazuje zerowej konwersji."
            ),
        )

    return AdsNegativeKeywordsReadContract(
        status="ready",
        title="Review wykluczeń z search terms",
        summary=(
            f"WILQ ma {len(candidates)} terminów do review: mają koszt lub kliknięcia "
            "i zero konwersji w bieżącym Google Ads evidence."
        ),
        candidates=candidates,
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_unique(
            evidence_id for candidate in candidates for evidence_id in candidate.evidence_ids
        ),
        missing_read_contracts=[
            "keyword match context",
            "90_day_safety_check",
            "negative_keyword_payload_preview",
        ],
        blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
        action_ids=negative_keyword_action_ids,
        next_step=(
            "Przejrzyj kandydatów jako review-only. Przed jakimkolwiek apply wymagaj "
            "kontekstu dopasowania, 90-dniowego safety checku, payload preview i "
            "walidacji ActionObject."
        ),
    )


def _negative_keyword_candidates(
    rows: list[AdsSearchTermMetricRow],
) -> list[AdsNegativeKeywordCandidate]:
    candidates: list[AdsNegativeKeywordCandidate] = []
    for row in sorted(rows, key=_search_term_row_sort_key):
        if not _is_negative_keyword_review_candidate(row):
            continue
        metric_facts = row.metric_facts[:12]
        candidates.append(
            AdsNegativeKeywordCandidate(
                id=(
                    "ads_negative_keyword_review_"
                    f"{_slug(row.campaign_id or row.campaign_name or 'campaign')}_"
                    f"{_slug(row.ad_group_id or row.ad_group_name or 'ad_group')}_"
                    f"{_slug(row.search_term)}"
                ),
                search_term=row.search_term,
                campaign_id=row.campaign_id,
                campaign_name=row.campaign_name,
                ad_group_id=row.ad_group_id,
                ad_group_name=row.ad_group_name,
                clicks=row.clicks,
                impressions=row.impressions,
                cost_micros=row.cost_micros,
                conversions=row.conversions,
                conversion_value=row.conversion_value,
                evidence_ids=row.evidence_ids,
                metric_facts=metric_facts,
                required_checks=[
                    "review_search_term_context",
                    "check_existing_keywords_and_match_types",
                    "90_day_safety_check",
                    "human_confirm_before_apply",
                ],
                safety_status="needs_90_day_review",
                validation_status="pending_validation",
                blocked_claims=NEGATIVE_KEYWORD_BLOCKED_CLAIMS,
                next_step=(
                    "Sprawdź intencję terminu, istniejące keywords/match types i "
                    "90-dniową historię przed jakimkolwiek wykluczeniem."
                ),
            )
        )
    return candidates[:12]


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
    derived_kpi_read_contract: AdsDerivedKpiReadContract,
    search_terms_read_contract: AdsSearchTermsReadContract,
    custom_segments_read_contract: AdsCustomSegmentsReadContract,
    negative_keywords_read_contract: AdsNegativeKeywordsReadContract,
    sections: list[AdsDiagnosticSection],
    blocked_handoff: AdsBlockedHandoff | None,
    action_ids: list[str],
) -> list[AdsDecisionItem]:
    if blocked_handoff is not None:
        return [
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
            )
        ]

    decisions: list[AdsDecisionItem] = []
    if campaign_read_contract.campaign_rows:
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
                    "Nie ma jeszcze pełnego kontraktu CPA, ROAS, rekomendacji ani historii zmian."
                ),
                next_step=(
                    "Sprawdź kampanie z największym kosztem i ruchem w tabeli dowodów. "
                    "Nie podejmuj decyzji budżetowych bez brakujących kontraktów odczytu."
                ),
                allowed_metrics=campaign_read_contract.allowed_metrics,
                missing_read_contracts=campaign_read_contract.missing_read_contracts,
                source_connectors=campaign_read_contract.source_connectors,
                evidence_ids=campaign_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                campaign_rows=campaign_read_contract.campaign_rows,
                action_ids=action_ids,
                blocked_claims=campaign_read_contract.blocked_claims,
                risk=ActionRisk.low,
            )
        )

    if derived_kpi_read_contract.kpi_rows:
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
                missing_read_contracts=derived_kpi_read_contract.missing_read_contracts,
                source_connectors=derived_kpi_read_contract.source_connectors,
                evidence_ids=derived_kpi_read_contract.evidence_ids,
                derived_kpi_rows=derived_kpi_read_contract.kpi_rows,
                blocked_claims=derived_kpi_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if search_terms_read_contract.search_term_rows:
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
                source_connectors=search_terms_read_contract.source_connectors,
                evidence_ids=search_terms_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                search_term_rows=search_terms_read_contract.search_term_rows,
                action_ids=action_ids,
                blocked_claims=search_terms_read_contract.blocked_claims,
                risk=ActionRisk.medium,
            )
        )

    if negative_keywords_read_contract.candidates:
        metric_facts = [
            fact
            for candidate in negative_keywords_read_contract.candidates
            for fact in candidate.metric_facts
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
                    "w bieżącym evidence. To jest sygnał do review, nie dowód waste ani "
                    "zgoda na automatyczne wykluczenie."
                ),
                next_step=negative_keywords_read_contract.next_step,
                allowed_metrics=[
                    "search_term",
                    "search_term_clicks",
                    "search_term_cost_micros",
                    "search_term_conversions",
                    "search_term_conversion_value",
                ],
                missing_read_contracts=negative_keywords_read_contract.missing_read_contracts,
                source_connectors=negative_keywords_read_contract.source_connectors,
                evidence_ids=negative_keywords_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                negative_keyword_candidates=negative_keywords_read_contract.candidates,
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
                    "brakuje Keyword Planner enrichment, audience size i payload preview."
                ),
                next_step=custom_segments_read_contract.next_step,
                allowed_metrics=[
                    "search_term",
                    "search_term_clicks",
                    "search_term_impressions",
                    "search_term_cost_micros",
                    "search_term_conversions",
                    "search_term_conversion_value",
                ],
                missing_read_contracts=custom_segments_read_contract.missing_read_contracts,
                source_connectors=custom_segments_read_contract.source_connectors,
                evidence_ids=custom_segments_read_contract.evidence_ids,
                metric_facts=metric_facts[:12],
                search_term_rows=search_term_rows[:12],
                custom_segment_candidates=custom_segments_read_contract.candidates,
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

    return decisions


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
