from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse


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
        print("WILQ Stop hook skipped non-local or unsupported API URL.")
        return
    payload = {
        "id": f"codex_stop_{int(time.time())}",
        "skill": None,
        "hook": "Stop",
        "source": "codex_hook",
        "status": "completed",
        "used_endpoints": [],
        "evidence_ids": [],
        "action_ids": [],
    }
    request = urllib.request.Request(
        f"{base_url}/api/codex/runs",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=2).close()  # noqa: S310  # nosec B310
    except (OSError, urllib.error.URLError):
        print("WILQ Stop hook skipped Codex run logging because API is unreachable.")


if __name__ == "__main__":
    main()
