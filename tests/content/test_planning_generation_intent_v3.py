"""Exact approved v3 packet is the only source for a v3 planning intent."""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.actions import create_actions_router
from apps.api.wilq_api.routers.content_planning_generation_intent_v3 import (
    register_content_planning_generation_intent_v3_routes,
)
from tests.content.test_generated_proposal_turn_v2 import (
    _planning_input_with_caller_context,
    _ready_inputs,
)
from tests.content.test_material_review_action_v2 import _configure_local_action_runtime
from tests.content.test_research_packet_v3_preview import _pack, _planning_result
from wilq.actions.mutation_readiness import mutation_readiness_blockers, vendor_write_possible
from wilq.actions.mutation_requirements import base_mutation_readiness_requirements
from wilq.actions.mutation_response import build_mutation_readiness_response
from wilq.actions.payload_readiness import (
    payload_apply_allowed,
    payload_preview_items,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_intent_v3 import (
    PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
    PLANNING_GENERATION_INTENT_V3_ADAPTER,
)
from wilq.content.planning.generation_intent_v3_dispatch import (
    PlanningGenerationIntentV3DispatchOutcome,
    dispatch_applied_planning_intent_v3,
)
from wilq.content.planning.input_sources import (
    ContentPlanningSourceFact,
    ContentPlanningSourceProvenance,
)
from wilq.content.planning.internal_link_candidates import ContentPlanningInternalLinkCandidate
from wilq.content.planning.packet_model_projection_v3 import ResearchPacketV3ModelProjection
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_preview import (
    ResearchPacketV3Preview,
    build_research_packet_v3_preview,
)
from wilq.content.workflow.research_packet_v3_receipt import (
    ResearchPacketV3ApprovalReceipt,
    ResearchPacketV3PreviewRecord,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)
from wilq.storage.local_state import LocalStateStore


def _preview() -> ResearchPacketV3Preview:
    preview = build_research_packet_v3_preview(
        "wi_exact", source_pack=_pack(), planning_result=_planning_result()
    )
    assert preview.status == "ready" and preview.preview_hash is not None
    return preview


def _client(
    tmp_path: Path,
    current: ResearchPacketV3Preview,
    *,
    current_preview_loader: Callable[[str], ResearchPacketV3Preview] | None = None,
) -> tuple[TestClient, ContentWorkflowStore]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    app = FastAPI()
    register_content_planning_generation_intent_v3_routes(
        app.router,
        store_factory=lambda: store,
        current_preview_loader=current_preview_loader or (lambda _work_item_id: current),
    )
    return TestClient(app), store


def _approve_exact_packet(
    store: ContentWorkflowStore,
    preview: ResearchPacketV3Preview,
) -> ResearchPacketV3ApprovalReceipt:
    assert preview.preview_hash is not None
    record = ResearchPacketV3PreviewRecord.from_preview(preview)
    assert store.record_research_packet_v3_preview(record) in {"created", "idempotent"}
    receipt = ResearchPacketV3ApprovalReceipt.from_action_chain(
        preview_hash=preview.preview_hash,
        action_id=f"act_content_research_packet_v3_{preview.preview_hash}",
        action_payload_digest="1" * 64,
        preview_audit_event_id="synthetic-preview",
        review_audit_event_id="synthetic-review",
        confirmation_audit_event_id="synthetic-confirmation",
        impact_audit_event_id="synthetic-impact",
        review_actor="synthetic-reviewer",
        verification_evidence_ids=preview.verification_evidence_ids,
        verification_evidence_digest=preview.verification_evidence_digest or "",
        approved_at=datetime.now(UTC),
    )
    status, stored = store._record_research_packet_v3_approval_receipt(receipt)
    assert status in {"created", "idempotent"}
    return stored


def _with_cta_drift(preview: ResearchPacketV3Preview) -> ResearchPacketV3Preview:
    changed = preview.model_copy(update={"cta_direction": "Umów dokładną konsultację."})
    digest = canonical_json_digest(changed.semantic_payload())
    return ResearchPacketV3Preview.model_validate(
        changed.model_dump(mode="python")
        | {
            "preview_hash": digest,
            "preview_id": f"content_research_packet_v3_{digest[:24]}",
        }
    )


def _with_work_item_drift(
    preview: ResearchPacketV3Preview,
    work_item_id: str,
) -> ResearchPacketV3Preview:
    changed = preview.model_copy(update={"work_item_id": work_item_id})
    digest = canonical_json_digest(changed.semantic_payload())
    return ResearchPacketV3Preview.model_validate(
        changed.model_dump(mode="python")
        | {
            "preview_hash": digest,
            "preview_id": f"content_research_packet_v3_{digest[:24]}",
        }
    )


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        found: set[str] = set()
        for key, child in value.items():
            found.add(key)
            found.update(_keys(child))
        return found
    if isinstance(value, list):
        return set().union(*(_keys(child) for child in value)) if value else set()
    return set()


def assert_v3_intent_local_mutation_readiness() -> None:
    action = ActionObject(
        id="act_content_planning_generation_intent_v3_readiness",
        title="Synthetic v3 intent",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=["ev_v3_readiness"],
        human_diagnosis="Synthetic local intent.",
        recommended_reason="Persist one local receipt.",
        payload={
            "action_type": PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "apply_allowed": True,
            "api_mutation_ready": True,
            "payload_preview": [{
                "apply_allowed": True,
                "api_mutation_ready": True,
            }],
        },
        validation_status="valid",
        created_by="synthetic_test",
    )
    preview = AuditEvent(
        id="audit_v3_readiness_preview",
        action_id=action.id,
        event_type="action_preview_generated",
        actor="synthetic-reviewer",
        summary="Local intent preview.",
    )
    confirmation = AuditEvent(
        id="audit_v3_readiness_confirmation",
        action_id=action.id,
        event_type="action_apply_confirmed",
        actor="synthetic-reviewer",
        summary="Local intent confirmation.",
    )
    impact = AuditEvent(
        id="audit_v3_readiness_impact",
        action_id=action.id,
        event_type="action_impact_check_completed",
        actor="synthetic-reviewer",
        summary="Local intent impact check.",
    )
    adapter = PLANNING_GENERATION_INTENT_V3_ADAPTER
    requirements = base_mutation_readiness_requirements(
        action=action,
        connector_configured=False,
        connector_evidence="missing_credentials",
        mutation_adapter=adapter,
        latest_preview=preview,
        latest_confirmation=confirmation,
        latest_impact_check=impact,
        payload_apply_allowed=lambda payload: payload_apply_allowed(
            payload, payload_preview_items(payload)
        ),
        impact_status=lambda event: "checked" if event is not None else None,
        evidence_label=lambda evidence_ids: ", ".join(evidence_ids),
    )
    connector_requirement = next(
        requirement for requirement in requirements if requirement.code == "connector_configured"
    )
    can_write = vendor_write_possible(action, adapter)
    blockers = mutation_readiness_blockers(requirements)
    readiness = build_mutation_readiness_response(
        action=action,
        mutation_adapter=adapter,
        wordpress_draft_readiness=None,
        requirements=requirements,
        blockers=blockers,
        vendor_write_possible=can_write,
        apply_contract=None,
        target={},
        operator_next_step="Synthetic readiness observation.",
        latest_mutation_audit=None,
        last_created_draft=None,
    )

    assert readiness.vendor_write_possible is False
    assert readiness.would_attempt_vendor_write is False
    assert connector_requirement.satisfied is True
    assert connector_requirement.evidence == "local_authority_only; no vendor write"
    assert not blockers


def test_v3_intent_readiness_is_local_only() -> None:
    assert_v3_intent_local_mutation_readiness()


def test_public_v3_generation_intent_blocks_when_approval_receipt_is_missing(
    tmp_path: Path,
) -> None:
    current = _preview()
    client, _store = _client(tmp_path, current)
    packet_id = f"content_research_packet_v3_{current.preview_hash[:24]}"

    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": packet_id, "packet_digest": current.preview_hash},
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["response_type"] == "planning_generation_intent_v3"
    assert body["status"] == "blocked"
    assert body["work_item_id"] == "wi_exact"
    assert body["blocker_code"] == "research_packet_v3_approval_missing"
    assert body["blocker_owner"] == "WILQ content workflow"
    assert body["evidence_ids"] == list(current.verification_evidence_ids)
    assert body["safe_next_step"]
    assert body["generation_performed"] is False
    assert body["model_enqueued"] is False
    assert body["external_write_attempted"] is False


def test_public_v3_intent_projects_only_exact_approved_packet_fields(
    tmp_path: Path,
) -> None:
    current = _preview()
    client, store = _client(tmp_path, current)
    receipt = _approve_exact_packet(store, current)
    packet_id = receipt.packet_id

    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": packet_id, "packet_digest": receipt.packet_digest},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["response_type"] == "planning_generation_intent_v3"
    assert body["generation_performed"] is False
    assert body["model_enqueued"] is False
    assert body["external_write_attempted"] is False
    snapshot = body["snapshot"]
    assert snapshot["approval_receipt_digest"] == receipt.receipt_digest
    assert snapshot["approval_action_id"] == receipt.action_id
    assert snapshot["work_item_id"] == current.work_item_id
    assert snapshot["packet_id"] == receipt.packet_id
    assert snapshot["packet_digest"] == receipt.packet_digest
    assert snapshot["content_kind"] == current.content_kind
    assert snapshot["service_card_id"] == current.service_card_id
    assert snapshot["page_url"] == current.page_url
    assert snapshot["canonical_path"] == current.canonical_path
    assert snapshot["selected_fact_ids"] == sorted(
        fact.source_fact_id for fact in current.selected_facts
    )
    assert receipt.verification_evidence_ids[0] in snapshot["evidence_ids"]
    assert snapshot["planning_context"] == current.planning_context.model_dump(mode="json")

    action = body["action"]
    action_json = json.dumps(action, ensure_ascii=False, sort_keys=True)
    assert all(fact.text not in action_json for fact in current.selected_facts)
    assert not _keys(action).intersection({"gsc_query_rows", "metric_comparisons", "source_facts"})
    assert action["payload"]["action_type"] == "content_planning_generation_intent_v3"
    assert action["payload"]["planning_generation_intent_v3"] == snapshot
    readback = client.get(
        f"/api/content/work-items/wi_exact/planning-generation-intent-v3/{body['action_id']}"
    )
    assert readback.status_code == 200, readback.text
    assert readback.json()["snapshot"] == snapshot


def test_public_v3_intent_blocks_semantic_packet_drift(
    tmp_path: Path,
) -> None:
    approved = _preview()
    current = _with_cta_drift(approved)
    client, store = _client(tmp_path, current)
    receipt = _approve_exact_packet(store, approved)

    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": receipt.packet_id, "packet_digest": receipt.packet_digest},
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["blocker_code"] == "research_packet_v3_current_drift"
    assert body["blocker_owner"] == "WILQ content workflow"
    assert body["evidence_ids"] == list(current.verification_evidence_ids)
    assert body["safe_next_step"]


@pytest.mark.parametrize(
    ("current_mode", "expected_code"),
    [
        ("unavailable", "research_packet_v3_current_read_unavailable"),
        ("identity_mismatch", "research_packet_v3_identity_mismatch"),
    ],
)
def test_public_v3_intent_blocks_unavailable_or_wrong_current_packet(
    tmp_path: Path,
    current_mode: str,
    expected_code: str,
) -> None:
    approved = _preview()
    if current_mode == "unavailable":
        def unavailable(_work_item_id: str) -> ResearchPacketV3Preview:
            raise RuntimeError("synthetic current packet read failure")

        current = approved
        loader = unavailable
    else:
        current = _with_work_item_drift(approved, "wi_other")

        def other_work_item(_work_item_id: str) -> ResearchPacketV3Preview:
            return current

        loader = other_work_item
    client, store = _client(
        tmp_path,
        current,
        current_preview_loader=loader,
    )
    receipt = _approve_exact_packet(store, approved)

    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": receipt.packet_id, "packet_digest": receipt.packet_digest},
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["blocker_code"] == expected_code
    assert body["blocker_owner"] == "WILQ content workflow"
    assert body["evidence_ids"]
    assert body["safe_next_step"]


def _synthetic_v3_projection_loader(
    *,
    store: ContentWorkflowStore,
    current: ResearchPacketV3Preview,
    action_ids: list[str],
    projection_context: dict[str, str | None],
) -> Callable[[str, str, str], ResearchPacketV3ModelProjection]:
    def load(
        _work_item_id: str,
        packet_id: str,
        packet_digest: str,
    ) -> ResearchPacketV3ModelProjection:
        proposal = store.load_planning_generation_intent_v3_proposal(action_ids[0])
        assert proposal is not None
        if projection_context["digest"] is None:
            projection_context["digest"] = proposal.snapshot.context_digest
        bound = _synthetic_bound_v3_input(current, packet_id, packet_digest)
        return ResearchPacketV3ModelProjection(
            packet=current,
            planning_input=bound,
            selected_source_facts=(),
            intent_context_digest=projection_context["digest"],
        )

    return load


def _synthetic_bound_v3_input(
    current: ResearchPacketV3Preview,
    packet_id: str,
    packet_digest: str,
) -> ContentPlanningInput:
    _source_pack_v2, seed = _ready_inputs()
    raw = _planning_input_with_caller_context(seed)
    packet_planning = _planning_result().planning_input
    selected = [
        ContentPlanningSourceFact(
            fact_id=f"planning_research_packet_v3_fact_{fact.source_fact_id}",
            summary=fact.text,
            source_connector=fact.source_connectors[0],
            evidence_ids=list(fact.evidence_ids),
            source_fact_ids=[fact.source_fact_id],
            regulatory_requirement_ids=list(fact.regulatory_requirement_ids),
        )
        for fact in current.selected_facts
    ]
    provenance = [
        ContentPlanningSourceProvenance(
            source_fact_id=fact.source_fact_id,
            source_url_or_path=fact.source_reference,
            freshness_date=fact.freshness_date,
            evidence_ids=list(fact.evidence_ids),
        )
        for fact in current.selected_facts
    ]
    inventory = raw.inventory.model_copy(
        update={
            "content_text": None,
            "content_summary": None,
            "source_field_lineage": [],
            "evidence_ids": [],
            "source_connectors": [],
            "sections": [],
        }
    )
    return raw.model_copy(
        update={
            "content_kind": "editorial",
            "confirmed_service_card_id": None,
            "service_label": None,
            "service_candidates": [],
            "final_canonical_url": current.page_url,
            "research_packet_id": packet_id,
            "research_packet_digest": packet_digest,
            "planning_input_digest": "9" * 64,
            "target_reader": current.planning_context.target_reader,
            "buyer_problem": current.planning_context.buyer_problem,
            "buyer_trigger": current.planning_context.buyer_trigger,
            "search_intent": current.planning_context.search_intent
            or "Brak zatwierdzonej intencji wyszukiwania.",
            "inventory": inventory,
            "source_facts": selected,
            "source_provenance": provenance,
            "source_assessments": packet_planning.source_assessments,
            "regulatory_coverage": packet_planning.regulatory_coverage,
            "query_portfolio": packet_planning.query_portfolio,
            "claim_ledger": [],
            "measurement_metrics": [],
            "metric_comparisons": [],
            "measurement_baseline_evidence_ids": [],
            "knowledge_card_ids": [],
            "evidence_ids": list(current.verification_evidence_ids),
            "source_connectors": sorted({
                *(fact.source_connectors[0] for fact in current.selected_facts),
                *(link.source_connector for link in current.internal_links),
            }),
            "baseline_cta_direction": current.cta_direction,
            "minimum_cta_blocks": current.minimum_cta_blocks,
            "required_cta_patterns": list(current.required_cta_patterns),
            "internal_link_candidates": [
                ContentPlanningInternalLinkCandidate(
                    target_url=link.target_url,
                    anchor_hint=link.anchor_hint,
                    evidence_ids=list(link.evidence_ids),
                )
                for link in current.internal_links
            ],
        }
    )


def _synthetic_v3_generation_turn(
    *,
    current: ResearchPacketV3Preview,
    turn_calls: list[dict[str, object]],
    **kwargs: object,
) -> ContentPlanningProposalResponse:
    planning_input = kwargs["prepared_planning_input"]
    turn_builder = kwargs["turn_request_builder"]
    turn = turn_builder(planning_input, "")
    payload = json.loads(turn.untrusted_context)["planning_input"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "UNREVIEWED OLD WP CLAIM" not in serialized
    assert "UNREVIEWED OLD WP BODY" not in serialized
    assert payload["query_portfolio"]["gsc_query_rows"] == []
    assert [fact["source_fact_ids"] for fact in payload["source_facts"]] == [
        [selected.source_fact_id] for selected in current.selected_facts
    ]
    turn_calls.append(payload)
    guard = kwargs["pre_persistence_guard"]
    assert callable(guard)
    assert guard() is None
    request = kwargs["request"]
    return ContentPlanningProposalResponse(
        status="generating",
        work_item_id=planning_input.work_item_id,
        content_kind=request.content_kind,
        service_card_id=request.service_card_id,
        planning_input_digest=request.expected_planning_input_digest,
        research_packet_id=request.research_packet_id,
        research_packet_digest=request.expected_research_packet_digest,
        safe_next_step="Synthetic model turn stayed inside v3 projection.",
    )


class _SyntheticV3Queue:
    def __init__(self, run_path: Path, calls: list[dict[str, object]]) -> None:
        self.run_path = run_path
        self.calls = calls

    def __call__(self, **kwargs: object) -> ContentPlanningProposalResponse:
        self.calls.append(kwargs)
        guard = kwargs["generation_guard"]
        assert callable(guard)
        assert guard() is None
        runner = kwargs["generation_runner"]
        assert callable(runner)
        request = kwargs["request"]
        runner(
            snapshot=SimpleNamespace(
                preflight=SimpleNamespace(item=SimpleNamespace(id=kwargs["work_item_id"]))
            ),
            request=request,
            client=SimpleNamespace(),
            store=kwargs["store"],
            run_store=LocalStateStore(self.run_path),
            pre_persistence_guard=guard,
            refresh_preparation_binding=None,
        )
        return ContentPlanningProposalResponse(
            status="generating",
            work_item_id=str(kwargs["work_item_id"]),
            content_kind=request.content_kind,
            service_card_id=request.service_card_id,
            planning_input_digest=request.expected_planning_input_digest,
            research_packet_id=request.research_packet_id,
            research_packet_digest=request.expected_research_packet_digest,
            safe_next_step="Synthetic queue observed exact guarded request.",
        )


def _install_v3_dispatch_harness(
    *,
    current: ResearchPacketV3Preview,
    store: ContentWorkflowStore,
    audit_store: LocalStateStore,
    tmp_path: Path,
    monkeypatch,
) -> tuple[
    list[str],
    list[dict[str, object]],
    list[dict[str, object]],
    list[str],
    dict[str, str | None],
    Callable[[str, str, str], ResearchPacketV3ModelProjection],
    _SyntheticV3Queue,
]:
    actions_module = importlib.import_module("apps.api.wilq_api.routers.actions")
    dispatch_calls: list[str] = []
    queue_calls: list[dict[str, object]] = []
    action_ids: list[str] = []
    projection_context: dict[str, str | None] = {"digest": None}
    projection_loader = _synthetic_v3_projection_loader(
        store=store,
        current=current,
        action_ids=action_ids,
        projection_context=projection_context,
    )
    queue = _SyntheticV3Queue(tmp_path / "synthetic-run.sqlite3", queue_calls)
    turn_calls: list[dict[str, object]] = []

    def synthetic_dispatch(action_id: str) -> PlanningGenerationIntentV3DispatchOutcome:
        dispatch_calls.append(action_id)
        return dispatch_applied_planning_intent_v3(
            action_id,
            workflow_store=store,
            audit_store=audit_store,
            proposal_store=ContentPlanningProposalStore(tmp_path / "proposal.sqlite3"),
            snapshot_loader=lambda _id: None,  # type: ignore[arg-type]
            enqueue=queue,
            projection_loader=projection_loader,
        )

    dispatch_module = importlib.import_module(
        "wilq.content.planning.generation_intent_v3_dispatch"
    )
    monkeypatch.setattr(
        dispatch_module,
        "generate_content_planning_proposal",
        lambda **kwargs: _synthetic_v3_generation_turn(
            current=current, turn_calls=turn_calls, **kwargs
        ),
    )
    monkeypatch.setattr(actions_module, "_post_apply_planning_dispatch_v3", synthetic_dispatch)
    return (
        dispatch_calls,
        queue_calls,
        turn_calls,
        action_ids,
        projection_context,
        projection_loader,
        queue,
    )


def test_generic_action_lifecycle_persists_only_local_v3_intent_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    current = _preview()
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    receipt = _approve_exact_packet(store, current)
    app = FastAPI()
    register_content_planning_generation_intent_v3_routes(
        app.router,
        store_factory=lambda: store,
        current_preview_loader=lambda _work_item_id: current,
    )
    app.include_router(create_actions_router(lambda: None))
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    _configure_local_action_runtime(monkeypatch, store, audit_store)
    packet_module = importlib.import_module(
        "apps.api.wilq_api.routers.content_research_packet_v3_preview"
    )
    monkeypatch.setattr(
        packet_module, "read_current_research_packet_v3_preview", lambda _work_item_id: current
    )
    (
        dispatch_calls,
        queue_calls,
        turn_calls,
        action_ids,
        projection_context,
        projection_loader,
        queue,
    ) = _install_v3_dispatch_harness(
        current=current,
        store=store,
        audit_store=audit_store,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    client = TestClient(app)
    prepared = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": receipt.packet_id, "packet_digest": receipt.packet_digest},
    )
    assert prepared.status_code == 200, prepared.text
    action_id = prepared.json()["action_id"]
    action_ids.append(action_id)
    before_apply = importlib.import_module(
        "apps.api.wilq_api.routers.actions"
    )._post_apply_planning_dispatch_v3(action_id)
    assert before_apply.status == "blocked"
    assert before_apply.blocker is not None
    assert before_apply.blocker.code == "generation_intent_v3_receipt_missing"
    assert queue_calls == []
    _assert_public_mutation_readiness(client, action_id)
    validation = client.post(f"/api/actions/{action_id}/validate").json()
    assert validation["valid"] is True, json.dumps(validation, indent=2)
    assert client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200
    applied = _complete_v3_intent_lifecycle(client, action_id)
    assert applied["applied"] is True
    adapter_result = applied["adapter_result"]
    assert adapter_result["generation_performed"] is False
    assert adapter_result["model_enqueued"] is False
    assert adapter_result["external_write_attempted"] is False
    stored = store.load_planning_generation_intent_v3_receipt(action_id)
    assert stored is not None
    assert stored.generation_performed is False
    assert stored.model_enqueued is False
    assert stored.external_write_attempted is False
    assert dispatch_calls == [action_id, action_id]
    assert adapter_result["dispatch"]["status"] == "accepted"
    assert adapter_result["dispatch"]["external_write_attempted"] is False
    assert queue_calls[0]["request"].research_packet_id == receipt.packet_id
    assert queue_calls[0]["request"].expected_research_packet_digest == receipt.packet_digest
    assert len(turn_calls) == 1
    _assert_v3_audit_and_drift_blockers(
        store=store,
        audit_store=LocalStateStore(tmp_path / "missing-audit.sqlite3"),
        current_audit_store=audit_store,
        proposal_path=tmp_path / "missing-audit-proposal.sqlite3",
        drift_proposal_path=tmp_path / "drift-proposal.sqlite3",
        action_id=action_id,
        projection_context=projection_context,
        projection_loader=projection_loader,
        fake_queue=queue,
    )


def _assert_v3_audit_and_drift_blockers(
    *,
    action_id: str,
    store: ContentWorkflowStore,
    audit_store: LocalStateStore,
    current_audit_store: LocalStateStore,
    proposal_path: Path,
    drift_proposal_path: Path,
    projection_context: dict[str, str | None],
    projection_loader: Callable[[str, str, str], ResearchPacketV3ModelProjection],
    fake_queue: _SyntheticV3Queue,
) -> None:
    without_apply_audit = dispatch_applied_planning_intent_v3(
        action_id,
        workflow_store=store,
        audit_store=audit_store,
        proposal_store=ContentPlanningProposalStore(proposal_path),
        snapshot_loader=lambda _id: None,  # type: ignore[arg-type]
        enqueue=fake_queue,
        projection_loader=projection_loader,
    )
    assert without_apply_audit.status == "blocked"
    assert without_apply_audit.blocker is not None
    assert without_apply_audit.blocker.code == "generation_intent_v3_apply_audit_missing"
    assert len(fake_queue.calls) == 1

    def drift_queue(**kwargs: object) -> ContentPlanningProposalResponse:
        projection_context["digest"] = "0" * 64
        result = kwargs["generation_guard"]()
        assert result is not None and result.status == "blocked"
        return result

    current_drift = dispatch_applied_planning_intent_v3(
        action_id,
        workflow_store=store,
        audit_store=current_audit_store,
        proposal_store=ContentPlanningProposalStore(drift_proposal_path),
        snapshot_loader=lambda _id: None,  # type: ignore[arg-type]
        enqueue=drift_queue,
        projection_loader=projection_loader,
    )
    assert current_drift.status == "blocked"
    assert current_drift.blocker is not None
    assert current_drift.blocker.code == "research_packet_v3_current_drift"
    assert store.load_planning_generation_intent_receipt(action_id) is None


def _complete_v3_intent_lifecycle(client: TestClient, action_id: str) -> dict[str, object]:
    reviewed = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "synthetic-reviewer",
            "notes": "Reviewed exact approved v3 planning intent.",
            "checked_items": ["reviewed_exact_generation_intent_v3"],
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    confirmed = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "synthetic-reviewer",
            "notes": "Local intent receipt only.",
            "preview_acknowledged": True,
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    impact = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "synthetic-reviewer", "notes": "No external write."},
    )
    assert impact.status_code == 200, impact.text
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-reviewer"},
    )
    assert applied.status_code == 200, applied.text
    return applied.json()


def _assert_public_mutation_readiness(client: TestClient, action_id: str) -> None:
    response = client.get(f"/api/actions/{action_id}/mutation-readiness")
    assert response.status_code == 200, response.text
    readiness = response.json()
    assert readiness["vendor_write_possible"] is False
    assert readiness["would_attempt_vendor_write"] is False
    connector = next(
        item for item in readiness["requirements"] if item["code"] == "connector_configured"
    )
    assert connector["satisfied"] is True
    assert connector["evidence"] == "local_authority_only; no vendor write"
