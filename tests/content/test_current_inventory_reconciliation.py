from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import wilq.content.workflow.current_inventory_reconciliation as reconciliation_module
from apps.api.wilq_api.routers.content_workflow import router as content_workflow_router
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run, ready_store
from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
    ContentProductionRegisteredInventoryReceipt,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityCommand,
    inventory_evidence_digest,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
)
from wilq.schemas import ConnectorCoveredWindow, ContentFreshnessAssessment


def _build_catalog(
    checked_at: datetime,
    *,
    evidence_id: str,
    include_url_only: bool,
) -> ContentInventoryCatalogResponse:
    items = [
        ContentInventoryCatalogItem(
            catalog_id="catalog_bdo_current",
            work_item_id="content_work_item_inventory_bdo",
            url="https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
            path="/bdo-co-musi-wiedziec-przedsiebiorca/",
            content_type="post",
            content_summary="Bieżący materiał BDO.",
            section_headings=["Zakres"],
            material_status="content_and_structure",
            source_connector="wordpress_ekologus",
            evidence_id=evidence_id,
            collected_at=checked_at,
        )
    ]
    if include_url_only:
        items.append(
            ContentInventoryCatalogItem(
                catalog_id="catalog_url_only",
                work_item_id="content_work_item_inventory_url_only",
                url="https://www.ekologus.pl/nieistniejaca-pozycja/",
                path="/nieistniejaca-pozycja/",
                content_type="post",
                material_status="url_only",
                source_connector="wordpress_ekologus",
                evidence_id=evidence_id,
                collected_at=checked_at,
            )
        )
    return ContentInventoryCatalogResponse(
        total_count=len(items),
        items=items,
        source_connectors=["wordpress_ekologus"],
        evidence_ids=[evidence_id],
        coverage=ContentInventoryCoverage(status="unknown", caveat="partial"),
    )


def _build_freshness(checked_at: datetime) -> ContentFreshnessAssessment:
    return ContentFreshnessAssessment(
        state="fresh",
        checked_at=checked_at,
        requires_refresh=False,
        connector_covered_windows={
            "google_search_console": ConnectorCoveredWindow(),
            "wordpress_ekologus": ConnectorCoveredWindow(),
        },
        summary="fresh",
        next_step="continue",
    )


def _patch_reconciliation_inputs(monkeypatch, catalog, freshness, store) -> None:
    monkeypatch.setattr(reconciliation_module, "build_content_inventory_catalog", lambda: catalog)
    monkeypatch.setattr(
        reconciliation_module,
        "build_content_freshness_assessment_fast",
        lambda **_kwargs: freshness,
    )
    monkeypatch.setattr(reconciliation_module, "content_workflow_store", lambda: store)
    monkeypatch.setattr(reconciliation_module, "_current_checkout_revision", lambda: "a" * 40)


async def _direct_to_thread(function, *args, **kwargs):
    return function(*args, **kwargs)


def _legacy_identity_command() -> ContentDeliveryIdentityCommand:
    run = exact_public_bdo_run()
    row = run.rows[0]
    assert row.current_work_item_id is not None
    evidence_ids = tuple(sorted(row.primary_evidence_ids[:1]))
    return ContentDeliveryIdentityCommand(
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        current_work_item_id=row.current_work_item_id,
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        classification_decision_set_digest=run.input.decision_set_digest,
        classification_source_row_digest=row.source_packet_row_digest,
        inventory_evidence_ids=evidence_ids,
        inventory_evidence_digest=inventory_evidence_digest(evidence_ids),
        final_disposition="keep",
        retained_work_item_id=None,
        retained_usage=None,
        recorded_by="content_delivery_test",
        recorded_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
    )


def _seed_legacy_state(path: Path):
    store = ready_store(path)
    legacy_identity = store.record_content_delivery_identity(_legacy_identity_command())
    legacy_identity_read = store.load_content_delivery_identity_record(
        legacy_identity.binding.binding_id
    )
    assert legacy_identity_read is not None
    retained_id = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding.retained_work_item_id
    assert retained_id is not None
    legacy_approval_state = store.load_draft_revision_state(retained_id)
    assert legacy_approval_state.latest_review is not None
    return store, legacy_identity, legacy_identity_read, retained_id, legacy_approval_state


def _build_http_app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(content_workflow_router)
    return test_app


def _assert_http_route_contract(test_app: FastAPI) -> None:
    operation = test_app.openapi()["paths"]["/api/content/inventory/reconciliation"]["post"]
    assert set(test_app.openapi()["paths"]["/api/content/inventory/reconciliation"]) == {"post"}
    assert "requestBody" not in operation
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/CurrentInventoryReconciliationResult")
    assert operation["responses"]["409"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/CurrentInventoryReconciliationErrorResponse")


async def _post_reconciliation(test_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        return await client.post(
            "/api/content/inventory/reconciliation",
            json={
                "catalog": {"forged": True},
                "classification": {"generation_allowed": True},
            },
        )


def _assert_all_rows_blocked(run: ContentProductionClassificationRun) -> None:
    counts = run.counts
    assert all(row.decision == "blocked" for row in run.rows)
    assert counts.blocked == counts.rows
    assert counts.generation_allowed == 0
    assert counts.verified_current_actions == 0
    assert counts.verified_current_drafts == 0


def _assert_current_row_blocked(
    run: ContentProductionClassificationRun,
) -> ContentProductionClassificationRow:
    current_row = next(
        row
        for row in run.rows
        if row.canonical_path == "/bdo-co-musi-wiedziec-przedsiebiorca"
    )
    assert current_row.decision == "blocked"
    assert current_row.generation_allowed is False
    assert isinstance(current_row.source_receipt, ContentProductionRegisteredInventoryReceipt)
    assert current_row.source_receipt.binding_state == "registered_current_inventory"
    assert current_row.source_receipt.inventory_complete is False
    assert current_row.source_receipt.delivery_identity_available is False
    assert current_row.source_receipt.source_pack_available is False
    assert current_row.revision_approved is False
    assert current_row.revision_complete is False
    assert current_row.retained_binding is None
    assert current_row.verified_actions == ()
    assert current_row.verified_drafts == ()
    return current_row


def _assert_http_result(response, store) -> None:
    assert response.status_code == 200, response.text
    result = reconciliation_module.CurrentInventoryReconciliationResult.model_validate(
        response.json()
    )
    assert result.classification.status == "created"
    assert result.registered_inventory_count == 1
    assert result.receipt_status_counts == {"created": 1, "idempotent": 0, "conflict": 0}
    assert result.classification.run.freshness.state == "fresh"
    _assert_all_rows_blocked(result.classification.run)
    current_row = _assert_current_row_blocked(result.classification.run)
    assert store.load_latest_production_classification() == result.classification.run
    stored_receipt = store.load_content_authoring_inventory_receipt(
        current_row.source_receipt.receipt_id
    )
    assert stored_receipt is not None
    assert stored_receipt.receipt_digest == current_row.source_receipt.receipt_digest


def _assert_legacy_state_unchanged(
    store,
    legacy_identity,
    legacy_identity_read,
    retained_id: str,
    legacy_approval_state,
) -> None:
    legacy_identity_after = store.load_content_delivery_identity_record(
        legacy_identity.binding.binding_id
    )
    assert legacy_identity_after is not None
    assert legacy_identity_after.binding == legacy_identity_read.binding
    assert legacy_identity_after.delivery_record == legacy_identity_read.delivery_record
    assert store.load_draft_revision_state(retained_id) == legacy_approval_state


def test_reconcile_persists_only_material_keep_receipts_and_a_blocked_run(
    monkeypatch, tmp_path: Path
) -> None:
    checked_at = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
    catalog = _build_catalog(
        checked_at,
        evidence_id="ev_wp_current_reconciliation",
        include_url_only=False,
    )
    freshness = _build_freshness(checked_at)
    store, legacy_identity, legacy_identity_read, retained_id, legacy_approval_state = (
        _seed_legacy_state(tmp_path / "http-reconciliation.sqlite3")
    )
    _patch_reconciliation_inputs(monkeypatch, catalog, freshness, store)
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    test_app = _build_http_app()
    response = asyncio.run(_post_reconciliation(test_app))
    _assert_http_result(response, store)
    _assert_http_route_contract(test_app)
    _assert_legacy_state_unchanged(
        store,
        legacy_identity,
        legacy_identity_read,
        retained_id,
        legacy_approval_state,
    )


def test_reconcile_domain_is_idempotent_for_same_material_snapshot(
    monkeypatch, tmp_path: Path
) -> None:
    checked_at = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    catalog = _build_catalog(
        checked_at,
        evidence_id="ev_wp_current",
        include_url_only=True,
    )
    freshness = _build_freshness(checked_at)
    store = ContentWorkflowStore(tmp_path / "reconciliation.sqlite3")
    _patch_reconciliation_inputs(monkeypatch, catalog, freshness, store)
    fresh_again = freshness.model_copy(
        update={"checked_at": datetime(2026, 9, 13, 12, 5, tzinfo=UTC)}
    )
    freshness_reads = iter((freshness, fresh_again))
    monkeypatch.setattr(
        reconciliation_module,
        "build_content_freshness_assessment_fast",
        lambda **_kwargs: next(freshness_reads),
    )

    first = reconciliation_module.reconcile_current_authoring_inventory()
    repeated = reconciliation_module.reconcile_current_authoring_inventory()

    assert first.classification.status == "created"
    assert first.registered_inventory_count == 1
    assert first.missing_inventory_count == 56
    _assert_all_rows_blocked(first.classification.run)
    bdo = _assert_current_row_blocked(first.classification.run)
    assert bdo.current_work_item_id == "content_work_item_inventory_bdo"
    assert repeated.classification.status == "idempotent"
    assert repeated.receipt_status_counts == {"created": 0, "idempotent": 1, "conflict": 0}
