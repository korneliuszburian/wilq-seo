#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SKILL_NAME = "wilq-ads-doctor"
REQUIRED_CONNECTORS = ["google_ads"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "ads_diagnostics",
}


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


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    health = request_json(args.api_base, "GET", "/api/health")
    if health.get("status") != "ok":
        raise SystemExit(f"WILQ API health is not ok: {health}")

    pack = request_json(args.api_base, "POST", "/api/codex/context-pack", {"skill": SKILL_NAME})
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(pack))
    if missing:
        raise SystemExit(f"Context pack missing required keys: {', '.join(missing)}")

    ads_diagnostics = request_json(args.api_base, "GET", "/api/ads/diagnostics")
    if ads_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Ads diagnostics language must be pl-PL")
    if not isinstance(ads_diagnostics.get("sections"), list) or not ads_diagnostics["sections"]:
        raise SystemExit("Ads diagnostics must expose sections")
    if pack.get("ads_diagnostics", {}).get("evidence_ids") != ads_diagnostics.get("evidence_ids"):
        raise SystemExit("Context pack ads_diagnostics evidence IDs differ from endpoint")
    if pack.get("ads_diagnostics", {}).get("action_ids") != ads_diagnostics.get("action_ids"):
        raise SystemExit("Context pack ads_diagnostics action IDs differ from endpoint")
    blocked_handoff = ads_diagnostics.get("blocked_handoff")
    if ads_diagnostics.get("live_data_available") is True:
        if blocked_handoff is not None:
            raise SystemExit("Live Ads diagnostics must not expose OAuth blocked_handoff")
    else:
        if not isinstance(blocked_handoff, dict):
            raise SystemExit("Blocked Ads diagnostics must expose blocked_handoff")
        if blocked_handoff.get("status") != "blocked":
            raise SystemExit("Blocked Ads handoff must expose blocked status")
        if "google_ads" not in blocked_handoff.get("source_connectors", []):
            raise SystemExit("Ads blocked_handoff must include google_ads source connector")
        if not blocked_handoff.get("evidence_ids"):
            raise SystemExit("Ads blocked_handoff must include evidence IDs")
        if not blocked_handoff.get("action_ids"):
            raise SystemExit("Blocked Ads handoff must include action IDs")
        blocked_claims = set(blocked_handoff.get("blocked_claims", []))
        if not {"ROAS", "search terms"} <= blocked_claims:
            raise SystemExit("Blocked Ads handoff must list blocked ROAS and search terms claims")
    campaign_read_contract = ads_diagnostics.get("campaign_read_contract") or {}
    search_terms_read_contract = ads_diagnostics.get("search_terms_read_contract") or {}
    negative_keywords_read_contract = (
        ads_diagnostics.get("negative_keywords_read_contract") or {}
    )
    if negative_keywords_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose negative_keywords_read_contract")
    if not negative_keywords_read_contract.get("blocked_claims"):
        raise SystemExit("Negative keyword contract must list blocked claims")
    if negative_keywords_read_contract.get("status") == "ready":
        if not negative_keywords_read_contract.get("candidates"):
            raise SystemExit("Ready negative keyword contract must expose candidates")
        if "act_prepare_negative_keyword_review_queue" not in (
            negative_keywords_read_contract.get("action_ids") or []
        ):
            raise SystemExit("Ready negative keyword contract must expose ActionObject")
    elif not negative_keywords_read_contract.get("missing_read_contracts"):
        raise SystemExit("Blocked negative keyword contract must list missing read contracts")

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    brief_items = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "kind": item.get("kind"),
            "source_connectors": item.get("source_connectors", []),
            "evidence_ids": item.get("evidence_ids", []),
            "action_ids": item.get("action_ids", []),
            "metric_facts": item.get("metric_facts", []),
        }
        for section in brief.get("sections", [])
        for item in section.get("items", [])
        if any(
            connector in REQUIRED_CONNECTORS
            for connector in item.get("source_connectors", [])
        )
    ][:8]

    connector_results = []
    for connector in REQUIRED_CONNECTORS:
        quoted = urllib.parse.quote(connector, safe="")
        status = request_json(args.api_base, "GET", f"/api/connectors/{quoted}/status")
        connector_results.append(
            {
                "id": status.get("id"),
                "status": status.get("status"),
                "configured": status.get("configured"),
                "missing_credentials": status.get("missing_credentials", []),
                "error": status.get("error"),
            }
        )

    instruction = str(pack.get("strict_instruction", "")).lower()
    if "must not invent metrics" not in instruction or "evidence" not in instruction:
        raise SystemExit("Context pack strict instruction does not include evidence guardrails")

    print(
        json.dumps(
            {
                "skill": SKILL_NAME,
                "api_base": args.api_base,
                "health": health.get("status"),
                "required_connectors": connector_results,
                "ads_diagnostics": {
                    "live_data_available": ads_diagnostics.get("live_data_available"),
                    "blocker_count": ads_diagnostics.get("blocker_count"),
                    "campaign_read_contract": {
                        "status": campaign_read_contract.get("status"),
                        "summary": campaign_read_contract.get("summary"),
                        "allowed_metrics": campaign_read_contract.get("allowed_metrics", []),
                        "missing_read_contracts": campaign_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "row_count": len(campaign_read_contract.get("campaign_rows") or []),
                    },
                    "search_terms_read_contract": {
                        "status": search_terms_read_contract.get("status"),
                        "summary": search_terms_read_contract.get("summary"),
                        "allowed_metrics": search_terms_read_contract.get(
                            "allowed_metrics", []
                        ),
                        "missing_read_contracts": search_terms_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "row_count": len(
                            search_terms_read_contract.get("search_term_rows") or []
                        ),
                    },
                    "negative_keywords_read_contract": {
                        "status": negative_keywords_read_contract.get("status"),
                        "summary": negative_keywords_read_contract.get("summary"),
                        "candidate_count": len(
                            negative_keywords_read_contract.get("candidates") or []
                        ),
                        "missing_read_contracts": negative_keywords_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "blocked_claims": negative_keywords_read_contract.get(
                            "blocked_claims", []
                        ),
                        "action_ids": negative_keywords_read_contract.get("action_ids", []),
                    },
                    "blocked_handoff": _blocked_handoff_summary(blocked_handoff),
                    "section_ids": [
                        section.get("id")
                        for section in ads_diagnostics.get("sections", [])
                        if section.get("id")
                    ],
                    "evidence_ids": ads_diagnostics.get("evidence_ids", []),
                    "action_ids": ads_diagnostics.get("action_ids", []),
                    "blocked_claims": [
                        claim
                        for section in ads_diagnostics.get("sections", [])
                        for claim in section.get("blocked_claims", [])
                    ][:20],
                    "latest_refresh_status": (
                        ads_diagnostics.get("latest_refresh") or {}
                    ).get("status"),
                },
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "evidence_ids": [
                    item.get("id")
                    for item in (pack.get("evidence_summaries") or [])
                    if item.get("id")
                ][:20],
                "opportunity_ids": [
                    item.get("id")
                    for item in (pack.get("top_opportunities") or [])
                    if item.get("id")
                ][:20],
                "action_ids": [
                    item.get("id")
                    for item in (pack.get("active_action_objects") or [])
                    if item.get("id")
                ][:20],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _blocked_handoff_summary(blocked_handoff: dict[str, Any] | None) -> dict[str, Any] | None:
    if blocked_handoff is None:
        return None
    return {
        "status": blocked_handoff.get("status"),
        "title": blocked_handoff.get("title"),
        "source_connectors": blocked_handoff.get("source_connectors", []),
        "evidence_ids": blocked_handoff.get("evidence_ids", []),
        "action_ids": blocked_handoff.get("action_ids", []),
    }


if __name__ == "__main__":
    raise SystemExit(main())
