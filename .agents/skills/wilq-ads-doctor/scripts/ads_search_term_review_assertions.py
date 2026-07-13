from __future__ import annotations

from typing import Any


def validate_search_term_review_contract(
    ads_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    contract = ads_diagnostics.get("search_term_review_summary_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose search_term_review_summary_contract")
    if contract.get("status") != "ready":
        return contract
    packed = pack.get("ads_diagnostics", {}).get("search_term_review_summary_contract") or {}
    if packed.get("summary") != contract.get("summary"):
        raise SystemExit("Context pack search-term review contract differs")
    if not contract.get("campaign_review_rows"):
        raise SystemExit("Ready search-term review contract must expose campaign rows")
    if "marnowanie budżetu na zapytaniach" not in contract.get("blocked_claims", []):
        raise SystemExit("Search-term review summary must keep waste claim blocked")
    return contract
