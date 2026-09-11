from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import wilq.content.workflow.decisions.inventory_binding as inventory_binding
import wilq.content.workflow.workspace.catalog as catalog_module
from wilq.content.workflow.decisions.inventory_binding import (
    content_kind_inventory_binding_for_work_item,
    inventory_decision_for_work_item,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
    ContentInventoryRestObject,
    inventory_work_item_id,
)

PUBLIC_URL = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
WORK_ITEM_ID = inventory_work_item_id(PUBLIC_URL)


def _catalog(rest_objects: list[ContentInventoryRestObject]) -> ContentInventoryCatalogResponse:
    return ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_integrated_permit",
                work_item_id=WORK_ITEM_ID,
                url=PUBLIC_URL,
                path="/analiza-pozwolen-zintegrowanych/",
                title="Analiza pozwoleń zintegrowanych",
                content_type="sitemap",
                material_status="url_only",
                source_connector="wordpress_ekologus",
                evidence_id="ev_public_inventory",
                collected_at=datetime(2026, 9, 1, tzinfo=UTC),
            )
        ],
        rest_content_objects=rest_objects,
        coverage=ContentInventoryCoverage(status="complete"),
    )


def test_exact_dev_rest_type_classifies_and_attaches_its_evidence(
    monkeypatch,
) -> None:
    catalog = _catalog(
        [
            ContentInventoryRestObject(
                url="https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
                content_type="posts",
                evidence_id="ev_dev_posts",
            )
        ]
    )
    monkeypatch.setattr(inventory_binding, "build_content_inventory_catalog", lambda: catalog)
    monkeypatch.setattr(inventory_binding, "inventory_metric_facts", lambda *_args: [])

    decision = inventory_decision_for_work_item(
        WORK_ITEM_ID,
        read_material=False,
        allow_material_pending=True,
    )

    assert decision is not None
    assert decision.wordpress_content_type == "posts"
    assert decision.content_kind == "editorial"
    assert decision.evidence_ids == ["ev_public_inventory", "ev_dev_posts"]


def test_conflicting_exact_dev_types_do_not_classify_or_attach_evidence(monkeypatch) -> None:
    catalog = _catalog(
        [
            ContentInventoryRestObject(
                url="https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
                content_type="posts",
                evidence_id="ev_dev_posts",
            ),
            ContentInventoryRestObject(
                url="https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
                content_type="pages",
                evidence_id="ev_dev_pages",
            ),
        ]
    )
    monkeypatch.setattr(inventory_binding, "build_content_inventory_catalog", lambda: catalog)
    monkeypatch.setattr(inventory_binding, "inventory_metric_facts", lambda *_args: [])

    decision = inventory_decision_for_work_item(
        WORK_ITEM_ID,
        read_material=False,
        allow_material_pending=True,
    )

    assert decision is not None
    assert decision.wordpress_content_type == "sitemap"
    assert decision.content_kind == "ambiguous"
    assert decision.evidence_ids == ["ev_public_inventory"]


def test_receipt_binding_requires_current_inventory_evidence(monkeypatch) -> None:
    catalog = _catalog(
        [
            ContentInventoryRestObject(
                url="https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
                content_type="post",
                evidence_id="ev_dev_post",
            )
        ]
    )
    monkeypatch.setattr(inventory_binding, "build_content_inventory_catalog", lambda: catalog)
    monkeypatch.setattr(
        inventory_binding,
        "latest_wordpress_vendor_read_evidence_ids",
        lambda: ("ev_public_inventory", "ev_dev_post"),
    )

    binding = content_kind_inventory_binding_for_work_item(WORK_ITEM_ID)

    assert binding is not None
    assert binding.content_kind == "editorial"
    assert binding.inventory_evidence_ids == ("ev_public_inventory", "ev_dev_post")
    assert binding.trusted is True


def test_authoring_rest_fallback_uses_only_latest_completed_wordpress_evidence(monkeypatch) -> None:
    latest = SimpleNamespace(
        mode=SimpleNamespace(value="vendor_read"),
        status=SimpleNamespace(value="completed"),
        evidence_ids=["ev_current"],
    )
    facts = [
        _rest_fact(
            "https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
            "posts",
            "ev_current",
        ),
        _rest_fact(
            "https://ekologus.dev.proudsite.pl/stary/",
            "posts",
            "ev_old",
        ),
        *[
            _rest_fact(url, "posts", "ev_current")
            for url in (
                "http://ekologus.dev.proudsite.pl/http/",
                "https://user@ekologus.dev.proudsite.pl/credentials/",
                "https://ekologus.dev.proudsite.pl:443/port/",
                "https://ekologus.dev.proudsite.pl/query/?x=1",
                "https://ekologus.dev.proudsite.pl/fragment/#x",
                "https://other.example/foreign/",
            )
        ],
    ]
    monkeypatch.setattr(
        catalog_module,
        "local_state_store",
        lambda: SimpleNamespace(list_connector_refresh_runs=lambda **_kwargs: [latest]),
    )
    monkeypatch.setattr(
        catalog_module,
        "metric_store",
        lambda: SimpleNamespace(list_metric_facts_by_evidence_ids=lambda _ids: facts),
    )

    objects = catalog_module._authoring_rest_content_objects()

    assert objects == [
        ContentInventoryRestObject(
            url="https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
            content_type="posts",
            evidence_id="ev_current",
        )
    ]


def _rest_fact(url: str, content_type: str, evidence_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        name="content_object_seen",
        source_connector="wordpress_ekologus",
        evidence_id=evidence_id,
        dimensions={
            "content_url": url,
            "content_type": content_type,
            "inventory_source": "wordpress_rest",
        },
    )
