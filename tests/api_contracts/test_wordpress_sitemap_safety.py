from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from wilq.connectors.vendor import VendorReadResult
from wilq.connectors.wordpress.client import refresh_wordpress_content_inventory
from wilq.content.canonical.urls import content_is_safe_public_url
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRequest


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


def _configure_wordpress_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_PUBLIC_URL", "https://www.ekologus.pl")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_USERNAME", "editor")
    monkeypatch.setenv("WORDPRESS_EKOLOGUS_APP_PASSWORD", "app-password")


@pytest.mark.parametrize("is_child_sitemap", [False, True], ids=["page", "child"])
def test_off_origin_sitemap_locations_are_not_fetched_or_persisted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    is_child_sitemap: bool,
) -> None:
    requested: list[str] = []
    attacker_url = (
        "https://attacker.example/child.xml"
        if is_child_sitemap
        else "https://attacker.example/page/"
    )
    injected_page_url = (
        "https://www.ekologus.pl/attacker-page/" if is_child_sitemap else attacker_url
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            root_tag, entry_tag = (
                ("sitemapindex", "sitemap") if is_child_sitemap else ("urlset", "url")
            )
            return _xml_response(
                f"<{root_tag}><{entry_tag}><loc>{attacker_url}</loc></{entry_tag}></{root_tag}>"
            )
        if request.url.host == "attacker.example":
            if is_child_sitemap:
                return _xml_response(f"<urlset><url><loc>{injected_page_url}</loc></url></urlset>")
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><body><main><h1>attacker content</h1></main></body></html>",
            )
        return httpx.Response(404)

    result = _refresh_sitemap_inventory(monkeypatch, tmp_path, handler)

    assert attacker_url not in requested
    assert result.metric_summary["sitemap_coverage_status"] == "partial"
    assert result.metric_summary["sitemap_url_uncovered_count"] == 1
    assert not any(
        fact.name == "content_object_seen"
        and fact.dimensions.get("content_url") == injected_page_url
        for fact in result.metric_facts
    )


@pytest.mark.parametrize("top_level", [False, True], ids=["page-metadata", "sitemap"])
def test_sitemap_fetches_do_not_follow_off_origin_redirect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    top_level: bool,
) -> None:
    requested: list[str] = []
    page_url = "https://www.ekologus.pl/redirected/"
    destination = (
        "https://attacker.example/redirected-sitemap.xml"
        if top_level
        else "https://attacker.example/metadata/"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            if top_level:
                return httpx.Response(302, headers={"Location": destination})
            return _xml_response(f"<urlset><url><loc>{page_url}</loc></url></urlset>")
        if not top_level and request.url.path == "/redirected/":
            return httpx.Response(302, headers={"Location": destination})
        if request.url.host == "attacker.example":
            if top_level:
                return _xml_response(
                    "<urlset><url><loc>https://www.ekologus.pl/injected/</loc></url></urlset>"
                )
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<h1>attacker</h1>",
            )
        return httpx.Response(404)

    result = _refresh_sitemap_inventory(
        monkeypatch,
        tmp_path,
        handler,
        follow_redirects=True,
    )

    assert destination not in requested
    if top_level:
        assert result.metric_summary["sitemap_coverage_status"] != "complete"
    else:
        fact = next(
            fact
            for fact in result.metric_facts
            if fact.name == "content_object_seen"
            and fact.dimensions.get("content_url") == page_url
        )
        assert fact.dimensions["title_or_h1"] == ""


def test_mixed_sitemap_index_counts_omitted_direct_url_as_uncovered(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    direct_url = "https://www.ekologus.pl/direct-page/"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            return _xml_response(
                "<sitemapindex>"
                "<sitemap><loc>https://www.ekologus.pl/page-sitemap.xml</loc></sitemap>"
                f"<url><loc>{direct_url}</loc></url>"
                "</sitemapindex>"
            )
        if request.url.path == "/page-sitemap.xml":
            return _xml_response(
                "<urlset><url><loc>https://www.ekologus.pl/child-page/</loc></url></urlset>"
            )
        return httpx.Response(404)

    result = _refresh_sitemap_inventory(monkeypatch, tmp_path, handler)

    assert result.metric_summary["sitemap_coverage_status"] == "partial"
    assert result.metric_summary["sitemap_url_uncovered_count"] == 1
    assert all(
        fact.dimensions.get("content_url") != direct_url for fact in result.metric_facts
    )


def test_off_origin_html_canonical_is_not_persisted_as_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    page_url = "https://www.ekologus.pl/canonical-source/"
    safe_page_url = "https://www.ekologus.pl/same-origin-canonical/"
    attacker_url = "https://attacker.example/canonical-target/"
    safe_canonical_url = "https://www.ekologus.pl/canonical-target/"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            return _xml_response(
                f"<urlset><url><loc>{page_url}</loc></url>"
                f"<url><loc>{safe_page_url}</loc></url></urlset>"
            )
        if request.url.path == "/canonical-source/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=(
                    '<html><head><link rel="canonical" '
                    f'href="{attacker_url}"></head>'
                    "<body><main><h1>Canonical source</h1></main></body></html>"
                ),
            )
        if request.url.path == "/same-origin-canonical/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=(
                    '<html><head><link rel="canonical" '
                    f'href="{safe_canonical_url}"></head>'
                    "<body><main><h1>Safe canonical</h1></main></body></html>"
                ),
            )
        return httpx.Response(404)

    result = _refresh_sitemap_inventory(monkeypatch, tmp_path, handler)

    assert not any(
        attacker_url in str(value)
        for fact in result.metric_facts
        for value in fact.dimensions.values()
    )
    facts_by_url = {
        fact.dimensions.get("content_url"): fact
        for fact in result.metric_facts
        if fact.name == "content_object_seen"
    }
    assert facts_by_url[page_url].dimensions["canonical_url"] == ""
    assert facts_by_url[safe_page_url].dimensions["canonical_url"] == safe_canonical_url


@pytest.mark.parametrize("nested", [True, False], ids=["nested-map", "child-map-cap"])
def test_untraversed_child_maps_are_counted_as_uncovered(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    nested: bool,
) -> None:
    import wilq.connectors.wordpress.sitemap_read as sitemap_read_module

    if not nested:
        monkeypatch.setattr(sitemap_read_module, "WORDPRESS_SITEMAP_CHILD_LIMIT", 1)
    fetched_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            if nested:
                return _xml_response(
                    "<sitemapindex>"
                    "<sitemap><loc>https://www.ekologus.pl/first-level.xml</loc></sitemap>"
                    "</sitemapindex>"
                )
            return _xml_response(
                "<sitemapindex>"
                "<sitemap><loc>https://www.ekologus.pl/first-child.xml</loc></sitemap>"
                "<sitemap><loc>https://www.ekologus.pl/omitted-child.xml</loc></sitemap>"
                "</sitemapindex>"
            )
        if request.url.path.endswith(".xml"):
            fetched_paths.append(request.url.path)
        if nested and request.url.path == "/first-level.xml":
            return _xml_response(
                "<sitemapindex><sitemap>"
                "<loc>https://www.ekologus.pl/nested-sitemap.xml</loc>"
                "</sitemap></sitemapindex>"
            )
        if not nested and request.url.path == "/first-child.xml":
            return _xml_response(
                "<urlset><url><loc>https://www.ekologus.pl/first-child-page/</loc></url></urlset>"
            )
        return httpx.Response(404)

    result = _refresh_sitemap_inventory(monkeypatch, tmp_path, handler)

    expected_map = "/first-level.xml" if nested else "/first-child.xml"
    assert fetched_paths == [expected_map]
    assert result.metric_summary["sitemap_coverage_status"] == "partial"
    assert result.metric_summary["sitemap_url_truncated"] is not nested
    assert result.metric_summary["sitemap_url_uncovered_count"] == 1


@pytest.mark.parametrize("is_child_sitemap", [False, True], ids=["direct", "child"])
def test_sitemap_url_caps_mark_omitted_urls_uncovered(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    is_child_sitemap: bool,
) -> None:
    import wilq.connectors.wordpress.sitemap_read as sitemap_read_module

    monkeypatch.setattr(sitemap_read_module, "WORDPRESS_SITEMAP_URL_LIMIT", 2)
    urls = [f"https://www.ekologus.pl/capped-{index}/" for index in range(3)]
    child_requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            if is_child_sitemap:
                return _xml_response(
                    "<sitemapindex><sitemap>"
                    "<loc>https://www.ekologus.pl/capped-child.xml</loc>"
                    "</sitemap><sitemap>"
                    "<loc>https://www.ekologus.pl/skipped-child.xml</loc>"
                    "</sitemap></sitemapindex>"
                )
            entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
            return _xml_response(f"<urlset>{entries}</urlset>")
        if is_child_sitemap and request.url.path.endswith("-child.xml"):
            child_requests.append(request.url.path)
        if is_child_sitemap and request.url.path == "/capped-child.xml":
            entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
            return _xml_response(f"<urlset>{entries}</urlset>")
        return httpx.Response(404)

    result = _refresh_sitemap_inventory(monkeypatch, tmp_path, handler)

    assert result.metric_summary["sitemap_url_count"] == 2
    assert result.metric_summary["sitemap_url_truncated"] is True
    assert result.metric_summary["sitemap_coverage_status"] == "partial"
    assert result.metric_summary["sitemap_url_uncovered_count"] == (
        2 if is_child_sitemap else 1
    )
    assert child_requests == (["/capped-child.xml"] if is_child_sitemap else [])


def _refresh_sitemap_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    follow_redirects: bool = False,
) -> VendorReadResult:
    _configure_wordpress_inventory(monkeypatch, tmp_path)
    return refresh_wordpress_content_inventory(
        "wordpress_ekologus",
        ConnectorRefreshRequest(mode=ConnectorRefreshMode.vendor_read),
        http_client=httpx.Client(
            follow_redirects=follow_redirects,
            transport=httpx.MockTransport(handler),
        ),
    )


@pytest.mark.parametrize(
    ("invalid_entry", "malformed_url"),
    [
        ("<url></url>", None),
        ("<url><loc> </loc></url>", None),
        ("<url><loc>https://[evil/path</loc></url>", "https://[evil/path"),
    ],
    ids=["missing-loc", "blank-loc", "malformed-authority"],
)
def test_invalid_sitemap_locations_are_uncovered_without_failing_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    invalid_entry: str,
    malformed_url: str | None,
) -> None:
    import wilq.connectors.wordpress.sitemap_read as sitemap_read_module

    valid_url = "https://www.ekologus.pl/valid-beside-malformed/"
    if malformed_url:
        def public_url_predicate(value: str | None) -> bool:
            if value == malformed_url:
                raise ValueError("malformed URL authority")
            return content_is_safe_public_url(value)

        monkeypatch.setattr(sitemap_read_module, "content_is_safe_public_url", public_url_predicate)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/wp-json/wp/v2/"):
            return httpx.Response(200, json=[])
        if request.url.path == "/wp-sitemap.xml":
            return _xml_response(
                f"<urlset><url><loc>{valid_url}</loc></url>{invalid_entry}</urlset>"
            )
        return httpx.Response(404)

    result = _refresh_sitemap_inventory(monkeypatch, tmp_path, handler)

    assert result.metric_summary["sitemap_coverage_status"] == "partial"
    assert result.metric_summary["sitemap_url_uncovered_count"] == 1
    assert valid_url in {
        fact.dimensions.get("content_url") for fact in result.metric_facts
    }
