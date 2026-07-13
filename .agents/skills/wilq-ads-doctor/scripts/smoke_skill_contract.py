#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from ads_account_readiness import validate_account_business_budget
from ads_campaign_contract import validate_campaign_contract
from ads_context_lineage import validate_context_lineage
from ads_contract_orchestration import validate_ads_contracts
from ads_readiness_assertions import validate_optimizer_readiness
from ads_smoke_aux import validate_auxiliary_contracts
from ads_smoke_report import build_ads_report
from ads_smoke_runtime import load_ads_context

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
    validate_campaign_contract(
        campaign_read_contract,
        campaign_triage_read_contract,
        ads_diagnostics,
        pack,
    )
    strategy_readiness_contract = validate_account_business_budget(
        pack,
        account_currency_read_contract,
        business_context_read_contract,
        budget_pacing_read_contract,
        budget_decision,
        pack_budget_decision,
    )
    contracts = validate_ads_contracts(ads_diagnostics, pack)

    action_validations, brief_items, connector_results = validate_auxiliary_contracts(
        args.api_base,
        pack,
        ads_diagnostics,
        REQUIRED_CONNECTORS,
        VALIDATED_ACTION_IDS,
    )

    report = build_ads_report(
        api_base=args.api_base,
        health=health,
        pack=pack,
        diagnostics=ads_diagnostics,
        campaign=campaign_read_contract,
        optimizer=optimizer_readiness_contract,
        currency=account_currency_read_contract,
        business=business_context_read_contract,
        strategy=strategy_readiness_contract,
        budget=budget_pacing_read_contract,
        budget_decision=budget_decision,
        contracts=contracts,
        decision_queue=decision_queue,
        brief_items=brief_items,
        connector_results=connector_results,
        blocked_handoff=blocked_handoff,
        action_validations=action_validations,
        pack_bytes=pack_bytes,
        pack_decision_queue=pack_decision_queue,
        full_pack_decision_queue=full_pack_decision_queue,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
