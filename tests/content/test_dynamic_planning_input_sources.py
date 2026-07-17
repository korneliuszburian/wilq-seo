from __future__ import annotations

import pytest

from wilq.content.briefs.sales import ContentSalesBrief, ContentSalesBriefMeasurementPlan
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.inventory.records import ContentInventoryRecord, ContentInventoryResolution
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.planning import input_sources
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputBuildResult,
    build_content_planning_input_from_components,
)
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    build_planning_inventory,
    build_source_assessments,
    usable_query_portfolio,
)
from wilq.content.workflow.demand_evidence import (
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.schemas import ContentFreshnessAssessment, Evidence, FreshnessState

PAGE = "https://www.ekologus.pl/usluga/"


@pytest.fixture
def source_context(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory]:
    evidence = Evidence(
        id="ev_wp",
        source_connector="wordpress_ekologus",
        source_type="metric_fact",
        source_id="wp_page",
        freshness=FreshnessState(state="fresh"),
        summary="Publiczne inventory WordPress.",
    )
    monkeypatch.setattr(input_sources, "list_evidence_by_ids", lambda _: [evidence])
    item = ContentWorkItem(
        id="content_work_item_service",
        topic="Usługa",
        source_public_url=PAGE,
        final_canonical_url=PAGE,
        wordpress_title_or_h1="Usługa dla firm",
        wordpress_section_headings=["Zakres usługi"],
        wordpress_content_summary="Istniejąca treść.",
        wordpress_content_word_count=300,
        source_connectors=["wordpress_ekologus", "google_search_console"],
    )
    record = ContentInventoryRecord(
        id="inventory_service",
        url=PAGE,
        final_canonical_url=PAGE,
        source_connectors=["wordpress_ekologus", "google_search_console"],
        evidence_ids=["ev_wp", "ev_gsc"],
    )
    resolution = ContentInventoryResolution(
        status="resolved",
        recommended_mode="preserve",
        records=[record],
        source_connectors=record.source_connectors,
        evidence_ids=record.evidence_ids,
        next_step="Zachowaj stronę.",
    )
    return item, resolution, build_planning_inventory(item, resolution)


def test_planning_inventory_requires_one_exact_wordpress_record(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, inventory = source_context
    assert inventory.status == "available"
    assert inventory.evidence_ids == ["ev_wp"]
    assert inventory.source_connectors == ["wordpress_ekologus"]
    assert inventory.landing_match_tiers == ["exact"]

    exact_record = resolution.records[0]
    mismatch = exact_record.model_copy(
        update={"url": f"{PAGE}obcy/", "final_canonical_url": f"{PAGE}obcy/"}
    )
    assert build_planning_inventory(
        item,
        resolution.model_copy(update={"records": [mismatch]}),
    ).status == "missing"
    duplicate = exact_record.model_copy(update={"id": "inventory_service_duplicate"})
    assert build_planning_inventory(
        item,
        resolution.model_copy(update={"records": [exact_record, duplicate]}),
    ).status == "missing"


def test_planning_readiness_uses_connector_freshness_not_global_state(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, inventory = source_context
    demand = _demand()
    stale_gsc = _freshness(["google_search_console"])
    brief, service_profile, baseline = _planning_models(demand)
    assessments = build_source_assessments(
        item=item,
        inventory=inventory,
        service_profile=service_profile,
        freshness=stale_gsc,
        brief=brief,
        demand=demand,
        service_lifecycle="approved_current",
    )
    statuses = {assessment.source: assessment.status for assessment in assessments}
    assert statuses["wordpress"] == "used"
    assert statuses["gsc"] == "stale"
    assert usable_query_portfolio(demand, assessments).gsc_query_rows == []

    irrelevant = _build_result(
        item, resolution, brief, service_profile, baseline, _freshness(["linkedin"])
    )
    assert "stale_planning_sources" not in {blocker.code for blocker in irrelevant.blockers}
    relevant = _build_result(
        item, resolution, brief, service_profile, baseline, stale_gsc
    )
    assert "stale_planning_sources" in {blocker.code for blocker in relevant.blockers}

    blocked_ads = demand.model_copy(
        update={
            "optional_ads_status": "blocked",
            "optional_ads_evidence_ids": ["ev_ads_blocked"],
            "optional_ads_blockers": ["ads_search_term_landing_invalid"],
        }
    )
    blocked_assessments = build_source_assessments(
        item=item,
        inventory=inventory,
        service_profile=service_profile,
        freshness=_freshness([]),
        brief=brief,
        demand=blocked_ads,
        service_lifecycle="approved_current",
    )
    ads_assessment = next(
        assessment
        for assessment in blocked_assessments
        if assessment.source == "google_ads"
    )
    assert ads_assessment.status == "blocked"
    assert ads_assessment.evidence_ids == ["ev_ads_blocked"]


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
        safe_next_step="Odśwież GSC.",
    )


def _freshness(stale_connectors: list[str]) -> ContentFreshnessAssessment:
    return ContentFreshnessAssessment(
        state="stale",
        requires_refresh=True,
        stale_connector_ids=stale_connectors,
        summary="Wybrane źródło wymaga odświeżenia.",
        next_step="Odśwież wskazane źródło.",
    )


def _planning_models(
    demand: ContentSearchDemandEvidence,
) -> tuple[ContentSalesBrief, ContentWorkItemServiceProfileContext, ContentPlanningProposal]:
    candidate = ContentWorkItemServiceCandidate(
        service_card_id="service_card",
        service_label="Usługa",
        lifecycle_status="approved_current",
        lifecycle_label="Zatwierdzona",
        matched_terms=["usługa"],
        match_reasons=["Dokładny temat"],
        recommended=True,
    )
    profile = ContentWorkItemServiceProfileContext.model_construct(
        service_card_id="service_card",
        service_label="Usługa",
        service_selection_confirmed=True,
        service_candidates=[candidate],
        source_connectors=["public_site"],
        evidence_ids=["ev_service"],
    )
    brief = ContentSalesBrief.model_construct(
        final_canonical_url=PAGE,
        target_reader="Firma",
        buyer_problem="Nie zna zakresu.",
        buyer_trigger="Potrzebuje wsparcia.",
        search_intent="informacyjna",
        source_facts=[],
        knowledge_card_ids=["service_card"],
        measurement_plan=ContentSalesBriefMeasurementPlan.model_construct(
            metrics_to_watch=["gsc_clicks"],
            baseline_evidence_ids=["ev_gsc"],
            earliest_verdict_note="Porównaj pełne okna.",
            success_claim_rule="Nie claimuj bez zamkniętego okna.",
        ),
    )
    baseline = ContentPlanningProposal.model_construct(
        search_demand=demand,
        cta_direction="Opisz sytuację firmy.",
    )
    return brief, profile, baseline


def _build_result(
    item: ContentWorkItem,
    resolution: ContentInventoryResolution,
    brief: ContentSalesBrief,
    profile: ContentWorkItemServiceProfileContext,
    baseline: ContentPlanningProposal,
    freshness: ContentFreshnessAssessment,
) -> ContentPlanningInputBuildResult:
    return build_content_planning_input_from_components(
        item=item,
        service_profile=profile,
        inventory_resolution=resolution,
        brief=brief,
        draft=ContentDraftPackage.model_construct(),
        baseline_proposal=baseline,
        freshness=freshness,
        claim_ledger=ContentClaimLedger(id="claim_ledger", work_item_id=item.id),
        service_card_id="service_card",
    )
