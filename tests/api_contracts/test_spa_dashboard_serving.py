from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import cast

import httpx
import pytest
from fastapi import FastAPI

MAIN_MODULE_PATH = (
    Path(__file__).parents[2] / "apps" / "api" / "wilq_api" / "main.py"
)


def load_fresh_app() -> FastAPI:
    spec = importlib.util.spec_from_file_location(
        "_wilq_spa_dashboard_test_main",
        MAIN_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Nie udało się wczytać aplikacji WILQ API.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(FastAPI, module.app)


def build_fake_dashboard_dist(tmp_path: Path) -> tuple[Path, str]:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True)
    index_html = (
        '<!doctype html><html><body><main id="spa-shell">WILQ SPA</main>'
        '<script type="module" src="/assets/app.js"></script></body></html>'
    )
    tmp_path.joinpath("index.html").write_text(index_html, encoding="utf-8")
    assets_dir.joinpath("app.js").write_text(
        'console.log("wilq-spa");',
        encoding="utf-8",
    )
    return tmp_path, index_html


def test_enabled_dashboard_serves_spa_assets_and_preserves_api_routes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dist_path, index_html = build_fake_dashboard_dist(tmp_path)
    monkeypatch.setenv("WILQ_SERVE_DASHBOARD", "true")
    monkeypatch.setenv("WILQ_DASHBOARD_DIST", str(dist_path))
    app = load_fresh_app()

    async def exercise() -> tuple[
        httpx.Response,
        httpx.Response,
        httpx.Response,
        httpx.Response,
        httpx.Response,
    ]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            for route in (
                "/command-center",
                "/command-center/content-review",
                "/dashboard",
                "/unknown-dashboard-path",
            ):
                response = await client.get(route)
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/html")
                assert response.text == index_html
            return (
                await client.get("/assets/app.js"),
                await client.get("/assets/missing.js"),
                await client.get("/api/not-a-route"),
                await client.get("/api/health"),
                await client.get("/"),
            )

    (
        asset_response,
        missing_asset_response,
        unknown_api_response,
        health_response,
        root_response,
    ) = asyncio.run(exercise())

    assert asset_response.status_code == 200
    assert asset_response.text == 'console.log("wilq-spa");'
    assert missing_asset_response.status_code == 404
    assert unknown_api_response.status_code == 404
    assert unknown_api_response.json() == {"detail": "Not Found"}

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "service": "wilq-api"}

    assert root_response.status_code == 200
    assert root_response.headers["content-type"].startswith("application/json")
    assert root_response.json()["service"] == "wilq-api"


@pytest.mark.parametrize(
    ("serve_dashboard", "dist_exists"),
    (("false", True), ("true", False)),
    ids=("disabled", "missing-dist"),
)
def test_unavailable_dashboard_preserves_existing_routes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    serve_dashboard: str,
    dist_exists: bool,
) -> None:
    dist_path = tmp_path / "dist"
    if dist_exists:
        build_fake_dashboard_dist(dist_path)
    monkeypatch.setenv("WILQ_SERVE_DASHBOARD", serve_dashboard)
    monkeypatch.setenv("WILQ_DASHBOARD_DIST", str(dist_path))
    app = load_fresh_app()

    async def exercise() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/command-center"), await client.get("/")

    dashboard_response, root_response = asyncio.run(exercise())

    assert dashboard_response.status_code == 404
    assert dashboard_response.json() == {"detail": "Not Found"}
    assert root_response.status_code == 200
    assert root_response.headers["content-type"].startswith("application/json")
    assert root_response.json()["service"] == "wilq-api"
