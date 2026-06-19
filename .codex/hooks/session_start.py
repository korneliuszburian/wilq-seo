from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import cast
from urllib.parse import urlparse


def get_json(url: str) -> dict[str, object] | None:
    parsed = urlparse(url)
    allowed_hosts = {
        "127.0.0.1",
        "localhost",
        "::1",
        *filter(None, os.getenv("WILQ_API_ALLOWED_HOSTS", "").split(",")),
    }
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed_hosts:
        print("WILQ hook skipped non-local or unsupported API URL.")
        return None
    try:
        with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310  # nosec B310
            return cast(dict[str, object], json.loads(response.read().decode("utf-8")))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def main() -> None:
    base_url = os.getenv("WILQ_API_BASE_URL", "http://127.0.0.1:8000")
    health = get_json(f"{base_url}/api/health")
    status = get_json(f"{base_url}/api/system/status") if health else None
    if not health:
        print("WILQ API unreachable. Use WILQ API for marketing metrics when it is available.")
        return
    connector_summary = (status or {}).get("connector_summary", {})
    print(
        "WILQ API reachable. Codex must fetch WILQ API context for marketing metrics. "
        f"Connector summary: {connector_summary}"
    )


if __name__ == "__main__":
    main()
