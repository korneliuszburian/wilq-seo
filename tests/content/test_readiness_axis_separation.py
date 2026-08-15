from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import wilq.content.planning.input_sources as input_sources
import wilq.content.workflow.pipeline_steps.decision_context as decision_context_module
from wilq.content.briefs.sales import ContentSalesBrief, ContentSalesBriefMeasurementPlan
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.inventory.records import ContentInventoryRecord, ContentInventoryResolution
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
)
from wilq.content.planning.dynamic_input import (
    build_content_planning_input_from_components,
    content_planning_input_readiness,
)
from wilq.content.planning.input_summary import ContentPlanningInputSummary
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.demand_evidence import (
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.pipeline_steps.queue import (
    build_content_work_item_queue_candidate,
    build_content_work_item_queue_response,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryMaterialResponse,
)
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    ContentFreshnessAssessment,
    Evidence,
    FreshnessState,
)

WORK_ITEM_ID = "content_work_item_readiness_axes"
PAGE_URL = "https://www.ekologus.pl/usluga/"


def test_queue_freshness_changes_evidence_blocker_without_changing_disposition() -> None:
    decision = _content_decision()
    fresh = _freshness()
    stale = _freshness(stale_connector_ids=["google_search_console"])

    fresh_candidate = build_content_work_item_queue_candidate(decision, fresh)
    stale_candidate = build_content_work_item_queue_candidate(decision, stale)
    fresh_queue = build_content_work_item_queue_response(
        _diagnostics(decision, fresh),
        minimum_actionable_candidates=1,
    )
    stale_queue = build_content_work_item_queue_response(
        _diagnostics(decision, stale),
        minimum_actionable_candidates=1,
    )

    assert fresh_candidate.recommended_mode == stale_candidate.recommended_mode == "refresh"
    assert fresh_candidate.model_dump(
        exclude={"blockers", "freshness_assessment", "safe_next_step"}
    ) == stale_candidate.model_dump(
        exclude={"blockers", "freshness_assessment", "safe_next_step"}
    )
    assert fresh_queue.candidates[0].recommended_mode == "refresh"
    assert stale_queue.candidates[0].recommended_mode == "refresh"
    assert fresh_queue.actionable_candidate_count == stale_queue.actionable_candidate_count == 1
    assert "content_sources_require_refresh" not in {
        blocker.code for blocker in fresh_candidate.blockers
    }
    assert "content_sources_require_refresh" in {
        blocker.code for blocker in stale_candidate.blockers
    }
    assert "content_sources_require_refresh" not in {
        blocker.code for blocker in fresh_queue.blockers
    }
    assert "content_sources_require_refresh" in {
        blocker.code for blocker in stale_queue.blockers
    }
    assert fresh_candidate.safe_next_step == decision.next_step
    assert stale_candidate.safe_next_step == stale.next_step
    assert fresh_queue.queue_status == "ready"
    assert stale_queue.queue_status == "blocked"


def test_decision_context_freshness_changes_only_the_evidence_axis_and_safe_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freshness = {"value": _freshness(stale_connector_ids=["google_search_console"])}
    _patch_decision_context(monkeypatch, freshness)

    stale_context = decision_context_module.build_content_decision_context(WORK_ITEM_ID)
    freshness["value"] = _freshness()
    fresh_context = decision_context_module.build_content_decision_context(WORK_ITEM_ID)

    assert stale_context is not None
    assert fresh_context is not None
    assert stale_context.work_item_id == fresh_context.work_item_id == WORK_ITEM_ID
    assert stale_context.object_readiness == fresh_context.object_readiness
    assert stale_context.decision_disposition == fresh_context.decision_disposition
    assert stale_context.delivery_capability == fresh_context.delivery_capability
    assert stale_context.measurement_target == fresh_context.measurement_target
    assert stale_context.evidence_readiness.status == "refresh_required"
    assert stale_context.evidence_readiness.blocker_codes == [
        "connector:google_search_console"
    ]
    assert fresh_context.evidence_readiness.status == "ready"
    assert fresh_context.evidence_readiness.blocker_codes == []
    assert (
        stale_context.next_safe_action.kind,
        stale_context.next_safe_action.connector_id,
    ) == ("refresh_connector", "google_search_console")
    assert (
        fresh_context.next_safe_action.kind,
        fresh_context.next_safe_action.connector_id,
    ) == ("open_workspace", None)


def test_planning_freshness_changes_only_source_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    components = _planning_components(monkeypatch)
    fresh_result = build_content_planning_input_from_components(
        **components,
        freshness=_freshness(),
    )
    stale = _freshness(stale_connector_ids=["google_search_console"])
    stale_result = build_content_planning_input_from_components(
        **components,
        freshness=stale,
    )

    fresh_readiness = content_planning_input_readiness(fresh_result)
    stale_readiness = content_planning_input_readiness(stale_result)

    assert fresh_readiness.status == "ready"
    assert stale_readiness.status == "blocked"
    assert fresh_readiness.work_item_id == stale_readiness.work_item_id == WORK_ITEM_ID
    assert fresh_readiness.input_summary is not None
    assert stale_readiness.input_summary is not None
    assert _planning_object_axis(fresh_readiness.input_summary) == _planning_object_axis(
        stale_readiness.input_summary
    )
    fresh_sources = {
        assessment.source: assessment.status
        for assessment in fresh_readiness.input_summary.source_assessments
    }
    stale_sources = {
        assessment.source: assessment.status
        for assessment in stale_readiness.input_summary.source_assessments
    }
    assert fresh_sources["gsc"] == "used"
    assert stale_sources["gsc"] == "stale"
    assert fresh_sources["wordpress"] == stale_sources["wordpress"] == "used"
    assert fresh_sources["service_profile"] == stale_sources["service_profile"] == "used"
    assert fresh_readiness.blockers == []
    assert [blocker.code for blocker in stale_readiness.blockers] == [
        "stale_planning_sources"
    ]
    assert stale_readiness.safe_next_step == stale.next_step
    assert fresh_readiness.safe_next_step != stale_readiness.safe_next_step


def _content_decision() -> ContentDecisionItem:
    return ContentDecisionItem(
        id="readiness_axes",
        decision_type="refresh_or_merge",
        status="ready",
        title="Usługa dla firm",
        primary_query="usługa dla firm",
        priority=1,
        source_public_url=PAGE_URL,
        final_canonical_url=PAGE_URL,
        inventory_gate_status="confirmed_current_inventory",
        canonical_gate_status="resolved",
        duplicate_gate_status="existing_public_content_requires_refresh_or_merge",
        source_connectors=["google_search_console", "wordpress_ekologus"],
        evidence_ids=["ev_gsc_readiness_axes", "ev_wp_readiness_axes"],
        rationale="Istniejąca strona wymaga odświeżenia.",
        next_step="Przejdź do planu odświeżenia.",
    )


def _freshness(
    *,
    stale_connector_ids: list[str] | None = None,
) -> ContentFreshnessAssessment:
    stale_connector_ids = stale_connector_ids or []
    if stale_connector_ids:
        return ContentFreshnessAssessment(
            state="stale",
            state_label="dane wymagają odświeżenia",
            requires_refresh=True,
            stale_connector_ids=stale_connector_ids,
            connector_labels_requiring_refresh=["Google Search Console"],
            summary="Google Search Console wymaga odświeżenia.",
            next_step="Odśwież Google Search Console.",
        )
    return ContentFreshnessAssessment(
        state="fresh",
        state_label="dane świeże",
        requires_refresh=False,
        summary="Dowody są aktualne.",
        next_step="Przejdź do warsztatu strony.",
    )


def _diagnostics(
    decision: ContentDecisionItem,
    freshness: ContentFreshnessAssessment,
) -> ContentDiagnosticsResponse:
    return ContentDiagnosticsResponse.model_construct(
        freshness_assessment=freshness,
        decision_queue=[decision],
    )


def _patch_decision_context(
    monkeypatch: pytest.MonkeyPatch,
    freshness: dict[str, ContentFreshnessAssessment],
) -> None:
    decision = _content_decision()
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        ready_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_readiness_axes",
                work_item_id=WORK_ITEM_ID,
                url=PAGE_URL,
                path="/usluga/",
                title="Usługa dla firm",
                content_type="sitemap",
                material_status="content_and_structure",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wp_readiness_axes",
                collected_at=datetime(2026, 8, 1, tzinfo=UTC),
                content_word_count=120,
                section_count=2,
                metrics_status="available",
            )
        ],
    )
    material = ContentInventoryMaterialResponse(
        status="ready",
        url=PAGE_URL,
        source_kind="wordpress_rest",
        title="Usługa dla firm",
        content_text="Treść istniejącej strony.",
        content_word_count=120,
        section_headings=["Zakres usługi", "Kontakt"],
        evidence_id="ev_wp_readiness_axes",
        extraction_region="wordpress_rest.content",
    )
    monkeypatch.setattr(
        decision_context_module,
        "inventory_decision_for_work_item",
        lambda work_item_id, **_kwargs: decision if work_item_id == WORK_ITEM_ID else None,
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_content_inventory_catalog_cached",
        lambda: catalog,
    )
    monkeypatch.setattr(
        decision_context_module,
        "read_content_inventory_material",
        lambda _url, *, catalog: material,
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_content_freshness_assessment_fast",
        lambda **_kwargs: freshness["value"],
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_wordpress_authoring_profile",
        lambda *_args, **_kwargs: SimpleNamespace(
            authoring_target="staging",
            write_boundary=SimpleNamespace(allowed_operation="create_wordpress_draft"),
        ),
    )
    monkeypatch.setattr(
        decision_context_module,
        "build_content_work_item_service_profile_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            service_label="Usługa",
            reason="Usługa pochodzi z dopasowanej karty.",
        ),
    )


def _planning_components(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    item, inventory_resolution = _planning_content(monkeypatch)
    demand = _planning_demand()
    service_candidate, service_profile, brief = _planning_service_context()
    return {
        "item": item,
        "service_profile": service_profile,
        "inventory_resolution": inventory_resolution,
        "brief": brief,
        "draft": ContentDraftPackage.model_construct(),
        "baseline_proposal": ContentPlanningProposal.model_construct(
            search_demand=demand,
            cta_direction="Opisz sytuację firmy.",
        ),
        "claim_ledger": ContentClaimLedger(
            id="claim_ledger_readiness_axes",
            work_item_id=WORK_ITEM_ID,
        ),
        "service_card_id": service_candidate.service_card_id,
        "existing_content_material_reviewed": True,
    }


def _planning_content(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ContentWorkItem, ContentInventoryResolution]:
    wordpress_evidence = Evidence(
        id="ev_wp_readiness_axes",
        source_connector="wordpress_ekologus",
        source_type="metric_fact",
        source_id="wp_page_readiness_axes",
        freshness=FreshnessState(state="fresh"),
        summary="Publiczne inventory WordPress.",
    )
    monkeypatch.setattr(
        input_sources,
        "list_evidence_by_ids",
        lambda _evidence_ids: [wordpress_evidence],
    )
    item = ContentWorkItem(
        id=WORK_ITEM_ID,
        topic="Usługa dla firm",
        source_public_url=PAGE_URL,
        final_canonical_url=PAGE_URL,
        wordpress_title_or_h1="Usługa dla firm",
        wordpress_section_headings=["Zakres usługi"],
        wordpress_section_inventory_status="available",
        wordpress_content_summary="Istniejąca treść.",
        wordpress_content_text="Pełny materiał istniejącej strony.",
        wordpress_content_word_count=300,
        wordpress_content_inventory_status="available",
        wordpress_content_source_kind="wordpress_rest",
        wordpress_content_extraction_region="wordpress_rest.content",
        wordpress_content_material_confidence="source_bound",
        wordpress_content_source_field_lineage=["wordpress_rest.content"],
        source_connectors=["wordpress_ekologus", "google_search_console"],
        evidence_ids=["ev_wp_readiness_axes", "ev_gsc_readiness_axes"],
    )
    record = ContentInventoryRecord(
        id="inventory_readiness_axes",
        url=PAGE_URL,
        final_canonical_url=PAGE_URL,
        source_connectors=["wordpress_ekologus", "google_search_console"],
        evidence_ids=["ev_wp_readiness_axes", "ev_gsc_readiness_axes"],
    )
    inventory_resolution = ContentInventoryResolution(
        status="resolved",
        recommended_mode="preserve",
        records=[record],
        source_connectors=record.source_connectors,
        evidence_ids=record.evidence_ids,
        next_step="Zachowaj stronę.",
    )
    return item, inventory_resolution


def _planning_demand() -> ContentSearchDemandEvidence:
    return ContentSearchDemandEvidence(
        status="available",
        gsc_query_rows=[
            ContentSearchDemandRow(
                source_kind="gsc_query",
                source_connector="google_search_console",
                term="usługa dla firm",
                page=PAGE_URL,
                landing_match_tiers=["exact"],
                alignment_basis="gsc_exact_page",
                section_mapping_status="page_only",
                period="last_28_days",
                freshness="fresh",
                evidence_ids=["ev_gsc_readiness_axes"],
            )
        ],
        source_connectors=["google_search_console"],
        evidence_ids=["ev_gsc_readiness_axes"],
        optional_ads_status="not_exactly_mapped",
        safe_next_step="Użyj tylko dokładnie powiązanych danych.",
    )


def _planning_service_context() -> tuple[
    ContentWorkItemServiceCandidate,
    ContentWorkItemServiceProfileContext,
    ContentSalesBrief,
]:
    service_candidate = ContentWorkItemServiceCandidate(
        service_card_id="service_card_readiness_axes",
        service_label="Usługa",
        lifecycle_status="approved_current",
        lifecycle_label="Zatwierdzona",
        matched_terms=["usługa"],
        match_reasons=["Dokładny temat"],
        recommended=True,
    )
    service_profile = ContentWorkItemServiceProfileContext.model_construct(
        service_card_id=service_candidate.service_card_id,
        service_label=service_candidate.service_label,
        service_selection_confirmed=True,
        service_candidates=[service_candidate],
        source_connectors=["public_site"],
        evidence_ids=["ev_service_readiness_axes"],
    )
    brief = ContentSalesBrief.model_construct(
        final_canonical_url=PAGE_URL,
        target_reader="Firma",
        buyer_problem="Nie zna zakresu usługi.",
        buyer_trigger="Potrzebuje wsparcia.",
        search_intent="informacyjna",
        source_facts=[],
        knowledge_card_ids=[service_candidate.service_card_id],
        measurement_plan=ContentSalesBriefMeasurementPlan.model_construct(
            metrics_to_watch=["gsc_clicks"],
            baseline_evidence_ids=["ev_gsc_readiness_axes"],
            earliest_verdict_note="Porównaj pełne okna.",
            success_claim_rule="Nie claimuj bez zamkniętego okna.",
        ),
    )
    return service_candidate, service_profile, brief


def _planning_object_axis(summary: ContentPlanningInputSummary) -> tuple[object, ...]:
    return (
        summary.goal,
        summary.final_canonical_url,
        summary.service_label,
        summary.inventory_status,
        summary.content_inventory_status,
        summary.acf_section_inventory_status,
    )
