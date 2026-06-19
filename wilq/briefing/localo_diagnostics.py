from __future__ import annotations

from collections.abc import Iterable

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
    metric_facts = metric_store().list_metric_facts(
        connector_id=LOCALO_CONNECTOR_ID,
        limit=LOCALO_METRIC_FACT_LIMIT,
    )
    visibility_facts = _visibility_facts(metric_facts)
    access_probe = _access_probe(
        connector_missing=connector.missing_credentials,
        run=latest_refresh,
    )
    live_data_available = bool(visibility_facts)
    sections = _localo_sections(access_probe, latest_refresh, visibility_facts)
    decision_queue = _localo_decision_queue(access_probe, visibility_facts)

    return LocaloDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        access_probe=access_probe,
        live_data_available=live_data_available,
        visibility_fact_count=len(visibility_facts),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=[],
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
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
    return [fact for fact in metric_facts if fact.name not in LOCALO_PROBE_METRIC_NAMES]


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

    visibility_section = LocaloDiagnosticSection(
        id="localo_visibility_contract",
        title="Localo: ranking/GBP evidence",
        status="ready" if visibility_facts else "missing",
        summary=(
            f"WILQ ma {len(visibility_facts)} Localo visibility facts."
            if visibility_facts
            else "WILQ nie ma jeszcze rankingów, GBP, competitor visibility ani reviews z Localo."
        ),
        diagnosis=(
            "Visibility facts mogą wspierać lokalną kolejkę działań."
            if visibility_facts
            else "Brak tych facts oznacza brak lokalnej diagnozy marketingowej, nie brak problemu."
        ),
        next_step=(
            "Przejrzyj ranking/GBP facts i połącz je z ActionObjectem lokalnej kolejki."
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
        action_ids=[],
        blocked_claims=[] if visibility_facts else LOCALO_BLOCKED_CLAIMS,
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
) -> list[LocaloDecisionItem]:
    if visibility_facts:
        return [
            LocaloDecisionItem(
                id="localo_review_visibility_facts",
                decision_type="review_local_visibility",
                status="ready",
                title="Przejrzyj lokalną widoczność z Localo facts",
                summary=f"WILQ ma {len(visibility_facts)} Localo visibility facts.",
                rationale="Ranking/GBP facts istnieją w WILQ evidence i mogą zostać ocenione.",
                next_step="Zbuduj lokalną kolejkę review z evidence IDs i bez ścieżki zapisu.",
                access_status=access_probe.status,
                allowed_evidence=["local_rankings", "gbp_visibility", "competitor_visibility"],
                missing_read_contracts=[],
                source_connectors=[LOCALO_CONNECTOR_ID],
                evidence_ids=_unique(
                    [*(fact.evidence_id for fact in visibility_facts), *access_probe.evidence_ids]
                ),
                metric_facts=visibility_facts[:12],
                action_ids=[],
                blocked_claims=["GBP write", "visibility uplift guaranteed"],
                risk=ActionRisk.low,
            )
        ]

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
                allowed_evidence=["mcp_initialize", "oauth_metadata", "access_token_presence"],
                missing_read_contracts=LOCALO_VISIBILITY_READ_CONTRACTS,
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


def _blocked_visibility_decision(access_probe: LocaloAccessProbe) -> LocaloDecisionItem:
    return LocaloDecisionItem(
        id="localo_block_visibility_claims_without_read_contract",
        decision_type="block_visibility_claims",
        status="blocked",
        title="Nie wyciągaj wniosków o lokalnej widoczności bez Localo facts",
        summary=(
            "WILQ blokuje claimy o rankingach, GBP, konkurencji, reviews i wzroście "
            "widoczności, dopóki Localo read contract nie dostarczy tych facts."
        ),
        rationale=(
            "Access/readiness nie jest metryką marketingową. To chroni dashboard i "
            "skille przed udawaniem lokalnego SEO insightu."
        ),
        next_step=(
            "Najpierw dodaj typed Localo read contract; dopiero potem buduj "
            "lokalne ActionObjecty."
        ),
        access_status=access_probe.status,
        allowed_evidence=["mcp_initialize"] if access_probe.status == "access_ready" else [],
        missing_read_contracts=LOCALO_VISIBILITY_READ_CONTRACTS,
        source_connectors=[LOCALO_CONNECTOR_ID],
        evidence_ids=access_probe.evidence_ids,
        action_ids=[],
        blocked_claims=LOCALO_BLOCKED_CLAIMS,
        risk=ActionRisk.medium,
    )


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
