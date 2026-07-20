from __future__ import annotations

from datetime import UTC, datetime
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
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
    _resolved_inventory_section_headings,
    build_content_planning_input_from_components,
    content_planning_input_summary,
    planning_generation_blockers,
)
from wilq.content.planning.generated_proposal_turn import (
    compact_planning_input_for_model,
)
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    ContentPlanningInventorySection,
    ContentPlanningSourceAssessment,
    build_planning_inventory,
    build_source_assessments,
    build_source_facts,
    usable_query_portfolio,
)
from wilq.content.workflow.demand_evidence import (
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.schemas import (
    ConnectorCoveredWindow,
    ConnectorQualityState,
    ConnectorSettlementState,
    ContentFreshnessAssessment,
    Evidence,
    FreshnessState,
    MetricFact,
)

PAGE = "https://www.ekologus.pl/usluga/"


def test_model_planning_envelope_compacts_repeated_query_lineage_without_dropping_rows() -> None:
    row = ContentSearchDemandRow(
        source_kind="gsc_query",
        source_connector="google_search_console",
        term="gospodarka odpadami",
        page=PAGE,
        section_mapping_status="page_only",
        period="2026-06",
        freshness="fresh",
        evidence_ids=[f"ev_{index}" for index in range(8)],
        impressions=120,
    )
    demand = ContentSearchDemandEvidence(
        status="available",
        gsc_query_rows=[row, row.model_copy(update={"term": "odpady"})],
        optional_ads_status="not_exactly_mapped",
        safe_next_step="Użyj tylko dokładnych danych.",
    )
    planning_input = ContentPlanningInput.model_construct(query_portfolio=demand)

    compact, coverage = compact_planning_input_for_model(planning_input)

    assert coverage == {"rows_available": 2, "rows_included": 2}
    assert len(compact["query_portfolio"]["gsc_query_rows"][0]["evidence_ids"]) == 3
    assert [row["term"] for row in compact["query_portfolio"]["gsc_query_rows"]] == [
        "gospodarka odpadami",
        "odpady",
    ]
    assert planning_input.query_portfolio.gsc_query_rows[0].evidence_ids == [
        f"ev_{index}" for index in range(8)
    ]


def test_ga4_page_signal_accepts_exact_landing_and_tracking_only_variants() -> None:
    item = ContentWorkItem.model_construct(
        metric_facts=[
            MetricFact(
                name="engaged_sessions",
                value=12,
                period="last_28_days",
                source_connector="google_analytics_4",
                evidence_id="ev_ga4",
                dimensions={"landing_page": "https://www.ekologus.pl/usluga/?utm_source=google"},
            )
        ]
    )

    evidence_ids, tiers = input_sources._ga4_page_signal(item, PAGE)

    assert evidence_ids == ["ev_ga4"]
    assert tiers == ["tracking_only"]


def test_model_planning_envelope_drops_inventory_navigation_and_dated_noise() -> None:
    planning_input = ContentPlanningInput.model_construct(
        inventory=ContentPlanningInventory(
            status="available",
            content_status="available",
            acf_section_status="missing",
            sections=[
                ContentPlanningInventorySection(
                    section_id="s1", heading="Kto musi złożyć wniosek?", evidence_ids=["ev_wp"]
                ),
                ContentPlanningInventorySection(
                    section_id="s2",
                    heading="13 marca 2020 w Bielsku-Białej",
                    evidence_ids=["ev_wp"],
                ),
                ContentPlanningInventorySection(
                    section_id="s3",
                    heading="Może Cię również zainteresować",
                    evidence_ids=["ev_wp"],
                ),
            ],
        )
    )

    compact, _ = compact_planning_input_for_model(planning_input)

    assert [section["heading"] for section in compact["inventory"]["sections"]] == [
        "Kto musi złożyć wniosek?"
    ]
    assert [section.heading for section in planning_input.inventory.sections] == [
        "Kto musi złożyć wniosek?",
        "13 marca 2020 w Bielsku-Białej",
        "Może Cię również zainteresować",
    ]


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
        wordpress_content_text="Pełny materiał z the_content.",
        wordpress_content_word_count=300,
        wordpress_content_inventory_status="available",
        wordpress_content_source_kind="rendered_html",
        wordpress_content_extraction_region="main_or_article_visible_text",
        wordpress_content_material_confidence="review_required",
        wordpress_content_source_field_lineage=["public_html.main_or_article"],
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
    assert inventory.content_text == "Pełny materiał z the_content."
    assert inventory.extraction_region == "main_or_article_visible_text"
    assert inventory.material_confidence == "review_required"
    assert inventory.source_field_lineage == ["public_html.main_or_article"]

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


def test_content_headings_remain_inventory_when_acf_has_fields_but_no_sections(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    item = item.model_copy(
        update={
            "wordpress_acf_section_inventory_status": "available",
            "wordpress_acf_section_headings": [],
            "wordpress_acf_field_names": ["hero"],
        }
    )

    inventory = build_planning_inventory(item, resolution)

    assert inventory.status == "available"
    assert inventory.acf_field_names == ["hero"]
    assert [section.heading for section in inventory.sections] == ["Zakres usługi"]


def test_the_content_only_inventory_is_plannable_without_structural_headings(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    item = item.model_copy(
        update={
            "wordpress_section_headings": [],
            "wordpress_acf_section_inventory_status": "missing",
            "wordpress_acf_section_headings": [],
            "wordpress_content_inventory_status": "available",
        }
    )

    inventory = build_planning_inventory(item, resolution)

    assert inventory.status == "available"
    assert inventory.content_status == "available"
    assert inventory.sections == []
    assert inventory.content_text == "Pełny materiał z the_content."


def test_query_mapping_uses_resolved_acf_inventory_when_sections_are_exposed(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    item = item.model_copy(
        update={
            "wordpress_section_headings": ["Stary the_content H2"],
            "wordpress_acf_section_inventory_status": "available",
            "wordpress_acf_section_headings": ["Nowy blok ACF", "Dowody i zakres"],
        }
    )

    assert _resolved_inventory_section_headings(item, resolution) == [
        "Nowy blok ACF",
        "Dowody i zakres",
    ]


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
    assert statuses["google_ads"] == "missing"
    assert statuses["merchant"] == "not_applicable"
    assert statuses["localo"] == "not_applicable"
    result = _build_result(
        item, resolution, brief, service_profile, baseline, _freshness([])
    )
    assert "wordpress_material_review_required" in {
        blocker.code for blocker in result.blockers
    }
    assert "wordpress_material_review_required" not in {
        blocker.code for blocker in planning_generation_blockers(result.blockers)
    }
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


def test_ads_source_assessment_explains_service_review_blocker(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, _, inventory = source_context
    brief, service_profile, _ = _planning_models(_demand())
    row = ContentSearchDemandRow(
        source_kind="ads_search_term",
        source_connector="google_ads",
        term="usługa środowiskowa",
        page=PAGE,
        landing_match_tiers=["exact"],
        service_binding_status="review_required",
        section_mapping_status="page_only",
        period="last_30_days",
        freshness="fresh",
        evidence_ids=["ev_ads_exact"],
        clicks=2,
        impressions=10,
    )
    demand = _demand().model_copy(
        update={
            "ads_term_rows": [row],
            "optional_ads_status": "exact_rows_available",
            "optional_ads_evidence_ids": ["ev_ads_exact"],
        }
    )

    assessments = build_source_assessments(
        item=item,
        inventory=inventory,
        service_profile=service_profile,
        freshness=_freshness([]),
        brief=brief,
        demand=demand,
        service_lifecycle="approved_current",
    )
    ads = next(assessment for assessment in assessments if assessment.source == "google_ads")

    assert ads.status == "blocked"
    assert "zatwierdzona i aktualna" in ads.reason
    assert ads.landing_match_tiers == ["exact"]


@pytest.mark.parametrize("binding_status", ["unbound", "ambiguous"])
def test_ads_source_assessment_explains_unresolved_service_binding(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
    binding_status: Literal["unbound", "ambiguous"],
) -> None:
    item, _, inventory = source_context
    brief, service_profile, _ = _planning_models(_demand())
    row = ContentSearchDemandRow(
        source_kind="ads_search_term",
        source_connector="google_ads",
        term="usługa środowiskowa",
        page=PAGE,
        landing_match_tiers=["exact"],
        service_binding_status=binding_status,
        section_mapping_status="page_only",
        period="last_30_days",
        freshness="fresh",
        evidence_ids=["ev_ads_exact"],
    )
    demand = _demand().model_copy(
        update={
            "ads_term_rows": [row],
            "optional_ads_status": "exact_rows_available",
            "optional_ads_evidence_ids": ["ev_ads_exact"],
        }
    )

    ads = next(
        assessment
        for assessment in build_source_assessments(
            item=item,
            inventory=inventory,
            service_profile=service_profile,
            freshness=_freshness([]),
            brief=brief,
            demand=demand,
            service_lifecycle="approved_current",
        )
        if assessment.source == "google_ads"
    )

    assert ads.status == "blocked"
    assert "jednego rozstrzygniętego powiązania" in ads.reason


def test_owner_reviewed_rendered_content_unblocks_material_gate_without_replanning(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    brief, service_profile, baseline = _planning_models(_demand())
    blocked = _build_result(
        item, resolution, brief, service_profile, baseline, _freshness([])
    )
    reviewed = build_content_planning_input_from_components(
        item=item,
        service_profile=service_profile,
        inventory_resolution=resolution,
        brief=brief,
        draft=ContentDraftPackage.model_construct(),
        baseline_proposal=baseline,
        freshness=_freshness([]),
        claim_ledger=ContentClaimLedger(id="claim_ledger", work_item_id=item.id),
        service_card_id="service_card",
        existing_content_material_reviewed=True,
    )

    assert "wordpress_material_review_required" in {
        blocker.code for blocker in blocked.blockers
    }
    assert "wordpress_material_review_required" not in {
        blocker.code for blocker in reviewed.blockers
    }
    assert blocked.planning_input is not None
    assert reviewed.planning_input is not None
    assert (
        blocked.planning_input.planning_input_digest
        == reviewed.planning_input.planning_input_digest
    )


def test_source_quality_is_part_of_planning_lineage_and_digest(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    brief, service_profile, baseline = _planning_models(_demand())
    freshness = _freshness([]).model_copy(
        update={
            "connector_refresh_run_ids": {"google_search_console": "refresh-gsc-1"},
            "connector_covered_windows": {
                "google_search_console": ConnectorCoveredWindow(
                    date_start="2026-07-15",
                    date_end="2026-07-15",
                    completeness="partial_possible",
                )
            },
            "connector_settlement_states": {
                "google_search_console": ConnectorSettlementState.settled
            },
            "connector_quality_states": {
                "google_search_console": ConnectorQualityState.partial
            },
            "connector_quality_caveats": {
                "google_search_console": ["Dane mogą być częściowe."]
            },
        }
    )
    assessments = build_source_assessments(
        item=item,
        inventory=build_planning_inventory(item, resolution),
        service_profile=service_profile,
        freshness=freshness,
        brief=brief,
        demand=baseline.search_demand,
        service_lifecycle="approved_current",
    )
    gsc = next(assessment for assessment in assessments if assessment.source == "gsc")
    assert gsc.refresh_run_id == "refresh-gsc-1"
    assert gsc.covered_window.date_start == "2026-07-15"
    assert gsc.quality_state == ConnectorQualityState.partial
    assert gsc.interpretation_caveats == ["Dane mogą być częściowe."]

    first = _build_result(item, resolution, brief, service_profile, baseline, freshness)
    changed = freshness.model_copy(
        update={
            "connector_quality_states": {
                "google_search_console": ConnectorQualityState.verified
            }
        }
    )
    second = _build_result(item, resolution, brief, service_profile, baseline, changed)
    assert first.planning_input is not None
    assert second.planning_input is not None
    assert first.planning_input.planning_input_digest != second.planning_input.planning_input_digest


def test_metric_comparison_contract_is_persisted_in_planning_digest(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    brief, service_profile, baseline = _planning_models(_demand())
    facts = [
        MetricFact(
            name=name,
            value=value,
            period=period,
            source_connector="google_search_console",
            evidence_id=evidence,
            dimensions={"page": PAGE, "query": "usługa"},
            collected_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        for period, evidence, values in [
            ("2026-07-01/2026-07-07", "ev-baseline", {"clicks": 1, "impressions": 10}),
            ("2026-07-08/2026-07-14", "ev-observation", {"clicks": 2, "impressions": 20}),
        ]
        for name, value in values.items()
    ]
    with_comparison = item.model_copy(update={"metric_facts": facts})
    first = _build_result(
        with_comparison, resolution, brief, service_profile, baseline, _freshness([])
    )
    changed = with_comparison.model_copy(
        update={
            "metric_facts": [
                facts[0],
                facts[1],
                facts[2].model_copy(update={"value": 99}),
                facts[3],
            ]
        }
    )
    second = _build_result(changed, resolution, brief, service_profile, baseline, _freshness([]))
    assert first.planning_input is not None
    assert second.planning_input is not None
    gsc = next(
        item
        for item in first.planning_input.metric_comparisons
        if item.source_connector == "google_search_console"
    )
    assert gsc.status == "available"
    assert first.planning_input.planning_input_digest != second.planning_input.planning_input_digest


def test_planning_input_preserves_source_fact_and_material_lineage(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    brief, service_profile, baseline = _planning_models(_demand())
    brief = brief.model_copy(
        update={
            "source_facts": [
                ContentSalesBriefSourceFact(
                    evidence_id="ev_service",
                    source_connector="public_site",
                    summary="Zatwierdzony fakt o usłudze.",
                    source_fact_ids=["ekologus_public_consulting_outsourcing_offer_2026_07_01"],
                    source_material_ids=["ekologus_material_portfolio"],
                )
            ]
        }
    )

    result = _build_result(item, resolution, brief, service_profile, baseline, _freshness([]))

    assert result.planning_input is not None
    assert result.planning_input.source_facts[0].source_fact_ids == [
        "ekologus_public_consulting_outsourcing_offer_2026_07_01"
    ]
    assert result.planning_input.source_facts[0].source_material_ids == [
        "ekologus_material_portfolio"
    ]
    summary = content_planning_input_summary(result.planning_input)
    assert summary.source_fact_ids == [
        "ekologus_public_consulting_outsourcing_offer_2026_07_01"
    ]
    assert summary.source_material_ids == ["ekologus_material_portfolio"]


def test_service_profile_projection_uses_the_approved_fact_summary() -> None:
    brief = ContentSalesBrief.model_construct(
        source_facts=[], knowledge_card_ids=["ekologus_service_bdo_reporting"]
    )
    service_profile = ContentWorkItemServiceProfileContext.model_construct(
        service_label="BDO",
        source_fact_ids=["ekologus_public_bdo_faq_2026_07_01"],
        source_material_ids=["ekologus_material_kb015"],
        knowledge_card_ids=["ekologus_service_bdo_reporting"],
        source_connectors=["public_site"],
        evidence_ids=["ev_content_service_profile_source_facts"],
    )
    assessments = [
        ContentPlanningSourceAssessment(
            source=name,
            status="used" if name == "service_profile" else "not_applicable",
            reason="test",
        )
        for name in (
            "wordpress", "service_profile", "gsc", "ga4", "google_ads",
            "ahrefs", "keyword_planner", "merchant", "localo", "social",
        )
    ]

    facts = build_source_facts(brief, assessments, service_profile)

    profile_fact = next(fact for fact in facts if fact.source_fact_ids)
    assert profile_fact.summary.startswith("Publiczny artykuł Ekologus")
    assert profile_fact.source_connector == "public_site"
    assert profile_fact.evidence_ids == ["ev_content_service_profile_source_facts"]
    assert profile_fact.source_fact_ids == ["ekologus_public_bdo_faq_2026_07_01"]
    assert profile_fact.source_material_ids == ["ekologus_material_kb015"]


def test_planning_blocks_an_unresolved_service_fact_id(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    brief, service_profile, baseline = _planning_models(_demand())
    unresolved_profile = service_profile.model_copy(
        update={"source_fact_ids": ["service_fact_not_in_approved_registry"]}
    )

    result = _build_result(
        item,
        resolution,
        brief,
        unresolved_profile,
        baseline,
        _freshness([]),
    )

    assert "missing_approved_service_fact" in {blocker.code for blocker in result.blockers}
    assert result.planning_input is not None
    assert all(
        "service_fact_not_in_approved_registry" not in fact.source_fact_ids
        for fact in result.planning_input.source_facts
    )
    assert all(
        fact.fact_id != "planning_service_fact_01"
        for fact in result.planning_input.source_facts
    )


def test_planning_blocks_rewrite_when_only_headings_are_available(
    source_context: tuple[ContentWorkItem, ContentInventoryResolution, ContentPlanningInventory],
) -> None:
    item, resolution, _ = source_context
    brief, service_profile, baseline = _planning_models(_demand())
    headings_only = item.model_copy(
        update={
            "wordpress_content_summary": None,
            "wordpress_content_word_count": None,
            "wordpress_content_inventory_status": "missing",
        }
    )

    result = _build_result(
        headings_only,
        resolution,
        brief,
        service_profile,
        baseline,
        _freshness([]),
    )

    assert "missing_wordpress_full_inventory" in {
        blocker.code for blocker in result.blockers
    }


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
