from __future__ import annotations

from typing import Any


def build_report(
    health: dict[str, Any],
    api_base: str,
    connectors: list[dict[str, Any]],
    brief_items: list[dict[str, Any]],
    pack: dict[str, Any],
    diagnostics: dict[str, Any],
    gap: dict[str, Any],
    record_count: int,
    missing: list[Any],
    status: Any,
    states: list[str],
    labels: list[str],
    operator_summary: dict[str, Any],
    action_ids: list[str],
    action_validations: dict[str, dict[str, Any]],
    decision_ids: set[str],
) -> dict[str, Any]:
    return {
        "skill": "wilq-ahrefs-gap-finder",
        "api_base": api_base,
        "health": health.get("status"),
        "required_connectors": connectors,
        "brief_items": brief_items,
        "evidence_count": len(pack.get("evidence_summaries") or []),
        "opportunity_count": len(pack.get("top_opportunities") or []),
        "action_count": len(pack.get("active_action_objects") or []),
        "diagnostics_action_ids": action_ids[:20],
        "action_validations": action_validations,
        "ahrefs_authority_fact_count": diagnostics.get("authority_fact_count"),
        "ahrefs_gap_fact_count": diagnostics.get("gap_fact_count"),
        "ahrefs_blocker_count": diagnostics.get("blocker_count"),
        "gap_read_contract": {
            "status": gap.get("status"),
            "gap_record_count": record_count,
            "gap_records_omitted": bool(gap.get("gap_records_omitted")),
            "missing_read_contracts": missing,
            "blocked_claims": gap.get("blocked_claims", []),
            "cross_check_status": status,
            "cross_check_summary": gap.get("cross_check_summary"),
            "cross_check_candidates_total": gap.get("cross_check_candidates_total"),
            "freshness_states": states,
            "freshness_labels": labels[:5],
            "review_mode": "validation-only",
        },
        "ahrefs_review_card": {
            "review_card_label": operator_summary.get("review_card_label"),
            "review_decision_after_review": operator_summary.get("review_decision_after_review"),
            "review_question_for_operator": operator_summary.get("review_question_for_operator"),
            "review_next_safe_click": operator_summary.get("review_next_safe_click"),
            "review_action_ids": operator_summary.get("review_action_ids", []),
        },
        "ahrefs_decision_ids": sorted(decision_ids),
        "evidence_ids": [
            item.get("id") for item in (pack.get("evidence_summaries") or []) if item.get("id")
        ][:20],
        "opportunity_ids": [
            item.get("id") for item in (pack.get("top_opportunities") or []) if item.get("id")
        ][:20],
        "action_ids": [
            item.get("id") for item in (pack.get("active_action_objects") or []) if item.get("id")
        ][:20],
    }
