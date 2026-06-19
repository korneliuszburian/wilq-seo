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
    budget_pacing_read_contract = ads_diagnostics.get("budget_pacing_read_contract") or {}
    recommendations_read_contract = (
        ads_diagnostics.get("recommendations_read_contract") or {}
    )
    impression_share_read_contract = (
        ads_diagnostics.get("impression_share_read_contract") or {}
    )
    change_history_read_contract = (
        ads_diagnostics.get("change_history_read_contract") or {}
    )
    search_terms_read_contract = ads_diagnostics.get("search_terms_read_contract") or {}
    search_term_safety_read_contract = (
        ads_diagnostics.get("search_term_safety_read_contract") or {}
    )
    negative_keywords_read_contract = (
        ads_diagnostics.get("negative_keywords_read_contract") or {}
    )
    decision_queue = ads_diagnostics.get("decision_queue") or []
    pack_decision_queue = pack.get("ads_diagnostics", {}).get("decision_queue") or []
    budget_decision = _find_decision(decision_queue, "ads_review_budget_context")
    pack_budget_decision = _find_decision(pack_decision_queue, "ads_review_budget_context")
    if (
        campaign_read_contract.get("status") == "ready"
        and campaign_read_contract.get("campaign_rows")
        and "act_prepare_ads_campaign_review_queue"
        not in (ads_diagnostics.get("action_ids") or [])
    ):
        raise SystemExit("Ready campaign diagnostics must expose campaign review ActionObject")
    if budget_pacing_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose budget_pacing_read_contract")
    if budget_pacing_read_contract.get("status") == "ready":
        if not budget_pacing_read_contract.get("budget_rows"):
            raise SystemExit("Ready budget pacing contract must expose budget rows")
        pack_budget_contract = (
            pack.get("ads_diagnostics", {}).get("budget_pacing_read_contract") or {}
        )
        if not pack_budget_contract.get("budget_rows"):
            raise SystemExit("Context pack must include ready budget pacing rows")
        if "budget apply" not in budget_pacing_read_contract.get("blocked_claims", []):
            raise SystemExit("Budget pacing contract must keep budget apply blocked")
        expected_budget_card = "card_google_ads_budget_review_playbook"
        expected_budget_rules = {
            "ads_scaling_candidates_v1",
            "ads_recommendations_v1",
            "ads_principles_v1",
        }
        if expected_budget_card not in budget_decision.get("knowledge_card_ids", []):
            raise SystemExit("Budget decision must expose budget review knowledge card")
        if not expected_budget_rules <= set(budget_decision.get("expert_rule_ids", [])):
            raise SystemExit("Budget decision must expose budget review expert rules")
        if pack_budget_decision.get("knowledge_card_ids") != budget_decision.get(
            "knowledge_card_ids"
        ):
            raise SystemExit("Context pack budget decision knowledge cards differ")
        if pack_budget_decision.get("expert_rule_ids") != budget_decision.get(
            "expert_rule_ids"
        ):
            raise SystemExit("Context pack budget decision expert rules differ")
    if recommendations_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose recommendations_read_contract")
    if not recommendations_read_contract.get("blocked_claims"):
        raise SystemExit("Recommendations contract must list blocked claims")
    if recommendations_read_contract.get("status") == "ready":
        pack_recommendations_contract = (
            pack.get("ads_diagnostics", {}).get("recommendations_read_contract") or {}
        )
        if pack_recommendations_contract.get("summary") != recommendations_read_contract.get(
            "summary"
        ):
            raise SystemExit("Context pack recommendations contract differs")
        if "recommendation apply" not in recommendations_read_contract.get(
            "blocked_claims",
            [],
        ):
            raise SystemExit("Recommendations contract must keep apply blocked")
    elif "recommendations" not in recommendations_read_contract.get(
        "missing_read_contracts",
        [],
    ):
        raise SystemExit("Blocked recommendations contract must list missing recommendations")
    if impression_share_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose impression_share_read_contract")
    if not impression_share_read_contract.get("blocked_claims"):
        raise SystemExit("Impression share contract must list blocked claims")
    if impression_share_read_contract.get("status") == "ready":
        pack_impression_share_contract = (
            pack.get("ads_diagnostics", {}).get("impression_share_read_contract") or {}
        )
        if pack_impression_share_contract.get("summary") != impression_share_read_contract.get(
            "summary"
        ):
            raise SystemExit("Context pack impression share contract differs")
        if "budget apply" not in impression_share_read_contract.get("blocked_claims", []):
            raise SystemExit("Impression share contract must keep budget apply blocked")
    elif "impression_share" not in impression_share_read_contract.get(
        "missing_read_contracts",
        [],
    ):
        raise SystemExit("Blocked impression share contract must list missing impression_share")
    if change_history_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose change_history_read_contract")
    if not change_history_read_contract.get("blocked_claims"):
        raise SystemExit("Change history contract must list blocked claims")
    if change_history_read_contract.get("status") == "ready":
        pack_change_history_contract = (
            pack.get("ads_diagnostics", {}).get("change_history_read_contract") or {}
        )
        if pack_change_history_contract.get("summary") != change_history_read_contract.get(
            "summary"
        ):
            raise SystemExit("Context pack change history contract differs")
        if "change impact" not in change_history_read_contract.get("blocked_claims", []):
            raise SystemExit("Change history contract must keep change impact blocked")
    elif "change_history" not in change_history_read_contract.get(
        "missing_read_contracts",
        [],
    ):
        raise SystemExit("Blocked change history contract must list missing change_history")
    if search_term_safety_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose search_term_safety_read_contract")
    if not search_term_safety_read_contract.get("blocked_claims"):
        raise SystemExit("Search-term safety contract must list blocked claims")
    if search_term_safety_read_contract.get("status") == "ready":
        pack_safety_contract = (
            pack.get("ads_diagnostics", {}).get("search_term_safety_read_contract") or {}
        )
        if pack_safety_contract.get("summary") != search_term_safety_read_contract.get(
            "summary"
        ):
            raise SystemExit("Context pack search-term safety contract differs")
        if "negative keyword apply" not in search_term_safety_read_contract.get(
            "blocked_claims",
            [],
        ):
            raise SystemExit("Search-term safety contract must keep apply blocked")
    elif "search_term_90d_read" not in search_term_safety_read_contract.get(
        "missing_read_contracts",
        [],
    ):
        raise SystemExit("Blocked search-term safety contract must list missing 90d read")
    if negative_keywords_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose negative_keywords_read_contract")
    if not negative_keywords_read_contract.get("blocked_claims"):
        raise SystemExit("Negative keyword contract must list blocked claims")
    if negative_keywords_read_contract.get("status") == "ready":
        if not negative_keywords_read_contract.get("candidates"):
            raise SystemExit("Ready negative keyword contract must expose candidates")
        if not negative_keywords_read_contract.get("payload_preview"):
            raise SystemExit(
                "Ready negative keyword contract must expose payload_preview"
            )
        if "negative_keyword_payload_preview" in (
            negative_keywords_read_contract.get("missing_read_contracts") or []
        ):
            raise SystemExit(
                "Ready negative keyword contract must not list payload preview as missing"
            )
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
                "knowledge_card_ids": _unique(
                    [
                        *[
                            card_id
                            for decision in decision_queue
                            for card_id in decision.get("knowledge_card_ids", [])
                        ],
                        *[
                            card.get("id")
                            for card in pack.get("knowledge_card_summaries", [])
                            if card.get("id")
                        ],
                    ]
                ),
                "expert_rule_ids": _unique(
                    [
                        *[
                            rule_id
                            for decision in decision_queue
                            for rule_id in decision.get("expert_rule_ids", [])
                        ],
                        *[
                            rule.get("id")
                            for rule in pack.get("expert_rule_summaries", [])
                            if rule.get("id")
                        ],
                    ]
                ),
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
                        "has_campaign_review_action": (
                            "act_prepare_ads_campaign_review_queue"
                            in (ads_diagnostics.get("action_ids") or [])
                        ),
                    },
                    "budget_pacing_read_contract": {
                        "status": budget_pacing_read_contract.get("status"),
                        "summary": budget_pacing_read_contract.get("summary"),
                        "allowed_metrics": budget_pacing_read_contract.get(
                            "allowed_metrics", []
                        ),
                        "missing_read_contracts": budget_pacing_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "row_count": len(
                            budget_pacing_read_contract.get("budget_rows") or []
                        ),
                    },
                    "budget_decision": {
                        "id": budget_decision.get("id"),
                        "status": budget_decision.get("status"),
                        "knowledge_card_ids": budget_decision.get(
                            "knowledge_card_ids", []
                        ),
                        "expert_rule_ids": budget_decision.get("expert_rule_ids", []),
                        "action_ids": budget_decision.get("action_ids", []),
                        "blocked_claims": budget_decision.get("blocked_claims", []),
                    },
                    "recommendations_read_contract": {
                        "status": recommendations_read_contract.get("status"),
                        "summary": recommendations_read_contract.get("summary"),
                        "allowed_metrics": recommendations_read_contract.get(
                            "allowed_metrics",
                            [],
                        ),
                        "missing_read_contracts": recommendations_read_contract.get(
                            "missing_read_contracts",
                            [],
                        ),
                        "row_count": len(
                            recommendations_read_contract.get("recommendation_rows") or []
                        ),
                        "blocked_claims": recommendations_read_contract.get(
                            "blocked_claims",
                            [],
                        ),
                    },
                    "impression_share_read_contract": {
                        "status": impression_share_read_contract.get("status"),
                        "summary": impression_share_read_contract.get("summary"),
                        "allowed_metrics": impression_share_read_contract.get(
                            "allowed_metrics",
                            [],
                        ),
                        "missing_read_contracts": impression_share_read_contract.get(
                            "missing_read_contracts",
                            [],
                        ),
                        "row_count": len(
                            impression_share_read_contract.get("impression_share_rows") or []
                        ),
                        "blocked_claims": impression_share_read_contract.get(
                            "blocked_claims",
                            [],
                        ),
                    },
                    "change_history_read_contract": {
                        "status": change_history_read_contract.get("status"),
                        "summary": change_history_read_contract.get("summary"),
                        "allowed_metrics": change_history_read_contract.get(
                            "allowed_metrics",
                            [],
                        ),
                        "missing_read_contracts": change_history_read_contract.get(
                            "missing_read_contracts",
                            [],
                        ),
                        "row_count": len(
                            change_history_read_contract.get("change_history_rows") or []
                        ),
                        "blocked_claims": change_history_read_contract.get(
                            "blocked_claims",
                            [],
                        ),
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
                    "search_term_safety_read_contract": {
                        "status": search_term_safety_read_contract.get("status"),
                        "summary": search_term_safety_read_contract.get("summary"),
                        "allowed_metrics": search_term_safety_read_contract.get(
                            "allowed_metrics",
                            [],
                        ),
                        "missing_read_contracts": search_term_safety_read_contract.get(
                            "missing_read_contracts",
                            [],
                        ),
                        "row_count": len(
                            search_term_safety_read_contract.get("safety_rows") or []
                        ),
                        "blocked_claims": search_term_safety_read_contract.get(
                            "blocked_claims",
                            [],
                        ),
                    },
                    "negative_keywords_read_contract": {
                        "status": negative_keywords_read_contract.get("status"),
                        "summary": negative_keywords_read_contract.get("summary"),
                        "candidate_count": len(
                            negative_keywords_read_contract.get("candidates") or []
                        ),
                        "payload_preview_count": len(
                            negative_keywords_read_contract.get("payload_preview") or []
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


def _find_decision(decisions: list[dict[str, Any]], decision_id: str) -> dict[str, Any]:
    for decision in decisions:
        if decision.get("id") == decision_id:
            return decision
    return {}


def _unique(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
