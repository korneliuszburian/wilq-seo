from __future__ import annotations

from typing import Any


def build_merchant_smoke_report(
    *,
    api_base: str,
    health: dict[str, Any],
    connector_results: list[dict[str, Any]],
    merchant_diagnostics: dict[str, Any],
    issue_clusters: list[dict[str, Any]],
    decision_queue: list[dict[str, Any]],
    unknowns: list[dict[str, Any]],
    freshness_assessment: dict[str, Any],
    operator_summary: dict[str, Any],
    product_sample_readiness: Any,
    product_performance_readiness: Any,
    price_impact_readiness: Any,
    merchant_preview_cards: list[dict[str, Any]],
    brief_items: list[dict[str, Any]],
    action_validations: list[dict[str, Any]],
    pack: dict[str, Any],
    context_pack_action_status: Any,
    context_pack_validation_status: Any,
) -> dict[str, Any]:
    return {
        "skill": "wilq-merchant-feed-operator",
        "api_base": api_base,
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
            item.get("id") for item in (pack.get("evidence_summaries") or []) if item.get("id")
        ][:20],
        "opportunity_ids": [
            item.get("id") for item in (pack.get("top_opportunities") or []) if item.get("id")
        ][:20],
        "action_validations": action_validations,
        "action_ids": [
            item.get("id") for item in (pack.get("active_action_objects") or []) if item.get("id")
        ][:20],
    }
