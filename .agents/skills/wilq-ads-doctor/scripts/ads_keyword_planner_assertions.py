from __future__ import annotations

from typing import Any


def validate_keyword_planner_contract(
    ads_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    contract = ads_diagnostics.get("keyword_planner_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose keyword_planner_read_contract")
    if not contract.get("blocked_claims"):
        raise SystemExit("Keyword Planner contract must list zablokowane obietnice")
    packed = pack.get("ads_diagnostics", {}).get("keyword_planner_read_contract") or {}
    if packed.get("summary") != contract.get("summary"):
        raise SystemExit("Context pack Keyword Planner contract differs")
    if contract.get("status") == "ready":
        if not contract.get("idea_rows") or not packed.get("idea_rows"):
            raise SystemExit("Ready Keyword Planner contract must expose idea rows")
        missing = set(contract.get("missing_read_contracts") or [])
        if "keyword_planner_enrichment" in missing:
            raise SystemExit("Ready Keyword Planner contract must not stay missing")
        if "forecast_or_audience_size" not in missing:
            raise SystemExit("Keyword Planner must keep forecast or audience-size blocked")
    else:
        if "keyword_planner_enrichment" not in contract.get("missing_read_contracts", []):
            raise SystemExit("Blocked Keyword Planner contract must list missing enrichment")
        if contract.get("idea_rows"):
            raise SystemExit("Blocked Keyword Planner contract must not expose idea rows")
    return contract
