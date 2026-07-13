from __future__ import annotations

from typing import Any


def validate_price_decision_parity(
    price_impact_readiness: dict[str, Any],
    price_preview: list[dict[str, Any]],
    price_status: str,
    decision_queue: list[dict[str, Any]],
    packed_decision_queue: list[dict[str, Any]],
    decision_id: str,
    decision_type: str,
    preview_contract: str,
) -> None:
    if price_impact_readiness.get("products_with_current_price", 0) <= 0 and not price_preview:
        return
    for surface_name, decisions in (
        ("Merchant diagnostics", decision_queue),
        ("Context pack merchant_diagnostics", packed_decision_queue),
    ):
        price_decision = next((item for item in decisions if item.get("id") == decision_id), None)
        if price_decision is None:
            raise SystemExit(f"{surface_name} must expose {decision_id}")
        if price_decision.get("decision_type") != decision_type:
            raise SystemExit(f"{surface_name} price decision must use {decision_type}")
        if price_decision.get("status") != price_status:
            raise SystemExit(f"{surface_name} price decision status must match price readiness")
        decision_preview = price_decision.get("change_preview") or []
        if not decision_preview or decision_preview[0].get("preview_contract") != preview_contract:
            raise SystemExit(f"{surface_name} price decision preview contract mismatch")
        if not {
            "wpływ zmiany ceny",
            "zwrot z reklam na poziomie produktu",
            "zapis do pliku produktowego",
        }.issubset(set(price_decision.get("blocked_claims") or [])):
            raise SystemExit(f"{surface_name} price decision must block price claims")


def validate_issue_decision_parity(
    merchant_diagnostics: dict[str, Any], packed_merchant: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Validate the marketer-facing Merchant issue and decision queue contract."""
    issue_clusters = merchant_diagnostics.get("issue_clusters") or []
    decision_queue = merchant_diagnostics.get("decision_queue") or []
    freshness_assessment = merchant_diagnostics.get("freshness_assessment") or {}
    operator_summary = merchant_diagnostics.get("operator_summary") or {}
    live = bool(merchant_diagnostics.get("live_data_available"))
    issue_count = merchant_diagnostics.get("issue_count", 0)
    if live and issue_count > 0 and not issue_clusters:
        raise SystemExit("Live Merchant diagnostics with issue_count must expose issue_clusters")
    if live and issue_count > 0 and not decision_queue:
        raise SystemExit("Live Merchant diagnostics with issue_count must expose decision_queue")
    if live and not freshness_assessment:
        raise SystemExit("Live Merchant diagnostics must expose freshness_assessment")
    if live:
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
    return issue_clusters, decision_queue, freshness_assessment, operator_summary
