from __future__ import annotations

from collections.abc import Callable
from typing import Any


def validate_context_contract(
    pack: dict[str, Any], ads_diagnostics: dict[str, Any], action_id: str
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str], list[str]]:
    if ads_diagnostics.get("language") != "pl-PL":
        raise SystemExit("Ads diagnostics language must be pl-PL")
    packed = pack.get("ads_diagnostics") or {}
    if packed.get("evidence_ids") != ads_diagnostics.get("evidence_ids"):
        raise SystemExit("Context pack ads_diagnostics evidence IDs differ from endpoint")
    pack_actions = packed.get("action_ids") or []
    active_actions = [
        item.get("id") for item in (pack.get("active_action_objects") or []) if item.get("id")
    ]
    if any(item != action_id for item in pack_actions + active_actions):
        raise SystemExit("Custom segments context must expose only the custom segment action")
    decisions = [item.get("id") for item in (packed.get("decision_queue") or []) if item.get("id")]
    if any(item != "ads_prepare_custom_segments_from_search_terms" for item in decisions):
        raise SystemExit("Custom segments context must expose only the custom segment decision")
    return (
        packed,
        packed.get("custom_segments_read_contract") or {},
        pack_actions,
        active_actions,
        decisions,
    )


def validate_candidate_contract(
    api_base: str,
    read_contract: dict[str, Any],
    forecast_contract: dict[str, Any],
    candidates: list[dict[str, Any]],
    pack_action_ids: list[str],
    active_action_ids: list[str],
    decision_ids: list[str],
    action_id: str,
    request_json: Callable[..., dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[str, Any]]:
    if not candidates:
        if not read_contract.get("missing_read_contracts"):
            raise SystemExit("Blocked custom segments contract must list missing read contracts")
        return None, [], {}
    _validate_forecast(forecast_contract)
    first = candidates[0]
    for field in ("source_terms", "evidence_ids", "payload_preview", "human_review_gates"):
        if not first.get(field):
            raise SystemExit(f"Custom segment candidate must expose {field}")
    if first.get("review_priority") not in {"pilne", "wysokie", "normalne", "niski sygnał"}:
        raise SystemExit("Custom segment candidate must expose review_priority")
    score = first.get("review_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise SystemExit("Custom segment candidate review_score must be 0-100")
    reason = str(first.get("review_reason") or "")
    if "kolejność oceny segmentu" not in reason or "nie dowód rozmiaru odbiorców" not in reason:
        raise SystemExit("Custom segment candidate must explain validation triage")
    if first["payload_preview"].get("apply_allowed") is not False:
        raise SystemExit("Custom segment change preview must keep apply_allowed=false")
    if "custom_segment_change_preview" in read_contract.get("missing_read_contracts", []):
        raise SystemExit("Ready custom segments contract must not miss change preview")
    if not read_contract.get("payload_preview"):
        raise SystemExit("Ready custom segments contract must expose payload_preview")
    safety = read_contract["payload_preview"][0].get("safety_review") or {}
    if safety.get("safety_contract") != "custom_segment_apply_safety_v1":
        raise SystemExit("Custom segment payload_preview must expose apply safety_review")
    if safety.get("apply_allowed") is not False or safety.get("api_mutation_ready") is not False:
        raise SystemExit("Custom segment safety_review must keep apply blocked")
    if safety.get("audit_required") is not True:
        raise SystemExit("Custom segment safety_review must require mutation audit")
    if not {"forecast_or_audience_size", "google_ads_mutation_audit"}.issubset(
        set(safety.get("missing_requirements") or [])
    ):
        raise SystemExit("Custom segment safety_review must require forecast and mutation audit")
    if action_id not in read_contract.get("action_ids", []):
        raise SystemExit("Custom segments read contract must expose custom segment action")
    if pack_action_ids != [action_id] or active_action_ids != [action_id]:
        raise SystemExit("Custom segments context must expose only the custom segment action")
    if decision_ids != ["ads_prepare_custom_segments_from_search_terms"]:
        raise SystemExit("Custom segments context must expose the custom segment decision")
    validation = request_json(api_base, "POST", f"/api/actions/{action_id}/validate", {})
    if validation.get("valid") is not True:
        raise SystemExit("Custom segment action validation must pass when candidates exist")
    compact_validation = {
        "action_id": validation.get("action_id"),
        "valid": validation.get("valid"),
        "status": validation.get("status"),
        "errors": validation.get("errors", []),
    }
    return validation, [compact_validation], safety


def _validate_forecast(contract: dict[str, Any]) -> None:
    rows = contract.get("forecast_rows") or []
    if not rows:
        raise SystemExit("Ready custom segments contract must expose forecast blocker rows")
    row = rows[0]
    if row.get("status") != "missing_forecast" or row.get("forecast_available") is not False:
        raise SystemExit("Audience forecast row must show missing forecast state")
    if row.get("audience_size") is not None:
        raise SystemExit("Audience forecast row must not invent audience_size")
