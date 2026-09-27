from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

import wilq.content.workflow.current_inventory_reconciliation as reconciliation_module
from apps.api.wilq_api.routers.content_workflow import router as content_workflow_router
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
    inventory_work_item_id,
)
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshStatus


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


def test_reconciliation_blocks_unknown_and_partial_coverage_before_metric_read(
    monkeypatch: Any,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    cases = (
        ("unknown", "inventory_coverage_incomplete", "ev_unknown", "ev_unknown", "ev_unknown"),
        ("partial", "inventory_coverage_incomplete", "ev_partial", "ev_partial", "ev_partial"),
        ("unknown", "inventory_coverage_incomplete", None, None, "ev_empty_catalog_source"),
        ("unknown", "inventory_source_evidence_missing", None, "ev_cached_only", None),
    )
    for coverage, code, item_id, catalog_id, source_id in cases:
        _run_blocker_case(
            monkeypatch,
            test_app,
            coverage=coverage,
            code=code,
            item_evidence_id=item_id,
            catalog_evidence_id=catalog_id,
            source_evidence_ids=[] if source_id is None else [source_id],
        )

    operation = test_app.openapi()["paths"]["/api/content/inventory/reconciliation"]["post"]
    assert set(test_app.openapi()["paths"]["/api/content/inventory/reconciliation"]) == {"post"}
    assert "requestBody" not in operation
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/CurrentInventoryScopeResponse")
    assert operation["responses"]["409"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/CurrentInventoryReconciliationErrorResponse")


def _run_blocker_case(
    monkeypatch: Any,
    test_app: FastAPI,
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
    monkeypatch.setattr(
        reconciliation_module,
        "latest_wordpress_vendor_read_evidence_ids",
        lambda: tuple(source_evidence_ids),
    )
    metric_facts = _MetricFactsStore(source_evidence_ids, [])
    monkeypatch.setattr(
        reconciliation_module,
        "metric_store",
        lambda: metric_facts,
        raising=False,
    )
    response = asyncio.run(_post_reconciliation(test_app))
    _assert_blocker_response(
        response,
        code=code,
        coverage_status=coverage,
        evidence_ids=source_evidence_ids,
    )
    assert metric_facts.calls == 0


def _scope_fact(
    evidence_id: str,
    url: str,
    *,
    eligible: str,
    scope: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        name="content_object_seen",
        source_connector="wordpress_ekologus",
        evidence_id=evidence_id,
        dimensions={
            "inventory_source": "public_sitemap",
            "content_url": url,
            "editorial_eligible": eligible,
            "inventory_scope": scope,
        },
    )


def _scope_catalog_item(
    catalog_id: str,
    url: str,
    evidence_id: str,
) -> ContentInventoryCatalogItem:
    path = url.removeprefix("https://www.ekologus.pl")
    return ContentInventoryCatalogItem(
        catalog_id=catalog_id,
        work_item_id=inventory_work_item_id(url),
        url=url,
        path=path,
        content_type="post",
        content_summary="Current safe material summary.",
        material_status="content_summary",
        source_connector="wordpress_ekologus",
        evidence_id=evidence_id,
        collected_at=datetime(2026, 9, 26, 7, 8, tzinfo=UTC),
    )


class _MetricFactsStore:
    def __init__(self, evidence_ids: list[str], facts: list[Any]) -> None:
        self.evidence_ids = evidence_ids
        self.facts = facts
        self.calls = 0

    def list_metric_facts_by_evidence_ids(self, evidence_ids: list[str]) -> list[Any]:
        self.calls += 1
        assert evidence_ids == self.evidence_ids
        return self.facts


def _scope_refresh_run(evidence_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=evidence_id.removeprefix("ev_refresh_"),
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=datetime(2026, 9, 26, 7, 8, tzinfo=UTC),
        metrics_persisted=True,
        vendor_data_collected=True,
    )


def _empty_scope_catalog(evidence_ids: list[str]) -> ContentInventoryCatalogResponse:
    return ContentInventoryCatalogResponse(
        total_count=0,
        evidence_ids=evidence_ids,
        coverage=ContentInventoryCoverage(
            status="complete",
            source_count=1,
            returned_count=1,
            public_sitemap_source_count=1,
            public_sitemap_returned_count=1,
            public_sitemap_limit=2000,
            public_sitemap_truncated=False,
            limit=2000,
            truncated=False,
        ),
    )


def _use_scope_refresh_batch(
    monkeypatch: Any,
    evidence_id: str,
    *,
    freshness_state: str = "fresh",
    last_success_at: datetime | None = None,
) -> SimpleNamespace:
    run = _scope_refresh_run(evidence_id)
    freshness_time = run.completed_at if last_success_at is None else last_success_at
    monkeypatch.setattr(
        reconciliation_module,
        "local_state_store",
        lambda: SimpleNamespace(list_connector_refresh_runs=lambda connector_id: [run]),
        raising=False,
    )
    monkeypatch.setattr(
        reconciliation_module,
        "get_connector_status",
        lambda connector_id: SimpleNamespace(
            freshness=SimpleNamespace(
                state=freshness_state,
                last_success_at=freshness_time,
            )
        ),
        raising=False,
    )
    return run


def _complete_scope_case(
    evidence_id: str,
) -> tuple[ContentInventoryCatalogResponse, list[str], list[Any]]:
    urls = [
        "https://www.ekologus.pl/aktualnosci/eligible-scope/",
        "https://www.ekologus.pl/produkt/example/",
        "https://www.ekologus.pl/kategoria/poradniki/",
        "https://www.ekologus.pl/aktualnosci/unbound-scope/",
    ]
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        items=[_scope_catalog_item("catalog_exact_eligible", urls[0], evidence_id)],
        source_connectors=["wordpress_ekologus"],
        evidence_ids=[evidence_id],
        coverage=ContentInventoryCoverage(
            status="complete",
            source_count=4,
            returned_count=4,
            public_sitemap_source_count=4,
            public_sitemap_returned_count=4,
            public_sitemap_limit=2000,
            public_sitemap_truncated=False,
            limit=2000,
            truncated=False,
        ),
    )
    facts = [
        _scope_fact(evidence_id, urls[0], eligible="true", scope="editorial"),
        _scope_fact(evidence_id, urls[1], eligible="false", scope="commerce_catalog"),
        _scope_fact(evidence_id, urls[2], eligible="false", scope="taxonomy"),
        _scope_fact(evidence_id, urls[3], eligible="true", scope="editorial"),
    ]
    return catalog, urls, facts


def _use_complete_scope_sources(
    monkeypatch: Any,
    catalog: ContentInventoryCatalogResponse,
    evidence_id: str,
    facts: list[Any],
) -> None:
    _use_scope_refresh_batch(monkeypatch, evidence_id)
    monkeypatch.setattr(reconciliation_module, "build_content_inventory_catalog", lambda: catalog)
    monkeypatch.setattr(
        reconciliation_module,
        "latest_wordpress_vendor_read_evidence_ids",
        lambda: (evidence_id,),
    )
    monkeypatch.setattr(
        reconciliation_module,
        "metric_store",
        lambda: _MetricFactsStore([evidence_id], facts),
        raising=False,
    )


def test_reconciliation_returns_exact_current_sitemap_scope(monkeypatch: Any) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = "ev_refresh_current_scope"
    catalog, urls, facts = _complete_scope_case(evidence_id)
    _use_complete_scope_sources(monkeypatch, catalog, evidence_id, facts)

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "complete"
    assert result["counts"] == {
        "rows": 4,
        "eligible": 1,
        "excluded": 2,
        "blocked": 1,
    }
    rows = {row["canonical_path"]: row for row in result["rows"]}
    assert set(rows) == {
        "/aktualnosci/eligible-scope",
        "/produkt/example",
        "/kategoria/poradniki",
        "/aktualnosci/unbound-scope",
    }
    assert rows["/aktualnosci/eligible-scope"]["disposition"] == "eligible"
    assert (
        rows["/aktualnosci/eligible-scope"]["current_work_item_id"]
        == inventory_work_item_id(urls[0])
    )
    assert rows["/produkt/example"]["disposition"] == "excluded"
    assert rows["/produkt/example"]["reason_code"] == "commerce_catalog_excluded"
    assert rows["/kategoria/poradniki"]["disposition"] == "excluded"
    assert rows["/kategoria/poradniki"]["reason_code"] == "taxonomy_excluded"
    assert rows["/aktualnosci/unbound-scope"]["disposition"] == "blocked"
    assert (
        rows["/aktualnosci/unbound-scope"]["blocker_code"]
        == "editorial_catalog_binding_missing"
    )
    assert all(row["generation_allowed"] is False for row in result["rows"])


def test_reconciliation_types_canonical_scope_and_catalog_conflicts(
    monkeypatch: Any,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = "ev_refresh_scope_conflicts"
    catalog, urls, facts = _complete_scope_case(evidence_id)
    facts[0].dimensions["canonical_url"] = "https://www.ekologus.pl/other-canonical/"
    facts[2].dimensions["inventory_scope"] = "unknown_scope"
    catalog.items.append(_scope_catalog_item("catalog_commerce_conflict", urls[1], evidence_id))
    catalog.total_count = len(catalog.items)
    _use_complete_scope_sources(monkeypatch, catalog, evidence_id, facts)

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["counts"] == {"rows": 4, "eligible": 0, "excluded": 0, "blocked": 4}
    assert {row["blocker_code"] for row in result["rows"]} == {
        "inventory_canonical_url_mismatch",
        "inventory_scope_catalog_conflict",
        "inventory_scope_metadata_invalid",
        "editorial_catalog_binding_missing",
    }


def test_reconciliation_blocks_sitemap_count_mismatch(monkeypatch: Any) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = "ev_refresh_scope_count_mismatch"
    catalog, _, facts = _complete_scope_case(evidence_id)
    catalog.coverage.public_sitemap_source_count = 5
    catalog.coverage.public_sitemap_returned_count = 5
    _use_complete_scope_sources(monkeypatch, catalog, evidence_id, facts)

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 409
    assert response.json()["detail"] == "inventory_sitemap_count_mismatch"
    assert response.json()["owner"] == "WILQ WordPress connector"


def test_reconciliation_blocks_catalog_item_outside_sitemap(monkeypatch: Any) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = "ev_refresh_scope_catalog_outside"
    catalog, _, facts = _complete_scope_case(evidence_id)
    catalog.items.append(
        _scope_catalog_item(
            "catalog_not_in_sitemap",
            "https://www.ekologus.pl/aktualnosci/not-in-sitemap/",
            evidence_id,
        )
    )
    catalog.total_count = len(catalog.items)
    _use_complete_scope_sources(monkeypatch, catalog, evidence_id, facts)

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 409
    assert response.json()["detail"] == "inventory_catalog_outside_sitemap"
    assert response.json()["owner"] == "WILQ content workflow"


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("unsafe_sitemap_url", "inventory_sitemap_fact_invalid"),
        ("catalog_work_item_mismatch", "inventory_catalog_binding_invalid"),
    ],
)
def test_reconciliation_blocks_unsafe_or_fuzzy_scope_inputs(
    monkeypatch: Any,
    failure: str,
    expected_code: str,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = f"ev_refresh_{failure}"
    catalog, urls, facts = _complete_scope_case(evidence_id)
    if failure == "unsafe_sitemap_url":
        facts[0].dimensions["content_url"] = "https://attacker.example/eligible-scope/"
    else:
        catalog.items[0].work_item_id = "unbound-work-item"
    _use_complete_scope_sources(monkeypatch, catalog, evidence_id, facts)

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 409
    assert response.json()["detail"] == expected_code


def test_reconciliation_blocks_duplicate_current_sitemap_paths(
    monkeypatch: Any,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = "ev_refresh_duplicate_scope"
    url = "https://www.ekologus.pl/produkt/duplicate/"
    catalog = ContentInventoryCatalogResponse(
        total_count=0,
        evidence_ids=[evidence_id],
        coverage=ContentInventoryCoverage(
            status="complete",
            source_count=2,
            returned_count=2,
            public_sitemap_source_count=2,
            public_sitemap_returned_count=2,
            public_sitemap_limit=2000,
            public_sitemap_truncated=False,
            limit=2000,
            truncated=False,
        ),
    )
    fact = _scope_fact(evidence_id, url, eligible="false", scope="commerce_catalog")

    monkeypatch.setattr(
        reconciliation_module,
        "build_content_inventory_catalog",
        lambda: catalog,
    )
    monkeypatch.setattr(
        reconciliation_module,
        "latest_wordpress_vendor_read_evidence_ids",
        lambda: (evidence_id,),
    )
    monkeypatch.setattr(
        reconciliation_module,
        "metric_store",
        lambda: _MetricFactsStore([evidence_id], [fact, fact]),
        raising=False,
    )
    _use_scope_refresh_batch(monkeypatch, evidence_id)

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 409
    assert response.json()["detail"] == "inventory_sitemap_duplicate_url"
    assert response.json()["owner"] == "WILQ WordPress connector"
    assert response.json()["coverage_status"] == "complete"


def test_reconciliation_blocks_stale_wordpress_scope(
    monkeypatch: Any,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = "ev_refresh_stale_scope"
    catalog = ContentInventoryCatalogResponse(
        total_count=0,
        evidence_ids=[evidence_id],
        coverage=ContentInventoryCoverage(
            status="complete",
            source_count=1,
            returned_count=1,
            public_sitemap_source_count=1,
            public_sitemap_returned_count=1,
            public_sitemap_limit=2000,
            public_sitemap_truncated=False,
            limit=2000,
            truncated=False,
        ),
    )
    monkeypatch.setattr(
        reconciliation_module,
        "build_content_inventory_catalog",
        lambda: catalog,
    )
    monkeypatch.setattr(
        reconciliation_module,
        "latest_wordpress_vendor_read_evidence_ids",
        lambda: (evidence_id,),
    )
    _use_scope_refresh_batch(monkeypatch, evidence_id, freshness_state="stale")

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 409
    assert response.json()["detail"] == "inventory_source_freshness_blocked"
    assert response.json()["owner"] == "WILQ WordPress connector"
    assert response.json()["coverage_status"] == "complete"


def test_reconciliation_binds_freshness_to_exact_sitemap_batch(
    monkeypatch: Any,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    evidence_id = "ev_refresh_mismatched_scope"
    catalog = ContentInventoryCatalogResponse(
        total_count=0,
        evidence_ids=[evidence_id],
        coverage=ContentInventoryCoverage(
            status="complete",
            source_count=1,
            returned_count=1,
            public_sitemap_source_count=1,
            public_sitemap_returned_count=1,
            public_sitemap_limit=2000,
            public_sitemap_truncated=False,
            limit=2000,
            truncated=False,
        ),
    )
    monkeypatch.setattr(
        reconciliation_module,
        "build_content_inventory_catalog",
        lambda: catalog,
    )
    monkeypatch.setattr(
        reconciliation_module,
        "latest_wordpress_vendor_read_evidence_ids",
        lambda: (evidence_id,),
    )
    run = _use_scope_refresh_batch(monkeypatch, evidence_id)
    monkeypatch.setattr(
        reconciliation_module,
        "get_connector_status",
        lambda connector_id: SimpleNamespace(
            freshness=SimpleNamespace(
                state="fresh",
                last_success_at=run.completed_at - timedelta(seconds=1),
            )
        ),
        raising=False,
    )

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 409
    assert response.json()["detail"] == "inventory_source_freshness_batch_mismatch"
    assert response.json()["owner"] == "WILQ WordPress connector"


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("no_matching_run", "inventory_source_run_evidence_mismatch"),
        ("multiple_matching_runs", "inventory_source_run_evidence_mismatch"),
        ("status_probe", "inventory_source_run_incomplete"),
        ("failed_run", "inventory_source_run_incomplete"),
        ("metrics_not_persisted", "inventory_source_run_incomplete"),
        ("vendor_data_missing", "inventory_source_run_incomplete"),
        ("completion_time_missing", "inventory_source_run_incomplete"),
    ],
)
def test_reconciliation_requires_one_completed_persisted_vendor_run(
    monkeypatch: Any,
    failure: str,
    expected_code: str,
) -> None:
    test_app = _build_http_app()
    monkeypatch.setattr(asyncio, "to_thread", _direct_to_thread)
    if failure == "no_matching_run":
        evidence_ids = ("ev_refresh_missing_scope_run",)
        runs: list[SimpleNamespace] = []
    elif failure == "multiple_matching_runs":
        evidence_ids = ("ev_refresh_scope_run_one", "ev_refresh_scope_run_two")
        runs = [_scope_refresh_run(item) for item in evidence_ids]
    else:
        evidence_ids = (f"ev_refresh_{failure}",)
        run = _scope_refresh_run(evidence_ids[0])
        if failure == "status_probe":
            run.mode = ConnectorRefreshMode.status_probe
        elif failure == "failed_run":
            run.status = ConnectorRefreshStatus.failed
        elif failure == "metrics_not_persisted":
            run.metrics_persisted = False
        elif failure == "vendor_data_missing":
            run.vendor_data_collected = False
        elif failure == "completion_time_missing":
            run.completed_at = None
        runs = [run]

    catalog = _empty_scope_catalog(list(evidence_ids))
    monkeypatch.setattr(
        reconciliation_module,
        "build_content_inventory_catalog",
        lambda: catalog,
    )
    monkeypatch.setattr(
        reconciliation_module,
        "latest_wordpress_vendor_read_evidence_ids",
        lambda: evidence_ids,
    )
    monkeypatch.setattr(
        reconciliation_module,
        "local_state_store",
        lambda: SimpleNamespace(list_connector_refresh_runs=lambda connector_id: runs),
        raising=False,
    )

    response = asyncio.run(_post_reconciliation(test_app))

    assert response.status_code == 409
    assert response.json()["detail"] == expected_code
    assert response.json()["owner"] == "WILQ WordPress connector"
