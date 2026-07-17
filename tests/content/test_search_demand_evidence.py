from __future__ import annotations

from datetime import UTC, datetime

from wilq.content.canonical.redacted_landing import build_redacted_landing_reference
from wilq.content.drafts.package import ContentDraftPackage, ContentDraftSection
from wilq.content.workflow.demand_evidence import (
    ContentSearchDemandEvidence,
    build_content_search_demand_evidence,
)
from wilq.schemas import ContentFreshnessAssessment, MetricFact


def test_search_demand_keeps_page_queries_but_maps_only_relevant_sections() -> None:
    page = "https://www.ekologus.pl/bdo/"
    service_card_id = "service_bdo"
    evidence = build_content_search_demand_evidence(
        metric_facts=_demand_facts(page, service_card_id),
        source_page=page,
        final_canonical_url=page,
        service_card_id=service_card_id,
        draft=_draft(),
        freshness=ContentFreshnessAssessment(
            state="fresh",
            requires_refresh=False,
            summary="Źródła aktualne.",
            next_step="Użyj dowodów.",
        ),
    )

    assert evidence.status == "available"
    assert [row.term for row in evidence.gsc_query_rows] == [
        "bdo odpady",
        "subdomena firmowa",
    ]
    assert evidence.gsc_query_rows[0].model_dump(
        include={"impressions", "clicks", "ctr", "average_position", "section_headings"}
    ) == {
        "impressions": 120,
        "clicks": 12,
        "ctr": 0.1,
        "average_position": 6.4,
        "section_headings": [],
    }
    assert evidence.gsc_query_rows[1].section_headings == []
    assert [row.section_mapping_status for row in evidence.gsc_query_rows] == [
        "page_only",
        "page_only",
    ]
    assert evidence.ads_term_rows[0].section_mapping_status == "page_only"
    assert evidence.gsc_query_rows[0].landing_match_tiers == ["exact"]
    assert evidence.ads_term_rows[0].landing_match_tiers == ["exact"]
    assert [row.evidence_ids for row in evidence.ads_term_rows] == [["ev_ads_exact"]]
    assert evidence.keyword_planner_rows == []
    assert evidence.evidence_ids == ["ev_gsc", "ev_ads_exact"]
    assert evidence.optional_ads_status == "exact_rows_available"


def test_search_demand_accepts_tracking_only_but_rejects_functional_page_variant() -> None:
    page = "https://www.ekologus.pl/oferta/?service=outsourcing"
    evidence = build_content_search_demand_evidence(
        metric_facts=[
            _fact(
                "google_search_console",
                "impressions",
                50,
                "ev_tracking",
                f"{page}&utm_source=search",
                "outsourcing środowiskowy",
            ),
            _fact(
                "google_search_console",
                "clicks",
                5,
                "ev_tracking",
                f"{page}&utm_medium=organic",
                "outsourcing środowiskowy",
            ),
            _fact(
                "google_search_console",
                "impressions",
                500,
                "ev_other_service",
                "https://www.ekologus.pl/oferta/?service=audyt",
                "audyt środowiskowy",
            ),
        ],
        source_page=page,
        final_canonical_url=page,
        service_card_id="service_outsourcing",
        draft=_draft(),
        freshness=ContentFreshnessAssessment(
            state="fresh",
            requires_refresh=False,
            summary="Źródła aktualne.",
            next_step="Użyj dowodów.",
        ),
    )

    assert [row.term for row in evidence.gsc_query_rows] == [
        "outsourcing środowiskowy"
    ]
    assert evidence.evidence_ids == ["ev_tracking"]
    assert evidence.gsc_query_rows[0].impressions == 50
    assert evidence.gsc_query_rows[0].clicks == 5
    assert evidence.gsc_query_rows[0].landing_match_tiers == ["tracking_only"]


def test_search_demand_joins_ads_metrics_to_clicked_search_term_landing() -> None:
    page, facts = _same_window_ads_case()
    exact = _build_demand(facts, page)

    assert len(exact.ads_term_rows) == 1
    assert exact.ads_term_rows[0].service_card_id == "service_bdo"
    assert exact.ads_term_rows[0].clicks == 9
    assert exact.ads_term_rows[0].impressions == 100
    assert exact.ads_term_rows[0].ctr == 0.09
    assert exact.ads_term_rows[0].cost_micros == 2_400_000
    assert exact.ads_term_rows[0].conversions == 1.5
    assert exact.ads_term_rows[0].evidence_ids == ["ev_ads_refresh"]
    assert exact.ads_term_rows[0].alignment_basis == "same_window_search_term_landing"


def test_search_demand_ignores_exact_term_for_a_different_clicked_landing() -> None:
    page, facts = _same_window_ads_case()
    other_page = "https://www.ekologus.pl/kpo/"
    other_landing_facts = [
        *(
            _ads_term_fact(
                name,
                value,
                page=other_page,
                campaign_id="102",
                evidence_id="ev_ads_other_landing",
            )
            for name, value in (
                ("search_term_clicks", 70),
                ("search_term_impressions", 700),
                ("search_term_cost_micros", 7_000_000),
                ("search_term_conversions", 2.0),
                ("search_term_conversion_value", 500.0),
            )
        ),
        MetricFact(
            name="search_term_payload_status",
            value="ready",
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_other_landing",
            dimensions={},
            collected_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
        ),
    ]

    evidence = _build_demand([*facts, *other_landing_facts], page)

    assert len(evidence.ads_term_rows) == 1
    assert evidence.ads_term_rows[0].clicks == 9
    assert evidence.optional_ads_status == "exact_rows_available"


def test_search_demand_blocks_invalid_clicked_landing_for_overlapping_term() -> None:
    page, facts = _same_window_ads_case()
    invalid_dimensions = {
        "campaign_id": "103",
        "ad_group_id": "201",
        "search_term": "bdo odpady",
        "landing_mapping_status": "sensitive",
    }
    invalid_metrics = [
        _ads_term_fact(
            name,
            value,
            page=page,
            campaign_id="103",
            evidence_id="ev_ads_invalid",
        ).model_copy(update={"dimensions": invalid_dimensions})
        for name, value in (
            ("search_term_clicks", 3),
            ("search_term_impressions", 30),
            ("search_term_cost_micros", 1_000_000),
            ("search_term_conversions", 0.5),
            ("search_term_conversion_value", 100.0),
        )
    ]
    invalid_status = MetricFact(
        name="search_term_payload_status",
        value="ready",
        period="last_30_days",
        source_connector="google_ads",
        evidence_id="ev_ads_invalid",
        dimensions={},
        collected_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
    )
    blocked = _build_demand([*facts, *invalid_metrics, invalid_status], page)

    assert blocked.ads_term_rows == []
    assert blocked.optional_ads_status == "blocked"
    assert blocked.optional_ads_blockers == ["ads_search_term_landing_invalid"]
    assert blocked.optional_ads_evidence_ids == ["ev_ads_invalid"]


def test_search_demand_blocks_partial_persisted_ads_batch() -> None:
    page, facts = _same_window_ads_case()
    partial = [
        fact
        for fact in facts
        if fact.name != "search_term_conversion_value"
    ]

    blocked = _build_demand(partial, page)

    assert blocked.ads_term_rows == []
    assert blocked.optional_ads_status == "blocked"
    assert blocked.optional_ads_blockers == ["ads_search_term_batch_incomplete"]
    assert blocked.optional_ads_evidence_ids == ["ev_ads_refresh"]


def test_search_demand_blocks_duplicate_persisted_ads_metrics() -> None:
    page, facts = _same_window_ads_case()
    duplicate_metrics = [
        fact
        for fact in facts
        if fact.name.startswith("search_term_")
        and fact.name != "search_term_payload_status"
    ]

    blocked = _build_demand([*facts, *duplicate_metrics], page)

    assert blocked.ads_term_rows == []
    assert blocked.optional_ads_status == "blocked"
    assert blocked.optional_ads_blockers == ["ads_search_term_batch_incomplete"]
    assert blocked.optional_ads_evidence_ids == ["ev_ads_refresh"]


def test_search_demand_projects_ads_freshness_per_connector() -> None:
    page, facts = _same_window_ads_case()

    evidence = _build_demand(
        facts,
        page,
        stale_connector_ids=["google_ads"],
    )

    assert evidence.optional_ads_status == "stale"
    assert evidence.optional_ads_evidence_ids == ["ev_ads_refresh"]
    assert evidence.gsc_query_rows[0].freshness == "fresh"
    assert evidence.ads_term_rows[0].freshness == "stale"


def _same_window_ads_case() -> tuple[str, list[MetricFact]]:
    page = "https://www.ekologus.pl/bdo/"
    return page, [
        _fact("google_search_console", "impressions", 40, "ev_gsc", page, "bdo odpady"),
        _fact("google_search_console", "clicks", 4, "ev_gsc", page, "bdo odpady"),
        _ads_term_fact("search_term_clicks", 9, page=page),
        _ads_term_fact("search_term_cost_micros", 2_400_000, page=page),
        _ads_term_fact("search_term_impressions", 100, page=page),
        _ads_term_fact("search_term_conversions", 1.5, page=page),
        _ads_term_fact("search_term_conversion_value", 900.0, page=page),
        MetricFact(
            name="search_term_payload_status",
            value="ready",
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_refresh",
            dimensions={},
            collected_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
        ),
    ]


def _ads_term_fact(
    name: str,
    value: int | float,
    *,
    page: str,
    campaign_id: str = "101",
    evidence_id: str = "ev_ads_refresh",
) -> MetricFact:
    identity = build_redacted_landing_reference(page).identity_sha256
    assert identity is not None
    return MetricFact(
        name=name,
        value=value,
        period="last_30_days",
        source_connector="google_ads",
        evidence_id=evidence_id,
        dimensions={
            "campaign_id": campaign_id,
            "ad_group_id": "201",
            "search_term": "bdo odpady",
            "landing_mapping_status": "resolved",
            "landing_identity_sha256": identity,
            "actual_clicked_in_window": "true",
        },
        collected_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
    )


def _build_demand(
    metric_facts: list[MetricFact],
    page: str,
    *,
    stale_connector_ids: list[str] | None = None,
) -> ContentSearchDemandEvidence:
    return build_content_search_demand_evidence(
        metric_facts=metric_facts,
        source_page=page,
        final_canonical_url=page,
        service_card_id="service_bdo",
        draft=_draft(),
        freshness=ContentFreshnessAssessment(
            state="fresh",
            requires_refresh=False,
            stale_connector_ids=stale_connector_ids or [],
            summary="Źródła aktualne.",
            next_step="Użyj dowodów.",
        ),
    )


def _demand_facts(page: str, service_card_id: str) -> list[MetricFact]:
    return [
        _fact("google_search_console", "impressions", 120, "ev_gsc", page, "bdo odpady"),
        _fact("google_search_console", "clicks", 12, "ev_gsc", page, "bdo odpady"),
        _fact("google_search_console", "ctr", 0.1, "ev_gsc", page, "bdo odpady"),
        _fact("google_search_console", "average_position", 6.4, "ev_gsc", page, "bdo odpady"),
        _fact(
            "google_search_console",
            "impressions",
            1,
            "ev_gsc",
            page,
            "subdomena firmowa",
        ),
        _fact(
            "google_search_console",
            "impressions",
            300,
            "ev_gsc_noise",
            page,
            '"bdo" -site:reddit.com -site:youtube.com -site:x.com',
        ),
        _fact(
            "google_search_console",
            "impressions",
            999,
            "ev_foreign_page",
            "https://www.ekologus.pl/kpo/",
            "kpo odpady",
        ),
        _fact(
            "google_ads",
            "search_term_clicks",
            7,
            "ev_ads_exact",
            page,
            "bdo odpady",
            service_card_id=service_card_id,
        ),
        _fact(
            "google_ads",
            "search_term_clicks",
            80,
            "ev_ads_foreign_service",
            page,
            "bdo odpady",
            service_card_id="service_kpo",
        ),
        MetricFact(
            name="keyword_planner_avg_monthly_searches",
            value=500,
            period="keyword_planner",
            source_connector="google_ads",
            evidence_id="ev_planner_unmapped",
            dimensions={"keyword_idea_text": "bdo odpady"},
            collected_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
        ),
    ]


def _draft() -> ContentDraftPackage:
    return ContentDraftPackage(
        id="draft_bdo",
        work_item_id="item_bdo",
        brief_id="brief_bdo",
        claim_ledger_id="ledger_bdo",
        title="BDO",
        sections=[
            ContentDraftSection(
                heading="Obowiązki BDO",
                purpose="Wyjaśnij obowiązki.",
                evidence_ids=["ev_gsc"],
            ),
            ContentDraftSection(
                heading="Subdomena firmowa",
                purpose="Nie mapuj bez wspólnego dowodu.",
                evidence_ids=["ev_service"],
            ),
        ],
    )


def _fact(
    connector: str,
    name: str,
    value: int | float,
    evidence_id: str,
    page: str,
    term: str,
    *,
    service_card_id: str | None = None,
) -> MetricFact:
    dimensions = {
        "page" if connector == "google_search_console" else "landing_page": page,
        "query" if connector == "google_search_console" else "search_term": term,
    }
    if service_card_id is not None:
        dimensions["service_card_id"] = service_card_id
    return MetricFact(
        name=name,
        value=value,
        period="last_28_days",
        source_connector=connector,
        evidence_id=evidence_id,
        dimensions=dimensions,
        collected_at=datetime(2026, 7, 15, 12, tzinfo=UTC),
    )
