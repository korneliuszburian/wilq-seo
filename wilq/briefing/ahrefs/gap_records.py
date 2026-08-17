"""Ahrefs gap contracts, records, coverage, and cross-checks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast

from wilq.content.operator_copy import unique
from wilq.content.planning.ahrefs import ahrefs_cross_source_candidate_rows
from wilq.content.planning.ahrefs_overlap import ahrefs_gap_mapping_key
from wilq.schemas import (
    ActionRisk,
    AhrefsGapReadContract,
    AhrefsGapRecord,
    ConnectorRefreshRun,
    ContentAhrefsCandidateRow,
    MetricFact,
)

from .keywords import (
    _gap_record_relevance_score,
    _slug,
)
from .labels import (
    _ahrefs_count_word,
    _ahrefs_cross_check_status_label,
    _ahrefs_gap_record_count_label,
    _ahrefs_metric_fact_label,
    _ahrefs_read_contract_label,
    _ahrefs_review_gate_label,
    _gap_fact_value_label,
    _gap_type_label,
    _labels_for_values,
    _metric_fact_labels_for_facts,
    _missing_gap_contract_label,
)
from .shared import (
    AHREFS_CONNECTOR_ID,
    AHREFS_CONTENT_REFRESH_ACTION_ID,
    AhrefsGapType,
    _ahrefs_snapshot_date,
    _clean_metric_tiles,
    _evidence_ids_for_facts_or_refresh,
)

AHREFS_GAP_READ_CONTRACTS = [
    "ahrefs_competitor_pages",
    "ahrefs_content_gap_records",
    "ahrefs_backlink_gap_records",
    "ahrefs_organic_keywords_by_url",
    "ahrefs_top_pages_by_competitor",
    "ahrefs_gap_coverage",
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

AHREFS_GAP_TYPES = {
    "competitor_page",
    "content_gap",
    "backlink_gap",
    "organic_keyword_gap",
    "top_page_gap",
}

AHREFS_REVIEWABLE_GAP_RECORD_LIMIT = 8


@dataclass(frozen=True)
class AhrefsGapCrossCheck:
    candidates: list[ContentAhrefsCandidateRow]
    mapping_candidates: list[ContentAhrefsCandidateRow]
    status: Literal["api_backed", "manual_required", "missing"]
    gsc_match_count: int
    wordpress_match_count: int
    source_connectors: list[str]
    evidence_ids: list[str]


def _ahrefs_gap_read_contract(
    *,
    latest_refresh: ConnectorRefreshRun | None,
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
    cross_check_facts: list[MetricFact],
) -> AhrefsGapReadContract:
    missing_contracts = _missing_gap_contracts(gap_facts)
    snapshot_date = _ahrefs_snapshot_date(latest_refresh)
    gap_records = _ahrefs_gap_records(gap_facts, snapshot_date=snapshot_date)
    cross_check = _build_ahrefs_gap_cross_check(
        gap_facts=gap_facts,
        cross_check_facts=cross_check_facts,
        gap_records=gap_records,
    )
    gap_records = _apply_exact_wordpress_cross_checks(
        gap_records,
        cross_check.mapping_candidates,
    )
    blocked_claims = _blocked_claims_for_missing_contracts(missing_contracts)
    evidence_ids = unique(
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
        source_connectors=unique([AHREFS_CONNECTOR_ID, *cross_check.source_connectors]),
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        gap_records=gap_records,
        gap_record_count=len(gap_records),
        coverage_summary=_gap_records_coverage_summary(gap_records),
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


def _apply_exact_wordpress_cross_checks(
    records: list[AhrefsGapRecord],
    candidates: list[ContentAhrefsCandidateRow],
) -> list[AhrefsGapRecord]:
    """Promote only an exact typed WordPress URL match, never phrase overlap."""
    for record in records:
        if not record.mapping_key:
            continue
        matches = [
            candidate
            for candidate in candidates
            if candidate.mapping_key == record.mapping_key
            and candidate.wordpress_cross_check.strength == "exact"
        ]
        urls = {
            url
            for candidate in matches
            for url in candidate.wordpress_overlap_urls
            if url.startswith("https://")
        }
        if len(urls) != 1:
            continue
        record.referenced_public_url = next(iter(urls))
        record.mapping_status = "exact"
        record.evidence_ids = list(
            dict.fromkeys(
                [
                    *record.evidence_ids,
                    *(
                        evidence_id
                        for candidate in matches
                        for evidence_id in candidate.wordpress_cross_check.evidence_ids
                    ),
                ]
            )
        )
    return records


def _build_ahrefs_gap_cross_check(
    *,
    gap_facts: list[MetricFact],
    cross_check_facts: list[MetricFact],
    gap_records: list[AhrefsGapRecord],
) -> AhrefsGapCrossCheck:
    candidates = ahrefs_cross_source_candidate_rows(gap_facts, cross_check_facts, limit=6)
    mapping_candidates = ahrefs_cross_source_candidate_rows(
        gap_facts,
        cross_check_facts,
        limit=None,
    )
    gsc_match_count = sum(
        candidate.gsc_cross_check.strength == "exact" for candidate in mapping_candidates
    )
    wordpress_match_count = sum(
        candidate.wordpress_cross_check.strength == "exact" for candidate in mapping_candidates
    )
    source_connectors, evidence_ids = _ahrefs_cross_check_trace(mapping_candidates)
    return AhrefsGapCrossCheck(
        candidates=candidates,
        mapping_candidates=mapping_candidates,
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
        unique(connector for check in exact_checks for connector in check.source_connectors),
        unique(evidence_id for check in exact_checks for evidence_id in check.evidence_ids),
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
        return "Sprawdź ręcznie GSC i spis WordPress dla tematów Ahrefs przed tworzeniem briefu."
    return "Najpierw odczytaj rekordy luk Ahrefs, potem sprawdź GSC i WordPress."


def _ahrefs_gap_records(
    gap_facts: list[MetricFact],
    *,
    snapshot_date: str | None = None,
) -> list[AhrefsGapRecord]:
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
            snapshot_date=snapshot_date,
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
    snapshot_date: str | None,
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
        mapping_key=ahrefs_gap_mapping_key(
            gap_type=gap_type,
            source_url=source_url,
            competitor_domain=competitor_domain,
            keyword=keyword,
        ),
        snapshot_date=snapshot_date,
        mapping_status=_gap_mapping_status(referenced_public_url, facts),
        derived_method=_gap_derived_method(facts),
        coverage_summary=_gap_coverage_summary(facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        metric_fact_labels=_metric_fact_labels_for_facts(facts),
        evidence_ids=unique(fact.evidence_id for fact in facts),
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
    derived = next(
        (fact.dimensions.get("gap_method") for fact in facts if fact.dimensions.get("gap_method")),
        None,
    )
    return (
        derived
        if isinstance(derived, str)
        else "różnica zbioru słów konkurencji i słów domeny docelowej"
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
    page_sample = next(
        (
            fact.dimensions.get("target_page_sample_size")
            for fact in facts
            if fact.dimensions.get("target_page_sample_size")
        ),
        None,
    )
    page_limit = next(
        (
            fact.dimensions.get("target_page_limit")
            for fact in facts
            if fact.dimensions.get("target_page_limit")
        ),
        None,
    )
    if page_sample and page_limit:
        return f"próbka stron konkurencji: {page_sample}; limit porównania: {page_limit}"
    refdomain_sample = next(
        (
            fact.dimensions.get("target_refdomain_sample_size")
            for fact in facts
            if fact.dimensions.get("target_refdomain_sample_size")
        ),
        None,
    )
    refdomain_limit = next(
        (
            fact.dimensions.get("target_refdomain_limit")
            for fact in facts
            if fact.dimensions.get("target_refdomain_limit")
        ),
        None,
    )
    if refdomain_sample and refdomain_limit:
        return f"próbka domen odsyłających: {refdomain_sample}; limit porównania: {refdomain_limit}"
    competitor_sample = next(
        (
            fact.dimensions.get("target_competitor_sample_size")
            for fact in facts
            if fact.dimensions.get("target_competitor_sample_size")
        ),
        None,
    )
    competitor_limit = next(
        (
            fact.dimensions.get("target_competitor_limit")
            for fact in facts
            if fact.dimensions.get("target_competitor_limit")
        ),
        None,
    )
    if competitor_sample and competitor_limit:
        return f"próbka konkurentów: {competitor_sample}; limit porównania: {competitor_limit}"
    return "zakres próby nie został podany w rekordzie"


def _gap_records_coverage_summary(records: list[AhrefsGapRecord]) -> str:
    summaries = list(
        dict.fromkeys(record.coverage_summary for record in records if record.coverage_summary)
    )
    if not summaries:
        return "Brak potwierdzonego zakresu próby."
    if len(summaries) == 1:
        return summaries[0]
    return "Zakres rekordów: " + "; ".join(summaries[:3])


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


def _missing_gap_contracts_summary(missing_contracts: list[str]) -> str:
    if not missing_contracts:
        return "dane kompletne"
    return ", ".join(_missing_gap_contract_label(contract) for contract in missing_contracts)


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
        if contract != "ahrefs_gap_coverage"
        if not fact_names.intersection(present_by_fact[contract])
    ]
    gap_records = _ahrefs_gap_records(gap_facts)
    if not gap_records and "ahrefs_content_gap_records" not in missing_contracts:
        missing_contracts.append("ahrefs_content_gap_records")
    if _gap_coverage_is_expected(gap_facts) and not all(
        _gap_record_has_complete_coverage(record) for record in gap_records
    ):
        missing_contracts.append("ahrefs_gap_coverage")
    return missing_contracts


def _gap_coverage_is_expected(gap_facts: list[MetricFact]) -> bool:
    """Only enforce comparison scope when the source declares that scope."""
    return any(
        fact.dimensions.get("target_domain")
        or fact.dimensions.get("target_keyword_sample_size")
        or fact.dimensions.get("target_keyword_limit")
        or fact.dimensions.get("target_page_sample_size")
        or fact.dimensions.get("target_page_limit")
        or fact.dimensions.get("target_refdomain_sample_size")
        or fact.dimensions.get("target_refdomain_limit")
        or fact.dimensions.get("target_competitor_sample_size")
        or fact.dimensions.get("target_competitor_limit")
        for fact in gap_facts
    )


def _gap_record_has_complete_coverage(record: AhrefsGapRecord) -> bool:
    return bool(record.coverage_summary) and (
        record.coverage_summary != "zakres próby nie został podany w rekordzie"
    )


def _available_gap_contracts(missing_contracts: list[str]) -> list[str]:
    return [contract for contract in AHREFS_GAP_READ_CONTRACTS if contract not in missing_contracts]


def _allowed_gap_evidence(
    authority_facts: list[MetricFact],
    gap_facts: list[MetricFact],
) -> list[str]:
    return unique(
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
        "ahrefs_gap_coverage": "kompletność zakresu porównania",
    }
    claims = [
        claim for contract, claim in claims_by_contract.items() if contract in missing_contracts
    ]
    claims.extend(AHREFS_GAP_IMPACT_BLOCKED_CLAIMS)
    return unique(claims)
