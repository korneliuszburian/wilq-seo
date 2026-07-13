#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from ads_change_history_assertions import validate_change_history_contract
from ads_change_impact_assertions import validate_change_impact_contract
from ads_custom_segments_assertions import validate_custom_segments_contract
from ads_impression_share_assertions import validate_impression_share_contract
from ads_keyword_match_assertions import validate_keyword_match_context_contract
from ads_keyword_planner_assertions import validate_keyword_planner_contract
from ads_negative_keyword_assertions import validate_negative_keyword_contract
from ads_readiness_assertions import validate_optimizer_readiness
from ads_recommendation_assertions import validate_recommendations_contract
from ads_search_term_ngram_assertions import validate_search_term_ngram_contract
from ads_search_term_review_assertions import validate_search_term_review_contract
from ads_search_term_safety_assertions import validate_search_term_safety_contract
from ads_smoke_runtime import load_ads_context

from scripts.skill_smoke_harness import has_polish_metric_source_guardrails, request_json

SKILL_NAME = "wilq-ads-doctor"
REQUIRED_CONNECTORS = ["google_ads"]
VALIDATED_ACTION_IDS = [
    "act_prepare_ads_campaign_review_queue",
    "act_prepare_google_ads_recommendation_review_queue",
    "act_prepare_custom_segments_from_search_terms",
    "act_prepare_negative_keyword_review_queue",
]
MAX_CONTEXT_PACK_BYTES = 260_000
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "ads_diagnostics",
    "knowledge_card_summaries",
    "expert_rule_summaries",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Smoke test {SKILL_NAME} WILQ API contract")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    runtime = load_ads_context(
        args.api_base,
        required_context_keys=REQUIRED_CONTEXT_KEYS,
        max_context_pack_bytes=MAX_CONTEXT_PACK_BYTES,
    )
    health = runtime["health"]
    pack = runtime["pack"]
    ads_diagnostics = runtime["ads_diagnostics"]
    full_pack = runtime["full_pack"]
    pack_bytes = runtime["pack_bytes"]
    blocked_handoff = runtime["blocked_handoff"]
    campaign_read_contract = ads_diagnostics.get("campaign_read_contract") or {}
    campaign_triage_read_contract = ads_diagnostics.get("campaign_triage_read_contract") or {}
    account_currency_read_contract = ads_diagnostics.get("account_currency_read_contract") or {}
    business_context_read_contract = ads_diagnostics.get("business_context_read_contract") or {}
    budget_pacing_read_contract = ads_diagnostics.get("budget_pacing_read_contract") or {}
    recommendations_read_contract = ads_diagnostics.get("recommendations_read_contract") or {}
    impression_share_read_contract = ads_diagnostics.get("impression_share_read_contract") or {}
    change_history_read_contract = ads_diagnostics.get("change_history_read_contract") or {}
    change_impact_readiness_contract = ads_diagnostics.get("change_impact_readiness_contract") or {}
    search_terms_read_contract = ads_diagnostics.get("search_terms_read_contract") or {}
    search_term_review_summary_contract = (
        ads_diagnostics.get("search_term_review_summary_contract") or {}
    )
    search_term_safety_read_contract = ads_diagnostics.get("search_term_safety_read_contract") or {}
    keyword_match_context_read_contract = (
        ads_diagnostics.get("keyword_match_context_read_contract") or {}
    )
    keyword_planner_read_contract = ads_diagnostics.get("keyword_planner_read_contract") or {}
    negative_keywords_read_contract = ads_diagnostics.get("negative_keywords_read_contract") or {}
    custom_segments_read_contract = ads_diagnostics.get("custom_segments_read_contract") or {}
    decision_queue = ads_diagnostics.get("decision_queue") or []
    pack_decision_queue = pack.get("ads_diagnostics", {}).get("decision_queue") or []
    full_pack_decision_queue = full_pack.get("ads_diagnostics", {}).get("decision_queue") or []
    endpoint_decision_ids = [decision.get("id") for decision in decision_queue]
    full_pack_decision_ids = [decision.get("id") for decision in full_pack_decision_queue]
    if full_pack_decision_ids != endpoint_decision_ids:
        raise SystemExit("Full Ads context-pack decision_queue differs from endpoint")
    if len(pack_decision_queue) > len(decision_queue):
        raise SystemExit("Default Ads context-pack decision_queue cannot exceed endpoint")
    validate_context_lineage(pack)
    optimizer_readiness_contract, budget_decision, pack_budget_decision = (
        validate_optimizer_readiness(
            ads_diagnostics,
            pack,
            decision_queue,
            pack_decision_queue,
            _find_decision,
            _find_readiness_item,
        )
    )
    if (
        campaign_read_contract.get("status") == "ready"
        and campaign_read_contract.get("campaign_rows")
        and "act_prepare_ads_campaign_review_queue" not in (ads_diagnostics.get("action_ids") or [])
    ):
        raise SystemExit("Ready campaign diagnostics must expose campaign review action")
    if campaign_read_contract.get("status") == "ready" and campaign_read_contract.get(
        "campaign_rows"
    ):
        if campaign_triage_read_contract.get("status") != "ready":
            raise SystemExit("Ready campaign diagnostics must expose campaign triage contract")
        triage_rows = campaign_triage_read_contract.get("triage_rows") or []
        if not triage_rows:
            raise SystemExit("Ready campaign triage contract must expose triage rows")
        if "zmarnowany budżet" not in campaign_triage_read_contract.get(
            "blocked_claims",
            [],
        ):
            raise SystemExit("Campaign triage contract must keep zmarnowany budżet blocked")
        pack_triage_contract = (
            pack.get("ads_diagnostics", {}).get("campaign_triage_read_contract") or {}
        )
        if pack_triage_contract.get("summary") != campaign_triage_read_contract.get("summary"):
            raise SystemExit("Context pack campaign triage contract differs")
        if not pack_triage_contract.get("triage_rows"):
            raise SystemExit("Context pack must include campaign triage rows")
        if "act_prepare_ads_campaign_review_queue" not in (
            campaign_triage_read_contract.get("action_ids") or []
        ):
            raise SystemExit("Campaign triage contract must expose campaign review action")
    if account_currency_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose account_currency_read_contract")
    pack_currency_contract = (
        pack.get("ads_diagnostics", {}).get("account_currency_read_contract") or {}
    )
    if pack_currency_contract.get("summary") != account_currency_read_contract.get("summary"):
        raise SystemExit("Context pack account currency contract differs")
    if account_currency_read_contract.get("status") == "ready":
        currency_code = account_currency_read_contract.get("currency_code")
        if not isinstance(currency_code, str) or len(currency_code) != 3:
            raise SystemExit("Ready account currency contract must expose ISO currency code")
    elif "account_currency" not in account_currency_read_contract.get(
        "missing_read_contracts",
        [],
    ):
        raise SystemExit("Blocked account currency contract must list missing account_currency")
    if business_context_read_contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose business_context_read_contract")
    pack_business_context_contract = (
        pack.get("ads_diagnostics", {}).get("business_context_read_contract") or {}
    )
    if pack_business_context_contract.get("summary") != business_context_read_contract.get(
        "summary"
    ):
        raise SystemExit("Context pack business context contract differs")
    strategy_readiness_contract = (
        business_context_read_contract.get("strategy_review_readiness_contract") or {}
    )
    pack_strategy_readiness_contract = (
        pack_business_context_contract.get("strategy_review_readiness_contract") or {}
    )
    if strategy_readiness_contract.get("id") != "ads_strategy_review_readiness_contract":
        raise SystemExit("Business context must expose strategy review readiness contract")
    if strategy_readiness_contract.get("apply_allowed") is not False:
        raise SystemExit("Strategy review readiness must keep apply_allowed=false")
    if "ocena opłacalności" not in strategy_readiness_contract.get(
        "blocked_claims",
        [],
    ):
        raise SystemExit("Strategy review readiness must block ocena opłacalności")
    if pack_strategy_readiness_contract.get("id") != (strategy_readiness_contract.get("id")):
        raise SystemExit("Context pack strategy review readiness ID differs")
    if pack_strategy_readiness_contract.get("status") != (
        strategy_readiness_contract.get("status")
    ):
        raise SystemExit("Context pack strategy review readiness status differs")
    if pack_strategy_readiness_contract.get("apply_allowed") is not False:
        raise SystemExit("Context pack strategy review readiness must keep apply blocked")
    if "human_strategy_review" not in pack_strategy_readiness_contract.get(
        "required_validation",
        [],
    ):
        raise SystemExit("Context pack strategy review readiness must require review")
    if "ocena opłacalności" not in pack_strategy_readiness_contract.get(
        "blocked_claims",
        [],
    ):
        raise SystemExit("Context pack strategy review readiness must block opłacalność")
    if business_context_read_contract.get("status") == "blocked" and not (
        business_context_read_contract.get("missing_read_contracts") or []
    ):
        raise SystemExit("Blocked business context contract must list missing contracts")
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
        shared_budget_rows = budget_pacing_read_contract.get("shared_budget_distribution_rows")
        if shared_budget_rows is None:
            raise SystemExit("Budget pacing contract must expose shared budget rows")
        budget_rows = budget_pacing_read_contract.get("budget_rows") or []
        if all(row.get("budget_id") for row in budget_rows) and (
            "shared_budget_distribution"
            in (budget_pacing_read_contract.get("missing_read_contracts") or [])
        ):
            raise SystemExit(
                "Budget pacing contract must not miss shared budget distribution "
                "when all budget rows expose budget_id"
            )
        if pack_budget_contract.get("shared_budget_distribution_rows") is None:
            raise SystemExit("Context pack must include shared budget distribution rows")
        if "zmiana budżetu" not in budget_pacing_read_contract.get("blocked_claims", []):
            raise SystemExit("Budget pacing contract must keep zmiana budżetu blocked")
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
        if pack_budget_decision.get("expert_rule_ids") != budget_decision.get("expert_rule_ids"):
            raise SystemExit("Context pack budget decision expert rules differ")
    recommendations_read_contract = validate_recommendations_contract(ads_diagnostics, pack)
    impression_share_read_contract = validate_impression_share_contract(ads_diagnostics, pack)
    change_history_read_contract = validate_change_history_contract(ads_diagnostics, pack)
    change_impact_readiness_contract = validate_change_impact_contract(
        ads_diagnostics, pack, change_history_read_contract
    )
    search_term_review_summary_contract = validate_search_term_review_contract(
        ads_diagnostics, pack
    )
    search_term_safety_read_contract = validate_search_term_safety_contract(ads_diagnostics, pack)
    keyword_match_context_read_contract = validate_keyword_match_context_contract(
        ads_diagnostics, pack
    )
    keyword_planner_read_contract = validate_keyword_planner_contract(ads_diagnostics, pack)
    custom_segments_read_contract = validate_custom_segments_contract(
        ads_diagnostics, pack, keyword_planner_read_contract
    )
    custom_segment_idea_count = sum(
        len(candidate.get("keyword_planner_ideas") or [])
        for candidate in custom_segments_read_contract.get("candidates") or []
    )
    validate_search_term_ngram_contract(ads_diagnostics)
    negative_keywords_read_contract = validate_negative_keyword_contract(ads_diagnostics)

    action_ids = ads_diagnostics.get("action_ids") or []
    if ads_diagnostics.get("live_data_available") is True:
        missing_validated_actions = sorted(set(VALIDATED_ACTION_IDS) - set(action_ids))
        if missing_validated_actions:
            raise SystemExit(
                "Live Ads diagnostics must expose review actions for validation: "
                + ", ".join(missing_validated_actions)
            )
    action_validations = []
    for action_id in VALIDATED_ACTION_IDS:
        if action_id not in action_ids:
            continue
        quoted_action = urllib.parse.quote(str(action_id), safe="")
        validation = request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")
        action_validations.append(
            {
                "action_id": validation.get("action_id"),
                "valid": validation.get("valid"),
                "status": validation.get("status"),
                "errors": validation.get("errors", []),
            }
        )
        if validation.get("valid") is not True or validation.get("status") != "valid":
            raise SystemExit(f"Ads action validation failed: {validation}")

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
        if any(connector in REQUIRED_CONNECTORS for connector in item.get("source_connectors", []))
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

    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )

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
                    "optimizer_readiness_contract": {
                        "status": optimizer_readiness_contract.get("status"),
                        "mode": optimizer_readiness_contract.get("mode"),
                        "ready_area_count": optimizer_readiness_contract.get("ready_area_count"),
                        "blocked_area_count": optimizer_readiness_contract.get(
                            "blocked_area_count"
                        ),
                        "apply_allowed": optimizer_readiness_contract.get("apply_allowed"),
                        "readiness_item_ids": [
                            item.get("id")
                            for item in optimizer_readiness_contract.get(
                                "readiness_items",
                            )
                            or []
                            if item.get("id")
                        ],
                        "missing_read_contracts": optimizer_readiness_contract.get(
                            "missing_read_contracts",
                            [],
                        ),
                        "blocked_claims": optimizer_readiness_contract.get(
                            "blocked_claims",
                            [],
                        ),
                    },
                    "account_currency_read_contract": {
                        "status": account_currency_read_contract.get("status"),
                        "currency_code": account_currency_read_contract.get("currency_code"),
                        "missing_read_contracts": account_currency_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "blocked_claims": account_currency_read_contract.get("blocked_claims", []),
                    },
                    "business_context_read_contract": {
                        "status": business_context_read_contract.get("status"),
                        "configured_sources": business_context_read_contract.get(
                            "configured_sources", []
                        ),
                        "strategy_review_readiness_contract": {
                            "status": strategy_readiness_contract.get("status"),
                            "latest_review_status": strategy_readiness_contract.get(
                                "latest_review_status"
                            ),
                            "missing_read_contracts": strategy_readiness_contract.get(
                                "missing_read_contracts", []
                            ),
                            "action_ids": strategy_readiness_contract.get("action_ids", []),
                            "apply_allowed": strategy_readiness_contract.get("apply_allowed"),
                        },
                        "missing_read_contracts": business_context_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "blocked_claims": business_context_read_contract.get("blocked_claims", []),
                    },
                    "budget_pacing_read_contract": {
                        "status": budget_pacing_read_contract.get("status"),
                        "summary": budget_pacing_read_contract.get("summary"),
                        "allowed_metrics": budget_pacing_read_contract.get("allowed_metrics", []),
                        "missing_read_contracts": budget_pacing_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "row_count": len(budget_pacing_read_contract.get("budget_rows") or []),
                    },
                    "budget_decision": {
                        "id": budget_decision.get("id"),
                        "status": budget_decision.get("status"),
                        "knowledge_card_ids": budget_decision.get("knowledge_card_ids", []),
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
                        "apply_preview_count": len(
                            recommendations_read_contract.get("payload_preview") or []
                        ),
                        "impact_row_count": sum(
                            1
                            for row in recommendations_read_contract.get(
                                "recommendation_rows",
                            )
                            or []
                            if row.get("impact_available")
                        ),
                        "urgent_review_count": sum(
                            1
                            for row in recommendations_read_contract.get(
                                "recommendation_rows",
                            )
                            or []
                            if row.get("review_priority") == "pilne"
                        ),
                        "high_review_count": sum(
                            1
                            for row in recommendations_read_contract.get(
                                "recommendation_rows",
                            )
                            or []
                            if row.get("review_priority") == "wysokie"
                        ),
                        "blocked_claims": recommendations_read_contract.get(
                            "blocked_claims",
                            [],
                        ),
                        "action_ids": recommendations_read_contract.get("action_ids", []),
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
                    "change_impact_readiness_contract": {
                        "status": change_impact_readiness_contract.get("status"),
                        "summary": change_impact_readiness_contract.get("summary"),
                        "allowed_metrics": change_impact_readiness_contract.get(
                            "allowed_metrics",
                            [],
                        ),
                        "missing_read_contracts": change_impact_readiness_contract.get(
                            "missing_read_contracts",
                            [],
                        ),
                        "row_count": len(
                            change_impact_readiness_contract.get("readiness_rows") or []
                        ),
                        "current_snapshot_count": sum(
                            1
                            for row in change_impact_readiness_contract.get(
                                "readiness_rows",
                            )
                            or []
                            if row.get("current_campaign_metrics_available")
                        ),
                        "apply_allowed": change_impact_readiness_contract.get("apply_allowed"),
                        "blocked_claims": change_impact_readiness_contract.get(
                            "blocked_claims",
                            [],
                        ),
                    },
                    "search_terms_read_contract": {
                        "status": search_terms_read_contract.get("status"),
                        "summary": search_terms_read_contract.get("summary"),
                        "allowed_metrics": search_terms_read_contract.get("allowed_metrics", []),
                        "missing_read_contracts": search_terms_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "row_count": len(search_terms_read_contract.get("search_term_rows") or []),
                    },
                    "search_term_review_summary_contract": {
                        "status": search_term_review_summary_contract.get("status"),
                        "summary": search_term_review_summary_contract.get("summary"),
                        "campaign_review_row_count": len(
                            search_term_review_summary_contract.get("campaign_review_rows") or []
                        ),
                        "zero_conversion_search_term_count": (
                            search_term_review_summary_contract.get(
                                "zero_conversion_search_term_count"
                            )
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
                        "row_count": len(search_term_safety_read_contract.get("safety_rows") or []),
                        "blocked_claims": search_term_safety_read_contract.get(
                            "blocked_claims",
                            [],
                        ),
                    },
                    "keyword_match_context_read_contract": {
                        "status": keyword_match_context_read_contract.get("status"),
                        "summary": keyword_match_context_read_contract.get("summary"),
                        "context_row_count": len(
                            keyword_match_context_read_contract.get("context_rows") or []
                        ),
                        "missing_read_contracts": keyword_match_context_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "blocked_claims": keyword_match_context_read_contract.get(
                            "blocked_claims", []
                        ),
                    },
                    "keyword_planner_read_contract": {
                        "status": keyword_planner_read_contract.get("status"),
                        "summary": keyword_planner_read_contract.get("summary"),
                        "idea_row_count": len(keyword_planner_read_contract.get("idea_rows") or []),
                        "missing_read_contracts": keyword_planner_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "blocked_claims": keyword_planner_read_contract.get("blocked_claims", []),
                    },
                    "custom_segments_read_contract": {
                        "status": custom_segments_read_contract.get("status"),
                        "summary": custom_segments_read_contract.get("summary"),
                        "candidate_count": len(
                            custom_segments_read_contract.get("candidates") or []
                        ),
                        "keyword_planner_idea_count": custom_segment_idea_count,
                        "missing_read_contracts": custom_segments_read_contract.get(
                            "missing_read_contracts", []
                        ),
                        "blocked_claims": custom_segments_read_contract.get("blocked_claims", []),
                        "action_ids": custom_segments_read_contract.get("action_ids", []),
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
                        "blocked_claims": negative_keywords_read_contract.get("blocked_claims", []),
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
                    "latest_refresh_status": (ads_diagnostics.get("latest_refresh") or {}).get(
                        "status"
                    ),
                },
                "brief_items": brief_items,
                "evidence_count": len(pack.get("evidence_summaries") or []),
                "opportunity_count": len(pack.get("top_opportunities") or []),
                "action_count": len(pack.get("active_action_objects") or []),
                "action_validations": action_validations,
                "context_pack_bytes": pack_bytes,
                "context_pack_decision_count": len(pack_decision_queue),
                "full_context_decision_count": len(full_pack_decision_queue),
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


def _find_readiness_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == item_id:
            return item
    return {}


def validate_context_lineage(pack: dict[str, Any]) -> None:
    decision_queue = pack.get("ads_diagnostics", {}).get("decision_queue") or []
    referenced_knowledge_card_ids = {
        card_id
        for decision in decision_queue
        if isinstance(decision, dict)
        for card_id in decision.get("knowledge_card_ids", [])
    }
    referenced_expert_rule_ids = {
        rule_id
        for decision in decision_queue
        if isinstance(decision, dict)
        for rule_id in decision.get("expert_rule_ids", [])
    }
    if not referenced_knowledge_card_ids:
        raise SystemExit("Ads context-pack decisions must expose knowledge card IDs")
    if not referenced_expert_rule_ids:
        raise SystemExit("Ads context-pack decisions must expose expert rule IDs")
    context_knowledge_card_ids = {
        card.get("id")
        for card in pack.get("knowledge_card_summaries", [])
        if isinstance(card, dict)
    }
    context_expert_rule_ids = {
        rule.get("id") for rule in pack.get("expert_rule_summaries", []) if isinstance(rule, dict)
    }
    missing_cards = referenced_knowledge_card_ids - context_knowledge_card_ids
    missing_rules = referenced_expert_rule_ids - context_expert_rule_ids
    if missing_cards:
        raise SystemExit(
            "Ads context-pack lacks knowledge card summaries for: "
            + ", ".join(sorted(missing_cards))
        )
    if missing_rules:
        raise SystemExit(
            "Ads context-pack lacks expert rule summaries for: " + ", ".join(sorted(missing_rules))
        )


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
