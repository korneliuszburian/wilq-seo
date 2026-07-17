from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from wilq.connectors.wordpress.client import refresh_wordpress_content_inventory
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRequest, ConnectorRefreshStatus

BDO_URL = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
OUTSOURCING_URL = (
    "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/"
)
UNSUPPORTED_URL = "https://www.ekologus.pl/oferta/unsupported-layout/"


def _public_sitemap_handler() -> Callable[[httpx.Request], httpx.Response]:
    post_urls = "".join(
        (
            f"<url><loc>{BDO_URL}</loc></url>"
            if index == 41
            else f"<url><loc>https://www.ekologus.pl/post-{index}/</loc></url>"
        )
        for index in range(1, 52)
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "ekologus.dev.proudsite.pl":
            return _dev_response(request)
        if request.url.path == "/wp-sitemap.xml":
            return httpx.Response(404)
        if request.url.path == "/sitemap_index.xml":
            return _xml_response(
                "<sitemapindex>"
                "<sitemap><loc>https://www.ekologus.pl/post-sitemap.xml</loc></sitemap>"
                "<sitemap><loc>https://www.ekologus.pl/page-sitemap.xml</loc></sitemap>"
                "</sitemapindex>"
            )
        if request.url.path == "/post-sitemap.xml":
            return _xml_response(f"<urlset>{post_urls}</urlset>")
        if request.url.path == "/page-sitemap.xml":
            return _xml_response(
                f"<urlset><url><loc>{OUTSOURCING_URL}</loc></url>"
                f"<url><loc>{UNSUPPORTED_URL}</loc></url></urlset>"
            )
        return _public_page_response(request)

    return handler


def _dev_response(request: httpx.Request) -> httpx.Response:
    if request.url.path in {"/wp-json/wp/v2/posts", "/wp-json/wp/v2/pages"}:
        return httpx.Response(200, headers={"X-WP-Total": "0"}, json=[])
    return httpx.Response(404)


def _xml_response(body: str) -> httpx.Response:
    namespaced = body.replace(
        "<urlset>",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        1,
    ).replace(
        "<sitemapindex>",
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        1,
    )
    return httpx.Response(
        200,
        text='<?xml version="1.0" encoding="UTF-8"?>' + namespaced,
    )


def _public_page_response(request: httpx.Request) -> httpx.Response:
    pages = {
        "/bdo-co-musi-wiedziec-przedsiebiorca/": (
            "BDO dla przedsiębiorcy",
            ["Obowiązki przedsiębiorcy", "Rejestr BDO"],
        ),
        "/oferta/doradztwo-i-outsourcing-ekologiczny/": (
            "Doradztwo środowiskowe i EKO-consulting",
            ["Zakres doradztwa", "Oferta<br>Pomiary Emisji"],
        ),
        "/oferta/unsupported-layout/": ("Obcy układ", []),
    }
    page = pages.get(request.url.path)
    if page is None:
        return httpx.Response(404)
    h1, headings = page
    heading_html = "".join(f"<h2>{heading}</h2>" for heading in headings)
    return httpx.Response(
        200,
        headers={"content-type": "text/html; charset=utf-8"},
        text=f"<html><body><h1>{h1}</h1>{heading_html}</body></html>",
    )


def test_public_inventory_enriches_posts_and_pages_with_separate_bounded_budgets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://ekologus.dev.proudsite.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")
    client = httpx.Client(transport=httpx.MockTransport(_public_sitemap_handler()))

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=client,
    )

    assert result.status == ConnectorRefreshStatus.completed
    facts = {
        fact.dimensions.get("content_url"): fact
        for fact in result.metric_facts
        if fact.name == "content_object_seen"
        and fact.dimensions.get("inventory_source") == "public_sitemap"
    }
    assert all("_metadata_group" not in fact.dimensions for fact in facts.values())
    assert json.loads(facts[BDO_URL].dimensions["section_headings_json"]) == [
        "Obowiązki przedsiębiorcy",
        "Rejestr BDO",
    ]
    assert json.loads(facts[OUTSOURCING_URL].dimensions["section_headings_json"]) == [
        "Zakres doradztwa",
        "Oferta Pomiary Emisji",
    ]
    assert json.loads(facts[UNSUPPORTED_URL].dimensions["section_headings_json"]) == []
