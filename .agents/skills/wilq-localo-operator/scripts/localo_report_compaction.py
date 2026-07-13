from __future__ import annotations

from typing import Any


def build_localo_smoke_report(
    *,
    api_base: str,
    health: dict[str, Any],
    connector_results: list[dict[str, Any]],
    brief_items: list[dict[str, Any]],
    latest_status: str,
    latest_source: str,
    refresh_attempt: dict[str, Any] | None,
    metric_summary: dict[str, Any],
    access_status: Any,
    operator_summary: dict[str, Any],
    decision_ids: set[str],
    preview_contract: str | None,
    preview_metric_names: list[str],
    pack: dict[str, Any],
    action_validations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "skill": "wilq-localo-operator",
        "api_base": api_base,
        "health": health.get("status"),
        "required_connectors": connector_results,
        "brief_items": brief_items,
        "localo_refresh_status": latest_status,
        "localo_refresh_source": latest_source,
        "localo_refresh_attempt_status": refresh_attempt.get("status") if refresh_attempt else None,
        "localo_metric_summary": metric_summary,
        "localo_access_status": access_status,
        "localo_review_card": {
            "label": operator_summary.get("review_card_label"),
            "decision_after_review": operator_summary.get("review_decision_after_review"),
            "question_for_operator": operator_summary.get("review_question_for_operator"),
            "next_safe_click": operator_summary.get("review_next_safe_click"),
            "action_ids": operator_summary.get("review_action_ids") or [],
        },
        "localo_decision_ids": sorted(item for item in decision_ids if item),
        "localo_action_preview_contract": preview_contract,
        "localo_preview_metric_names": preview_metric_names[:20],
        "evidence_count": len(pack.get("evidence_summaries") or []),
        "opportunity_count": len(pack.get("top_opportunities") or []),
        "action_count": len(pack.get("active_action_objects") or []),
        "action_validations": action_validations,
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
