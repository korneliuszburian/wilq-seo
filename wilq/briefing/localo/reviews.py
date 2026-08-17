"""Decomposed localo_diagnostics reviews implementation."""

from __future__ import annotations

from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.briefing.localo.labels import _label_localo_operator_summary
from wilq.briefing.localo.shared import (
    LOCALO_CONNECTOR_ID,
    _localo_missing_contracts_phrase,
    _missing_contract_ids,
)
from wilq.content.operator_copy import unique
from wilq.schemas import (
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    LocaloAccessProbe,
    LocaloDecisionItem,
    LocaloOperatorSummary,
    LocaloReadContractStatus,
)


def _operator_connector(connector: ConnectorStatus) -> ConnectorStatus:
    """Return the Localo status without configuration-field names for marketers."""
    missing_count = len(connector.missing_credentials)
    return connector.model_copy(
        update={
            "missing_credentials": [],
            "missing_credentials_summary_label": (
                f"{missing_count} pola dostępu wymagają konfiguracji"
                if missing_count
                else connector.missing_credentials_summary_label
            ),
            "available_credential_sources": [],
            "credential_source_summary_label": "Źródło konfiguracji do sprawdzenia",
            "required_env": [],
            "error": None,
        }
    )


def _operator_refresh(run: ConnectorRefreshRun | None) -> ConnectorRefreshRun | None:
    if run is None:
        return None
    summary = run.summary
    if run.status in {ConnectorRefreshStatus.blocked, ConnectorRefreshStatus.failed}:
        summary = "Ostatni odczyt Localo nie dostarczył danych widoczności."
    return run.model_copy(
        update={
            "missing_credentials": [],
            "checked_credentials": [],
            "summary": summary,
            "errors": [],
            "redacted": True,
        }
    )


def _operator_summary(
    decisions: list[LocaloDecisionItem],
    access_probe: LocaloAccessProbe,
    visibility_fact_count: int,
    read_contract_statuses: list[LocaloReadContractStatus],
) -> LocaloOperatorSummary:
    top_decisions = decisions[:4]
    missing_contracts = _missing_contract_ids(read_contract_statuses)
    return _label_localo_operator_summary(
        LocaloOperatorSummary(
            title="Co marketer ma wiedzieć o Localo",
            summary=_operator_summary_text(visibility_fact_count, missing_contracts),
            next_step=_operator_summary_next_step(visibility_fact_count, missing_contracts),
            review_decision_after_review=_operator_review_decision_after_review(
                visibility_fact_count,
                missing_contracts,
            ),
            review_question_for_operator=_operator_review_question(
                visibility_fact_count,
                missing_contracts,
            ),
            review_next_safe_click=_operator_review_next_safe_click(
                visibility_fact_count,
                top_decisions,
            ),
            review_action_ids=_operator_review_action_ids(top_decisions),
            top_decision_ids=[decision.id for decision in top_decisions],
            access_status=access_probe.status,
            visibility_fact_count=visibility_fact_count,
            missing_read_contracts=unique(
                contract
                for decision in top_decisions
                for contract in decision.missing_read_contracts
            ),
            read_contract_statuses=read_contract_statuses,
            source_connectors=unique(
                connector for decision in top_decisions for connector in decision.source_connectors
            )
            or [LOCALO_CONNECTOR_ID],
            evidence_ids=unique(
                [
                    *(
                        evidence_id
                        for decision in top_decisions
                        for evidence_id in decision.evidence_ids
                    ),
                    *access_probe.evidence_ids,
                ]
            ),
            action_ids=unique(
                action_id for decision in top_decisions for action_id in decision.action_ids
            ),
            blocked_claims=unique(
                claim for decision in top_decisions for claim in decision.blocked_claims
            ),
        )
    )


def _operator_summary_text(visibility_fact_count: int, missing_contracts: list[str]) -> str:
    if visibility_fact_count:
        if (
            "gbp_visibility" not in missing_contracts
            and "competitor_visibility" not in missing_contracts
        ):
            return (
                "Localo dostarczył agregaty miejsc, fraz, profilu firmy w Google, konkurencji "
                "i recenzji. WILQ może użyć ich do lokalnego sprawdzenia, ale nadal "
                "blokuje zadania lokalne, zapis zmian i obietnicę wzrostu widoczności "
                "bez osobnej akcji i dowodu efektu."
            )
        return (
            "Localo dostarczył agregaty widoczności, miejsc, fraz i recenzji. "
            "WILQ może użyć ich do lokalnego sprawdzenia, ale nadal blokuje profil "
            "firmy w Google, konkurencję, zapis zmian i obietnicę wzrostu "
            "widoczności bez osobnych danych."
        )
    return (
        "Ten widok pokazuje, czy Localo może już wspierać decyzje lokalnego SEO. "
        "Sam dostęp do Localo nie jest jeszcze dowodem rankingów, profilu firmy "
        "w Google, konkurencji ani recenzji, więc WILQ blokuje obietnice bez "
        "danych widoczności."
    )


def _operator_summary_next_step(
    visibility_fact_count: int,
    missing_contracts: list[str],
) -> str:
    if visibility_fact_count:
        if (
            "gbp_visibility" not in missing_contracts
            and "competitor_visibility" not in missing_contracts
        ):
            return (
                "Przejrzyj agregaty Localo: miejsca, frazy, profil firmy w Google, konkurencję "
                "i recenzje. Zadania lokalne i zapis zmian zostaw zablokowane."
            )
        return (
            "Przejrzyj agregaty Localo: miejsca, frazy, średnią widoczność i "
            "recenzje. Konkurencję, profil firmy w Google i zapis zmian zostaw zablokowane."
        )
    return (
        "Użyj top decyzji jako statusu źródła. Nie proponuj lokalnych działań "
        "SEO ani zmian w profilu firmy w Google, dopóki odczyt danych Localo "
        "nie dostarczy danych widoczności."
    )


def _operator_review_decision_after_review(
    visibility_fact_count: int,
    missing_contracts: list[str],
) -> str:
    if visibility_fact_count:
        if missing_contracts:
            return (
                "Po review przygotuj tylko listę lokalnych obserwacji i braków; "
                "zadania lokalne, zapis GBP i obietnicę poprawy widoczności zostaw zablokowane."
            )
        return (
            "Po review można przygotować listę lokalnych działań do osobnej akcji, "
            "ale bez zapisu GBP i bez obietnicy wzrostu widoczności."
        )
    return (
        "Po review potwierdź tylko stan dostępu Localo; decyzje lokalnego SEO zostają "
        "zablokowane do czasu odczytu danych widoczności."
    )


def _operator_review_question(
    visibility_fact_count: int,
    missing_contracts: list[str],
) -> str:
    if visibility_fact_count:
        missing_phrase = _localo_missing_contracts_phrase(missing_contracts)
        return (
            "Czy dostępne agregaty Localo wystarczą do briefu lokalnego review, "
            f"czy najpierw uzupełnić brakujące dane: {missing_phrase}?"
        )
    return (
        "Czy mamy odświeżyć Localo, zanim pokażemy marketerowi lokalne rankingi, GBP, "
        "konkurencję albo recenzje jako podstawę decyzji?"
    )


def _operator_review_next_safe_click(
    visibility_fact_count: int,
    decisions: list[LocaloDecisionItem],
) -> str:
    action_ids = _operator_review_action_ids(decisions)
    if action_ids:
        return (
            f"Kliknij podgląd `{action_ids[0]}`; to przygotuje review Localo, "
            "bez zapisu w profilu firmy i bez publikacji zmian."
        )
    if visibility_fact_count:
        return "Przejrzyj agregaty Localo i odśwież brakujące kontrakty przed decyzją."
    return "Uruchom odczyt Localo; nie oceniaj lokalnej widoczności z samego dostępu."


def _operator_review_action_ids(decisions: list[LocaloDecisionItem]) -> list[str]:
    return unique(
        action_id
        for decision in decisions
        for action_id in decision.action_ids
        if action_id == LOCALO_VISIBILITY_REVIEW_ACTION_ID
    )
