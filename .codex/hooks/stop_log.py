from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse


def emit_continue(message: str) -> None:
    print(
        json.dumps(
            {
                "continue": True,
                "systemMessage": message,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def allowed_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    allowed_hosts = {
        "127.0.0.1",
        "localhost",
        "::1",
        *filter(None, os.getenv("WILQ_API_ALLOWED_HOSTS", "").split(",")),
    }
    return parsed.scheme in {"http", "https"} and parsed.hostname in allowed_hosts


def main() -> None:
    base_url = os.getenv("WILQ_API_BASE_URL", "http://127.0.0.1:8000")
    if not allowed_base_url(base_url):
        emit_continue("WILQ Stop hook skipped non-local or unsupported API URL.")
        return
    request = urllib.request.Request(
        f"{base_url}/api/codex/telemetry/stop-events",
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=2).close()  # noqa: S310  # nosec B310
    except (OSError, urllib.error.URLError):
        emit_continue("WILQ Stop hook skipped telemetry because API is unreachable.")


if __name__ == "__main__":
    main()
