"""Exact approved v3 packet is the only source for a v3 planning intent."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_planning_generation_intent_v3 import (
    register_content_planning_generation_intent_v3_routes,
)
from tests.content.test_research_packet_v3_preview import _pack, _planning_result
from wilq.actions.mutation_readiness import mutation_readiness_blockers, vendor_write_possible
from wilq.actions.mutation_requirements import base_mutation_readiness_requirements
from wilq.actions.mutation_response import build_mutation_readiness_response
from wilq.actions.payload_readiness import (
    payload_apply_allowed,
    payload_preview_items,
)
from wilq.content.planning.generation_intent_v3 import (
    PLANNING_GENERATION_INTENT_V3_ACTION_TYPE,
    PLANNING_GENERATION_INTENT_V3_ADAPTER,
)
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
    current_preview_loader: Callable[[str, str | None], ResearchPacketV3Preview] | None = None,
) -> tuple[TestClient, ContentWorkflowStore]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    app = FastAPI()
    register_content_planning_generation_intent_v3_routes(
        app.router,
        store_factory=lambda: store,
        current_preview_loader=current_preview_loader
        or (lambda _work_item_id, _identity_action_id=None: current),
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
    assert snapshot.get("per_url_delivery_identity_action_id") == (
        current.per_url_delivery_identity_action_id
    )
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
        def unavailable(
            _work_item_id: str,
            _identity_action_id: str | None,
        ) -> ResearchPacketV3Preview:
            raise RuntimeError("synthetic current packet read failure")

        current = approved
        loader = unavailable
    else:
        current = _with_work_item_drift(approved, "wi_other")

        def other_work_item(
            _work_item_id: str,
            _identity_action_id: str | None,
        ) -> ResearchPacketV3Preview:
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
