"""Parent-safe observer for targeted WordPress inventory coverage."""

from __future__ import annotations

import httpx


def _inventory_fetcher():
    try:
        from wilq.connectors.wordpress.inventory import _fetch_public_sitemap_objects
    except (AttributeError, ImportError):  # pragma: no cover - parent-safe guard
        return None
    return _fetch_public_sitemap_objects


def test_targeted_refresh_preserves_baseline_page_metadata() -> None:
    fetch_public_sitemap_objects = _inventory_fetcher()
    assert fetch_public_sitemap_objects is not None, (
        "WordPress public sitemap inventory seam is required"
    )

    baseline_url = "https://public.example/baseline/"
    other_baseline_url = "https://public.example/other-baseline/"
    target_url = "https://public.example/target/"
    labels = {
        "/baseline/": "Baseline",
        "/other-baseline/": "Other baseline",
        "/target/": "Target",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/wp-sitemap.xml":
            return httpx.Response(
                200,
                text=(
                    "<urlset>"
                    f"<url><loc>{baseline_url}</loc></url>"
                    f"<url><loc>{other_baseline_url}</loc></url>"
                    f"<url><loc>{target_url}</loc></url>"
                    "</urlset>"
                ),
            )
        label = labels.get(request.url.path)
        if label is not None:
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text=(
                    "<html><body><main>"
                    f"<h1>{label}</h1><p>{label} content.</p>"
                    "</main></body></html>"
                ),
            )
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = fetch_public_sitemap_objects(
            client,
            "https://dev.example",
            "https://public.example",
            priority_urls=[target_url],
        )

    assert [item["content_url"] for item in result.objects] == [
        baseline_url,
        other_baseline_url,
        target_url,
    ]
    objects = {item["content_url"]: item for item in result.objects}
    assert objects[baseline_url].get("title_or_h1") == "Baseline"
    assert "Baseline content." in objects[baseline_url].get("content_summary", "")
    assert objects[other_baseline_url].get("title_or_h1") == "Other baseline"
    assert objects[target_url].get("title_or_h1") == "Target"
