"""Exact v3 packet preview from approved official facts and safe planning context."""

from importlib import import_module
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from wilq.content.measurement.aggregates import MeasurementPeriodComparison
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
)
from wilq.content.planning.input_service_policy import ContentPlanningInputBlocker
from wilq.content.planning.input_sources import (
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
)
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryRequirement,
    ContentRegulatoryRequirementCoverage,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityServiceBinding,
)
from wilq.content.workflow.source_pack_v3 import (
    SourcePackV3Fact,
    SourcePackV3Preview,
    SourcePackV3Requirement,
)


def _pack() -> SourcePackV3Preview:
    fact = SourcePackV3Fact(
        source_fact_id="fact_exact",
        fact_digest="a" * 64,
        text="Zatwierdzony fakt prawny.",
        source_reference="https://eli.gov.pl/acts/synthetic",
        freshness_date="2026-09-24",
        evidence_ids=("ev_official_fact",),
        source_connectors=("official_regulatory_review",),
        regulatory_requirement_ids=("requirement_exact",),
    )
    seed = SourcePackV3Preview.model_construct(
        status="ready",
        work_item_id="wi_exact",
        page_url="https://www.ekologus.pl/exact/",
        canonical_path="/exact",
        identity_id="current_page_identity_v3_exact",
        identity_digest="b" * 64,
        material_meaning_digest="c" * 64,
        registry_digest="d" * 64,
        regulatory_profile_id="synthetic_profile",
        regulatory_profile_version="synthetic-v1",
        service_binding=ContentSourceFactAuthorityServiceBinding(
            status="exact_bound", binding_url="https://www.ekologus.pl/exact/"
        ),
        facts=(fact,),
        requirements=(SourcePackV3Requirement(
            requirement_id="requirement_exact",
            source_fact_ids=("fact_exact",),
            evidence_ids=("ev_official_fact",),
        ),),
        verification_evidence_ids=("ev_current", "ev_official_fact"),
        verification_evidence_digest="e" * 64,
    )
    digest = canonical_json_digest(seed.semantic_payload())
    return SourcePackV3Preview.model_validate(seed.model_dump(mode="python") | {
        "source_pack_id": f"source_pack_v3_{digest}",
        "source_pack_hash": digest,
    })


def _planning_result() -> ContentPlanningInputBuildResult:
    coverage = ContentRegulatoryCoverage(
        applicability_status="required",
        profile_id="synthetic_profile",
        profile_version="synthetic-v1",
        canonical_path="/exact",
        requirements=[ContentRegulatoryRequirement(
            id="requirement_exact", label="Wymaganie prawne", reason="Źródło urzędowe."
        )],
        requirement_coverage=[ContentRegulatoryRequirementCoverage(
            requirement_id="requirement_exact",
            source_fact_ids=["fact_exact"],
            evidence_ids=["ev_official_fact"],
        )],
        source_fact_ids=["fact_exact"],
        evidence_ids=["ev_official_fact"],
    )
    demand = ContentSearchDemandEvidence.model_construct(
        status="missing", gsc_query_rows=[], ads_term_rows=[], keyword_planner_rows=[],
        source_connectors=[], evidence_ids=[], optional_ads_status="not_exactly_mapped",
        optional_ads_evidence_ids=[], optional_ads_blockers=[], safe_next_step="Brak świeżego GSC.",
    )
    assessments = [
        ContentPlanningSourceAssessment(
            source=source, status="stale" if source == "gsc" else "used"
            if source == "wordpress" else "missing", reason="Syntetyczny stan źródła."
        )
        for source in (
            "wordpress", "service_profile", "gsc", "ga4", "google_ads", "ahrefs",
            "keyword_planner", "merchant", "localo", "social",
        )
    ]
    planning = ContentPlanningInput.model_construct(
        planning_input_digest="f" * 64,
        work_item_id="wi_exact",
        content_kind="editorial",
        final_canonical_url="https://www.ekologus.pl/exact/",
        target_reader="Operator środowiskowy",
        buyer_problem="Brak pewności co do obowiązku.",
        buyer_trigger="Zmiana wymagań.",
        search_intent="sprawdzenie obowiązku",
        source_facts=[ContentPlanningSourceFact(
            fact_id="old_page_claim",
            summary="UNREVIEWED OLD PAGE CLAIM",
            source_connector="wordpress_ekologus",
            evidence_ids=["ev_current"],
        )],
        evidence_ids=["ev_internal_link", "ev_official_fact"],
        baseline_cta_direction="Kontakt z doradcą",
        minimum_cta_blocks=1,
        required_cta_patterns=[],
        internal_link_candidates=[ContentPlanningInternalLinkCandidate(
            target_url="https://www.ekologus.pl/kontakt/",
            anchor_hint="Kontakt z doradcą",
            evidence_ids=["ev_internal_link"],
        )],
        regulatory_coverage=coverage,
        query_portfolio=demand,
        source_assessments=assessments,
        metric_comparisons=[],
    )
    return ContentPlanningInputBuildResult.model_construct(
        planning_input=planning,
        blockers=[ContentPlanningInputBlocker(
            code="stale_planning_sources",
            label="GSC nieświeże",
            reason="Tylko GSC wymaga odświeżenia.",
            next_step="Odśwież GSC przed rekomendacją ruchu.",
        )],
    )


def _client(pack, planning) -> TestClient:
    router = APIRouter()
    route_path = Path(__file__).resolve().parents[2] / (
        "apps/api/wilq_api/routers/content_research_packet_v3_preview.py"
    )
    if route_path.is_file():
        module = import_module("apps.api.wilq_api.routers.content_research_packet_v3_preview")
        module.register_content_research_packet_v3_preview_route(
            router,
            source_pack_loader=lambda _work_item_id: pack["current"],
            planning_result_loader=lambda _work_item_id: planning["current"],
        )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_public_v3_packet_is_exact_and_excludes_stale_gsc_and_old_page_claims() -> None:
    pack = {"current": _pack()}
    planning = {"current": _planning_result()}
    client = _client(pack, planning)
    path = "/api/content/work-items/wi_exact/research-packet-v3-preview"
    response = client.get(path)
    assert response.status_code == 200, response.text
    ready = response.json()
    assert ready["status"] == "ready"
    assert ready["source_pack_hash"] == pack["current"].source_pack_hash
    assert ready["demand_evidence_status"] == "missing"
    assert ready["generation_allowed"] is False
    assert "UNREVIEWED OLD PAGE CLAIM" not in str(ready)
    assert "keep_receipt_id" not in ready
    assert ready["selected_facts"][0]["source_fact_id"] == "fact_exact"
    assert ready["legal_requirements"][0]["evidence_ids"] == ["ev_official_fact"]

    pack["current"] = pack["current"].model_copy(update={
        "verification_evidence_ids": ("ev_current_rotated", "ev_official_fact"),
        "verification_evidence_digest": "1" * 64,
    })
    rotated = client.get(path).json()
    assert rotated["status"] == "ready"
    assert rotated["preview_hash"] == ready["preview_hash"]
    assert rotated["verification_evidence_ids"] != ready["verification_evidence_ids"]

    planning["current"].planning_input.query_portfolio.gsc_query_rows = [object()]
    stale_gsc = client.get(path).json()
    assert stale_gsc["status"] == "blocked"
    assert stale_gsc["blocker"]["code"] == "stale_gsc_data_in_packet"


def test_public_v3_packet_blocks_other_stale_sources_metrics_and_foreign_requirements() -> None:
    pack = {"current": _pack()}
    planning = {"current": _planning_result()}
    client = _client(pack, planning)
    path = "/api/content/work-items/wi_exact/research-packet-v3-preview"

    planning["current"].planning_input.final_canonical_url = (
        "https://www.ekologus.pl/other/"
    )
    wrong_page = client.get(path).json()
    assert wrong_page["status"] == "blocked"
    assert wrong_page["blocker"]["code"] == "planning_page_identity_mismatch"

    planning["current"] = _planning_result()
    planning["current"].planning_input.regulatory_coverage.canonical_path = "/other"
    wrong_coverage_page = client.get(path).json()
    assert wrong_coverage_page["status"] == "blocked"
    assert wrong_coverage_page["blocker"]["code"] == "planning_page_identity_mismatch"

    planning["current"] = _planning_result()
    planning["current"].planning_input.source_assessments[0].status = "stale"
    stale_wordpress = client.get(path).json()
    assert stale_wordpress["status"] == "blocked"
    assert stale_wordpress["blocker"]["code"] == "stale_gsc_data_in_packet"

    planning["current"] = _planning_result()
    planning["current"].planning_input.metric_comparisons = [
        MeasurementPeriodComparison.model_construct(
            source_connector="google_search_console", status="available"
        )
    ]
    stale_metric = client.get(path).json()
    assert stale_metric["status"] == "blocked"
    assert stale_metric["blocker"]["code"] == "stale_gsc_data_in_packet"

    planning["current"] = _planning_result()
    planning["current"].planning_input.regulatory_coverage.requirement_coverage[0].evidence_ids = [
        "ev_foreign"
    ]
    foreign = client.get(path).json()
    assert foreign["status"] == "blocked"
    assert foreign["blocker"]["code"] == "legal_requirement_evidence_unbound"

    planning["current"] = _planning_result()
    pack["current"] = pack["current"].model_copy(update={"source_pack_hash": "0" * 64})
    invalid_pack = client.get(path).json()
    assert invalid_pack["status"] == "blocked"
    assert invalid_pack["blocker"]["code"] == "source_pack_invalid"
