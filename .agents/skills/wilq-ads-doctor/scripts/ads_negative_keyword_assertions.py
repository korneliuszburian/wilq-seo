from __future__ import annotations

from typing import Any


def validate_negative_keyword_contract(ads_diagnostics: dict[str, Any]) -> dict[str, Any]:
    contract = ads_diagnostics.get("negative_keywords_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose negative_keywords_read_contract")
    if not contract.get("blocked_claims"):
        raise SystemExit("Negative keyword contract must list zablokowane obietnice")
    if contract.get("status") == "ready":
        if not contract.get("candidates"):
            raise SystemExit("Ready negative keyword contract must expose candidates")
        if not contract.get("payload_preview"):
            raise SystemExit("Ready negative keyword contract must expose payload_preview")
        if "negative_keyword_change_preview" in contract.get("missing_read_contracts", []):
            raise SystemExit(
                "Ready negative keyword contract must not list change preview as missing"
            )
        if "act_prepare_negative_keyword_review_queue" not in contract.get("action_ids", []):
            raise SystemExit("Ready negative keyword contract must expose action")
    elif not contract.get("missing_read_contracts"):
        raise SystemExit("Blocked negative keyword contract must list missing read contracts")
    return contract
