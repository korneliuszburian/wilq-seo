from __future__ import annotations

from typing import Any


def validate_search_term_ngram_contract(ads_diagnostics: dict[str, Any]) -> dict[str, Any]:
    contract = ads_diagnostics.get("search_term_ngram_read_contract") or {}
    if contract.get("status") != "ready":
        return contract
    missing = set(contract.get("missing_read_contracts") or [])
    if "negative_keyword_change_preview" in missing:
        raise SystemExit(
            "Search-term n-gram contract must not use the generic negative "
            "keyword change preview blocker"
        )
    if "ngram_to_negative_keyword_change_preview" not in missing:
        raise SystemExit(
            "Search-term n-gram contract must list the n-gram-specific change preview blocker"
        )
    return contract
