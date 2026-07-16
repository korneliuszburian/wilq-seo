from __future__ import annotations

from typing import Any


def validate_ga4_contract(
    pack: dict[str, Any], diagnostics: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[str]]:
    sections = {section.get("id") for section in diagnostics.get("sections", [])}
    missing = {"ga4_landing_behavior", "ga4_tracking_readiness", "ga4_action_safety"} - sections
    if missing:
        raise SystemExit(f"GA4 diagnostics missing sections: {', '.join(sorted(missing))}")
    context = pack.get("ga4_diagnostics") or {}
    if context.get("evidence_ids") != diagnostics.get("evidence_ids") or context.get(
        "action_ids"
    ) != diagnostics.get("action_ids"):
        raise SystemExit("Context-pack GA4 trace differs from route")
    readiness = diagnostics.get("conversion_readiness_contract") or {}
    if (
        readiness.get("id") != "ga4_conversion_readiness_contract"
        or context.get("conversion_readiness_contract") != readiness
    ):
        raise SystemExit("GA4 conversion readiness contract differs from route")
    if readiness.get("status") != "ready":
        missing_contracts = set(readiness.get("missing_read_contracts", []))
        claims = set(readiness.get("blocked_claims", []))
        if "conversion_or_key_event_mapping" not in missing_contracts:
            raise SystemExit("Unconfirmed GA4 conversion readiness must expose mapping gap")
        required = {"współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"}
        if not required.issubset(claims):
            raise SystemExit("Unconfirmed GA4 conversion readiness lacks blocked claims")
    decisions = diagnostics.get("decision_queue", [])
    if _trace(context.get("decision_queue", [])) != _trace(decisions):
        raise SystemExit("Context-pack ga4_diagnostics decision trace differs from route")
    if diagnostics.get("live_data_available") and diagnostics.get("landing_group_count", 0) > 0:
        _validate_decisions(decisions, diagnostics.get("action_ids", []))
    return (
        readiness,
        decisions,
        context,
        [section.get("id") for section in diagnostics.get("sections", [])],
    )


def _trace(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: decision.get(key, [])
            for key in ("id", "decision_type", "source_connectors", "evidence_ids", "action_ids")
        }
        for decision in decisions
    ]


def _validate_decisions(decisions: list[dict[str, Any]], action_ids: list[str]) -> None:
    allowed = {"fix_measurement", "review_landing_mapping", "review_traffic_quality"}
    if not decisions or not {item.get("decision_type") for item in decisions} & allowed:
        raise SystemExit("GA4 diagnostics decision_queue has no useful decision types")
    for decision in decisions:
        if decision.get("decision_type") not in allowed:
            raise SystemExit("GA4 diagnostics expose unknown decision type")
        evidence = decision.get("evidence_ids") or []
        sources = decision.get("source_connectors") or []
        if not evidence or "google_analytics_4" not in sources or not decision.get("next_step"):
            raise SystemExit(f"GA4 decision lacks evidence/source/next_step: {decision.get('id')}")
    action = "act_review_ga4_tracking_quality"
    if action in action_ids and action not in {
        item for decision in decisions for item in decision.get("action_ids", [])
    }:
        raise SystemExit("GA4 decision_queue must carry act_review_ga4_tracking_quality")
