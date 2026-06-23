from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
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
    "local ranking",
    "GBP performance",
    "competitor visibility",
    "local visibility uplift",
    "review velocity",
]


def build_localo_diagnostics() -> LocaloDiagnosticsResponse:
    connector = get_connector_status(LOCALO_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Localo connector is not registered.")

    refresh_runs = list_connector_refresh_runs(connector_id=LOCALO_CONNECTOR_ID)
    latest_refresh = _latest_relevant_localo_refresh(refresh_runs)
    metric_facts = _metric_facts_for_refresh(latest_refresh)
    visibility_facts = _visibility_facts(metric_facts)
    access_probe = _access_probe(
        connector_missing=connector.missing_credentials,
        run=latest_refresh,
    )
    live_data_available = bool(visibility_facts)
    sections = _localo_sections(access_probe, latest_refresh, visibility_facts)
    read_contract_statuses = _localo_read_contract_statuses(visibility_facts)
    decision_queue = _localo_decision_queue(
        access_probe,
        visibility_facts,
        read_contract_statuses,
    )
    action_ids = _unique(
        action_id for decision in decision_queue for action_id in decision.action_ids
    )

    return LocaloDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
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
    return LocaloOperatorSummary(
        title="Co marketer ma wiedzieć o Localo",
        summary=_operator_summary_text(visibility_fact_count),
        next_step=_operator_summary_next_step(visibility_fact_count),
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


def _operator_summary_text(visibility_fact_count: int) -> str:
    if visibility_fact_count:
        return (
            "Localo dostarczył typed agregaty widoczności, miejsc, fraz i recenzji. "
            "WILQ może użyć ich do lokalnego review, ale nadal blokuje GBP, "
            "konkurencję, write path i claim o wzroście widoczności bez osobnych "
            "kontraktów."
        )
    return (
        "Ten widok pokazuje, czy Localo może już wspierać decyzje lokalnego SEO. "
        "Dostęp MCP nie jest jeszcze dowodem rankingów, GBP, konkurencji ani "
        "recenzji, więc WILQ blokuje claimy bez typed visibility facts."
    )


def _operator_summary_next_step(visibility_fact_count: int) -> str:
    if visibility_fact_count:
        return (
            "Przejrzyj agregaty Localo: miejsca, frazy, średnią widoczność i "
            "recenzje. Konkurencję, GBP i działania write zostaw zablokowane."
        )
    return (
        "Użyj top decyzji jako statusu źródła. Nie proponuj lokalnych działań "
        "SEO ani GBP, dopóki Localo read contract nie dostarczy visibility facts."
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
        run.status == ConnectorRefreshStatus.completed
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
            facts_by_name[fact.name] = fact
    return list(facts_by_name.values())


def _metric_facts_for_refresh(run: ConnectorRefreshRun | None) -> list[MetricFact]:
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
                "Localo MCP initialize zwrócił 200. To potwierdza dostęp WILQ do MCP, "
                "ale nie jest jeszcze dowodem rankingów, GBP ani konkurencji."
            ),
        )

    has_blocked_refresh = run and run.status in {
        ConnectorRefreshStatus.blocked,
        ConnectorRefreshStatus.failed,
    }
    if connector_missing or has_blocked_refresh:
        missing = ", ".join(connector_missing) if connector_missing else "Localo MCP access"
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
            "WILQ nie ma świeżego Localo MCP initialize proof. To jest stan "
            "niepewny, więc lokalne rankingi i GBP pozostają zablokowane."
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
        title="Localo: status dostępu MCP",
        status="ready" if access_ready else "blocked",
        summary=(
            "Dostęp MCP jest gotowy; initialize proof i źródłowe evidence IDs "
            "są dostępne w tym widoku."
            if access_ready
            else access_probe.summary
        ),
        diagnosis=(
            "Dostęp MCP pozwala WILQ rozmawiać z Localo jako adapterem. Sam "
            "initialize nie mówi jeszcze nic o pozycjach lokalnych, profilu GBP "
            "ani konkurencji."
            if access_ready
            else "Bez działającego Localo access WILQ nie może pobierać lokalnego evidence."
        ),
        next_step=(
            "Nie pokazuj Localo jako zadania dziennego. Użyj tego widoku jako "
            "statusu źródła i dodaj ranking/GBP read contract przed rekomendacjami."
            if access_ready
            else "Dokończ Localo OAuth authorization_code + PKCE i wykonaj vendor_read."
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
        title="Localo: ranking/GBP evidence",
        status="ready" if visibility_facts else "missing",
        summary=(
            (
                f"WILQ ma {len(visibility_facts)} Localo aggregate facts dla kontraktów: "
                f"{', '.join(present_contracts)}. Nadal brakuje: "
                f"{', '.join(missing_contracts) or 'brak'}."
            )
            if visibility_facts
            else "WILQ nie ma jeszcze rankingów, GBP, competitor visibility ani reviews z Localo."
        ),
        diagnosis=(
            "Localo facts wspierają tylko wskazane kontrakty. WILQ nie rozszerza ich "
            "na GBP, konkurencję ani poprawę widoczności bez osobnego evidence."
            if visibility_facts
            else "Brak tych facts oznacza brak lokalnej diagnozy marketingowej, nie brak problemu."
        ),
        next_step=(
            "Przejrzyj agregaty miejsc, fraz i recenzji. Claimy z brakujących "
            "kontraktów zostaw zablokowane."
            if visibility_facts
            else (
                "Zbuduj Localo read contract dla rankings/GBP/competitors/reviews "
                "zanim WILQ zaproponuje lokalne działania."
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
        title="Bezpieczeństwo działań Localo/GBP",
        status="blocked" if not visibility_facts else "ready",
        summary=(
            "Publiczne działania GBP, posty i zmiany profilu wymagają osobnych ActionObjectów, "
            "podglądu akcji, walidacji i audytu."
        ),
        diagnosis=(
            "WILQ może raportować stan dostępu albo przygotować przyszły review. Nie może "
            "twierdzić poprawy widoczności lokalnej bez ranking/GBP evidence."
        ),
        next_step="Zostaw ścieżkę zapisu zablokowaną do czasu typed Localo ActionObject.",
        source_connectors=[LOCALO_CONNECTOR_ID],
        evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
        action_ids=[],
        blocked_claims=[
            "GBP post published",
            "profile edit applied",
            "local visibility uplift",
        ],
        risk=ActionRisk.medium,
    )
    return [access_section, visibility_section, safety_section]


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
                    f"WILQ ma {len(visibility_facts)} Localo aggregate facts: "
                    f"{', '.join(present_contracts)}."
                ),
                rationale=(
                    "Localo dostarczył read-only agregaty dla miejsc, monitorowanych fraz "
                    "i recenzji. To pozwala na review, ale nie na claim o poprawie "
                    "widoczności ani działania GBP."
                ),
                next_step=(
                    "Sprawdź średnią widoczność, pozycje grid i stan recenzji. "
                    "Konkurencję/GBP/write path zostaw zablokowane."
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
                title="Localo access działa; brakuje ranking/GBP facts",
                summary=(
                    "MCP initialize=200 potwierdza dostęp. WILQ nie ma jeszcze "
                    "lokalnych rankingów, GBP, konkurencji ani reviews."
                ),
                rationale=(
                    "To jest gotowość adaptera, nie diagnoza lokalnej widoczności. "
                    "Marketer nie powinien traktować tego jako zadania optymalizacyjnego."
                ),
                next_step=(
                    "Zostaw Localo jako status źródła i dodaj Localo read contract "
                    "dla rankings/GBP/competitors/reviews."
                ),
                access_status=access_probe.status,
                priority=30,
                metric_tiles={
                    "dostęp MCP": 1,
                    "fakty Localo": 0,
                    "braki kontraktu": len(LOCALO_VISIBILITY_READ_CONTRACTS),
                },
                allowed_evidence=["mcp_initialize", "oauth_metadata", "access_token_presence"],
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
            title="Dokończ Localo access przed lokalnymi rekomendacjami",
            summary=access_probe.summary,
            rationale=(
                "Bez działającego Localo access WILQ nie może pobrać rankingów, "
                "GBP ani competitor evidence."
            ),
            next_step="Wykonaj Localo OAuth helper i vendor_read, potem wróć do /localo.",
            access_status=access_probe.status,
            priority=5,
            metric_tiles={
                "dostęp MCP": 0,
                "braki kontraktu": len(LOCALO_VISIBILITY_READ_CONTRACTS) + 1,
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
    return LocaloDecisionItem(
        id="localo_block_visibility_claims_without_read_contract",
        decision_type="block_visibility_claims",
        status="blocked",
        title=(
            "Blokuj GBP, konkurencję i local tasks bez pełnych kontraktów Localo"
            if has_partial_visibility_facts
            else "Nie wyciągaj wniosków o lokalnej widoczności bez Localo facts"
        ),
        summary=(
            (
                "WILQ ma częściowe agregaty Localo, ale blokuje claimy zależne od "
                "brakujących kontraktów: GBP, konkurencji, local tasks i write path."
            )
            if has_partial_visibility_facts
            else (
                "WILQ blokuje claimy o rankingach, GBP, konkurencji, reviews i wzroście "
                "widoczności, dopóki Localo read contract nie dostarczy tych facts."
            )
        ),
        rationale=(
            (
                "Częściowe facts są wystarczające do review agregatów, ale nie do "
                "rozszerzania ich na nieobsługiwane obszary Localo."
            )
            if has_partial_visibility_facts
            else (
                "Access/readiness nie jest metryką marketingową. To chroni dashboard i "
                "skille przed udawaniem lokalnego SEO insightu."
            )
        ),
        next_step=(
            (
                "Przejrzyj dostępne agregaty Localo, a kontrakty GBP, konkurencji "
                "i local tasks dodaj przed szerszymi claimami lub write path."
            )
            if has_partial_visibility_facts
            else (
                "Najpierw dodaj typed Localo read contract; dopiero potem buduj "
                "lokalne ActionObjecty."
            )
        ),
        access_status=access_probe.status,
        priority=10,
        metric_tiles={
            "blokady claimów": len(effective_blocked_claims),
            "braki kontraktu": len(effective_missing_contracts),
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
        LocaloReadContractStatus(
            id=contract,  # type: ignore[arg-type]
            status="ready" if facts_by_contract.get(contract) else "missing",
            evidence_kind=_localo_contract_evidence_kind(contract),
            metric_fact_names=_unique(fact.name for fact in facts_by_contract.get(contract, [])),
            blocked_claims=[]
            if facts_by_contract.get(contract)
            else _blocked_claims_for_contract(contract),
            next_step=_localo_contract_next_step(
                contract,
                ready=bool(facts_by_contract.get(contract)),
            ),
        )
        for contract in LOCALO_CONTRACT_ORDER
    ]


def _localo_contract_evidence_kind(contract: str) -> str:
    labels = {
        "place_inventory": "miejsca i aktywne profile",
        "local_rankings": "agregaty fraz, widoczności i pozycji grid",
        "gbp_visibility": "widoczność Google Business Profile",
        "competitor_visibility": "porównanie lokalnych konkurentów",
        "reviews": "recenzje i odpowiedzi",
        "local_tasks": "lokalne zadania do wykonania",
    }
    return labels.get(contract, contract)


def _blocked_claims_for_contract(contract: str) -> list[str]:
    claims_by_contract = {
        "local_rankings": ["local ranking", "local visibility uplift"],
        "gbp_visibility": ["GBP performance", "GBP write", "local visibility uplift"],
        "competitor_visibility": ["competitor visibility", "local visibility uplift"],
        "reviews": ["review velocity", "local visibility uplift"],
        "local_tasks": ["local task completed", "GBP write", "local visibility uplift"],
    }
    return claims_by_contract.get(contract, [])


def _localo_contract_next_step(contract: str, *, ready: bool) -> str:
    if ready:
        return "Użyj tego kontraktu jako evidence dla Localo review."
    next_steps = {
        "gbp_visibility": "Dodaj read-only Localo/GBP visibility contract przed oceną GBP.",
        "competitor_visibility": (
            "Dodaj read-only competitor visibility contract przed porównaniem konkurencji."
        ),
        "local_tasks": "Dodaj read-only local tasks contract przed planem zadań lokalnych.",
        "local_rankings": "Dodaj read-only local rankings contract przed claimami o pozycjach.",
        "reviews": "Dodaj read-only reviews contract przed oceną velocity recenzji.",
        "place_inventory": "Dodaj read-only place inventory contract przed oceną profili.",
    }
    return next_steps.get(contract, "Dodaj typed Localo read contract przed claimami.")


def _missing_visibility_contracts(present_contracts: list[str]) -> list[str]:
    present = set(present_contracts)
    return [contract for contract in LOCALO_VISIBILITY_READ_CONTRACTS if contract not in present]


def _blocked_claims_for_missing_contracts(missing_contracts: list[str]) -> list[str]:
    claims_by_contract = {
        "local_rankings": "local ranking",
        "gbp_visibility": "GBP performance",
        "competitor_visibility": "competitor visibility",
        "reviews": "review velocity",
        "local_tasks": "local task completed",
    }
    claims = [
        claim
        for contract, claim in claims_by_contract.items()
        if contract in missing_contracts
    ]
    claims.extend(["GBP write", "local visibility uplift"])
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
        "fakty Localo": len(visibility_facts),
        "miejsca": _int_fact_value(visibility_facts, "localo_active_place_count"),
        "frazy": _int_fact_value(visibility_facts, "localo_tracked_keyword_count"),
        "średnia widoczność": _float_fact_value(
            visibility_facts,
            "localo_avg_visibility_current",
        ),
        "recenzje": _int_fact_value(visibility_facts, "localo_reviews_count"),
        "braki kontraktu": len(missing_contracts),
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
        return round(float(value), 4)
    return 0.0


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
