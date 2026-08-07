from __future__ import annotations

from typing import Literal

import pytest

from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefMeasurementPlan,
    ContentSalesBriefSourceFact,
)
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.inventory.records import ContentInventoryRecord, ContentInventoryResolution
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.planning import input_sources
from wilq.content.planning.dynamic_input import build_content_planning_input_from_components
from wilq.content.workflow.demand_evidence import (
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.schemas import ContentFreshnessAssessment, Evidence, FreshnessState, MetricFact

PAGE = "https://www.ekologus.pl/usluga/"


@pytest.mark.parametrize(
    ("gsc_query", "expected_status"),
    [
        ("gospodarka odpadami", "used"),
        ("usługa dla firm", "blocked"),
    ],
)
def test_ahrefs_gap_source_is_used_only_with_exact_gsc_cross_source_match(
    monkeypatch: pytest.MonkeyPatch,
    gsc_query: str,
    expected_status: Literal["used", "blocked"],
) -> None:
    monkeypatch.setattr(
        input_sources,
        "list_evidence_by_ids",
        lambda _: [
            Evidence(
                id="ev_wp",
                source_connector="wordpress_ekologus",
                source_type="metric_fact",
                source_id="wp_page",
                freshness=FreshnessState(state="fresh"),
                summary="Publiczne inventory WordPress.",
            )
        ],
    )
    ahrefs_fact = MetricFact(
        name="ahrefs_content_gap_count",
        value=1,
        period="current",
        source_connector="ahrefs",
        evidence_id="ev_ahrefs_gap",
        dimensions={
            "gap_type": "content_gap",
            "keyword": "gospodarka odpadami",
            "competitor_domain": "example.com",
        },
    )
    item = _work_item(
        metric_facts=[
            ahrefs_fact,
            MetricFact(
                name="impressions",
                value=10,
                period="last_28_days",
                source_connector="google_search_console",
                evidence_id="ev_gsc_cross_source",
                dimensions={"query": gsc_query, "page": PAGE},
            ),
        ]
    )
    result = build_content_planning_input_from_components(
        item=item,
        service_profile=_service_profile(),
        inventory_resolution=_inventory_resolution(),
        brief=_brief(ahrefs_fact),
        draft=ContentDraftPackage.model_construct(),
        baseline_proposal=ContentPlanningProposal.model_construct(
            search_demand=_demand(),
            cta_direction="Opisz sytuację firmy.",
        ),
        freshness=ContentFreshnessAssessment(
            state="fresh",
            requires_refresh=False,
            summary="Źródła są aktualne.",
            next_step="Użyj aktualnych źródeł.",
        ),
        claim_ledger=ContentClaimLedger(id="claim_ledger", work_item_id=item.id),
        service_card_id="service_card",
    )

    assert result.planning_input is not None
    assessment = next(
        item
        for item in result.planning_input.source_assessments
        if item.source == "ahrefs"
    )
    assert assessment.status == expected_status
    assert assessment.evidence_ids == ["ev_ahrefs_gap"]
    if expected_status == "used":
        assert "dokładny, cross-source sygnał" in assessment.reason
        assert "nie metrykę ruchu" in assessment.reason
    else:
        assert "bez exact cross-source matchu" in assessment.reason


def _work_item(*, metric_facts: list[MetricFact]) -> ContentWorkItem:
    return ContentWorkItem(
        id="content_work_item_service",
        topic="Usługa",
        source_public_url=PAGE,
        final_canonical_url=PAGE,
        wordpress_title_or_h1="Usługa dla firm",
        wordpress_section_headings=["Zakres usługi"],
        wordpress_content_summary="Istniejąca treść.",
        wordpress_content_text="Pełny materiał z the_content.",
        wordpress_content_word_count=300,
        wordpress_content_inventory_status="available",
        wordpress_content_source_kind="rendered_html",
        wordpress_content_extraction_region="main_or_article_visible_text",
        wordpress_content_material_confidence="source_bound",
        wordpress_content_source_field_lineage=["public_html.main_or_article"],
        source_connectors=["wordpress_ekologus", "google_search_console", "ahrefs"],
        metric_facts=metric_facts,
    )


def _inventory_resolution() -> ContentInventoryResolution:
    record = ContentInventoryRecord(
        id="inventory_service",
        url=PAGE,
        final_canonical_url=PAGE,
        source_connectors=["wordpress_ekologus", "google_search_console"],
        evidence_ids=["ev_wp", "ev_gsc"],
    )
    return ContentInventoryResolution(
        status="resolved",
        recommended_mode="preserve",
        records=[record],
        source_connectors=record.source_connectors,
        evidence_ids=record.evidence_ids,
        next_step="Zachowaj stronę.",
    )


def _service_profile() -> ContentWorkItemServiceProfileContext:
    candidate = ContentWorkItemServiceCandidate(
        service_card_id="service_card",
        service_label="Usługa",
        lifecycle_status="approved_current",
        lifecycle_label="Zatwierdzona",
        matched_terms=["usługa"],
        match_reasons=["Dokładny temat"],
        recommended=True,
    )
    return ContentWorkItemServiceProfileContext.model_construct(
        service_card_id="service_card",
        service_label="Usługa",
        service_selection_confirmed=True,
        service_candidates=[candidate],
        source_connectors=["public_site"],
        evidence_ids=["ev_service"],
    )


def _brief(ahrefs_fact: MetricFact) -> ContentSalesBrief:
    return ContentSalesBrief.model_construct(
        final_canonical_url=PAGE,
        target_reader="Firma",
        buyer_problem="Nie zna zakresu.",
        buyer_trigger="Potrzebuje wsparcia.",
        search_intent="informacyjna",
        source_facts=[
            ContentSalesBriefSourceFact(
                evidence_id=ahrefs_fact.evidence_id,
                source_connector="ahrefs",
                summary="Ahrefs wskazuje lukę dla frazy gospodarka odpadami.",
            )
        ],
        knowledge_card_ids=["service_card"],
        measurement_plan=ContentSalesBriefMeasurementPlan.model_construct(
            metrics_to_watch=["gsc_clicks"],
            baseline_evidence_ids=["ev_gsc"],
            earliest_verdict_note="Porównaj pełne okna.",
            success_claim_rule="Nie claimuj bez zamkniętego okna.",
        ),
    )


def _demand() -> ContentSearchDemandEvidence:
    row = ContentSearchDemandRow(
        source_kind="gsc_query",
        source_connector="google_search_console",
        term="usługa dla firm",
        page=PAGE,
        landing_match_tiers=["exact"],
        alignment_basis="gsc_exact_page",
        section_mapping_status="page_only",
        period="last_28_days",
        freshness="fresh",
        evidence_ids=["ev_gsc"],
    )
    return ContentSearchDemandEvidence(
        status="available",
        gsc_query_rows=[row],
        source_connectors=["google_search_console"],
        evidence_ids=["ev_gsc"],
        optional_ads_status="not_exactly_mapped",
        safe_next_step="Użyj dokładnych danych GSC.",
    )
