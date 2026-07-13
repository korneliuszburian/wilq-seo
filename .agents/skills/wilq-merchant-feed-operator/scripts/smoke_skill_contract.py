#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.skill_smoke_harness import (
    has_polish_metric_source_guardrails,
    request_json,
    require_evidence_sources,
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
    packed_merchant = pack.get("merchant_diagnostics", {})
    if packed_merchant.get("evidence_ids") != merchant_diagnostics.get("evidence_ids"):
        raise SystemExit("Context pack merchant_diagnostics evidence IDs differ from endpoint")
    if packed_merchant.get("action_ids") != merchant_diagnostics.get("action_ids"):
        raise SystemExit("Context pack merchant_diagnostics action IDs differ from endpoint")
    packed_price_impact = packed_merchant.get("price_impact_readiness")
    endpoint_price_impact = merchant_diagnostics.get("price_impact_readiness")
    if not isinstance(packed_price_impact, dict) or not isinstance(endpoint_price_impact, dict):
        raise SystemExit("Context pack merchant price_impact_readiness must be an object")
    for key in (
        "status",
        "evidence_ids",
        "source_connectors",
        "missing_read_contracts",
        "blocked_claims",
    ):
        if packed_price_impact.get(key) != endpoint_price_impact.get(key):
            raise SystemExit(
                f"Context pack merchant price_impact_readiness differs on {key}"
            )
    endpoint_preview = endpoint_price_impact.get("change_preview")
    if isinstance(endpoint_preview, list) and packed_price_impact.get(
        "change_preview_total"
    ) != len(endpoint_preview):
        raise SystemExit("Context pack merchant price preview total differs from endpoint")
    product_sample_readiness = merchant_diagnostics.get("product_sample_readiness")
    if not isinstance(product_sample_readiness, dict):
        raise SystemExit("Merchant diagnostics must expose product_sample_readiness")
    current_read_contract = product_sample_readiness.get("current_read_contract")
    if current_read_contract != "merchant_aggregate_product_statuses":
        raise SystemExit("Merchant product_sample_readiness must name the aggregate read contract")
    required_product_contracts = set(product_sample_readiness.get("required_read_contracts") or [])
    if not {
        "merchant_products_list_product_status",
        "merchant_reports_product_view_issue_filter",
    }.issubset(required_product_contracts):
        raise SystemExit("Merchant product_sample_readiness must name product-level read contracts")
    if product_sample_readiness.get("sample_products_available") is True:
        if product_sample_readiness.get("sample_count", 0) <= 0:
            raise SystemExit("Merchant product_sample_readiness ready state must include samples")
        if not product_sample_readiness.get("sample_product_ids"):
            raise SystemExit("Merchant diagnostics with samples must expose sample product IDs")
    elif product_sample_readiness.get("status") != "blocked":
        raise SystemExit("Merchant product_sample_readiness without samples must be blocked")
    product_performance_readiness = merchant_diagnostics.get("product_performance_readiness")
    if not isinstance(product_performance_readiness, dict):
        raise SystemExit("Merchant diagnostics must expose product_performance_readiness")
    required_performance_contracts = set(
        product_performance_readiness.get("required_read_contracts") or []
    )
    if not {
        "merchant_product_id_join_key",
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    }.issubset(required_performance_contracts):
        raise SystemExit(
            "Merchant product_performance_readiness must name product performance read contracts"
        )
    performance_status = product_performance_readiness.get("status")
    if performance_status == "ready":
        if product_performance_readiness.get("joined_product_count", 0) <= 0:
            raise SystemExit("Ready product_performance_readiness must include joined products")
        if not product_performance_readiness.get("performance_rows"):
            raise SystemExit("Ready product_performance_readiness must include rows")
        for row in product_performance_readiness.get("performance_rows") or []:
            if not row.get("product_id"):
                raise SystemExit("Product performance rows must include product_id")
            require_evidence_sources(row, "Product performance row")
    elif performance_status == "blocked":
        blocked_claims = set(product_performance_readiness.get("blocked_claims") or [])
        if not {
            "zwrot z reklam na poziomie produktu",
            "odzyskany przychód produktu",
            "efekt naprawy produktu",
            "zapis do pliku produktowego",
        }.issubset(blocked_claims):
            raise SystemExit(
                "Blocked product_performance_readiness must block product "
                "przychód/zwrot z reklam claims"
            )
    else:
        raise SystemExit("Merchant product_performance_readiness status must be ready or blocked")
    price_impact_readiness = merchant_diagnostics.get("price_impact_readiness")
    if not isinstance(price_impact_readiness, dict):
        raise SystemExit("Merchant diagnostics must expose price_impact_readiness")
    required_price_contracts = set(price_impact_readiness.get("required_read_contracts") or [])
    if not {
        "google_ads_shopping_product_current_price",
        "google_ads_shopping_product_price_history",
        "merchant_price_change_event_or_snapshot",
        "google_ads_or_ga4_product_performance_window",
    }.issubset(required_price_contracts):
        raise SystemExit("Merchant price_impact_readiness must name price readiness read contracts")
    price_status = price_impact_readiness.get("status")
    price_preview = price_impact_readiness.get("change_preview") or []
    if price_status == "ready":
        if price_impact_readiness.get("products_with_current_price", 0) <= 0:
            raise SystemExit("Ready price_impact_readiness must include current prices")
        if price_impact_readiness.get("products_with_previous_price", 0) <= 0:
            raise SystemExit("Ready price_impact_readiness must include previous prices")
        if price_impact_readiness.get("products_with_price_change", 0) <= 0:
            raise SystemExit("Ready price_impact_readiness must include changed prices")
        if price_impact_readiness.get("products_with_performance_metrics", 0) <= 0:
            raise SystemExit("Ready price_impact_readiness must include performance windows")
    elif price_status == "blocked":
        blocked_claims = set(price_impact_readiness.get("blocked_claims") or [])
        if not {
            "wpływ zmiany ceny",
            "zwrot z reklam na poziomie produktu",
            "opłacalność produktu",
            "zapis do pliku produktowego",
        }.issubset(blocked_claims):
            raise SystemExit(
                "Blocked price_impact_readiness must block price/zwrot z reklam claims"
            )
        if not price_impact_readiness.get("missing_read_contracts"):
            raise SystemExit("Blocked price_impact_readiness must list missing read contracts")
    else:
        raise SystemExit("Merchant price_impact_readiness status must be ready or blocked")
    if price_preview:
        if price_preview[0].get("preview_contract") != MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT:
            raise SystemExit("Merchant price readiness preview contract mismatch")
        if price_preview[0].get("apply_allowed") is not False:
            raise SystemExit("Merchant price readiness preview must keep apply_allowed=false")
        if price_preview[0].get("api_mutation_ready") is not False:
            raise SystemExit("Merchant price readiness preview must keep api_mutation_ready=false")
        products = price_preview[0].get("products") or []
        if products:
            first_product = products[0]
            if "has_price_change" not in first_product:
                raise SystemExit("Merchant price readiness preview must expose has_price_change")
    issue_clusters = merchant_diagnostics.get("issue_clusters") or []
    decision_queue = merchant_diagnostics.get("decision_queue") or []
    packed_decision_queue = packed_merchant.get("decision_queue") or []
    unknowns = merchant_diagnostics.get("unknowns") or []
    freshness_assessment = merchant_diagnostics.get("freshness_assessment") or {}
    operator_summary = merchant_diagnostics.get("operator_summary") or {}
    if (
        merchant_diagnostics.get("live_data_available")
        and merchant_diagnostics.get("issue_count", 0) > 0
        and not issue_clusters
    ):
        raise SystemExit("Live Merchant diagnostics with issue_count must expose issue_clusters")
    if (
        merchant_diagnostics.get("live_data_available")
        and merchant_diagnostics.get("issue_count", 0) > 0
        and not decision_queue
    ):
        raise SystemExit("Live Merchant diagnostics with issue_count must expose decision_queue")
    if merchant_diagnostics.get("live_data_available") and not freshness_assessment:
        raise SystemExit("Live Merchant diagnostics must expose freshness_assessment")
    if merchant_diagnostics.get("live_data_available"):
        if "requires_refresh" not in freshness_assessment:
            raise SystemExit("Merchant freshness_assessment must expose requires_refresh")
        if operator_summary.get("decision_source") != "decision_queue":
            raise SystemExit("Merchant operator summary must identify decision_queue as source")
        if operator_summary.get("drilldown_source") != "issue_clusters":
            raise SystemExit("Merchant operator summary must identify issue_clusters as drilldown")
        if operator_summary.get("count_semantics") != "reported_issue_occurrences":
            raise SystemExit(
                "Merchant operator summary must expose reported issue occurrence semantics"
            )
    for cluster in issue_clusters:
        if cluster.get("count_semantics") != "reported_issue_occurrences":
            raise SystemExit("Merchant issue clusters must expose reported issue count semantics")
    for decision in decision_queue:
        if decision.get("count_semantics") != "reported_issue_occurrences":
            raise SystemExit("Merchant decisions must expose reported issue count semantics")
    if price_impact_readiness.get("products_with_current_price", 0) > 0 or price_preview:
        for surface_name, decisions in (
            ("Merchant diagnostics", decision_queue),
            ("Context pack merchant_diagnostics", packed_decision_queue),
        ):
            price_decision = find_decision(decisions, MERCHANT_PRICE_IMPACT_DECISION_ID)
            if price_decision is None:
                raise SystemExit(f"{surface_name} must expose {MERCHANT_PRICE_IMPACT_DECISION_ID}")
            if price_decision.get("decision_type") != MERCHANT_PRICE_IMPACT_DECISION_TYPE:
                raise SystemExit(
                    f"{surface_name} price decision must use {MERCHANT_PRICE_IMPACT_DECISION_TYPE}"
                )
            if price_decision.get("status") != price_status:
                raise SystemExit(f"{surface_name} price decision status must match price readiness")
            decision_preview = price_decision.get("change_preview") or []
            if not decision_preview:
                raise SystemExit(f"{surface_name} price decision must expose change_preview")
            if (
                decision_preview[0].get("preview_contract")
                != MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT
            ):
                raise SystemExit(f"{surface_name} price decision preview contract mismatch")
            decision_claims = set(price_decision.get("blocked_claims") or [])
            if not {
                "wpływ zmiany ceny",
                "zwrot z reklam na poziomie produktu",
                "zapis do pliku produktowego",
            }.issubset(decision_claims):
                raise SystemExit(f"{surface_name} price decision must block price claims")
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

    action_validations = []
    for action_id in merchant_diagnostics.get("action_ids", []):
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
            raise SystemExit(f"Merchant action validation failed: {validation}")

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
                "merchant_diagnostics": {
                    "live_data_available": merchant_diagnostics.get("live_data_available"),
                    "product_count": merchant_diagnostics.get("product_count"),
                    "issue_count": merchant_diagnostics.get("issue_count"),
                    "issue_cluster_count": len(issue_clusters),
                    "decision_count": len(decision_queue),
                    "top_issue_clusters": issue_clusters[:5],
                    "decision_queue": decision_queue[:5],
                    "unknowns": unknowns,
                    "freshness_assessment": freshness_assessment,
                    "operator_summary": operator_summary,
                    "blocker_count": merchant_diagnostics.get("blocker_count"),
                    "section_ids": [
                        section.get("id")
                        for section in merchant_diagnostics.get("sections", [])
                        if section.get("id")
                    ],
                    "evidence_ids": merchant_diagnostics.get("evidence_ids", []),
                    "action_ids": merchant_diagnostics.get("action_ids", []),
                    "tactical_item_ids": [
                        item.get("id")
                        for section in merchant_diagnostics.get("sections", [])
                        for item in section.get("tactical_items", [])
                        if item.get("id")
                    ][:20],
                    "blocked_claims": [
                        claim
                        for section in merchant_diagnostics.get("sections", [])
                        for claim in section.get("blocked_claims", [])
                    ][:20],
                    "product_sample_readiness": product_sample_readiness,
                    "product_performance_readiness": product_performance_readiness,
                    "price_impact_readiness": price_impact_readiness,
                    "latest_refresh_status": (merchant_diagnostics.get("latest_refresh") or {}).get(
                        "status"
                    ),
                    "context_pack_action_status": context_pack_action_status,
                    "context_pack_validation_status": context_pack_validation_status,
                    "preview_card_kinds": [
                        item.get("kind") for item in merchant_preview_cards if item.get("kind")
                    ],
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
                "action_validations": action_validations,
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


if __name__ == "__main__":
    raise SystemExit(main())
