from __future__ import annotations

from typing import Any

from ads_report_compaction import compact_blocked_handoff, unique_ids


def _contract(contract: dict[str, Any], row_key: str) -> dict[str, Any]:
    return {
        "status": contract.get("status"),
        "summary": contract.get("summary"),
        "allowed_metrics": contract.get("allowed_metrics", []),
        "missing_read_contracts": contract.get("missing_read_contracts", []),
        "row_count": len(contract.get(row_key) or []),
        "blocked_claims": contract.get("blocked_claims", []),
    }


def _account_report(
    currency: dict[str, Any],
    business: dict[str, Any],
    strategy: dict[str, Any],
    budget: dict[str, Any],
    budget_decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "account_currency_read_contract": {
            "status": currency.get("status"),
            "currency_code": currency.get("currency_code"),
            "missing_read_contracts": currency.get("missing_read_contracts", []),
            "blocked_claims": currency.get("blocked_claims", []),
        },
        "business_context_read_contract": {
            "status": business.get("status"),
            "configured_sources": business.get("configured_sources", []),
            "strategy_review_readiness_contract": {
                "status": strategy.get("status"),
                "latest_review_status": strategy.get("latest_review_status"),
                "missing_read_contracts": strategy.get("missing_read_contracts", []),
                "action_ids": strategy.get("action_ids", []),
                "apply_allowed": strategy.get("apply_allowed"),
            },
            "missing_read_contracts": business.get("missing_read_contracts", []),
            "blocked_claims": business.get("blocked_claims", []),
        },
        "budget_pacing_read_contract": _contract(budget, "budget_rows"),
        "budget_decision": {
            "id": budget_decision.get("id"),
            "status": budget_decision.get("status"),
            "knowledge_card_ids": budget_decision.get("knowledge_card_ids", []),
            "expert_rule_ids": budget_decision.get("expert_rule_ids", []),
            "action_ids": budget_decision.get("action_ids", []),
            "blocked_claims": budget_decision.get("blocked_claims", []),
        },
    }


def _recommendation_report(contract: dict[str, Any]) -> dict[str, Any]:
    rows = contract.get("recommendation_rows") or []
    result = _contract(contract, "recommendation_rows")
    result.update(
        {
            "apply_preview_count": len(contract.get("payload_preview") or []),
            "impact_row_count": sum(1 for row in rows if row.get("impact_available")),
            "urgent_review_count": sum(1 for row in rows if row.get("review_priority") == "pilne"),
            "high_review_count": sum(1 for row in rows if row.get("review_priority") == "wysokie"),
            "action_ids": contract.get("action_ids", []),
        }
    )
    return result


def _search_report(
    diagnostics: dict[str, Any],
    contracts: dict[str, Any],
    custom_segment_idea_count: int,
) -> dict[str, Any]:
    search_terms = diagnostics.get("search_terms_read_contract") or {}
    review = contracts["search_term_review"]
    safety = contracts["search_term_safety"]
    keyword_match = contracts["keyword_match"]
    planner = contracts["keyword_planner"]
    custom = contracts["custom_segments"]
    return {
        "search_terms_read_contract": _contract(search_terms, "search_term_rows"),
        "search_term_review_summary_contract": {
            "status": review.get("status"),
            "summary": review.get("summary"),
            "campaign_review_row_count": len(review.get("campaign_review_rows") or []),
            "zero_conversion_search_term_count": review.get("zero_conversion_search_term_count"),
        },
        "search_term_safety_read_contract": _contract(safety, "safety_rows"),
        "keyword_match_context_read_contract": {
            "status": keyword_match.get("status"),
            "summary": keyword_match.get("summary"),
            "context_row_count": len(keyword_match.get("context_rows") or []),
            "missing_read_contracts": keyword_match.get("missing_read_contracts", []),
            "blocked_claims": keyword_match.get("blocked_claims", []),
        },
        "keyword_planner_read_contract": {
            "status": planner.get("status"),
            "summary": planner.get("summary"),
            "idea_row_count": len(planner.get("idea_rows") or []),
            "missing_read_contracts": planner.get("missing_read_contracts", []),
            "blocked_claims": planner.get("blocked_claims", []),
        },
        "custom_segments_read_contract": {
            "status": custom.get("status"),
            "summary": custom.get("summary"),
            "candidate_count": len(custom.get("candidates") or []),
            "keyword_planner_idea_count": custom_segment_idea_count,
            "missing_read_contracts": custom.get("missing_read_contracts", []),
            "blocked_claims": custom.get("blocked_claims", []),
            "action_ids": custom.get("action_ids", []),
        },
        "negative_keywords_read_contract": {
            "status": contracts["negative_keywords"].get("status"),
            "summary": contracts["negative_keywords"].get("summary"),
            "candidate_count": len(contracts["negative_keywords"].get("candidates") or []),
            "payload_preview_count": len(
                contracts["negative_keywords"].get("payload_preview") or []
            ),
            "missing_read_contracts": contracts["negative_keywords"].get(
                "missing_read_contracts", []
            ),
            "blocked_claims": contracts["negative_keywords"].get("blocked_claims", []),
            "action_ids": contracts["negative_keywords"].get("action_ids", []),
        },
    }


def _diagnostics_report(
    diagnostics: dict[str, Any],
    contracts: dict[str, Any],
    optimizer: dict[str, Any],
    account: dict[str, Any],
    campaign: dict[str, Any],
    blocked_handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    campaign_report = _contract(campaign, "campaign_rows")
    campaign_report["has_campaign_review_action"] = "act_prepare_ads_campaign_review_queue" in (
        diagnostics.get("action_ids") or []
    )
    result = {
        "live_data_available": diagnostics.get("live_data_available"),
        "blocker_count": diagnostics.get("blocker_count"),
        "campaign_read_contract": campaign_report,
        "optimizer_readiness_contract": {
            "status": optimizer.get("status"),
            "mode": optimizer.get("mode"),
            "ready_area_count": optimizer.get("ready_area_count"),
            "blocked_area_count": optimizer.get("blocked_area_count"),
            "apply_allowed": optimizer.get("apply_allowed"),
            "readiness_item_ids": [
                item.get("id")
                for item in optimizer.get("readiness_items", []) or []
                if item.get("id")
            ],
            "missing_read_contracts": optimizer.get("missing_read_contracts", []),
            "blocked_claims": optimizer.get("blocked_claims", []),
        },
        **account,
        "recommendations_read_contract": _recommendation_report(contracts["recommendations"]),
        "impression_share_read_contract": _contract(
            contracts["impression_share"], "impression_share_rows"
        ),
        "change_history_read_contract": _contract(
            contracts["change_history"], "change_history_rows"
        ),
        "change_impact_readiness_contract": _contract(contracts["change_impact"], "readiness_rows"),
        **_search_report(diagnostics, contracts, contracts["custom_segment_idea_count"]),
        "blocked_handoff": compact_blocked_handoff(blocked_handoff),
        "section_ids": [
            section.get("id") for section in diagnostics.get("sections", []) if section.get("id")
        ],
        "evidence_ids": diagnostics.get("evidence_ids", []),
        "action_ids": diagnostics.get("action_ids", []),
        "blocked_claims": [
            claim
            for section in diagnostics.get("sections", [])
            for claim in section.get("blocked_claims", [])
        ][:20],
        "latest_refresh_status": (diagnostics.get("latest_refresh") or {}).get("status"),
    }
    return result


def build_ads_report(
    *,
    api_base: str,
    health: dict[str, Any],
    pack: dict[str, Any],
    diagnostics: dict[str, Any],
    campaign: dict[str, Any],
    optimizer: dict[str, Any],
    currency: dict[str, Any],
    business: dict[str, Any],
    strategy: dict[str, Any],
    budget: dict[str, Any],
    budget_decision: dict[str, Any],
    contracts: dict[str, Any],
    decision_queue: list[dict[str, Any]],
    brief_items: list[dict[str, Any]],
    connector_results: list[dict[str, Any]],
    blocked_handoff: dict[str, Any] | None,
    action_validations: list[dict[str, Any]],
    pack_bytes: int,
    pack_decision_queue: list[dict[str, Any]],
    full_pack_decision_queue: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "skill": "wilq-ads-doctor",
        "api_base": api_base,
        "health": health.get("status"),
        "required_connectors": connector_results,
        "knowledge_card_ids": unique_ids(
            [
                card_id
                for decision in decision_queue
                for card_id in decision.get("knowledge_card_ids", [])
            ]
            + [
                card.get("id")
                for card in pack.get("knowledge_card_summaries", [])
                if card.get("id")
            ]
        ),
        "expert_rule_ids": unique_ids(
            [
                rule_id
                for decision in decision_queue
                for rule_id in decision.get("expert_rule_ids", [])
            ]
            + [rule.get("id") for rule in pack.get("expert_rule_summaries", []) if rule.get("id")]
        ),
        "ads_diagnostics": _diagnostics_report(
            diagnostics,
            contracts,
            optimizer,
            _account_report(currency, business, strategy, budget, budget_decision),
            campaign,
            blocked_handoff,
        ),
        "brief_items": brief_items,
        "evidence_count": len(pack.get("evidence_summaries") or []),
        "opportunity_count": len(pack.get("top_opportunities") or []),
        "action_count": len(pack.get("active_action_objects") or []),
        "action_validations": action_validations,
        "context_pack_bytes": pack_bytes,
        "context_pack_decision_count": len(pack_decision_queue),
        "full_context_decision_count": len(full_pack_decision_queue),
        "evidence_ids": [
            item.get("id") for item in pack.get("evidence_summaries", []) if item.get("id")
        ][:20],
        "opportunity_ids": [
            item.get("id") for item in pack.get("top_opportunities", []) if item.get("id")
        ][:20],
        "action_ids": [
            item.get("id") for item in pack.get("active_action_objects", []) if item.get("id")
        ][:20],
    }
