from __future__ import annotations

from wilq.actions.content_refresh import content_contract_label
from wilq.content.preflight.marketer_view import content_blocked_claim_labels
from wilq.operator_labels import (
    action_count_label,
    evidence_count_label,
    source_connector_label,
)
from wilq.schemas import (
    ConnectorRefreshRun,
    ConnectorStatus,
    ContentDiagnosticSection,
    MetricFact,
    connector_refresh_run_status_label,
)

CONTENT_CONNECTOR_STATUS_LABELS = {
    "configured": "dostęp skonfigurowany",
    "missing_credentials": "brakuje dostępu",
    "disabled": "źródło wyłączone",
    "missing_dependency": "brak zależności",
    "unreachable": "źródło niedostępne",
    "auth_error": "błąd dostępu",
    "rate_limited": "limit odczytu",
    "error": "błąd źródła",
}
CONTENT_REFRESH_STATUS_LABELS = {
    "completed": "zakończony",
    "blocked": "zablokowany",
    "failed": "błąd",
}
CONTENT_METRIC_FACT_LABELS = {
    "ahrefs_backlink_gap_count": "Luki linków z Ahrefs",
    "ahrefs_competitor_page_count": "Strony konkurencji z Ahrefs",
    "ahrefs_content_gap_count": "Luki treści z Ahrefs",
    "ahrefs_organic_keyword_gap_count": "Luki fraz z Ahrefs",
    "ahrefs_referring_domain_gap_count": "Luki domen linkujących z Ahrefs",
    "ahrefs_top_page_gap_count": "Mocne strony konkurencji",
    "average_position": "Pozycja",
    "clicks": "Kliknięcia",
    "content_object_count": "Obiekty WordPress",
    "content_object_seen": "Treść w spisie",
    "ctr": "CTR",
    "engaged_sessions": "Sesje zaangażowane",
    "engagement_rate": "Współczynnik zaangażowania",
    "impressions": "Wyświetlenia",
    "pages_total": "Strony WordPress",
    "posts_total": "Wpisy WordPress",
    "sessions": "Sesje",
}


def content_connector_with_api_label(connector: ConnectorStatus) -> ConnectorStatus:
    return connector.model_copy(
        update={"status_label": content_connector_status_label(str(connector.status))}
    )


def content_refresh_with_api_label(refresh: ConnectorRefreshRun) -> ConnectorRefreshRun:
    return refresh.model_copy(
        update={
            "connector_label": source_connector_label(refresh.connector_id),
            "status_label": content_refresh_status_label(refresh),
        }
    )


def content_live_data_status_label(live_data_available: bool) -> str:
    return (
        "dane GSC i WordPress dostępne"
        if live_data_available
        else "brak danych GSC lub WordPress do decyzji"
    )


def content_section_with_api_labels(
    section: ContentDiagnosticSection,
) -> ContentDiagnosticSection:
    return section.model_copy(
        update={
            "metric_facts": [
                content_metric_fact_with_api_label(fact) for fact in section.metric_facts
            ],
            "evidence_summary_label": evidence_count_label(section.evidence_ids),
            "action_summary_label": action_count_label(section.action_ids),
            "blocked_claim_labels": content_blocked_claim_labels(section.blocked_claims),
        }
    )


def content_metric_fact_with_api_label(fact: MetricFact) -> MetricFact:
    return fact.model_copy(update={"metric_label": content_metric_fact_label(fact.name)})


def content_connector_status_label(value: str) -> str:
    return CONTENT_CONNECTOR_STATUS_LABELS.get(value, content_contract_label(value))


def content_refresh_status_label(value: ConnectorRefreshRun | str) -> str:
    if isinstance(value, ConnectorRefreshRun):
        if not value.metrics_persisted:
            return connector_refresh_run_status_label(value)
        status = getattr(value.status, "value", value.status)
        return CONTENT_REFRESH_STATUS_LABELS.get(str(status), content_contract_label(str(status)))
    return CONTENT_REFRESH_STATUS_LABELS.get(value, content_contract_label(value))


def content_metric_fact_label(value: str) -> str:
    return CONTENT_METRIC_FACT_LABELS.get(value, content_contract_label(value))
