from __future__ import annotations

from typing import Any


def build_report(
    health: dict[str, Any],
    api_base: str,
    connectors: list[dict[str, Any]],
    ads: dict[str, Any],
    read_contract: dict[str, Any],
    forecast: dict[str, Any],
    candidates: list[dict[str, Any]],
    safety: dict[str, Any],
    action_validation: dict[str, Any] | None,
    action_validations: list[dict[str, Any]],
    brief_items: list[dict[str, Any]],
    pack: dict[str, Any],
    decision_ids: list[str],
) -> dict[str, Any]:
    return {
        "skill": "wilq-custom-segments",
        "api_base": api_base,
        "health": health.get("status"),
        "required_connectors": connectors,
        "ads_diagnostics": {
            "live_data_available": ads.get("live_data_available"),
            "custom_segments_read_contract": {
                "status": read_contract.get("status"),
                "summary": read_contract.get("summary"),
                "candidate_count": len(candidates),
                "change_preview_count": len(read_contract.get("payload_preview") or []),
                "apply_safety_review": {
                    "status": safety.get("status"),
                    "safety_contract": safety.get("safety_contract"),
                    "missing_requirements": safety.get("missing_requirements", []),
                    "audit_required": safety.get("audit_required"),
                    "apply_allowed": safety.get("apply_allowed"),
                },
                "missing_read_contracts": read_contract.get("missing_read_contracts", []),
                "audience_forecast_read_contract": {
                    "status": forecast.get("status"),
                    "forecast_row_count": forecast.get("forecast_row_count"),
                    "missing_read_contracts": forecast.get("missing_read_contracts", []),
                    "blocked_claims": forecast.get("blocked_claims", []),
                },
                "blocked_claims": read_contract.get("blocked_claims", []),
                "action_ids": read_contract.get("action_ids", []),
            },
            "decision_ids": decision_ids,
            "section_ids": [
                section.get("id") for section in ads.get("sections", []) if section.get("id")
            ],
        },
        "custom_segment_candidates": [
            {
                "id": candidate.get("id"),
                "name": candidate.get("name"),
                "review_priority": candidate.get("review_priority"),
                "review_score": candidate.get("review_score"),
                "review_reason": candidate.get("review_reason"),
                "human_review_gates": candidate.get("human_review_gates", []),
                "source_terms": candidate.get("source_terms", []),
                "confidence": candidate.get("confidence"),
                "validation_status": candidate.get("validation_status"),
                "evidence_ids": candidate.get("evidence_ids", []),
            }
            for candidate in candidates[:6]
        ],
        "custom_segment_action_validation": action_validation,
        "action_validations": action_validations,
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
        "action_ids": [
            item.get("id") for item in (pack.get("active_action_objects") or []) if item.get("id")
        ][:20],
        "context_decision_ids": decision_ids,
    }
