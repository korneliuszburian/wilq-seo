from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import apps.api.wilq_api.routers.content_initial_draft as initial_draft_router
import apps.api.wilq_api.routers.content_planning_proposals as planning_router
import apps.api.wilq_api.routers.content_research_packet as packet_router
import apps.api.wilq_api.routers.content_source_fact_authority as authority_router
import apps.api.wilq_api.routers.content_source_pack_binding as source_pack_router
import wilq.actions.action_catalog as action_catalog
import wilq.actions.action_validation as action_validation_module
import wilq.actions.audit_store as audit_store_module
import wilq.actions.service as action_service
import wilq.content.workflow.store.store as workflow_store_module
from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers.content_initial_draft import register_content_initial_draft_route
from apps.api.wilq_api.routers.content_planning_proposals import (
    register_content_planning_proposal_routes,
)
from apps.api.wilq_api.routers.content_refresh_preparation import (
    register_content_refresh_preparation_routes,
)
from apps.api.wilq_api.routers.content_research_packet import (
    register_content_research_packet_routes,
)
from tests.content.dynamic_planning_test_support import configure_planning_harness
from tests.content.initial_draft_authority_fakes import _rebuild_run, exact_public_bdo_run
from tests.content.test_delivery_identity_binding import _command as identity_command
from wilq.content.planning import planning_generation_queue
from wilq.content.planning.generated_proposal_store import content_planning_proposal_store
from wilq.content.workflow.decisions.planning import build_content_planning_workspace
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityCommand
from wilq.content.workflow.refresh_preparation import ContentRefreshPreparationAuthority
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


class _InlineExecutor:
    def submit(self, fn: Any, /, *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)


def _patch_public_stores(monkeypatch: pytest.MonkeyPatch, store: ContentWorkflowStore) -> None:
    monkeypatch.setattr(authority_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(source_pack_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(packet_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(planning_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(initial_draft_router, "content_workflow_store", lambda: store)
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)
    if hasattr(action_catalog, "content_workflow_store"):
        monkeypatch.setattr(action_catalog, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    audit_store = LocalStateStore(store.path.parent / "audit.sqlite3")
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(action_validation_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(audit_store_module, "local_state_store", lambda: audit_store)


def _loader_with_typed_cta(monkeypatch: pytest.MonkeyPatch):
    from apps.api.wilq_api.routers.content_snapshot import snapshot_for_work_item_or_404

    def loader(work_item_id: str, _service_card_id: str | None = None):
        snapshot = snapshot_for_work_item_or_404(
            work_item_id,
            resolve_planning_proposal=False,
        )
        brief = snapshot.sales_brief.sales_brief_result.brief
        if brief is None:
            return snapshot
        brief_result = snapshot.sales_brief.sales_brief_result.model_copy(
            update={"brief": brief.model_copy(update={"cta_destination": "/kontakt/"})}
        )
        snapshot = snapshot.model_copy(
            update={
                "sales_brief": snapshot.sales_brief.model_copy(
                    update={"sales_brief_result": brief_result}
                )
            }
        )
        proposal = content_planning_proposal_store().latest(work_item_id)
        if proposal is not None:
            snapshot = snapshot.model_copy(
                update={
                    "planning_workspace": build_content_planning_workspace(proposal, [])
                }
            )
        return snapshot

    return loader


def _public_chain_app(
    monkeypatch: pytest.MonkeyPatch,
    loader: Any,
    store: ContentWorkflowStore,
) -> FastAPI:
    router = APIRouter()
    register_content_research_packet_routes(router, snapshot_loader=loader)

    def authority_factory() -> ContentRefreshPreparationAuthority:
        return ContentRefreshPreparationAuthority(
            store=store,
            snapshot_loader=loader,
            proposal_store=content_planning_proposal_store(),
        )
    register_content_refresh_preparation_routes(
        router,
        authority_factory=authority_factory,
    )
    register_content_planning_proposal_routes(
        router,
        snapshot_loader=loader,
        refresh_authority_factory=authority_factory,
    )
    register_content_initial_draft_route(
        router,
        snapshot_loader=loader,
        refresh_authority_factory=authority_factory,
    )
    monkeypatch.setattr(
        planning_generation_queue, "_PLANNING_GENERATION_EXECUTOR", _InlineExecutor()
    )
    application = FastAPI()
    application.include_router(router)
    return application


def _wait_for_plan(client: TestClient, work_item_id: str) -> dict[str, Any]:
    for _ in range(20):
        payload = client.get(
            f"/api/content/work-items/{work_item_id}/planning-proposals"
        ).json()
        if payload.get("status") != "generating":
            return payload
        time.sleep(0.01)
    return payload


def _seed_http_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ContentWorkflowStore, Any, Any]:
    _, runtime = configure_planning_harness(monkeypatch, tmp_path)
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    run = exact_public_bdo_run()
    refresh_row = run.rows[0].model_copy(
        update={
            "decision": "refresh",
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "revision_approved": False,
            "revision_complete": False,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    run = _rebuild_run(run, (refresh_row, run.rows[1]))
    store.record_production_classification(run)
    identity_payload = identity_command(retained=True, run=exact_public_bdo_run()).model_dump(
        mode="python"
    )
    identity_payload.update(
        {
            "classification_run_id": run.run_id,
            "classification_run_digest": run.run_digest,
            "classification_source_row_digest": refresh_row.source_packet_row_digest,
            "retained_work_item_id": None,
            "retained_usage": None,
        }
    )
    identity = store.record_content_delivery_identity(
        ContentDeliveryIdentityCommand.model_validate(identity_payload)
    ).binding
    _patch_public_stores(monkeypatch, store)
    return store, identity, runtime


def _record_authority_source_pack(authority_client: TestClient, identity: Any) -> None:
    preview = authority_client.post(
        "/api/content/source-fact-authority-reviews/preview",
        json={
            "identity_binding_id": identity.binding_id,
            "proposed_source_fact_ids": ["ekologus_public_bdo_faq_2026_07_01"],
        },
    )
    assert preview.status_code == 200, preview.text
    action_id = preview.json()["action"]["id"]
    assert authority_client.post(f"/api/actions/{action_id}/validate").json()["valid"] is True
    assert authority_client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200
    assert authority_client.post(
        f"/api/actions/{action_id}/review",
        json={"outcome": "approved_for_prepare", "reviewed_by": "wilku", "notes": "exact"},
    ).status_code == 200
    assert authority_client.post(
        f"/api/actions/{action_id}/confirm",
        json={"confirmed_by": "wilku", "notes": "exact", "preview_acknowledged": True},
    ).status_code == 200
    assert authority_client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "wilku", "notes": "exact"},
    ).status_code == 200
    applied = authority_client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "wilku"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["adapter_result"]["external_write_attempted"] is False

    prerequisites = authority_client.get(
        f"/api/content/source-pack-bindings/prerequisites/{identity.binding_id}"
    )
    assert prerequisites.status_code == 200, prerequisites.text
    prerequisite_payload = prerequisites.json()
    source_pack = authority_client.post(
        "/api/content/source-pack-bindings",
        json={
            "source_pack_id": "source_pack_http_packet_chain",
            "source_pack_sha256": "a" * 64,
            "identity_binding_id": prerequisite_payload["identity_binding_id"],
            "identity_binding_digest": prerequisite_payload["identity_binding_digest"],
            "current_work_item_id": prerequisite_payload["current_work_item_id"],
            "source_fact_ids": prerequisite_payload["approved_source_fact_ids"],
            "evidence_ids": prerequisite_payload["row_authority_evidence_ids"],
            "fresh_context_digest": prerequisite_payload["fresh_context_digest"],
            "source_fact_registry_receipt": prerequisite_payload["source_fact_registry_receipt"],
            "fresh_context_attestation": prerequisite_payload["fresh_context_attestation"],
            "recorded_by": "http_packet_chain",
            "recorded_at": prerequisite_payload["source_fact_registry_receipt"]["checked_at"],
        },
    )
    assert source_pack.status_code == 201, source_pack.text
    source_pack_payload = source_pack.json()["binding"]
    assert source_pack_payload["status"] == "exact_current"
    assert authority_client.get(
        f"/api/content/source-pack-bindings/{source_pack_payload['binding_id']}"
    ).json()["binding"] == source_pack_payload


def _authorize_refresh(
    client: TestClient,
    work_item_id: str,
    planning_input_digest: str,
) -> dict[str, Any]:
    refresh = client.get(
        f"/api/content/work-items/{work_item_id}/refresh-preparation",
        params={"service_card_id": "ekologus_service_bdo_reporting"},
    )
    assert refresh.status_code == 200, refresh.text
    refresh_payload = refresh.json()
    assert refresh_payload["status"] == "ready_to_authorize", refresh_payload
    classification = refresh_payload["classification"]
    authorization = client.post(
        f"/api/content/work-items/{work_item_id}/refresh-preparation/authorizations",
        json={
            "expected_production_classification_run_digest": classification[
                "classification_run_digest"
            ],
            "expected_production_classification_decision_set_digest": classification[
                "decision_set_digest"
            ],
            "expected_production_classification_source_packet_row_digest": classification[
                "source_packet_row_digest"
            ],
            "expected_planning_input_digest": planning_input_digest,
            "service_card_id": "ekologus_service_bdo_reporting",
            "authorized_by": "wilku",
            "acknowledged_classification_blocker_codes": classification[
                "classification_blocker_codes"
            ],
        },
    )
    assert authorization.status_code == 201, authorization.text
    return authorization.json()["authorization"]


def _assert_plan_and_draft_chain(
    client: TestClient,
    work_item_id: str,
    planning_input_digest: str,
    authorization: dict[str, Any],
) -> str:
    planning_post = client.post(
        f"/api/content/work-items/{work_item_id}/planning-proposals",
        json={
            "content_kind": "service",
            "service_card_id": "ekologus_service_bdo_reporting",
            "expected_planning_input_digest": planning_input_digest,
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    assert planning_post.status_code == 200, planning_post.text
    if planning_post.json().get("status") == "blocked":
        raise AssertionError(json.dumps(planning_post.json(), ensure_ascii=False, indent=2))
    ready = _wait_for_plan(client, work_item_id)
    assert ready["status"] in {"ready", "idempotent"}, {
        "posted": planning_post.json(),
        "read": ready,
    }
    assert ready["research_packet_id"]
    assert ready["research_packet_digest"]
    assert ready["proposal"]["research_packet_id"] == ready["research_packet_id"]
    assert ready["proposal"]["research_packet_digest"] == ready["research_packet_digest"]
    packet_read = client.get(
        f"/api/content/research-packets/{ready['research_packet_id']}"
    )
    assert packet_read.status_code == 200, packet_read.text
    packet_payload = packet_read.json()["packet"]
    assert packet_payload["packet_digest"] == ready["research_packet_digest"]
    assert packet_payload["status"] == "exact_current"
    current_projection = packet_read.json()["current"]
    assert current_projection["status"] == "current"
    assert current_projection["packet_id"] == ready["research_packet_id"]
    assert current_projection["packet_digest"] == ready["research_packet_digest"]

    draft_post = client.post(
        f"/api/content/work-items/{work_item_id}/initial-draft",
        json={
            "expected_proposal_id": ready["proposal"]["proposal_id"],
            "expected_planning_digest": ready["proposal"]["planning_digest"],
            "expected_planning_input_digest": ready["proposal"]["planning_input_digest"],
            "requested_by": "wilku",
            "refresh_preparation_authorization_id": authorization["authorization_id"],
            "expected_refresh_preparation_authorization_digest": authorization[
                "authorization_digest"
            ],
        },
    )
    assert draft_post.status_code == 200, draft_post.text
    draft = draft_post.json()
    if draft["status"] == "generating":
        draft_read = client.get(f"/api/content/work-items/{work_item_id}/initial-draft")
        assert draft_read.status_code == 200, draft_read.text
        draft = draft_read.json()
    assert draft["status"] == "created", draft
    draft_read = client.get(f"/api/content/work-items/{work_item_id}/initial-draft")
    assert draft_read.status_code == 200, draft_read.text
    draft = draft_read.json()
    assert draft["status"] == "created", draft["blockers"]
    assert draft["revision"] is not None, draft
    revision = draft["revision"]
    assert revision["research_packet_id"] == ready["research_packet_id"]
    assert revision["research_packet_digest"] == ready["research_packet_digest"]
    assert revision["proposal_metadata"]["research_packet_id"] == ready["research_packet_id"]
    assert revision["proposal_metadata"]["research_packet_digest"] == ready[
        "research_packet_digest"
    ]
    return ready["research_packet_id"]


def test_public_http_packet_plan_draft_chain_is_exact_and_local_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, identity, runtime = _seed_http_identity(tmp_path, monkeypatch)
    authority_client = TestClient(app)
    _record_authority_source_pack(authority_client, identity)

    loader = _loader_with_typed_cta(monkeypatch)
    chain_app = _public_chain_app(monkeypatch, loader, store)
    client = TestClient(chain_app)
    work_item_id = identity.current_work_item_id
    before = client.get(f"/api/content/work-items/{work_item_id}/planning-proposals")
    assert before.status_code == 200, before.text
    before_payload = before.json()
    authorization = _authorize_refresh(
        client, work_item_id, before_payload["planning_input_digest"]
    )
    packet_id = _assert_plan_and_draft_chain(
        client,
        work_item_id,
        before_payload["planning_input_digest"],
        authorization,
    )
    current_classification = store.load_production_classification_for_work_item(work_item_id)
    assert current_classification is not None
    drifted_classification = current_classification.model_copy(
        update={"decision_set_digest": "f" * 64}
    )
    monkeypatch.setattr(
        store,
        "load_production_classification_for_work_item",
        lambda _work_item_id: drifted_classification,
    )
    drifted_read = client.get(f"/api/content/research-packets/{packet_id}")
    assert drifted_read.status_code == 200, drifted_read.text
    assert drifted_read.json()["current"]["status"] == "blocked"
    assert drifted_read.json()["current"]["blocker"]["reason"] == (
        "identity_binding_blocked"
    )
    assert runtime.calls >= 2
