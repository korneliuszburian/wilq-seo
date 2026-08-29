from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

import wilq.content.workflow.workspace.catalog as catalog_module
from wilq.connectors.wordpress.client import (
    WordPressCredentials,
    read_wordpress_content_material,
)
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
    inventory_work_item_id,
)

PAGE_URL = "https://www.ekologus.pl/oferta/doradztwo/"


@pytest.fixture(autouse=True)
def _material_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wilq.connectors.wordpress.client.wordpress_credentials",
        lambda _connector: WordPressCredentials(
            base_url="https://www.ekologus.pl/",
            public_url="https://www.ekologus.pl/",
            username="reader",
            application_auth="password",
            site_kind="primary",
        ),
    )


@pytest.mark.parametrize(
    ("content_type_hint", "expected_endpoint"),
    [
        ("post", "posts"),
        ("posts", "posts"),
        ("page", "pages"),
        ("pages", "pages"),
        ("uslugi", "uslugi"),
    ],
)
def test_content_type_hint_limits_rest_probe_and_keeps_exact_path_match(
    content_type_hint: str,
    expected_endpoint: str,
) -> None:
    rest_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        rest_paths.append(request.url.path)
        return httpx.Response(
            200,
            request=request,
            json=[
                {
                    "link": "https://www.ekologus.pl/wiedza/doradztwo/",
                    "title": {"rendered": "Inna strona"},
                    "content": {"rendered": "<p>Inna treść.</p>"},
                    "acf": {},
                },
                {
                    "link": PAGE_URL,
                    "title": {"rendered": "Doradztwo"},
                    "content": {"rendered": "<p>Dokładna treść.</p>"},
                    "acf": {},
                },
            ],
        )

    material = read_wordpress_content_material(
        PAGE_URL,
        content_type_hint=content_type_hint,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert material.content_text == "Dokładna treść."
    assert rest_paths == [f"/wp-json/wp/v2/{expected_endpoint}"]


@pytest.mark.parametrize(
    ("content_type_hint", "expected_paths"),
    [
        ("page", ["/wp-json/wp/v2/pages", "/oferta/doradztwo/"]),
        (
            "sitemap",
            [
                "/wp-json/wp/v2/posts",
                "/wp-json/wp/v2/pages",
                "/wp-json/wp/v2/uslugi",
                "/oferta/doradztwo/",
            ],
        ),
        (
            "unknown",
            [
                "/wp-json/wp/v2/posts",
                "/wp-json/wp/v2/pages",
                "/wp-json/wp/v2/uslugi",
                "/oferta/doradztwo/",
            ],
        ),
    ],
)
def test_material_fallback_is_explicitly_bounded(
    content_type_hint: str,
    expected_paths: list[str],
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "wp-json" in str(request.url):
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            request=request,
            text="<html><body><main><p>Materiał HTML.</p></main></body></html>",
        )

    material = read_wordpress_content_material(
        PAGE_URL,
        content_type_hint=content_type_hint,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert material.source_kind == "rendered_html"
    assert [request.url.path for request in requests] == expected_paths
    assert all(
        set(request.extensions["timeout"].values()) == {3.0}
        for request in requests
    )


def _catalog(url: str, *, evidence_id: str) -> ContentInventoryCatalogResponse:
    return ContentInventoryCatalogResponse(
        total_count=1,
        items=[
            ContentInventoryCatalogItem(
                catalog_id=f"catalog_{evidence_id}",
                work_item_id=inventory_work_item_id(url),
                url=url,
                path="/news/",
                content_type="post",
                material_status="url_only",
                source_connector="wordpress_ekologus",
                evidence_id=evidence_id,
                collected_at=datetime(2026, 7, 17, tzinfo=UTC),
            )
        ],
    )


def _material(url: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(
        url=url,
        source_kind="wordpress_rest",
        title="News",
        content_text=text,
        content_summary=text,
        content_word_count=len(text.split()),
        section_headings=["News"],
        acf_field_names=[],
        acf_section_headings=[],
        modified_gmt=None,
        extraction_region="wordpress_rest.content",
        material_confidence="source_bound",
        source_field_lineage=["wordpress_rest.content"],
    )


def test_catalog_passes_inventory_type_to_validating_connector_and_reuses_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://www.ekologus.pl/news/"
    calls: list[str | None] = []

    def read_once(_url: str, *, content_type_hint: str | None = None) -> SimpleNamespace:
        calls.append(content_type_hint)
        return _material(url, "Treść artykułu.")

    monkeypatch.setattr(catalog_module, "_inventory_material_cache", {})
    monkeypatch.setattr(catalog_module, "read_wordpress_content_material", read_once)

    first = catalog_module.read_content_inventory_material(
        url,
        catalog=_catalog(url, evidence_id="ev_new"),
    )
    second = catalog_module.read_content_inventory_material(
        url,
        catalog=_catalog(url, evidence_id="ev_new"),
    )

    assert first.content_text == second.content_text == "Treść artykułu."
    assert calls == ["post"]


def test_material_cache_ttl_starts_when_slow_read_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://www.ekologus.pl/news/"
    clock = SimpleNamespace(now=0.0)
    calls = 0

    def slow_read(_url: str, *, content_type_hint: str | None = None) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        clock.now = 40.0
        return _material(url, "Treść po wolnym odczycie.")

    monkeypatch.setattr(catalog_module, "_inventory_material_cache", {})
    monkeypatch.setattr(catalog_module, "_inventory_material_build_locks", {})
    monkeypatch.setattr(catalog_module, "monotonic", lambda: clock.now)
    monkeypatch.setattr(catalog_module, "read_wordpress_content_material", slow_read)

    first = catalog_module.read_content_inventory_material(
        url,
        catalog=_catalog(url, evidence_id="ev_slow"),
    )
    clock.now = 65.0
    second = catalog_module.read_content_inventory_material(
        url,
        catalog=_catalog(url, evidence_id="ev_slow"),
    )

    assert first.content_text == second.content_text == "Treść po wolnym odczycie."
    assert calls == 1
