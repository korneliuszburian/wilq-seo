"""Ahrefs domain authority and competitor-read diagnostics."""
from __future__ import annotations

from wilq.schemas import (
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)

from .gap_records import (
    _missing_gap_contracts,
)
from .labels import (
    _ahrefs_country_label,
    _ahrefs_metric_value_label,
    _ahrefs_read_mode_label,
    _ahrefs_read_status_label,
    _ahrefs_refresh_status_label,
)
from .shared import (
    _clean_metric_tiles,
    _fact_value,
)


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

