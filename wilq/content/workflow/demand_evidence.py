from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.drafts.package import ContentDraftPackage
from wilq.schemas import ContentFreshnessAssessment, MetricFact

ContentDemandSourceKind = Literal["gsc_query", "ads_search_term", "keyword_planner"]


class ContentSearchDemandRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: ContentDemandSourceKind
    source_connector: Literal["google_search_console", "google_ads"]
    term: str = Field(min_length=1)
    page: str = Field(min_length=1)
    service_card_id: str | None = None
    section_headings: list[str] = Field(min_length=1)
    period: str = Field(min_length=1)
    freshness: Literal["fresh", "stale", "missing", "blocked"]
    collected_at: datetime | None = None
    evidence_ids: list[str] = Field(min_length=1)
    impressions: int | None = None
    clicks: int | None = None
    ctr: float | None = None
    average_position: float | None = None
    average_monthly_searches: int | None = None


class ContentSearchDemandEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "missing"]
    gsc_query_rows: list[ContentSearchDemandRow] = Field(default_factory=list)
    ads_term_rows: list[ContentSearchDemandRow] = Field(default_factory=list)
    keyword_planner_rows: list[ContentSearchDemandRow] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    optional_ads_status: Literal["exact_rows_available", "not_exactly_mapped"]
    safe_next_step: str


def build_content_search_demand_evidence(
    *,
    metric_facts: list[MetricFact],
    source_page: str | None,
    final_canonical_url: str,
    service_card_id: str | None,
    draft: ContentDraftPackage,
    freshness: ContentFreshnessAssessment,
) -> ContentSearchDemandEvidence:
    allowed_pages = {page for page in (source_page, final_canonical_url) if page}
    gsc_groups = _group_facts(
        fact
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and fact.dimensions.get("page") in allowed_pages
        and fact.dimensions.get("query")
        and content_query_is_planning_signal(fact.dimensions["query"])
    )
    gsc_rows = [
        row
        for key, facts in gsc_groups.items()
        if (
            row := _gsc_row(
                term=key[1],
                page=key[0],
                facts=facts,
                service_card_id=service_card_id,
                draft=draft,
                freshness=freshness,
            )
        )
        is not None
    ]
    gsc_rows.sort(key=lambda row: (row.impressions or 0, row.clicks or 0), reverse=True)

    gsc_by_term = {row.term: row for row in gsc_rows}
    ads_groups = _group_facts(
        fact
        for fact in metric_facts
        if fact.source_connector == "google_ads"
        and _strict_ads_scope_matches(
            fact,
            allowed_pages=allowed_pages,
            service_card_id=service_card_id,
        )
    )
    ads_rows: list[ContentSearchDemandRow] = []
    planner_rows: list[ContentSearchDemandRow] = []
    for (_, term), facts in ads_groups.items():
        gsc_row = gsc_by_term.get(term)
        if gsc_row is None:
            continue
        source_kind: Literal["ads_search_term", "keyword_planner"] = (
            "keyword_planner"
            if any(fact.dimensions.get("keyword_idea_text") == term for fact in facts)
            else "ads_search_term"
        )
        row = _ads_row(
            source_kind=source_kind,
            term=term,
            gsc_row=gsc_row,
            facts=facts,
            service_card_id=service_card_id,
            freshness=freshness,
        )
        (planner_rows if source_kind == "keyword_planner" else ads_rows).append(row)

    all_rows = [*gsc_rows, *ads_rows, *planner_rows]
    return ContentSearchDemandEvidence(
        status="available" if gsc_rows else "missing",
        gsc_query_rows=gsc_rows,
        ads_term_rows=ads_rows,
        keyword_planner_rows=planner_rows,
        source_connectors=list(dict.fromkeys(row.source_connector for row in all_rows)),
        evidence_ids=list(
            dict.fromkeys(evidence_id for row in all_rows for evidence_id in row.evidence_ids)
        ),
        optional_ads_status=(
            "exact_rows_available" if ads_rows or planner_rows else "not_exactly_mapped"
        ),
        safe_next_step=(
            "Sprawdź zapytania GSC przypisane do strony i sekcji; dane Ads są "
            "opcjonalne i pojawią się dopiero po ścisłym mapowaniu termu, strony i usługi."
            if gsc_rows
            else "Odśwież GSC albo sprawdź exact page mapping; nie planuj słów kluczowych z opisu."
        ),
    )


def _group_facts(facts: Iterable[MetricFact]) -> dict[tuple[str, str], list[MetricFact]]:
    grouped: dict[tuple[str, str], list[MetricFact]] = {}
    for fact in facts:
        page = _fact_page(fact)
        term = (
            fact.dimensions.get("query")
            or fact.dimensions.get("search_term")
            or fact.dimensions.get("keyword_idea_text")
        )
        if page and term:
            grouped.setdefault((page, term), []).append(fact)
    return grouped


def _gsc_row(
    *,
    term: str,
    page: str,
    facts: list[MetricFact],
    service_card_id: str | None,
    draft: ContentDraftPackage,
    freshness: ContentFreshnessAssessment,
) -> ContentSearchDemandRow | None:
    evidence_ids = list(dict.fromkeys(fact.evidence_id for fact in facts))
    section_headings = [
        section.heading
        for section in draft.sections
        if set(section.evidence_ids).intersection(evidence_ids)
    ]
    if not section_headings:
        return None
    return ContentSearchDemandRow(
        source_kind="gsc_query",
        source_connector="google_search_console",
        term=term,
        page=page,
        service_card_id=service_card_id,
        section_headings=section_headings,
        period=facts[0].period,
        freshness=freshness.state,
        collected_at=max(
            (fact.collected_at for fact in facts if fact.collected_at is not None),
            default=None,
        ),
        evidence_ids=evidence_ids,
        impressions=_int_metric(facts, "impressions"),
        clicks=_int_metric(facts, "clicks"),
        ctr=_float_metric(facts, "ctr"),
        average_position=_float_metric(facts, "average_position"),
    )


def _ads_row(
    *,
    source_kind: Literal["ads_search_term", "keyword_planner"],
    term: str,
    gsc_row: ContentSearchDemandRow,
    facts: list[MetricFact],
    service_card_id: str | None,
    freshness: ContentFreshnessAssessment,
) -> ContentSearchDemandRow:
    return ContentSearchDemandRow(
        source_kind=source_kind,
        source_connector="google_ads",
        term=term,
        page=gsc_row.page,
        service_card_id=service_card_id,
        section_headings=gsc_row.section_headings,
        period=facts[0].period,
        freshness=freshness.state,
        collected_at=max(
            (fact.collected_at for fact in facts if fact.collected_at is not None),
            default=None,
        ),
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in facts)),
        impressions=_int_metric(facts, "search_term_impressions"),
        clicks=_int_metric(facts, "search_term_clicks"),
        average_monthly_searches=_int_metric(
            facts, "keyword_planner_avg_monthly_searches"
        ),
    )


def _strict_ads_scope_matches(
    fact: MetricFact,
    *,
    allowed_pages: set[str],
    service_card_id: str | None,
) -> bool:
    return bool(
        service_card_id
        and fact.dimensions.get("service_card_id") == service_card_id
        and _fact_page(fact) in allowed_pages
        and (
            fact.dimensions.get("search_term")
            or fact.dimensions.get("keyword_idea_text")
        )
    )


def _fact_page(fact: MetricFact) -> str | None:
    return (
        fact.dimensions.get("page")
        or fact.dimensions.get("landing_page")
        or fact.dimensions.get("final_url")
    )


def _int_metric(facts: list[MetricFact], name: str) -> int | None:
    value = _metric(facts, name)
    return int(value) if isinstance(value, int | float) else None


def _float_metric(facts: list[MetricFact], name: str) -> float | None:
    value = _metric(facts, name)
    return float(value) if isinstance(value, int | float) else None


def _metric(facts: list[MetricFact], name: str) -> float | int | str | None:
    return next((fact.value for fact in facts if fact.name == name), None)


def content_query_is_planning_signal(term: str) -> bool:
    normalized = term.strip().casefold()
    if not normalized:
        return False
    return len(term) <= 160 and normalized.count("-site:") < 2 and not normalized.startswith(
        "site:"
    )
