from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

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
    Ga4DecisionItem,
    Ga4DiagnosticSection,
    Ga4DiagnosticsResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)
from wilq.storage.metric_store import metric_store

GA4_CONNECTOR_ID = "google_analytics_4"
GA4_METRIC_FACT_LIMIT = 240
Ga4DecisionType = Literal[
    "fix_measurement",
    "review_traffic_quality",
    "review_landing_mapping",
]


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
    decision_queue = _ga4_decision_queue(tactical_items, action_ids)
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
        landing_group_count=max(
            _landing_group_count(trusted_facts),
            _tactical_landing_group_count(tactical_items),
        ),
        low_engagement_count=_low_engagement_count(tactical_items),
        wordpress_match_count=_wordpress_match_count(tactical_items),
        decision_queue=decision_queue,
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
    if not dimensioned_facts and not tactical_items:
        return Ga4DiagnosticSection(
            id="ga4_landing_behavior",
            title="GA4: brak landing/source/campaign breakdown",
            status="blocked",
            summary=_ga4_blocker_reason(latest_refresh),
            diagnosis=(
                "WILQ nie ma metryk GA4 z landing page, źródłem i kampanią, "
                "więc nie może ocenić jakości landingów ani kampanii bez zmyślania."
            ),
            next_step="Uruchom odczyt GA4 i zbierz metryki landingów, źródeł i kampanii.",
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["landing page quality", "campaign quality", "message match"],
            risk=ActionRisk.medium,
        )
    if not dimensioned_facts:
        return Ga4DiagnosticSection(
            id="ga4_landing_behavior",
            title="GA4: jakość ruchu z landingów",
            status="ready",
            summary=(
                f"WILQ ma {_tactical_landing_group_count(tactical_items)} "
                "grup ruchu landing/źródło/kampania. Pełne metryki są "
                "dostępne w kolejce decyzji GA4."
            ),
            diagnosis=(
                "GA4 pozwala wskazać landing page do kontroli jakości "
                "ruchu. To nadal nie jest dowód konwersji, ROAS ani opłacalności."
            ),
            next_step=(
                "Sprawdź landing, źródło i kampanię w kolejce decyzji oraz oddziel "
                "problem pomiaru od problemu strony."
            ),
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_unique(
                evidence_id for item in tactical_items for evidence_id in item.evidence_ids
            ),
            metric_facts=_tactical_metric_facts(tactical_items)[:12],
            tactical_items=tactical_items[:6],
            action_ids=action_ids,
            blocked_claims=["conversion rate", "ROAS", "revenue", "profitability"],
            risk=ActionRisk.low,
        )
    return Ga4DiagnosticSection(
        id="ga4_landing_behavior",
        title="GA4: jakość ruchu z landingów",
        status="ready",
        summary=(
            f"WILQ ma {_landing_group_count(dimensioned_facts)} grup ruchu "
            f"landing/źródło/kampania i {len(dimensioned_facts)} metryk GA4."
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
    tactical_group_count = _tactical_landing_group_count(tactical_items)
    if not facts:
        return Ga4DiagnosticSection(
            id="ga4_tracking_readiness",
            title="GA4: brak metryk zachowania",
            status="blocked",
            summary=_ga4_blocker_reason(latest_refresh),
            diagnosis="Brak GA4 metric facts oznacza blocker, nie spadek jakości ruchu.",
            next_step="Odśwież odczyt GA4 i dopiero potem sprawdzaj problemy pomiaru.",
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["tracking gap", "conversion drop", "funnel dropoff"],
            risk=ActionRisk.medium,
        )
    return Ga4DiagnosticSection(
        id="ga4_tracking_readiness",
        title="GA4: gotowość pomiaru konwersji",
        status="ready" if conversion_like_facts else "missing",
        summary=(
            f"WILQ ma {len(dimensioned_facts)} metryk zachowania, "
            f"{tactical_group_count} grup landingów i "
            f"{len(conversion_like_facts)} metryk konwersji albo kluczowych zdarzeń."
        ),
        diagnosis=(
            "Aktualne dane wspierają review jakości ruchu. Jeżeli brakuje metryk "
            "konwersji albo kluczowych zdarzeń, WILQ musi oznaczyć konwersje jako "
            "brakujący wymiar analizy."
        ),
        next_step=(
            "Waliduj ActionObject i przygotuj checklistę jakości pomiaru "
            "bez wykonania zmian."
        ),
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
        title="Bezpieczeństwo akcji GA4",
        status="ready" if facts or tactical_items else "blocked",
        summary="Akcje GA4 pozostają w trybie przygotowania i nie wykonują zmian w pomiarze.",
        diagnosis=(
            "WILQ może przygotować checklistę jakości pomiaru i review landingów. Nie może "
            "zmieniać konfiguracji GA4 ani twierdzić, że naprawił pomiar bez osobnego "
            "ActionObject, walidacji i audytu."
        ),
        next_step="Waliduj `act_review_ga4_tracking_quality` i zatrzymaj wykonanie zmian.",
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=["GA4 write", "conversion setup applied", "tracking fixed"],
        risk=ActionRisk.medium,
    )


def _ga4_decision_queue(
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> list[Ga4DecisionItem]:
    decisions: list[Ga4DecisionItem] = []
    for item in _unique_tactical_items(tactical_items):
        landing_page = item.dimensions.get("landing_page")
        source_medium = item.dimensions.get("source_medium")
        campaign_name = item.dimensions.get("campaign_name")
        wordpress_match = item.dimensions.get("wordpress_match")
        has_missing_reporting_dimension = any(
            value == "(not set)" for value in (landing_page, source_medium, campaign_name)
        )
        if item.intent == "tracking_gap" or has_missing_reporting_dimension:
            decision_type: Ga4DecisionType = "fix_measurement"
            title = "Napraw problem pomiaru GA4"
            rationale = (
                "GA4 zwraca brakujące wymiary raportu, więc to jest problem pomiaru "
                "albo atrybucji, nie gotowa rekomendacja marketingowa."
            )
            next_step = (
                "Sprawdź landing page, source/medium, UTM-y i konfigurację raportu. "
                "Nie oceniaj kampanii ani strony po tym wierszu."
            )
            risk = ActionRisk.medium
        elif wordpress_match == "missing":
            decision_type = "review_landing_mapping"
            title = f"Sprawdź mapowanie landing page: {landing_page or 'brak landing page'}"
            rationale = (
                "GA4 widzi ruch, ale inventory WordPress nie potwierdza tej strony. "
                "Najpierw trzeba sprawdzić mapowanie URL, zanim powstanie wniosek o treści."
            )
            next_step = (
                "Zweryfikuj, czy landing istnieje w WordPress lub sitemap, a potem sprawdź "
                "message match dla kampanii."
            )
            risk = ActionRisk.medium
        else:
            decision_type = "review_traffic_quality"
            title = f"Sprawdź jakość ruchu: {landing_page or 'brak landing page'}"
            rationale = (
                "GA4 pokazuje ruch dla potwierdzonego landing page. To wystarcza do "
                "review jakości ruchu i message match, ale nie do claimów o konwersjach."
            )
            next_step = (
                "Porównaj landing, źródło i kampanię z intencją strony. Nie oceniaj ROAS "
                "ani revenue bez osobnych metryk konwersji i kosztów."
            )
            risk = ActionRisk.low
        decisions.append(
            Ga4DecisionItem(
                id=f"ga4_decision_{_slug(item.id)}",
                decision_type=decision_type,
                title=title,
                landing_page=landing_page,
                source_medium=source_medium,
                campaign_name=campaign_name,
                wordpress_match=wordpress_match,
                wordpress_match_confidence=item.dimensions.get("wordpress_match_confidence"),
                wordpress_content_url=item.dimensions.get("wordpress_content_url"),
                source_connectors=item.source_connectors,
                evidence_ids=item.evidence_ids,
                metric_facts=item.metric_facts[:8],
                action_ids=_unique([*item.action_ids, *action_ids]),
                blocked_claims=_unique(
                    [
                        *item.blocked_claims,
                        "conversion rate",
                        "ROAS",
                        "revenue",
                        "profitability",
                    ]
                ),
                rationale=rationale,
                next_step=next_step,
                risk=risk,
            )
        )
    return sorted(decisions, key=lambda decision: (decision.risk.value, decision.id))[:6]


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


def _tactical_landing_group_count(items: Iterable[TacticalQueueItem]) -> int:
    return len(
        {
            (
                item.dimensions.get("landing_page", ""),
                item.dimensions.get("source_medium", ""),
                item.dimensions.get("campaign_name", ""),
            )
            for item in items
            if item.dimensions.get("landing_page")
        }
    )


def _tactical_metric_facts(items: Iterable[TacticalQueueItem]) -> list[MetricFact]:
    facts: list[MetricFact] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        for fact in item.metric_facts:
            key = (fact.source_connector, fact.name, fact.evidence_id)
            if key in seen:
                continue
            seen.add(key)
            facts.append(fact)
    return facts


def _unique_tactical_items(items: Iterable[TacticalQueueItem]) -> list[TacticalQueueItem]:
    seen: set[str] = set()
    result: list[TacticalQueueItem] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result


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


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")[:96]
