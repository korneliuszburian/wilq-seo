#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any

REQUIRED_KEYS = {
    "strict_instruction",
    "available_connectors",
    "connector_status",
    "connector_refresh_runs",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "knowledge_card_summaries",
    "expert_rule_summaries",
    "expert_capabilities",
}
FORBIDDEN_MARKERS = ("fake_metric", "mock_metric", "seed_metric")


def request_json(api_base: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from {path}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach WILQ API at {api_base}: {exc.reason}") from exc


def scan_strings(value: Any) -> list[str]:
    hits: list[str] = []
    if isinstance(value, str):
        lowered = value.lower()
        hits.extend(marker for marker in FORBIDDEN_MARKERS if marker in lowered)
    elif isinstance(value, dict):
        for nested in value.values():
            hits.extend(scan_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            hits.extend(scan_strings(nested))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test wilq-daily-command against WILQ API")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    health = request_json(args.api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    pack = request_json(
        args.api_base, "POST", "/api/codex/context-pack", {"skill": "wilq-daily-command"}
    )
    missing = sorted(REQUIRED_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")

    instruction = str(pack.get("strict_instruction", "")).lower()
    if "must not invent metrics" not in instruction or "evidence" not in instruction:
        raise SystemExit(
            "Context pack strict instruction does not include WILQ evidence/API guardrails"
        )

    marker_hits = sorted(set(scan_strings(pack)))
    if marker_hits:
        raise SystemExit(f"Context pack contains forbidden marker(s): {', '.join(marker_hits)}")

    connector_status = pack.get("connector_status") or []
    configured = [item.get("id") for item in connector_status if item.get("configured")]
    blocked = [
        item.get("id")
        for item in connector_status
        if item.get("status") in {"missing_credentials", "disabled"}
    ]
    summary = {
        "api_base": args.api_base,
        "health": health.get("status"),
        "configured_connectors": configured,
        "blocked_or_disabled_connectors": blocked,
        "evidence_count": len(pack.get("evidence_summaries") or []),
        "opportunity_ids": [item.get("id") for item in (pack.get("top_opportunities") or [])[:5]],
        "action_ids": [item.get("id") for item in (pack.get("active_action_objects") or [])[:5]],
        "refresh_run_count": len(pack.get("connector_refresh_runs") or []),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
