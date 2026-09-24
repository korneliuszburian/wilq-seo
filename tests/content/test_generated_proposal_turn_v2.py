from __future__ import annotations

import json
from pathlib import Path

import pytest

import wilq.content.planning.generated_proposal_turn as generated_proposal_turn
import wilq.content.planning.packet_model_projection as packet_model_projection
from tests.content.test_research_packet_v2_preview import _ready_inputs
from tests.content.test_research_packet_v2_store import _receipt
from wilq.content.claims.ledger import ContentClaimLedgerEntry
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput, _digest
from wilq.content.planning.generated_proposal_turn import content_planning_turn_request
from wilq.content.planning.input_sources import (
    PLANNING_SOURCE_NAMES,
    ContentPlanningInventory,
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
)
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.planning.packet_input_binding import bind_packet_identity_to_planning_input
from wilq.content.planning.source_pack_projection import project_research_packet_v2_facts
from wilq.content.workflow.decisions.demand_evidence import (
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    build_research_packet_v2_preview,
)
from wilq.content.workflow.research_packet_v2_receipt import (
    ResearchPacketV2ApprovalReceipt,
    ResearchPacketV2PreviewRecord,
)
from wilq.content.workflow.source_pack_v2 import SourcePackV2Fact, SourcePackV2Preview
from wilq.content.workflow.store.store import ContentWorkflowStore


def test_model_turn_does_not_treat_v2_packet_as_missing_v1_and_leak_caller_facts(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source_pack, planning_input = _ready_inputs()
    digest = "d" * 64
    planning_input = planning_input.model_copy(
        update={
            "research_packet_id": f"content_research_packet_v2_{digest[:24]}",
            "research_packet_digest": digest,
        }
    )
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    monkeypatch.setattr(packet_model_projection, "content_workflow_store", lambda: store)

    try:
        request = content_planning_turn_request(planning_input, operator_hint="")
    except ValueError as error:
        assert "approved v2" in str(error).lower()
    else:
        assert "UNREVIEWED CLAIM" not in request.untrusted_context


def test_model_turn_does_not_fall_through_from_v3_packet_to_raw_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source_pack, planning_input = _ready_inputs()
    planning_input = _planning_input_with_caller_context(planning_input)
    digest = "e" * 64
    planning_input = planning_input.model_copy(
        update={
            "research_packet_id": f"content_research_packet_v3_{digest[:24]}",
            "research_packet_digest": digest,
        }
    )
    monkeypatch.setattr(
        generated_proposal_turn,
        "current_research_packet_for_model",
        lambda *_: None,
    )

    with pytest.raises(ValueError, match="Approved v3"):
        content_planning_turn_request(planning_input, operator_hint="")


def _selected_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="fact_selected",
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path="https://www.ekologus.pl/exact/",
        extracted_fact="Selected exact source fact.",
        scope="service",
        freshness_date="2026-09-24",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["ev_selected"],
        source_connectors=["public_site"],
        target_card_id="card_exact",
        target_card_type="service",
        target_card_title="Exact service",
    )


def _source_pack_with_selected_fact(
    source_pack: SourcePackV2Preview,
    selected_fact: ContentSourceFact,
) -> SourcePackV2Preview:
    packet_fact = SourcePackV2Fact(
        source_fact_id=selected_fact.source_id,
        fact_digest=canonical_json_digest(selected_fact.model_dump(mode="json")),
        text=selected_fact.extracted_fact,
        source_reference=selected_fact.source_url_or_path,
        freshness_date=selected_fact.freshness_date,
        source_type=selected_fact.source_type,
        source_connectors=("public_site",),
        evidence_ids=("ev_selected",),
    )
    source_pack_seed = source_pack.model_copy(
        update={
            "facts": (packet_fact,),
            "verification_evidence_ids": ("ev_selected",),
        }
    )
    source_pack_hash = canonical_json_digest(source_pack_seed.semantic_payload())
    source_pack = SourcePackV2Preview.model_validate(
        source_pack_seed.model_dump(mode="json")
        | {
            "source_pack_hash": source_pack_hash,
            "source_pack_id": f"source_pack_v2_{source_pack_hash}",
        }
    )
    return source_pack


def _model_query_portfolio() -> ContentSearchDemandEvidence:
    return ContentSearchDemandEvidence(
        status="available",
        gsc_query_rows=[
            ContentSearchDemandRow(
                source_kind="gsc_query",
                source_connector="google_search_console",
                term="exact query signal",
                page="https://www.ekologus.pl/exact/",
                section_mapping_status="page_only",
                period="2026-09",
                freshness="fresh",
                evidence_ids=["ev_query"],
            )
        ],
        optional_ads_status="not_exactly_mapped",
        safe_next_step="Sprawdź zapytanie.",
    )


def _planning_input_with_caller_context(
    planning_input: ContentPlanningInput,
) -> ContentPlanningInput:
    planning_input = planning_input.model_copy(
        update={
            "content_kind": "service",
            "confirmed_service_card_id": "card_exact",
            "final_canonical_url": "https://www.ekologus.pl/exact/",
            "inventory": ContentPlanningInventory(
                status="available",
                content_status="available",
                acf_section_status="missing",
            ),
            "measurement_observation_rule": "Compare exact closed periods.",
            "measurement_success_claim_rule": "Do not claim measured success without evidence.",
            "baseline_cta_direction": "Contact the service team.",
            "source_assessments": [
                ContentPlanningSourceAssessment(
                    source=source,
                    status="missing",
                    reason="Model-edge packet test.",
                )
                for source in sorted(PLANNING_SOURCE_NAMES)
            ],
            "source_facts": [
                ContentPlanningSourceFact(
                    fact_id="caller_fact",
                    summary="CALLER-ONLY FACT",
                    source_connector="public_site",
                    evidence_ids=["ev_caller"],
                    source_fact_ids=["caller_fact"],
                )
            ],
            "claim_ledger": [
                ContentClaimLedgerEntry(
                    id="claim_selected",
                    claim_text="Selected fact claim.",
                    claim_type="service_claim",
                    status="allowed_with_evidence",
                    evidence_ids=["ev_selected"],
                    reason="Exact selected source.",
                ),
                ContentClaimLedgerEntry(
                    id="claim_caller",
                    claim_text="CALLER-ONLY CLAIM",
                    claim_type="service_claim",
                    status="allowed_with_evidence",
                    evidence_ids=["ev_caller"],
                    reason="Caller supplied.",
                ),
            ],
            "evidence_ids": [
                "ev_selected",
                "ev_caller",
                "ev_query",
                "ev_exact",
            ],
            "query_portfolio": _model_query_portfolio(),
            "internal_link_candidates": [
                ContentPlanningInternalLinkCandidate(
                    target_url="https://www.ekologus.pl/kontakt/",
                    anchor_hint="Kontakt",
                    evidence_ids=["ev_exact"],
                ),
                ContentPlanningInternalLinkCandidate(
                    target_url="https://www.ekologus.pl/caller-link/",
                    anchor_hint="Caller link",
                    evidence_ids=["ev_outside_link"],
                ),
            ],
        }
    )
    raw_payload = planning_input.model_dump(mode="json")
    raw_payload.pop("planning_input_digest", None)
    planning_input = planning_input.model_copy(
        update={
            "planning_input_digest": _digest(
                {
                    "schema_name": planning_input.schema_name,
                    "criteria_version": planning_input.criteria_version,
                    "inventory_mapping_policy": planning_input.inventory_mapping_policy,
                    **raw_payload,
                }
            )
        }
    )
    return planning_input


def _packet_model_case(
    tmp_path: Path,
) -> tuple[
    ContentWorkflowStore,
    ContentSourceFact,
    ContentPlanningInput,
    ResearchPacketV2Preview,
    ResearchPacketV2ApprovalReceipt,
]:
    source_pack, input_seed = _ready_inputs()
    selected_fact = _selected_fact()
    source_pack = _source_pack_with_selected_fact(source_pack, selected_fact)
    planning_input = _planning_input_with_caller_context(input_seed)
    preview = build_research_packet_v2_preview(
        "wi_exact", source_pack=source_pack, planning_input=planning_input
    )
    assert preview.status == "ready", preview.blocker
    record = ResearchPacketV2PreviewRecord.from_preview(preview)
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    assert store.record_research_packet_v2_preview(record) == "created"
    receipt = _receipt(record)
    assert store._record_research_packet_v2_approval_receipt(receipt) == "created"
    projected = project_research_packet_v2_facts(
        planning_input, preview.selected_facts, (selected_fact,)
    )
    bound = bind_packet_identity_to_planning_input(
        projected,
        work_item_id=preview.work_item_id,
        packet_id=receipt.packet_id,
        packet_digest=receipt.packet_digest,
    )
    return store, selected_fact, bound, preview, receipt


def test_v2_model_turn_uses_approved_preview_selected_facts_and_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, selected_fact, bound, preview, receipt = _packet_model_case(tmp_path)
    monkeypatch.setattr(packet_model_projection, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        packet_model_projection, "ekologus_source_facts", lambda: (selected_fact,)
    )
    assert preview.planning_input_digest != bound.planning_input_digest

    request = content_planning_turn_request(bound, operator_hint="")
    model_input = json.loads(request.untrusted_context)["planning_input"]

    assert model_input["research_packet_id"] == receipt.packet_id
    assert model_input["research_packet_digest"] == receipt.packet_digest
    assert [fact["source_fact_ids"] for fact in model_input["source_facts"]] == [
        [selected_fact.source_id]
    ]
    assert "CALLER-ONLY FACT" not in json.dumps(model_input)
    assert "CALLER-ONLY CLAIM" not in json.dumps(model_input)
    assert [row["term"] for row in model_input["query_portfolio"]["gsc_query_rows"]] == [
        "exact query signal"
    ]
    assert model_input["internal_link_candidates"] == [
        {
            "target_url": link.target_url,
            "anchor_hint": link.anchor_hint,
            "source_connector": link.source_connector,
            "evidence_ids": list(link.evidence_ids),
        }
        for link in preview.internal_links
    ]
    assert "ev_caller" not in model_input["evidence_ids"]
    assert "ev_outside_link" not in json.dumps(model_input)


def test_v2_model_turn_blocks_selected_fact_registry_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, selected_fact, bound, _preview, _receipt = _packet_model_case(tmp_path)
    changed_fact = selected_fact.model_copy(
        update={"extracted_fact": "Changed after packet approval."}
    )
    monkeypatch.setattr(packet_model_projection, "content_workflow_store", lambda: store)
    monkeypatch.setattr(
        packet_model_projection, "ekologus_source_facts", lambda: (changed_fact,)
    )

    with pytest.raises(ValueError, match="current registry"):
        content_planning_turn_request(bound, operator_hint="")
