"""Decomposed ga4_diagnostics traffic implementation."""

from __future__ import annotations

from wilq.briefing.ga4.shared import (
    GA4_CONNECTOR_ID,
    _dimensioned_ga4_facts,
    _ga4_blocker_reason,
    _landing_group_count,
    _refresh_or_connector_evidence_ids,
    _tactical_landing_group_count,
    _tactical_metric_facts,
    _unique,
)
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshRun,
    Ga4ConversionReadinessContract,
    Ga4DecisionItem,
    Ga4DiagnosticSection,
    Ga4FreshnessAssessment,
    Ga4OperatorSummary,
    MetricFact,
    TacticalQueueItem,
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
            "WILQ pokazuje grupy ruchu do kontroli stron wejścia, źródeł ruchu i kampanii. "
            f"{conversion_note}"
            f"{freshness_note}"
        ),
        next_step=(
            "Przejdź przez top decyzje GA4, oddziel problem pomiaru od problemu "
            "jakości ruchu i sprawdź propozycję w WILQ do sprawdzenia."
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
            connector for decision in top_decisions for connector in decision.source_connectors
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
            "WILQ ma potwierdzoną konfigurację zdarzeń kluczowych, ale zwrot z reklam, "
            "opłacalność, spadek konwersji i wina kampanii nadal wymagają "
            "osobnych dowodów oraz kontekstu kosztów, historii i atrybucji."
        )
    if contract.status == "review_required":
        return (
            "GA4 zwraca kolumny konwersji lub zdarzeń kluczowych, ale WILQ nie ma "
            "potwierdzenia ich konfiguracji. Nie wolno na tej podstawie oceniać "
            "konwersji, przychodu ani opłacalności."
        )
    return (
        "Brak metryk konwersji oznacza, że nie wolno wyciągać wniosków o zwrot z reklam, "
        "przychód, spadku konwersji ani winie kampanii."
    )


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
            title="GA4: brak zestawienia strony wejścia, źródła ruchu i kampanii",
            status="blocked",
            summary=_ga4_blocker_reason(latest_refresh),
            diagnosis=(
                "WILQ nie ma metryk GA4 ze stroną wejścia, źródłem ruchu i kampanią, "
                "więc nie może ocenić jakości stron wejścia ani kampanii bez zmyślania."
            ),
            next_step="Uruchom odczyt GA4 i zbierz metryki stron wejścia, źródeł ruchu i kampanii.",
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["jakość strony wejścia", "jakość kampanii", "dopasowanie komunikatu"],
            risk=ActionRisk.medium,
        )
    if not dimensioned_facts:
        return Ga4DiagnosticSection(
            id="ga4_landing_behavior",
            title="GA4: jakość ruchu ze stron wejścia",
            status="ready",
            summary=(
                f"WILQ ma {_tactical_landing_group_count(tactical_items)} "
                "grup ruchu strona wejścia/źródło/kampania. Pełne metryki są "
                "dostępne w kolejce decyzji GA4."
            ),
            diagnosis=(
                "GA4 pozwala wskazać stronę wejścia do kontroli jakości "
                "ruchu. To nadal nie jest dowód konwersji, zwrotu z reklam ani opłacalności."
            ),
            next_step=(
                "Sprawdź stronę wejścia, źródło ruchu i kampanię w kolejce decyzji oraz oddziel "
                "problem pomiaru od problemu strony."
            ),
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_unique(
                evidence_id for item in tactical_items for evidence_id in item.evidence_ids
            ),
            metric_facts=_tactical_metric_facts(tactical_items)[:12],
            tactical_items=tactical_items[:6],
            action_ids=action_ids,
            blocked_claims=["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"],
            risk=ActionRisk.low,
        )
    return Ga4DiagnosticSection(
        id="ga4_landing_behavior",
        title="GA4: jakość ruchu ze stron wejścia",
        status="ready",
        summary=(
            f"WILQ ma {_landing_group_count(dimensioned_facts)} grup ruchu "
            f"strona wejścia/źródło/kampania i {len(dimensioned_facts)} metryk GA4."
        ),
        diagnosis=(
            "Fakty zachowania z GA4 pozwalają wskazać strony wejścia do kontroli jakości ruchu. "
            "To nadal nie jest dowód konwersji, zwrotu z reklam ani opłacalności."
        ),
        next_step=(
            "Najpierw sprawdź grupy z niskim zaangażowaniem i dopiero potem oceniaj "
            "dopasowanie komunikatu."
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
        blocked_claims=["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"],
        risk=ActionRisk.low,
    )
