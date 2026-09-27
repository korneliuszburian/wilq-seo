from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.actions import create_actions_router
from apps.api.wilq_api.routers.content_material_review import (
    register_content_material_review_routes,
)
from wilq.content.workflow.store import store as workflow_store_module
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)
from wilq.schemas import (
    ConnectorCapability,
    ConnectorStatus,
    ConnectorStatusValue,
    ContentDecisionItem,
    FreshnessState,
)
from wilq.storage.local_state import LocalStateStore

WORK_ITEM_ID = "content_work_item_exact_material_action"
PAGE_URL = "https://www.ekologus.pl/oferta/exact-material-action/"
PAGE_PATH = "/oferta/exact-material-action/"


def _configure_local_action_runtime(
    monkeypatch: pytest.MonkeyPatch,
    store: ContentWorkflowStore,
    audit_store: LocalStateStore,
) -> None:
    import wilq.actions.action_catalog as action_catalog
    import wilq.actions.action_validation as action_validation
    import wilq.actions.audit_store as audit_store_module
    import wilq.actions.service as action_service

    wordpress = ConnectorStatus(
        id="wordpress_ekologus",
        label="WordPress Ekologus",
        status=ConnectorStatusValue.missing_credentials,
        configured=False,
        freshness=FreshnessState(state="unknown"),
        capabilities=ConnectorCapability(read=True, write=False),
        health_check="Synthetic unconfigured test connector.",
    )

    def connector_status(connector_id: str) -> ConnectorStatus | None:
        return wordpress if connector_id == "wordpress_ekologus" else None

    monkeypatch.setattr(action_catalog, "content_workflow_store", lambda: store)
    monkeypatch.setattr(action_validation, "get_connector_status", connector_status)
    monkeypatch.setattr(action_validation, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(action_service, "get_connector_status", connector_status)
    monkeypatch.setattr(action_service, "action_content_workflow_store", lambda: store)
    monkeypatch.setattr(action_service, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(audit_store_module, "local_state_store", lambda: audit_store)
    monkeypatch.setattr(
        action_service,
        "wordpress_draft_apply_capability",
        lambda *_args, **_kwargs: pytest.fail("Local material review reached WordPress."),
    )


@pytest.fixture
def runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    now = datetime.now(UTC)
    body = {"text": "Exact current material " + ("body " * 400)}
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    catalog_item = ContentInventoryCatalogItem(
        catalog_id="catalog_exact_material_action",
        work_item_id=WORK_ITEM_ID,
        url=PAGE_URL,
        path=PAGE_PATH,
        title="Exact material action",
        content_type="page",
        content_summary="Current source material",
        content_word_count=402,
        section_count=1,
        section_headings=["Current material"],
        material_status="content_and_structure",
        source_connector="wordpress_ekologus",
        evidence_id="ev_inventory_exact_material_action",
        collected_at=now,
    )
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        ready_count=1,
        items=[catalog_item],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=[catalog_item.evidence_id],
    )
    selected = SimpleNamespace(
        id=WORK_ITEM_ID.removeprefix("content_work_item_"),
        final_canonical_url=PAGE_URL,
        source_public_url=PAGE_URL,
        normalized_page_path=PAGE_PATH,
        wordpress_content_material_confidence="review_required",
    )

    def selected_item(work_item_id: str) -> ContentDecisionItem | None:
        return cast(ContentDecisionItem, selected) if work_item_id == WORK_ITEM_ID else None

    def read_material(_url: str) -> SimpleNamespace:
        return SimpleNamespace(
            url=PAGE_URL,
            title="Bieżąca strona testowa",
            content_text=body["text"],
            extraction_region="public_html.main_or_article",
        )

    app = FastAPI()
    register_content_material_review_routes(
        app.router,
        store_factory=lambda: store,
        catalog_loader=lambda: catalog,
        selected_item_loader=selected_item,
        material_reader_factory=lambda: read_material,
        clock=lambda: datetime.now(UTC),
    )
    action_router_module_name = "apps.api.wilq_api.routers.content_material_review_action_v2"
    action_router_path = (
        Path(__file__).resolve().parents[2]
        / "apps/api/wilq_api/routers/content_material_review_action_v2.py"
    )
    action_module = None
    if action_router_path.is_file():
        action_router_module = importlib.import_module(action_router_module_name)
        action_router_module.register_content_material_review_action_v2_routes(
            app.router,
            store_factory=lambda: store,
            catalog_loader=lambda: catalog,
            selected_item_loader=selected_item,
            material_reader_factory=lambda: read_material,
            clock=lambda: datetime.now(UTC),
        )
        action_module = importlib.import_module("wilq.content.workflow.material_review_action_v2")
    app.include_router(create_actions_router(lambda: None))
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    monkeypatch.setattr(workflow_store_module, "content_workflow_store", lambda: store)

    _configure_local_action_runtime(monkeypatch, store, audit_store)
    if action_module is not None:
        original_revalidate = action_module.revalidate_content_material_review_preview

        def revalidate_fixture_material(*, work_item_id: str, preview: Any) -> Any:
            return original_revalidate(
                work_item_id=work_item_id,
                preview=preview,
                catalog_loader=lambda: catalog,
                selected_item_loader=selected_item,
                material_reader_factory=lambda: read_material,
                clock=lambda: datetime.now(UTC),
            )

        monkeypatch.setattr(
            action_module,
            "revalidate_content_material_review_preview",
            revalidate_fixture_material,
        )
    return SimpleNamespace(
        body=body, client=TestClient(app), store=store, work_item_id=WORK_ITEM_ID
    )


def _preview(client: TestClient, work_item_id: str = WORK_ITEM_ID) -> dict[str, Any]:
    response = client.post(f"/api/content/work-items/{work_item_id}/material-review-action/preview")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "preview_ready"
    assert payload["external_write_attempted"] is False
    assert "content_text" not in str(payload)
    return cast(dict[str, Any], payload)


def test_public_exact_material_text_read_is_complete_and_blocks_changed_page(
    runtime: SimpleNamespace,
) -> None:
    runtime.body["text"] = "Exact current material " + ("body " * 600)
    prepared = _preview(runtime.client)
    action_id = prepared["action_id"]
    path = (
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review-action/"
        f"{action_id}/text"
    )
    exact = runtime.client.get(path)
    assert exact.status_code == 200, exact.text
    body = exact.json()
    assert body["status"] == "exact"
    assert body["title"] == "Bieżąca strona testowa"
    assert body["text"] == runtime.body["text"].strip()
    assert len(body["text"]) > len(prepared["preview"]["observation"]["sanitized_excerpt"])
    assert body["body_digest"] == prepared["preview"]["observation"]["body_digest"]
    assert body["source_url"] == PAGE_URL
    assert runtime.store.latest_content_material_review(WORK_ITEM_ID) is None
    assert "content_text" not in str(runtime.client.get(f"/api/actions/{action_id}").json())

    runtime.body["text"] += " changed"
    stale = runtime.client.get(path)
    assert stale.status_code == 409, stale.text
    assert stale.json()["status"] == "blocked"
    assert stale.json()["blocker_code"] == "material_review_text_changed"
    assert "text" not in stale.json()


def _complete_action(
    client: TestClient,
    action_id: str,
    *,
    checked_items: list[str] | None = None,
    outcome: str = "approved_for_prepare",
) -> dict[str, Any]:
    validated = client.post(f"/api/actions/{action_id}/validate")
    assert validated.status_code == 200, validated.text
    assert validated.json()["valid"] is True, validated.text
    previewed = client.post(f"/api/actions/{action_id}/preview", json={})
    assert previewed.status_code == 200, previewed.text
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": outcome,
            "reviewed_by": "synthetic-reviewer",
            "notes": "Synthetic local ActionObject review.",
            "checked_items": checked_items or ["reviewed_full_material"],
        },
    )
    assert review.status_code == 200, review.text
    confirmed = client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "synthetic-confirmer",
            "notes": "Synthetic local confirmation.",
            "preview_acknowledged": True,
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    impact = client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "synthetic-checker", "notes": "Local impact checked."},
    )
    assert impact.status_code == 200, impact.text
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-confirmer", "notes": "Apply."},
    )
    response_payload = applied.json()
    payload = response_payload.get("detail", response_payload)
    assert "applied" in payload, (applied.status_code, payload.get("errors"))
    return cast(dict[str, Any], payload)


def test_public_action_lifecycle_approves_only_exact_reviewed_current_material(
    runtime: SimpleNamespace,
) -> None:
    client = runtime.client
    prepared = _preview(client)
    from wilq.content.workflow.material_review_action_v2 import (
        validate_current_material_review_action_v2_payload,
    )

    malformed_payload = dict(prepared["action"]["payload"])
    malformed_payload["payload_preview"] = [None]
    assert any(
        "preview row" in error
        for error in validate_current_material_review_action_v2_payload(malformed_payload)
    )
    action_id = prepared["action_id"]
    assert (
        client.get(
            f"/api/content/work-items/{WORK_ITEM_ID}/material-review-action/{action_id}"
        ).status_code
        == 200
    )
    applied = _complete_action(client, action_id)
    assert applied["applied"] is True, applied
    assert applied["adapter_result"]["external_write_attempted"] is False
    assert applied["adapter_result"]["verification_evidence_ids"]
    assert "body" not in str(applied["adapter_result"])
    approved = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/material-review")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved_current"
    action_read = client.get(f"/api/actions/{action_id}")
    assert action_read.status_code == 200, action_read.text
    approved_review_event = next(
        event
        for event in action_read.json()["audit_events"]
        if event["event_type"] == "human_review_approved_for_prepare"
    )
    assert approved.json()["review"]["reviewer"] == approved_review_event["actor"]
    assert approved.json()["review"]["reviewed_full_material"] is True
    assert "reviewed_full_material" in approved_review_event["details"]["checked_items"]
    assert approved.json()["material_meaning_digest"]

    no_attestation = _preview(client)
    blocked = _complete_action(
        client,
        no_attestation["action_id"],
        checked_items=["reviewed_url"],
    )
    assert blocked["applied"] is False
    assert any("reviewed_full_material" in error for error in blocked["errors"])
    assert (
        runtime.store.latest_content_material_review(WORK_ITEM_ID).preview_id
        == prepared["preview"]["preview_id"]
    )

    rejected = _preview(client)
    rejected_result = _complete_action(
        client,
        rejected["action_id"],
        outcome="rejected",
    )
    assert rejected_result["applied"] is False
    assert (
        runtime.store.latest_content_material_review(WORK_ITEM_ID).preview_id
        == prepared["preview"]["preview_id"]
    )

    legacy = client.post(
        f"/api/content/work-items/{WORK_ITEM_ID}/material-review",
        json={},
    )
    assert legacy.status_code == 409
    assert legacy.json()["code"] == "material_review_action_required"
    assert legacy.json()["blocker_owner"] == "WILQ content workflow"
    assert legacy.json()["safe_next_step"]

    # A new body with the same stored page identity cannot consume the old approval action.
    drifted = _preview(client)
    runtime.body["text"] += " changed"
    drift_result = _complete_action(client, drifted["action_id"])
    assert drift_result["applied"] is False
    assert any("changed" in error or "lineage" in error for error in drift_result["errors"])


def test_public_material_review_action_preview_returns_typed_missing_work_item(
    runtime: SimpleNamespace,
) -> None:
    response = runtime.client.post(
        "/api/content/work-items/content_work_item_missing/material-review-action/preview"
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["blocker_code"] == "material_review_work_item_missing"
    assert body["blocker_owner"] == "WILQ content workflow"
    assert body["safe_next_step"]
    assert body["external_write_attempted"] is False
    assert body["generation_allowed"] is False
    assert runtime.store.latest_content_material_review("content_work_item_missing") is None


def test_approved_material_receipt_clears_the_review_required_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.api.wilq_api.routers import content_workflow as content_workflow_router

    monkeypatch.setattr(content_workflow_router, "content_workflow_store", lambda: object())
    monkeypatch.setattr(
        content_workflow_router,
        "read_content_material_review",
        lambda **_: SimpleNamespace(status="approved_current"),
    )
    assert (
        content_workflow_router._semantic_material_confidence(
            work_item_id="wi_exact",
            original_confidence="review_required",
        )
        is None
    )

    seen: list[dict[str, object]] = []

    def _reader(**kwargs: object) -> SimpleNamespace:
        seen.append(kwargs)
        return SimpleNamespace(status="superseded")

    monkeypatch.setattr(content_workflow_router, "read_content_material_review", _reader)
    assert (
        content_workflow_router._semantic_material_confidence(
            work_item_id="wi_exact",
            original_confidence="review_required",
        )
        == "review_required"
    )
    assert seen and seen[0]["work_item_id"] == "wi_exact"
