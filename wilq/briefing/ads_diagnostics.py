from __future__ import annotations

from collections.abc import Iterable

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
    AdsDiagnosticSection,
    AdsDiagnosticsResponse,
    AdsSearchTermMetricRow,
    AdsSearchTermsReadContract,
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
    search_terms_read_contract = _search_terms_read_contract(
        trusted_metric_facts,
        latest_refresh,
    )
    action_ids = _google_ads_action_ids(list_actions())
    sections = [
        _oauth_or_live_section(latest_refresh, trusted_metric_facts, action_ids),
        _campaign_overview_section(
            trusted_metric_facts,
            latest_refresh,
            action_ids,
            campaign_read_contract,
        ),
        _search_terms_section(search_terms_read_contract, action_ids),
        _safe_action_section(action_ids, latest_refresh),
    ]
    return AdsDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        campaign_read_contract=campaign_read_contract,
        search_terms_read_contract=search_terms_read_contract,
        sections=sections,
        blocked_handoff=_blocked_handoff(live_data_available, latest_refresh, sections, action_ids),
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )


def _latest_google_ads_refresh() -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=GOOGLE_ADS_CONNECTOR_ID)
    return runs[0] if runs else None


def _google_ads_action_ids(actions: list[ActionObject]) -> list[str]:
    return [action.id for action in actions if action.connector == GOOGLE_ADS_CONNECTOR_ID]


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
            summary="WILQ ma zapisane metric facts z read-only Google Ads vendor_read.",
            diagnosis=(
                "Można przejść do diagnozy kampanii, ale nadal każda rekomendacja musi "
                "wskazać evidence ID, metric facts i bezpieczny ActionObject."
            ),
            next_step="Rozszerz Ads read pack o search terms, recommendations i change events.",
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
            title="Campaign activity read contract",
            status="ready",
            summary=campaign_read_contract.summary,
            diagnosis=(
                "WILQ ma wymiarowe campaign activity rows z Google Ads. To wystarcza "
                "do pierwszego przeglądu aktywności kampanii, ale nadal nie wystarcza "
                "do diagnozy CPA, ROAS, search-term waste ani negative keywords."
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
        title="Campaign overview",
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
        "search terms",
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
            title="Google Ads: campaign activity rows",
            summary=(
                f"WILQ ma {len(rows)} campaign rows: clicks={total_clicks}, "
                f"impressions={total_impressions}, cost_micros={total_cost_micros}, "
                f"conversions={_format_float(total_conversions)}, "
                f"conversion_value={_format_float(total_conversion_value)}."
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
                "Użyj campaign rows do przeglądu aktywności. Przed wnioskami o waste, "
                "CPA, ROAS albo negative keywords dodaj brakujące read contracts."
            ),
        )

    return AdsCampaignReadContract(
        status="blocked",
        title="Google Ads: brak campaign activity rows",
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
        blocked_claims=["CPA", "ROAS", "search terms", "wasted budget"],
    )


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
            title="Google Ads: search terms read-only rows",
            summary=(
                f"WILQ ma {len(rows)} search term rows: clicks={total_clicks}, "
                f"impressions={total_impressions}, cost_micros={total_cost_micros}, "
                f"conversions={_format_float(total_conversions)}, "
                f"conversion_value={_format_float(total_conversion_value)}."
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
                "Użyj search term rows jako read-only przeglądu zapytań. Nie twórz "
                "negative keywords ani waste claimów bez konwersji, 90-dniowego checku "
                "i zwalidowanego ActionObject."
            ),
        )

    return AdsSearchTermsReadContract(
        status="blocked",
        title="Google Ads: brak search terms rows",
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
            title="Search terms read contract",
            status="ready",
            summary=search_terms_read_contract.summary,
            diagnosis=(
                "WILQ ma read-only search term rows z Google Ads. To jeszcze nie "
                "odblokowuje negative keywords: brakuje match contextu, 90-dniowego "
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
        title="Search terms i waste",
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


def _safe_action_section(
    action_ids: list[str],
    latest_refresh: ConnectorRefreshRun | None,
) -> AdsDiagnosticSection:
    evidence_ids = _refresh_or_connector_evidence_ids(latest_refresh)
    return AdsDiagnosticSection(
        id="ads_action_safety",
        title="Bezpieczne akcje Ads",
        status="blocked",
        summary="WILQ ma tylko prepare-only repair action dla OAuth.",
        diagnosis=(
            "Żadna zmiana Google Ads nie może przejść do apply bez payload preview, "
            "walidacji, jawnego confirm i audit eventu. Obecnie jedyny sensowny "
            "ActionObject to naprawa dostępu."
        ),
        next_step=(
            "Zweryfikuj `act_configure_google_ads_env`; apply pozostaje zablokowany "
            "bez explicit support."
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=["budget apply", "campaign creation", "negative keyword apply"],
        risk=ActionRisk.medium,
    )


def _blocked_handoff(
    live_data_available: bool,
    latest_refresh: ConnectorRefreshRun | None,
    sections: list[AdsDiagnosticSection],
    action_ids: list[str],
) -> AdsBlockedHandoff:
    evidence_ids = _unique(
        evidence_id for section in sections for evidence_id in section.evidence_ids
    )
    blocked_claims = _unique(claim for section in sections for claim in section.blocked_claims)
    if live_data_available:
        return AdsBlockedHandoff(
            status="ready",
            title="Google Ads: live read gotowy do kolejnego kroku",
            summary=(
                "WILQ ma live metric facts z Google Ads, ale akcje zapisu nadal wymagają "
                "walidacji."
            ),
            marketer_message=(
                "Możesz pokazać bazowy odczyt Google Ads, ale search terms, negative keywords "
                "i apply zmian wymagają osobnych evidence oraz ActionObject validation."
            ),
            repair_steps=[
                "Rozszerz read-only Google Ads vendor_read o search terms i recommendations.",
                "Waliduj każdy ActionObject przed apply.",
                "Nie wykonuj budżetów, wykluczeń ani kampanii bez preview i audit eventu.",
            ],
            allowed_demo_claims=[
                "Google Ads connector ma live metric facts.",
                "WILQ wymaga evidence IDs i ActionObject validation przed działaniami.",
            ],
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=evidence_ids,
            action_ids=action_ids,
        )
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
