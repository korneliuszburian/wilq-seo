from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    Ga4DiagnosticSection,
    Ga4DiagnosticsResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)
from wilq.storage.metric_store import metric_store

GA4_CONNECTOR_ID = "google_analytics_4"
GA4_METRIC_FACT_LIMIT = 240


def build_ga4_diagnostics() -> Ga4DiagnosticsResponse:
    connector = get_connector_status(GA4_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("GA4 connector is not registered.")
    latest_refresh = _latest_ga4_refresh()
    metric_facts = metric_store().list_metric_facts(
        connector_id=GA4_CONNECTOR_ID,
        limit=GA4_METRIC_FACT_LIMIT,
    )
    live_data_available = bool(metric_facts) and (
        latest_refresh is None
        or (
            latest_refresh.status == ConnectorRefreshStatus.completed
            and latest_refresh.vendor_data_collected
        )
    )
    trusted_facts = metric_facts if live_data_available else []
    tactical_items = [
        item for item in build_tactical_queue().items if item.domain == OpportunityDomain.ga4
    ]
    action_ids = _ga4_action_ids(list_actions())
    sections = [
        _landing_behavior_section(latest_refresh, trusted_facts, tactical_items, action_ids),
        _tracking_readiness_section(latest_refresh, trusted_facts, tactical_items, action_ids),
        _ga4_action_safety_section(latest_refresh, trusted_facts, tactical_items, action_ids),
    ]
    return Ga4DiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        landing_group_count=_landing_group_count(trusted_facts),
        low_engagement_count=_low_engagement_count(tactical_items),
        wordpress_match_count=_wordpress_match_count(tactical_items),
        sections=sections,
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )


def _latest_ga4_refresh() -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=GA4_CONNECTOR_ID)
    return runs[0] if runs else None


def _ga4_action_ids(actions: list[ActionObject]) -> list[str]:
    return [action.id for action in actions if action.connector == GA4_CONNECTOR_ID]


def _landing_behavior_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4DiagnosticSection:
    dimensioned_facts = _dimensioned_ga4_facts(facts)
    if not dimensioned_facts:
        return Ga4DiagnosticSection(
            id="ga4_landing_behavior",
            title="GA4: brak landing/source/campaign breakdown",
            status="blocked",
            summary=_ga4_blocker_reason(latest_refresh),
            diagnosis=(
                "WILQ nie ma GA4 facts z landing_page, source_medium i campaign_name, "
                "więc nie może ocenić jakości landingów ani kampanii bez zmyślania."
            ),
            next_step="Uruchom read-only GA4 vendor_read i zbierz landing/source/campaign facts.",
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["landing page quality", "campaign quality", "message match"],
            risk=ActionRisk.medium,
        )
    return Ga4DiagnosticSection(
        id="ga4_landing_behavior",
        title="GA4: landing/source/campaign behavior",
        status="ready",
        summary=(
            f"WILQ ma {_landing_group_count(dimensioned_facts)} landing/source/campaign "
            f"groups i {len(dimensioned_facts)} GA4 metric facts."
        ),
        diagnosis=(
            "GA4 behavior facts pozwalają wskazać landing pages do kontroli jakości ruchu. "
            "To nadal nie jest dowód konwersji, ROAS ani opłacalności."
        ),
        next_step=(
            "Najpierw sprawdź grupy z niskim engagement i dopiero potem oceniaj "
            "message match."
        ),
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in dimensioned_facts),
                *(evidence_id for item in tactical_items for evidence_id in item.evidence_ids),
            ]
        ),
        metric_facts=dimensioned_facts[:12],
        tactical_items=tactical_items[:6],
        action_ids=action_ids,
        blocked_claims=["conversion rate", "ROAS", "revenue", "profitability"],
        risk=ActionRisk.low,
    )


def _tracking_readiness_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4DiagnosticSection:
    conversion_like_facts = [
        fact
        for fact in facts
        if fact.name
        in {"conversions", "key_events", "purchase_revenue", "total_revenue", "transactions"}
    ]
    dimensioned_facts = _dimensioned_ga4_facts(facts)
    if not facts:
        return Ga4DiagnosticSection(
            id="ga4_tracking_readiness",
            title="GA4: brak behavior facts",
            status="blocked",
            summary=_ga4_blocker_reason(latest_refresh),
            diagnosis="Brak GA4 metric facts oznacza blocker, nie spadek jakości ruchu.",
            next_step="Odśwież GA4 vendor_read i dopiero potem sprawdzaj tracking gaps.",
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["tracking gap", "conversion drop", "funnel dropoff"],
            risk=ActionRisk.medium,
        )
    return Ga4DiagnosticSection(
        id="ga4_tracking_readiness",
        title="GA4: tracking/conversion readiness",
        status="ready" if conversion_like_facts else "missing",
        summary=(
            f"WILQ ma {len(dimensioned_facts)} behavior facts i "
            f"{len(conversion_like_facts)} conversion-like facts."
        ),
        diagnosis=(
            "Aktualne dane wspierają review jakości ruchu. Jeżeli conversion-like facts "
            "są puste, WILQ musi oznaczyć konwersje jako brakujący wymiar analizy."
        ),
        next_step="Waliduj ActionObject i przygotuj tracking-gap checklist bez apply.",
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_unique(fact.evidence_id for fact in facts[:20]),
        metric_facts=[*dimensioned_facts[:8], *conversion_like_facts[:4]],
        tactical_items=tactical_items[:4],
        action_ids=action_ids,
        blocked_claims=["conversion drop", "funnel diagnosis", "attribution verdict"],
        risk=ActionRisk.low if conversion_like_facts else ActionRisk.medium,
    )


def _ga4_action_safety_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4DiagnosticSection:
    return Ga4DiagnosticSection(
        id="ga4_action_safety",
        title="GA4: bezpieczne akcje analityczne",
        status="ready" if facts or tactical_items else "blocked",
        summary="GA4 actions pozostają review/prepare-only i nie wykonują zmian w pomiarze.",
        diagnosis=(
            "WILQ może przygotować checklistę tracking quality i landing review. Nie może "
            "zmieniać konfiguracji GA4 ani twierdzić, że naprawił tracking bez osobnego "
            "ActionObject, walidacji i audytu."
        ),
        next_step="Pokaż payload preview `act_review_ga4_tracking_quality` i zatrzymaj apply.",
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=["GA4 write", "conversion setup applied", "tracking fixed"],
        risk=ActionRisk.medium,
    )


def _dimensioned_ga4_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    return [
        fact
        for fact in facts
        if fact.source_connector == GA4_CONNECTOR_ID
        and {"landing_page", "source_medium", "campaign_name"}.issubset(fact.dimensions)
    ]


def _landing_group_count(facts: Iterable[MetricFact]) -> int:
    return len(
        {
            (
                fact.dimensions.get("landing_page", ""),
                fact.dimensions.get("source_medium", ""),
                fact.dimensions.get("campaign_name", ""),
            )
            for fact in _dimensioned_ga4_facts(facts)
        }
    )


def _low_engagement_count(tactical_items: Iterable[TacticalQueueItem]) -> int:
    return sum(1 for item in tactical_items if item.intent == "landing_page_quality")


def _wordpress_match_count(tactical_items: Iterable[TacticalQueueItem]) -> int:
    return sum(1 for item in tactical_items if item.dimensions.get("wordpress_match") == "found")


def _ga4_blocker_reason(latest_refresh: ConnectorRefreshRun | None) -> str:
    if latest_refresh is None:
        return "Brak GA4 refresh run."
    if latest_refresh.status == ConnectorRefreshStatus.blocked:
        return f"GA4 refresh blocked: {', '.join(latest_refresh.errors) or latest_refresh.summary}"
    if latest_refresh.status == ConnectorRefreshStatus.failed:
        return f"GA4 refresh failed: {', '.join(latest_refresh.errors) or latest_refresh.summary}"
    if not latest_refresh.vendor_data_collected:
        return "Ostatni GA4 refresh nie zebrał vendor data."
    return latest_refresh.summary


def _refresh_or_connector_evidence_ids(latest_refresh: ConnectorRefreshRun | None) -> list[str]:
    if latest_refresh and latest_refresh.evidence_ids:
        return latest_refresh.evidence_ids
    return [connector_evidence_id(GA4_CONNECTOR_ID)]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
