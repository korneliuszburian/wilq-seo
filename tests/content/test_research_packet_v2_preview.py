from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_research_packet_v2_preview import (
    _planning_blocker,
    register_content_research_packet_v2_preview_route,
)
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    ContentPlanningInputBuildResult,
)
from wilq.content.planning.input_service_policy import ContentPlanningInputBlocker
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryRequirement,
    ContentRegulatoryRequirementCoverage,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v2_preview import (
    build_research_packet_v2_preview,
)
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityServiceBinding,
)
from wilq.content.workflow.source_pack_v2 import (
    SourcePackV2Blocker,
    SourcePackV2Fact,
    SourcePackV2Preview,
)


def _client(source_pack: SourcePackV2Preview, planning_input: ContentPlanningInput) -> TestClient:
    app = FastAPI()
    router = APIRouter()
    register_content_research_packet_v2_preview_route(
        router,
        source_pack_loader=lambda _work_item_id: source_pack,
        planning_input_loader=lambda _work_item_id: planning_input,
    )
    app.include_router(router)
    return TestClient(app)


def _ready_inputs() -> tuple[SourcePackV2Preview, ContentPlanningInput]:
    fact = SourcePackV2Fact(
        source_fact_id="fact_exact",
        fact_digest="a" * 64,
        text="Zatwierdzony fakt.",
        source_reference="https://example.test/source",
        freshness_date="2026-09-23",
        source_type="official_guidance",
        source_connectors=("official_regulatory_review",),
        evidence_ids=("ev_exact",),
    )
    seed = SourcePackV2Preview.model_construct(
        status="ready",
        work_item_id="wi_exact",
        page_url="https://www.ekologus.pl/exact/",
        canonical_path="/exact",
        keep_receipt_id="content_keep_exact",
        keep_receipt_digest="b" * 64,
        material_meaning_digest="c" * 64,
        authority_receipt_id="content_authority_exact",
        authority_receipt_digest="d" * 64,
        authority_snapshot_digest="e" * 64,
        service_binding=ContentSourceFactAuthorityServiceBinding(
            status="exact_bound",
            card_id="card_exact",
            binding_url="https://www.ekologus.pl/exact/",
        ),
        facts=(fact,),
        verification_evidence_ids=("ev_exact",),
        verification_registry_digest="f" * 64,
        generation_allowed=False,
        source_pack_write_allowed=False,
    )
    source_pack_hash = canonical_json_digest(seed.semantic_payload())
    source_pack = SourcePackV2Preview.model_validate(
        seed.model_dump(mode="python")
        | {
            "source_pack_id": f"source_pack_v2_{source_pack_hash}",
            "source_pack_hash": source_pack_hash,
        }
    )
    planning_input = ContentPlanningInput.model_construct(
        planning_input_digest="c" * 64,
        work_item_id="wi_exact",
        target_reader="Operator środowiskowy",
        buyer_problem="Brak pewności co do obowiązku.",
        buyer_trigger="Zmiana wymagań.",
        search_intent="sprawdzenie obowiązku",
        source_facts=[{"unreviewed_claim": "UNREVIEWED CLAIM"}],
        evidence_ids=["ev_exact"],
        baseline_cta_direction="Kontakt z doradcą",
        minimum_cta_blocks=1,
        required_cta_patterns=[],
        internal_link_candidates=[
            ContentPlanningInternalLinkCandidate(
                target_url="https://www.ekologus.pl/kontakt",
                anchor_hint="Kontakt z doradcą",
                evidence_ids=["ev_exact"],
            )
        ],
        regulatory_coverage=ContentRegulatoryCoverage(applicability_status="not_required"),
    )
    return source_pack, planning_input


def test_public_preview_hash_binds_exact_source_pack_and_current_planning_input() -> None:
    source_pack, planning_input = _ready_inputs()
    source_pack_hash = source_pack.source_pack_hash

    response = _client(source_pack, planning_input).get(
        "/api/content/work-items/wi_exact/research-packet-v2-preview"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["source_pack_hash"] == source_pack_hash
    assert payload["planning_input_digest"] == "c" * 64
    assert payload["selected_facts"][0]["text"] == "Zatwierdzony fakt."
    assert "UNREVIEWED CLAIM" not in str(payload)
    assert payload["keep_receipt_id"] == "content_keep_exact"
    assert payload["material_meaning_digest"] == "c" * 64
    assert payload["generation_allowed"] is False
    assert payload["packet_write_allowed"] is False
    assert len(payload["preview_hash"]) == 64

    changed_planning = _client(
        source_pack,
        planning_input.model_copy(update={"planning_input_digest": "9" * 64}),
    ).get("/api/content/work-items/wi_exact/research-packet-v2-preview")
    assert changed_planning.json()["preview_hash"] != payload["preview_hash"]

    forged_pack = source_pack.model_copy(update={"source_pack_hash": "0" * 64})
    invalid = _client(forged_pack, planning_input).get(
        "/api/content/work-items/wi_exact/research-packet-v2-preview"
    )
    assert invalid.json()["blocker"]["code"] == "source_pack_invalid"
    assert invalid.json()["selected_facts"] == []

    unreviewed_requirement = ContentRegulatoryCoverage(
        applicability_status="required",
        profile_id="profile_exact",
        profile_version="2026-09-23",
        requirements=[
            ContentRegulatoryRequirement(
                id="requirement_exact", label="Wymóg źródłowy", reason="Podstawa prawna."
            )
        ],
        requirement_coverage=[
            ContentRegulatoryRequirementCoverage(
                requirement_id="requirement_exact",
                source_fact_ids=["fact_unreviewed"],
                evidence_ids=["ev_legal"],
            )
        ],
        source_fact_ids=["fact_unreviewed"],
        evidence_ids=["ev_legal"],
    )
    blocked = _client(
        source_pack,
        planning_input.model_copy(update={"regulatory_coverage": unreviewed_requirement}),
    ).get("/api/content/work-items/wi_exact/research-packet-v2-preview")
    assert blocked.status_code == 200
    assert blocked.json()["blocker"]["code"] == "legal_requirement_outside_reviewed_pack"
    assert blocked.json()["selected_facts"] == []

    foreign_evidence = unreviewed_requirement.model_copy(
        update={
            "requirement_coverage": [
                ContentRegulatoryRequirementCoverage(
                    requirement_id="requirement_exact",
                    source_fact_ids=["fact_exact"],
                    evidence_ids=["ev_foreign"],
                )
            ]
        }
    )
    evidence_blocked = _client(
        source_pack,
        planning_input.model_copy(update={"regulatory_coverage": foreign_evidence}),
    ).get("/api/content/work-items/wi_exact/research-packet-v2-preview")
    assert evidence_blocked.json()["blocker"]["code"] == "legal_requirement_evidence_unbound"


def test_planning_readiness_blocker_prevents_ready_packet_even_with_input() -> None:
    source_pack, planning_input = _ready_inputs()
    blocker = ContentPlanningInputBlocker(
        code="missing_regulatory_source_coverage",
        label="Niepełne źródła",
        reason="Brak aktualnego źródła.",
        next_step="Uzupełnij oficjalne źródło.",
    )
    result = ContentPlanningInputBuildResult.model_construct(
        planning_input=planning_input,
        blockers=[blocker],
    )
    projected = _planning_blocker(result, ("ev_exact",))
    assert projected is not None
    preview = build_research_packet_v2_preview(
        "wi_exact",
        source_pack=source_pack,
        planning_input=planning_input,
        planning_blocker=projected,
    )
    assert preview.status == "blocked"
    assert preview.blocker is not None
    assert preview.blocker.code == "missing_regulatory_source_coverage"


def test_public_preview_returns_typed_blocker_without_loading_planning_or_connectors() -> None:
    blocked = SourcePackV2Preview.model_construct(
        status="blocked",
        work_item_id="wi_blocked",
        blocker=SourcePackV2Blocker(
            code="material_review_missing_or_stale",
            owner="WILQ content workflow",
            evidence_ids=("ev_page",),
            safe_next_step="Przeprowadź exact review bieżącego materiału.",
        ),
        generation_allowed=False,
        source_pack_write_allowed=False,
    )
    app = FastAPI()
    router = APIRouter()

    def unexpected_planning_load(_work_item_id: str) -> ContentPlanningInput:
        raise AssertionError("blocked source pack must not load planning or connectors")

    register_content_research_packet_v2_preview_route(
        router,
        source_pack_loader=lambda _work_item_id: blocked,
        planning_input_loader=unexpected_planning_load,
    )
    app.include_router(router)

    response = TestClient(app).get("/api/content/work-items/wi_blocked/research-packet-v2-preview")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["blocker"] == {
        "code": "material_review_missing_or_stale",
        "owner": "WILQ content workflow",
        "evidence_ids": ["ev_page"],
        "safe_next_step": "Przeprowadź exact review bieżącego materiału.",
    }
    assert payload["generation_allowed"] is False
    assert payload["packet_write_allowed"] is False
    with pytest.raises(ValueError, match="Blocked preview cannot expose an artifact"):
        from wilq.content.workflow.research_packet_v2_preview import ResearchPacketV2Preview

        ResearchPacketV2Preview.model_validate(
            payload | {"source_pack_id": "source_pack_v2_foreign"}
        )
