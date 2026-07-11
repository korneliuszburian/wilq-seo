from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import action_count_label, source_connector_label
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
    connector_refresh_has_live_data,
    connector_refresh_run_status_label,
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
    "współczynnik konwersji",
    "zwrot z reklam",
    "przychód",
    "opłacalność",
    "spadek konwersji",
    "diagnoza lejka",
    "ocena atrybucji",
]
GA4_READ_CONTRACT_LABELS = {
    "conversion_or_key_event_mapping": "powiązanie konwersji i zdarzeń kluczowych",
    "conversion_or_key_event_metric_facts": "metryki konwersji i zdarzeń kluczowych",
}
GA4_METRIC_FACT_LABELS = {
    "active_users": "aktywni użytkownicy",
    "conversions": "konwersje",
    "ecommerce_purchases": "zakupy e-commerce",
    "engagement_rate": "zaangażowanie",
    "event_count": "zdarzenia",
    "key_events": "zdarzenia kluczowe",
    "purchase_revenue": "przychód z zakupu",
    "screen_page_views": "odsłony",
    "sessions": "sesje",
    "total_revenue": "przychód razem",
    "transactions": "transakcje",
}
GA4_METRIC_DIMENSION_LABELS = {
    "campaign_name": "kampania",
    "landing_page": "strona wejścia",
    "source_medium": "źródło i medium ruchu",
}
GA4_DECISION_TYPE_LABELS = {
    "fix_measurement": "problem pomiaru",
    "review_landing_mapping": "sprawdzenie strony wejścia",
    "review_traffic_quality": "kontrola jakości ruchu",
}
GA4_SECTION_LABELS = {
    "ga4_landing_behavior": "Jakość ruchu ze stron wejścia",
    "ga4_tracking_readiness": "Gotowość pomiaru konwersji",
    "ga4_action_safety": "Bezpieczeństwo akcji GA4",
}
GA4_WORDPRESS_MATCH_LABELS = {
    "found": "potwierdzony",
    "missing": "niepotwierdzone w WordPress",
}
GA4_WORDPRESS_MATCH_CONFIDENCE_LABELS = {
    "exact_url": "dokładny adres URL",
    "host_alias_sitemap": "alias hosta z mapy strony",
    "path_fallback": "dopasowanie ścieżki",
    "missing": "dopasowanie niepotwierdzone",
}
GA4_KNOWLEDGE_CARD_IDS = ["card_ga4_behavior_diagnostics_playbook"]
GA4_EXPERT_RULE_IDS = ["ga4_diagnostics_v1", "ga4_platform_traps_v1"]
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
    metric_facts = [_ga4_metric_fact_with_marketer_labels(fact) for fact in metric_facts]
    live_data_available = bool(metric_facts) and (
        latest_refresh is None
        or connector_refresh_has_live_data(latest_refresh)
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
    response = Ga4DiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        connector_status_label=_ga4_connector_status_label(connector.status),
        latest_refresh=latest_refresh,
        latest_refresh_status_label=_ga4_refresh_status_label(latest_refresh)
        if latest_refresh
        else "",
        live_data_available=live_data_available,
        live_data_status_label=_ga4_live_data_status_label(live_data_available),
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
                *(evidence_id for section in sections for evidence_id in section.evidence_ids),
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
    return _ga4_response_with_marketer_labels(response)


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
            "WILQ ma metryki konwersji i zdarzeń kluczowych w dowodach, ale zwrot z reklam, "
            "opłacalność, spadek konwersji i wina kampanii nadal wymagają "
            "osobnych dowodów oraz kontekstu kosztów, historii i atrybucji."
        )
    return (
        "Brak metryk konwersji oznacza, że nie wolno wyciągać wniosków o zwrot z reklam, "
        "przychód, spadku konwersji ani winie kampanii."
    )


def _ga4_response_with_marketer_labels(
    response: Ga4DiagnosticsResponse,
) -> Ga4DiagnosticsResponse:
    return response.model_copy(
        update={
            "freshness_assessment": response.freshness_assessment.model_copy(
                update={
                    "state_label": _ga4_freshness_label(response.freshness_assessment.state),
                }
            ),
            "conversion_readiness_contract": (
                response.conversion_readiness_contract.model_copy(
                    update={
                        "status_label": _ga4_conversion_readiness_status_label(
                            response.conversion_readiness_contract.status
                        ),
                        "source_connector_labels": _ga4_source_connector_labels(
                            response.conversion_readiness_contract.source_connectors
                        ),
                        "evidence_summary_label": _ga4_evidence_summary_label(
                            response.conversion_readiness_contract.evidence_ids
                        ),
                        "action_summary_label": _ga4_action_summary_label(
                            response.conversion_readiness_contract.action_ids
                        ),
                    }
                )
            ),
            "operator_summary": response.operator_summary.model_copy(
                update={
                    "source_connector_labels": _ga4_source_connector_labels(
                        response.operator_summary.source_connectors
                    ),
                    "evidence_summary_label": _ga4_evidence_summary_label(
                        response.operator_summary.evidence_ids
                    ),
                    "action_summary_label": _ga4_action_summary_label(
                        response.operator_summary.action_ids
                    ),
                    "blocked_claim_labels": _ga4_blocked_claim_labels(
                        response.operator_summary.blocked_claims
                    ),
                }
            ),
            "decision_queue": [
                _ga4_decision_with_marketer_labels(decision) for decision in response.decision_queue
            ],
            "sections": [
                _ga4_section_with_marketer_labels(section) for section in response.sections
            ],
            "evidence_summary_label": _ga4_evidence_summary_label(response.evidence_ids),
            "source_connector_labels": _ga4_source_connector_labels(
                response.operator_summary.source_connectors
            ),
            "action_summary_label": _ga4_action_summary_label(response.action_ids),
        }
    )


def _ga4_decision_with_marketer_labels(decision: Ga4DecisionItem) -> Ga4DecisionItem:
    return decision.model_copy(
        update={
            "decision_type_label": GA4_DECISION_TYPE_LABELS.get(
                decision.decision_type,
                "typ decyzji GA4 do sprawdzenia",
            ),
            "status_label": _ga4_decision_status_label(decision.status),
            "wordpress_match_label": _ga4_optional_label(
                decision.wordpress_match,
                GA4_WORDPRESS_MATCH_LABELS,
            ),
            "wordpress_match_confidence_label": _ga4_optional_label(
                decision.wordpress_match_confidence,
                GA4_WORDPRESS_MATCH_CONFIDENCE_LABELS,
            ),
            "landing_page_label": _ga4_dimension_value_label(
                decision.landing_page,
                missing_label="brak strony wejścia w raporcie",
            ),
            "source_medium_label": _ga4_dimension_value_label(
                decision.source_medium,
                missing_label="brak źródła i medium w raporcie",
            ),
            "campaign_name_label": _ga4_dimension_value_label(
                decision.campaign_name,
                missing_label="brak kampanii w raporcie",
            ),
            "source_connector_labels": _ga4_source_connector_labels(decision.source_connectors),
            "evidence_summary_label": _ga4_evidence_summary_label(decision.evidence_ids),
            "action_summary_label": _ga4_action_summary_label(decision.action_ids),
            "metric_facts": [
                _ga4_metric_fact_with_marketer_labels(fact) for fact in decision.metric_facts
            ],
            "blocked_claim_labels": _ga4_blocked_claim_labels(decision.blocked_claims),
            "risk_label": _ga4_risk_label(decision.risk),
        }
    )


def _ga4_section_with_marketer_labels(section: Ga4DiagnosticSection) -> Ga4DiagnosticSection:
    return section.model_copy(
        update={
            "label": GA4_SECTION_LABELS.get(section.id, section.title),
            "status_label": _ga4_section_status_label(section.status),
            "source_connector_labels": _ga4_source_connector_labels(section.source_connectors),
            "evidence_summary_label": _ga4_evidence_summary_label(section.evidence_ids),
            "action_summary_label": _ga4_action_summary_label(section.action_ids),
            "metric_facts": [
                _ga4_metric_fact_with_marketer_labels(fact) for fact in section.metric_facts
            ],
            "blocked_claim_labels": _ga4_blocked_claim_labels(section.blocked_claims),
            "risk_label": _ga4_risk_label(section.risk),
        }
    )


def _ga4_metric_fact_with_marketer_labels(fact: MetricFact) -> MetricFact:
    return fact.model_copy(
        update={
            "metric_label": GA4_METRIC_FACT_LABELS.get(fact.name, "metryka GA4"),
            "dimension_labels": {
                key: GA4_METRIC_DIMENSION_LABELS.get(key, "wymiar GA4") for key in fact.dimensions
            },
            "dimension_value_labels": {
                key: _ga4_metric_dimension_value_label(key, value)
                for key, value in fact.dimensions.items()
            },
        }
    )


def _ga4_metric_dimension_value_label(key: str, value: str) -> str:
    if key == "landing_page":
        return _ga4_dimension_value_label(
            value,
            missing_label="brak strony wejścia w raporcie",
        )
    if key == "source_medium":
        return _ga4_dimension_value_label(
            value,
            missing_label="brak źródła i medium ruchu w raporcie",
        )
    if key == "campaign_name":
        return _ga4_dimension_value_label(
            value,
            missing_label="brak kampanii w raporcie",
        )
    return value


def _ga4_optional_label(value: str | None, labels: dict[str, str]) -> str | None:
    if value is None:
        return None
    return labels.get(value, "wartość GA4 do sprawdzenia")


def _ga4_dimension_value_label(value: str | None, *, missing_label: str) -> str:
    if value is None or value == "" or value == "(not set)":
        return missing_label
    return value


def _ga4_source_connector_labels(connector_ids: Iterable[str]) -> list[str]:
    labels = {
        GA4_CONNECTOR_ID: "GA4",
        "wordpress_ekologus": "WordPress ekologus.pl",
        "google_search_console": "Google Search Console",
    }
    return _unique(
        labels.get(connector_id, source_connector_label(connector_id))
        for connector_id in connector_ids
    )


def _ga4_evidence_summary_label(evidence_ids: Iterable[str]) -> str:
    count = len(list(evidence_ids))
    if count == 0:
        return "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def _ga4_action_summary_label(action_ids: Iterable[str]) -> str:
    return action_count_label(action_ids)


def _ga4_connector_status_label(status: object) -> str:
    normalized = _enum_value(status)
    labels = {
        "configured": "dostęp skonfigurowany",
        "missing_credentials": "brakuje dostępu",
        "disabled": "źródło wyłączone",
    }
    return labels.get(normalized, "status źródła do sprawdzenia")


def _ga4_refresh_status_label(run: ConnectorRefreshRun | object) -> str:
    if not isinstance(run, ConnectorRefreshRun):
        return "status odczytu do sprawdzenia"
    return connector_refresh_run_status_label(run)


def _ga4_live_data_status_label(live_data_available: bool) -> str:
    return "metryki GA4 dostępne" if live_data_available else "metryki GA4 niepotwierdzone"


def _ga4_freshness_label(status: object) -> str:
    normalized = _enum_value(status)
    labels = {
        "fresh": "dane świeże",
        "stale": "dane do odświeżenia",
        "missing": "odczyt niepotwierdzony",
        "blocked": "odczyt zablokowany",
    }
    return labels.get(normalized, "świeżość danych do sprawdzenia")


def _ga4_decision_status_label(status: object) -> str:
    return "zablokowane" if _enum_value(status) == "blocked" else "gotowe"


def _ga4_section_status_label(status: object) -> str:
    normalized = _enum_value(status)
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
        "missing": "metryki konwersji niepotwierdzone",
    }
    return labels.get(normalized, "status sekcji do sprawdzenia")


def _ga4_conversion_readiness_status_label(status: object) -> str:
    return "blokuje wnioski o konwersjach" if _enum_value(status) == "blocked" else "gotowe"


def _ga4_risk_label(risk: object) -> str:
    normalized = _enum_value(risk)
    labels = {
        "low": "niskie ryzyko",
        "medium": "średnie ryzyko",
        "high": "wysokie ryzyko",
        "critical": "ryzyko krytyczne",
    }
    return labels.get(normalized, "ryzyko do sprawdzenia")


def _ga4_blocked_claim_labels(claims: Iterable[str]) -> list[str]:
    labels = {
        "naprawiony pomiar": "pomiar naprawiony",
        "brak w pomiarze": "problem pomiaru",
    }
    return _unique(labels.get(claim, claim) for claim in claims)


def _enum_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)


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
                        f"Najnowsze metryki GA4 mają około {age_hours:.1f}h i są do odświeżenia."
                    ),
                    next_step=(
                        "Uruchom odczyt danych GA4, jeśli pytanie dotyczy "
                        "aktualnego stanu stron wejścia, źródeł ruchu albo kampanii."
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
                    f"Najnowsze metryki GA4 mają około {age_hours:.1f}h i mieszczą się "
                    f"w progu {GA4_STALE_AFTER_HOURS}h."
                ),
                next_step="Można użyć danych GA4 do sprawdzenia bez dodatkowego odświeżenia.",
            )
        return Ga4FreshnessAssessment(
            state="missing",
            latest_refresh_id=None,
            latest_refresh_completed_at=None,
            age_hours=None,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary="Brak zapisanego odczytu danych GA4.",
            next_step="Uruchom odczyt danych GA4 przed oceną aktualnej jakości ruchu.",
        )

    completed_at = latest_refresh.completed_at or latest_refresh.started_at
    age_hours = round((utc_now() - completed_at).total_seconds() / 3600, 2)
    if not connector_refresh_has_live_data(latest_refresh):
        return Ga4FreshnessAssessment(
            state="blocked",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=GA4_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                "Ostatni odczyt GA4 nie zakończył się pełnym pobraniem metryk. "
                f"Status odczytu: {_ga4_refresh_status_label(latest_refresh)}."
            ),
            next_step=(
                "Napraw blocker odczytu i uruchom ponownie odczyt danych GA4 przed "
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
                f"Ostatni odczyt danych GA4 ma około {age_hours:.1f}h i jest do odświeżenia. "
                "To wystarcza do przeglądu nieświeżych danych, "
                "ale nie do obietnic o bieżącym stanie ruchu."
            ),
            next_step=(
                "Uruchom odczyt danych GA4, jeśli pytanie dotyczy aktualnego "
                "stanu stron wejścia, źródeł ruchu albo kampanii."
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
            f"Ostatni odczyt danych GA4 ma około {age_hours:.1f}h i mieści się "
            f"w progu {GA4_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć danych GA4 do sprawdzenia bez dodatkowego odświeżenia.",
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


def _tracking_readiness_section(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4DiagnosticSection:
    conversion_like_facts = [fact for fact in facts if fact.name in GA4_CONVERSION_METRIC_NAMES]
    dimensioned_facts = _dimensioned_ga4_facts(facts)
    tactical_group_count = _tactical_landing_group_count(tactical_items)
    if not facts:
        return Ga4DiagnosticSection(
            id="ga4_tracking_readiness",
            title="GA4: brak metryk zachowania",
            status="blocked",
            summary=_ga4_blocker_reason(latest_refresh),
            diagnosis="Brak metryk GA4 oznacza blokadę pomiaru, nie spadek jakości ruchu.",
            next_step="Odśwież odczyt GA4 i dopiero potem sprawdzaj problemy pomiaru.",
            source_connectors=[GA4_CONNECTOR_ID],
            evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
            action_ids=action_ids,
            blocked_claims=["brak w pomiarze", "spadek konwersji", "spadek w lejku"],
            risk=ActionRisk.medium,
        )
    return Ga4DiagnosticSection(
        id="ga4_tracking_readiness",
        title="GA4: gotowość pomiaru konwersji",
        status="ready" if conversion_like_facts else "missing",
        summary=(
            f"WILQ ma {len(dimensioned_facts)} metryk zachowania, "
            f"{tactical_group_count} grup stron wejścia i "
            f"{len(conversion_like_facts)} metryk konwersji albo kluczowych zdarzeń."
        ),
        diagnosis=(
            "Aktualne dane wspierają ocenę jakości ruchu. Jeżeli brakuje metryk "
            "konwersji albo kluczowych zdarzeń, WILQ musi oznaczyć konwersje jako "
            "brakujący wymiar analizy."
        ),
        next_step=(
            "Sprawdź propozycję w WILQ i przygotuj checklistę jakości pomiaru bez zapisu zmian."
        ),
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_unique(fact.evidence_id for fact in facts[:20]),
        metric_facts=[*dimensioned_facts[:8], *conversion_like_facts[:4]],
        tactical_items=tactical_items[:4],
        action_ids=action_ids,
        blocked_claims=[
            "spadek konwersji",
            "diagnoza lejka",
            "ocena atrybucji",
        ],
        risk=ActionRisk.low if conversion_like_facts else ActionRisk.medium,
    )


def _conversion_readiness_contract(
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> Ga4ConversionReadinessContract:
    conversion_like_facts = [fact for fact in facts if fact.name in GA4_CONVERSION_METRIC_NAMES]
    dimensioned_facts = _dimensioned_ga4_facts(facts)
    landing_group_count = max(
        _landing_group_count(dimensioned_facts),
        _tactical_landing_group_count(tactical_items),
    )
    status: Literal["ready", "blocked"] = "ready" if conversion_like_facts else "blocked"
    available_read_contracts = (
        ["conversion_or_key_event_metric_facts"] if conversion_like_facts else []
    )
    missing_read_contracts = [] if conversion_like_facts else ["conversion_or_key_event_mapping"]
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
        title="GA4: gotowość konwersji i zdarzeń kluczowych",
        summary=(
            "WILQ może oceniać jakość ruchu z GA4, ale obietnice konwersji, "
            "zwrotu z reklam, przychodu i opłacalności wymagają osobnych metryk konwersji "
            "albo zdarzeń kluczowych."
        ),
        allowed_metrics=sorted(GA4_CONVERSION_METRIC_NAMES),
        available_read_contracts=available_read_contracts,
        available_read_contract_labels=_ga4_read_contract_labels(available_read_contracts),
        missing_read_contracts=missing_read_contracts,
        missing_read_contract_labels=_ga4_read_contract_labels(missing_read_contracts),
        conversion_like_metric_count=len(conversion_like_facts),
        dimensioned_behavior_metric_count=len(dimensioned_facts),
        landing_group_count=landing_group_count,
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocked_claims=[] if conversion_like_facts else GA4_CONVERSION_BLOCKED_CLAIMS,
        next_step=(
            "Sprawdź jakość pomiaru w WILQ i potwierdź powiązanie "
            "konwersji i zdarzeń kluczowych przed wnioskami o opłacalności."
        ),
        risk=ActionRisk.low if conversion_like_facts else ActionRisk.medium,
    )


def _ga4_read_contract_labels(values: Iterable[str]) -> list[str]:
    return [
        GA4_READ_CONTRACT_LABELS.get(value, "zakres danych GA4 do sprawdzenia") for value in values
    ]


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
        summary="Akcje GA4 pozostają w trybie przygotowania i nie zapisują zmian w pomiarze.",
        diagnosis=(
            "WILQ może przygotować listę sprawdzenia jakości pomiaru "
            "i przegląd stron wejścia. Nie może "
            "zmieniać konfiguracji GA4 ani twierdzić, że naprawił pomiar bez osobnego "
            "potwierdzenia, sprawdzenia i audytu."
        ),
        next_step="Sprawdź jakość pomiaru w WILQ i zatrzymaj zapis zmian.",
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=action_ids,
        blocked_claims=["zapis w GA4", "wdrożona konfiguracja konwersji", "naprawiony pomiar"],
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
                "Sprawdź stronę wejścia, źródło i medium ruchu, UTM-y i konfigurację raportu. "
                "Nie oceniaj kampanii ani strony po tym wierszu."
            )
            risk = ActionRisk.medium
        elif wordpress_match == "missing":
            decision_type = "review_landing_mapping"
            title = f"Sprawdź stronę wejścia: {landing_page or 'brak strony wejścia'}"
            rationale = (
                "GA4 widzi ruch, ale spis treści WordPress nie potwierdza tej strony. "
                "Najpierw trzeba sprawdzić, czy URL istnieje i jest poprawnym adresem, "
                "zanim powstanie wniosek o treści."
            )
            next_step = (
                "Zweryfikuj, czy strona wejścia istnieje w WordPress lub mapie strony, "
                "a potem sprawdź "
                "dopasowanie komunikatu dla kampanii."
            )
            risk = ActionRisk.medium
        else:
            decision_type = "review_traffic_quality"
            title = f"Sprawdź jakość ruchu: {landing_page or 'brak strony wejścia'}"
            rationale = (
                "GA4 pokazuje ruch dla potwierdzonej strony wejścia. To wystarcza do "
                "oceny jakości ruchu i dopasowania komunikatu, ale nie do obietnic konwersji."
            )
            next_step = (
                "Porównaj stronę wejścia, źródło ruchu i kampanię z intencją strony. "
                "Nie oceniaj zwrotu z reklam "
                "ani przychodu bez osobnych metryk konwersji i kosztów."
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
                        "współczynnik konwersji",
                        "zwrot z reklam",
                        "przychód",
                        "opłacalność",
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
                "UTM-y i atrybucję zamiast oceniać kampanię lub stronę wejścia."
            )
            next_step = (
                "Zweryfikuj stronę wejścia, źródło i medium ruchu oraz nazwę kampanii w GA4. "
                "Nie oceniaj jakości kampanii po wierszu z brakującymi wymiarami."
            )
            risk = ActionRisk.medium
        else:
            decision_type = "review_traffic_quality"
            title = f"Sprawdź jakość ruchu: {landing_page}"
            rationale = (
                "GA4 ma fakty strony wejścia, źródła ruchu i kampanii. "
                "To wystarcza do sprawdzenia jakości ruchu i dopasowania komunikatu, "
                "ale nie do obietnic zwrotu z reklam albo przychodu."
            )
            next_step = (
                "Porównaj stronę wejścia, źródło ruchu i kampanię z intencją strony. Jeśli trzeba, "
                "sprawdź jakość pomiaru w WILQ jako akcję do sprawdzenia."
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
                    "współczynnik konwersji",
                    "zwrot z reklam",
                    "przychód",
                    "opłacalność",
                ],
                rationale=rationale,
                next_step=next_step,
                risk=risk,
            )
        )
    return decisions


def _ga4_measurement_title(landing_page: str | None, source_medium: str | None) -> str:
    landing_label = _ga4_dimension_value_label(
        landing_page,
        missing_label="brak strony wejścia w raporcie",
    )
    source_label = _ga4_dimension_value_label(
        source_medium,
        missing_label="brak źródła i medium w raporcie",
    )
    return f"GA4: napraw pomiar - {landing_label}; źródło ruchu: {source_label}"


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
        tiles["zaangażowanie"] = _format_percent(engagement_value)
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
    if not latest_refresh.metrics_persisted:
        return "Ostatni GA4 refresh nie utrwalił metryk."
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
