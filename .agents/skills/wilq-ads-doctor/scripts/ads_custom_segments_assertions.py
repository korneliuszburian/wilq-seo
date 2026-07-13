from __future__ import annotations

from typing import Any


def validate_custom_segments_contract(
    ads_diagnostics: dict[str, Any],
    pack: dict[str, Any],
    keyword_planner: dict[str, Any],
) -> dict[str, Any]:
    contract = ads_diagnostics.get("custom_segments_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose custom_segments_read_contract")
    packed = pack.get("ads_diagnostics", {}).get("custom_segments_read_contract") or {}
    if packed.get("summary") != contract.get("summary"):
        raise SystemExit("Context pack custom segments contract differs")
    missing = set(contract.get("missing_read_contracts") or [])
    idea_count = sum(
        len(candidate.get("keyword_planner_ideas") or [])
        for candidate in contract.get("candidates") or []
    )
    if keyword_planner.get("status") == "ready":
        if "keyword_planner_enrichment" in missing:
            raise SystemExit("Ready Keyword Planner must unblock custom segments enrichment")
        if not idea_count:
            raise SystemExit("Ready Keyword Planner must enrich custom segment candidates")
    elif contract.get("status") == "ready":
        if "keyword_planner_enrichment" not in missing:
            raise SystemExit("Custom segments must keep Keyword Planner enrichment missing")
        if idea_count:
            raise SystemExit("Blocked Keyword Planner must not enrich custom segment candidates")
    return contract
