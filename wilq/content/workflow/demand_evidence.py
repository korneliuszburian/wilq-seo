from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.connectors.google_ads.ad_landing_pages import (
    ADS_DEMAND_PERIOD,
    ADS_LANDING_ACTUAL_CLICKED,
    ADS_LANDING_IDENTITY,
    ADS_LANDING_MAPPING_STATUS,
    ADS_LANDING_RESOLVED,
    ADS_SEARCH_TERM_PAYLOAD_STATUS,
)
from wilq.content.canonical.landing_identity import (
    LandingMatchTier,
    LandingPageCandidate,
    build_landing_page_identity,
    match_landing_page,
)
from wilq.content.canonical.redacted_landing import build_redacted_landing_reference
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.workflow.query_section_intent import assign_query_to_sections
from wilq.schemas import ContentFreshnessAssessment, MetricFact

ContentDemandSourceKind = Literal["gsc_query", "ads_search_term", "keyword_planner"]
ContentAcceptedLandingMatchTier = Literal["exact", "tracking_only", "host_alias"]
ContentOptionalAdsStatus = Literal[
    "exact_rows_available", "not_exactly_mapped", "stale", "blocked"
]
CONTENT_ADS_TERM_METRIC_NAMES = {
    "search_term_clicks",
    "search_term_impressions",
    "search_term_cost_micros",
    "search_term_conversions",
    "search_term_conversion_value",
}


class ContentSearchDemandRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: ContentDemandSourceKind
    source_connector: Literal["google_search_console", "google_ads"]
    term: str = Field(min_length=1)
    page: str = Field(min_length=1)
    landing_match_tiers: list[ContentAcceptedLandingMatchTier] = Field(
        default_factory=list
    )
    service_card_id: str | None = None
    alignment_basis: Literal[
        "legacy_unspecified",
        "gsc_exact_page",
        "direct_page_service_scope",
        "same_window_search_term_landing",
    ] = "legacy_unspecified"
    review_required: bool = True
    section_headings: list[str] = Field(default_factory=list)
    section_mapping_status: Literal[
        "intent_relevance", "lexical_relevance", "page_only"
    ]
    period: str = Field(min_length=1)
    freshness: Literal["fresh", "stale", "missing", "blocked"]
    collected_at: datetime | None = None
    evidence_ids: list[str] = Field(min_length=1)
    impressions: int | None = None
    clicks: int | None = None
    ctr: float | None = None
    average_position: float | None = None
    average_monthly_searches: int | None = None
    cost_micros: int | None = None
    conversions: float | None = None
    conversion_value: float | None = None


class ContentSearchDemandEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "missing"]
    gsc_query_rows: list[ContentSearchDemandRow] = Field(default_factory=list)
    ads_term_rows: list[ContentSearchDemandRow] = Field(default_factory=list)
    keyword_planner_rows: list[ContentSearchDemandRow] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    optional_ads_status: ContentOptionalAdsStatus
    optional_ads_evidence_ids: list[str] = Field(default_factory=list)
    optional_ads_blockers: list[str] = Field(default_factory=list)
    safe_next_step: str

    @model_validator(mode="after")
    def validate_optional_ads_contract(self) -> ContentSearchDemandEvidence:
        rows = [*self.ads_term_rows, *self.keyword_planner_rows]
        if self.optional_ads_status == "blocked":
            if not self.optional_ads_evidence_ids or not self.optional_ads_blockers:
                raise ValueError("blocked Ads demand requires evidence and blockers")
            if rows:
                raise ValueError("blocked Ads demand cannot expose usable rows")
        elif self.optional_ads_blockers:
            raise ValueError("non-blocked Ads demand cannot expose blockers")
        if self.optional_ads_status == "exact_rows_available" and (
            not rows or not self.optional_ads_evidence_ids
        ):
            raise ValueError("exact Ads demand requires rows and evidence")
        if self.optional_ads_status == "stale" and (
            not self.optional_ads_evidence_ids
            or any(row.freshness != "stale" for row in rows)
        ):
            raise ValueError("stale Ads demand requires evidence and only stale rows")
        if self.optional_ads_status == "not_exactly_mapped" and rows:
            raise ValueError("unmapped Ads demand cannot expose exact rows")
        return self


def build_content_search_demand_evidence(
    *,
    metric_facts: list[MetricFact],
    source_page: str | None,
    final_canonical_url: str,
    service_card_id: str | None,
    draft: ContentDraftPackage,
    freshness: ContentFreshnessAssessment,
) -> ContentSearchDemandEvidence:
    allowed_pages = [page for page in (source_page, final_canonical_url) if page]
    gsc_rows = _build_gsc_rows(
        metric_facts=metric_facts,
        allowed_pages=allowed_pages,
        final_canonical_url=final_canonical_url,
        service_card_id=service_card_id,
        draft=draft,
        freshness=freshness,
    )
    gsc_rows.sort(key=lambda row: (row.impressions or 0, row.clicks or 0), reverse=True)

    (
        ads_rows,
        planner_rows,
        ads_blocker_evidence_ids,
        ads_blocker_codes,
        optional_ads_status,
    ) = _prepare_optional_ads_demand(
        metric_facts=metric_facts,
        allowed_pages=allowed_pages,
        final_canonical_url=final_canonical_url,
        service_card_id=service_card_id,
        gsc_rows=gsc_rows,
        freshness=freshness,
    )
    all_rows = [*gsc_rows, *ads_rows, *planner_rows]
    return ContentSearchDemandEvidence(
        status="available" if gsc_rows else "missing",
        gsc_query_rows=gsc_rows,
        ads_term_rows=ads_rows,
        keyword_planner_rows=planner_rows,
        source_connectors=list(dict.fromkeys(row.source_connector for row in all_rows)),
        evidence_ids=list(
            dict.fromkeys(
                [
                    *(evidence_id for row in all_rows for evidence_id in row.evidence_ids),
                    *ads_blocker_evidence_ids,
                ]
            )
        ),
        optional_ads_status=optional_ads_status,
        optional_ads_evidence_ids=list(
            dict.fromkeys(
                [
                    *(
                        evidence_id
                        for row in [*ads_rows, *planner_rows]
                        for evidence_id in row.evidence_ids
                    ),
                    *ads_blocker_evidence_ids,
                ]
            )
        ),
        optional_ads_blockers=ads_blocker_codes,
        safe_next_step=(
            "Odśwież lub napraw raport Ads; nie przypisujemy termów z niepełnych albo "
            "wrażliwych wierszy term → kliknięty landing."
            if ads_blocker_evidence_ids
            else "Odśwież Google Ads przed użyciem dopasowanych terminów w planie."
            if optional_ads_status == "stale"
            else
            "Sprawdź zapytania GSC przypisane do strony i sekcji; dane Ads są "
            "opcjonalne i pojawią się dopiero po ścisłym mapowaniu termu, strony i usługi."
            if gsc_rows
            else "Odśwież GSC albo sprawdź exact page mapping; nie planuj słów kluczowych z opisu."
        ),
    )


def _prepare_optional_ads_demand(
    *,
    metric_facts: list[MetricFact],
    allowed_pages: list[str],
    final_canonical_url: str,
    service_card_id: str | None,
    gsc_rows: list[ContentSearchDemandRow],
    freshness: ContentFreshnessAssessment,
) -> tuple[
    list[ContentSearchDemandRow],
    list[ContentSearchDemandRow],
    list[str],
    list[str],
    ContentOptionalAdsStatus,
]:
    gsc_by_page_term = {(row.page, row.term): row for row in gsc_rows}
    blocker_evidence_ids, blocker_codes = _ads_mapping_blockers(
        metric_facts,
        gsc_terms={row.term for row in gsc_rows},
    )
    ads_rows, planner_rows = _build_exact_ads_rows(
        ads_groups=_exact_ads_groups(
            metric_facts,
            allowed_pages=allowed_pages,
            service_card_id=service_card_id,
        ),
        gsc_by_page_term=gsc_by_page_term,
        final_canonical_url=final_canonical_url,
        service_card_id=service_card_id,
        freshness=freshness,
    )
    if (
        _connector_freshness_state(freshness, "google_ads") in {"blocked", "missing"}
        and (ads_rows or planner_rows)
    ):
        blocker_evidence_ids = list(
            dict.fromkeys(
                [
                    *blocker_evidence_ids,
                    *(
                        evidence_id
                        for row in [*ads_rows, *planner_rows]
                        for evidence_id in row.evidence_ids
                    ),
                ]
            )
        )
        blocker_codes = list(
            dict.fromkeys([*blocker_codes, "ads_source_freshness_blocked"])
        )
    if blocker_evidence_ids:
        ads_rows = []
        planner_rows = []
    status = _optional_ads_status(
        rows=[*ads_rows, *planner_rows],
        blocker_evidence_ids=blocker_evidence_ids,
    )
    return ads_rows, planner_rows, blocker_evidence_ids, blocker_codes, status


def _optional_ads_status(
    *,
    rows: list[ContentSearchDemandRow],
    blocker_evidence_ids: list[str],
) -> ContentOptionalAdsStatus:
    if blocker_evidence_ids:
        return "blocked"
    if not rows:
        return "not_exactly_mapped"
    if any(row.freshness == "stale" for row in rows):
        return "stale"
    return "exact_rows_available"


def _build_gsc_rows(
    *,
    metric_facts: list[MetricFact],
    allowed_pages: list[str],
    final_canonical_url: str,
    service_card_id: str | None,
    draft: ContentDraftPackage,
    freshness: ContentFreshnessAssessment,
) -> list[ContentSearchDemandRow]:
    groups = _group_facts(
        fact
        for fact in metric_facts
        if fact.source_connector == "google_search_console"
        and _page_matches_allowed(_fact_page(fact), allowed_pages)
        and fact.dimensions.get("query")
        and content_query_is_planning_signal(fact.dimensions["query"])
    )
    return [
        row
        for (page, term), facts in groups.items()
        if (
            row := _gsc_row(
                term=term,
                page=page,
                facts=facts,
                final_canonical_url=final_canonical_url,
                service_card_id=service_card_id,
                draft=draft,
                freshness=freshness,
            )
        )
        is not None
    ]


def _build_exact_ads_rows(
    *,
    ads_groups: dict[tuple[str, str], list[MetricFact]],
    gsc_by_page_term: dict[tuple[str, str], ContentSearchDemandRow],
    final_canonical_url: str,
    service_card_id: str | None,
    freshness: ContentFreshnessAssessment,
) -> tuple[list[ContentSearchDemandRow], list[ContentSearchDemandRow]]:
    ads_rows: list[ContentSearchDemandRow] = []
    planner_rows: list[ContentSearchDemandRow] = []
    for (ads_page, term), facts in ads_groups.items():
        gsc_row = gsc_by_page_term.get((ads_page, term))
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
            final_canonical_url=final_canonical_url,
            service_card_id=service_card_id,
            freshness=freshness,
        )
        if row is not None:
            (planner_rows if source_kind == "keyword_planner" else ads_rows).append(row)
    return ads_rows, planner_rows


def _ads_mapping_blockers(
    metric_facts: list[MetricFact],
    *,
    gsc_terms: set[str],
) -> tuple[list[str], list[str]]:
    global_blockers = [
        fact
        for fact in metric_facts
        if fact.source_connector == "google_ads"
        and fact.name == ADS_SEARCH_TERM_PAYLOAD_STATUS
        and fact.value == "blocked"
    ]
    ready_evidence_ids = _ready_ads_batch_evidence_ids(metric_facts)
    lineage_blockers: list[MetricFact] = []
    lineage_blocker_codes: list[str] = []
    for (_scope, _term, _landing_identity), facts in _group_ads_term_facts(
        metric_facts,
        allowed_terms=gsc_terms,
    ).items():
        if not _clicked_landing_batch_is_complete(facts, ready_evidence_ids):
            lineage_blockers.extend(facts)
            lineage_blocker_codes.append("ads_search_term_batch_incomplete")
        elif not _clicked_landing_lineage_is_valid(facts):
            lineage_blockers.extend(facts)
            lineage_blocker_codes.append("ads_search_term_landing_invalid")
    evidence_ids = list(
        dict.fromkeys(
            fact.evidence_id
            for fact in [*global_blockers, *lineage_blockers]
        )
    )
    blocker_codes = list(
        dict.fromkeys(
            [
                *(
                    "ads_search_term_payload_invalid"
                    for _ in global_blockers
                ),
                *lineage_blocker_codes,
            ]
        )
    )
    return evidence_ids, blocker_codes


def _group_facts(facts: Iterable[MetricFact]) -> dict[tuple[str, str], list[MetricFact]]:
    grouped: dict[tuple[str, str], list[MetricFact]] = {}
    for fact in facts:
        page = _fact_page(fact)
        term = (
            fact.dimensions.get("query")
            or fact.dimensions.get("search_term")
            or fact.dimensions.get("keyword_idea_text")
        )
        identity = build_landing_page_identity(page)
        if identity.canonical_url and term:
            grouped.setdefault((identity.canonical_url, term), []).append(fact)
    return grouped


def _gsc_row(
    *,
    term: str,
    page: str,
    facts: list[MetricFact],
    final_canonical_url: str,
    service_card_id: str | None,
    draft: ContentDraftPackage,
    freshness: ContentFreshnessAssessment,
) -> ContentSearchDemandRow | None:
    landing_match_tiers = _landing_match_tiers(facts, final_canonical_url)
    if not landing_match_tiers:
        return None
    evidence_ids = list(dict.fromkeys(fact.evidence_id for fact in facts))
    section_headings = assign_query_to_sections(
        term,
        (
            (section.heading, section.purpose)
            for section in draft.sections
            if set(section.evidence_ids).intersection(evidence_ids)
        ),
    )
    return ContentSearchDemandRow(
        source_kind="gsc_query",
        source_connector="google_search_console",
        term=term,
        page=page,
        landing_match_tiers=landing_match_tiers,
        service_card_id=service_card_id,
        alignment_basis="gsc_exact_page",
        review_required=False,
        section_headings=section_headings,
        section_mapping_status=(
            "intent_relevance" if section_headings else "page_only"
        ),
        period=facts[0].period,
        freshness=_connector_freshness_state(freshness, "google_search_console"),
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
    gsc_row: ContentSearchDemandRow | None,
    facts: list[MetricFact],
    final_canonical_url: str,
    service_card_id: str | None,
    freshness: ContentFreshnessAssessment,
) -> ContentSearchDemandRow | None:
    landing_match_tiers = _landing_match_tiers(facts, final_canonical_url)
    if not landing_match_tiers:
        return None
    page = gsc_row.page if gsc_row is not None else _fact_page(facts[0])
    if page is None:
        return None
    section_headings = gsc_row.section_headings if gsc_row is not None else []
    section_mapping_status = (
        gsc_row.section_mapping_status if gsc_row is not None else "page_only"
    )
    return ContentSearchDemandRow(
        source_kind=source_kind,
        source_connector="google_ads",
        term=term,
        page=page,
        landing_match_tiers=landing_match_tiers,
        service_card_id=service_card_id,
        alignment_basis=(
            "same_window_search_term_landing"
            if any(ADS_LANDING_IDENTITY in fact.dimensions for fact in facts)
            else "direct_page_service_scope"
        ),
        review_required=gsc_row is None,
        section_headings=section_headings,
        section_mapping_status=section_mapping_status,
        period=facts[0].period,
        freshness=_connector_freshness_state(freshness, "google_ads"),
        collected_at=max(
            (fact.collected_at for fact in facts if fact.collected_at is not None),
            default=None,
        ),
        evidence_ids=list(dict.fromkeys(fact.evidence_id for fact in facts)),
        impressions=_int_sum_metric(facts, "search_term_impressions"),
        clicks=_int_sum_metric(facts, "search_term_clicks"),
        ctr=_sum_ratio_metric(facts, "search_term_clicks", "search_term_impressions"),
        cost_micros=_int_sum_metric(facts, "search_term_cost_micros"),
        conversions=_float_sum_metric(facts, "search_term_conversions"),
        conversion_value=_float_sum_metric(facts, "search_term_conversion_value"),
        average_monthly_searches=_int_metric(
            facts, "keyword_planner_avg_monthly_searches"
        ),
    )


def _landing_match_tiers(
    facts: list[MetricFact],
    final_canonical_url: str,
) -> list[ContentAcceptedLandingMatchTier]:
    accepted: set[ContentAcceptedLandingMatchTier] = set()
    for fact in facts:
        page = _fact_page(fact)
        if not page:
            continue
        match = match_landing_page(
            final_canonical_url,
            LandingPageCandidate(candidate_id=fact.evidence_id, url=page),
        )
        if match.matched and match.tier in {"exact", "tracking_only", "host_alias"}:
            accepted.add(_accepted_landing_tier(match.tier))
    order = {"exact": 0, "tracking_only": 1, "host_alias": 2}
    return sorted(accepted, key=order.__getitem__)


def _accepted_landing_tier(tier: LandingMatchTier) -> ContentAcceptedLandingMatchTier:
    if tier not in {"exact", "tracking_only", "host_alias"}:
        raise ValueError(f"Unsupported accepted landing tier: {tier}")
    return cast(ContentAcceptedLandingMatchTier, tier)


def _strict_ads_scope_matches(
    fact: MetricFact,
    *,
    allowed_pages: list[str],
    service_card_id: str | None,
) -> bool:
    return bool(
        service_card_id
        and fact.dimensions.get("service_card_id") == service_card_id
        and _page_matches_allowed(_fact_page(fact), allowed_pages)
        and (
            fact.dimensions.get("search_term")
            or fact.dimensions.get("keyword_idea_text")
        )
    )


def _exact_ads_groups(
    metric_facts: list[MetricFact],
    *,
    allowed_pages: list[str],
    service_card_id: str | None,
) -> dict[tuple[str, str], list[MetricFact]]:
    direct_groups = _group_facts(
        fact
        for fact in metric_facts
        if fact.source_connector == "google_ads"
        and _strict_ads_scope_matches(
            fact,
            allowed_pages=allowed_pages,
            service_card_id=service_card_id,
        )
    )
    if not service_card_id:
        return direct_groups

    ready_evidence_ids = _ready_ads_batch_evidence_ids(metric_facts)
    ads_metric_facts = [
        fact for fact in metric_facts if fact.source_connector == "google_ads"
    ]
    for (_scope, term, landing_identity), term_facts in _group_ads_term_facts(
        ads_metric_facts
    ).items():
        if not _clicked_landing_batch_is_complete(
            term_facts,
            ready_evidence_ids,
        ) or not _clicked_landing_lineage_is_valid(term_facts):
            continue
        landing_page = _allowed_page_for_landing_identity(
            landing_identity,
            allowed_pages,
        )
        if landing_page is None:
            continue
        page_scoped_facts = [
            fact.model_copy(
                update={
                    "dimensions": {
                        **fact.dimensions,
                        "mapped_allowed_page": landing_page,
                        "final_url": landing_page,
                    }
                }
            )
            for fact in term_facts
        ]
        direct_groups.setdefault((landing_page, term), []).extend(page_scoped_facts)
    return direct_groups


def _group_ads_term_facts(
    metric_facts: list[MetricFact],
    *,
    allowed_terms: set[str] | None = None,
) -> dict[tuple[tuple[str, str], str, str], list[MetricFact]]:
    grouped: dict[tuple[tuple[str, str], str, str], list[MetricFact]] = {}
    for fact in metric_facts:
        scope = _ads_scope(fact)
        term = fact.dimensions.get("search_term")
        if (
            fact.source_connector != "google_ads"
            or fact.name not in CONTENT_ADS_TERM_METRIC_NAMES
            or scope is None
            or not term
            or _fact_page(fact)
            or (allowed_terms is not None and term not in allowed_terms)
        ):
            continue
        landing_identity = fact.dimensions.get(ADS_LANDING_IDENTITY, "")
        grouped.setdefault((scope, term, landing_identity), []).append(fact)
    return grouped


def _ads_scope(fact: MetricFact) -> tuple[str, str] | None:
    campaign_id = fact.dimensions.get("campaign_id")
    ad_group_id = fact.dimensions.get("ad_group_id")
    if not campaign_id or not ad_group_id:
        return None
    return campaign_id, ad_group_id


def _ready_ads_batch_evidence_ids(metric_facts: list[MetricFact]) -> set[str]:
    status_facts: dict[str, list[MetricFact]] = {}
    for fact in metric_facts:
        if (
            fact.source_connector == "google_ads"
            and fact.name == ADS_SEARCH_TERM_PAYLOAD_STATUS
            and fact.period == ADS_DEMAND_PERIOD
        ):
            status_facts.setdefault(fact.evidence_id, []).append(fact)
    return {
        evidence_id
        for evidence_id, facts in status_facts.items()
        if len(facts) == 1 and facts[0].value == "ready"
    }


def _clicked_landing_batch_is_complete(
    facts: list[MetricFact],
    ready_evidence_ids: set[str],
) -> bool:
    evidence_ids = {fact.evidence_id for fact in facts}
    counts = Counter(fact.name for fact in facts)
    return bool(
        len(evidence_ids) == 1
        and next(iter(evidence_ids), None) in ready_evidence_ids
        and set(counts) == CONTENT_ADS_TERM_METRIC_NAMES
        and set(counts.values()) == {1}
    )


def _allowed_page_for_landing_identity(
    landing_identity: str,
    allowed_pages: list[str],
) -> str | None:
    if not landing_identity:
        return None
    matches = []
    for allowed_page in allowed_pages:
        reference = build_redacted_landing_reference(allowed_page)
        if reference.identity_sha256 == landing_identity:
            identity = build_landing_page_identity(allowed_page)
            if identity.canonical_url:
                matches.append(identity.canonical_url)
    if len(set(matches)) != 1:
        return None
    return matches[0]


def _clicked_landing_lineage_is_valid(facts: list[MetricFact]) -> bool:
    if not facts:
        return False
    if any(fact.period != ADS_DEMAND_PERIOD for fact in facts):
        return False
    evidence_ids = {fact.evidence_id for fact in facts}
    identities = {fact.dimensions.get(ADS_LANDING_IDENTITY) for fact in facts}
    return (
        len(evidence_ids) == 1
        and len(identities) == 1
        and None not in identities
        and all(
            fact.dimensions.get(ADS_LANDING_MAPPING_STATUS) == ADS_LANDING_RESOLVED
            and fact.dimensions.get(ADS_LANDING_ACTUAL_CLICKED) == "true"
            for fact in facts
        )
    )


def _fact_page(fact: MetricFact) -> str | None:
    return (
        fact.dimensions.get("page")
        or fact.dimensions.get("landing_page")
        or fact.dimensions.get("final_url")
    )


def _page_matches_allowed(page: str | None, allowed_pages: list[str]) -> bool:
    return bool(page) and any(
        match_landing_page(
            expected,
            LandingPageCandidate(candidate_id="metric_fact_page", url=page),
        ).matched
        for expected in allowed_pages
    )


def _connector_freshness_state(
    freshness: ContentFreshnessAssessment,
    connector_id: str,
) -> Literal["fresh", "stale", "missing", "blocked"]:
    if connector_id in freshness.blocked_connector_ids:
        return "blocked"
    if connector_id in freshness.stale_connector_ids:
        return "stale"
    if connector_id in freshness.missing_connector_ids:
        return "missing"
    if (
        freshness.blocked_connector_ids
        or freshness.stale_connector_ids
        or freshness.missing_connector_ids
    ):
        return "fresh"
    return freshness.state


def _int_metric(facts: list[MetricFact], name: str) -> int | None:
    value = _metric(facts, name)
    return int(value) if isinstance(value, int | float) else None


def _float_metric(facts: list[MetricFact], name: str) -> float | None:
    value = _metric(facts, name)
    return float(value) if isinstance(value, int | float) else None


def _float_sum_metric(facts: list[MetricFact], name: str) -> float | None:
    values = [
        float(fact.value)
        for fact in facts
        if fact.name == name and isinstance(fact.value, int | float)
    ]
    return sum(values) if values else None


def _int_sum_metric(facts: list[MetricFact], name: str) -> int | None:
    value = _float_sum_metric(facts, name)
    return int(value) if value is not None else None


def _sum_ratio_metric(
    facts: list[MetricFact],
    numerator_name: str,
    denominator_name: str,
) -> float | None:
    numerator = _float_sum_metric(facts, numerator_name)
    denominator = _float_sum_metric(facts, denominator_name)
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _metric(facts: list[MetricFact], name: str) -> float | int | str | None:
    return next((fact.value for fact in facts if fact.name == name), None)


def content_query_is_planning_signal(term: str) -> bool:
    normalized = term.strip().casefold()
    if not normalized:
        return False
    return len(term) <= 160 and normalized.count("-site:") < 2 and not normalized.startswith(
        "site:"
    )
