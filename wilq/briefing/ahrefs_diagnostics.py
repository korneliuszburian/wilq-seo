from __future__ import annotations

from collections.abc import Iterable

from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionRisk,
    AhrefsDecisionItem,
    AhrefsDiagnosticSection,
    AhrefsDiagnosticsResponse,
    AhrefsGapReadContract,
    AhrefsGapRecord,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)
from wilq.storage.metric_store import metric_store

AHREFS_CONNECTOR_ID = "ahrefs"
AHREFS_METRIC_FACT_LIMIT = 120
AHREFS_AUTHORITY_FACT_NAMES = {"domain_rating", "ahrefs_rank"}
AHREFS_GAP_FACT_NAMES = {
    "ahrefs_competitor_page_count",
    "ahrefs_content_gap_count",
    "ahrefs_backlink_gap_count",
    "ahrefs_referring_domain_gap_count",
    "ahrefs_organic_keyword_gap_count",
}
AHREFS_GAP_READ_CONTRACTS = [
    "ahrefs_competitor_pages",
    "ahrefs_content_gap_records",
    "ahrefs_backlink_gap_records",
    "ahrefs_organic_keywords_by_url",
    "ahrefs_top_pages_by_competitor",
]
AHREFS_GAP_BLOCKED_CLAIMS = [
    "competitor gap",
    "content gap",
    "backlink gap",
    "ranking opportunity",
    "traffic uplift",
    "authority improvement",
]


def build_ahrefs_diagnostics() -> AhrefsDiagnosticsResponse:
    connector = get_connector_status(AHREFS_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Ahrefs connector is not registered.")

    refresh_runs = list_connector_refresh_runs(connector_id=AHREFS_CONNECTOR_ID)
    latest_refresh = _latest_relevant_ahrefs_refresh(refresh_runs)
    metric_facts = metric_store().list_metric_facts(
        connector_id=AHREFS_CONNECTOR_ID,
        limit=AHREFS_METRIC_FACT_LIMIT,
    )
    authority_facts = _latest_facts_by_name(metric_facts, AHREFS_AUTHORITY_FACT_NAMES)
    gap_facts = _gap_facts(metric_facts)
    live_data_available = bool(authority_facts or gap_facts)
    sections = _ahrefs_sections(
        connector_missing=connector.missing_credentials,
        latest_refresh=latest_refresh,
        authority_facts=authority_facts,
        gap_facts=gap_facts,
    )
    decision_queue = _ahrefs_decision_queue(
        connector_missing=connector.missing_credentials,
        latest_refresh=latest_refresh,
        authority_facts=authority_facts,
        gap_facts=gap_facts,
    )

    return AhrefsDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        latest_refresh=latest_refresh,
        live_data_available=live_data_available,
        authority_fact_count=len(authority_facts),
        gap_fact_count=len(gap_facts),
        gap_read_contract=_ahrefs_gap_read_contract(
            latest_refresh=latest_refresh,
            authority_facts=authority_facts,
            gap_facts=gap_facts,
        ),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=_unique(
            [
                *(evidence_id for section in sections for evidence_id in section.evidence_ids),
                *(
                    evidence_id
                    for decision in decision_queue
                    for evidence_id in decision.evidence_ids
                ),
            ]
        ),
        action_ids=[],
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
    )


def _ahrefs_gap_read_contract(
    *,
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> AhrefsGapReadContract:
    missing_contracts = _missing_gap_contracts(gap_facts)
    gap_records: list[AhrefsGapRecord] = []
    blocked_claims = _blocked_claims_for_missing_contracts(missing_contracts)
    evidence_ids = _evidence_ids_for_facts_or_refresh(
        [*gap_facts, *authority_facts],
        latest_refresh,
    )
    available_contracts = []
    if authority_facts:
        available_contracts.append("ahrefs_authority_summary")
    if gap_facts:
        available_contracts.append("ahrefs_gap_metric_facts")
    return AhrefsGapReadContract(
        status="ready" if gap_records and not missing_contracts else "blocked",
        title="Ahrefs gap records",
        summary=(
            f"WILQ ma {len(gap_records)} typed Ahrefs gap records. "
            f"Brakujące kontrakty: {', '.join(missing_contracts) or 'brak'}."
        ),
        available_read_contracts=available_contracts,
        missing_read_contracts=missing_contracts,
        allowed_evidence=["domain_rating", "ahrefs_rank"] if authority_facts else [],
        blocked_claims=blocked_claims,
        operator_review_gates=[
            "ahrefs_gap_records_required",
            "content_planner_review_required",
            "human_strategy_review",
        ],
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=evidence_ids,
        gap_records=gap_records,
        next_step=(
            "Dodaj read-only records dla konkurencyjnych stron, luk treści, luk backlinków, "
            "organicznych słów per URL i top pages konkurencji. Do tego czasu używaj Ahrefs "
            "tylko jako kontekstu autorytetu."
            if missing_contracts
            else "Połącz gap records z GSC/WordPress i przygotuj kolejkę review."
        ),
        risk=ActionRisk.medium,
    )


def _latest_relevant_ahrefs_refresh(
    refresh_runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    for run in refresh_runs:
        if (
            run.mode.value == "vendor_read"
            and run.status == ConnectorRefreshStatus.completed
            and run.vendor_data_collected
        ):
            return run
    return refresh_runs[0] if refresh_runs else None


def _latest_facts_by_name(
    facts: list[MetricFact],
    names: set[str],
) -> list[MetricFact]:
    facts_by_name: dict[str, MetricFact] = {}
    for fact in facts:
        if fact.name not in names:
            continue
        facts_by_name.setdefault(fact.name, fact)
    return list(facts_by_name.values())


def _gap_facts(facts: list[MetricFact]) -> list[MetricFact]:
    return [fact for fact in facts if fact.name in AHREFS_GAP_FACT_NAMES]


def _ahrefs_sections(
    *,
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[AhrefsDiagnosticSection]:
    authority_section = AhrefsDiagnosticSection(
        id="ahrefs_authority_context",
        title="Ahrefs: kontekst autorytetu",
        status="ready" if authority_facts else ("blocked" if connector_missing else "missing"),
        summary=(
            f"WILQ ma {len(authority_facts)} świeże fakty autorytetu z Ahrefs: "
            f"{_authority_summary(authority_facts)}."
            if authority_facts
            else _missing_authority_summary(connector_missing, latest_refresh)
        ),
        diagnosis=(
            "DR i Ahrefs Rank mogą wspierać priorytety SEO jako kontekst autorytetu, "
            "ale nie są samodzielnym dowodem luki treści, luki backlinków ani wzrostu ruchu."
            if authority_facts
            else (
                "Bez faktów autorytetu z Ahrefs WILQ nie może nawet użyć "
                "Ahrefs jako kontekstu SEO."
            )
        ),
        next_step=(
            "Użyj tych faktów jako pomocniczego kontekstu przy content/GSC review. "
            "Nie zamieniaj ich w claim o luce konkurencyjnej."
            if authority_facts
            else "Uruchom read-only Ahrefs vendor_read dla domain-rating, potem wróć do /ahrefs."
        ),
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(authority_facts, latest_refresh),
        metric_facts=authority_facts,
        blocked_claims=[] if authority_facts else AHREFS_GAP_BLOCKED_CLAIMS,
        risk=ActionRisk.low if authority_facts else ActionRisk.medium,
    )

    missing_gap_contracts = _missing_gap_contracts(gap_facts)
    gap_section = AhrefsDiagnosticSection(
        id="ahrefs_gap_contract",
        title="Ahrefs: rekordy luk SEO",
        status="ready" if gap_facts else "blocked",
        summary=(
            f"WILQ ma {len(gap_facts)} rekordów luk z Ahrefs. Brakujące kontrakty: "
            f"{', '.join(missing_gap_contracts) or 'brak'}."
            if gap_facts
            else "WILQ nie ma jeszcze rekordów luk konkurencji, treści ani backlinków z Ahrefs."
        ),
        diagnosis=(
            "Rekordy luk można połączyć z GSC i WordPress inventory, ale tylko w zakresie "
            "konkretnych records z evidence IDs."
            if gap_facts
            else (
                "To jest brak kontraktu odczytu, nie brak promptu. DR/rank nie mówi, "
                "gdzie konkurencja ma przewagę ani które linki/treści trzeba zbudować."
            )
        ),
        next_step=(
            "Połącz rekordy luk z GSC/WordPress i przygotuj kolejkę review treści/backlinków."
            if gap_facts
            else (
                "Dodaj typed Ahrefs read contracts dla stron konkurencji, luk treści "
                "i luk backlinków."
            )
        ),
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(gap_facts, latest_refresh),
        metric_facts=gap_facts[:12],
        blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
        risk=ActionRisk.low if gap_facts else ActionRisk.medium,
    )

    safety_section = AhrefsDiagnosticSection(
        id="ahrefs_action_safety",
        title="Bezpieczeństwo decyzji Ahrefs",
        status="blocked" if not gap_facts else "ready",
        summary=(
            "Ahrefs jest źródłem read-only. WILQ nie może robić claimów o luce treści, "
            "luce backlinków ani wzroście ruchu bez konkretnych records i "
            "walidacji przez operatora."
        ),
        diagnosis=(
            "Metryki autorytetu są pomocne, ale zbyt ogólne. Decyzje contentowe muszą przejść "
            "przez Content Planner, GSC/WordPress inventory i ActionObject review."
        ),
        next_step="Zostaw apply/write path zablokowany. Najpierw dodaj brakujące read contracts.",
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(
            [*authority_facts, *gap_facts],
            latest_refresh,
        ),
        blocked_claims=AHREFS_GAP_BLOCKED_CLAIMS,
        risk=ActionRisk.medium,
    )
    return [authority_section, gap_section, safety_section]


def _ahrefs_decision_queue(
    *,
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[AhrefsDecisionItem]:
    decisions: list[AhrefsDecisionItem] = []
    if authority_facts:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_review_authority_context",
                decision_type="review_authority_context",
                status="ready",
                title="Użyj Ahrefs tylko jako kontekstu autorytetu",
                summary=_authority_summary(authority_facts),
                rationale=(
                    "WILQ ma Ahrefs DR/rank z evidence, więc może dodać kontekst "
                    "autorytetu do SEO/content review. To nadal nie jest analiza luk."
                ),
                next_step=(
                    "Połącz ten kontekst z /content-planner i GSC. Nie twierdź, że "
                    "Ahrefs wykrył lukę treści/backlinków, dopóki nie ma rekordów luk."
                ),
                priority=25,
                metric_tiles=_authority_tiles(authority_facts, gap_facts),
                allowed_evidence=["domain_rating", "ahrefs_rank", "authority_summary"],
                missing_read_contracts=_missing_gap_contracts(gap_facts),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_evidence_ids_for_facts_or_refresh(authority_facts, latest_refresh),
                metric_facts=authority_facts,
                action_ids=[],
                blocked_claims=_blocked_claims_for_missing_contracts(
                    _missing_gap_contracts(gap_facts)
                ),
                risk=ActionRisk.low,
            )
        )
    else:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_run_authority_read_before_gap_review",
                decision_type="run_authority_read",
                status="blocked",
                title="Uruchom odczyt autorytetu Ahrefs przed review luk SEO",
                summary=_missing_authority_summary(connector_missing, latest_refresh),
                rationale=(
                    "Bez świeżych faktów autorytetu Ahrefs WILQ nie powinien nawet używać "
                    "Ahrefs jako kontekstu SEO."
                ),
                next_step=(
                    "Sprawdź credential AHREFS_API_TOKEN i wykonaj read-only Ahrefs vendor_read."
                    if connector_missing
                    else "Wykonaj read-only Ahrefs vendor_read, potem wróć do /ahrefs."
                ),
                priority=10,
                metric_tiles={"fakty Ahrefs": 0, "braki kontraktu": len(AHREFS_GAP_READ_CONTRACTS)},
                allowed_evidence=[],
                missing_read_contracts=["domain_rating", *AHREFS_GAP_READ_CONTRACTS],
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
                action_ids=[],
                blocked_claims=AHREFS_GAP_BLOCKED_CLAIMS,
                risk=ActionRisk.medium,
            )
        )

    missing_gap_contracts = _missing_gap_contracts(gap_facts)
    if missing_gap_contracts:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_block_gap_claims_without_records",
                decision_type="block_gap_claims",
                status="blocked",
                title="Nie wskazuj luk konkurencji bez rekordów Ahrefs",
                summary=(
                    "Brakuje typed records Ahrefs dla luk treści, luk backlinków, "
                    "organicznych słów kluczowych i top pages konkurencji."
                ),
                rationale=(
                    "DR/rank to metryki domeny. Nie mówią, które treści, linki albo "
                    "konkurenci tworzą realną przestrzeń do działania."
                ),
                next_step=(
                    "Dodaj read-only contracts: strony konkurencji, rekordy luk treści, "
                    "rekordy luk backlinków, organiczne słowa per URL i top pages konkurencji."
                ),
                priority=12,
                metric_tiles={
                    "braki kontraktu": len(missing_gap_contracts),
                    "blokady claimów": len(
                        _blocked_claims_for_missing_contracts(missing_gap_contracts)
                    ),
                },
                allowed_evidence=["domain_rating", "ahrefs_rank"] if authority_facts else [],
                missing_read_contracts=missing_gap_contracts,
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_evidence_ids_for_facts_or_refresh(authority_facts, latest_refresh),
                action_ids=[],
                blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
                risk=ActionRisk.medium,
            )
        )
    return decisions


def _authority_summary(authority_facts: list[MetricFact]) -> str:
    domain_rating = _fact_value(authority_facts, "domain_rating")
    ahrefs_rank = _fact_value(authority_facts, "ahrefs_rank")
    parts = []
    if domain_rating is not None:
        parts.append(f"domain_rating={domain_rating}")
    if ahrefs_rank is not None:
        parts.append(f"ahrefs_rank={ahrefs_rank}")
    return ", ".join(parts) if parts else "brak faktów autorytetu"


def _missing_authority_summary(
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
) -> str:
    if connector_missing:
        return (
            "Ahrefs connector ma brakujące credential names: "
            f"{', '.join(connector_missing)}."
        )
    if latest_refresh and latest_refresh.status != ConnectorRefreshStatus.completed:
        return f"Ostatni Ahrefs refresh zakończył się statusem {latest_refresh.status.value}."
    return "WILQ nie ma świeżych faktów autorytetu Ahrefs w metric store."


def _authority_tiles(
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> dict[str, int | float | str]:
    return _clean_metric_tiles(
        {
            "DR": _fact_value(authority_facts, "domain_rating"),
            "Ahrefs Rank": _fact_value(authority_facts, "ahrefs_rank"),
            "fakty luk": len(gap_facts),
            "braki kontraktu": len(_missing_gap_contracts(gap_facts)),
        }
    )


def _missing_gap_contracts(gap_facts: list[MetricFact]) -> list[str]:
    if not gap_facts:
        return AHREFS_GAP_READ_CONTRACTS.copy()
    # Future-proof for detailed records: each gap contract is considered present only
    # after a matching metric fact exists. Current domain-rating reads intentionally
    # leave all gap contracts missing.
    fact_names = {fact.name for fact in gap_facts}
    present_by_fact = {
        "ahrefs_competitor_pages": {"ahrefs_competitor_page_count"},
        "ahrefs_content_gap_records": {"ahrefs_content_gap_count"},
        "ahrefs_backlink_gap_records": {
            "ahrefs_backlink_gap_count",
            "ahrefs_referring_domain_gap_count",
        },
        "ahrefs_organic_keywords_by_url": {"ahrefs_organic_keyword_gap_count"},
        "ahrefs_top_pages_by_competitor": {"ahrefs_competitor_page_count"},
    }
    return [
        contract
        for contract in AHREFS_GAP_READ_CONTRACTS
        if not fact_names.intersection(present_by_fact[contract])
    ]


def _blocked_claims_for_missing_contracts(missing_contracts: list[str]) -> list[str]:
    claims_by_contract = {
        "ahrefs_competitor_pages": "competitor gap",
        "ahrefs_content_gap_records": "content gap",
        "ahrefs_backlink_gap_records": "backlink gap",
        "ahrefs_organic_keywords_by_url": "ranking opportunity",
        "ahrefs_top_pages_by_competitor": "traffic uplift",
    }
    claims = [
        claim
        for contract, claim in claims_by_contract.items()
        if contract in missing_contracts
    ]
    claims.append("authority improvement")
    return _unique(claims)


def _fact_value(facts: list[MetricFact], name: str) -> int | float | str | None:
    for fact in facts:
        if fact.name == name:
            return fact.value
    return None


def _clean_metric_tiles(
    tiles: dict[str, int | float | str | None],
) -> dict[str, int | float | str]:
    return {key: value for key, value in tiles.items() if value is not None}


def _evidence_ids_for_facts_or_refresh(
    facts: list[MetricFact],
    run: ConnectorRefreshRun | None,
) -> list[str]:
    fact_evidence_ids = _unique(fact.evidence_id for fact in facts if fact.evidence_id)
    if fact_evidence_ids:
        return fact_evidence_ids
    return _refresh_or_connector_evidence_ids(run)


def _refresh_or_connector_evidence_ids(run: ConnectorRefreshRun | None) -> list[str]:
    if run and run.evidence_ids:
        return run.evidence_ids
    return [connector_evidence_id(AHREFS_CONNECTOR_ID)]


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
