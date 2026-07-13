from __future__ import annotations

from typing import Any


def validate_keyword_match_context_contract(
    ads_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    contract = ads_diagnostics.get("keyword_match_context_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose keyword_match_context_read_contract")
    if not contract.get("blocked_claims"):
        raise SystemExit("Keyword match context contract must list zablokowane obietnice")
    if contract.get("status") == "ready":
        packed = pack.get("ads_diagnostics", {}).get("keyword_match_context_read_contract") or {}
        if packed.get("summary") != contract.get("summary"):
            raise SystemExit("Context-pack Ads diagnostics must include keyword match context")
    elif "keyword_match_context_read" not in contract.get("missing_read_contracts", []):
        raise SystemExit("Blocked keyword match context must list missing read contract")
    return contract
