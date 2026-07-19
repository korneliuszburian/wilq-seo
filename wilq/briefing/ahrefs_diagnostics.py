from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal, cast

from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.content.planning.ahrefs import ahrefs_cross_source_candidate_rows
from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import evidence_count_label, source_connector_labels
from wilq.schemas import (
    ActionRisk,
    AhrefsDecisionItem,
    AhrefsDiagnosticSection,
    AhrefsDiagnosticsResponse,
    AhrefsGapReadContract,
    AhrefsGapRecord,
    AhrefsOperatorSummary,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ContentAhrefsCandidateRow,
    MetricFact,
    connector_refresh_has_live_data,
    connector_refresh_run_status_label,
)
from wilq.storage.metric_store import metric_store

AhrefsGapType = Literal[
    "competitor_page",
    "content_gap",
    "backlink_gap",
    "organic_keyword_gap",
    "top_page_gap",
]

AHREFS_CONNECTOR_ID = "ahrefs"
AHREFS_CONTENT_REFRESH_ACTION_ID = "act_prepare_content_refresh_queue"
AHREFS_CROSS_CHECK_CONNECTOR_IDS = (
    "google_search_console",
    "wordpress_ekologus",
    "wordpress_sklep",
)
AHREFS_METRIC_FACT_LIMIT = 1000
AHREFS_CROSS_CHECK_METRIC_FACT_LIMIT = 1200
AHREFS_AUTHORITY_FACT_NAMES = {"domain_rating", "ahrefs_rank"}
AHREFS_COMPETITOR_READ_FACT_NAMES = {
    "organic_competitor_read_status",
    "organic_competitor_rows",
    "organic_competitor_country",
    "organic_competitor_mode",
}
AHREFS_GAP_FACT_NAMES = {
    "ahrefs_competitor_page_count",
    "ahrefs_content_gap_count",
    "ahrefs_backlink_gap_count",
    "ahrefs_referring_domain_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
}
AHREFS_GAP_READ_CONTRACTS = [
    "ahrefs_competitor_pages",
    "ahrefs_content_gap_records",
    "ahrefs_backlink_gap_records",
    "ahrefs_organic_keywords_by_url",
    "ahrefs_top_pages_by_competitor",
]
AHREFS_GAP_BLOCKED_CLAIMS = [
    "luka względem konkurencji",
    "luka treści",
    "luka linków",
    "szansa na wzrost pozycji",
    "wzrost ruchu",
    "wzrost autorytetu",
]
AHREFS_GAP_IMPACT_BLOCKED_CLAIMS = [
    "wzrost ruchu",
    "wzrost autorytetu",
]
AHREFS_KNOWLEDGE_CARD_IDS = ["card_ahrefs_content_gap_playbook"]
AHREFS_EXPERT_RULE_IDS = ["content_brief_rules_v1"]
AHREFS_GAP_TYPES = {
    "competitor_page",
    "content_gap",
    "backlink_gap",
    "organic_keyword_gap",
    "top_page_gap",
}
AHREFS_DECISION_TYPE_LABELS = {
    "review_authority_context": "kontekst autorytetu",
    "review_gap_records": "sprawdzenie luk",
    "run_authority_read": "odczyt autorytetu",
    "block_gap_claims": "blokada luk",
}
AHREFS_GAP_TYPE_LABELS = {
    "competitor_page": "strona konkurencji",
    "content_gap": "luka treści",
    "backlink_gap": "luka linków",
    "organic_keyword_gap": "luka słów organicznych",
    "top_page_gap": "luka najlepszych stron konkurencji",
}
AHREFS_METRIC_FACT_LABELS = {
    "domain_rating": "ocena domeny Ahrefs",
    "ahrefs_rank": "pozycja w rankingu Ahrefs",
    "organic_competitor_read_status": "status odczytu konkurencji",
    "organic_competitor_rows": "konkurenci organiczni",
    "organic_competitor_country": "kraj odczytu konkurencji",
    "organic_competitor_mode": "zakres odczytu konkurencji",
    "ahrefs_competitor_page_count": "strony konkurencji",
    "ahrefs_content_gap_count": "luki treści",
    "ahrefs_backlink_gap_count": "luki linków",
    "ahrefs_referring_domain_gap_count": "luki domen linkujących",
    "ahrefs_organic_keyword_gap_count": "luki słów organicznych",
    "ahrefs_top_page_gap_count": "luki najlepszych stron konkurencji",
    "authority_summary": "podsumowanie autorytetu domeny",
}
AHREFS_READ_CONTRACT_LABELS = {
    "ahrefs_authority_summary": "podsumowanie autorytetu domeny",
    "ahrefs_gap_metric_facts": "metryki luk z Ahrefs",
    "ahrefs_competitor_pages": "strony konkurencji",
    "ahrefs_content_gap_records": "rekordy luk treści",
    "ahrefs_backlink_gap_records": "rekordy luk linków",
    "ahrefs_organic_keywords_by_url": "organiczne słowa dla URL",
    "ahrefs_top_pages_by_competitor": "najlepsze strony konkurencji",
    "domain_rating": "ocena domeny Ahrefs",
}
AHREFS_REVIEW_GATE_LABELS = {
    "ahrefs_gap_records_required": "wymagane konkretne rekordy luk Ahrefs",
    "content_workflow_review_required": "sprawdzenie w workflow treści",
    "human_strategy_review": "sprawdzenie strategii przez człowieka",
}
AHREFS_REVIEWABLE_GAP_RECORD_LIMIT = 8
AHREFS_EKOLOGUS_RELEVANCE_TERMS = (
    "bdo",
    "odpady",
    "odpad",
    "srodowisko",
    "srodowiskowy",
    "remediacja",
    "operat",
    "wodnoprawny",
    "pozwolenie",
    "zintegrowane",
    "zielony lad",
    "ppwr",
    "recykling",
    "emisja",
    "esg",
    "beczka",
    "sorbent",
    "wanna wychwytowa",
    "magazynowanie",
    "substancje",
    "chemiczne",
    "denios",
)
AHREFS_RELEVANT_COMPETITOR_DOMAINS = {
    "denios.pl",
    "dla-przemyslu.pl",
    "manutan.pl",
}
AHREFS_OFF_TOPIC_TERMS = (
    "prawo jazdy",
    "kalkulator oc",
    "ubezpieczenie samochodu",
    "samochod",
    "samochodu",
    "ubezpieczenie",
    "oc",
    "ac",
)
AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS = {
    "cuk.pl",
    "ltesty.pl",
}
AHREFS_BROAD_BACKLINK_DOMAINS = {
    "apple.com",
    "google.com",
    "waze.com",
    "wikipedia.org",
    "youtube.com",
    "businessinsider.com.pl",
    "storeleads.app",
    "trustedshops.pl",
    "wykop.pl",
}
AHREFS_RELEVANCE_STOPWORDS = {
    "https",
    "http",
    "www",
    "com",
    "pl",
    "dla",
    "oraz",
    "jest",
    "jak",
    "czy",
    "the",
}
POLISH_ASCII_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "a",
        "Ć": "c",
        "Ę": "e",
        "Ł": "l",
        "Ń": "n",
        "Ó": "o",
        "Ś": "s",
        "Ź": "z",
        "Ż": "z",
    }
)


@dataclass(frozen=True)
class AhrefsGapCrossCheck:
    candidates: list[ContentAhrefsCandidateRow]
    status: Literal["api_backed", "manual_required", "missing"]
    gsc_match_count: int
    wordpress_match_count: int
    source_connectors: list[str]
    evidence_ids: list[str]


def build_ahrefs_diagnostics() -> AhrefsDiagnosticsResponse:
    connector = get_connector_status(AHREFS_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Ahrefs connector is not registered.")

    refresh_runs = list_connector_refresh_runs(connector_id=AHREFS_CONNECTOR_ID)
    latest_refresh = _latest_relevant_ahrefs_refresh(refresh_runs)
    metric_facts = _facts_for_known_refresh_runs(
        metric_store().list_metric_facts(
            connector_id=AHREFS_CONNECTOR_ID,
            limit=AHREFS_METRIC_FACT_LIMIT,
        ),
        refresh_runs,
    )
    authority_facts = _latest_facts_by_name(metric_facts, AHREFS_AUTHORITY_FACT_NAMES)
    competitor_read_facts = _latest_facts_by_name(
        metric_facts,
        AHREFS_COMPETITOR_READ_FACT_NAMES,
    )
    gap_facts = _gap_facts(metric_facts)
    cross_check_facts = _cross_check_metric_facts()
    live_data_available = bool(authority_facts or competitor_read_facts or gap_facts)
    sections = _ahrefs_sections(
        connector_missing=connector.missing_credentials,
        latest_refresh=latest_refresh,
        authority_facts=authority_facts,
        competitor_read_facts=competitor_read_facts,
        gap_facts=gap_facts,
    )
    decision_queue = _ahrefs_decisions_with_lineage(
        _ahrefs_decision_queue(
            connector_missing=connector.missing_credentials,
            latest_refresh=latest_refresh,
            authority_facts=authority_facts,
            competitor_read_facts=competitor_read_facts,
            gap_facts=gap_facts,
        )
    )
    gap_read_contract = _ahrefs_gap_read_contract(
        latest_refresh=latest_refresh,
        authority_facts=authority_facts,
        gap_facts=gap_facts,
        cross_check_facts=cross_check_facts,
    )
    labeled_gap_read_contract = _label_ahrefs_gap_read_contract(gap_read_contract)

    evidence_ids = _unique(
        [
            *(evidence_id for section in sections for evidence_id in section.evidence_ids),
            *(evidence_id for decision in decision_queue for evidence_id in decision.evidence_ids),
            *labeled_gap_read_contract.evidence_ids,
        ]
    )
    action_ids = _unique(
        [
            *(action_id for section in sections for action_id in section.action_ids),
            *(action_id for decision in decision_queue for action_id in decision.action_ids),
            *labeled_gap_read_contract.action_ids,
        ]
    )
    response_source_connectors = _unique(
        [
            *(connector for section in sections for connector in section.source_connectors),
            *(connector for decision in decision_queue for connector in decision.source_connectors),
            *labeled_gap_read_contract.source_connectors,
        ]
    )
    return AhrefsDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        connector_status_label=_ahrefs_connector_status_label(str(connector.status)),
        latest_refresh=latest_refresh,
        latest_refresh_status_label=_ahrefs_refresh_status_label(latest_refresh)
        if latest_refresh
        else None,
        live_data_status_label=_ahrefs_live_data_status_label(live_data_available),
        live_data_available=live_data_available,
        authority_fact_count=len(authority_facts),
        gap_fact_count=len(gap_facts),
        gap_read_contract=labeled_gap_read_contract,
        operator_summary=_operator_summary(
            decision_queue,
            labeled_gap_read_contract,
            len(authority_facts),
            len(gap_facts),
        ),
        decision_queue=decision_queue,
        sections=[_label_ahrefs_section(section) for section in sections],
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_count_label(evidence_ids),
        source_connector_labels=source_connector_labels(response_source_connectors),
        action_ids=action_ids,
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
    )


def _operator_summary(
    decisions: list[AhrefsDecisionItem],
    gap_read_contract: AhrefsGapReadContract,
    authority_fact_count: int,
    gap_fact_count: int,
) -> AhrefsOperatorSummary:
    top_decisions = decisions[:4]
    available_contracts = gap_read_contract.available_read_contracts
    missing_contracts = gap_read_contract.missing_read_contracts
    return _label_ahrefs_operator_summary(
        AhrefsOperatorSummary(
            title="Co marketer ma wiedzieć o Ahrefs",
            summary=(
                "Ten widok pokazuje, czy Ahrefs może wesprzeć decyzje SEO i treści. "
                "Autorytet domeny może być kontekstem, ale wnioski o lukach treści "
                "lub linków zwrotnych wymagają konkretnych danych Ahrefs."
            ),
            next_step=_operator_summary_next_step(gap_read_contract),
            review_decision_after_review=_ahrefs_review_decision_after_review(
                gap_read_contract
            ),
            review_question_for_operator=_ahrefs_review_question_for_operator(
                gap_read_contract
            ),
            review_next_safe_click=_ahrefs_review_next_safe_click(gap_read_contract),
            review_action_ids=list(gap_read_contract.action_ids),
            top_decision_ids=[decision.id for decision in top_decisions],
            gap_read_status=gap_read_contract.status,
            authority_fact_count=authority_fact_count,
            gap_fact_count=gap_fact_count,
            available_read_contracts=available_contracts,
            available_read_contract_labels=_labels_for_values(
                available_contracts,
                _ahrefs_read_contract_label,
            ),
            missing_read_contracts=missing_contracts,
            missing_read_contract_labels=_labels_for_values(
                missing_contracts,
                _missing_gap_contract_label,
            ),
            source_connectors=_unique(
                [
                    *(
                        connector
                        for decision in top_decisions
                        for connector in decision.source_connectors
                    ),
                    *gap_read_contract.source_connectors,
                ]
            ),
            evidence_ids=_unique(
                [
                    *(
                        evidence_id
                        for decision in top_decisions
                        for evidence_id in decision.evidence_ids
                    ),
                    *gap_read_contract.evidence_ids,
                ]
            ),
            action_ids=_unique(
                [
                    *(action_id for decision in top_decisions for action_id in decision.action_ids),
                    *gap_read_contract.action_ids,
                ]
            ),
            blocked_claims=_unique(
                [
                    *(claim for decision in top_decisions for claim in decision.blocked_claims),
                    *gap_read_contract.blocked_claims,
                ]
            ),
        )
    )


def _operator_summary_next_step(gap_read_contract: AhrefsGapReadContract) -> str:
    if gap_read_contract.status == "ready":
        return (
            "Połącz kontekst autorytetu z rekordami luk Ahrefs, widokiem Treści i GSC. "
            "Przygotuj sprawdzenie treści/linków bez obietnic wzrostu widoczności."
        )
    return (
        "Użyj najważniejszych decyzji Ahrefs jako kontekstu dla widoku Treści. "
        "Nie twierdź o lukach treści, lukach linków ani wzroście widoczności "
        "bez konkretnych danych Ahrefs."
    )


def _ahrefs_review_decision_after_review(
    gap_read_contract: AhrefsGapReadContract,
) -> str:
    if gap_read_contract.status == "ready":
        if gap_read_contract.cross_check_status == "api_backed":
            return (
                "Po review wybierz, czy temat z Ahrefs idzie do odświeżenia albo "
                "scalenia istniejącej treści, osobnego briefu contentowego, link-review "
                "czy zostaje w obserwacji. Sprawdzenie GSC i WordPress jest dostępne, "
                "ale nadal nie odblokowuje obietnic wzrostu ruchu ani autorytetu."
            )
        return (
            "Po review zdecyduj, czy luka z Ahrefs ma przejść do dalszego "
            "sprawdzenia GSC i WordPress, briefu contentowego, link-review czy "
            "obserwacji. Bez cross-checku nie traktuj jej jako gotowego tematu."
        )
    return (
        "Po review możesz użyć Ahrefs tylko jako kontekstu autorytetu. Luki treści, "
        "luki linków i przewaga konkurencji zostają zablokowane do czasu brakujących "
        "rekordów Ahrefs."
    )


def _ahrefs_review_question_for_operator(
    gap_read_contract: AhrefsGapReadContract,
) -> str:
    if gap_read_contract.status == "ready":
        return (
            "Który temat z Ahrefs ma największy sens dla Ekologus po porównaniu "
            "intencji, istniejącego URL, GSC i WordPress: odświeżenie, scalenie, "
            "nowy brief, link-review czy obserwacja?"
        )
    return (
        "Czy dostępne dane Ahrefs wystarczają tylko do kontekstu autorytetu, "
        "czy najpierw trzeba odświeżyć/uzupełnić rekordy luk treści i linków?"
    )


def _ahrefs_review_next_safe_click(gap_read_contract: AhrefsGapReadContract) -> str:
    if AHREFS_CONTENT_REFRESH_ACTION_ID in gap_read_contract.action_ids:
        return (
            f"Uruchom podgląd bez zapisu dla {AHREFS_CONTENT_REFRESH_ACTION_ID}, "
            "ale dopiero po ręcznym review intencji, GSC, WordPress i zakresu "
            "treści/linków. To nie publikuje treści i nie tworzy automatycznego briefu."
        )
    if gap_read_contract.cross_check_status == "manual_required":
        return (
            "Najpierw ręcznie porównaj temat Ahrefs z zapytaniami GSC i spisem WordPress. "
            "Słabe podobieństwo nie odblokowuje podglądu kolejki ani briefu."
        )
    return (
        "Najpierw odśwież lub uzupełnij dane Ahrefs; bez rekordów luk nie ma "
        "bezpiecznego kliknięcia do kolejki treści."
    )


def _facts_for_known_refresh_runs(
    metric_facts: list[MetricFact],
    refresh_runs: list[ConnectorRefreshRun],
) -> list[MetricFact]:
    known_evidence_ids = {
        evidence_id
        for run in refresh_runs
        for evidence_id in run.evidence_ids
        if evidence_id.startswith("ev_refresh_")
    }
    if not known_evidence_ids:
        return metric_facts
    return [fact for fact in metric_facts if fact.evidence_id in known_evidence_ids]


def _ahrefs_gap_read_contract(
    *,
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
    cross_check_facts: list[MetricFact],
) -> AhrefsGapReadContract:
    missing_contracts = _missing_gap_contracts(gap_facts)
    gap_records = _ahrefs_gap_records(gap_facts)
    cross_check = _build_ahrefs_gap_cross_check(
        gap_facts=gap_facts,
        cross_check_facts=cross_check_facts,
        gap_records=gap_records,
    )
    blocked_claims = _blocked_claims_for_missing_contracts(missing_contracts)
    evidence_ids = _unique(
        [
            *_evidence_ids_for_facts_or_refresh(
                [*gap_facts, *authority_facts],
                latest_refresh,
            ),
            *cross_check.evidence_ids,
        ]
    )
    available_contracts = []
    if authority_facts:
        available_contracts.append("ahrefs_authority_summary")
    if gap_facts:
        available_contracts.append("ahrefs_gap_metric_facts")
        available_contracts.extend(_available_gap_contracts(missing_contracts))
    allowed_evidence = _allowed_gap_evidence(authority_facts, gap_facts)
    action_ids = _ahrefs_gap_action_ids(
        gap_records=gap_records,
        missing_contracts=missing_contracts,
        cross_check_status=cross_check.status,
    )
    return AhrefsGapReadContract(
        status="ready" if gap_records and not missing_contracts else "blocked",
        title="Luki SEO z Ahrefs",
        summary=(
            f"WILQ ma {_ahrefs_gap_record_count_label(len(gap_records))} z Ahrefs. "
            f"Brakujące dane: {_missing_gap_contracts_summary(missing_contracts)}."
        ),
        available_read_contracts=available_contracts,
        available_read_contract_labels=_labels_for_values(
            available_contracts,
            _ahrefs_read_contract_label,
        ),
        missing_read_contracts=missing_contracts,
        missing_read_contract_labels=_labels_for_values(
            missing_contracts,
            _missing_gap_contract_label,
        ),
        allowed_evidence=allowed_evidence,
        allowed_evidence_labels=_labels_for_values(
            allowed_evidence,
            _ahrefs_metric_fact_label,
        ),
        blocked_claims=blocked_claims,
        operator_review_gates=[
            "ahrefs_gap_records_required",
            "content_workflow_review_required",
            "human_strategy_review",
        ],
        operator_review_gate_labels=_labels_for_values(
            [
                "ahrefs_gap_records_required",
                "content_workflow_review_required",
                "human_strategy_review",
            ],
            _ahrefs_review_gate_label,
        ),
        source_connectors=_unique([AHREFS_CONNECTOR_ID, *cross_check.source_connectors]),
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        gap_records=gap_records,
        gap_record_count=len(gap_records),
        cross_check_status=cross_check.status,
        cross_check_status_label=_ahrefs_cross_check_status_label(cross_check.status),
        cross_check_summary=_ahrefs_cross_check_summary(
            status=cross_check.status,
            candidate_count=len(cross_check.candidates),
            gsc_match_count=cross_check.gsc_match_count,
            wordpress_match_count=cross_check.wordpress_match_count,
        ),
        cross_check_next_step=_ahrefs_cross_check_next_step(cross_check.status),
        cross_check_gsc_match_count=cross_check.gsc_match_count,
        cross_check_wordpress_match_count=cross_check.wordpress_match_count,
        cross_check_source_connectors=cross_check.source_connectors,
        cross_check_evidence_ids=cross_check.evidence_ids,
        cross_check_candidates=cross_check.candidates,
        next_step=_ahrefs_gap_read_next_step(
            missing_contracts=missing_contracts,
            cross_check_status=cross_check.status,
        ),
        risk=ActionRisk.medium,
    )


def _build_ahrefs_gap_cross_check(
    *,
    gap_facts: list[MetricFact],
    cross_check_facts: list[MetricFact],
    gap_records: list[AhrefsGapRecord],
) -> AhrefsGapCrossCheck:
    candidates = ahrefs_cross_source_candidate_rows(gap_facts, cross_check_facts, limit=6)
    gsc_match_count = sum(
        candidate.gsc_cross_check.strength == "exact" for candidate in candidates
    )
    wordpress_match_count = sum(
        candidate.wordpress_cross_check.strength == "exact" for candidate in candidates
    )
    source_connectors, evidence_ids = _ahrefs_cross_check_trace(candidates)
    return AhrefsGapCrossCheck(
        candidates=candidates,
        status=_ahrefs_cross_check_status(
            gap_records=gap_records,
            gsc_match_count=gsc_match_count,
            wordpress_match_count=wordpress_match_count,
        ),
        gsc_match_count=gsc_match_count,
        wordpress_match_count=wordpress_match_count,
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
    )


def _ahrefs_gap_action_ids(
    *,
    gap_records: list[AhrefsGapRecord],
    missing_contracts: list[str],
    cross_check_status: str,
) -> list[str]:
    if gap_records and not missing_contracts and cross_check_status == "api_backed":
        return [AHREFS_CONTENT_REFRESH_ACTION_ID]
    return []


def _ahrefs_gap_read_next_step(
    *,
    missing_contracts: list[str],
    cross_check_status: str,
) -> str:
    if missing_contracts:
        return (
            "Dodaj odczyty danych dla konkurencyjnych stron, luk treści, luk linków zwrotnych, "
            "organicznych słów dla URL i najlepszych stron konkurencji. Do tego "
            "czasu używaj Ahrefs tylko jako kontekstu autorytetu."
        )
    if cross_check_status == "manual_required":
        return (
            "Ręcznie sprawdź każdy temat Ahrefs w GSC i spisie WordPress. Słabe podobieństwo "
            "nie odblokowuje briefu, decyzji o duplikacie ani kolejki do podglądu."
        )
    return "Połącz luki Ahrefs z GSC i WordPress, potem przygotuj kolejkę sprawdzenia."


def _cross_check_metric_facts() -> list[MetricFact]:
    facts: list[MetricFact] = []
    for connector_id in AHREFS_CROSS_CHECK_CONNECTOR_IDS:
        facts.extend(
            metric_store().list_metric_facts(
                connector_id=connector_id,
                limit=AHREFS_CROSS_CHECK_METRIC_FACT_LIMIT,
            )
        )
    return facts


def _ahrefs_cross_check_trace(
    candidates: Iterable[ContentAhrefsCandidateRow],
) -> tuple[list[str], list[str]]:
    exact_checks = [
        check
        for candidate in candidates
        for check in (candidate.gsc_cross_check, candidate.wordpress_cross_check)
        if check.strength == "exact"
    ]
    return (
        _unique(connector for check in exact_checks for connector in check.source_connectors),
        _unique(evidence_id for check in exact_checks for evidence_id in check.evidence_ids),
    )


def _ahrefs_cross_check_status(
    *,
    gap_records: list[AhrefsGapRecord],
    gsc_match_count: int,
    wordpress_match_count: int,
) -> Literal["api_backed", "manual_required", "missing"]:
    if not gap_records:
        return "missing"
    if gsc_match_count or wordpress_match_count:
        return "api_backed"
    return "manual_required"


def _ahrefs_cross_check_status_label(status: str) -> str:
    labels = {
        "api_backed": "sprawdzenie GSC i WordPress ma dopasowania z API",
        "manual_required": "sprawdzenie GSC i WordPress wymaga ręcznej oceny",
        "missing": "brak rekordów Ahrefs do cross-checku",
    }
    return labels.get(status, "cross-check do sprawdzenia")


def _ahrefs_cross_check_summary(
    *,
    status: str,
    candidate_count: int,
    gsc_match_count: int,
    wordpress_match_count: int,
) -> str:
    if status == "missing":
        return "Brak rekordów Ahrefs, więc WILQ nie ma czego łączyć z GSC ani WordPress."
    if status == "api_backed":
        return (
            f"WILQ znalazł {candidate_count} propozycji Ahrefs do walidacji: "
            f"{gsc_match_count} ma dopasowanie w GSC, a {wordpress_match_count} "
            "ma dopasowanie w spisie WordPress."
        )
    return (
        f"WILQ ma {candidate_count} propozycji Ahrefs, ale nie znalazł jeszcze "
        "dopasowania w GSC ani WordPress. To zostaje ręcznym cross-checkiem, "
        "nie brief-ready decyzją."
    )


def _ahrefs_cross_check_next_step(status: str) -> str:
    if status == "api_backed":
        return (
            "Otwórz propozycje z dopasowaniem GSC i WordPress i zdecyduj: brief, "
            "scalenie, obserwacja albo blokada tematu."
        )
    if status == "manual_required":
        return (
            "Sprawdź ręcznie GSC i spis WordPress dla tematów Ahrefs przed "
            "tworzeniem briefu."
        )
    return "Najpierw odczytaj rekordy luk Ahrefs, potem sprawdź GSC i WordPress."


def _latest_relevant_ahrefs_refresh(
    refresh_runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    for run in refresh_runs:
        if (
            run.mode.value == "vendor_read"
            and connector_refresh_has_live_data(run)
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


def _ahrefs_gap_records(gap_facts: list[MetricFact]) -> list[AhrefsGapRecord]:
    grouped_facts: dict[
        tuple[AhrefsGapType, str | None, str | None, str | None, str | None],
        list[MetricFact],
    ] = {}
    for fact in gap_facts:
        if not _is_record_level_gap_fact(fact):
            continue
        gap_type = _gap_type_for_fact(fact)
        source_url = _dimension_value(
            fact,
            "source_url",
            "competitor_url",
            "competitor_page",
            "source_page",
            "url",
            "page_url",
        )
        referenced_public_url = _dimension_value(
            fact,
            "referenced_public_url",
            "target_page",
            "ekologus_url",
            "ekologus_page",
            "page",
        )
        competitor_domain = _dimension_value(
            fact,
            "competitor_domain",
            "competitor",
            "domain",
        )
        keyword = _dimension_value(fact, "keyword", "query", "organic_keyword")
        key = (gap_type, source_url, referenced_public_url, competitor_domain, keyword)
        grouped_facts.setdefault(key, []).append(fact)

    records = [
        _ahrefs_gap_record(
            gap_type=gap_type,
            source_url=source_url,
            referenced_public_url=referenced_public_url,
            competitor_domain=competitor_domain,
            keyword=keyword,
            facts=facts,
        )
        for (
            gap_type,
            source_url,
            referenced_public_url,
            competitor_domain,
            keyword,
        ), facts in grouped_facts.items()
    ]
    scored_records = [(_gap_record_relevance_score(record), record) for record in records]
    reviewable_records = [(score, record) for score, record in scored_records if score >= 0]
    return [
        record
        for _, record in sorted(
            reviewable_records,
            key=lambda item: (
                -item[0],
                _gap_record_type_priority(item[1].gap_type),
                item[1].id,
            ),
        )[:AHREFS_REVIEWABLE_GAP_RECORD_LIMIT]
    ]


def _ahrefs_gap_record(
    *,
    gap_type: AhrefsGapType,
    source_url: str | None,
    referenced_public_url: str | None,
    competitor_domain: str | None,
    keyword: str | None,
    facts: list[MetricFact],
) -> AhrefsGapRecord:
    title = _gap_record_title(
        gap_type=gap_type,
        source_url=source_url,
        referenced_public_url=referenced_public_url,
        competitor_domain=competitor_domain,
        keyword=keyword,
    )
    return AhrefsGapRecord(
        id=_gap_record_id(gap_type, source_url, referenced_public_url, competitor_domain, keyword),
        gap_type=gap_type,
        gap_type_label=_gap_type_label(gap_type),
        title=title,
        summary=(
            f"{title}. Dane Ahrefs: {_gap_fact_summary(gap_type, facts)}. "
            "To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu."
        ),
        source_url=source_url,
        referenced_public_url=referenced_public_url,
        competitor_domain=competitor_domain,
        keyword=keyword,
        mapping_status=_gap_mapping_status(referenced_public_url, facts),
        derived_method=_gap_derived_method(facts),
        coverage_summary=_gap_coverage_summary(facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        metric_fact_labels=_metric_fact_labels_for_facts(facts),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        blocked_claims=AHREFS_GAP_IMPACT_BLOCKED_CLAIMS,
        next_step=_gap_record_next_step(gap_type),
        risk=ActionRisk.medium,
    )


def _gap_mapping_status(
    referenced_public_url: str | None,
    facts: list[MetricFact],
) -> Literal["unbound", "review_required", "exact"]:
    configured = next(
        (fact.dimensions.get("mapping_status") for fact in facts),
        None,
    )
    if configured == "exact" and referenced_public_url:
        return "exact"
    return "review_required" if referenced_public_url else "unbound"


def _gap_derived_method(facts: list[MetricFact]) -> str:
    return next(
        (
            fact.dimensions.get("gap_method")
            for fact in facts
            if fact.dimensions.get("gap_method")
        ),
        "różnica zbioru słów konkurencji i słów domeny docelowej",
    )


def _gap_coverage_summary(facts: list[MetricFact]) -> str:
    sample = next(
        (
            fact.dimensions.get("target_keyword_sample_size")
            for fact in facts
            if fact.dimensions.get("target_keyword_sample_size")
        ),
        None,
    )
    limit = next(
        (
            fact.dimensions.get("target_keyword_limit")
            for fact in facts
            if fact.dimensions.get("target_keyword_limit")
        ),
        None,
    )
    if sample and limit:
        return f"próbka domeny docelowej: {sample}; limit porównania: {limit}"
    return "zakres próby nie został podany w rekordzie"


def _gap_type_for_fact(fact: MetricFact) -> AhrefsGapType:
    configured_type = fact.dimensions.get("gap_type")
    if configured_type in AHREFS_GAP_TYPES:
        return cast(AhrefsGapType, configured_type)
    if fact.name == "ahrefs_competitor_page_count":
        return "competitor_page"
    if fact.name == "ahrefs_content_gap_count":
        return "content_gap"
    if fact.name in {"ahrefs_backlink_gap_count", "ahrefs_referring_domain_gap_count"}:
        return "backlink_gap"
    if fact.name == "ahrefs_organic_keyword_gap_count":
        return "organic_keyword_gap"
    if fact.name == "ahrefs_top_page_gap_count":
        return "top_page_gap"
    return "content_gap"


def _dimension_value(fact: MetricFact, *keys: str) -> str | None:
    for key in keys:
        value = fact.dimensions.get(key)
        if value:
            return value
    return None


def _is_record_level_gap_fact(fact: MetricFact) -> bool:
    return (
        _dimension_value(
            fact,
            "source_url",
            "competitor_url",
            "competitor_page",
            "source_page",
            "url",
            "page_url",
            "referenced_public_url",
            "target_page",
            "ekologus_url",
            "ekologus_page",
            "page",
            "competitor_domain",
            "competitor",
            "domain",
            "keyword",
            "query",
            "organic_keyword",
            "gap_type",
        )
        is not None
    )


def _gap_record_title(
    *,
    gap_type: AhrefsGapType,
    source_url: str | None,
    referenced_public_url: str | None,
    competitor_domain: str | None,
    keyword: str | None,
) -> str:
    anchor = keyword or referenced_public_url or source_url or competitor_domain or "brak wymiaru"
    labels = {
        "competitor_page": "Strona konkurencji",
        "content_gap": "Luka treści",
        "backlink_gap": "Luka linków zwrotnych",
        "organic_keyword_gap": "Luka słów organicznych",
        "top_page_gap": "Luka najlepszych stron konkurencji",
    }
    return f"{labels[gap_type]}: {anchor}"


def _gap_fact_summary(gap_type: AhrefsGapType, facts: list[MetricFact]) -> str:
    sorted_facts = sorted(facts, key=lambda fact: fact.name)
    if len(sorted_facts) > 1:
        signal_label = _ahrefs_count_word(len(sorted_facts), "sygnał", "sygnały", "sygnałów")
        return f"{len(sorted_facts)} {signal_label} Ahrefs typu {_gap_type_label(gap_type)}"
    return ", ".join(_gap_fact_value_label(fact) for fact in sorted_facts)


def _gap_fact_value_label(fact: MetricFact) -> str:
    if isinstance(fact.value, int | float):
        count = int(fact.value)
        count_labels = {
            "ahrefs_competitor_page_count": (
                "strona konkurencji",
                "strony konkurencji",
                "stron konkurencji",
            ),
            "ahrefs_content_gap_count": ("luka treści", "luki treści", "luk treści"),
            "ahrefs_backlink_gap_count": (
                "luka linków zwrotnych",
                "luki linków zwrotnych",
                "luk linków zwrotnych",
            ),
            "ahrefs_referring_domain_gap_count": (
                "luka domen linkujących",
                "luki domen linkujących",
                "luk domen linkujących",
            ),
            "ahrefs_organic_keyword_gap_count": (
                "luka w słowach organicznych",
                "luki w słowach organicznych",
                "luk w słowach organicznych",
            ),
            "ahrefs_top_page_gap_count": (
                "luka w najlepszych stronach konkurencji",
                "luki w najlepszych stronach konkurencji",
                "luk w najlepszych stronach konkurencji",
            ),
        }
        if fact.name in count_labels:
            one, few, many = count_labels[fact.name]
            return f"{count} {_ahrefs_count_word(count, one, few, many)}"

    return f"{_gap_fact_label(fact.name)}: {fact.value}"


def _gap_fact_label(name: str) -> str:
    return _ahrefs_metric_fact_label(name)


def _missing_gap_contracts_summary(missing_contracts: list[str]) -> str:
    if not missing_contracts:
        return "dane kompletne"
    return ", ".join(_missing_gap_contract_label(contract) for contract in missing_contracts)


def _ahrefs_gap_record_count_label(count: int) -> str:
    return f"{count} {_ahrefs_count_word(count, 'rekord luk', 'rekordy luk', 'rekordów luk')}"


def _ahrefs_count_word(count: int, one: str, few: str, many: str) -> str:
    absolute = abs(count)
    if absolute == 1:
        return one
    if 2 <= absolute % 10 <= 4 and absolute % 100 not in {12, 13, 14}:
        return few
    return many


def _missing_gap_contract_label(contract: str) -> str:
    return _ahrefs_read_contract_label(contract)


def _gap_type_label(gap_type: AhrefsGapType) -> str:
    return AHREFS_GAP_TYPE_LABELS[gap_type]


def _label_ahrefs_section(section: AhrefsDiagnosticSection) -> AhrefsDiagnosticSection:
    return section.model_copy(
        update={
            "status_label": _ahrefs_status_label(section.status),
            "blocked_claim_labels": section.blocked_claims,
        }
    )


def _label_ahrefs_decision(decision: AhrefsDecisionItem) -> AhrefsDecisionItem:
    return decision.model_copy(
        update={
            "status_label": _ahrefs_status_label(decision.status),
            "priority_label": _ahrefs_priority_label(decision.priority),
            "blocked_claim_labels": decision.blocked_claims,
        }
    )


def _label_ahrefs_gap_read_contract(
    contract: AhrefsGapReadContract,
) -> AhrefsGapReadContract:
    return contract.model_copy(
        update={
            "status_label": _ahrefs_status_label(contract.status),
            "blocked_claim_labels": contract.blocked_claims,
        }
    )


def _label_ahrefs_operator_summary(
    summary: AhrefsOperatorSummary,
) -> AhrefsOperatorSummary:
    return summary.model_copy(
        update={
            "gap_read_status_label": _ahrefs_status_label(summary.gap_read_status),
            "blocked_claim_labels": summary.blocked_claims,
        }
    )


def _ahrefs_status_label(status: str) -> str:
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
        "missing": "dane Ahrefs niepotwierdzone",
    }
    return labels.get(status, "status Ahrefs do sprawdzenia")


def _ahrefs_connector_status_label(status: str) -> str:
    labels = {
        "configured": "dostęp skonfigurowany",
        "missing_credentials": "brakuje dostępu",
        "disabled": "źródło wyłączone",
    }
    return labels.get(status, "status źródła do sprawdzenia")


def _ahrefs_refresh_status_label(run: ConnectorRefreshRun | object) -> str:
    if not isinstance(run, ConnectorRefreshRun):
        return "status odczytu do sprawdzenia"
    return connector_refresh_run_status_label(run)


def _ahrefs_live_data_status_label(live_data_available: bool) -> str:
    return "metryki Ahrefs dostępne" if live_data_available else "brak metryk Ahrefs"


def _ahrefs_priority_label(priority: int) -> str:
    if priority <= 10:
        return "pilne"
    if priority <= 30:
        return "wysoki priorytet"
    if priority <= 60:
        return "średni priorytet"
    return "niski priorytet"


def _ahrefs_decision_type_label(value: str) -> str:
    return AHREFS_DECISION_TYPE_LABELS.get(value, "decyzja Ahrefs")


def _ahrefs_metric_fact_label(name: str) -> str:
    return AHREFS_METRIC_FACT_LABELS.get(name, "metryka Ahrefs")


def _ahrefs_read_contract_label(contract: str) -> str:
    return AHREFS_READ_CONTRACT_LABELS.get(contract, "dane Ahrefs")


def _ahrefs_review_gate_label(gate: str) -> str:
    return AHREFS_REVIEW_GATE_LABELS.get(gate, "sprawdzenie przez operatora")


def _metric_fact_labels_for_facts(facts: list[MetricFact]) -> dict[str, str]:
    return {fact.name: _ahrefs_metric_fact_label(fact.name) for fact in facts}


def _labels_for_values(
    values: Iterable[str],
    labeler: Callable[[str], str],
) -> list[str]:
    return _unique(labeler(value) for value in values)


def _ahrefs_read_status_label(status: int | float | str | None) -> str:
    if status == "completed":
        return "zakończony"
    if status == "failed":
        return "błąd odczytu"
    if status == "blocked":
        return "zablokowany"
    if status:
        return "status wymaga sprawdzenia"
    return "brak statusu"


def _ahrefs_read_mode_label(mode: int | float | str | None) -> str:
    if mode == "subdomains":
        return "subdomeny"
    if mode == "exact":
        return "dokładna domena"
    if mode == "prefix":
        return "prefiks URL"
    if mode:
        return "zakres wymaga sprawdzenia"
    return "brak zakresu"


def _ahrefs_country_label(country: int | float | str | None) -> str:
    if country == "pl":
        return "Polska"
    if country:
        return str(country).upper()
    return "brak kraju"


def _gap_record_next_step(gap_type: AhrefsGapType) -> str:
    if gap_type == "backlink_gap":
        return (
            "Sprawdź ręcznie jakość domen/linków i nie planuj link buildingu bez "
            "sprawdzenia ryzyka oraz źródła."
        )
    if gap_type in {"content_gap", "organic_keyword_gap", "competitor_page", "top_page_gap"}:
        return (
            "Połącz rekord z GSC i spisem treści WordPress, potem zdecyduj: "
            "zachowanie, odświeżenie, scalenie, utworzenie albo blokada."
        )
    return "Przejrzyj rekord Ahrefs z operatorem przed jakąkolwiek rekomendacją."


def _gap_record_relevance_score(record: AhrefsGapRecord) -> int:
    text = " ".join(
        value
        for value in (
            record.keyword,
            record.source_url,
            record.referenced_public_url,
            record.competitor_domain,
        )
        if value
    )
    normalized_text = _normalize_text(text)
    tokens = _tokens_from_text(text)
    competitor_domain = _normalized_domain(record.competitor_domain)
    source_domain = _normalized_domain(record.source_url)
    if record.gap_type == "backlink_gap" and source_domain in AHREFS_BROAD_BACKLINK_DOMAINS:
        return -100
    score = 1

    if any(
        _matches_normalized_term(normalized_text, tokens, term)
        for term in AHREFS_EKOLOGUS_RELEVANCE_TERMS
    ):
        score += 4
    if competitor_domain in AHREFS_RELEVANT_COMPETITOR_DOMAINS:
        score += 3
    if record.gap_type in {"content_gap", "organic_keyword_gap", "top_page_gap"}:
        score += 1
    elif record.gap_type == "backlink_gap":
        score -= 1

    if any(
        _matches_normalized_term(normalized_text, tokens, term) for term in AHREFS_OFF_TOPIC_TERMS
    ):
        score -= 6
    if competitor_domain in AHREFS_OFF_TOPIC_COMPETITOR_DOMAINS:
        score -= 4
    if source_domain in AHREFS_BROAD_BACKLINK_DOMAINS:
        score -= 5
    return score


def _gap_record_type_priority(gap_type: AhrefsGapType) -> int:
    priorities = {
        "content_gap": 0,
        "organic_keyword_gap": 1,
        "top_page_gap": 2,
        "competitor_page": 3,
        "backlink_gap": 4,
    }
    return priorities[gap_type]


def _gap_record_id(
    gap_type: AhrefsGapType,
    source_url: str | None,
    referenced_public_url: str | None,
    competitor_domain: str | None,
    keyword: str | None,
) -> str:
    parts = [gap_type, competitor_domain, keyword, referenced_public_url, source_url]
    return f"ahrefs_gap_{_slug('_'.join(part for part in parts if part))}"


def _tokens_from_text(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", _normalize_text(text))
        if len(token) > 2 and token not in AHREFS_RELEVANCE_STOPWORDS
    }


def _matches_normalized_term(normalized_text: str, tokens: set[str], term: str) -> bool:
    normalized_term = _normalize_text(term)
    if " " in normalized_term:
        return normalized_term in normalized_text
    return normalized_term in tokens


def _normalize_text(text: str) -> str:
    translated = text.translate(POLISH_ASCII_TRANSLATION)
    ascii_text = unicodedata.normalize("NFKD", translated).encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _normalized_domain(value: str | None) -> str | None:
    if not value:
        return None
    normalized = _normalize_text(value).replace("https://", "").replace("http://", "")
    return normalized.split("/")[0].removeprefix("www.") or None


def _slug(value: str) -> str:
    normalized = []
    previous_separator = False
    for character in value.lower():
        if character.isalnum():
            normalized.append(character)
            previous_separator = False
        elif not previous_separator:
            normalized.append("_")
            previous_separator = True
    return "".join(normalized).strip("_")[:96] or "record"


def _ahrefs_sections(
    *,
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    competitor_read_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[AhrefsDiagnosticSection]:
    authority_section = AhrefsDiagnosticSection(
        id="ahrefs_authority_context",
        title="Ahrefs: kontekst autorytetu",
        status="ready" if authority_facts else ("blocked" if connector_missing else "missing"),
        summary=(
            f"WILQ ma {len(authority_facts)} świeże dane autorytetu z Ahrefs: "
            f"{_authority_summary(authority_facts)}. "
            f"{_competitor_read_summary(competitor_read_facts)}"
            if authority_facts
            else _missing_authority_summary(connector_missing, latest_refresh)
        ),
        diagnosis=(
            "Metryki autorytetu Ahrefs mogą wspierać priorytety SEO jako kontekst, "
            "ale nie są samodzielnym dowodem luki treści, luki linków zwrotnych ani wzrostu ruchu."
            if authority_facts
            else (
                "Bez danych autorytetu z Ahrefs WILQ nie może nawet użyć Ahrefs jako kontekstu SEO."
            )
        ),
        next_step=(
            "Użyj tych danych jako pomocniczego kontekstu przy sprawdzeniu treści i GSC. "
            "Nie zamieniaj ich w obietnicę przewagi nad konkurencją."
            if authority_facts
            else "Uruchom odczyt danych autorytetu Ahrefs, potem wróć do /ahrefs."
        ),
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(
            [*authority_facts, *competitor_read_facts],
            latest_refresh,
        ),
        metric_facts=[*authority_facts, *competitor_read_facts],
        metric_fact_labels=_metric_fact_labels_for_facts(
            [*authority_facts, *competitor_read_facts]
        ),
        blocked_claims=[] if authority_facts else AHREFS_GAP_BLOCKED_CLAIMS,
        risk=ActionRisk.low if authority_facts else ActionRisk.medium,
    )

    missing_gap_contracts = _missing_gap_contracts(gap_facts)
    gap_records = _ahrefs_gap_records(gap_facts)
    gap_section = AhrefsDiagnosticSection(
        id="ahrefs_gap_contract",
        title="Ahrefs: rekordy luk SEO",
        status="ready" if gap_records else "blocked",
        summary=(
            f"WILQ ma {_ahrefs_gap_record_count_label(len(gap_records))} z Ahrefs. Brakujące dane: "
            f"{_missing_gap_contracts_summary(missing_gap_contracts)}."
            if gap_records
            else (
                "WILQ nie ma jeszcze rekordów luk konkurencji, treści "
                "ani linków zwrotnych z Ahrefs."
            )
        ),
        diagnosis=(
            "Rekordy luk można połączyć z GSC i spisem treści WordPress, ale tylko w zakresie "
            "konkretnych danych z dowodami."
            if gap_records
            else (
                "To jest brak danych, nie brak promptu. DR/rank nie mówi, "
                "gdzie konkurencja ma przewagę ani które linki/treści trzeba zbudować."
            )
        ),
        next_step=(
            "Połącz rekordy luk z GSC i WordPress, "
            "potem przygotuj kolejkę sprawdzenia treści i linków."
            if gap_records
            else ("Dodaj odczyt danych Ahrefs dla stron konkurencji, luk treści i luk linków.")
        ),
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(gap_facts, latest_refresh),
        metric_facts=gap_facts[:12],
        metric_fact_labels=_metric_fact_labels_for_facts(gap_facts),
        blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
        risk=ActionRisk.low if gap_records else ActionRisk.medium,
    )

    safety_section = AhrefsDiagnosticSection(
        id="ahrefs_action_safety",
        title="Bezpieczeństwo decyzji Ahrefs",
        status="blocked" if not gap_facts else "ready",
        summary=(
            "Ahrefs jest źródłem danych do sprawdzenia. WILQ nie może obiecywać luki treści, "
            "luki linków zwrotnych ani wzrostu ruchu bez konkretnych danych i "
            "sprawdzenia przez operatora."
        ),
        diagnosis=(
            "Metryki autorytetu są pomocne, ale zbyt ogólne. Decyzje treściowe muszą przejść "
            "przez widok treści, GSC, spis treści WordPress i przegląd akcji."
        ),
        next_step="Zostaw zapis zmian zablokowany. Najpierw dodaj brakujące odczyty danych.",
        source_connectors=[AHREFS_CONNECTOR_ID],
        evidence_ids=_evidence_ids_for_facts_or_refresh(
            [*authority_facts, *gap_facts],
            latest_refresh,
        ),
        metric_fact_labels=_metric_fact_labels_for_facts([*authority_facts, *gap_facts]),
        blocked_claims=AHREFS_GAP_BLOCKED_CLAIMS,
        risk=ActionRisk.medium,
    )
    return [authority_section, gap_section, safety_section]


def _ahrefs_decision_queue(
    *,
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    competitor_read_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[AhrefsDecisionItem]:
    decisions: list[AhrefsDecisionItem] = []
    gap_records = _ahrefs_gap_records(gap_facts)
    if authority_facts:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_review_authority_context",
                decision_type="review_authority_context",
                status="ready",
                decision_type_label=_ahrefs_decision_type_label("review_authority_context"),
                title="Użyj Ahrefs tylko jako kontekstu autorytetu",
                summary=(
                    f"{_authority_summary(authority_facts)}. "
                    f"{_competitor_read_summary(competitor_read_facts)}"
                ),
                rationale=(
                    "WILQ ma metryki autorytetu Ahrefs z dowodami, więc może dodać kontekst "
                    "autorytetu do sprawdzenia SEO i treści. To nadal nie jest analiza luk."
                ),
                next_step=(
                    "Połącz ten kontekst z rekordami luk Ahrefs, widokiem Treści i GSC. "
                    "Sprawdzenie luk nadal wymaga kontroli GSC i WordPress i nie jest obietnicą "
                    "wzrostu."
                    if gap_records
                    else (
                        "Połącz ten kontekst z widokiem Treści i GSC. Nie twierdź, że "
                        "Ahrefs wykrył lukę treści/linków, dopóki nie ma rekordów luk."
                    )
                ),
                priority=25,
                metric_tiles=_authority_tiles(
                    authority_facts,
                    gap_facts,
                    competitor_read_facts,
                ),
                allowed_evidence=[
                    "domain_rating",
                    "ahrefs_rank",
                    "authority_summary",
                    *(fact.name for fact in competitor_read_facts),
                ],
                allowed_evidence_labels=_labels_for_values(
                    [
                        "domain_rating",
                        "ahrefs_rank",
                        "authority_summary",
                        *(fact.name for fact in competitor_read_facts),
                    ],
                    _ahrefs_metric_fact_label,
                ),
                missing_read_contracts=_missing_gap_contracts(gap_facts),
                missing_read_contract_labels=_labels_for_values(
                    _missing_gap_contracts(gap_facts),
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_evidence_ids_for_facts_or_refresh(
                    [*authority_facts, *competitor_read_facts],
                    latest_refresh,
                ),
                metric_facts=[*authority_facts, *competitor_read_facts],
                metric_fact_labels=_metric_fact_labels_for_facts(
                    [*authority_facts, *competitor_read_facts]
                ),
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
                decision_type_label=_ahrefs_decision_type_label("run_authority_read"),
                title="Uruchom odczyt autorytetu Ahrefs przed sprawdzeniem luk SEO",
                summary=_missing_authority_summary(connector_missing, latest_refresh),
                rationale=(
                    "Bez świeżych danych autorytetu Ahrefs WILQ nie powinien nawet używać "
                    "Ahrefs jako kontekstu SEO."
                ),
                next_step=(
                    "Uzupełnij dostęp Ahrefs i wykonaj odczyt danych."
                    if connector_missing
                    else "Wykonaj odczyt danych Ahrefs, potem wróć do /ahrefs."
                ),
                priority=10,
                metric_tiles={"dane Ahrefs": 0, "brakujące dane": len(AHREFS_GAP_READ_CONTRACTS)},
                allowed_evidence=[],
                missing_read_contracts=["domain_rating", *AHREFS_GAP_READ_CONTRACTS],
                missing_read_contract_labels=_labels_for_values(
                    ["domain_rating", *AHREFS_GAP_READ_CONTRACTS],
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_refresh_or_connector_evidence_ids(latest_refresh),
                action_ids=[],
                blocked_claims=AHREFS_GAP_BLOCKED_CLAIMS,
                risk=ActionRisk.medium,
            )
        )

    missing_gap_contracts = _missing_gap_contracts(gap_facts)
    if gap_records:
        allowed_evidence = _allowed_gap_evidence(authority_facts, gap_facts)
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_review_gap_records",
                decision_type="review_gap_records",
                status="ready",
                decision_type_label=_ahrefs_decision_type_label("review_gap_records"),
                title="Przejrzyj rekordy luk Ahrefs",
                summary=(
                    f"WILQ ma {_ahrefs_gap_record_count_label(len(gap_records))} z Ahrefs. "
                    f"Brakujące dane: {_missing_gap_contracts_summary(missing_gap_contracts)}."
                ),
                rationale=(
                    "To są konkretne rekordy z dowodami Ahrefs, więc mogą wejść do "
                    "sprawdzenia SEO i treści. Nadal wymagają połączenia z GSC i spisem "
                    "treści WordPress przed decyzją publikacyjną."
                ),
                next_step=(
                    "Połącz rekordy z widokiem Treści, sprawdź duplikaty WordPress "
                    "i przygotuj zachowanie, odświeżenie, scalenie, utworzenie albo blokadę "
                    "zamiast obiecywać wzrost."
                ),
                priority=18,
                metric_tiles=_gap_record_tiles(gap_records, missing_gap_contracts),
                allowed_evidence=allowed_evidence,
                allowed_evidence_labels=_labels_for_values(
                    allowed_evidence,
                    _ahrefs_metric_fact_label,
                ),
                missing_read_contracts=missing_gap_contracts,
                missing_read_contract_labels=_labels_for_values(
                    missing_gap_contracts,
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_unique(
                    evidence_id for record in gap_records for evidence_id in record.evidence_ids
                ),
                metric_facts=[fact for record in gap_records for fact in record.metric_facts][:12],
                metric_fact_labels=_metric_fact_labels_for_facts(
                    [fact for record in gap_records for fact in record.metric_facts]
                ),
                action_ids=[],
                blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
                risk=ActionRisk.medium if missing_gap_contracts else ActionRisk.low,
            )
        )
    if missing_gap_contracts:
        decisions.append(
            AhrefsDecisionItem(
                id="ahrefs_block_gap_claims_without_records",
                decision_type="block_gap_claims",
                status="blocked",
                decision_type_label=_ahrefs_decision_type_label("block_gap_claims"),
                title="Nie wskazuj luk konkurencji bez rekordów Ahrefs",
                summary=(
                    "Brakuje danych Ahrefs dla luk treści, luk linków zwrotnych, "
                    "organicznych słów kluczowych i najlepszych stron konkurencji."
                ),
                rationale=(
                    "DR/rank to metryki domeny. Nie mówią, które treści, linki albo "
                    "konkurenci tworzą realną przestrzeń do działania."
                ),
                next_step=(
                    "Dodaj odczyty danych: strony konkurencji, rekordy luk treści, "
                    "rekordy luk linków zwrotnych, organiczne słowa dla URL i najlepsze "
                    "strony konkurencji."
                ),
                priority=12,
                metric_tiles={
                    "brakujące dane": len(missing_gap_contracts),
                    "nie wolno twierdzić": len(
                        _blocked_claims_for_missing_contracts(missing_gap_contracts)
                    ),
                },
                allowed_evidence=["domain_rating", "ahrefs_rank"] if authority_facts else [],
                allowed_evidence_labels=_labels_for_values(
                    ["domain_rating", "ahrefs_rank"] if authority_facts else [],
                    _ahrefs_metric_fact_label,
                ),
                missing_read_contracts=missing_gap_contracts,
                missing_read_contract_labels=_labels_for_values(
                    missing_gap_contracts,
                    _missing_gap_contract_label,
                ),
                source_connectors=[AHREFS_CONNECTOR_ID],
                evidence_ids=_evidence_ids_for_facts_or_refresh(authority_facts, latest_refresh),
                action_ids=[],
                blocked_claims=_blocked_claims_for_missing_contracts(missing_gap_contracts),
                risk=ActionRisk.medium,
            )
        )
    return decisions


def _ahrefs_decisions_with_lineage(
    decisions: list[AhrefsDecisionItem],
) -> list[AhrefsDecisionItem]:
    return [
        _label_ahrefs_decision(decision).model_copy(
            update={
                "knowledge_card_ids": _unique(
                    [*decision.knowledge_card_ids, *AHREFS_KNOWLEDGE_CARD_IDS]
                ),
                "expert_rule_ids": _unique([*decision.expert_rule_ids, *AHREFS_EXPERT_RULE_IDS]),
            }
        )
        for decision in decisions
    ]


def _authority_summary(authority_facts: list[MetricFact]) -> str:
    domain_rating = _fact_value(authority_facts, "domain_rating")
    ahrefs_rank = _fact_value(authority_facts, "ahrefs_rank")
    parts = []
    if domain_rating is not None:
        parts.append(f"ocena domeny Ahrefs: {_ahrefs_metric_value_label(domain_rating)}")
    if ahrefs_rank is not None:
        parts.append(f"pozycja w rankingu Ahrefs: {_ahrefs_metric_value_label(ahrefs_rank)}")
    return ", ".join(parts) if parts else "brak faktów autorytetu"


def _competitor_read_summary(competitor_read_facts: list[MetricFact]) -> str:
    if not competitor_read_facts:
        return "Odczyt konkurencji organicznej nie ma jeszcze statusu."
    status = _fact_value(competitor_read_facts, "organic_competitor_read_status")
    rows = _fact_value(competitor_read_facts, "organic_competitor_rows")
    country = _fact_value(competitor_read_facts, "organic_competitor_country")
    mode = _fact_value(competitor_read_facts, "organic_competitor_mode")
    return (
        "Odczyt konkurencji organicznej: "
        f"{_ahrefs_read_status_label(status)}, "
        f"liczba konkurentów: {_ahrefs_metric_value_label(rows if rows is not None else 0)}, "
        f"kraj: {_ahrefs_country_label(country)}, "
        f"zakres: {_ahrefs_read_mode_label(mode)}."
    )


def _ahrefs_metric_value_label(value: int | float | str) -> str:
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}".replace(",", " ")
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return str(value)


def _missing_authority_summary(
    connector_missing: list[str],
    latest_refresh: ConnectorRefreshRun | None,
) -> str:
    if connector_missing:
        return f"Ahrefs ma braki dostępu: {len(connector_missing)}."
    if latest_refresh and latest_refresh.status != ConnectorRefreshStatus.completed:
        return (
            "Ostatni odczyt Ahrefs zakończył się statusem "
            f"{_ahrefs_refresh_status_label(latest_refresh.status)}."
        )
    return "WILQ nie ma świeżych danych autorytetu Ahrefs."


def _authority_tiles(
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
    competitor_read_facts: list[MetricFact],
) -> dict[str, int | float | str]:
    return _clean_metric_tiles(
        {
            "ocena domeny Ahrefs": _fact_value(authority_facts, "domain_rating"),
            "pozycja w rankingu Ahrefs": _fact_value(authority_facts, "ahrefs_rank"),
            "konkurenci organiczni": _fact_value(
                competitor_read_facts,
                "organic_competitor_rows",
            ),
            "odczyt konkurencji": _ahrefs_read_status_label(
                _fact_value(competitor_read_facts, "organic_competitor_read_status")
            )
            if competitor_read_facts
            else None,
            "zakres konkurencji": _ahrefs_read_mode_label(
                _fact_value(competitor_read_facts, "organic_competitor_mode")
            )
            if competitor_read_facts
            else None,
            "luki Ahrefs": len(gap_facts),
            "brakujące dane": len(_missing_gap_contracts(gap_facts)),
        }
    )


def _gap_record_tiles(
    gap_records: list[AhrefsGapRecord],
    missing_contracts: list[str],
) -> dict[str, int | float | str]:
    counts_by_type: dict[str, int] = {}
    for record in gap_records:
        counts_by_type[record.gap_type] = counts_by_type.get(record.gap_type, 0) + 1
    return _clean_metric_tiles(
        {
            "rekordy luk": len(gap_records),
            "luki treści": counts_by_type.get("content_gap"),
            "luki linków zwrotnych": counts_by_type.get("backlink_gap"),
            "strony konkurencji": counts_by_type.get("competitor_page"),
            "słowa organiczne": counts_by_type.get("organic_keyword_gap"),
            "najlepsze strony": counts_by_type.get("top_page_gap"),
            "brakujące dane": len(missing_contracts),
        }
    )


def _missing_gap_contracts(gap_facts: list[MetricFact]) -> list[str]:
    if not gap_facts:
        return AHREFS_GAP_READ_CONTRACTS.copy()
    # Future-proof for detailed records: each gap contract is considered present only
    # after a matching metric fact exists. Current domain-rating reads intentionally
    # leave all gap contracts missing.
    fact_names = {fact.name for fact in gap_facts if _is_record_level_gap_fact(fact)}
    present_by_fact = {
        "ahrefs_competitor_pages": {"ahrefs_competitor_page_count"},
        "ahrefs_content_gap_records": {"ahrefs_content_gap_count"},
        "ahrefs_backlink_gap_records": {
            "ahrefs_backlink_gap_count",
            "ahrefs_referring_domain_gap_count",
        },
        "ahrefs_organic_keywords_by_url": {"ahrefs_organic_keyword_gap_count"},
        "ahrefs_top_pages_by_competitor": {"ahrefs_top_page_gap_count"},
    }
    missing_contracts = [
        contract
        for contract in AHREFS_GAP_READ_CONTRACTS
        if not fact_names.intersection(present_by_fact[contract])
    ]
    if not _ahrefs_gap_records(gap_facts) and "ahrefs_content_gap_records" not in missing_contracts:
        missing_contracts.append("ahrefs_content_gap_records")
    return missing_contracts


def _available_gap_contracts(missing_contracts: list[str]) -> list[str]:
    return [contract for contract in AHREFS_GAP_READ_CONTRACTS if contract not in missing_contracts]


def _allowed_gap_evidence(
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[str]:
    return _unique(
        [
            *(fact.name for fact in authority_facts),
            *(fact.name for fact in gap_facts),
        ]
    )


def _blocked_claims_for_missing_contracts(missing_contracts: list[str]) -> list[str]:
    claims_by_contract = {
        "ahrefs_competitor_pages": "luka względem konkurencji",
        "ahrefs_content_gap_records": "luka treści",
        "ahrefs_backlink_gap_records": "luka linków",
        "ahrefs_organic_keywords_by_url": "szansa na wzrost pozycji",
        "ahrefs_top_pages_by_competitor": "wzrost ruchu",
    }
    claims = [
        claim for contract, claim in claims_by_contract.items() if contract in missing_contracts
    ]
    claims.extend(AHREFS_GAP_IMPACT_BLOCKED_CLAIMS)
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
