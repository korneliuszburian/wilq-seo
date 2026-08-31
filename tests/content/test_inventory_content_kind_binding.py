from datetime import UTC, datetime
from types import SimpleNamespace

import wilq.content.workflow.workspace.catalog as catalog_module
from wilq.content.workflow.decisions.inventory_binding import inventory_decision_for_work_item
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    ContentInventoryCoverage,
    ContentInventoryRestObject,
    inventory_work_item_id,
)


def _rest_object(content_type: str) -> ContentInventoryRestObject:
    return ContentInventoryRestObject(
        url="https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/",
        content_type=content_type,
        evidence_id=f"ev_dev_{content_type}",
    )


def _catalog(
    url: str,
    rest_objects: list[ContentInventoryRestObject],
) -> ContentInventoryCatalogResponse:
    return ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_integrated_permits",
                work_item_id=inventory_work_item_id(url),
                url=url,
                path="/analiza-pozwolen-zintegrowanych/",
                title="Analiza pozwoleń zintegrowanych",
                content_type="sitemap",
                material_status="url_only",
                source_connector="wordpress_ekologus",
                evidence_id="ev_integrated_permits",
                collected_at=datetime(2026, 8, 31, tzinfo=UTC),
            )
        ],
        rest_content_objects=rest_objects,
    )


def test_inventory_decision_uses_exact_rest_object_type_fallback(monkeypatch) -> None:
    url = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
    monkeypatch.setattr(
        "wilq.content.workflow.decisions.inventory_binding.build_content_inventory_catalog",
        lambda: _catalog(url, [_rest_object("posts")]),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.decisions.inventory_binding.inventory_metric_facts",
        lambda *_args, **_kwargs: [],
    )

    decision = inventory_decision_for_work_item(
        inventory_work_item_id(url),
        read_material=False,
        allow_material_pending=True,
    )

    assert decision is not None
    assert decision.wordpress_content_type == "posts"
    assert decision.content_kind == "editorial"
    assert "ev_dev_posts" in decision.evidence_ids


def test_inventory_decision_keeps_conflicting_exact_rest_types_ambiguous(monkeypatch) -> None:
    url = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
    monkeypatch.setattr(
        "wilq.content.workflow.decisions.inventory_binding.build_content_inventory_catalog",
        lambda: _catalog(url, [_rest_object("posts"), _rest_object("pages")]),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.decisions.inventory_binding.inventory_metric_facts",
        lambda *_args, **_kwargs: [],
    )

    decision = inventory_decision_for_work_item(
        inventory_work_item_id(url),
        read_material=False,
        allow_material_pending=True,
    )

    assert decision is not None
    assert decision.wordpress_content_type == "sitemap"
    assert decision.content_kind == "ambiguous"
    assert "ev_dev_posts" not in decision.evidence_ids
    assert "ev_dev_pages" not in decision.evidence_ids


def test_catalog_fallback_keeps_only_current_authoring_host_rest_objects(monkeypatch) -> None:
    public_url = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/"
    dimensions = {
        "content_url": public_url,
        "content_type": "sitemap",
        "editorial_eligible": "true",
    }
    facts = [
        SimpleNamespace(
            name="content_object_seen",
            dimensions=dimensions,
            source_connector="wordpress_ekologus",
            evidence_id="ev_current_sitemap",
            collected_at=datetime(2026, 8, 31, tzinfo=UTC),
        ),
        SimpleNamespace(
            name="content_object_seen",
            dimensions={
                **dimensions,
                "content_type": "posts",
                "inventory_source": "wordpress_rest",
            },
            source_connector="wordpress_ekologus",
            evidence_id="ev_current_public_rest",
            collected_at=datetime(2026, 8, 31, tzinfo=UTC),
        ),
        SimpleNamespace(
            name="content_object_seen",
            dimensions={
                **dimensions,
                "content_url": (
                    "https://ekologus.dev.proudsite.pl/analiza-pozwolen-zintegrowanych/"
                ),
                "content_type": "posts",
                "inventory_source": "wordpress_rest",
            },
            source_connector="wordpress_ekologus",
            evidence_id="ev_current_dev_rest",
            collected_at=datetime(2026, 8, 31, tzinfo=UTC),
        ),
    ]
    monkeypatch.setattr(catalog_module, "_latest_wordpress_inventory_facts", lambda: facts)
    monkeypatch.setattr(catalog_module, "_catalog_metric_facts_by_path", lambda: {})
    monkeypatch.setattr(
        catalog_module,
        "_inventory_coverage",
        lambda: ContentInventoryCoverage(status="complete"),
    )

    catalog = catalog_module.build_content_inventory_catalog()

    assert [item.evidence_id for item in catalog.rest_content_objects] == ["ev_current_dev_rest"]
    assert catalog.model_dump()["items"]
    assert "rest_content_objects" not in catalog.model_dump()


def test_rest_fallback_reads_only_latest_completed_refresh_evidence(monkeypatch) -> None:
    latest_fact = SimpleNamespace(evidence_id="ev_current_dev_rest")
    requested_evidence_ids: list[list[str]] = []
    runs = [
        SimpleNamespace(
            mode=SimpleNamespace(value="vendor_read"),
            status=SimpleNamespace(value="completed"),
            evidence_ids=["ev_current_dev_rest"],
        ),
        SimpleNamespace(
            mode=SimpleNamespace(value="vendor_read"),
            status=SimpleNamespace(value="completed"),
            evidence_ids=["ev_old_dev_rest"],
        ),
    ]
    monkeypatch.setattr(
        catalog_module,
        "local_state_store",
        lambda: SimpleNamespace(list_connector_refresh_runs=lambda **_kwargs: runs),
    )
    monkeypatch.setattr(
        catalog_module,
        "metric_store",
        lambda: SimpleNamespace(
            list_metric_facts_by_evidence_ids=lambda evidence_ids: (
                requested_evidence_ids.append(evidence_ids) or [latest_fact]
            )
        ),
    )

    facts = catalog_module._latest_connector_refresh_facts("wordpress_ekologus")

    assert facts == [latest_fact]
    assert requested_evidence_ids == [["ev_current_dev_rest"]]
