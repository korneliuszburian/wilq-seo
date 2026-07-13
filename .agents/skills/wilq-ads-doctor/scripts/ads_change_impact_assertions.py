from __future__ import annotations

from typing import Any


def validate_change_impact_contract(
    ads_diagnostics: dict[str, Any],
    pack: dict[str, Any],
    change_history: dict[str, Any],
) -> dict[str, Any]:
    contract = ads_diagnostics.get("change_impact_readiness_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose change_impact_readiness_contract")
    if contract.get("apply_allowed") is not False:
        raise SystemExit("Change impact readiness must keep apply_allowed=false")
    if contract.get("api_mutation_ready") is not False:
        raise SystemExit("Change impact readiness must keep api_mutation_ready=false")
    if "wpływ zmian" not in contract.get("blocked_claims", []):
        raise SystemExit("Change impact readiness must block wpływ zmian claim")
    packed = pack.get("ads_diagnostics", {}).get("change_impact_readiness_contract") or {}
    if packed.get("summary") != contract.get("summary"):
        raise SystemExit("Context pack wpływ zmian readiness contract differs")
    history_rows = change_history.get("change_history_rows") or []
    impact_rows = contract.get("readiness_rows") or []
    if history_rows and not impact_rows:
        raise SystemExit("Change impact readiness must expose rows for change events")
    missing = contract.get("missing_read_contracts") or []
    if impact_rows and "pre_change_performance_window" not in missing:
        raise SystemExit("Change impact readiness must keep pre-change window missing")
    if impact_rows and "post_change_performance_window" not in missing:
        raise SystemExit("Change impact readiness must keep post-change window missing")
    return contract
