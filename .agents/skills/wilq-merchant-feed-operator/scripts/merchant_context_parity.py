from __future__ import annotations

from typing import Any


def validate_merchant_context_parity(
    merchant_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    packed = pack.get("merchant_diagnostics", {})
    if packed.get("evidence_ids") != merchant_diagnostics.get("evidence_ids"):
        raise SystemExit("Context pack merchant_diagnostics evidence IDs differ from endpoint")
    if packed.get("action_ids") != merchant_diagnostics.get("action_ids"):
        raise SystemExit("Context pack merchant_diagnostics action IDs differ from endpoint")
    packed_price = packed.get("price_impact_readiness")
    endpoint_price = merchant_diagnostics.get("price_impact_readiness")
    if not isinstance(packed_price, dict) or not isinstance(endpoint_price, dict):
        raise SystemExit("Context pack merchant price_impact_readiness must be an object")
    for key in (
        "status",
        "evidence_ids",
        "source_connectors",
        "missing_read_contracts",
        "blocked_claims",
    ):
        if packed_price.get(key) != endpoint_price.get(key):
            raise SystemExit(f"Context pack merchant price_impact_readiness differs on {key}")
    preview = endpoint_price.get("change_preview")
    if isinstance(preview, list) and packed_price.get("change_preview_total") != len(preview):
        raise SystemExit("Context pack merchant price preview total differs from endpoint")
    return packed
