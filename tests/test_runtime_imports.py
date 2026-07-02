from __future__ import annotations

import importlib


def test_committed_runtime_entrypoints_import() -> None:
    for module_name in (
        "wilq.cli",
        "apps.api.wilq_api.main",
        "wilq.connectors.registry",
        "wilq.connectors.google_auth",
        "apps.api.wilq_api.routers.system",
        "wilq.credentials.runtime",
    ):
        importlib.import_module(module_name)
