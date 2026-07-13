from __future__ import annotations

from typing import Any


def validate_impression_share_contract(
    ads_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    contract = ads_diagnostics.get("impression_share_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose impression_share_read_contract")
    if not contract.get("blocked_claims"):
        raise SystemExit("Impression share contract must list zablokowane obietnice")
    if contract.get("status") == "ready":
        packed = pack.get("ads_diagnostics", {}).get("impression_share_read_contract") or {}
        if packed.get("summary") != contract.get("summary"):
            raise SystemExit("Context pack impression share contract differs")
        if "zmiana budżetu" not in contract.get("blocked_claims", []):
            raise SystemExit("Impression share contract must keep zmiana budżetu blocked")
    elif "impression_share" not in contract.get("missing_read_contracts", []):
        raise SystemExit("Blocked impression share contract must list missing impression_share")
    return contract
