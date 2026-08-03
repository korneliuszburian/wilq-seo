from datetime import UTC, datetime
from types import SimpleNamespace

from wilq.content.workflow.catalog import build_content_inventory_catalog


def test_inventory_catalog_excludes_commerce_sitemap_entries(monkeypatch):
    rows = [
        SimpleNamespace(
            name="content_object_seen",
            dimensions={
                "content_url": "https://www.ekologus.pl/sorbenty/olejowe/",
                "sitemap_group": "products",
                "editorial_eligible": "false",
            },
            source_connector="wordpress_ekologus",
            evidence_id="ev_product",
            collected_at=datetime(2026, 8, 3, tzinfo=UTC),
        ),
        SimpleNamespace(
            name="content_object_seen",
            dimensions={
                "content_url": "https://www.ekologus.pl/bdo/",
                "sitemap_group": "pages",
                "editorial_eligible": "true",
            },
            source_connector="wordpress_ekologus",
            evidence_id="ev_page",
            collected_at=datetime(2026, 8, 3, tzinfo=UTC),
        ),
    ]
    monkeypatch.setattr(
        "wilq.content.workflow.catalog.metric_store",
        lambda: SimpleNamespace(list_metric_facts=lambda *_args, **_kwargs: rows),
    )

    result = build_content_inventory_catalog()

    assert [item.url for item in result.items] == ["https://www.ekologus.pl/bdo/"]
