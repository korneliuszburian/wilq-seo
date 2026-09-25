"""Focused per-URL identity checks for exact v3 planning intents and dispatch."""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

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
from tests.content.test_planning_generation_intent_v3 import (
    _approve_exact_packet,
    _client,
    _preview,
)
from tests.content.test_research_packet_v3_preview import _planning_result
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalResponse
from wilq.content.planning.generated_proposal_store import ContentPlanningProposalStore
from wilq.content.planning.generation_intent_v3 import (
    ApprovedPacketV3PlanningProjection,
    PlanningGenerationIntentV3Proposal,
    PlanningGenerationIntentV3Receipt,
    PlanningGenerationIntentV3Snapshot,
    planning_generation_intent_v3_action,
    planning_generation_intent_v3_action_id,
    planning_generation_intent_v3_context_digest,
    planning_generation_intent_v3_digest,
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
    ResearchPacketV3Blocker,
    ResearchPacketV3Preview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


def test_public_v3_intent_snapshot_binds_exact_per_url_identity(tmp_path: Path) -> None:
    current = _preview()
    client, store = _client(tmp_path, current)
    packet_receipt = _approve_exact_packet(store, current)

    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": packet_receipt.packet_id, "packet_digest": packet_receipt.packet_digest},
    )

    assert response.status_code == 200, response.text
    assert response.json()["snapshot"].get("per_url_delivery_identity_action_id") == (
        current.per_url_delivery_identity_action_id
    )


def test_v3_legacy_intent_snapshot_and_receipt_remain_readable_without_identity_id(
    tmp_path: Path,
) -> None:
    current = _preview()
    client, store = _client(tmp_path, current)
    packet_receipt = _approve_exact_packet(store, current)
    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": packet_receipt.packet_id, "packet_digest": packet_receipt.packet_digest},
    )
    assert response.status_code == 200, response.text
    proposal = store.load_planning_generation_intent_v3_proposal(response.json()["action_id"])
    assert proposal is not None
    current_snapshot = proposal.snapshot
    projection_payload = current_snapshot.model_dump(
        mode="python",
        exclude={
            "schema_version",
            "intent_digest",
            "context_digest",
            "generation_performed",
            "model_enqueued",
            "external_write_attempted",
        },
    )
    projection_payload.pop("per_url_delivery_identity_action_id", None)
    old_projection = ApprovedPacketV3PlanningProjection.model_validate(
        projection_payload, strict=True
    )
    old_projection_payload = old_projection.model_dump(mode="json")
    old_projection_payload.pop("per_url_delivery_identity_action_id", None)
    old_context_digest = planning_generation_intent_v3_context_digest(old_projection_payload)
    old_intent_digest = planning_generation_intent_v3_digest(old_context_digest)
    old_snapshot_payload = current_snapshot.model_dump(mode="python") | {
        "context_digest": old_context_digest,
        "intent_digest": old_intent_digest,
    }
    old_snapshot_payload.pop("per_url_delivery_identity_action_id", None)
    old_snapshot = PlanningGenerationIntentV3Snapshot.model_validate(
        old_snapshot_payload, strict=True
    )
    old_action_id = planning_generation_intent_v3_action_id(old_intent_digest)
    old_action = planning_generation_intent_v3_action(
        PlanningGenerationIntentV3Proposal(action_id=old_action_id, snapshot=old_snapshot)
    )
    assert (
        "per_url_delivery_identity_action_id"
        not in old_action.payload["planning_generation_intent_v3"]
    )

    old_receipt_snapshot = old_snapshot.model_dump(mode="json")
    old_receipt_snapshot.pop("per_url_delivery_identity_action_id", None)
    old_receipt_payload: dict[str, object] = {
        "schema_version": "wilq_planning_generation_intent_receipt_v3",
        "receipt_id": "",
        "receipt_digest": "0" * 64,
        "action_id": old_action_id,
        "action_payload_digest": "1" * 64,
        "snapshot": old_receipt_snapshot,
        "preview_audit_id": "legacy-preview",
        "review_audit_id": "legacy-review",
        "confirmation_audit_id": "legacy-confirmation",
        "impact_audit_id": "legacy-impact",
        "reviewed_by": "legacy-reviewer",
        "confirmed_by": "legacy-reviewer",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "generation_performed": False,
        "model_enqueued": False,
        "external_write_attempted": False,
    }
    old_receipt_basis = {
        key: value
        for key, value in old_receipt_payload.items()
        if key not in {"receipt_id", "receipt_digest"}
    }
    old_receipt_digest = canonical_json_digest(old_receipt_basis)
    old_receipt_payload["receipt_digest"] = old_receipt_digest
    old_receipt_payload["receipt_id"] = (
        f"content_planning_generation_intent_v3_receipt_{old_receipt_digest}"
    )
    parsed_old_receipt = PlanningGenerationIntentV3Receipt.model_validate_json(
        json.dumps(old_receipt_payload, sort_keys=True), strict=True
    )
    assert getattr(parsed_old_receipt.snapshot, "per_url_delivery_identity_action_id", None) is None


def test_public_v3_intent_blocks_if_approved_packet_per_url_identity_changes(
    tmp_path: Path,
) -> None:
    approved = _preview()
    current = approved.model_copy(
        update={"per_url_delivery_identity_action_id": "act_per_url_identity_superseded"}
    )
    client, store = _client(
        tmp_path,
        current,
        current_preview_loader=lambda _work_item_id, _identity_action_id=None: current,
    )
    receipt = _approve_exact_packet(store, approved)

    response = client.post(
        "/api/content/work-items/wi_exact/planning-generation-intent-v3/preview",
        json={"packet_id": receipt.packet_id, "packet_digest": receipt.packet_digest},
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["blocker_code"] == "per_url_delivery_identity_mismatch"
    assert body["blocker_owner"] == "WILQ content workflow"
    assert body["safe_next_step"]


def _synthetic_v3_projection_loader(
    *,
    store: ContentWorkflowStore,
    current: ResearchPacketV3Preview,
    action_ids: list[str],
    projection_context: dict[str, str | None],
) -> Callable[
    [str, str, str, str | None],
    ResearchPacketV3ModelProjection | ResearchPacketV3Blocker,
]:
    def load(
        _work_item_id: str,
        packet_id: str,
        packet_digest: str,
        per_url_delivery_identity_action_id: str | None = None,
    ) -> ResearchPacketV3ModelProjection | ResearchPacketV3Blocker:
        if projection_context.get("require_dispatch_identity") == "true":
            projection_context["dispatch_per_url_identity_action_id"] = (
                per_url_delivery_identity_action_id
            )
            if (
                per_url_delivery_identity_action_id is not None
                and per_url_delivery_identity_action_id
                != projection_context.get("observed_per_url_identity_action_id")
            ):
                return ResearchPacketV3Blocker(
                    code="per_url_delivery_identity_mismatch",
                    owner="WILQ content workflow",
                    evidence_ids=current.verification_evidence_ids,
                    safe_next_step="Odczytaj ponownie intent dla bieżącej tożsamości strony.",
                )
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
            "source_connectors": sorted(
                {
                    *(fact.source_connectors[0] for fact in current.selected_facts),
                    *(link.source_connector for link in current.internal_links),
                }
            ),
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
    Callable[
        [str, str, str, str | None],
        ResearchPacketV3ModelProjection | ResearchPacketV3Blocker,
    ],
    _SyntheticV3Queue,
]:
    actions_module = importlib.import_module("apps.api.wilq_api.routers.actions")
    dispatch_calls: list[str] = []
    queue_calls: list[dict[str, object]] = []
    action_ids: list[str] = []
    projection_context: dict[str, str | None] = {
        "digest": None,
        "dispatch_per_url_identity_action_id": None,
        "observed_per_url_identity_action_id": current.per_url_delivery_identity_action_id,
    }
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

    dispatch_module = importlib.import_module("wilq.content.planning.generation_intent_v3_dispatch")
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
        current_preview_loader=lambda _work_item_id, _identity_action_id: current,
    )
    app.include_router(create_actions_router(lambda: None))
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    _configure_local_action_runtime(monkeypatch, store, audit_store)
    packet_module = importlib.import_module(
        "apps.api.wilq_api.routers.content_research_packet_v3_preview"
    )
    monkeypatch.setattr(
        packet_module,
        "read_current_research_packet_v3_preview",
        lambda _work_item_id, per_url_delivery_identity_action_id=None: current,
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


def test_v3_intent_apply_rechecks_approved_per_url_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    current = _preview()
    assert current.per_url_delivery_identity_action_id is not None
    current_state = {"preview": current}
    identity_reads: list[str | None] = []
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    packet_receipt = _approve_exact_packet(store, current)
    app = FastAPI()

    def load_current(
        _work_item_id: str,
        identity_action_id: str | None = None,
    ) -> ResearchPacketV3Preview:
        identity_reads.append(identity_action_id)
        return current_state["preview"]

    def read_current(
        _work_item_id: str,
        *,
        per_url_delivery_identity_action_id: str | None = None,
    ) -> ResearchPacketV3Preview:
        identity_reads.append(per_url_delivery_identity_action_id)
        return current_state["preview"]

    register_content_planning_generation_intent_v3_routes(
        app.router,
        store_factory=lambda: store,
        current_preview_loader=load_current,
    )
    app.include_router(create_actions_router(lambda: None))
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    _configure_local_action_runtime(monkeypatch, store, audit_store)
    packet_module = importlib.import_module(
        "apps.api.wilq_api.routers.content_research_packet_v3_preview"
    )
    monkeypatch.setattr(packet_module, "read_current_research_packet_v3_preview", read_current)
    (
        _dispatch_calls,
        queue_calls,
        turn_calls,
        action_ids,
        _projection_context,
        _projection_loader,
        _queue,
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
        json={
            "packet_id": packet_receipt.packet_id,
            "packet_digest": packet_receipt.packet_digest,
        },
    )
    assert prepared.status_code == 200, prepared.text
    action_id = prepared.json()["action_id"]
    action_ids.append(action_id)
    assert client.post(f"/api/actions/{action_id}/validate").json()["valid"] is True
    assert client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200

    def supersede_identity() -> None:
        current_state["preview"] = current.model_copy(
            update={"per_url_delivery_identity_action_id": "act_per_url_identity_superseded"}
        )

    applied = _complete_v3_intent_lifecycle(
        client,
        action_id,
        before_apply=supersede_identity,
        expected_apply_status=409,
    )

    assert applied["applied"] is False
    assert applied["adapter_result"]["status"] == "blocked"
    assert applied["adapter_result"]["blocker"]["code"] == ("per_url_delivery_identity_mismatch")
    assert identity_reads[-1] == current.per_url_delivery_identity_action_id
    assert store.load_planning_generation_intent_v3_receipt(action_id) is None
    assert queue_calls == []
    assert turn_calls == []


def test_v3_dispatch_blocks_superseded_identity_before_queue_or_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    current = _preview()
    assert current.per_url_delivery_identity_action_id is not None
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    receipt = _approve_exact_packet(store, current)
    app = FastAPI()
    register_content_planning_generation_intent_v3_routes(
        app.router,
        store_factory=lambda: store,
        current_preview_loader=lambda _work_item_id, _identity_action_id=None: current,
    )
    app.include_router(create_actions_router(lambda: None))
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    _configure_local_action_runtime(monkeypatch, store, audit_store)
    packet_module = importlib.import_module(
        "apps.api.wilq_api.routers.content_research_packet_v3_preview"
    )
    monkeypatch.setattr(
        packet_module,
        "read_current_research_packet_v3_preview",
        lambda _work_item_id, per_url_delivery_identity_action_id=None: current,
    )
    (
        _dispatch_calls,
        queue_calls,
        turn_calls,
        action_ids,
        projection_context,
        _projection_loader,
        _queue,
    ) = _install_v3_dispatch_harness(
        current=current,
        store=store,
        audit_store=audit_store,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    projection_context["observed_per_url_identity_action_id"] = "act_per_url_identity_superseded"
    projection_context["require_dispatch_identity"] = "true"
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

    assert client.post(f"/api/actions/{action_id}/validate").json()["valid"] is True
    assert client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200
    applied = _complete_v3_intent_lifecycle(client, action_id)

    assert applied["applied"] is True
    dispatch = applied["adapter_result"]["dispatch"]
    assert dispatch["status"] == "blocked"
    assert dispatch["blocker"]["code"] == "per_url_delivery_identity_mismatch"
    assert projection_context["dispatch_per_url_identity_action_id"] == (
        current.per_url_delivery_identity_action_id
    )
    assert queue_calls == []
    assert turn_calls == []


def _assert_v3_audit_and_drift_blockers(
    *,
    action_id: str,
    store: ContentWorkflowStore,
    audit_store: LocalStateStore,
    current_audit_store: LocalStateStore,
    proposal_path: Path,
    drift_proposal_path: Path,
    projection_context: dict[str, str | None],
    projection_loader: Callable[
        [str, str, str, str | None],
        ResearchPacketV3ModelProjection | ResearchPacketV3Blocker,
    ],
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


def _complete_v3_intent_lifecycle(
    client: TestClient,
    action_id: str,
    *,
    before_apply: Callable[[], None] | None = None,
    expected_apply_status: int = 200,
) -> dict[str, object]:
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
    if before_apply is not None:
        before_apply()
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-reviewer"},
    )
    assert applied.status_code == expected_apply_status, applied.text
    body = applied.json()
    return body["detail"] if expected_apply_status == 409 else body


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
