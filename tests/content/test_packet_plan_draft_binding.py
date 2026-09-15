from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

import apps.api.wilq_api.routers.content_planning_proposals as planning_route
import wilq.content.drafts.initial_full_draft_turn as initial_full_draft_turn_module
import wilq.content.planning.proposal_packet_binding as proposal_packet_binding
import wilq.content.planning.route_packet_binding as route_packet_binding
from tests.content.packet_plan_draft_fixtures import (
    build_packet_preparation_case,
    snapshot_without_cta,
)
from tests.content.test_new_page_initial_draft import _draft_case
from tests.content.test_research_packet import legacy_exact_source_pack_fixture
from tests.content.test_source_pack_binding import _setup_store
from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.claims.ledger import ContentClaimLedgerEntry
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
)
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.planning.compact_projections import compact_initial_draft_planning_input
from wilq.content.planning.dynamic_input import (
    ContentPlanningInput,
    bind_research_packet_to_planning_input,
)
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.planning.generated_proposal_turn import (
    compact_planning_input_for_model,
)
from wilq.content.planning.input_sources import (
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
)
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.demand_evidence import (
    ContentSearchDemandEvidence,
    ContentSearchDemandRow,
)
from wilq.content.workflow.research_packet import (
    ContentResearchPacketBlocker,
)
from wilq.content.workflow.research_packet_preparation import (
    build_server_owned_research_packet_command,
    current_research_packet_blocker,
    prepare_content_research_packet,
)
from wilq.content.workflow.source_pack_binding import ContentSourcePackBindingBlocker


def test_planning_turn_carries_server_owned_research_packet_binding() -> None:
    planning_input = ContentPlanningInput.model_construct(
        planning_input_digest="a" * 64,
        work_item_id="content_work_item_packet_binding",
        research_packet_id="content_research_packet_current",
        research_packet_digest="b" * 64,
        content_kind="editorial",
        confirmed_service_card_id=None,
        query_portfolio=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Odczytaj popyt.",
        ),
    )

    context = compact_initial_draft_planning_input(planning_input)
    expected = {
        "packet_id": "content_research_packet_current",
        "packet_digest": "b" * 64,
    }
    assert context["research_packet_id"] == expected["packet_id"]
    assert context["research_packet_digest"] == expected["packet_digest"]


def test_packet_command_derives_semantics_from_typed_planning_context(
    tmp_path: Path,
) -> None:
    store, identity = _setup_store(tmp_path)
    source_pack = legacy_exact_source_pack_fixture(store, identity)
    brief = ContentSalesBrief.model_construct(
        id="sales_brief_packet_binding",
        work_item_id=identity.current_work_item_id,
        evidence_ids=["ev_brief_packet"],
        cta_destination="/kontakt/",
    )
    demand = ContentSearchDemandEvidence(
        status="available",
        gsc_query_rows=[
            ContentSearchDemandRow(
                source_kind="gsc_query",
                source_connector="google_search_console",
                term="bdo dla firm",
                page=identity.public_url,
                section_mapping_status="page_only",
                period="2026-09",
                freshness="fresh",
                evidence_ids=["ev_demand_packet"],
            )
        ],
        optional_ads_status="not_exactly_mapped",
        safe_next_step="Sprawdź popyt.",
    )
    planning_input = ContentPlanningInput.model_construct(
        planning_input_digest="a" * 64,
        work_item_id=identity.current_work_item_id,
        content_kind="service",
        confirmed_service_card_id="ekologus_service_bdo_reporting",
        service_label="Raportowanie BDO",
        target_reader="Przedsiębiorca",
        buyer_problem="Niepewność obowiązków.",
        buyer_trigger="Zbliżający się termin.",
        search_intent="bdo dla firm",
        source_facts=[],
        source_assessments=[],
        query_portfolio=demand,
        regulatory_coverage=ContentRegulatoryCoverage(),
        inventory=SimpleNamespace(),
        internal_link_candidates=[],
        evidence_ids=["ev_planning_packet"],
    )
    snapshot = SimpleNamespace(
        sales_brief=SimpleNamespace(sales_brief_result=SimpleNamespace(brief=brief)),
        service_profile_context=ContentWorkItemServiceProfileContext.not_evaluated(),
        freshness_assessment={"state": "fresh"},
        preflight=SimpleNamespace(item=SimpleNamespace(evidence_ids=["ev_preflight_packet"])),
    )

    command = build_server_owned_research_packet_command(
        snapshot=snapshot,
        planning_input=planning_input,
        source_pack=source_pack,
        identity=identity,
        now=datetime.now(UTC),
    )

    assert not isinstance(command, ContentResearchPacketBlocker)
    assert command.intent == planning_input.search_intent
    assert command.query_cluster == ("bdo dla firm",)
    assert command.canonical_owner == identity.canonical_path
    assert command.cta_destination == "/kontakt/"
    assert command.legal_source_requirements == ("none_identified",)
    assert command.context_receipt is not None
    assert command.context_receipt.brief_semantic_digest != "0" * 64


def test_initial_draft_turn_carries_packet_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)
    packet_id = "content_research_packet_current"
    packet_digest = "b" * 64
    planning_input = case.planning_input.model_copy(
        update={
            "research_packet_id": packet_id,
            "research_packet_digest": packet_digest,
        }
    )
    proposal = case.proposal.model_copy(
        update={
            "research_packet_id": packet_id,
            "research_packet_digest": packet_digest,
        }
    )
    contract = StructuredDraftGenerationContract.model_construct(
        model_input=StructuredDraftGenerationInput.model_construct(),
        output_schema={},
        system_instruction="",
        user_instruction="",
    )
    monkeypatch.setattr(
        initial_full_draft_turn_module,
        "current_research_packet_for_model",
        lambda _planning_input: None,
    )

    request = initial_full_draft_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=contract,
    )

    assert json.loads(request.application_context)["research_packet_binding"] == {
        "packet_id": packet_id,
        "packet_digest": packet_digest,
    }
    assert json.loads(request.untrusted_context)["research_packet_binding"] == {
        "packet_id": packet_id,
        "packet_digest": packet_digest,
    }


def test_research_packet_binding_changes_planning_input_digest(tmp_path: Path) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.planning_input = case.planning_input.model_copy(
        update={
            "final_canonical_url": case.identity.public_url,
            "inventory": SimpleNamespace(
                status="available",
                content_status="available",
                acf_section_status="missing",
            ),
            "source_assessments": [
                ContentPlanningSourceAssessment(source=source, status="missing", reason="test")
                for source in (
                    "wordpress",
                    "service_profile",
                    "gsc",
                    "ga4",
                    "google_ads",
                    "ahrefs",
                    "keyword_planner",
                    "merchant",
                    "localo",
                    "social",
                )
            ],
        }
    )
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None

    bound = bind_research_packet_to_planning_input(case.planning_input, prepared.packet)
    alternate = bind_research_packet_to_planning_input(
        case.planning_input,
        prepared.packet.model_copy(update={"packet_digest": "f" * 64}),
    )

    assert bound.research_packet_id == prepared.packet.packet_id
    assert bound.research_packet_digest == prepared.packet.packet_digest
    assert bound.planning_input_digest != case.planning_input.planning_input_digest
    assert alternate.planning_input_digest != bound.planning_input_digest


def test_explicit_source_pack_for_foreign_work_item_is_blocked_before_derivation(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    foreign_pack = case.source_pack.model_copy(
        update={"current_work_item_id": "content_work_item_foreign"}
    )
    case.store.source_pack = foreign_pack

    result = prepare_content_research_packet(
        store=case.store,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
        source_pack_binding_id=foreign_pack.binding_id,
    )

    assert result.status == "blocked"
    assert result.blocker is not None
    assert result.blocker.reason == "work_item_mismatch"


def test_selected_latest_blocked_source_pack_does_not_fall_back_to_older_exact(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    latest_blocker = ContentSourcePackBindingBlocker(
        seam="classification",
        reason="classification_stale",
        evidence_ids=case.source_pack.evidence_ids,
        next_step="Odśwież bieżącą klasyfikację.",
    )
    latest = case.source_pack.model_copy(
        update={
            "binding_id": "content_source_pack_binding_latest",
            "status": "blocked",
            "blocker": latest_blocker,
            "recorded_at": case.source_pack.recorded_at + timedelta(minutes=1),
        }
    )
    case.store.list_content_source_pack_bindings = lambda **_: [case.source_pack, latest]

    result = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )

    assert result.status == "blocked"
    assert result.blocker is not None
    assert result.blocker.reason == "source_pack_binding_blocked"


def test_current_classification_decision_set_mismatch_blocks_packet(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.store.classification = SimpleNamespace(
        run_id=case.identity.classification_run_id,
        run_digest=case.identity.classification_run_digest,
        decision_set_digest="f" * 64,
        row=SimpleNamespace(
            source_packet_row_digest=case.identity.classification_source_row_digest
        ),
    )

    result = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )

    assert result.status == "blocked"
    assert result.blocker is not None
    assert result.blocker.reason == "identity_binding_blocked"


def test_packet_revalidation_rejects_a_newer_current_source_pack(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    newer = case.source_pack.model_copy(
        update={
            "binding_id": "content_source_pack_binding_newer",
            "binding_digest": "f" * 64,
            "recorded_at": case.source_pack.recorded_at + timedelta(minutes=1),
        }
    )
    case.store.list_content_source_pack_bindings = lambda **_: [case.source_pack, newer]

    blocker = current_research_packet_blocker(
        store=case.store,
        packet=prepared.packet,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )

    assert blocker is not None
    assert blocker.reason == "packet_conflict"


def test_packet_revalidation_rejects_semantic_context_receipt_drift(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    assert prepared.packet.context_receipt is not None
    drifted = prepared.packet.model_copy(
        update={
            "context_receipt": prepared.packet.context_receipt.model_copy(
                update={"brief_semantic_digest": "f" * 64}
            )
        }
    )

    blocker = current_research_packet_blocker(
        store=case.store,
        packet=drifted,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )

    assert blocker is not None
    assert blocker.reason == "context_receipt_mismatch"


def test_packet_revalidation_requires_a_latest_relevant_source_pack(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    case.store.list_content_source_pack_bindings = lambda **_: []

    blocker = current_research_packet_blocker(
        store=case.store,
        packet=prepared.packet,
        snapshot=case.snapshot,
        planning_input=case.planning_input,
    )

    assert blocker is not None
    assert blocker.reason == "source_pack_binding_missing"


def test_canonical_planning_without_current_source_pack_is_typed_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.planning_input = case.planning_input.model_copy(
        update={
            "final_canonical_url": case.identity.public_url,
            "inventory": SimpleNamespace(
                status="available",
                content_status="available",
                acf_section_status="missing",
            ),
            "source_assessments": [
                ContentPlanningSourceAssessment(
                    source=source,
                    status="not_applicable",
                    reason="Testowy brak źródła.",
                )
                for source in (
                    "wordpress",
                    "service_profile",
                    "gsc",
                    "ga4",
                    "google_ads",
                    "ahrefs",
                    "keyword_planner",
                    "merchant",
                    "localo",
                    "social",
                )
            ],
        }
    )
    case.store.list_content_source_pack_bindings = lambda **_: []
    case.store.list_content_delivery_identity_bindings = lambda: [case.identity]
    monkeypatch.setattr(planning_route, "content_workflow_store", lambda: case.store)
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id=case.planning_input.confirmed_service_card_id,
        expected_planning_input_digest=case.planning_input.planning_input_digest,
        requested_by="wilku",
    )

    response, bound_input, _bound_request = planning_route._prepare_and_bind_research_packet(
        work_item_id=case.identity.current_work_item_id,
        request=request,
        planning_input=case.planning_input,
        snapshot=case.snapshot,
    )

    assert response is not None
    assert response.status_code == 409
    assert bound_input is None
    assert response.body is not None
    assert json.loads(response.body)["blockers"][0]["code"] == "research_packet_missing"


def test_planning_model_context_excludes_facts_queries_and_evidence_outside_packet(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    outside_fact = ContentPlanningSourceFact(
        fact_id="outside_service_profile_fact",
        summary="Nieautoryzowany fakt usługi spoza packetu.",
        source_connector="public_site",
        evidence_ids=["ev_outside_packet"],
        source_fact_ids=["outside_service_profile_fact"],
    )
    outside_row = ContentSearchDemandRow(
        source_kind="gsc_query",
        source_connector="google_search_console",
        term="spoza packetu",
        page=case.identity.public_url,
        section_mapping_status="page_only",
        period="2026-09",
        freshness="fresh",
        evidence_ids=["ev_outside_packet"],
    )
    planning_input = case.planning_input.model_copy(
        update={
            "source_facts": [outside_fact],
            "evidence_ids": [*case.planning_input.evidence_ids, "ev_outside_packet"],
            "query_portfolio": case.planning_input.query_portfolio.model_copy(
                update={
                    "gsc_query_rows": [
                        *case.planning_input.query_portfolio.gsc_query_rows,
                        outside_row,
                    ]
                }
            ),
        }
    )
    bound = bind_research_packet_to_planning_input(planning_input, prepared.packet)

    model_input, _coverage = compact_planning_input_for_model(bound, prepared.packet)

    assert "outside_service_profile_fact" not in json.dumps(model_input)
    assert "ev_outside_packet" not in json.dumps(model_input)
    assert all(
        row["term"] != "spoza packetu"
        for row in model_input["query_portfolio"]["gsc_query_rows"]
    )
    draft_model_input = compact_initial_draft_planning_input(bound, prepared.packet)
    assert "outside_service_profile_fact" not in json.dumps(draft_model_input)
    assert "ev_outside_packet" not in json.dumps(draft_model_input)


def test_packet_projection_trims_mixed_claim_and_measurement_evidence(
    tmp_path: Path,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    prepared = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    assert prepared.packet is not None
    allowed_evidence = prepared.packet.evidence_ids[0]
    outside_evidence = "ev_outside_measurement_packet"
    planning_input = case.planning_input.model_copy(
        update={
            "claim_ledger": [
                ContentClaimLedgerEntry(
                    id="claim_mixed_packet_projection",
                    claim_text="Twierdzenie z mieszanym lineage.",
                    claim_type="service_claim",
                    status="allowed_with_evidence",
                    evidence_ids=[allowed_evidence, outside_evidence],
                    source_connectors=["public_site"],
                    reason="Test projection.",
                )
            ],
            "measurement_baseline_evidence_ids": [allowed_evidence, outside_evidence],
            "internal_link_candidates": [
                case.planning_input.internal_link_candidates[0].model_copy(
                    update={"evidence_ids": [allowed_evidence, outside_evidence]}
                )
            ],
        }
    )

    model_input, _coverage = compact_planning_input_for_model(
        bind_research_packet_to_planning_input(planning_input, prepared.packet),
        prepared.packet,
    )

    assert model_input["measurement_baseline_evidence_ids"] == [allowed_evidence]
    assert model_input["claim_ledger"][0]["evidence_ids"] == [allowed_evidence]
    assert model_input["internal_link_candidates"][0]["evidence_ids"] == [allowed_evidence]
    assert outside_evidence not in json.dumps(model_input)


def test_require_packet_blocks_without_a_pack_even_when_identity_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.planning_input = case.planning_input.model_copy(
        update={
            "final_canonical_url": case.identity.public_url,
            "inventory": SimpleNamespace(
                status="available",
                content_status="available",
                acf_section_status="missing",
            ),
            "source_assessments": [
                ContentPlanningSourceAssessment(source=source, status="missing", reason="test")
                for source in (
                    "wordpress",
                    "service_profile",
                    "gsc",
                    "ga4",
                    "google_ads",
                    "ahrefs",
                    "keyword_planner",
                    "merchant",
                    "localo",
                    "social",
                )
            ],
        }
    )

    class EmptyPacketStore:
        def list_content_source_pack_bindings(self, *, current_work_item_id: str | None = None):
            del current_work_item_id
            return []

    monkeypatch.setattr(
        proposal_packet_binding, "content_workflow_store", lambda: EmptyPacketStore()
    )
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id=case.planning_input.confirmed_service_card_id,
        expected_planning_input_digest=case.planning_input.planning_input_digest,
        requested_by="wilku",
    )

    bound, response = proposal_packet_binding.bind_research_packet(
        snapshot=case.snapshot,
        planning_input=case.planning_input,
        request=request,
        require_packet=True,
    )

    assert bound is None
    assert response is not None
    assert response.blockers[0].code == "research_packet_missing"
    assert "packet" in response.blockers[0].next_step.lower()


def test_route_packet_binding_blocks_without_a_pack_before_queueing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    case.planning_input = case.planning_input.model_copy(
        update={
            "final_canonical_url": case.identity.public_url,
            "inventory": SimpleNamespace(
                status="available",
                content_status="available",
                acf_section_status="missing",
            ),
            "source_assessments": [
                ContentPlanningSourceAssessment(source=source, status="missing", reason="test")
                for source in (
                    "wordpress",
                    "service_profile",
                    "gsc",
                    "ga4",
                    "google_ads",
                    "ahrefs",
                    "keyword_planner",
                    "merchant",
                    "localo",
                    "social",
                )
            ],
        }
    )
    case.store.list_content_source_pack_bindings = lambda **_: []
    case.store.list_content_delivery_identity_bindings = lambda: []
    monkeypatch.setattr(planning_route, "content_workflow_store", lambda: case.store)
    request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id=case.planning_input.confirmed_service_card_id,
        expected_planning_input_digest=case.planning_input.planning_input_digest,
        requested_by="wilku",
    )

    response, bound, _request = planning_route._prepare_and_bind_research_packet(
        work_item_id=case.identity.current_work_item_id,
        request=request,
        planning_input=case.planning_input,
        snapshot=case.snapshot,
    )

    assert response is not None
    assert response.status_code == 409
    assert bound is None


def test_packet_route_binding_domain_has_no_fastapi_transport_dependency() -> None:
    source = Path(route_packet_binding.__file__).read_text(encoding="utf-8")

    assert "fastapi" not in source.lower()
    assert "JSONResponse" not in source


def test_packet_preparation_is_idempotent_and_server_owned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_packet_preparation_case(tmp_path)
    first = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )
    second = prepare_content_research_packet(
        store=case.store, snapshot=case.snapshot, planning_input=case.planning_input
    )

    assert first.status == "created"
    assert second.status == "idempotent"
    assert first.packet == second.packet
    assert first.packet is not None
    assert first.packet.context_receipt is not None
    assert first.packet.cta_destination == "/kontakt/"

    monkeypatch.setattr(planning_route, "content_workflow_store", lambda: case.store)
    route_request = ContentPlanningProposalRequest(
        content_kind="service",
        service_card_id="ekologus_service_bdo_reporting",
        expected_planning_input_digest=case.planning_input.planning_input_digest,
        requested_by="wilku",
    )
    route_error, bound_input, bound_request = planning_route._prepare_and_bind_research_packet(
        work_item_id=case.identity.current_work_item_id,
        request=route_request,
        planning_input=case.planning_input,
        snapshot=case.snapshot,
    )

    assert route_error is None
    assert bound_input is not None
    assert bound_request.research_packet_id == first.packet.packet_id
    assert bound_request.expected_research_packet_digest == first.packet.packet_digest
    assert bound_request.expected_planning_input_digest == bound_input.planning_input_digest

    missing_cta = prepare_content_research_packet(
        store=case.store,
        snapshot=snapshot_without_cta(case),
        planning_input=case.planning_input,
    )

    assert missing_cta.status == "blocked"
    assert missing_cta.blocker is not None
    assert missing_cta.blocker.reason == "cta_destination_missing"
