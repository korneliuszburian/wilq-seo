from __future__ import annotations

from collections.abc import Callable
from typing import Any


def validate_optimizer_readiness(
    ads_diagnostics: dict[str, Any],
    pack: dict[str, Any],
    decision_queue: list[dict[str, Any]],
    pack_decision_queue: list[dict[str, Any]],
    find_decision: Callable[[list[dict[str, Any]], str], dict[str, Any]],
    find_readiness_item: Callable[[list[dict[str, Any]], str], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    readiness = ads_diagnostics.get("optimizer_readiness_contract") or {}
    packed_readiness = pack.get("ads_diagnostics", {}).get("optimizer_readiness_contract") or {}
    if readiness.get("status") not in {"review_ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose optimizer_readiness_contract")
    if readiness.get("mode") != "review_only":
        raise SystemExit("Ads optimizer readiness must stay review_only")
    if readiness.get("apply_allowed") is not False:
        raise SystemExit("Ads optimizer readiness must keep apply_allowed=false")
    if readiness.get("api_mutation_ready") is not False:
        raise SystemExit("Ads optimizer readiness must keep api_mutation_ready=false")
    if "zapis zmian kampanii" not in readiness.get("blocked_claims", []):
        raise SystemExit("Ads optimizer readiness must block zapis zmian kampanii claims")
    items = readiness.get("readiness_items") or []
    if not items:
        raise SystemExit("Ads optimizer readiness must expose readiness_items")
    change_impact = find_readiness_item(items, "change_history_impact_review")
    if change_impact.get("status") != "blocked":
        raise SystemExit("Ads optimizer readiness must block wpływ zmian review")
    if "ads_change_history_read_contract" not in change_impact.get("source_contract_ids", []):
        raise SystemExit("Change impact readiness item must cite change history contract")
    if "ads_change_impact_readiness_contract" not in change_impact.get("source_contract_ids", []):
        raise SystemExit("Change impact readiness item must cite readiness contract")
    if "wpływ zmian" not in change_impact.get("blocked_claims", []):
        raise SystemExit("Change impact readiness item must block wpływ zmian claim")
    if find_readiness_item(items, "ads_apply_safety_gate").get("status") != "blocked":
        raise SystemExit("Ads optimizer readiness must block apply safety gate")
    if packed_readiness.get("summary") != readiness.get("summary"):
        raise SystemExit("Context pack optimizer readiness contract differs")
    if packed_readiness.get("mode") != "review_only":
        raise SystemExit("Context pack optimizer readiness must stay review_only")
    if packed_readiness.get("apply_allowed") is not False:
        raise SystemExit("Context pack optimizer readiness must keep apply blocked")
    return (
        readiness,
        find_decision(decision_queue, "ads_review_budget_context"),
        find_decision(pack_decision_queue, "ads_review_budget_context"),
    )
