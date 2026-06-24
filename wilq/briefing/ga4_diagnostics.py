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
    Ga4ConversionReadinessContract,
    Ga4DecisionItem,
    Ga4DiagnosticSection,
    Ga4DiagnosticsResponse,
    Ga4FreshnessAssessment,
    Ga4OperatorSummary,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    utc_now,
)
from wilq.storage.metric_store import metric_store

GA4_CONNECTOR_ID = "google_analytics_4"
GA4_METRIC_FACT_LIMIT = 2000
GA4_STALE_AFTER_HOURS = 48
GA4_CONVERSION_METRIC_NAMES = {
    "conversions",
    "ecommerce_purchases",
    "key_events",
    "purchase_revenue",
    "total_revenue",
    "transactions",
}
GA4_CONVERSION_BLOCKED_CLAIMS = [
    "conversion rate",
    "ROAS",
    "revenue",
    "profitability",
    "conversion drop",
    "funnel diagnosis",
    "attribution verdict",
]
GA4_KNOWLEDGE_CARD_IDS = ["card_ga4_behavior_diagnostics_playbook"]
GA4_EXPERT_RULE_IDS = ["ga4_diagnostics_v1"]
Ga4DecisionType = Literal[
    "fix_measurement",
    "review_traffic_quality",
    "review_landing_mapping",
]


def build_ga4_diagnostics(
    tactical_items: list[TacticalQueueItem] | None = None,
    actions: list[ActionObject] | None = None,
    metric_facts: list[MetricFact] | None = None,
) -> Ga4DiagnosticsResponse:
    connector = get_connector_status(GA4_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("GA4 connector is not registered.")
    latest_refresh = _latest_ga4_refresh()
    metric_facts = (
        metric_facts
        if metric_facts is not None
        else metric_store().list_metric_facts(
            connector_id=GA4_CONNECTOR_ID,
            limit=GA4_METRIC_FACT_LIMIT,
        )
    )
    live_data_available = bool(metric_facts) and (
        latest_refresh is None
        or (
            latest_refresh.status == ConnectorRefreshStatus.completed
            and latest_refresh.vendor_data_collected
        )
    )
    trusted_facts = metric_facts if live_data_available else []
    source_tactical_items = (
        tactical_items if tactical_items is not None else build_tactical_queue().items
    )
    tactical_items = [
        item for item in source_tactical_items if item.domain == OpportunityDomain.ga4
    ]
    actions = actions if actions is not None else list_actions()
    action_ids = _ga4_action_ids(actions)
    dimensioned_facts = _dimensioned_ga4_facts(trusted_facts)
    decision_queue = _ga4_decisions_with_lineage(
        _ga4_decision_queue(tactical_items, action_ids, dimensioned_facts)
    )
    freshness_assessment = _ga4_freshness_assessment(latest_refresh, trusted_facts)
    conversion_readiness_contract = _conversion_readiness_contract(
        latest_refresh=latest_refresh,
        facts=trusted_facts,
        tactical_items=tactical_items,
        action_ids=action_ids,
    )
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
        freshness_assessment=freshness_assessment,
        conversion_readiness_contract=conversion_readiness_contract,
        operator_summary=_operator_summary(
            decision_queue,
            conversion_readiness_contract,
            freshness_assessment,
            sections,
            action_ids,
        ),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=_unique(
            [
                *(
                    evidence_id
                    for section in sections
                    for evidence_id in section.evidence_ids
                ),
                *conversion_readiness_contract.evidence_ids,
            ]
        ),
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=(
            sum(1 for section in sections if section.status == "blocked")
            + (1 if conversion_readiness_contract.status == "blocked" else 0)
        ),
        decision_blocker_count=sum(
            1 for decision in decision_queue if decision.status == "blocked"
        ),
    )


def _operator_summary(
    decisions: list[Ga4DecisionItem],
    conversion_readiness_contract: Ga4ConversionReadinessContract,
    freshness_assessment: Ga4FreshnessAssessment,
    sections: list[Ga4DiagnosticSection],
    action_ids: list[str],
) -> Ga4OperatorSummary:
    top_decisions = sorted(decisions, key=lambda item: (item.priority, item.id))[:4]
    freshness_note = (
        f" Dane GA4 są do odświeżenia: {freshness_assessment.summary}"
        if freshness_assessment.requires_refresh
        else f" {freshness_assessment.summary}"
    )
    freshness_next_step = (
        f" Najpierw: {freshness_assessment.next_step}"
        if freshness_assessment.requires_refresh
        else ""
    )
    conversion_note = _operator_conversion_note(conversion_readiness_contract)
    return Ga4OperatorSummary(
        title="Co marketer ma sprawdzić teraz w jakości ruchu",
        summary=(
            "WILQ pokazuje grupy ruchu do kontroli landingów, źródeł i kampanii. "
            f"{conversion_note}"
            f"{freshness_note}"
        ),
        next_step=(
            "Przejdź przez top decyzje GA4, oddziel problem pomiaru od problemu "
            "jakości ruchu i waliduj ActionObject tylko jako review-only."
            f"{freshness_next_step}"
        ),
        top_decision_ids=[decision.id for decision in top_decisions],
        measurement_issue_count=sum(
            1 for decision in decisions if decision.decision_type == "fix_measurement"
        ),
        wordpress_missing_count=sum(
            1 for decision in decisions if decision.wordpress_match == "missing"
        ),
        conversion_readiness_status=conversion_readiness_contract.status,
        source_connectors=_unique(
            connector
            for decision in top_decisions
            for connector in decision.source_connectors
        )
        or [GA4_CONNECTOR_ID],
        evidence_ids=_unique(
            [
                *(
                    evidence_id
                    for decision in top_decisions
                    for evidence_id in decision.evidence_ids
                ),
                *conversion_readiness_contract.evidence_ids,
            ]
        ),
        action_ids=action_ids,
        blocked_claims=_unique(
            [
                *(claim for section in sections for claim in section.blocked_claims),
                *conversion_readiness_contract.blocked_claims,
            ]
        ),
    )


def _operator_conversion_note(contract: Ga4ConversionReadinessContract) -> str:
    if contract.status == "ready":
        return (
            "WILQ ma metryki konwersji/key events w evidence, ale ROAS, "
            "profitability, spadek konwersji i wina kampanii nadal wymagają "
            "osobnych dowodów oraz kontekstu kosztów, historii i atrybucji."
        )
    return (
        "Brak metryk konwersji oznacza, że nie wolno wyciągać wniosków o ROAS, "
        "revenue, spadku konwersji ani winie kampanii."
    )


def _latest_ga4_refresh() -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=GA4_CONNECTOR_ID)
    return runs[0] if runs else None


def _ga4_freshness_assessment(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
) -> Ga4FreshnessAssessment:
    if latest_refresh is None:
        fact_collected_dates = [
            fact.collected_at for fact in facts if fact.collected_at is not None
        ]
        if fact_collected_dates:
            latest_fact_collected_at = max(fact_collected_dates)
            age_hours = round((utc_now() - latest_fact_collected_at).total_seconds() / 3600, 2)
            if age_hours > GA4_STALE_AFTER_HOURS:
                return Ga4FreshnessAssessment(
                    state="stale",
                    latest_refresh_id=None,
                    latest_refresh_completed_at=latest_fact_collected_at,
                    age_hours=age_hours,
                    stale_after_hours=GA4_STALE_AFTER_HOURS,
                    requires_refresh=True,
                    summary=(
                        f"Najnowsze GA4 metric facts mają około {age_hours:.1f}h "
                        "i są do odświeżenia."
                    ),
                    next_step=(
                        "Uruchom read-only GA4 vendor_read, jeśli pytanie dotyczy "
                        "aktualnego stanu landingów, źródeł albo kampanii."
                    ),
                )
            return Ga4FreshnessAssessment(
                state="fresh",
                latest_refresh_id=None,
                latest_refresh_completed_at=latest_fact_collected_at,
                age_hours=age_hours,
                stale_after_hours=GA4_STALE_AFTER_HOURS,
                requires_refresh=False,
                summary=(
                    f"Najnowsze GA4 metric facts mają około {age_hours:.1f}h i mieszczą się "
                    f"w progu {GA4_STALE_AFTER_HOURS}h."
                ),
                next_step="Można użyć danych GA4 do review bez dodatkowego refreshu.",
            )
        return Ga4FreshnessAssessment(
            state="missing",
            latest_refresh_id=None,
            latest_refresh_completed_at=None,
            age_hours=None,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary="Brak zapisanego read-only vendor_read GA4.",
            next_step="Uruchom read-only GA4 vendor_read przed oceną aktualnej jakości ruchu.",
        )

    completed_at = latest_refresh.completed_at or latest_refresh.started_at
    age_hours = round((utc_now() - completed_at).total_seconds() / 3600, 2)
    if (
        latest_refresh.status != ConnectorRefreshStatus.completed
        or not latest_refresh.vendor_data_collected
    ):
        return Ga4FreshnessAssessment(
            state="blocked",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                "Ostatni odczyt GA4 nie zakończył się pełnym vendor_read z metrykami, "
                f"tylko {latest_refresh.status.value}."
            ),
            next_step=(
                "Napraw blocker odczytu i uruchom read-only GA4 vendor_read przed "
                "wnioskami o aktualnej jakości ruchu."
            ),
        )

    if age_hours > GA4_STALE_AFTER_HOURS:
        return Ga4FreshnessAssessment(
            state="stale",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                f"Ostatni GA4 vendor_read ma około {age_hours:.1f}h i jest do odświeżenia. "
                "To wystarcza do stale review, ale nie do claimów o bieżącym stanie ruchu."
            ),
            next_step=(
                "Uruchom read-only GA4 vendor_read, jeśli pytanie dotyczy aktualnego "
                "stanu landingów, źródeł albo kampanii."
            ),
        )

    return Ga4FreshnessAssessment(
        state="fresh",
        latest_refresh_id=latest_refresh.id,
        latest_refresh_completed_at=completed_at,
        age_hours=age_hours,
        stale_after_hours=GA4_STALE_AFTER_HOURS,
        requires_refresh=False,
        summary=(
            f"Ostatni GA4 vendor_read ma około {age_hours:.1f}h i mieści się "
            f"w progu {GA4_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć danych GA4 do review bez dodatkowego refreshu.",
    )


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
        fact for fact in facts if fact.name in GA4_CONVERSION_METRIC_NAMES
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
        blocked_claims=[
            "conversion drop",
            "funnel diagnosis",
            "attribution verdict",
        ],
        risk=ActionRisk.low if conversion_like_facts else ActionRisk.medium,
    )


def _conversion_readiness_contract(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4ConversionReadinessContract:
    conversion_like_facts = [
        fact for fact in facts if fact.name in GA4_CONVERSION_METRIC_NAMES
    ]
    dimensioned_facts = _dimensioned_ga4_facts(facts)
    landing_group_count = max(
        _landing_group_count(dimensioned_facts),
        _tactical_landing_group_count(tactical_items),
    )
    status: Literal["ready", "blocked"] = "ready" if conversion_like_facts else "blocked"
    evidence_ids = _unique(
        [
            *(fact.evidence_id for fact in conversion_like_facts),
            *(fact.evidence_id for fact in dimensioned_facts[:12]),
            *(evidence_id for item in tactical_items for evidence_id in item.evidence_ids),
            *_refresh_or_connector_evidence_ids(latest_refresh),
        ]
    )
    return Ga4ConversionReadinessContract(
        status=status,
        title="GA4: kontrakt konwersji i key events",
        summary=(
            "WILQ może oceniać jakość ruchu z GA4, ale claimy o konwersjach, "
            "ROAS, revenue i profitability wymagają osobnych metryk konwersji "
            "albo key events."
        ),
        allowed_metrics=sorted(GA4_CONVERSION_METRIC_NAMES),
        available_read_contracts=(
            ["conversion_or_key_event_metric_facts"] if conversion_like_facts else []
        ),
        missing_read_contracts=(
            [] if conversion_like_facts else ["conversion_or_key_event_mapping"]
        ),
        conversion_like_metric_count=len(conversion_like_facts),
        dimensioned_behavior_metric_count=len(dimensioned_facts),
        landing_group_count=landing_group_count,
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=[] if conversion_like_facts else GA4_CONVERSION_BLOCKED_CLAIMS,
        next_step=(
            "Waliduj `act_review_ga4_tracking_quality` i sprawdź mapowanie "
            "konwersji/key events przed wnioskami o opłacalności."
        ),
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
    dimensioned_facts: list[MetricFact],
) -> list[Ga4DecisionItem]:
    decisions: list[Ga4DecisionItem] = []
    for index, item in enumerate(_unique_tactical_items(tactical_items), start=1):
        landing_page = item.dimensions.get("landing_page")
        source_medium = item.dimensions.get("source_medium")
        campaign_name = item.dimensions.get("campaign_name")
        wordpress_match = item.dimensions.get("wordpress_match")
        has_missing_reporting_dimension = any(
            value == "(not set)" for value in (landing_page, source_medium, campaign_name)
        )
        if item.intent == "tracking_gap" or has_missing_reporting_dimension:
            decision_type: Ga4DecisionType = "fix_measurement"
            title = _ga4_measurement_title(landing_page, source_medium)
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
                status=_ga4_decision_status(decision_type),
                priority=_ga4_decision_priority(decision_type, index),
                metric_tiles=_ga4_metric_tiles(item.metric_facts),
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
    if not decisions:
        decisions.extend(_ga4_decisions_from_dimensioned_facts(dimensioned_facts, action_ids))
    return sorted(decisions, key=lambda decision: (decision.priority, decision.id))[:6]


def _ga4_decisions_with_lineage(decisions: list[Ga4DecisionItem]) -> list[Ga4DecisionItem]:
    return [
        decision.model_copy(
            update={
                "knowledge_card_ids": _unique(
                    [*decision.knowledge_card_ids, *GA4_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": _unique([*decision.expert_rule_ids, *GA4_EXPERT_RULE_IDS]),
            }
        )
        for decision in decisions
    ]


def _ga4_decisions_from_dimensioned_facts(
    facts: list[MetricFact],
    action_ids: list[str],
) -> list[Ga4DecisionItem]:
    grouped: dict[tuple[str, str, str], list[MetricFact]] = {}
    for fact in facts:
        key = (
            fact.dimensions.get("landing_page", ""),
            fact.dimensions.get("source_medium", ""),
            fact.dimensions.get("campaign_name", ""),
        )
        grouped.setdefault(key, []).append(fact)

    decisions: list[Ga4DecisionItem] = []
    for index, ((landing_page, source_medium, campaign_name), group_facts) in enumerate(
        grouped.items(),
        start=1,
    ):
        has_missing_reporting_dimension = any(
            value == "(not set)" for value in (landing_page, source_medium, campaign_name)
        )
        if has_missing_reporting_dimension:
            decision_type: Ga4DecisionType = "fix_measurement"
            title = _ga4_measurement_title(landing_page, source_medium)
            rationale = (
                "GA4 ma wymiar `(not set)`, więc najpierw trzeba sprawdzić pomiar, "
                "UTM-y i atrybucję zamiast oceniać kampanię lub landing."
            )
            next_step = (
                "Zweryfikuj landing page, source/medium i campaign_name w GA4. "
                "Nie oceniaj jakości kampanii po wierszu z brakującymi wymiarami."
            )
            risk = ActionRisk.medium
        else:
            decision_type = "review_traffic_quality"
            title = f"Sprawdź jakość ruchu: {landing_page}"
            rationale = (
                "GA4 ma landing/source/campaign facts. To wystarcza do review jakości "
                "ruchu i message match, ale nie do claimów o ROAS albo revenue."
            )
            next_step = (
                "Porównaj landing, źródło i kampanię z intencją strony. Jeśli trzeba, "
                "waliduj `act_review_ga4_tracking_quality` jako review-only."
            )
            risk = ActionRisk.low

        decisions.append(
            Ga4DecisionItem(
                id=(
                    "ga4_decision_metric_"
                    f"{_slug(landing_page)}_{_slug(source_medium)}_{_slug(campaign_name)}"
                ),
                decision_type=decision_type,
                title=title,
                status=_ga4_decision_status(decision_type),
                priority=_ga4_decision_priority(decision_type, index),
                metric_tiles=_ga4_metric_tiles(group_facts),
                landing_page=landing_page,
                source_medium=source_medium,
                campaign_name=campaign_name,
                source_connectors=[GA4_CONNECTOR_ID],
                evidence_ids=_unique(fact.evidence_id for fact in group_facts),
                metric_facts=group_facts[:8],
                action_ids=action_ids,
                blocked_claims=[
                    "conversion rate",
                    "ROAS",
                    "revenue",
                    "profitability",
                ],
                rationale=rationale,
                next_step=next_step,
                risk=risk,
            )
        )
    return decisions


def _ga4_measurement_title(landing_page: str | None, source_medium: str | None) -> str:
    landing_label = landing_page or "brak landing page"
    source_label = source_medium or "brak source/medium"
    return f"GA4: napraw pomiar - {landing_label} / {source_label}"


def _ga4_decision_status(decision_type: Ga4DecisionType) -> Literal["ready", "blocked"]:
    if decision_type in {"fix_measurement", "review_landing_mapping"}:
        return "blocked"
    return "ready"


def _ga4_decision_priority(decision_type: Ga4DecisionType, index: int) -> int:
    base_priority = {
        "fix_measurement": 10,
        "review_landing_mapping": 30,
        "review_traffic_quality": 50,
    }[decision_type]
    return min(base_priority + index, 100)


def _ga4_metric_tiles(facts: Iterable[MetricFact]) -> dict[str, float | int | str]:
    latest_by_name: dict[str, MetricFact] = {}
    for fact in facts:
        latest_by_name.setdefault(fact.name, fact)

    tiles: dict[str, float | int | str] = {}
    for metric_name, label in (
        ("active_users", "aktywni"),
        ("sessions", "sesje"),
        ("event_count", "zdarzenia"),
        ("screen_page_views", "odsłony"),
    ):
        metric_fact = latest_by_name.get(metric_name)
        if metric_fact is None:
            continue
        value = _numeric_value(metric_fact.value)
        tiles[label] = int(value) if value.is_integer() else round(value, 2)

    engagement_fact = latest_by_name.get("engagement_rate")
    if engagement_fact is not None:
        engagement_value = _numeric_value(engagement_fact.value)
        tiles["engagement"] = _format_percent(engagement_value)
    return tiles


def _numeric_value(value: str | int | float) -> float:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(value)
    except ValueError:
        return 0.0


def _format_percent(value: float) -> str:
    percent_value = value * 100 if value <= 1 else value
    formatted = f"{percent_value:.2f}".rstrip("0").rstrip(".")
    return f"{formatted}%"


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
