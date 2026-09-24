from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tests.content.test_generated_proposal_turn_v2 import (
    _planning_input_with_caller_context,
    _ready_inputs,
)
from tests.content.test_research_packet_v3_preview import _pack, _planning_result
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning import route_packet_binding
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.input_sources import ContentPlanningInventorySection
from wilq.content.planning.packet_model_projection_v3 import (
    ResearchPacketV3ModelProjectionBlocked,
    content_planning_turn_request_v3,
    project_planning_input_for_packet_v3,
)
from wilq.content.planning.proposal_packet_binding import bind_research_packet
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_preview import (
    ResearchPacketV3Preview,
    build_research_packet_v3_preview,
)
from wilq.content.workflow.source_pack_v3 import (
    SourcePackV3Fact,
    SourcePackV3Preview,
)


def _approved_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="fact_exact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://eli.gov.pl/acts/synthetic",
        extracted_fact="Zatwierdzony fakt prawny.",
        scope="claim_policy",
        freshness_date="2026-09-24",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["ev_official_fact"],
        source_connectors=["official_regulatory_review"],
        target_card_id="synthetic_profile",
        target_card_type="regulatory_source",
        target_card_title="Synthetic profile",
        official_source=True,
        regulatory_profile_id="synthetic_profile",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["requirement_exact"],
        applicable_canonical_paths=["/exact"],
    )


def _packet(fact: ContentSourceFact) -> tuple[SourcePackV3Preview, ResearchPacketV3Preview]:
    source_pack = _pack()
    selected = SourcePackV3Fact(
        source_fact_id=fact.source_id,
        fact_digest=canonical_json_digest(fact.model_dump(mode="json")),
        text=fact.extracted_fact,
        source_reference=fact.source_url_or_path,
        freshness_date=fact.freshness_date,
        source_type="legal_update",
        source_connectors=tuple(sorted(set(fact.source_connectors))),
        evidence_ids=tuple(sorted(set(fact.evidence_ids))),
        regulatory_requirement_ids=tuple(sorted(set(fact.regulatory_requirement_ids))),
    )
    seed = source_pack.model_copy(update={"facts": (selected,)})
    digest = canonical_json_digest(seed.semantic_payload())
    source_pack = SourcePackV3Preview.model_validate(
        seed.model_dump(mode="python")
        | {
            "source_pack_hash": digest,
            "source_pack_id": f"source_pack_v3_{digest}",
        },
        strict=True,
    )
    packet = build_research_packet_v3_preview(
        "wi_exact", source_pack=source_pack, planning_result=_planning_result()
    )
    assert packet.status == "ready", packet.blocker
    return source_pack, packet


def _raw_input(packet: ResearchPacketV3Preview) -> ContentPlanningInput:
    _source_pack_v2, seed = _ready_inputs()
    raw = _planning_input_with_caller_context(seed)
    assert packet.page_url is not None
    return raw.model_copy(
        update={
            "work_item_id": packet.work_item_id,
            "content_kind": "editorial",
            "confirmed_service_card_id": None,
            "service_label": None,
            "service_candidates": [],
            "final_canonical_url": packet.page_url,
            "source_facts": [
                raw.source_facts[0].model_copy(
                    update={"summary": "UNREVIEWED OLD WP CLAIM", "evidence_ids": ["ev_caller"]}
                )
            ],
            "claim_ledger": [
                raw.claim_ledger[0].model_copy(
                    update={"claim_text": "UNREVIEWED OLD WP CLAIM", "evidence_ids": ["ev_caller"]}
                ),
                raw.claim_ledger[1],
            ],
            "evidence_ids": ["ev_caller", "ev_query", "ev_official_fact"],
            "inventory": raw.inventory.model_copy(
                update={
                    "title_or_h1": "UNREVIEWED OLD WP TITLE",
                    "content_text": "UNREVIEWED OLD WP BODY",
                    "content_summary": "UNREVIEWED OLD WP SUMMARY",
                    "evidence_ids": ["ev_caller"],
                    "source_connectors": ["wordpress_ekologus"],
                    "sections": [
                        ContentPlanningInventorySection(
                            section_id="inventory_section_old",
                            heading="UNREVIEWED OLD WP HEADING",
                            evidence_ids=["ev_caller"],
                        )
                    ],
                }
            ),
        }
    )


def test_v3_model_projection_uses_only_current_approved_facts_and_packet_context() -> None:
    fact = _approved_fact()
    source_pack, packet = _packet(fact)
    projected = project_planning_input_for_packet_v3(
        _raw_input(packet),
        packet=packet,
        source_pack=source_pack,
        source_facts=(fact,),
    )
    request = content_planning_turn_request_v3(projected, operator_hint="")
    model_input = json.loads(request.untrusted_context)["planning_input"]
    serialized = json.dumps(model_input, ensure_ascii=False)

    assert model_input["research_packet_id"] == (
        f"content_research_packet_v3_{packet.preview_hash[:24]}"
    )
    assert model_input["research_packet_digest"] == packet.preview_hash
    assert model_input["target_reader"] == packet.planning_context.target_reader
    assert model_input["buyer_problem"] == packet.planning_context.buyer_problem
    assert [row["source_fact_ids"] for row in model_input["source_facts"]] == [["fact_exact"]]
    assert model_input["regulatory_coverage"]["requirement_coverage"][0]["requirement_id"] == (
        "requirement_exact"
    )
    assert model_input["query_portfolio"]["status"] == "missing"
    assert model_input["query_portfolio"]["gsc_query_rows"] == []
    assert model_input["claim_ledger"] == []
    assert "search_intent" not in model_input
    assert "UNREVIEWED OLD WP CLAIM" not in serialized
    assert "UNREVIEWED OLD WP TITLE" not in serialized
    assert "UNREVIEWED OLD WP HEADING" not in serialized
    assert "UNREVIEWED OLD WP BODY" not in serialized
    assert "UNREVIEWED OLD WP SUMMARY" not in serialized
    assert "exact query signal" not in serialized
    assert "ev_caller" not in model_input["evidence_ids"]
    assert model_input["internal_link_candidates"][0]["target_url"] == (
        packet.internal_links[0].target_url
    )


def test_v3_model_projection_blocks_registry_drift() -> None:
    fact = _approved_fact()
    source_pack, packet = _packet(fact)
    changed = fact.model_copy(update={"extracted_fact": "Inny fakt po review."})

    with pytest.raises(ResearchPacketV3ModelProjectionBlocked) as captured:
        project_planning_input_for_packet_v3(
            _raw_input(packet),
            packet=packet,
            source_pack=source_pack,
            source_facts=(changed,),
        )

    assert captured.value.code == "research_packet_v3_registry_drift"


def test_v3_model_projection_blocks_content_subject_drift() -> None:
    fact = _approved_fact()
    source_pack, packet = _packet(fact)
    changed_subject = _raw_input(packet).model_copy(
        update={
            "content_kind": "service",
            "confirmed_service_card_id": "unreviewed_service",
            "service_label": "Unreviewed service",
            "service_candidates": [],
        }
    )

    with pytest.raises(ResearchPacketV3ModelProjectionBlocked) as captured:
        project_planning_input_for_packet_v3(
            changed_subject,
            packet=packet,
            source_pack=source_pack,
            source_facts=(fact,),
        )

    assert captured.value.code == "research_packet_v3_model_identity_mismatch"


def test_v3_packet_id_cannot_enter_the_legacy_source_pack_binding() -> None:
    _source_pack_v2, seed = _ready_inputs()
    planning_input = _planning_input_with_caller_context(seed)
    digest = "a" * 64
    packet_id = f"content_research_packet_v3_{digest[:24]}"
    bound = planning_input.model_copy(
        update={"research_packet_id": packet_id, "research_packet_digest": digest}
    )
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id="card_exact",
        expected_planning_input_digest=bound.planning_input_digest,
        research_packet_id=packet_id,
        expected_research_packet_digest=digest,
        requested_by="synthetic-reviewer",
    )

    class ForbiddenLegacyStore:
        def load_content_research_packet(self, _packet_id: str) -> None:
            pytest.fail("v3 packet ID must not enter the legacy packet loader")

    projected, response = bind_research_packet(
        snapshot=SimpleNamespace(),  # type: ignore[arg-type]
        planning_input=bound,
        request=request,
        workflow_store=ForbiddenLegacyStore(),  # type: ignore[arg-type]
    )

    assert projected is None
    assert response is not None and response.status == "blocked"
    assert response.blockers[0].code == "research_packet_action_required"
    assert response.blockers[0].source_codes == ["research_packet_v3_intent_required"]


def test_route_packet_preparation_rejects_v3_before_legacy_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source_pack, seed = _ready_inputs()
    planning_input = _planning_input_with_caller_context(seed)
    digest = "b" * 64
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id="card_exact",
        expected_planning_input_digest=planning_input.planning_input_digest,
        research_packet_id=f"content_research_packet_v3_{digest[:24]}",
        expected_research_packet_digest=digest,
        requested_by="synthetic-reviewer",
    )
    monkeypatch.setattr(
        route_packet_binding,
        "canonical_inventory_work_item_id",
        lambda work_item_id: work_item_id,
    )

    result = route_packet_binding.prepare_and_bind_research_packet(
        work_item_id=planning_input.work_item_id,
        request=request,
        planning_input=planning_input,
        snapshot=SimpleNamespace(),  # type: ignore[arg-type]
        store=object(),  # type: ignore[arg-type]
    )

    assert result.response is not None and result.response.status == "blocked"
    assert result.response.blockers[0].code == "research_packet_action_required"
    assert result.response.blockers[0].source_codes == ["research_packet_v3_intent_required"]
