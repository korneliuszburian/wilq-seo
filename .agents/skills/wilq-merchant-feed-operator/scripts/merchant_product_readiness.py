from __future__ import annotations

from typing import Any

from scripts.skill_smoke_harness import require_evidence_sources


def validate_product_readiness(merchant_diagnostics: dict[str, Any]) -> dict[str, Any]:
    sample = merchant_diagnostics.get("product_sample_readiness")
    if not isinstance(sample, dict):
        raise SystemExit("Merchant diagnostics must expose product_sample_readiness")
    if sample.get("current_read_contract") != "merchant_aggregate_product_statuses":
        raise SystemExit("Merchant product_sample_readiness must name the aggregate read contract")
    required_sample = set(sample.get("required_read_contracts") or [])
    if not {
        "merchant_products_list_product_status",
        "merchant_reports_product_view_issue_filter",
    }.issubset(required_sample):
        raise SystemExit("Merchant product_sample_readiness must name product-level read contracts")
    if sample.get("sample_products_available") is True:
        if sample.get("sample_count", 0) <= 0 or not sample.get("sample_product_ids"):
            raise SystemExit("Merchant product_sample_readiness ready state must include samples")
    elif sample.get("status") != "blocked":
        raise SystemExit("Merchant product_sample_readiness without samples must be blocked")

    performance = merchant_diagnostics.get("product_performance_readiness")
    if not isinstance(performance, dict):
        raise SystemExit("Merchant diagnostics must expose product_performance_readiness")
    required_performance = set(performance.get("required_read_contracts") or [])
    if not {
        "merchant_product_id_join_key",
        "google_ads_shopping_product_performance",
        "ga4_item_product_performance",
    }.issubset(required_performance):
        raise SystemExit(
            "Merchant product_performance_readiness must name product performance read contracts"
        )
    status = performance.get("status")
    if status == "ready":
        if performance.get("joined_product_count", 0) <= 0 or not performance.get(
            "performance_rows"
        ):
            raise SystemExit(
                "Ready product_performance_readiness must include joined products and rows"
            )
        for row in performance.get("performance_rows") or []:
            if not row.get("product_id"):
                raise SystemExit("Product performance rows must include product_id")
            require_evidence_sources(row, "Product performance row")
    elif status == "blocked":
        blocked = set(performance.get("blocked_claims") or [])
        if not {
            "zwrot z reklam na poziomie produktu",
            "odzyskany przychód produktu",
            "efekt naprawy produktu",
            "zapis do pliku produktowego",
        }.issubset(blocked):
            raise SystemExit("Blocked product_performance_readiness must block product claims")
    else:
        raise SystemExit("Merchant product_performance_readiness status must be ready or blocked")
    return performance
