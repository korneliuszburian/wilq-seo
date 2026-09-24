"""Scoped test route insertion; delete after v2 ActionObject integration supersedes legacy POSTs."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import APIRouter, FastAPI


def insert_legacy_test_post(
    app: FastAPI,
    route: Any,
    *,
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if any(
        getattr(getattr(candidate, "endpoint", None), "_legacy_test_post_for", None) == path
        for candidate in _walk_routes(app.router)
    ):
        return
    route.endpoint._legacy_test_post_for = path
    if not any(
        getattr(candidate, "path", None) == path
        and "POST" in getattr(candidate, "methods", set())
        for candidate in _walk_routes(app.router)
    ):
        raise RuntimeError("Production POST route is not registered.")
    monkeypatch.setattr(app.router, "routes", [route, *app.router.routes])
    monkeypatch.setattr(app, "openapi_schema", None)


def _walk_routes(router: APIRouter) -> list[Any]:
    found: list[Any] = []
    for route in router.routes:
        found.append(route)
        original = getattr(route, "original_router", None)
        if isinstance(original, APIRouter):
            found.extend(_walk_routes(original))
    return found


__all__ = ["insert_legacy_test_post"]
