#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from merchant_context_parity import validate_merchant_context_parity
from merchant_issue_parity import validate_issue_decision_parity, validate_price_decision_parity
from merchant_price_readiness import validate_price_readiness
from merchant_product_readiness import validate_product_readiness
from merchant_report_compaction import build_merchant_smoke_report
from merchant_runtime_assertions import (
    collect_connector_results,
    compact_brief_items,
    validate_action_ids,
)

from scripts.skill_smoke_harness import (
    has_polish_metric_source_guardrails,
    request_json,
    require_polish_language,
)

SKILL_NAME = "wilq-merchant-feed-operator"
MERCHANT_FEED_ACTION_ID = "act_review_merchant_feed_issues"
MERCHANT_FEED_PREVIEW_CONTRACT = "merchant_feed_issue_review_preview_v1"
MERCHANT_PRICE_IMPACT_DECISION_ID = "merchant_decision_review_price_impact_readiness"
MERCHANT_PRICE_IMPACT_DECISION_TYPE = "review_price_impact_readiness"
MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT = "merchant_price_impact_readiness_preview_v1"
REQUIRED_CONNECTORS = ["google_merchant_center"]
REQUIRED_CONTEXT_KEYS = {
    "strict_instruction",
    "connector_status",
    "evidence_summaries",
    "top_opportunities",
    "active_action_objects",
    "merchant_diagnostics",
}


def find_decision(decisions: list[dict[str, Any]], decision_id: str) -> dict[str, Any] | None:
    for decision in decisions:
        if decision.get("id") == decision_id:
            return decision
    return None


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

    merchant_diagnostics = request_json(args.api_base, "GET", "/api/merchant/diagnostics")
    require_polish_language(merchant_diagnostics, "Merchant diagnostics")
    sections = merchant_diagnostics.get("sections")
    if not isinstance(sections, list) or not sections:
        raise SystemExit("Merchant diagnostics must expose sections")
    packed_merchant = validate_merchant_context_parity(merchant_diagnostics, pack)
    product_sample_readiness = merchant_diagnostics.get("product_sample_readiness")
    product_performance_readiness = validate_product_readiness(merchant_diagnostics)
    price_impact_readiness, price_status, price_preview = validate_price_readiness(
        merchant_diagnostics
    )
    issue_clusters, decision_queue, freshness_assessment, operator_summary = (
        validate_issue_decision_parity(merchant_diagnostics, packed_merchant)
    )
    packed_decision_queue = packed_merchant.get("decision_queue") or []
    unknowns = merchant_diagnostics.get("unknowns") or []
    validate_price_decision_parity(
        price_impact_readiness,
        price_preview,
        price_status,
        decision_queue,
        packed_decision_queue,
        MERCHANT_PRICE_IMPACT_DECISION_ID,
        MERCHANT_PRICE_IMPACT_DECISION_TYPE,
        MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT,
    )
    merchant_action = next(
        (
            action
            for action in pack.get("active_action_objects", [])
            if action.get("id") == MERCHANT_FEED_ACTION_ID
        ),
        None,
    )
    merchant_preview_cards = merchant_action.get("preview_cards", []) if merchant_action else []
    context_pack_action_status = merchant_action.get("status") if merchant_action else None
    context_pack_validation_status = (
        merchant_action.get("validation_status") if merchant_action else None
    )
    if issue_clusters and merchant_action is None:
        raise SystemExit("Merchant issue clusters must expose review action")
    if issue_clusters and not merchant_preview_cards:
        raise SystemExit("Merchant review action must keep compact change preview")
    if issue_clusters and merchant_preview_cards[0].get("kind") != "merchant_feed_issue_review":
        raise SystemExit("Merchant change preview contract mismatch")
    if (
        issue_clusters
        and merchant_preview_cards[0].get("apply_state_label") != "zapis zmian zablokowany"
    ):
        raise SystemExit("Merchant change preview must keep blocked write state")

    action_validations = validate_action_ids(
        args.api_base, merchant_diagnostics.get("action_ids", []), request_json
    )

    brief = request_json(args.api_base, "GET", "/api/marketing/brief")
    brief_items = compact_brief_items(brief, REQUIRED_CONNECTORS)
    connector_results = collect_connector_results(args.api_base, REQUIRED_CONNECTORS, request_json)

    instruction = str(pack.get("strict_instruction", ""))
    if not has_polish_metric_source_guardrails(instruction):
        raise SystemExit(
            "Instrukcja context-packa nie zawiera polskich zasad metryk i dowodów źródłowych"
        )

    print(json.dumps(build_merchant_smoke_report(
        api_base=args.api_base,
        health=health,
        connector_results=connector_results,
        merchant_diagnostics=merchant_diagnostics,
        issue_clusters=issue_clusters,
        decision_queue=decision_queue,
        unknowns=unknowns,
        freshness_assessment=freshness_assessment,
        operator_summary=operator_summary,
        product_sample_readiness=product_sample_readiness,
        product_performance_readiness=product_performance_readiness,
        price_impact_readiness=price_impact_readiness,
        merchant_preview_cards=merchant_preview_cards,
        brief_items=brief_items,
        action_validations=action_validations,
        pack=pack,
        context_pack_action_status=context_pack_action_status,
        context_pack_validation_status=context_pack_validation_status,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
