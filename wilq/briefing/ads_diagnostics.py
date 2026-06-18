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
    AdsDiagnosticSection,
    AdsDiagnosticsResponse,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.metric_store import metric_store

GOOGLE_ADS_CONNECTOR_ID = "google_ads"
ADS_METRIC_FACT_LIMIT = 120


def build_ads_diagnostics() -> AdsDiagnosticsResponse:
    connector = get_connector_status(GOOGLE_ADS_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Google Ads connector is not registered.")
    latest_refresh = _latest_google_ads_refresh()
    metric_facts = metric_store().list_metric_facts(
        connector_id=GOOGLE_ADS_CONNECTOR_ID,
        limit=ADS_METRIC_FACT_LIMIT,
    )
    live_data_available = bool(metric_facts) and (
        latest_refresh is None or latest_refresh.vendor_data_collected
    )
    action_ids = _google_ads_action_ids(list_actions())
    sections = [
        _oauth_or_live_section(latest_refresh, metric_facts, action_ids),
        _campaign_overview_section(metric_facts, latest_refresh, action_ids),
        _search_terms_section(latest_refresh, action_ids),
        _safe_action_section(action_ids, latest_refresh),
    ]
    return AdsDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        sections=sections,
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
) -> AdsDiagnosticSection:
    campaign_facts = [
        fact
        for fact in metric_facts
        if fact.name in {"clicks", "impressions", "cost_micros"}
    ]
    if campaign_facts:
        return AdsDiagnosticSection(
            id="ads_campaign_overview",
            title="Campaign overview",
            status="ready",
            summary=_metric_sentence(campaign_facts),
            diagnosis=(
                "WILQ ma bazowy odczyt kampanii z Google Ads. To wystarcza do "
                "pierwszego przeglądu aktywności, ale nie do diagnozy waste bez "
                "search-term i conversion evidence."
            ),
            next_step=(
                "Dodaj search-term read contract i konwersje przed rekomendacjami "
                "negative keywords."
            ),
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(fact.evidence_id for fact in campaign_facts),
            metric_facts=campaign_facts[:12],
            action_ids=action_ids,
            blocked_claims=["search-term waste", "CPA", "ROAS"],
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


def _search_terms_section(
    latest_refresh: ConnectorRefreshRun | None,
    action_ids: list[str],
) -> AdsDiagnosticSection:
    evidence_ids = _refresh_or_connector_evidence_ids(latest_refresh)
    return AdsDiagnosticSection(
        id="ads_search_terms",
        title="Search terms i waste",
        status="missing",
        summary="Google Ads adapter nie ma jeszcze search-term read contract.",
        diagnosis=(
            "BDOS-klasa wymaga search terms, kosztu, konwersji i 90-dniowego checku "
            "ochronnego przed wykluczeniami. Obecny adapter nie może z tego tworzyć "
            "negative keyword candidates."
        ),
        next_step=(
            "Po naprawie OAuth dodaj query contract dla search_term_view i walidację "
            "kandydatów negative keywords jako prepare-only ActionObject."
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=["negative keyword candidates", "ngram waste", "query exclusions"],
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
