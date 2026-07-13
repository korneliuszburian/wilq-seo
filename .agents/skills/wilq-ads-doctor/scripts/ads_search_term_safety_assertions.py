from __future__ import annotations

from typing import Any


def validate_search_term_safety_contract(
    ads_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    contract = ads_diagnostics.get("search_term_safety_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose search_term_safety_read_contract")
    if not contract.get("blocked_claims"):
        raise SystemExit("Search-term safety contract must list zablokowane obietnice")
    if contract.get("status") == "ready":
        packed = pack.get("ads_diagnostics", {}).get("search_term_safety_read_contract") or {}
        if packed.get("summary") != contract.get("summary"):
            raise SystemExit("Context pack search-term safety contract differs")
        if "dodanie wykluczających słów kluczowych" not in contract.get("blocked_claims", []):
            raise SystemExit("Search-term safety contract must keep apply blocked")
    elif "search_term_90d_read" not in contract.get("missing_read_contracts", []):
        raise SystemExit("Blocked search-term safety contract must list missing 90d read")
    return contract
