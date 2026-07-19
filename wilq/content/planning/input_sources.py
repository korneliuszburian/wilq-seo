from __future__ import annotations

from typing import Literal, cast
from urllib.parse import urljoin, urlsplit

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.canonical.landing_identity import LandingPageCandidate, match_landing_page
from wilq.content.inventory.records import ContentInventoryRecord, ContentInventoryResolution
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.workflow.demand_evidence import (
    ContentAcceptedLandingMatchTier,
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.evidence.registry import list_evidence_by_ids
from wilq.schemas import (
    ConnectorCoveredWindow,
    ConnectorQualityState,
    ConnectorSettlementState,
    ContentFreshnessAssessment,
)

ContentPlanningSourceStatus = Literal[
    "used", "not_applicable", "missing", "stale", "blocked"
]
ContentPlanningSourceName = Literal[
    "wordpress",
    "service_profile",
    "gsc",
    "ga4",
    "google_ads",
    "ahrefs",
    "keyword_planner",
    "merchant",
    "localo",
    "social",
]
PLANNING_SOURCE_NAMES = {
    "wordpress",
    "service_profile",
    "gsc",
    "ga4",
    "google_ads",
    "ahrefs",
    "keyword_planner",
    "merchant",
    "localo",
    "social",
}
_ASSESSMENT_SOURCE_BY_CONNECTOR: dict[str, ContentPlanningSourceName] = {
    "public_site": "service_profile",
    "wordpress_ekologus": "wordpress",
    "wordpress_sklep": "wordpress",
    "google_search_console": "gsc",
    "google_analytics_4": "ga4",
    "google_ads": "google_ads",
    "ahrefs": "ahrefs",
    "google_merchant_center": "merchant",
    "localo": "localo",
}
_QUERY_PORTFOLIO_CONNECTORS = {"google_search_console", "google_ads"}


class ContentPlanningInventorySection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    recommended_disposition: Literal["preserve"] = "preserve"
    evidence_ids: list[str] = Field(default_factory=list)


class ContentPlanningInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "missing"]
    content_status: Literal["available", "missing"] = "missing"
    acf_section_status: Literal["available", "missing"] = "missing"
    title_or_h1: str | None = None
    content_summary: str | None = None
    # Read-only material projection used by the planner.  Keeping the exact
    # extracted body and its provenance in the typed input prevents the model
    # from planning against a title/heading-only shadow of the page.
    content_text: str | None = None
    extraction_region: str | None = None
    material_confidence: Literal["source_bound", "review_required", "unknown"] = "unknown"
    source_field_lineage: list[str] = Field(default_factory=list)
    word_count: int | None = Field(default=None, ge=0)
    sections: list[ContentPlanningInventorySection] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    landing_match_tiers: list[ContentAcceptedLandingMatchTier] = Field(default_factory=list)
    note: str = ""


class ContentPlanningSourceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_connector: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    source_fact_ids: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)


class ContentPlanningSourceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: ContentPlanningSourceName
    status: ContentPlanningSourceStatus
    reason: str = Field(min_length=1)
    landing_match_tiers: list[ContentAcceptedLandingMatchTier] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    refresh_run_id: str | None = None
    covered_window: ConnectorCoveredWindow = Field(default_factory=ConnectorCoveredWindow)
    settlement_state: ConnectorSettlementState = ConnectorSettlementState.unknown
    quality_state: ConnectorQualityState = ConnectorQualityState.unknown
    interpretation_caveats: list[str] = Field(default_factory=list)


def validate_source_assessment_membership(
    assessments: list[ContentPlanningSourceAssessment],
) -> None:
    sources = [assessment.source for assessment in assessments]
    if len(sources) != len(PLANNING_SOURCE_NAMES) or set(sources) != PLANNING_SOURCE_NAMES:
        raise ValueError("Source assessments require every planning source exactly once.")


def build_planning_inventory(
    item: ContentWorkItem,
    resolution: ContentInventoryResolution,
) -> ContentPlanningInventory:
    expected_url = item.final_canonical_url or item.source_public_url
    matches = [
        matched
        for record in resolution.records
        if (matched := _matching_record(expected_url, record)) is not None
    ]
    if len(matches) != 1:
        note = (
            "Nie znaleziono dokładnego rekordu inventory dla finalnego canonicalu."
            if not matches
            else "Więcej niż jeden rekord inventory pasuje do finalnego canonicalu."
        )
        return ContentPlanningInventory(status="missing", note=note)
    _, record, tiers = matches[0]
    wordpress_evidence = [
        evidence
        for evidence in list_evidence_by_ids(record.evidence_ids)
        if evidence.source_connector in {"wordpress_ekologus", "wordpress_sklep"}
    ]
    evidence_ids = [evidence.id for evidence in wordpress_evidence]
    connectors = _unique([evidence.source_connector for evidence in wordpress_evidence])
    if not evidence_ids or not connectors:
        return ContentPlanningInventory(
            status="missing",
            note="Dokładny rekord inventory nie ma rozwiązywalnego evidence WordPress.",
        )
    headings = (
        item.wordpress_acf_section_headings
        if item.wordpress_acf_section_inventory_status == "available"
        else item.wordpress_section_headings
    )
    return ContentPlanningInventory(
        status="available" if headings else "missing",
        content_status=item.wordpress_content_inventory_status,
        acf_section_status=item.wordpress_acf_section_inventory_status,
        title_or_h1=item.wordpress_title_or_h1,
        content_summary=item.wordpress_content_summary,
        content_text=item.wordpress_content_text,
        extraction_region=item.wordpress_content_extraction_region,
        material_confidence=cast(
            Literal["source_bound", "review_required", "unknown"],
            item.wordpress_content_material_confidence or "unknown",
        ),
        source_field_lineage=item.wordpress_content_source_field_lineage,
        word_count=item.wordpress_content_word_count,
        sections=[
            ContentPlanningInventorySection(
                section_id=f"inventory_section_{index:02d}",
                heading=heading,
                evidence_ids=evidence_ids,
            )
            for index, heading in enumerate(headings, start=1)
        ],
        evidence_ids=evidence_ids,
        source_connectors=connectors,
        landing_match_tiers=tiers,
        note=(
            item.wordpress_content_inventory_note
            or item.wordpress_acf_section_inventory_note
            or ""
        ),
    )


def build_source_assessments(
    *,
    item: ContentWorkItem,
    inventory: ContentPlanningInventory,
    service_profile: ContentWorkItemServiceProfileContext,
    freshness: ContentFreshnessAssessment,
    brief: ContentSalesBrief,
    demand: ContentSearchDemandEvidence,
    service_lifecycle: str,
) -> list[ContentPlanningSourceAssessment]:
    fact_kinds = {fact.source_connector for fact in brief.source_facts}
    fact_evidence = _fact_evidence_by_connector(brief)
    gsc_evidence = _row_evidence(demand.gsc_query_rows)
    ads_evidence = _row_evidence(demand.ads_term_rows)
    planner_evidence = _row_evidence(demand.keyword_planner_rows)
    gsc_tiers = _demand_tiers(demand.gsc_query_rows)
    ads_tiers = _demand_tiers(demand.ads_term_rows)
    planner_tiers = _demand_tiers(demand.keyword_planner_rows)
    ga4_evidence, ga4_tiers = _ga4_page_signal(item, brief.final_canonical_url)
    wordpress_status = _source_status(
        available=inventory.status == "available",
        connector_ids=inventory.source_connectors,
        freshness=freshness,
        absent_status="missing",
    )
    service_status = _source_status(
        available=service_lifecycle == "approved_current",
        connector_ids=service_profile.source_connectors,
        freshness=freshness,
        absent_status="blocked",
    )
    assessments = [
        _assessment(
            "wordpress",
            wordpress_status,
            "Publiczne inventory strony jest wejściem do decyzji zachowaj/scal/przepisz."
            if wordpress_status == "used"
            else "Brakuje aktualnego, dokładnie powiązanego inventory WordPress.",
            inventory.evidence_ids,
            landing_match_tiers=inventory.landing_match_tiers,
        ),
        _assessment(
            "service_profile",
            service_status,
            "Zatwierdzona karta usługi ogranicza odbiorcę, problemy, CTA i twierdzenia."
            if service_status == "used"
            else "Karta usługi nie jest zatwierdzona albo jej źródło wymaga odświeżenia.",
            service_profile.evidence_ids,
            brief.knowledge_card_ids,
        ),
        _assessment(
            "gsc",
            _available_status(gsc_evidence and gsc_tiers, ["google_search_console"], freshness),
            "Dokładne zapytania tej strony są wejściem planu."
            if gsc_evidence
            else "Brak dokładnych zapytań GSC dla strony.",
            gsc_evidence,
            landing_match_tiers=gsc_tiers,
        ),
        _assessment(
            "ga4",
            _available_status(ga4_evidence and ga4_tiers, ["google_analytics_4"], freshness),
            "GA4 ma exact landing signal i zasila diagnozę zachowania strony."
            if ga4_evidence and ga4_tiers
            else "Brak exact sygnału GA4 dla tej strony.",
            ga4_evidence,
            landing_match_tiers=ga4_tiers,
        ),
        _ads_source_assessment(
            demand=demand,
            freshness=freshness,
            evidence_ids=ads_evidence,
            landing_match_tiers=ads_tiers,
        ),
        _blocked_typed_source(
            "ahrefs", "ahrefs", fact_kinds, fact_evidence,
            "Ahrefs ma evidence, ale bez typed cross-source matchu nie zasila planu.",
            "Brak dokładnego, cross-source sygnału Ahrefs dla tej strony.",
        ),
        _assessment(
            "keyword_planner",
            _available_status(planner_evidence and planner_tiers, ["google_ads"], freshness),
            "Dokładne metryki Keyword Planner są dostępne."
            if planner_evidence
            else "Brak developer tokena albo exact term mappingu; nie zgadujemy wolumenu.",
            planner_evidence,
            landing_match_tiers=planner_tiers,
        ),
        *_conditional_assessments(
            item=item,
            brief=brief,
            fact_kinds=fact_kinds,
            fact_evidence=fact_evidence,
        ),
    ]
    return [
        assessment.model_copy(update=_source_quality_update(assessment.source, freshness))
        for assessment in assessments
    ]


def _ga4_page_signal(
    item: ContentWorkItem,
    final_canonical_url: str,
) -> tuple[list[str], list[ContentAcceptedLandingMatchTier]]:
    evidence_ids: list[str] = []
    tiers: list[ContentAcceptedLandingMatchTier] = []
    for fact in item.metric_facts:
        if fact.source_connector != "google_analytics_4":
            continue
        candidate_url = next(
            (
                fact.dimensions.get(key)
                for key in ("landing_page", "landingPagePlusQueryString", "page")
                if fact.dimensions.get(key)
            ),
            None,
        )
        if not candidate_url:
            continue
        parsed_candidate = urlsplit(candidate_url)
        if parsed_candidate.path.startswith("/") and not parsed_candidate.netloc:
            candidate_url = urljoin(final_canonical_url, candidate_url)
        match = match_landing_page(
            final_canonical_url,
            LandingPageCandidate(
                candidate_id=f"ga4_{fact.evidence_id}_{fact.name}",
                url=candidate_url,
            ),
        )
        if match.matched and match.tier in {"exact", "tracking_only", "host_alias"}:
            evidence_ids.append(fact.evidence_id)
            tiers.append(cast(ContentAcceptedLandingMatchTier, match.tier))
    return list(dict.fromkeys(evidence_ids)), list(dict.fromkeys(tiers))


_SOURCE_QUALITY_CONNECTORS: dict[ContentPlanningSourceName, tuple[str, ...]] = {
    "wordpress": ("wordpress_ekologus", "wordpress_sklep"),
    "gsc": ("google_search_console",),
    "ga4": ("google_analytics_4",),
    "google_ads": ("google_ads",),
    "ahrefs": ("ahrefs",),
    "merchant": ("google_merchant_center",),
    "localo": ("localo",),
}


def _source_quality_update(
    source: ContentPlanningSourceName,
    freshness: ContentFreshnessAssessment,
) -> dict[str, object]:
    connector_id = next(
        (
            candidate
            for candidate in _SOURCE_QUALITY_CONNECTORS.get(source, ())
            if candidate in freshness.connector_refresh_run_ids
        ),
        None,
    )
    if connector_id is None:
        return {}
    return {
        "refresh_run_id": freshness.connector_refresh_run_ids[connector_id],
        "covered_window": freshness.connector_covered_windows.get(
            connector_id, ConnectorCoveredWindow()
        ),
        "settlement_state": freshness.connector_settlement_states.get(
            connector_id, ConnectorSettlementState.unknown
        ),
        "quality_state": freshness.connector_quality_states.get(
            connector_id, ConnectorQualityState.unknown
        ),
        "interpretation_caveats": freshness.connector_quality_caveats.get(
            connector_id, []
        ),
    }


def _ads_source_assessment(
    *,
    demand: ContentSearchDemandEvidence,
    freshness: ContentFreshnessAssessment,
    evidence_ids: list[str],
    landing_match_tiers: list[ContentAcceptedLandingMatchTier],
) -> ContentPlanningSourceAssessment:
    service_binding_blocked = any(
        row.service_binding_status in {"unbound", "ambiguous", "review_required"}
        for row in demand.ads_term_rows
    )
    blocked = (
        demand.optional_ads_status == "blocked"
        or "google_ads" in freshness.blocked_connector_ids
        or service_binding_blocked
    )
    status = (
        "blocked"
        if blocked
        else _available_status(
            bool(evidence_ids and landing_match_tiers),
            ["google_ads"],
            freshness,
            absent_status="not_applicable",
        )
    )
    reason = (
        "Raport Ads jest niepełny albo nie pozwala na ścisłe mapowanie landingu lub usługi."
        if blocked
        else "Dopasowanie termu i klikniętego landingu jest dokładne, ale batch Ads "
        "jest nieaktualny i nie zasila planu do czasu odświeżenia."
        if demand.optional_ads_status == "stale"
        else "Termin Ads, jego metryki i faktycznie kliknięty landing pochodzą z "
        "tego samego 30-dniowego wiersza; landing dokładnie pasuje do strony, a "
        "usługa jest potwierdzona przez operatora."
        if evidence_ids
        else "Brak ścisłego mapowania termu, strony i usługi; Ads nie zasila planu."
    )
    return _assessment(
        "google_ads",
        status,
        reason,
        evidence_ids or demand.optional_ads_evidence_ids,
        landing_match_tiers=landing_match_tiers,
    )


def _conditional_assessments(
    *,
    item: ContentWorkItem,
    brief: ContentSalesBrief,
    fact_kinds: set[str],
    fact_evidence: dict[str, list[str]],
) -> list[ContentPlanningSourceAssessment]:
    return [
        _conditional_typed_source(
            "merchant", "google_merchant_center", fact_kinds, fact_evidence,
            "wordpress_sklep" in item.source_connectors,
            "Merchant ma evidence, ale bez typed product/page matchu nie zasila planu.",
            "Strona produktowa nie ma dokładnych faktów Merchant.",
            "To nie jest strona produktowa.",
        ),
        _conditional_typed_source(
            "localo", "localo", fact_kinds, fact_evidence,
            "lokal" in brief.search_intent.casefold(),
            "Localo ma evidence, ale bez typed lokalnego matchu nie zasila planu.",
            "Lokalna intencja wymaga dokładnego sygnału Localo.",
            "Strona nie ma potwierdzonej lokalnej intencji.",
        ),
        _assessment(
            "social",
            "not_applicable",
            "Social może ponownie użyć dopiero zatwierdzonej treści; nie zmienia planu strony.",
        ),
    ]


def build_source_facts(
    brief: ContentSalesBrief,
    assessments: list[ContentPlanningSourceAssessment],
    service_profile: ContentWorkItemServiceProfileContext | None = None,
) -> list[ContentPlanningSourceFact]:
    statuses = {assessment.source: assessment.status for assessment in assessments}
    facts = [
        ContentPlanningSourceFact(
            fact_id=f"planning_fact_{index:02d}",
            summary=fact.summary,
            source_connector=fact.source_connector,
            evidence_ids=[fact.evidence_id],
            knowledge_card_ids=brief.knowledge_card_ids,
            source_fact_ids=fact.source_fact_ids,
            source_material_ids=fact.source_material_ids,
        )
        for index, fact in enumerate(brief.source_facts, start=1)
        if fact.source_connector not in _QUERY_PORTFOLIO_CONNECTORS
        and (
            (source := _ASSESSMENT_SOURCE_BY_CONNECTOR.get(fact.source_connector)) is None
            or statuses.get(source) == "used"
        )
    ]
    if service_profile is not None and service_profile.source_fact_ids:
        facts.extend(
            ContentPlanningSourceFact(
                fact_id=f"planning_service_fact_{index:02d}",
                summary=(
                    f"Zatwierdzony fakt profilu usługi: {service_profile.service_label or 'usługa'}"
                ),
                source_connector=(service_profile.source_connectors or ["service_profile"])[0],
                evidence_ids=service_profile.evidence_ids or ["service_profile_source_fact"],
                knowledge_card_ids=service_profile.knowledge_card_ids,
                source_fact_ids=list(service_profile.source_fact_ids),
                source_material_ids=list(service_profile.source_material_ids),
            )
            for index in range(1, 2)
        )
    return facts


def assessment_status(
    assessments: list[ContentPlanningSourceAssessment],
    source: ContentPlanningSourceName,
) -> ContentPlanningSourceStatus | None:
    return next((item.status for item in assessments if item.source == source), None)


def usable_query_portfolio(
    demand: ContentSearchDemandEvidence,
    assessments: list[ContentPlanningSourceAssessment],
) -> ContentSearchDemandEvidence:
    gsc = demand.gsc_query_rows if assessment_status(assessments, "gsc") == "used" else []
    ads = demand.ads_term_rows if assessment_status(assessments, "google_ads") == "used" else []
    planner = (
        demand.keyword_planner_rows
        if assessment_status(assessments, "keyword_planner") == "used"
        else []
    )
    rows = [*gsc, *ads, *planner]
    return demand.model_copy(update={
        "status": "available" if gsc else "missing",
        "gsc_query_rows": gsc,
        "ads_term_rows": ads,
        "keyword_planner_rows": planner,
        "source_connectors": _unique([row.source_connector for row in rows]),
        "evidence_ids": _row_evidence(rows),
        "optional_ads_status": (
            "blocked"
            if demand.optional_ads_status == "blocked"
            else "stale"
            if demand.optional_ads_status == "stale"
            else "exact_rows_available"
            if ads or planner
            else "not_exactly_mapped"
        ),
    })


def planning_source_connectors(
    *,
    inventory: ContentPlanningInventory,
    service_profile: ContentWorkItemServiceProfileContext,
    demand: ContentSearchDemandEvidence,
    source_facts: list[ContentPlanningSourceFact],
    assessments: list[ContentPlanningSourceAssessment],
) -> list[str]:
    connectors = [*demand.source_connectors, *(fact.source_connector for fact in source_facts)]
    if assessment_status(assessments, "wordpress") == "used":
        connectors.extend(inventory.source_connectors)
    if assessment_status(assessments, "service_profile") == "used":
        connectors.extend(service_profile.source_connectors)
    return _unique(connectors)


def _matching_record(
    expected_url: str | None,
    record: ContentInventoryRecord,
) -> tuple[str, ContentInventoryRecord, list[ContentAcceptedLandingMatchTier]] | None:
    if not expected_url:
        return None
    tiers: list[ContentAcceptedLandingMatchTier] = []
    for candidate_url in [record.url, record.final_canonical_url]:
        if not candidate_url:
            continue
        match = match_landing_page(
            expected_url,
            LandingPageCandidate(candidate_id=record.id, url=candidate_url),
        )
        if not match.matched or match.tier not in {"exact", "tracking_only", "host_alias"}:
            return None
        tiers.append(cast(ContentAcceptedLandingMatchTier, match.tier))
    return (record.id, record, _ordered_tiers(tiers)) if tiers else None


def _assessment(
    source: ContentPlanningSourceName,
    status: ContentPlanningSourceStatus,
    reason: str,
    evidence_ids: list[str] | None = None,
    knowledge_card_ids: list[str] | None = None,
    *,
    landing_match_tiers: list[ContentAcceptedLandingMatchTier] | None = None,
) -> ContentPlanningSourceAssessment:
    return ContentPlanningSourceAssessment(
        source=source,
        status=status,
        reason=reason,
        evidence_ids=_unique(evidence_ids or []),
        knowledge_card_ids=_unique(knowledge_card_ids or []),
        landing_match_tiers=landing_match_tiers or [],
    )


def _blocked_typed_source(
    source: ContentPlanningSourceName,
    connector: str,
    fact_kinds: set[str],
    evidence: dict[str, list[str]],
    blocked_reason: str,
    missing_reason: str,
) -> ContentPlanningSourceAssessment:
    present = connector in fact_kinds
    return _assessment(
        source, "blocked" if present else "missing",
        blocked_reason if present else missing_reason,
        evidence.get(connector),
    )


def _conditional_typed_source(
    source: ContentPlanningSourceName,
    connector: str,
    fact_kinds: set[str],
    evidence: dict[str, list[str]],
    applicable: bool,
    blocked_reason: str,
    missing_reason: str,
    not_applicable_reason: str,
) -> ContentPlanningSourceAssessment:
    if connector in fact_kinds:
        return _assessment(source, "blocked", blocked_reason, evidence.get(connector))
    return _assessment(
        source,
        "missing" if applicable else "not_applicable",
        missing_reason if applicable else not_applicable_reason,
    )


def _available_status(
    available: object,
    connector_ids: list[str],
    freshness: ContentFreshnessAssessment,
    *,
    absent_status: ContentPlanningSourceStatus = "missing",
) -> ContentPlanningSourceStatus:
    return _source_status(
        available=bool(available),
        connector_ids=connector_ids,
        freshness=freshness,
        absent_status=absent_status,
    )


def _source_status(
    *,
    available: bool,
    connector_ids: list[str],
    freshness: ContentFreshnessAssessment,
    absent_status: ContentPlanningSourceStatus,
) -> ContentPlanningSourceStatus:
    if not available:
        return absent_status
    connectors = set(connector_ids)
    if connectors.intersection(freshness.blocked_connector_ids):
        return "blocked"
    if connectors.intersection(freshness.stale_connector_ids):
        return "stale"
    if connectors.intersection(freshness.missing_connector_ids):
        return "missing"
    return "used"


def _fact_evidence_by_connector(brief: ContentSalesBrief) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for fact in brief.source_facts:
        grouped.setdefault(fact.source_connector, []).append(fact.evidence_id)
    return {connector: _unique(ids) for connector, ids in grouped.items()}


def _row_evidence(rows: list[ContentSearchDemandRow]) -> list[str]:
    return _unique([evidence_id for row in rows for evidence_id in row.evidence_ids])


def _demand_tiers(rows: list[ContentSearchDemandRow]) -> list[ContentAcceptedLandingMatchTier]:
    return _ordered_tiers([tier for row in rows for tier in row.landing_match_tiers])


def _ordered_tiers(
    tiers: list[ContentAcceptedLandingMatchTier],
) -> list[ContentAcceptedLandingMatchTier]:
    order = {"exact": 0, "tracking_only": 1, "host_alias": 2}
    return sorted(set(tiers), key=order.__getitem__)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = [
    "ContentPlanningInventory",
    "ContentPlanningSourceAssessment",
    "ContentPlanningSourceFact",
    "assessment_status",
    "build_planning_inventory",
    "build_source_assessments",
    "build_source_facts",
    "planning_source_connectors",
    "usable_query_portfolio",
    "validate_source_assessment_membership",
]
