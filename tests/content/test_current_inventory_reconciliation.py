from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

import wilq.content.workflow.current_inventory_reconciliation as reconciliation_module
from apps.api.wilq_api.routers.content_workflow import router as content_workflow_router
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.workflow.decisions.production import ContentProductionClassificationRun
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


def _build_http_app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(content_workflow_router)
    return test_app


async def _direct_to_thread[ResultT](
    function: Callable[..., ResultT], *args: Any, **kwargs: Any
) -> ResultT:
    return function(*args, **kwargs)


async def _post_reconciliation(test_app: FastAPI) -> Response:
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        return await client.post(
            "/api/content/inventory/reconciliation",
            json={
                "catalog": {"forged": True},
                "classification": {"generation_allowed": True},
            },
        )


def _historical_identity_command(
    run: ContentProductionClassificationRun,
) -> ContentDeliveryIdentityCommand:
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
        recorded_by="current_inventory_reconciliation_test",
        recorded_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
    )


def _catalog_for_case(
    coverage_status: str,
    *,
    item_evidence_id: str | None,
    catalog_evidence_id: str | None,
) -> ContentInventoryCatalogResponse:
    items = []
    if item_evidence_id is not None:
        items.append(
            ContentInventoryCatalogItem(
                catalog_id=f"catalog_{coverage_status}_current",
                work_item_id=f"content_work_item_{coverage_status}_current",
                url="https://www.ekologus.pl/current-eligible-outside-dated-57/",
                path="/current-eligible-outside-dated-57/",
                content_type="post",
                content_summary="Synthetic current material outside the dated keep subset.",
                material_status="content_summary",
                source_connector="wordpress_ekologus",
                evidence_id=item_evidence_id,
                collected_at=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
            )
        )
    return ContentInventoryCatalogResponse(
        total_count=len(items),
        items=items,
        source_connectors=["wordpress_ekologus"],
        evidence_ids=[] if catalog_evidence_id is None else [catalog_evidence_id],
        coverage=ContentInventoryCoverage(status=coverage_status),
    )


def _assert_blocker_response(
    response: Response,
    *,
    code: str,
    coverage_status: str,
    evidence_ids: list[str],
) -> None:
    owner, safe_next_step = {
        "inventory_coverage_incomplete": (
            "WILQ WordPress connector",
            "Zweryfikuj kompletność bieżącego odczytu publicznej mapy witryny WordPress.",
        ),
        "current_eligible_scope_policy_unavailable": (
            "WILQ content workflow",
            "Zaimplementuj dokładną politykę bieżącego zakresu kwalifikującego "
            "z kompletnego katalogu.",
        ),
        "inventory_source_evidence_missing": (
            "WILQ WordPress connector",
            "Ukończ bieżący odczyt vendor_read WordPress z identyfikatorami dowodów.",
        ),
    }[code]
    assert response.status_code == 409, response.text
    assert response.json() == {
        "detail": code,
        "owner": owner,
        "safe_next_step": safe_next_step,
        "coverage_status": coverage_status,
        "evidence_ids": evidence_ids,
    }


def test_reconciliation_blocks_unknown_and_complete_coverage_before_store_access(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    store = ContentWorkflowStore(tmp_path / "reconciliation.sqlite3")
    historical_run = exact_public_bdo_run()
    store.record_production_classification(historical_run)
    historical_identity = store.record_content_delivery_identity(
        _historical_identity_command(historical_run)
    )
    cases = (
        ("unknown", "inventory_coverage_incomplete", "ev_unknown", "ev_unknown", "ev_unknown"),
        ("partial", "inventory_coverage_incomplete", "ev_partial", "ev_partial", "ev_partial"),
        (
            "complete",
            "current_eligible_scope_policy_unavailable",
            "ev_complete",
            "ev_complete",
            "ev_complete",
        ),
        ("unknown", "inventory_coverage_incomplete", None, None, "ev_empty_catalog_source"),
        ("unknown", "inventory_source_evidence_missing", None, "ev_cached_only", None),
    )
    for coverage, code, item_id, catalog_id, source_id in cases:
        _run_blocker_case(
            monkeypatch,
            test_app,
            store,
            coverage=coverage,
            code=code,
            item_evidence_id=item_id,
            catalog_evidence_id=catalog_id,
            source_evidence_ids=[] if source_id is None else [source_id],
        )
        assert store.load_latest_production_classification() == historical_run
        assert (
            store.load_content_delivery_identity(historical_identity.binding.binding_id)
            == historical_identity.binding
        )

    operation = test_app.openapi()["paths"]["/api/content/inventory/reconciliation"]["post"]
    assert set(test_app.openapi()["paths"]["/api/content/inventory/reconciliation"]) == {"post"}
    assert "requestBody" not in operation
    assert operation["responses"]["409"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/CurrentInventoryReconciliationErrorResponse")


def _run_blocker_case(
    monkeypatch: Any,
    test_app: FastAPI,
    store: ContentWorkflowStore,
    *,
    coverage: str,
    code: str,
    item_evidence_id: str | None,
    catalog_evidence_id: str | None,
    source_evidence_ids: list[str],
) -> None:
    catalog = _catalog_for_case(
        coverage,
        item_evidence_id=item_evidence_id,
        catalog_evidence_id=catalog_evidence_id,
    )
    monkeypatch.setattr(reconciliation_module, "build_content_inventory_catalog", lambda: catalog)
    if hasattr(reconciliation_module, "preflight_current_inventory_reconciliation"):
        monkeypatch.setattr(
            reconciliation_module,
            "latest_wordpress_vendor_read_evidence_ids",
            lambda: tuple(source_evidence_ids),
        )
    spy = _StoreSpy(store)
    monkeypatch.setattr(
        reconciliation_module,
        "content_workflow_store",
        lambda: spy,
        raising=False,
    )
    response = asyncio.run(_post_reconciliation(test_app))
    _assert_blocker_response(
        response,
        code=code,
        coverage_status=coverage,
        evidence_ids=source_evidence_ids,
    )
    assert spy.calls == 0


class _StoreSpy:
    def __init__(self, delegate: ContentWorkflowStore) -> None:
        self.delegate = delegate
        self.calls = 0

    def __getattr__(self, name: str) -> Any:
        self.calls += 1
        return getattr(self.delegate, name)
