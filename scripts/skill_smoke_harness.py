"""Shared transport and language guards for WILQ skill contract smokes."""

from __future__ import annotations

import json
import unicodedata
import urllib.error
import urllib.request
from typing import Any


def request_json(
    api_base: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    timeout_seconds: float = 60.0,
    timeout: float | None = None,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        request_timeout = timeout if timeout is not None else timeout_seconds
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def has_polish_metric_source_guardrails(value: str) -> bool:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("ł", "l")
    return "metryk" in normalized and "dowod" in normalized and "zrodl" in normalized


def require_polish_language(payload: dict[str, Any], label: str) -> None:
    if payload.get("language") != "pl-PL":
        raise SystemExit(f"{label} must declare language=pl-PL")


def require_evidence_sources(
    payload: dict[str, Any], label: str, required_connector: str | None = None
) -> None:
    if not payload.get("evidence_ids"):
        raise SystemExit(f"{label} lacks evidence IDs")
    connectors = payload.get("source_connectors") or []
    if not connectors:
        raise SystemExit(f"{label} lacks source connectors")
    if required_connector is not None and required_connector not in connectors:
        raise SystemExit(f"{label} lacks source connector {required_connector}")
