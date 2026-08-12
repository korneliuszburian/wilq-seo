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
        if request.url.path in {
            "/wp-json/wp/v2/posts",
            "/wp-json/wp/v2/pages",
            "/wp-json/wp/v2/uslugi",
        }:
            return _public_rest_response(request)
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
    if request.url.path in {
        "/wp-json/wp/v2/posts",
        "/wp-json/wp/v2/pages",
        "/wp-json/wp/v2/uslugi",
    }:
        return httpx.Response(200, headers={"X-WP-Total": "0"}, json=[])
    return httpx.Response(404)


def _public_rest_response(request: httpx.Request) -> httpx.Response:
    slug = request.url.params.get("slug")
    if request.url.path.endswith("/posts") and slug == "bdo-co-musi-wiedziec-przedsiebiorca":
        return httpx.Response(
            200,
            json=[
                {
                    "link": BDO_URL,
                    "acf": {"wyrozniony_tytul": "BDO", "wyswietlenia": 1},
                }
            ],
        )
    if (
        request.url.path.endswith("/uslugi")
        and slug == "doradztwo-i-outsourcing-ekologiczny"
    ):
        return httpx.Response(
            200,
            json=[
                {
                    "link": OUTSOURCING_URL,
                    "acf": {
                        "podstrona": {
                            "elementy": [
                                {
                                    "acf_fc_layout": "blok_z_ikonami",
                                    "tytul": "Zakres obsługi środowiskowej",
                                },
                                {
                                    "acf_fc_layout": "wezwanie_do_dzialania",
                                    "naglowek": "Porozmawiajmy o obowiązkach",
                                },
                            ]
                        }
                    },
                }
            ],
        )
    return httpx.Response(200, json=[])


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
        text=(
            f"<html><body><main><h1>{h1}</h1>{heading_html}"
            "<p>Aktualny opis usługi do bezpiecznego inventory treści.</p>"
            "</main><footer>Nie wliczaj stopki.</footer></body></html>"
        ),
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
        ConnectorRefreshRequest(
            mode=ConnectorRefreshMode.vendor_read,
            target_urls=[BDO_URL, OUTSOURCING_URL],
        ),
        http_client=client,
    )

    bdo_fact = next(
        fact
        for fact in result.metric_facts
        if fact.dimensions.get("content_url") == BDO_URL
        and fact.dimensions.get("content_summary")
    )
    assert bdo_fact.dimensions["content_summary"].startswith("BDO dla przedsiębiorcy")
    assert int(bdo_fact.dimensions["content_word_count"]) > 0
    assert "Nie wliczaj stopki" not in bdo_fact.dimensions["content_summary"]

    assert result.status == ConnectorRefreshStatus.completed
    assert result.metric_summary["target_url_count"] == 2
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
    assert json.loads(facts[OUTSOURCING_URL].dimensions["acf_section_headings_json"]) == [
        "Zakres obsługi środowiskowej",
        "Porozmawiajmy o obowiązkach",
    ]
    assert facts[OUTSOURCING_URL].dimensions["acf_section_count"] == "2"
    assert json.loads(facts[BDO_URL].dimensions["acf_field_names_json"]) == [
        "wyrozniony_tytul",
        "wyswietlenia",
    ]
    assert facts[BDO_URL].dimensions["acf_section_headings_json"] == ""
    assert facts[UNSUPPORTED_URL].dimensions["section_headings_json"] == ""


def _configure_wordpress_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_required_wordpress_rest_failures_never_become_successful_zero_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status_code: int,
) -> None:
    _configure_wordpress_inventory(monkeypatch, tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/wp-json/wp/v2/posts":
            return httpx.Response(status_code)
        return httpx.Response(200, json=[])

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.failed
    assert result.external_call_attempted is True
    assert result.vendor_data_collected is False
    assert result.metric_summary == {}
    assert result.metric_facts == []
    assert str(status_code) in result.errors[0]


def test_absent_wordpress_content_type_endpoint_is_the_only_rest_zero_absence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_wordpress_inventory(monkeypatch, tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/wp-json/wp/v2/uslugi":
            return httpx.Response(404)
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            return _xml_response("<urlset></urlset>")
        return httpx.Response(404)

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.vendor_data_collected is True
    assert result.metric_summary["content_object_count"] == 0
    assert result.metric_summary["inventory_coverage_status"] == "complete"


@pytest.mark.parametrize(
    ("headers", "body"),
    [
        ({"content-type": "application/json"}, "{"),
        ({"content-type": "text/html"}, "<html>upstream error</html>"),
    ],
)
def test_successful_wordpress_rest_response_requires_valid_json_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    headers: dict[str, str],
    body: str,
) -> None:
    _configure_wordpress_inventory(monkeypatch, tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/wp-json/wp/v2/posts":
            return httpx.Response(200, headers=headers, text=body)
        return httpx.Response(200, json=[])

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.failed
    assert result.vendor_data_collected is False
    assert result.errors == [
        "WordPress wordpress_ekologus content inventory invalid_response_payload."
    ]


def test_failed_child_sitemap_is_retained_as_partial_inventory_coverage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_wordpress_inventory(monkeypatch, tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            return _xml_response(
                "<sitemapindex>"
                "<sitemap><loc>https://www.ekologus.pl/failed.xml</loc></sitemap>"
                "<sitemap><loc>https://www.ekologus.pl/valid.xml</loc></sitemap>"
                "</sitemapindex>"
            )
        if request.url.path == "/failed.xml":
            return httpx.Response(500)
        if request.url.path == "/valid.xml":
            return _xml_response(
                "<urlset><url><loc>https://www.ekologus.pl/valid-page/</loc></url></urlset>"
            )
        return httpx.Response(404)

    result = refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.status == ConnectorRefreshStatus.completed
    assert result.metric_summary["sitemap_url_count"] == 1
    assert result.metric_summary["sitemap_coverage_status"] == "partial"
    assert result.metric_summary["inventory_coverage_status"] == "partial"
    assert result.metric_summary["aggregate_data_completeness"] == "partial_possible"
