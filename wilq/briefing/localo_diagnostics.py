from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.briefing.localo_labels import (
    localo_contract_label,
    localo_evidence_label,
    localo_metric_fact_label,
)
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import source_connector_label
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    LocaloAccessProbe,
    LocaloDecisionItem,
    LocaloDiagnosticSection,
    LocaloDiagnosticsResponse,
    LocaloOperatorSummary,
    LocaloReadContractStatus,
    MetricFact,
    connector_refresh_has_live_data,
    connector_refresh_run_status_label,
)
from wilq.storage.metric_store import metric_store

LOCALO_CONNECTOR_ID = "localo"
LOCALO_METRIC_FACT_LIMIT = 120
LOCALO_PROBE_METRIC_NAMES = {
    "access_token_present",
    "api",
    "authorization_code_supported",
    "mcp_initialize_status",
    "pkce_s256_supported",
}
LOCALO_VISIBILITY_READ_CONTRACTS = [
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks",
]
LOCALO_CONTRACT_FACT_NAMES = {
    "place_inventory": {
        "localo_active_place_count",
        "localo_place_detail_count",
    },
    "local_rankings": {
        "localo_tracked_keyword_count",
        "localo_visibility_score_count",
        "localo_avg_visibility_current",
        "localo_avg_visibility_change",
        "localo_latest_grid_position_count",
        "localo_avg_latest_grid_position",
        "localo_keyword_volume_count",
        "localo_total_keyword_volume",
    },
    "reviews": {
        "localo_avg_rating",
        "localo_snapshot_reviews_count",
        "localo_reviews_count",
        "localo_reviews_replied_count",
        "localo_reviews_removed_count",
        "localo_review_reply_rate",
    },
    "gbp_visibility": {
        "localo_gbp_impressions_total",
        "localo_gbp_actions_total",
        "localo_gbp_metric_point_count",
    },
    "competitor_visibility": {
        "localo_competitor_count",
        "localo_favorite_competitor_count",
        "localo_competitor_change_count",
    },
}
LOCALO_CONTRACT_ORDER = [
    "place_inventory",
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks",
]
LOCALO_BLOCKED_CLAIMS = [
    "lokalne rankingi",
    "wyniki profilu firmy w Google",
    "widoczności konkurencji",
    "poprawa widoczności lokalnej",
    "tempo nowych opinii",
]
LOCALO_KNOWLEDGE_CARD_IDS = ["card_localo_local_seo_playbook"]
LOCALO_EXPERT_RULE_IDS = ["local_visibility_v1", "local_reviews_v1"]


def build_localo_diagnostics() -> LocaloDiagnosticsResponse:
    connector = get_connector_status(LOCALO_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Localo connector is not registered.")

    refresh_runs = list_connector_refresh_runs(connector_id=LOCALO_CONNECTOR_ID)
    latest_refresh = _latest_relevant_localo_refresh(refresh_runs)
    metric_facts = _metric_facts_for_refresh(latest_refresh)
    visibility_facts = _visibility_facts(metric_facts)
    access_probe = _label_localo_access_probe(
        _access_probe(
            connector_missing=connector.missing_credentials,
            run=latest_refresh,
        )
    )
    live_data_available = bool(visibility_facts)
    sections = _localo_sections(access_probe, latest_refresh, visibility_facts)
    read_contract_statuses = _localo_read_contract_statuses(visibility_facts)
    decision_queue = _localo_decisions_with_lineage(
        _localo_decision_queue(
            access_probe,
            visibility_facts,
            read_contract_statuses,
        )
    )
    action_ids = _unique(
        action_id for decision in decision_queue for action_id in decision.action_ids
    )

    return LocaloDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        connector_status_label=_localo_connector_status_label(str(connector.status)),
        latest_refresh=latest_refresh,
        latest_refresh_status_label=_localo_refresh_status_label(latest_refresh)
        if latest_refresh
        else None,
        access_probe=access_probe,
        live_data_available=live_data_available,
        visibility_fact_count=len(visibility_facts),
        read_contract_statuses=read_contract_statuses,
        operator_summary=_operator_summary(
            decision_queue,
            access_probe,
            len(visibility_facts),
            read_contract_statuses,
        ),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=action_ids,
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
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
            missing_read_contracts=_unique(
                contract
                for decision in top_decisions
                for contract in decision.missing_read_contracts
            ),
            read_contract_statuses=read_contract_statuses,
            source_connectors=_unique(
                connector for decision in top_decisions for connector in decision.source_connectors
            )
            or [LOCALO_CONNECTOR_ID],
            evidence_ids=_unique(
                [
                    *(
                        evidence_id
                        for decision in top_decisions
                        for evidence_id in decision.evidence_ids
                    ),
                    *access_probe.evidence_ids,
                ]
            ),
            action_ids=_unique(
                action_id for decision in top_decisions for action_id in decision.action_ids
            ),
            blocked_claims=_unique(
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
    return _unique(
        action_id
        for decision in decisions
        for action_id in decision.action_ids
        if action_id == LOCALO_VISIBILITY_REVIEW_ACTION_ID
    )


def _latest_relevant_localo_refresh(
    refresh_runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    for run in refresh_runs:
        if _is_successful_mcp_probe(run):
            return run
    return refresh_runs[0] if refresh_runs else None


def _is_successful_mcp_probe(run: ConnectorRefreshRun) -> bool:
    return (
        connector_refresh_has_live_data(run)
        and run.metric_summary.get("api") == "localo_mcp_oauth_probe"
        and int(run.metric_summary.get("mcp_initialize_status", 0)) == 200
    )


def _visibility_facts(metric_facts: list[MetricFact]) -> list[MetricFact]:
    facts_by_name: dict[str, MetricFact] = {}
    for fact in metric_facts:
        if fact.name in LOCALO_PROBE_METRIC_NAMES:
            continue
        existing = facts_by_name.get(fact.name)
        if existing is None or (not existing.dimensions and fact.dimensions):
            facts_by_name[fact.name] = _localo_metric_fact_with_label(fact)
    return list(facts_by_name.values())


def _localo_metric_fact_with_label(fact: MetricFact) -> MetricFact:
    return fact.model_copy(update={"metric_label": localo_metric_fact_label(fact.name)})


def _metric_facts_for_refresh(run: ConnectorRefreshRun | None) -> list[MetricFact]:
    if run is not None and not run.metrics_persisted:
        return []
    if run and run.evidence_ids:
        facts = metric_store().list_metric_facts_by_evidence_ids(run.evidence_ids)
        if facts:
            return facts
    return metric_store().list_metric_facts(
        connector_id=LOCALO_CONNECTOR_ID,
        limit=LOCALO_METRIC_FACT_LIMIT,
    )


def _access_probe(
    *,
    connector_missing: list[str],
    run: ConnectorRefreshRun | None,
) -> LocaloAccessProbe:
    evidence_ids = _refresh_or_connector_evidence_ids(run)
    metric_summary = run.metric_summary if run else {}
    mcp_status = _int_or_none(metric_summary.get("mcp_initialize_status"))
    access_token_present = _bool_or_none(metric_summary.get("access_token_present"))
    authorization_code_supported = _bool_or_none(metric_summary.get("authorization_code_supported"))
    pkce_s256_supported = _bool_or_none(metric_summary.get("pkce_s256_supported"))

    if run and _is_successful_mcp_probe(run):
        return LocaloAccessProbe(
            status="access_ready",
            source_run_id=run.id,
            mcp_initialize_status=mcp_status,
            authorization_code_supported=authorization_code_supported,
            pkce_s256_supported=pkce_s256_supported,
            access_token_present=access_token_present,
            evidence_ids=evidence_ids,
            summary=(
                "Localo potwierdził dostęp do odczytu danych. To nadal nie jest "
                "dowód rankingów, profilu firmy w Google ani konkurencji."
            ),
        )

    has_blocked_refresh = run and run.status in {
        ConnectorRefreshStatus.blocked,
        ConnectorRefreshStatus.failed,
    }
    if connector_missing or has_blocked_refresh:
        missing = ", ".join(connector_missing) if connector_missing else "dostęp Localo"
        return LocaloAccessProbe(
            status="access_blocked",
            source_run_id=run.id if run else None,
            mcp_initialize_status=mcp_status,
            authorization_code_supported=authorization_code_supported,
            pkce_s256_supported=pkce_s256_supported,
            access_token_present=access_token_present,
            evidence_ids=evidence_ids,
            summary=(
                f"Localo nie ma gotowego dostępu do odczytu: {missing}. "
                "WILQ blokuje lokalne rekomendacje zamiast zgadywać widoczność."
            ),
        )

    return LocaloAccessProbe(
        status="unknown",
        source_run_id=run.id if run else None,
        mcp_initialize_status=mcp_status,
        authorization_code_supported=authorization_code_supported,
        pkce_s256_supported=pkce_s256_supported,
        access_token_present=access_token_present,
        evidence_ids=evidence_ids,
        summary=(
            "WILQ nie ma świeżego potwierdzenia dostępu Localo. To jest stan "
            "niepewny, więc lokalne rankingi i profil firmy w Google pozostają zablokowane."
        ),
    )


def _localo_sections(
    access_probe: LocaloAccessProbe,
    latest_refresh: ConnectorRefreshRun | None,
    visibility_facts: list[MetricFact],
) -> list[LocaloDiagnosticSection]:
    access_ready = access_probe.status == "access_ready"
    access_section = LocaloDiagnosticSection(
        id="localo_access_status",
        title="Localo: status dostępu do danych",
        status="ready" if access_ready else "blocked",
        summary=(
            "Dostęp do danych Localo jest gotowy; potwierdzenie dostępu "
            "i dowody są dostępne w szczegółach."
            if access_ready
            else access_probe.summary
        ),
        diagnosis=(
            "Dostęp do Localo pozwala WILQ pobierać dane ze źródła. Sam dostęp "
            "nie mówi jeszcze nic o pozycjach lokalnych, profilu firmy w Google ani konkurencji."
            if access_ready
            else "Bez działającego dostępu Localo WILQ nie może pobierać lokalnych dowodów."
        ),
        next_step=(
            "Nie pokazuj Localo jako zadania dziennego. Użyj tego widoku jako "
            "statusu źródła i dodaj dane rankingów oraz profilu firmy w Google "
            "przed rekomendacjami."
            if access_ready
            else "Dokończ dostęp Localo i wykonaj odczyt danych."
        ),
        source_connectors=[LOCALO_CONNECTOR_ID],
        evidence_ids=access_probe.evidence_ids,
        action_ids=[],
        blocked_claims=[] if access_ready else LOCALO_BLOCKED_CLAIMS,
        risk=ActionRisk.low if access_ready else ActionRisk.medium,
    )

    present_contracts = _present_contracts(visibility_facts)
    missing_contracts = _missing_visibility_contracts(present_contracts)
    blocked_claims = _blocked_claims_for_missing_contracts(missing_contracts)
    visibility_action_ids = _localo_visibility_action_ids(visibility_facts)
    visibility_section = LocaloDiagnosticSection(
        id="localo_visibility_contract",
        title="Localo: dane rankingów i profilu firmy w Google",
        status="ready" if visibility_facts else "missing",
        summary=(
            _localo_visibility_summary_with_contracts(
                visibility_facts=visibility_facts,
                present_contracts=present_contracts,
                missing_contracts=missing_contracts,
            )
            if visibility_facts
            else (
                "WILQ nie ma jeszcze rankingów, danych profilu firmy w Google, "
                "widoczności konkurencji ani recenzji z Localo."
            )
        ),
        diagnosis=(
            "Dane Localo wspierają tylko wskazane obszary. WILQ nie rozszerza ich "
            "na brakujące dane, zapis zmian ani poprawę widoczności bez "
            "osobnych dowodów."
            if visibility_facts
            else "Brak tych danych oznacza brak lokalnej diagnozy marketingowej, nie brak problemu."
        ),
        next_step=(
            "Przejrzyj agregaty miejsc, fraz i recenzji. Claimy z brakujących "
            "danych zostaw zablokowane."
            if visibility_facts
            else (
                "Dodaj odczyt rankingów, profilu firmy w Google, konkurencji "
                "i recenzji zanim WILQ zaproponuje lokalne działania."
            )
        ),
        source_connectors=[LOCALO_CONNECTOR_ID],
        evidence_ids=_unique(
            [*(fact.evidence_id for fact in visibility_facts), *access_probe.evidence_ids]
        ),
        metric_facts=visibility_facts[:12],
        action_ids=visibility_action_ids,
        blocked_claims=blocked_claims if visibility_facts else LOCALO_BLOCKED_CLAIMS,
        risk=ActionRisk.low if visibility_facts else ActionRisk.medium,
    )

    safety_section = LocaloDiagnosticSection(
        id="localo_action_safety",
        title="Bezpieczeństwo działań Localo i profilu firmy w Google",
        status="blocked" if not visibility_facts else "ready",
        summary=(
            "Publiczne działania w profilu firmy w Google, posty i zmiany profilu "
            "wymagają osobnych akcji, podglądu zmian, sprawdzenia i audytu."
        ),
        diagnosis=(
            "WILQ może raportować stan dostępu albo przygotować przyszłe sprawdzenie. Nie może "
            "twierdzić poprawy widoczności lokalnej bez danych rankingów i profilu firmy w Google."
        ),
        next_step="Zostaw ścieżkę zapisu zablokowaną do czasu osobnej akcji Localo.",
        source_connectors=[LOCALO_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=[],
        blocked_claims=[
            "publikacja posta w profilu firmy w Google",
            "zmiana profilu firmy w Google",
            "poprawa widoczności lokalnej",
        ],
        risk=ActionRisk.medium,
    )
    return [
        _label_localo_section(access_section),
        _label_localo_section(visibility_section),
        _label_localo_section(safety_section),
    ]


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
                evidence_ids=_unique(
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
                "knowledge_card_ids": _unique(
                    [*decision.knowledge_card_ids, *LOCALO_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": _unique([*decision.expert_rule_ids, *LOCALO_EXPERT_RULE_IDS]),
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


def _present_contracts(visibility_facts: list[MetricFact]) -> list[str]:
    fact_names = {fact.name for fact in visibility_facts}
    present = [
        contract
        for contract in LOCALO_CONTRACT_ORDER
        if contract in LOCALO_CONTRACT_FACT_NAMES
        and fact_names.intersection(LOCALO_CONTRACT_FACT_NAMES[contract])
    ]
    return present


def _localo_read_contract_statuses(
    visibility_facts: list[MetricFact],
) -> list[LocaloReadContractStatus]:
    facts_by_contract: dict[str, list[MetricFact]] = {}
    for fact in visibility_facts:
        contract = str(fact.dimensions.get("contract") or "")
        if contract:
            facts_by_contract.setdefault(contract, []).append(fact)

    return [
        _label_localo_read_contract_status(
            LocaloReadContractStatus(
                id=contract,  # type: ignore[arg-type]
                status="ready" if facts_by_contract.get(contract) else "missing",
                evidence_kind=_localo_contract_evidence_kind(contract),
                metric_fact_names=_unique(
                    fact.name for fact in facts_by_contract.get(contract, [])
                ),
                blocked_claims=[]
                if facts_by_contract.get(contract)
                else _blocked_claims_for_contract(contract),
                next_step=_localo_contract_next_step(
                    contract,
                    ready=bool(facts_by_contract.get(contract)),
                ),
            )
        )
        for contract in LOCALO_CONTRACT_ORDER
    ]


def _missing_contract_ids(
    read_contract_statuses: list[LocaloReadContractStatus],
) -> list[str]:
    return [str(contract.id) for contract in read_contract_statuses if contract.status != "ready"]


def _localo_contract_evidence_kind(contract: str) -> str:
    labels = {
        "place_inventory": "miejsca i aktywne profile",
        "local_rankings": "agregaty fraz, widoczności i pozycji grid",
        "gbp_visibility": "widoczność profilu firmy w Google",
        "competitor_visibility": "porównanie lokalnych konkurentów",
        "reviews": "recenzje i odpowiedzi",
        "local_tasks": "lokalne zadania do wykonania",
    }
    return labels.get(contract, "zakres danych Localo do sprawdzenia")


def _localo_contracts_phrase(contracts: list[str]) -> str:
    labels = {
        "place_inventory": "miejsca i profile",
        "local_rankings": "lokalne pozycje i frazy",
        "gbp_visibility": "profil firmy w Google",
        "competitor_visibility": "lokalni konkurenci",
        "reviews": "opinie",
        "local_tasks": "zadania lokalne",
    }
    values = [labels.get(contract, "zakres danych Localo do sprawdzenia") for contract in contracts]
    if not values:
        return "żaden zakres danych Localo nie jest brakujący"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} i {values[-1]}"


def _localo_missing_contracts_phrase(contracts: list[str]) -> str:
    labels = {
        "place_inventory": "miejsca i profile",
        "local_rankings": "lokalne rankingi",
        "gbp_visibility": "profil firmy w Google",
        "competitor_visibility": "konkurencję",
        "reviews": "recenzje",
        "local_tasks": "zadania lokalne",
    }
    values = [labels.get(contract, "zakres danych Localo do sprawdzenia") for contract in contracts]
    if not values:
        return "żaden brakujący zakres danych Localo"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} i {values[-1]}"


def _localo_visibility_summary_with_contracts(
    *,
    visibility_facts: list[MetricFact],
    present_contracts: list[str],
    missing_contracts: list[str],
) -> str:
    ready_summary = (
        f"WILQ ma {_localo_aggregate_count_label(len(visibility_facts))} dla danych: "
        f"{_localo_contracts_phrase(present_contracts)}."
    )
    if not missing_contracts:
        return (
            f"{ready_summary} Żaden zakres Localo z obecnego kontraktu nie jest oznaczony "
            "jako brakujący."
        )
    return f"{ready_summary} Nadal brakuje: {_localo_contracts_phrase(missing_contracts)}."


def _blocked_claims_for_contract(contract: str) -> list[str]:
    claims_by_contract = {
        "local_rankings": ["lokalne rankingi", "poprawa widoczności lokalnej"],
        "gbp_visibility": [
            "wyniki profilu firmy w Google",
            "zapis zmian w profilu firmy",
            "poprawa widoczności lokalnej",
        ],
        "competitor_visibility": ["widoczności konkurencji", "poprawa widoczności lokalnej"],
        "reviews": ["tempo nowych opinii", "poprawa widoczności lokalnej"],
        "local_tasks": [
            "ukończone zadanie lokalne",
            "zapis zmian w profilu firmy",
            "poprawa widoczności lokalnej",
        ],
    }
    return claims_by_contract.get(contract, [])


def _localo_contract_next_step(contract: str, *, ready: bool) -> str:
    if ready:
        return "Użyj tych danych jako dowodu dla sprawdzenia Localo."
    next_steps = {
        "gbp_visibility": (
            "Dodaj odczyt widoczności profilu firmy w Google przed oceną tego profilu."
        ),
        "competitor_visibility": (
            "Dodaj odczyt widoczności konkurencji przed porównaniem konkurencji."
        ),
        "local_tasks": "Dodaj odczyt zadań lokalnych przed planem zadań lokalnych.",
        "local_rankings": "Dodaj odczyt lokalnych rankingów przed obietnicami o pozycjach.",
        "reviews": "Dodaj odczyt recenzji przed oceną tempa recenzji.",
        "place_inventory": "Dodaj odczyt miejsca i profile przed oceną profili.",
    }
    return next_steps.get(contract, "Dodaj odczyt danych Localo przed obietnicami.")


def _missing_visibility_contracts(present_contracts: list[str]) -> list[str]:
    present = set(present_contracts)
    return [contract for contract in LOCALO_VISIBILITY_READ_CONTRACTS if contract not in present]


def _blocked_claims_for_missing_contracts(missing_contracts: list[str]) -> list[str]:
    claims_by_contract = {
        "local_rankings": "lokalne rankingi",
        "gbp_visibility": "wyniki profilu firmy w Google",
        "competitor_visibility": "widoczności konkurencji",
        "reviews": "tempo nowych opinii",
        "local_tasks": "ukończone zadanie lokalne",
    }
    claims = [
        claim for contract, claim in claims_by_contract.items() if contract in missing_contracts
    ]
    claims.extend(["zapis zmian w profilu firmy", "poprawa widoczności lokalnej"])
    return _unique(claims)


def _localo_visibility_action_ids(visibility_facts: list[MetricFact]) -> list[str]:
    if not visibility_facts:
        return []
    return [LOCALO_VISIBILITY_REVIEW_ACTION_ID]


def _localo_visibility_tiles(
    visibility_facts: list[MetricFact],
    missing_contracts: list[str],
) -> dict[str, int | float | str]:
    return {
        "dane Localo": len(visibility_facts),
        "miejsca": _int_fact_value(visibility_facts, "localo_active_place_count"),
        "frazy": _int_fact_value(visibility_facts, "localo_tracked_keyword_count"),
        "średnia widoczność": _float_fact_value(
            visibility_facts,
            "localo_avg_visibility_current",
        ),
        "recenzje": _int_fact_value(visibility_facts, "localo_reviews_count"),
        "brakujące dane": len(missing_contracts),
    }


def _int_fact_value(visibility_facts: list[MetricFact], name: str) -> int:
    value = _fact_value(visibility_facts, name)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _float_fact_value(visibility_facts: list[MetricFact], name: str) -> float:
    value = _fact_value(visibility_facts, name)
    if isinstance(value, int | float):
        return round(float(value), 2)
    return 0.0


def _localo_aggregate_count_label(count: int) -> str:
    if count == 1:
        return "1 agregat Localo"
    if 2 <= count % 10 <= 4 and count % 100 not in {12, 13, 14}:
        return f"{count} agregaty Localo"
    return f"{count} agregatów Localo"


def _fact_value(visibility_facts: list[MetricFact], name: str) -> int | float | str | None:
    for fact in visibility_facts:
        if fact.name == name:
            return fact.value
    return None


def _refresh_or_connector_evidence_ids(run: ConnectorRefreshRun | None) -> list[str]:
    if run and run.evidence_ids:
        return run.evidence_ids
    return [connector_evidence_id(LOCALO_CONNECTOR_ID)]


def _int_or_none(value: float | int | str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: float | int | str | None) -> bool | None:
    numeric_value = _int_or_none(value)
    if numeric_value is None:
        return None
    return bool(numeric_value)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered
