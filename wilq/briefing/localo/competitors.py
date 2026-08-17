"""Decomposed localo_diagnostics competitors implementation."""

from __future__ import annotations

from wilq.briefing.localo.labels import _label_localo_decision
from wilq.briefing.localo.shared import (
    LOCALO_BLOCKED_CLAIMS,
    LOCALO_CONNECTOR_ID,
    LOCALO_EXPERT_RULE_IDS,
    LOCALO_KNOWLEDGE_CARD_IDS,
    LOCALO_VISIBILITY_READ_CONTRACTS,
    _blocked_claims_for_missing_contracts,
    _localo_aggregate_count_label,
    _localo_contracts_phrase,
    _localo_missing_contracts_phrase,
    _localo_visibility_action_ids,
    _localo_visibility_tiles,
    _missing_visibility_contracts,
    _present_contracts,
)
from wilq.content.operator_copy import unique
from wilq.schemas import (
    ActionRisk,
    LocaloAccessProbe,
    LocaloDecisionItem,
    LocaloReadContractStatus,
    MetricFact,
)


def _localo_decision_queue(
    access_probe: LocaloAccessProbe,
    visibility_facts: list[MetricFact],
    read_contract_statuses: list[LocaloReadContractStatus],
) -> list[LocaloDecisionItem]:
    if visibility_facts:
        present_contracts = _present_contracts(visibility_facts)
        missing_contracts = _missing_visibility_contracts(present_contracts)
        blocked_claims = _blocked_claims_for_missing_contracts(missing_contracts)
        action_ids = _localo_visibility_action_ids(visibility_facts)
        decisions = [
            LocaloDecisionItem(
                id="localo_review_visibility_facts",
                decision_type="review_local_visibility",
                status="ready",
                title="Przejrzyj agregaty widoczności lokalnej z Localo",
                summary=(
                    f"WILQ ma {_localo_aggregate_count_label(len(visibility_facts))}: "
                    f"{_localo_contracts_phrase(present_contracts)}."
                ),
                rationale=(
                    "Localo dostarczył agregaty dla miejsc, monitorowanych fraz "
                    "i obsługiwanych danych widoczności. To pozwala na sprawdzenie, "
                    "ale nie na obietnicę poprawy widoczności ani zapis zmian."
                ),
                next_step=(
                    "Sprawdź średnią widoczność, pozycje w siatce lokalnej, profil firmy "
                    "w Google, konkurencję i stan recenzji. Zadania lokalne i zapis zmian "
                    "zostaw zablokowane."
                ),
                access_status=access_probe.status,
                priority=20,
                metric_tiles=_localo_visibility_tiles(visibility_facts, missing_contracts),
                allowed_evidence=present_contracts,
                missing_read_contracts=missing_contracts,
                read_contract_statuses=read_contract_statuses,
                source_connectors=[LOCALO_CONNECTOR_ID],
                evidence_ids=unique(
                    [*(fact.evidence_id for fact in visibility_facts), *access_probe.evidence_ids]
                ),
                metric_facts=visibility_facts[:12],
                action_ids=action_ids,
                blocked_claims=blocked_claims,
                risk=ActionRisk.low,
            )
        ]
        if missing_contracts:
            decisions.append(
                _blocked_visibility_decision(
                    access_probe,
                    missing_contracts=missing_contracts,
                    blocked_claims=blocked_claims,
                    read_contract_statuses=read_contract_statuses,
                )
            )
        return decisions

    if access_probe.status == "access_ready":
        return [
            LocaloDecisionItem(
                id="localo_access_ready_wait_for_visibility_facts",
                decision_type="access_ready_wait_for_visibility_facts",
                status="ready",
                title="Dostęp Localo działa; brakuje rankingów i danych profilu firmy w Google",
                summary=(
                    "Localo potwierdził dostęp do odczytu danych. WILQ nie ma jeszcze "
                    "lokalnych rankingów, danych profilu firmy w Google, konkurencji ani recenzji."
                ),
                rationale=(
                    "To jest gotowość dostępu do Localo, nie diagnoza lokalnej widoczności. "
                    "Marketer nie powinien traktować tego jako zadania optymalizacyjnego."
                ),
                next_step=(
                    "Zostaw Localo jako status źródła i dodaj odczyt danych rankingów, "
                    "profilu firmy w Google, konkurencji i recenzji."
                ),
                access_status=access_probe.status,
                priority=30,
                metric_tiles={
                    "dostęp Localo": 1,
                    "dane Localo": 0,
                    "brakujące dane": len(LOCALO_VISIBILITY_READ_CONTRACTS),
                },
                allowed_evidence=["mcp_initialize", "oauth_metadata", "local_access_presence"],
                missing_read_contracts=LOCALO_VISIBILITY_READ_CONTRACTS,
                read_contract_statuses=read_contract_statuses,
                source_connectors=[LOCALO_CONNECTOR_ID],
                evidence_ids=access_probe.evidence_ids,
                action_ids=[],
                blocked_claims=LOCALO_BLOCKED_CLAIMS,
                risk=ActionRisk.low,
            ),
            _blocked_visibility_decision(access_probe),
        ]

    return [
        LocaloDecisionItem(
            id="localo_fix_access_before_visibility_review",
            decision_type="fix_access",
            status="blocked",
            title="Dokończ dostęp Localo przed lokalnymi rekomendacjami",
            summary=access_probe.summary,
            rationale=(
                "Bez działającego dostępu Localo WILQ nie może pobrać rankingów, "
                "danych profilu firmy w Google ani dowodów o konkurencji."
            ),
            next_step="Dokończ dostęp Localo i odczyt danych, potem wróć do widoku Localo.",
            access_status=access_probe.status,
            priority=5,
            metric_tiles={
                "dostęp Localo": 0,
                "brakujące dane": len(LOCALO_VISIBILITY_READ_CONTRACTS) + 1,
            },
            allowed_evidence=[],
            missing_read_contracts=["mcp_initialize", *LOCALO_VISIBILITY_READ_CONTRACTS],
            source_connectors=[LOCALO_CONNECTOR_ID],
            evidence_ids=access_probe.evidence_ids,
            action_ids=[],
            blocked_claims=LOCALO_BLOCKED_CLAIMS,
            risk=ActionRisk.medium,
        ),
        _blocked_visibility_decision(access_probe),
    ]


def _localo_decisions_with_lineage(
    decisions: list[LocaloDecisionItem],
) -> list[LocaloDecisionItem]:
    return [
        _label_localo_decision(decision).model_copy(
            update={
                "knowledge_card_ids": unique(
                    [*decision.knowledge_card_ids, *LOCALO_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": unique([*decision.expert_rule_ids, *LOCALO_EXPERT_RULE_IDS]),
            }
        )
        for decision in decisions
    ]


def _blocked_visibility_decision(
    access_probe: LocaloAccessProbe,
    *,
    missing_contracts: list[str] | None = None,
    blocked_claims: list[str] | None = None,
    read_contract_statuses: list[LocaloReadContractStatus] | None = None,
) -> LocaloDecisionItem:
    effective_missing_contracts = missing_contracts or LOCALO_VISIBILITY_READ_CONTRACTS
    effective_blocked_claims = blocked_claims or LOCALO_BLOCKED_CLAIMS
    has_partial_visibility_facts = missing_contracts is not None
    missing_contracts_phrase = _localo_missing_contracts_phrase(effective_missing_contracts)
    return LocaloDecisionItem(
        id="localo_block_visibility_claims_without_read_contract",
        decision_type="block_visibility_claims",
        status="blocked",
        title=(
            f"Blokuj {missing_contracts_phrase} bez pełnych danych Localo"
            if has_partial_visibility_facts
            else "Nie wyciągaj wniosków o lokalnej widoczności bez danych Localo"
        ),
        summary=(
            (
                "WILQ ma częściowe agregaty Localo, ale blokuje obietnice zależne od "
                f"brakujących danych: {missing_contracts_phrase} i zapis zmian."
            )
            if has_partial_visibility_facts
            else (
                "WILQ blokuje obietnice o rankingach, profilu firmy w Google, "
                "konkurencji, recenzjach i wzroście widoczności, dopóki Localo "
                "nie dostarczy tych danych."
            )
        ),
        rationale=(
            (
                "Częściowe dane są wystarczające do sprawdzenia agregatów, ale nie do "
                "rozszerzania ich na nieobsługiwane obszary Localo."
            )
            if has_partial_visibility_facts
            else (
                "Dostęp do źródła nie jest metryką marketingową. To chroni dashboard i "
                "skille przed udawaniem lokalnego SEO insightu."
            )
        ),
        next_step=(
            (
                "Przejrzyj dostępne agregaty Localo, a brakujące dane "
                f"{missing_contracts_phrase} dodaj przed szerszymi obietnicami lub zapisem zmian."
            )
            if has_partial_visibility_facts
            else (
                "Najpierw dodaj odczyt danych Localo; dopiero potem buduj "
                "lokalne akcje do sprawdzenia."
            )
        ),
        access_status=access_probe.status,
        priority=10,
        metric_tiles={
            "blokady obietnic": len(effective_blocked_claims),
            "brakujące dane": len(effective_missing_contracts),
        },
        allowed_evidence=["mcp_initialize"] if access_probe.status == "access_ready" else [],
        missing_read_contracts=effective_missing_contracts,
        read_contract_statuses=read_contract_statuses or [],
        source_connectors=[LOCALO_CONNECTOR_ID],
        evidence_ids=access_probe.evidence_ids,
        action_ids=[],
        blocked_claims=effective_blocked_claims,
        risk=ActionRisk.medium,
    )
