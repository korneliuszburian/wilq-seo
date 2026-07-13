#!/usr/bin/env python3
"""Validate and compact API-owned DailyCheckResult input for skill evals."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

SKILL_CONNECTORS = {
    "wilq-daily-command": {"google_ads", "google_search_console", "google_analytics_4"},
    "wilq-gsc-content-doctor": {"google_search_console", "wordpress_ekologus"},
    "wilq-content-strategist": {"google_search_console", "wordpress_ekologus"},
    "wilq-content-operator": {"google_search_console", "wordpress_ekologus"},
    "wilq-ga4-analyst": {"google_analytics_4"},
    "wilq-ads-doctor": {"google_ads"},
}


def _request(api_base: str) -> dict[str, Any]:
    request = urllib.request.Request(f"{api_base.rstrip('/')}/api/marketing/daily-check")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise SystemExit(f"DailyCheckResult request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("DailyCheckResult must be an object")
    return payload


def compact_daily_check(payload: dict[str, Any], skill: str) -> dict[str, Any]:
    if payload.get("status") not in {"ready", "review_ready", "blocked", "degraded"}:
        raise SystemExit("DailyCheckResult has invalid status")
    freshness = payload.get("freshness")
    if not isinstance(freshness, dict) or freshness.get("state") not in {
        "fresh",
        "stale",
        "missing",
        "unknown",
    }:
        raise SystemExit("DailyCheckResult must expose typed freshness")
    items = [
        item
        for item in [
            *(payload.get("safe_next_actions") or []),
            *(payload.get("blocked_recommendations") or []),
            *(payload.get("opportunities") or []),
        ]
        if isinstance(item, dict)
    ]
    required_connectors = SKILL_CONNECTORS.get(skill, set())
    checked = {
        str(item.get("connector_id"))
        for item in [*(payload.get("checked_connectors") or [])]
        if isinstance(item, dict)
    }
    if required_connectors and not required_connectors & checked:
        raise SystemExit(f"DailyCheckResult does not cover {skill} connectors")
    compact_items = [
        {
            "id": item.get("id"),
            "status": item.get("status"),
            "title": item.get("title"),
            "source_connectors": item.get("source_connectors") or [],
            "evidence_ids": item.get("evidence_ids") or [],
            "expert_rule_ids": item.get("expert_rule_ids") or [],
            "freshness": item.get("freshness") or {},
            "next_step": item.get("next_step"),
            "action_ids": item.get("action_ids") or [],
            "false_positive_guards": item.get("false_positive_guards") or [],
        }
        for item in items
    ]
    return {
        "status": payload["status"],
        "freshness": freshness,
        "source_connectors": payload.get("source_connectors") or [],
        "evidence_ids": payload.get("evidence_ids") or [],
        "expert_rule_ids": payload.get("expert_rules_used") or [],
        "blocked_recommendation_ids": [
            item.get("id")
            for item in payload.get("blocked_recommendations") or []
            if isinstance(item, dict)
        ],
        "safe_next_action_ids": [
            item.get("id")
            for item in payload.get("safe_next_actions") or []
            if isinstance(item, dict)
        ],
        "items": compact_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--skill", required=True)
    args = parser.parse_args()
    print(json.dumps(compact_daily_check(_request(args.api_base), args.skill), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
