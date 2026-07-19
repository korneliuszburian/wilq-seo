from datetime import UTC, datetime
from types import SimpleNamespace

import httpx

import wilq.content.workflow.catalog as catalog_module
from wilq.connectors.wordpress.client import WordPressCredentials, read_wordpress_content_material
from wilq.content.planning.decisions import content_decision_work_item_id_for_url
from wilq.content.workflow.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    bind_content_inventory_item,
    build_content_inventory_catalog,
    inventory_metric_facts,
    inventory_work_item_id,
)
from wilq.content.workflow.inventory_binding import inventory_decision_for_work_item
from wilq.schemas import MetricFact


def test_inventory_catalog_deduplicates_urls_and_keeps_acf_headings(monkeypatch):
    rows = [
        SimpleNamespace(
            name="content_object_seen",
            dimensions={
                "content_url": "https://www.ekologus.pl/oferta/",
                "title_or_h1": "Oferta",
                "content_type": "page",
                "section_heading_count": "4",
                "section_headings_json": '["Wstęp", "Zakres usługi", "FAQ", "CTA"]',
                "acf_section_count": "2",
                "acf_section_headings_json": '["Hero", "FAQ"]',
            },
            source_connector="wordpress_ekologus",
            evidence_id="ev_wp",
            collected_at=datetime(2026, 7, 17, tzinfo=UTC),
        ),
        SimpleNamespace(
            name="content_object_seen",
            dimensions={
                "content_url": "https://www.ekologus.pl/oferta/",
                "title_or_h1": "duplicate",
            },
            source_connector="wordpress_ekologus",
            evidence_id="ev_wp_old",
            collected_at=datetime(2026, 7, 16, tzinfo=UTC),
        ),
        SimpleNamespace(name="clicks", dimensions={"content_url": "https://ignored"}),
    ]
    monkeypatch.setattr(
        "wilq.content.workflow.catalog.metric_store",
        lambda: SimpleNamespace(
            list_metric_facts=lambda *_args, **_kwargs: rows
        ),
    )

    result = build_content_inventory_catalog()

    assert result.total_count == 1
    assert result.items[0].work_item_id.startswith("content_work_item_inventory_")
    assert result.items[0].path == "/oferta/"
    assert result.items[0].section_headings == ["Wstęp", "Zakres usługi", "FAQ", "CTA"]
    assert result.items[0].acf_section_headings == ["Hero", "FAQ"]
    assert result.items[0].material_status == "structure_only"
    assert result.items[0].evidence_id == "ev_wp"


def test_inventory_catalog_excludes_non_public_hosts(monkeypatch):
    rows = [
        SimpleNamespace(
            name="content_object_seen",
            dimensions={"content_url": "https://ekologus.dev.proudsite.pl/bdo/"},
            source_connector="wordpress_ekologus",
            evidence_id="ev_wp_dev",
            collected_at=datetime(2026, 7, 18, tzinfo=UTC),
        ),
        SimpleNamespace(
            name="content_object_seen",
            dimensions={"content_url": "https://www.ekologus.pl/bdo/"},
            source_connector="wordpress_ekologus",
            evidence_id="ev_wp_public",
            collected_at=datetime(2026, 7, 18, tzinfo=UTC),
        ),
    ]
    monkeypatch.setattr(
        "wilq.content.workflow.catalog.metric_store",
        lambda: SimpleNamespace(list_metric_facts=lambda *_args, **_kwargs: rows),
    )

    result = build_content_inventory_catalog()

    assert [item.url for item in result.items] == ["https://www.ekologus.pl/bdo/"]


def test_inventory_catalog_uses_the_latest_wordpress_refresh_batch(monkeypatch):
    old_row = SimpleNamespace(
        name="content_object_seen",
        dimensions={"content_url": "https://www.ekologus.pl/old-page/"},
        source_connector="wordpress_ekologus",
        evidence_id="ev_refresh_old",
        collected_at=datetime(2026, 7, 16, tzinfo=UTC),
    )
    current_row = SimpleNamespace(
        name="content_object_seen",
        dimensions={"content_url": "https://www.ekologus.pl/current-page/"},
        source_connector="wordpress_ekologus",
        evidence_id="ev_refresh_current",
        collected_at=datetime(2026, 7, 18, tzinfo=UTC),
    )
    latest_run = SimpleNamespace(
        mode=SimpleNamespace(value="vendor_read"),
        status=SimpleNamespace(value="completed"),
        evidence_ids=["ev_connector_wordpress_ekologus_status", "ev_refresh_current"],
        metric_summary={},
    )
    store = SimpleNamespace(
        list_metric_facts=lambda *_args, **_kwargs: [old_row, current_row],
        list_metric_facts_by_evidence_ids=lambda evidence_ids: (
            [current_row]
            if evidence_ids
            == ["ev_connector_wordpress_ekologus_status", "ev_refresh_current"]
            else []
        ),
    )
    monkeypatch.setattr(catalog_module, "metric_store", lambda: store)
    monkeypatch.setattr(
        catalog_module,
        "local_state_store",
        lambda: SimpleNamespace(
            list_connector_refresh_runs=lambda connector_id: [latest_run]
        ),
    )

    result = build_content_inventory_catalog()

    assert result.total_count == 1
    assert result.items[0].url == "https://www.ekologus.pl/current-page/"


def test_inventory_catalog_uses_only_latest_search_refresh_metrics(monkeypatch):
    page_url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    wordpress_row = SimpleNamespace(
        name="content_object_seen",
        dimensions={"content_url": page_url},
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp_current",
        collected_at=datetime(2026, 7, 18, tzinfo=UTC),
    )
    old_clicks = SimpleNamespace(
        name="clicks",
        dimensions={"page": page_url, "query": "stare zapytanie"},
        source_connector="google_search_console",
        evidence_id="ev_gsc_old",
        value="99",
        collected_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    current_clicks = SimpleNamespace(
        name="clicks",
        dimensions={"page": page_url, "query": "bdo"},
        source_connector="google_search_console",
        evidence_id="ev_gsc_current",
        value="1",
        collected_at=datetime(2026, 7, 18, tzinfo=UTC),
    )
    wordpress_run = SimpleNamespace(
        mode=SimpleNamespace(value="vendor_read"),
        status=SimpleNamespace(value="completed"),
        evidence_ids=["ev_wp_current"],
        metric_summary={},
    )
    gsc_run = SimpleNamespace(
        mode=SimpleNamespace(value="vendor_read"),
        status=SimpleNamespace(value="completed"),
        evidence_ids=["ev_gsc_current"],
    )
    store = SimpleNamespace(
        list_metric_facts=lambda connector_id, **_kwargs: (
            [wordpress_row]
            if connector_id == "wordpress_ekologus"
            else [old_clicks, current_clicks]
        ),
        list_metric_facts_by_evidence_ids=lambda evidence_ids: (
            [wordpress_row]
            if evidence_ids == ["ev_wp_current"]
            else [current_clicks]
        ),
    )
    monkeypatch.setattr(catalog_module, "metric_store", lambda: store)
    monkeypatch.setattr(
        catalog_module,
        "local_state_store",
        lambda: SimpleNamespace(
            list_connector_refresh_runs=lambda connector_id: (
                [wordpress_run]
                if connector_id == "wordpress_ekologus"
                else [gsc_run]
            )
        ),
    )

    result = build_content_inventory_catalog()

    assert result.total_count == 1
    assert result.items[0].metrics_clicks == 1
    assert result.items[0].metrics_query_count == 1
    assert result.items[0].metrics_evidence_ids == ["ev_gsc_current"]


def test_inventory_coverage_does_not_claim_complete_for_legacy_public_cap(monkeypatch):
    latest_run = SimpleNamespace(
        mode=SimpleNamespace(value="vendor_read"),
        status=SimpleNamespace(value="completed"),
        metric_summary={
            "sitemap_url_source_count": 102,
            "sitemap_url_returned_count": 102,
            "sitemap_url_limit": 500,
            "sitemap_url_truncated": False,
            "public_sitemap_url_source_count": 500,
            "public_sitemap_url_returned_count": 500,
            "public_sitemap_url_limit": 500,
            # Older refreshes did not persist this field.
            "public_sitemap_url_count": 500,
        },
    )
    monkeypatch.setattr(
        catalog_module,
        "local_state_store",
        lambda: SimpleNamespace(
            list_connector_refresh_runs=lambda connector_id: [latest_run]
        ),
    )

    coverage = catalog_module._inventory_coverage()

    assert coverage.status == "unknown"
    assert coverage.public_sitemap_truncated is None
    assert "starszy odczyt" in coverage.caveat


def test_inventory_metric_facts_do_not_mix_search_refresh_history(monkeypatch):
    page_url = "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/"
    old_fact = SimpleNamespace(
        name="clicks",
        dimensions={"page": page_url, "query": "stare"},
        source_connector="google_search_console",
        evidence_id="ev_gsc_old",
        value="20",
        model_dump_json=lambda: "old",
    )
    current_fact = SimpleNamespace(
        name="clicks",
        dimensions={"page": page_url, "query": "doradztwo środowiskowe"},
        source_connector="google_search_console",
        evidence_id="ev_gsc_current",
        value="0",
        model_dump_json=lambda: "current",
    )
    latest_run = SimpleNamespace(
        mode=SimpleNamespace(value="vendor_read"),
        status=SimpleNamespace(value="completed"),
        evidence_ids=["ev_gsc_current"],
    )
    monkeypatch.setattr(
        catalog_module,
        "metric_store",
        lambda: SimpleNamespace(
            list_metric_facts_for_content_url=lambda connectors, *_args, **_kwargs: (
                [old_fact, current_fact]
                if connectors == ["google_search_console"]
                else []
            )
        ),
    )
    monkeypatch.setattr(
        catalog_module,
        "local_state_store",
        lambda: SimpleNamespace(
            list_connector_refresh_runs=lambda connector_id: (
                [latest_run]
                if connector_id == "google_search_console"
                else []
            )
        ),
    )

    facts = inventory_metric_facts(page_url, "/oferta/doradztwo-i-outsourcing-ekologiczny/")

    assert [fact.evidence_id for fact in facts] == ["ev_gsc_current"]


def test_dynamic_material_falls_back_to_rendered_the_content(monkeypatch):
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client._wordpress_credentials",
        lambda _connector: WordPressCredentials(
            base_url="https://staging.example/",
            public_url="https://www.ekologus.pl/",
            username="reader",
            application_auth="password",
            site_kind="primary",
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if "wp-json" in str(request.url):
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/html"},
            text=(
                "<html><head><title>Artykuł</title></head><body><main>"
                "<h1>Artykuł</h1><p>Pełny materiał z the_content.</p>"
                "</main></body></html>"
            ),
        )

    material = read_wordpress_content_material(
        "https://www.ekologus.pl/czy-przygotowane-wieloletnie-plany-inwestycyjne-z-zakresu-gospodarki-odpadami-spelniaja-nowe-wymagania-prawne/",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert material.source_kind == "rendered_html"
    assert material.content_word_count == 5
    assert "Pełny materiał" in material.content_text


def test_dynamic_material_extracts_the_content_headings_from_rest(monkeypatch):
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client._wordpress_credentials",
        lambda _connector: WordPressCredentials(
            base_url="https://staging.example/",
            public_url="https://www.ekologus.pl/",
            username="reader",
            application_auth="password",
            site_kind="primary",
        ),
    )

    page_url = (
        "https://www.ekologus.pl/czy-przygotowane-wieloletnie-plany-inwestycyjne-z-zakresu-"
        "gospodarki-odpadami-spelniaja-nowe-wymagania-prawne/"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if "wp-json" not in str(request.url):
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            request=request,
            json=[
                {
                    "link": page_url,
                    "title": {"rendered": "Plany inwestycyjne"},
                    "content": {
                        "raw": "<h2>Nowe wymagania prawne</h2><p>Treść artykułu.</p>"
                    },
                    "acf": {},
                }
            ],
        )

    material = read_wordpress_content_material(
        page_url,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert material.source_kind == "wordpress_rest"
    assert material.section_headings == ["Nowe wymagania prawne"]


def test_inventory_binding_is_stable_and_evidence_bound(monkeypatch):
    row = SimpleNamespace(
        name="content_object_seen",
        dimensions={"content_url": "https://www.ekologus.pl/news/"},
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp",
        collected_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.catalog.metric_store",
        lambda: SimpleNamespace(
            list_metric_facts=lambda *_args, **_kwargs: [row],
            list_metric_facts_for_content_url=lambda *_args, **_kwargs: [],
        ),
    )

    first = bind_content_inventory_item("https://www.ekologus.pl/news/")
    second = bind_content_inventory_item("https://www.ekologus.pl/news")

    assert first.status == "ready"
    assert first.work_item_id == second.work_item_id
    assert first.evidence_id == "ev_wp"


def test_inventory_binding_resolves_public_material_for_url_only_row(monkeypatch):
    monkeypatch.setattr(catalog_module, "_inventory_catalog_cache", None)
    row = SimpleNamespace(
        name="content_object_seen",
        dimensions={"content_url": "https://www.ekologus.pl/oferta/doradztwo/"},
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp",
        collected_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.catalog.metric_store",
        lambda: SimpleNamespace(
            list_metric_facts=lambda *_args, **_kwargs: [row],
            list_metric_facts_for_content_url=lambda *_args, **_kwargs: [],
        ),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.catalog.read_content_inventory_material",
        lambda _url, *, catalog: SimpleNamespace(
            status="ready",
            content_text="pełny materiał",
            title="Doradztwo środowiskowe",
            section_headings=["Korzyści"],
            acf_field_names=[],
            source_kind="rendered_html",
            material_confidence="review_required",
            extraction_region="the_content",
            source_field_lineage=["public_html.main_or_article"],
        ),
    )

    result = bind_content_inventory_item("https://www.ekologus.pl/oferta/doradztwo/")

    assert result.material_status == "content_and_structure"
    assert result.title == "Doradztwo środowiskowe"
    assert result.material_source_kind == "rendered_html"
    assert result.material_confidence == "review_required"
    assert result.extraction_region == "the_content"
    assert result.source_field_lineage == ["public_html.main_or_article"]


def test_inventory_decision_reuses_the_current_catalog_for_material_read(monkeypatch):
    url = "https://www.ekologus.pl/news/"
    item = ContentInventoryCatalogItem(
        catalog_id="catalog_news",
        work_item_id=inventory_work_item_id(url),
        url=url,
        path="/news/",
        title="News",
        content_type="post",
        material_status="content_summary",
        source_connector="wordpress_ekologus",
        evidence_id="ev_news",
        collected_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    catalog = ContentInventoryCatalogResponse(total_count=1, items=[item])
    calls = 0

    def catalog_reader():
        nonlocal calls
        calls += 1
        return catalog

    seen_catalogs = []
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.build_content_inventory_catalog",
        catalog_reader,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.inventory_metric_facts",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.read_content_inventory_material",
        lambda _url, *, catalog: seen_catalogs.append(catalog) or SimpleNamespace(
            status="blocked",
            content_text=None,
            content_summary="News summary",
            content_word_count=2,
            section_headings=[],
            acf_section_headings=[],
            acf_field_names=[],
            source_kind=None,
            extraction_region=None,
            material_confidence=None,
            source_field_lineage=[],
        ),
    )

    decision = inventory_decision_for_work_item(inventory_work_item_id(url))

    assert decision is not None
    assert calls == 1
    assert seen_catalogs == [catalog]


def test_inventory_decision_resolves_the_canonical_diagnostics_work_item_id(
    monkeypatch,
):
    url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    item = ContentInventoryCatalogItem(
        catalog_id="catalog_bdo",
        work_item_id=inventory_work_item_id(url),
        url=url,
        path="/bdo-co-musi-wiedziec-przedsiebiorca/",
        title="BDO — co musi wiedzieć przedsiębiorca",
        content_type="page",
        material_status="content_summary",
        source_connector="wordpress_ekologus",
        evidence_id="ev_bdo",
        collected_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.build_content_inventory_catalog",
        lambda: ContentInventoryCatalogResponse(total_count=1, items=[item]),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.inventory_metric_facts",
        lambda *_args, **_kwargs: [],
    )

    decision = inventory_decision_for_work_item(
        content_decision_work_item_id_for_url(url),
        read_material=False,
        allow_material_pending=True,
    )

    assert decision is not None
    assert decision.id == content_decision_work_item_id_for_url(url).removeprefix(
        "content_work_item_"
    )
    assert decision.page == url


def test_inventory_decision_retains_exact_ga4_landing_facts_for_planning(monkeypatch):
    url = "https://www.ekologus.pl/oferta/"
    item = ContentInventoryCatalogItem(
        catalog_id="catalog_offer",
        work_item_id=inventory_work_item_id(url),
        url=url,
        path="/oferta/",
        title="Oferta",
        content_type="page",
        material_status="content_summary",
        content_summary="Oferta Ekologus",
        source_connector="wordpress_ekologus",
        evidence_id="ev_wp_offer",
        collected_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.build_content_inventory_catalog",
        lambda: ContentInventoryCatalogResponse(total_count=1, items=[item]),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.inventory_metric_facts",
        lambda *_args, **_kwargs: [
            MetricFact(
                name="clicks",
                value=2,
                period="connector_refresh",
                source_connector="google_search_console",
                evidence_id="ev_gsc_offer",
                dimensions={"page": url, "query": "oferta ekologus"},
            ),
            MetricFact(
                name="active_users",
                value=7,
                period="connector_refresh",
                source_connector="google_analytics_4",
                evidence_id="ev_ga4_offer",
                dimensions={"landing_page": "/"},
            ),
        ],
    )

    decision = inventory_decision_for_work_item(
        content_decision_work_item_id_for_url(url),
        read_material=False,
        allow_material_pending=True,
    )

    assert decision is not None
    assert "google_analytics_4" in decision.source_connectors
    assert [fact.evidence_id for fact in decision.metric_facts] == [
        "ev_gsc_offer",
        "ev_ga4_offer",
    ]


def test_inventory_catalog_cache_reuses_one_snapshot(monkeypatch):
    catalog = ContentInventoryCatalogResponse(total_count=0)
    calls = 0

    def build_once():
        nonlocal calls
        calls += 1
        return catalog

    monkeypatch.setattr(catalog_module, "_inventory_catalog_cache", None)
    monkeypatch.setattr(catalog_module, "build_content_inventory_catalog", build_once)

    first = catalog_module.build_content_inventory_catalog_cached()
    second = catalog_module.build_content_inventory_catalog_cached()

    assert first is second is catalog
    assert calls == 1


def test_inventory_material_cache_reuses_read_only_wordpress_material(monkeypatch):
    url = "https://www.ekologus.pl/news/"
    catalog = ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id="catalog_news",
                work_item_id=inventory_work_item_id(url),
                url=url,
                path="/news/",
                content_type="post",
                material_status="url_only",
                source_connector="wordpress_ekologus",
                evidence_id="ev_new",
                collected_at=datetime(2026, 7, 17, tzinfo=UTC),
            )
        ],
    )
    monkeypatch.setattr(catalog_module, "_inventory_material_cache", {})
    calls = 0

    def read_once(_url):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            url=url,
            source_kind="rendered_html",
            title="News",
            content_text="Treść artykułu.",
            content_summary="Treść artykułu.",
            content_word_count=2,
            section_headings=["News"],
            acf_field_names=[],
            acf_section_headings=[],
            modified_gmt=None,
            extraction_region="the_content",
            material_confidence="high",
            source_field_lineage=["wordpress:the_content"],
        )

    monkeypatch.setattr(catalog_module, "read_wordpress_content_material", read_once)

    first = catalog_module.read_content_inventory_material(url, catalog=catalog)
    second = catalog_module.read_content_inventory_material(url, catalog=catalog)

    assert first.content_text == second.content_text == "Treść artykułu."
    assert first.evidence_id == second.evidence_id == "ev_new"
    assert calls == 1


def test_inventory_decision_metadata_only_skips_live_material(monkeypatch):
    url = "https://www.ekologus.pl/news/"
    item = ContentInventoryCatalogItem(
        catalog_id="catalog_news_fast",
        work_item_id=inventory_work_item_id(url),
        url=url,
        path="/news/",
        title="News",
        content_type="post",
        content_summary="Zatwierdzone podsumowanie materiału.",
        content_word_count=20,
        material_status="content_summary",
        source_connector="wordpress_ekologus",
        evidence_id="ev_news_fast",
        collected_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.build_content_inventory_catalog",
        lambda: ContentInventoryCatalogResponse(total_count=1, items=[item]),
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.inventory_metric_facts",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "wilq.content.workflow.inventory_binding.read_content_inventory_material",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("metadata-only decision must not read live material")
        ),
    )

    decision = inventory_decision_for_work_item(
        inventory_work_item_id(url),
        read_material=False,
    )

    assert decision is not None
    assert decision.wordpress_content_summary == "Zatwierdzone podsumowanie materiału."
    assert decision.wordpress_content_text is None
