"""Decomposed localo_diagnostics visibility implementation."""

from __future__ import annotations

from wilq.briefing.localo.labels import _label_localo_read_contract_status, _label_localo_section
from wilq.briefing.localo.shared import (
    LOCALO_BLOCKED_CLAIMS,
    LOCALO_CONNECTOR_ID,
    LOCALO_CONTRACT_ORDER,
    LOCALO_METRIC_FACT_LIMIT,
    LOCALO_PROBE_METRIC_NAMES,
    _blocked_claims_for_contract,
    _blocked_claims_for_missing_contracts,
    _bool_or_none,
    _int_or_none,
    _localo_contract_evidence_kind,
    _localo_contract_next_step,
    _localo_visibility_action_ids,
    _localo_visibility_summary_with_contracts,
    _missing_visibility_contracts,
    _present_contracts,
    _refresh_or_connector_evidence_ids,
)
from wilq.briefing.localo_labels import localo_metric_fact_label
from wilq.content.operator_copy import unique
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    LocaloAccessProbe,
    LocaloDiagnosticSection,
    LocaloReadContractStatus,
    MetricFact,
    connector_refresh_has_live_data,
)
from wilq.storage.metric_store import metric_store


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
        return LocaloAccessProbe(
            status="access_blocked",
            source_run_id=run.id if run else None,
            mcp_initialize_status=mcp_status,
            authorization_code_supported=authorization_code_supported,
            pkce_s256_supported=pkce_s256_supported,
            access_token_present=access_token_present,
            evidence_ids=evidence_ids,
            summary=(
                "Localo nie ma gotowego dostępu do odczytu danych. "
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
        evidence_ids=unique(
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
                metric_fact_names=unique(fact.name for fact in facts_by_contract.get(contract, [])),
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
