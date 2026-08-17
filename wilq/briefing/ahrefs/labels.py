"""Polish Ahrefs operator labels."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from wilq.content.operator_copy import unique
from wilq.schemas import (
    AhrefsDecisionItem,
    AhrefsDiagnosticSection,
    AhrefsGapReadContract,
    AhrefsOperatorSummary,
    ConnectorRefreshRun,
    MetricFact,
    connector_refresh_run_status_label,
)

from .shared import (
    AhrefsBudgetStageStatus,
    AhrefsGapType,
)

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
    "ahrefs_gap_coverage": "zakres próby i limit porównania dla każdej luki",
    "domain_rating": "ocena domeny Ahrefs",
}

AHREFS_REVIEW_GATE_LABELS = {
    "ahrefs_gap_records_required": "wymagane konkretne rekordy luk Ahrefs",
    "content_workflow_review_required": "sprawdzenie w workflow treści",
    "human_strategy_review": "sprawdzenie strategii przez człowieka",
}


def _ahrefs_budget_stage_status_label(status: AhrefsBudgetStageStatus) -> str:
    return {
        "completed": "zakończony",
        "failed": "błąd odczytu",
        "skipped": "pominięty",
        "not_run": "nieuruchomiony",
    }[status]


def _ahrefs_cross_check_status_label(status: str) -> str:
    labels = {
        "api_backed": "sprawdzenie GSC i WordPress ma dopasowania z API",
        "manual_required": "sprawdzenie GSC i WordPress wymaga ręcznej oceny",
        "missing": "brak rekordów Ahrefs do cross-checku",
    }
    return labels.get(status, "cross-check do sprawdzenia")


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
    return unique(labeler(value) for value in values)


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


def _ahrefs_metric_value_label(value: int | float | str) -> str:
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}".replace(",", " ")
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return str(value)
