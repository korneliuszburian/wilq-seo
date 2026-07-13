from __future__ import annotations

from typing import Any


def validate_recommendations_contract(
    ads_diagnostics: dict[str, Any], pack: dict[str, Any]
) -> dict[str, Any]:
    contract = ads_diagnostics.get("recommendations_read_contract") or {}
    if contract.get("status") not in {"ready", "blocked"}:
        raise SystemExit("Ads diagnostics must expose recommendations_read_contract")
    if not contract.get("blocked_claims"):
        raise SystemExit("Recommendations contract must list zablokowane obietnice")
    if contract.get("status") != "ready":
        if "recommendations" not in contract.get("missing_read_contracts", []):
            raise SystemExit("Blocked recommendations contract must list missing recommendations")
        return contract
    packed = pack.get("ads_diagnostics", {}).get("recommendations_read_contract") or {}
    _validate_ready_contract(contract, packed)
    _validate_packed_preview(contract, packed, pack)
    return contract


def _validate_ready_contract(contract: dict[str, Any], packed: dict[str, Any]) -> None:
    if packed.get("summary") != contract.get("summary"):
        raise SystemExit("Context pack recommendations contract differs")
    if "zapis rekomendacji" not in contract.get("blocked_claims", []):
        raise SystemExit("Recommendations contract must keep apply blocked")
    rows = contract.get("recommendation_rows") or []
    previews = contract.get("payload_preview") or []
    impact_count = sum(1 for row in rows if row.get("impact_available"))
    if impact_count and "recommendation_impact_preview" in contract.get(
        "missing_read_contracts", []
    ):
        raise SystemExit("Ready recommendation impact must not remain missing")
    if previews and "recommendation_apply_preview" in contract.get("missing_read_contracts", []):
        raise SystemExit("Ready recommendation change preview must not remain missing")
    if previews and "act_prepare_google_ads_recommendation_review_queue" not in contract.get(
        "action_ids", []
    ):
        raise SystemExit("Ready recommendation change preview must expose action")
    for row in rows:
        if (
            row.get("review_priority") not in {"pilne", "wysokie", "normalne", "niski sygnał"}
            or not isinstance(row.get("review_score"), int)
            or not 0 <= row.get("review_score", -1) <= 100
            or "kolejność przeglądu rekomendacji" not in row.get("review_reason", "")
            or not row.get("human_review_gates")
        ):
            raise SystemExit("Ready recommendation rows must expose review triage")
    for item in previews:
        if item.get("operation_type") != "ApplyRecommendationOperation":
            raise SystemExit("Recommendation preview must use ApplyRecommendationOperation")
        if item.get("apply_allowed") is not False or item.get("api_mutation_ready") is not False:
            raise SystemExit("Recommendation preview must remain non-mutation-ready")


def _validate_packed_preview(
    contract: dict[str, Any], packed: dict[str, Any], pack: dict[str, Any]
) -> None:
    rows = contract.get("recommendation_rows") or []
    previews = contract.get("payload_preview") or []
    impact_count = sum(1 for row in rows if row.get("impact_available"))
    packed_rows = packed.get("recommendation_rows") or []
    packed_previews = packed.get("payload_preview") or []
    packed_compaction = pack.get("ads_diagnostics", {}).get("context_pack_compaction") or {}
    if sum(1 for row in packed_rows if row.get("impact_available")) > impact_count:
        raise SystemExit("Context pack recommendation impact row count differs")
    if rows and not all(
        row.get("review_reason") and row.get("human_review_gates") for row in packed_rows
    ):
        raise SystemExit("Context pack recommendation rows must preserve review triage")
    total = packed_compaction.get("recommendation_apply_preview_total")
    included = packed_compaction.get("recommendation_apply_preview_included")
    if total is not None and total < len(packed_previews):
        raise SystemExit("Context pack recommendation change preview total undercounts")
    if included is not None and included != len(packed_previews):
        raise SystemExit("Context pack recommendation change preview included differs")
    if len(packed_previews) > len(previews):
        raise SystemExit("Context pack recommendation change preview over-includes")
