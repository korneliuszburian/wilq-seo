"""Decomposed ga4_diagnostics labels implementation."""

from __future__ import annotations

from collections.abc import Iterable

from wilq.briefing.ga4.shared import GA4_CONNECTOR_ID
from wilq.content.operator_copy import unique
from wilq.operator_labels import action_count_label, source_connector_label
from wilq.schemas import (
    ConnectorRefreshRun,
    Ga4DecisionItem,
    Ga4DiagnosticSection,
    Ga4DiagnosticsResponse,
    MetricFact,
    connector_refresh_run_status_label,
)

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
    return unique(
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
    normalized = _enum_value(status)
    if normalized == "ready":
        return "konfiguracja zdarzeń potwierdzona"
    if normalized == "review_required":
        return "konfiguracja zdarzeń do potwierdzenia"
    return "blokuje wnioski o konwersjach"


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
    return unique(labels.get(claim, claim) for claim in claims)


def _enum_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)
