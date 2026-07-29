from __future__ import annotations

from wilq.codex.app_server import StdioCodexAppServerClient


def content_codex_app_server_client() -> StdioCodexAppServerClient:
    """Construct the bounded server-side Codex client for active content flows."""

    return StdioCodexAppServerClient()


__all__ = ["content_codex_app_server_client"]
