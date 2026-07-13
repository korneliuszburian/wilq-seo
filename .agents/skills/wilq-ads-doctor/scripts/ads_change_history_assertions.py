from __future__ import annotations

from typing import Any


def validate_change_history_contract(
    ads_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    contract = ads_diagnostics.get("change_history_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose change_history_read_contract")
    if not contract.get("blocked_claims"):
        raise SystemExit("Change history contract must list zablokowane obietnice")
    if contract.get("status") == "ready":
        packed = pack.get("ads_diagnostics", {}).get("change_history_read_contract") or {}
        if packed.get("summary") != contract.get("summary"):
            raise SystemExit("Context pack change history contract differs")
        if "wpływ zmian" not in contract.get("blocked_claims", []):
            raise SystemExit("Change history contract must keep wpływ zmian blocked")
        return contract
    missing = set(contract.get("missing_read_contracts") or [])
    rows = contract.get("change_history_rows") or []
    if "change_history" not in missing and not ("change_event_rows" in missing and len(rows) == 0):
        raise SystemExit(
            "Blocked change history contract must list missing change_history "
            "or empty change_event_rows"
        )
    return contract
