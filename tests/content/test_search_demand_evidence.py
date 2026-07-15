from __future__ import annotations

from datetime import UTC, datetime

from wilq.content.drafts.package import ContentDraftPackage, ContentDraftSection
from wilq.content.workflow.demand_evidence import build_content_search_demand_evidence
from wilq.schemas import ContentFreshnessAssessment, MetricFact


def test_search_demand_requires_exact_page_service_and_section_evidence() -> None:
    page = "https://www.ekologus.pl/bdo/"
    service_card_id = "service_bdo"
    collected_at = datetime(2026, 7, 15, 12, tzinfo=UTC)
    facts = [
        _fact("google_search_console", "impressions", 120, "ev_gsc", page, "bdo odpady"),
        _fact("google_search_console", "clicks", 12, "ev_gsc", page, "bdo odpady"),
        _fact("google_search_console", "ctr", 0.1, "ev_gsc", page, "bdo odpady"),
        _fact("google_search_console", "average_position", 6.4, "ev_gsc", page, "bdo odpady"),
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
            collected_at=collected_at,
        ),
    ]
    draft = ContentDraftPackage(
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
                heading="Kontakt",
                purpose="Podaj następny krok.",
                evidence_ids=["ev_service"],
            ),
        ],
    )

    evidence = build_content_search_demand_evidence(
        metric_facts=facts,
        source_page=page,
        final_canonical_url=page,
        service_card_id=service_card_id,
        draft=draft,
        freshness=ContentFreshnessAssessment(
            state="fresh",
            requires_refresh=False,
            summary="Źródła aktualne.",
            next_step="Użyj dowodów.",
        ),
    )

    assert evidence.status == "available"
    assert [row.term for row in evidence.gsc_query_rows] == ["bdo odpady"]
    assert evidence.gsc_query_rows[0].model_dump(
        include={"impressions", "clicks", "ctr", "average_position", "section_headings"}
    ) == {
        "impressions": 120,
        "clicks": 12,
        "ctr": 0.1,
        "average_position": 6.4,
        "section_headings": ["Obowiązki BDO"],
    }
    assert [row.evidence_ids for row in evidence.ads_term_rows] == [["ev_ads_exact"]]
    assert evidence.keyword_planner_rows == []
    assert evidence.evidence_ids == ["ev_gsc", "ev_ads_exact"]
    assert evidence.optional_ads_status == "exact_rows_available"


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
