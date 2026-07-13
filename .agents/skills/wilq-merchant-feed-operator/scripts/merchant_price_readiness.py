from __future__ import annotations

from typing import Any

PRICE_PREVIEW_CONTRACT = "merchant_price_impact_readiness_preview_v1"


def validate_price_readiness(
    merchant_diagnostics: dict[str, Any],
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    readiness = merchant_diagnostics.get("price_impact_readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("Merchant diagnostics must expose price_impact_readiness")
    required = set(readiness.get("required_read_contracts") or [])
    if not {
        "google_ads_shopping_product_current_price",
        "google_ads_shopping_product_price_history",
        "merchant_price_change_event_or_snapshot",
        "google_ads_or_ga4_product_performance_window",
    }.issubset(required):
        raise SystemExit("Merchant price_impact_readiness must name price readiness read contracts")
    status = readiness.get("status")
    preview = readiness.get("change_preview") or []
    if status == "ready":
        for field, message in (
            ("products_with_current_price", "current prices"),
            ("products_with_previous_price", "previous prices"),
            ("products_with_price_change", "changed prices"),
            ("products_with_performance_metrics", "performance windows"),
        ):
            if readiness.get(field, 0) <= 0:
                raise SystemExit(f"Ready price_impact_readiness must include {message}")
    elif status == "blocked":
        blocked = set(readiness.get("blocked_claims") or [])
        if not {
            "wpływ zmiany ceny",
            "zwrot z reklam na poziomie produktu",
            "opłacalność produktu",
            "zapis do pliku produktowego",
        }.issubset(blocked):
            raise SystemExit("Blocked price_impact_readiness must block price/ROAS claims")
        if not readiness.get("missing_read_contracts"):
            raise SystemExit("Blocked price_impact_readiness must list missing read contracts")
    else:
        raise SystemExit("Merchant price_impact_readiness status must be ready or blocked")
    if preview:
        first = preview[0]
        if first.get("preview_contract") != PRICE_PREVIEW_CONTRACT:
            raise SystemExit("Merchant price readiness preview contract mismatch")
        if first.get("apply_allowed") is not False or first.get("api_mutation_ready") is not False:
            raise SystemExit("Merchant price readiness preview must keep apply blocked")
        products = first.get("products") or []
        if products and "has_price_change" not in products[0]:
            raise SystemExit("Merchant price readiness preview must expose has_price_change")
    return readiness, status, preview
