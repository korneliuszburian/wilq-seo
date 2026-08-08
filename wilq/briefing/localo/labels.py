"""Decomposed localo_diagnostics labels implementation."""

from __future__ import annotations

from collections.abc import Iterable

from wilq.briefing.localo.shared import LOCALO_CONNECTOR_ID, _unique
from wilq.briefing.localo_labels import (
    localo_contract_label,
    localo_evidence_label,
    localo_metric_fact_label,
)
from wilq.operator_labels import source_connector_label
from wilq.schemas import (
    ConnectorRefreshRun,
    LocaloAccessProbe,
    LocaloDecisionItem,
    LocaloDiagnosticSection,
    LocaloOperatorSummary,
    LocaloReadContractStatus,
    connector_refresh_run_status_label,
)


def _label_localo_access_probe(probe: LocaloAccessProbe) -> LocaloAccessProbe:
    return probe.model_copy(
        update={
            "status_label": _localo_access_status_label(probe.status),
            "access_check_label": _localo_access_check_label(probe.mcp_initialize_status),
            "authorization_code_supported_label": _localo_bool_label(
                probe.authorization_code_supported
            ),
            "authorization_readiness_label": _localo_readiness_label(
                probe.authorization_code_supported,
                ready="gotowe do połączenia",
                blocked="brak gotowej autoryzacji",
                unknown="autoryzacja niepotwierdzona",
            ),
            "pkce_s256_supported_label": _localo_bool_label(probe.pkce_s256_supported),
            "secure_readiness_label": _localo_readiness_label(
                probe.pkce_s256_supported,
                ready="bezpieczne połączenie gotowe",
                blocked="brak potwierdzenia bezpiecznego połączenia",
                unknown="bezpieczeństwo połączenia niepotwierdzone",
            ),
            "access_token_present_label": _localo_token_presence_label(probe.access_token_present),
            "credential_readiness_label": _localo_readiness_label(
                probe.access_token_present,
                ready="dostęp lokalny gotowy",
                blocked="brak lokalnego dostępu",
                unknown="lokalny dostęp niepotwierdzony",
            ),
            "evidence_summary_label": _localo_evidence_summary_label(probe.evidence_ids),
        }
    )


def _label_localo_section(section: LocaloDiagnosticSection) -> LocaloDiagnosticSection:
    return section.model_copy(
        update={
            "status_label": _localo_section_status_label(section.status),
            "source_connector_labels": _localo_source_connector_labels(section.source_connectors),
            "evidence_summary_label": _localo_evidence_summary_label(section.evidence_ids),
            "blocked_claim_labels": section.blocked_claims,
        }
    )


def _label_localo_read_contract_status(
    contract_status: LocaloReadContractStatus,
) -> LocaloReadContractStatus:
    return contract_status.model_copy(
        update={
            "id_label": _localo_contract_label(str(contract_status.id)),
            "status_label": _localo_read_contract_status_label(contract_status.status),
            "metric_fact_labels": {
                name: _localo_metric_fact_label(name) for name in contract_status.metric_fact_names
            },
            "blocked_claim_labels": contract_status.blocked_claims,
        }
    )


def _label_localo_decision(decision: LocaloDecisionItem) -> LocaloDecisionItem:
    return decision.model_copy(
        update={
            "decision_type_label": _localo_decision_type_label(decision.decision_type),
            "status_label": _localo_decision_status_label(decision.status),
            "access_status_label": _localo_access_status_label(decision.access_status),
            "priority_label": _localo_priority_label(decision.priority),
            "allowed_evidence_labels": [
                _localo_evidence_label(value) for value in decision.allowed_evidence
            ],
            "missing_read_contract_labels": [
                _localo_contract_label(value) for value in decision.missing_read_contracts
            ],
            "source_connector_labels": _localo_source_connector_labels(decision.source_connectors),
            "evidence_summary_label": _localo_evidence_summary_label(decision.evidence_ids),
            "metric_fact_labels": {
                fact.name: _localo_metric_fact_label(fact.name) for fact in decision.metric_facts
            },
            "blocked_claim_labels": decision.blocked_claims,
        }
    )


def _label_localo_operator_summary(
    summary: LocaloOperatorSummary,
) -> LocaloOperatorSummary:
    return summary.model_copy(
        update={
            "access_status_label": _localo_access_status_label(summary.access_status),
            "missing_read_contract_labels": [
                _localo_contract_label(value) for value in summary.missing_read_contracts
            ],
            "source_connector_labels": _localo_source_connector_labels(summary.source_connectors),
            "evidence_summary_label": _localo_evidence_summary_label(summary.evidence_ids),
            "blocked_claim_labels": summary.blocked_claims,
        }
    )


def _localo_decision_status_label(status: str) -> str:
    labels = {"ready": "gotowe", "blocked": "zablokowane"}
    return labels.get(status, "status decyzji do sprawdzenia")


def _localo_section_status_label(status: str) -> str:
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
        "missing": "zakres danych niepodłączony",
    }
    return labels.get(status, "status sekcji do sprawdzenia")


def _localo_read_contract_status_label(status: str) -> str:
    labels = {"ready": "gotowe", "missing": "zakres danych niepotwierdzony"}
    return labels.get(status, "status danych do sprawdzenia")


def _localo_decision_type_label(value: str) -> str:
    labels = {
        "access_ready_wait_for_visibility_facts": "status źródła",
        "fix_access": "napraw dostęp",
        "review_local_visibility": "przejrzyj widoczność",
        "block_visibility_claims": "blokada obietnic",
    }
    return labels.get(value, "typ decyzji Localo do sprawdzenia")


def _localo_connector_status_label(status: str) -> str:
    labels = {
        "configured": "dostęp skonfigurowany",
        "missing_credentials": "brakuje dostępu",
        "disabled": "źródło wyłączone",
    }
    return labels.get(status, "status źródła do sprawdzenia")


def _localo_refresh_status_label(run: ConnectorRefreshRun | object) -> str:
    if not isinstance(run, ConnectorRefreshRun):
        return "status odczytu do sprawdzenia"
    return connector_refresh_run_status_label(run)


def _localo_access_status_label(status: str) -> str:
    labels = {
        "access_ready": "dostęp działa",
        "access_blocked": "dostęp zablokowany",
        "unknown": "dostęp niepewny",
    }
    return labels.get(status, "dostęp niepewny")


def _localo_access_check_label(status: int | None) -> str:
    if status == 200:
        return "połączenie potwierdzone"
    if status is None:
        return "połączenie niepotwierdzone"
    return "połączenie zablokowane"


def _localo_readiness_label(
    value: bool | None,
    *,
    ready: str,
    blocked: str,
    unknown: str,
) -> str:
    if value is True:
        return ready
    if value is False:
        return blocked
    return unknown


def _localo_bool_label(value: bool | None) -> str:
    if value is True:
        return "tak"
    if value is False:
        return "nie"
    return "niepotwierdzone"


def _localo_token_presence_label(value: bool | None) -> str:
    if value is True:
        return "token obecny"
    if value is False:
        return "token nieobecny"
    return "stan tokena niepotwierdzony"


def _localo_source_connector_labels(connector_ids: Iterable[str]) -> list[str]:
    labels = {
        LOCALO_CONNECTOR_ID: "Localo",
    }
    return _unique(
        labels.get(connector_id, source_connector_label(connector_id))
        for connector_id in connector_ids
    )


def _localo_evidence_summary_label(evidence_ids: Iterable[str]) -> str:
    count = len(list(evidence_ids))
    if count == 0:
        return "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def _localo_priority_label(priority: int) -> str:
    if priority <= 10:
        return "pilne"
    if priority <= 30:
        return "wysoki priorytet"
    if priority <= 60:
        return "średni priorytet"
    return "niski priorytet"


def _localo_contract_label(value: str) -> str:
    return localo_contract_label(value)


def _localo_evidence_label(value: str) -> str:
    return localo_evidence_label(value)


def _localo_metric_fact_label(value: str) -> str:
    return localo_metric_fact_label(value)
